# -*- coding: utf-8 -*-
"""
News Collection Agent (03)
==========================
RSS / Atom feeds se news articles collect karta hai.

Production features:
- Unicode-safe text cleaning (Devanagari preserved via NFC)
- Retry with exponential backoff + jitter
- Per-source isolation (ek fail ho toh baaki ruke nahi)
- URL normalization (tracking params strip)
- De-duplication (URL + title hash)
- Config via JSON file OR Python module
- Structured logging + run summary
- Atomic output write (crash-safe)
"""
from __future__ import annotations

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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import feedparser
import requests

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
REPO_ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = REPO_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(LOGS_DIR / "news_collection.log"), encoding="utf-8"),
    ],
)
logger = logging.getLogger("agent.03_news_collection")

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #
USER_AGENT = "AgriLearningPoint/1.0 (+https://github.com/agrilearningpoint)"
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
BACKOFF_BASE = 2
MAX_ARTICLES_PER_SOURCE = int(os.getenv("MAX_ARTICLES_PER_SOURCE", "100"))
MAX_RESPONSE_BYTES = int(os.getenv("MAX_RESPONSE_BYTES", str(5 * 1024 * 1024)))

OUTPUT_DIR = REPO_ROOT / "data" / "raw"

# Config candidates — JSON preferred, Python module supported
CONFIG_JSON_CANDIDATES = [
    REPO_ROOT / "config" / "news_sources.json",
    REPO_ROOT / "config" / "sources.json",
]
CONFIG_PY_CANDIDATES = [
    REPO_ROOT / "config" / "sources.py",
    REPO_ROOT / "config" / "feeds.py",
]

# Text cleaning regexes
HTML_TAG_RE = re.compile(r"<[^>]+>")
# Control chars ONLY (excludes \t \n \r which are legitimate whitespace)
CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
WHITESPACE_RE = re.compile(r"\s+")

# Tracking params to strip from URLs
TRACKING_PARAMS = re.compile(
    r"^(utm_|fbclid|gclid|ref|_ga|mc_|yclid|_hsenc|_hsmi|hsCtaTracking)",
    re.IGNORECASE,
)


# --------------------------------------------------------------------------- #
# Unicode-Safe Text Cleaning  ← THE CRITICAL FIX
# --------------------------------------------------------------------------- #
def clean_text(text: str, max_len: int = 5000) -> str:
    """
    Unicode-safe text cleaning.

    Preserves Devanagari, Tamil, Bengali, and all valid Unicode letters.
    Only strips:
    - HTML tags
    - Control characters (not \t \n \r)
    - Collapses whitespace

    Normalizes via NFC (required for correct Devanagari conjuncts).
    """
    if not text:
        return ""

    # 1. Strip HTML tags
    text = HTML_TAG_RE.sub(" ", text)

    # 2. Unescape HTML entities (&amp; &lt; &nbsp; etc.)
    text = html.unescape(text)

    # 3. NFC normalization — critical for Devanagari/Indic scripts
    text = unicodedata.normalize("NFC", text)

    # 4. Remove control chars ONLY (Devanagari is \u0900-\u097F — must survive)
    text = CONTROL_CHAR_RE.sub("", text)

    # 5. Collapse whitespace
    text = WHITESPACE_RE.sub(" ", text).strip()

    # 6. Length cap
    if len(text) > max_len:
        text = text[:max_len].rstrip()

    return text


# --------------------------------------------------------------------------- #
# URL Normalization & Hashing
# --------------------------------------------------------------------------- #
def normalize_url(url: str) -> str:
    """Strip fragments and tracking params for dedup stability."""
    if not url:
        return ""
    url = url.strip()

    # Remove fragment
    url = url.split("#", 1)[0]

    # Remove tracking params
    if "?" in url:
        base, qs = url.split("?", 1)
        kept = [
            pair for pair in qs.split("&")
            if pair and not TRACKING_PARAMS.match(pair.split("=", 1)[0])
        ]
        url = base + ("?" + "&".join(kept) if kept else "")

    return url.rstrip("/")


def article_hash(title: str, link: str) -> str:
    raw = f"{title.lower().strip()}|{link}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


# --------------------------------------------------------------------------- #
# Config Loader (JSON or Python module)
# --------------------------------------------------------------------------- #
def _extract_sources_from_python(module_path: Path) -> List[str]:
    """Extract source URLs from a Python config module."""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("_cfg_sources", module_path)
        if spec is None or spec.loader is None:
            return []
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as exc:
        logger.warning("Failed to import %s: %s", module_path, exc)
        return []

    feed_url_provider = getattr(mod, "get_rss_feed_urls", None)
    if callable(feed_url_provider):
        try:
            job_type = os.getenv("ALP_JOB_TYPE", "daily")
            urls = feed_url_provider(job_type)
            if isinstance(urls, (list, tuple)):
                return list(dict.fromkeys(
                    str(url).strip() for url in urls if str(url).strip()
                ))
        except Exception as exc:
            logger.warning("Failed to load RSS URLs from %s: %s", module_path, exc)
            return []

    # Common attribute names
    for attr in ("RSS_FEEDS", "FEEDS", "SOURCES", "rss_feeds", "sources"):
        val = getattr(mod, attr, None)
        if isinstance(val, (list, tuple)):
            return [
                item["url"] if isinstance(item, dict) and "url" in item else str(item)
                for item in val if item
            ]
    return []


