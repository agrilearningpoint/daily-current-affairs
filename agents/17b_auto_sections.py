# -*- coding: utf-8 -*-
"""
AUTO SECTIONS AGENT (17b) — Quick Bites + Agriculture Corner, FAIL-SOFT.

Runs after the MCQ stages (so the final MCQ units are known) and before the PDF
stage.  Builds ``content["quick_bites"]`` (30-40 bilingual two-line items by
exam category, from good stories that are not MCQ units) and
``content["agri_corner"]`` (farm / rural / food / fisheries / animal husbandry
stories + verified agri static GK) — see pipeline/auto_sections.py.

Fail-soft by contract: any problem (no provider, translation budget used up,
bad input) leaves the edition without these optional sections and exits 0; the
content artifact is only rewritten atomically when the build succeeded.
Weekly/monthly editions are not affected (the stage is daily-only).
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logger = logging.getLogger("agent.17b_auto_sections")


def _load_items(path: Path, keys=("items", "reserves")) -> list:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    out = []
    for k in keys:
        out.extend(x for x in (data.get(k) or []) if isinstance(x, dict))
    return out


def run(job_id: str, job_type: str) -> int:
    from pipeline.auto_sections import build_sections
    from pipeline.state import write_json_atomic

    if job_type != "daily" and os.getenv("ALP_AUTO_SECTIONS_ALL_TYPES", "0") != "1":
        logger.info("[17b] %s edition: auto sections are daily-only; nothing to do", job_type)
        return 0
    if os.getenv("ALP_AUTO_SECTIONS", "1") == "0":
        logger.info("[17b] disabled by ALP_AUTO_SECTIONS=0")
        return 0
    content_path = ROOT / "data" / "content" / f"{job_id}.json"
    try:
        content = json.loads(content_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("[17b] content unreadable (%s); edition continues without auto sections", exc)
        return 0
    candidates = (_load_items(ROOT / "data" / "scored" / f"{job_id}.json")
                  + _load_items(ROOT / "data" / "selected" / f"{job_id}.json")
                  + [x for x in content.get("reserve_items") or [] if isinstance(x, dict)])
    try:
        stats = build_sections(content, candidates)
    except Exception as exc:  # fail-soft: optional sections never fail the run
        logger.warning("[17b] auto sections skipped: %s", exc)
        return 0
    write_json_atomic(content_path, content)
    logger.info("[17b] Quick Bites=%s, Agriculture Corner items=%s (%s)",
                stats.get("quick_bites"), stats.get("agri_items"), stats)
    return 0


def main() -> int:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"),
                        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
    job_type = os.getenv("ALP_JOB_TYPE") or "daily"
    job_date = os.getenv("ALP_JOB_DATE") or ""
    job_id = os.getenv("ALP_JOB_ID") or f"{job_type}_{job_date}"
    try:
        return run(job_id, job_type)
    except Exception as exc:  # pragma: no cover - last-resort fail-soft
        logger.warning("[17b] unexpected error, continuing without auto sections: %s", exc)
        return 0


if __name__ == "__main__":
    sys.exit(main())
