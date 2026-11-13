"""The AI layer must never break the daily run (audit 2026-11-03, run 41573515743).

Offline: every provider call is a stub; no real credentials or network.
"""
from __future__ import annotations

import importlib.util
import json
import logging
import sys
import time
from pathlib import Path

import pytest
import requests

from pipeline import ai_router, ai_translator

ROOT = Path(__file__).resolve().parents[1]
FT = ai_router.FailureType

_ALL_PROVIDER_ENV = (
    "GEMINI_API_KEY", "GOOGLE_API_KEY", "GROQ_API_KEY",
    "LLM_API_URL", "LLM_API_KEY", "OPENROUTER_API_KEY", "MISTRAL_API_KEY", "NVIDIA_API_KEY",
    "COHERE_API_KEY", "LL7_API_KEY", "LLM7_API_KEY", "HUGGINGFACE_API_KEY", "HF_TOKEN",
    "POLLINATIONS_API_KEY", "POLLINATIONS_BASE_URL", "POLLINATIONS_MODEL",
    "SILICONFLOW_API_KEY", "SILICONFLOW_BASE_URL", "SILICONFLOW_MODEL",
)


def _clear_env(monkeypatch):
    for var in _ALL_PROVIDER_ENV:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ALP_MODEL_AUTO_DISCOVERY", "0")


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


def _new_stage():
    """Simulate the next stage subprocess: in-memory state gone, health file kept."""
    ai_router._HEALTH_LOADED[0] = None


# --------------------------------------------------------------------------- #
# Dead / paid providers
# --------------------------------------------------------------------------- #
def test_402_is_skipped_for_the_rest_of_the_run_across_stages(monkeypatch):
    calls = []
    paid = ai_router.Provider(name="paidco", url="https://p/chat/completions", key="k", model="m", priority=1)
    _use(monkeypatch, [paid])

    def fake(provider, *a, **k):
        calls.append(provider.name)
        return None, ai_router._classify_error(402, "Insufficient Balance")

    monkeypatch.setattr(ai_router, "_call_provider", fake)
    assert ai_router.route("first") is None
    assert calls == ["paidco"]

    _new_stage()
    fresh = ai_router.Provider(name="paidco", url="https://p/chat/completions", key="k", model="m")
    _use(monkeypatch, [fresh])
    assert ai_router.route("second") is None
    assert calls == ["paidco"]  # not called again in the "next stage"
    assert ai_router.blocked_until("paidco") - time.time() > 3600


def test_repeated_timeouts_park_provider_for_long_and_persist(monkeypatch):
    calls = []
    slow = ai_router.Provider(name="slowco", url="https://s/chat/completions", key="k", model="m")
    _use(monkeypatch, [slow])

    def fake(provider, *a, **k):
        calls.append(1)
        return None, FT.TIMEOUT

    monkeypatch.setattr(ai_router, "_call_provider", fake)
    ai_router.route("a")
    ai_router.route("b")
    assert len(calls) == ai_router.TRANSIENT_STRIKES
    ai_router.route("c")
    assert len(calls) == ai_router.TRANSIENT_STRIKES
    _new_stage()
    parked = ai_router.blocked_until("slowco") - time.time()
    assert parked > ai_router.PROVIDER_TIMEOUT_COOLDOWN - 60
    # 2026-11-13: the park must also stay *shorter than a run*, or one hung
    # provider is lost for the whole edition (nvidia/llm7 were out for 30 min).
    assert parked <= ai_router.PROVIDER_TIMEOUT_COOLDOWN


