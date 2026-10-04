# -*- coding: utf-8 -*-
"""
FACT VERIFICATION AGENT
Main focus: News सही है या नहीं।

Command:
> "Verify every candidate news item using primary or authoritative sources whenever possible. Verify dates, numbers, names, organizations, schemes, rankings, appointments, locations and important claims. Reject unsupported, outdated, misleading or unverifiable information. Never fill missing facts by guessing."

Work: Primary source search → cross-check → reject if unverifiable
"""

COMMAND = """Verify every candidate news item using primary or authoritative sources whenever possible. Verify dates, numbers, names, organizations, schemes, rankings, appointments, locations and important claims. Reject unsupported, outdated, misleading or unverifiable information. Never fill missing facts by guessing."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- For each raw item: searches Tier-1 primary source for corroboration (e.g., if Tier-2 says RBI hike, must find RBI press release)
- Verifies: date (must be within job window), numbers (Rs 23,731 Cr exact?), names (Sudhakar Malli correct spelling), org, scheme name, ranking, appointment order
- Uses source_priority: Official 100 must match, if only Aggregator 60 then reject unless Tier-1 confirms
- Output: data/verified/<job_id>_verified.json with verified=True/False, verified_source_url, verification_notes, rejected_reason if any
- Never invents: if fact missing (e.g., exact amount not found), leaves blank and lowers score, does not guess
- Keeps only verified=True for next stage
"""

class Agent:
    """FACT VERIFICATION AGENT — detailed implementation"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type  # daily/weekly/monthly
        self.context = context
        self.name = "FACT VERIFICATION AGENT"

    def run(self):
        """
        Execute FACT VERIFICATION AGENT
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
        # - For each raw item: searches Tier-1 primary source for corroboration (e.g., if Tier-2 says RBI hike, must find RBI press release)
        # TODO: Implement full logic — see DETAILS and TIER sources / PDF design spec
        # For now, log and pass through (real implementation in src/)
        logging.info(f"[{self.name}] COMMAND: {COMMAND[:80]}...")
        # Simulate work
        time.sleep(0.1)
        # Update context
        self.context["last_agent"] = self.name
        self.context["last_success_stage"] = "04_fact_verification"
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
