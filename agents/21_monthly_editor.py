"""
Monthly Editor Module
---------------------
Yeh module ek month ke weekly digests + daily edited articles ko aggregate karke
monthly digest banata hai.

Production features:
- Prefer weekly digests (avoid double-summarization)
- Fallback to daily edited articles if weeklies missing
- Thematic clustering via keyword extraction
- Trend analysis (top keywords, sources)
- Chunked LLM calls (token-safe)
- Rule-based fallback (always works)
- Graceful empty-month handling
- Pydantic output validation
"""

import os
import re
import sys
import json
import math
import logging
import argparse
from datetime import datetime, timedelta, timezone
from calendar import monthrange
from collections import Counter
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
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/monthly_editor.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------
WEEKLY_DIR = "data/weekly"
EDITED_DIR = "data/edited"
OUTPUT_DIR = "data/monthly"

MAX_ARTICLES_IN_DIGEST = 60
MAX_SECTIONS = 8
LLM_CHUNK_SIZE = 8
LLM_API_URL = os.getenv("LLM_API_URL", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_TIMEOUT = 120
MAX_LLM_RETRIES = 3

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "this", "that", "these", "those", "it", "its", "as", "has", "have",
    "had", "will", "would", "can", "could", "should", "may", "might",
    "also", "more", "than", "then", "over", "into", "out", "up", "down",
    "new", "says", "said", "amid", "after", "before", "during", "while",
    "india", "indian",  # generic — remove if too broad for your domain
}


# ------------------------------------------------------------------
# Pydantic Models
# ------------------------------------------------------------------
class MonthlySection(BaseModel):
    heading: str = Field(..., min_length=3, max_length=150)
    content: str = Field(..., min_length=20)
    article_ids: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class TrendSummary(BaseModel):
    top_keywords: List[str] = Field(default_factory=list)
    top_sources: List[str] = Field(default_factory=list)
    total_articles: int = 0
    avg_confidence: float = 0.0
    covered_weeks: int = 0


class MonthlyDigest(BaseModel):
    month: str  # "YYYY-MM"
    month_start: str
    month_end: str
    generated_at: str
    total_articles: int
    sections: List[MonthlySection]
    trends: TrendSummary
    editor_method: str  # "llm" | "rule_based" | "hybrid"
    source_data: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("month_start", "month_end", "generated_at")
    @classmethod
    def iso_format(cls, v: str) -> str:
        try:
            datetime.fromisoformat(v)
        except ValueError:
            raise ValueError(f"Invalid ISO date: {v}")
        return v

    @field_validator("month")
    @classmethod
    def month_format(cls, v: str) -> str:
        if not re.match(r"^\d{4}-\d{2}$", v):
            raise ValueError(f"month must be YYYY-MM, got: {v}")
        return v


# ------------------------------------------------------------------
# Date Utilities
# ------------------------------------------------------------------
def resolve_month_range(reference: Optional[datetime] = None) -> Tuple[datetime, datetime, str]:
    """
    Return (start, end, "YYYY-MM") for the month containing `reference`.
    end is exclusive (first day of next month).
    """
    ref = reference or datetime.now(timezone.utc)
    year, month = ref.year, ref.month
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    return start, end, f"{year:04d}-{month:02d}"


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
# Loading
# ------------------------------------------------------------------
def load_weekly_digests(start: datetime, end: datetime) -> List[Dict[str, Any]]:
    """Load weekly digests whose week_end falls within [start, end)."""
    if not os.path.isdir(WEEKLY_DIR):
        return []
    collected: List[Dict[str, Any]] = []
    for fname in sorted(os.listdir(WEEKLY_DIR)):
        if not (fname.startswith("weekly_") and fname.endswith(".json")):
            continue
        try:
            with open(os.path.join(WEEKLY_DIR, fname), "r", encoding="utf-8") as f:
                data = json.load(f)
            week_end = parse_iso_safe(data.get("week_end", ""))
            if week_end and start <= week_end < end:
                collected.append(data)
        except Exception as exc:
            logger.warning("Skipping %s: %s", fname, exc)
    logger.info("Loaded %d weekly digests for month.", len(collected))
    return collected


