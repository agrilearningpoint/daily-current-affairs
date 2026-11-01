import importlib.util
import time
from pathlib import Path

import pipeline.ai_router as router


def _load_fact_module():
    path = Path(__file__).resolve().parents[1] / "agents" / "04_fact_verification.py"
    spec = importlib.util.spec_from_file_location("fact_verification_budget", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_repeated_transient_failures_cool_down_provider(monkeypatch):
    p = router.Provider(name="slow", url="https://x/chat/completions", key="k", model="m")
    monkeypatch.setattr(router, "_get_providers", lambda: [p])
    monkeypatch.setattr(router, "_call_provider", lambda *a, **k: (None, router.FailureType.TRANSIENT))
    router.clear_cache()
    assert router.route("a", task="fact_verification") is None
    assert p.is_available()
    assert router.route("b", task="fact_verification") is None
    assert not p.is_available()


def test_fact_llm_stops_after_consecutive_misses(monkeypatch):
    mod = _load_fact_module()
    calls = []
    monkeypatch.setattr(mod, "llm_score", lambda a: (calls.append(1), (0.0, ["llm_unavailable"]))[1])
    monkeypatch.setattr("pipeline.ai_router.is_configured", lambda: True)
    arts = [{"title": f"t{i}", "link": f"https://e.com/{i}", "summary": "s"} for i in range(10)]
    for a in arts:
        mod.verify_article(a, arts)
    assert len(calls) == mod.LLM_MAX_CONSECUTIVE_MISSES


def test_fact_llm_time_budget(monkeypatch):
    mod = _load_fact_module()
    monkeypatch.setattr(mod, "LLM_BUDGET_SECONDS", 0.0)
    mod._LLM_STATE["started"] = time.time() - 1
    assert mod._llm_allowed() is False
