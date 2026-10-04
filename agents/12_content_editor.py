# -*- coding: utf-8 -*-
"""
CONTENT EDITOR AGENT
Main focus: selected news को student-friendly बनाना।

Command:
> "Convert only selected and verified news into concise, exam-oriented current-affairs content following the reference PDF structure: Headline → Key Points → Static Facts → Exam Fact → Explanation where useful. Preserve factual accuracy. Do not add unsupported information. Keep the content easy to revise and avoid unnecessary storytelling."

Work: Headline → Key Points → Static Facts → Exam Fact
"""

COMMAND = """Convert only selected and verified news into concise, exam-oriented current-affairs content following the reference PDF structure: Headline → Key Points → Static Facts → Exam Fact → Explanation where useful. Preserve factual accuracy. Do not add unsupported information. Keep the content easy to revise and avoid unnecessary storytelling."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- For each selected item: writes headline_en (18pt style), key_points_en (3-4 bullets, 12pt), static_facts dict (for table), exam_fact_en (12.5pt yellow box)
- Follows reference PDF structure exactly, no storytelling fluff
- Preserves facts: numbers, names, dates exact from verified source, no hallucination
- Output: data/content/<job_id>_content.json — bilingual source for next agents (en only, hi via next agent)
"""

class Agent:
    """CONTENT EDITOR AGENT — detailed implementation"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type  # daily/weekly/monthly
        self.context = context
        self.name = "CONTENT EDITOR AGENT"

    def run(self):
        """
        Execute CONTENT EDITOR AGENT
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
        # - For each selected item: writes headline_en (18pt style), key_points_en (3-4 bullets, 12pt), static_facts dict (for table), exam_fact_en (12.5pt yellow box)
        # TODO: Implement full logic — see DETAILS and TIER sources / PDF design spec
        # For now, log and pass through (real implementation in src/)
        logging.info(f"[{self.name}] COMMAND: {COMMAND[:80]}...")
        # Simulate work
        time.sleep(0.1)
        # Update context
        self.context["last_agent"] = self.name
        self.context["last_success_stage"] = "12_content_editor"
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
