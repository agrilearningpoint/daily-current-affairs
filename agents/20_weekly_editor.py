"""
Weekly Editor Module
--------------------
Yeh module 7 din ke daily edited articles ko aggregate karke ek weekly digest banata hai.

Production features:
- Robust date range resolution (UTC, ISO week)
- Deduplication by article_id / link
- Chunked LLM calls (token-safe)
- Fallback: rule-based digest if LLM unavailable
- Graceful handling of empty/missing days
- Ranking by confidence + recency + source diversity
- Pydantic output validation
"""

import os
import re
import sys
import json
import math
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple

import requests
from pydantic import BaseModel, Field, field_validator
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
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/weekly_editor.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------
INPUT_DIR = "data/edited"
OUTPUT_DIR = "data/weekly"
LOOKBACK_DAYS = 7
MAX_ARTICLES_IN_DIGEST = 25
LLM_CHUNK_SIZE = 10  # articles per LLM call
LLM_API_URL = os.getenv("LLM_API_URL", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_TIMEOUT = 90
MAX_LLM_RETRIES = 3


# ------------------------------------------------------------------
# Pydantic Models
# ------------------------------------------------------------------
class DigestSection(BaseModel):
    heading: str = Field(..., min_length=3, max_length=120)
    content: str = Field(..., min_length=20)
    article_ids: List[str] = Field(default_factory=list)


class WeeklyDigest(BaseModel):
    week_start: str
    week_end: str
    generated_at: str
    total_articles: int
    sections: List[DigestSection]
    editor_method: str  # "llm" | "rule_based" | "hybrid"
    summary_stats: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("week_start", "week_end", "generated_at")
    @classmethod
    def iso_format(cls, v: str) -> str:
        try:
            datetime.fromisoformat(v)
        except ValueError:
            raise ValueError(f"Invalid ISO date: {v}")
        return v


# ------------------------------------------------------------------
# Date Utilities
# ------------------------------------------------------------------
def resolve_week_range(reference: Optional[datetime] = None) -> Tuple[datetime, datetime]:
    """
    Return (start, end) for the 7-day window ending at `reference`.
    Both UTC-aware, start inclusive, end exclusive.
    """
    ref = reference or datetime.now(timezone.utc)
    end = ref.replace(hour=0, minute=0, second=0, microsecond=0)
    start = end - timedelta(days=LOOKBACK_DAYS)
    return start, end


def parse_iso_safe(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


# ------------------------------------------------------------------
# Loading & Filtering
# ------------------------------------------------------------------
def load_edited_articles(input_dir: str, start: datetime, end: datetime) -> List[Dict[str, Any]]:
    """
    Load all edited_*.json files, filter articles by edited_at within [start, end).
    Missing/invalid files are skipped with warning (not fatal).
    """
    if not os.path.isdir(input_dir):
        logger.error("Input directory not found: %s", input_dir)
        return []

    collected: List[Dict[str, Any]] = []
    files = sorted(f for f in os.listdir(input_dir) if f.startswith("edited_") and f.endswith(".json"))
    logger.info("Found %d edited files in %s", len(files), input_dir)

    for fname in files:
        fpath = os.path.join(input_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                logger.warning("Skipping %s: not a list", fname)
                continue
            for article in data:
                edited_at = parse_iso_safe(article.get("edited_at", ""))
                if edited_at is None:
                    logger.debug("Skipping article with invalid edited_at in %s", fname)
                    continue
                if start <= edited_at < end:
                    collected.append(article)
        except json.JSONDecodeError as exc:
            logger.warning("Corrupt JSON in %s: %s", fname, exc)
        except Exception as exc:
            logger.exception("Failed to read %s: %s", fname, exc)

    logger.info("Collected %d articles within week range.", len(collected))
    return collected


def deduplicate_articles(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicate by article_id, keeping the highest confidence version.
    Falls back to link-based dedup if article_id missing.
    """
    seen: Dict[str, Dict[str, Any]] = {}
    for art in articles:
        key = art.get("article_id") or art.get("link", "")
        if not key:
            continue
        existing = seen.get(key)
        if existing is None or art.get("confidence_score", 0) > existing.get("confidence_score", 0):
            seen[key] = art
    deduped = list(seen.values())
    logger.info("After dedup: %d articles (%d removed).", len(deduped), len(articles) - len(deduped))
    return deduped


# ------------------------------------------------------------------
# Ranking
# ------------------------------------------------------------------
def rank_articles(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Rank by weighted score: confidence (0.5) + recency (0.3) + source diversity (0.2).
    """
    if not articles:
        return []

    now = datetime.now(timezone.utc)
    source_counts: Dict[str, int] = {}
    for art in articles:
        src = art.get("source_feed", "unknown")
        source_counts[src] = source_counts.get(src, 0) + 1

    total = len(articles)
    scored: List[Tuple[float, Dict[str, Any]]] = []
    for art in articles:
        conf = float(art.get("confidence_score", 0.0))
        edited_at = parse_iso_safe(art.get("edited_at", ""))
        if edited_at:
            age_days = (now - edited_at).total_seconds() / 86400
            recency = max(0.0, 1.0 - age_days / LOOKBACK_DAYS)
        else:
            recency = 0.0
        src = art.get("source_feed", "unknown")
        diversity = 1.0 - (source_counts.get(src, 1) / max(total, 1))
        score = 0.5 * conf + 0.3 * recency + 0.2 * diversity
        scored.append((score, art))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [art for _, art in scored[:MAX_ARTICLES_IN_DIGEST]]


# ------------------------------------------------------------------
# Rule-Based Digest (Fallback — always works)
# ------------------------------------------------------------------
def group_by_source(articles: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for art in articles:
        src = art.get("source_feed", "General")
        groups.setdefault(src, []).append(art)
    return groups


def rule_based_digest(
    articles: List[Dict[str, Any]],
    start: datetime,
    end: datetime,
) -> WeeklyDigest:
    groups = group_by_source(articles)
    sections: List[DigestSection] = []

    for source, arts in groups.items():
        bullets = []
        ids = []
        for a in arts:
            title = a.get("title", "").strip()
            summary = a.get("summary", "").strip()
            if not title:
                continue
            bullets.append(f"• {title} — {summary[:200]}")
            ids.append(a.get("article_id", ""))
        if bullets:
            sections.append(DigestSection(
                heading=f"Top stories from {source}",
                content="\n".join(bullets),
                article_ids=ids,
            ))

    if not sections:
        sections = [DigestSection(
            heading="No significant stories this week",
            content="No verified articles were available for the selected week.",
            article_ids=[],
        )]

    return WeeklyDigest(
        week_start=start.isoformat(),
        week_end=end.isoformat(),
        generated_at=datetime.now(timezone.utc).isoformat(),
        total_articles=len(articles),
        sections=sections,
        editor_method="rule_based",
        summary_stats=_build_stats(articles),
    )


def _build_stats(articles: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not articles:
        return {"sources": 0, "avg_confidence": 0.0}
    sources = {a.get("source_feed", "unknown") for a in articles}
    avg_conf = sum(float(a.get("confidence_score", 0)) for a in articles) / len(articles)
    return {
        "sources": len(sources),
        "avg_confidence": round(avg_conf, 3),
        "top_sources": sorted(sources)[:5],
    }


# ------------------------------------------------------------------
# LLM Digest (with chunking)
# ------------------------------------------------------------------
@retry(
    stop=stop_after_attempt(MAX_LLM_RETRIES),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    retry=retry_if_exception_type(requests.RequestException),
    reraise=True,
)
def _call_llm(prompt: str) -> str:
    if not LLM_API_URL or not LLM_API_KEY:
        raise RuntimeError("LLM not configured")
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a senior news editor creating a weekly digest. "
                    "Return JSON only with key 'sections': list of "
                    "{heading: string, content: string, article_ids: list}. "
                    "Group related stories; keep content concise and factual."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
    }
    response = requests.post(LLM_API_URL, headers=headers, json=payload, timeout=LLM_TIMEOUT)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def _chunk(items: List[Any], size: int) -> List[List[Any]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def llm_digest_sections(articles: List[Dict[str, Any]]) -> Optional[List[DigestSection]]:
    """Try LLM digest in chunks. Returns None on failure."""
    if not articles:
        return None
    try:
        all_sections: List[DigestSection] = []
        for chunk in _chunk(articles, LLM_CHUNK_SIZE):
            payload = {
                "articles": [
                    {
                        "id": a.get("article_id", ""),
                        "title": a.get("title", ""),
                        "summary": a.get("summary", ""),
                        "source": a.get("source_feed", ""),
                    }
                    for a in chunk
                ]
            }
            raw = _call_llm(json.dumps(payload, ensure_ascii=False))
            parsed = json.loads(raw)
            for sec in parsed.get("sections", []):
                if not isinstance(sec, dict):
                    continue
                heading = str(sec.get("heading", "")).strip()
                content = str(sec.get("content", "")).strip()
                ids = sec.get("article_ids", []) or []
                if heading and content and isinstance(ids, list):
                    all_sections.append(DigestSection(
                        heading=heading[:120],
                        content=content,
                        article_ids=[str(i) for i in ids],
                    ))
        return all_sections or None
    except Exception as exc:
        logger.warning("LLM digest failed: %s", exc)
        return None


# ------------------------------------------------------------------
# Hybrid Digest Builder
# ------------------------------------------------------------------
def build_weekly_digest(
    articles: List[Dict[str, Any]],
    start: datetime,
    end: datetime,
) -> WeeklyDigest:
    fallback = rule_based_digest(articles, start, end)

    if not (LLM_API_URL and LLM_API_KEY):
        logger.info("LLM not configured; using rule-based digest.")
        return fallback

    llm_sections = llm_digest_sections(articles)
    if not llm_sections:
        logger.warning("LLM unavailable; falling back to rule-based digest.")
        return fallback

    return WeeklyDigest(
        week_start=start.isoformat(),
        week_end=end.isoformat(),
        generated_at=datetime.now(timezone.utc).isoformat(),
        total_articles=len(articles),
        sections=llm_sections,
        editor_method="llm",
        summary_stats=_build_stats(articles),
    )


# ------------------------------------------------------------------
# I/O
# ------------------------------------------------------------------
def save_digest(digest: WeeklyDigest, output_file: str) -> None:
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(digest.model_dump(), f, ensure_ascii=False, indent=2)
    logger.info("Saved weekly digest to %s", output_file)


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def main() -> None:
    start, end = resolve_week_range()
    logger.info("Weekly window: %s → %s", start.isoformat(), end.isoformat())

    try:
        articles = load_edited_articles(INPUT_DIR, start, end)
    except Exception as exc:
        logger.exception("Failed to load edited articles: %s", exc)
        sys.exit(1)

    articles = deduplicate_articles(articles)

    if not articles:
        # Non-fatal: still emit an empty digest so downstream doesn't break
        logger.warning("No articles found for this week. Emitting empty digest.")
        empty = rule_based_digest([], start, end)
        date_str = end.strftime("%Y-%m-%d")
        save_digest(empty, os.path.join(OUTPUT_DIR, f"weekly_{date_str}.json"))
        sys.exit(0)

    ranked = rank_articles(articles)
    logger.info("Ranked %d articles for digest (top %d).", len(articles), len(ranked))

    try:
        digest = build_weekly_digest(ranked, start, end)
    except Exception as exc:
        logger.exception("Digest build failed: %s", exc)
        # Emergency fallback
        digest = rule_based_digest(ranked, start, end)

    date_str = end.strftime("%Y-%m-%d")
    output_file = os.path.join(OUTPUT_DIR, f"weekly_{date_str}.json")
    save_digest(digest, output_file)
    logger.info("Weekly editor stage completed successfully.")


if __name__ == "__main__":
    main()