def load_sources() -> List[str]:
    """Load source URLs from JSON or Python config."""
    # Try JSON first
    for cfg in CONFIG_JSON_CANDIDATES:
        if cfg.exists():
            try:
                data = json.loads(cfg.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return [str(x) for x in data if x]
                if isinstance(data, dict):
                    for key in ("rss_feeds", "feeds", "sources"):
                        if key in data and isinstance(data[key], list):
                            return [
                                item["url"] if isinstance(item, dict) and "url" in item
                                else str(item)
                                for item in data[key] if item
                            ]
            except Exception as exc:
                logger.error("Failed to read %s: %s", cfg, exc)

    # Try Python module
    for cfg in CONFIG_PY_CANDIDATES:
        if cfg.exists():
            urls = _extract_sources_from_python(cfg)
            if urls:
                logger.info("Loaded %d sources from %s", len(urls), cfg.name)
                return urls

    return []


# --------------------------------------------------------------------------- #
# HTTP Fetching
# --------------------------------------------------------------------------- #
def fetch_feed_bytes(url: str) -> Optional[bytes]:
    """Fetch feed with retry + size guard. Returns bytes or None."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
    }
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with requests.get(
                url, headers=headers, timeout=REQUEST_TIMEOUT, stream=True
            ) as r:
                r.raise_for_status()
                content = b""
                for chunk in r.iter_content(chunk_size=65536):
                    content += chunk
                    if len(content) > MAX_RESPONSE_BYTES:
                        logger.warning("%s exceeds size cap — truncating", url)
                        break
                return content
        except requests.RequestException as exc:
            wait = (BACKOFF_BASE ** attempt) + random.uniform(0, 1)
            logger.warning(
                "Fetch attempt %d/%d failed for %s: %s (retry in %.1fs)",
                attempt, MAX_RETRIES, url, exc, wait,
            )
            if attempt < MAX_RETRIES:
                time.sleep(wait)

    logger.error("All %d attempts failed for %s", MAX_RETRIES, url)
    return None


# --------------------------------------------------------------------------- #
# Feed Parsing
# --------------------------------------------------------------------------- #
def extract_articles(feed_url: str, raw_bytes: bytes) -> List[Dict[str, Any]]:
    """Parse feed bytes → list of sanitized article dicts."""
    articles: List[Dict[str, Any]] = []
    collected_at = datetime.now(timezone.utc).isoformat()

    try:
        feed = feedparser.parse(raw_bytes)
    except Exception as exc:
        logger.exception("Feed parser crash for %s: %s", feed_url, exc)
        return articles

    if getattr(feed, "bozo", 0):
        logger.warning("Feed warning for %s: %s", feed_url, feed.bozo_exception)

    for entry in feed.entries[:MAX_ARTICLES_PER_SOURCE]:
        try:
            title = clean_text(entry.get("title", ""), max_len=500)
            link = normalize_url(entry.get("link", ""))
            summary = clean_text(
                entry.get("summary", "") or entry.get("description", ""),
                max_len=3000,
            )
            published = clean_text(
                entry.get("published", "") or entry.get("updated", ""),
                max_len=100,
            )

            if not title or not link:
                continue
            if not link.startswith(("http://", "https://")):
                continue

            articles.append({
                "title": title,
                "link": link,
                "summary": summary,
                "published": published,
                "source_feed": feed_url,
                "collected_at": collected_at,
                "content_hash": article_hash(title, link),
            })
        except Exception as exc:
            logger.warning("Skipped malformed entry in %s: %s", feed_url, exc)

    return articles


# --------------------------------------------------------------------------- #
# Deduplication
# --------------------------------------------------------------------------- #
def deduplicate(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Keep one article per (normalized URL) and per (title hash)."""
    by_url: Dict[str, Dict[str, Any]] = {}
    for art in articles:
        url = art.get("link", "")
        if not url:
            continue
        existing = by_url.get(url)
        # Prefer the one with longer summary
        if existing is None or len(art.get("summary", "")) > len(existing.get("summary", "")):
            by_url[url] = art

    by_hash: Dict[str, Dict[str, Any]] = {}
    for art in by_url.values():
        h = art.get("content_hash") or article_hash(art.get("title", ""), art.get("link", ""))
        if h not in by_hash:
            by_hash[h] = art

    return list(by_hash.values())


# --------------------------------------------------------------------------- #
# Atomic Output
# --------------------------------------------------------------------------- #
def save_articles(articles: List[Dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = output_path.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(articles, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with open(tmp, "rb") as f:
        os.fsync(f.fileno())
    os.replace(tmp, output_path)
    logger.info("Saved %d articles → %s", len(articles), output_path)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> int:
    sources = load_sources()
    if not sources:
        logger.error("No sources configured. Checked: %s and %s",
                     [str(p) for p in CONFIG_JSON_CANDIDATES],
                     [str(p) for p in CONFIG_PY_CANDIDATES])
        return 1

    logger.info("Starting collection from %d source(s)", len(sources))
    start_time = time.time()
    all_articles: List[Dict[str, Any]] = []
    failed_sources = 0

    for idx, src in enumerate(sources, 1):
        logger.info("[%d/%d] %s", idx, len(sources), src)
        raw = fetch_feed_bytes(src)
        if raw is None:
            failed_sources += 1
            continue
        articles = extract_articles(src, raw)
        logger.info("    → %d articles", len(articles))
        all_articles.extend(articles)

    elapsed = time.time() - start_time
    logger.info(
        "Fetch complete in %.1fs | %d raw articles | %d source(s) failed",
        elapsed, len(all_articles), failed_sources,
    )

    unique = deduplicate(all_articles)
    logger.info("Dedup: %d → %d unique articles", len(all_articles), len(unique))

    if not unique:
        logger.error("No articles collected after dedup.")
        # Emit empty file so downstream doesn't crash on missing input
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        save_articles([], OUTPUT_DIR / f"news_{date_str}.json")
        return 1

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    save_articles(unique, OUTPUT_DIR / f"news_{date_str}.json")
    logger.info("✔ News collection completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
