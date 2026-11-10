"""Every repo secret wired in: new AI providers, news/search helpers, key verifier,
and the watchdog no longer failing on an edition that was already published.

All network is faked; no test talks to a real API.
"""
import importlib.util
import json
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import requests

import main
from pipeline import ai_router, discovery_api, news_api_sources
from pipeline.persistence import write_json_atomic

ROOT = Path(__file__).resolve().parents[1]
FT = ai_router.FailureType

_PROVIDER_ENV = (
    "GEMINI_API_KEY", "GOOGLE_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY",
    "OPENAI_BASE_URL", "LLM_API_URL", "LLM_API_KEY", "OPENROUTER_API_KEY", "MISTRAL_API_KEY",
    "NVIDIA_API_KEY", "OLLAMA_API_KEY", "OLLAMA_BASE_URL", "OLLAMA_API_URL",
    "COHERE_API_KEY", "LL7_API_KEY", "LLM7_API_KEY", "HUGGINGFACE_API_KEY", "HF_TOKEN",
    "POLLINATIONS_API_KEY", "POLLINATIONS_BASE_URL", "POLLINATIONS_MODEL",
    "SILICONFLOW_API_KEY", "SILICONFLOW_BASE_URL", "SILICONFLOW_MODEL",
)
_AUX_ENV = ("SERPER_API_KEY", "GNEWS_API_KEY", "NEWSDATA_API_KEY", "JINA_API_KEY")

# Not real credentials; short enough that CI's secret scan never matches them.
OPENROUTER_STYLE = "sk-or-v1-fake"
OPENAI_STYLE = "sk-proj-fake"
POLLINATIONS_STYLE = "0" * 32 + ".fakesecret"
SILICONFLOW_STYLE = "sk-fakesiliconflowkey"


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    for var in _PROVIDER_ENV + _AUX_ENV:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ALP_MODEL_AUTO_DISCOVERY", "0")
    monkeypatch.delenv("ALP_DISABLE_NETWORK", raising=False)
    discovery_api.reset_services()
    yield
    discovery_api.reset_services()


