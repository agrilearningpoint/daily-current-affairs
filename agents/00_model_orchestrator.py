# -*- coding: utf-8 -*-
"""
Model Orchestrator Agent (00)
=============================
Pipeline ka foundation — AI provider keys validate + register karta hai.

Responsibilities:
- Env se API keys load karo (Gemini, Groq, OpenAI, Mistral)
- Provider health check (1 test call each)
- Dead keys → warn, don't crash
- Write provider status to state/model_status.json
- Export available providers for downstream agents

Env:
  GEMINI_API_KEY, GROQ_API_KEY, OPENAI_API_KEY, MISTRAL_API_KEY
  ORCHESTRATOR_SKIP_HEALTHCHECK  (1 = skip live test calls)
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# --------------------------------------------------------------------------- #
REPO_ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = REPO_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(LOGS_DIR / "orchestrator_00.log"), encoding="utf-8"),
    ],
)
logger = logging.getLogger("agent.00_model_orchestrator")
from pipeline.persistence import install_secret_log_filter
install_secret_log_filter()


STATE_DIR = REPO_ROOT / "state"
STATE_DIR.mkdir(exist_ok=True)
STATUS_FILE = STATE_DIR / "model_status.json"
SKIP_HEALTHCHECK = os.getenv("ORCHESTRATOR_SKIP_HEALTHCHECK", "0") == "1"
HEALTH_TIMEOUT = int(os.getenv("ORCHESTRATOR_HEALTH_TIMEOUT", "15"))


# --------------------------------------------------------------------------- #
def provider_defaults() -> List[Dict[str, Any]]:
    """Provider names/endpoints/models, derived from the router's single registry.

    The old hard-coded table here still pointed at retired models
    (llama-3.3-70b-versatile, gemini-1.5-flash); keeping one source of truth in
    pipeline.ai_router._build_default_providers() stops the two drifting apart.
    """
    from pipeline.ai_router import _build_default_providers
    return [{"name": p.name, "url": p.url, "model": p.model, "priority": p.priority}
            for p in _build_default_providers()]


# --------------------------------------------------------------------------- #
def load_keys() -> List[Dict[str, Any]]:
    from pipeline.ai_router import _build_default_providers
    env_names = {
        "gemini": "GEMINI_API_KEY" if os.getenv("GEMINI_API_KEY") else "GOOGLE_API_KEY",
        "groq": "GROQ_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "openai": "OPENAI_API_KEY",
        "mistral": "MISTRAL_API_KEY",
        "generic-openai": "LLM_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "nvidia": "NVIDIA_API_KEY",
        "ollama": "OLLAMA_API_KEY" if os.getenv("OLLAMA_API_KEY") else "OLLAMA_BASE_URL",
        "sambanova": "SAMBANOVA_API_KEY",
        "cloudflare": "CLOUDFLARE_ACCOUNT_ID+" + ("CLOUDFLARE_API_TOKEN" if os.getenv("CLOUDFLARE_API_TOKEN") else "CLOUDFLARE_TOKEN"),
        "cohere": "COHERE_API_KEY",
        "llm7": "LL7_API_KEY" if os.getenv("LL7_API_KEY") else "LLM7_API_KEY",
        "huggingface": "HUGGINGFACE_API_KEY" if os.getenv("HUGGINGFACE_API_KEY") else "HF_TOKEN",
        "cerebras": "CEREBRAS_API_KEY",
    }
    return [{"name": provider.name, "url": provider.url, "key": provider.key,
             "model": provider.model, "priority": provider.priority,
             "models": list(provider.models or [provider.model]),
             "env_used": env_names.get(provider.name, "API_KEY")} for provider in _build_default_providers()]


# Statuses where another model of the same provider may still work: a retired
# model (404/410 — NVIDIA llama-3.1-8b EOL, Gemini 2.5-flash-lite for new keys)
# or one that hangs (Gemini 3.5-flash-lite timed out at 40s on 2026-11-03).
_TRY_NEXT_MODEL = {"model_error", "timeout"}
MAX_HEALTH_MODELS = int(os.getenv("ORCHESTRATOR_MAX_HEALTH_MODELS", "3"))


def health_check_models(provider: Dict[str, Any]) -> Dict[str, Any]:
    """Health-check a provider, moving to its next model on 404/410/timeout.

    Returns the health of the first model that answered (or the last failure)
    plus `failed_models` = [(model, status)] for models to retire for the run."""
    models = [m for m in (provider.get("models") or [provider["model"]]) if m][:max(1, MAX_HEALTH_MODELS)]
    failed: List[tuple] = []
    result: Dict[str, Any] = {"status": "error", "detail": "no model"}
    for model in models:
        result = health_check(dict(provider, model=model))
        if result["status"] not in _TRY_NEXT_MODEL or len(models) == 1:
            result["model"] = model
            break
        failed.append((model, result["status"]))
        result["model"] = model
    if failed:
        result["failed_models"] = failed
    return result


def health_check(provider: Dict[str, Any]) -> Dict[str, Any]:
    """One small test call per provider."""
    if SKIP_HEALTHCHECK:
        return {"status": "skipped", "detail": "ORCHESTRATOR_SKIP_HEALTHCHECK=1"}

    try:
        import requests
    except ImportError:
        return {"status": "error", "detail": "requests not installed"}

    name = provider["name"]
    try:
        if name == "gemini":
            # Key in a header, never in the URL (URLs end up in exception text/logs).
            url = f"{provider['url']}/{provider['model']}:generateContent"
            r = requests.post(url, headers={"x-goog-api-key": provider["key"],
                                            "Content-Type": "application/json"}, json={
                "contents": [{"parts": [{"text": "Say OK"}]}],
                "generationConfig": {"maxOutputTokens": 5},
            }, timeout=HEALTH_TIMEOUT)
        else:
            r = requests.post(
                provider["url"],
                headers={"Authorization": f"Bearer {provider['key']}",
                         "Content-Type": "application/json"},
                json={
                    "model": provider["model"],
                    "messages": [{"role": "user", "content": "Say OK"}],
                    "max_tokens": 5,
                },
                timeout=HEALTH_TIMEOUT,
            )

        if r.status_code == 200:
            body = r.json()
            if name == "gemini":
                parts = (body.get("candidates") or [{}])[0].get("content", {}).get("parts", [])
                text = "".join(part.get("text", "") for part in parts)
            else:
                text = (body.get("choices") or [{}])[0].get("message", {}).get("content")
            if not isinstance(text, str) or not text.strip():
                # Reasoning models (gpt-oss on Groq/Ollama) spend a 5-token budget on
                # reasoning and return empty content: reachable, not down.
                return {"status": "malformed", "detail": "provider returned no text (reachable)"}
            return {"status": "ok", "detail": "live"}
        if r.status_code in (401, 403):
            return {"status": "auth_error", "detail": f"HTTP {r.status_code} (invalid key / forbidden)"}
        if r.status_code == 402:
            return {"status": "credit_error", "detail": "HTTP 402 (no balance / paid model)"}
        if r.status_code in (404, 410):
            return {"status": "model_error", "detail": f"HTTP {r.status_code} (model retired / not found)"}
        if r.status_code == 429:
            return {"status": "rate_limit", "detail": "quota exceeded"}
        return {"status": "http_error", "detail": f"HTTP {r.status_code}"}
    except requests.Timeout:
        return {"status": "timeout", "detail": f"{HEALTH_TIMEOUT}s timeout"}
    except requests.RequestException as exc:
        return {"status": "network_error", "detail": type(exc).__name__}
    except Exception as exc:
        from pipeline.persistence import redact
        return {"status": "error", "detail": redact(str(exc), os.environ)[:200]}


def atomic_write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


# --------------------------------------------------------------------------- #
# Health statuses that mean "do not call this provider in the rest of the run".
# They seed the router's shared provider health so stages 04/12/16/17b skip the
# provider at once instead of each re-learning it (DeepSeek 402, NVIDIA timeouts).
_SEED_COOLDOWNS = {
    "auth_error": ("AUTH_COOLDOWN", "health check: auth error"),
    "credit_error": ("AUTH_COOLDOWN", "health check: HTTP 402 no balance"),
    "timeout": ("TIMEOUT_COOLDOWN", "health check: timeout"),
}
# Reachable statuses: the provider answered (a 429 or an empty 5-token reply is
# not "down"); only these count towards the healthy total.
_REACHABLE = {"ok", "skipped", "malformed", "rate_limit"}


def seed_router_health(results: List[Dict[str, Any]]) -> List[str]:
    from pipeline import ai_router
    seeded = []
    for res in results:
        # Retired / hung models are blocked model-by-model so later stages
        # rotate past them instead of losing the whole provider.
        for model, model_status in res["health"].get("failed_models") or []:
            seconds = ai_router.AUTH_COOLDOWN if model_status == "model_error" else ai_router.TIMEOUT_COOLDOWN
            ai_router.block(f"{res['name']}::{model}", seconds, f"health check: {model_status}")
        status = res["health"]["status"]
        if status in _SEED_COOLDOWNS:
            attr, reason = _SEED_COOLDOWNS[status]
            ai_router.block(res["name"], getattr(ai_router, attr), reason)
            seeded.append(res["name"])
    return seeded


def main() -> int:
    logger.info("Model orchestrator starting")
    from pipeline import ai_router
    notes = ai_router.unconfigured_notes()
    for note in notes:
        logger.warning("Provider not enabled — %s", note)
    configured = load_keys()
    # News / search helpers (no live call here: their free quotas are small).
    try:
        from pipeline import discovery_api
        aux = {name: ("configured" if st["configured"] else "missing — OFF")
               for name, st in discovery_api.services_status().items()}
        logger.info("News/search keys: %s", aux)
    except Exception:  # pragma: no cover
        aux = {}

    if not configured:
        logger.warning("No AI providers configured (no API keys found)")
        report = {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "providers": [],
            "status": "no_providers",
            "notes": notes,
            "aux_services": aux,
            "note": "Pipeline will run in heuristic-only mode",
        }
        atomic_write(STATUS_FILE, report)
        return 0  # Non-fatal — pipeline can still work without AI

    results = []
    for p in sorted(configured, key=lambda x: x["priority"]):
        logger.info("Checking %s (model=%s)", p["name"], p["model"])
        hc = health_check_models(p)
        results.append({
            "name": p["name"],
            "model": hc.get("model", p["model"]),
            "priority": p["priority"],
            "env_used": p["env_used"],
            "health": hc,
        })
        icon = "✅" if hc["status"] in ("ok", "skipped") else ("⚠️" if hc["status"] in _REACHABLE else "❌")
        logger.info("  %s %s → %s (%s)", icon, p["name"], hc["status"], hc.get("detail", ""))

    seeded = seed_router_health(results)
    if seeded:
        logger.info("Marked down for this run (later stages skip them): %s", seeded)

    healthy = [r for r in results if r["health"]["status"] in _REACHABLE]
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "providers": results,
        "status": "ok" if healthy else "all_failed",
        "healthy_count": len(healthy),
        "total_count": len(results),
        "marked_down": seeded,
        "notes": notes,
        "aux_services": aux,
    }
    atomic_write(STATUS_FILE, report)

    logger.info("Model status: %d/%d reachable → %s",
                len(healthy), len(results), STATUS_FILE)
    if not healthy:
        # AI is optional for this stage: a momentary all-429 must not kill the
        # edition here. Later stages fail closed (no unreviewed Hindi is shipped)
        # and a failed run alerts the admin.
        logger.error("No AI provider reachable right now; continuing — later stages "
                     "use cooldown-aware routing and fail closed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
