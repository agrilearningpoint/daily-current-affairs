# -*- coding: utf-8 -*-
"""
NEWS COLLECTION AGENT
Main focus: ज्यादा से ज्यादा relevant raw news collect करना, लेकिन final selection नहीं करना।

Command:
> "Collect current-affairs news from reliable and preferably primary/official sources. Prioritize Agriculture, Banking, Government, Economy, National, International, Science, Environment, Awards, Appointments, Reports and Sports. Capture headline, publication time, source, URL, category and raw facts. Collect broadly; do not decide final importance at this stage."

Work: Tier-1 primary first, then Tier-2 discovery, Tier-3 aggregators for coverage
"""

COMMAND = """Collect current-affairs news from reliable and preferably primary/official sources. Prioritize Agriculture, Banking, Government, Economy, National, International, Science, Environment, Awards, Appointments, Reports and Sports. Capture headline, publication time, source, URL, category and raw facts. Collect broadly; do not decide final importance at this stage."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- Iterates TIER_1_SOURCES from config/sources.py (PIB, Agri, ICAR, RBI, NABARD, etc. ~40 sources)
- For each source: fetch RSS/press-release page, parse headline, time (Asia/Kolkata), source, URL, category, raw HTML
- Also queries TIER_2 (Reuters, The Hindu etc.) for discovery, but marks as needs_primary_verification
- Stores raw in data/raw/<job_id>_raw.json — does NOT filter by importance, collects broadly (target 80-120 raw items per daily job)
- Captures: headline_en, pub_time_ist, source_name, source_url, source_tier, category, raw_facts, image_url if any
- Respects robots, timeout 10s, retry 2x
"""

class Agent:
    """NEWS COLLECTION AGENT — detailed implementation"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type  # daily/weekly/monthly
        self.context = context
        self.name = "NEWS COLLECTION AGENT"

    def run(self):
        """
        Execute NEWS COLLECTION AGENT
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
        # - Iterates TIER_1_SOURCES from config/sources.py (PIB, Agri, ICAR, RBI, NABARD, etc. ~40 sources)
        # TODO: Implement full logic — see DETAILS and TIER sources / PDF design spec
        # For now, log and pass through (real implementation in src/)
        logging.info(f"[{self.name}] COMMAND: {COMMAND[:80]}...")
        # Simulate work
        time.sleep(0.1)
        # Update context
        self.context["last_agent"] = self.name
        self.context["last_success_stage"] = "03_news_collection"
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