def _load(rel, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _use(monkeypatch, providers):
    monkeypatch.setattr(ai_router, "_get_providers", lambda: providers)
    monkeypatch.setattr(ai_router, "_PROVIDERS", providers)
    monkeypatch.setattr(ai_router, "_within_budget", lambda: True)
    ai_router.clear_cache()


class Resp:
    def __init__(self, code=200, data=None, text=None, headers=None):
        self.status_code = code
        self._data = data if data is not None else {}
        self.text = text if text is not None else json.dumps(self._data)
        self.headers = headers or {}

    def json(self):
        return self._data


def _no_network(*_a, **_k):
    raise AssertionError("network must not be touched")


# --------------------------------------------------------------------------- #
# Router: registry, order, caps
# --------------------------------------------------------------------------- #
def test_new_providers_are_off_without_their_secrets():
    assert ai_router._build_default_providers() == []


def test_full_provider_order_cheapest_and_most_reliable_first(monkeypatch):
    for var in ("GROQ_API_KEY", "GEMINI_API_KEY", "MISTRAL_API_KEY",
                "OPENROUTER_API_KEY", "NVIDIA_API_KEY", "COHERE_API_KEY", "LL7_API_KEY",
                "HUGGINGFACE_API_KEY", "POLLINATIONS_API_KEY", "SILICONFLOW_API_KEY"):
        monkeypatch.setenv(var, "k")
    names = [p.name for p in ai_router._build_default_providers()]
    assert names == ["groq", "gemini", "llm7", "mistral", "openrouter",
                     "cohere", "pollinations", "huggingface", "nvidia", "siliconflow"]


def test_new_provider_endpoints_and_low_caps(monkeypatch):
    monkeypatch.setenv("COHERE_API_KEY", "c")
    monkeypatch.setenv("LL7_API_KEY", "l")
    monkeypatch.setenv("HUGGINGFACE_API_KEY", "h")
    monkeypatch.setenv("NVIDIA_API_KEY", "n")
    monkeypatch.setenv("POLLINATIONS_API_KEY", POLLINATIONS_STYLE)
    monkeypatch.setenv("SILICONFLOW_API_KEY", SILICONFLOW_STYLE)
    by = {p.name: p for p in ai_router._build_default_providers()}
    assert by["cohere"].url == "https://api.cohere.ai/compatibility/v1/chat/completions"
    assert by["cohere"].model == "command-r7b-12-2024" and by["cohere"].rpd_limit == 30
    assert by["llm7"].url == "https://api.llm7.io/v1/chat/completions" and by["llm7"].model == "default"
    assert by["huggingface"].url == "https://router.huggingface.co/v1/chat/completions"
    assert by["huggingface"].rpd_limit <= 20
    # Pollinations: anonymous tier is 1 reply / 45 s per IP, so the cap is small —
    # a 402 FREE_LIMIT takes the provider out for the run anyway.
    assert by["pollinations"].url == "https://text.pollinations.ai/openai/chat/completions"
    assert by["pollinations"].model == "openai" and by["pollinations"].rpd_limit <= 40
    # SiliconFlow: paid per token → after NVIDIA / the generic endpoint.
    assert by["siliconflow"].url == "https://api.siliconflow.com/v1/chat/completions"
    assert by["siliconflow"].model == "Qwen/Qwen3.5-9B"
    assert by["siliconflow"].priority > by["nvidia"].priority


def test_daily_cap_takes_cohere_out_after_30_calls(monkeypatch):
    monkeypatch.setenv("COHERE_API_KEY", "c")
    cohere = ai_router._build_default_providers()[0]
    for _ in range(30):
        ai_router._count_call(cohere.quota_key())
    assert not cohere.is_available()


def test_wrong_shaped_keys_are_reported_without_leaking_the_value(monkeypatch):
    """A key that cannot possibly authenticate is named in unconfigured_notes()."""
    monkeypatch.setenv("SILICONFLOW_API_KEY", "not-a-siliconflow-key")
    monkeypatch.setenv("POLLINATIONS_API_KEY", "not-a-pollinations-token")
    notes = ai_router.unconfigured_notes()
    assert any("SILICONFLOW_API_KEY" in n for n in notes)
    assert any("POLLINATIONS_API_KEY" in n for n in notes)
    joined = " ".join(notes)
    assert "not-a-siliconflow-key" not in joined and "not-a-pollinations-token" not in joined

    # Correctly shaped keys are silent (shape check only — no network).
    monkeypatch.setenv("SILICONFLOW_API_KEY", SILICONFLOW_STYLE)
    monkeypatch.setenv("POLLINATIONS_API_KEY", POLLINATIONS_STYLE)
    assert ai_router.unconfigured_notes() == []
    names = [p.name for p in ai_router._build_default_providers()]
    assert names == ["pollinations", "siliconflow"]


# --------------------------------------------------------------------------- #
# Router: failure handling for the new providers
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("code", [401, 402])
def test_401_and_402_take_a_provider_out_for_the_run(monkeypatch, code):
    paid = ai_router.Provider(name="siliconflow", url="https://api.siliconflow.com/v1/chat/completions",
                              key="k", model="Qwen/Qwen3.5-9B", priority=1)
    backup = ai_router.Provider(name="llm7", url="https://api.llm7.io/v1/chat/completions",
                                key="k", model="default", priority=2)
    _use(monkeypatch, [paid, backup])
    calls = []

    def fake(provider, *a, **k):
        calls.append(provider.name)
        if provider.name == "siliconflow":
            return None, ai_router._classify_error(code, "payment_required")
        return "ok", None

    monkeypatch.setattr(ai_router, "_call_provider", fake)
    assert ai_router.route("one") == "ok"
    assert ai_router.route("two") == "ok"
    assert calls == ["siliconflow", "llm7", "llm7"]
    assert ai_router.blocked_until("siliconflow") - time.time() > 3600


def test_429_rotates_groq_to_its_next_model_in_the_same_call(monkeypatch):
    groq = ai_router.Provider(name="groq", url="https://api.groq.com/openai/v1/chat/completions", key="k",
                              model="openai/gpt-oss-120b", per_model_quota=True,
                              models=["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"])
    _use(monkeypatch, [groq])
    seen = []

    def fake(provider, *a, **k):
        seen.append(provider.model)
        return (None, FT.RATE_LIMIT) if provider.model == "openai/gpt-oss-120b" else ("ok", None)

    monkeypatch.setattr(ai_router, "_call_provider", fake)
    assert ai_router.route("x") == "ok"
    assert seen == ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]
    assert ai_router.is_blocked("groq::openai/gpt-oss-120b") and not ai_router.is_blocked("groq")


