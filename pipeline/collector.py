# -*- coding: utf-8 -*-
"""Production-oriented news collector for Agri Learning Point.

Responsibilities
-----------------
* Load the repository's six-level ``config.sources`` registry.
* Collect from declared RSS/Atom feeds first, then native RSS candidates,
  official listing-page links, and finally Google News site-search where configured.
* Normalize all articles to one schema that is compatible with both Agent 04
  (title/link/summary/published/source_feed) and pipeline.scoring
  (headline_en/source_url/raw_facts/source_level/source_tier).
* Apply a job-type/date window, preserve undated records with an explicit flag,
  deduplicate exact canonical URLs, track source health, and write atomically.
* Never claim that a Google News/discovery result is a verified primary source.

This module does NOT fact-check claims. Agent 04 must perform verification before
content selection or publication.

CLI:
    python -m pipeline.collector --job-type daily --date 2026-10-14
    python -m pipeline.collector --job-type daily --date 2026-10-14 --dry-run

Python API:
    items = collect_all(job_type="daily", job_date="2026-10-14")
    report = collect_with_report(job_type="daily", job_date="2026-10-14")
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import logging
import os
import random
import re
import sys
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time as dt_time, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Optional
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

# Support both `python -m pipeline.collector` and direct script execution from
# main.py (`python /repo/pipeline/collector.py`).
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from config.sources import (
        ALL_SOURCES,
        TIER_1_SOURCES,
        TIER_2_DISCOVERY,
        TIER_3_AGGREGATORS,
        LEVEL_0_CORE,
        PRIORITY_MAP,
        LEVEL_NAMES,
    )
except ImportError as exc:  # fail loudly; a collector with no source registry is unsafe
    raise RuntimeError(
        "Cannot import config.sources. Run this module from the repository root "
        "and ensure config/sources.py exports the production source registry."
    ) from exc

try:
    from config.feeds import VERIFIED_RSS, GOOGLE_NEWS_SITES, gnews_url
except Exception:  # feed extras are optional; source registry remains mandatory
    VERIFIED_RSS: list[tuple[str, str, str, str]] = []
    GOOGLE_NEWS_SITES: dict[str, str] = {}

    def gnews_url(domain: str) -> str:
        from urllib.parse import quote
        return (
            "https://news.google.com/rss/search?q="
            + quote(f"site:{domain} when:2d")
            + "&hl=en-IN&gl=IN&ceid=IN:en"
        )


RAW_DIR = REPO_ROOT / "data" / "raw"
LOG_DIR = REPO_ROOT / "logs"
STATE_DIR = REPO_ROOT / "state"
IST = ZoneInfo("Asia/Kolkata")
UTC = timezone.utc

LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("pipeline.collector")

USER_AGENT = os.getenv(
    "COLLECT_USER_AGENT",
    "AgriLearningPointNewsCollector/2.0 (+https://github.com/agrilearningpoint/daily-current-affairs)",
)
REQUEST_TIMEOUT = max(2, int(os.getenv("COLLECT_REQUEST_TIMEOUT", "8")))
MAX_RETRIES = max(0, int(os.getenv("COLLECT_RETRIES", "2")))
MAX_RESPONSE_BYTES = max(64_000, int(os.getenv("COLLECT_MAX_RESPONSE_BYTES", str(5 * 1024 * 1024))))
MAX_ENTRIES_PER_FEED = max(1, int(os.getenv("COLLECT_MAX_ENTRIES_PER_FEED", "50")))
MAX_HTML_LINKS_PER_SOURCE = max(1, int(os.getenv("COLLECT_MAX_HTML_LINKS_PER_SOURCE", "20")))
MAX_WORKERS = max(1, min(24, int(os.getenv("COLLECT_MAX_WORKERS", "8"))))
COLLECT_DEADLINE_S = max(15, int(os.getenv("COLLECT_DEADLINE_S", "300")))
MAX_ITEMS_DEFAULT = max(1, int(os.getenv("COLLECT_MAX_ITEMS", "140")))
MIN_ITEMS_DEFAULT = max(1, int(os.getenv("COLLECT_MIN_ITEMS", "10")))
KEEP_UNDATED = os.getenv("COLLECT_KEEP_UNDATED", "1").strip().lower() not in {"0", "false", "no"}
ENABLE_TIER5_FALLBACK = os.getenv("COLLECT_ENABLE_TIER5_FALLBACK", "0").strip().lower() in {"1", "true", "yes"}
ENFORCE_CORE_COVERAGE = os.getenv("COLLECT_ENFORCE_CORE_COVERAGE", "0").strip().lower() in {"1", "true", "yes"}
MIN_CORE_COVERAGE = min(1.0, max(0.0, float(os.getenv("COLLECT_MIN_CORE_COVERAGE", "0.15"))))

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "igshid", "mc_cid", "mc_eid", "ref", "src",
}
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
WHITESPACE = re.compile(r"\s+")

CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Agriculture": (
        "agriculture", "farmer", "farmers", "kisan", "crop", "msp", "icar", "iari",
        "horticulture", "apeda", "nhb", "fisheries", "dairy", "livestock", "monsoon",
        "soil", "seed", "irrigation", "agri", "food processing", "animal husbandry",
    ),
    "Banking & Finance": (
        "rbi", "bank", "nabard", "sebi", "upi", "npci", "loan", "credit", "repo",
        "monetary", "insurance", "irdai", "pfrda", "deposit", "nbfc", "currency",
    ),
    "Economy": (
        "gdp", "inflation", "budget", "economic", "mospi", "trade", "export", "import",
        "gst", "finance", "survey", "forex", "deficit", "growth", "industry", "fiscal",
    ),
    "Government Schemes": (
        "scheme", "yojana", "mission", "initiative", "cabinet", "policy", "mou", "launched",
        "approved", "gazette", "notification", "programme", "program", "guidelines",
    ),
    "International": (
        "united nations", "fao", "world bank", "imf", "wto", "who", "unesco", "unep",
        "undp", "ilo", "climate", "global", "international", "summit", "bilateral",
    ),
    "Science & Technology": (
        "scient", "research", "technology", "space", "satellite", "quantum", "vaccine",
        "medical", "health", "dst", "innovation", "startup", "digital", "isro", "drdo",
    ),
    "Environment": (
        "environment", "forest", "climate change", "pollution", "wildlife", "carbon",
        "renewable", "solar", "wind", "biodiversity", "moefcc", "cpcb", "emission",
    ),
    "Sports": ("sports", "cricket", "hockey", "tournament", "medal", "olympic", "federation"),
}

CATEGORY_ALIASES = {
    "agriculture_core": "Agriculture", "agriculture": "Agriculture", "agri": "Agriculture",
    "banking_finance": "Banking & Finance", "finance": "Banking & Finance",
    "economy_data": "Economy", "economy": "Economy", "govt_national": "National",
    "international": "International", "science": "Science & Technology",
    "environment": "Environment", "discovery": "National", "aggregator": "National",
    "health": "Science & Technology", "energy": "Environment", "education": "National",
    "defence": "National", "rural": "Agriculture", "cooperation": "Agriculture",
}


@dataclass(frozen=True)
class CollectorConfig:
    job_type: str = "daily"
    job_date: str = ""
    max_items: int = MAX_ITEMS_DEFAULT
    min_items: int = MIN_ITEMS_DEFAULT
    workers: int = MAX_WORKERS
    deadline_seconds: int = COLLECT_DEADLINE_S
    keep_undated: bool = KEEP_UNDATED
    include_tier5_fallback: bool = ENABLE_TIER5_FALLBACK


@dataclass
class SourceResult:
    source_name: str
    source_url: str
    source_level: int
    success: bool = False
    item_count: int = 0
    method: str = "none"
    attempts: int = 0
    error: str = ""
    duration_seconds: float = 0.0


@dataclass
class CollectionReport:
    job_type: str
    job_date: str
    started_at: str
    finished_at: str = ""
    duration_seconds: float = 0.0
    source_count: int = 0
    source_success_count: int = 0
    source_failure_count: int = 0
    raw_item_count: int = 0
    in_window_count: int = 0
    unique_item_count: int = 0
    core_coverage: dict[str, Any] = field(default_factory=dict)
    source_results: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------
def clean_text(value: Any, max_len: int = 5000) -> str:
    """Strip HTML/control chars and normalize Unicode without damaging Hindi text."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    text = html.unescape(str(value))
    text = BeautifulSoup(text, "html.parser").get_text(" ", strip=True)
    text = unicodedata.normalize("NFC", text)
    text = CONTROL_CHARS.sub("", text)
    text = WHITESPACE.sub(" ", text).strip()
    return text[:max_len].rstrip()


