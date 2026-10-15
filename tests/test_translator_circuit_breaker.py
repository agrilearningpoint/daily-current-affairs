"""Translator provider circuit breaker.

Live 2026-10-15 evidence: every configured provider rejected translation calls
(Gemini 429, Groq 404 unknown model, OpenRouter 402 no credit, Mistral 429), and
the translator re-dialled all of them for every text of every item — the stage
burned its whole 900s budget three times and the edition could never reach the
PDF stage. A provider that is rate-limited or whose credentials are rejected
must be parked for the rest of the run instead.
"""
import pytest
import requests

from pipeline import ai_translator as translator

PROVIDERS = [
    {"name": "gemini", "url": "https://gemini.example/models", "key": "k1", "model": "m1"},
    {"name": "mistral", "url": "https://mistral.example/chat", "key": "k2", "model": "m2"},
]


class _Response:
    def __init__(self, status_code):
        self.status_code = status_code
        self.text = "diagnostic"

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"{self.status_code} Client Error")

    def json(self):
        return {"choices": [{"message": {"content": "भारत ने योजना को मंजूरी दी।"}}]}


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    translator.reset_provider_circuits()
    translator._CACHE.clear()
    monkeypatch.setattr(translator, "_PROVIDERS_CACHE", list(PROVIDERS), raising=False)
    monkeypatch.setattr(translator.time, "sleep", lambda _seconds: None)
    yield
    translator.reset_provider_circuits()
    translator._CACHE.clear()
    monkeypatch.setattr(translator, "_PROVIDERS_CACHE", None, raising=False)


def _install_post(monkeypatch, statuses, calls):
    """Return configured status codes per provider name and count the calls."""
    def post(url, *, headers, json, timeout):
        name = "gemini" if "gemini" in url else "mistral"
        calls.append(name)
        code = statuses.get(name, 429)
        if isinstance(code, Exception):
            raise code
        return _Response(code)
    # _call_provider imports requests lazily, so patch the module attribute
    monkeypatch.setattr(requests, "post", post)


def test_rate_limited_provider_is_parked_and_not_redialled(monkeypatch):
    calls = []
    _install_post(monkeypatch, {"gemini": 429, "mistral": 429}, calls)
    first = translator.translate_content("Wheat MSP raised by Rs 150 per quintal.", task="headline")
    assert first["passed"] is False and first["provider"] == "parked"
    assert calls.count("gemini") == 1, "a 429 provider must be parked after one attempt"
    assert calls.count("mistral") == 1

    calls.clear()
    second = translator.translate_content("Kharif sowing area increased 2 percent.", task="headline")
    assert second["provider"] == "parked"
    assert calls == [], "parked providers must not be dialled again for other texts"


def test_rejected_credentials_open_a_long_circuit(monkeypatch):
    calls = []
    _install_post(monkeypatch, {"gemini": 402, "mistral": 429}, calls)
    translator.translate_content("RBI kept the repo rate at 6.00 percent.", task="headline")
    assert translator._provider_available("gemini") is False
    assert translator._provider_available("mistral") is False
    # 402 means "no credit" — a far longer park than a transient 429
    assert translator._PROVIDER_DOWN_UNTIL["gemini"] > translator._PROVIDER_DOWN_UNTIL["mistral"]


def test_healthy_provider_still_answers_and_opens_no_circuit(monkeypatch):
    calls = []
    _install_post(monkeypatch, {"gemini": 429, "mistral": 200}, calls)
    result = translator.translate_content("Cabinet approved a scheme for farmers.", task="headline")
    assert result["passed"] is True and result["provider"] == "mistral"
    assert translator._provider_available("mistral") is True
    assert translator._provider_available("gemini") is False


def test_cooldown_expiry_restores_the_provider(monkeypatch):
    calls = []
    _install_post(monkeypatch, {"gemini": 429, "mistral": 429}, calls)
    translator.translate_content("ICAR released a drought tolerant variety.", task="headline")
    assert translator._provider_available("gemini") is False
    for name in list(translator._PROVIDER_DOWN_UNTIL):
        translator._PROVIDER_DOWN_UNTIL[name] = 0.0
    assert translator._provider_available("gemini") is True


def test_no_configured_provider_is_reported_distinctly(monkeypatch):
    monkeypatch.setattr(translator, "_PROVIDERS_CACHE", [], raising=False)
    result = translator.translate_content("Some text for translation.", task="general")
    assert result["provider"] == "none" and result["issues"] == ["no providers configured"]