def test_repeated_rate_limits_never_park_a_provider_for_the_whole_run(monkeypatch):
    """llm7 was the fleet's biggest contributor and 429'd into a 1800s park."""
    p = ai_router.Provider(name="busyco", url="https://b/chat/completions", key="k", model="m")
    _use(monkeypatch, [p])
    monkeypatch.setattr(ai_router, "_call_provider", lambda provider, *a, **k: (None, FT.RATE_LIMIT))
    for probe in "abcdef":                      # escalate the 429 counter hard
        ai_router.route(probe)
    parked = ai_router.blocked_until("busyco") - time.time()
    assert parked <= ai_router.RATE_LIMIT_MAX_COOLDOWN
    assert ai_router.RATE_LIMIT_MAX_COOLDOWN <= 600   # run-scale, not day-scale


def test_requests_timeout_is_classified_as_timeout(monkeypatch):
    p = ai_router.Provider(name="x", url="https://x/chat/completions", key="k", model="m")

    def post(*a, **k):
        raise requests.Timeout("slow")

    monkeypatch.setattr(requests, "post", post)
    assert ai_router._call_provider(p, "hi", "general") == (None, FT.TIMEOUT)


# --------------------------------------------------------------------------- #
# 429 handling
# --------------------------------------------------------------------------- #
def test_retry_after_header_and_gemini_retry_delay_are_parsed():
    assert ai_router.parse_retry_after({"retry-after": "42"}) == 42
    assert ai_router.parse_retry_after({}, '{"error":{"details":[{"retryDelay": "37s"}]}}') == 37
    assert ai_router.parse_retry_after(None, "") is None


def test_429_honours_retry_after_and_escalates(monkeypatch):
    p = ai_router.Provider(name="rl", url="https://r/chat/completions", key="k", model="m")
    _use(monkeypatch, [p])
    ai_router.report_failure("rl", FT.RATE_LIMIT, retry_after=600, provider=p)
    assert 590 < ai_router.blocked_until("rl") - time.time() <= 600
    ai_router._HEALTH["blocks"].clear()
    ai_router._HEALTH["strikes"].clear()
    ai_router.report_failure("rl", FT.RATE_LIMIT, provider=p)
    first = ai_router.blocked_until("rl") - time.time()
    ai_router._HEALTH["blocks"].clear()
    ai_router.report_failure("rl", FT.RATE_LIMIT, provider=p)
    second = ai_router.blocked_until("rl") - time.time()
    assert second > first * 1.8  # repeated 429s back off harder (no hammering)
    ai_router.report_success("rl", p)
    assert ai_router._HEALTH["strikes"].get("rl:429") is None


def test_429_rotates_to_next_model_of_same_provider(monkeypatch):
    groq = ai_router.Provider(name="groq", url="https://g/chat/completions", key="k",
                              model="openai/gpt-oss-120b", per_model_quota=True,
                              models=["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"])
    other = ai_router.Provider(name="other", url="https://o/chat/completions", key="k", model="m", priority=200)
    _use(monkeypatch, [groq, other])
    seen = []

    def fake(provider, *a, **k):
        seen.append((provider.name, provider.model))
        if provider.model == "openai/gpt-oss-120b":
            return None, FT.RATE_LIMIT
        return "ok", None

    monkeypatch.setattr(ai_router, "_call_provider", fake)
    assert ai_router.route("hello") == "ok"
    assert seen == [("groq", "openai/gpt-oss-120b"), ("groq", "openai/gpt-oss-20b")]
    assert ai_router.is_blocked("groq::openai/gpt-oss-120b")
    assert not ai_router.is_blocked("groq")


def test_all_models_rate_limited_cools_down_the_provider(monkeypatch):
    gem = ai_router.Provider(name="gemini", url="https://g", key="k", model="a",
                             per_model_quota=True, models=["a", "b"])
    _use(monkeypatch, [gem])
    seen = []
    monkeypatch.setattr(ai_router, "_call_provider",
                        lambda provider, *a, **k: (seen.append(provider.model), (None, FT.RATE_LIMIT))[1])
    assert ai_router.route("x") is None
    assert seen == ["a", "b"]
    assert ai_router.is_blocked("gemini")
    assert ai_router.route("y") is None
    assert seen == ["a", "b"]  # no hammering while cooled down


