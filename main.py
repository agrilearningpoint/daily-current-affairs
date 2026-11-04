#!/usr/bin/env python3
"""AGRI LEARNING POINT — Daily Current Affairs Pipeline Orchestrator.

Runs the bilingual (Hindi + English) daily edition pipeline end-to-end:
collect -> verify -> dedup -> score -> select -> edit -> MCQ -> PDF -> QA -> publish.

Canonical usage:
    python main.py --type daily                 # today (UTC)
    python main.py --type daily --date 2026-10-04   # backfill, date authoritative
    python main.py --type weekly --date 2026-10-11
    python main.py --type monthly --date 2026-09-30
    python main.py --watchdog                   # detect stuck/failed jobs

Exit codes:
    0  success / nothing to recover
    1  a critical stage failed / recovery needed (watchdog)
    2  bad invocation or fatal configuration error
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def _load_dotenv(env_file: Path) -> None:
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip("'\"")
            if k not in os.environ:
                os.environ[k] = v

_load_dotenv(ROOT / ".env")

# ---------------------------------------------------------------------------
from pipeline.persistence import file_lock, redact, write_json_atomic
from pipeline.checkpoints import capture, resume_after

# Stage registry (local mirror of config/workflow.py — MUST be kept in sync;
# tests/test_stage_registry.py enforces this contract).
#
# Task 01 decision: exactly ONE collection path runs in production.
#   - pipeline/01_source_fetch.py is the canonical collector (registry-driven,
#     job-date aware, enriched article schema).
#   - agents/03_news_collection.py is RETIRED from the stage list to prevent a
#     second competing collector writing different files/schemas. The script
#     itself is kept on disk for compatibility until its shim/deprecation
#     commit lands.
# ---------------------------------------------------------------------------

DAILY_STAGES: list[tuple[str, str, bool]] = [
    ("00_model_orchestrator",         "agents/00_model_orchestrator.py",          True),
    ("01_source_fetch",               "pipeline/01_source_fetch.py",              True),
    ("04_fact_verification",          "agents/04_fact_verification.py",           True),
    ("05_deduplication",              "agents/05_deduplication.py",               True),
    ("06_news_importance",            "agents/06_news_importance.py",             True),
    ("07_student_domain_relevance",   "agents/07_student_domain_relevance.py",    True),
    ("10_final_news_selection",       "agents/10_final_news_selection.py",        True),
    ("11_importance_memory",          "agents/11_importance_memory.py",           True),
    ("12_content_editor",             "agents/12_content_editor.py",              True),
    ("16_mcq_generator",              "agents/16_mcq_generator.py",               True),
    ("17_mcq_validator",              "agents/17_mcq_validator.py",               True),
    # Quick Bites + Agriculture Corner: optional, fail-soft, daily-only (non-critical).
    ("17b_auto_sections",             "agents/17b_auto_sections.py",              False),
    # Strict Static GK check (officeholders vs config/current_facts.json): fail-open, non-critical.
    ("17c_static_gk_validator",       "agents/17c_static_gk_validator.py",        False),
    ("18_pdf_design",                 "agents/18_pdf_design.py",                  True),
    ("19_pdf_qa",                     "agents/19_pdf_qa.py",                      True),
    ("22_telegram_publisher",         "agents/22_telegram_publisher.py",          True),
    ("23_telegram_pin_verifier",      "agents/23_telegram_pin_verifier.py",       True),
    ("24_final_health_audit",          "agents/24_final_health_audit.py",          True),
]

# Weekly/monthly reuse the daily content→publish tail. Select those stages BY
# NAME (order preserved from DAILY_STAGES) so re-ordering or inserting a daily
# stage can never silently change which stages weekly/monthly run.
_TAIL_STAGE_NAMES = (
    "12_content_editor", "16_mcq_generator", "17_mcq_validator", "17c_static_gk_validator", "18_pdf_design",
    "19_pdf_qa", "22_telegram_publisher", "23_telegram_pin_verifier",
    "24_final_health_audit",
)
_POST_SELECTION_STAGES: list[tuple[str, str, bool]] = [
    stage for stage in DAILY_STAGES if stage[0] in _TAIL_STAGE_NAMES
]

WEEKLY_STAGES: list[tuple[str, str, bool]] = [
    DAILY_STAGES[0],
    ("20_weekly_editor", "agents/20_weekly_editor.py", True),
    *_POST_SELECTION_STAGES,
]

MONTHLY_STAGES: list[tuple[str, str, bool]] = [
    DAILY_STAGES[0],
    ("21_monthly_editor", "agents/21_monthly_editor.py", True),
    *_POST_SELECTION_STAGES,
]

STAGES_BY_TYPE = {
    "daily": DAILY_STAGES,
    "weekly": WEEKLY_STAGES,
    "monthly": MONTHLY_STAGES,
}

# Tunables (env-overridable so workflows can adjust without code change).
# Each accepts its legacy un-prefixed name as a documented backward-compatible
# alias (older .env files used STAGE_TIMEOUT_SECONDS / MAX_STAGE_RETRIES /
# WATCHDOG_STUCK_HOURS); the ALP_-prefixed name always wins.
def _fatal(msg: str) -> None:
    """Print a fatal configuration error and exit with the documented code 2."""
    print(f"FATAL: {msg}", file=sys.stderr, flush=True)
    raise SystemExit(2)


def _int_env(primary: str, legacy: str, default: int) -> int:
    for key in (primary, legacy):
        raw = os.environ.get(key)
        if raw is not None and raw.strip():
            try:
                return int(raw)
            except ValueError:
                _fatal(f"invalid {key}={raw!r}; expected an integer")
    return default


def _float_env(primary: str, legacy: str, default: float) -> float:
    for key in (primary, legacy):
        raw = os.environ.get(key)
        if raw is not None and raw.strip():
            try:
                return float(raw)
            except ValueError:
                _fatal(f"invalid {key}={raw!r}; expected a number")
    return default


STAGE_TIMEOUT_SECONDS = _int_env("ALP_STAGE_TIMEOUT", "STAGE_TIMEOUT_SECONDS", 900)
MAX_RETRIES = _int_env("ALP_MAX_RETRIES", "MAX_STAGE_RETRIES", 2)
RETRY_BASE_DELAY = _int_env("ALP_RETRY_BASE_DELAY", "RETRY_BASE_DELAY", 5)
RUNNING_STUCK_HOURS = _float_env("ALP_RUNNING_STUCK_HOURS", "WATCHDOG_STUCK_HOURS", 6)
FAILED_LOOKBACK_HOURS = _float_env("ALP_FAILED_LOOKBACK_HOURS", "FAILED_LOOKBACK_HOURS", 72)

_PUBLISH_STAGES = {"22_telegram_publisher", "23_telegram_pin_verifier"}
# The publish gate (ALP_PUBLISH_NOT_BEFORE) stops the run before this stage.
_PUBLISH_GATED_STAGES = {"22_telegram_publisher"}


def validate_settings(job_type: str) -> None:
    """Fail fast (exit code 2) on unusable numeric/behavioral settings.

    Runs before any expensive stage so misconfiguration surfaces immediately
    instead of after collection/PDF work.
    """
    if STAGE_TIMEOUT_SECONDS < 1:
        _fatal("ALP_STAGE_TIMEOUT/STAGE_TIMEOUT_SECONDS must be >= 1 second")
    if MAX_RETRIES < 0:
        _fatal("ALP_MAX_RETRIES/MAX_STAGE_RETRIES must be >= 0")
    if RUNNING_STUCK_HOURS <= 0:
        _fatal("ALP_RUNNING_STUCK_HOURS/WATCHDOG_STUCK_HOURS must be > 0")


def warn_missing_publish_credentials(job_type: str) -> list[str]:
    """Return (and log) missing Telegram credentials for a real publish run.

    Surfaced immediately at startup so misconfiguration is obvious in logs,
    while the enforcing failure stays in the publish stage (which fails the
    critical stage closed). Kept non-fatal so library/test callers that stub
    the publisher keep their execute_job() contract.
    """
    stages = {name for name, _, _ in STAGES_BY_TYPE.get(job_type, [])}
    if not (stages & _PUBLISH_STAGES) or os.getenv("DRY_RUN", "0") == "1":
        return []
    missing = [k for k in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")
               if not os.getenv(k, "").strip()]
    if missing:
        log_err(f"missing required publish settings ({', '.join(missing)}); "
                f"the publish stage will fail — set them as secrets or use DRY_RUN=1")
    return missing


def log(msg: str) -> None:
    """Timestamped orchestrator log line (stdout)."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[orchestrator {ts}] {msg}", flush=True)


