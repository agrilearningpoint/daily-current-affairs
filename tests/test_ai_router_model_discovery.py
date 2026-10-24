"""Regression tests for live AI model discovery and retired-model recovery."""
from __future__ import annotations

from pipeline import ai_router


def test_choose_live_model_prefers_current_catalogue_entry():
    provider = ai_router.Provider(
        name="groq", url="https://api.groq.com/openai/v1/chat/completions",
        key="test", model="llama-3.3-70b-versatile",
    )
    selected = ai_router._choose_live_model(
        provider, ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]
    )
    assert selected == "openai/gpt-oss-120b"


def test_refresh_model_uses_catalogue_and_excludes_retired(monkeypatch):
    provider = ai_router.Provider(
        name="gemini", url="https://generativelanguage.googleapis.com/v1beta/models",
        key="test", model="gemini-1.5-flash",
    )
    monkeypatch.setattr(ai_router, "_live_model_ids", lambda _p: ["gemini-2.0-flash"])
    assert ai_router._refresh_provider_model(provider, exclude={"gemini-1.5-flash"})
    assert provider.model == "gemini-2.0-flash"


def test_retired_status_codes_are_model_errors():
    assert ai_router._classify_error(404, "") == ai_router.FailureType.MODEL_ERROR
    assert ai_router._classify_error(410, "") == ai_router.FailureType.MODEL_ERROR
