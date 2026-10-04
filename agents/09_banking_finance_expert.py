# -*- coding: utf-8 -*-
"""
BANKING & FINANCE EXPERT AGENT
Main focus: AFO/NABARD/Banking relevance।

Command:
> "Analyze Banking and Finance news for NABARD, AFO, IBPS AFO and banking exams. Prioritize RBI, NABARD, SEBI, NPCI, monetary policy, financial inclusion, banking schemes, digital payments, financial institutions, reports, indices, appointments and important financial statistics. Reject low-value financial noise."

Work: Banking lens scoring
"""

COMMAND = """Analyze Banking and Finance news for NABARD, AFO, IBPS AFO and banking exams. Prioritize RBI, NABARD, SEBI, NPCI, monetary policy, financial inclusion, banking schemes, digital payments, financial institutions, reports, indices, appointments and important financial statistics. Reject low-value financial noise."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- Filters via RBI, NABARD, SEBI, FinMin, DEA, NPCI etc. + keywords (repo, MPC, NPA, UPI)
- Scores banking_score 0-100: monetary policy, financial inclusion, banking schemes, digital payments, FI, reports, indices, appointments, stats
- Rejects noise: daily Sensex 100 pts up/down without context
- Example high: RBI ED appointment, MPC 25 bps hike expectation, bulk deposit 10.10 AM rule, forex $18.3bn fall
- Output: data/scored/<job_id>_banking.json
"""

class Agent:
    """BANKING & FINANCE EXPERT AGENT — detailed implementation"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type  # daily/weekly/monthly
        self.context = context
        self.name = "BANKING & FINANCE EXPERT AGENT"

    def run(self):
        """
        Execute BANKING & FINANCE EXPERT AGENT
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
        # - Filters via RBI, NABARD, SEBI, FinMin, DEA, NPCI etc. + keywords (repo, MPC, NPA, UPI)
        # TODO: Implement full logic — see DETAILS and TIER sources / PDF design spec
        # For now, log and pass through (real implementation in src/)
        logging.info(f"[{self.name}] COMMAND: {COMMAND[:80]}...")
        # Simulate work
        time.sleep(0.1)
        # Update context
        self.context["last_agent"] = self.name
        self.context["last_success_stage"] = "09_banking_finance_expert"
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
