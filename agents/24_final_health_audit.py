# -*- coding: utf-8 -*-
"""
FINAL HEALTH AUDIT AGENT
Main focus: पूरी pipeline की monitoring, timeout detection और recovery।

Command:
> "Final health audit of the job: state must be PIN_VERIFIED→COMPLETE path, all artefacts exist (raw/verified/dedup/scored/selected/content/mcq/pdf/qa report), PDF size sane, QA approved. On anomalies: mark job, alert admin via Telegram DM (ADMIN_ID). Also runs standalone every 5 min via .github/workflows/watchdog.yml (python main.py --watchdog)."

Work: Real end-to-end audit + alerting
Real implementation — see pipeline/ library. Quality gates enforced; empty output = failure.
"""

COMMAND = """Final health audit of the job: state must be PIN_VERIFIED→COMPLETE path, all artefacts exist (raw/verified/dedup/scored/selected/content/mcq/pdf/qa report), PDF size sane, QA approved. On anomalies: mark job, alert admin via Telegram DM (ADMIN_ID). Also runs standalone every 5 min via .github/workflows/watchdog.yml (python main.py --watchdog)."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- validates every artefact + job state machine
- sends watchdog alerts through pipeline.telegram_api.alert_admin"""


class Agent:
    """FINAL HEALTH AUDIT AGENT — real implementation"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type
        self.context = context
        self.name = "FINAL HEALTH AUDIT AGENT"

    def run(self):
        import logging, os
        from pipeline.state import (load_job, save_job, RAW_DIR, VERIFIED_DIR, DEDUP_DIR, SCORED_DIR,
                                    SELECTED_DIR, CONTENT_DIR, MCQ_DIR, QA_LOG_DIR, OUTPUT_DIR,
                                    data_path, read_json)
        from pipeline.telegram_api import alert_admin
        job = load_job(self.job_id, self.job_type, self.context["job_date"])
        problems = []
        need = [("raw", data_path(RAW_DIR, self.job_id)), ("verified", data_path(VERIFIED_DIR, self.job_id)),
                ("dedup", data_path(DEDUP_DIR, self.job_id)), ("scored", data_path(SCORED_DIR, self.job_id)),
                ("selected", data_path(SELECTED_DIR, self.job_id)), ("content", data_path(CONTENT_DIR, self.job_id)),
                ("mcq_validated", data_path(MCQ_DIR, self.job_id, "_validated")),
                ("qa_report", data_path(QA_LOG_DIR, self.job_id))]
        for nm, p in need:
            if not os.path.exists(p):
                problems.append(f"missing artefact: {nm}")
        qa = read_json(data_path(QA_LOG_DIR, self.job_id), {})
        if not qa.get("approved"):
            problems.append("QA report not APPROVED")
        pdf = self.context.get("pdf_path", "")
        if not (os.path.exists(pdf) and os.path.getsize(pdf) > 20000):
            problems.append("PDF missing/too small")
        if job.get("status") != "PIN_VERIFIED":
            problems.append(f"unexpected state at watchdog: {job.get('status')}")
        if problems:
            alert_admin(f"⚠️ {self.job_id} watchdog found: " + "; ".join(problems))
            self.context["stage_failed"] = "watchdog audit failed: " + "; ".join(problems)
            raise RuntimeError(self.context["stage_failed"])
        save_job(job, stage="24_final_health_audit", watchdog="healthy")
        logging.info(f"[{self.name}] audit PASSED for {self.job_id}")
        return self.context

    def verify(self):
        return not self.context.get("stage_failed")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    ctx = {"job_id": "test_2026-10-04", "job_type": "daily", "job_date": "2026-10-04"}
    print(Agent("test_2026-10-04", "daily", ctx).run())
