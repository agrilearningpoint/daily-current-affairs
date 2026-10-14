# -*- coding: utf-8 -*-
"""
State Migration & Cleanup Script
================================
One-time cleanup for legacy state/jobs.json.

Fixes:
- Invalid last_success_stage per job_type (e.g. daily has 21_monthly_editor)
- Legacy statuses (COLLECTED, RETRYING, QA_REJECTED, etc.) → FAILED for retry
- Stuck RUNNING jobs (> threshold hours) → FAILED
- FAILED_FINAL → FAILED (--reset-failed-final)
- Missing job_type inferred from job_id
- Missing timestamps filled
- Field aliases normalized (updated/failed_at → updated_at/failed_stage)

Safety:
- Dry-run mode (no writes)
- Auto-backup before write
- Append-only archive (full history)
- Atomic write (temp + fsync + os.replace)
- Idempotent (safe to re-run)
- Detailed JSON report

Usage:
    python maintenance/migrate_state.py --dry-run
    python maintenance/migrate_state.py --reset-failed-final
    python maintenance/migrate_state.py --reset-job daily_2026-10-13
    python maintenance/migrate_state.py --stuck-hours 4
    python maintenance/migrate_state.py --no-backup
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# --------------------------------------------------------------------------- #
# Paths & Logging
# --------------------------------------------------------------------------- #
REPO_ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = REPO_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(LOGS_DIR / "state_migration.log"), encoding="utf-8"),
    ],
)
logger = logging.getLogger("state_migration")

STATE_FILE = REPO_ROOT / "state" / "jobs.json"
BACKUP_DIR = REPO_ROOT / "state" / "backups"
ARCHIVE_FILE = REPO_ROOT / "state" / "archive" / "jobs_archive.json"
REPORT_FILE = REPO_ROOT / "state" / "migration_report.json"

# --------------------------------------------------------------------------- #
# Valid Stages per Job Type (mirror of main.py)
# --------------------------------------------------------------------------- #
VALID_STAGES: Dict[str, List[str]] = {
    "daily": [
        "00_model_orchestrator", "01_source_fetch", "03_news_collection",
        "04_fact_verification", "05_deduplication", "06_news_importance",
        "07_student_domain_relevance", "10_final_news_selection",
        "11_importance_memory", "12_content_editor", "16_mcq_generator",
        "17_mcq_validator", "18_pdf_design", "19_pdf_qa",
        "22_telegram_publisher", "23_telegram_pin_verifier",
        "24_final_health_audit",
    ],
    "weekly": ["20_weekly_editor", "22_telegram_publisher"],
    "monthly": ["21_monthly_editor", "22_telegram_publisher"],
}

VALID_STATUSES = {"PENDING", "RUNNING", "SUCCESS", "FAILED", "FAILED_FINAL"}

# Legacy intermediate statuses → normalize to FAILED for retry
LEGACY_FAILED_STATUSES = {
    "COLLECTED", "COLLECTING", "VERIFYING", "VERIFIED", "DEDUPLICATED",
    "SCORED", "SELECTED", "CONTENT_READY", "MCQ_READY", "MCQ_VALIDATED",
    "PDF_GENERATED", "QA_APPROVED", "QA_REJECTED", "PUBLISHED", "PIN_VERIFIED",
    "COMPLETE", "CREATED", "RETRYING", "RECOVERED",
}

DEFAULT_STUCK_HOURS = 2


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def infer_job_type(job_id: str) -> Optional[str]:
    if job_id.startswith("daily_"):
        return "daily"
    if job_id.startswith("weekly_"):
        return "weekly"
    if job_id.startswith("monthly_"):
        return "monthly"
    return None


# --------------------------------------------------------------------------- #
# Action tracking
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
def analyze(
    job_id: str,
    job: Dict[str, Any],
    reset_failed_final: bool,
    stuck_hours: int,
) -> Tuple[Dict[str, Any], List[Action], List[str]]:
    patched = dict(job)
    actions: List[Action] = []
    warnings: List[str] = []

    # ---- 1. job_type infer/fix ----
    jt = infer_job_type(job_id)
    if jt is None:
        warnings.append(f"Unknown job_type for {job_id} — skipping")
        return patched, actions, warnings
    if job.get("job_type") != jt:
        actions.append(Action(job_id, "job_type", job.get("job_type"), jt,
                              "inferred from job_id prefix"))
        patched["job_type"] = jt

    valid_stages = VALID_STAGES[jt]

    # ---- 2. Status normalization ----
    status = str(job.get("status", "")).upper()
    if status not in VALID_STATUSES:
        if status in LEGACY_FAILED_STATUSES:
            actions.append(Action(job_id, "status", status, "FAILED",
                                  "legacy intermediate status → FAILED"))
            patched["status"] = "FAILED"
            status = "FAILED"
        else:
            actions.append(Action(job_id, "status", status, "FAILED",
                                  "unknown status → FAILED"))
            patched["status"] = "FAILED"
            status = "FAILED"

    # ---- 3. last_success_stage validity ----
    lss = job.get("last_success_stage")
    if lss and lss not in valid_stages:
        actions.append(Action(job_id, "last_success_stage", lss, None,
                              f"stage not valid for {jt}"))
        patched["last_success_stage"] = None

    # ---- 4. failed_at / failed_stage validity ----
    for field in ("failed_at", "failed_stage"):
        fs = job.get(field)
        if fs and fs not in valid_stages:
            actions.append(Action(job_id, field, fs, None,
                                  f"stage not valid for {jt}"))
            patched[field] = None

    # ---- 5. Stuck RUNNING ----
    if status == "RUNNING":
        upd = parse_iso(job.get("updated_at") or job.get("updated"))
        if upd is None:
            actions.append(Action(job_id, "status", "RUNNING", "FAILED",
                                  "RUNNING without valid timestamp"))
            patched["status"] = "FAILED"
            status = "FAILED"
        elif (now_utc() - upd) > timedelta(hours=stuck_hours):
            age_h = (now_utc() - upd).total_seconds() / 3600
            actions.append(Action(job_id, "status", "RUNNING", "FAILED",
                                  f"stuck RUNNING for {age_h:.1f}h"))
            patched["status"] = "FAILED"
            patched["error"] = f"Recovered: stuck RUNNING ({age_h:.1f}h)"
            status = "FAILED"

    # ---- 6. FAILED_FINAL → FAILED ----
    if status == "FAILED_FINAL" and reset_failed_final:
        actions.append(Action(job_id, "status", "FAILED_FINAL", "FAILED",
                              "reset for retry"))
        patched["status"] = "FAILED"
        for field in ("failed_at", "failed_stage", "error"):
            if patched.get(field):
                actions.append(Action(job_id, field, "<cleared>", None,
                                      "cleared on FAILED_FINAL reset"))
                patched[field] = None

    # ---- 7. Field aliases → canonical ----
    if "updated" in patched and "updated_at" not in patched:
        patched["updated_at"] = patched.pop("updated")
    if "created" in patched and "created_at" not in patched:
        patched["created_at"] = patched.pop("created")
    if "failed_at" in patched and "failed_stage" not in patched:
        patched["failed_stage"] = patched.pop("failed_at")

    # ---- 8. Timestamps filled ----
    now_str = now_utc().isoformat()
    if not parse_iso(patched.get("updated_at")):
        patched["updated_at"] = now_str
    if not parse_iso(patched.get("created_at")):
        patched["created_at"] = now_str

    # ---- 9. attempts int ----
    try:
        patched["attempts"] = max(0, int(patched.get("attempts", 0)))
    except (TypeError, ValueError):
        patched["attempts"] = 0

    return patched, actions, warnings


# --------------------------------------------------------------------------- #
# Atomic I/O
# --------------------------------------------------------------------------- #
def load_state() -> Any:
    if not STATE_FILE.exists():
        raise FileNotFoundError(f"State not found: {STATE_FILE}")
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


def save_state(state: Any) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        prefix=".jobs_", suffix=".tmp", dir=str(STATE_FILE.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, STATE_FILE)
    except Exception:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        raise


def backup_state() -> Optional[Path]:
    if not STATE_FILE.exists():
        return None
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = now_utc().strftime("%Y%m%d_%H%M%S")
    dst = BACKUP_DIR / f"jobs_{ts}.json"
    shutil.copy2(STATE_FILE, dst)
    logger.info("Backup: %s", dst)
    return dst


def append_archive(jobs_snapshot: Dict[str, Any]) -> None:
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
        "count": len(jobs_snapshot),
        "jobs": jobs_snapshot,
    })

    tmp = ARCHIVE_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(archive, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    os.replace(tmp, ARCHIVE_FILE)
    logger.info("Archived %d jobs → %s", len(jobs_snapshot), ARCHIVE_FILE)


# --------------------------------------------------------------------------- #
# Migration
# --------------------------------------------------------------------------- #
def migrate(
    dry_run: bool,
    reset_failed_final: bool,
    stuck_hours: int,
    no_backup: bool,
    reset_job: Optional[str],
) -> int:
    if not STATE_FILE.exists():
        logger.error("State file not found: %s", STATE_FILE)
        return 1

    state = load_state()

    # Support both {"jobs": {...}} and flat {job_id: {...}}
    if isinstance(state, dict) and "jobs" in state and isinstance(state["jobs"], dict):
        jobs = state["jobs"]
        wrapper = state
    elif isinstance(state, dict):
        jobs = state
        wrapper = {"jobs": jobs, "version": 1}
    else:
        logger.error("Malformed state: top-level must be a dict")
        return 1

    logger.info("Loaded %d job records from %s", len(jobs), STATE_FILE)

    original_snapshot = json.loads(json.dumps(jobs))
    new_jobs: Dict[str, Any] = {}
    all_actions: List[Action] = []
    all_warnings: List[str] = []

    for job_id, job in jobs.items():
        if not isinstance(job, dict):
            all_warnings.append(f"Malformed job entry: {job_id}")
            continue

        # Manual reset for a single job
        if reset_job and job_id == reset_job:
            j = dict(job)
            j["status"] = "FAILED"
            j["failed_stage"] = None
            j["failed_at"] = None
            j["error"] = None
            j["updated_at"] = now_utc().isoformat()
            all_actions.append(Action(job_id, "status", job.get("status"), "FAILED",
                                      "manual reset (--reset-job)"))
            new_jobs[job_id] = j
            continue

        patched, acts, warns = analyze(
            job_id, job,
            reset_failed_final=reset_failed_final,
            stuck_hours=stuck_hours,
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

    # ---- Print summary ----
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
            print(f"  ⚠  {w}")
    print("=" * 72 + "\n")

    # ---- Report ----
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(
        json.dumps({
            "generated_at": now_utc().isoformat(),
            "dry_run": dry_run,
            "stats": stats,
            "warnings": all_warnings,
            "actions": [a.to_dict() for a in all_actions],
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if dry_run:
        logger.info("Dry-run complete. No changes applied.")
        return 0

    if not all_actions:
        logger.info("Nothing to migrate — state already clean.")
        return 0

    if not no_backup:
        backup_state()
    append_archive(original_snapshot)

    wrapper["jobs"] = new_jobs
    wrapper["version"] = int(wrapper.get("version", 1)) + 1
    wrapper["last_migrated_at"] = now_utc().isoformat()
    save_state(wrapper)
    logger.info(
        "✔ Migration applied: %d actions. version → %s",
        len(all_actions), wrapper["version"],
    )
    return 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Clean & migrate state/jobs.json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python maintenance/migrate_state.py --dry-run
  python maintenance/migrate_state.py --reset-failed-final
  python maintenance/migrate_state.py --reset-job daily_2026-10-13
  python maintenance/migrate_state.py --stuck-hours 4
""",
    )
    p.add_argument("--dry-run", action="store_true",
                   help="Preview changes without writing")
    p.add_argument("--reset-failed-final", action="store_true",
                   help="Reset FAILED_FINAL jobs → FAILED for retry")
    p.add_argument("--stuck-hours", type=int, default=DEFAULT_STUCK_HOURS,
                   help=f"Stuck RUNNING threshold (default: {DEFAULT_STUCK_HOURS}h)")
    p.add_argument("--reset-job", type=str, default=None,
                   help="Force a specific job_id to FAILED")
    p.add_argument("--no-backup", action="store_true",
                   help="Skip backup (NOT recommended)")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    try:
        return migrate(
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
