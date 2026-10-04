# -*- coding: utf-8 -*-
"""
AGRI LEARNING POINT — AGENT WORKFLOW (24 Agents)
Master pipeline: SCHEDULER → COLLECTOR → ... → WATCHDOG
Architecture principle: Same database, different selection for Daily/Weekly/Monthly
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
    "12_content_editor",
    "13_bilingual_editor",
    "14_english_editor",
    "15_image_agent",
    "16_mcq_generator",
    "17_mcq_validator",
    "18_pdf_design",
    "19_pdf_qa",
    "20_weekly_editor",
    "21_monthly_editor",
    "22_telegram_publisher",
    "23_telegram_pin_verifier",
    "24_watchdog_recovery"
]

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
                         ↓
                 CONTENT EDITOR
                    ↙         ↘
              BILINGUAL      ENGLISH
                    ↓           ↓
                 MCQ GENERATOR
                       ↓
                 MCQ VALIDATOR
                       ↓
                 IMAGE SELECTOR
                       ↓
                  PDF DESIGN
                       ↓
                    PDF QA
                       ↓
               TELEGRAM PUBLISH
                       ↓
                  PIN VERIFY
                       ↓
                  JOB COMPLETE"""

WATCHDOG_FLOW = """WATCHDOG
   ↓
MONITOR
   ↓
RETRY
   ↓
RECOVER
   ↓
ALERT"""

ARCHITECTURE_PRINCIPLE = """
Same database, different selection:
- Daily: "Aaj student ko kya zaroor padhna chahiye?"
- Weekly: "Is poore saptah me sabse mahatvapurna kya tha?" (fresh Best-of-Week, not daily combine)
- Monthly: "Is poore mahine me sabse mahatvapurna kya raha?" (fresh Best-of-Month)
Like GitHub Horizon / SmartReader: profile-based scoring, thresholding, topic deduplication, multi-stage ranking.
"""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news for competitive-exam students."
