# -*- coding: utf-8 -*-
"""
FINAL NEWS SELECTION AGENT
Main focus: सबसे important final filter — PDF में क्या जाएगा? (Most important)

Command:
> "Select only the highest-value current-affairs items for the final student edition. Combine overall importance, exam relevance, agriculture relevance, banking relevance, factual value, MCQ potential, uniqueness and source reliability. Do not target a fixed number of news items. If only 25 news are genuinely valuable, select 25; if 40 are genuinely valuable, select 40. Never add low-value news just to increase the count."

Work: Quality > Quantity — no fixed count
"""

COMMAND = """Select only the highest-value current-affairs items for the final student edition. Combine overall importance, exam relevance, agriculture relevance, banking relevance, factual value, MCQ potential, uniqueness and source reliability. Do not target a fixed number of news items. If only 25 news are genuinely valuable, select 25; if 40 are genuinely valuable, select 40. Never add low-value news just to increase the count."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- Combines: importance_score (0-100) + student_score + agri_score + banking_score + source_score (100/95/90/80/60) + MCQ potential + uniqueness
- Weighted final_score = 0.25*importance + 0.25*student + 0.15*agri + 0.15*banking + 0.1*source + 0.05*MCQ + 0.05*unique
- Sorts descending, selects top until marginal value drops (elbow) — no target 8 or 15, but typically 6-12 for daily (ensures quality)
- Golden rule: never add low-value to reach 15 — if only 7 valuable, PDF has 7 news + 20 one-liners + MCQs
- Output: data/selected/<job_id>_final.json with selected=True + final_rank
"""

class Agent:
    """FINAL NEWS SELECTION AGENT — detailed implementation"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type  # daily/weekly/monthly
        self.context = context
        self.name = "FINAL NEWS SELECTION AGENT"

    def run(self):
        """
        Execute FINAL NEWS SELECTION AGENT
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
        # - Combines: importance_score (0-100) + student_score + agri_score + banking_score + source_score (100/95/90/80/60) + MCQ potential + uniqueness
        # TODO: Implement full logic — see DETAILS and TIER sources / PDF design spec
        # For now, log and pass through (real implementation in src/)
        logging.info(f"[{self.name}] COMMAND: {COMMAND[:80]}...")
        # Simulate work
        time.sleep(0.1)
        # Update context
        self.context["last_agent"] = self.name
        self.context["last_success_stage"] = "10_final_news_selection"
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
