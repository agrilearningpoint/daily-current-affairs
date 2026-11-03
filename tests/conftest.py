"""Shared test isolation for the AI provider health registry.

The router keeps provider cooldowns in a process-wide registry (and, in a real
run, a per-job health file). Tests must never see another test's cooldowns or
write into the repository's logs/.
"""
import pytest


@pytest.fixture(autouse=True)
def _isolated_ai_provider_health(tmp_path, monkeypatch):
    monkeypatch.setenv("ALP_AI_HEALTH_FILE", str(tmp_path / "ai_health.json"))
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
