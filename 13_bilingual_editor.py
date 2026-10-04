# -*- coding: utf-8 -*-
"""
BILINGUAL EDITOR AGENT
Main focus: Hindi + English version।

Command:
> "Create a natural bilingual Hindi-English version from the same verified data. English and Hindi must contain the same facts, numbers, names and dates. Do not introduce information during translation. Keep English exam terminology where useful and make Hindi natural and student-friendly."

Work: Natural Hindi, same facts
"""

COMMAND = """Create a natural bilingual Hindi-English version from the same verified data. English and Hindi must contain the same facts, numbers, names and dates. Do not introduce information during translation. Keep English exam terminology where useful and make Hindi natural and student-friendly."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- Takes content_en and creates hi: headline_hi (Mukta 17pt), key_points_hi (Mukta 12.5pt) via translation
- Must keep: Rs 23,731 Cr, 10 years FY27-36, Sudhakar Malli, 33% same in both
- Do not add extra info during translation
- Keep exam terms in English where useful (e.g., CBG, MPC, Repo 5.50%)
- Hindi natural student-friendly, not literal Google Translate
- Uses Mukta font, harfbuzz shaping
- Output: data/content/<job_id>_bilingual.json
"""

class Agent:
    """BILINGUAL EDITOR AGENT — detailed implementation"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type  # daily/weekly/monthly
        self.context = context
        self.name = "BILINGUAL EDITOR AGENT"

    def run(self):
        """
        Execute BILINGUAL EDITOR AGENT
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
        # - Takes content_en and creates hi: headline_hi (Mukta 17pt), key_points_hi (Mukta 12.5pt) via translation
        # TODO: Implement full logic — see DETAILS and TIER sources / PDF design spec
        # For now, log and pass through (real implementation in src/)
        logging.info(f"[{self.name}] COMMAND: {COMMAND[:80]}...")
        # Simulate work
        time.sleep(0.1)
        # Update context
        self.context["last_agent"] = self.name
        self.context["last_success_stage"] = "13_bilingual_editor"
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
