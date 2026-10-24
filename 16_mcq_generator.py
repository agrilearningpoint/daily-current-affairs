#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent 16: Bilingual 5-Option MCQ Generator (Exam Genius Style)
==============================================================
Generates high-yield competitive exam MCQs with:
  - Bilingual Question (`Ques:` in English + `प्रश्न:` in Hindi)
  - 5 Options (`A)` to `E)`) formatted in Bilingual `English / हिंदी` where applicable
  - Correct Answer key (`Option A` .. `Option E`)
  - Detailed point-by-point bilingual explanation pairs (`explanation_pairs`)
  - Bilingual Static GK facts (`static_gk`)
"""

from __future__ import annotations
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.content import (
    sanitize_text,
    format_bilingual_option,
    normalize_explanation_pairs,
    normalize_static_gk_pairs,
)

logger = logging.getLogger("agent.16_mcq_generator")


def generate_mcqs(content_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generates 5-option (A-E) bilingual MCQs with paired explanations and Static GK."""
    mcqs: List[Dict[str, Any]] = []
    for idx, item in enumerate(content_items, start=1):
        q_en = sanitize_text(item.get("question_en", ""))
        q_hi = sanitize_text(item.get("question_hi", ""))
        title_en = sanitize_text(item.get("title_en") or item.get("title", f"Current Affairs Topic {idx}"))
        title_hi = sanitize_text(item.get("title_hi") or title_en)

        if not q_en:
            q_en = f"Which organization or ministry is associated with {title_en}?"
        if not q_hi:
            q_hi = f"निम्नलिखित में से कौन-सा संस्थान या मंत्रालय '{title_hi}' से संबंधित है?"

        raw_options = item.get("options") or []
        formatted_options: List[str] = []
        for opt in raw_options:
            if isinstance(opt, dict):
                formatted_options.append(format_bilingual_option(opt.get("en", ""), opt.get("hi", "")))
            else:
                formatted_options.append(sanitize_text(str(opt)))

        default_fallbacks = [
            "NABARD / नाबार्ड",
            "Reserve Bank of India (RBI) / भारतीय रिज़र्व बैंक (RBI)",
            "ICAR, New Delhi / भा.कृ.अनु.प. (ICAR), नई दिल्ली",
            "Ministry of Agriculture & Farmers Welfare / कृषि एवं किसान कल्याण मंत्रालय",
            "State Bank of India (SBI) / भारतीय स्टेट बैंक (SBI)",
        ]
        while len(formatted_options) < 5:
            formatted_options.append(default_fallbacks[len(formatted_options)])

        explanation_pairs = normalize_explanation_pairs(item)
        if not explanation_pairs:
            explanation_pairs = [
                {
                    "en": sanitize_text(item.get("summary_en", f"Key exam development related to {title_en}.")),
                    "hi": sanitize_text(item.get("summary_hi", f"{title_hi} से संबंधित महत्वपूर्ण परीक्षा उपयोगी तथ्य।")),
                }
            ]

        static_gk = normalize_static_gk_pairs(item)

        mcq_entry: Dict[str, Any] = {
            "id": item.get("id", idx),
            "question_en": q_en,
            "question_hi": q_hi,
            "options": formatted_options[:5],
            "answer": item.get("answer", "Option B"),
            "explanation_pairs": explanation_pairs,
            "static_gk": static_gk,
        }
        if item.get("recent_headlines_box"):
            mcq_entry["recent_headlines_box"] = item["recent_headlines_box"]

        mcqs.append(mcq_entry)

    return mcqs


def main() -> int:
    logger.info("Executing Agent 16 MCQ Generator (5-Option Bilingual Exam Genius Format)...")
    job_id = os.getenv("ALP_JOB_ID", "daily_test")
    content_file = ROOT / "data" / "content" / f"{job_id}.json"
    mcq_dir = ROOT / "data" / "mcq"
    mcq_dir.mkdir(parents=True, exist_ok=True)
    mcq_file = mcq_dir / f"{job_id}.json"

    if content_file.is_file():
        data = json.loads(content_file.read_text(encoding="utf-8"))
        items = data.get("items", [])
        mcqs = generate_mcqs(items)
        mcq_file.write_text(json.dumps({"mcqs": mcqs}, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Generated %d 5-option bilingual MCQs -> %s", len(mcqs), mcq_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
