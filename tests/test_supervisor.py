"""Tests for MasterSupervisor (Phase 1-2 lifecycle, bounded repair, release approval) and Agent 25."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

import main
from pipeline.persistence import write_json_atomic
from pipeline.supervisor import (
    MasterSupervisor,
    STAGE_STATUS_FAILED_FINAL,
    STAGE_STATUS_PASS,
    STAGE_STATUS_REPAIR,
    release_approval_path,
    verify_release_approval,
)

ROOT = Path(__file__).resolve().parents[1]


def _load_agent(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_supervisor_detects_missing_output_despite_exit_zero(tmp_path):
    (tmp_path / "config").mkdir(parents=True)
    (tmp_path / "config" / "supervisor_policy.json").write_text(
        (ROOT / "config" / "supervisor_policy.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    sup = MasterSupervisor(tmp_path, "daily_2026-11-28", "daily", "2026-11-28")
    critique = sup.observe_and_critique(
        "04_fact_verification",
        exit_ok=True,
        msg="ok",
        duration_s=1.2,
        strict_files=True,
    )
    assert critique.status == STAGE_STATUS_REPAIR
    assert "missing or empty required output: data/verified/daily_2026-11-28.json" in critique.reasons


def test_supervisor_downstream_invalidation_and_bounded_repair_budget(tmp_path, monkeypatch):
    monkeypatch.setenv("ALP_MAX_REPAIR_CYCLES", "3")
    (tmp_path / "config").mkdir(parents=True)
    (tmp_path / "config" / "supervisor_policy.json").write_text(
        (ROOT / "config" / "supervisor_policy.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    sup = MasterSupervisor(tmp_path, "daily_2026-11-28", "daily", "2026-11-28")
    stages = ["12_content_editor", "16_mcq_generator", "18_pdf_design", "19_pdf_qa"]
    write_json_atomic(tmp_path / "data/content/daily_2026-11-28.json", {"items": [{"id": 1}]})
    sup.plan(stages, None, {})
    sup.state["completed_stages"] = list(stages)
    sup.state["pending_stages"] = []
    sup.save()

    affected = sup.invalidate_downstream(stages, "16_mcq_generator")
    assert affected == ["16_mcq_generator", "18_pdf_design", "19_pdf_qa"]
    assert sup.state["completed_stages"] == ["12_content_editor"]
    assert sup.state["final_release_decision"]["approved"] is False

    defect = "19_pdf_qa:19_pdf_qa reported passed=False"
    for i in range(1, 4):
        assert sup._can_repair(defect) is True
        sup.record_repair_attempt(defect, "18_pdf_design", ["layout defect"])
    assert sup._can_repair(defect) is False
    critique = sup.observe_and_critique(
        "19_pdf_qa",
        exit_ok=False,
        msg="19_pdf_qa reported passed=False",
        duration_s=0.5,
        strict_files=True,
    )
    assert critique.status == STAGE_STATUS_FAILED_FINAL


def test_supervisor_release_approval_token_and_tamper_rejection(tmp_path):
    (tmp_path / "config").mkdir(parents=True)
    (tmp_path / "config" / "supervisor_policy.json").write_text(
        (ROOT / "config" / "supervisor_policy.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    job = "daily_2026-11-28"
    pdf = tmp_path / "output" / f"{job}.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-1.4\nhello world\n%%EOF")
    pdf_sha = hashlib.sha256(pdf.read_bytes()).hexdigest()

    qa = tmp_path / "logs" / "qa" / f"{job}_qa.json"
    qa.parent.mkdir(parents=True)
    write_json_atomic(qa, {"job_id": job, "passed": True, "file_sha256": pdf_sha, "issues": []})
    qa_sha = hashlib.sha256(qa.read_bytes()).hexdigest()

    sup = MasterSupervisor(tmp_path, job, "daily", "2026-11-28")
    decision = sup.issue_release_decision(strict_files=True)
    assert decision["approved"] is True
    assert decision["decision"] == "APPROVED"

    ok, _ = verify_release_approval(tmp_path, job, pdf_sha, qa_sha, require_approval_file=True)
    assert ok is True

    # Tampered PDF hash must fail verification even if QA file exists.
    ok_bad, reason = verify_release_approval(tmp_path, job, "0" * 64, qa_sha, require_approval_file=True)
    assert ok_bad is False
    assert "pdf_sha256" in reason

    # Tampered approval token fails.
    ap = release_approval_path(tmp_path, job)
    rec = json.loads(ap.read_text(encoding="utf-8"))
    rec["approval_token"] = "tampered"
    write_json_atomic(ap, rec)
    ok_tok, reason_tok = verify_release_approval(tmp_path, job, pdf_sha, qa_sha, require_approval_file=True)
    assert ok_tok is False
    assert "token" in reason_tok


def test_main_execute_job_runs_supervisor_repair_rewind(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "ROOT", tmp_path)
    monkeypatch.setattr(main, "JOBS_STATE_PATH", tmp_path / "state/jobs.json")
    (tmp_path / "state/locks").mkdir(parents=True)
    (tmp_path / "config").mkdir(parents=True)
    (tmp_path / "config/supervisor_policy.json").write_text(
        (ROOT / "config/supervisor_policy.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    job = "daily_2026-11-28"
    pdf = tmp_path / f"output/{job}.pdf"
    pdf.parent.mkdir(parents=True)
    qa = tmp_path / f"logs/qa/{job}_qa.json"
    qa.parent.mkdir(parents=True)
    selected = tmp_path / f"data/selected/{job}.json"
    selected.parent.mkdir(parents=True)
    write_json_atomic(selected, {"items": [{"headline_en": "Test", "event_id": "e1"}]})
    content = tmp_path / f"data/content/{job}.json"
    content.parent.mkdir(parents=True)
    write_json_atomic(content, {"items": [{"headline_en": "Test", "event_id": "e1"}]})

    stages = [("18_pdf_design", "x", True), ("19_pdf_qa", "y", True)]
    monkeypatch.setitem(main.STAGES_BY_TYPE, "daily", stages)
    monkeypatch.setattr(main, "validate_settings", lambda jt: None)
    monkeypatch.setenv("DRY_RUN", "1")
    monkeypatch.setenv("ALP_MAX_REPAIR_CYCLES", "2")

    calls = []

    def fake_run(name, script, critical, extra_env):
        calls.append(name)
        if name == "18_pdf_design":
            pdf.write_bytes(b"%PDF-1.4\nrepaired\n%%EOF")
            return True, "ok"
        if name == "19_pdf_qa":
            digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
            passed = calls.count("19_pdf_qa") >= 2
            write_json_atomic(qa, {"job_id": job, "passed": passed, "file_sha256": digest, "issues": []})
            return passed, ("ok" if passed else "layout issue")
        return True, "ok"

    monkeypatch.setattr(main, "run_stage", fake_run)
    code = main.execute_job("daily", "2026-11-28")
    assert code == 0
    assert calls == ["18_pdf_design", "19_pdf_qa", "18_pdf_design", "19_pdf_qa"]

    sup = MasterSupervisor(tmp_path, job, "daily", "2026-11-28")
    assert len(sup.state["repair_history"]) == 1
    assert sup.state["stage_statuses"]["19_pdf_qa"]["status"] == STAGE_STATUS_PASS


def test_agent25_preserves_valid_jobs_and_quarantines_corrupt(tmp_path):
    a25 = _load_agent("agents/25_auto_healer.py", "a25_test")
    sdir = tmp_path / "state"
    (sdir / "locks").mkdir(parents=True)
    jobs_file = sdir / "jobs.json"
    jobs_file.write_text('{"daily_2026-11-27": {"status": "success"}}', encoding="utf-8")

    # Valid jobs.json must NEVER be wiped even if error mentions state_corruption.
    res_valid = a25.execute_rule_based_recovery("daily_x", "state_corruption", "jsondecodeerror", state_dir=sdir)
    assert res_valid["status"] == "recovered"
    assert json.loads(jobs_file.read_text(encoding="utf-8")) == {"daily_2026-11-27": {"status": "success"}}

    # Genuinely corrupt jobs.json is quarantined, leaving empty valid state.
    jobs_file.write_text("{corrupt", encoding="utf-8")
    res_bad = a25.execute_rule_based_recovery("daily_y", "state_corruption", "jsondecodeerror", state_dir=sdir)
    assert res_bad["status"] == "recovered"
    assert json.loads(jobs_file.read_text(encoding="utf-8")) == {}
    assert list(sdir.glob("jobs.corrupt.*.json"))
