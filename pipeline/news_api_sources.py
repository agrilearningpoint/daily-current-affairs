# -*- coding: utf-8 -*-
"""Keyed news APIs as extra India sources for the collection stage (01_source_fetch).

GNews v4 (GNEWS_API_KEY) and NewsData.io (NEWSDATA_API_KEY) top up the RSS
registry. They are OFF when their key is missing (or ALP_NEWS_APIS=0), use a
small per-run request budget well inside the free quotas, keep the shared
edition window (items outside [window_start, window_end] are dropped), and are
de-duplicated against the RSS items by link and by normalised title.

Free limits (2026-11): GNews 100 requests/day x 10 articles; NewsData 200
credits/day x 10 articles. Default budgets per collection run: GNews 4,
NewsData 3 (ALP_GNEWS_MAX_CALLS / ALP_NEWSDATA_MAX_CALLS), so even the daily
run plus every backup cron stays far below both quotas.

Items are tagged as aggregator discovery (source_tier "tier3", source_level 5,
category "aggregator") so verification (stage 04) re-derives the category and
still requires corroboration before anything is published.
"""
from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from pipeline import discovery_api as api

logger = logging.getLogger(__name__)

# (endpoint, query, category) — one request each, in priority order.
GNEWS_REQUESTS = (
    ("top-headlines", "", "nation"),
    ("top-headlines", "", "business"),
    ("search", "agriculture OR farmers OR monsoon OR ICAR", ""),
    ("top-headlines", "", "science"),
)
# (query, category) — one credit each.
NEWSDATA_REQUESTS = (
    ("", "top,politics,business"),
    ("agriculture OR farmers OR crop", ""),
    ("", "science,environment,health"),
)


def enabled() -> bool:
    return os.getenv("ALP_NEWS_APIS", "1") == "1" and os.getenv("ALP_DISABLE_NETWORK", "0") != "1"


def _parse_time(value: Any) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None
    text = text.replace("Z", "+00:00")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", text):
        text = text.replace(" ", "T") + "+00:00"  # NewsData pubDate is UTC
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def title_key(title: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9\u0900-\u097f ]", " ", (title or "").lower()).split())


def _gnews_items(window_start: datetime, window_end: datetime) -> List[Dict[str, Any]]:
    items = []
    for endpoint, query, category in GNEWS_REQUESTS:
        if not api.GNEWS.enabled():
            break
        for a in api.gnews_articles(endpoint=endpoint, query=query, category=category,
                                    date_from=_iso_z(window_start), date_to=_iso_z(window_end)):
            source = a.get("source") or {}
            items.append({
                "title": a.get("title") or "", "link": a.get("url") or "",
                "summary": a.get("description") or "", "published": a.get("publishedAt"),
                "image_url": a.get("image") or "", "source_name": source.get("name") or "GNews",
                "publisher_url": source.get("url") or "", "api": "gnews",
                "api_query": category or query,
            })
    return items


def _newsdata_items() -> List[Dict[str, Any]]:
    items = []
    for query, category in NEWSDATA_REQUESTS:
        if not api.NEWSDATA.enabled():
            break
        for a in api.newsdata_latest(query=query, category=category):
            if a.get("duplicate") is True:
                continue
            items.append({
                "title": a.get("title") or "", "link": a.get("link") or "",
                "summary": a.get("description") or "", "published": a.get("pubDate"),
                "image_url": a.get("image_url") or "", "source_name": a.get("source_name") or a.get("source_id") or "NewsData",
                "publisher_url": a.get("source_url") or "", "api": "newsdata",
                "api_query": category or query,
            })
    return items


def collect(window_start: datetime, window_end: datetime, *,
            seen_hashes: set, seen_titles: set,
            validate_title: Callable[[str, str], tuple],
            clean_url: Callable[[str], str],
            content_hash: Callable[[str, str], str],
            clean_summary: Callable[[str], str]) -> Dict[str, Any]:
    """Fetch API items inside the window and normalise them to the raw-article schema.

    `seen_hashes` / `seen_titles` are the RSS items already collected; both are
    updated in place. Returns {"articles": [...], "report": {...}}; never raises."""
    report: Dict[str, Any] = {"enabled": enabled(), "fetched": 0, "kept": 0,
                              "out_of_window": 0, "duplicates": 0, "invalid": 0}
    if not enabled() or not (api.GNEWS.enabled() or api.NEWSDATA.enabled()):
        report["services"] = api.services_status()
        return {"articles": [], "report": report}
    raw: List[Dict[str, Any]] = []
    for fetch in (lambda: _gnews_items(window_start, window_end), _newsdata_items):
        try:
            raw.extend(fetch())
        except Exception as exc:  # never fail collection because of an extra source
            logger.warning("[news_apis] source failed: %s", type(exc).__name__)
    report["fetched"] = len(raw)
    cap = int(os.getenv("ALP_NEWS_API_MAX_ITEMS", "60") or 60)
    articles: List[Dict[str, Any]] = []
    now = datetime.now(timezone.utc).isoformat()
    for item in raw:
        if len(articles) >= cap:
            break
        title, ok = validate_title(item["title"], item["source_name"])
        link = clean_url(str(item["link"]).strip())
        if not ok or not link.lower().startswith(("http://", "https://")):
            report["invalid"] += 1
            continue
        published = _parse_time(item["published"])
        if published is None or not (window_start <= published <= window_end):
            report["out_of_window"] += 1
            continue
        h = content_hash(title, link)
        tkey = title_key(title)
        if h in seen_hashes or tkey in seen_titles:
            report["duplicates"] += 1
            continue
        seen_hashes.add(h)
        seen_titles.add(tkey)
        articles.append({
            "title": title,
            "link": link,
            "summary": clean_summary(str(item["summary"] or ""))[:2000],
            "published": published.isoformat(),
            "source_feed": f"api:{item['api']}",
            "source_name": str(item["source_name"])[:80],
            "source_id": f"api_{item['api']}",
            "source_tier": "tier3",
            "source_level": 5,
            "publisher_url": item["publisher_url"] or link,
            "official": False,
            "category": "aggregator",
            "language": "en",
            "collected_at": now,
            "content_hash": h,
            "image_url": item["image_url"] if str(item["image_url"]).startswith("https://") else "",
            "date_source": "api",
            "discovered_via": item["api"],
        })
    report["kept"] = len(articles)
    report["services"] = {k: v for k, v in api.services_status().items() if k in ("gnews", "newsdata")}
    return {"articles": articles, "report": report}
