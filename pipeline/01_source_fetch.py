# -*- coding: utf-8 -*-
"""
Zero-Key RSS/Atom-First News Collector with ETag Caching & Dead-Feed Quarantine
==============================================================================
Implements Master Spec Section 4:
- Works with 0 paid search API keys using `config/news_sources.json` & `config/feeds.py`.
- Concurrent RSS/Atom collection with per-request timeout & exponential backoff.
- Conditional HTTP requests (`If-None-Match` ETag and `If-Modified-Since`).
- Content caching for 304 Not Modified responses.
- Feed health tracking in `state/feed_health.json`:
  - Quarantines any feed after `MAX_FAILURES` (default 3) consecutive failures for
    `QUARANTINE_HOURS` (default 24h), then automatically probes recovery.
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import json
import logging
import os
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from pipeline.store import STATE_DIR, atomic_write_json, canonicalize_url, safe_read_json
from pipeline.windows import compute_edition_window, filter_articles_by_window

ROOT_DIR = Path(__file__).resolve().parent.parent
SOURCES_JSON = ROOT_DIR / "config" / "news_sources.json"
FEED_HEALTH_JSON = STATE_DIR / "feed_health.json"
FEED_CACHE_DIR = STATE_DIR / "feed_cache"
FEED_CACHE_DIR.mkdir(parents=True, exist_ok=True)

MAX_CONSECUTIVE_FAILURES = int(os.getenv("ALP_FEED_MAX_FAILURES", "3"))
QUARANTINE_HOURS = int(os.getenv("ALP_FEED_QUARANTINE_HOURS", "24"))
REQUEST_TIMEOUT = float(os.getenv("ALP_RSS_TIMEOUT", "10.0"))

logger = logging.getLogger("pipeline.01_source_fetch")


def load_configured_sources() -> List[Dict[str, Any]]:
    data = safe_read_json(SOURCES_JSON, {"sources": []})
    return [s for s in data.get("sources", []) if s.get("enabled", True)]


def is_feed_quarantined(health_entry: Dict[str, Any], now_utc: datetime) -> bool:
    q_until = health_entry.get("quarantined_until")
    if not q_until:
        return False
    try:
        until_dt = datetime.fromisoformat(q_until)
        if until_dt.tzinfo is None:
            until_dt = until_dt.replace(tzinfo=timezone.utc)
        # Automatic recovery probe once quarantine window expires
        return now_utc < until_dt
    except Exception:
        return False


def record_feed_result(
    health: Dict[str, Any],
    source_id: str,
    success: bool,
    now_utc: datetime,
    etag: Optional[str] = None,
    last_modified: Optional[str] = None,
    error_msg: str = "",
) -> None:
    entry = health.setdefault(source_id, {"failure_count": 0})
    if success:
        entry["failure_count"] = 0
        entry["last_successful_fetch"] = now_utc.isoformat()
        entry["quarantined_until"] = None
        entry["last_error"] = ""
        if etag:
            entry["etag"] = etag
        if last_modified:
            entry["last_modified"] = last_modified
    else:
        entry["failure_count"] = int(entry.get("failure_count", 0)) + 1
        entry["last_failure_at"] = now_utc.isoformat()
        entry["last_error"] = error_msg[:240]
        if entry["failure_count"] >= MAX_CONSECUTIVE_FAILURES:
            entry["quarantined_until"] = (now_utc + timedelta(hours=QUARANTINE_HOURS)).isoformat()


def parse_rss_or_atom_xml(xml_bytes: bytes, source_meta: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse RSS 2.0 or Atom XML using Python stdlib ElementTree."""
    items: List[Dict[str, Any]] = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return items

    # RSS 2.0 <item> elements
    for item_el in root.findall(".//item"):
        title = (item_el.findtext("title") or "").strip()
        link = (item_el.findtext("link") or "").strip()
        desc = (item_el.findtext("description") or "").strip()
        pub_date = (item_el.findtext("pubDate") or item_el.findtext("{http://purl.org/dc/elements/1.1/}date") or "").strip()
        if title and link:
            items.append({
                "title": title,
                "headline_en": title,
                "summary": desc or title,
                "summary_en": desc or title,
                "link": canonicalize_url(link),
                "original_published_at": pub_date,
                "published_at": pub_date,
                "source_id": source_meta.get("source_id", ""),
                "source_name": source_meta.get("source_name", ""),
                "domain": source_meta.get("domain", ""),
                "category": source_meta.get("category", "National Affairs & Schemes"),
                "reliability_level": source_meta.get("reliability_level", "tier2_editorial"),
            })

    # Atom <entry> elements
    if not items:
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry_el in root.findall(".//atom:entry", ns) + root.findall(".//entry"):
            title = (entry_el.findtext("atom:title", default="", namespaces=ns) or entry_el.findtext("title") or "").strip()
            link_el = entry_el.find("atom:link", ns) or entry_el.find("link")
            link = (link_el.attrib.get("href", "") if link_el is not None else "").strip()
            summary = (
                entry_el.findtext("atom:summary", default="", namespaces=ns)
                or entry_el.findtext("atom:content", default="", namespaces=ns)
                or entry_el.findtext("summary")
                or ""
            ).strip()
            published = (
                entry_el.findtext("atom:published", default="", namespaces=ns)
                or entry_el.findtext("published")
                or entry_el.findtext("atom:updated", default="", namespaces=ns)
                or ""
            ).strip()
            if title and link:
                items.append({
                    "title": title,
                    "headline_en": title,
                    "summary": summary or title,
                    "summary_en": summary or title,
                    "link": canonicalize_url(link),
                    "original_published_at": published,
                    "published_at": published,
                    "source_id": source_meta.get("source_id", ""),
                    "source_name": source_meta.get("source_name", ""),
                    "domain": source_meta.get("domain", ""),
                    "category": source_meta.get("category", "National Affairs & Schemes"),
                    "reliability_level": source_meta.get("reliability_level", "tier2_editorial"),
                })
    return items


