# -*- coding: utf-8 -*-
"""
DISCOVERY APIs — Serper.dev, GNews.io v4, NewsData.io, Jina Reader
==================================================================
Standalone, env-gated helpers for primary-source discovery, news top-up,
corroboration and article text.

Keys (all optional — a missing key means the helper is OFF and returns empty):
  SERPER_API_KEY    google.serper.dev search/news (2,500 free credits, one-time)
  GNEWS_API_KEY     gnews.io v4 (free: 100 requests/day, 10 articles/request)
  NEWSDATA_API_KEY  newsdata.io (free: 200 credits/day, 10 articles/credit)
  JINA_API_KEY      r.jina.ai reader (paid balance; keyless reader is the fallback)

Design rules:
  - No key => graceful empty result (never raises for missing config).
  - Each service has a per-process call budget (ALP_<SERVICE>_MAX_CALLS).
  - 401/402/403 => the key is OFF for the rest of the run (no retries, no noise).
  - 429 => the service is OFF for the rest of the run (free quotas are daily).
  - Any other failure only logs (masked) and returns empty.
  - Never invents URLs; returns exactly what the APIs return.
  - Secret values never reach logs: error bodies are masked.
"""
from __future__ import annotations

import logging
import os
import re
import threading
from typing import Any, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

_TIMEOUT = int(os.getenv("ALP_DISCOVERY_TIMEOUT", "15"))


def _mask(text: str) -> str:
    """Mask every configured secret value that might be echoed in an error body/URL."""
    text = str(text or "")
    for name, value in os.environ.items():
        if value and len(value) >= 6 and (name.endswith(("_KEY", "_TOKEN")) or name in _SERVICE_ENV.values()):
            text = text.replace(value, "***")
    return text


class _Service:
    """Run-scoped guard for one keyed API: key lookup, call budget, off-switch."""

    def __init__(self, name: str, env: str, default_budget: int):
        self.name = name
        self.env = env
        self.default_budget = default_budget
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        self.calls = 0
        self.off_reason = ""

    @property
    def key(self) -> str:
        return os.environ.get(self.env, "").strip()

    @property
    def budget(self) -> int:
        try:
            return int(os.getenv(f"ALP_{self.name.upper()}_MAX_CALLS", "") or self.default_budget)
        except ValueError:
            return self.default_budget

    def enabled(self) -> bool:
        return bool(self.key) and not self.off_reason

    def take(self) -> bool:
        """Reserve one call from the budget (False when off / spent)."""
        with self._lock:
            if not self.enabled():
                return False
            if self.calls >= self.budget:
                if not self.off_reason:
                    self.off_reason = f"per-run budget of {self.budget} calls used"
                    logger.info("[discovery] %s: %s — off for the rest of the run", self.name, self.off_reason)
                return False
            self.calls += 1
            return True

    def fail(self, status: int, body: str = "") -> None:
        """Classify an HTTP failure; 401/402/403/429 turn the service off for the run."""
        if status in (401, 402, 403):
            reason = {401: "invalid key (401)", 402: "no balance / payment required (402)",
                      403: "forbidden (403)"}[status]
        elif status == 429:
            reason = "rate limit / daily quota reached (429)"
        else:
            logger.warning("[discovery] %s HTTP %s: %s", self.name, status, _mask(body)[:160])
            return
        with self._lock:
            if not self.off_reason:
                self.off_reason = reason
                logger.warning("[discovery] %s %s — off for the rest of the run", self.name, reason)

    def status(self) -> Dict[str, Any]:
        return {"configured": bool(self.key), "enabled": self.enabled(), "calls": self.calls,
                "budget": self.budget, "off_reason": self.off_reason}


SERPER = _Service("serper", "SERPER_API_KEY", 25)
GNEWS = _Service("gnews", "GNEWS_API_KEY", 4)
NEWSDATA = _Service("newsdata", "NEWSDATA_API_KEY", 3)
JINA = _Service("jina", "JINA_API_KEY", 20)
_SERVICES = (SERPER, GNEWS, NEWSDATA, JINA)
_SERVICE_ENV = {s.name: s.env for s in _SERVICES}


def reset_services() -> None:
    """Tests / new run: forget budgets and off-switches."""
    for service in _SERVICES:
        service.reset()
    _KEYLESS["calls"] = 0


def services_status() -> Dict[str, Dict[str, Any]]:
    return {s.name: s.status() for s in _SERVICES}


def _get(service: _Service, url: str, *, params=None, headers=None, json_body=None,
         method: str = "GET", timeout: Optional[float] = None) -> Optional[requests.Response]:
    """One guarded request. Returns the 200 response or None (already logged)."""
    if not service.take():
        return None
    try:
        if method == "POST":
            r = requests.post(url, headers=headers, json=json_body, timeout=timeout or _TIMEOUT)
        else:
            r = requests.get(url, params=params, headers=headers, timeout=timeout or _TIMEOUT)
    except requests.RequestException as exc:
        logger.warning("[discovery] %s request failed: %s", service.name, type(exc).__name__)
        return None
    if r.status_code != 200:
        service.fail(r.status_code, getattr(r, "text", "") or "")
        return None
    return r


