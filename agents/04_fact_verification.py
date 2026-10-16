# -*- coding: utf-8 -*-
"""
Fact Verification Agent (04)
============================
Collected articles ko verify karta hai using multiple strategies:

1. Cross-source corroboration  (same claim multiple sources mein?)
2. Heuristic checks            (title/summary/URL sanity)
3. Optional LLM verification   (fallback with graceful degradation)

Production features:
- Confidence scoring (0.0 - 1.0) — binary pass/fail NAHI
- Configurable threshold via env (DEFAULT 0.3, tunable)
- Multi-strategy weighted combination
- Graceful degradation (LLM fail → heuristics still work)
- Retry with exponential backoff for LLM calls
- Unicode-safe (preserves Devanagari)
- Per-item error isolation
- Structured logging + run summary
- Atomic output

Env switches:
  MIN_CONFIDENCE_THRESHOLD=0.3   # 0.0-1.0, default 0.3 (lower = more permissive)
  MIN_VERIFIED_COUNT=1           # min items to pass (default 1, was hardcoded 5)
  ALP_DISABLE_LLM_VERIFY=1       # skip LLM verify entirely (heuristics only)
  LLM_API_URL, LLM_API_KEY       # OpenAI-compatible endpoint
"""
from __future__ import annotations

import hashlib
import html
import json
import logging
import os
import re
import sys
import time
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse
from difflib import SequenceMatcher

import requests

# --------------------------------------------------------------------------- #
# Logging
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
        logging.FileHandler(str(LOGS_DIR / "fact_verification.log"), encoding="utf-8"),
    ],
)
logger = logging.getLogger("agent.04_fact_verification")

# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
INPUT_DIR = REPO_ROOT / "data" / "raw"
OUTPUT_DIR = REPO_ROOT / "data" / "verified"

MIN_CONFIDENCE_THRESHOLD = float(os.getenv("MIN_CONFIDENCE_THRESHOLD", "0.3"))
MIN_VERIFIED_COUNT = int(os.getenv("MIN_VERIFIED_COUNT", "1"))
DISABLE_LLM = os.getenv("ALP_DISABLE_LLM_VERIFY", "0") == "1"

LLM_API_URL = os.getenv("LLM_API_URL", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "30"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))

# Regexes
CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
WHITESPACE_RE = re.compile(r"\s+")
URL_RE = re.compile(r"^https?://")
STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "this", "that", "these", "those", "it", "its", "as", "has", "have",
    "had", "will", "would", "can", "could", "should", "may", "might",
    "also", "more", "than", "then", "over", "into", "out", "up", "down",
    "new", "says", "said", "amid", "after", "before", "during", "while",
}


# --------------------------------------------------------------------------- #
# Utilities
# --------------------------------------------------------------------------- #
def clean_text(text: str, max_len: int = 5000) -> str:
    """Unicode-safe cleaning (Devanagari preserved)."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = unicodedata.normalize("NFC", text)
    text = CONTROL_CHAR_RE.sub("", text)
    text = WHITESPACE_RE.sub(" ", text).strip()
    if len(text) > max_len:
        text = text[:max_len].rstrip()
    return text


def normalize_for_compare(text: str) -> str:
    """Lowercase, strip punctuation for content matching."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    text = WHITESPACE_RE.sub(" ", text).strip()
    return text


def extract_key_terms(text: str, top_n: int = 15) -> List[str]:
    """Frequency-based key terms (naive; production mein spaCy/KeyBERT)."""
    if not text:
        return []
    words = normalize_for_compare(text).split()
    filtered = [w for w in words if w not in STOPWORDS and len(w) > 3]
    freq = Counter(filtered)
    return [term for term, _ in freq.most_common(top_n)]


def content_hash(article: Dict[str, Any]) -> str:
    raw = f"{article.get('title', '').lower()}|{article.get('link', '')}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


# --------------------------------------------------------------------------- #
# Strategy 1: Cross-Source Corroboration
# --------------------------------------------------------------------------- #
def independent_domain(url):
    """Group sibling subdomains; recognize common multi-label public suffixes."""
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    labels = host.split(".")
    suffixes = {"co.in", "gov.in", "nic.in", "org.in", "net.in", "ac.in", "edu.in",
                "co.uk", "org.uk", "com.au", "co.jp", "co.nz", "com.br"}
    count = 3 if ".".join(labels[-2:]) in suffixes else 2
    return ".".join(labels[-count:])


