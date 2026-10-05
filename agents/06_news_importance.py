# -*- coding: utf-8 -*-
"""
NEWS IMPORTANCE AGENT
Main focus: हर event को 0-100 multi-factor score देना।

Command:
> "Score every deduplicated event 0-100 using the factor weights: national impact 20, government policy 15, economy 15, agriculture 15, banking 10, student exam relevance 10, future importance 5, static fact value 5, uniqueness 5 — then weight by source reliability (SOURCE_SCORE)."

Work: Multi-factor ranking
Real implementation — see pipeline/ library. Quality gates enforced; empty output = failure.
"""

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
        items = read_json(data_path(DEDUP_DIR, self.job_id), {"items": []})["items"]
        scored = score_all(items)
        logging.info(f"[{self.name}] scored {len(scored)} events, top={scored[0]['importance_score'] if scored else 0}")
        if len(scored) < 1:
            self.context["stage_failed"] = "scoring produced <5 events"
            raise RuntimeError(self.context["stage_failed"])
        write_json_atomic(data_path(SCORED_DIR, self.job_id), {"items": scored})
        self.context["scored"] = len(scored)
        return self.context

    def verify(self):
        return not self.context.get("stage_failed")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    ctx = {"job_id": "test_2026-10-04", "job_type": "daily", "job_date": "2026-10-04"}
    print(Agent("test_2026-10-04", "daily", ctx).run())
