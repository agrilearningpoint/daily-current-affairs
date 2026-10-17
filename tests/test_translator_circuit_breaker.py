"""Translator provider parking on top of main's rate-limit skipping.

Live 2026-10-15 evidence: gemini 429, groq 404 (unknown model), openrouter 402
(no credit) and mistral 429 - every provider rejected every call, and the
translator re-dialled them for each text of each item, which burned the whole
900 s stage budget three times. main added rate-limit skipping; these tests pin
the additional guarantee that a provider whose credentials are rejected outright
is not dialled again either.
"""
import pytest
import requests

from pipeline import ai_translator


class _Response:
    def __init__(self, status_code, body=None):
        self.status_code = status_code
        self._body = body or {"choices": [{"message": {"content": "भारत ने योजना को मंजूरी दी।"}}]}
        self.text = "diagnostic"

    def raise_for_status(self):
        if self.status_code >= 400:
            error = requests.HTTPError(f"{self.status_code} Client Error")
            error.response = self
            raise error

    def json(self):
        return self._body


PROVIDERS = [
    {"name": "gemini", "url": "https://gemini.example/v1/models", "key": "k1", "model": "m1"},
    {"name": "mistral", "url": "https://mistral.example/v1/chat/completions", "key": "k2", "model": "m2"},
]


@pytest.fixture(autouse=True)
def clean_state(monkeypatch):
    ai_translator.reset_provider_state()
    ai_translator.clear_cache()
    monkeypatch.setattr(ai_translator, "_PROVIDERS_CACHE", list(PROVIDERS), raising=False)
    monkeypatch.setattr(ai_translator.time, "sleep", lambda _seconds: None)
    yield
    ai_translator.reset_provider_state()
    ai_translator.clear_cache()
    monkeypatch.setattr(ai_translator, "_PROVIDERS_CACHE", None, raising=False)


def _install_post(monkeypatch, statuses, calls):
    def post(url, *, headers, json, timeout):
        name = "gemini" if "gemini" in url else "mistral"
        calls.append(name)
        code = statuses.get(name, 429)
        if isinstance(code, Exception):
            raise code
        return _Response(code)
    monkeypatch.setattr(requests, "post", post)


def test_rate_limited_providers_are_not_redialled(monkeypatch):
    calls = []
    _install_post(monkeypatch, {"gemini": 429, "mistral": 429}, calls)
    first = ai_translator.translate_content("Wheat MSP raised by Rs 150 per quintal.", task="headline")
    assert first["passed"] is False
    assert calls.count("gemini") == 1 and calls.count("mistral") == 1

    calls.clear()
    second = ai_translator.translate_content("Kharif sowing area increased 2 percent.", task="headline")
    assert second["passed"] is False
    assert calls == [], "providers that already refused must not be dialled again"


@pytest.mark.parametrize("status, healthy", [(402, "mistral"), (404, "mistral"), (401, "mistral")])
def test_rejected_credentials_park_the_provider(monkeypatch, status, healthy):
    calls = []
    _install_post(monkeypatch, {"gemini": status, "mistral": 200}, calls)
    result = ai_translator.translate_content("Cabinet approved a scheme for farmers.", task="headline")
    assert result["passed"] is True and result["provider"] == healthy
    assert ai_translator._provider_available("gemini") is False
    assert [p["name"] for p in ai_translator.available_providers()] == ["mistral"]

    calls.clear()
    ai_translator.translate_content("ICAR released a drought tolerant variety.", task="headline")
    assert "gemini" not in calls, "a parked provider must be skipped for later texts"


def test_server_errors_stay_retryable_and_do_not_park_forever(monkeypatch):
    calls = []
    _install_post(monkeypatch, {"gemini": 503, "mistral": 200}, calls)
    result = ai_translator.translate_content("Wheat procurement began in the state mandis.", task="headline")
    assert result["provider"] == "mistral"
    assert ai_translator._provider_available("gemini") is True, "5xx is transient, not dead credentials"


def test_park_expiry_restores_the_provider(monkeypatch):
    calls = []
    _install_post(monkeypatch, {"gemini": 402, "mistral": 429}, calls)
    ai_translator.translate_content("NABARD announced a refinance facility.", task="headline")
    assert ai_translator._provider_available("gemini") is False
    for name in list(ai_translator._PARKED_PROVIDERS):
        ai_translator._PARKED_PROVIDERS[name] = 0.0
    assert ai_translator._provider_available("gemini") is True


def test_exhausted_flag_marks_a_parked_dead_end(monkeypatch):
    """A caller can distinguish "all providers rejected" from a one-off failure."""
    calls = []
    _install_post(monkeypatch, {"gemini": 401, "mistral": 402}, calls)
    result = ai_translator.translate_content("Buffer stock release was approved.", task="headline")
    assert result["passed"] is False
    assert result["issues"] == ["gemini: HTTP 401", "mistral: HTTP 402"]
    assert result["exhausted"] is True
    assert ai_translator.available_providers() == []


def test_transient_failures_do_not_report_exhausted(monkeypatch):
    calls = []
    _install_post(monkeypatch, {"gemini": 503, "mistral": 503}, calls)
    result = ai_translator.translate_content("Sowing progress is ahead of last year.", task="headline")
    assert result["passed"] is False
    assert result["exhausted"] is False, "5xx providers are still diallable next time"


def test_no_configured_provider_reports_no_providers(monkeypatch):
    monkeypatch.setattr(ai_translator, "_PROVIDERS_CACHE", [], raising=False)
    result = ai_translator.translate_content("Some text for translation.", task="general")
    assert result["provider"] == "none" and result["issues"] == ["no providers configured"]
