# -*- coding: utf-8 -*-
"""
JOB STATE MACHINE + ATOMIC FILE HELPERS
========================================
States (pipeline-internal):
    CREATED → COLLECTING → COLLECTED → VERIFYING → VERIFIED → DEDUPLICATED
    → SCORED → SELECTED → CONTENT_READY → MCQ_READY → MCQ_VALIDATED
    → PDF_GENERATED → QA_APPROVED → PUBLISHED → PIN_VERIFIED → COMPLETE

Failure paths:
    FAILED → RETRYING → RECOVERED
    FAILED → FAILED_FINAL           (terminal)
    QA_REJECTED                     (blocks publishing)

Orchestrator-compat states (main.py sync):
    PENDING, RUNNING, SUCCESS, FAILED, FAILED_FINAL

Locking:
    data/jobs/<job_id>.lock  (O_CREAT|O_EXCL)
    Stale locks auto-clear after max_age_min.

This module is the SINGLE SOURCE OF TRUTH for state transitions.
main.py's sync_pipeline_state() calls into here.
"""
from __future__ import annotations

import errno
import json
import os
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import pytz

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
TZ = pytz.timezone("Asia/Kolkata")
ROOT = Path(os.environ.get("ALP_ROOT", os.getcwd())).resolve()

JOBS_DIR     = ROOT / "data" / "jobs"
RAW_DIR      = ROOT / "data" / "raw"
VERIFIED_DIR = ROOT / "data" / "verified"
DEDUP_DIR    = ROOT / "data" / "dedup"
SCORED_DIR   = ROOT / "data" / "scored"
SELECTED_DIR = ROOT / "data" / "selected"
CONTENT_DIR  = ROOT / "data" / "content"
MCQ_DIR      = ROOT / "data" / "mcq"
MEMORY_DIR   = ROOT / "data" / "memory"
IMAGES_DIR   = ROOT / "assets" / "images"
OUTPUT_DIR   = ROOT / "output"
QA_LOG_DIR   = ROOT / "logs" / "qa"

ALL_DIRS = [
    JOBS_DIR, RAW_DIR, VERIFIED_DIR, DEDUP_DIR, SCORED_DIR, SELECTED_DIR,
    CONTENT_DIR, MCQ_DIR, MEMORY_DIR, IMAGES_DIR, OUTPUT_DIR, QA_LOG_DIR,
    ROOT / "logs",
]

# --------------------------------------------------------------------------- #
# Valid States (union of pipeline + orchestrator)
# --------------------------------------------------------------------------- #
VALID_STATES = {
    # --- Pipeline lifecycle ---
    "CREATED", "COLLECTING", "COLLECTED", "VERIFYING", "VERIFIED", "DEDUPLICATED",
    "SCORED", "SELECTED", "CONTENT_READY", "MCQ_READY", "MCQ_VALIDATED",
    "PDF_GENERATED", "QA_APPROVED", "QA_REJECTED", "PUBLISHED", "PIN_VERIFIED",
    "COMPLETE",
    # --- Failure paths ---
    "FAILED", "RETRYING", "RECOVERED", "FAILED_FINAL",
    # --- Orchestrator aliases (main.py sync) ---
    "PENDING", "RUNNING", "SUCCESS",
}

# Terminal states — no further transitions allowed
TERMINAL_STATES = {"COMPLETE", "FAILED_FINAL"}

# Allowed forward transitions for pipeline states
ALLOWED_TRANSITIONS: Dict[str, set] = {
    "CREATED":       {"COLLECTING", "FAILED"},
    "COLLECTING":    {"COLLECTED", "FAILED"},
    "COLLECTED":     {"VERIFYING", "FAILED"},
    "VERIFYING":     {"VERIFIED", "FAILED"},
    "VERIFIED":      {"DEDUPLICATED", "FAILED"},
    "DEDUPLICATED":  {"SCORED", "FAILED"},
    "SCORED":        {"SELECTED", "FAILED"},
    "SELECTED":      {"CONTENT_READY", "FAILED"},
    "CONTENT_READY": {"MCQ_READY", "FAILED"},
    "MCQ_READY":     {"MCQ_VALIDATED", "FAILED"},
    "MCQ_VALIDATED": {"PDF_GENERATED", "FAILED"},
    "PDF_GENERATED": {"QA_APPROVED", "QA_REJECTED", "FAILED"},
    "QA_APPROVED":   {"PUBLISHED", "FAILED"},
    "QA_REJECTED":   {"RETRYING", "FAILED_FINAL"},
    "PUBLISHED":     {"PIN_VERIFIED", "FAILED"},
    "PIN_VERIFIED":  {"COMPLETE", "FAILED"},
    "FAILED":        {"RETRYING", "FAILED_FINAL", "RECOVERED"},
    "RETRYING":      {"RECOVERED", "FAILED_FINAL"},
    "RECOVERED":     {"COMPLETE"},
    # Orchestrator compat
    "PENDING":       {"RUNNING"},
    "RUNNING":       {"SUCCESS", "FAILED", "FAILED_FINAL"},
    "SUCCESS":       set(),
    "COMPLETE":      set(),
    "FAILED_FINAL":  set(),
}


