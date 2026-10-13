"""
Source Fetcher Module
---------------------
Yeh module configured RSS/Atom feeds + APIs se raw news articles fetch karta hai.

Production features:
- Parallel fetching with bounded concurrency (ThreadPoolExecutor)
- Per-source timeout + retry with exponential backoff
- Source health tracking (dead feeds identified, warned)
- Content sanitization (HTML strip, unicode normalize, control char removal)
- De-duplication (by URL + content hash)
- Size limits (prevents memory blowup)
- Graceful degradation (partial success > total failure)
- Atomic output write
"""

import os
import re
import sys
import json
import time
import html
import hashlib
import logging
import argparse
import unicodedata
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import requests
import feedparser
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/source_fetch.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------
CONFIG_FILE = "config/sources.json"
OUTPUT_DIR = "data/raw"
HEALTH_FILE = "state/source_health.json"

USER_AGENT = "AgriLearningPoint-Bot/1.0 (+https://github.com/agrilearningpoint)"
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "8"))
MAX_RESPONSE_BYTES = int(os.getenv("MAX_RESPONSE_BYTES", str(5 * 1024 * 1024)))  # 5 MB
MAX_ARTICLES_PER_SOURCE = int(os.getenv("MAX_ARTICLES_PER_SOURCE", "100"))

# Sanitization
HTML_TAG_RE = re.compile(r"<[^>]+>")
CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
WHITESPACE_RE = re.compile(r"\s+")


# ------------------------------------------------------------------
# Utilities
# ------------------------------------------------------------------
def clean_text(text: str, max_len: int = 5000) -> str:
    """
    Sanitize text for downstream processing:
    - HTML tag strip
    - HTML entity unescape
    - Unicode NFC normalize
    - Control chars remove
    - Whitespace collapse
    - Length cap
    """
    if not text:
        return ""
    # Strip tags BEFORE unescaping entities (order matters)
    text = HTML_TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = unicodedata.normalize("NFC", text)
    text = CONTROL_CHAR_RE.sub("", text)
    text = WHITESPACE_RE.sub(" ", text).strip()
    if len(text) > max_len:
        text = text[:max_len].rstrip()
    return text


def content_hash(article: Dict[str, Any]) -> str:
    """Stable hash for dedup across sources."""
    raw = f"{article.get('title', '').lower()}|{article.get('link', '')}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def normalize_url(url: str) -> str:
    """Strip tracking params and fragments for dedup."""
    if not url:
        return ""
    # Remove fragment
    url = url.split("#", 1)[0]
    # Remove common tracking params
    if "?" in url:
        base, qs = url.split("?", 1)
        keep = []
        for pair in qs.split("&"):
            k = pair.split("=", 1)[0].lower()
            if k.startswith(("utm_", "fbclid", "gclid", "ref", "_ga")):
                continue
            keep.append(pair)
        url = base + ("?" + "&".join(keep) if keep else "")
    return url.rstrip("/")


# ------------------------------------------------------------------
# Source Health Tracking
# ------------------------------------------------------------------
def load_health(path: str = HEALTH_FILE) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {"version": 1, "sources": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"version": 1, "sources": {}}


