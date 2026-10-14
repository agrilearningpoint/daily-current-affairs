# -*- coding: utf-8 -*-
"""
Source Fetch Stage (01)
========================
Canonical RSS/Atom fetch stage.

Reads sources from config.registry (unified).
Writes canonical output: data/raw/{job_id}.json
Also writes legacy: data/raw/news_{date}.json

Env (set by main.py):
  ALP_JOB_ID, ALP_JOB_TYPE, ALP_JOB_DATE
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
from typing import Any, Dict, List, Optional

import feedparser
import requests

# Path setup
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

LOGS_DIR = REPO_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(LOGS_DIR / "source_fetch.log"), encoding="utf-8"),
    ],
)
logger = logging.getLogger("stage.01_source_fetch")

USER_AGENT = "AgriLearningPoint/1.0 (+https://github.com/agrilearningpoint)"
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
MAX_ARTICLES_PER_SOURCE = int(os.getenv("MAX_ARTICLES_PER_SOURCE", "100"))
MAX_RESPONSE_BYTES = int(os.getenv("MAX_RESPONSE_BYTES", str(5 * 1024 * 1024)))

HTML_TAG_RE = re.compile(r"<[^>]+>")
CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
WHITESPACE_RE = re.compile(r"\s+")
TRACKING_PARAMS = re.compile(
    r"^(utm_|fbclid|gclid|ref|_ga|mc_|yclid|_hsenc|_hsmi)", re.IGNORECASE
)


# --------------------------------------------------------------------------- #
# Utilities
# --------------------------------------------------------------------------- #
def clean_text(text: str, max_len: int = 5000) -> str:
    if not text:
        return ""
    text = HTML_TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = unicodedata.normalize("NFC", text)
    text = CONTROL_CHAR_RE.sub("", text)
    text = WHITESPACE_RE.sub(" ", text).strip()
    if len(text) > max_len:
        text = text[:max_len].rstrip()
    return text


def normalize_url(url: str) -> str:
    if not url:
        return ""
    url = url.split("#", 1)[0]
    if "?" in url:
        base, qs = url.split("?", 1)
        kept = [
            p for p in qs.split("&")
            if p and not TRACKING_PARAMS.match(p.split("=", 1)[0])
        ]
        url = base + ("?" + "&".join(kept) if kept else "")
    return url.rstrip("/")


def article_hash(title: str, link: str) -> str:
    return hashlib.sha256(f"{title.lower()}|{link}".encode("utf-8")).hexdigest()[:16]


def atomic_write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    with open(tmp, "rb") as f:
        os.fsync(f.fileno())
    os.replace(tmp, path)


# --------------------------------------------------------------------------- #
# Fetch
# --------------------------------------------------------------------------- #
def fetch_feed_bytes(url: str) -> Optional[bytes]:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/rss+xml, application/atom+xml, */*",
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
                        logger.warning("%s exceeds size cap", url)
                        break
                return content
        except requests.RequestException as exc:
            wait = (2 ** attempt) + random.uniform(0, 1)
            logger.warning(
                "attempt %d/%d failed %s: %s (retry %.1fs)",
                attempt, MAX_RETRIES, url, exc, wait,
            )
            if attempt < MAX_RETRIES:
                time.sleep(wait)
    return None


def parse_feed(url: str, raw: bytes) -> List[Dict[str, Any]]:
    articles = []
    collected_at = datetime.now(timezone.utc).isoformat()
    try:
        feed = feedparser.parse(raw)
    except Exception as exc:
        logger.exception("parse failed %s: %s", url, exc)
        return []
    if getattr(feed, "bozo", 0):
        logger.warning("feed warning %s: %s", url, feed.bozo_exception)
    for entry in feed.entries[:MAX_ARTICLES_PER_SOURCE]:
        try:
            title = clean_text(entry.get("title", ""), 500)
            link = normalize_url(entry.get("link", ""))
            summary = clean_text(
                entry.get("summary", "") or entry.get("description", ""), 3000
            )
            published = clean_text(
                entry.get("published", "") or entry.get("updated", ""), 100
            )
            if not title or not link or not link.startswith(("http://", "https://")):
                continue
            articles.append({
                "title": title,
                "link": link,
                "summary": summary,
                "published": published,
                "source_feed": url,
                "collected_at": collected_at,
                "content_hash": article_hash(title, link),
            })
        except Exception:
            continue
    return articles


def dedup(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_url = {}
    for a in articles:
        u = a.get("link", "")
        if not u:
            continue
        cur = by_url.get(u)
        if cur is None or len(a.get("summary", "")) > len(cur.get("summary", "")):
            by_url[u] = a
    by_hash = {}
    for a in by_url.values():
        h = a.get("content_hash", "")
        if h not in by_hash:
            by_hash[h] = a
    return list(by_hash.values())


# --------------------------------------------------------------------------- #
# Config loading (with fallbacks)
# --------------------------------------------------------------------------- #
def _load_source_urls() -> List[str]:
    """Load URLs from config.registry, config.sources, or config.feeds."""
    # Try canonical registry first
    try:
        from config.registry import get_feed_urls  # type: ignore
        urls = get_feed_urls()
        if urls:
            logger.info("Loaded %d URLs from config.registry", len(urls))
            return urls
    except ImportError:
        pass
    except Exception as exc:
        logger.warning("config.registry failed: %s", exc)

    # Fallback: config.sources
    try:
        from config.sources import RSS_FEEDS  # type: ignore
        if RSS_FEEDS:
            logger.info("Loaded %d URLs from config.sources", len(RSS_FEEDS))
            return list(RSS_FEEDS)
    except ImportError:
        pass
    except Exception as exc:
        logger.warning("config.sources failed: %s", exc)

    # Fallback: config.feeds
    try:
        from config.feeds import VERIFIED_RSS  # type: ignore
        if VERIFIED_RSS:
            logger.info("Loaded %d URLs from config.feeds", len(VERIFIED_RSS))
            return list(VERIFIED_RSS)
    except ImportError:
        pass
    except Exception as exc:
        logger.warning("config.feeds failed: %s", exc)

    return []


def _get_job_context() -> Dict[str, str]:
    """Read job context from env, with fallbacks."""
    job_id = os.getenv("ALP_JOB_ID") or os.getenv("JOB_ID") or ""
    job_type = os.getenv("ALP_JOB_TYPE") or os.getenv("JOB_TYPE") or "daily"
    job_date = os.getenv("ALP_JOB_DATE") or ""

    if not job_date and job_id and "_" in job_id:
        job_date = job_id.split("_", 1)[1]
    if not job_date:
        job_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not job_id:
        job_id = f"{job_type}_{job_date}"

    return {"job_id": job_id, "job_type": job_type, "job_date": job_date}


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> int:
    ctx = _get_job_context()
    logger.info("Source fetch | job=%s date=%s", ctx["job_id"], ctx["job_date"])

    urls = _load_source_urls()
    output_dir = REPO_ROOT / "data" / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)

    canonical_out = output_dir / f"{ctx['job_id']}.json"
    legacy_out = output_dir / f"news_{ctx['job_date']}.json"

    if not urls:
        logger.error("No sources configured. Checked config.registry, "
                     "config.sources, config.feeds")
        atomic_write(canonical_out, [])
        atomic_write(legacy_out, [])
        return 1

    logger.info("Fetching from %d sources", len(urls))
    all_articles: List[Dict[str, Any]] = []
    failed = 0

    for idx, url in enumerate(urls, 1):
        logger.info("[%d/%d] %s", idx, len(urls), url[:80])
        raw = fetch_feed_bytes(url)
        if raw is None:
            failed += 1
            continue
        articles = parse_feed(url, raw)
        logger.info("  -> %d articles", len(articles))
        all_articles.extend(articles)

    unique = dedup(all_articles)
    logger.info("Dedup: %d -> %d", len(all_articles), len(unique))

    atomic_write(canonical_out, unique)
    if legacy_out != canonical_out:
        atomic_write(legacy_out, unique)

    if not unique:
        logger.error("0 articles after dedup — %d sources failed", failed)
        return 1
    logger.info("OK - %d unique articles -> %s", len(unique), canonical_out)
    return 0


if __name__ == "__main__":
    sys.exit(main())