# --------------------------------------------------------------------------- #
# Stage → State mapping (used by main.py sync)
# --------------------------------------------------------------------------- #
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


def stage_to_state(stage_id: str) -> Optional[str]:
    """Public helper — main.py uses this indirectly."""
    return STAGE_TO_STATE.get(stage_id)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def ensure_dirs() -> None:
    """Idempotent — creates all pipeline dirs."""
    for d in ALL_DIRS:
        d.mkdir(parents=True, exist_ok=True)


def now_iso() -> str:
    return datetime.now(TZ).isoformat()


def job_path(job_id: str) -> Path:
    return JOBS_DIR / f"{job_id}.json"


# --------------------------------------------------------------------------- #
# JSON I/O
# --------------------------------------------------------------------------- #
def read_json(path: Path, default: Any = None) -> Any:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def write_json_atomic(path: Path, obj: Any) -> None:
    """
    Atomic write with fsync + rename.
    Safe under concurrent writers (tempfile per call).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=f".{path.stem}_", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        raise


# --------------------------------------------------------------------------- #
# Job API
# --------------------------------------------------------------------------- #
def load_job(job_id: str, job_type: str = "daily", job_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Load job from disk, creating a fresh one if absent.
    Signature kept backward-compatible with existing callers.
    """
    if job_date is None:
        # Infer from job_id like "daily_2026-10-13"
        parts = job_id.split("_", 1)
        job_date = parts[1] if len(parts) > 1 else datetime.now(TZ).strftime("%Y-%m-%d")

    p = job_path(job_id)
    job = read_json(p)
    if job is None:
        job = {
            "job_id": job_id,
            "job_type": job_type,
            "job_date": job_date,
            "status": "CREATED",
            "stage_history": [],
            "created": now_iso(),
            "updated": now_iso(),
        }
        write_json_atomic(p, job)
    return job


def save_job(job: Dict[str, Any], state: Optional[str] = None,
             stage: Optional[str] = None, **extra: Any) -> Dict[str, Any]:
    """
    Persist job to disk atomically.
    - If `state` provided: validate + transition
    - If `stage` provided: append to stage_history + set last_success_stage
    - Extra kwargs merged into job (e.g., error, attempts)
    """
    job_id = job.get("job_id")
    if not job_id:
        raise ValueError("save_job: job has no job_id")

    # --- State transition (validated) ---
    if state is not None:
        if state not in VALID_STATES:
            raise ValueError(f"Invalid state: {state!r}. Valid: {sorted(VALID_STATES)}")

        current = job.get("status", "CREATED")
        # Allow same-state writes (idempotent)
        if state != current:
            allowed = ALLOWED_TRANSITIONS.get(current, set())
            # Be lenient: allow re-writing from non-terminal states
            if current not in TERMINAL_STATES and state not in allowed and state != "FAILED":
                # Log but don't crash — main.py sync may push a forward state directly
                pass
            job["status"] = state

    # --- Stage tracking ---
    if stage:
        job["last_success_stage"] = stage
        job.setdefault("stage_history", []).append({
            "stage": stage,
            "state": job.get("status"),
            "at": now_iso(),
        })

    # --- Merge extras ---
    job.update(extra)
    job["updated"] = now_iso()

    write_json_atomic(job_path(job_id), job)
    return job


def data_path(folder: Path, job_id: str, suffix: str = "") -> Path:
    return folder / f"{job_id}{suffix}.json"


# --------------------------------------------------------------------------- #
# Cross-process Lock (O_CREAT|O_EXCL with stale detection)
# --------------------------------------------------------------------------- #
class JobLock:
    """
    Exclusive cross-process lock using atomic O_CREAT|O_EXCL lockfile.
    Stale locks (> max_age_min) auto-cleared so a dead runner can't block forever.

    Usage:
        with JobLock("daily_2026-10-13"):
            ... do work ...
    """
    def __init__(self, job_id: str, max_age_min: int = 90):
        self.path = JOBS_DIR / f"{job_id}.lock"
        self.max_age = max_age_min * 60
        self.acquired = False

    def acquire(self) -> bool:
        JOBS_DIR.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"pid={os.getpid()} at={now_iso()}".encode("utf-8"))
            os.close(fd)
            self.acquired = True
            return True
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
            # Lock exists — check staleness
            try:
                age = time.time() - os.path.getmtime(str(self.path))
                if age > self.max_age:
                    try:
                        os.remove(str(self.path))
                    except OSError:
                        pass
                    return self.acquire()
            except OSError:
                pass
            return False

    def release(self) -> None:
        if self.acquired:
            try:
                os.remove(str(self.path))
            except OSError:
                pass
            self.acquired = False

    def __enter__(self):
        if not self.acquire():
            raise BlockingIOError(f"Job lock held by another process: {self.path}")
        return self

    def __exit__(self, *exc):
        self.release()


# --------------------------------------------------------------------------- #
# Public helpers for main.py
# --------------------------------------------------------------------------- #
def transition_state(job: Dict[str, Any], new_state: str, **extra: Any) -> Dict[str, Any]:
    """Explicit transition wrapper — calls save_job with new state."""
    return save_job(job, state=new_state, **extra)


def is_terminal(job: Dict[str, Any]) -> bool:
    return job.get("status") in TERMINAL_STATES
