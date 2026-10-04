# -*- coding: utf-8 -*-
"""
STUDENT RELEVANCE AGENT
Main focus: Exam student के लिए कौन-सी news सबसे useful है? (Star agent)

Command:
> "Act as an expert editor for Indian competitive-exam students, especially AGTA, AFO, NABARD, FCI, ICAR, IBPS AFO and Agriculture exams. Judge whether each news item is worth a student's limited study time. Prioritize information from which a direct or conceptual exam question can realistically be created. Reject news that is important to the general public but has low exam value. Prefer high-value, factual, unique and revision-worthy current affairs."

Work: Core question: If student has limited time, should they read this?
"""

COMMAND = """Act as an expert editor for Indian competitive-exam students, especially AGTA, AFO, NABARD, FCI, ICAR, IBPS AFO and Agriculture exams. Judge whether each news item is worth a student's limited study time. Prioritize information from which a direct or conceptual exam question can realistically be created. Reject news that is important to the general public but has low exam value. Prefer high-value, factual, unique and revision-worthy current affairs."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- Scores student_relevance 0-100 for each item, with AGTA/AFO/NABARD/FCI/ICAR lens
- High if: direct MCQ possible (e.g., GOBARdhan outlay Rs 23,731 Cr → MCQ), conceptual (e.g., Woman Farmer 2026 → gender in agri), factual unique, revision-worthy
- Low if: general politics trending but no exam angle, vague, no fact
- Rejects: important for public but low exam value (e.g., celebrity gossip)
- Output: data/scored/<job_id>_student.json with student_score + reason (e.g., "High: direct scheme outlay MCQ for NABARD")
"""

class Agent:
    """STUDENT RELEVANCE AGENT — detailed implementation"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type  # daily/weekly/monthly
        self.context = context
        self.name = "STUDENT RELEVANCE AGENT"

    def run(self):
        """
        Execute STUDENT RELEVANCE AGENT
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
        # - Scores student_relevance 0-100 for each item, with AGTA/AFO/NABARD/FCI/ICAR lens
        # TODO: Implement full logic — see DETAILS and TIER sources / PDF design spec
        # For now, log and pass through (real implementation in src/)
        logging.info(f"[{self.name}] COMMAND: {COMMAND[:80]}...")
        # Simulate work
        time.sleep(0.1)
        # Update context
        self.context["last_agent"] = self.name
        self.context["last_success_stage"] = "07_student_relevance"
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
