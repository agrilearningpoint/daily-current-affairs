# -*- coding: utf-8 -*-
"""
Content Editor Module
---------------------
Yeh module verified news articles ko edit karta hai:
- Grammar/spelling correction
- Readability improvement
- Tone consistency (formal, news-style)
- Length normalization (title/summary limits)
- Optional LLM-based rewriting with fallback

Production features:
- Pydantic validation (no malformed output)
- Retry with exponential backoff for LLM calls
- Graceful degradation (LLM fail -> rule-based editing)
- Idempotent (same input -> same output)
- Structured logging
"""

import os
import re
import sys
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field, ValidationError, field_validator

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/content_editor.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
INPUT_DIR = "data/verified"
OUTPUT_DIR = "data/edited"
MAX_TITLE_LEN = 120
MAX_SUMMARY_LEN = 500
MIN_SUMMARY_LEN = 80

# ---------------------------------------------------------------------------
# Pydantic Models (Output Contract)
# ---------------------------------------------------------------------------
class EditedArticle(BaseModel):
    """Structured, validated representation of an edited article."""
    article_id: str
    title: str = Field(..., min_length=5, max_length=MAX_TITLE_LEN)
    summary: str = Field(..., min_length=MIN_SUMMARY_LEN, max_length=MAX_SUMMARY_LEN)
    link: str
    source_feed: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    edited_at: str
    editor_method: str  # "llm" | "rule_based" | "hybrid"
    change_log: List[str] = Field(default_factory=list)

    @field_validator("title", "summary")
    @classmethod
    def no_double_spaces(cls, v: str) -> str:
        return re.sub(r"\s+", " ", v).strip()

    @field_validator("link")
    @classmethod
    def valid_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError(f"Invalid URL: {v}")
        return v


# ---------------------------------------------------------------------------
# Rule-Based Editing (Fallback - always available)
# ---------------------------------------------------------------------------
def clean_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def fix_common_typos(text: str) -> str:
    """Fix common typos."""
    replacements = {
        r"\bteh\b": "the",
        r"\brecieve\b": "receive",
        r"\boccured\b": "occurred",
        r"\bseperate\b": "separate",
        r"\bdefinately\b": "definitely",
        r"\bgoverment\b": "government",
        r"\boccassion\b": "occasion",
        r"\bwich\b": "which",
    }
    for pattern, repl in replacements.items():
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
    return text


def trim_title(title: str, max_len: int = MAX_TITLE_LEN) -> str:
    """Trim title at word boundary."""
    title = clean_whitespace(title)
    if len(title) <= max_len:
        return title
    trimmed = title[:max_len].rsplit(" ", 1)[0]
    return trimmed.rstrip(".,;:;") + "..."


def trim_summary(summary: str, max_len: int = MAX_SUMMARY_LEN) -> str:
    """Trim summary at sentence boundary if possible."""
    summary = clean_whitespace(summary)
    if len(summary) <= max_len:
        return summary
    trimmed = summary[:max_len]
    last_period = trimmed.rfind(". ")
    if last_period > MIN_SUMMARY_LEN:
        return trimmed[: last_period + 1].strip()
    return trimmed.rsplit(" ", 1)[0].rstrip(".,;:;") + "..."


def rule_based_edit(article: Dict[str, Any]) -> Dict[str, Any]:
    """Apply rule-based editing. Always succeeds."""
    change_log: List[str] = []

    original_title = article.get("title", "")
    original_summary = article.get("summary", "")

    title = fix_common_typos(clean_whitespace(original_title))
    if title != original_title:
        change_log.append("typo_fix_title")

    trimmed_title = trim_title(title)
    if trimmed_title != title:
        change_log.append("title_trimmed")
    title = trimmed_title

    summary = fix_common_typos(clean_whitespace(original_summary))
    if summary != original_summary:
        change_log.append("typo_fix_summary")

    trimmed_summary = trim_summary(summary)
    if trimmed_summary != summary:
        change_log.append("summary_trimmed")
    summary = trimmed_summary

    return {
        "title": title,
        "summary": summary,
        "change_log": change_log,
    }


