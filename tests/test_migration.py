# -*- coding: utf-8 -*-
"""
Test maintenance/migrate_state.py — the one-time cleanup script.

Verifies:
- Invalid stage detection per job_type
- Legacy status normalization
- Stuck RUNNING reset
- FAILED_FINAL reset
- Field alias migration
"""
import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def migrator():
    path = REPO_ROOT / "maintenance" / "migrate_state.py"
    if not path.exists():
        pytest.skip("migrate_state.py not found")
    spec = importlib.util.spec_from_file_location("migrate_state", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestInferJobType:
    def test_daily(self, migrator):
        assert migrator.infer_job_type("daily_2026-10-13") == "daily"

    def test_weekly(self, migrator):
        assert migrator.infer_job_type("weekly_2026-10-11") == "weekly"

    def test_monthly(self, migrator):
        assert migrator.infer_job_type("monthly_2026-10") == "monthly"

    def test_unknown(self, migrator):
        assert migrator.infer_job_type("gibberish") is None


class TestInvalidStageCleanup:
    def test_monthly_stage_in_daily_cleared(self, migrator):
        job = {
            "job_id": "daily_test",
            "status": "FAILED",
            "last_success_stage": "21_monthly_editor",  # invalid for daily
            "updated_at": "2026-10-13T00:00:00+00:00",
            "created_at": "2026-10-13T00:00:00+00:00",
        }
        patched, actions, _ = migrator.analyze(
            "daily_test", job, reset_failed_final=False, stuck_hours=2,
        )
        assert patched["last_success_stage"] is None
        assert any(a.field == "last_success_stage" for a in actions)


class TestLegacyStatusNormalization:
    def test_collected_to_failed(self, migrator):
        job = {
            "job_id": "daily_test",
            "status": "COLLECTED",
            "updated_at": "2026-10-13T00:00:00+00:00",
            "created_at": "2026-10-13T00:00:00+00:00",
        }
        patched, _, _ = migrator.analyze(
            "daily_test", job, reset_failed_final=False, stuck_hours=2,
        )
        assert patched["status"] == "FAILED"

    def test_qa_rejected_to_failed(self, migrator):
        job = {
            "job_id": "daily_test",
            "status": "QA_REJECTED",
            "updated_at": "2026-10-13T00:00:00+00:00",
            "created_at": "2026-10-13T00:00:00+00:00",
        }
        patched, _, _ = migrator.analyze(
            "daily_test", job, reset_failed_final=False, stuck_hours=2,
        )
        assert patched["status"] == "FAILED"


class TestFailedFinalReset:
    def test_reset_to_failed(self, migrator):
        job = {
            "job_id": "daily_test",
            "status": "FAILED_FINAL",
            "failed_stage": "04_fact_verification",
            "error": "0 verified items",
            "updated_at": "2026-10-13T00:00:00+00:00",
            "created_at": "2026-10-13T00:00:00+00:00",
        }
        patched, _, _ = migrator.analyze(
            "daily_test", job, reset_failed_final=True, stuck_hours=2,
        )
        assert patched["status"] == "FAILED"
        assert patched["failed_stage"] is None
        assert patched["error"] is None

    def test_no_reset_when_flag_off(self, migrator):
        job = {
            "job_id": "daily_test",
            "status": "FAILED_FINAL",
            "updated_at": "2026-10-13T00:00:00+00:00",
            "created_at": "2026-10-13T00:00:00+00:00",
        }
        patched, _, _ = migrator.analyze(
            "daily_test", job, reset_failed_final=False, stuck_hours=2,
        )
        assert patched["status"] == "FAILED_FINAL"


class TestStuckRunning:
    def test_old_running_reset(self, migrator):
        from datetime import datetime, timezone, timedelta
        old = (datetime.now(timezone.utc) - timedelta(hours=10)).isoformat()
        job = {
            "job_id": "daily_test",
            "status": "RUNNING",
            "updated_at": old,
            "created_at": old,
        }
        patched, _, _ = migrator.analyze(
            "daily_test", job, reset_failed_final=False, stuck_hours=2,
        )
        assert patched["status"] == "FAILED"

    def test_recent_running_kept(self, migrator):
        from datetime import datetime, timezone
        recent = datetime.now(timezone.utc).isoformat()
        job = {
            "job_id": "daily_test",
            "status": "RUNNING",
            "updated_at": recent,
            "created_at": recent,
        }
        patched, _, _ = migrator.analyze(
            "daily_test", job, reset_failed_final=False, stuck_hours=2,
        )
        assert patched["status"] == "RUNNING"


class TestFieldAliases:
    def test_updated_to_updated_at(self, migrator):
        job = {
            "job_id": "daily_test",
            "status": "FAILED",
            "updated": "2026-10-13T00:00:00+00:00",
        }
        patched, _, _ = migrator.analyze(
            "daily_test", job, reset_failed_final=False, stuck_hours=2,
        )
        assert "updated_at" in patched
        assert "updated" not in patched

    def test_failed_at_to_failed_stage(self, migrator):
        job = {
            "job_id": "daily_test",
            "status": "FAILED",
            "failed_at": "03_news_collection",
            "updated_at": "2026-10-13T00:00:00+00:00",
            "created_at": "2026-10-13T00:00:00+00:00",
        }
        patched, _, _ = migrator.analyze(
            "daily_test", job, reset_failed_final=False, stuck_hours=2,
        )
        assert "failed_stage" in patched
        assert "failed_at" not in patched
