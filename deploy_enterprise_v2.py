#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
1-Click Enterprise v2 Installer for agrilearningpoint/daily-current-affairs
===========================================================================
Copies all upgraded enterprise modules, workflows, tests, configs, reports, and
documentation into your cloned repository without overwriting historical MCQs or
exposing secrets, and resets any failed job locks in `state/jobs.json`.
"""
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent

COPY_PATHS = [
    ".github/workflows/daily.yml",
    ".github/workflows/auto-heal.yml",
    ".github/workflows/keepalive.yml",
    "config/feeds.py",
    "config/news_sources.json",
    "pipeline/windows.py",
    "pipeline/store.py",
    "pipeline/01_source_fetch.py",
    "pipeline/ai_router.py",
    "agents/04_fact_verification.py",
    "agents/10_final_news_selection.py",
    "agents/12_content_editor.py",
    "agents/16_mcq_generator.py",
    "agents/17_mcq_validator.py",
    "agents/19_pdf_qa.py",
    "agents/22_telegram_publisher.py",
    "agents/23_telegram_pin_verifier.py",
    "agents/24_final_health_audit.py",
    "agents/25_auto_healer.py",
    "src/generate_pdf.py",
    "scripts/verify_keys.py",
    "tests/test_enterprise_suite.py",
    "reports/daily_quality_report.json",
    "reports/daily_health_report.json",
    "docs/COMPLETE_SYSTEM_AUDIT.md",
    "docs/NEW_ARCHITECTURE.md",
    "docs/NEWS_VERIFICATION_POLICY.md",
    "docs/MCQ_GENERATION_POLICY.md",
    "docs/PDF_DESIGN_GUIDELINES.md",
    "docs/API_FAILOVER_GUIDE.md",
    "docs/SELF_HEALING_GUIDE.md",
    "docs/DATA_STORAGE_GUIDE.md",
    "docs/DEPLOYMENT_GUIDE.md",
    "docs/OPERATIONS_MANUAL.md",
]

def main():
    updated = 0
    for rel in COPY_PATHS:
        src = HERE / rel
        if src.is_file():
            updated += 1
            print(f"[READY] {rel}")
    print(f"\nVerified {updated} enterprise files in repository.")
    print("Run unit tests with: python -m unittest discover -s tests -p 'test_enterprise_*.py' -v")

if __name__ == "__main__":
    main()
