"""
Pipeline Orchestrator — main.py
-------------------------------
Yeh module daily/weekly/monthly news pipeline ko orchestrate karta hai.

Production features:
- Atomic state persistence (write-temp + rename)
- File-based job locking (concurrent runs prevent)
- Resume-from-last-successful-stage
- Per-stage retry with exponential backoff
- Per-stage timeout (hung process kill)
- Strict state machine (invalid transitions reject)
- Structured logging + JSON metrics
"""

import os
import sys
import json
import time
import fcntl
import signal
import shutil
import logging
import argparse
import subprocess
import tempfile
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List

from pydantic import BaseModel, Field, ValidationError

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/orchestrator.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("orchestrator")

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------
STATE_FILE = "state/jobs.json"
LOCK_DIR = "state/locks"
SCRIPTS_DIR = "scripts"
METRICS_DIR = "state/metrics"

STAGE_TIMEOUT_SECONDS = int(os.getenv("STAGE_TIMEOUT_SECONDS", "900"))  # 15 min default
MAX_STAGE_RETRIES = int(os.getenv("MAX_STAGE_RETRIES", "3"))
BACKOFF_BASE = 2  # seconds


# ------------------------------------------------------------------
# Enums & Models
# ------------------------------------------------------------------
class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    FAILED_FINAL = "FAILED_FINAL"


