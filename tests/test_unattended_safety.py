"""Offline regressions for unattended checkpoints, recovery, and durable git state."""
import importlib.util
import json
from pathlib import Path
import subprocess
from datetime import datetime, timezone

import pytest
import main
from pipeline.checkpoints import capture, resume_after
from pipeline.persistence import redact, write_json_atomic
from pipeline.windows import collect_window

ROOT = Path(__file__).resolve().parents[1]
BRANCH = "arena/d5dd1833-daily-current-affairs"


def module(path):
    spec = importlib.util.spec_from_file_location(path.stem, ROOT / path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def test_mutable_outputs_rewind_to_first_producer(tmp_path):
    job = "daily_2026-10-05"
    path = tmp_path / f"data/scored/{job}.json"
    write_json_atomic(path, {"items": [1]})
    evidence = capture(tmp_path, job, "06_news_importance", {})
    write_json_atomic(path, {"items": [2]})
    evidence = capture(tmp_path, job, "07_student_domain_relevance", evidence)
    names = ["00_model_orchestrator", "05_deduplication", "06_news_importance", "07_student_domain_relevance"]
    # The preceding dedup artifact is needed too.
    write_json_atomic(tmp_path / f"data/dedup/{job}.json", [1])
    evidence = capture(tmp_path, job, "05_deduplication", evidence)
    entry = {"last_success_stage": names[-1], "artifacts": evidence}
    assert resume_after(tmp_path, job, entry, names) == names[-1]
    path.write_text("tampered")
    assert resume_after(tmp_path, job, entry, names) == "05_deduplication"
    assert evidence[path.relative_to(tmp_path).as_posix()]["stage"] == "06_news_importance"


def test_resume_rejects_escaping_paths(tmp_path):
    names = ["00_model_orchestrator"]
    assert resume_after(tmp_path, "daily_2026-10-05", {
        "last_success_stage": names[0], "artifacts": {"../outside": {"stage": names[0]}}
    }, names) is None


def test_credential_redaction_includes_url_encoding():
    value = "diagnostic-key:/123"
    from urllib.parse import quote
    assert redact(value + " " + quote(value, safe=""), {"EXAMPLE_API_KEY": value}) == "[REDACTED] [REDACTED]"


def test_recovery_parser_deduplicates_exact_dates():
    recovery = module(Path("scripts/recover_jobs.py"))
    plan = {"actions": [{"job_id": "daily_2026-10-05", "action": "retry"},
                        {"job_id": "daily_2026-10-05", "action": "retry"},
                        {"job_id": "weekly_2026-10-04", "action": "retry"},
                        {"job_id": "monthly_2026-10-01", "action": "manual"}]}
    assert recovery.recovery_jobs(plan) == ["daily_2026-10-05", "weekly_2026-10-04"]
    assert recovery.recovery_jobs(["monthly_2026-10-01"]) == ["monthly_2026-10-01"]
    with pytest.raises(ValueError):
        recovery.recovery_jobs(["daily_2026-02-30"])


def test_watchdog_exhaustion_is_fail_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "ROOT", tmp_path)
    monkeypatch.setattr(main, "JOBS_STATE_PATH", tmp_path / "state/jobs.json")
    job = {"status": "failed", "run_attempts": 6, "updated_at": datetime.now(timezone.utc).isoformat()}
    write_json_atomic(main.JOBS_STATE_PATH, {"daily_2026-10-05": job})
    assert main.watchdog() == 2
    assert json.loads((tmp_path / "recovery_plan.json").read_text())["actions"] == []
    job["run_attempts"] = 5
    write_json_atomic(main.JOBS_STATE_PATH, {"daily_2026-10-05": job})
    assert main.watchdog() == 1


def test_live_verification_needs_independent_publishers(monkeypatch):
    fact = module(Path("agents/04_fact_verification.py"))
    monkeypatch.setenv("DRY_RUN", "0")
    monkeypatch.setattr(fact, "DISABLE_LLM", True)
    article = {"title": "Cabinet Approves Agriculture Export Scheme with Rs 5000 Crore Outlay",
               "summary": "Union Cabinet approved an agriculture export scheme with Rs 5000 Crore outlay.",
               "link": "https://news.publisher.example/article"}
    sibling = dict(article, link="https://business.publisher.example/article")
    assert not fact.verify_article(article, [article, sibling])["is_verified"]
    others = [dict(article, link=f"https://{host}/article") for host in ("second.example", "third.example")]
    assert fact.verify_article(article, [article, *others])["provenance_verified"]
    contradictory = dict(others[0], title=article["title"].replace("5000", "9000"))
    assert not fact.verify_article(article, [article, contradictory, others[1]])["is_verified"]
    official = dict(article, official=True, publisher_url="https://publisher.example")
    assert fact.verify_article(official, [official])["is_verified"]


