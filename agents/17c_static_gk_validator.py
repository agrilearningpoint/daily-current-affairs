# -*- coding: utf-8 -*-
"""
STATIC GK VALIDATOR STAGE (17c) — strict officeholder / stale-fact check, FAIL-OPEN.

Runs after content (12), MCQ generation/validation (16/17) and the auto
sections (17b), immediately before the PDF stage (18).  Every Static GK line
in the content artifact (story ``static_gk_pairs`` / ``static_gk`` /
``static_facts``, Agriculture Corner ``static_gk``) and in the MCQ artifact
(LLM ``static_gk`` rows) is checked against config/current_facts.json by
agents/static_gk_validator.py: wrong officeholders are corrected, unverifiable
officeholder names and stale "latest" figures are dropped.

Fail-open by contract: any problem leaves the edition as it was (or with the
officeholder-type lines removed when the validator itself breaks) and exits 0.
Artifacts are only rewritten atomically.  Hindi stays fail-closed: a corrected
English line never keeps an unverified Hindi name.
"""
from __future__ import annotations

import copy
import json
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logger = logging.getLogger("agent.17c_static_gk_validator")


def _read(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def run(job_id: str) -> int:
    from agents.static_gk_validator import validate_edition
    from pipeline.state import write_json_atomic

    if os.getenv("ALP_STATIC_GK_VALIDATOR", "1") == "0":
        logger.info("[17c] disabled by ALP_STATIC_GK_VALIDATOR=0")
        return 0
    content_path = ROOT / "data" / "content" / f"{job_id}.json"
    mcq_path = ROOT / "data" / "mcq" / f"{job_id}.json"
    content = _read(content_path)
    if not isinstance(content, dict):
        logger.warning("[17c] content unreadable; edition continues without static GK validation")
        return 0
    mcq = _read(mcq_path) if mcq_path.is_file() else None
    before_c, before_m = copy.deepcopy(content), copy.deepcopy(mcq)
    report = validate_edition(content, mcq)
    content["static_gk_validation"] = {k: v for k, v in report.items() if k != "details"}
    # Hindi post-fix (glossary, mixed script, English leftovers, name spelling). Fail-closed per
    # line (an unrepairable Hindi line is blanked -> English-only); fail-open for the stage.
    if os.getenv("ALP_HINDI_POSTFIX", "1") != "0":
        try:
            from pipeline.hindi_postfix import budgeted_translators, fix_edition
            word_tr, line_tr = budgeted_translators()
            content["hindi_postfix"] = fix_edition(content, mcq, translator=word_tr, line_translator=line_tr)
        except Exception as exc:
            logger.warning("[17c] Hindi post-fix skipped (%s)", exc)
    try:
        write_json_atomic(content_path, content)
        if mcq is not None and mcq != before_m:
            write_json_atomic(mcq_path, mcq)
    except Exception as exc:  # fail open: keep the previous artifacts
        logger.warning("[17c] could not write validated artifacts (%s); edition continues unchanged", exc)
        try:
            write_json_atomic(content_path, before_c)
        except Exception:
            pass
        return 0
    try:
        out = ROOT / "logs" / "qa" / f"{job_id}_static_gk.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    logger.info("[17c] static GK: %s", content["static_gk_validation"])
    return 0


def main() -> int:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"),
                        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
    job_type = os.getenv("ALP_JOB_TYPE") or "daily"
    job_date = os.getenv("ALP_JOB_DATE") or ""
    job_id = os.getenv("ALP_JOB_ID") or f"{job_type}_{job_date}"
    try:
        return run(job_id)
    except Exception as exc:  # pragma: no cover - last-resort fail-open
        logger.warning("[17c] unexpected error, edition continues: %s", exc)
        return 0


if __name__ == "__main__":
    sys.exit(main())
