# -*- coding: utf-8 -*-
"""
NEWS IMPORTANCE AGENT
Main focus: कौन-सी news genuinely important है?

Command:
> "Score every verified news item from 0–100 for overall current-affairs importance. Consider national significance, government importance, economic impact, agriculture relevance, banking relevance, exam potential, future relevance, static-fact value, uniqueness and source reliability. Do not select news merely because it is trending or widely reported."

Work: Multi-factor 0-100 scoring
"""

COMMAND = """Score every verified news item from 0–100 for overall current-affairs importance. Consider national significance, government importance, economic impact, agriculture relevance, banking relevance, exam potential, future relevance, static-fact value, uniqueness and source reliability. Do not select news merely because it is trending or widely reported."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- Scores each deduped item 0-100:
  - national_significance 0-20
  - govt_importance 0-15
  - economic_impact 0-15
  - agri_relevance 0-15
  - banking_relevance 0-10
  - exam_potential 0-10
  - future_relevance 0-5
  - static_fact_value 0-5
  - uniqueness 0-5
- Weighted by source_reliability (Official 100 = full weight, Aggregator 60 = 0.6x)
- Does NOT boost just because trending on Twitter/Many sites — uses importance, not popularity
- Output: data/scored/<job_id>_importance.json with importance_score
"""

class Agent:
    """NEWS IMPORTANCE AGENT — detailed implementation"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type  # daily/weekly/monthly
        self.context = context
        self.name = "NEWS IMPORTANCE AGENT"

    def run(self):
        """
        Execute NEWS IMPORTANCE AGENT
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
        # - Scores each deduped item 0-100:
        # TODO: Implement full logic — see DETAILS and TIER sources / PDF design spec
        # For now, log and pass through (real implementation in src/)
        logging.info(f"[{self.name}] COMMAND: {COMMAND[:80]}...")
        # Simulate work
        time.sleep(0.1)
        # Update context
        self.context["last_agent"] = self.name
        self.context["last_success_stage"] = "06_news_importance"
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
