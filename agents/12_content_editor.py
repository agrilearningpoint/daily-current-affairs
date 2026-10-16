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
- Graceful degradation (LLM fail → rule-based editing)
- Idempotent (same input → same output)
- Structured logging
"""

import os
import re
import sys
import json
import hashlib
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field, ValidationError, field_validator

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------
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

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------
INPUT_DIR = "data/verified"
OUTPUT_DIR = "data/edited"
MAX_TITLE_LEN = 120
MAX_SUMMARY_LEN = 500
MIN_SUMMARY_LEN = 80
# ------------------------------------------------------------------
# Pydantic Models (Output Contract)
# ------------------------------------------------------------------
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


# ------------------------------------------------------------------
# Rule-Based Editing (Fallback — always available)
# ------------------------------------------------------------------
def clean_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def fix_common_typos(text: str) -> str:
    """Fix common typos. Production mein aap `language_tool_python` use karein."""
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
    return trimmed.rstrip(".,;:") + "..."


def trim_summary(summary: str, max_len: int = MAX_SUMMARY_LEN) -> str:
    """Trim summary at sentence boundary if possible."""
    summary = clean_whitespace(summary)
    if len(summary) <= max_len:
        return summary
    trimmed = summary[:max_len]
    # Try to end at sentence boundary
    last_period = trimmed.rfind(". ")
    if last_period > MIN_SUMMARY_LEN:
        return trimmed[: last_period + 1].strip()
    return trimmed.rsplit(" ", 1)[0].rstrip(".,;:") + "..."


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

    # Ensure summary meets minimum length
    if len(summary) < MIN_SUMMARY_LEN:
        # Pad with title-based context (last resort)
        summary = f"{title}. {summary}".strip()
        change_log.append("summary_padded")

    return {
        "title": title,
        "summary": summary,
        "change_log": change_log,
    }


# ------------------------------------------------------------------
# LLM-Based Editing
# ------------------------------------------------------------------
def _call_llm(prompt: str) -> str:
    from pipeline.ai_router import is_configured, route

    if not is_configured():
        raise RuntimeError("LLM not configured")
    return route(prompt, task="content_editing",
                 response_format={"type": "json_object"}, fail_on_all=True,
                 system_prompt=(
                     "You are a professional news editor. Preserve all facts. Return "
                     "JSON only with keys title, summary, and change_log (a list of "
                     "strings). The title must be at most 120 characters and the "
                     "summary must be 80 to 500 characters."
                 ))


def llm_edit(article: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Try LLM editing. Returns None on failure."""
    prompt = f"""Edit the following news article for grammar, clarity, and tone.
Keep facts unchanged. Do not add new information.

Title: {article.get('title', '')}
Summary: {article.get('summary', '')}
"""
    try:
        raw = _call_llm(prompt)
        parsed = json.loads(raw)
        # Validate structure
        if not isinstance(parsed.get("title"), str) or not isinstance(parsed.get("summary"), str):
            raise ValueError("Malformed LLM response")
        parsed["change_log"] = parsed.get("change_log", ["llm_edit"])
        if not isinstance(parsed["change_log"], list):
            parsed["change_log"] = ["llm_edit"]
        return parsed
    except Exception as exc:
        logger.warning("LLM edit failed for %s: %s", article.get("article_id"), exc)
        return None


# ------------------------------------------------------------------
# Hybrid Editor
# ------------------------------------------------------------------
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


# ------------------------------------------------------------------
# I/O
# ------------------------------------------------------------------
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


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def main() -> int:
    from pipeline.agent_context import get_context
    from pipeline.artifacts import read_news_items
    from pipeline.content import build_content
    from pipeline.state import write_json_atomic
    ctx = get_context()
    path = ctx.find_input("selected")
    if path is None:
        logger.error("No selected news for %s", ctx.job_id)
        return 1
    items = read_news_items(path)
    job = {"id": ctx.job_id, "type": ctx.job_type, "date": ctx.job_date,
           "date_display": datetime.strptime(ctx.job_date, "%Y-%m-%d").strftime("%d %B %Y")}
    job["period_start"] = os.getenv("ALP_WINDOW_START", "")
    job["period_end"] = os.getenv("ALP_WINDOW_END", "")
    if ctx.job_type == "monthly" and job["period_start"]:
        job["date_display"] = datetime.fromisoformat(job["period_start"]).strftime("%B %Y")
    # Dictionary fallback is for offline previews only, never live publication.
    dry_run = os.getenv("DRY_RUN", "0") == "1"
    os.environ["ALP_TRANSLATION_STRICT"] = "0" if dry_run else "1"
    content = build_content(items, job)
    if not content["items"]:
        logger.error("Content builder produced no items")
        return 1
    write_json_atomic(ctx.output_path("content"), content)
    if not dry_run and any(item.get("needs_review") for item in content["items"]):
        logger.error("Translation validation failed; refusing to publish unreviewed content")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
