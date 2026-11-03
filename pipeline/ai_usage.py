"""Append-only record of which AI provider/model answered which task.

One JSON line per call outcome in logs/ai_usage.jsonl (override with
ALP_AI_USAGE_LOG). scripts/run_summary.py aggregates it into the job log and
$GITHUB_STEP_SUMMARY, because run artifacts are not always inspectable.
Never raises: usage accounting must not break a pipeline stage.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


def usage_log_path() -> Path:
    override = os.getenv("ALP_AI_USAGE_LOG")
    return Path(override) if override else _ROOT / "logs" / "ai_usage.jsonl"


def record_ai_usage(provider: str, model: str, task: str, ok: bool, detail: str = "") -> None:
    try:
        path = usage_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        row = {"at": datetime.now(timezone.utc).isoformat(), "job": os.getenv("ALP_JOB_ID", ""),
               "stage": os.getenv("ALP_STAGE_ID", ""), "provider": str(provider or ""),
               "model": str(model or ""), "task": str(task or ""), "ok": bool(ok)}
        if detail:
            row["detail"] = str(detail)[:80]
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001 - accounting is best effort
        pass
