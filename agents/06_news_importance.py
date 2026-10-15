# -*- coding: utf-8 -*-
"""
NEWS IMPORTANCE AGENT
Main focus: har event ko 0-100 multi-factor score dena.

Command:
> "Score every deduplicated event 0-100 using the factor weights:
   national impact 20, government policy 15, economy 15, agriculture 15,
   banking 10, student exam relevance 10, future importance 5,
   static fact value 5, uniqueness 5 — then weight by source reliability (SOURCE_SCORE)."

Work: Multi-factor ranking
Real implementation — see pipeline/ library. Quality gates enforced; empty output = failure.
"""
import os
import sys
from pathlib import Path

# Ensure repo root is importable (fixes 'No module named pipeline' when run from agents/)
_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

COMMAND = """Score every deduplicated event 0-100 using the factor weights: national impact 20, government policy 15, economy 15, agriculture 15, banking 10, student exam relevance 10, future importance 5, static fact value 5, uniqueness 5 — then weight by source reliability (SOURCE_SCORE)."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- pipeline.scoring.score_all(): keyword-evidence factor scores + source-reliability multiplier
- Writes data/scored/<job_id>.json sorted by importance_score"""


class Agent:
    """NEWS IMPORTANCE AGENT — real implementation"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type
        self.context = context
        self.name = "NEWS IMPORTANCE AGENT"

    def run(self):
        import logging
        from pipeline.scoring import score_all
        from pipeline.state import DEDUP_DIR, SCORED_DIR, data_path, read_json, write_json_atomic
        from pipeline.artifacts import read_news_items
        items = read_news_items(data_path(DEDUP_DIR, self.job_id))
        scored = score_all(items)
        logging.info(f"[{self.name}] scored {len(scored)} events, top={scored[0]['importance_score'] if scored else 0}")
        if len(scored) < 1:
            self.context["stage_failed"] = "scoring produced <1 events"
            raise RuntimeError(self.context["stage_failed"])
        write_json_atomic(data_path(SCORED_DIR, self.job_id), {"items": scored})
        self.context["scored"] = len(scored)
        return self.context

    def verify(self):
        return not self.context.get("stage_failed")


# =============================================================================
# STANDALONE ENTRYPOINT — uses real job context from env vars
# =============================================================================
if __name__ == "__main__":
    import logging

    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )

    # Load job context — prefer pipeline.agent_context, fallback to env vars
    _job_id = _job_date = _job_type = None
    try:
        from pipeline.agent_context import get_context
        _ctx_obj = get_context()
        _job_id = _ctx_obj.job_id
        _job_date = _ctx_obj.job_date
        _job_type = _ctx_obj.job_type
    except Exception:
        pass

    if not _job_id:
        _job_id = os.getenv("ALP_JOB_ID") or os.getenv("JOB_ID") or ""
    if not _job_type:
        _job_type = os.getenv("ALP_JOB_TYPE") or os.getenv("JOB_TYPE") or "daily"
    if not _job_date:
        _job_date = os.getenv("ALP_JOB_DATE") or ""
        if not _job_date and _job_id and "_" in _job_id:
            _job_date = _job_id.split("_", 1)[1]

    if not _job_date:
        from datetime import datetime, timezone
        _job_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not _job_id:
        _job_id = f"{_job_type}_{_job_date}"

    print(f"[06_news_importance] job={_job_id} type={_job_type} date={_job_date}")

    _context = {"job_id": _job_id, "job_type": _job_type, "job_date": _job_date}
    _exit = 0
    try:
        _result = Agent(_job_id, _job_type, _context).run()
        print(f"[06] OK — scored={_context.get('scored', '?')}")
    except Exception as exc:
        print(f"[06] FAILED: {exc}", file=sys.stderr)
        _exit = 1

    sys.exit(_exit)