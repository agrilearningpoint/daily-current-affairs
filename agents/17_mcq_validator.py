# -*- coding: utf-8 -*-
"""
MCQ VALIDATOR AGENT
Main focus: हर MCQ की accuracy validate करना — invalid कभी publish नहीं।

Command:
> "Validate every MCQ: options unique, <=5 options, answer index valid, correct option supported verbatim by its source text, explanation contains the answer value, no duplicate questions, no auto 'None of these', bilingual fields present. Rejected MCQs never reach the PDF."

Work: Full validator chain
Real implementation — see pipeline/ library. Quality gates enforced; empty output = failure.
"""

COMMAND = """Validate every MCQ: options unique, <=5 options, answer index valid, correct option supported verbatim by its source text, explanation contains the answer value, no duplicate questions, no auto 'None of these', bilingual fields present. Rejected MCQs never reach the PDF."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- pipeline.content.validate_mcqs(); writes data/mcq/<job_id>_validated.json; fails stage if <5 valid"""


class Agent:
    """MCQ VALIDATOR AGENT — real implementation"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type
        self.context = context
        self.name = "MCQ VALIDATOR AGENT"

    def run(self):
        import logging
        from pipeline.content import validate_mcqs
        from pipeline.state import CONTENT_DIR, MCQ_DIR, data_path, read_json, write_json_atomic, load_job, save_job
        mcqs = read_json(data_path(MCQ_DIR, self.job_id), [])
        c = read_json(data_path(CONTENT_DIR, self.job_id))
        valid, rejected = validate_mcqs(mcqs, c["items"])
        if rejected:
            logging.warning(f"[{self.name}] REJECTED {len(rejected)} MCQs: {[r['errors'] for r in rejected]}")
        if len(valid) < 5:
            self.context["stage_failed"] = f"only {len(valid)} valid MCQs after validation"
            raise RuntimeError(self.context["stage_failed"])
        write_json_atomic(data_path(MCQ_DIR, self.job_id, "_validated"), valid)
        save_job(load_job(self.job_id, self.job_type, self.context["job_date"]),
                 state="MCQ_VALIDATED", stage="17_mcq_validator", mcq_valid=len(valid), mcq_rejected=len(rejected))
        self.context["mcqs_valid"] = len(valid)
        return self.context

    def verify(self):
        return not self.context.get("stage_failed")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    ctx = {"job_id": "test_2026-10-04", "job_type": "daily", "job_date": "2026-10-04"}
    print(Agent("test_2026-10-04", "daily", ctx).run())
