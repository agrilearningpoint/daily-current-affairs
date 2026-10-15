"""Legacy publication-ledger compatibility.

The committed ``state/published_events.json`` still uses the pre-versioned flat
schema ``{key: {"jobs": [...], "last_published": date}}``. Refusing to read it
aborted the whole publisher ("Publication ledger unreadable"), so a daily run
could never reach stage 22/23/24. These tests pin the adoption rules: history is
preserved, never invented, and an edition with unreconcilable history is never
silently resent.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

import main
from pipeline.checkpoints import STAGE_FILES, capture
from pipeline.persistence import write_json_atomic
from pipeline.publication import migrate_legacy_flat_ledger, records_at

ROOT = Path(__file__).resolve().parents[1]
JOB = "daily_2026-10-05"
CHAT = "-100000777"

LEGACY = {
    "0907dd4d50b4e04b": {"jobs": ["daily_2026-10-11"], "last_published": "2026-10-11"},
    "7530c1aae9ee4f0f": {"jobs": ["daily_2026-10-10", "daily_2026-10-11"], "last_published": "2026-10-11"},
}


def load_agent(number):
    path = next((ROOT / "agents").glob(f"{number}_*.py"))
    spec = importlib.util.spec_from_file_location(f"ledger_legacy_test_{number}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migrate_legacy_flat_ledger_preserves_every_entry():
    migrated = migrate_legacy_flat_ledger(LEGACY)
    assert migrated["version"] == 1
    assert set(migrated["records"]) == set(LEGACY), "legacy keys must be preserved"
    first = migrated["records"]["0907dd4d50b4e04b"]
    assert first["jobs"] == ["daily_2026-10-11"]
    assert first["job_id"] == "daily_2026-10-11"
    assert first["last_published"] == "2026-10-11"
    assert first["status"] == "legacy_unknown", "legacy rows are never live receipts"
    second = migrated["records"]["7530c1aae9ee4f0f"]
    assert second["jobs"] == ["daily_2026-10-10", "daily_2026-10-11"]
    assert second["job_id"] == "daily_2026-10-11"


@pytest.mark.parametrize("value", [
    {"records": {}}, {"version": 1, "records": {}}, {}, "text",
    {"key": {"jobs": "not-a-list"}}, {"key": "not-a-dict"},
])
def test_migration_only_claims_the_legacy_shape(value):
    assert migrate_legacy_flat_ledger(value) is None


def test_records_at_reads_legacy_file(tmp_path):
    path = tmp_path / "published_events.json"
    path.write_text(json.dumps(LEGACY), encoding="utf-8")
    records = records_at(path)
    assert set(records) == set(LEGACY)
    assert all(record["status"] == "legacy_unknown" for record in records.values())


@pytest.mark.parametrize("text", ["{broken", "[null]", '{"records": []}', '{"records": {"bad": null}}', '[]'])
def test_corrupt_publication_ledger_still_fails_closed(tmp_path, text):
    path = tmp_path / "published_events.json"
    path.write_text(text, encoding="utf-8")
    with pytest.raises((ValueError, json.JSONDecodeError)):
        records_at(path)


@pytest.fixture
def publisher(tmp_path, monkeypatch):
    module = load_agent("22")
    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(module, "LEDGER_FILE", tmp_path / "state/published_events.json")
    monkeypatch.setattr(module, "DRY_RUN", False)
    monkeypatch.setattr(module, "TELEGRAM_CHAT_ID", CHAT)
    (tmp_path / "state").mkdir(parents=True, exist_ok=True)
    (tmp_path / "state/published_events.json").write_text(json.dumps(LEGACY), encoding="utf-8")
    return module


def test_load_ledger_adopts_legacy_history(publisher):
    ledger = publisher.load_ledger()
    assert ledger["version"] == 1
    assert len(ledger["records"]) == len(LEGACY)
    assert {r["status"] for r in ledger["records"].values()} == {"legacy_unknown"}


def _seed_pre_qa_checkpoints(root, job_id):
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
    write_json_atomic(root / "data/content" / f"{job_id}.json", {"job": {"id": job_id}, "items": [
        {"needs_review": False, "verification_passed": True}]})
    return pdf, artifacts


JOB_11 = "daily_2026-10-11"


@pytest.mark.parametrize("dry_run, expected", [(False, False), (True, True)])
def test_edition_inside_legacy_history_is_never_silently_resent(
        publisher, monkeypatch, tmp_path, dry_run, expected, caplog):
    """Live sends for an edition with unreconcilable history stay blocked; dry runs are inert."""
    monkeypatch.setattr(publisher, "DRY_RUN", dry_run)
    monkeypatch.setenv("ALP_ROOT", str(tmp_path))
    monkeypatch.setenv("ALP_JOB_ID", JOB_11)
    monkeypatch.setenv("ALP_JOB_TYPE", "daily")
    monkeypatch.setenv("ALP_JOB_DATE", "2026-10-11")
    monkeypatch.setenv("ALP_OUTPUT_PREFIX", JOB_11)
    monkeypatch.setattr(main, "ROOT", tmp_path)
    monkeypatch.setattr(main, "JOBS_STATE_PATH", tmp_path / "state/jobs.json")
    pdf, artifacts = _seed_pre_qa_checkpoints(tmp_path, JOB_11)
    write_json_atomic(tmp_path / "state/jobs.json", {JOB_11: {
        "status": "running", "dry_run": dry_run, "last_success_stage": "19_pdf_qa",
        "artifacts": artifacts}})
    caplog.clear()
    published = publisher.publish_pdf(pdf, publisher.load_ledger())
    assert published is expected
    guard = "cannot be reconciled automatically" if not dry_run else "unreconciled legacy history"
    assert guard in caplog.text, "the legacy-history guard must be the deciding gate"
    if not dry_run:
        records = json.loads((tmp_path / "state/published_events.json").read_text())
        assert not any(record.get("status") == "sending" for record in records.values())


def test_other_editions_still_publish_normally(publisher, monkeypatch, tmp_path):
    """A legacy ledger must not block an edition that is not part of it."""
    monkeypatch.setattr(publisher, "DRY_RUN", True)
    monkeypatch.setenv("ALP_ROOT", str(tmp_path))
    monkeypatch.setenv("ALP_JOB_ID", JOB)
    monkeypatch.setenv("ALP_JOB_TYPE", "daily")
    monkeypatch.setenv("ALP_JOB_DATE", "2026-10-05")
    monkeypatch.setenv("ALP_OUTPUT_PREFIX", JOB)
    monkeypatch.setattr(main, "ROOT", tmp_path)
    monkeypatch.setattr(main, "JOBS_STATE_PATH", tmp_path / "state/jobs.json")
    pdf, artifacts = _seed_pre_qa_checkpoints(tmp_path, JOB)
    write_json_atomic(tmp_path / "state/jobs.json", {JOB: {
        "status": "running", "dry_run": True, "last_success_stage": "19_pdf_qa",
        "artifacts": artifacts}})
    assert publisher.publish_pdf(pdf, publisher.load_ledger()) is True