def test_period_calendar_bounds():
    start, end = collect_window("weekly", "2026-10-04")
    assert start.date().isoformat() == "2026-09-28" and end.date().isoformat() == "2026-10-04"
    start, end = collect_window("monthly", "2026-10-01")
    assert start.date().isoformat() == "2026-09-01" and end.date().isoformat() == "2026-09-30"


def test_period_editor_rejects_missing_live_proof(tmp_path, monkeypatch):
    from pipeline import period_editor
    from pipeline.agent_context import JobContext
    monkeypatch.setenv("DRY_RUN", "0")
    monkeypatch.setattr(period_editor, "load_memory", lambda: {
        "unproven": {"is_verified": True, "published": "2026-10-04T12:00:00Z"}})
    ctx = JobContext("weekly_2026-10-04", "weekly", "2026-10-04", "weekly_2026-10-04", repo_root=tmp_path)
    with pytest.raises(ValueError, match="only 0 verified"):
        period_editor.prepare(ctx)


def test_ledger_union_supports_legacy_records():
    sync = module(Path("scripts/sync_state.py"))
    merged = sync.merge_document("state/published_jobs.json", {"old": {"status": "success"}},
                                 {"version": 1, "records": {"new": {"status": "success"}}})
    assert set(merged["records"]) == {"old", "new"}
    assert sync.merge_document("recovery_plan.json", ["daily_2026-10-05"], []) == ["daily_2026-10-05"]


def test_git_state_sync_preserves_concurrent_jobs(tmp_path, monkeypatch):
    """Use isolated local git repositories; never mutate the working checkout."""
    sync = module(Path("scripts/sync_state.py"))
    origin, a, b = (tmp_path / name for name in ("origin.git", "a", "b"))

    def git(cwd, *args):
        return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)

    git(tmp_path, "init", "--bare", "--initial-branch", BRANCH, str(origin))
    git(tmp_path, "clone", str(origin), str(a))
    for repo in (a,):
        git(repo, "config", "user.email", "test@example.invalid")
        git(repo, "config", "user.name", "Safety test")
    write_json_atomic(a / "state/jobs.json", {})
    (a / "source.txt").write_text("source stays intact\n")
    git(a, "add", "."); git(a, "commit", "-m", "initial"); git(a, "push", "origin", BRANCH)
    git(tmp_path, "clone", str(origin), str(b))
    git(b, "config", "user.email", "test@example.invalid"); git(b, "config", "user.name", "Safety test")
    write_json_atomic(a / "state/jobs.json", {"daily_2026-10-05": {"status": "success", "updated_at": "2026-10-05T12:00:00Z"}})
    write_json_atomic(b / "state/jobs.json", {"weekly_2026-10-04": {"status": "success", "updated_at": "2026-10-05T13:00:00Z"}})
    git(b, "add", "."); git(b, "commit", "-m", "concurrent update"); git(b, "push", "origin", BRANCH)
    monkeypatch.chdir(a)
    sync.sync(BRANCH, "test: state")
    state = json.loads((a / "state/jobs.json").read_text())
    assert set(state) == {"daily_2026-10-05", "weekly_2026-10-04"}
    assert not git(a, "status", "--porcelain").stdout
    (a / "source.txt").write_text("unrelated edit")
    with pytest.raises(ValueError, match="non-state modifications"):
        sync.sync(BRANCH, "must refuse")
    assert (a / "source.txt").read_text() == "unrelated edit"


def test_pipeline_lock_blocks_a_second_process(tmp_path, monkeypatch):
    from pipeline.persistence import file_lock
    monkeypatch.setattr(main, "JOBS_STATE_PATH", tmp_path / "state/jobs.json")
    monkeypatch.setattr(main, "execute_job", lambda *a: pytest.fail("entered a locked pipeline"))
    with file_lock(tmp_path / "state/locks/pipeline.lock"):
        assert main.main(["--type", "daily", "--date", "2026-10-05"]) == 1
    assert not main.JOBS_STATE_PATH.exists()


def test_windows_file_lock_rejects_a_second_nonblocking_lock(tmp_path):
    import pipeline.persistence as persistence

    if persistence.msvcrt is None:
        pytest.skip("Windows locking API is unavailable")

    lock_path = tmp_path / "pipeline.lock"
    with persistence.file_lock(lock_path):
        with pytest.raises(BlockingIOError):
            with persistence.file_lock(lock_path, blocking=False):
                pytest.fail("a second handle acquired an exclusive Windows lock")