# --------------------------------------------------------------------------- #
# Serper (Google search / news)
# --------------------------------------------------------------------------- #
def serper_search(query: str, num: int = 5, gl: str = "in", kind: str = "search") -> List[Dict[str, Any]]:
    """Google Search (kind="search") or Google News (kind="news") via Serper.dev.

    Returns [{title, link, snippet, date?, source?}, ...]; [] when off or failing."""
    if not query or not SERPER.enabled():
        return []
    kind = "news" if kind == "news" else "search"
    r = _get(SERPER, f"https://google.serper.dev/{kind}", method="POST",
             headers={"X-API-KEY": SERPER.key, "Content-Type": "application/json"},
             json_body={"q": query, "gl": gl, "num": min(max(num, 1), 10)})
    if r is None:
        return []
    try:
        data = r.json()
    except ValueError:
        return []
    return (data.get("news") if kind == "news" else data.get("organic")) or []


def fetch_gnews_api(query: str, lang: str = "en", country: str = "in",
                    max_articles: int = 10) -> List[Dict[str, Any]]:
    """GNews.io v4 search. Returns [{title, description, url, source{name}, publishedAt, image}, ...]."""
    return gnews_articles(endpoint="search", query=query, lang=lang, country=country,
                          max_articles=max_articles)


def gnews_articles(endpoint: str = "top-headlines", query: str = "", category: str = "",
                   lang: str = "en", country: str = "in", max_articles: int = 10,
                   date_from: str = "", date_to: str = "") -> List[Dict[str, Any]]:
    """GNews v4 top-headlines or search (country=in, lang=en by default)."""
    if not GNEWS.enabled():
        return []
    endpoint = "search" if endpoint == "search" else "top-headlines"
    params: Dict[str, Any] = {"lang": lang, "country": country, "max": min(max_articles, 10),
                              "apikey": GNEWS.key}
    if query:
        params["q"] = query
    if category and endpoint == "top-headlines":
        params["category"] = category
    if date_from:
        params["from"] = date_from
    if date_to:
        params["to"] = date_to
    r = _get(GNEWS, f"https://gnews.io/api/v4/{endpoint}", params=params)
    if r is None:
        return []
    try:
        return r.json().get("articles", []) or []
    except ValueError:
        return []


def newsdata_latest(query: str = "", category: str = "", language: str = "en",
                    country: str = "in") -> List[Dict[str, Any]]:
    """NewsData.io /latest (1 credit, up to 10 articles on the free plan)."""
    if not NEWSDATA.enabled():
        return []
    params: Dict[str, Any] = {"apikey": NEWSDATA.key, "country": country, "language": language}
    if query:
        params["q"] = query
    if category:
        params["category"] = category
    r = _get(NEWSDATA, "https://newsdata.io/api/1/latest", params=params)
    if r is None:
        return []
    try:
        data = r.json()
    except ValueError:
        return []
    if str(data.get("status", "success")).lower() != "success":
        logger.warning("[discovery] newsdata error: %s", _mask(str(data.get("results") or data))[:160])
        return []
    return data.get("results", []) or []


# --------------------------------------------------------------------------- #
# Jina Reader
# --------------------------------------------------------------------------- #
_MD_IMAGE_RE = re.compile(r"!\[[^\]]*\]\((https?://[^)\s]+\.(?:jpe?g|png|webp)(?:\?[^)\s]*)?)\)", re.I)
_BAD_IMAGE_RE = re.compile(r"(?:logo|icon|sprite|avatar|placeholder|banner-ad|pixel|1x1)", re.I)


_KEYLESS = {"calls": 0}
_KEYLESS_LOCK = threading.Lock()


def _take_keyless() -> bool:
    """Bounded use of the free keyless reader (ALP_JINA_KEYLESS=0 turns it off)."""
    if os.getenv("ALP_JINA_KEYLESS", "1") != "1":
        return False
    try:
        budget = int(os.getenv("ALP_JINA_KEYLESS_MAX_CALLS", "40") or 40)
    except ValueError:
        budget = 40
    with _KEYLESS_LOCK:
        if _KEYLESS["calls"] >= budget:
            return False
        _KEYLESS["calls"] += 1
        return True


_MD_LINK_RE = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")


def jina_article_text(text: str) -> str:
    """Plain article text from a Jina Reader reply (drops the header and markdown)."""
    body = text.split("Markdown Content:", 1)[-1] if text else ""
    body = _MD_LINK_RE.sub(lambda m: m.group(1) if not m.group(0).startswith("!") else "", body)
    lines = [ln.strip(" #>*-_|\t") for ln in body.splitlines()]
    paragraphs = [ln for ln in lines if len(ln) > 40]
    return " ".join(" ".join(paragraphs).split())