def normalize_url(url: str) -> str:
    """Canonicalize HTTP(S) URLs and remove known tracking parameters."""
    if not url:
        return ""
    try:
        p = urlsplit(url.strip())
        if p.scheme.lower() not in {"http", "https"} or not p.hostname:
            return ""
        host = p.hostname.lower().rstrip(".")
        if host.startswith("www."):
            host = host[4:]
        port = p.port
        netloc = host
        if port and not ((p.scheme.lower() == "http" and port == 80) or (p.scheme.lower() == "https" and port == 443)):
            netloc = f"{host}:{port}"
        query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if k.lower() not in TRACKING_PARAMS and not k.lower().startswith("utm_")]
        path = re.sub(r"/{2,}", "/", p.path or "/")
        if path != "/":
            path = path.rstrip("/")
        return urlunsplit((p.scheme.lower(), netloc, path, urlencode(query, doseq=True), ""))
    except (ValueError, TypeError):
        return ""


def url_host(url: str) -> str:
    try:
        return (urlsplit(url).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


def _hash(*parts: str) -> str:
    payload = "||".join(str(p or "") for p in parts)
    return hashlib.sha256(payload.encode("utf-8", errors="replace")).hexdigest()[:20]


def parse_dt(raw: Any) -> Optional[datetime]:
    """Parse a timestamp to timezone-aware IST; return None if absent/invalid."""
    if not raw:
        return None
    try:
        parsed = date_parser.parse(str(raw))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(IST)
    except (ValueError, OverflowError, TypeError, OSError):
        return None


def infer_category(text: str, source_category: str = "") -> str:
    alias = CATEGORY_ALIASES.get((source_category or "").strip().lower())
    if alias:
        return alias
    lower = f" {(text or '').lower()} "
    scores = {category: sum(1 for keyword in keywords if keyword in lower)
              for category, keywords in CATEGORY_KEYWORDS.items()}
    best = max(scores, key=scores.get) if scores else "National"
    return best if scores.get(best, 0) else "National"


def _is_gnews_url(url: str) -> bool:
    return url_host(url) == "news.google.com"


def _tier_name(level: int, discovery: bool = False) -> str:
    if discovery or level >= 4:
        return "tier2" if level == 4 or discovery else "tier3"
    return "tier1"


def _source_host_matches(source_url: str, article_url: str) -> bool:
    """True only for same host or a subdomain of the configured source host."""
    base = url_host(source_url)
    article = url_host(article_url)
    if not base or not article:
        return False
    return article == base or article.endswith("." + base)


def _source_registry() -> list[tuple[str, dict[str, Any]]]:
    """Flatten the configured levels while retaining group labels and stable IDs."""
    grouped: list[tuple[str, dict[str, Any]]] = []
    for group, sources in TIER_1_SOURCES.items():
        for src in sources:
            grouped.append((group, dict(src)))
    for src in TIER_2_DISCOVERY:
        grouped.append(("discovery", dict(src)))
    if ENABLE_TIER5_FALLBACK:
        for src in TIER_3_AGGREGATORS:
            grouped.append(("fallback", dict(src)))
    # Defensive dedupe by name + URL; do not collapse different feeds for one domain.
    out: list[tuple[str, dict[str, Any]]] = []
    seen: set[tuple[str, str]] = set()
    for group, src in grouped:
        key = (str(src.get("name", "")).strip().lower(), str(src.get("url", "")).strip().lower())
        if key not in seen:
            seen.add(key)
            out.append((group, src))
    return out


def select_sources(job_type: str) -> list[tuple[str, dict[str, Any]]]:
    """Select sources by configured frequency and authority level."""
    if job_type not in {"daily", "weekly", "monthly"}:
        raise ValueError(f"Unsupported job_type: {job_type!r}")
    selected = []
    for group, src in _source_registry():
        level = int(src.get("level", 5))
        frequency = str(src.get("frequency", "daily")).lower()
        if level == 0:
            selected.append((group, src))  # core sources are always attempted
        elif job_type == "daily":
            if frequency in {"daily", "on_demand"} or level == 4:
                selected.append((group, src))
        else:
            selected.append((group, src))
    selected.sort(key=lambda pair: (-int(pair[1].get("priority", 0)), int(pair[1].get("level", 5)), pair[1].get("name", "")))
    return selected


# ---------------------------------------------------------------------------
# Time windows
# ---------------------------------------------------------------------------
from pipeline.windows import collect_window


def in_window(item: dict[str, Any], start: datetime, end: datetime, keep_undated: bool = KEEP_UNDATED) -> bool:
    raw = item.get("pub_time_ist") or item.get("published") or item.get("published_at")
    if not raw:
        return keep_undated
    parsed = parse_dt(raw)
    if parsed is None:
        return keep_undated
    return start <= parsed <= end


# ---------------------------------------------------------------------------
# HTTP and feed adapters
# ---------------------------------------------------------------------------
def _fetch_text(url: str) -> tuple[int | None, str | None, str | None, int]:
    """Fetch bounded response body. Return (status, text, error, attempts)."""
    normalized = normalize_url(url)
    if not normalized:
        return None, None, "invalid_http_url", 0
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, text/html;q=0.9, */*;q=0.8",
        "Accept-Language": "en-IN,en;q=0.8,hi;q=0.6",
    }
    last_error = "request_failed"
    attempts = 0
    for attempt in range(MAX_RETRIES + 1):
        attempts += 1
        try:
            with requests.get(normalized, headers=headers, timeout=REQUEST_TIMEOUT, stream=True, allow_redirects=True) as response:
                status = response.status_code
                if status == 429 or status >= 500:
                    last_error = f"http_{status}"
                    retry_after = response.headers.get("Retry-After", "")
                    if attempt < MAX_RETRIES:
                        try:
                            wait = min(8.0, max(0.0, float(retry_after))) if retry_after else min(8.0, (2 ** attempt) + random.random())
                        except ValueError:
                            wait = min(8.0, (2 ** attempt) + random.random())
                        time.sleep(wait)
                        continue
                    return status, None, last_error, attempts
                if status < 200 or status >= 300:
                    return status, None, f"http_{status}", attempts
                chunks: list[bytes] = []
                total = 0
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > MAX_RESPONSE_BYTES:
                        return status, None, f"response_too_large>{MAX_RESPONSE_BYTES}", attempts
                    chunks.append(chunk)
                raw = b"".join(chunks)
                encoding = response.encoding or "utf-8"
                try:
                    body = raw.decode(encoding, errors="replace")
                except LookupError:
                    body = raw.decode("utf-8", errors="replace")
                if not body.strip():
                    return status, None, "empty_response", attempts
                return status, body, None, attempts
        except requests.RequestException as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < MAX_RETRIES:
                time.sleep(min(8.0, (2 ** attempt) + random.random()))
    return None, None, last_error, attempts


def _feed_candidates(source: dict[str, Any], base_url: str) -> list[tuple[str, str]]:
    """Return (feed_url, method) candidates in explicit-first order."""
    candidates: list[tuple[str, str]] = []
    declared = source.get("rss")
    if isinstance(declared, str) and declared.strip():
        candidates.append((declared.strip(), "declared_rss"))
    # Do not guess RSS URLs for a Google News query; it is already a feed URL.
    if not _is_gnews_url(base_url):
        base = base_url.rstrip("/")
        candidates.extend([
            (urljoin(base + "/", "rss.xml"), "native_rss_guess"),
            (urljoin(base + "/", "feed.xml"), "native_rss_guess"),
            (urljoin(base + "/", "feed"), "native_rss_guess"),
            (urljoin(base + "/", "rss"), "native_rss_guess"),
        ])
    fallback_rss = source.get("fallback_rss")
    if isinstance(fallback_rss, str) and fallback_rss.strip():
        candidates.append((fallback_rss.strip(), "configured_gnews_fallback" if _is_gnews_url(fallback_rss) else "configured_fallback_rss"))
    # Only use generated Google News queries for explicitly mapped domains or configured fallback policy.
    host = url_host(base_url)
    fallback_policy = source.get("fallback") or []
    if isinstance(fallback_policy, str):
        fallback_policy = [fallback_policy]
    if host and (host in GOOGLE_NEWS_SITES or "gnews_site_search" in fallback_policy):
        generated = gnews_url(host)
        if generated:
            candidates.append((generated, "gnews_discovery"))
    out, seen = [], set()
    for candidate, method in candidates:
        normalized = normalize_url(candidate)
        if normalized and normalized not in seen:
            seen.add(normalized)
            out.append((candidate, method))
    return out


def _extract_image(entry: Any) -> str:
    for key in ("media_thumbnail", "media_content"):
        values = entry.get(key) or []
        if isinstance(values, list):
            for value in values:
                candidate = value.get("url", "") if isinstance(value, dict) else ""
                if normalize_url(candidate):
                    return candidate
    for enclosure in entry.get("enclosures", []) or []:
        candidate = enclosure.get("href", "")
        mime = str(enclosure.get("type", "")).lower()
        if candidate and (mime.startswith("image/") or not mime):
            if normalize_url(candidate):
                return candidate
    return ""


def _parse_feed(source: dict[str, Any], feed_url: str, body: str, method: str, group: str) -> list[dict[str, Any]]:
    parsed = feedparser.parse(body)
    entries = getattr(parsed, "entries", []) or []
    out: list[dict[str, Any]] = []
    for entry in entries[:MAX_ENTRIES_PER_FEED]:
        title = clean_text(entry.get("title", ""), 500)
        link = normalize_url(entry.get("link", ""))
        if not title or not link:
            continue
        summary = clean_text(entry.get("summary", "") or entry.get("description", "") or entry.get("subtitle", ""), 2500)
        published = parse_dt(entry.get("published") or entry.get("updated") or entry.get("created"))
        out.append(make_item(
            title=title,
            link=link,
            source=source,
            feed_url=feed_url,
            method=method,
            group=group,
            published=published,
            summary=summary,
            image_url=_extract_image(entry),
            entry_id=clean_text(entry.get("id", ""), 500),
        ))
    if getattr(parsed, "bozo", 0) and not entries:
        logger.debug("Feed parser warning for %s: %s", feed_url, getattr(parsed, "bozo_exception", "unknown"))
    return out


def rss_items(source: dict[str, Any], url: str, tier: str = "tier1", role: Optional[str] = None) -> list[dict[str, Any]]:
    """Compatibility wrapper: fetch and parse a specific RSS/Atom URL."""
    method = role or ("gnews_discovery" if _is_gnews_url(url) else "declared_rss")
    status, body, error, _ = _fetch_text(url)
    if status is None or body is None or error:
        logger.debug("RSS fetch failed for %s: %s", url, error or status)
        return []
    group = "discovery" if _is_gnews_url(url) else "configured_feed"
    return _parse_feed(source, url, body, method, group)


def _extract_listing_items(source: dict[str, Any], page_url: str, body: str, group: str, limit: int) -> list[dict[str, Any]]:
    soup = BeautifulSoup(body, "lxml")
    base_host = url_host(page_url)
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for anchor in soup.select("a[href]"):
        title = clean_text(anchor.get_text(" ", strip=True), 500)
        if len(title) < 25:
            continue
        href = normalize_url(urljoin(page_url, anchor.get("href", "")))
        if not href or not _source_host_matches(page_url, href):
            continue
        path = urlsplit(href).path.lower()
        if path in {"", "/", "/home", "/home.aspx"}:
            continue
        # Reject common navigation/account/search links; do not rely on brittle href regexes.
        if any(part in path for part in ("/login", "/signin", "/register", "/search", "/contact", "/privacy", "/terms")):
            continue
        if href in seen:
            continue
        seen.add(href)
        out.append(make_item(
            title=title,
            link=href,
            source=source,
            feed_url=page_url,
            method="official_html_listing",
            group=group,
            published=None,
            summary=title,
            image_url="",
            entry_id="",
        ))
        if len(out) >= limit:
            break
    return out


def html_items(
    source: dict[str, Any],
    url: str,
    tier: str = "tier1",
    role: Optional[str] = None,
    link_pattern: Optional[str] = None,
    limit: int = MAX_HTML_LINKS_PER_SOURCE,
) -> list[dict[str, Any]]:
    """Compatibility wrapper: extract same-host article links from a listing page."""
    status, body, error, _ = _fetch_text(url)
    if status is None or body is None or error:
        logger.debug("HTML listing fetch failed for %s: %s", url, error or status)
        return []
    return _extract_listing_items(source, url, body, "official_html", limit)


def make_item(
    title: str,
    link: str,
    source: dict[str, Any],
    tier: str = "tier1",
    published: Optional[datetime] = None,
    summary: str = "",
    img: str = "",
    role: Optional[str] = None,
    *,
    feed_url: str = "",
    method: str = "unknown",
    group: str = "",
    image_url: str = "",
    entry_id: str = "",
) -> dict[str, Any]:
    """Create one normalized record with compatibility aliases for downstream agents."""
    title = clean_text(title, 500)
    summary = clean_text(summary, 2500)
    canonical_link = normalize_url(link)
    published = published.astimezone(IST) if published and published.tzinfo else (published.replace(tzinfo=UTC).astimezone(IST) if published else None)
    level_claimed = int(source.get("level", 0 if tier == "tier1" else 4))
    configured_source_url = str(source.get("url", ""))
    off_source_host = bool(configured_source_url and canonical_link and not _source_host_matches(configured_source_url, canonical_link))
    is_discovery = (
        method.startswith("gnews")
        or _is_gnews_url(feed_url)
        or _is_gnews_url(canonical_link)
        or level_claimed >= 4
        or off_source_host
    )
    # Never award a primary-source level to an item whose only observed route is
    # an aggregator or an off-domain link. Preserve the configured level separately.
    effective_level = max(4, level_claimed) if is_discovery and level_claimed < 4 else level_claimed
    effective_tier = _tier_name(effective_level, discovery=is_discovery)
    source_name = clean_text(source.get("name", "Unknown source"), 200) or "Unknown source"
    source_url = canonical_link
    pub_iso = published.isoformat() if published else None
    category = infer_category(title + " " + summary, str(source.get("category", "")))
    content_hash = _hash(title.casefold(), canonical_link)
    # Event ID is title/date based, not source based, so reports can correlate candidates.
    normalized_title = re.sub(r"[^\w]+", " ", title.casefold(), flags=re.UNICODE).strip()
    event_id = _hash(normalized_title, published.date().isoformat() if published else "undated")
    timestamp = datetime.now(IST).isoformat()
    needs_primary = bool(source.get("verification_required", level_claimed <= 3)) or is_discovery or not _source_host_matches(str(source.get("url", "")), canonical_link)
    item = {
        "event_id": event_id,
        "content_hash": content_hash,
        "headline_en": title,
        "title": title,                         # Agent 04 compatibility
        "source_url": source_url,
        "link": source_url,                     # Agent 04 compatibility
        "raw_facts": summary or title,
        "summary": summary or title,             # Agent 04 compatibility
        "pub_time_ist": pub_iso,
        "published": pub_iso,                    # Agent 04 compatibility
        "source_name": source_name,
        "source_feed": feed_url or str(source.get("rss") or source.get("url") or ""),
        "source_tier": effective_tier,
        "source_level": effective_level,
        "claimed_source_level": level_claimed,
        "priority_score": int(source.get("priority", PRIORITY_MAP.get(effective_level, 60))),
        "source_category": str(source.get("category", "")),
        "category": category,
        "verification_required": bool(source.get("verification_required", level_claimed <= 3)),
        "needs_primary_verification": needs_primary,
        "access_method": method or str(source.get("access_method", "unknown")),
        "discovery_role": role or ("discovery" if is_discovery else "primary_candidate"),
        "source_group": group,
        "image_url": normalize_url(image_url or img) if (image_url or img) else "",
        "feed_entry_id": entry_id,
        "collected_at": timestamp,
        "date_missing": published is None,
        "date_in_window": None,                   # set by collect_with_report
        "supporting_sources": [],
    }
    return item


# ---------------------------------------------------------------------------
# Source collection and reports
# ---------------------------------------------------------------------------
def _source_host(source: dict[str, Any]) -> str:
    return url_host(str(source.get("url", "")))


def _source_is_enabled_for_job(source: dict[str, Any], job_type: str) -> bool:
    level = int(source.get("level", 5))
    frequency = str(source.get("frequency", "daily")).lower()
    if level == 0:
        return True
    if job_type == "daily":
        return frequency in {"daily", "on_demand"} or level == 4
    return True


def _collect_one(group: str, source: dict[str, Any]) -> tuple[list[dict[str, Any]], SourceResult]:
    started = time.monotonic()
    name = str(source.get("name", "Unknown source"))
    base_url = str(source.get("url", "")).strip()
    result = SourceResult(name, base_url, int(source.get("level", 5)))
    if not normalize_url(base_url):
        result.error = "invalid_or_missing_source_url"
        result.duration_seconds = time.monotonic() - started
        return [], result

    all_candidates: list[dict[str, Any]] = []
    attempted_methods: list[str] = []
    # First: declared feed and allowed fallback feed candidates.
    for feed_url, method in _feed_candidates(source, base_url):
        if time.monotonic() - started > REQUEST_TIMEOUT * (MAX_RETRIES + 1) * 3:
            result.error = "source_time_budget_exceeded"
            break
        attempted_methods.append(method)
        status, body, error, attempts = _fetch_text(feed_url)
        result.attempts += attempts
        if status is None or body is None or error:
            result.error = error or f"http_{status}"
            continue
        items = _parse_feed(source, feed_url, body, method, group)
        if items:
            all_candidates = items
            result.method = method
            break
        result.error = "feed_parsed_but_no_valid_entries"

    # Second: official listing page. Only use it when RSS routes yielded nothing.
    if not all_candidates:
        attempted_methods.append("official_html_listing")
        status, body, error, attempts = _fetch_text(base_url)
        result.attempts += attempts
        if status is not None and body is not None and not error:
            all_candidates = _extract_listing_items(source, base_url, body, group, MAX_HTML_LINKS_PER_SOURCE)
            if all_candidates:
                result.method = "official_html_listing"
        else:
            result.error = error or f"html_http_{status}"

    # Do not hide a failed source, but do not let one failure block the whole batch.
    if all_candidates:
        result.success = True
        result.item_count = len(all_candidates)
        result.error = ""
    elif not result.error:
        result.error = "no_valid_articles_found"
    if attempted_methods and not result.method:
        result.method = "+".join(dict.fromkeys(attempted_methods))
    result.duration_seconds = round(time.monotonic() - started, 3)
    return all_candidates, result


def _collect_verified_feeds() -> tuple[list[dict[str, Any]], list[SourceResult]]:
    """Fetch the small, explicitly verified-feed list directly (no HTML fallback)."""
    items: list[dict[str, Any]] = []
    results: list[SourceResult] = []
    for name, feed_url, tier, category in VERIFIED_RSS:
        level = 4 if tier == "tier2" else 0
        source = {
            "name": name,
            "url": feed_url,
            "rss": feed_url,
            "level": level,
            "priority": 80 if tier == "tier2" else 100,
            "category": category,
            "verification_required": tier == "tier1",
            "frequency": "daily",
        }
        started = time.monotonic()
        status, body, error, attempts = _fetch_text(feed_url)
        result = SourceResult(
            source_name=name,
            source_url=feed_url,
            source_level=level,
            attempts=attempts,
            method="verified_rss",
        )
        if status is not None and body is not None and not error:
            fetched = _parse_feed(source, feed_url, body, "verified_rss", "verified_feed")
            items.extend(fetched)
            result.success = bool(fetched)
            result.item_count = len(fetched)
            result.error = "" if fetched else "feed_parsed_but_no_valid_entries"
        else:
            result.error = error or f"http_{status}"
        result.duration_seconds = round(time.monotonic() - started, 3)
        results.append(result)
    return items, results


def _canonical_dedupe(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate exact canonical URLs only; keep cross-source corroboration candidates."""
    by_url: dict[str, dict[str, Any]] = {}
    for item in items:
        url = normalize_url(str(item.get("source_url") or item.get("link") or ""))
        if not url:
            continue
        item["source_url"] = url
        item["link"] = url
        old = by_url.get(url)
        if old is None:
            by_url[url] = item
            continue
        # Preserve the better summary and retain provenance from both records.
        if len(item.get("summary", "")) > len(old.get("summary", "")):
            item.setdefault("supporting_sources", []).append({"name": old.get("source_name"), "url": old.get("source_feed")})
            by_url[url] = item
        else:
            old.setdefault("supporting_sources", []).append({"name": item.get("source_name"), "url": item.get("source_feed")})
    return list(by_url.values())


def core_coverage_report(collected_items: list[dict[str, Any]], source_results: Optional[list[SourceResult]] = None) -> dict[str, Any]:
    """Report how many configured Level-0 core sources returned at least one item."""
    core = list(LEVEL_0_CORE)
    counts = {str(src.get("name", "Unknown")): 0 for src in core}
    by_name = {name.casefold(): name for name in counts}
    for item in collected_items:
        name = str(item.get("source_name", "")).casefold()
        if name in by_name:
            counts[by_name[name]] += 1
    attempted_names = {r.source_name.casefold() for r in (source_results or [])}
    missing = [name for name, count in counts.items() if count == 0]
    covered = sum(1 for count in counts.values() if count > 0)
    total = len(counts)
    return {
        "configured": total,
        "attempted": sum(1 for name in counts if name.casefold() in attempted_names),
        "covered": covered,
        "missing": missing,
        "counts": counts,
        "coverage_ratio": round(covered / total, 4) if total else 1.0,
    }


def collect_with_report(
    max_items: Optional[int] = None,
    job_type: str = "daily",
    job_date: Optional[str] = None,
    *,
    min_items: Optional[int] = None,
    workers: Optional[int] = None,
    deadline_seconds: Optional[int] = None,
    keep_undated: Optional[bool] = None,
) -> dict[str, Any]:
    """Collect items and return a report dictionary; raises on unusable output."""
    effective_date = job_date or os.getenv("ALP_JOB_DATE") or datetime.now(IST).date().isoformat()
    cfg = CollectorConfig(
        job_type=job_type,
        job_date=effective_date,
        max_items=max(1, int(max_items or MAX_ITEMS_DEFAULT)),
        min_items=max(1, int(min_items if min_items is not None else MIN_ITEMS_DEFAULT)),
        workers=max(1, min(24, int(workers or MAX_WORKERS))),
        deadline_seconds=max(15, int(deadline_seconds or COLLECT_DEADLINE_S)),
        keep_undated=KEEP_UNDATED if keep_undated is None else bool(keep_undated),
        include_tier5_fallback=ENABLE_TIER5_FALLBACK,
    )
    start_window, end_window = collect_window(cfg.job_type, cfg.job_date)
    started_dt = datetime.now(IST)
    started_mono = time.monotonic()
    report = CollectionReport(cfg.job_type, cfg.job_date, started_dt.isoformat())
    selected = [(group, source) for group, source in _source_registry() if _source_is_enabled_for_job(source, cfg.job_type)]
    selected.sort(key=lambda pair: (-int(pair[1].get("priority", 0)), int(pair[1].get("level", 5)), str(pair[1].get("name", ""))))
    raw_items: list[dict[str, Any]] = []
    source_results: list[SourceResult] = []

    # Verified, known RSS feeds are quick and independent; include them as extra candidates.
    verified_items, verified_results = _collect_verified_feeds()
    raw_items.extend(verified_items)
    source_results.extend(verified_results)

    # Source tasks are isolated; each one returns its own error instead of failing the pool.
    executor = ThreadPoolExecutor(max_workers=min(cfg.workers, max(1, len(selected))))
    futures = {executor.submit(_collect_one, group, source): (group, source) for group, source in selected}
    try:
        remaining = max(1.0, cfg.deadline_seconds - (time.monotonic() - started_mono))
        for future in as_completed(futures, timeout=remaining):
            try:
                items, result = future.result()
                raw_items.extend(items)
                source_results.append(result)
            except Exception as exc:  # source-level isolation is a hard requirement
                group, source = futures[future]
                source_results.append(SourceResult(
                    source_name=str(source.get("name", "Unknown source")),
                    source_url=str(source.get("url", "")),
                    source_level=int(source.get("level", 5)),
                    error=f"unexpected_worker_error:{type(exc).__name__}:{exc}",
                ))
    except FuturesTimeoutError:
        report.warnings.append("collector_deadline_reached_partial_results_kept")
        logger.warning("Collector deadline reached; returning completed source results only")
    finally:
        # Cancel queued work; HTTP requests are independently bounded by REQUEST_TIMEOUT.
        for future in futures:
            if not future.done():
                future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)

    report.source_count = len(source_results)
    report.source_success_count = sum(1 for result in source_results if result.success)
    report.source_failure_count = sum(1 for result in source_results if not result.success)
    report.raw_item_count = len(raw_items)

    in_window_items: list[dict[str, Any]] = []
    for item in raw_items:
        accepted = in_window(item, start_window, end_window, cfg.keep_undated)
        item["date_in_window"] = accepted
        if accepted:
            in_window_items.append(item)
    report.in_window_count = len(in_window_items)

    unique_items = _canonical_dedupe(in_window_items)
    unique_items.sort(key=lambda item: (
        int(item.get("priority_score", 0)),
        1 if item.get("pub_time_ist") else 0,
        str(item.get("pub_time_ist") or ""),
    ), reverse=True)
    unique_items = unique_items[:cfg.max_items]
    report.unique_item_count = len(unique_items)
    report.core_coverage = core_coverage_report(unique_items, source_results)
    report.source_results = [asdict(result) for result in sorted(source_results, key=lambda r: (-r.source_level, r.source_name))]

    elapsed = time.monotonic() - started_mono
    finished = datetime.now(IST)
    report.finished_at = finished.isoformat()
    report.duration_seconds = round(elapsed, 3)

    if ENFORCE_CORE_COVERAGE and report.core_coverage.get("coverage_ratio", 0.0) < MIN_CORE_COVERAGE:
        raise RuntimeError(
            f"Core source coverage {report.core_coverage.get('coverage_ratio', 0):.1%} "
            f"is below configured minimum {MIN_CORE_COVERAGE:.1%}. "
            f"Missing: {report.core_coverage.get('missing', [])[:8]}"
        )
    if len(unique_items) < cfg.min_items:
        errors = [r.error for r in source_results if r.error][:8]
        raise RuntimeError(
            f"Collection yielded {len(unique_items)} unique in-window items; minimum is {cfg.min_items}. "
            f"Window={start_window.isoformat()}..{end_window.isoformat()}; errors={errors}"
        )

    logger.info(
        "Collection complete job=%s type=%s items=%d raw=%d sources_ok=%d/%d duration=%.1fs core=%.1f%%",
        cfg.job_date, cfg.job_type, len(unique_items), len(raw_items), report.source_success_count,
        report.source_count, report.duration_seconds, report.core_coverage.get("coverage_ratio", 0.0) * 100,
    )
    return {"items": unique_items, "report": asdict(report), "window": {"start": start_window.isoformat(), "end": end_window.isoformat()}}


def collect_all(
    max_items: int = MAX_ITEMS_DEFAULT,
    job_type: str = "daily",
    job_date: Optional[str] = None,
    *,
    return_errors: bool = False,
) -> Any:
    """Compatibility API: return list of items by default.

    Set ``return_errors=True`` to get ``(items, source_errors)`` for callers that
    used the old collector's tuple contract.
    """
    result = collect_with_report(max_items=max_items, job_type=job_type, job_date=job_date)
    items = result["items"]
    if return_errors:
        errors = [entry for entry in result["report"]["source_results"] if entry.get("error")]
        return items, errors
    return items


def _collect_all_inner(t0: float, max_items: int, job_type: str = "daily") -> tuple[list[dict[str, Any]], list[str]]:
    """Legacy internal adapter retained for old callers; prefer collect_with_report()."""
    items, errors = collect_all(max_items=max_items, job_type=job_type, return_errors=True)
    return items, [str(e.get("error", "")) for e in errors if e.get("error")]


def _gnews_source(source: dict[str, Any], tier: str = "tier2", cap: int = 25) -> list[dict[str, Any]]:
    """Compatibility helper for Google News site-search RSS discovery."""
    host = _source_host(source)
    url = gnews_url(host) if host else ""
    if not url:
        return []
    return rss_items(source, url, tier=tier, role="gnews_discovery")[:cap]


# ---------------------------------------------------------------------------
# Atomic outputs and CLI
# ---------------------------------------------------------------------------
def _atomic_json_write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + f".{os.getpid()}.tmp")
    try:
        with temp.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        try:
            if temp.exists():
                temp.unlink()
        except OSError:
            pass


def _update_source_health(report: dict[str, Any], path: Path = STATE_DIR / "source_health.json") -> None:
    """Persist last-run source outcomes without allowing health-file errors to hide collection."""
    try:
        old: dict[str, Any] = {}
        if path.exists():
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    old = loaded
            except (OSError, json.JSONDecodeError):
                old = {}
        sources = old.get("sources") if isinstance(old.get("sources"), dict) else {}
        for result in report.get("source_results", []):
            key = str(result.get("source_url") or result.get("source_name") or "unknown")
            previous = sources.get(key, {}) if isinstance(sources.get(key), dict) else {}
            ok = bool(result.get("success"))
            sources[key] = {
                **previous,
                "source_name": result.get("source_name"),
                "source_level": result.get("source_level"),
                "last_attempt_at": report.get("finished_at"),
                "last_success_at": report.get("finished_at") if ok else previous.get("last_success_at"),
                "last_success": ok,
                "last_item_count": int(result.get("item_count", 0)),
                "consecutive_failures": 0 if ok else int(previous.get("consecutive_failures", 0)) + 1,
                "last_error": "" if ok else result.get("error", "unknown_error"),
                "last_method": result.get("method", "none"),
            }
        payload = {"version": 1, "updated_at": report.get("finished_at"), "sources": sources}
        _atomic_json_write(path, payload)
    except Exception as exc:
        logger.warning("Could not update source health file %s: %s", path, exc)


def _default_output_path(job_type: str, job_date: str) -> Path:
    """Use the current pipeline's Agent 04-compatible date-based raw filename."""
    return RAW_DIR / f"news_{job_date}.json"


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect and normalize news for Agri Learning Point")
    parser.add_argument("--job-type", "--type", dest="job_type", choices=("daily", "weekly", "monthly"), default=os.getenv("ALP_JOB_TYPE", "daily"))
    parser.add_argument("--date", dest="job_date", default=os.getenv("ALP_JOB_DATE", ""), help="Edition date YYYY-MM-DD")
    parser.add_argument("--max-items", type=int, default=MAX_ITEMS_DEFAULT)
    parser.add_argument("--min-items", type=int, default=MIN_ITEMS_DEFAULT)
    parser.add_argument("--workers", type=int, default=MAX_WORKERS)
    parser.add_argument("--deadline-seconds", type=int, default=COLLECT_DEADLINE_S)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Collect and report, but do not write raw output")
    parser.add_argument("--json-report", type=Path, default=None, help="Optional path to write a detailed report JSON")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    job_date = args.job_date or datetime.now(IST).date().isoformat()
    try:
        result = collect_with_report(
            max_items=args.max_items,
            job_type=args.job_type,
            job_date=job_date,
            min_items=args.min_items,
            workers=args.workers,
            deadline_seconds=args.deadline_seconds,
        )
    except Exception as exc:
        logger.exception("Collection failed for %s/%s: %s", args.job_type, job_date, exc)
        return 2

    report = result["report"]
    output_path = args.output or _default_output_path(args.job_type, job_date)
    if not args.dry_run:
        _atomic_json_write(output_path, result["items"])
        logger.info("Wrote %d normalized articles to %s", len(result["items"]), output_path)
        _update_source_health(report)
    else:
        logger.info("DRY RUN: not writing %s", output_path)

    if args.json_report:
        _atomic_json_write(args.json_report, {**report, "window": result["window"], "output_path": str(output_path), "dry_run": args.dry_run})
    logger.info("Summary: %s", json.dumps({
        "job_type": args.job_type,
        "job_date": job_date,
        "item_count": len(result["items"]),
        "source_success_count": report["source_success_count"],
        "source_failure_count": report["source_failure_count"],
        "core_coverage": report["core_coverage"].get("coverage_ratio", 0),
        "output": None if args.dry_run else str(output_path),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
