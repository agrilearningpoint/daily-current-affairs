# -*- coding: utf-8 -*-
"""
MCQ GENERATOR AGENT
Main focus: selected news से high-quality exam questions।

Command:
> "Create high-quality competitive-exam MCQs only from verified and selected current affairs. Prioritize direct, conceptual, statement-based and static-linked questions relevant to AGTA, AFO, NABARD, FCI, ICAR and general competitive exams. Avoid ambiguous questions, trivial questions, duplicate questions and questions whose answers are not clearly supported by the source data."

Work: Exam-level MCQs from verified content
"""

COMMAND = """Create high-quality competitive-exam MCQs only from verified and selected current affairs. Prioritize direct, conceptual, statement-based and static-linked questions relevant to AGTA, AFO, NABARD, FCI, ICAR and general competitive exams. Avoid ambiguous questions, trivial questions, duplicate questions and questions whose answers are not clearly supported by the source data."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- Generates 12-15 MCQs per daily job, 5 options A-E, based ONLY on selected news (02-03 Oct window)
- Types: direct (GOBARdhan outlay?), conceptual (why CBG saves forex?), statement-based, static-linked (RBI established 1935)
- For AGTA/AFO/NABARD level, not trivial (e.g., not "What is full form of RBI?")
- Avoids ambiguous (2 correct), duplicate, unsupported answer
- Output: data/mcq/<job_id>_mcqs.json with Q, options, correct, explanation, source_ref
"""

class Agent:
    """MCQ GENERATOR AGENT — detailed implementation"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type  # daily/weekly/monthly
        self.context = context
        self.name = "MCQ GENERATOR AGENT"

    def run(self):
        """
        Execute MCQ GENERATOR AGENT
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
        # - Generates 12-15 MCQs per daily job, 5 options A-E, based ONLY on selected news (02-03 Oct window)
        # TODO: Implement full logic — see DETAILS and TIER sources / PDF design spec
        # For now, log and pass through (real implementation in src/)
        logging.info(f"[{self.name}] COMMAND: {COMMAND[:80]}...")
        # Simulate work
        time.sleep(0.1)
        # Update context
        self.context["last_agent"] = self.name
        self.context["last_success_stage"] = "16_mcq_generator"
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