def test_429_on_account_wide_cohere_moves_to_next_provider(monkeypatch):
    cohere = ai_router.Provider(name="cohere", url="https://c/chat/completions", key="k",
                                model="command-r7b-12-2024", priority=1)
    llm7 = ai_router.Provider(name="llm7", url="https://l/chat/completions", key="k", model="default", priority=2)
    _use(monkeypatch, [cohere, llm7])
    seen = []

    def fake(provider, *a, **k):
        seen.append(provider.name)
        return (None, FT.RATE_LIMIT) if provider.name == "cohere" else ("ok", None)

    monkeypatch.setattr(ai_router, "_call_provider", fake)
    assert ai_router.route("x") == "ok"
    assert seen == ["cohere", "llm7"] and ai_router.is_blocked("cohere")


def test_410_retires_the_nvidia_model_and_rotates(monkeypatch):
    nvidia = ai_router.Provider(name="nvidia", url="https://integrate.api.nvidia.com/v1/chat/completions",
                                key="k", model="meta/llama-3.1-8b-instruct",
                                models=["meta/llama-3.1-8b-instruct", "openai/gpt-oss-20b"])
    _use(monkeypatch, [nvidia])
    seen = []

    def fake(provider, *a, **k):
        seen.append(provider.model)
        if provider.model == "meta/llama-3.1-8b-instruct":
            return None, ai_router._classify_error(410, "end of life")
        return "ok", None

    monkeypatch.setattr(ai_router, "_call_provider", fake)
    assert ai_router.route("x") == "ok"
    assert seen == ["meta/llama-3.1-8b-instruct", "openai/gpt-oss-20b"]
    assert ai_router.is_blocked("nvidia::meta/llama-3.1-8b-instruct")
    assert not ai_router.is_blocked("nvidia")


def test_discovery_never_picks_an_eol_or_retired_nvidia_model():
    nvidia = ai_router.Provider(name="nvidia", url="https://integrate.api.nvidia.com/v1/chat/completions",
                                key="k", model="not-listed")
    live = ["01-ai/yi-large", "meta/llama-3.1-8b-instruct", "abc/some-chat-model",
            "openai/gpt-oss-20b", "meta/llama-guard-4-12b"]
    # Only EOL / hanging / unreviewed / moderation models advertised: no pick at all.
    assert ai_router._choose_live_model(nvidia, live) is None
    live.append("meta/llama-3.2-90b-vision-instruct")
    assert ai_router._choose_live_model(nvidia, live) == "meta/llama-3.2-90b-vision-instruct"
    ai_router.block("nvidia::meta/llama-3.2-90b-vision-instruct", 3600, "410 earlier in the run")
    assert ai_router._choose_live_model(nvidia, live) is None


def test_gemini_timeout_is_short_and_a_hung_model_is_parked(monkeypatch):
    monkeypatch.delenv("ALP_STAGE_TIMEOUT", raising=False)
    assert ai_router.request_timeout("gemini") <= 25
    assert ai_router.request_timeout("groq") == ai_router.TIMEOUT
    gem = ai_router.Provider(name="gemini", url="https://g/v1beta/models", key="k",
                             model="gemini-3.5-flash-lite", per_model_quota=True,
                             models=["gemini-3.5-flash-lite", "gemini-3.1-flash-lite"])
    _use(monkeypatch, [gem])
    monkeypatch.setattr(ai_router, "_call_provider", lambda p, *a, **k: (None, FT.TIMEOUT))
    assert ai_router.route("x") is None
    assert ai_router.is_blocked("gemini::gemini-3.5-flash-lite")
    assert gem.model == "gemini-3.1-flash-lite"


