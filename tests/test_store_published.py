"""Regression tests for the published-ledger helpers and store locking.

- ``is_job_published`` must report a live success receipt for the job and must
  ignore dry-run / pending / message-id-less records.
- ``_file_lock`` must delegate to pipeline.persistence.file_lock so locking is
  real on Windows too (previously it silently skipped off-POSIX).
"""
from contextlib import contextmanager

import pipeline.persistence as persistence
import pipeline.store as store


def _ledger(tmp_path, monkeypatch):
    path = tmp_path / "published_events.json"
    monkeypatch.setenv("ALP_PUBLISHED_PATH", str(path))
    return path


def test_live_success_receipt_is_published(tmp_path, monkeypatch):
    _ledger(tmp_path, monkeypatch)
    store.save_published({"version": 1, "records": {
        "k1": {"key": "k1", "job_id": "daily_2026-10-05", "status": "success",
               "message_id": 42, "dry_run": False},
    }})
    assert store.is_job_published("daily_2026-10-05") is True
    assert store.is_job_published("daily_2026-10-06") is False


def test_dry_run_receipt_is_not_a_live_publish(tmp_path, monkeypatch):
    _ledger(tmp_path, monkeypatch)
    store.save_published({"version": 1, "records": {
        "k1": {"job_id": "daily_x", "status": "success", "message_id": 7, "dry_run": True},
    }})
    assert store.is_job_published("daily_x") is False


def test_pending_and_zero_message_id_are_not_published(tmp_path, monkeypatch):
    _ledger(tmp_path, monkeypatch)
    store.save_published({"version": 1, "records": {
        "k1": {"job_id": "daily_pending", "status": "sending", "message_id": 9},
        "k2": {"job_id": "daily_zero", "status": "success", "message_id": 0},
        "k3": {"job_id": "daily_bool", "status": "success", "message_id": True},
    }})
    assert store.is_job_published("daily_pending") is False
    assert store.is_job_published("daily_zero") is False
    assert store.is_job_published("daily_bool") is False, "bool is not a valid message id"


def test_missing_ledger_is_not_published(tmp_path, monkeypatch):
    _ledger(tmp_path, monkeypatch)
    assert store.is_job_published("daily_anything") is False


def test_file_lock_delegates_to_persistence(tmp_path, monkeypatch):
    seen = []

    @contextmanager
    def fake_file_lock(path, **kwargs):
        seen.append(path)
        yield

    monkeypatch.setattr(persistence, "file_lock", fake_file_lock)
    target = tmp_path / "importance_memory.json"
    with store._file_lock(target):
        pass
    assert seen, "store._file_lock did not delegate to persistence.file_lock"
    assert seen[0].name == "importance_memory.json.lock"
    assert seen[0].parent == target.parent
