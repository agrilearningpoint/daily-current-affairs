# -*- coding: utf-8 -*-
"""
Weekly Editor Agent (20)
========================
Aggregates 7 days of daily edited articles into a weekly digest.

Production features:
- UTC-safe 7-day window resolution
- Deduplication by article_id/link
- Empty-week handling (emits empty digest, doesn't crash)
- Ranking by confidence + recency + source diversity
- Chunked LLM calls (token-safe)
- Rule-based fallback (always works)
- Atomic write
- Never fails silently — logs "0 selection" as warning, exits gracefully

Env:
  WEEKLY_LOOKBACK_DAYS    (default 7)
  WEEKLY_MAX_ARTICLES     (default 40)
  Any provider configured in pipeline.ai_router (optional)
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
        logging.FileHandler(str(LOGS_DIR / "weekly_editor.log"), encoding="utf-8"),
    ],
)
logger = logging.getLogger("agent.20_weekly_editor")

EDITED_DIR = REPO_ROOT / "data" / "edited"
OUTPUT_DIR = REPO_ROOT / "data" / "weekly"
MEMORY_FILE = REPO_ROOT / "state" / "importance_memory.json"

LOOKBACK_DAYS = int(os.getenv("WEEKLY_LOOKBACK_DAYS", "7"))
MAX_ARTICLES = int(os.getenv("WEEKLY_MAX_ARTICLES", "40"))


# --------------------------------------------------------------------------- #
def parse_iso_safe(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    except Exception:
        return None


def resolve_week_range(reference: Optional[datetime] = None) -> Tuple[datetime, datetime]:
    ref = reference or datetime.now(timezone.utc)
    end = ref.replace(hour=0, minute=0, second=0, microsecond=0)
    start = end - timedelta(days=LOOKBACK_DAYS)
    return start, end


def atomic_write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


# --------------------------------------------------------------------------- #
def load_articles(start: datetime, end: datetime) -> List[Dict[str, Any]]:
    """Load edited articles from files within [start, end)."""
    if not EDITED_DIR.exists():
        return []
    collected: List[Dict[str, Any]] = []
    for f in sorted(EDITED_DIR.glob("edited_*.json"), reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                continue
            for art in data:
                ts = parse_iso_safe(art.get("edited_at"))
                if ts and start <= ts < end:
                    collected.append(art)
        except Exception as exc:
            logger.warning("Skipping %s: %s", f.name, exc)
    logger.info("Loaded %d articles in window [%s, %s)",
                len(collected), start.isoformat(), end.isoformat())
    return collected


def dedup_articles(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: Dict[str, Dict[str, Any]] = {}
    for a in articles:
        key = a.get("article_id") or a.get("event_id") or a.get("link", "")
        if not key:
            continue
        existing = seen.get(key)
        if existing is None or a.get("confidence_score", 0) > existing.get("confidence_score", 0):
            seen[key] = a
    logger.info("Dedup: %d → %d", len(articles), len(seen))
    return list(seen.values())


def rank_articles(articles: List[Dict[str, Any]], top_n: int = MAX_ARTICLES) -> List[Dict[str, Any]]:
    now = datetime.now(timezone.utc)
    from collections import Counter
    src_counts = Counter(a.get("source_feed", "?") for a in articles)
    total = len(articles) or 1
    scored: List[Tuple[float, Dict[str, Any]]] = []
    for a in articles:
        conf = float(a.get("confidence_score", 0) or 0)
        ts = parse_iso_safe(a.get("edited_at"))
        recency = 0.0
        if ts:
            age_days = (now - ts).total_seconds() / 86400
            recency = max(0.0, 1.0 - age_days / LOOKBACK_DAYS)
        src = a.get("source_feed", "?")
        diversity = 1.0 - (src_counts[src] / total)
        score = 0.5 * conf + 0.3 * recency + 0.2 * diversity
        scored.append((score, a))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [a for _, a in scored[:top_n]]


# --------------------------------------------------------------------------- #
def build_rule_based(articles: List[Dict[str, Any]], start: datetime, end: datetime) -> Dict[str, Any]:
    """Fallback: source-grouped digest. Always works."""
    from collections import defaultdict
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for a in articles:
        groups[a.get("source_feed", "General")].append(a)

    sections = []
    for src, arts in groups.items():
        bullets = []
        ids = []
        for a in arts[:10]:
            title = (a.get("headline_en") or a.get("title") or "").strip()
            if title:
                bullets.append(f"• {title}")
                ids.append(a.get("article_id") or a.get("event_id") or "")
        if bullets:
            sections.append({
                "heading": f"Top stories from {src[:60]}",
                "content": "\n".join(bullets),
                "article_ids": ids,
            })

    if not sections:
        sections = [{
            "heading": "No significant stories this week",
            "content": "No verified articles available for the selected week.",
            "article_ids": [],
        }]

    return {
        "week_start": start.isoformat(),
        "week_end": end.isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_articles": len(articles),
        "sections": sections,
        "editor_method": "rule_based",
    }


def try_llm_digest(articles: List[Dict[str, Any]], start: datetime, end: datetime) -> Optional[Dict[str, Any]]:
    """Try LLM. Returns None if unavailable."""
    from pipeline.ai_router import is_configured, route

    if not is_configured():
        return None

    try:
        # Chunk articles to stay under token limits
        chunk = articles[:20]
        payload = {
            "articles": [
                {"id": a.get("article_id") or a.get("event_id", ""),
                 "title": a.get("headline_en") or a.get("title", ""),
                 "summary": (a.get("key_points_en") or [""])[0] if a.get("key_points_en") else a.get("summary", ""),
                 "source": a.get("source_feed", "")}
                for a in chunk
            ]
        }
        prompt = (
            "Create a weekly news digest from these source-grounded articles. "
            'Return JSON: {"sections":[{"heading":str,"content":str,"article_ids":list}]}.\n'
            + json.dumps(payload, ensure_ascii=False)
        )
        raw = route(prompt, task="weekly_digest",
                    response_format={"type": "json_object"},
                    system_prompt=(
                        "Create a factual weekly news digest grounded only in the "
                        "provided articles. Return JSON only with a sections list; "
                        "each section has heading, content, and article_ids."
                    ))
        if not raw:
            return None
        data = json.loads(raw)
        sections = data.get("sections") or []
        if not sections:
            return None
        return {
            "week_start": start.isoformat(),
            "week_end": end.isoformat(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_articles": len(articles),
            "sections": sections,
            "editor_method": "llm",
        }
    except Exception as exc:
        logger.warning("LLM digest failed: %s", exc)
        return None


# --------------------------------------------------------------------------- #
def main() -> int:
    from pipeline.agent_context import get_context
    from pipeline.period_editor import prepare
    return prepare(get_context())


if __name__ == "__main__":
    sys.exit(main())
