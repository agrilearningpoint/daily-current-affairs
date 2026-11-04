# -*- coding: utf-8 -*-
"""
AI LOOKUP FOR UNTRACKED OFFICEHOLDER POSTS (used by agents/static_gk_validator.py, stage 17c).

When a Static GK line names the holder of a post that config/current_facts.json
does not track (Defence Minister, a state CM, a PSU chief, a scheme head ...),
the validator used to drop the line.  This module tries to verify the holder
from live Google results first:

1. Serper (Google) — two queries per post:
     "current <post> of India <year>"
     "current <post> <year> site:gov.in OR site:nic.in OR site:pib.gov.in"
2. The top OFFICIAL result (gov.in / nic.in / pib.gov.in / org.in / known official
   hosts) is read (direct fetch, then the Jina reader; 10 s each).
3. An LLM (pipeline.ai_router.route) reads ONLY that page text and returns strict
   JSON {post, name, since, source_url, confidence}; "unknown" when unclear.
4. Strict acceptance — all of:
     (a) the name literally appears in the fetched official page text;
     (b) a second, independent source (another Serper result on a different
         host, not older than ~6 months when it carries a date) names the person;
     (c) the LLM confidence is "high".
   Nothing is ever taken from model memory.
5. Accepted results are cached in state/ai_facts_cache.json (TTL 7 days) with
   verified_on + source.  current_facts.json is never written from here; the
   weekly refresh workflow may promote cache entries through a PR.

Budgets per process (= per stage run): ALP_STATIC_GK_AI_MAX_LOOKUPS (8) lookups,
2 Serper queries each (16 max, also drawn from the shared discovery_api.SERPER
budget), 10 s per fetch and ALP_STATIC_GK_AI_BUDGET_S (90) seconds in total.

FAIL-OPEN: no key, no LLM provider, network disabled, a 429, an exhausted budget
or any exception -> ``None`` (the caller keeps today's behaviour: drop the line).
Off under pytest unless a test opts in, and off with ALP_STATIC_GK_AI=0.
"""
from __future__ import annotations

import html
import json
import logging
import os
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger("agent.static_gk_ai_lookup")

ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = ROOT / "state" / "ai_facts_cache.json"
TTL_DAYS = 7
FETCH_TIMEOUT = 10.0
LLM_TIMEOUT = 25.0
SECOND_SOURCE_MAX_AGE_DAYS = 183

# Tests opt in explicitly (monkeypatch this to True); real runs never see PYTEST_CURRENT_TEST.
ALLOW_IN_TESTS = False

OFFICIAL_SUFFIXES = (".gov.in", ".nic.in", ".res.in", ".org.in", ".ac.in", ".edu.in", ".gov")
OFFICIAL_EXTRA = ("pib.gov.in", "rbi.org.in", "icar.org.in", "nabard.org", "iffco.in", "nddb.coop",
                  "fao.org", "who.int", "wto.org", "imf.org", "worldbank.org", "un.org", "isro.gov.in")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")

PROMPT = """You read ONE official web page and report who CURRENTLY holds one post.
Use ONLY the PAGE TEXT below. Do NOT use your own memory. If the page does not clearly
name the current holder of exactly this post, set "name" to "unknown".
POST: {post}
SOURCE URL: {url}
PAGE TEXT (truncated):
{text}

Reply with ONLY this JSON object:
{{"post": "<post>", "name": "<full name exactly as written on the page, or unknown>",
"since": "<YYYY-MM-DD if stated, else null>", "source_url": "{url}",
"confidence": "<high|medium|low>"}}"""


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def norm(s: str) -> str:
    s = re.sub(r"^(?:shri|smt|sri|dr|mr|ms|mrs|prof|gen|general|adm|admiral|air chief marshal|justice|hon'?ble)\.?\s+",
               "", str(s or "").strip(), flags=re.I)
    return re.sub(r"[^a-z0-9\u0900-\u097f]+", " ", s.lower()).strip()


