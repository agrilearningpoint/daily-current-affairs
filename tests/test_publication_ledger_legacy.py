"""Legacy publication-ledger compatibility (merged design).

``state/published_events.json`` came from the pre-versioned ledger format
``{key: {"jobs": [...], "last_published": date}}``. Two shapes exist in the wild
and both must stay safe:

1. a file that is still entirely flat  -> adopted as ``legacy_history``;
2. a file already migrated to ``{"version": 1, "records": {...}}`` but still
   carrying those flat rows *inside* ``records`` (the shape committed on main).

Flat rows carry no chat_id/file_hash/status, so they can neither prove nor
authorise a send - but the editions they list must never be resent silently.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

import main
from pipeline.checkpoints import STAGE_FILES, capture
from pipeline.persistence import write_json_atomic
from pipeline.publication import records_at

ROOT = Path(__file__).resolve().parents[1]
JOB = "daily_2026-10-05"
PUBLISHED_JOB = "daily_2026-10-11"
CHAT = "-100000777"

LEGACY_FLAT = {
    "0907dd4d50b4e04b": {"jobs": ["daily_2026-10-11"], "last_published": "2026-10-11"},
    "7530c1aae9ee4f0f": {"jobs": ["daily_2026-10-10", "daily_2026-10-11"], "last_published": "2026-10-11"},
}
MIGRATED_WITH_LEGACY_ROWS = {
    "version": 1,
    "records": {
        **LEGACY_FLAT,
        "9f2c1b7a5e4d3c2b": {"job_id": "daily_2026-10-14", "chat_id": CHAT, "file_hash": "abc",
                             "file_sha256": "f" * 64, "status": "success", "message_id": 39,
                             "published_at": "2026-10-16T07:37:43+00:00"},
    },
}


def load_agent(number):
    path = next((ROOT / "agents").glob(f"{number}_*.py"))
    spec = importlib.util.spec_from_file_location(f"ledger_legacy_test_{number}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def publisher(tmp_path, monkeypatch):
    module = load_agent("22")
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(module, "LEDGER_FILE", tmp_path / "state/published_events.json")
    monkeypatch.setattr(module, "DRY_RUN", False)
    monkeypatch.setattr(module, "TELEGRAM_CHAT_ID", CHAT)
    (tmp_path / "state").mkdir(parents=True, exist_ok=True)
    return module


def _write_ledger(publisher, value):
    publisher.LEDGER_FILE.write_text(json.dumps(value), encoding="utf-8")


def test_flat_ledger_is_adopted_as_history(publisher):
    _write_ledger(publisher, LEGACY_FLAT)
    ledger = publisher.load_ledger()
    assert ledger["records"] == {}
    assert ledger["legacy_history"] == LEGACY_FLAT


def test_flat_rows_inside_records_are_folded_into_history(publisher):
    """The shape committed on main must not bypass the duplicate-send guard."""
    _write_ledger(publisher, MIGRATED_WITH_LEGACY_ROWS)
    ledger = publisher.load_ledger()
    assert set(ledger["records"]) == {"9f2c1b7a5e4d3c2b"}, "only verifiable receipts stay in records"
    assert set(ledger["legacy_history"]) == set(LEGACY_FLAT)
    assert ledger["records"]["9f2c1b7a5e4d3c2b"]["status"] == "success"


@pytest.mark.parametrize("value", [LEGACY_FLAT, MIGRATED_WITH_LEGACY_ROWS])
def test_edition_listed_in_legacy_history_is_never_resent(publisher, value):
    _write_ledger(publisher, value)
    ledger = publisher.load_ledger()
    pdf = publisher.REPO_ROOT / f"output/{PUBLISHED_JOB}.pdf"
    pdf.parent.mkdir(parents=True, exist_ok=True)
    pdf.write_bytes(b"%PDF-1.4\nlegacy guard fixture\n%%EOF")
    assert publisher.publish_pdf(pdf, ledger) is False
    after = json.loads(publisher.LEDGER_FILE.read_text())
    assert not any(isinstance(r, dict) and r.get("status") == "sending"
                   for r in after.get("records", {}).values())


def test_records_at_skips_unverifiable_rows_but_still_fails_closed(tmp_path):
    """The migrated shape keeps verifiable receipts only; corruption still raises."""
    path = tmp_path / "published_events.json"
    path.write_text(json.dumps(MIGRATED_WITH_LEGACY_ROWS), encoding="utf-8")
    records = records_at(path)
    assert set(records) == {"9f2c1b7a5e4d3c2b"}, "flat rows must not be treated as receipts"
    assert all(record.get("status") is not None for record in records.values())

    for text in ("{broken", "[null]", '{"records": []}', '{"records": {"bad": null}}', "[]",
                 json.dumps(LEGACY_FLAT)):
        path.write_text(text, encoding="utf-8")
        with pytest.raises((ValueError, json.JSONDecodeError)):
            records_at(path)


def _seed_checkpoints(root, job_id):
    pdf = root / f"output/{job_id}.pdf"
    pdf.parent.mkdir(parents=True, exist_ok=True)
    pdf.write_bytes(b"%PDF-1.4\nSeeded legacy-ledger fixture\n%%EOF")
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    artifacts = {}
    for stage, _, _ in main.DAILY_STAGES:
        template = STAGE_FILES.get(stage)
        if template:
            path = root / template.format(job=job_id)
            if stage == "19_pdf_qa":
                write_json_atomic(path, {"passed": True, "job_id": job_id, "file_sha256": digest})
            elif stage != "18_pdf_design":
                write_json_atomic(path, {"items": [{"needs_review": False, "verification_passed": True}]})
            artifacts = capture(root, job_id, stage, artifacts)
        if stage == "19_pdf_qa":
            break
    return pdf, artifacts


def test_edition_outside_legacy_history_still_publishes(publisher, monkeypatch, tmp_path):
    """A ledger migrated from the flat format must not freeze publishing."""
    _write_ledger(publisher, MIGRATED_WITH_LEGACY_ROWS)
    monkeypatch.setattr(publisher, "DRY_RUN", True)
    monkeypatch.setenv("ALP_ROOT", str(tmp_path))
    monkeypatch.setenv("ALP_JOB_ID", JOB)
    monkeypatch.setenv("ALP_JOB_TYPE", "daily")
    monkeypatch.setenv("ALP_JOB_DATE", "2026-10-05")
    monkeypatch.setenv("ALP_OUTPUT_PREFIX", JOB)
    monkeypatch.setattr(main, "ROOT", tmp_path)
    monkeypatch.setattr(main, "JOBS_STATE_PATH", tmp_path / "state/jobs.json")
    pdf, artifacts = _seed_checkpoints(tmp_path, JOB)
    write_json_atomic(tmp_path / "state/jobs.json", {JOB: {
        "status": "running", "dry_run": True, "last_success_stage": "19_pdf_qa", "artifacts": artifacts}})
    assert publisher.publish_pdf(pdf, publisher.load_ledger()) is True
