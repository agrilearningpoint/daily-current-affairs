# -*- coding: utf-8 -*-
"""
SCHEDULER AGENT
Main focus: job window (daily 24h / weekly / monthly) तय करना और schedule validate करना।

Command:
> "Determine the collection window for this job type in Asia/Kolkata and validate the schedule request."

Work: Window planner
Real implementation: pipeline/ library (state machine + quality gates). Empty stage output = FAILURE.
"""

COMMAND = """Determine the collection window for this job type in Asia/Kolkata and validate the schedule request."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- daily = last 24h ending 06:00 IST; weekly = last 7 days; monthly = full calendar month."""


class Agent:
    """SCHEDULER AGENT — real implementation"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type
        self.context = context
        self.name = "SCHEDULER AGENT"

    def run(self):
        from pipeline.collector import collect_window
        start, end = collect_window(self.job_type, self.context["job_date"])
        self.context["window_start"] = start.isoformat()
        self.context["window_end"] = end.isoformat()
        from pipeline.state import load_job, save_job
        save_job(load_job(self.job_id, self.job_type, self.context["job_date"]),
                 stage="02_scheduler")
        return self.context

    def verify(self):
        """QA check for this agent's output."""
        return not self.context.get("stage_failed")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    ctx = {"job_id": "test_2026-10-04", "job_type": "daily", "job_date": "2026-10-04"}
    print(Agent("test_2026-10-04", "daily", ctx).run())