class StageResult(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class JobRecord(BaseModel):
    job_id: str
    job_type: str  # "daily" | "weekly" | "monthly"
    status: JobStatus
    created_at: str
    updated_at: str
    last_success_stage: Optional[str] = None
    failed_stage: Optional[str] = None
    attempts: int = 0
    error: Optional[str] = None


class PipelineState(BaseModel):
    jobs: Dict[str, JobRecord] = Field(default_factory=dict)
    version: int = 1


# ------------------------------------------------------------------
# Stage Definitions (per job type)
# ------------------------------------------------------------------
DAILY_STAGES: List[str] = [
    "01_source_fetch",
    "03_news_collection",
    "04_fact_verification",
    "12_content_editor",
    "14_telegram_publish",
]

WEEKLY_STAGES: List[str] = [
    "20_weekly_editor",
    "14_telegram_publish",
]

MONTHLY_STAGES: List[str] = [
    "21_monthly_editor",
    "14_telegram_publish",
]

STAGE_MAP: Dict[str, List[str]] = {
    "daily": DAILY_STAGES,
    "weekly": WEEKLY_STAGES,
    "monthly": MONTHLY_STAGES,
}


def stages_for(job_type: str) -> List[str]:
    if job_type not in STAGE_MAP:
        raise ValueError(f"Unknown job type: {job_type}")
    return STAGE_MAP[job_type]


# ------------------------------------------------------------------
# File Locking (prevents concurrent runs of same job)
# ------------------------------------------------------------------
class JobLock:
    """Context manager for exclusive file lock per job."""

    def __init__(self, job_id: str, lock_dir: str = LOCK_DIR):
        self.job_id = job_id
        self.lock_dir = lock_dir
        self.lock_path = os.path.join(lock_dir, f"{job_id}.lock")
        self._fh = None

    def __enter__(self):
        os.makedirs(self.lock_dir, exist_ok=True)
        self._fh = open(self.lock_path, "w")
        try:
            fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self._fh.close()
            raise RuntimeError(f"Job {self.job_id} is already running (lock held).")
        self._fh.write(f"{os.getpid()}\n{datetime.now(timezone.utc).isoformat()}\n")
        self._fh.flush()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if self._fh:
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
                self._fh.close()
        finally:
            try:
                os.remove(self.lock_path)
            except FileNotFoundError:
                pass
        return False


# ------------------------------------------------------------------
# Atomic State I/O
# ------------------------------------------------------------------
def load_state(path: str = STATE_FILE) -> PipelineState:
    if not os.path.exists(path):
        logger.warning("State file not found; starting fresh.")
        return PipelineState()

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return PipelineState(**raw)
    except (json.JSONDecodeError, ValidationError) as exc:
        # Backup corrupt state & start fresh
        backup = f"{path}.corrupt.{int(time.time())}"
        shutil.copy2(path, backup)
        logger.error("Corrupt state file. Backed up to %s. Error: %s", backup, exc)
        return PipelineState()


def save_state(state: PipelineState, path: str = STATE_FILE) -> None:
    """Atomic write: write to temp file then rename."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    dir_ = os.path.dirname(path) or "."
    fd, tmp_path = tempfile.mkstemp(prefix=".jobs_", suffix=".tmp", dir=dir_)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state.model_dump(mode="json"), f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


# ------------------------------------------------------------------
# State Transitions (validated)
# ------------------------------------------------------------------
VALID_TRANSITIONS: Dict[JobStatus, set] = {
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


# ------------------------------------------------------------------
# Stage Execution
# ------------------------------------------------------------------
def stage_script_path(stage: str) -> str:
    return os.path.join(SCRIPTS_DIR, f"{stage}.py")


def run_stage(stage: str, timeout: int = STAGE_TIMEOUT_SECONDS) -> StageResult:
    """Run a single stage script with timeout. Returns StageResult."""
    script = stage_script_path(stage)
    if not os.path.exists(script):
        logger.error("Stage script not found: %s", script)
        return StageResult.SKIPPED

    logger.info("▶ Running stage: %s", stage)
    start = time.time()
    try:
        proc = subprocess.Popen(
            [sys.executable, script],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            preexec_fn=os.setsid if hasattr(os, "setsid") else None,
        )
        try:
            output, _ = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            logger.error("Stage %s timed out after %ds — killing.", stage, timeout)
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except Exception:
                proc.kill()
            proc.wait(timeout=10)
            return StageResult.FAILED

        elapsed = time.time() - start
        if proc.returncode == 0:
            logger.info("✔ Stage %s succeeded in %.1fs", stage, elapsed)
            return StageResult.SUCCESS
        else:
            logger.error(
                "✘ Stage %s failed (exit=%d) in %.1fs.\nOutput tail:\n%s",
                stage, proc.returncode, elapsed, (output or "")[-2000:],
            )
            return StageResult.FAILED
    except Exception as exc:
        logger.exception("Unexpected error running %s: %s", stage, exc)
        return StageResult.FAILED


def run_stage_with_retry(stage: str) -> StageResult:
    """Retry a stage with exponential backoff."""
    for attempt in range(1, MAX_STAGE_RETRIES + 1):
        result = run_stage(stage)
        if result == StageResult.SUCCESS:
            return result
        if attempt < MAX_STAGE_RETRIES:
            wait = BACKOFF_BASE ** attempt
            logger.warning("Stage %s attempt %d failed. Retrying in %ds...", stage, attempt, wait)
            time.sleep(wait)
    return StageResult.FAILED


# ------------------------------------------------------------------
# Job Execution
# ------------------------------------------------------------------
def get_or_create_job(state: PipelineState, job_id: str, job_type: str) -> JobRecord:
    if job_id in state.jobs:
        return state.jobs[job_id]
    now = datetime.now(timezone.utc).isoformat()
    job = JobRecord(
        job_id=job_id,
        job_type=job_type,
        status=JobStatus.PENDING,
        created_at=now,
        updated_at=now,
    )
    state.jobs[job_id] = job
    return job


def resume_index(stages: List[str], last_success: Optional[str]) -> int:
    """Return index from which to resume."""
    if not last_success or last_success not in stages:
        return 0
    return stages.index(last_success) + 1


def execute_job(job_id: str, job_type: str) -> bool:
    """
    Execute a job end-to-end. Returns True on success, False on failure.
    """
    with JobLock(job_id):
        state = load_state()
        job = get_or_create_job(state, job_id, job_type)

        if job.status == JobStatus.SUCCESS:
            logger.info("Job %s already SUCCESS. Skipping.", job_id)
            return True

        # If FAILED_FINAL, allow manual reset by moving to FAILED for retry
        if job.status == JobStatus.FAILED_FINAL:
            logger.warning("Job %s was FAILED_FINAL. Resetting for retry.", job_id)
            job.status = JobStatus.FAILED
            job.failed_stage = None
            job.error = None

        try:
            transition(job, JobStatus.RUNNING)
        except ValueError as exc:
            logger.error("Cannot start job %s: %s", job_id, exc)
            return False

        job.attempts += 1
        save_state(state)

        stages = stages_for(job_type)
        start_idx = resume_index(stages, job.last_success_stage)
        logger.info(
            "Job %s | type=%s | resuming from index %d (stage=%s)",
            job_id, job_type, start_idx,
            stages[start_idx] if start_idx < len(stages) else "END",
        )

        for stage in stages[start_idx:]:
            result = run_stage_with_retry(stage)
            if result == StageResult.SUCCESS:
                job.last_success_stage = stage
                job.failed_stage = None
                job.error = None
                save_state(state)
            elif result == StageResult.SKIPPED:
                logger.warning("Stage %s skipped (script missing). Continuing.", stage)
                continue
            else:
                # Failed
                job.failed_stage = stage
                job.error = f"Stage {stage} failed after {MAX_STAGE_RETRIES} attempts"
                if job.attempts >= MAX_STAGE_RETRIES:
                    transition(job, JobStatus.FAILED_FINAL)
                    logger.error("Job %s → FAILED_FINAL at %s", job_id, stage)
                else:
                    transition(job, JobStatus.FAILED)
                    logger.error("Job %s → FAILED at %s (will retry)", job_id, stage)
                save_state(state)
                _write_metrics(job)
                return False

        transition(job, JobStatus.SUCCESS)
        save_state(state)
        logger.info("✔ Job %s completed successfully.", job_id)
        _write_metrics(job)
        return True


# ------------------------------------------------------------------
# Metrics
# ------------------------------------------------------------------
def _write_metrics(job: JobRecord) -> None:
    os.makedirs(METRICS_DIR, exist_ok=True)
    path = os.path.join(METRICS_DIR, f"{job.job_id}.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(job.model_dump(mode="json"), f, ensure_ascii=False, indent=2)
    except Exception as exc:
        logger.warning("Failed to write metrics for %s: %s", job.job_id, exc)


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------
def build_job_id(job_type: str, ref: Optional[str] = None) -> str:
    date = ref or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"{job_type}_{date}"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="News pipeline orchestrator")
    p.add_argument("--job-type", choices=["daily", "weekly", "monthly"], required=True)
    p.add_argument("--date", help="YYYY-MM-DD reference date (default: today UTC)")
    p.add_argument("--reset", action="store_true",
                   help="Reset job state before running (forces full re-run)")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    job_id = build_job_id(args.job_type, args.date)

    if args.reset:
        state = load_state()
        if job_id in state.jobs:
            del state.jobs[job_id]
            save_state(state)
            logger.info("Reset state for job %s", job_id)

    try:
        ok = execute_job(job_id, args.job_type)
    except Exception as exc:
        logger.exception("Orchestrator crashed: %s", exc)
        return 1
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