def test_stage00_moves_past_a_retired_model_and_seeds_only_that_model(monkeypatch, tmp_path):
    setup = _load("agents/00_model_orchestrator.py", "orch_all_keys")
    monkeypatch.setattr(setup, "STATUS_FILE", tmp_path / "model_status.json")
    monkeypatch.setattr(setup, "load_keys", lambda: [
        {"name": "nvidia", "url": "u", "key": "k", "model": "old", "models": ["old", "new"],
         "priority": 50, "env_used": "NVIDIA_API_KEY"}])
    monkeypatch.setattr(setup, "health_check", lambda p: (
        {"status": "model_error", "detail": "HTTP 410"} if p["model"] == "old" else {"status": "ok", "detail": "live"}))
    assert setup.main() == 0
    report = json.loads((tmp_path / "model_status.json").read_text())
    assert report["providers"][0]["model"] == "new" and report["status"] == "ok"
    assert ai_router.is_blocked("nvidia::old") and not ai_router.is_blocked("nvidia")
    assert set(report["aux_services"]) == {"serper", "gnews", "newsdata", "jina"}


def test_stage00_410_is_a_model_error(monkeypatch):
    setup = _load("agents/00_model_orchestrator.py", "orch_410")
    monkeypatch.setattr(requests, "post", lambda *a, **k: Resp(410))
    assert setup.health_check({"name": "nvidia", "url": "https://x", "key": "k", "model": "m"})["status"] == "model_error"


# --------------------------------------------------------------------------- #
# News / search helpers
# --------------------------------------------------------------------------- #
def test_helpers_are_off_without_keys(monkeypatch):
    monkeypatch.setattr(discovery_api.requests, "get", _no_network)
    monkeypatch.setattr(discovery_api.requests, "post", _no_network)
    assert discovery_api.serper_search("x") == []
    assert discovery_api.gnews_articles() == []
    assert discovery_api.newsdata_latest() == []
    assert discovery_api.corroborate("Cabinet approves new farm scheme for farmers") == {"sources": [], "official": False}
    out = news_api_sources.collect(datetime.now(timezone.utc) - timedelta(days=1), datetime.now(timezone.utc),
                                   seen_hashes=set(), seen_titles=set(), validate_title=lambda t, s: (t, True),
                                   clean_url=lambda u: u, content_hash=lambda t, u: t, clean_summary=lambda s: s)
    assert out["articles"] == []


@pytest.mark.parametrize("code", [401, 402, 403, 429])
def test_gnews_auth_credit_or_quota_error_turns_it_off_for_the_run(monkeypatch, code):
    monkeypatch.setenv("GNEWS_API_KEY", "gnews-test-key-123")
    calls = []
    monkeypatch.setattr(discovery_api.requests, "get",
                        lambda *a, **k: (calls.append(1), Resp(code, {"errors": ["gnews-test-key-123 bad"]}))[1])
    assert discovery_api.gnews_articles() == []
    assert discovery_api.gnews_articles() == []
    assert len(calls) == 1 and not discovery_api.GNEWS.enabled()
    assert "gnews-test-key-123" not in json.dumps(discovery_api.services_status())


def test_per_run_budget_caps_requests(monkeypatch):
    monkeypatch.setenv("NEWSDATA_API_KEY", "nd")
    monkeypatch.setenv("ALP_NEWSDATA_MAX_CALLS", "2")
    calls = []
    monkeypatch.setattr(discovery_api.requests, "get",
                        lambda *a, **k: (calls.append(1), Resp(200, {"status": "success", "results": []}))[1])
    for _ in range(5):
        discovery_api.newsdata_latest()
    assert len(calls) == 2


def test_jina_402_drops_the_key_for_the_run_and_uses_keyless_reader(monkeypatch):
    monkeypatch.setenv("JINA_API_KEY", "jina-test-key")
    auth_seen = []
    body = "Title: x\n\nMarkdown Content:\n" + "Farmers in Punjab received the new MSP payments this week. " * 10

    def get(url, headers=None, timeout=None):
        auth_seen.append("Authorization" in (headers or {}))
        if "Authorization" in (headers or {}):
            return Resp(402, text='{"code":402,"message":"insufficient balance"}')
        return Resp(200, text=body)

    monkeypatch.setattr(discovery_api.requests, "get", get)
    text, _ = discovery_api.jina_read("https://example.com/a")
    assert "MSP payments" in text
    assert not discovery_api.JINA.enabled() and "402" in discovery_api.JINA.off_reason
    discovery_api.jina_read("https://example.com/b")
    assert auth_seen == [True, False, False]


