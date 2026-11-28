"""Shared test isolation for the AI provider health and observability logs.

Tests must never leak cooldowns or telemetry writes into repository logs/.
"""
import pytest


@pytest.fixture(autouse=True)
def _isolated_ai_provider_health(tmp_path, monkeypatch):
    monkeypatch.setenv("ALP_AI_HEALTH_FILE", str(tmp_path / "ai_health.json"))
    monkeypatch.setenv("ALP_AI_USAGE_LOG", str(tmp_path / "ai_usage.jsonl"))
    monkeypatch.setenv("ALP_PROVIDER_HEALTH_PATH", str(tmp_path / "provider_health.json"))
    monkeypatch.setenv("ALP_PROVIDER_SUMMARY_PATH", str(tmp_path / "provider_summary.json"))
    monkeypatch.delenv("ALP_AI_STAGE_BUDGET", raising=False)
    monkeypatch.delenv("ALP_STAGE_STARTED_AT", raising=False)
    monkeypatch.delenv("ALP_STAGE_TIMEOUT", raising=False)
    try:
        from pipeline import ai_router
    except Exception:  # pragma: no cover
        yield
        return
    ai_router._reset_health()
    yield
    ai_router._reset_health()
