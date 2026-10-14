#!/usr/bin/env python3
"""Dispatch bounded watchdog actions using exact edition dates, not wall-clock today."""

import argparse
import json
from pathlib import Path
import re
import subprocess

WORKFLOWS = {"daily": "daily.yml", "weekly": "weekly.yml", "monthly": "monthly.yml"}


def recovery_jobs(plan):
    actions = plan.get("actions", []) if isinstance(plan, dict) else plan
    if not isinstance(actions, list):
        raise ValueError("recovery actions must be a list")
    jobs = []
    for action in actions:
        job = action.get("job_id") if isinstance(action, dict) and action.get("action") == "retry" else action if isinstance(action, str) else None
        if isinstance(job, str) and re.fullmatch(r"(daily|weekly|monthly)_\d{4}-\d{2}-\d{2}", job):
            from datetime import date
            date.fromisoformat(job.split("_", 1)[1])
            if job not in jobs:
                jobs.append(job)
    return jobs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, default=Path("recovery_plan.json"))
    parser.add_argument("--ref", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    for job in recovery_jobs(json.loads(args.plan.read_text(encoding="utf-8"))):
        kind, date = job.split("_", 1)
        command = ["gh", "workflow", "run", WORKFLOWS[kind], "--ref", args.ref, "-f", f"date={date}"]
        print("recovery:", " ".join(command), flush=True)
        if not args.dry_run:
            subprocess.run(command, check=True, timeout=60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
