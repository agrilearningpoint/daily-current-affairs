# -*- coding: utf-8 -*-
"""
MCQ GENERATOR AGENT
Main focus: selected verified news से 12-15 MCQ बनाना।

Command:
> "Generate 12-15 MCQs ONLY from verified selected content. Types: direct/static-number, who-org, statement style. Options A-E max, exactly one correct taken verbatim from that news's own facts; distractors are real values from OTHER news (wrong for this question). Never auto-add 'None of these'. Never ask about unverified info."

Work: Deterministic fact-grounded MCQ
Real implementation — see pipeline/ library. Quality gates enforced; empty output = failure.
"""

COMMAND = """Generate 12-15 MCQs ONLY from verified selected content. Types: direct/static-number, who-org, statement style. Options A-E max, exactly one correct taken verbatim from that news's own facts; distractors are real values from OTHER news (wrong for this question). Never auto-add 'None of these'. Never ask about unverified info."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- pipeline.content.generate_mcqs(); writes data/mcq/<job_id>.json"""


class Agent:
    """MCQ GENERATOR AGENT — real implementation"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type
        self.context = context
        self.name = "MCQ GENERATOR AGENT"

    def run(self):
        import logging
        from pipeline.content import generate_mcqs
        from pipeline.state import CONTENT_DIR, MCQ_DIR, data_path, read_json, write_json_atomic
        c = read_json(data_path(CONTENT_DIR, self.job_id))
        mcqs = generate_mcqs(c["items"])
        n_items = len(c["items"])
        if len(mcqs) < min(8, n_items):
            self.context["stage_failed"] = f"only {len(mcqs)} MCQs generated for {n_items} news (need >=min(8,n))"
            raise RuntimeError(self.context["stage_failed"])
        write_json_atomic(data_path(MCQ_DIR, self.job_id), mcqs)
        save_state = None
        logging.info(f"[{self.name}] generated {len(mcqs)} MCQs")
        self.context["mcqs_generated"] = len(mcqs)
        return self.context

    def verify(self):
        return not self.context.get("stage_failed")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    ctx = {"job_id": "test_2026-10-04", "job_type": "daily", "job_date": "2026-10-04"}
    print(Agent("test_2026-10-04", "daily", ctx).run())
