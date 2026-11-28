#!/usr/bin/env python3
"""Agent 26: Master Editorial Newsroom Supervisor interface."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.supervisor import (  # noqa: E402
    MasterSupervisor,
    release_approval_path,
    supervisor_state_path,
    verify_release_approval,
)


def inspect_job(job_id: str, job_type: str = "daily", edition_date: str = "") -> dict:
    date_part = edition_date or job_id.split("_", 1)[-1]
    sup = MasterSupervisor(ROOT, job_id, job_type, date_part)
    return sup.state


def evaluate_release(job_id: str, job_type: str = "daily", edition_date: str = "") -> dict:
    date_part = edition_date or job_id.split("_", 1)[-1]
    sup = MasterSupervisor(ROOT, job_id, job_type, date_part)
    return sup.issue_release_decision(strict_files=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Agri Learning Point Master Supervisor")
    parser.add_argument("--job-id", default=os.getenv("ALP_JOB_ID", ""))
    parser.add_argument("--job-type", default=os.getenv("ALP_JOB_TYPE", "daily"))
    parser.add_argument("--date", default=os.getenv("ALP_JOB_DATE", ""))
    parser.add_argument("--verify-release", action="store_true")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args(argv)

    date_str = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    job_id = args.job_id or f"{args.job_type}_{date_str}"

    if args.verify_release:
        decision = evaluate_release(job_id, args.job_type, date_str)
        print(json.dumps(decision, indent=2, ensure_ascii=False))
        return 0 if decision.get("approved") else 1

    state_file = supervisor_state_path(ROOT, job_id)
    if args.status and not state_file.is_file():
        print(json.dumps({"job_id": job_id, "status": "not_initialized"}))
        return 0
    state = inspect_job(job_id, args.job_type, date_str)
    print(json.dumps(state, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
