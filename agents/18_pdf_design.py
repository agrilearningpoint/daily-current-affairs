#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent 18: PDF Design & Publishing Layout Engine
================================================
Orchestrates the creation of the Exam Genius-grade Daily Current Affairs PDF booklet.
Reads:
  - data/content/{job_id}.json (stories, facts, bilingual summaries)
  - data/content/mcqs_{job_id}.json (validated MCQs, options, answers)
Writes:
  - output/{job_id}.pdf (production publication PDF)
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.generate_pdf import generate_pdf, get_shaping_diagnostics

LOGS_DIR = ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(LOGS_DIR / "pdf_design.log"), encoding="utf-8"),
    ],
)
logger = logging.getLogger("agent.18_pdf_design")


def run_stage(job_id: str, date_str: str) -> bool:
    """Execute PDF generation stage for job_id."""
    content_file = ROOT / "data" / "content" / f"{job_id}.json"
    mcq_file = ROOT / "data" / "mcq" / f"{job_id}.json"
    if not mcq_file.is_file():
        mcq_file = ROOT / "data" / "content" / f"mcqs_{job_id}.json"

    if not content_file.is_file():
        logger.error("Content file not found: %s", content_file)
        return False

    try:
        content = json.loads(content_file.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.error("Failed to parse content JSON: %s", exc)
        return False

    mcqs: List[Dict[str, Any]] = []
    if mcq_file.is_file():
        try:
            mcq_data = json.loads(mcq_file.read_text(encoding="utf-8"))
            if isinstance(mcq_data, list):
                mcqs = mcq_data
            elif isinstance(mcq_data, dict):
                mcqs = mcq_data.get("mcqs", [])
        except Exception as exc:
            logger.warning("Could not read MCQs JSON: %s", exc)

    items = content.get("items") or []
    if not items:
        logger.error("Content has zero items. Refusing to generate empty PDF.")
        return False

    output_dir = ROOT / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    out_pdf = output_dir / f"{job_id}.pdf"

    has_shaping, diag = get_shaping_diagnostics()
    logger.info("Devanagari shaping diagnostics: %s", diag)

    logger.info("Generating Exam Genius PDF with %d items and %d MCQs -> %s", len(items), len(mcqs), out_pdf.name)
    try:
        pdf_path = generate_pdf(content, mcqs, output_path=str(out_pdf))
        logger.info("[OK] Exam Genius PDF generated successfully: %s", pdf_path)
        return True
    except Exception as exc:
        logger.exception("Failed to generate PDF: %s", exc)
        return False


def main() -> int:
    job_id = os.getenv("ALP_JOB_ID")
    date_str = os.getenv("ALP_JOB_DATE")

    if not job_id:
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        job_id = f"daily_{date_str or today_str}"
    if not date_str:
        date_str = job_id.replace("daily_", "").replace("weekly_", "").replace("monthly_", "")

    success = run_stage(job_id, date_str)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
