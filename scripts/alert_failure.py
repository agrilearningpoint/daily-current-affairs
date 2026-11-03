#!/usr/bin/env python3
"""Telegram admin alert for a failed pipeline run (never fails the workflow).

Sends one DM to ADMIN_ID (never to the public channel) with the job, the failed
stage and its error from state/jobs.json, the AI provider health of the run
(logs/ai_health/<job>.json) and the run URL.

Usage: python scripts/alert_failure.py --job-id daily_2026-11-03 [--workflow Daily]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def build_message(job_id: str, workflow: str = "") -> str:
    job: dict = {}
    try:
        data = json.loads((ROOT / "state" / "jobs.json").read_text(encoding="utf-8"))
        job = (data.get("jobs", data) or {}).get(job_id, {}) or {}
    except (OSError, ValueError, AttributeError):
        pass
    lines = [f"❌ {workflow or 'Pipeline'} run FAILED: {job_id}"]
    if job.get("failed_stage"):
        lines.append(f"Stage: {job['failed_stage']}")
    if job.get("error"):
        lines.append(f"Error: {str(job['error'])[:600]}")
    if job.get("status"):
        lines.append(f"Status: {job['status']}")
    health_file = ROOT / "logs" / "ai_health" / f"{job_id}.json"
    try:
        health = json.loads(health_file.read_text(encoding="utf-8"))
        now = time.time()
        down = sorted(f"{k} ({v.get('reason', '')})" for k, v in (health.get("blocks") or {}).items()
                      if float(v.get("until", 0)) > now)
        if down:
            lines.append("AI providers cooled down: " + "; ".join(down)[:800])
    except (OSError, ValueError, AttributeError, TypeError):
        pass
    server = os.getenv("GITHUB_SERVER_URL", "https://github.com")
    repo = os.getenv("GITHUB_REPOSITORY", "")
    run_id = os.getenv("GITHUB_RUN_ID", "")
    if repo and run_id:
        lines.append(f"Logs: {server}/{repo}/actions/runs/{run_id}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--workflow", default="")
    args = parser.parse_args(argv)
    text = build_message(args.job_id, args.workflow)
    print(text)
    try:
        from pipeline.telegram_api import alert_admin
        sent = alert_admin(text)
        print("admin alert sent" if sent else "admin alert NOT sent (see log above)")
    except Exception as exc:  # never fail the workflow because of the alert
        print(f"admin alert failed: {type(exc).__name__}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
