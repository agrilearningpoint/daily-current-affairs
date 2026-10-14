# -*- coding: utf-8 -*-
"""
Pipeline Orchestrator — Production Grade
=========================================
Daily / Weekly / Monthly news pipeline orchestrator.

Backward-compatible with legacy state/jobs.json:
- Field aliases: updated<->updated_at, created<->created_at, failed_at<->failed_stage
- Missing job_type inferred from job_id prefix (daily_/weekly_/monthly_)
- Legacy intermediate statuses (COLLECTED, RETRYING, QA_REJECTED, ...) → FAILED

Critical fixes vs previous version:
- SCRIPTS_DIR dynamically resolved (agents/ + pipeline/)
- Missing CRITICAL stage => job FAILED (never silently SKIPPED)
- --type alias for --job-type (workflow compatibility)
- --watchdog flag support (README compliant)
- pipeline/state.py state-machine sync (best-effort)
"""
from __future__ import annotations

import argparse
import fcntl
import json
import logging
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, ValidationError, model_validator

# --------------------------------------------------------------------------- #
# Paths & Constants
# --------------------------------------------------------------------------- #
REPO_ROOT = Path(__file__).resolve().parent
STATE_FILE = REPO_ROOT / "state" / "jobs.json"
LOCK_DIR = REPO_ROOT / "state" / "locks"
METRICS_DIR = REPO_ROOT / "state" / "metrics"
LOGS_DIR = REPO_ROOT / "logs"
RECOVERY_PLAN_FILE = REPO_ROOT / "recovery_plan.json"

STAGE_TIMEOUT_SECONDS = int(os.getenv("STAGE_TIMEOUT_SECONDS", "900"))
MAX_STAGE_RETRIES = int(os.getenv("MAX_STAGE_RETRIES", "3"))
BACKOFF_BASE = 2
WATCHDOG_STUCK_HOURS_DEFAULT = int(os.getenv("WATCHDOG_STUCK_HOURS", "2"))

# Canonical orchestrator statuses
VALID_ORCH_STATUSES = {"PENDING", "RUNNING", "SUCCESS", "FAILED", "FAILED_FINAL"}

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
LOGS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(LOGS_DIR / "orchestrator.log"), encoding="utf-8"),
    ],
)
logger = logging.getLogger("orchestrator")


