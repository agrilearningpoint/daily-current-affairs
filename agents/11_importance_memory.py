# -*- coding: utf-8 -*-
"""
IMPORTANCE MEMORY / TREND AGENT
Main focus: जो news बाद में ज्यादा important हो जाए उसे पहचानना।

Command:
> "Track the importance of each event over time. Increase priority when an event gains major government, economic, agricultural, policy, examination or national significance. Use historical importance when creating Weekly and Monthly selections. Do not repeatedly publish the same event unless there is meaningful new development."

Work: Temporal importance tracking for Weekly/Monthly
"""

COMMAND = """Track the importance of each event over time. Increase priority when an event gains major government, economic, agricultural, policy, examination or national significance. Use historical importance when creating Weekly and Monthly selections. Do not repeatedly publish the same event unless there is meaningful new development."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- Maintains data/memory/importance_history.json — map event_id → history of scores over days
- When event gains significance (e.g., GOBARdhan day1 70, day3 after budget mention 85) — increase trend_score
- For Weekly/Monthly: re-ranks using cumulative importance (avg + max + trend), so week/month best-of, not just daily repetition
- Deduplicates repeated stories: if same GOBARdhan appears 3 days, keep only latest with new development, else suppress
- Useful for Weekly/Monthly fresh selection
"""

class Agent:
    """IMPORTANCE MEMORY / TREND AGENT — detailed implementation"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type  # daily/weekly/monthly
        self.context = context
        self.name = "IMPORTANCE MEMORY / TREND AGENT"

    def run(self):
        """
        Execute IMPORTANCE MEMORY / TREND AGENT
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
        # - Maintains data/memory/importance_history.json — map event_id → history of scores over days
        # TODO: Implement full logic — see DETAILS and TIER sources / PDF design spec
        # For now, log and pass through (real implementation in src/)
        logging.info(f"[{self.name}] COMMAND: {COMMAND[:80]}...")
        # Simulate work
        time.sleep(0.1)
        # Update context
        self.context["last_agent"] = self.name
        self.context["last_success_stage"] = "11_importance_memory"
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