# --------------------------------------------------------------------------- #
# Client-side throttling
# --------------------------------------------------------------------------- #
def test_min_interval_spaces_requests(monkeypatch):
    p = ai_router.Provider(name="mistral", url="https://m/chat/completions", key="k", model="m",
                           min_interval=0.3)
    stamps = []
    p.throttle()
    stamps.append(time.time())
    p.throttle()
    stamps.append(time.time())
    assert stamps[1] - stamps[0] >= 0.25


def test_daily_cap_is_persisted_across_stages(monkeypatch):
    p = ai_router.Provider(name="openrouter", url="https://o/chat/completions", key="k", model="m",
                           rpm_limit=20, rpd_limit=2)
    _use(monkeypatch, [p])
    calls = []
    monkeypatch.setattr(ai_router, "_call_provider",
                        lambda provider, *a, **k: (calls.append(1), ("ok", None))[1])
    assert ai_router.route("1") == "ok"
    assert ai_router.route("2") == "ok"
    _new_stage()
    fresh = ai_router.Provider(name="openrouter", url="https://o/chat/completions", key="k", model="m",
                               rpm_limit=20, rpd_limit=2)
    _use(monkeypatch, [fresh])
    assert ai_router.route("3") is None
    assert len(calls) == 2


def test_builder_sets_free_tier_limits(monkeypatch):
    _clear_env(monkeypatch)
    for name in ("GROQ", "MISTRAL", "OPENROUTER", "GEMINI"):
        monkeypatch.setenv(f"{name}_API_KEY", "k")
    providers = {p.name: p for p in ai_router._build_default_providers()}
    assert providers["groq"].per_model_quota and providers["groq"].rpd_limit == 1000
    assert providers["groq"].models == list(ai_router._PREFERRED_MODELS["groq"])
    assert providers["gemini"].per_model_quota and len(providers["gemini"].models) > 1
    assert providers["mistral"].min_interval >= 1.0
    assert (providers["openrouter"].rpm_limit, providers["openrouter"].rpd_limit) == (20, 50)