# --------------------------------------------------------------------------- #
# Pydantic Models — Backward Compatible
# --------------------------------------------------------------------------- #
class JobRecord(BaseModel):
    """
    Job record with backward-compatible field aliases.

    Supports BOTH schemas:
        main.py style:    updated_at, failed_stage, created_at, job_type
        pipeline style:   updated,    failed_at,    created,    (no job_type)
    """
    model_config = {"populate_by_name": True, "extra": "ignore"}

    job_id: str
    job_type: str = "daily"
    status: str = "PENDING"
    created_at: str = ""
    updated_at: str = ""
    last_success_stage: Optional[str] = None
    failed_stage: Optional[str] = None
    attempts: int = 0
    error: Optional[str] = None
    # Legacy passthrough
    job_date: Optional[str] = None
    stage_history: List[Dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _normalize_legacy(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        d = dict(data)

        # --- Field aliases: legacy → canonical ---
        if "updated" in d and not d.get("updated_at"):
            d["updated_at"] = d.pop("updated")
        if "created" in d and not d.get("created_at"):
            d["created_at"] = d.pop("created")
        if "failed_at" in d and not d.get("failed_stage"):
            d["failed_stage"] = d.pop("failed_at")

        # --- Infer job_type from job_id if missing ---
        if not d.get("job_type"):
            jid = str(d.get("job_id", ""))
            if jid.startswith("daily_"):
                d["job_type"] = "daily"
            elif jid.startswith("weekly_"):
                d["job_type"] = "weekly"
            elif jid.startswith("monthly_"):
                d["job_type"] = "monthly"
            else:
                d["job_type"] = "daily"

        # --- Fill missing timestamps ---
        now = datetime.now(timezone.utc).isoformat()
        d.setdefault("created_at", now)
        d.setdefault("updated_at", now)

        # --- Normalize legacy status → orchestrator status ---
        status = str(d.get("status", "PENDING"))
        if status not in VALID_ORCH_STATUSES:
            original = status
            d["status"] = "FAILED"
            if not d.get("error"):
                d["error"] = f"Legacy status '{original}' normalized to FAILED for retry"
            # If a legacy intermediate state existed, keep last_success_stage
            # so orchestrator can resume from the correct point.

        # --- Sanity: attempts must be int >= 0 ---
        try:
            d["attempts"] = max(0, int(d.get("attempts", 0)))
        except (TypeError, ValueError):
            d["attempts"] = 0

        return d


class PipelineState(BaseModel):
    model_config = {"extra": "ignore"}
    jobs: Dict[str, JobRecord] = Field(default_factory=dict)
    version: int = 1
    last_migrated_at: Optional[str] = None


# --------------------------------------------------------------------------- #
# Stage Definitions — (stage_id, critical, candidates)
# --------------------------------------------------------------------------- #
DAILY_STAGES: List[Tuple[str, bool, List[str]]] = [
    ("00_model_orchestrator",       True,  ["agents/00_model_orchestrator.py",
                                             "pipeline/00_model_orchestrator.py"]),
    ("01_source_fetch",             True,  ["pipeline/01_source_fetch.py",
                                             "agents/01_source_fetch.py"]),
    ("03_news_collection",          True,  ["agents/03_news_collection.py",
                                             "pipeline/03_news_collection.py"]),
    ("04_fact_verification",        True,  ["agents/04_fact_verification.py",
                                             "pipeline/04_fact_verification.py"]),
    ("05_deduplication",            True,  ["agents/05_deduplication.py"]),
    ("06_news_importance",          True,  ["agents/06_news_importance.py"]),
    ("07_student_domain_relevance", True,  ["agents/07_student_domain_relevance.py"]),
    ("10_final_news_selection",     True,  ["agents/10_final_news_selection.py"]),
    ("11_importance_memory",        True,  ["agents/11_importance_memory.py"]),
    ("12_content_editor",           True,  ["agents/12_content_editor.py",
                                             "pipeline/12_content_editor.py"]),
    ("16_mcq_generator",            True,  ["agents/16_mcq_generator.py"]),
    ("17_mcq_validator",            True,  ["agents/17_mcq_validator.py"]),
    ("18_pdf_design",               True,  ["agents/18_pdf_design.py"]),
    ("19_pdf_qa",                   True,  ["agents/19_pdf_qa.py"]),
    ("22_telegram_publisher",       True,  ["agents/22_telegram_publisher.py",
                                             "agents/14_telegram_publish.py",
                                             "pipeline/14_telegram_publish.py"]),
    ("23_telegram_pin_verifier",    True,  ["agents/23_telegram_pin_verifier.py"]),
    ("24_final_health_audit",       False, ["agents/24_final_health_audit.py"]),
]

WEEKLY_STAGES: List[Tuple[str, bool, List[str]]] = [
    ("20_weekly_editor",      True, ["agents/20_weekly_editor.py"]),
    ("22_telegram_publisher", True, ["agents/22_telegram_publisher.py",
                                      "agents/14_telegram_publish.py"]),
]

MONTHLY_STAGES: List[Tuple[str, bool, List[str]]] = [
    ("21_monthly_editor",     True, ["agents/21_monthly_editor.py"]),
    ("22_telegram_publisher", True, ["agents/22_telegram_publisher.py",
                                      "agents/14_telegram_publish.py"]),
]

STAGE_MAP: Dict[str, List[Tuple[str, bool, List[str]]]] = {
    "daily": DAILY_STAGES,
    "weekly": WEEKLY_STAGES,
    "monthly": MONTHLY_STAGES,
}

# stage_id → pipeline/state.py state
STAGE_TO_STATE: Dict[str, str] = {
    "00_model_orchestrator": "CREATED",
    "01_source_fetch":       "COLLECTING",
    "03_news_collection":    "COLLECTED",
    "04_fact_verification":  "VERIFIED",
    "05_deduplication":      "DEDUPLICATED",
    "06_news_importance":    "SCORED",
    "07_student_domain_relevance": "SCORED",
    "10_final_news_selection": "SELECTED",
    "11_importance_memory":  "SELECTED",
    "12_content_editor":     "CONTENT_READY",
    "16_mcq_generator":      "MCQ_READY",
    "17_mcq_validator":      "MCQ_VALIDATED",
    "18_pdf_design":         "PDF_GENERATED",
    "19_pdf_qa":             "QA_APPROVED",
    "20_weekly_editor":      "SELECTED",
    "21_monthly_editor":     "SELECTED",
    "22_telegram_publisher": "PUBLISHED",
    "23_telegram_pin_verifier": "PIN_VERIFIED",
    "24_final_health_audit": "COMPLETE",
}


def stages_for(job_type: str) -> List[Tuple[str, bool, List[str]]]:
    if job_type not in STAGE_MAP:
        raise ValueError(f"Unknown job type: {job_type}")
    return STAGE_MAP[job_type]


# --------------------------------------------------------------------------- #
# File Locking (fcntl-based, cross-platform fallback)
# --------------------------------------------------------------------------- #
class JobLock:
    """Cross-process lock via fcntl. Auto-releases on crash (fd close)."""

    def __init__(self, job_id: str):
        LOCK_DIR.mkdir(parents=True, exist_ok=True)
        self.lock_path = LOCK_DIR / f"{job_id}.lock"
        self._fh = None

    def __enter__(self):
        self._fh = open(self.lock_path, "w")
        try:
            fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self._fh.close()
            self._fh = None
            raise RuntimeError(
                f"Job {self.lock_path.stem} already running (lock held). "
                f"If this is stale, delete: {self.lock_path}"
            )
        self._fh.write(f"pid={os.getpid()}\nat={datetime.now(timezone.utc).isoformat()}\n")
        self._fh.flush()
        return self

    def __exit__(self, *exc):
        try:
            if self._fh:
                try:
                    fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
                finally:
                    self._fh.close()
        finally:
            try:
                os.remove(self.lock_path)
            except FileNotFoundError:
                pass


# --------------------------------------------------------------------------- #
# Atomic State I/O
# --------------------------------------------------------------------------- #
def load_state() -> PipelineState:
    if not STATE_FILE.exists():
        return PipelineState()
    try:
        raw = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        # Support both {"jobs": {...}} and flat {job_id: {...}}
        if isinstance(raw, dict) and "jobs" not in raw and "version" not in raw:
            raw = {"jobs": raw, "version": 1}
        return PipelineState(**raw)
    except (json.JSONDecodeError, ValidationError) as exc:
        backup = STATE_FILE.with_suffix(f".corrupt.{int(time.time())}.json")
        try:
            shutil.copy2(STATE_FILE, backup)
            logger.error("Corrupt state backed up to %s. Error: %s", backup, exc)
        except Exception:
            logger.error("Corrupt state (backup failed): %s", exc)
        return PipelineState()


def save_state(state: PipelineState) -> None:
    """Atomic write: temp + fsync + os.replace."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        prefix=".jobs_", suffix=".tmp", dir=str(STATE_FILE.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state.model_dump(mode="json"), f, ensure_ascii=False, indent=2)
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


# --------------------------------------------------------------------------- #
# State Transitions
# --------------------------------------------------------------------------- #
VALID_TRANSITIONS: Dict[str, set] = {
    "PENDING":      {"RUNNING"},
    "RUNNING":      {"SUCCESS", "FAILED", "FAILED_FINAL"},
    "FAILED":       {"RUNNING", "FAILED_FINAL"},
    "FAILED_FINAL": set(),
    "SUCCESS":      set(),
}


def transition(job: JobRecord, new_status: str) -> None:
    """Validate and apply a status transition."""
    if new_status == job.status:
        return
    allowed = VALID_TRANSITIONS.get(job.status, set())
    if new_status not in allowed:
        raise ValueError(f"Invalid transition: {job.status} → {new_status}")
    job.status = new_status
    job.updated_at = datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------- #
# Stage Resolution
# --------------------------------------------------------------------------- #
def resolve_stage_script(candidates: List[str]) -> Optional[Path]:
    """Return first existing candidate path, else None."""
    for rel in candidates:
        p = REPO_ROOT / rel
        if p.exists() and p.is_file():
            return p
    return None


def run_stage(
    stage_id: str,
    critical: bool,
    candidates: List[str],
    timeout: int = STAGE_TIMEOUT_SECONDS,
) -> str:
    """
    Run one stage. Returns:
      'SUCCESS' | 'FAILED' | 'MISSING'
    """
    script = resolve_stage_script(candidates)

    if script is None:
        tried = ", ".join(candidates)
        if critical:
            logger.error("✘ CRITICAL MISSING: %s — tried: %s", stage_id, tried)
        else:
            logger.warning("⚠ OPTIONAL MISSING: %s — tried: %s", stage_id, tried)
        return "MISSING"

    logger.info("▶ Running stage: %s (%s)", stage_id, script.relative_to(REPO_ROOT))
    start = time.time()
    try:
        proc = subprocess.Popen(
            [sys.executable, str(script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(REPO_ROOT),
            preexec_fn=os.setsid if hasattr(os, "setsid") else None,
        )
        try:
            output, _ = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            logger.error("Stage %s timed out after %ds — killing", stage_id, timeout)
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
            try:
                proc.wait(timeout=10)
            except Exception:
                pass
            return "FAILED"

        elapsed = time.time() - start
        if proc.returncode == 0:
            logger.info("✔ Stage %s succeeded in %.1fs", stage_id, elapsed)
            return "SUCCESS"

        logger.error(
            "✘ Stage %s failed (exit=%d) in %.1fs. Output tail:\n%s",
            stage_id, proc.returncode, elapsed, (output or "")[-2000:],
        )
        return "FAILED"
    except Exception as exc:
        logger.exception("Unexpected error running %s: %s", stage_id, exc)
        return "FAILED"


def run_stage_with_retry(
    stage_id: str,
    critical: bool,
    candidates: List[str],
) -> str:
    """Retry with exponential backoff. Returns final status."""
    last = "FAILED"
    for attempt in range(1, MAX_STAGE_RETRIES + 1):
        result = run_stage(stage_id, critical, candidates)
        if result == "SUCCESS":
            return result
        if result == "MISSING" and not critical:
            return result
        last = result
        if attempt < MAX_STAGE_RETRIES:
            wait = BACKOFF_BASE ** attempt
            logger.warning(
                "Stage %s attempt %d/%d failed. Retry in %ds...",
                stage_id, attempt, MAX_STAGE_RETRIES, wait,
            )
            time.sleep(wait)
    return last


# --------------------------------------------------------------------------- #
# pipeline/state.py Sync (best-effort)
# --------------------------------------------------------------------------- #
def sync_pipeline_state(job_id: str, job_type: str, stage_id: str) -> None:
    """Best-effort sync with pipeline.state. Silently skip if unavailable."""
    new_state = STAGE_TO_STATE.get(stage_id)
    if not new_state:
        return
    try:
        from pipeline.state import load_job, save_job  # type: ignore
    except Exception:
        return

    try:
        # pipeline.state.load_job(job_id, job_type, job_date)
        job_date = job_id.split("_", 1)[1] if "_" in job_id else datetime.now(timezone.utc).strftime("%Y-%m-%d")
        job = load_job(job_id, job_type, job_date)
        save_job(job, state=new_state, stage=stage_id)
    except Exception as exc:
        logger.debug("pipeline.state sync skipped for %s: %s", stage_id, exc)


# --------------------------------------------------------------------------- #
# Job Management
# --------------------------------------------------------------------------- #
def get_or_create_job(state: PipelineState, job_id: str, job_type: str) -> JobRecord:
    if job_id in state.jobs:
        return state.jobs[job_id]
    now = datetime.now(timezone.utc).isoformat()
    job = JobRecord(
        job_id=job_id,
        job_type=job_type,
        status="PENDING",
        created_at=now,
        updated_at=now,
    )
    state.jobs[job_id] = job
    return job


def resume_index(
    stages: List[Tuple[str, bool, List[str]]],
    last_success: Optional[str],
) -> int:
    if not last_success:
        return 0
    ids = [s[0] for s in stages]
    if last_success not in ids:
        return 0
    return ids.index(last_success) + 1


# --------------------------------------------------------------------------- #
# Job Execution
# --------------------------------------------------------------------------- #
def execute_job(job_id: str, job_type: str) -> bool:
    with JobLock(job_id):
        state = load_state()
        job = get_or_create_job(state, job_id, job_type)

        if job.status == "SUCCESS":
            logger.info("Job %s already SUCCESS — skipping.", job_id)
            return True

        if job.status == "FAILED_FINAL":
            logger.warning("Job %s was FAILED_FINAL — resetting for retry.", job_id)
            job.status = "FAILED"
            job.failed_stage = None
            job.error = None

        try:
            transition(job, "RUNNING")
        except ValueError as exc:
            logger.error("Cannot start job %s: %s", job_id, exc)
            return False

        job.attempts += 1
        save_state(state)

        stages = stages_for(job_type)
        start_idx = resume_index(stages, job.last_success_stage)
        logger.info(
            "Job %s | type=%s | resuming from index %d (next: %s)",
            job_id, job_type, start_idx,
            stages[start_idx][0] if start_idx < len(stages) else "END",
        )

        for stage_id, critical, candidates in stages[start_idx:]:
            result = run_stage_with_retry(stage_id, critical, candidates)

            if result == "SUCCESS":
                job.last_success_stage = stage_id
                job.failed_stage = None
                job.error = None
                save_state(state)
                sync_pipeline_state(job_id, job_type, stage_id)
                continue

            if result == "MISSING" and not critical:
                logger.warning("Optional stage %s missing — continuing.", stage_id)
                continue

            # FAILED or CRITICAL MISSING → job fails
            reason = (
                "script missing (critical)" if result == "MISSING"
                else "stage execution failed"
            )
            job.failed_stage = stage_id
            job.error = f"{stage_id}: {reason}"

            final = job.attempts >= MAX_STAGE_RETRIES
            try:
                transition(job, "FAILED_FINAL" if final else "FAILED")
            except ValueError as exc:
                logger.error("Transition error for %s: %s", job_id, exc)
                job.status = "FAILED_FINAL" if final else "FAILED"
                job.updated_at = datetime.now(timezone.utc).isoformat()

            logger.error(
                "Job %s → %s at %s (%s)",
                job_id, job.status, stage_id, reason,
            )
            save_state(state)
            _write_metrics(job)
            return False

        transition(job, "SUCCESS")
        save_state(state)
        logger.info("✔ Job %s completed successfully.", job_id)
        _write_metrics(job)
        return True


def _write_metrics(job: JobRecord) -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        (METRICS_DIR / f"{job.job_id}.json").write_text(
            json.dumps(job.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as exc:
        logger.warning("Metrics write failed for %s: %s", job.job_id, exc)


# --------------------------------------------------------------------------- #
# Watchdog
# --------------------------------------------------------------------------- #
def run_watchdog(stuck_hours: int = WATCHDOG_STUCK_HOURS_DEFAULT) -> int:
    """
    Detect stuck RUNNING jobs & recent FAILED_FINAL jobs.
    Auto-reset stuck RUNNING → FAILED. Write recovery_plan.json.
    """
    logger.info("🐕 Watchdog running (stuck threshold = %dh)", stuck_hours)
    state = load_state()
    now = datetime.now(timezone.utc)

    stale_running: List[str] = []
    recent_failed: List[str] = []

    for job_id, job in state.jobs.items():
        try:
            updated = datetime.fromisoformat(job.updated_at.replace("Z", "+00:00"))
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
        except Exception:
            continue

        if job.status == "RUNNING":
            age_h = (now - updated).total_seconds() / 3600
            if age_h > stuck_hours:
                stale_running.append(job_id)
                logger.warning("STUCK: %s (RUNNING %.1fh)", job_id, age_h)

        if job.status == "FAILED_FINAL":
            if (now - updated).total_seconds() < 7 * 86400:
                recent_failed.append(job_id)

    actions: List[Dict[str, Any]] = []

    for job_id in stale_running:
        job = state.jobs[job_id]
        try:
            transition(job, "FAILED")
            job.error = "Watchdog: reset from stuck RUNNING"
            actions.append({"job_id": job_id, "action": "reset_running_to_failed"})
        except ValueError as exc:
            logger.warning("Cannot reset %s: %s", job_id, exc)

    if stale_running:
        save_state(state)

    plan = {
        "generated_at": now.isoformat(),
        "stuck_hours": stuck_hours,
        "stuck_running": stale_running,
        "recent_failed_final": recent_failed,
        "actions": actions,
    }
    try:
        RECOVERY_PLAN_FILE.write_text(
            json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info("Recovery plan written: %s", RECOVERY_PLAN_FILE)
    except Exception as exc:
        logger.error("Failed to write recovery plan: %s", exc)

    logger.info(
        "Watchdog complete. Stuck=%d | Recent FAILED_FINAL=%d",
        len(stale_running), len(recent_failed),
    )
    return 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_job_id(job_type: str, ref: Optional[str] = None) -> str:
    date = ref or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"{job_type}_{date}"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="News pipeline orchestrator")
    # --type alias for --job-type (workflow compatibility)
    p.add_argument(
        "--job-type", "--type",
        dest="job_type",
        choices=["daily", "weekly", "monthly"],
        required=False,
    )
    p.add_argument("--date", help="YYYY-MM-DD reference (default: today UTC)")
    p.add_argument("--reset", action="store_true",
                   help="Reset state for this job before running")
    p.add_argument("--watchdog", action="store_true",
                   help="Run watchdog mode (stuck job detection + recovery plan)")
    p.add_argument("--stuck-hours", type=int, default=WATCHDOG_STUCK_HOURS_DEFAULT,
                   help=f"Watchdog stuck threshold in hours (default: {WATCHDOG_STUCK_HOURS_DEFAULT})")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    # Watchdog mode
    if args.watchdog:
        return run_watchdog(stuck_hours=args.stuck_hours)

    if not args.job_type:
        logger.error("Either --job-type/--type is required, or use --watchdog")
        return 2

    job_id = build_job_id(args.job_type, args.date)

    if args.reset:
        state = load_state()
        if job_id in state.jobs:
            del state.jobs[job_id]
            save_state(state)
            logger.info("Reset state for job %s", job_id)

    try:
        ok = execute_job(job_id, args.job_type)
    except Exception:
        logger.exception("Orchestrator crashed")
        return 1
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