def test_watchdog_invalid_attempts_clear_stale_plan(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "ROOT", tmp_path)
    monkeypatch.setattr(main, "JOBS_STATE_PATH", tmp_path / "state/jobs.json")
    write_json_atomic(main.JOBS_STATE_PATH, {"daily_2026-10-05": {
        "status": "running", "updated_at": 123, "run_attempts": "invalid"}})
    write_json_atomic(tmp_path / "recovery_plan.json", ["daily_2026-10-05"])
    assert main.watchdog() == 2
    assert json.loads((tmp_path / "recovery_plan.json").read_text())["actions"] == []


def test_source_health_union_keeps_both_sources():
    sync = module(Path("scripts/sync_state.py"))
    merged = sync.merge_document("state/source_health.json", {"sources": {"local": {}}}, {"sources": {"remote": {}}})
    assert set(merged["sources"]) == {"local", "remote"}


def test_hashless_legacy_files_do_not_authorize_resume(tmp_path):
    job = "daily_2026-10-05"
    write_json_atomic(tmp_path / f"data/raw/{job}.json", ["legacy unproven data"])
    names = ["00_model_orchestrator", "01_source_fetch"]
    assert resume_after(tmp_path, job, {"last_success_stage": "01_source_fetch", "artifacts": {}}, names) is None


def test_period_scored_output_is_required_for_resume(tmp_path):
    job = "weekly_2026-10-04"
    write_json_atomic(tmp_path / f"data/selected/{job}.json", {"items": [1]})
    write_json_atomic(tmp_path / f"data/scored/{job}.json", {"items": [1]})
    evidence = capture(tmp_path, job, "20_weekly_editor", {})
    (tmp_path / f"data/scored/{job}.json").unlink()
    names = ["00_model_orchestrator", "20_weekly_editor"]
    assert resume_after(tmp_path, job, {"last_success_stage": names[-1], "artifacts": evidence}, names) is None


@pytest.mark.parametrize("kind", ["missing", "legacy", "stale", "future", "naive"])
def test_dispatch_rejects_stale_or_unstamped_plans(tmp_path, monkeypatch, kind):
    from datetime import timedelta
    import sys
    recovery = module(Path("scripts/recover_jobs.py"))
    now = datetime.now(timezone.utc)
    plan = {"actions": [{"job_id": "daily_2026-10-05", "action": "retry"}]}
    if kind == "legacy":
        plan = ["daily_2026-10-05"]
    elif kind != "missing":
        stamp = now - timedelta(hours=1) if kind == "stale" else now + timedelta(hours=1)
        if kind == "naive":
            stamp = now.replace(tzinfo=None)
        plan["generated_at"] = stamp.isoformat()
    path = tmp_path / "plan.json"
    write_json_atomic(path, plan)
    monkeypatch.setattr(sys, "argv", ["recover", "--plan", str(path), "--ref", BRANCH])
    monkeypatch.setattr(recovery.subprocess, "run", lambda *a, **k: pytest.fail("stale dispatch attempted"))
    with pytest.raises(ValueError):
        recovery.main()


def test_fresh_plan_dispatches_exact_date_once(tmp_path, monkeypatch):
    import sys
    recovery = module(Path("scripts/recover_jobs.py"))
    path = tmp_path / "plan.json"
    action = {"job_id": "daily_2026-10-05", "action": "retry"}
    write_json_atomic(path, {"generated_at": datetime.now(timezone.utc).isoformat(), "actions": [action, action]})
    calls = []
    monkeypatch.setattr(sys, "argv", ["recover", "--plan", str(path), "--ref", BRANCH])
    monkeypatch.setattr(recovery.subprocess, "run", lambda command, **kwargs: calls.append(command))
    assert recovery.main() == 0
    assert calls == [["gh", "workflow", "run", "daily.yml", "--ref", BRANCH, "-f", "date=2026-10-05"]]


def test_log_handler_redacts_exception_traceback(monkeypatch):
    import io
    import logging
    from pipeline.persistence import install_secret_log_filter
    value = "diagnostic-secret-for-log-filter"
    monkeypatch.setenv("EXAMPLE_API_KEY", value)
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    logger = logging.getLogger()
    logger.addHandler(handler)
    try:
        install_secret_log_filter()
        try:
            raise RuntimeError(f"diagnostic exception: {value}")
        except RuntimeError:
            logger.error("diagnostic message %s", value, exc_info=True)
        assert value not in stream.getvalue() and "[REDACTED]" in stream.getvalue()
    finally:
        logger.removeHandler(handler)
