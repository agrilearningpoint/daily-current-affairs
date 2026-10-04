# -*- coding: utf-8 -*-
"""
DEDUPLICATION AGENT
Main focus: एक ही event की duplicate news merge करना (similarity > 0.85)।

Command:
> "Deduplicate verified news by event similarity (>0.85 token-shingle Jaccard). Merge duplicates keeping the authoritative (Tier-1) source and unioning reported facts without invention."

Work: Event clustering
Real implementation: pipeline/ library (state machine + quality gates). Empty stage output = FAILURE.
"""

COMMAND = """Deduplicate verified news by event similarity (>0.85 token-shingle Jaccard). Merge duplicates keeping the authoritative (Tier-1) source and unioning reported facts without invention."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- pipeline.scoring.deduplicate(threshold=0.85); keeps strongest source per cluster"""


class Agent:
    """DEDUPLICATION AGENT — real implementation"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type
        self.context = context
        self.name = "DEDUPLICATION AGENT"

    def run(self):
        import logging
        from pipeline.scoring import deduplicate
        from pipeline.state import VERIFIED_DIR, DEDUP_DIR, data_path, read_json, write_json_atomic, load_job, save_job
        items = read_json(data_path(VERIFIED_DIR, self.job_id), {"items": []})["items"]
        merged = deduplicate(items, threshold=0.85)
        logging.info(f"[{self.name}] {len(items)} -> {len(merged)} unique events")
        if len(merged) < 5:
            self.context["stage_failed"] = f"only {len(merged)} unique events after dedup"
            raise RuntimeError(self.context["stage_failed"])
        write_json_atomic(data_path(DEDUP_DIR, self.job_id), {"items": merged})
        save_job(load_job(self.job_id, self.job_type, self.context["job_date"]),
                 state="DEDUPLICATED", stage="05_deduplication", unique=len(merged))
        self.context["unique_events"] = len(merged)
        return self.context

    def verify(self):
        """QA check for this agent's output."""
        return not self.context.get("stage_failed")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    ctx = {"job_id": "test_2026-10-04", "job_type": "daily", "job_date": "2026-10-04"}
    print(Agent("test_2026-10-04", "daily", ctx).run())
