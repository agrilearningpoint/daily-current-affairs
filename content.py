#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pipeline Content Utilities & Bilingual MCQ-First Data Models
============================================================
Helper functions and schemas to sanitize, deduplicate, and structure news
articles into the Exam Genius / Agri Learning Point Bilingual MCQ-First format:
  - Question (English + Hindi)
  - 5 Options (A to E, with EN / HI slash formatting where applicable)
  - Correct Answer (Option A-E)
  - Pair-wise Bilingual Explanation bullets ([{'en': '...', 'hi': '...'}])
  - Pair-wise Bilingual Static GK facts ([{'en': '...', 'hi': '...'}])
  - Optional 'Recent News Headlines Related to ...' revision box
"""

from __future__ import annotations
from typing import Any, Dict, List
from pipeline.static_gk_db import lookup_static_gk, lookup_recent_headlines_box


def sanitize_text(text: str) -> str:
    """Removes bad characters, extra whitespace, and normalizes unicode."""
    if not text:
        return ""
    return " ".join(str(text).strip().split())


def format_bilingual_option(opt_en: str, opt_hi: str = "") -> str:
    """Formats an MCQ option as 'English / हिंदी' if Hindi differs from English/numeric."""
    en_clean = sanitize_text(opt_en)
    hi_clean = sanitize_text(opt_hi)
    if not hi_clean or hi_clean == en_clean:
        return en_clean
    if "/" in en_clean:
        return en_clean
    return f"{en_clean} / {hi_clean}"


def normalize_explanation_pairs(item: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Extracts or builds 4-6 paired bilingual explanation bullets:
    [{'en': 'English fact sentence.', 'hi': 'हिंदी तथ्य वाक्य।'}, ...]
    """
    pairs = item.get("explanation_pairs") or item.get("bilingual_bullets")
    if isinstance(pairs, list) and pairs:
        cleaned = []
        for p in pairs:
            if isinstance(p, dict):
                en_s = sanitize_text(p.get("en", ""))
                hi_s = sanitize_text(p.get("hi", ""))
                if en_s or hi_s:
                    cleaned.append({"en": en_s, "hi": hi_s})
        if cleaned:
            return cleaned

    # Fallback: pair summary_en sentences with summary_hi sentences
    en_bullets = item.get("bullets_en") or []
    hi_bullets = item.get("bullets_hi") or []
    if not en_bullets and item.get("summary_en"):
        en_bullets = [s.strip() for s in str(item["summary_en"]).split(". ") if s.strip()]
    if not hi_bullets and item.get("summary_hi"):
        hi_bullets = [s.strip() for s in str(item["summary_hi"]).split("।") if s.strip()]

    max_len = max(len(en_bullets), len(hi_bullets))
    out: List[Dict[str, str]] = []
    for i in range(max_len):
        en_val = sanitize_text(en_bullets[i]) if i < len(en_bullets) else ""
        if en_val and not en_val.endswith("."):
            en_val += "."
        hi_val = sanitize_text(hi_bullets[i]) if i < len(hi_bullets) else ""
        if hi_val and not hi_val.endswith("।") and not hi_val.endswith("."):
            hi_val += "।"
        if en_val or hi_val:
            out.append({"en": en_val, "hi": hi_val})
    return out


def normalize_static_gk_pairs(item: Dict[str, Any]) -> List[Dict[str, str]]:
    """Extracts or enriches bilingual Static GK facts for a news item."""
    raw_gk = item.get("static_gk") or []
    normalized: List[Dict[str, str]] = []
    for g in raw_gk:
        if isinstance(g, dict):
            normalized.append({
                "en": sanitize_text(g.get("en", "")),
                "hi": sanitize_text(g.get("hi", "")),
                "mode": g.get("mode", "paired"),
            })
        elif isinstance(g, str) and g.strip():
            normalized.append({"en": sanitize_text(g), "hi": "", "mode": "slash"})

    if not normalized:
        search_blob = f"{item.get('title_en', '')} {item.get('question_en', '')} {item.get('summary_en', '')}"
        normalized = lookup_static_gk(search_blob)

    return normalized


def enrich_item_for_exam_genius_pdf(item: Dict[str, Any], mcq: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Combines a news item and its 5-option MCQ into a unified Exam-Genius card dict."""
    merged = dict(item)
    if mcq:
        for k in ("question_en", "question_hi", "options", "answer", "explanation_pairs", "static_gk"):
            if mcq.get(k):
                merged[k] = mcq[k]

    # Ensure 5 options (A to E)
    options = list(merged.get("options") or [])
    while len(options) < 5:
        options.append(f"None of the above / उपर्युक्त में से कोई नहीं" if len(options) == 4 else f"Option {chr(65 + len(options))}")
    merged["options"] = options[:5]

    merged["explanation_pairs"] = normalize_explanation_pairs(merged)
    merged["static_gk"] = normalize_static_gk_pairs(merged)

    if "recent_headlines_box" not in merged:
        search_blob = f"{merged.get('title_en', '')} {merged.get('question_en', '')}"
        box = lookup_recent_headlines_box(search_blob, merged.get("category", ""))
        if box:
            merged["recent_headlines_box"] = box

    return merged
