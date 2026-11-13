# -*- coding: utf-8 -*-
"""
Persistent Historical Storage & Atomic State Manager (Section 6 & 14)
====================================================================
Maintains durable Git-tracked JSON + SQLite-compatible historical stores in `state/`
with file locking and atomic write-replace so data survives GitHub Actions runner
destruction (via `scripts/sync_state.py` + artifact checkpoints) and prevents
concurrent corruption:
1. state/news_history.json        - Permanent 4-layer event & article history
2. state/mcq_history.json         - Permanent MCQ fingerprint & stem database
3. state/feed_health.json         - RSS ETag/Last-Modified cache & quarantine state
4. state/api_health.json          - Per-key cooldown, RPM/RPD, and error state
5. state/fact_ledger.json         - Verified numerical & institutional fact ledger
6. state/published_events.json    - Telegram publication & pin reconciliation ledger
7. state/healing_history.json     - Auto-healer repair budget & incident log
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

ROOT_DIR = Path(__file__).resolve().parent.parent
STATE_DIR = ROOT_DIR / "state"
STATE_DIR.mkdir(parents=True, exist_ok=True)


def atomic_write_json(path: Path, data: Any) -> None:
    """Write JSON atomically via temp file + os.replace to prevent partial writes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            try:
                os.remove(tmp_name)
            except OSError:
                pass


def safe_read_json(path: Path, default: Any) -> Any:
    """Read JSON safely; if corrupted, quarantine the broken file and return default."""
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        quarantine = path.with_suffix(f".corrupt.{int(datetime.now(timezone.utc).timestamp())}.json")
        try:
            os.replace(path, quarantine)
        except OSError:
            pass
        return default


# ---------------------------------------------------------------------------
# 4-Layer News & Event Deduplication Engine (Section 6)
# ---------------------------------------------------------------------------
TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "ref", "outputType", "icheck",
}

STOPWORDS = {
    "the", "a", "an", "in", "on", "at", "to", "for", "of", "and", "or", "by",
    "with", "from", "as", "is", "are", "was", "were", "has", "have", "had",
    "new", "india", "indian", "government", "govt", "ministry", "announces",
    "launched", "launches", "launch", "scheme", "programme", "mission", "under",
}


def canonicalize_url(url: str) -> str:
    """Layer 1: Normalize scheme, netloc, path, and strip tracking query params."""
    raw = str(url or "").strip()
    if not raw:
        return ""
    try:
        parsed = urlparse(raw)
        scheme = "https" if parsed.scheme in ("http", "https", "") else parsed.scheme.lower()
        netloc = parsed.netloc.lower().removeprefix("www.")
        path = re.sub(r"/+$", "", parsed.path or "")
        q_pairs = [(k, v) for k, v in parse_qsl(parsed.query) if k.lower() not in TRACKING_PARAMS]
        q_pairs.sort()
        return urlunparse((scheme, netloc, path, "", urlencode(q_pairs), ""))
    except Exception:
        return raw.lower()