def cross_source_score(
    article: Dict[str, Any],
    all_articles: List[Dict[str, Any]],
    similarity_threshold: float = 0.25,
) -> Tuple[float, List[str]]:
    """
    Check if same claim appears in multiple sources.
    Returns (confidence 0-1, corroborating_source_list).
    """
    art_text = f"{article.get('title', '')} {article.get('summary', '')}"
    art_terms = set(extract_key_terms(art_text))
    if not art_terms:
        return 0.3, []  # no terms → weak but non-zero

    article_link = article.get("link", "")
    own_host = independent_domain(article_link)
    corroborating: List[str] = []
    title = clean_text(article.get("title", "")).lower()
    numbers = {float(value) for value in re.findall(r"\b\d+(?:\.\d+)?\b", title)}
    for other in all_articles:
        other_link = other.get("link", "")
        host = independent_domain(other_link)
        # Syndicated pages or another article in the same feed are not independent proof.
        if not host or host == own_host or other_link == article_link:
            continue
        other_title = clean_text(other.get("title", "")).lower()
        other_numbers = {float(value) for value in re.findall(r"\b\d+(?:\.\d+)?\b", other_title)}
        if numbers and other_numbers and numbers != other_numbers:
            continue
        other_text = f"{other_title} {other.get('summary', '')}"
        other_terms = set(extract_key_terms(other_text))
        if not other_terms:
            continue
        overlap = len(art_terms & other_terms) / max(len(art_terms | other_terms), 1)
        similarity = SequenceMatcher(None, title, other_title).ratio()
        if overlap >= max(similarity_threshold, 0.55) and similarity >= 0.65:
            if host not in corroborating:
                corroborating.append(host)

    n = len(corroborating)
    if n >= 3:
        score = 0.95
    elif n == 2:
        score = 0.8
    elif n == 1:
        score = 0.6
    else:
        score = 0.35  # single-source — still valid, just lower confidence
    return score, corroborating


# --------------------------------------------------------------------------- #
# Strategy 2: Heuristic Sanity Checks
# --------------------------------------------------------------------------- #
def heuristic_score(article: Dict[str, Any]) -> Tuple[float, List[str]]:
    """Title/summary/URL sanity. Returns (score, flags)."""
    flags: List[str] = []
    score = 1.0

    title = article.get("title", "").strip()
    summary = article.get("summary", "").strip()
    link = article.get("link", "").strip()

    if len(title) < 10:
        flags.append("title_too_short")
        score -= 0.15
    if len(title) > 300:
        flags.append("title_too_long")
        score -= 0.05
    if len(summary) < 30:
        flags.append("summary_too_short")
        score -= 0.1

    # All caps title (likely spam/error)
    if title.isupper() and len(title) > 20:
        flags.append("title_all_caps")
        score -= 0.1

    # Excessive punctuation (clickbait)
    if re.search(r"[!?]{3,}", title):
        flags.append("excessive_punctuation")
        score -= 0.1

    # URL sanity
    if not URL_RE.match(link):
        flags.append("invalid_url")
        score -= 0.3

    # Unicode sanity — at least some letters (not all symbols/digits)
    letters = re.findall(r"\w", title, flags=re.UNICODE)
    if len(letters) < 5:
        flags.append("no_letters_in_title")
        score -= 0.3

    return max(0.0, min(1.0, score)), flags


# --------------------------------------------------------------------------- #
# Strategy 3: LLM Verification (optional, with retries)
# --------------------------------------------------------------------------- #
def _call_llm(prompt: str) -> Optional[str]:
    """Call LLM with retry. Returns content or None."""
    if not LLM_API_URL or not LLM_API_KEY:
        return None

    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system",
             "content": "You are a fact-checking assistant. Respond with JSON only."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
    }

    for attempt in range(1, LLM_MAX_RETRIES + 1):
        try:
            r = requests.post(
                LLM_API_URL, headers=headers, json=payload, timeout=LLM_TIMEOUT
            )
            if r.status_code == 429:
                wait = 2 ** attempt
                logger.warning("LLM rate-limited, waiting %ds", wait)
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            logger.warning("LLM attempt %d/%d failed: %s", attempt, LLM_MAX_RETRIES, exc)
            if attempt < LLM_MAX_RETRIES:
                time.sleep(2 ** attempt)
    return None


def llm_score(article: Dict[str, Any]) -> Tuple[float, List[str]]:
    """LLM-based verification. Returns (score, flags). Silent fail → (0, ['llm_unavailable'])."""
    if DISABLE_LLM or not LLM_API_URL or not LLM_API_KEY:
        return 0.0, ["llm_disabled"]

    prompt = (
        "Assess the factual plausibility of this news article.\n"
        'Return JSON: {"confidence": <0.0-1.0>, "flags": [<strings>]}\n\n'
        f"Title: {article.get('title', '')}\n"
        f"Summary: {article.get('summary', '')[:500]}\n"
        f"Source: {article.get('source_feed', '')}\n"
    )
    raw = _call_llm(prompt)
    if not raw:
        return 0.0, ["llm_unavailable"]

    try:
        data = json.loads(raw)
        conf = float(data.get("confidence", 0.5))
        flags = data.get("flags", [])
        if not isinstance(flags, list):
            flags = []
        return max(0.0, min(1.0, conf)), [str(f) for f in flags]
    except Exception as exc:
        logger.warning("LLM parse failed: %s", exc)
        return 0.0, ["llm_parse_error"]


