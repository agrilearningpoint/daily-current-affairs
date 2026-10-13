# -*- coding: utf-8 -*-
"""
State Migration & Cleanup Script
================================
Yeh script `state/jobs.json` ko safely clean karta hai jab:
- Invalid `last_success_stage` ho (e.g. daily job mein `21_monthly_editor`)
- FAILED_FINAL jobs stuck ho
- RUNNING jobs ghanton se atke ho
- job_type mismatch ho job_id se

Features:
- Dry-run mode (preview only)
- Automatic backup before write
- Append-only archive (history preserved)
- Atomic state writes
- Idempotent (safe to run multiple times)
- Detailed JSON report
- Reads valid stages from main.py if possible; else uses built-in defaults

Usage:
  # 1. Preview kya change hoga
  python maintenance/migrate_state.py --dry-run

  # 2. Apply cleanup (FAILED_FINAL → FAILED for retry)
  python maintenance/migrate_state.py --reset-failed-final

  # 3. Sirf stuck RUNNING clean karo
  python maintenance/migrate_state.py --stuck-hours 4

  # 4. Ek specific job reset karo
  python maintenance/migrate_state.py --reset-job daily_2026-10-13
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/state_migration.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("state_migration")

# --------------------------------------------------------------------------- #
# Paths & Constants
# --------------------------------------------------------------------------- #
REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = REPO_ROOT / "state" / "jobs.json"
BACKUP_DIR = REPO_ROOT / "state" / "backups"
ARCHIVE_FILE = REPO_ROOT / "state" / "archive" / "jobs_archive.json"
REPORT_FILE = REPO_ROOT / "state" / "migration_report.json"

# Valid stage names per job type. Update these if main.py changes.
# Derived from repo structure (agents/, pipeline/) + jobs.json observed history.
VALID_STAGES: Dict[str, List[str]] = {
    "daily": [
        "00_model_orchestrator",
        "01_source_fetch",
        "03_news_collection",
        "04_fact_verification",
        "05_deduplication",
        "06_news_importance",
        "07_student_domain_relevance",
        "10_final_news_selection",
        "11_importance_memory",
        "12_content_editor",
        "16_mcq_generator",
        "22_telegram_publisher",
    ],
    "weekly": [
        "20_weekly_editor",
        "22_telegram_publisher",
    ],
    "monthly": [
        "21_monthly_editor",
        "22_telegram_publisher",
    ],
}

VALID_STATUSES = {"PENDING", "RUNNING", "SUCCESS", "FAILED", "FAILED_FINAL", "COLLECTED"}
# Note: COLLECTED is included because it appeared in jobs.json — if it's an invalid
# intermediate state, we'll convert it to FAILED during migration.

# A RUNNING job older than this is stuck
DEFAULT_STUCK_HOURS = 2


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_iso_safe(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def infer_job_type(job_id: str, declared_type: Optional[str]) -> Optional[str]:
    """Prefer declared_type if valid, else infer from job_id prefix."""
    if declared_type in VALID_STAGES:
        return declared_type
    if job_id.startswith("daily_"):
        return "daily"
    if job_id.startswith("weekly_"):
        return "weekly"
    if job_id.startswith("monthly_"):
        return "monthly"
    return None


def try_load_stages_from_main() -> Optional[Dict[str, List[str]]]:
    """
    Try to read stage lists from main.py dynamically so we stay in sync.
    Returns None if not found — fall back to VALID_STAGES.
    """
    main_path = REPO_ROOT / "main.py"
    if not main_path.exists():
        return None
    try:
        # Light-weight: exec main.py in a namespace and grab known vars
        ns: Dict[str, Any] = {}
        src = main_path.read_text(encoding="utf-8")
        # Only exec top-level assignments — safe-ish for local tooling
        exec(compile(src, str(main_path), "exec"), ns)  # noqa: S102
        found: Dict[str, List[str]] = {}
        for key in ("DAILY_STAGES", "WEEKLY_STAGES", "MONTHLY_STAGES"):
            value = ns.get(key)
            if isinstance(value, list) and all(isinstance(x, str) for x in value):
                found[key.replace("_STAGES", "").lower()] = value
        return found or None
    except Exception as exc:
        logger.warning("main.py stage discovery failed: %s — using built-in defaults", exc)
        return None


# --------------------------------------------------------------------------- #
# Migration Action
# --------------------------------------------------------------------------- #
class Action:
    __slots__ = ("job_id", "field", "old", "new", "reason")

    def __init__(self, job_id: str, field: str, old: Any, new: Any, reason: str):
        self.job_id = job_id
        self.field = field
        self.old = old
        self.new = new
        self.reason = reason

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "field": self.field,
            "old": self.old,
            "new": self.new,
            "reason": self.reason,
        }

    def __repr__(self) -> str:
        return f"[{self.job_id}] {self.field}: {self.old!r} → {self.new!r}  ({self.reason})"


# --------------------------------------------------------------------------- #
# Per-Job Analysis
# --------------------------------------------------------------------------- #
def analyze_job(
    job_id: str,
    job: Dict[str, Any],
    reset_failed_final: bool,
    stuck_hours: int,
    stage_map: Dict[str, List[str]],
) -> Tuple[Dict[str, Any], List[Action], List[str]]:
    """Return (patched_job, actions, warnings). Does NOT mutate input."""
    patched = dict(job)
    actions: List[Action] = []
    warnings: List[str] = []

    # ---- 1. job_type ----
    declared_type = job.get("job_type")
    inferred_type = infer_job_type(job_id, declared_type)
    if inferred_type is None:
        warnings.append(f"Unknown job_type for {job_id} (declared={declared_type!r}) — skipping")
        return patched, actions, warnings

    if declared_type != inferred_type:
        actions.append(Action(job_id, "job_type", declared_type, inferred_type,
                              "corrected from job_id prefix"))
        patched["job_type"] = inferred_type

    valid_stages = stage_map.get(inferred_type, [])

    # ---- 2. status ----
    status = job.get("status")
    if status not in VALID_STATUSES:
        actions.append(Action(job_id, "status", status, "FAILED",
                              f"unknown status {status!r}"))
        patched["status"] = "FAILED"
        status = "FAILED"
    elif status == "COLLECTED":
        # Intermediate state that never completed — treat as FAILED for retry
        actions.append(Action(job_id, "status", "COLLECTED", "FAILED",
                              "intermediate COLLECTED state never progressed"))
        patched["status"] = "FAILED"
        status = "FAILED"

    # ---- 3. last_success_stage ----
    lss = job.get("last_success_stage")
    if lss is not None and lss not in valid_stages:
        actions.append(Action(job_id, "last_success_stage", lss, None,
                              f"stage {lss!r} not valid for job_type={inferred_type}"))
        patched["last_success_stage"] = None

    # ---- 4. failed_stage ----
    fs = job.get("failed_stage")
    if fs is not None and fs not in valid_stages:
        actions.append(Action(job_id, "failed_stage", fs, None,
                              f"stage {fs!r} not valid for job_type={inferred_type}"))
        patched["failed_stage"] = None

    # ---- 5. stuck RUNNING ----
    if status == "RUNNING":
        updated_at = parse_iso_safe(job.get("updated_at"))
        if updated_at is None:
            actions.append(Action(job_id, "status", "RUNNING", "FAILED",
                                  "RUNNING without valid updated_at"))
            patched["status"] = "FAILED"
            patched["error"] = "Recovered: RUNNING with invalid timestamp"
            status = "FAILED"
        else:
            age = now_utc() - updated_at
            if age > timedelta(hours=stuck_hours):
                actions.append(Action(job_id, "status", "RUNNING", "FAILED",
                                      f"stuck RUNNING for {age.total_seconds()/3600:.1f}h"))
                patched["status"] = "FAILED"
                patched["error"] = f"Recovered: stuck RUNNING (age={age})"
                status = "FAILED"

    # ---- 6. FAILED_FINAL → FAILED ----
    if status == "FAILED_FINAL" and reset_failed_final:
        actions.append(Action(job_id, "status", "FAILED_FINAL", "FAILED",
                              "reset for retry"))
        patched["status"] = "FAILED"
        if patched.get("failed_stage"):
            actions.append(Action(job_id, "failed_stage", patched["failed_stage"], None,
                                  "cleared on reset"))
            patched["failed_stage"] = None
        if patched.get("error"):
            actions.append(Action(job_id, "error", "<cleared>", None,
                                  "cleared on reset"))
            patched["error"] = None

    # ---- 7. attempts ----
    attempts = job.get("attempts", 0)
    if not isinstance(attempts, int) or attempts < 0:
        actions.append(Action(job_id, "attempts", attempts, 0, "invalid → 0"))
        patched["attempts"] = 0

    # ---- 8. timestamps ----
    for ts_field in ("created_at", "updated_at"):
        if not parse_iso_safe(job.get(ts_field)):
            new_ts = now_utc().isoformat()
            actions.append(Action(job_id, ts_field, job.get(ts_field), new_ts,
                                  f"invalid/missing {ts_field}"))
            patched[ts_field] = new_ts

    return patched, actions, warnings


# --------------------------------------------------------------------------- #
# Backup / Archive / Report
# --------------------------------------------------------------------------- #
def backup_state(state_file: Path) -> Optional[Path]:
    if not state_file.exists():
        return None
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = now_utc().strftime("%Y%m%d_%H%M%S")
    dst = BACKUP_DIR / f"jobs_{ts}.json"
    shutil.copy2(state_file, dst)
    logger.info("Backup: %s", dst)
    return dst


def append_to_archive(original_jobs: Dict[str, Any]) -> None:
    ARCHIVE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if ARCHIVE_FILE.exists():
        try:
            archive = json.loads(ARCHIVE_FILE.read_text(encoding="utf-8"))
        except Exception:
            archive = {"version": 1, "snapshots": []}
    else:
        archive = {"version": 1, "snapshots": []}

    archive.setdefault("snapshots", []).append({
        "archived_at": now_utc().isoformat(),
        "count": len(original_jobs),
        "jobs": original_jobs,
    })

    tmp = ARCHIVE_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(archive, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, ARCHIVE_FILE)
    logger.info("Archived %d jobs → %s", len(original_jobs), ARCHIVE_FILE)


def write_report(actions: List[Action], warnings: List[str], stats: Dict[str, Any], dry_run: bool) -> None:
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "generated_at": now_utc().isoformat(),
        "dry_run": dry_run,
        "stats": stats,
        "warnings": warnings,
        "actions": [a.to_dict() for a in actions],
    }
    REPORT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Report: %s", REPORT_FILE)


# --------------------------------------------------------------------------- #
# Atomic Write
# --------------------------------------------------------------------------- #
def save_state(state: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    with open(tmp, "rb") as f:
        os.fsync(f.fileno())
    os.replace(tmp, path)


# --------------------------------------------------------------------------- #
# Main migration
# --------------------------------------------------------------------------- #
def migrate(
    state_file: Path,
    dry_run: bool,
    reset_failed_final: bool,
    stuck_hours: int,
    no_backup: bool,
    reset_job: Optional[str],
) -> int:
    if not state_file.exists():
        logger.error("State file not found: %s", state_file)
        return 1

    state = json.loads(state_file.read_text(encoding="utf-8"))
    jobs = state.get("jobs", {})
    if not isinstance(jobs, dict):
        logger.error("Malformed state: 'jobs' is not a dict")
        return 1

    logger.info("Loaded %d job records from %s", len(jobs), state_file)

    # Discover stages
    discovered = try_load_stages_from_main()
    stage_map = discovered if discovered else VALID_STAGES
    logger.info("Using stage map: %s", {k: len(v) for k, v in stage_map.items()})

    original_snapshot = json.loads(json.dumps(jobs))
    new_jobs: Dict[str, Any] = {}
    all_actions: List[Action] = []
    all_warnings: List[str] = []

    for job_id, job in jobs.items():
        if not isinstance(job, dict):
            all_warnings.append(f"Malformed job entry: {job_id}")
            continue

        # If --reset-job specified, force only that job to FAILED
        if reset_job and job_id == reset_job:
            j = dict(job)
            j["status"] = "FAILED"
            j["failed_stage"] = None
            j["error"] = None
            j["updated_at"] = now_utc().isoformat()
            all_actions.append(Action(job_id, "status", job.get("status"), "FAILED",
                                      "manual reset (--reset-job)"))
            new_jobs[job_id] = j
            continue

        patched, acts, warns = analyze_job(
            job_id, job,
            reset_failed_final=reset_failed_final,
            stuck_hours=stuck_hours,
            stage_map=stage_map,
        )
        new_jobs[job_id] = patched
        all_actions.extend(acts)
        all_warnings.extend(warns)

    # ---- Stats ----
    stats: Dict[str, Any] = {
        "total_jobs": len(jobs),
        "total_actions": len(all_actions),
        "total_warnings": len(all_warnings),
        "jobs_by_status": {},
        "actions_by_field": {},
    }
    for j in new_jobs.values():
        s = j.get("status", "UNKNOWN")
        stats["jobs_by_status"][s] = stats["jobs_by_status"].get(s, 0) + 1
    for a in all_actions:
        stats["actions_by_field"][a.field] = stats["actions_by_field"].get(a.field, 0) + 1

    # ---- Human-readable summary ----
    print("\n" + "=" * 72)
    print(f"STATE MIGRATION {'(DRY RUN)' if dry_run else ''}")
    print("=" * 72)
    print(f"Total jobs:     {stats['total_jobs']}")
    print(f"Total actions:  {stats['total_actions']}")
    print(f"Total warnings: {stats['total_warnings']}")
    print(f"\nJobs by status:")
    for s, c in sorted(stats["jobs_by_status"].items()):
        print(f"  {s:15s} : {c}")
    print(f"\nActions by field:")
    for f, c in sorted(stats["actions_by_field"].items()):
        print(f"  {f:25s} : {c}")

    if all_actions:
        print(f"\n--- Detailed Actions ({len(all_actions)}) ---")
        for a in all_actions:
            print(f"  {a}")

    if all_warnings:
        print(f"\n--- Warnings ---")
        for w in all_warnings:
            print(f"  ⚠️  {w}")
    print("=" * 72 + "\n")

    write_report(all_actions, all_warnings, stats, dry_run)

    if dry_run:
        logger.info("Dry-run complete. No changes applied.")
        return 0

    if not all_actions:
        logger.info("Nothing to migrate — state already clean.")
        return 0

    if not no_backup:
        backup_state(state_file)
    else:
        logger.warning("Skipping backup (--no-backup)")

    append_to_archive(original_snapshot)

    state["jobs"] = new_jobs
    state["version"] = int(state.get("version", 1)) + 1
    state["last_migrated_at"] = now_utc().isoformat()
    save_state(state, state_file)
    logger.info("✔ Migration applied: %d actions. version → %s",
                len(all_actions), state["version"])
    return 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Clean & migrate state/jobs.json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--state-file", type=Path, default=STATE_FILE,
                   help=f"Path to jobs.json (default: {STATE_FILE})")
    p.add_argument("--dry-run", action="store_true",
                   help="Preview changes without writing")
    p.add_argument("--reset-failed-final", action="store_true",
                   help="Reset FAILED_FINAL jobs → FAILED for retry")
    p.add_argument("--stuck-hours", type=int, default=DEFAULT_STUCK_HOURS,
                   help=f"Hours after which RUNNING is 'stuck' (default: {DEFAULT_STUCK_HOURS})")
    p.add_argument("--reset-job", type=str, default=None,
                   help="Force a specific job_id to FAILED for retry")
    p.add_argument("--no-backup", action="store_true",
                   help="Skip backup (NOT recommended)")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    # Ensure logs/ exists
    (REPO_ROOT / "logs").mkdir(exist_ok=True)
    try:
        return migrate(
            state_file=args.state_file,
            dry_run=args.dry_run,
            reset_failed_final=args.reset_failed_final,
            stuck_hours=args.stuck_hours,
            no_backup=args.no_backup,
            reset_job=args.reset_job,
        )
    except Exception:
        logger.exception("Migration failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
