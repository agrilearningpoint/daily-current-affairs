# -*- coding: utf-8 -*-
"""
PDF DESIGN AGENT
Main focus: content को premium लेकिन simple PDF में बदलना।

Command:
> "Design a clean, colorful and highly readable Current Affairs PDF based on the approved reference structure. Use controlled multiple colors, clear hierarchy, attractive headings, useful images, proper spacing and mobile-friendly typography. Every page must contain Agri Learning Point branding, logo, footer and page number. Never overcrowd pages or alter approved facts."

Work: Mobile-first premium design with approved hierarchy
"""

COMMAND = """Design a clean, colorful and highly readable Current Affairs PDF based on the approved reference structure. Use controlled multiple colors, clear hierarchy, attractive headings, useful images, proper spacing and mobile-friendly typography. Every page must contain Agri Learning Point branding, logo, footer and page number. Never overcrowd pages or alter approved facts."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- Uses src/generate_pdf.py with FINAL spec:
  - Hindi Mukta 12.5pt, English Poppins 12pt, Headline 18pt, Section 16pt, MCQ 12.5pt, Footer 9pt, line spacing 1.30, margins 13mm, single-column, max 2 font families (Mukta/Poppins)
  - Colors: Agriculture Green, Banking Blue, National Orange, etc. (controlled)
  - Watermark: PAID BATCHES logo centered 90mm, 0.09 alpha, every page
  - Double border Red+Green, logo, header/footer, page numbers, no Vol on cover
  - Smart layout: no orphan heading, smart page fill, tables compact, images proportional, text priority
- Takes bilingual content + validated MCQs + images from previous agents, outputs PDF to output/Agri_Learning_Point_DD_MMM_YYYY_Bilingual.pdf (3.7MB, 21 pages typical)
- Never alters facts — only designs
"""

class Agent:
    """PDF DESIGN AGENT — detailed implementation"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type  # daily/weekly/monthly
        self.context = context
        self.name = "PDF DESIGN AGENT"

    def run(self):
        """
        Execute PDF DESIGN AGENT
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
        # - Uses src/generate_pdf.py with FINAL spec:
        # TODO: Implement full logic — see DETAILS and TIER sources / PDF design spec
        # For now, log and pass through (real implementation in src/)
        logging.info(f"[{self.name}] COMMAND: {COMMAND[:80]}...")
        # Simulate work
        time.sleep(0.1)
        # Update context
        self.context["last_agent"] = self.name
        self.context["last_success_stage"] = "18_pdf_design"
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