def load_edited_articles(start: datetime, end: datetime) -> List[Dict[str, Any]]:
    """Fallback: load daily edited articles within [start, end)."""
    if not os.path.isdir(EDITED_DIR):
        return []
    collected: List[Dict[str, Any]] = []
    for fname in sorted(os.listdir(EDITED_DIR)):
        if not (fname.startswith("edited_") and fname.endswith(".json")):
            continue
        try:
            with open(os.path.join(EDITED_DIR, fname), "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                continue
            for art in data:
                edited_at = parse_iso_safe(art.get("edited_at", ""))
                if edited_at and start <= edited_at < end:
                    collected.append(art)
        except Exception as exc:
            logger.warning("Skipping %s: %s", fname, exc)
    logger.info("Loaded %d edited articles for month.", len(collected))
    return collected


# ------------------------------------------------------------------
# Dedup + Ranking (reuse pattern from weekly)
# ------------------------------------------------------------------
def deduplicate_articles(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: Dict[str, Dict[str, Any]] = {}
    for art in articles:
        key = art.get("article_id") or art.get("link", "")
        if not key:
            continue
        existing = seen.get(key)
        if existing is None or art.get("confidence_score", 0) > existing.get("confidence_score", 0):
            seen[key] = art
    return list(seen.values())


def rank_articles(articles: List[Dict[str, Any]], top_n: int = MAX_ARTICLES_IN_DIGEST) -> List[Dict[str, Any]]:
    if not articles:
        return []
    now = datetime.now(timezone.utc)
    source_counts: Counter = Counter(a.get("source_feed", "unknown") for a in articles)
    total = len(articles)
    scored: List[Tuple[float, Dict[str, Any]]] = []
    for art in articles:
        conf = float(art.get("confidence_score", 0.0))
        edited_at = parse_iso_safe(art.get("edited_at", ""))
        recency = 0.0
        if edited_at:
            age_days = (now - edited_at).total_seconds() / 86400
            recency = max(0.0, 1.0 - age_days / 30)
        src = art.get("source_feed", "unknown")
        diversity = 1.0 - (source_counts.get(src, 1) / max(total, 1))
        score = 0.5 * conf + 0.3 * recency + 0.2 * diversity
        scored.append((score, art))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [a for _, a in scored[:top_n]]


# ------------------------------------------------------------------
# Trend Analysis
# ------------------------------------------------------------------
def extract_keywords(text: str, top_n: int = 20) -> List[str]:
    if not text:
        return []
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    words = [w for w in text.split() if w not in STOPWORDS and len(w) > 3]
    freq = Counter(words)
    return [w for w, _ in freq.most_common(top_n)]


def compute_trends(
    articles: List[Dict[str, Any]],
    covered_weeks: int,
) -> TrendSummary:
    if not articles:
        return TrendSummary(covered_weeks=covered_weeks)

    all_text = " ".join(
        f"{a.get('title', '')} {a.get('summary', '')}" for a in articles
    )
    top_keywords = extract_keywords(all_text, top_n=15)

    source_counter = Counter(a.get("source_feed", "unknown") for a in articles)
    top_sources = [s for s, _ in source_counter.most_common(5)]

    avg_conf = sum(float(a.get("confidence_score", 0)) for a in articles) / len(articles)

    return TrendSummary(
        top_keywords=top_keywords,
        top_sources=top_sources,
        total_articles=len(articles),
        avg_confidence=round(avg_conf, 3),
        covered_weeks=covered_weeks,
    )


def cluster_by_keyword(
    articles: List[Dict[str, Any]],
    top_keywords: List[str],
    max_clusters: int = MAX_SECTIONS,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Simple keyword-based clustering.
    Each article assigned to the first matching top-keyword cluster.
    Remaining articles go to "Other Stories".
    """
    clusters: Dict[str, List[Dict[str, Any]]] = {kw: [] for kw in top_keywords[:max_clusters]}
    other: List[Dict[str, Any]] = []

    for art in articles:
        text = f"{art.get('title', '')} {art.get('summary', '')}".lower()
        assigned = False
        for kw in clusters:
            if re.search(rf"\b{re.escape(kw)}\b", text):
                clusters[kw].append(art)
                assigned = True
                break
        if not assigned:
            other.append(art)

    # Drop empty clusters
    clusters = {k: v for k, v in clusters.items() if v}
    if other:
        clusters["Other Stories"] = other
    return clusters


# ------------------------------------------------------------------
# Rule-Based Digest (Fallback — always works)
# ------------------------------------------------------------------
def rule_based_digest(
    articles: List[Dict[str, Any]],
    weekly_digests: List[Dict[str, Any]],
    start: datetime,
    end: datetime,
    month_str: str,
) -> MonthlyDigest:
    trends = compute_trends(articles, covered_weeks=len(weekly_digests))
    clusters = cluster_by_keyword(articles, trends.top_keywords)

    sections: List[MonthlySection] = []
    for kw, arts in clusters.items():
        bullets = []
        ids = []
        for a in arts[:10]:
            title = a.get("title", "").strip()
            summary = a.get("summary", "").strip()
            if not title:
                continue
            bullets.append(f"• {title} — {summary[:180]}")
            ids.append(a.get("article_id", ""))
        if bullets:
            sections.append(MonthlySection(
                heading=kw.title(),
                content="\n".join(bullets),
                article_ids=ids,
                tags=[kw],
            ))

    if not sections:
        sections = [MonthlySection(
            heading="No significant stories this month",
            content="No verified articles were available for the selected month.",
            article_ids=[],
            tags=[],
        )]

    return MonthlyDigest(
        month=month_str,
        month_start=start.isoformat(),
        month_end=end.isoformat(),
        generated_at=datetime.now(timezone.utc).isoformat(),
        total_articles=len(articles),
        sections=sections,
        trends=trends,
        editor_method="rule_based",
        source_data={
            "weekly_digests_used": len(weekly_digests),
            "edited_articles_used": len(articles),
        },
    )


# ------------------------------------------------------------------
# LLM Digest
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
                    "You are a senior news analyst creating a monthly digest. "
                    "Return JSON only with key 'sections': list of "
                    "{heading: string, content: string, article_ids: list, tags: list}. "
                    "Group thematically. Be factual and concise. Do not invent facts."
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


def llm_digest_sections(
    articles: List[Dict[str, Any]],
    top_keywords: List[str],
) -> Optional[List[MonthlySection]]:
    """Try LLM. Chunks articles; falls back to None on failure."""
    if not articles:
        return None
    try:
        all_sections: List[MonthlySection] = []
        for chunk in _chunk(articles, LLM_CHUNK_SIZE):
            payload = {
                "theme_hints": top_keywords[:10],
                "articles": [
                    {
                        "id": a.get("article_id", ""),
                        "title": a.get("title", ""),
                        "summary": a.get("summary", ""),
                        "source": a.get("source_feed", ""),
                    }
                    for a in chunk
                ],
            }
            raw = _call_llm(json.dumps(payload, ensure_ascii=False))
            parsed = json.loads(raw)
            for sec in parsed.get("sections", []):
                if not isinstance(sec, dict):
                    continue
                heading = str(sec.get("heading", "")).strip()
                content = str(sec.get("content", "")).strip()
                ids = sec.get("article_ids", []) or []
                tags = sec.get("tags", []) or []
                if heading and content:
                    all_sections.append(MonthlySection(
                        heading=heading[:150],
                        content=content,
                        article_ids=[str(i) for i in ids if i],
                        tags=[str(t) for t in tags if t][:5],
                    ))
        return all_sections or None
    except Exception as exc:
        logger.warning("LLM monthly digest failed: %s", exc)
        return None


# ------------------------------------------------------------------
# Hybrid Builder
# ------------------------------------------------------------------
def build_monthly_digest(
    articles: List[Dict[str, Any]],
    weekly_digests: List[Dict[str, Any]],
    start: datetime,
    end: datetime,
    month_str: str,
) -> MonthlyDigest:
    fallback = rule_based_digest(articles, weekly_digests, start, end, month_str)

    if not (LLM_API_URL and LLM_API_KEY):
        logger.info("LLM not configured; using rule-based monthly digest.")
        return fallback

    trends = fallback.trends
    llm_sections = llm_digest_sections(articles, trends.top_keywords)
    if not llm_sections:
        logger.warning("LLM unavailable; falling back to rule-based monthly digest.")
        return fallback

    return MonthlyDigest(
        month=month_str,
        month_start=start.isoformat(),
        month_end=end.isoformat(),
        generated_at=datetime.now(timezone.utc).isoformat(),
        total_articles=len(articles),
        sections=llm_sections[:MAX_SECTIONS],
        trends=trends,
        editor_method="llm",
        source_data={
            "weekly_digests_used": len(weekly_digests),
            "edited_articles_used": len(articles),
        },
    )


# ------------------------------------------------------------------
# I/O
# ------------------------------------------------------------------
def save_digest(digest: MonthlyDigest, output_file: str) -> None:
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    tmp = f"{output_file}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(digest.model_dump(), f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, output_file)
    logger.info("Saved monthly digest to %s", output_file)


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Monthly digest generator")
    p.add_argument("--date", help="Reference date (YYYY-MM-DD). Default: today UTC.")
    return p.parse_args()


def main() -> int:
    from pipeline.agent_context import get_context
    from pipeline.period_editor import prepare
    return prepare(get_context())


if __name__ == "__main__":
    sys.exit(main())
