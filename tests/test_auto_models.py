"""'auto' model selection and free-only / cooldown behaviour."""
import time

from pipeline import ai_router, ai_translator


def _clear_keys(monkeypatch):
    for var in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GROQ_API_KEY", "DEEPSEEK_API_KEY",
                "OPENAI_API_KEY", "LLM_API_URL", "LLM_API_KEY", "OPENROUTER_API_KEY",
                "MISTRAL_API_KEY", "NVIDIA_API_KEY", "OLLAMA_API_KEY", "OLLAMA_BASE_URL",
                "OLLAMA_API_URL"):
        monkeypatch.delenv(var, raising=False)


def test_auto_resolves_to_first_preference_without_discovery(monkeypatch):
    _clear_keys(monkeypatch)
    monkeypatch.setenv("ALP_MODEL_AUTO_DISCOVERY", "0")
    monkeypatch.setenv("ALP_ENABLE_DEEPSEEK", "1")
    for name in ("GEMINI", "GROQ", "NVIDIA", "MISTRAL", "OPENROUTER", "OLLAMA", "DEEPSEEK"):
        monkeypatch.setenv(f"{name}_API_KEY", "k")
        monkeypatch.setenv(f"{name}_MODEL", "auto")
    providers = {p.name: p for p in ai_router._build_default_providers()}
    for name, provider in providers.items():
        assert provider.model == ai_router._PREFERRED_MODELS[name][0]
    # free providers first, paid DeepSeek last
    assert list(providers)[-1] == "deepseek"


def test_ollama_key_alone_uses_ollama_cloud(monkeypatch):
    _clear_keys(monkeypatch)
    monkeypatch.setenv("ALP_MODEL_AUTO_DISCOVERY", "0")
    monkeypatch.setenv("OLLAMA_API_KEY", "k")
    (provider,) = ai_router._build_default_providers()
    assert provider.url == "https://ollama.com/v1/chat/completions"


def test_auto_picks_live_preferred_model_and_skips_retired(monkeypatch):
    provider = ai_router.Provider(name="nvidia", url="https://x/v1/chat/completions", key="k",
                                  model="meta/llama-3.3-70b-instruct")
    live = ["nvidia/nemotron-3-super-120b-a12b", "openai/gpt-oss-20b", "nvidia/nemotron-3.5-embed-1b"]
    assert ai_router._choose_live_model(provider, live) == "nvidia/nemotron-3-super-120b-a12b"


def test_openrouter_catalogue_is_free_only():
    assert ai_router._is_free_listing({"id": "google/gemma-4-31b-it:free"})
    assert ai_router._is_free_listing({"id": "x/y", "pricing": {"prompt": "0", "completion": "0"}})
    assert not ai_router._is_free_listing({"id": "openai/gpt-4o-mini",
                                           "pricing": {"prompt": "0.00000015", "completion": "0.0000006"}})


def test_rate_limit_is_a_cooldown_not_a_ban(monkeypatch):
    ai_translator.reset_provider_cache()
    ai_translator._park_provider("groq", 60)
    assert ai_translator._provider_parked("groq")
    ai_translator._COOLDOWN_UNTIL["groq"] = time.time() - 1
    assert not ai_translator._provider_parked("groq")
    ai_translator._park_provider("deepseek", None)
    time.sleep(0.02)
    assert ai_translator._provider_parked("deepseek")
    ai_translator.reset_provider_cache()
