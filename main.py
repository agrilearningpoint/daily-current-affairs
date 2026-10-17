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
from datetime import date, datetime, timezone
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
    ("18_pdf_design",                 "agents/18_pdf_design.py",                  True),
    ("19_pdf_qa",                     "agents/19_pdf_qa.py",                      True),
    ("22_telegram_publisher",         "agents/22_telegram_publisher.py",          True),
    ("23_telegram_pin_verifier",      "agents/23_telegram_pin_verifier.py",       True),
    ("24_final_health_audit",          "agents/24_final_health_audit.py",          True),
]

WEEKLY_STAGES: list[tuple[str, str, bool]] = [
    DAILY_STAGES[0],
    ("20_weekly_editor", "agents/20_weekly_editor.py", True),
] + DAILY_STAGES[8:]

MONTHLY_STAGES: list[tuple[str, str, bool]] = [
    DAILY_STAGES[0],
    ("21_monthly_editor", "agents/21_monthly_editor.py", True),
] + DAILY_STAGES[8:]

STAGES_BY_TYPE = {
    "daily": DAILY_STAGES,
    "weekly": WEEKLY_STAGES,
    "monthly": MONTHLY_STAGES,
}

# Tunables (env-overridable so workflows can adjust without code change)
STAGE_TIMEOUT_SECONDS = int(os.environ.get("ALP_STAGE_TIMEOUT", "900"))
MAX_RETRIES = int(os.environ.get("ALP_MAX_RETRIES", "2"))
RETRY_BASE_DELAY = int(os.environ.get("ALP_RETRY_BASE_DELAY", "5"))
RUNNING_STUCK_HOURS = float(os.environ.get("ALP_RUNNING_STUCK_HOURS", "6"))
FAILED_LOOKBACK_HOURS = float(os.environ.get("ALP_FAILED_LOOKBACK_HOURS", "72"))


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
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        date.fromisoformat(date_str)
    except ValueError:
        raise SystemExit(
            f"invalid job date {date_str!r}; expected YYYY-MM-DD "
            f"(e.g. --date 2026-10-14)"
        )
    from pipeline.windows import collect_window
    window_start, window_end = collect_window(job_type, date_str)
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

    attempts = MAX_RETRIES + 1
    last_err = ""
    for attempt in range(1, attempts + 1):
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
            stage_log = ROOT / "logs" / "stages" / extra_env["ALP_JOB_ID"] / f"{name}.log"
            stage_log.parent.mkdir(parents=True, exist_ok=True)
            with stage_log.open("a", encoding="utf-8") as handle:
                handle.write(f"\n--- attempt {attempt}; exit {result.returncode} ---\n{output}\n")
            if result.returncode == 0:
                return True, f"ok (attempt {attempt})"
            last_err = _truncate(output) or \
                       f"exit code {result.returncode}"
        except subprocess.TimeoutExpired:
            last_err = f"timeout after {STAGE_TIMEOUT_SECONDS}s"
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
    if entry.get("status") not in {"running", "failed", "success"}:
        return None
    if entry.get("dry_run") != (os.getenv("DRY_RUN", "0") == "1"):
        return None
    return resume_after(ROOT, job_id, entry, [name for name, _, _ in stages])


# ---------------------------------------------------------------------------
# Job execution
# ---------------------------------------------------------------------------

def execute_job(job_type: str, date_str: str | None) -> int:
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
            digest = hashlib.sha256((ROOT / f"output/{job_id}.pdf").read_bytes()).hexdigest()
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

    Exit codes: 0 = healthy, 1 = recovery actions exist, 2 = state unreadable.
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
        elif status == "failed" and age_h <= FAILED_LOOKBACK_HOURS:
            failed.append(jid)

    candidates = sorted(set(stuck) | set(failed))
    manual = []
    try:
        from pipeline.publication import records_at
        published = records_at(ROOT / "state" / "published_events.json")
        uncertain = {record.get("job_id") for record in published.values()
                     if record.get("status") in {"sending", "uncertain", "blocked_revision"}}
        max_recovery = int(os.getenv("ALP_RECOVERY_MAX_ATTEMPTS", "6"))
        if max_recovery < 1:
            raise ValueError("recovery budget must be positive")
        actions = []
        for job in candidates:
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
    }

    out = ROOT / "recovery_plan.json"
    write_json_atomic(out, plan)

    print(json.dumps(plan, indent=2, ensure_ascii=False))
    if actions:
        log(f"watchdog: {len(actions)} job(s) need recovery")
        return 1
    if stuck or failed:
        log_err("watchdog: recovery budget exhausted; manual attention required")
        return 2
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
