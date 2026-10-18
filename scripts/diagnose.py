# -*- coding: utf-8 -*-
"""
Project Diagnostic
==================
Scans repo and reports ALL known issues in one run.
Run BEFORE pushing to GitHub.

Usage:
    python scripts/diagnose.py
    python scripts/diagnose.py --fix-hints
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import List, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent


if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


class Report:
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.passed: List[str] = []

    def err(self, msg: str):
        self.errors.append(msg)
        print(f"  [X] {msg}")

    def warn(self, msg: str):
        self.warnings.append(msg)
        print(f"  [!] {msg}")

    def ok(self, msg: str):
        self.passed.append(msg)
        print(f"  [OK] {msg}")

    def summary(self) -> int:
        print()
        print("=" * 70)
        print(f"ERRORS:   {len(self.errors)}")
        print(f"WARNINGS: {len(self.warnings)}")
        print(f"PASSED:   {len(self.passed)}")
        print("=" * 70)
        if self.errors:
            print("\nFix all ERRORS before pushing.\n")
            return 1
        if self.warnings:
            print("\nWarnings present but no blockers.\n")
            return 0
        print("\n[OK] All checks passed.\n")
        return 0


# --------------------------------------------------------------------------- #
def check_python_files_compile(r: Report):
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


def check_critical_files(r: Report):
    print("\n[2] Critical files exist")
    files = [
        "main.py",
        "pipeline/01_source_fetch.py",
        "pipeline/agent_context.py",
        "pipeline/state.py",
        "pipeline/store.py",
        "pipeline/content.py",
        "pipeline/ai_router.py",
        "pipeline/ai_translator.py",
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
        "config/registry.py",
        "requirements.txt",
    ]
    for f in files:
        p = REPO_ROOT / f
        if p.exists():
            r.ok(f"{f}")
        else:
            r.err(f"MISSING: {f}")


def check_content_functions(r: Report):
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
            r.err(f"content.{fn} MISSING (imported by agents)")


def check_store_functions(r: Report):
    print("\n[4] pipeline/store.py functions")
    p = REPO_ROOT / "pipeline" / "store.py"
    if not p.exists():
        r.err("pipeline/store.py missing")
        return
    text = p.read_text(encoding="utf-8")
    required = ["load_memory", "save_memory", "load_published", "save_published",
                "record_scores", "is_job_published", "pull", "push", "prune",
                "update_source_health"]
    for fn in required:
        if re.search(rf"def\s+{fn}\s*\(", text):
            r.ok(f"store.{fn} defined")
        else:
            r.warn(f"store.{fn} missing (may be called by agents)")


def check_agent_entrypoints(r: Report):
    print("\n[5] Agent standalone entrypoints")
    agents = ["10_final_news_selection", "16_mcq_generator", "17_mcq_validator",
              "18_pdf_design", "19_pdf_qa", "22_telegram_publisher"]
    for name in agents:
        p = REPO_ROOT / "agents" / f"{name}.py"
        if not p.exists():
            r.warn(f"{name}.py not found")
            continue
        text = p.read_text(encoding="utf-8")
        if '__name__' in text and '__main__' in text:
            r.ok(f"{name}.py has __main__ block")
        else:
            r.err(f"{name}.py MISSING __main__ block (will silently pass)")


def check_hardcoded_job_ids(r: Report):
    print("\n[6] Hardcoded test job IDs in agents")
    pattern = re.compile(r'["\'](daily|weekly|monthly)_20\d{2}-\d{2}-\d{2}["\']')
    found = 0
    for p in (REPO_ROOT / "agents").glob("*.py"):
        text = p.read_text(encoding="utf-8")
        matches = pattern.findall(text)
        if matches:
            r.warn(f"{p.name}: hardcoded job_id {matches[:3]}")
            found += 1
    if found == 0:
        r.ok("No hardcoded job IDs")


def check_ci_workflow(r: Report):
    print("\n[7] CI workflow Ruff flags")
    p = REPO_ROOT / ".github" / "workflows" / "ci.yml"
    if not p.exists():
        r.warn(".github/workflows/ci.yml missing")
        return
    text = p.read_text(encoding="utf-8")
    # Check for invalid Ruff flags
    for bad in ["W503", "W605"]:
        if bad in text:
            r.err(f"CI uses invalid Ruff flag: {bad} (removed in Ruff 0.6+)")
    if "W503" not in text and "W605" not in text:
        r.ok("No invalid Ruff flags")


def check_workflow_env(r: Report):
    print("\n[8] Workflow env var consistency")
    wf_dir = REPO_ROOT / ".github" / "workflows"
    if not wf_dir.exists():
        return
    bad_found = 0
    for wf in wf_dir.glob("*.yml"):
        text = wf.read_text(encoding="utf-8")
        if "TELEGRAM_CHANNEL_ID" in text:
            r.err(f"{wf.name} uses TELEGRAM_CHANNEL_ID (should be TELEGRAM_CHAT_ID)")
            bad_found += 1
    if bad_found == 0:
        r.ok("TELEGRAM_CHAT_ID used consistently")


def check_python_version(r: Report):
    print("\n[9] Python version in workflows")
    wf_dir = REPO_ROOT / ".github" / "workflows"
    if not wf_dir.exists():
        return
    versions = set()
    for wf in wf_dir.glob("*.yml"):
        for line in wf.read_text(encoding="utf-8").split("\n"):
            m = re.search(r'python-version:\s*["\']?([\d.]+)', line)
            if m:
                versions.add(m.group(1))
    if len(versions) > 1:
        r.err(f"Multiple Python versions in workflows: {versions}")
    elif versions:
        r.ok(f"Single Python version: {list(versions)[0]}")
    else:
        r.warn("No python-version found in workflows")


def check_config_registry(r: Report):
    print("\n[10] Config registry (sources)")
    p = REPO_ROOT / "config" / "registry.py"
    if not p.exists():
        r.err("config/registry.py missing (required for source unification)")
    else:
        r.ok("config/registry.py exists")
    # Try to import
    sys.path.insert(0, str(REPO_ROOT))
    try:
        from config.registry import get_feed_urls  # type: ignore
        urls = get_feed_urls()
        if urls:
            r.ok(f"Registry loaded {len(urls)} feeds")
        else:
            r.err("Registry returned 0 feeds — sources config broken")
    except Exception as exc:
        r.err(f"Registry import failed: {exc}")

    # Canonical runtime registry (what the production collector actually loads).
    try:
        from pipeline.source_registry import load_sources  # type: ignore
        specs = load_sources()
        rss_urls = [s.rss_url for s in specs]
        dupes = sorted({u for u in rss_urls if rss_urls.count(u) > 1})
        if dupes:
            r.err(f"Canonical registry duplicate RSS URLs: {dupes[:5]}")
        else:
            r.ok(f"Canonical registry: {len(specs)} enabled sources, no duplicate URLs")
    except Exception as exc:
        r.err(f"Canonical source registry failed to load: {exc}")


def check_requirements(r: Report):
    print("\n[11] requirements.txt")
    p = REPO_ROOT / "requirements.txt"
    if not p.exists():
        r.err("requirements.txt missing")
        return
    text = p.read_text(encoding="utf-8")
    required = ["requests", "feedparser", "pydantic", "tenacity",
                "python-dotenv", "reportlab", "pymupdf"]
    for pkg in required:
        if re.search(rf"^{pkg}[=><~]", text, re.MULTILINE | re.IGNORECASE):
            r.ok(f"{pkg} present")
        else:
            r.warn(f"{pkg} missing from requirements.txt")


def check_json_configs(r: Report):
    print("\n[12] JSON configs valid")
    count = 0
    for p in REPO_ROOT.rglob("*.json"):
        if any(part in {".git", ".venv", "data", "logs", "node_modules"}
               for part in p.parts):
            continue
        if "backups" in p.parts or "archive" in p.parts:
            continue
        try:
            json.loads(p.read_text(encoding="utf-8"))
            count += 1
        except Exception as e:
            r.err(f"Invalid JSON: {p.relative_to(REPO_ROOT)}: {e}")
    if count:
        r.ok(f"{count} JSON files valid")


def check_ruff_local(r: Report):
    print("\n[13] Ruff lint (if installed)")
    try:
        import subprocess
        result = subprocess.run(
            ["ruff", "check", ".",
             "--select", "E,F,W",
             "--ignore", "E501,E402,E722,F401",
             "--output-format", "concise"],
            cwd=str(REPO_ROOT),
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0:
            r.ok("Ruff: no issues")
        else:
            # Count errors
            lines = [l for l in result.stdout.splitlines() if l.strip()]
            r.warn(f"Ruff: {len(lines)} issue(s) — not blocking")
            for l in lines[:5]:
                print(f"     {l}")
    except FileNotFoundError:
        r.warn("Ruff not installed — skip")
    except Exception as e:
        r.warn(f"Ruff check failed: {e}")


def check_venv(r: Report):
    print("\n[14] Environment")
    if sys.version_info < (3, 11):
        r.err(f"Python {sys.version_info[:2]} detected — need 3.11+")
    else:
        r.ok(f"Python {sys.version_info.major}.{sys.version_info.minor}")
    import os
    if os.getenv("VIRTUAL_ENV"):
        r.ok(f"venv active: {Path(os.getenv('VIRTUAL_ENV')).name}")
    else:
        r.warn("No active venv")


# --------------------------------------------------------------------------- #
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fix-hints", action="store_true",
                        help="Print fix hints for each error")
    parser.parse_args()

    print("=" * 70)
    print("PROJECT DIAGNOSTIC")
    print(f"Repo: {REPO_ROOT}")
    print("=" * 70)

    r = Report()
    check_python_files_compile(r)
    check_critical_files(r)
    check_content_functions(r)
    check_store_functions(r)
    check_agent_entrypoints(r)
    check_hardcoded_job_ids(r)
    check_ci_workflow(r)
    check_workflow_env(r)
    check_python_version(r)
    check_config_registry(r)
    check_requirements(r)
    check_json_configs(r)
    check_ruff_local(r)
    check_venv(r)

    return r.summary()


if __name__ == "__main__":
    sys.exit(main())
