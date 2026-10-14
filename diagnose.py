# -*- coding: utf-8 -*-
"""
Project Diagnostic — Run BEFORE pushing to GitHub.
Usage: python diagnose.py
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import List

REPO_ROOT = Path(__file__).resolve().parent


class Report:
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.passed: List[str] = []

    def err(self, msg):
        self.errors.append(msg)
        print(f"  [X] {msg}")

    def warn(self, msg):
        self.warnings.append(msg)
        print(f"  [!] {msg}")

    def ok(self, msg):
        self.passed.append(msg)
        print(f"  [OK] {msg}")

    def summary(self):
        print()
        print("=" * 70)
        print(f"ERRORS:   {len(self.errors)}")
        print(f"WARNINGS: {len(self.warnings)}")
        print(f"PASSED:   {len(self.passed)}")
        print("=" * 70)
        if self.errors:
            print("\nFix all ERRORS before pushing.\n")
            return 1
        print("\nAll checks passed.\n")
        return 0


def check_python_compile(r):
    print("\n[1] Python compilation")
    failed = 0
    for p in REPO_ROOT.rglob("*.py"):
        if any(part in {".git", ".venv", "venv", "__pycache__", "build", "dist"}
               for part in p.parts):
            continue
        try:
            compile(p.read_text(encoding="utf-8"), str(p), "exec")
        except SyntaxError as e:
            r.err(f"Syntax error in {p.relative_to(REPO_ROOT)}: {e}")
            failed += 1
    if failed == 0:
        r.ok("All Python files compile")


def check_critical_files(r):
    print("\n[2] Critical files exist")
    files = [
        "main.py",
        "pipeline/state.py",
        "pipeline/store.py",
        "pipeline/content.py",
        "pipeline/ai_router.py",
        "pipeline/ai_translator.py",
        "pipeline/01_source_fetch.py",
        "agents/03_news_collection.py",
        "agents/04_fact_verification.py",
        "agents/10_final_news_selection.py",
        "agents/16_mcq_generator.py",
        "agents/17_mcq_validator.py",
        "agents/18_pdf_design.py",
        "agents/19_pdf_qa.py",
        "agents/22_telegram_publisher.py",
        "agents/23_telegram_pin_verifier.py",
        "config/sources.py",
        "config/feeds.py",
        "requirements.txt",
    ]
    for f in files:
        p = REPO_ROOT / f
        if p.exists():
            r.ok(f)
        else:
            r.err(f"MISSING: {f}")


def check_content_functions(r):
    print("\n[3] pipeline/content.py functions")
    p = REPO_ROOT / "pipeline" / "content.py"
    if not p.exists():
        r.err("pipeline/content.py missing")
        return
    text = p.read_text(encoding="utf-8")
    for fn in ["build_content", "generate_mcqs", "validate_mcqs"]:
        if re.search(rf"def\s+{fn}\s*\(", text):
            r.ok(f"content.{fn} defined")
        else:
            r.err(f"content.{fn} MISSING (imported by agents 16, 17)")


def check_store_functions(r):
    print("\n[4] pipeline/store.py functions")
    p = REPO_ROOT / "pipeline" / "store.py"
    if not p.exists():
        r.err("pipeline/store.py missing")
        return
    text = p.read_text(encoding="utf-8")
    required = ["load_memory", "save_memory", "load_published", "save_published",
                "record_scores", "is_job_published", "pull", "push", "prune"]
    for fn in required:
        if re.search(rf"def\s+{fn}\s*\(", text):
            r.ok(f"store.{fn} defined")
        else:
            r.warn(f"store.{fn} missing")


def check_agent_entrypoints(r):
    print("\n[5] Agent standalone entrypoints")
    agents = ["10_final_news_selection", "16_mcq_generator", "17_mcq_validator",
              "18_pdf_design", "19_pdf_qa", "22_telegram_publisher"]
    for name in agents:
        p = REPO_ROOT / "agents" / f"{name}.py"
        if not p.exists():
            r.warn(f"{name}.py not found")
            continue
        text = p.read_text(encoding="utf-8")
        if "__main__" in text:
            r.ok(f"{name}.py has __main__ block")
        else:
            r.err(f"{name}.py MISSING __main__ block")


def check_hardcoded_job_ids(r):
    print("\n[6] Hardcoded job IDs in agents")
    pattern = re.compile(r'["\'](daily|weekly|monthly)_20\d{2}-\d{2}-\d{2}["\']')
    found = 0
    ad = REPO_ROOT / "agents"
    if not ad.exists():
        return
    for p in ad.glob("*.py"):
        text = p.read_text(encoding="utf-8")
        matches = pattern.findall(text)
        if matches:
            r.warn(f"{p.name}: hardcoded {matches[:2]}")
            found += 1
    if found == 0:
        r.ok("No hardcoded job IDs")


def check_ci_workflow(r):
    print("\n[7] CI workflow Ruff flags")
    p = REPO_ROOT / ".github" / "workflows" / "ci.yml"
    if not p.exists():
        r.warn(".github/workflows/ci.yml missing")
        return
    text = p.read_text(encoding="utf-8")
    bad = 0
    for flag in ["W503", "W605"]:
        if flag in text:
            r.err(f"CI uses invalid Ruff flag: {flag} (removed in Ruff 0.6+)")
            bad += 1
    if bad == 0:
        r.ok("No invalid Ruff flags")


def check_workflow_env(r):
    print("\n[8] Workflow env vars")
    wd = REPO_ROOT / ".github" / "workflows"
    if not wd.exists():
        return
    bad = 0
    for wf in wd.glob("*.yml"):
        text = wf.read_text(encoding="utf-8")
        if "TELEGRAM_CHANNEL_ID" in text:
            r.err(f"{wf.name} uses TELEGRAM_CHANNEL_ID (should be TELEGRAM_CHAT_ID)")
            bad += 1
    if bad == 0:
        r.ok("TELEGRAM_CHAT_ID consistent")


def check_python_version(r):
    print("\n[9] Python version in workflows")
    wd = REPO_ROOT / ".github" / "workflows"
    if not wd.exists():
        return
    versions = set()
    for wf in wd.glob("*.yml"):
        for line in wf.read_text(encoding="utf-8").split("\n"):
            m = re.search(r'python-version:\s*["\']?([\d.]+)', line)
            if m:
                versions.add(m.group(1))
    if len(versions) > 1:
        r.err(f"Multiple Python versions: {versions}")
    elif versions:
        r.ok(f"Single version: {list(versions)[0]}")
    else:
        r.warn("No python-version in workflows")


def check_requirements(r):
    print("\n[10] requirements.txt")
    p = REPO_ROOT / "requirements.txt"
    if not p.exists():
        r.err("requirements.txt missing")
        return
    text = p.read_text(encoding="utf-8")
    required = ["requests", "feedparser", "pydantic", "tenacity",
                "python-dotenv", "reportlab", "pymupdf"]
    for pkg in required:
        if re.search(rf"^{pkg}[=><~]", text, re.MULTILINE | re.IGNORECASE):
            r.ok(f"{pkg}")
        else:
            r.warn(f"{pkg} missing")


def check_json_configs(r):
    print("\n[11] JSON configs")
    count = 0
    for p in REPO_ROOT.rglob("*.json"):
        if any(part in {".git", ".venv", "data", "logs", "node_modules", "__pycache__"}
               for part in p.parts):
            continue
        if "backups" in p.parts or "archive" in p.parts:
            continue
        try:
            json.loads(p.read_text(encoding="utf-8"))
            count += 1
        except Exception as e:
            r.err(f"Invalid JSON: {p.relative_to(REPO_ROOT)}")
    if count:
        r.ok(f"{count} JSON files valid")


def check_venv(r):
    print("\n[12] Environment")
    if sys.version_info < (3, 11):
        r.err(f"Python {sys.version_info[:2]} — need 3.11+")
    else:
        r.ok(f"Python {sys.version_info.major}.{sys.version_info.minor}")


def main():
    print("=" * 70)
    print("PROJECT DIAGNOSTIC")
    print(f"Repo: {REPO_ROOT}")
    print("=" * 70)

    r = Report()
    check_python_compile(r)
    check_critical_files(r)
    check_content_functions(r)
    check_store_functions(r)
    check_agent_entrypoints(r)
    check_hardcoded_job_ids(r)
    check_ci_workflow(r)
    check_workflow_env(r)
    check_python_version(r)
    check_requirements(r)
    check_json_configs(r)
    check_venv(r)

    return r.summary()


if __name__ == "__main__":
    sys.exit(main())