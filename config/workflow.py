# -*- coding: utf-8 -*-
"""
AGRI LEARNING POINT — AUTHORITATIVE AGENT WORKFLOW (18 daily stages + Master Supervisor)
Pipeline: MODEL ORCHESTRATOR → SOURCE FETCH → ... → FINAL HEALTH AUDIT.
Architecture principle: Same verified knowledge base, tailored selection for Daily/Weekly/Monthly,
supervised end-to-end by pipeline.supervisor.MasterSupervisor (agents/26_master_supervisor.py).
"""

# main.py is the executable registry; documentation/config must stay 1:1 synced.
from main import DAILY_STAGES, WEEKLY_STAGES, MONTHLY_STAGES

DAILY_AGENTS = [name for name, _, _ in DAILY_STAGES]
WEEKLY_AGENTS = [name for name, _, _ in WEEKLY_STAGES]
MONTHLY_AGENTS = [name for name, _, _ in MONTHLY_STAGES]
WORKFLOW_ORDER = list(dict.fromkeys(DAILY_AGENTS + WEEKLY_AGENTS + MONTHLY_AGENTS))
WORKFLOWS_BY_TYPE = {"daily": DAILY_AGENTS, "weekly": WEEKLY_AGENTS, "monthly": MONTHLY_AGENTS}

SUPERVISOR_CYCLE = ["PLAN", "EXECUTE", "OBSERVE", "CRITIQUE", "REPAIR", "RETEST", "APPROVE_OR_REJECT"]

PIPELINE_FLOW = """00 MODEL ORCHESTRATOR
   ↓
01 SOURCE FETCH (+IST window / GNews paced waves)
   ↓
04 FACT VERIFICATION (corroboration + claim-level evidence)
   ↓
05 DEDUPLICATION
   ↓
06 NEWS IMPORTANCE (0-100)
   ↓
07 STUDENT + DOMAIN RELEVANCE (agri/banking boosts & tags)
   ↓
10 FINAL NEWS SELECTION
   ↓        (weekly/monthly: 20/21 period assembly from published daily editions)
11 IMPORTANCE MEMORY
   ↓
12 CONTENT EDITOR (EN + HI + strict Hindi validation)
   ↓
16 MCQ GENERATOR
   ↓
17 MCQ VALIDATOR (+ independent adversarial examiner)
   ↓
17b AUTO SECTIONS (Agriculture Corner + Quick Bites)
   ↓
17c STATIC GK VALIDATOR (+ Hindi post-fix)
   ↓
18 PDF DESIGN (Image Curator + ReportLab/HarfBuzz layout)
   ↓
19 PDF QA — HARD GATE (Structural + Content + Visual QA; bounded repair)
   ↓
26 MASTER SUPERVISOR RELEASE GATE (signed SHA-256 approval)
   ↓
22 TELEGRAM PUBLISH
   ↓
23 TELEGRAM PIN VERIFIER
   ↓
24 FINAL HEALTH AUDIT → JOB COMPLETE"""

WATCHDOG_FLOW = "WATCHDOG → MONITOR → DETECT STUCK/FAILED → RECOVERY PLAN → ALERT"

STATE_MACHINE = {
    "job_statuses": ["running", "awaiting_stage", "awaiting_publish", "failed", "success"],
    "stage_verdicts": [
        "PASS",
        "PASS_WITH_APPROVED_LIMITATION",
        "RETRY_REQUIRED",
        "REPAIR_REQUIRED",
        "BLOCKED",
        "FAILED_FINAL",
    ],
    "qa_gate": ["REJECTED (blocks 22_telegram_publisher; failed 19_pdf_qa forces clean rebuild)"],
}

ARCHITECTURE_PRINCIPLE = """
Same database, different selection:
- Daily: "Aaj student ko kya zaroor padhna chahiye?"
- Weekly: "Is poore saptah me sabse mahatvapurna kya tha?" (fresh Best-of-Week, not daily combine)
- Monthly: "Is poore mahine me sabse mahatvapurna kya raha?" (fresh Best-of-Month)
Like GitHub Horizon / SmartReader: profile-based scoring, thresholding, topic deduplication, multi-stage ranking.
"""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news for competitive-exam students."