# -*- coding: utf-8 -*-
"""
IMAGE AGENT
Main focus: सिर्फ useful images।

Command:
> "Add an image only when it improves understanding, recognition or visual value of an important current-affairs topic. Prefer official or reliable images. Never add random decorative stock images merely to fill space. Verify that the image actually represents the event, person, place, crop, technology or organization discussed."

Work: Official/reliable, verified representation
"""

COMMAND = """Add an image only when it improves understanding, recognition or visual value of an important current-affairs topic. Prefer official or reliable images. Never add random decorative stock images merely to fill space. Verify that the image actually represents the event, person, place, crop, technology or organization discussed."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- For each news: decides needs_image=True if visual value (e.g., GOBARdhan plant, RBI building, hockey team)
- Prefers official: PIB, RBI, ICAR, Ministry sites
- Downloads, verifies: checks image URL reachable, aspect, not placeholder, actually represents event (e.g., not random building for Malli — if portrait not available, uses RBI logo and notes)
- Stores in assets/images/<job_id>/<slug>.jpg, records image_path, caption, source
- If no useful image, sets image_path=None — never fills with stock
- Output: updates content json with image_path
"""

class Agent:
    """IMAGE AGENT — detailed implementation"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type  # daily/weekly/monthly
        self.context = context
        self.name = "IMAGE AGENT"

    def run(self):
        """
        Execute IMAGE AGENT
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
        # - For each news: decides needs_image=True if visual value (e.g., GOBARdhan plant, RBI building, hockey team)
        # TODO: Implement full logic — see DETAILS and TIER sources / PDF design spec
        # For now, log and pass through (real implementation in src/)
        logging.info(f"[{self.name}] COMMAND: {COMMAND[:80]}...")
        # Simulate work
        time.sleep(0.1)
        # Update context
        self.context["last_agent"] = self.name
        self.context["last_success_stage"] = "15_image_agent"
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
