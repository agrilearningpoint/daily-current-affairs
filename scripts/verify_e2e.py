#!/usr/bin/env python3
"""Verify canonical edition outputs, checkpoint hashes and exact PDF approvals.

Usage: python scripts/verify_e2e.py --date 2026-10-14 --job-type daily
No provider calls or Telegram sends are performed.
"""
import argparse
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d"))
    parser.add_argument("--job-type", choices=("daily", "weekly", "monthly"), default="daily")
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    date.fromisoformat(args.date)
    root = args.root.resolve()
    job_id = f"{args.job_type}_{args.date}"
    failures = []

    def check(name, valid):
        print(f"{'PASS' if valid else 'FAIL'}: {name}")
        if not valid:
            failures.append(name)

    def read(relative):
        try:
            return json.loads((root / relative).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    state = read("state/jobs.json") or {}
    entry = state.get("jobs", state).get(job_id, {})
    check("job status is success", entry.get("status") == "success")
    folders = ["scored", "selected", "content", "mcq"]
    if args.job_type == "daily":
        folders += ["raw", "verified", "dedup"]
    for folder in folders:
        value = read(f"data/{folder}/{job_id}.json")
        items = value.get("items", value.get("mcqs", [])) if isinstance(value, dict) else value
        check(f"nonempty {folder} JSON", isinstance(items, list) and len(items) > 0)
    pdf = root / f"output/{job_id}.pdf"
    pdf_bytes = pdf.read_bytes() if pdf.is_file() else b""
    check("PDF header", pdf_bytes.startswith(b"%PDF"))
    qa = read(f"logs/qa/{job_id}_qa.json") or {}
    check("exact PDF QA approval", qa.get("passed") is True and qa.get("job_id") == job_id
          and qa.get("file_sha256") == hashlib.sha256(pdf_bytes).hexdigest())
    health = read(f"logs/qa/{job_id}_health.json") or {}
    check("final health approval", health.get("passed") is True and health.get("job_id") == job_id
          and health.get("dry_run") == entry.get("dry_run"))
    from main import STAGES_BY_TYPE
    from pipeline.checkpoints import resume_after
    names = [name for name, _, _ in STAGES_BY_TYPE[args.job_type]]
    check("all checkpoint evidence intact", bool(entry.get("artifacts"))
          and resume_after(root, job_id, entry, names) == names[-1])
    if not entry.get("dry_run"):
        for filename, status in [("published_jobs.json", "success"), ("pin_verification.json", "verified")]:
            ledger = read(f"state/{filename}") or {}
            check(filename, any(isinstance(record, dict) and record.get("job_id") == job_id
                               and record.get("status") == status for record in ledger.get("records", {}).values()))
    print(f"Verification {'FAILED' if failures else 'PASSED'}: {job_id}; dry_run={entry.get('dry_run')}")
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