# --------------------------------------------------------------------------- #
# Verified models (2026-11-03)
# --------------------------------------------------------------------------- #
def test_nvidia_auto_is_the_vision_model_only_and_never_discovers_others(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("NVIDIA_API_KEY", "k")
    monkeypatch.setenv("NVIDIA_MODEL", "auto")
    live = ["openai/gpt-oss-20b", "meta/llama-guard-4-12b", "meta/llama-3.1-8b-instruct",
            "nvidia/nemotron-3-super-120b-a12b", "meta/llama-3.2-90b-vision-instruct"]
    monkeypatch.setattr(ai_router, "_live_model_ids", lambda p: live)
    (nv,) = ai_router._build_default_providers()
    assert nv.model == "meta/llama-3.2-90b-vision-instruct"
    assert nv.models == ["meta/llama-3.2-90b-vision-instruct"]
    assert "openai/gpt-oss-20b" in ai_router._RETIRED_MODELS["nvidia"]
    # Even with the vision model excluded, discovery picks nothing else.
    assert ai_router._choose_live_model(nv, live, {"meta/llama-3.2-90b-vision-instruct"}) is None
    assert ai_router.request_timeout("nvidia") == 40


def test_llm7_is_third_with_45s_timeout_and_60_call_cap(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("ALP_MODEL_AUTO_DISCOVERY", "0")
    for var in ("GROQ_API_KEY", "GEMINI_API_KEY", "LL7_API_KEY", "MISTRAL_API_KEY"):
        monkeypatch.setenv(var, "k")
    providers = ai_router._build_default_providers()
    assert [p.name for p in providers] == ["groq", "gemini", "llm7", "mistral"]
    llm7 = providers[2]
    assert llm7.model == "default" and llm7.models == ["default", "fast"] and llm7.rpd_limit == 60
    assert ai_router.request_timeout("llm7") == 45


def test_first_models_are_the_verified_ones(monkeypatch):
    pm = ai_router._PREFERRED_MODELS
    assert pm["groq"] == ("openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b")
    assert pm["gemini"][0] == "gemini-3.5-flash-lite" and "gemini-2.5-flash-lite" not in pm["gemini"]
    assert pm["cohere"][0] == "command-r7b-12-2024"
    # Verified 2026-11-10: pollinations serves "openai" on this token (its
    # catalogue advertises only "openai-fast"), siliconflow ids all exist.
    assert pm["pollinations"][0] == "openai"
    assert pm["siliconflow"][0] == "Qwen/Qwen3.5-9B"


def test_siliconflow_is_last_because_it_bills_per_token(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("ALP_MODEL_AUTO_DISCOVERY", "0")
    monkeypatch.setenv("SILICONFLOW_API_KEY", "sk-fakesiliconflow")
    monkeypatch.setenv("NVIDIA_API_KEY", "k")
    providers = ai_router._build_default_providers()
    assert [p.name for p in providers] == ["nvidia", "siliconflow"]
    assert providers[-1].model == "Qwen/Qwen3.5-9B"
    assert providers[-1].url == "https://api.siliconflow.com/v1/chat/completions"


def test_pollinations_is_capped_because_the_token_answers_anonymous(monkeypatch):
    """Anonymous tier = 1 reply / 45 s per IP → keep the per-run cap small."""
    _clear_env(monkeypatch)
    monkeypatch.setenv("ALP_MODEL_AUTO_DISCOVERY", "0")
    monkeypatch.setenv("POLLINATIONS_API_KEY", "0" * 32 + ".fakesecret")
    provider = ai_router._build_default_providers()[0]
    assert provider.name == "pollinations"
    assert provider.rpd_limit <= 40 and provider.min_interval >= 1.0
    # Catalogue discovery is off: it advertises a model this token cannot use.
    assert "pollinations" in ai_router._NO_DISCOVERY
    assert "pollinations" in ai_router._PREFERRED_ONLY


# --------------------------------------------------------------------------- #
# Stage 00 health check feeds later stages and never kills the run
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("code,status", [(402, "credit_error"), (403, "auth_error")])
def test_health_check_classifies_credit_and_forbidden(monkeypatch, code, status):
    setup = _load("agents/00_model_orchestrator.py", f"orch_{code}")
    monkeypatch.setattr(setup, "SKIP_HEALTHCHECK", False)

    class Response:
        status_code = code

    monkeypatch.setattr(requests, "post", lambda *a, **k: Response())
    assert setup.health_check({"name": "x", "url": "https://x", "key": "k", "model": "m"})["status"] == status


def test_stage00_all_failed_is_not_fatal_and_seeds_cooldowns(monkeypatch, tmp_path):
    setup = _load("agents/00_model_orchestrator.py", "orch_all_failed")
    monkeypatch.setattr(setup, "STATUS_FILE", tmp_path / "model_status.json")
    monkeypatch.setattr(setup, "load_keys", lambda: [
        {"name": "siliconflow", "url": "u", "key": "k", "model": "m", "priority": 78, "env_used": "S"},
        {"name": "nvidia", "url": "u", "key": "k", "model": "m", "priority": 25, "env_used": "N"},
    ])
    statuses = {"siliconflow": {"status": "credit_error", "detail": "402"},
                "nvidia": {"status": "timeout", "detail": "15s"}}
    monkeypatch.setattr(setup, "health_check", lambda p: statuses[p["name"]])
    assert setup.main() == 0
    report = json.loads((tmp_path / "model_status.json").read_text())
    assert report["status"] == "all_failed"
    assert ai_router.is_blocked("siliconflow") and ai_router.is_blocked("nvidia")


def test_stage00_empty_reasoning_reply_counts_as_reachable(monkeypatch, tmp_path):
    setup = _load("agents/00_model_orchestrator.py", "orch_reachable")
    monkeypatch.setattr(setup, "STATUS_FILE", tmp_path / "model_status.json")
    monkeypatch.setattr(setup, "load_keys", lambda: [
        {"name": "groq", "url": "u", "key": "k", "model": "m", "priority": 20, "env_used": "G"}])
    monkeypatch.setattr(setup, "health_check", lambda p: {"status": "malformed", "detail": "empty"})
    assert setup.main() == 0
    assert json.loads((tmp_path / "model_status.json").read_text())["status"] == "ok"
    assert not ai_router.is_blocked("groq")


# --------------------------------------------------------------------------- #
# Stage AI deadline (ALP_STAGE_TIMEOUT=900 must never be hit because of AI)
# --------------------------------------------------------------------------- #
def test_stage_ai_budget_stops_calls_and_clips_timeouts(monkeypatch):
    p = ai_router.Provider(name="p", url="https://p/chat/completions", key="k", model="m")
    _use(monkeypatch, [p])
    calls = []
    monkeypatch.setattr(ai_router, "_call_provider",
                        lambda provider, *a, **k: (calls.append(1), ("ok", None))[1])
    monkeypatch.setenv("ALP_STAGE_TIMEOUT", "900")
    monkeypatch.setenv("ALP_STAGE_STARTED_AT", str(time.time() - 640))  # 70% = 630s used
    assert ai_router.route("late call") is None
    assert calls == []
    monkeypatch.setenv("ALP_STAGE_STARTED_AT", str(time.time() - 620))
    assert ai_router.clip_timeout(60) <= 10.5
    assert ai_router.route("in budget") == "ok"


def test_translator_respects_stage_budget_and_shared_health(monkeypatch):
    providers = [{"name": n, "url": f"https://{n}/chat/completions", "key": "k", "model": "m"}
                 for n in ("gemini", "groq")]
    monkeypatch.setattr(ai_translator, "_PROVIDERS_CACHE", providers)
    ai_translator.clear_cache()
    ai_translator._RATE_LIMITED_PROVIDERS.clear()
    attempted = []

    def call(provider, system, user):
        attempted.append(provider["name"])
        return "किसानों को सहायता मिलेगी।"

    monkeypatch.setattr(ai_translator, "_call_provider", call)
    ai_router.block("gemini", 600, "cooled down by an earlier stage")
    assert ai_translator.translate_content("Farmers receive support.")["provider"] == "groq"
    assert attempted == ["groq"]

    monkeypatch.setenv("ALP_AI_STAGE_BUDGET", "1")
    monkeypatch.setenv("ALP_STAGE_STARTED_AT", str(time.time() - 5))
    res = ai_translator.translate_content("Another farm update.")
    assert res["passed"] is False and attempted == ["groq"]


def test_translator_timeout_is_not_retried_and_cools_down(monkeypatch):
    providers = [{"name": n, "url": f"https://{n}/chat/completions", "key": "k", "model": "m"}
                 for n in ("nvidia", "groq")]
    monkeypatch.setattr(ai_translator, "_PROVIDERS_CACHE", providers)
    ai_translator.clear_cache()
    attempted = []

    def call(provider, system, user):
        attempted.append(provider["name"])
        if provider["name"] == "nvidia":
            raise ai_translator.ProviderRequestFailed("request timed out", timeout=True)
        return "किसानों को सहायता मिलेगी।"

    monkeypatch.setattr(ai_translator, "_call_provider", call)
    monkeypatch.setattr(ai_translator.time, "sleep", lambda s: pytest.fail("timeout must not back off"))
    ai_translator.translate_content("Farmers receive support.")
    ai_translator.translate_content("Farmers receive more support.")
    assert attempted == ["nvidia", "groq", "nvidia", "groq"]
    ai_translator.translate_content("Farmers receive even more support.")
    assert attempted[-1] == "groq" and attempted.count("nvidia") == 2  # cooled down after 2 strikes


def test_translator_stops_after_repeated_validation_failures(monkeypatch):
    providers = [{"name": n, "url": f"https://{n}/chat/completions", "key": "k", "model": "m"}
                 for n in ("a", "b", "c", "d")]
    monkeypatch.setattr(ai_translator, "_PROVIDERS_CACHE", providers)
    ai_translator.clear_cache()
    attempted = []
    monkeypatch.setattr(ai_translator, "_call_provider",
                        lambda p, s, u: (attempted.append(p["name"]), "English only")[1])
    assert ai_translator.translate_content("AWARDS night for farmers")["passed"] is False
    assert attempted == ["a", "b"]


# --------------------------------------------------------------------------- #
# All providers down: fail closed, never ship English as Hindi
# --------------------------------------------------------------------------- #
def _run_stage12(monkeypatch, tmp_path, items):
    mod = _load("agents/12_content_editor.py", f"content_editor_{len(items)}")
    import pipeline.agent_context as agent_context
    import pipeline.artifacts as artifacts
    import pipeline.content as content
    import pipeline.state as state

    selected = tmp_path / "selected.json"
    selected.write_text(json.dumps({"items": []}))
    written = {}

    class Ctx:
        job_id, job_type, job_date = "daily_2026-11-03", "daily", "2026-11-03"

        def find_input(self, kind):
            return str(selected)

        def output_path(self, kind):
            return tmp_path / f"{kind}.json"

    monkeypatch.setattr(agent_context, "get_context", lambda: Ctx())
    monkeypatch.setattr(artifacts, "read_news_items", lambda path: [{"event_id": i["event_id"]} for i in items])
    monkeypatch.setattr(content, "build_content",
                        lambda its, job: {"items": [dict(i) for i in items], "translation_stats": {}})
    monkeypatch.setattr(content, "refresh_content_summaries", lambda c: None)
    monkeypatch.setattr(state, "write_json_atomic", lambda path, data: written.update(data=data))
    monkeypatch.setenv("DRY_RUN", "0")
    monkeypatch.setenv("ALP_ALLOW_FALLBACK_TRANSLATION", "0")
    monkeypatch.setenv("MIN_VERIFIED_COUNT", "1")
    return mod.main(), written.get("data")


def test_stage12_fails_closed_when_no_story_has_validated_hindi(monkeypatch, tmp_path):
    items = [{"event_id": f"e{i}", "needs_review": True, "translation_incomplete": True} for i in range(3)]
    rc, data = _run_stage12(monkeypatch, tmp_path, items)
    assert rc == 1 and data is None


def test_stage12_still_unflags_complete_hindi_but_never_untranslated(monkeypatch, tmp_path):
    items = [{"event_id": "ok", "needs_review": True, "translation_incomplete": False},
             {"event_id": "en", "needs_review": True, "translation_incomplete": True}]
    rc, data = _run_stage12(monkeypatch, tmp_path, items)
    assert rc == 0
    assert [i["event_id"] for i in data["items"]] == ["ok"]
    assert data["items"][0]["needs_review"] is False


# --------------------------------------------------------------------------- #
# Observability: a timed-out stage keeps its output; failures alert the admin
# --------------------------------------------------------------------------- #
def test_stage_timeout_keeps_partial_output(monkeypatch, tmp_path):
    import main
    script = tmp_path / "slow_stage.py"
    script.write_text("import time\nprint('reached translation batch 7', flush=True)\ntime.sleep(30)\n")
    monkeypatch.setattr(main, "ROOT", tmp_path)
    monkeypatch.setattr(main, "STAGE_TIMEOUT_SECONDS", 2)
    monkeypatch.setattr(main, "MAX_RETRIES", 0)
    ok, msg = main.run_stage("12_content_editor", str(script), True, {"ALP_JOB_ID": "daily_t"})
    assert not ok and "timeout" in msg
    log = (tmp_path / "logs" / "stages" / "daily_t" / "12_content_editor.log").read_text()
    assert "TIMEOUT" in log and "reached translation batch 7" in log


def test_failure_alert_message(monkeypatch, tmp_path):
    alert = _load("scripts/alert_failure.py", "alert_failure_t")
    (tmp_path / "state").mkdir()
    (tmp_path / "state" / "jobs.json").write_text(json.dumps({"jobs": {"daily_x": {
        "status": "failed", "failed_stage": "12_content_editor", "error": "AI translation unavailable"}}}))
    (tmp_path / "logs" / "ai_health").mkdir(parents=True)
    (tmp_path / "logs" / "ai_health" / "daily_x.json").write_text(json.dumps(
        {"blocks": {"openrouter": {"until": time.time() + 100, "reason": "auth/credit error"}}}))
    monkeypatch.setattr(alert, "ROOT", tmp_path)
    monkeypatch.setenv("GITHUB_REPOSITORY", "o/r")
    monkeypatch.setenv("GITHUB_RUN_ID", "1")
    text = alert.build_message("daily_x", "Daily")
    assert "12_content_editor" in text and "openrouter" in text and "/o/r/actions/runs/1" in text
    sent = []
    monkeypatch.setattr("pipeline.telegram_api.alert_admin", lambda t: sent.append(t) or True)
    assert alert.main(["--job-id", "daily_x"]) == 0 and sent


def test_mcq_llm_pass_does_not_retry_when_no_provider_answers():
    from pipeline.mcq_schema import generate_llm_mcqs
    calls = []
    out = generate_llm_mcqs([{"event_id": "e1", "headline_en": "x"}], lambda i: "src",
                            route=lambda *a, **k: calls.append(1), attempts=3)
    assert out == {} and calls == [1]


# --------------------------------------------------------------------------- #
# 2026-11-13: all-provider cooldown must name itself and offer a recovery wait
# --------------------------------------------------------------------------- #
def test_all_cooled_down_error_names_the_cooldowns(monkeypatch, caplog):
    """Eight failed runs logged "Last error: None" — the reason must survive."""
    p = ai_router.Provider(name="onlyco", url="https://o/chat/completions", key="k", model="m")
    _use(monkeypatch, [p])
    p.mark_disabled("rate limited", 300)
    with caplog.at_level(logging.ERROR, logger="pipeline.ai_router"):
        assert ai_router.route("x") is None
    assert "all providers cooled down" in caplog.text
    assert "onlyco" in caplog.text and "rate limited" in caplog.text
    assert "Last error: None" not in caplog.text


def test_recovery_wait_is_none_while_a_provider_can_serve(monkeypatch):
    ok = ai_router.Provider(name="okco", url="https://o", key="k", model="m")
    _use(monkeypatch, [ok])
    assert ai_router.all_providers_recovery_wait() is None


def test_recovery_wait_reports_the_soonest_expiry(monkeypatch):
    far = ai_router.Provider(name="farco", url="https://f", key="k", model="m")
    near = ai_router.Provider(name="nearco", url="https://n", key="k", model="m")
    _use(monkeypatch, [far, near])
    far.mark_disabled("repeated timeouts", 1800)
    near.mark_disabled("rate limited", 90)
    wait = ai_router.all_providers_recovery_wait()
    assert wait is not None and 60 < wait <= 90


# --------------------------------------------------------------------------- #
# 2026-11-13: content builder must ride out a translation storm
# --------------------------------------------------------------------------- #
def _storm_items(n):
    return [{"event_id": f"e{i}", "headline_en": f"Scheme {i} approved with Rs 500{i} Crore",
             "source_name": "PIB", "source_url": f"https://pib.gov.in/e{i}", "source_tier": "tier1",
             "category": "Agriculture", "raw_facts": f"Cabinet approved scheme {i}.",
             "pub_time_ist": None, "duplicate_count": 1, "is_verified": True,
             "provenance_verified": True, "verification_mode": "live"} for i in range(n)]


def test_content_builder_waits_out_a_translation_storm_and_retries(monkeypatch):
    from pipeline import content
    import time as _time

    slept = []
    monkeypatch.setattr(_time, "sleep", lambda s: slept.append(s))
    monkeypatch.setattr(ai_router, "all_providers_recovery_wait", lambda: 90.0)
    monkeypatch.setattr(ai_router, "ai_time_left", lambda: 600.0)

    storm = {"on": True}

    def fake_entry(it, stats):
        if storm["on"]:                              # storm: every translation falls back
            stats["untranslated"] += 1
            return {"event_id": it["event_id"], "translation_incomplete": True, "needs_review": True}
        stats["ai_passed"] += 1                      # recovered: validated Hindi
        return {"event_id": it["event_id"], "translation_incomplete": False, "needs_review": False}

    real_sleep = _time.sleep

    def fake_sleep(s):
        slept.append(s)
        storm["on"] = False                          # providers recover during the wait

    monkeypatch.setattr(_time, "sleep", fake_sleep)
    monkeypatch.setattr(content, "_build_entry", fake_entry)
    monkeypatch.setattr(content, "_prefill_headline_translation_cache", lambda items: None)
    monkeypatch.setattr(content, "_build_category_one_liners", lambda out: {})

    c = content.build_content(_storm_items(6), {"type": "daily"})
    assert slept == [90.0]                           # waited out the storm exactly once
    assert all(not it.get("translation_incomplete") for it in c["items"])
    assert c["translation_stats"]["ai_passed"] == 6  # whole batch salvaged


def test_content_builder_does_not_retry_when_translations_are_fine(monkeypatch):
    from pipeline import content
    import time as _time

    slept = []
    monkeypatch.setattr(_time, "sleep", lambda s: slept.append(s))
    monkeypatch.setattr(ai_router, "all_providers_recovery_wait", lambda: 90.0)
    monkeypatch.setattr(ai_router, "ai_time_left", lambda: 600.0)

    def good_entry(it, stats):
        stats["ai_passed"] += 1
        return {"event_id": it["event_id"], "translation_incomplete": False, "needs_review": False}

    monkeypatch.setattr(content, "_build_entry", good_entry)
    monkeypatch.setattr(content, "_prefill_headline_translation_cache", lambda items: None)
    monkeypatch.setattr(content, "_build_category_one_liners", lambda out: {})
    c = content.build_content(_storm_items(6), {"type": "daily"})
    assert not slept
    assert c["translation_stats"]["ai_failed"] == 0


def test_content_builder_ignores_a_couple_of_stragglers(monkeypatch):
    """Only a batch-wide storm justifies the wait; 1-2 stragglers do not."""
    from pipeline import content
    import time as _time

    slept = []
    monkeypatch.setattr(_time, "sleep", lambda s: slept.append(s))
    monkeypatch.setattr(ai_router, "all_providers_recovery_wait", lambda: 90.0)
    monkeypatch.setattr(ai_router, "ai_time_left", lambda: 600.0)

    def entry(it, stats):
        bad = it["event_id"] == "e0"
        stats["untranslated" if bad else "ai_passed"] += 1
        return {"event_id": it["event_id"], "translation_incomplete": bad, "needs_review": bad}

    monkeypatch.setattr(content, "_build_entry", entry)
    monkeypatch.setattr(content, "_prefill_headline_translation_cache", lambda items: None)
    monkeypatch.setattr(content, "_build_category_one_liners", lambda out: {})
    c = content.build_content(_storm_items(6), {"type": "daily"})
    assert not slept
    assert sum(1 for it in c["items"] if it["translation_incomplete"]) == 1