def save_health(health: Dict[str, Any], path: str = HEALTH_FILE) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(health, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def update_health(
    health: Dict[str, Any],
    source_url: str,
    success: bool,
    article_count: int = 0,
    error: Optional[str] = None,
) -> None:
    sources = health.setdefault("sources", {})
    entry = sources.setdefault(source_url, {
        "success_count": 0,
        "failure_count": 0,
        "consecutive_failures": 0,
        "last_success_at": None,
        "last_failure_at": None,
        "last_error": None,
        "last_article_count": 0,
    })
    now = datetime.now(timezone.utc).isoformat()
    if success:
        entry["success_count"] += 1
        entry["consecutive_failures"] = 0
        entry["last_success_at"] = now
        entry["last_article_count"] = article_count
        entry["last_error"] = None
    else:
        entry["failure_count"] += 1
        entry["consecutive_failures"] += 1
        entry["last_failure_at"] = now
        entry["last_error"] = (error or "")[:500]


# ------------------------------------------------------------------
# Fetching
# ------------------------------------------------------------------
@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=2, min=2, max=20),
    retry=retry_if_exception_type(requests.RequestException),
    reraise=True,
)
def _fetch_raw(url: str) -> bytes:
    """Fetch URL with retry + timeout + size guard."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
    }
    with requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT, stream=True) as r:
        r.raise_for_status()
        content = b""
        for chunk in r.iter_content(chunk_size=65536):
            content += chunk
            if len(content) > MAX_RESPONSE_BYTES:
                raise requests.RequestException(
                    f"Response exceeds {MAX_RESPONSE_BYTES} bytes"
                )
        return content


def parse_feed(raw_bytes: bytes) -> Any:
    """Parse RSS/Atom safely."""
    # feedparser handles bytes; pass through
    return feedparser.parse(raw_bytes)


def extract_articles_from_feed(
    feed_url: str,
    feed_data: Any,
    collected_at: str,
) -> List[Dict[str, Any]]:
    """
    Extract & sanitize articles from a parsed feed.
    Skips entries without title/link, caps per-source count.
    """
    articles: List[Dict[str, Any]] = []

    if getattr(feed_data, "bozo", 0):
        logger.warning("Feed parse warning for %s: %s", feed_url, feed_data.bozo_exception)

    for entry in feed_data.entries[:MAX_ARTICLES_PER_SOURCE]:
        title = clean_text(entry.get("title", ""), max_len=500)
        link = normalize_url(entry.get("link", "").strip())
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

        article = {
            "title": title,
            "link": link,
            "summary": summary,
            "published": published,
            "source_feed": feed_url,
            "collected_at": collected_at,
        }
        article["content_hash"] = content_hash(article)
        articles.append(article)

    return articles


def fetch_source(
    source_url: str,
    collected_at: str,
) -> Tuple[str, List[Dict[str, Any]], Optional[str]]:
    """
    Fetch & parse one source. Returns (url, articles, error).
    Never raises — always returns a tuple.
    """
    try:
        raw = _fetch_raw(source_url)
        feed = parse_feed(raw)
        articles = extract_articles_from_feed(source_url, feed, collected_at)
        logger.info("✔ %s → %d articles", source_url, len(articles))
        return source_url, articles, None
    except Exception as exc:
        logger.warning("✘ %s → %s", source_url, exc)
        return source_url, [], str(exc)


# ------------------------------------------------------------------
# Deduplication
# ------------------------------------------------------------------
def deduplicate_articles(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Dedup by URL first, then by content_hash.
    Keeps the article with longer summary (better content).
    """
    by_url: Dict[str, Dict[str, Any]] = {}
    for art in articles:
        url = art.get("link", "")
        if not url:
            continue
        existing = by_url.get(url)
        if existing is None or len(art.get("summary", "")) > len(existing.get("summary", "")):
            by_url[url] = art

    by_hash: Dict[str, Dict[str, Any]] = {}
    for art in by_url.values():
        h = art.get("content_hash") or content_hash(art)
        if h not in by_hash:
            by_hash[h] = art

    result = list(by_hash.values())
    logger.info("Dedup: %d → %d articles", len(articles), len(result))
    return result


# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------
def load_sources(config_path: str = CONFIG_FILE) -> List[str]:
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Support both {"rss_feeds": [...]} and {"sources": [{"url": ...}]}
    if isinstance(config, list):
        return [str(s) for s in config if s]
    if "rss_feeds" in config:
        return [str(s) for s in config["rss_feeds"] if s]
    if "sources" in config:
        return [str(s.get("url") if isinstance(s, dict) else s) for s in config["sources"] if s]
    raise ValueError("Config must have 'rss_feeds' or 'sources' key.")


# ------------------------------------------------------------------
# Output
# ------------------------------------------------------------------
def save_articles(articles: List[Dict[str, Any]], output_file: str) -> None:
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    tmp = f"{output_file}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, output_file)
    logger.info("Saved %d articles to %s", len(articles), output_file)


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fetch news from configured sources")
    p.add_argument("--config", default=CONFIG_FILE)
    p.add_argument("--workers", type=int, default=MAX_WORKERS)
    p.add_argument("--max-per-source", type=int, default=MAX_ARTICLES_PER_SOURCE)
    p.add_argument("--fail-on-empty", action="store_true",
                   help="Exit non-zero if no articles collected")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    global MAX_ARTICLES_PER_SOURCE
    MAX_ARTICLES_PER_SOURCE = args.max_per_source

    try:
        sources = load_sources(args.config)
    except Exception as exc:
        logger.error("Failed to load sources: %s", exc)
        return 1

    if not sources:
        logger.error("No sources configured.")
        return 1

    logger.info("Starting fetch from %d sources (workers=%d)", len(sources), args.workers)
    collected_at = datetime.now(timezone.utc).isoformat()
    all_articles: List[Dict[str, Any]] = []
    health = load_health()

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(fetch_source, url, collected_at): url for url in sources}
        for fut in as_completed(futures):
            url, articles, error = fut.result()
            all_articles.extend(articles)
            update_health(health, url, success=error is None,
                          article_count=len(articles), error=error)

    save_health(health)

    all_articles = deduplicate_articles(all_articles)

    if not all_articles:
        logger.error("No articles collected from any source.")
        if args.fail_on_empty:
            return 2
        # Still emit empty file so downstream doesn't break on missing input
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        save_articles([], os.path.join(OUTPUT_DIR, f"news_{date_str}.json"))
        return 0

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    output_file = os.path.join(OUTPUT_DIR, f"news_{date_str}.json")
    save_articles(all_articles, output_file)
    logger.info("Source fetch stage completed: %d unique articles.", len(all_articles))
    return 0


if __name__ == "__main__":
    sys.exit(main())