def log_err(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[orchestrator {ts}] ERROR: {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Canonical job context (Task 01 §6 — date/backfill correctness)
# ---------------------------------------------------------------------------

def _previous_daily_window_end(date_str: str) -> datetime | None:
    """Recorded window end of the previous day's daily edition, if it published.

    Used so consecutive daily windows are contiguous (no overlap, no gap) even
    when yesterday's run was late, early or reset. Unreadable state -> None,
    which falls back to the fixed 06:00 IST edition window.
    """
    try:
        prev_id = f"daily_{(date.fromisoformat(date_str) - timedelta(days=1)).isoformat()}"
        entry = load_jobs_state().get(prev_id) or {}
        if entry.get("status") != "success":
            return None
        end = (entry.get("window") or {}).get("end")
        return datetime.fromisoformat(str(end)) if end else None
    except (ValueError, TypeError, OSError, AttributeError):
        return None


def publish_not_before(job_type: str, date_str: str) -> datetime | None:
    """Earliest moment the Telegram publish stage may send this edition.

    ALP_PUBLISH_NOT_BEFORE="HH:MM" (IST wall clock on the edition date) gates
    daily editions only; unset/empty disables the gate. Generation can finish
    hours earlier (02:00-04:00 IST crons) and the job then parks in
    "awaiting_publish" until a publish-window cron resumes it. After the gate
    opens there is no upper bound: a late edition still goes out immediately.
    """
    raw = (os.getenv("ALP_PUBLISH_NOT_BEFORE") or "").strip()
    if job_type != "daily" or not raw or os.getenv("DRY_RUN", "0") == "1":
        return None
    from datetime import time as dt_time
    from zoneinfo import ZoneInfo
    try:
        hh, mm = raw.split(":", 1)
        gate = dt_time(int(hh), int(mm))
        return datetime.combine(date.fromisoformat(date_str), gate, tzinfo=ZoneInfo("Asia/Kolkata"))
    except (ValueError, TypeError):
        log_err(f"ignoring invalid ALP_PUBLISH_NOT_BEFORE={raw!r}; expected HH:MM")
        return None


def job_context_env(job_type: str, date_str: str | None) -> dict[str, str]:
    """Return the canonical ALP_JOB_* environment block for one run.

    Rules:
      * An explicit --date (or pre-set ALP_JOB_DATE) is AUTHORITATIVE. It is
        never silently replaced by wall-clock "today" (backfill safety).
      * job_id format: "<type>_<YYYY-MM-DD>" — matches collector/QA contracts.
      * Returned values are strings, ready to merge into a subprocess env.
    """
    date_str = (date_str or os.environ.get("ALP_JOB_DATE") or "").strip()
    if not date_str:
        # Editions are dated in IST: a 02:00 IST run belongs to today's IST
        # edition even though it is still the previous day in UTC.
        from zoneinfo import ZoneInfo
        date_str = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")
    try:
        date.fromisoformat(date_str)
    except ValueError:
        raise SystemExit(
            f"invalid job date {date_str!r}; expected YYYY-MM-DD "
            f"(e.g. --date 2026-10-14)"
        )
    from pipeline.windows import collect_window
    previous_end = _previous_daily_window_end(date_str) if job_type == "daily" else None
    window_start, window_end = collect_window(job_type, date_str, previous_end=previous_end)
    return {
        "ALP_OUTPUT_PREFIX": f"{job_type}_{date_str}",
        "ALP_WINDOW_START": window_start.isoformat(),
        "ALP_WINDOW_END": window_end.isoformat(),
        "ALP_JOB_ID": f"{job_type}_{date_str}",
        "ALP_JOB_TYPE": job_type,
        "ALP_JOB_DATE": date_str,
    }


# ---------------------------------------------------------------------------
# Job state persistence (state/jobs.json — atomic writes)
# ---------------------------------------------------------------------------

JOBS_STATE_PATH = ROOT / "state" / "jobs.json"


def parse_jobs_state(data: object) -> dict:
    """Validate and unwrap legacy/current state without rewriting job history.

    Legacy files use {"jobs": {...}, "version": 1}; the current writer saves
    the job map directly. Both must yield the same map to the orchestrator.
    """
    if not isinstance(data, dict):
        raise ValueError("jobs.json top-level must be a JSON object")
    jobs = data.get("jobs", data)
    if not isinstance(jobs, dict):
        raise ValueError("jobs.json 'jobs' must be a JSON object")
    for job_id, entry in jobs.items():
        if not isinstance(entry, dict):
            raise ValueError(f"job {job_id!r} must be a JSON object")
        if not isinstance(entry.get("status"), str) or not entry["status"].strip():
            raise ValueError(f"job {job_id!r} must have a non-empty string status")
    return jobs


def load_jobs_state(*, strict: bool = False) -> dict:
    """Load both state formats; strict mode surfaces errors for CI validation.

    Normal operation retains the existing warn-and-start-empty behavior for
    unreadable state. CI must not mistake that fallback for a valid file.
    """
    if JOBS_STATE_PATH.exists():
        try:
            data = json.loads(JOBS_STATE_PATH.read_text(encoding="utf-8"))
            jobs = parse_jobs_state(data)
            if strict:
                return jobs
            aliases = {"RUNNING": "running", "SUCCESS": "success", "COMPLETE": "success", "FAILED": "failed", "FAILED_FINAL": "failed"}
            return {jid: dict(entry, status=aliases.get(entry["status"], entry["status"])) for jid, entry in jobs.items()}
        except (ValueError, OSError) as exc:
            if strict:
                raise
            log_err(f"jobs.json unreadable ({exc}); starting fresh state")
    return {}


def save_jobs_state(state: dict) -> None:
    """Atomic, flushed write; update_job locks read-modify-write operations."""
    write_json_atomic(JOBS_STATE_PATH, state)


def update_job(job_id: str, *, status: str | None = None,
               last_stage: str | None = None, error: str | None = None,
               started_new: bool = False, artifacts: dict | None = None,
               context: dict | None = None, record_attempt: bool = True) -> dict:
    with file_lock(JOBS_STATE_PATH.parent / "locks" / "state.lock"):
        state = load_jobs_state(strict=True)
        entry = state.setdefault(job_id, {})
        now_iso = datetime.now(timezone.utc).isoformat()
        if started_new:
            entry["started_at"] = now_iso
            entry.pop("last_success_stage", None)
            entry.pop("last_error", None)
            entry.pop("failed_stage", None)
            entry["artifacts"] = {}
        if context:
            entry["run_attempts"] = int(entry.get("run_attempts", 0)) + int(record_attempt)
            entry.update(job_id=job_id, job_type=context["ALP_JOB_TYPE"],
                         job_date=context["ALP_JOB_DATE"], dry_run=os.getenv("DRY_RUN", "0") == "1")
            entry["window"] = {"start": context["ALP_WINDOW_START"], "end": context["ALP_WINDOW_END"]}
            if os.getenv("GITHUB_RUN_ID"):
                entry["github_run_id"] = os.environ["GITHUB_RUN_ID"]
        if status is not None:
            entry["status"] = status
        if last_stage is not None:
            entry["last_success_stage"] = last_stage
            entry.pop("last_error", None)
            entry.pop("failed_stage", None)
        if error is not None:
            entry["last_error"] = error[:2000]
        if artifacts is not None:
            entry["artifacts"] = artifacts
        entry["updated_at"] = now_iso
        save_jobs_state(state)
        return entry


# ---------------------------------------------------------------------------
# Stage execution with retries
# ---------------------------------------------------------------------------

def _truncate(text: str, limit: int = 800) -> str:
    text = (text or "").strip()
    return text[-limit:] if len(text) > limit else text


def run_stage(name: str, script_rel: str, critical: bool,
              extra_env: dict[str, str]) -> tuple[bool, str]:
    """Execute one stage script as a subprocess. Returns (ok, message).

    Success contract (Task 01 §3.1 note): exit code 0 only. Stages that must
    hard-fail on empty output (like 01_source_fetch) use nonzero exits — the
    orchestrator does NOT paper over them.
    """
    script_path = ROOT / script_rel
    if not script_path.exists():
        msg = f"stage script missing: {script_rel}"
        # Missing non-critical stage => skip with warning; critical => fail.
        return (not critical, msg)

    env = os.environ.copy()
    env.update(extra_env)  # canonical ALP_JOB_* context reaches every stage
    env["ALP_STAGE_ID"] = name
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(ROOT), env.get("PYTHONPATH", "")]))
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    # The AI router derives its per-stage AI deadline from these, so AI calls stop
    # (and callers take their fallback) well before the hard stage timeout.
    env["ALP_STAGE_TIMEOUT"] = str(STAGE_TIMEOUT_SECONDS)
    stage_log = ROOT / "logs" / "stages" / extra_env.get("ALP_JOB_ID", "unknown_job") / f"{name}.log"

    attempts = MAX_RETRIES + 1
    last_err = ""
    for attempt in range(1, attempts + 1):
        env["ALP_STAGE_STARTED_AT"] = f"{time.time():.3f}"
        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(ROOT),
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=STAGE_TIMEOUT_SECONDS,
            )
            output = redact((result.stdout or "") + "\n" + (result.stderr or ""), env)
            stage_log.parent.mkdir(parents=True, exist_ok=True)
            with stage_log.open("a", encoding="utf-8") as handle:
                handle.write(f"\n--- attempt {attempt}; exit {result.returncode} ---\n{output}\n")
            if result.returncode == 0:
                return True, f"ok (attempt {attempt})"
            last_err = _truncate(output) or \
                       f"exit code {result.returncode}"
        except subprocess.TimeoutExpired as exc:
            last_err = f"timeout after {STAGE_TIMEOUT_SECONDS}s"
            # Keep what the killed attempt printed: without it a stage timeout
            # leaves no trace of where the time went (run 41513421804, stage 12).
            try:
                partial = "\n".join(
                    (part.decode("utf-8", "replace") if isinstance(part, bytes) else (part or ""))
                    for part in (exc.stdout, exc.stderr))
                stage_log.parent.mkdir(parents=True, exist_ok=True)
                with stage_log.open("a", encoding="utf-8") as handle:
                    handle.write(f"\n--- attempt {attempt}; TIMEOUT after {STAGE_TIMEOUT_SECONDS}s ---\n"
                                 f"{redact(partial, env)}\n")
            except OSError:
                pass
        except OSError as exc:
            last_err = f"launch failed: {exc}"
            break  # cannot even start the interpreter; retrying is pointless

        if attempt < attempts:
            delay = min(RETRY_BASE_DELAY * (2 ** (attempt - 1)), 60)
            log(f"stage {name} failed (attempt {attempt}/{attempts}): "
                f"{last_err[:200]} — retrying in {delay}s")
            time.sleep(delay)

    return False, f"failed after {attempts} attempt(s): {last_err}"