def name_in_text(name: str, text: str) -> bool:
    """Whole-word, case/punctuation-insensitive match ('Dr. S. Jaishankar' ~ 'S Jaishankar')."""
    n = norm(name)
    if not n or len(n) < 4:
        return False
    return f" {n} " in f" {norm(text)} "


def post_key(post: str) -> str:
    return norm(post)


def host_of(url: str) -> str:
    try:
        h = (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""
    return h[4:] if h.startswith("www.") else h


def _site(host: str) -> str:
    """Registrable-ish part used for 'independent source' (pib.gov.in vs mod.gov.in differ)."""
    parts = host.split(".")
    if len(parts) >= 3 and parts[-2] in ("gov", "nic", "org", "co", "ac", "res", "edu", "net"):
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def is_official(url: str) -> bool:
    h = host_of(url)
    return bool(h) and (h.endswith(OFFICIAL_SUFFIXES) or any(h == x or h.endswith("." + x) for x in OFFICIAL_EXTRA))


def page_text(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", " ", raw or "")
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    raw = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", raw)  # markdown links (Jina)
    return re.sub(r"\s+", " ", html.unescape(raw)).strip()


_REL_RE = re.compile(r"(\d+)\s+(minute|hour|day|week|month|year)s?\s+ago", re.I)


def result_age_days(date_str: str, today: date) -> Optional[int]:
    """Age of a Serper 'date' field ('3 days ago', 'Jun 12, 2026', '2026-06-12'); None if unknown."""
    s = str(date_str or "").strip()
    if not s:
        return None
    m = _REL_RE.search(s)
    if m:
        n, unit = int(m.group(1)), m.group(2).lower()
        mult = {"minute": 0, "hour": 0, "day": 1, "week": 7, "month": 30, "year": 365}[unit]
        return n * mult
    for fmt in ("%b %d, %Y", "%d %b %Y", "%B %d, %Y", "%d %B %Y", "%Y-%m-%d"):
        try:
            return (today - datetime.strptime(s, fmt).date()).days
        except ValueError:
            continue
    return None


# --------------------------------------------------------------------------- #
# cache
# --------------------------------------------------------------------------- #
def load_cache(path: Optional[Path] = None) -> Dict[str, Any]:
    p = Path(path or CACHE_PATH)
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(doc, dict) and isinstance(doc.get("records"), dict):
            return doc
    except Exception:
        pass
    return {"version": 1, "records": {}}


def save_cache(doc: Dict[str, Any], path: Optional[Path] = None) -> None:
    p = Path(path or CACHE_PATH)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(p)
    except Exception as exc:  # cache is best-effort
        logger.info("[static-gk-ai] cache not saved: %s", exc)


def cache_fresh(rec: Dict[str, Any], today: date, ttl_days: int = TTL_DAYS) -> bool:
    try:
        d = date.fromisoformat(str(rec.get("verified_on"))[:10])
    except ValueError:
        return False
    return 0 <= (today - d).days <= ttl_days and bool(rec.get("name"))


# --------------------------------------------------------------------------- #
# default I/O (all replaceable in tests)
# --------------------------------------------------------------------------- #
def default_search(query: str) -> List[Dict[str, Any]]:
    from pipeline.discovery_api import serper_search
    return serper_search(query, num=8)


def default_fetch(url: str) -> str:
    """Official page text: direct GET, then the Jina reader. '' on failure."""
    import requests
    try:
        r = requests.get(url, headers={"User-Agent": UA, "Accept": "text/html,*/*",
                                       "Accept-Language": "en-US,en;q=0.9"}, timeout=FETCH_TIMEOUT)
        if r.status_code == 200 and "html" in (r.headers.get("content-type") or "html").lower():
            t = page_text(r.text)
            if len(t) > 200:
                return t
    except Exception as exc:
        logger.debug("[static-gk-ai] direct fetch failed: %s", type(exc).__name__)
    try:
        from pipeline.discovery_api import jina_read
        text, _img = jina_read(url, timeout=FETCH_TIMEOUT)
        return page_text(text.split("Markdown Content:", 1)[-1]) if text else ""
    except Exception:
        return ""


def default_llm(prompt: str) -> Optional[str]:
    from pipeline.ai_router import route
    return route(prompt, task="fact_verification", response_format={"type": "json_object"},
                 system_prompt="You extract facts from the given page text only. Return JSON only.")


def default_ready() -> Tuple[bool, str]:
    if os.getenv("ALP_STATIC_GK_AI", "1") == "0":
        return False, "disabled (ALP_STATIC_GK_AI=0)"
    if os.getenv("ALP_DISABLE_NETWORK", "0") == "1":
        return False, "network disabled"
    if os.getenv("PYTEST_CURRENT_TEST") and not ALLOW_IN_TESTS:
        return False, "off under pytest"
    try:
        from pipeline.discovery_api import SERPER
        if not SERPER.enabled():
            return False, "SERPER_API_KEY missing or Serper off"
        from pipeline.ai_router import is_configured
        if not is_configured():
            return False, "no LLM provider configured"
    except Exception as exc:
        return False, f"unavailable: {type(exc).__name__}"
    return True, ""


def _call_with_timeout(fn: Callable[[], Any], timeout: float) -> Any:
    """Run fn in a daemon thread; None on timeout (never blocks process exit)."""
    box: Dict[str, Any] = {}

    def _run() -> None:
        try:
            box["v"] = fn()
        except Exception as exc:  # surfaced as None
            box["e"] = exc

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(max(0.1, timeout))
    if t.is_alive() or "e" in box:
        return None
    return box.get("v")


# --------------------------------------------------------------------------- #
# lookup
# --------------------------------------------------------------------------- #
@dataclass
class AIFact:
    post: str
    name: str
    since: Optional[str]
    source_url: str
    second_source: str
    verified_on: str
    from_cache: bool = False


@dataclass
class Lookup:
    """One run's lookup service. Call it as ``lookup(post)`` -> AIFact | None. Never raises."""
    search: Callable[[str], List[Dict[str, Any]]] = default_search
    fetch: Callable[[str], str] = default_fetch
    llm: Callable[[str], Optional[str]] = default_llm
    ready: Callable[[], Tuple[bool, str]] = default_ready
    cache_path: Optional[Path] = None
    today: Optional[date] = None
    max_lookups: int = 8
    max_queries: int = 16
    budget_s: float = 90.0
    llm_timeout: float = LLM_TIMEOUT
    stats: Dict[str, Any] = field(default_factory=lambda: {
        "lookups": 0, "accepted": 0, "rejected": 0, "cache_hits": 0, "serper_calls": 0,
        "errors": 0, "skipped": 0, "off_reason": ""})

    def __post_init__(self) -> None:
        try:
            self.max_lookups = int(os.getenv("ALP_STATIC_GK_AI_MAX_LOOKUPS", "") or self.max_lookups)
            self.budget_s = float(os.getenv("ALP_STATIC_GK_AI_BUDGET_S", "") or self.budget_s)
        except ValueError:
            pass
        self.max_lookups = min(self.max_lookups, 8)
        self.max_queries = min(self.max_queries, 2 * self.max_lookups)
        self.today = self.today or datetime.now(timezone.utc).date()
        self._t0: Optional[float] = None
        self._cache: Optional[Dict[str, Any]] = None
        self._memo: Dict[str, Optional[AIFact]] = {}
        self._ready: Optional[Tuple[bool, str]] = None

    # -- budget ------------------------------------------------------------ #
    def _time_left(self) -> float:
        if self._t0 is None:
            self._t0 = time.monotonic()
        return self.budget_s - (time.monotonic() - self._t0)

    def _query(self, q: str) -> List[Dict[str, Any]]:
        if self.stats["serper_calls"] >= self.max_queries or self._time_left() <= 0:
            return []
        self.stats["serper_calls"] += 1
        res = self.search(q)
        return [r for r in (res or []) if isinstance(r, dict)]

    def _cache_doc(self) -> Dict[str, Any]:
        if self._cache is None:
            self._cache = load_cache(self.cache_path)
        return self._cache

    # -- public ------------------------------------------------------------ #
    def __call__(self, post: str) -> Optional[AIFact]:
        try:
            return self._lookup(post)
        except Exception as exc:  # FAIL-OPEN
            self.stats["errors"] += 1
            logger.info("[static-gk-ai] lookup error for %r: %s", post, type(exc).__name__)
            return None

    def _lookup(self, post: str) -> Optional[AIFact]:
        post = re.sub(r"\s+", " ", str(post or "")).strip(" -–:,.")
        key = post_key(post)
        if not key or len(key) < 4:
            return None
        if key in self._memo:
            return self._memo[key]
        rec = self._cache_doc().get("records", {}).get(key)
        if isinstance(rec, dict) and cache_fresh(rec, self.today):
            self.stats["cache_hits"] += 1
            fact = AIFact(post=rec.get("post") or post, name=rec["name"], since=rec.get("since"),
                          source_url=rec.get("source_url", ""), second_source=rec.get("second_source", ""),
                          verified_on=rec["verified_on"], from_cache=True)
            self._memo[key] = fact
            return fact
        if self._ready is None:
            self._ready = self.ready()
            if not self._ready[0]:
                self.stats["off_reason"] = self._ready[1]
                logger.info("[static-gk-ai] off: %s", self._ready[1])
        if not self._ready[0]:
            return None
        if self.stats["lookups"] >= self.max_lookups or self._time_left() <= 0:
            self.stats["skipped"] += 1
            if not self.stats["off_reason"]:
                self.stats["off_reason"] = "lookup/time budget used"
            return None
        self.stats["lookups"] += 1
        fact = self._verify(post)
        self._memo[key] = fact
        if fact:
            self.stats["accepted"] += 1
            doc = self._cache_doc()
            doc.setdefault("records", {})[key] = {
                "post": fact.post, "name": fact.name, "since": fact.since, "source_url": fact.source_url,
                "second_source": fact.second_source, "verified_on": fact.verified_on,
                "verified_at": f"{fact.verified_on}T00:00:00+00:00", "method": "serper+official-page+llm"}
            doc["updated"] = fact.verified_on
            save_cache(doc, self.cache_path)
        else:
            self.stats["rejected"] += 1
        return fact

    def _verify(self, post: str) -> Optional[AIFact]:
        year = self.today.year
        place = bool(re.search(r"\bindia\b|\bof\s+[A-Z]", post, re.I))
        q1 = f"current {post} {year}" if place else f"current {post} of India {year}"
        q2 = f"current {post} {year} site:gov.in OR site:nic.in OR site:pib.gov.in"
        r1 = self._query(q1)
        r2 = self._query(q2)
        results = r2 + r1  # official-restricted first
        officials = [r for r in results if is_official(str(r.get("link") or ""))]
        if not officials:
            logger.info("[static-gk-ai] %r: no official result", post)
            return None
        off = officials[0]
        url = str(off["link"])
        if self._time_left() <= 0:
            return None
        text = _call_with_timeout(lambda: self.fetch(url), min(FETCH_TIMEOUT * 2 + 1, max(1.0, self._time_left())))
        if not text or len(text) < 100:
            logger.info("[static-gk-ai] %r: official page unreadable", post)
            return None
        snippet = self._focus(text, post)
        raw = _call_with_timeout(lambda: self.llm(PROMPT.format(post=post, url=url, text=snippet)),
                                 min(self.llm_timeout, max(1.0, self._time_left())))
        data = self._parse(raw)
        if not data:
            return None
        name = str(data.get("name") or "").strip()
        conf = str(data.get("confidence") or "").strip().lower()
        if not name or name.lower() in ("unknown", "null", "none", "n/a"):
            return None
        try:
            high = conf == "high" or float(conf) >= 0.9
        except ValueError:
            high = False
        if not high:
            logger.info("[static-gk-ai] %r: LLM confidence %r — rejected", post, conf)
            return None
        # (a) literally on the official page
        if not name_in_text(name, text):
            logger.info("[static-gk-ai] %r: %r not on the official page — rejected", post, name)
            return None
        # (b) independent second source (different site), recent if dated
        off_site = _site(host_of(url))
        second = ""
        for r in results:
            link = str(r.get("link") or "")
            if not link or _site(host_of(link)) == off_site:
                continue
            age = result_age_days(str(r.get("date") or ""), self.today)
            if age is not None and age > SECOND_SOURCE_MAX_AGE_DAYS:
                continue
            blob = f"{r.get('title', '')} {r.get('snippet', '')}"
            if name_in_text(name, blob):
                second = link
                break
        if not second:
            logger.info("[static-gk-ai] %r: no independent second source for %r — rejected", post, name)
            return None
        since = data.get("since")
        since = since if isinstance(since, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", since) else None
        logger.info("[static-gk-ai] %r -> %r (page %s, second %s)", post, name, url, second)
        return AIFact(post=post, name=name, since=since, source_url=url, second_source=second,
                      verified_on=self.today.isoformat())

    @staticmethod
    def _focus(text: str, post: str) -> str:
        words = [w for w in re.findall(r"[A-Za-z]{4,}", post) if w.lower() not in {"india", "union", "current"}]
        idx = [i for i in (text.lower().find(w.lower()) for w in words) if i >= 0]
        i = min(idx) if idx else 0
        return text[max(0, i - 2500): i + 4500]

    @staticmethod
    def _parse(raw: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(raw, str):
            return None
        m = re.search(r"\{.*\}", raw, re.S)
        if not m:
            return None
        try:
            data = json.loads(m.group(0))
        except ValueError:
            return None
        return data if isinstance(data, dict) else None


# --------------------------------------------------------------------------- #
# post extraction from a Static GK line
# --------------------------------------------------------------------------- #
_ROLE_CORE = (r"(?:Chief\s+Minister|Deputy\s+Chief\s+Minister|Minister(?:\s+of\s+State)?|Governor|Lieutenant\s+Governor|"
              r"Chair(?:man|person|woman)?|CMD|Managing\s+Director|MD|CEO|Chief\s+Executive(?:\s+Officer)?|"
              r"Director[\s-]General|DG|Director|President|Secretary(?:[\s-]General)?|Commissioner|Chief|Head|"
              r"Speaker|Mantri|Mission\s+Director)")
_LEFT = r"(?:(?:Union|Cabinet|Indian|India's|[A-Z][A-Za-z&'’.\-]*|of|and|for|&)\s+){0,4}"
_RIGHT = r"(?:\s+(?:of|for)\s+(?:the\s+)?(?:[A-Z][A-Za-z&'’.\-]*|and|&|of)(?:\s+(?:[A-Z][A-Za-z&'’.\-]*|and|&|of)){0,5})?"
_POST_RE = re.compile(_LEFT + _ROLE_CORE + r"\b" + _RIGHT)


def post_spans(line: str) -> List[Tuple[int, int]]:
    """Character spans of post phrases in a line (used to tell place words from person names)."""
    return [m.span() for m in _POST_RE.finditer(str(line or "")) if re.search(r"\s", m.group(0).strip())]


def extract_post(line: str, person: str) -> str:
    """The officeholder post a line attributes to *person* ('Defence Minister – X' -> 'Defence Minister')."""
    text = str(line or "").replace(person or "\x00", " | ")
    best = ""
    for m in _POST_RE.finditer(text):
        s = m.group(0).strip(" -–:,.|")
        s = re.sub(r"^(?:Current|Present|The|Incumbent|Is|Now)\s+", "", s, flags=re.I)
        s = re.sub(r"\s+(?:of|for|and|&)$", "", s)
        if len(s) > len(best):
            best = s
    best = re.sub(r"\s+", " ", best).strip()
    if len(best) < 4 or len(best) > 90:
        return ""
    # A bare role word is too vague to search ("Chairman", "Head").
    if not re.search(r"\s", best) and best.lower() not in ("cmd",):
        return ""
    return best
