from pipeline import ai_translator


def test_provider_discovery_keeps_all_configured_keys(monkeypatch):
    from pipeline import ai_router

    providers = [
        {"name": name, "url": f"https://{name}.example/v1/chat/completions",
         "key": f"test-key-{name}", "model": f"{name}-model"}
        for name in ("gemini", "groq", "openrouter", "mistral")
    ]
    monkeypatch.setattr(ai_router, "list_providers", lambda: providers)
    monkeypatch.setattr(ai_translator, "_PROVIDERS_CACHE", None)

    discovered = ai_translator._discover_providers()

    assert [provider["name"] for provider in discovered] == [
        "gemini", "groq", "openrouter", "mistral"
    ]


def configure_providers(monkeypatch, names):
    providers = [
        {"name": name, "url": f"https://{name}.example/v1/chat/completions",
         "key": f"test-key-{name}", "model": f"{name}-model"}
        for name in names
    ]
    monkeypatch.setattr(ai_translator, "_PROVIDERS_CACHE", providers)
    ai_translator.clear_cache()
    ai_translator._RATE_LIMITED_PROVIDERS.clear()
    return providers


def test_rate_limited_provider_is_skipped_and_all_keys_are_tried(monkeypatch):
    providers = configure_providers(monkeypatch, ["gemini", "groq", "openrouter", "mistral"])
    attempted = []

    def rate_limited(provider, system, user):
        attempted.append(provider["name"])
        raise ai_translator.ProviderRateLimited(provider["name"])

    monkeypatch.setattr(ai_translator, "_call_provider", rate_limited)
    monkeypatch.setattr(ai_translator, "MAX_RETRIES", 2)

    result = ai_translator.translate_content("Farmers receive support.")

    assert attempted == [provider["name"] for provider in providers]
    assert result["passed"] is False
    assert result["issues"] == [f"{name}: rate limited" for name in attempted]

    ai_translator.translate_content("Another agriculture update.")
    assert attempted == [provider["name"] for provider in providers]


def test_http_429_marks_provider_for_fallback(monkeypatch):
    import requests

    class RateLimitedResponse:
        status_code = 429

    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: RateLimitedResponse())
    provider = {"name": "mistral", "url": "https://mistral.example/v1/chat/completions",
                "key": "diagnostic-key", "model": "mistral-model"}

    try:
        ai_translator._call_provider(provider, "system", "user")
    except ai_translator.ProviderRateLimited as exc:
        assert str(exc) == "mistral"
    else:
        raise AssertionError("HTTP 429 did not trigger provider fallback")


def test_translation_falls_back_after_a_rate_limited_provider(monkeypatch):
    configure_providers(monkeypatch, ["gemini", "groq"])
    attempted = []

    def translate(provider, system, user):
        attempted.append(provider["name"])
        if provider["name"] == "gemini":
            raise ai_translator.ProviderRateLimited(provider["name"])
        return "किसानों को सहायता मिलेगी।"

    monkeypatch.setattr(ai_translator, "_call_provider", translate)
    result = ai_translator.translate_content("Farmers receive support.")

    assert attempted == ["gemini", "groq"]
    assert result["passed"] is True
    assert result["provider"] == "groq"


def test_translation_reports_provider_http_failures(monkeypatch):
    configure_providers(monkeypatch, ["gemini", "openrouter"])
    attempted = []

    def unavailable(provider, system, user):
        attempted.append(provider["name"])
        raise ai_translator.ProviderRequestFailed("HTTP 401")

    monkeypatch.setattr(ai_translator, "_call_provider", unavailable)
    result = ai_translator.translate_content("Farmers receive support.")

    assert attempted == ["gemini", "openrouter"]
    assert result["issues"] == ["gemini: HTTP 401", "openrouter: HTTP 401"]
