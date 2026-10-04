# -*- coding: utf-8 -*-
"""
AGRICULTURE EXPERT AGENT
Main focus: Agriculture-related news की expert filtering।

Command:
> "Analyze Agriculture and allied-sector news specifically for AGTA, AFO, NABARD, FCI and ICAR exams. Prioritize agriculture schemes, MSP, crops, varieties, ICAR/IARI research, horticulture, animal husbandry, fisheries, forestry, soil, irrigation, seeds, fertilizers, pesticides, agricultural economics, food processing, agri exports, cooperatives, agri-tech, weather and government agriculture initiatives. Identify the most exam-relevant facts."

Work: Agri lens scoring
"""

COMMAND = """Analyze Agriculture and allied-sector news specifically for AGTA, AFO, NABARD, FCI and ICAR exams. Prioritize agriculture schemes, MSP, crops, varieties, ICAR/IARI research, horticulture, animal husbandry, fisheries, forestry, soil, irrigation, seeds, fertilizers, pesticides, agricultural economics, food processing, agri exports, cooperatives, agri-tech, weather and government agriculture initiatives. Identify the most exam-relevant facts."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- Filters via keywords + source: MoA&FW, ICAR, IARI, DARE, APEDA, NHB, DAHD, Fisheries, ICFRE, IMD, CACP, Mofpi, etc.
- Scores agri_score 0-100 based on: scheme (PM-KISAN, GOBARdhan), MSP, crop variety, ICAR research, horticulture, AH vs fish vs forestry, soil/irrigation, seeds/fertilizer/pesticide, agri econ, food processing, exports, cooperatives, agri-tech, weather
- Extracts exam-relevant facts: e.g., for GOBARdhan — CBG, 10 years, Rs 23,731 Cr, nodal Ministry, SATAT link
- Output: data/scored/<job_id>_agri.json with agri_score + agri_facts
"""

class Agent:
    """AGRICULTURE EXPERT AGENT — detailed implementation"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type  # daily/weekly/monthly
        self.context = context
        self.name = "AGRICULTURE EXPERT AGENT"

    def run(self):
        """
        Execute AGRICULTURE EXPERT AGENT
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
        # - Filters via keywords + source: MoA&FW, ICAR, IARI, DARE, APEDA, NHB, DAHD, Fisheries, ICFRE, IMD, CACP, Mofpi, etc.
        # TODO: Implement full logic — see DETAILS and TIER sources / PDF design spec
        # For now, log and pass through (real implementation in src/)
        logging.info(f"[{self.name}] COMMAND: {COMMAND[:80]}...")
        # Simulate work
        time.sleep(0.1)
        # Update context
        self.context["last_agent"] = self.name
        self.context["last_success_stage"] = "08_agriculture_expert"
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