# ---------------------------------------------------------------------------
# Resume support
# ---------------------------------------------------------------------------

def resolve_resume_stage(job_id: str, stages: list[tuple[str, str, bool]]) -> str | None:
    """Resume interrupted/failed editions only with intact edition-local outputs.

    --reset is the explicit restart path after code/content changes. When a new
    Actions runner has no restored outputs, rewind rather than skipping stages.
    """
    entry = load_jobs_state().get(job_id, {})
    if entry.get("status") not in {"running", "failed", "success", "awaiting_publish"}:
        return None
    if entry.get("dry_run") != (os.getenv("DRY_RUN", "0") == "1"):
        return None
    return resume_after(ROOT, job_id, entry, [name for name, _, _ in stages])


# ---------------------------------------------------------------------------
# Job execution
# ---------------------------------------------------------------------------

def execute_job(job_type: str, date_str: str | None) -> int:
    validate_settings(job_type)
    ctx = job_context_env(job_type, date_str)
    job_id = ctx["ALP_JOB_ID"]
    stages = STAGES_BY_TYPE[job_type]

    previous = load_jobs_state().get(job_id, {})
    same_mode = previous.get("dry_run") == (os.getenv("DRY_RUN", "0") == "1")
    names = [name for name, _, _ in stages]
    if previous.get("status") == "success" and same_mode and resume_after(ROOT, job_id, previous, names) == names[-1]:
        if not previous.get("dry_run"):
            import hashlib
            from pipeline.publication import publication_issues
            pdf_path = ROOT / "output" / f"{job_id}.pdf"
            # A "success" job whose PDF is missing/unreadable cannot be proven
            # published — fail closed instead of crashing on read_bytes().
            if not pdf_path.is_file():
                update_job(job_id, status="failed",
                           error="completed edition PDF missing; manual reconciliation required")
                with file_lock(JOBS_STATE_PATH.parent / "locks" / "state.lock"):
                    state = load_jobs_state(strict=True)
                    state[job_id]["recovery_blocked"] = "completed edition PDF missing"
                    save_jobs_state(state)
                log_err(f"Completed edition '{job_id}' has no PDF at {pdf_path}; refusing replay")
                return 1
            try:
                digest = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
            except OSError as exc:
                update_job(job_id, status="failed", error=f"cannot read edition PDF: {exc}")
                log_err(f"Completed edition '{job_id}' PDF unreadable: {exc}")
                return 1
            issues = publication_issues(ROOT, job_id, digest, os.getenv("TELEGRAM_CHAT_ID"))
            if issues:
                update_job(job_id, status="failed", error="publication evidence missing; manual reconciliation required")
                with file_lock(JOBS_STATE_PATH.parent / "locks" / "state.lock"):
                    state = load_jobs_state(strict=True)
                    state[job_id]["recovery_blocked"] = "publication evidence missing; manual reconciliation required"
                    save_jobs_state(state)
                log_err("Completed edition has missing/mismatched publication evidence; refusing automatic replay")
                return 1
        log(f"job '{job_id}' already complete with intact checkpoints; use --reset for a fresh edition")
        return 0
    if previous.get("recovery_blocked"):
        log_err(f"job '{job_id}' requires manual reconciliation; refusing automatic replay")
        return 1
    resume_from = resolve_resume_stage(job_id, stages)
    skipping = resume_from is not None

    previous = load_jobs_state().get(job_id, {})
    if same_mode and isinstance(previous.get("window"), dict) and previous["window"].get("start") and previous["window"].get("end"):
        ctx["ALP_WINDOW_START"] = previous["window"]["start"]
        ctx["ALP_WINDOW_END"] = previous["window"]["end"]
    artifacts = dict(previous.get("artifacts", {})) if resume_from else {}
    if resume_from:
        prefix = [n for n, _, _ in stages][: [n for n, _, _ in stages].index(resume_from) + 1]
        artifacts = {path: record for path, record in artifacts.items() if record.get("stage") in prefix}
    update_job(job_id, status="running", started_new=not skipping, context=ctx, artifacts=artifacts)
    log(f"{job_type} job '{job_id}' — {len(stages)} stages"
        + (f", resuming after completed stage '{resume_from}'" if skipping else ""))

    for name, script, critical in stages:
        if skipping:
            if name == resume_from:
                skipping = False
                log(f"stage {name}: already completed, skipping")
                continue
            log(f"stage {name}: already completed earlier, skipping")
            continue

        if name in _PUBLISH_GATED_STAGES:
            gate = publish_not_before(job_type, ctx["ALP_JOB_DATE"])
            if gate is not None and datetime.now(timezone.utc) < gate:
                update_job(job_id, status="awaiting_publish")
                with file_lock(JOBS_STATE_PATH.parent / "locks" / "state.lock"):
                    state = load_jobs_state(strict=True)
                    state[job_id]["publish_not_before"] = gate.isoformat()
                    save_jobs_state(state)
                log(f"job '{job_id}' READY — awaiting publish window (not before "
                    f"{gate.isoformat()}); checkpoints kept, a later run will publish")
                return 0

        ok, msg = run_stage(name, script, critical, extra_env=ctx)
        if ok:
            try:
                artifacts = capture(ROOT, job_id, name, artifacts)
            except (ValueError, OSError) as exc:
                ok, msg = False, str(exc)
        if ok:
            log(f"stage {name}: {msg}")
            update_job(job_id, status="running", last_stage=name, artifacts=artifacts)
        else:
            log_err(f"stage {name}: {msg}")
            if critical:
                entry = update_job(job_id, status="failed", error=f"{name}: {msg}")
                with file_lock(JOBS_STATE_PATH.parent / "locks" / "state.lock"):
                    state = load_jobs_state(strict=True)
                    state[job_id]["failed_stage"] = name
                    save_jobs_state(state)
                log(f"job '{job_id}' FAILED at critical stage {name}")
                return 1
            update_job(job_id, error=f"non-critical {name}: {msg}")
            log(f"stage {name} is non-critical — continuing")

    update_job(job_id, status="success")
    log(f"job '{job_id}' SUCCESS")
    return 0


