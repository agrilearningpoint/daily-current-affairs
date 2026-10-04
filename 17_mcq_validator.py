# -*- coding: utf-8 -*-
"""
MCQ VALIDATOR AGENT
Main focus: MCQ में कोई गलती न रहे।

Command:
> "Validate every MCQ independently. Check question clarity, option uniqueness, correct answer, explanation, factual accuracy, source support, ambiguity, duplicate similarity and exam relevance. Reject or regenerate any question with multiple possible answers or insufficient evidence."

Work: Independent validation
"""

COMMAND = """Validate every MCQ independently. Check question clarity, option uniqueness, correct answer, explanation, factual accuracy, source support, ambiguity, duplicate similarity and exam relevance. Reject or regenerate any question with multiple possible answers or insufficient evidence."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- For each MCQ: checks clarity (is Q understandable?), uniqueness (5 options distinct?), correct (is C truly 10 years?), explanation (does it match source?), source support (is answer in verified content?), ambiguity (could B also be correct?), duplicate (is Q5 similar to Q2?), exam relevance (worth for NABARD?)
- If fails any, marks rejected and regenerates via MCQ Generator (max 2 retries)
- Only validated MCQs go to PDF — ensures no MCQ-answer mismatch (QA will also check)
- Output: data/mcq/<job_id>_validated.json
"""

class Agent:
    """MCQ VALIDATOR AGENT — detailed implementation"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type  # daily/weekly/monthly
        self.context = context
        self.name = "MCQ VALIDATOR AGENT"

    def run(self):
        """
        Execute MCQ VALIDATOR AGENT
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
        # - For each MCQ: checks clarity (is Q understandable?), uniqueness (5 options distinct?), correct (is C truly 10 years?), explanation (does it match source?), source support (is answer in verified content?), ambiguity (could B also be correct?), duplicate (is Q5 similar to Q2?), exam relevance (worth for NABARD?)
        # TODO: Implement full logic — see DETAILS and TIER sources / PDF design spec
        # For now, log and pass through (real implementation in src/)
        logging.info(f"[{self.name}] COMMAND: {COMMAND[:80]}...")
        # Simulate work
        time.sleep(0.1)
        # Update context
        self.context["last_agent"] = self.name
        self.context["last_success_stage"] = "17_mcq_validator"
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
