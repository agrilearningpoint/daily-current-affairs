#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent 12: Content Editor & Bilingual Exam-Genius Structuring Engine
===================================================================
Processes curated news articles into the Exam Genius / Agri Learning Point
Bilingual structure:
  - Question in English (`question_en`) & Hindi (`question_hi`)
  - 5 Bilingual Options (`A)` to `E)`)
  - Correct Answer (`Option A` .. `Option E`)
  - 4 to 6 Pair-wise Bilingual Explanation Bullets (`explanation_pairs`)
  - Pair-wise Bilingual Static GK Facts (`static_gk`)
  - Related Recent News Headlines Revision Box (`recent_headlines_box`)
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
    normalize_explanation_pairs,
    normalize_static_gk_pairs,
    enrich_item_for_exam_genius_pdf,
)

logger = logging.getLogger("agent.12_content_editor")


def build_content(raw_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Transforms raw articles into bilingual MCQ + paired explanation + Static GK items."""
    processed: List[Dict[str, Any]] = []
    seen_boxes: set[str] = set()

    for idx, item in enumerate(raw_items, start=1):
        base = {
            "id": item.get("id", idx),
            "title_en": sanitize_text(item.get("title_en") or item.get("title", "")),
            "title_hi": sanitize_text(item.get("title_hi", "")),
            "question_en": sanitize_text(item.get("question_en", "")),
            "question_hi": sanitize_text(item.get("question_hi", "")),
            "options": item.get("options", []),
            "answer": item.get("answer", "Option B"),
            "summary_en": sanitize_text(item.get("summary_en") or item.get("summary", "")),
            "summary_hi": sanitize_text(item.get("summary_hi", "")),
            "explanation_pairs": normalize_explanation_pairs(item),
            "static_gk": normalize_static_gk_pairs(item),
            "category": item.get("category", "Agriculture & National Affairs"),
        }
        if item.get("recent_headlines_box"):
            base["recent_headlines_box"] = item["recent_headlines_box"]

        enriched = enrich_item_for_exam_genius_pdf(base)

        # Deduplicate revision boxes so the same entity box is not repeated twice in one issue
        box = enriched.get("recent_headlines_box")
        if box and isinstance(box, dict):
            btitle = box.get("box_title", "")
            if btitle in seen_boxes:
                enriched.pop("recent_headlines_box", None)
            else:
                seen_boxes.add(btitle)

        processed.append(enriched)

    return {"items": processed}


def main() -> int:
    logger.info("Executing Agent 12 Content Editor (Bilingual Paired Format)...")
    job_id = os.getenv("ALP_JOB_ID", "daily_test")
    selected_file = ROOT / "data" / "selected" / f"{job_id}.json"
    content_dir = ROOT / "data" / "content"
    content_dir.mkdir(parents=True, exist_ok=True)
    content_file = content_dir / f"{job_id}.json"

    if selected_file.is_file():
        raw_data = json.loads(selected_file.read_text(encoding="utf-8"))
        raw_items = raw_data.get("items", raw_data) if isinstance(raw_data, dict) else raw_data
        built = build_content(raw_items)
        content_file.write_text(json.dumps(built, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Saved %d bilingual structured items to %s", len(built["items"]), content_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