def fetch_single_source(
    source: Dict[str, Any],
    health: Dict[str, Any],
    now_utc: datetime,
    http_getter: Optional[Callable[[str, Dict[str, str], float], Tuple[int, bytes, Dict[str, str]]]] = None,
    max_retries: int = 2,
) -> List[Dict[str, Any]]:
    """Fetch a single RSS source with conditional ETag/Last-Modified, retries, and cache fallback."""
    source_id = source["source_id"]
    url = source["url"]
    h_entry = health.get(source_id, {})

    if is_feed_quarantined(h_entry, now_utc):
        logger.info("Skipping quarantined feed %s until %s", source_id, h_entry.get("quarantined_until"))
        return []

    headers = {
        "User-Agent": "AgriLearningPointBot/2.0 (+https://github.com/agrilearningpoint/daily-current-affairs)",
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
    }
    if h_entry.get("etag"):
        headers["If-None-Match"] = h_entry["etag"]
    if h_entry.get("last_modified"):
        headers["If-Modified-Since"] = h_entry["last_modified"]

    cache_file = FEED_CACHE_DIR / f"{source_id}.json"

    for attempt in range(max_retries + 1):
        try:
            if http_getter is not None:
                status, body, resp_headers = http_getter(url, headers, REQUEST_TIMEOUT)
            else:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                    status = resp.status
                    body = resp.read()
                    resp_headers = {k.lower(): v for k, v in resp.headers.items()}

            if status == 304 and cache_file.is_file():
                record_feed_result(health, source_id, True, now_utc)
                return safe_read_json(cache_file, [])

            if 200 <= status < 300:
                parsed_items = parse_rss_or_atom_xml(body, source)
                record_feed_result(
                    health,
                    source_id,
                    True,
                    now_utc,
                    etag=resp_headers.get("etag"),
                    last_modified=resp_headers.get("last-modified"),
                )
                atomic_write_json(cache_file, parsed_items)
                return parsed_items

            raise RuntimeError(f"HTTP {status}")
        except urllib.error.HTTPError as exc:
            if exc.code == 304 and cache_file.is_file():
                record_feed_result(health, source_id, True, now_utc)
                return safe_read_json(cache_file, [])
            err_str = f"HTTPError {exc.code}: {exc.reason}"
        except Exception as exc:
            err_str = f"{type(exc).__name__}: {exc}"

        if attempt < max_retries:
            time.sleep(0.05 * (2 ** attempt))
        else:
            record_feed_result(health, source_id, False, now_utc, error_msg=err_str)

    return []


def collect_all_sources(
    edition_date: Optional[str] = None,
    sources: Optional[List[Dict[str, Any]]] = None,
    http_getter: Optional[Callable[[str, Dict[str, str], float], Tuple[int, bytes, Dict[str, str]]]] = None,
    now_utc: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Concurrent RSS-first collection + strict 24h IST window filtering."""
    now_utc = now_utc or datetime.now(timezone.utc)
    active_sources = sources if sources is not None else load_configured_sources()
    health = safe_read_json(FEED_HEALTH_JSON, {})
    window = compute_edition_window(edition_date)

    raw_items: List[Dict[str, Any]] = []
    # Sequential when custom http_getter is used in unit tests to keep health state deterministic,
    # or ThreadPoolExecutor in production
    if http_getter is not None:
        for src in active_sources:
            raw_items.extend(fetch_single_source(src, health, now_utc, http_getter=http_getter))
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            futs = {pool.submit(fetch_single_source, src, health, now_utc): src for src in active_sources}
            for fut in concurrent.futures.as_completed(futs):
                try:
                    raw_items.extend(fut.result())
                except Exception as exc:
                    logger.warning("Worker exception: %s", exc)

    atomic_write_json(FEED_HEALTH_JSON, health)

    accepted, rejected, quarantined = filter_articles_by_window(raw_items, window)
    return {
        "edition_date": window.edition_date,
        "window_label": window.label,
        "window_start": window.start_ist.isoformat(),
        "window_end": window.end_ist.isoformat(),
        "raw_fetched_count": len(raw_items),
        "accepted_count": len(accepted),
        "rejected_outside_window_count": len(rejected),
        "quarantined_missing_timestamp_count": len(quarantined),
        "items": accepted,
        "rejected": rejected,
        "quarantined": quarantined,
    }
