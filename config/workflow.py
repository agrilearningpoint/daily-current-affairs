# -*- coding: utf-8 -*-
"""
AGRI LEARNING POINT — AGENT WORKFLOW (17 logical stages)
Pipeline: COLLECTOR → ... → FINAL HEALTH AUDIT.
Architecture principle: Same database, different selection for Daily/Weekly/Monthly.

REFACTOR (2026-10 audit):
- 01 Master Supervisor REMOVED  — main.py already owns orchestration (lock/retry/resume/alert).
- 02 Scheduler MERGED into 03   — window calculation is one line inside collection.
- 07 Student Relevance + 08 Agriculture Expert + 09 Banking Expert MERGED into a single
  "student & domain relevance" stage — 08/09 were only tagging agri_focus/banking_focus.
- 13 Bilingual Editor + 14 English Editor MERGED into 12 Content Editor — build_content()
  already produces bilingual fields; the extra passes were thin fallbacks/cleanup.
- 24 Watchdog Recovery RENAMED to 24_final_health_audit — standalone watchdog lives in
  main.py --watchdog + .github/workflows/watchdog.yml; this agent is only the end-of-run audit.
Numbering keeps original IDs (gaps are intentional history markers).
"""

# main.py is the executable registry; documentation/config must not diverge.
from main import DAILY_STAGES, WEEKLY_STAGES, MONTHLY_STAGES

DAILY_AGENTS = [name for name, _, _ in DAILY_STAGES]
WEEKLY_AGENTS = [name for name, _, _ in WEEKLY_STAGES]
MONTHLY_AGENTS = [name for name, _, _ in MONTHLY_STAGES]
WORKFLOW_ORDER = list(dict.fromkeys(DAILY_AGENTS + WEEKLY_AGENTS + MONTHLY_AGENTS))
WORKFLOWS_BY_TYPE = {"daily": DAILY_AGENTS, "weekly": WEEKLY_AGENTS, "monthly": MONTHLY_AGENTS}

PIPELINE_FLOW = """NEWS COLLECTOR (+window)
   ↓
FACT VERIFIER
   ↓
DEDUPLICATOR
   ↓
IMPORTANCE SCORER (0-100)
   ↓
STUDENT + DOMAIN RELEVANCE (agri/banking boosts & tags)
   ↓
FINAL NEWS SELECTOR
   ↓        (weekly/monthly: fresh Best-of re-selection here)
IMPORTANCE MEMORY
   ↓
CONTENT EDITOR (EN + HI + validation in one stage)
   ↓
 IMAGE SELECTOR
   ↓
 MCQ GENERATOR
      ↓
 MCQ VALIDATOR
      ↓
  PDF DESIGN (dynamic generator)
      ↓
  PDF QA — HARD GATE (REJECTED blocks publish)
      ↓
 TELEGRAM PUBLISH
      ↓
  PIN VERIFY
      ↓
 FINAL HEALTH AUDIT → JOB COMPLETE"""

WATCHDOG_FLOW = "WATCHDOG → MONITOR → TIMEOUT → RETRY → RECOVER → ALERT"

STATE_MACHINE = {
    "happy_path": ["CREATED", "COLLECTING", "COLLECTED", "VERIFYING", "VERIFIED", "DEDUPLICATED",
                   "SCORED", "SELECTED", "CONTENT_READY", "MCQ_READY", "MCQ_VALIDATED",
                   "PDF_GENERATED", "QA_APPROVED", "PUBLISHED", "PIN_VERIFIED", "COMPLETE"],
    "failure": ["FAILED", "RETRYING", "RECOVERED", "FAILED_FINAL"],
    "qa_gate": ["QA_REJECTED  (blocks Telegram publish; job cannot become COMPLETE)"],
}

ARCHITECTURE_PRINCIPLE = """
Same database, different selection:
- Daily: "Aaj student ko kya zaroor padhna chahiye?"
- Weekly: "Is poore saptah me sabse mahatvapurna kya tha?" (fresh Best-of-Week, not daily combine)
- Monthly: "Is poore mahine me sabse mahatvapurna kya raha?" (fresh Best-of-Month)
Like GitHub Horizon / SmartReader: profile-based scoring, thresholding, topic deduplication, multi-stage ranking.
"""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news for competitive-exam students."