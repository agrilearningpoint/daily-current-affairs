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
             "LLM_API_KEY", "OPENROUTER_API_KEY", "NVIDIA_API_KEY"]
    for name in names:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("LLM_API_URL", "https://provider.example/chat/completions")
    monkeypatch.setenv("LLM_API_KEY", "diagnostic-generic-not-a-credential")
    monkeypatch.setenv("OPENROUTER_API_KEY", "diagnostic-openrouter-not-a-credential")
    monkeypatch.setenv("NVIDIA_API_KEY", "diagnostic-nvidia-not-a-credential")
    expected = ai_router._build_default_providers()
    actual = orchestrator().load_keys()
    assert [item["name"] for item in actual] == [item.name for item in expected] == [
        "generic-openai", "openrouter", "nvidia"
    ]
    assert [item["model"] for item in actual] == [item.model for item in expected]
    assert actual[0]["env_used"] == "LLM_API_KEY"
    assert actual[-1]["env_used"] == "NVIDIA_API_KEY"


def test_groq_default_uses_a_current_model(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "diagnostic-groq-not-a-credential")
    monkeypatch.delenv("GROQ_MODEL", raising=False)

    groq = next(provider for provider in ai_router._build_default_providers()
                if provider.name == "groq")

    assert groq.model == "llama-3.3-70b-versatile"


def test_nvidia_default_endpoint_and_model(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "diagnostic-nvidia-not-a-credential")
    monkeypatch.delenv("NVIDIA_MODEL", raising=False)

    nvidia = next(provider for provider in ai_router._build_default_providers()
                  if provider.name == "nvidia")

    assert nvidia.url == "https://integrate.api.nvidia.com/v1/chat/completions"
    assert nvidia.model == "meta/llama-3.3-70b-instruct"


def test_openai_and_generic_openai_keys_both_join_fallback_registry(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "diagnostic-openai-not-a-credential")
    monkeypatch.setenv("LLM_API_URL", "https://generic.example/v1/chat/completions")
    monkeypatch.setenv("LLM_API_KEY", "diagnostic-generic-not-a-credential")

    providers = ai_router._build_default_providers()

    assert [provider.name for provider in providers] == ["openai", "generic-openai"]


def test_router_falls_back_to_nvidia_and_preserves_json_mode(monkeypatch):
    providers = [
        ai_router.Provider(name="openrouter", url="https://openrouter.example/chat/completions",
                           key="diagnostic-openrouter-not-a-credential", model="first-model", priority=1),
        ai_router.Provider(name="nvidia", url="https://integrate.api.nvidia.com/v1/chat/completions",
                           key="diagnostic-nvidia-not-a-credential", model="nvidia-model", priority=2),
    ]
    calls = []

    class Response:
        def __init__(self, status_code):
            self.status_code = status_code
            self.text = ""

        def json(self):
            return {"choices": [{"message": {"content": "translated"}}]}

    def post(url, *, headers, json, timeout):
        calls.append((url, headers, json))
        return Response(401 if len(calls) == 1 else 200)

    monkeypatch.setattr(ai_router, "_get_providers", lambda: providers)
    monkeypatch.setattr(ai_router, "_within_budget", lambda: True)
    monkeypatch.setattr(requests, "post", post)
    ai_router.clear_cache()

    result = ai_router.route(
        "diagnostic nvidia fallback prompt",
        task="structured_test",
        response_format={"type": "json_object"},
        system_prompt="Return JSON only.",
    )

    assert result == "translated"
    assert [call[0] for call in calls] == [
        "https://openrouter.example/chat/completions",
        "https://integrate.api.nvidia.com/v1/chat/completions",
    ]
    assert calls[1][1]["Authorization"] == "Bearer diagnostic-nvidia-not-a-credential"
    assert calls[1][2]["response_format"] == {"type": "json_object"}
    assert calls[1][2]["messages"][0] == {
        "role": "system", "content": "Return JSON only."
    }


def test_gemini_router_applies_system_prompt_and_json_mode(monkeypatch):
    provider = ai_router.Provider(
        name="gemini",
        url="https://generativelanguage.example/v1beta/models",
        key="diagnostic-gemini-not-a-credential",
        model="gemini-test",
        priority=1,
    )
    calls = []

    class Response:
        status_code = 200
        text = ""

        def json(self):
            return {"candidates": [{"content": {"parts": [{"text": "{\"ok\":true}"}]}}]}

    def post(url, *, headers, json, timeout):
        calls.append((url, headers, json))
        return Response()

    monkeypatch.setattr(ai_router, "_get_providers", lambda: [provider])
    monkeypatch.setattr(ai_router, "_within_budget", lambda: True)
    monkeypatch.setattr(requests, "post", post)
    ai_router.clear_cache()

    assert ai_router.route(
        "Produce the requested object",
        task="gemini_json_test",
        response_format={"type": "json_object"},
        system_prompt="Return a valid JSON object.",
    ) == '{"ok":true}'
    assert calls[0][0] == (
        "https://generativelanguage.example/v1beta/models/gemini-test:generateContent"
    )
    assert calls[0][1]["x-goog-api-key"] == provider.key
    assert calls[0][2]["systemInstruction"]["parts"][0]["text"] == "Return a valid JSON object."
    assert calls[0][2]["generationConfig"]["responseMimeType"] == "application/json"


@pytest.mark.parametrize("provider_name", ["gemini", "generic-openai", "nvidia"])
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


def test_legacy_nvidia_helper_uses_openai_compatible_transport(monkeypatch):
    from pipeline import llm_helper

    secret = "diagnostic-nvidia-not-a-credential"
    monkeypatch.setenv("NVIDIA_API_KEY", secret)
    monkeypatch.delenv("NVIDIA_MODEL", raising=False)

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "Hello"}}]}

    def post(url, *, headers, json, timeout):
        assert url == "https://integrate.api.nvidia.com/v1/chat/completions"
        assert headers["Authorization"] == f"Bearer {secret}"
        assert json["model"] == "meta/llama-3.3-70b-instruct"
        assert json["messages"] == [{"role": "user", "content": "Say hello"}]
        assert timeout == 60
        return Response()

    monkeypatch.setattr(requests, "post", post)
    assert llm_helper.call_nvidia("Say hello") == (
        "Hello", "nvidia/meta/llama-3.3-70b-instruct"
    )


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