def test_jina_402_without_keyless_fallback_returns_empty_quietly(monkeypatch):
    monkeypatch.setenv("JINA_API_KEY", "jina-test-key")
    monkeypatch.setenv("ALP_JINA_KEYLESS", "0")
    monkeypatch.setattr(discovery_api.requests, "get", lambda *a, **k: Resp(402, text="no balance"))
    assert discovery_api.jina_read("https://example.com/a") == ("", "")
    from pipeline.llm_helper import call_jina_reader
    assert call_jina_reader("https://example.com/b") is None


def test_news_apis_keep_window_and_dedupe_against_rss(monkeypatch):
    monkeypatch.setenv("GNEWS_API_KEY", "g")
    monkeypatch.setenv("NEWSDATA_API_KEY", "n")
    end = datetime(2026, 11, 3, 3, 40, tzinfo=timezone.utc)
    start = end - timedelta(days=1)
    inside = (end - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    outside = (start - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    gnews = {"articles": [
        {"title": "RBI keeps repo rate unchanged at 5.25 per cent", "url": "https://a.example/rbi",
         "description": "The Monetary Policy Committee decided to keep the policy repo rate unchanged today.",
         "publishedAt": inside, "image": "https://a.example/i.jpg", "source": {"name": "A News", "url": "https://a.example"}},
        {"title": "Old story from last week about something", "url": "https://a.example/old",
         "description": "d", "publishedAt": outside, "source": {"name": "A"}},
        {"title": "Same Headline Already In RSS Feed Today", "url": "https://b.example/dup",
         "description": "d", "publishedAt": inside, "source": {"name": "B"}},
    ]}
    newsdata = {"status": "success", "results": [
        {"title": "Cabinet approves Rs 10,000 crore scheme for oilseed farmers", "link": "https://c.example/x",
         "description": "The Union Cabinet approved a new scheme for oilseeds.", "pubDate": (end - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
         "image_url": None, "source_name": "C Times", "source_url": "https://c.example", "duplicate": False},
        {"title": "RBI keeps repo rate unchanged at 5.25 per cent", "link": "https://d.example/rbi",
         "description": "dup", "pubDate": (end - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")},
    ]}
    requested = []

    def get(url, params=None, headers=None, timeout=None):
        requested.append((url, dict(params or {})))
        return Resp(200, gnews if "gnews.io" in url else newsdata)

    monkeypatch.setattr(discovery_api.requests, "get", get)
    seen_titles = {news_api_sources.title_key("Same headline already in RSS feed today")}
    out = news_api_sources.collect(start, end, seen_hashes=set(), seen_titles=seen_titles,
                                   validate_title=lambda t, s: (t.strip(), len(t) > 10),
                                   clean_url=lambda u: u, content_hash=lambda t, u: f"{t}|{u}",
                                   clean_summary=lambda s: s)
    titles = [a["title"] for a in out["articles"]]
    assert titles == ["RBI keeps repo rate unchanged at 5.25 per cent",
                      "Cabinet approves Rs 10,000 crore scheme for oilseed farmers"]
    first = out["articles"][0]
    assert first["source_id"] == "api_gnews" and first["source_tier"] == "tier3" and first["official"] is False
    assert out["report"]["out_of_window"] >= 1 and out["report"]["duplicates"] >= 2
    gnews_calls = [p for u, p in requested if "gnews.io" in u]
    assert len(gnews_calls) <= 4 and all(p["country"] == "in" and p["lang"] == "en" for p in gnews_calls)
    assert gnews_calls[0]["from"] == start.strftime("%Y-%m-%dT%H:%M:%SZ")
    assert len([u for u, _ in requested if "newsdata.io" in u]) <= 3


def test_serper_corroboration_and_402_off(monkeypatch):
    monkeypatch.setenv("SERPER_API_KEY", "serper-test")
    news = {"news": [
        {"title": "Cabinet approves new oilseed mission for farmers", "link": "https://pib.gov.in/x"},
        {"title": "Cabinet approves new oilseed mission for farmers: details", "link": "https://www.thehindu.com/y"},
        {"title": "Unrelated cricket score", "link": "https://z.example/c"},
    ]}
    monkeypatch.setattr(discovery_api.requests, "post", lambda *a, **k: Resp(200, news))
    found = discovery_api.corroborate("Cabinet approves new oilseed mission for farmers", "https://own.example/a")
    assert [s["host"] for s in found["sources"]] == ["pib.gov.in", "thehindu.com"] and found["official"]
    monkeypatch.setattr(discovery_api.requests, "post", lambda *a, **k: Resp(402, text="no credits"))
    discovery_api.reset_services()
    assert discovery_api.corroborate("Cabinet approves new oilseed mission for farmers")["sources"] == []
    assert not discovery_api.SERPER.enabled()


def test_stage04_uses_serper_only_for_items_without_provenance(monkeypatch):
    fv = _load("agents/04_fact_verification.py", "fv_all_keys")
    monkeypatch.setenv("SERPER_API_KEY", "serper-test")
    monkeypatch.setenv("DRY_RUN", "0")
    monkeypatch.setattr(fv, "DISABLE_LLM", True)
    asked = []
    monkeypatch.setattr(discovery_api, "corroborate", lambda title, link="": (
        asked.append(title), {"sources": [{"host": "pib.gov.in", "link": "https://pib.gov.in/x", "title": title}],
                              "official": True})[1])
    article = {"title": "Cabinet approves new oilseed mission worth Rs 10,103 crore for farmers",
               "link": "https://news.example.org/story", "summary": "The Union Cabinet chaired by the Prime Minister "
               "approved the National Mission on Edible Oils with an outlay of Rs 10,103 crore over seven years.",
               "published": datetime.now(timezone.utc).isoformat(), "source_name": "Example News",
               "source_tier": "tier3", "source_level": 5, "category": "aggregator"}
    result = fv.verify_article(article, [article])
    assert asked, "serper should be asked for an item without provenance"
    assert result["provenance_verified"] and "serper_corroborated" in result["flags"]
    assert "serper:pib.gov.in" in result["corroborating_sources"]
    monkeypatch.delenv("SERPER_API_KEY")
    asked.clear()
    plain = fv.verify_article(article, [article])
    assert asked == [] and not plain["provenance_verified"]


# --------------------------------------------------------------------------- #
# scripts/verify_keys.py
# --------------------------------------------------------------------------- #
def test_verify_keys_masks_values_and_reports_missing(monkeypatch, capsys):
    vk = _load("scripts/verify_keys.py", "verify_keys_t")
    for name in vk.SECRETS:
        monkeypatch.delenv(name, raising=False)
    secret = "cohere-test-secret-9876"
    monkeypatch.setenv("COHERE_API_KEY", secret)
    monkeypatch.setattr(vk.requests, "post", lambda *a, **k: Resp(
        402, {"message": f"payment_required for key {secret}"}))
    monkeypatch.setattr(vk.requests, "get", _no_network)
    assert vk.main(["--only", "COHERE_API_KEY,GNEWS_API_KEY"]) == 0
    out = capsys.readouterr().out
    assert secret not in out
    assert re.search(r"COHERE_API_KEY\s*\| FAIL\s*\| 402", out)
    assert re.search(r"GNEWS_API_KEY\s*\| MISSING", out) and "Missing: GNEWS_API_KEY" in out
    assert vk.main(["--only", "COHERE_API_KEY", "--strict"]) == 1


def test_verify_keys_flags_an_anonymous_pollinations_token(monkeypatch, capsys):
    """A 200 is not proof: the reply's user_tier says whether the token counts."""
    vk = _load("scripts/verify_keys.py", "verify_keys_t")
    for name in vk.SECRETS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("POLLINATIONS_API_KEY", "0" * 32 + ".faketoken")
    monkeypatch.setattr(vk.requests, "post", lambda *a, **k: Resp(
        200, {"user_tier": "anonymous", "choices": [{"message": {"content": "OK"}}]}))
    monkeypatch.setattr(vk.requests, "get", _no_network)
    assert vk.main(["--only", "POLLINATIONS_API_KEY"]) == 0
    out = capsys.readouterr().out
    assert re.search(r"POLLINATIONS_API_KEY\s*\| WARN\s*\| 200", out)
    assert "anonymous" in out


def test_verify_keys_flags_a_zero_balance_siliconflow_account(monkeypatch, capsys):
    """Catalogue 200 + chat 402 = valid key, empty wallet."""
    vk = _load("scripts/verify_keys.py", "verify_keys_t")
    for name in vk.SECRETS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("SILICONFLOW_API_KEY", "sk-fakesiliconflowkey")

    def fake_get(url, **k):
        return Resp(200, {"data": [{"id": "Qwen/Qwen3.5-9B"}] * 79})

    def fake_post(url, **k):
        return Resp(402, {"code": 30001, "message": "Sorry, your account balance is insufficient"})

    monkeypatch.setattr(vk.requests, "get", fake_get)
    monkeypatch.setattr(vk.requests, "post", fake_post)
    assert vk.main(["--only", "SILICONFLOW_API_KEY"]) == 0
    out = capsys.readouterr().out
    assert re.search(r"SILICONFLOW_API_KEY\s*\| WARN\s*\| 402", out)
    assert "balance is 0" in out


def test_verify_keys_workflow_is_manual_read_only_and_explicit():
    # Plain-text checks: CI has no PyYAML.
    text = (ROOT / ".github/workflows/verify-keys.yml").read_text()
    on_block = text.split("\non:", 1)[1].split("\n\n", 1)[0]
    assert "workflow_dispatch" in on_block
    assert not re.search(r"^\s+(push|pull_request|schedule|workflow_run)\s*:", on_block, re.M)
    assert re.search(r"^permissions:\n  contents: read\n", text, re.M)
    group = re.search(r"^concurrency:\n  group: (\S+)", text, re.M).group(1)
    assert group == "verify-keys" and group != "current-affairs-pipeline"
    assert "toJSON(secrets)" not in text
    vk = _load("scripts/verify_keys.py", "verify_keys_wf")
    for name in vk.SECRETS:
        assert "%s: ${{ secrets.%s }}" % (name, name) in text, name


def test_pipeline_workflows_pass_every_key():
    keys = ("NEWSDATA_API_KEY", "JINA_API_KEY", "GNEWS_API_KEY", "SERPER_API_KEY", "COHERE_API_KEY",
            "LL7_API_KEY", "HUGGINGFACE_API_KEY", "GROQ_API_KEY", "GEMINI_API_KEY",
            "MISTRAL_API_KEY", "OPENROUTER_API_KEY", "NVIDIA_API_KEY",
            "POLLINATIONS_API_KEY", "SILICONFLOW_API_KEY",
            "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "ADMIN_ID")
    for wf in ("daily", "weekly", "monthly"):
        text = (ROOT / f".github/workflows/{wf}.yml").read_text()
        for key in keys:
            assert "%s: ${{ secrets.%s }}" % (key, key) in text, (wf, key)


# Removed on 2026-11-03 (cerebras/sambanova/cloudflare/deepseek — no free access
# on those keys) and on 2026-11-10 (ollama/openai — dead keys: 402 no balance on
# both, removed at the owner's request). This guard is the only place in the repo
# that may still name them. "openai" cannot be part of the regex: Groq serves
# `openai/gpt-oss-*` model ids and the generic provider is called
# "generic-openai", so the OpenAI *secret* names are asserted separately below.
_REMOVED_PROVIDERS = re.compile(r"cerebras|sambanova|cloudflare|deepseek|ollama", re.I)
_REMOVED_SECRETS = re.compile(r"OPENAI_API_KEY|OPENAI_BASE_URL|DEEPSEEK_API_KEY|OLLAMA_API_KEY", re.I)


def test_removed_providers_are_gone_everywhere():
    removed = {"cerebras", "sambanova", "cloudflare", "deepseek", "ollama", "openai"}
    assert not removed & set(ai_router._PREFERRED_MODELS)
    assert not removed & set(ai_router._KEY_POOL_VARS)
    this = Path(__file__).resolve()
    hits = []
    for sub in ("pipeline", "agents", "scripts", "tests", "docs", ".github"):
        for path in (ROOT / sub).rglob("*"):
            if path.is_file() and path.suffix in {".py", ".yml", ".yaml", ".md"} and path.resolve() != this:
                text = path.read_text(encoding="utf-8", errors="ignore")
                if _REMOVED_PROVIDERS.search(text) or _REMOVED_SECRETS.search(text):
                    hits.append(str(path.relative_to(ROOT)))
    env_example = (ROOT / ".env.example").read_text()
    if _REMOVED_PROVIDERS.search(env_example) or _REMOVED_SECRETS.search(env_example):
        hits.append(".env.example")
    assert not hits, hits


def test_removed_provider_env_vars_no_longer_build_a_provider(monkeypatch):
    """Even with the dead secrets present in the environment, no provider appears."""
    monkeypatch.setenv("OPENAI_API_KEY", OPENAI_STYLE)
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("OLLAMA_API_KEY", "fake-local-key")
    monkeypatch.setenv("OLLAMA_BASE_URL", "https://ollama.com")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-fake-deepseek")
    assert ai_router._build_default_providers() == []


# --------------------------------------------------------------------------- #
# Watchdog
# --------------------------------------------------------------------------- #
def _wd(tmp_path, monkeypatch, jobs, records):
    monkeypatch.setattr(main, "ROOT", tmp_path)
    monkeypatch.setattr(main, "JOBS_STATE_PATH", tmp_path / "state/jobs.json")
    write_json_atomic(main.JOBS_STATE_PATH, jobs)
    write_json_atomic(tmp_path / "state/published_events.json", {"records": records})


def test_watchdog_does_not_fail_for_an_edition_already_published(tmp_path, monkeypatch):
    now = datetime.now(timezone.utc).isoformat()
    jobs = {"daily_2026-11-01": {"status": "failed", "run_attempts": 2, "updated_at": now,
                                 "failed_stage": "22_telegram_publisher"}}
    records = {"a": {"job_id": "daily_2026-11-01", "status": "success", "message_id": 176},
               "b": {"job_id": "daily_2026-11-01", "status": "blocked_revision"}}
    _wd(tmp_path, monkeypatch, jobs, records)
    assert main.watchdog() == 0
    plan = json.loads((tmp_path / "recovery_plan.json").read_text())
    assert plan["actions"] == [] and plan["manual_attention"] == []
    assert plan["resolved"][0]["job_id"] == "daily_2026-11-01"


def test_watchdog_still_fails_closed_for_uncertain_send_and_honours_ack(tmp_path, monkeypatch):
    now = datetime.now(timezone.utc).isoformat()
    jobs = {"monthly_2026-11-01": {"status": "failed", "run_attempts": 6, "updated_at": now},
            "daily_2026-11-02": {"status": "failed", "run_attempts": 1, "updated_at": now}}
    records = {"u": {"job_id": "daily_2026-11-02", "status": "uncertain"}}
    _wd(tmp_path, monkeypatch, jobs, records)
    monkeypatch.delenv("ALP_WATCHDOG_ACK", raising=False)
    assert main.watchdog() == 2
    monkeypatch.setenv("ALP_WATCHDOG_ACK", "monthly_2026-11-01, daily_2026-11-02")
    assert main.watchdog() == 0


def test_watchdog_still_triggers_recovery_next_to_a_legacy_manual_job(tmp_path, monkeypatch):
    now = datetime.now(timezone.utc).isoformat()
    jobs = {"monthly_2026-11-01": {"status": "failed", "run_attempts": 6, "updated_at": now},
            "daily_2026-11-04": {"status": "failed", "run_attempts": 1, "updated_at": now}}
    _wd(tmp_path, monkeypatch, jobs, {})
    assert main.watchdog() == 1
    plan = json.loads((tmp_path / "recovery_plan.json").read_text())
    assert plan["actions"] == [{"job_id": "daily_2026-11-04", "action": "retry"}]
