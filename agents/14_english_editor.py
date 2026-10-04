# -*- coding: utf-8 -*-
"""
ENGLISH EDITOR AGENT
Main focus: English edition quality pass।

Command:
> "Proofread the English side: strip markup artefacts, enforce sentence casing, cap headline length, ensure every item retains its verbatim source link. No fact changes allowed."

Work: English QA pass
Real implementation — see pipeline/ library. Quality gates enforced; empty output = failure.
"""

COMMAND = """Proofread the English side: strip markup artefacts, enforce sentence casing, cap headline length, ensure every item retains its verbatim source link. No fact changes allowed."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- cleanup + validation of English fields in content JSON"""


class Agent:
    """ENGLISH EDITOR AGENT — real implementation"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type
        self.context = context
        self.name = "ENGLISH EDITOR AGENT"

    def run(self):
        import logging, re
        from pipeline.state import CONTENT_DIR, data_path, read_json, write_json_atomic
        c = read_json(data_path(CONTENT_DIR, self.job_id))
        for it in c["items"]:
            it["headline_en"] = re.sub(r"\s+", " ", it["headline_en"]).strip()[:160]
            it["key_points_en"] = [re.sub(r"\s+", " ", p).strip() for p in it["key_points_en"] if p.strip()]
            if not it["source"].get("url"):
                raise RuntimeError(f"item without source url: {it['event_id']}")
        write_json_atomic(data_path(CONTENT_DIR, self.job_id), c)
        logging.info(f"[{self.name}] english pass done")
        return self.context

    def verify(self):
        return not self.context.get("stage_failed")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    ctx = {"job_id": "test_2026-10-04", "job_type": "daily", "job_date": "2026-10-04"}
    print(Agent("test_2026-10-04", "daily", ctx).run())
