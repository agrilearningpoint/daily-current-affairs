# -*- coding: utf-8 -*-
"""
JOB STATE MACHINE + ATOMIC FILE HELPERS
States: CREATED → COLLECTING → COLLECTED → VERIFYING → VERIFIED → DEDUPLICATED
        → SCORED → SELECTED → CONTENT_READY → MCQ_READY → MCQ_VALIDATED
        → PDF_GENERATED → QA_APPROVED → PUBLISHED → PIN_VERIFIED → COMPLETE
Failure: FAILED → RETRYING → RECOVERED / FAILED_FINAL ; QA fail = QA_REJECTED
Locking: data/jobs/<job_id>.lock (O_CREAT|O_EXCL) — prevents duplicate runs.
"""
import json, os, time, errno
from datetime import datetime
import pytz

TZ = pytz.timezone("Asia/Kolkata")
ROOT = os.environ.get("ALP_ROOT", os.getcwd())

JOBS_DIR = os.path.join(ROOT, "data", "jobs")
RAW_DIR = os.path.join(ROOT, "data", "raw")
VERIFIED_DIR = os.path.join(ROOT, "data", "verified")
DEDUP_DIR = os.path.join(ROOT, "data", "dedup")
SCORED_DIR = os.path.join(ROOT, "data", "scored")
SELECTED_DIR = os.path.join(ROOT, "data", "selected")
CONTENT_DIR = os.path.join(ROOT, "data", "content")
MCQ_DIR = os.path.join(ROOT, "data", "mcq")
MEMORY_DIR = os.path.join(ROOT, "data", "memory")
IMAGES_DIR = os.path.join(ROOT, "assets", "images")
OUTPUT_DIR = os.path.join(ROOT, "output")
QA_LOG_DIR = os.path.join(ROOT, "logs", "qa")

ALL_DIRS = [JOBS_DIR, RAW_DIR, VERIFIED_DIR, DEDUP_DIR, SCORED_DIR, SELECTED_DIR,
            CONTENT_DIR, MCQ_DIR, MEMORY_DIR, IMAGES_DIR, OUTPUT_DIR,
            QA_LOG_DIR, os.path.join(ROOT, "logs")]

VALID_STATES = [
    "CREATED", "COLLECTING", "COLLECTED", "VERIFYING", "VERIFIED", "DEDUPLICATED",
    "SCORED", "SELECTED", "CONTENT_READY", "MCQ_READY", "MCQ_VALIDATED",
    "PDF_GENERATED", "QA_APPROVED", "QA_REJECTED", "PUBLISHED", "PIN_VERIFIED",
    "COMPLETE", "FAILED", "RETRYING", "RECOVERED", "FAILED_FINAL",
]


def ensure_dirs():
    for d in ALL_DIRS:
        os.makedirs(d, exist_ok=True)


def now_iso():
    return datetime.now(TZ).isoformat()


def job_path(job_id):
    return os.path.join(JOBS_DIR, f"{job_id}.json")


def read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json_atomic(path, obj):
    """Atomic write: temp file + os.replace (never leaves half-written JSON)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def load_job(job_id, job_type, job_date):
    p = job_path(job_id)
    job = read_json(p)
    if job is None:
        job = {"job_id": job_id, "job_type": job_type, "job_date": job_date,
               "status": "CREATED", "stage_history": [], "created": now_iso()}
        write_json_atomic(p, job)
    return job


def save_job(job, state=None, stage=None, **extra):
    """Transition job to a new state (validated) and persist atomically."""
    if state:
        if state not in VALID_STATES:
            raise ValueError(f"Invalid state {state}")
        job["status"] = state
    if stage:
        job["last_success_stage"] = stage
        job.setdefault("stage_history", []).append({"stage": stage, "at": now_iso()})
    job["updated"] = now_iso()
    job.update(extra)
    write_json_atomic(job_path(job["job_id"]), job)
    return job


class JobLock:
    """Exclusive cross-process lock using atomic O_CREAT|O_EXCL lockfile.
    Stale locks (> max_age_min) are auto-cleared so a dead runner can't block forever."""

    def __init__(self, job_id, max_age_min=90):
        self.path = os.path.join(JOBS_DIR, f"{job_id}.lock")
        self.max_age = max_age_min * 60
        self.acquired = False

    def acquire(self):
        os.makedirs(JOBS_DIR, exist_ok=True)
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"pid={os.getpid()} at={now_iso()}".encode())
            os.close(fd)
            self.acquired = True
            return True
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
            # Lock exists — check staleness
            try:
                age = time.time() - os.path.getmtime(self.path)
                if age > self.max_age:
                    os.remove(self.path)
                    return self.acquire()
            except OSError:
                pass
            return False

    def release(self):
        if self.acquired:
            try:
                os.remove(self.path)
            except OSError:
                pass
            self.acquired = False

    def __enter__(self):
        if not self.acquire():
            raise BlockingIOError(f"Job lock held by another process: {self.path}")
        return self

    def __exit__(self, *a):
        self.release()


def data_path(folder, job_id, suffix=""):
    return os.path.join(folder, f"{job_id}{suffix}.json")
