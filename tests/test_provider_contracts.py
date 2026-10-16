"""Offline provider transport/registration contracts; no real API credentials."""
import importlib.util
from pathlib import Path

import pytest
import requests

from pipeline import ai_router, ai_translator

ROOT = Path(__file__).resolve().parents[1]


def orchestrator():
    spec = importlib.util.spec_from_file_location("provider_contract_setup", ROOT / "agents/00_model_orchestrator.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_setup_and_translation_use_the_same_provider_registry(monkeypatch):
    names = ["GEMINI_API_KEY", "GOOGLE_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY", "MISTRAL_API_KEY",
             "LLM_API_KEY", "OPENROUTER_API_KEY"]
    for name in names:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LLM_API_URL", "https://provider.example/chat/completions")
    monkeypatch.setenv("LLM_API_KEY", "diagnostic-generic-not-a-credential")
    monkeypatch.setenv("OPENROUTER_API_KEY", "diagnostic-openrouter-not-a-credential")
    expected = ai_router._build_default_providers()
    actual = orchestrator().load_keys()
    assert [item["name"] for item in actual] == [item.name for item in expected] == ["generic-openai", "openrouter"]
    assert [item["model"] for item in actual] == [item.model for item in expected]
    assert actual[0]["env_used"] == "LLM_API_KEY"


def test_groq_default_uses_a_current_model(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "diagnostic-groq-not-a-credential")
    monkeypatch.delenv("GROQ_MODEL", raising=False)

    groq = next(provider for provider in ai_router._build_default_providers()
                if provider.name == "groq")

    assert groq.model == "openai/gpt-oss-120b"


@pytest.mark.parametrize("provider_name", ["gemini", "generic-openai"])
def test_translator_uses_provider_native_request_and_response(monkeypatch, provider_name):
    provider = {"name": provider_name, "key": "diagnostic-key-not-a-credential", "model": "diagnostic-model",
                "url": "https://provider.example/models"}
    hindi = "भारत ने कृषि योजना को मंजूरी दी।"

    class Response:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            if provider_name == "gemini":
                return {"candidates": [{"content": {"parts": [{"text": hindi}]}}]}
            return {"choices": [{"message": {"content": hindi}}]}

    def post(url, *, headers, json, timeout):
        if provider_name == "gemini":
            assert url.endswith("/diagnostic-model:generateContent")
            assert "key=" not in url
            assert headers["x-goog-api-key"] == provider["key"]
            assert "contents" in json and "messages" not in json
        else:
            assert url == provider["url"]
            assert headers["Authorization"] == f"Bearer {provider['key']}"
            assert "messages" in json
        return Response()

    monkeypatch.setattr(requests, "post", post)
    assert ai_translator._call_provider(provider, "Translate accurately", "India approved an agriculture scheme.") == hindi


def test_translator_redacts_provider_errors(monkeypatch, caplog):
    value = "diagnostic-provider-private-value"
    monkeypatch.setenv("GEMINI_API_KEY", value)
    provider = {"name": "gemini", "key": value, "model": "fixture", "url": "https://provider.example/models"}

    def post(*args, **kwargs):
        raise requests.ConnectionError(f"diagnostic URL key={value}")

    monkeypatch.setattr(requests, "post", post)
    with pytest.raises(ai_translator.ProviderRequestFailed, match="network request failed"):
        ai_translator._call_provider(provider, "translate", "test")
    assert value not in caplog.text and "[REDACTED]" in caplog.text


@pytest.mark.parametrize("code,status", [(200, "ok"), (401, "auth_error"), (404, "model_error"), (429, "rate_limit"), (503, "http_error")])
def test_model_setup_classifies_provider_failures(monkeypatch, code, status):
    setup = orchestrator()
    monkeypatch.setattr(setup, "SKIP_HEALTHCHECK", False)

    class Response:
        status_code = code

        def json(self):
            return {"choices": [{"message": {"content": "OK"}}]}

    monkeypatch.setattr(requests, "post", lambda *a, **k: Response())
    assert setup.health_check({"name": "generic-openai", "url": "https://provider.example/chat",
                               "key": "diagnostic-key-not-a-credential", "model": "fixture"})["status"] == status


def test_model_setup_rejects_empty_success_body(monkeypatch):
    setup = orchestrator()
    monkeypatch.setattr(setup, "SKIP_HEALTHCHECK", False)

    class Response:
        status_code = 200

        def json(self):
            return {"choices": []}

    monkeypatch.setattr(requests, "post", lambda *a, **k: Response())
    assert setup.health_check({"name": "generic-openai", "url": "https://provider.example/chat",
                               "key": "diagnostic-key-not-a-credential", "model": "fixture"})["status"] == "malformed"
