"""Tests for universal auto free model rotation, slow API pacing, and overnight scheduling."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import main
from pipeline import ai_router, discovery_api, news_api_sources

FT = ai_router.FailureType


def _clear_ai_keys(monkeypatch):
    for key in (
        "GEMINI_API_KEY", "GOOGLE_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY", "NVIDIA_API_KEY",
        "MISTRAL_API_KEY", "COHERE_API_KEY", "LL7_API_KEY", "LLM7_API_KEY", "HUGGINGFACE_API_KEY",
        "HF_TOKEN", "POLLINATIONS_API_KEY", "SILICONFLOW_API_KEY", "LLM_API_KEY", "LLM_API_URL",
        "GEMINI_MODEL", "GROQ_MODEL", "OPENROUTER_MODEL", "NVIDIA_MODEL",
        "MISTRAL_MODEL", "COHERE_MODEL", "LLM7_MODEL", "HUGGINGFACE_MODEL",
    ):
        monkeypatch.delenv(key, raising=False)


def test_openrouter_prefers_free_router_skips_paid_and_rotates_on_429(monkeypatch):
    _clear_ai_keys(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-key")
    monkeypatch.setenv("OPENROUTER_MODEL", "auto")
    monkeypatch.setenv("ALP_MODEL_AUTO_DISCOVERY", "1")
    live = [
        "openai/gpt-4o",
        "meta-llama/llama-3.3-70b-instruct:free",
        "openrouter/free",
        "google/gemma-4-31b-it:free",
    ]
    monkeypatch.setattr(ai_router, "_live_model_ids", lambda p: live)

    (or_prov,) = ai_router._build_default_providers()
    assert or_prov.model == "openrouter/free"
    assert "openai/gpt-4o" not in or_prov.models
    assert "meta-llama/llama-3.3-70b-instruct:free" in or_prov.models

    seen: list[str] = []

    def fake_call(provider, *a, **kw):
        seen.append(provider.model)
        if provider.model == "openrouter/free":
            return None, FT.RATE_LIMIT
        return "ok-free-reply", None

    monkeypatch.setattr(ai_router, "_PROVIDERS", [or_prov])
    monkeypatch.setattr(ai_router, "_get_providers", lambda: [or_prov])
    monkeypatch.setattr(ai_router, "_within_budget", lambda: True)
    monkeypatch.setattr(ai_router, "_call_provider", fake_call)
    ai_router.clear_cache()

    assert ai_router.route("hello openrouter") == "ok-free-reply"
    assert seen[0] == "openrouter/free"
    assert len(seen) == 2
    assert seen[1].endswith(":free") or seen[1] in or_prov.models
    assert ai_router.is_blocked("openrouter::openrouter/free")
    assert not ai_router.is_blocked("openrouter")


def test_mistral_discovers_text_models_skips_vision_and_rotates_on_429(monkeypatch):
    _clear_ai_keys(monkeypatch)
    monkeypatch.setenv("MISTRAL_API_KEY", "mistral-test-key")
    monkeypatch.setenv("MISTRAL_MODEL", "auto")
    monkeypatch.setenv("ALP_MODEL_AUTO_DISCOVERY", "1")
    live = ["pixtral-12b-2409", "mistral-small-latest", "open-mistral-nemo"]
    monkeypatch.setattr(ai_router, "_live_model_ids", lambda p: live)

    (mis,) = ai_router._build_default_providers()
    assert mis.model == "mistral-small-latest"
    assert "pixtral-12b-2409" not in mis.models
    assert "open-mistral-nemo" in mis.models

    seen: list[str] = []

    def fake_call(provider, *a, **kw):
        seen.append(provider.model)
        if provider.model == "mistral-small-latest":
            return None, FT.RATE_LIMIT
        return "ok-mistral-reply", None

    monkeypatch.setattr(ai_router, "_PROVIDERS", [mis])
    monkeypatch.setattr(ai_router, "_get_providers", lambda: [mis])
    monkeypatch.setattr(ai_router, "_within_budget", lambda: True)
    monkeypatch.setattr(ai_router, "_call_provider", fake_call)
    ai_router.clear_cache()

    assert ai_router.route("hello mistral") == "ok-mistral-reply"
    assert seen == ["mistral-small-latest", "open-mistral-nemo"]
    assert ai_router.is_blocked("mistral::mistral-small-latest")
    assert not ai_router.is_blocked("mistral")


def test_discovery_service_paces_gnews_when_interval_set(monkeypatch):
    svc = discovery_api._Service("gnews", "GNEWS_API_KEY", default_budget=4, default_min_interval=12.0)
    monkeypatch.setenv("ALP_GNEWS_MIN_INTERVAL", "15")
    monkeypatch.delenv("ALP_DISCOVERY_NO_SLEEP", raising=False)

    now = [100.0]
    sleeps: list[float] = []

    def fake_monotonic():
        return now[0]

    def fake_sleep(secs: float):
        sleeps.append(secs)
        now[0] += secs

    monkeypatch.setattr(discovery_api.time, "monotonic", fake_monotonic)
    monkeypatch.setattr(discovery_api.time, "sleep", fake_sleep)

    svc.pace()
    now[0] += 2.0  # only 2s elapsed since first call -> should sleep 13s
    svc.pace()

    assert sleeps == [pytest.approx(13.0, abs=0.05)]


def test_topup_gnews_into_raw_merges_unique_wave_items(tmp_path, monkeypatch):
    monkeypatch.setenv("GNEWS_API_KEY", "gnews-test-key")
    discovery_api.GNEWS.reset()
    try:
        raw_path = tmp_path / "daily_2026-11-28.json"
        raw_path.write_text(json.dumps({
            "articles": [
                {"title": "RBI keeps repo rate steady at 6.5%", "link": "https://example.com/rbi", "source_name": "RBI"},
            ],
            "article_count": 1,
        }), encoding="utf-8")

        seen_calls: list[tuple[int, bool, int]] = []

        def fake_collect(ws, we, *, seen_hashes, seen_titles, gnews_offset=0, include_newsdata=True, **kwargs):
            seen_calls.append((gnews_offset, include_newsdata, len(seen_titles)))
            return {
                "articles": [
                    {"title": "ICAR launches climate-resilient paddy seed variety", "link": "https://example.com/icar-seed", "source_name": "PIB"},
                ],
                "report": {"kept": 1},
            }

        monkeypatch.setattr(news_api_sources, "collect", fake_collect)
        ws = datetime(2026, 11, 27, 6, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
        we = datetime(2026, 11, 28, 1, 45, tzinfo=ZoneInfo("Asia/Kolkata"))

        res = news_api_sources.topup_gnews_into_raw(raw_path, ws, we, wave=1)
        assert seen_calls == [(4, False, 1)]
        assert res["added"] == 1
        assert res["total"] == 2
        saved = json.loads(raw_path.read_text(encoding="utf-8"))
        assert saved["article_count"] == 2
        assert len(saved["articles"]) == 2
        assert saved["articles"][1]["link"] == "https://example.com/icar-seed"
        assert saved["gnews_topups"][0]["wave"] == 1
    finally:
        discovery_api.GNEWS.reset()


def test_stage_gate_and_watchdog_awaiting_stage(tmp_path, monkeypatch):
    monkeypatch.setenv("ALP_STAGE_GATES", "04_fact_verification=02:00,12_content_editor=03:00")
    monkeypatch.delenv("DRY_RUN", raising=False)

    gate = main.stage_gate_not_before("daily", "2026-11-28", "04_fact_verification")
    assert gate is not None
    assert gate.astimezone(ZoneInfo("Asia/Kolkata")).hour == 2
    assert gate.astimezone(ZoneInfo("Asia/Kolkata")).minute == 0
    assert main.stage_gate_not_before("weekly", "2026-11-28", "04_fact_verification") is None
    assert main.stage_gate_not_before("daily", "2026-11-28", "05_deduplication") is None

    monkeypatch.setattr(main, "ROOT", tmp_path)
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True)
    jobs_path = state_dir / "jobs.json"
    monkeypatch.setattr(main, "JOBS_STATE_PATH", jobs_path)

    # Gate still in the future -> watchdog stays green (0).
    future_gate = datetime(2099, 1, 1, 2, 0, tzinfo=ZoneInfo("Asia/Kolkata")).isoformat()
    jobs_path.write_text(json.dumps({
        "daily_2099-01-01": {
            "status": "awaiting_stage",
            "next_stage_gate": future_gate,
            "next_stage_name": "04_fact_verification",
            "updated_at": datetime.now(UTC).isoformat(),
            "run_attempts": 1,
        }
    }), encoding="utf-8")
    assert main.watchdog() == 0

    # Gate opened 2 hours ago and never resumed -> watchdog flags it (1).
    stale_gate = "2020-01-01T02:00:00+05:30"
    jobs_path.write_text(json.dumps({
        "daily_2020-01-01": {
            "status": "awaiting_stage",
            "next_stage_gate": stale_gate,
            "next_stage_name": "04_fact_verification",
            "updated_at": datetime.now(UTC).isoformat(),
            "run_attempts": 1,
        }
    }), encoding="utf-8")
    assert main.watchdog() == 1


def test_workflows_enable_auto_discovery_and_overnight_crons():
    daily = (ROOT / ".github" / "workflows" / "daily.yml").read_text(encoding="utf-8")
    for expected in (
        'cron: "30 19 * * *"',   # 01:00 IST
        'cron: "10 20 * * *"',   # 01:40 IST
        'cron: "30 23 * * *"',   # 05:00 IST
        'cron: "0 0 * * *"',     # 05:30 IST
        'ALP_MODEL_AUTO_DISCOVERY: "1"',
        'ALP_GNEWS_MIN_INTERVAL: "15"',
        'ALP_AI_CALL_INTERVAL: "1.5"',
        'ALP_INTER_STAGE_PAUSE: "15"',
        "ALP_STAGE_GATES:",
        "ALP_GNEWS_TOPUP:",
    ):
        assert expected in daily, f"daily.yml missing {expected!r}"

    for wf_name in ("weekly.yml", "monthly.yml", "refresh-current-facts.yml", "verify-keys.yml", "keepalive.yml"):
        text = (ROOT / ".github" / "workflows" / wf_name).read_text(encoding="utf-8")
        assert 'ALP_MODEL_AUTO_DISCOVERY: "1"' in text, f"{wf_name} missing ALP_MODEL_AUTO_DISCOVERY"

    # Zero-dependency duplicate YAML mapping key detector (CI does not install PyYAML).
    import re as _re
    key_re = _re.compile(r"^(\s*)([A-Za-z_][A-Za-z0-9_-]*)\s*:(?:\s|$)")
    block_scalar_re = _re.compile(r":\s*[|>][-+\d]*\s*(?:#.*)?$")
    for wf_path in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        stack: list[tuple[int, set[str]]] = []
        block_indent: int | None = None
        for raw_line in wf_path.read_text(encoding="utf-8").splitlines():
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = len(raw_line) - len(raw_line.lstrip(" "))
            if block_indent is not None:
                if indent > block_indent:
                    continue
                block_indent = None
            if stripped.startswith("- "):
                while stack and stack[-1][0] >= indent + 2:
                    stack.pop()
                continue
            m = key_re.match(raw_line)
            if not m:
                continue
            while stack and stack[-1][0] > indent:
                stack.pop()
            if not stack or stack[-1][0] < indent:
                stack.append((indent, set()))
            key = m.group(2)
            assert key not in stack[-1][1], f"{wf_path.name}: duplicate YAML mapping key {key!r}"
            stack[-1][1].add(key)
            if block_scalar_re.search(raw_line):
                block_indent = indent