def jina_read(url: str, timeout: float = 30) -> Tuple[str, str]:
    """(text, first photo url) for an article via r.jina.ai.

    Uses JINA_API_KEY while it works; a 401/402/403 turns the key off for the run
    (no balance → HTTP 402 on 2026-11-03) and the free keyless reader is used
    instead (ALP_JINA_KEYLESS=0 disables that too). Never raises."""
    if not url or not url.startswith(("http://", "https://")):
        return "", ""
    if os.getenv("ALP_DISABLE_NETWORK", "0") == "1":
        return "", ""
    headers = {"Accept": "text/plain", "User-Agent": "AgriLearningPoint/1.0"}
    use_key = JINA.enabled() and JINA.take()
    if use_key:
        headers["Authorization"] = f"Bearer {JINA.key}"
    elif not _take_keyless():
        return "", ""
    for attempt in range(2):
        try:
            r = requests.get(f"https://r.jina.ai/{url}", headers=headers, timeout=timeout)
        except requests.RequestException as exc:
            logger.debug("[discovery] jina fetch failed: %s", type(exc).__name__)
            return "", ""
        if r.status_code == 200 and len(r.text or "") > 300:
            text = r.text
            image = ""
            for match in _MD_IMAGE_RE.finditer(text[:20000]):
                if not _BAD_IMAGE_RE.search(match.group(1)):
                    image = match.group(1)
                    break
            return text, image
        if "Authorization" in headers and r.status_code in (401, 402, 403):
            JINA.fail(r.status_code, getattr(r, "text", "") or "")
            headers.pop("Authorization", None)
            if not _take_keyless():
                return "", ""
            continue  # keyless reader for this and later calls
        if r.status_code == 429 and "Authorization" not in headers:
            logger.debug("[discovery] jina keyless reader rate-limited")
        return "", ""
    return "", ""


# --------------------------------------------------------------------------- #
# Official mirrors + corroboration (Serper)
# --------------------------------------------------------------------------- #
# Official/primary domains used for mirror discovery (tier-2 -> primary upgrade)
OFFICIAL_HOSTS = (
    "pib.gov.in", "agricoop.nic.in", "icar.org.in", "rbi.org.in", "nabard.org",
    "sebi.gov.in", "mospi.gov.in", "niti.gov.in", "mea.gov.in", "mausam.imd.gov.in",
    "isro.gov.in", "drdo.gov.in", "india.gov.in", "pmindia.gov.in", "mof.gov.in",
    "fssai.gov.in", "apeda.gov.in", "nhb.gov.in", "dahd.gov.in", "fao.org",
    "worldbank.org", "imf.org", "wto.org", "who.int",
)
_OFFICIAL_SUFFIXES = (".gov.in", ".nic.in", ".res.in") + OFFICIAL_HOSTS


def _title_words(title: str) -> List[str]:
    norm = re.sub(r"[^a-z0-9 ]", " ", (title or "").lower())
    return [w for w in norm.split() if len(w) > 3][:10]


def find_official_mirror(title: str, extra_hosts: tuple = ()) -> str | None:
    """Serper site-restricted search for the official page of a news title.
    Returns an official-domain URL whose page title closely matches, else None.
    Never invents URLs — only returns links Google actually indexed."""
    if not title or not SERPER.enabled():
        return None
    words = _title_words(title)[:8]
    if len(words) < 3:
        return None
    phrase = " ".join(words)
    hosts = tuple(dict.fromkeys(OFFICIAL_HOSTS + tuple(extra_hosts)))
    # one combined query: site:a OR site:b ... "key phrase"
    site_q = " OR ".join(f"site:{h}" for h in hosts[:12])
    for res in serper_search(f"({site_q}) {phrase}", num=6):
        link = res.get("link", "")
        rtitle = re.sub(r"[^a-z0-9 ]", "", (res.get("title") or "").lower())
        overlap = sum(1 for w in words if w in rtitle)
        if overlap >= max(3, len(words) // 2) and any(h in link for h in hosts):
            logger.info(f"[discovery] official mirror: {link[:90]}")
            return link
    return None


def _host(url: str) -> str:
    m = re.match(r"^https?://([^/]+)", url or "")
    return (m.group(1).lower().removeprefix("www.") if m else "")


def corroborate(title: str, own_link: str = "") -> Dict[str, Any]:
    """Look for independent reports of a headline on Google News (Serper).

    Returns {"sources": [{"host", "link", "title"}], "official": bool}; empty when
    Serper is off/spent. A source counts when its title shares most key words
    with the headline and it is on a different host than the article itself."""
    empty: Dict[str, Any] = {"sources": [], "official": False}
    words = _title_words(title)
    if len(words) < 3 or not SERPER.enabled():
        return empty
    own = _host(own_link)
    results = serper_search(" ".join(words[:8]), num=8, kind="news")
    seen, sources, official = set(), [], False
    need = max(3, int(len(words) * 0.5))
    for res in results:
        link = str(res.get("link") or "")
        host = _host(link)
        if not host or host == own or host in seen:
            continue
        rtitle = " ".join(_title_words(str(res.get("title") or "")))
        if sum(1 for w in words if w in rtitle) < need:
            continue
        seen.add(host)
        sources.append({"host": host, "link": link, "title": str(res.get("title") or "")[:200]})
        if any(host == s or host.endswith(s) or host.endswith("." + s.lstrip(".")) for s in _OFFICIAL_SUFFIXES):
            official = True
    return {"sources": sources, "official": official}
