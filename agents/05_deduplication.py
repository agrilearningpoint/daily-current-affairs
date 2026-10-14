# -*- coding: utf-8 -*-
"""
Deduplication Agent (05)
========================
Verified articles ko dedup karta hai across multiple dimensions:
1. URL normalization
2. Title fingerprint (SHA1)
3. Content similarity (SequenceMatcher)
4. Event-level clustering (same event, different sources)

Production features:
- Multi-stage dedup (URL → hash → similarity)
- Event fingerprinting for cross-source news
- Unicode-safe normalization
- Preserves highest-confidence version
- Atomic output

Env:
  DEDUP_SIMILARITY_THRESHOLD  (default 0.85)
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = REPO_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(LOGS_DIR / "deduplication.log"), encoding="utf-8"),
    ],
)
logger = logging.getLogger("agent.05_deduplication")

INPUT_DIR = REPO_ROOT / "data" / "verified"
OUTPUT_DIR = REPO_ROOT / "data" / "dedup"
SIMILARITY_THRESHOLD = float(os.getenv("DEDUP_SIMILARITY_THRESHOLD", "0.85"))

TRACKING_PARAMS = re.compile(
    r"^(utm_|fbclid|gclid|ref|_ga|mc_|yclid)", re.IGNORECASE
)
WHITESPACE_RE = re.compile(r"\s+")


# --------------------------------------------------------------------------- #
def normalize_url(url: str) -> str:
    if not url:
        return ""
    url = url.split("#", 1)[0]
    if "?" in url:
        base, qs = url.split("?", 1)
        kept = [p for p in qs.split("&")
                if p and not TRACKING_PARAMS.match(p.split("=", 1)[0])]
        url = base + ("?" + "&".join(kept) if kept else "")
    return url.rstrip("/").lower()


def normalize_text(t: str) -> str:
    if not t:
        return ""
    t = unicodedata.normalize("NFC", t)
    t = t.lower()
    t = re.sub(r"[^\w\s]", " ", t, flags=re.UNICODE)
    return WHITESPACE_RE.sub(" ", t).strip()


def fingerprint(text: str) -> str:
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()[:16]


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()


# --------------------------------------------------------------------------- #
def load_latest() -> Tuple[List[Dict[str, Any]], Path]:
    if not INPUT_DIR.exists():
        return [], None
    files = sorted(
        [f for f in INPUT_DIR.glob("verified_*.json") if f.is_file()],
        key=lambda p: p.stat().st_mtime, reverse=True,
    )
    if not files:
        files = sorted(
            [f for f in INPUT_DIR.glob("*.json") if f.is_file()],
            key=lambda p: p.stat().st_mtime, reverse=True,
        )
    if not files:
        return [], None
    try:
        data = json.loads(files[0].read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = data.get("items") or data.get("articles") or []
        return (data if isinstance(data, list) else []), files[0]
    except Exception as exc:
        logger.exception("Load failed: %s", exc)
        return [], None


def atomic_write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    with open(tmp, "rb") as f:
        os.fsync(f.fileno())
    os.replace(tmp, path)


# --------------------------------------------------------------------------- #
def dedup_url(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Stage 1: URL-based dedup. Keeps longest summary."""
    seen: Dict[str, Dict[str, Any]] = {}
    for a in articles:
        url = normalize_url(a.get("link", ""))
        if not url:
            continue
        cur = seen.get(url)
        if cur is None or len(a.get("summary", "")) > len(cur.get("summary", "")):
            seen[url] = a
    return list(seen.values())


def dedup_fingerprint(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Stage 2: title fingerprint dedup."""
    seen: Dict[str, Dict[str, Any]] = {}
    for a in articles:
        title = a.get("title", "")
        fp = fingerprint(title)
        cur = seen.get(fp)
        if cur is None or a.get("confidence_score", 0) > cur.get("confidence_score", 0):
            seen[fp] = a
    return list(seen.values())


def dedup_similarity(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Stage 3: content-similarity clustering (O(n²), small n)."""
    clusters: List[Dict[str, Any]] = []
    for a in articles:
        title = a.get("title", "")
        merged = False
        for c in clusters:
            if similarity(title, c.get("title", "")) > SIMILARITY_THRESHOLD:
                # Same event — keep higher confidence
                if a.get("confidence_score", 0) > c.get("confidence_score", 0):
                    c.update(a)
                # merge sources
                c.setdefault("_sources", set()).add(a.get("source_feed", ""))
                merged = True
                break
        if not merged:
            a = dict(a)
            a["_sources"] = {a.get("source_feed", "")}
            clusters.append(a)

    # Convert _sources set → list + count
    for c in clusters:
        srcs = sorted(c.pop("_sources", set()))
        c["duplicate_sources"] = srcs
        c["source_count"] = len(srcs)
    return clusters


# --------------------------------------------------------------------------- #
def main() -> int:
    articles, src = load_latest()
    if not articles:
        logger.error("No verified articles found")
        return 1

    logger.info("Input: %d articles from %s", len(articles), src.name if src else "?")

    after_url = dedup_url(articles)
    logger.info("After URL dedup: %d", len(after_url))

    after_fp = dedup_fingerprint(after_url)
    logger.info("After fingerprint dedup: %d", len(after_fp))

    after_sim = dedup_similarity(after_fp)
    logger.info("After similarity clustering: %d", len(after_sim))

    # Sort by source_count desc + confidence
    after_sim.sort(key=lambda a: (a.get("source_count", 1),
                                   a.get("confidence_score", 0)),
                   reverse=True)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out = OUTPUT_DIR / f"dedup_{date_str}.json"
    atomic_write(out, after_sim)

    logger.info("✔ Dedup complete: %d → %d (%.1f%% reduction)",
                len(articles), len(after_sim),
                (1 - len(after_sim) / len(articles)) * 100)
    return 0


if __name__ == "__main__":
    sys.exit(main())
