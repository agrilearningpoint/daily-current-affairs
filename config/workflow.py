# -*- coding: utf-8 -*-
"""
AGRI LEARNING POINT — AGENT WORKFLOW (24 Agents)
Pipeline: SCHEDULER → COLLECTOR → ... → WATCHDOG.
Architecture principle: Same database, different selection for Daily/Weekly/Monthly.
FIX (2026-10): Weekly/Monthly editors now run BEFORE Content→PDF so their fresh
selection actually flows into the edition (previously they sat after PDF/QA and
their output never reached downstream stages).
"""

WORKFLOW_ORDER = [
    "01_master_supervisor",
    "02_scheduler",
    "03_news_collection",
    "04_fact_verification",
    "05_deduplication",
    "06_news_importance",
    "07_student_relevance",
    "08_agriculture_expert",
    "09_banking_finance_expert",
    "10_final_news_selection",
    "11_importance_memory",
    "20_weekly_editor",
    "21_monthly_editor",
    "12_content_editor",
    "13_bilingual_editor",
    "14_english_editor",
    "15_image_agent",
    "16_mcq_generator",
    "17_mcq_validator",
    "18_pdf_design",
    "19_pdf_qa",
    "22_telegram_publisher",
    "23_telegram_pin_verifier",
    "24_watchdog_recovery"
]

# Which agents are active per job type (editors 20/21 skip non-matching types internally too)
DAILY_AGENTS = [a for a in WORKFLOW_ORDER if a not in ("20_weekly_editor", "21_monthly_editor")]
WEEKLY_AGENTS = [a for a in WORKFLOW_ORDER if a != "21_monthly_editor"]
MONTHLY_AGENTS = [a for a in WORKFLOW_ORDER if a != "20_weekly_editor"]
WORKFLOWS_BY_TYPE = {"daily": DAILY_AGENTS, "weekly": WEEKLY_AGENTS, "monthly": MONTHLY_AGENTS}

PIPELINE_FLOW = """SCHEDULER
   ↓
NEWS COLLECTOR
   ↓
FACT VERIFIER
   ↓
DEDUPLICATOR
   ↓
IMPORTANCE SCORER (0-100)
   ↓
STUDENT RELEVANCE SCORER
   ↓
AGRICULTURE EXPERT ─┐
                    ├──→ FINAL NEWS SELECTOR
BANKING EXPERT ─────┘
   ↓        (weekly/monthly: fresh Best-of re-selection here)
CONTENT EDITOR
    ↙         ↘
 BILINGUAL   ENGLISH
    ↓           ↓
 MCQ GENERATOR
      ↓
 MCQ VALIDATOR
      ↓
 IMAGE SELECTOR
      ↓
  PDF DESIGN (dynamic generator)
      ↓
  PDF QA — HARD GATE (REJECTED blocks publish)
      ↓
 TELEGRAM PUBLISH
      ↓
  PIN VERIFY
      ↓
 JOB COMPLETE"""

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