# ---------------------------------------------------------------------------
# Watchdog (structured plan; workflow reads fields, not raw dict iteration)
# ---------------------------------------------------------------------------

def watchdog(stuck_hours: float | None = None) -> int:
    """Detect stuck-running and recently-failed jobs; write recovery plan.

    Plan schema (consumed by .github/workflows/watchdog.yml):
        {"generated_at", "stuck_running": [job_id...],
         "recent_failed_final": [job_id...], "actions": [{"job_id","action"}]}

    Exit codes: 0 = healthy, 1 = recovery actions exist, 2 = state unreadable
    or a job needs manual attention.

    Not counted as needing attention (listed in the plan for visibility):
      - "already_published": the edition reached the channel (a success record
        in the publication ledger) and only a later revision was refused
        (blocked_revision). Retrying would be refused again, so there is
        nothing to recover and nothing for an operator to do.
      - "acknowledged": job ids an operator listed in ALP_WATCHDOG_ACK
        (repo variable WATCHDOG_ACK_JOBS, comma separated) or marked
        "manual_ack": true in state/jobs.json after handling them by hand.
    """
    try:
        state = load_jobs_state(strict=True)
    except (ValueError, OSError) as exc:
        log_err(f"watchdog: state unreadable: {exc}")
        return 2
    aliases = {"RUNNING": "running", "FAILED": "failed", "FAILED_FINAL": "failed"}
    state = {jid: dict(entry, status=aliases.get(entry["status"], entry["status"])) for jid, entry in state.items()}
    now = datetime.now(timezone.utc)
    stuck: list[str] = []
    failed: list[str] = []

    for jid, entry in sorted(state.items()):
        status = entry.get("status")
        ts = entry.get("updated_at", "")
        try:
            updated = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
            age_h = (now - updated).total_seconds() / 3600.0
        except (ValueError, TypeError):
            age_h = float("inf")
        if status == "running" and age_h > (RUNNING_STUCK_HOURS if stuck_hours is None else stuck_hours):
            stuck.append(jid)
        elif status == "awaiting_publish":
            # Parked by the publish gate; flag it only if no publish-window run
            # picked it up within 90 minutes of the gate opening.
            try:
                gate = datetime.fromisoformat(str(entry.get("publish_not_before", "")))
                if gate.tzinfo is None:
                    gate = gate.replace(tzinfo=timezone.utc)
                if now > gate + timedelta(minutes=90):
                    stuck.append(jid)
            except (ValueError, TypeError):
                if age_h > (RUNNING_STUCK_HOURS if stuck_hours is None else stuck_hours):
                    stuck.append(jid)
        elif status == "failed" and age_h <= FAILED_LOOKBACK_HOURS:
            failed.append(jid)

    candidates = sorted(set(stuck) | set(failed))
    manual = []
    try:
        from pipeline.publication import records_at
        published = records_at(ROOT / "state" / "published_events.json")
        by_job: dict[str, set] = {}
        for record in published.values():
            by_job.setdefault(record.get("job_id"), set()).add(record.get("status"))
        # Edition delivered; only a later revision was refused → nothing to do.
        already_published = {job for job, statuses in by_job.items()
                             if "success" in statuses and statuses <= {"success", "blocked_revision"}}
        uncertain = {job for job, statuses in by_job.items()
                     if statuses & {"sending", "uncertain", "blocked_revision"} and job not in already_published}
        acked = {j.strip() for j in os.getenv("ALP_WATCHDOG_ACK", "").split(",") if j.strip()}
        max_recovery = int(os.getenv("ALP_RECOVERY_MAX_ATTEMPTS", "6"))
        if max_recovery < 1:
            raise ValueError("recovery budget must be positive")
        actions = []
        resolved = []
        for job in candidates:
            if job in already_published and state[job].get("failed_stage", "22_telegram_publisher") == "22_telegram_publisher":
                resolved.append({"job_id": job, "reason": "already_published (later revision refused)"})
                continue
            if job in acked or state[job].get("manual_ack") is True:
                resolved.append({"job_id": job, "reason": "acknowledged by operator"})
                continue
            attempts = int(state[job].get("run_attempts", 0))
            if job in uncertain or attempts >= max_recovery or state[job].get("recovery_blocked"):
                manual.append({"job_id": job, "reason": state[job].get("recovery_blocked") or ("publication outcome uncertain" if job in uncertain else "recovery budget exhausted")})
            else:
                actions.append({"job_id": job, "action": "retry"})
    except (TypeError, ValueError, OSError):
        write_json_atomic(ROOT / "recovery_plan.json", {"generated_at": now.isoformat(), "actions": [],
                                                      "error": "invalid recovery state, ledger, budget or run-attempt counter"})
        log_err("watchdog: unreadable recovery state; manual attention required")
        return 2
    plan = {
        "generated_at": now.isoformat(),
        "stuck_running": stuck,
        "recent_failed_final": failed,
        "actions": actions,
        "manual_attention": manual,
        "resolved": resolved,
    }

    out = ROOT / "recovery_plan.json"
    write_json_atomic(out, plan)

    print(json.dumps(plan, indent=2, ensure_ascii=False))
    if actions:
        log(f"watchdog: {len(actions)} job(s) need recovery")
        return 1
    if manual:
        log_err("watchdog: recovery budget exhausted or publication uncertain; manual attention required: "
                + ", ".join(m["job_id"] for m in manual))
        return 2
    if resolved:
        log("watchdog: all clear (" + ", ".join(f"{r['job_id']}: {r['reason']}" for r in resolved) + ")")
        return 0
    log("watchdog: all clear")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="main.py",
        description="ALP daily current-affairs pipeline orchestrator",
    )
    p.add_argument("--job-type", "--type", dest="type", default="daily",
                   choices=sorted(STAGES_BY_TYPE), help="job type (default: daily)")
    p.add_argument("--date", default=None, metavar="YYYY-MM-DD",
                   help="authoritative job date for backfills; defaults to today UTC")
    p.add_argument("--watchdog", action="store_true",
                   help="scan job state for stuck/failed jobs and emit recovery plan")
    p.add_argument("--reset", action="store_true", help="restart this job from the first stage")
    p.add_argument("--stuck-hours", type=float, default=None, help="watchdog running-job age threshold")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.watchdog:
        return watchdog(args.stuck_hours)
    warn_missing_publish_credentials(args.type)
    try:
        with file_lock(JOBS_STATE_PATH.parent / "locks" / "pipeline.lock", blocking=False):
            if args.reset:
                job_id = job_context_env(args.type, args.date)["ALP_JOB_ID"]
                with file_lock(JOBS_STATE_PATH.parent / "locks" / "state.lock"):
                    state = load_jobs_state(strict=True)
                    state.pop(job_id, None)
                    save_jobs_state(state)
            return execute_job(args.type, args.date)
    except BlockingIOError:
        log_err("another pipeline process holds the run lock; no state changed")
        return 1



if __name__ == "__main__":
    raise SystemExit(main())