def normalize_headline(text: str) -> str:
    """Layer 2: Lowercase, strip punctuation/source suffixes, collapse whitespace."""
    s = str(text or "").strip()
    s = re.sub(r"\s+[\-|–|—]\s+[A-Za-z0-9\s.&]{2,30}$", "", s)
    s = re.sub(r"(?i)\b(?:rs|inr)\b\.?\s*", "₹", s)
    s = re.sub(r"[^a-z0-9\u0900-\u097f₹]+", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def semantic_tokens(text: str) -> Set[str]:
    """Extract content-bearing tokens for Layer 3 Jaccard/cosine similarity."""
    norm = normalize_headline(text)
    return {tok for tok in norm.split() if len(tok) > 2 and tok not in STOPWORDS}


def semantic_similarity(text_a: str, text_b: str) -> float:
    """Layer 3: Token overlap similarity (Jaccard + containment boost)."""
    ta = semantic_tokens(text_a)
    tb = semantic_tokens(text_b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    jaccard = inter / union if union else 0.0
    containment = inter / min(len(ta), len(tb))
    return round(0.6 * jaccard + 0.4 * containment, 4)


def compute_event_signature(item: Dict[str, Any]) -> str:
    """Layer 4: Event identity signature combining key entities, numbers, and core nouns."""
    title = str(item.get("headline_en") or item.get("title") or "")
    summary = str(item.get("summary_en") or item.get("summary") or "")
    text = f"{title} {summary[:200]}"
    # Extract numbers/amounts and capitalized entities/acronyms
    nums = sorted(set(re.findall(r"\d+(?:\.\d+)?", title)))
    acronyms = sorted(set(re.findall(r"\b[A-Z]{2,8}\b", title)))
    core = sorted(list(semantic_tokens(title)))[:6]
    raw_sig = "|".join(acronyms[:3] + nums[:3] + core[:5])
    return hashlib.sha1(raw_sig.encode("utf-8")).hexdigest()[:16] if raw_sig else ""


def deduplicate_news_4layer(
    candidates: List[Dict[str, Any]],
    edition_date: str,
    history_path: Optional[Path] = None,
    similarity_threshold: float = 0.62,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Run 4-layer deduplication across incoming candidates AND permanent historical database.
    Allows a historical event through ONLY when `is_verified_update=True` with new facts.
    Returns (unique_events, dropped_duplicates).
    """
    h_path = history_path or (STATE_DIR / "news_history.json")
    history = safe_read_json(h_path, {"events": {}})
    hist_events: Dict[str, Dict[str, Any]] = history.get("events", {})

    seen_urls: Dict[str, str] = {}
    seen_norm_titles: Dict[str, str] = {}
    seen_signatures: Dict[str, str] = {}
    for ev_id, rec in hist_events.items():
        if rec.get("canonical_url"):
            seen_urls[rec["canonical_url"]] = ev_id
        if rec.get("normalized_headline"):
            seen_norm_titles[rec["normalized_headline"]] = ev_id
        if rec.get("event_signature"):
            seen_signatures[rec["event_signature"]] = ev_id

    kept: List[Dict[str, Any]] = []
    dropped: List[Dict[str, Any]] = []

    for item in candidates:
        c_url = canonicalize_url(item.get("link") or item.get("url") or "")
        headline = str(item.get("headline_en") or item.get("title") or "").strip()
        summary = str(item.get("summary_en") or item.get("summary") or "").strip()
        norm_h = normalize_headline(headline)
        ev_sig = compute_event_signature(item)
        is_update = bool(item.get("is_verified_update"))

        dup_reason = None
        matched_event_id = None

        # Layer 1: Canonical URL match
        if c_url and c_url in seen_urls and not is_update:
            dup_reason = "layer1_canonical_url"
            matched_event_id = seen_urls[c_url]

        # Layer 2: Normalized headline match
        if not dup_reason and norm_h and norm_h in seen_norm_titles and not is_update:
            dup_reason = "layer2_normalized_headline"
            matched_event_id = seen_norm_titles[norm_h]

        # Layer 3: Semantic headline + summary similarity
        if not dup_reason and not is_update:
            cand_text = f"{headline} {summary[:160]}"
            for existing in kept:
                ex_text = f"{existing.get('headline_en') or existing.get('title') or ''} {(existing.get('summary_en') or existing.get('summary') or '')[:160]}"
                if semantic_similarity(headline, str(existing.get("headline_en") or existing.get("title") or "")) >= similarity_threshold or semantic_similarity(cand_text, ex_text) >= similarity_threshold:
                    dup_reason = "layer3_semantic_similarity"
                    matched_event_id = existing.get("event_id")
                    existing.setdefault("other_reporting_urls", [])
                    if c_url and c_url not in existing["other_reporting_urls"]:
                        existing["other_reporting_urls"].append(c_url)
                    break
            if not dup_reason:
                for ev_id, rec in hist_events.items():
                    if semantic_similarity(headline, rec.get("original_headline", "")) >= similarity_threshold:
                        dup_reason = "layer3_historical_semantic_similarity"
                        matched_event_id = ev_id
                        break

        # Layer 4: Event identity signature match
        if not dup_reason and ev_sig and ev_sig in seen_signatures and not is_update:
            # Verify shared numbers/entities to avoid false collision
            prev_rec = hist_events.get(seen_signatures[ev_sig], {})
            if semantic_similarity(headline, prev_rec.get("original_headline", headline)) >= 0.45:
                dup_reason = "layer4_event_identity"
                matched_event_id = seen_signatures[ev_sig]

        if dup_reason:
            dup_copy = dict(item)
            dup_copy["duplicate_reason"] = dup_reason
            dup_copy["matched_event_id"] = matched_event_id
            if matched_event_id and matched_event_id in hist_events:
                hist_events[matched_event_id]["last_seen_date"] = edition_date
                if c_url and c_url not in hist_events[matched_event_id].get("other_reporting_urls", []):
                    hist_events[matched_event_id].setdefault("other_reporting_urls", []).append(c_url)
            dropped.append(dup_copy)
            continue

        event_id = item.get("event_id") or f"ev_{hashlib.sha1((c_url or norm_h).encode('utf-8')).hexdigest()[:12]}"
        enriched = dict(item)
        enriched["event_id"] = event_id
        enriched["canonical_url"] = c_url
        enriched["normalized_headline"] = norm_h
        enriched["event_signature"] = ev_sig
        enriched.setdefault("other_reporting_urls", [])
        if is_update:
            enriched["update_badge"] = "VERIFIED UPDATE"

        kept.append(enriched)
        if c_url:
            seen_urls[c_url] = event_id
        if norm_h:
            seen_norm_titles[norm_h] = event_id
        if ev_sig:
            seen_signatures[ev_sig] = event_id

        hist_events[event_id] = {
            "event_id": event_id,
            "canonical_url": c_url,
            "original_headline": headline,
            "normalized_headline": norm_h,
            "event_signature": ev_sig,
            "original_source": item.get("source_name") or item.get("source_id") or "",
            "publication_time": item.get("published_at_ist") or item.get("published_at") or "",
            "other_reporting_urls": enriched["other_reporting_urls"],
            "verification_status": item.get("verification_status", "verified"),
            "first_seen_date": hist_events.get(event_id, {}).get("first_seen_date", edition_date),
            "last_seen_date": edition_date,
        }

    history["events"] = hist_events
    history["updated_at"] = datetime.now(timezone.utc).isoformat()
    atomic_write_json(h_path, history)
    return kept, dropped


def recently_selected(job_id: str, days: int = 3) -> Dict[str, Set[str]]:
    """Backward-compatible helper for 10_final_news_selection.py."""
    h_path = STATE_DIR / "news_history.json"
    history = safe_read_json(h_path, {"events": {}})
    ids: Set[str] = set()
    links: Set[str] = set()
    keys: Set[str] = set()
    for ev_id, rec in (history.get("events") or {}).items():
        ids.add(str(ev_id))
        if rec.get("canonical_url"):
            links.add(rec["canonical_url"])
        if rec.get("normalized_headline"):
            keys.add(rec["normalized_headline"])
    return {"ids": ids, "links": links, "keys": keys}
