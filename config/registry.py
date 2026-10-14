# -*- coding: utf-8 -*-
"""
Canonical Source Registry
==========================
Single source of truth for all news sources.

Unifies:
    config/sources.py   → ALL_SOURCES, LEVEL_0_CORE, etc.
    config/feeds.py     → VERIFIED_RSS, etc.
    config/news_sources.json → if present

Canonical schema per source:
    {
        "id": "pib_gov",
        "name": "PIB",
        "url": "https://pib.gov.in/...",
        "category": "Government",
        "tier": "1",
        "priority": 1,
        "language": "en",
        "enabled": True,
        "verification": "strict",
    }

Public API:
    get_all_sources(include_disabled=False) -> list[dict]
    get_feed_urls() -> list[str]
    reload_registry() -> None

Backward-compat:
    RSS_FEEDS, FEEDS, SOURCES — auto-populated flat URL lists

Usage:
    from config.registry import get_feed_urls
    urls = get_feed_urls()
"""
from __future__ import annotations

import importlib.util
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("config.registry")

REPO_ROOT = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------- #
# Loader
# --------------------------------------------------------------------------- #
def _load_module_attr(module_path: str, attr_names: List[str]) -> Optional[Any]:
    """Try to load first available attribute from a Python module."""
    p = REPO_ROOT / module_path
    if not p.exists():
        return None
    try:
        spec = importlib.util.spec_from_file_location(f"_cfg_{p.stem}", str(p))
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for attr in attr_names:
            val = getattr(mod, attr, None)
            if val is not None:
                logger.debug("[registry] loaded %s.%s", module_path, attr)
                return val
    except Exception as exc:
        logger.warning("[registry] failed to load %s: %s", module_path, exc)
    return None


def _normalize_entry(entry: Any, default_category: str = "General") -> Optional[Dict[str, Any]]:
    """Normalize string/dict/tuple entry → canonical dict."""
    if isinstance(entry, str):
        url = entry.strip()
        if not url:
            return None
        name = url.split("/")[2] if "//" in url and "/" in url[8:] else url[:40]
        return {
            "id": url,
            "name": name,
            "url": url,
            "category": default_category,
            "tier": "2",
            "priority": 5,
            "language": "en",
            "enabled": True,
            "verification": "normal",
        }
    if isinstance(entry, dict):
        url = entry.get("url") or entry.get("feed_url") or entry.get("link") or ""
        if not url:
            return None
        name = entry.get("name") or (url.split("/")[2] if "//" in url else url[:40])
        return {
            "id": str(entry.get("id") or url),
            "name": str(name),
            "url": str(url),
            "category": str(entry.get("category", default_category)),
            "tier": str(entry.get("tier", entry.get("authority", "2"))),
            "priority": int(entry.get("priority", 5)),
            "language": str(entry.get("language", "en")),
            "enabled": bool(entry.get("enabled", True)),
            "verification": str(entry.get("verification", "normal")),
        }
    if isinstance(entry, (list, tuple)) and len(entry) >= 2:
        a, b = entry[0], entry[1]
        if isinstance(a, str) and isinstance(b, str):
            if a.startswith("http"):
                url, name = a, b
            else:
                name, url = a, b
            return _normalize_entry({"name": name, "url": url})
    return None


# --------------------------------------------------------------------------- #
# Collection
# --------------------------------------------------------------------------- #
def _collect_sources() -> List[Dict[str, Any]]:
    """Collect + normalize + dedupe sources from all config files."""
    raw: List[Any] = []

    # 1. config/sources.py
    sources_data = _load_module_attr(
        "config/sources.py",
        ["ALL_SOURCES", "RSS_FEEDS", "FEEDS", "SOURCES",
         "LEVEL_0_CORE", "LEVEL_1_CORE", "REGISTRY", "SOURCES_REGISTRY"],
    )
    if isinstance(sources_data, dict):
        raw.extend(list(sources_data.values()))
    elif isinstance(sources_data, (list, tuple)):
        raw.extend(sources_data)

    # 2. config/feeds.py
    feeds_data = _load_module_attr(
        "config/feeds.py",
        ["VERIFIED_RSS", "RSS_FEEDS", "FEEDS", "VERIFIED_FEEDS"],
    )
    if isinstance(feeds_data, (list, tuple)):
        raw.extend(feeds_data)
    elif isinstance(feeds_data, dict):
        raw.extend(list(feeds_data.values()))

    # 3. config/news_sources.json
    json_path = REPO_ROOT / "config" / "news_sources.json"
    if json_path.exists():
        try:
            import json
            data = json.loads(json_path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "rss_feeds" in data:
                raw.extend(data["rss_feeds"])
            elif isinstance(data, list):
                raw.extend(data)
        except Exception as exc:
            logger.warning("[registry] news_sources.json read failed: %s", exc)

    # Normalize + dedupe by URL
    seen: Dict[str, Dict[str, Any]] = {}
    for entry in raw:
        norm = _normalize_entry(entry)
        if not norm:
            continue
        if norm["url"] in seen:
            continue
        seen[norm["url"]] = norm

    sources = list(seen.values())
    logger.info("[registry] collected %d unique sources", len(sources))
    return sources


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
_CACHE: Optional[List[Dict[str, Any]]] = None


def get_all_sources(include_disabled: bool = False) -> List[Dict[str, Any]]:
    """Return all sources (canonical schema)."""
    global _CACHE
    if _CACHE is None:
        _CACHE = _collect_sources()
    if include_disabled:
        return list(_CACHE)
    return [s for s in _CACHE if s.get("enabled", True)]


def get_feed_urls() -> List[str]:
    """Flat list of URLs."""
    return [s["url"] for s in get_all_sources()]


def reload_registry() -> None:
    """Clear cache — for tests."""
    global _CACHE
    _CACHE = None


# --------------------------------------------------------------------------- #
# Backward-compat aliases
# --------------------------------------------------------------------------- #
RSS_FEEDS: List[str] = []
FEEDS: List[str] = []
SOURCES: List[str] = []


def _populate_aliases() -> None:
    global RSS_FEEDS, FEEDS, SOURCES
    urls = get_feed_urls()
    RSS_FEEDS = urls
    FEEDS = urls
    SOURCES = urls


try:
    _populate_aliases()
except Exception as exc:
    logger.warning("[registry] alias population failed: %s", exc)


# --------------------------------------------------------------------------- #
# Smoke test
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sources = get_all_sources()
    print(f"Total enabled sources: {len(sources)}")
    print()
    for s in sources[:10]:
        print(f"  [{s['tier']}] {s['name']:30s} {s['category']:20s} {s['url'][:60]}")
    print()
    print(f"URLs (flat): {len(get_feed_urls())}")
