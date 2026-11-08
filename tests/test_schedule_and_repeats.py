"""Publish gate, edition date, reserve preservation, cross-edition repeats,
run summary and workflow schedule (2026-11-03 late/thin edition fixes)."""
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import main
from pipeline import store

ROOT = Path(__file__).resolve().parents[1]


def load_agent(number):
    path = next((ROOT / "agents").glob(f"{number}_*.py"))
    spec = importlib.util.spec_from_file_location(f"sched_test_{number}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------- #
# Publish gate
# --------------------------------------------------------------------------- #
@pytest.fixture
def fake_pipeline(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "ROOT", tmp_path)
    monkeypatch.setattr(main, "JOBS_STATE_PATH", tmp_path / "state/jobs.json")
    (tmp_path / "state" / "locks").mkdir(parents=True)
    stages = [("10_final_news_selection", "x", True), ("19_pdf_qa", "x", True),
              ("22_telegram_publisher", "x", True), ("24_final_health_audit", "x", True)]
    monkeypatch.setitem(main.STAGES_BY_TYPE, "daily", stages)
    monkeypatch.setattr(main, "validate_settings", lambda job_type: None)
    monkeypatch.setattr(main, "capture", lambda root, job, stage, previous: dict(previous))
    ran = []

    def fake_run_stage(name, script, critical, extra_env):
        ran.append(name)
        return True, "ok"

    monkeypatch.setattr(main, "run_stage", fake_run_stage)
    monkeypatch.setenv("DRY_RUN", "0")
    return ran


def test_publish_gate_parks_job_before_stage_22(fake_pipeline, monkeypatch):
    future = (datetime.now(timezone.utc) + timedelta(days=2)).astimezone(main_ist()).date().isoformat()
    monkeypatch.setenv("ALP_PUBLISH_NOT_BEFORE", "06:00")
    assert main.execute_job("daily", future) == 0          # green run
    assert fake_pipeline == ["10_final_news_selection", "19_pdf_qa"]
    entry = main.load_jobs_state()[f"daily_{future}"]
    assert entry["status"] == "awaiting_publish"
    assert entry["last_success_stage"] == "19_pdf_qa"
    assert entry["publish_not_before"].startswith(f"{future}T06:00:00+05:30")


def test_publish_gate_open_publishes_late_editions(fake_pipeline, monkeypatch):
    monkeypatch.setenv("ALP_PUBLISH_NOT_BEFORE", "06:00")
    assert main.execute_job("daily", "2026-10-05") == 0    # long past 06:00 -> send now
    assert "22_telegram_publisher" in fake_pipeline
    assert main.load_jobs_state()["daily_2026-10-05"]["status"] == "success"


def test_publish_gate_disabled_without_env(fake_pipeline, monkeypatch):
    monkeypatch.delenv("ALP_PUBLISH_NOT_BEFORE", raising=False)
    future = (datetime.now(timezone.utc) + timedelta(days=2)).date().isoformat()
    assert main.publish_not_before("daily", future) is None
    assert main.publish_not_before("weekly", future) is None


def test_awaiting_publish_is_resumable(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "JOBS_STATE_PATH", tmp_path / "state/jobs.json")
    (tmp_path / "state" / "locks").mkdir(parents=True)
    main.save_jobs_state({"daily_2026-11-04": {"status": "awaiting_publish", "dry_run": False}})
    monkeypatch.setenv("DRY_RUN", "0")
    calls = []
    monkeypatch.setattr(main, "resume_after", lambda *a: calls.append(a) or "19_pdf_qa")
    assert main.resolve_resume_stage("daily_2026-11-04", main.DAILY_STAGES) == "19_pdf_qa"


def test_watchdog_flags_only_overdue_awaiting_publish(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "ROOT", tmp_path)
    monkeypatch.setattr(main, "JOBS_STATE_PATH", tmp_path / "state/jobs.json")
    (tmp_path / "state" / "locks").mkdir(parents=True)
    now = datetime.now(timezone.utc)
    main.save_jobs_state({
        "daily_a": {"status": "awaiting_publish", "updated_at": now.isoformat(),
                    "publish_not_before": (now + timedelta(hours=3)).isoformat()},
        "daily_b": {"status": "awaiting_publish", "updated_at": now.isoformat(),
                    "publish_not_before": (now - timedelta(hours=3)).isoformat()},
    })
    main.watchdog()
    plan = json.loads((tmp_path / "recovery_plan.json").read_text())
    assert plan["stuck_running"] == ["daily_b"]


def test_review_hold_parks_before_publish_then_resumes(fake_pipeline, monkeypatch):
    monkeypatch.delenv("ALP_PUBLISH_NOT_BEFORE", raising=False)
    monkeypatch.setenv("ALP_HOLD_PUBLISH", "1")
    assert main.execute_job("daily", "2026-10-06") == 0
    assert fake_pipeline == ["10_final_news_selection", "19_pdf_qa"]
    entry = main.load_jobs_state()["daily_2026-10-06"]
    assert entry["status"] == "awaiting_publish" and entry["publish_hold"] == "review"
    main.watchdog()
    plan = json.loads((main.ROOT / "recovery_plan.json").read_text())
    assert "daily_2026-10-06" not in plan["stuck_running"]
    monkeypatch.setenv("ALP_HOLD_PUBLISH", "0")
    monkeypatch.setattr(main, "resume_after", lambda *a: "19_pdf_qa")
    fake_pipeline.clear()
    assert main.execute_job("daily", "2026-10-06") == 0
    assert fake_pipeline == ["22_telegram_publisher", "24_final_health_audit"]
    entry = main.load_jobs_state()["daily_2026-10-06"]
    assert entry["status"] == "success" and "publish_hold" not in entry


def main_ist():
    from zoneinfo import ZoneInfo
    return ZoneInfo("Asia/Kolkata")


def test_default_edition_date_is_ist(monkeypatch):
    monkeypatch.delenv("ALP_JOB_DATE", raising=False)
    ctx = main.job_context_env("daily", None)
    assert ctx["ALP_JOB_DATE"] == datetime.now(main_ist()).date().isoformat()


def test_context_window_continues_from_previous_edition(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "JOBS_STATE_PATH", tmp_path / "state/jobs.json")
    (tmp_path / "state" / "locks").mkdir(parents=True)
    main.save_jobs_state({"daily_2026-10-04": {"status": "success", "window": {
        "start": "2026-10-03T07:00:00+05:30", "end": "2026-10-04T07:30:00+05:30"}}})
    ctx = main.job_context_env("daily", "2026-10-05")
    assert ctx["ALP_WINDOW_START"] == "2026-10-04T07:30:00+05:30"
    assert ctx["ALP_WINDOW_END"] == "2026-10-05T06:00:00+05:30"


# --------------------------------------------------------------------------- #
# Stage 11 keeps reserves; cross-edition repeat filter
# --------------------------------------------------------------------------- #
def _item(eid, title, score=50, link=None):
    return {"event_id": eid, "headline_en": title, "title": title, "link": link or f"https://x/{eid}",
            "importance_score": score, "student_relevance": score, "category": "National",
            "source_name": f"src-{eid}"}


@pytest.fixture
def data_dirs(tmp_path, monkeypatch):
    import pipeline.state as pstate
    for name in ("SELECTED_DIR", "SCORED_DIR", "MEMORY_DIR"):
        directory = tmp_path / name.lower()
        directory.mkdir()
        monkeypatch.setattr(pstate, name, directory)
    monkeypatch.setenv("ALP_MEMORY_PATH", str(tmp_path / "importance_memory.json"))
    return pstate


def test_stage11_preserves_reserves_and_tags_selection(data_dirs):
    pstate = data_dirs
    sel = [_item("a1", "Cabinet approves logistics authority")]
    reserves = [_item("r1", "RBI keeps repo rate unchanged at 5.5%")]
    pstate.write_json_atomic(pstate.data_path(pstate.SELECTED_DIR, "daily_2026-11-03"),
                             {"items": sel, "reserves": reserves})
    pstate.write_json_atomic(pstate.data_path(pstate.SCORED_DIR, "daily_2026-11-03"),
                             {"items": sel + reserves})
    agent = load_agent("11").Agent("daily_2026-11-03", "daily", {"job_date": "2026-11-03"})
    agent.run()
    assert agent.verify()
    doc = pstate.read_json(pstate.data_path(pstate.SELECTED_DIR, "daily_2026-11-03"), {})
    assert [r["event_id"] for r in doc["reserves"]] == ["r1"]
    memory = store.load_memory()
    assert memory["a1"]["selected_in"] == ["daily_2026-11-03"]
    assert "selected_in" not in memory["r1"]


def test_record_scores_keeps_earlier_selection_tags(data_dirs):
    store.record_scores([_item("a1", "Story")], "daily_2026-11-02", selected_ids=["a1"])
    store.record_scores([_item("a1", "Story")], "daily_2026-11-03", selected_ids=[])
    assert store.load_memory()["a1"]["selected_in"] == ["daily_2026-11-02"]


def test_selection_drops_stories_from_previous_editions(data_dirs, monkeypatch):
    pstate = data_dirs
    monkeypatch.setenv("ALP_TARGET_NEWS_COUNT", "3")
    monkeypatch.setenv("ALP_MIN_DAILY_NEWS", "1")
    monkeypatch.setenv("ALP_MIN_OFFICIAL_STORIES", "0")
    old = _item("old1", "Shri Inbasekar Sundaramurthi appointed as the next Ambassador of India to Fiji", 90)
    store.record_scores([old], "daily_2026-11-02", selected_ids=["old1"])
    # same story re-stamped with a new event id and a publisher suffix
    repeat = _item("new1", "Shri Inbasekar Sundaramurthi appointed as the next Ambassador of India to Fiji - MEA", 95)
    fresh = [_item(f"f{i}", f"Fresh national development number {i} announced today", 60 - i) for i in range(4)]
    pstate.write_json_atomic(pstate.data_path(pstate.SCORED_DIR, "daily_2026-11-03"),
                             {"items": [repeat] + fresh})
    agent = load_agent("10").Agent("daily_2026-11-03", "daily", {})
    agent.run()
    doc = pstate.read_json(pstate.data_path(pstate.SELECTED_DIR, "daily_2026-11-03"), {})
    ids = {i["event_id"] for i in doc["items"] + doc["reserves"]}
    assert "new1" not in ids and len(doc["items"]) == 3
    assert agent.context["repeat_dropped"] == 1


def test_selection_keeps_own_edition_on_retry(data_dirs, monkeypatch):
    pstate = data_dirs
    monkeypatch.setenv("ALP_TARGET_NEWS_COUNT", "1")
    monkeypatch.setenv("ALP_MIN_DAILY_NEWS", "1")
    monkeypatch.setenv("ALP_MIN_OFFICIAL_STORIES", "0")
    story = _item("s1", "Cabinet approves Integrated Transport and Logistics Authority", 80)
    store.record_scores([story], "daily_2026-11-03", selected_ids=["s1"])
    pstate.write_json_atomic(pstate.data_path(pstate.SCORED_DIR, "daily_2026-11-03"), {"items": [story]})
    load_agent("10").Agent("daily_2026-11-03", "daily", {}).run()
    doc = pstate.read_json(pstate.data_path(pstate.SELECTED_DIR, "daily_2026-11-03"), {})
    assert [i["event_id"] for i in doc["items"]] == ["s1"]


def test_news_digest_roundups_are_not_news():
    from pipeline.news_filters import is_non_news
    assert is_non_news("Morning Digest: Cyclone 'Murasu' makes landfall in Andhra Pradesh")
    assert not is_non_news("Cyclone Murasu makes landfall in Andhra Pradesh")


# --------------------------------------------------------------------------- #
# Run summary + AI usage
# --------------------------------------------------------------------------- #
def test_run_summary_reports_counts_and_providers(tmp_path, monkeypatch, capsys):
    job = "daily_2026-11-03"
    (tmp_path / "state").mkdir()
    (tmp_path / "state/jobs.json").write_text(json.dumps({job: {"status": "awaiting_publish",
                                                               "publish_not_before": "x"}}))
    for name, doc in {"raw": {"article_count": 559, "articles": []}, "verified": {"items": [1] * 5},
                      "dedup": {"items": [1] * 4}, "scored": {"items": [1] * 3},
                      "selected": {"items": [1, 2], "reserves": [3]}, "mcq": [1, 2],
                      "content": {"items": [1, 2], "quick_bites": [1] * 40,
                                  "agri_corner": {"items": [1] * 6}, "image_stats": {"attached": 4}}}.items():
        (tmp_path / "data" / name).mkdir(parents=True)
        (tmp_path / "data" / name / f"{job}.json").write_text(json.dumps(doc))
    monkeypatch.setenv("ALP_AI_USAGE_LOG", str(tmp_path / "logs/ai_usage.jsonl"))
    monkeypatch.setenv("ALP_JOB_ID", job)
    from pipeline.ai_usage import record_ai_usage
    record_ai_usage("gemini", "gemini-3.5-flash-lite", "mcq", True)
    record_ai_usage("groq", "openai/gpt-oss-120b", "mcq", False, "rate_limit")
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    spec = importlib.util.spec_from_file_location("run_summary", ROOT / "scripts/run_summary.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.main(["--job-id", job, "--root", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "raw=559" in out and "reserves=1" in out and "quick_bites=40" in out and "agri_items=6" in out
    assert "gemini [gemini-3.5-flash-lite]: mcq×1" in out and "FAIL groq" in out
    assert "awaiting_publish" in summary.read_text()


# --------------------------------------------------------------------------- #
# Workflow
# --------------------------------------------------------------------------- #
def test_daily_workflow_schedule_and_flags():
    text = (ROOT / ".github/workflows/daily.yml").read_text()
    for cron in ("30 20 * * *", "0 21 * * *", "30 21 * * *", "30 22 * * *",
                 "30 0 * * *", "50 0 * * *", "10 1 * * *"):
        assert f'cron: "{cron}"' in text
    assert 'ALP_PUBLISH_NOT_BEFORE: "06:00"' in text
    assert "github.event.inputs.allow_fallback == 'true' && '1' || '0'" in text
    assert "allow_fallback == 'false'" not in text
    assert "scripts/run_summary.py" in text
