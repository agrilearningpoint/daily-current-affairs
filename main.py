# -*- coding: utf-8 -*-
"""
Pipeline Orchestrator — Production Grade
=========================================
Yeh module daily/weekly/monthly news pipeline ko orchestrate karta hai.

Critical fix vs previous version:
- SCRIPTS_DIR dynamically resolve hota hai (agents/ + pipeline/)
- Missing CRITICAL stage => job FAILED (silently SKIPPED nahi)
- --type aur --job-type dono accept karta hai (workflow compatibility)
- --watchdog flag support (README compliant)
- pipeline/state.py ke saath state-machine sync
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
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, ValidationError

# --------------------------------------------------------------------------- #
# Paths & Constants
# --------------------------------------------------------------------------- #
REPO_ROOT = Path(__file__).resolve().parent
AGENTS_DIR = REPO_ROOT / "agents"
PIPELINE_DIR = REPO_ROOT / "pipeline"
STATE_FILE = REPO_ROOT / "state" / "jobs.json"
LOCK_DIR = REPO_ROOT / "state" / "locks"
METRICS_DIR = REPO_ROOT / "state" / "metrics"

STAGE_TIMEOUT_SECONDS = int(os.getenv("STAGE_TIMEOUT_SECONDS", "900"))
MAX_STAGE_RETRIES = int(os.getenv("MAX_STAGE_RETRIES", "3"))
BACKOFF_BASE = 2

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/orchestrator.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("orchestrator")


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #
class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    FAILED_FINAL = "FAILED_FINAL"


class StageResult(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    MISSING = "MISSING"


# --------------------------------------------------------------------------- #
# Pydantic Models
# --------------------------------------------------------------------------- #
class JobRecord(BaseModel):
    job_id: str
    job_type: str
    status: JobStatus = JobStatus.PENDING
    created_at: str
    updated_at: str
    last_success_stage: Optional[str] = None
    failed_stage: Optional[str] = None
    attempts: int = 0
    error: Optional[str] = None


class PipelineState(BaseModel):
    jobs: Dict[str, JobRecord] = Field(default_factory=dict)
    version: int = 1


# --------------------------------------------------------------------------- #
# STAGE DEFINITIONS
# --------------------------------------------------------------------------- #
# Har stage ka structure:
#   (stage_id, critical, candidates)
# - critical=True => missing file = FAIL, skip nahi
# - candidates: kis folder/file mein ho sakta hai (order matters)
#
# Aapki repo ke actual files ke basis par mapping:
# --------------------------------------------------------------------------- #

DAILY_STAGES: List[Tuple[str, bool, List[str]]] = [
    # (stage_id,              critical, candidate paths relative to repo root)
    ("00_model_orchestrator", True,  ["agents/00_model_orchestrator.py",
                                       "pipeline/00_model_orchestrator.py"]),
    ("01_source_fetch",       True,  ["pipeline/01_source_fetch.py",
                                       "agents/01_source_fetch.py"]),
    ("03_news_collection",    True,  ["agents/03_news_collection.py",
                                       "pipeline/03_news_collection.py"]),
    ("04_fact_verification",  True,  ["agents/04_fact_verification.py",
                                       "pipeline/04_fact_verification.py"]),
    ("05_deduplication",      True,  ["agents/05_deduplication.py"]),
    ("06_news_importance",    True,  ["agents/06_news_importance.py"]),
    ("07_student_domain_relevance", True, ["agents/07_student_domain_relevance.py"]),
    ("10_final_news_selection", True, ["agents/10_final_news_selection.py"]),
    ("11_importance_memory",  True,  ["agents/11_importance_memory.py"]),
    ("12_content_editor",     True,  ["agents/12_content_editor.py"]),
    ("16_mcq_generator",      True,  ["agents/16_mcq_generator.py"]),
    ("17_mcq_validator",      True,  ["agents/17_mcq_validator.py"]),
    ("18_pdf_design",         True,  ["agents/18_pdf_design.py"]),
    ("19_pdf_qa",             True,  ["agents/19_pdf_qa.py"]),
    ("22_telegram_publisher", True,  ["agents/22_telegram_publisher.py",
                                       "agents/14_telegram_publish.py"]),
    ("23_telegram_pin_verifier", True, ["agents/23_telegram_pin_verifier.py"]),
    ("24_final_health_audit", False, ["agents/24_final_health_audit.py"]),
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

# Stage → pipeline/state.py state mapping
STAGE_TO_STATE: Dict[str, str] = {
    "00_model_orchestrator": "CREATED",
    "01_source_fetch": "COLLECTING",
    "03_news_collection": "COLLECTED",
    "04_fact_verification": "VERIFIED",
    "05_deduplication": "DEDUPLICATED",
    "06_news_importance": "SCORED",
    "07_student_domain_relevance": "SCORED",
    "10_final_news_selection": "SELECTED",
    "11_importance_memory": "SELECTED",
    "12_content_editor": "CONTENT_READY",
    "16_mcq_generator": "MCQ_READY",
    "17_mcq_validator": "MCQ_VALIDATED",
    "18_pdf_design": "PDF_GENERATED",
    "19_pdf_qa": "QA_APPROVED",
    "20_weekly_editor": "SELECTED",
    "21_monthly_editor": "SELECTED",
    "22_telegram_publisher": "PUBLISHED",
    "23_telegram_pin_verifier": "PIN_VERIFIED",
    "24_final_health_audit": "COMPLETE",
}


def stages_for(job_type: str) -> List[Tuple[str, bool, List[str]]]:
    if job_type not in STAGE_MAP:
        raise ValueError(f"Unknown job type: {job_type}")
    return STAGE_MAP[job_type]


# --------------------------------------------------------------------------- #
# File Locking
# --------------------------------------------------------------------------- #
class JobLock:
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
            raise RuntimeError(f"Job {self.lock_path.stem} already running (lock held)")
        self._fh.write(f"{os.getpid()}\n{datetime.now(timezone.utc).isoformat()}\n")
        self._fh.flush()
        return self

    def __exit__(self, *exc):
        try:
            if self._fh:
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
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
        return PipelineState(**json.loads(STATE_FILE.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, ValidationError) as exc:
        backup = STATE_FILE.with_suffix(f".corrupt.{int(time.time())}.json")
        shutil.copy2(STATE_FILE, backup)
        logger.error("Corrupt state backed up to %s. Error: %s", backup, exc)
        return PipelineState()


def save_state(state: PipelineState) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".jobs_", suffix=".tmp", dir=str(STATE_FILE.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state.model_dump(mode="json"), f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, STATE_FILE)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


# --------------------------------------------------------------------------- #
# State Transitions
# --------------------------------------------------------------------------- #
VALID_TRANSITIONS = {
    JobStatus.PENDING: {JobStatus.RUNNING},
    JobStatus.RUNNING: {JobStatus.SUCCESS, JobStatus.FAILED, JobStatus.FAILED_FINAL},
    JobStatus.FAILED: {JobStatus.RUNNING, JobStatus.FAILED_FINAL},
    JobStatus.FAILED_FINAL: set(),
    JobStatus.SUCCESS: set(),
}


def transition(job: JobRecord, new_status: JobStatus) -> None:
    if new_status == job.status:
        return
    if new_status not in VALID_TRANSITIONS.get(job.status, set()):
        raise ValueError(f"Invalid transition: {job.status} → {new_status}")
    job.status = new_status
    job.updated_at = datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------- #
# Stage Resolution (CRITICAL FIX)
# --------------------------------------------------------------------------- #
def resolve_stage_script(candidates: List[str]) -> Optional[Path]:
    """Try each candidate path. Return first existing file."""
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
) -> StageResult:
    """Run a single stage with timeout. MISSING = FAIL if critical."""
    script = resolve_stage_script(candidates)

    if script is None:
        msg = f"Stage {stage_id} — no script found. Tried: {candidates}"
        if critical:
            logger.error("✘ CRITICAL: %s", msg)
            return StageResult.MISSING
        logger.warning("⚠ OPTIONAL: %s — skipping", msg)
        return StageResult.MISSING  # caller decides

    logger.info("▶ Running stage: %s (%s)", stage_id, script.relative_to(REPO_ROOT))
    start = time.time()
    try:
        proc = subprocess.Popen(
            [sys.executable, str(script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            preexec_fn=os.setsid if hasattr(os, "setsid") else None,
            cwd=str(REPO_ROOT),
        )
        try:
            output, _ = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            logger.error("Stage %s timed out after %ds — killing", stage_id, timeout)
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except Exception:
                proc.kill()
            proc.wait(timeout=10)
            return StageResult.FAILED

        elapsed = time.time() - start
        if proc.returncode == 0:
            logger.info("✔ Stage %s succeeded in %.1fs", stage_id, elapsed)
            return StageResult.SUCCESS
        logger.error(
            "✘ Stage %s failed (exit=%d) in %.1fs. Output tail:\n%s",
            stage_id, proc.returncode, elapsed, (output or "")[-2000:],
        )
        return StageResult.FAILED
    except Exception as exc:
        logger.exception("Unexpected error running %s: %s", stage_id, exc)
        return StageResult.FAILED


def run_stage_with_retry(
    stage_id: str,
    critical: bool,
    candidates: List[str],
) -> StageResult:
    last = StageResult.FAILED
    for attempt in range(1, MAX_STAGE_RETRIES + 1):
        result = run_stage(stage_id, critical, candidates)
        if result == StageResult.SUCCESS:
            return result
        if result == StageResult.MISSING and not critical:
            return result  # optional missing => OK
        last = result
        if attempt < MAX_STAGE_RETRIES:
            wait = BACKOFF_BASE ** attempt
            logger.warning("Stage %s attempt %d failed. Retry in %ds...",
                           stage_id, attempt, wait)
            time.sleep(wait)
    return last


# --------------------------------------------------------------------------- #
# Optional: pipeline/state.py sync
# --------------------------------------------------------------------------- #
def sync_pipeline_state(job_id: str, stage_id: str) -> None:
    """Best-effort sync with pipeline.state (silent if module missing)."""
    try:
        from pipeline.state import load_job, save_job  # type: ignore
    except Exception:
        return
    new_state = STAGE_TO_STATE.get(stage_id)
    if not new_state:
        return
    try:
        job = load_job(job_id)
        if job:
            save_job(job, state=new_state, stage=stage_id)
    except Exception as exc:
        logger.debug("pipeline.state sync skipped: %s", exc)


# --------------------------------------------------------------------------- #
# Job Execution
# --------------------------------------------------------------------------- #
def get_or_create_job(state: PipelineState, job_id: str, job_type: str) -> JobRecord:
    if job_id in state.jobs:
        return state.jobs[job_id]
    now = datetime.now(timezone.utc).isoformat()
    job = JobRecord(job_id=job_id, job_type=job_type,
                    status=JobStatus.PENDING, created_at=now, updated_at=now)
    state.jobs[job_id] = job
    return job


def resume_index(stages: List[Tuple[str, bool, List[str]]], last_success: Optional[str]) -> int:
    if not last_success:
        return 0
    ids = [s[0] for s in stages]
    if last_success not in ids:
        return 0
    return ids.index(last_success) + 1


def execute_job(job_id: str, job_type: str) -> bool:
    with JobLock(job_id):
        state = load_state()
        job = get_or_create_job(state, job_id, job_type)

        if job.status == JobStatus.SUCCESS:
            logger.info("Job %s already SUCCESS — skipping", job_id)
            return True

        if job.status == JobStatus.FAILED_FINAL:
            logger.warning("Job %s FAILED_FINAL — resetting for retry", job_id)
            job.status = JobStatus.FAILED
            job.failed_stage = None
            job.error = None

        try:
            transition(job, JobStatus.RUNNING)
        except ValueError as exc:
            logger.error("Cannot start %s: %s", job_id, exc)
            return False

        job.attempts += 1
        save_state(state)

        stages = stages_for(job_type)
        start_idx = resume_index(stages, job.last_success_stage)
        logger.info(
            "Job %s | type=%s | resuming from index %d",
            job_id, job_type, start_idx,
        )

        for stage_id, critical, candidates in stages[start_idx:]:
            result = run_stage_with_retry(stage_id, critical, candidates)

            if result == StageResult.SUCCESS:
                job.last_success_stage = stage_id
                job.failed_stage = None
                job.error = None
                save_state(state)
                sync_pipeline_state(job_id, stage_id)

            elif result == StageResult.MISSING and not critical:
                logger.warning("Stage %s optional & missing — continuing", stage_id)
                continue

            else:
                # FAILED or CRITICAL MISSING => job fails
                reason = ("script missing (critical)" if result == StageResult.MISSING
                          else "stage execution failed")
                job.failed_stage = stage_id
                job.error = f"{stage_id}: {reason}"
                if job.attempts >= MAX_STAGE_RETRIES:
                    transition(job, JobStatus.FAILED_FINAL)
                    logger.error("Job %s → FAILED_FINAL at %s (%s)",
                                 job_id, stage_id, reason)
                else:
                    transition(job, JobStatus.FAILED)
                    logger.error("Job %s → FAILED at %s (%s)",
                                 job_id, stage_id, reason)
                save_state(state)
                _write_metrics(job)
                return False

        transition(job, JobStatus.SUCCESS)
        save_state(state)
        logger.info("✔ Job %s completed successfully", job_id)
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
def run_watchdog(stuck_hours: int = 2) -> int:
    """
    Detect stuck RUNNING jobs, stale FAILED_FINAL jobs.
    Optionally auto-reset & retry. Writes recovery_plan.json.
    """
    logger.info("🐕 Watchdog running (stuck threshold = %dh)", stuck_hours)
    state = load_state()
    now = datetime.now(timezone.utc)
    stale_running: List[str] = []
    recent_failed: List[str] = []

    for job_id, job in state.jobs.items():
        if job.status == JobStatus.RUNNING:
            try:
                updated = datetime.fromisoformat(job.updated_at.replace("Z", "+00:00"))
            except Exception:
                continue
            age_h = (now - updated).total_seconds() / 3600
            if age_h > stuck_hours:
                stale_running.append(job_id)
                logger.warning("STUCK: %s (RUNNING %.1fh)", job_id, age_h)

        if job.status == JobStatus.FAILED_FINAL:
            try:
                updated = datetime.fromisoformat(job.updated_at.replace("Z", "+00:00"))
            except Exception:
                continue
            if (now - updated).total_seconds() < 7 * 86400:
                recent_failed.append(job_id)

    recovery_plan = {
        "generated_at": now.isoformat(),
        "stuck_running": stale_running,
        "recent_failed_final": recent_failed,
        "actions": [],
    }

    # Auto-reset stuck RUNNING → FAILED
    for job_id in stale_running:
        job = state.jobs[job_id]
        try:
            transition(job, JobStatus.FAILED)
            job.error = "Watchdog: reset from stuck RUNNING"
            recovery_plan["actions"].append(
                {"job_id": job_id, "action": "reset_running_to_failed"}
            )
        except ValueError as exc:
            logger.warning("Cannot reset %s: %s", job_id, exc)

    if stale_running:
        save_state(state)

    plan_file = REPO_ROOT / "recovery_plan.json"
    plan_file.write_text(json.dumps(recovery_plan, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    logger.info("Watchdog complete. Plan: %s", plan_file)
    logger.info("Stuck running: %d | Recent FAILED_FINAL: %d",
                len(stale_running), len(recent_failed))
    return 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_job_id(job_type: str, ref: Optional[str] = None) -> str:
    date = ref or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"{job_type}_{date}"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="News pipeline orchestrator")
    # NOTE: --type alias for --job-type (workflow compatibility)
    p.add_argument("--job-type", "--type", dest="job_type",
                   choices=["daily", "weekly", "monthly"], required=False)
    p.add_argument("--date", help="YYYY-MM-DD reference (default: today UTC)")
    p.add_argument("--reset", action="store_true",
                   help="Reset state for this job before running")
    p.add_argument("--watchdog", action="store_true",
                   help="Run watchdog mode (stuck job detection + recovery plan)")
    p.add_argument("--stuck-hours", type=int, default=2,
                   help="Watchdog threshold in hours (default: 2)")
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
