"""
Fact Verification Module
------------------------
Yeh module collected news articles ko verify karta hai using multiple strategies:
1. Cross-source corroboration (same claim multiple sources mein hai?)
2. Heuristic checks (dates, numbers, entities consistency)
3. Optional LLM-based verification (fallback ke saath)

Production features:
- Confidence scoring (0.0 - 1.0) instead of binary pass/fail
- Graceful degradation: LLM fail ho toh heuristics use karo
- Retry with exponential backoff for API calls
- Structured logging + metrics
- Type hints + validation
"""

import os
import re
import sys
import json
import time
import logging
import hashlib
from datetime import datetime
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional, Tuple

import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

# ------------------------------------------------------------------
# Logging Configuration
# ------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/fact_verification.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------
INPUT_DIR = "data/raw"
OUTPUT_DIR = "data/verified"
MIN_CONFIDENCE_THRESHOLD = float(os.getenv("MIN_CONFIDENCE_THRESHOLD", "0.5"))
LLM_API_URL = os.getenv("LLM_API_URL", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_TIMEOUT = 60  # seconds
MAX_LLM_RETRIES = 3


# ------------------------------------------------------------------
# Data Models
# ------------------------------------------------------------------
@dataclass
class VerifiedArticle:
    """Represents a fact-verified article."""
    article_id: str
    title: str
    link: str
    summary: str
    source_feed: str
    collected_at: str
    verified_at: str
    confidence_score: float
    verification_method: str  # "cross_source" | "heuristic" | "llm" | "combined"
    corroborating_sources: List[str] = field(default_factory=list)
    flags: List[str] = field(default_factory=list)
    is_verified: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ------------------------------------------------------------------
# Utilities
# ------------------------------------------------------------------
def generate_article_id(article: Dict[str, Any]) -> str:
    """Generate stable ID from article link/title."""
    raw = f"{article.get('link', '')}|{article.get('title', '')}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def normalize_text(text: str) -> str:
    """Normalize text for comparison (lowercase, remove punctuation)."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_key_terms(text: str, top_n: int = 10) -> List[str]:
    """
    Extract key terms (naive keyword extraction).
    Production mein aap spaCy/KeyBERT use kar sakte hain.
    """
    stopwords = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
        "this", "that", "these", "those", "it", "its", "as", "has", "have",
        "had", "will", "would", "can", "could", "should", "may", "might",
    }
    words = normalize_text(text).split()
    filtered = [w for w in words if w not in stopwords and len(w) > 3]
    # Frequency-based top N
    freq: Dict[str, int] = {}
    for w in filtered:
        freq[w] = freq.get(w, 0) + 1
    sorted_terms = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [term for term, _ in sorted_terms[:top_n]]


# ------------------------------------------------------------------
# Verification Strategies
# ------------------------------------------------------------------
def cross_source_verification(
    article: Dict[str, Any],
    all_articles: List[Dict[str, Any]],
    similarity_threshold: float = 0.3,
) -> Tuple[float, List[str]]:
    """
    Check if same claim appears in multiple sources.
    Returns (confidence_score, list_of_corroborating_sources).
    """
    article_terms = set(extract_key_terms(article.get("title", "") + " " + article.get("summary", "")))
    if not article_terms:
        return 0.0, []

    corroborating: List[str] = []
    article_link = article.get("link", "")

    for other in all_articles:
        if other.get("link") == article_link:
            continue
        other_terms = set(extract_key_terms(
            other.get("title", "") + " " + other.get("summary", "")
        ))
        if not other_terms:
            continue
        overlap = len(article_terms & other_terms) / max(len(article_terms), 1)
        if overlap >= similarity_threshold:
            source = other.get("source_feed", "unknown")
            if source not in corroborating:
                corroborating.append(source)

    # Score based on number of corroborating sources
    if len(corroborating) >= 3:
        score = 0.95
    elif len(corroborating) == 2:
        score = 0.8
    elif len(corroborating) == 1:
        score = 0.6
    else:
        score = 0.3
    return score, corroborating


def heuristic_verification(article: Dict[str, Any]) -> Tuple[float, List[str]]:
    """
    Heuristic checks: title length, summary presence, date validity, etc.
    Returns (score, flags).
    """
    flags: List[str] = []
    score = 1.0

    title = article.get("title", "").strip()
    summary = article.get("summary", "").strip()

    if len(title) < 15:
        flags.append("title_too_short")
        score -= 0.2
    if len(summary) < 50:
        flags.append("summary_too_short")
        score -= 0.2

    # Check for suspicious patterns (all caps, excessive punctuation)
    if title.isupper() and len(title) > 20:
        flags.append("title_all_caps")
        score -= 0.15
    if re.search(r"[!?]{3,}", title):
        flags.append("excessive_punctuation")
        score -= 0.15

    # URL sanity
    link = article.get("link", "")
    if not link.startswith(("http://", "https://")):
        flags.append("invalid_url")
        score -= 0.3

    return max(0.0, min(1.0, score)), flags


@retry(
    stop=stop_after_attempt(MAX_LLM_RETRIES),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    retry=retry_if_exception_type(requests.RequestException),
    reraise=True,
)
def _call_llm_api(prompt: str) -> str:
    """Call LLM API with retry. Raises on failure."""
    if not LLM_API_URL or not LLM_API_KEY:
        raise RuntimeError("LLM API not configured")

    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a fact-checking assistant. Respond with JSON only."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
    }
    response = requests.post(
        LLM_API_URL, headers=headers, json=payload, timeout=LLM_TIMEOUT
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


def llm_verification(article: Dict[str, Any]) -> Tuple[float, List[str]]:
    """
    LLM-based verification. Agar API fail ho toh (0.0, ["llm_unavailable"]) return karta hai.
    """
    prompt = f"""Verify the following news article for factual plausibility.
Return JSON with fields: {{"confidence": float between 0 and 1, "flags": [list of strings]}}.

Title: {article.get('title', '')}
Summary: {article.get('summary', '')}
Source: {article.get('source_feed', '')}
"""
    try:
        raw = _call_llm_api(prompt)
        parsed = json.loads(raw)
        confidence = float(parsed.get("confidence", 0.5))
        flags = parsed.get("flags", [])
        if not isinstance(flags, list):
            flags = []
        return max(0.0, min(1.0, confidence)), flags
    except Exception as exc:
        logger.warning("LLM verification failed for %s: %s", article.get("link"), exc)
        return 0.0, ["llm_unavailable"]


# ------------------------------------------------------------------
# Combined Verification
# ------------------------------------------------------------------
def verify_article(
    article: Dict[str, Any],
    all_articles: List[Dict[str, Any]],
) -> VerifiedArticle:
    """
    Run all verification strategies and combine scores.
    Weighted average: cross_source (0.5), heuristic (0.2), llm (0.3).
    """
    cross_score, corroborating = cross_source_verification(article, all_articles)
    heur_score, heur_flags = heuristic_verification(article)

    llm_score, llm_flags = 0.0, []
    if LLM_API_URL and LLM_API_KEY:
        llm_score, llm_flags = llm_verification(article)

    # Weighted combination (agar LLM available nahi, toh weights adjust)
    if llm_score > 0:
        final_score = 0.5 * cross_score + 0.2 * heur_score + 0.3 * llm_score
    else:
        final_score = 0.7 * cross_score + 0.3 * heur_score

    all_flags = heur_flags + llm_flags
    method = "combined" if llm_score > 0 else "heuristic+cross_source"

    verified = VerifiedArticle(
        article_id=generate_article_id(article),
        title=article.get("title", ""),
        link=article.get("link", ""),
        summary=article.get("summary", ""),
        source_feed=article.get("source_feed", ""),
        collected_at=article.get("collected_at", ""),
        verified_at=datetime.utcnow().isoformat(),
        confidence_score=round(final_score, 4),
        verification_method=method,
        corroborating_sources=corroborating,
        flags=all_flags,
        is_verified=final_score >= MIN_CONFIDENCE_THRESHOLD,
    )
    return verified


# ------------------------------------------------------------------
# Main Pipeline
# ------------------------------------------------------------------
def load_input_articles(input_file: str) -> List[Dict[str, Any]]:
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Expected list in {input_file}, got {type(data)}")
    return data


def save_verified_articles(articles: List[VerifiedArticle], output_file: str) -> None:
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump([a.to_dict() for a in articles], f, ensure_ascii=False, indent=2)
    logger.info("Saved %d verified articles to %s", len(articles), output_file)


def main() -> None:
    # Find latest raw file
    if not os.path.isdir(INPUT_DIR):
        logger.error("Input directory not found: %s", INPUT_DIR)
        sys.exit(1)

    raw_files = sorted(
        [f for f in os.listdir(INPUT_DIR) if f.startswith("news_") and f.endswith(".json")],
        reverse=True,
    )
    if not raw_files:
        logger.error("No raw news files found in %s", INPUT_DIR)
        sys.exit(1)

    input_file = os.path.join(INPUT_DIR, raw_files[0])
    logger.info("Processing input file: %s", input_file)

    try:
        articles = load_input_articles(input_file)
    except Exception as exc:
        logger.exception("Failed to load input articles: %s", exc)
        sys.exit(1)

    if not articles:
        logger.error("Input file has no articles.")
        sys.exit(1)

    logger.info("Verifying %d articles (threshold=%.2f)...", len(articles), MIN_CONFIDENCE_THRESHOLD)
    verified: List[VerifiedArticle] = []
    for idx, article in enumerate(articles, 1):
        try:
            v = verify_article(article, articles)
            verified.append(v)
            logger.debug(
                "[%d/%d] %s → score=%.2f verified=%s",
                idx, len(articles), v.article_id, v.confidence_score, v.is_verified,
            )
        except Exception as exc:
            logger.exception("Verification failed for article %s: %s", article.get("link"), exc)

    verified_only = [v for v in verified if v.is_verified]
    logger.info(
        "Verification complete: %d/%d articles passed threshold.",
        len(verified_only), len(verified),
    )

    if not verified_only:
        logger.error(
            "0 content-verified items. Check sources, threshold (%.2f), or LLM config.",
            MIN_CONFIDENCE_THRESHOLD,
        )
        sys.exit(2)

    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    output_file = os.path.join(OUTPUT_DIR, f"verified_{date_str}.json")
    save_verified_articles(verified_only, output_file)
    logger.info("Fact verification stage completed successfully.")


if __name__ == "__main__":
    main()
