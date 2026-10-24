"""Canonical production collection stage (Task 01).

Single source-fetch path for daily jobs. Loads the canonical registry from
pipeline.source_registry, fetches RSS feeds with feedparser, normalizes and
validates every article at this boundary, and writes one edition JSON file.

Contract:
- Output path: data/raw/<job_id>.json   (job_id = ALP_JOB_ID or daily_<date>)
- Date policy : requested ALP_JOB_DATE is authoritative for naming; the
                collection uses the shared IST edition window (previous day
                for historical daily editions). Backfill never becomes "today".
- Failure    : zero usable articles after a full run -> exit 2 (loud fail).
               A single failed feed does NOT discard other feeds' results.
- No live network access happens at import time.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import html
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    import feedparser  # declared in requirements.txt
    import requests
except ImportError as exc:  # pragma: no cover - environment issue
    raise SystemExit(
        "feedparser is required for source fetching. "
        "Install project dependencies (pip install -r requirements.txt). "
        f"Original error: {exc}"
    ) from exc

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.source_registry import SourceSpec, SourceConfigError, load_sources

RAW_DIR = ROOT / "data" / "raw"


# --------------------------------------------------------------------------
# Job context (date/backfill correctness)
# --------------------------------------------------------------------------

# Regex to detect raw document filenames (e.g. 459-1.pdf - CPCB) that must never become news headlines
RAW_FILE_RE = re.compile(
    r"(?:\b[\w\-_.]+\.(?:pdf|docx?|xlsx?|csv|pptx)\b)|(?:^\s*[\w\-_.]+\.(?:pdf|docx?|xlsx?)\b)",
    re.IGNORECASE,
)


def job_context() -> Tuple[str, str, datetime]:
    """Return (job_id, job_date_iso, window_end_utc).

    ALP_JOB_DATE is authoritative. Never substitutes wall-clock today when an
    explicit date was requested. Window boundaries come from pipeline.windows
    so all collection paths share one edition policy.
    """
    now = datetime.now(timezone.utc)
    date_env = os.environ.get("ALP_JOB_DATE", "").strip()
    if date_env:
        try:
            base = datetime.strptime(date_env, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            print(f"[01_source_fetch] invalid ALP_JOB_DATE={date_env!r}; "
                  f"expected YYYY-MM-DD", file=sys.stderr)
            raise SystemExit(2)
    else:
        base = now
    job_date = base.strftime("%Y-%m-%d")
    job_id = os.environ.get("ALP_JOB_ID", "").strip() or f"daily_{job_date}"
    from pipeline.windows import collect_window
    _, window_end = collect_window(os.getenv("ALP_JOB_TYPE", "daily"), job_date)
    if os.getenv("ALP_WINDOW_END"):
        window_end = datetime.fromisoformat(os.environ["ALP_WINDOW_END"])
    window_end = window_end.astimezone(timezone.utc)
    return job_id, job_date, window_end


def _parse_entry_time(entry: Any) -> datetime | None:
    """Timezone-aware publication datetime from a feedparser entry, or None."""
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        t = getattr(entry, key, None)
        if t:
            try:
                return datetime.fromtimestamp(calendar_time_to_epoch(t), tz=timezone.utc)
            except Exception:
                continue
    # Robust fallback: parse string representations if struct_time is unavailable
    for key in ("published", "updated", "pubDate", "created", "dc_date"):
        val = getattr(entry, key, None)
        if val and isinstance(val, str):
            try:
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(val)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except Exception:
                pass
            try:
                dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except Exception:
                pass
    return None


def calendar_time_to_epoch(t) -> float:
    import calendar
    return calendar.timegm(t)


def content_hash(title: str, link: str) -> str:
    """Stable dedup key: normalized title + normalized link."""
    norm_title = " ".join((title or "").lower().split())
    norm_link = (link or "").strip().lower()
    return hashlib.sha256(f"{norm_title}|{norm_link}".encode("utf-8")).hexdigest()[:16]


QUALITY_PUBLISHERS = {
    "thehindu": "The Hindu", "indianexpress": "Indian Express", "ndtv": "NDTV",
    "timesofindia": "TOI", "hindustantimes": "Hindustan Times", "thewire": "The Wire",
    "moneycontrol": "Moneycontrol", "deccanherald": "Deccan Herald", "theprint": "The Print",
    "scroll.in": "Scroll", "bbc": "BBC", "reuters": "Reuters", "bloomberg": "Bloomberg",
    "forbes": "Forbes", "financialexpress": "Financial Express", "cnbctv18": "CNBC TV18",
    "pib": "PIB", "ani": "ANI", "pti": "PTI", "ddnews": "DD News",
    "news18": "News18", "indiatoday": "India Today", "thequint": "The Quint",
    "business-standard": "Business Standard", "livemint": "Mint",
    "economictimes": "Economic Times", "businessline": "BusinessLine",
    "icar": "ICAR", "iari": "IARI", "rbi": "RBI", "nabard": "NABARD", "niti": "NITI Aayog",
    "sebi": "SEBI", "pfrda": "PFRDA", "irdai": "IRDAI", "npci": "NPCI",
    "isro": "ISRO", "drdo": "DRDO", "fao": "FAO", "who": "WHO",
    "worldbank": "World Bank", "imf": "IMF", "wto": "WTO",
}


def clean_url(url: str) -> str:
    """Normalize and unwrap Google News redirect links and strip tracking tokens."""
    url = (url or "").strip()
    if not url:
        return ""
    if url.startswith("/"):
        url = "https://news.google.com" + url
    if "news.google.com" in url:
        m = re.search(r"url=([^&\s]+)", url)
        if m:
            try:
                from urllib.parse import unquote
                url = unquote(m.group(1))
            except Exception:
                pass
    if "news.google.com" in url and len(url) > 120:
        m = re.search(r"CBM[ij][a-zA-Z0-9_-]+", url)
        if m:
            cid = m.group(0)
            url = "https://news.google.com/articles/" + cid
    return url[:300]


def resolve_publisher(url: str, default_name: str) -> str:
    """Extract clean publication brand from target domain."""
    if not url:
        return default_name
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower().replace("www.", "").replace("m.", "")
        for key, name in QUALITY_PUBLISHERS.items():
            if key in domain:
                return name
    except Exception:
        pass
    return default_name


def sanitize_feed_text(text: str) -> str:
    """Strip raw HTML tags, unescape HTML entities, and collapse whitespace."""
    if not text:
        return ""
    cleaned = re.sub(r"<[^>]+>", " ", text)
    cleaned = html.unescape(cleaned)
    return " ".join(cleaned.split()).strip()


def clean_and_validate_headline(raw_title: str, source_name: str = "") -> Tuple[str, bool]:
    """Clean, sanitize, and validate headline against junk/untitled/truncated patterns.
    
    Returns (cleaned_title, is_valid).
    """
    title = sanitize_feed_text(raw_title)
    if not title:
        return "", False

    # Strip leading dashes, bullets, spaces, arrows
    title = re.sub(r"^[-–—•:\|\s\>]+", "", title).strip()

    # Strip redundant trailing publisher repetition (e.g. 'Headline - Source Name')
    if source_name:
        s_clean = re.sub(r"[^\w\s]", "", source_name).lower().strip()
        parts = title.rsplit(" - ", 1)
        if len(parts) == 2:
            suffix_clean = re.sub(r"[^\w\s]", "", parts[1]).lower().strip()
            if suffix_clean == s_clean or (s_clean and s_clean in suffix_clean):
                title = parts[0].strip()

    # Reject placeholder "Untitled"
    if re.search(r"\buntitled\b", title, re.IGNORECASE):
        return title, False

    # Reject raw files (.pdf, .docx, etc.)
    if RAW_FILE_RE.search(title):
        return title, False

    # Reject bare ministry / department / organisation names without an event
    bare_org_patterns = [
        r"^(?:Department|Ministry)\s+of\s+[A-Za-z\s,&-]+$",
        r"^Sports Authority of India$",
        r"^Election Commission of India$",
        r"^Indian Council of Agricultural Research$",
        r"^ICAR-[A-Za-z\s,&-]+$",
    ]
    for pat in bare_org_patterns:
        if re.match(pat, title.strip(), re.IGNORECASE):
            return title, False

    # Length and word count checks
    words = title.split()
    if len(title) < 18 or len(words) < 4:
        return title, False

    # Check for truncated leading characters (e.g. 'aiwan' -> 'Taiwan', 'ranscript' -> 'Transcript')
    first_char = title[0]
    if first_char.isalpha() and first_char.islower() and not title.startswith(("e-", "i-", "m-")):
        if title.startswith("aiwan "):
            title = "T" + title
        elif title.startswith("ranscript "):
            title = "T" + title
        else:
            return title, False

    return title, True


def extract_article_text(url: str, timeout: int = 5) -> str:
    """Safely extract plain article text from webpage URL without hanging."""
    if not url or not url.startswith(("http://", "https://")):
        return ""
    if os.getenv("ALP_DISABLE_NETWORK", "0") == "1" or os.getenv("DRY_RUN", "0") == "1":
        return ""
    try:
        from bs4 import BeautifulSoup
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        if resp.status_code != 200 or not resp.text:
            return ""
        soup = BeautifulSoup(resp.content[:300_000], "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "aside"]):
            tag.decompose()
        paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        meaningful = [
            p for p in paragraphs
            if len(p) > 30 and not any(w in p.lower() for w in ("copyright", "all rights reserved", "subscribe", "terms of use"))
        ]
        text = " ".join(meaningful)
        return " ".join(text.split())[:3000]
    except Exception:
        return ""


# --------------------------------------------------------------------------
# Fetch + normalize
# --------------------------------------------------------------------------

def fetch_spec(spec: SourceSpec, window_start: datetime, window_end: datetime,
               seen_hashes: set | None = None) -> Tuple[List[Dict[str, Any]], int, int, str | None]:
    """Fetch one feed. Returns (articles, total_entries, skipped_malformed, error).

    Errors are reported per feed; they never discard results from other feeds.
    """
    if seen_hashes is None:
        seen_hashes = set()
    collected: List[Dict[str, Any]] = []
    malformed = 0
    try:
        # ALP_FEED_TIMEOUT is canonical; REQUEST_TIMEOUT is the legacy alias
        # documented in older .env files.
        timeout = int(os.getenv("ALP_FEED_TIMEOUT") or os.getenv("REQUEST_TIMEOUT") or "20")
        response = requests.get(spec.rss_url, headers={"User-Agent": "alp-collector/1.0"},
                                timeout=timeout)
        response.raise_for_status()
        parsed = feedparser.parse(response.content)
    except Exception as exc:  # network/disk level failure
        return [], 0, 0, f"{type(exc).__name__}: {exc}"

    status = getattr(parsed, "status", None)
    if parsed.bozo and not parsed.entries:
        err = getattr(parsed, "bozo_exception", "unparseable feed")
        if status == 404:
            return [], 0, 0, f"HTTP 404 (feed moved/deleted): {spec.rss_url}"
        return [], 0, 0, f"feed parse error ({err})"

    entries = list(getattr(parsed, "entries", []) or [])
    for entry in entries:
        raw_title = getattr(entry, "title", "") or ""
        title, is_valid = clean_and_validate_headline(raw_title, spec.name)
        link = clean_url((getattr(entry, "link", "") or "").strip())
        if not is_valid or not link.lower().startswith(("http://", "https://")):
            malformed += 1
            continue  # validated at collection boundary; logged via counter
        published = _parse_entry_time(entry)
        if published is None:
            # Missing timestamps are NOT treated as current news.
            malformed += 1
            continue
        if not (window_start <= published <= window_end):
            continue  # outside the requested job window
        h = content_hash(title, link)
        if h in seen_hashes:
            continue
        seen_hashes.add(h)
        summary = sanitize_feed_text(getattr(entry, "summary", "") or "")
        # If summary is thin or identical to title, attempt substantive paragraph extraction
        if len(summary) < 120 or summary.lower() == title.lower():
            body_txt = extract_article_text(link, timeout=4)
            if len(body_txt) > len(summary):
                summary = body_txt
        source_name = resolve_publisher(link, spec.name)
        collected.append({
            "title": title,
            "link": link,
            "summary": summary[:2000],
            "published": published.isoformat(),
            "source_feed": spec.rss_url,
            "source_name": source_name,
            "source_id": spec.source_id,
            "source_tier": spec.tier,
            "publisher_url": spec.extra.get("url", spec.rss_url),
            **({"source_level": spec.extra["level"]} if "level" in spec.extra else {}),
            "official": spec.official,
            "category": spec.category,
            "language": spec.language,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "content_hash": h,
        })
    return collected, len(entries), malformed, None


def main() -> int:
    job_id, job_date, window_end = job_context()
    from pipeline.windows import collect_window
    window_start, _ = collect_window(os.getenv("ALP_JOB_TYPE", "daily"), job_date)
    if os.getenv("ALP_WINDOW_START"):
        window_start = datetime.fromisoformat(os.environ["ALP_WINDOW_START"])
    window_start = window_start.astimezone(timezone.utc)

    try:
        specs = load_sources()
    except SourceConfigError as exc:
        print(f"[01_source_fetch] FATAL source config error:\n{exc}", file=sys.stderr)
        return 2

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RAW_DIR / f"{job_id}.json"

    all_articles: List[Dict[str, Any]] = []
    seen_hashes: set = set()
    feed_failures: List[Dict[str, str]] = []
    ok_feeds = 0

    # Staggered harvesting into 4 controlled batches to prevent burst rate-limits
    def _source_batch_id(spec: SourceSpec) -> tuple[int, str]:
        cat = (spec.category or "").lower()
        if any(k in cat for k in ("agriculture", "govt_national", "core")):
            return 1, "Core Government & Agriculture"
        if any(k in cat for k in ("banking", "finance", "economy")):
            return 2, "Banking, Finance & Regulators"
        if any(k in cat for k in ("science", "defence", "international_org", "health")):
            return 3, "Science, Defence & Multilateral Orgs"
        return 4, "Discovery, Media & Broadcasters"

    batches: Dict[int, Tuple[str, List[SourceSpec]]] = {}
    for spec in specs:
        b_id, b_name = _source_batch_id(spec)
        if b_id not in batches:
            batches[b_id] = (b_name, [])
        batches[b_id][1].append(spec)

    print(f"[01_source_fetch] Staggered harvesting: {len(specs)} sources partitioned across {len(batches)} batches")
    import time
    for b_id in sorted(batches.keys()):
        b_name, b_specs = batches[b_id]
        print(f"[01_source_fetch] >>> Starting Batch {b_id}/{len(batches)}: {b_name} ({len(b_specs)} sources)")
        max_workers = min(6, max(1, len(b_specs)))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_spec = {
                executor.submit(fetch_spec, spec, window_start, window_end, None): spec
                for spec in b_specs
            }
            for future in concurrent.futures.as_completed(future_to_spec):
                spec = future_to_spec[future]
                try:
                    arts, total, malformed, error = future.result()
                except Exception as exc:
                    error = f"{type(exc).__name__}: {exc}"
                    arts, total, malformed = [], 0, 0
                if error:
                    feed_failures.append({"source_id": spec.source_id,
                                          "url": spec.rss_url, "error": error})
                    print(f"[01_source_fetch] WARN feed failed: {spec.name} -> {error}",
                          file=sys.stderr)
                    continue
                ok_feeds += 1
                for art in arts:
                    h = art.get("content_hash") or content_hash(art.get("title", ""), art.get("link", ""))
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        all_articles.append(art)
                print(f"[01_source_fetch] {spec.name}: {len(arts)} in-window "
                      f"(of {total} entries, {malformed} malformed skipped)")
        if b_id < len(batches):
            time.sleep(1.0)

    edition = {
        "schema_version": "1.0",
        "job_id": job_id,
        "job_date": job_date,
        "collected_window": {
            "start": window_start.isoformat(),
            "end": window_end.isoformat(),
        },
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "sources_enabled": len(specs),
        "sources_fetched_ok": ok_feeds,
        "sources_failed": len(feed_failures),
        "feed_failures": feed_failures,
        "article_count": len(all_articles),
        "articles": all_articles,
    }

    tmp_path = out_path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(edition, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    os.replace(tmp_path, out_path)  # atomic write

    if not all_articles:
        print(f"[01_source_fetch] FATAL: zero usable articles collected into "
              f"{out_path} ({len(feed_failures)} feed failures). Refusing to "
              f"produce an empty edition.", file=sys.stderr)
        return 2

    print(f"[01_source_fetch] wrote {out_path} "
          f"({len(all_articles)} articles, {ok_feeds}/{len(specs)} feeds ok)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
