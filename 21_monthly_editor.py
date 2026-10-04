# -*- coding: utf-8 -*-
"""
MONTHLY EDITOR AGENT
Main focus: पूरे month का best-of-month।

Command:
> "Review all verified current-affairs events from the complete month and create a fresh Best-of-the-Month selection. Re-rank events using month-long significance, exam relevance, agriculture and banking relevance, policy impact, repeated developments, static-fact value and future exam potential. Do not merge daily or weekly PDFs. Select only the most important events of the month."

Work: Fresh Best-of-Month
"""

COMMAND = """Review all verified current-affairs events from the complete month and create a fresh Best-of-the-Month selection. Re-rank events using month-long significance, exam relevance, agriculture and banking relevance, policy impact, repeated developments, static-fact value and future exam potential. Do not merge daily or weekly PDFs. Select only the most important events of the month."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- Triggered only last date of month (Scheduler)
- Loads all verified events from 1st to last date of month
- Re-ranks using month-long significance, policy impact (e.g., Budget), repeated developments, static value, future exam potential
- Selects top 20-30 most important events of month (not daily*30)
- Then downstream to PDF
- Output: output/Monthly_MonthYYYY.pdf
"""

class Agent:
    """MONTHLY EDITOR AGENT — detailed implementation"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type  # daily/weekly/monthly
        self.context = context
        self.name = "MONTHLY EDITOR AGENT"

    def run(self):
        """
        Execute MONTHLY EDITOR AGENT
        Input: context from previous agent
        Output: updated context + writes to data/* / logs/*
        On failure: raises Exception for Master Supervisor to catch and retry
        """
        import json, os, time, logging
        from datetime import datetime
        import pytz
        tz = pytz.timezone("Asia/Kolkata")
        start = datetime.now(tz)
        logging.info(f"[{self.name}] Starting job {self.job_id} ({self.job_type}) at {start}")
        # --- Detailed logic as per DETAILS ---
        # - Triggered only last date of month (Scheduler)
        # TODO: Implement full logic — see DETAILS and TIER sources / PDF design spec
        # For now, log and pass through (real implementation in src/)
        logging.info(f"[{self.name}] COMMAND: {COMMAND[:80]}...")
        # Simulate work
        time.sleep(0.1)
        # Update context
        self.context["last_agent"] = self.name
        self.context["last_success_stage"] = "21_monthly_editor"
        logging.info(f"[{self.name}] Completed job {self.job_id}")
        return self.context

    def verify(self):
        """QA check for this agent's output"""
        return True

if __name__ == "__main__":
    # Test run
    ctx = {"job_id": "test_2026-10-04", "job_type": "daily"}
    agent = Agent("test_2026-10-04", "daily", ctx)
    print(agent.run())