# --------------------------------------------------------------------------- #
# Combined Verification
# --------------------------------------------------------------------------- #
def verify_article(
    article: Dict[str, Any],
    all_articles: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Run all strategies + weighted combine. Never raises."""
    cross_s, corroborating = cross_source_score(article, all_articles)
    heur_s, heur_flags = heuristic_score(article)

    llm_s = 0.0
    llm_flags: List[str] = []
    if not DISABLE_LLM and LLM_API_URL and LLM_API_KEY:
        llm_s, llm_flags = llm_score(article)

    # Weighted combination
    if llm_s > 0:
        final = 0.5 * cross_s + 0.2 * heur_s + 0.3 * llm_s
        method = "combined"
    else:
        final = 0.7 * cross_s + 0.3 * heur_s
        method = "heuristic+cross_source"

    all_flags = heur_flags + llm_flags
    dry_run = os.getenv("DRY_RUN", "0") == "1"
    host = (urlparse(article.get("link", "")).hostname or "").removeprefix("www.")
    publisher = (urlparse(article.get("publisher_url") or article.get("source_feed", "")).hostname or "").removeprefix("www.")
    primary = (article.get("official") is True and bool(publisher)
               and (host == publisher or host.endswith("." + publisher)))
    provenance = primary or len(corroborating) >= 2
    is_verified = final >= MIN_CONFIDENCE_THRESHOLD and (dry_run or provenance)
    if not provenance:
        all_flags.append("independent_source_verification_missing")

    return {
        **article,
        "event_id": content_hash(article),
        "title": clean_text(article.get("title", ""), 500),
        "link": article.get("link", ""),
        "summary": clean_text(article.get("summary", ""), 3000),
        "published": article.get("published", ""),
        "source_feed": article.get("source_feed", ""),
        "collected_at": article.get("collected_at", ""),
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "confidence_score": round(final, 4),
        "verification_method": method,
        "corroborating_sources": corroborating,
        "flags": all_flags,
        "is_verified": is_verified,
        "verification_mode": "dry_run" if dry_run else "live",
        "provenance_verified": provenance,
    }


# --------------------------------------------------------------------------- #
# I/O
# --------------------------------------------------------------------------- #
def load_latest_raw() -> Optional[Path]:
    from pipeline.agent_context import get_context
    return get_context().find_input("raw")


def atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> int:
    input_file = load_latest_raw()
    if input_file is None:
        logger.error("No raw news files found in %s", INPUT_DIR)
        return 1

    logger.info("Loading raw articles from %s", input_file.name)
    try:
        from pipeline.artifacts import read_news_items
        articles = read_news_items(input_file)
    except Exception as exc:
        logger.exception("Failed to load %s: %s", input_file, exc)
        return 1

    if not isinstance(articles, list) or not articles:
        logger.error("Raw file is empty or malformed: %s", input_file)
        # Emit empty verified file so downstream doesn't crash
        from pipeline.agent_context import get_context
        date_str = get_context().job_date
        atomic_write_json(get_context().output_path("verified"), {"items": []})
        return 1

    logger.info(
        "Verifying %d articles | threshold=%.2f | min_count=%d | llm=%s",
        len(articles), MIN_CONFIDENCE_THRESHOLD, MIN_VERIFIED_COUNT,
        "off" if DISABLE_LLM else ("on" if LLM_API_KEY else "unconfigured"),
    )

    start_time = time.time()
    verified: List[Dict[str, Any]] = []
    failed = 0

    for idx, art in enumerate(articles, 1):
        try:
            result = verify_article(art, articles)
            verified.append(result)
            logger.debug(
                "[%d/%d] %s → %.2f (%s)",
                idx, len(articles),
                result["event_id"],
                result["confidence_score"],
                result["verification_method"],
            )
        except Exception as exc:
            failed += 1
            logger.exception("[%d/%d] Verification crash: %s", idx, len(articles), exc)

    elapsed = time.time() - start_time
    passed = [v for v in verified if v["is_verified"]]
    rejected = [v for v in verified if not v["is_verified"]]

    logger.info(
        "Verification complete in %.1fs | %d total | %d passed | %d rejected | %d crashed",
        elapsed, len(verified), len(passed), len(rejected), failed,
    )

    # Summary stats
    if verified:
        avg_conf = sum(v["confidence_score"] for v in verified) / len(verified)
        method_counts = Counter(v["verification_method"] for v in verified)
        logger.info("Avg confidence: %.3f", avg_conf)
        logger.info("Methods: %s", dict(method_counts))

    # Gate check
    if len(passed) < MIN_VERIFIED_COUNT:
        logger.error(
            "Only %d verified items (min %d required). "
            "Tuning tips: lower MIN_CONFIDENCE_THRESHOLD (current=%.2f), "
            "check input quality, enable LLM verify.",
            len(passed), MIN_VERIFIED_COUNT, MIN_CONFIDENCE_THRESHOLD,
        )
        # Emit whatever we have so downstream can inspect, but exit non-zero
        from pipeline.agent_context import get_context
        atomic_write_json(get_context().output_path("verified"), {"items": passed})
        return 1

    from pipeline.agent_context import get_context
    output_file = get_context().output_path("verified")
    atomic_write_json(output_file, {"items": passed})
    logger.info("✔ Fact verification completed: %d items → %s", len(passed), output_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
