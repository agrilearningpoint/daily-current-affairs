# -*- coding: utf-8 -*-
"""
End-to-End Verification Script
===============================
Run after `main.py --job-type daily` to verify all artifacts were produced.

Usage:
    python scripts/verify_e2e.py --date 2026-10-14
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def check(name: str, ok: bool, detail: str = "") -> bool:
    icon = "✅" if ok else "❌"
    print(f"  {icon} {name:30s} {detail}")
    return ok


def load_json_safe(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--date", default="2026-10-14")
    p.add_argument("--job-type", default="daily")
    args = p.parse_args()

    job_id = f"{args.job_type}_{args.date}"
    print(f"Verifying E2E for job: {job_id}")
    print("=" * 70)

    all_ok = True

    # 1. State
    print("\n[1] State file")
    state_file = REPO_ROOT / "state" / "jobs.json"
    state = load_json_safe(state_file)
    if state:
        jobs = state.get("jobs", state)
        job = jobs.get(job_id, {})
        all_ok &= check("state/jobs.json exists", True, "")
        all_ok &= check(f"job {job_id} present", bool(job),
                        f"status={job.get('status', '?')}")
        all_ok &= check("job status == SUCCESS", job.get("status") == "SUCCESS",
                        job.get("status", "?"))
    else:
        all_ok &= check("state/jobs.json exists", False)

    # 2. Artifacts (canonical + legacy)
    print("\n[2] Artifacts")
    artifacts = [
        ("raw",          f"data/raw/{job_id}.json"),
        ("raw (legacy)", f"data/raw/news_{args.date}.json"),
        ("verified",     f"data/verified/{job_id}.json"),
        ("dedup",        f"data/dedup/{job_id}.json"),
        ("scored",       f"data/scored/{job_id}.json"),
        ("selected",     f"data/selected/{job_id}.json"),
        ("content",      f"data/content/{job_id}.json"),
        ("mcq",          f"data/mcq/{job_id}.json"),
        ("pdf",          f"output/{job_id}.pdf"),
        ("qa_report",    f"logs/qa/{job_id}_qa.json"),
    ]
    for name, rel in artifacts:
        path = REPO_ROOT / rel
        if path.exists():
            size = path.stat().st_size
            all_ok &= check(name, True, f"{size} bytes")
        else:
            all_ok &= check(name, False, "MISSING")

    # 3. Content sanity
    print("\n[3] Content sanity")
    content_file = REPO_ROOT / f"data/content/{job_id}.json"
    content = load_json_safe(content_file)
    if content:
        items = content.get("items") if isinstance(content, dict) else content
        if isinstance(items, list) and items:
            first = items[0]
            all_ok &= check("content has items", True, f"{len(items)} items")
            all_ok &= check("first item has headline_en",
                            bool(first.get("headline_en")),
                            (first.get("headline_en") or "")[:50])
            all_ok &= check("first item has headline_hi",
                            bool(first.get("headline_hi")),
                            (first.get("headline_hi") or "")[:50])

    # 4. MCQ sanity
    print("\n[4] MCQ sanity")
    mcq_file = REPO_ROOT / f"data/mcq/{job_id}.json"
    mcqs_data = load_json_safe(mcq_file)
    if mcqs_data:
        mcqs = mcqs_data.get("mcqs") if isinstance(mcqs_data, dict) else mcqs_data
        if isinstance(mcqs, list):
            all_ok &= check("MCQs generated", True, f"{len(mcqs)} MCQs")
            all_ok &= check("MCQ count >= 10", len(mcqs) >= 10, str(len(mcqs)))
            if mcqs:
                all_ok &= check("MCQ has question_en",
                                bool(mcqs[0].get("question_en")))
                all_ok &= check("MCQ has options",
                                len(mcqs[0].get("options", [])) >= 4)

    # 5. PDF sanity
    print("\n[5] PDF sanity")
    pdf_file = REPO_ROOT / f"output/{job_id}.pdf"
    if pdf_file.exists():
        size_kb = pdf_file.stat().st_size // 1024
        all_ok &= check("PDF size >= 5 KB", size_kb >= 5, f"{size_kb} KB")
        # Check header
        header = pdf_file.read_bytes()[:8]
        all_ok &= check("Valid PDF header", header.startswith(b"%PDF"),
                        header.decode(errors="replace"))

    # Summary
    print("\n" + "=" * 70)
    if all_ok:
        print("✅ E2E VERIFICATION PASSED")
        return 0
    else:
        print("❌ E2E VERIFICATION FAILED — check above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
