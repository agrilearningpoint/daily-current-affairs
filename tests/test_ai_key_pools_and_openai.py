"""Tests for Phase 3 multi-key pools, OpenAI zero-token healthchecks, task routing, and observability."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from pipeline import ai_router, ai_usage

ROOT = Path(__file__).resolve().parents[1]

_POOL_VARS = (
    "GEMINI_API_KEY", "GOOGLE_API_KEY",
    "GEMINI_API_KEY_1", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3", "GEMINI_API_KEY_4",
    "GEMINI_API_KEY_5", "GEMINI_API_KEY_6", "GEMINI_API_KEY_7",
    "GROQ_API_KEY", "GROQ_API_KEY_1", "GROQ_API_KEY_2",
    "OPENAI_API_KEY", "OPENAI_API_KEY_1", "OPENAI_BASE_URL", "OPENAI_MODEL",
    "MISTRAL_API_KEY", "OPENROUTER_API_KEY", "NVIDIA_API_KEY",
    "COHERE_API_KEY", "LL7_API_KEY", "LLM7_API_KEY",
    "HUGGINGFACE_API_KEY", "HF_TOKEN",
    "POLLINATIONS_API_KEY", "SILICONFLOW_API_KEY",
    "LLM_API_KEY", "LLM_API_URL", "ALP_KEY_SCHEDULING",
)


@pytest.fixture(autouse=True)
def _clean_ai_env(monkeypatch):
    for var in _POOL_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ALP_MODEL_AUTO_DISCOVERY", "0")
    monkeypatch.setenv("ALP_AI_CALL_INTERVAL", "0")
    ai_router.reset()
    yield
    ai_router.reset()


def _load_script(rel: str, mod_name: str):
    spec = importlib.util.spec_from_file_location(mod_name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_pool_discovery_without_base_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY_3", "AIzaFakeSlot3Key000000000000000")
    monkeypatch.setenv("GEMINI_API_KEY_7", "AIzaFakeSlot7Key000000000000000")
    monkeypatch.setenv("GROQ_API_KEY_2", "gsk_fakeslot2_0000000000000000")
    monkeypatch.setenv("OPENAI_API_KEY_1", "sk-proj-fake-slot1-0000000000")

    providers = ai_router._build_default_providers()
    by_name = {p.name: p for p in providers}

    assert list(by_name["gemini"].key_slots) == ["gemini:GEMINI_API_KEY_3", "gemini:GEMINI_API_KEY_7"]
    assert by_name["gemini"].current_slot == "gemini:GEMINI_API_KEY_3"
    assert list(by_name["groq"].key_slots) == ["groq:GROQ_API_KEY_2"]
    assert list(by_name["openai"].key_slots) == ["openai:OPENAI_API_KEY_1"]
    assert by_name["openai"].current_slot == "openai:OPENAI_API_KEY_1"


def test_key_rotation_isolated_per_slot_and_bounded(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaFake0")
    monkeypatch.setenv("GEMINI_API_KEY_1", "AIzaFake1")
    monkeypatch.setenv("GEMINI_API_KEY_2", "AIzaFake2")
    monkeypatch.setenv("ALP_KEY_SCHEDULING", "round_robin")

    providers = ai_router._build_default_providers()
    gemini = next(p for p in providers if p.name == "gemini")
    gemini.models = [gemini.model]  # pin single model to test slot rotation
    monkeypatch.setattr(ai_router, "_PROVIDERS", [gemini])

    seen_keys: list[str] = []

    def _mock_call_provider(provider, prompt, task, needs_hindi=False, response_format=None, system_prompt=None):
        seen_keys.append(provider.key)
        if len(seen_keys) <= 2:
            return None, ai_router.FailureType.RATE_LIMIT
        ai_router._LAST.usage = {"prompt_tokens": 12, "completion_tokens": 5, "total_tokens": 17}
        return "verified-ok", None

    monkeypatch.setattr(ai_router, "_call_provider", _mock_call_provider)
    out = ai_router.route("hello", task="content_editing", fail_on_all=True)
    assert out == "verified-ok"
    assert seen_keys == ["AIzaFake0", "AIzaFake1", "AIzaFake2"]
    assert ai_router.is_blocked("gemini#slot:0")
    assert ai_router.is_blocked("gemini#slot:1")
    assert not ai_router.is_blocked("gemini#slot:2")


def test_gemini_shared_project_quota_marks_remaining_slots_cooled(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaFake0")
    monkeypatch.setenv("GEMINI_API_KEY_1", "AIzaFake1")
    monkeypatch.setenv("GEMINI_API_KEY_2", "AIzaFake2")
    monkeypatch.setenv("GEMINI_API_KEY_3", "AIzaFake3")

    providers = ai_router._build_default_providers()
    gemini = next(p for p in providers if p.name == "gemini")
    gemini.models = [gemini.model]  # pin single model to test slot rotation
    monkeypatch.setattr(ai_router, "_PROVIDERS", [gemini])

    def _all_429(provider, prompt, task, needs_hindi=False, response_format=None, system_prompt=None):
        return None, ai_router.FailureType.RATE_LIMIT

    monkeypatch.setattr(ai_router, "_call_provider", _all_429)
    out = ai_router.route("test shared quota", task="news_research", fail_on_all=False)
    assert out is None
    # 3 distinct slot 429s in 60s sets shared_quota flag and stops burning extra slots
    assert ai_router._HEALTH["shared_quota"].get("gemini") is True


def test_key_scheduling_least_used_vs_round_robin(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaFake0")
    monkeypatch.setenv("GEMINI_API_KEY_1", "AIzaFake1")
    providers = ai_router._build_default_providers()
    gemini = next(p for p in providers if p.name == "gemini")

    # Mark base key slot heavily used; slot 1 unused.
    slot0 = gemini.key_slots[0]
    slot1 = gemini.key_slots[1]
    for _ in range(5):
        ai_router._record_slot_call(slot0)

    monkeypatch.setenv("ALP_KEY_SCHEDULING", "least_used")
    next_slot_idx = ai_router._select_next_slot("gemini", gemini.key_slots, current_idx=0)
    assert next_slot_idx == 1

    monkeypatch.setenv("ALP_KEY_SCHEDULING", "round_robin")
    next_rr_idx = ai_router._select_next_slot("gemini", gemini.key_slots, current_idx=1)
    assert next_rr_idx == 0


def test_openai_two_key_rotation_and_zero_token_healthcheck(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-fake-0")
    monkeypatch.setenv("OPENAI_API_KEY_1", "sk-proj-fake-1")

    verify_keys = _load_script("scripts/verify_keys.py", "verify_keys_phase3")
    orchestrator = _load_script("agents/00_model_orchestrator.py", "stage00_phase3")

    methods_called: list[tuple[str, str]] = []

    class _Resp:
        def __init__(self, status_code: int, payload: dict):
            self.status_code = status_code
            self._payload = payload
            self.text = json.dumps(payload)
            self.headers = {}

        def json(self):
            return self._payload

    def _fake_get(url, headers=None, timeout=None, **kwargs):
        methods_called.append(("GET", url))
        return _Resp(200, {"data": [{"id": "gpt-4o-mini"}]})

    def _fake_post(*args, **kwargs):
        methods_called.append(("POST", str(args[0])))
        raise AssertionError("Healthcheck must NOT call completion POST endpoints")

    monkeypatch.setattr("requests.get", _fake_get)
    monkeypatch.setattr("requests.post", _fake_post)
    r0 = verify_keys.CHECKS["OPENAI_API_KEY"]()
    r1 = verify_keys.CHECKS["OPENAI_API_KEY_1"]()
    assert r0[0] == "OK"
    assert r1[0] == "OK"

    probe = orchestrator.health_check({"name": "openai", "key": "sk-proj-fake-0", "url": "https://api.openai.com/v1/chat/completions"})
    assert probe["status"] == "ok"
    assert all(m == "GET" for m, _ in methods_called)

    # Validate wrong key shape warning (sk-or prefix in OpenAI slot)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-or-v1-wrong-openrouter-key")
    problems = ai_router.unconfigured_notes()
    assert any("OPENAI_API_KEY" in p for p in problems)

    # Runtime two-key rotation
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-fake-0")
    monkeypatch.setenv("OPENAI_API_KEY_1", "sk-proj-fake-1")
    ai_router.reset()
    providers = ai_router._build_default_providers()
    openai_p = next(p for p in providers if p.name == "openai")
    monkeypatch.setattr(ai_router, "_PROVIDERS", [openai_p])
    seen = []

    def _openai_call(provider, prompt, task, needs_hindi=False, response_format=None, system_prompt=None):
        seen.append((provider.name, provider.current_slot, provider.key))
        if provider.key == "sk-proj-fake-0":
            return None, ai_router.FailureType.RATE_LIMIT
        ai_router._LAST.usage = {"prompt_tokens": 20, "completion_tokens": 8, "total_tokens": 28}
        return "openai-slot1-ok", None

    monkeypatch.setattr(ai_router, "_call_provider", _openai_call)
    res = ai_router.route("Verify agriculture fact", task="fact_verification", fail_on_all=True)
    assert res == "openai-slot1-ok"
    assert seen == [
        ("openai", "openai:OPENAI_API_KEY", "sk-proj-fake-0"),
        ("openai", "openai:OPENAI_API_KEY_1", "sk-proj-fake-1"),
    ]


def test_task_aware_routing_and_mcq_independence(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaFake")
    monkeypatch.setenv("GROQ_API_KEY", "gsk_fake")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-fake")
    monkeypatch.setenv("MISTRAL_API_KEY", "mistral_fake")

    providers = ai_router._build_default_providers()
    monkeypatch.setattr(ai_router, "_PROVIDERS", providers)

    mcq_verifiers = ai_router.providers_for_task("mcq_verification", exclude_providers={"gemini"})
    names = [p.name for p in mcq_verifiers]
    assert "gemini" not in names
    assert names[0] == "mistral"

    research_chain = [p.name for p in ai_router.providers_for_task("news_research")]
    assert research_chain[0] == "gemini"


def test_usage_and_provider_observability_files(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-fake")
    providers = ai_router._build_default_providers()
    openai_p = next(p for p in providers if p.name == "openai")
    monkeypatch.setattr(ai_router, "_PROVIDERS", [openai_p])

    def _mock_success(provider, prompt, task, needs_hindi=False, response_format=None, system_prompt=None):
        ai_router._LAST.usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
        return "done", None

    monkeypatch.setattr(ai_router, "_call_provider", _mock_success)
    out = ai_router.route("Summarize MSP", task="content_editing", fail_on_all=True)
    assert out == "done"

    ai_usage.update_provider_observability(providers=providers)

    usage_lines = ai_usage.usage_log_path().read_text(encoding="utf-8").strip().splitlines()
    assert len(usage_lines) == 1
    rec = json.loads(usage_lines[0])
    assert rec["provider"] == "openai"
    assert rec["total_tokens"] == 150
    assert isinstance(rec["latency_ms"], (int, float))
    assert rec["cost_usd"] >= 0.0

    health = json.loads(ai_usage.provider_health_path().read_text(encoding="utf-8"))
    summary = json.loads(ai_usage.provider_summary_path().read_text(encoding="utf-8"))
    assert "openai" in health["providers"]
    assert summary["totals"]["calls"] == 1
    assert summary["totals"]["total_tokens"] == 150
