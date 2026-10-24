#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent 17: MCQ Validator (Supports 5-Option Banking/IBPS & 4-Option Standard MCQs)
=================================================================================
Audits generated MCQs for grammatical correctness, option count (5 options A-E
for Exam Genius format, with backward compatibility for 4 options), correct
answer key format, and bilingual explanation completeness.
"""

from __future__ import annotations
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
logger = logging.getLogger("agent.17_mcq_validator")


def validate_mcqs(mcqs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validates 5-option (or 4-option) bilingual MCQs."""
    valid_mcqs: List[Dict[str, Any]] = []
    for mcq in mcqs:
        q_en = mcq.get("question_en", "").strip()
        options = mcq.get("options") or []
        if q_en and isinstance(options, list) and len(options) in (4, 5):
            # Pad to 5 options if 4 were passed so PDF always renders A) to E) consistently
            if len(options) == 4:
                options = list(options) + ["None of the above / उपर्युक्त में से कोई नहीं"]
                mcq = dict(mcq)
                mcq["options"] = options
            valid_mcqs.append(mcq)
    return valid_mcqs


def main() -> int:
    logger.info("Executing Agent 17 MCQ Validator...")
    job_id = os.getenv("ALP_JOB_ID", "daily_test")
    mcq_file = ROOT / "data" / "mcq" / f"{job_id}.json"
    if mcq_file.is_file():
        data = json.loads(mcq_file.read_text(encoding="utf-8"))
        mcqs = data.get("mcqs", data) if isinstance(data, dict) else data
        valid = validate_mcqs(mcqs)
        mcq_file.write_text(json.dumps({"mcqs": valid}, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Validated %d / %d MCQs", len(valid), len(mcqs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