# ---------------------------------------------------------------------------
# LLM-Based Editing (Optional)
# ---------------------------------------------------------------------------
def _build_edit_prompt(title: str, summary: str) -> str:
    return (
        "You are an editor for an Indian agriculture current affairs portal. "
        "Improve grammar, readability, and tone of this news item. "
        "Keep it factual. Do NOT add new information. Keep Indian context.\n\n"
        f"Title: {title}\n"
        f"Summary: {summary}\n\n"
        "Return ONLY a JSON object with keys 'title' and 'summary'. No markdown."
    )


def llm_edit(article: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Try to edit with LLM via ai_router."""
    try:
        from pipeline.ai_router import route
        prompt = _build_edit_prompt(article.get("title", ""), article.get("summary", ""))
        resp = route(prompt, task="edit", needs_hindi=False)
        if not resp:
            return None
        resp_clean = resp.strip()
        if resp_clean.startswith("```"):
            resp_clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", resp_clean)
        data = json.loads(resp_clean)
        if "title" in data and "summary" in data:
            return {
                "title": clean_whitespace(data["title"]),
                "summary": clean_whitespace(data["summary"]),
                "change_log": ["llm_rewrite"],
            }
    except Exception as e:
        logger.warning("LLM edit failed: %s, falling back to rule-based", e)
    return None


# ---------------------------------------------------------------------------
# Hybrid Editor
# ---------------------------------------------------------------------------
def edit_article(article: Dict[str, Any]) -> EditedArticle:
    """
    Edit a single article using hybrid approach:
    1. Try LLM (if configured)
    2. Always run rule-based cleanup on top
    3. Validate via Pydantic
    """
    method = "rule_based"
    change_log: List[str] = []

    working = dict(article)
    llm_result: Optional[Dict[str, Any]] = None

    from pipeline.ai_router import is_configured
    if is_configured():
        llm_result = llm_edit(article)

    if llm_result:
        working["title"] = llm_result["title"]
        working["summary"] = llm_result["summary"]
        change_log.extend(llm_result["change_log"])
        method = "llm"

    # Always apply rule-based cleanup as safety net
    rule_result = rule_based_edit(working)
    working["title"] = rule_result["title"]
    working["summary"] = rule_result["summary"]
    change_log.extend(rule_result["change_log"])

    if llm_result and rule_result["change_log"]:
        method = "hybrid"

    edited = EditedArticle(
        article_id=article.get("article_id") or _fallback_id(article),
        title=working["title"],
        summary=working["summary"],
        link=article.get("link", ""),
        source_feed=article.get("source_feed", ""),
        confidence_score=float(article.get("confidence_score", 0.0)),
        edited_at=datetime.utcnow().isoformat(),
        editor_method=method,
        change_log=change_log,
    )
    return edited


def _fallback_id(article: Dict[str, Any]) -> str:
    raw = f"{article.get('link', '')}|{article.get('title', '')}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _sanitize_untitled(item: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure no story carries an 'Untitled' placeholder into the PDF."""
    for field_name in ("headline_en", "title", "headline"):
        val = str(item.get(field_name) or "").strip()
        if re.search(r"\buntitled\b", val, re.IGNORECASE):
            fallback = (
                str(item.get("raw_title") or item.get("summary_en") or "Current Affairs Update")
                .split(".")[0]
                .strip()[:110]
            )
            item[field_name] = re.sub(r"(?i)\buntitled\b", "Update", fallback).strip()
    return item


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------
def load_verified_articles(input_file: str) -> List[Dict[str, Any]]:
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Expected list in {input_file}")
    return data


def save_edited_articles(articles: List[EditedArticle], output_file: str) -> None:
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump([a.model_dump() for a in articles], f, ensure_ascii=False, indent=2)
    logger.info("Saved %d edited articles to %s", len(articles), output_file)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"\'')
            if k not in os.environ:
                os.environ[k] = v
    from pipeline.agent_context import get_context
    from pipeline.artifacts import read_news_items
    from pipeline.content import build_content
    from pipeline.state import write_json_atomic
    ctx = get_context()
    path = ctx.find_input("selected")
    if path is None:
        logger.error("No selected news for %s", ctx.job_id)
        return 1

    items, reserves = read_news_items(path)
    dry_run = "--dry-run" in sys.argv
    # Honor both ALP_ALLOW_UNREVIEWED_TRANSLATION and ALP_ALLOW_FALLBACK_TRANSLATION (used in daily.yml)
    allow_fallback = (
        os.getenv("ALP_ALLOW_UNREVIEWED_TRANSLATION", "").lower() in ("1", "true", "yes")
        or os.getenv("ALP_ALLOW_FALLBACK_TRANSLATION", "").lower() in ("1", "true", "yes")
    )
    job = ctx.job_id
    content = build_content(items, job)
    if allow_fallback:
        for item in content["items"]:
            item["needs_review"] = False

    target = len(items)
    try:
        spares = max(0, int(os.getenv("ALP_CONTENT_SPARES", "5")))
    except ValueError:
        spares = 5
    strict = not dry_run and not allow_fallback

    def _clean(entries):
        return [it for it in entries if not (strict and it.get("needs_review"))]

    # Backfill: stories dropped by the builder (junk/paywall evidence) or held back
    # for unreviewed translation are replaced by the next reserve stories, and a few
    # spare stories are prepared for stage 16 (stories that get no valid MCQ).
    clean = _clean(content["items"])
    flagged = [it for it in content["items"] if strict and it.get("needs_review")]
    rounds = 0
    while reserves and len(clean) < target + spares and rounds < 5:
        need = target + spares - len(clean)
        take = need + (2 if len(clean) < target else 0)  # small margin only when short of target
        batch, reserves = reserves[:take], reserves[take:]
        extra = build_content(batch, job)
        if allow_fallback:
            for item in extra["items"]:
                item["needs_review"] = False
        for k, v in (extra.get("translation_stats") or {}).items():
            if isinstance(v, (int, float)):
                content["translation_stats"][k] = content["translation_stats"].get(k, 0) + v
        seen = {it.get("event_id") for it in clean}
        clean += [it for it in _clean(extra["items"]) if it.get("event_id") not in seen]
        flagged += [it for it in extra["items"] if strict and it.get("needs_review")]
        rounds += 1
    if rounds:
        logger.info("[Content Editor] reserve backfill: %d round(s), %d clean stories available for target %d",
                    rounds, len(clean), target)

    # Production resilience: ensure clean count reaches at least the QA story floor
    # (e.g., 13 for 15 selected) by rescuing strippable items that already have
    # complete Hindi translations (not translation_incomplete).
    qa_floor = max(1, target - max(2, -(-target // 5)) + 1)
    min_required = max(int(os.getenv("MIN_VERIFIED_COUNT", "5")), qa_floor)
    # Never un-flag a story whose Hindi was not produced by a validated AI
    # translation: in strict mode its Hindi fields still hold English, and
    # stripping the flag would publish that silently (all-providers-down case).
    seen_clean_ids = {it.get("event_id") for it in clean}
    strippable = [
        it for it in flagged
        if not it.get("translation_incomplete") and it.get("event_id") not in seen_clean_ids
    ]
    untranslated = [it for it in flagged if it.get("translation_incomplete")]
    if flagged and len(clean) < max(min_required, target):
        needed_to_fill = max(min_required, target + spares) - len(clean)
        rescued = strippable[:needed_to_fill]
        logger.warning("[Content Editor] Clean items (%d) below target/floor (%d); stripping the "
                       "provenance flag from %d item(s) with complete Hindi; %d item(s) with "
                       "untranslated Hindi stay excluded", len(clean), max(min_required, target),
                       len(rescued), len(untranslated))
        for item in rescued:
            item["needs_review"] = False
        clean = clean + rescued
    elif flagged:
        logger.warning("[Content Editor] Dropped %d unreviewed item(s); proceeding with %d verified clean items",
                       len(flagged), len(clean))

    if not clean and untranslated:
        logger.error("[Content Editor] AI translation unavailable: none of %d stories has validated "
                     "Hindi (translation_stats=%s). Failing closed - no edition with English in the "
                     "Hindi fields is produced.", len(untranslated), content.get("translation_stats"))
        return 1
    if not clean:
        logger.error("Content builder produced no items")
        return 1
    if len(clean) < target:
        logger.warning("[Content Editor] only %d/%d stories after reserve backfill", len(clean), target)

    clean = [_sanitize_untitled(it) for it in clean]
    content["items"] = clean[:target]
    content["reserve_items"] = clean[target:target + spares]
    from pipeline.content import refresh_content_summaries
    refresh_content_summaries(content)

    write_json_atomic(ctx.output_path("content"), content)
    return 0


if __name__ == "__main__":
    sys.exit(main())
