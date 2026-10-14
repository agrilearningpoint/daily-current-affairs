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

STATE_DIR = REPO_ROOT / "state"
STATE_DIR.mkdir(exist_ok=True)
STATUS_FILE = STATE_DIR / "model_status.json"
SKIP_HEALTHCHECK = os.getenv("ORCHESTRATOR_SKIP_HEALTHCHECK", "0") == "1"


# --------------------------------------------------------------------------- #
PROVIDERS = [
    {"name": "gemini", "env_keys": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
     "url": "https://generativelanguage.googleapis.com/v1beta/models",
     "model": os.getenv("GEMINI_MODEL", "gemini-1.5-flash"), "priority": 10},
    {"name": "groq", "env_keys": ["GROQ_API_KEY"],
     "url": "https://api.groq.com/openai/v1/chat/completions",
     "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"), "priority": 20},
    {"name": "openai", "env_keys": ["OPENAI_API_KEY"],
     "url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/") + "/chat/completions",
     "model": os.getenv("ALP_LLM", "gpt-4o-mini"), "priority": 30},
    {"name": "mistral", "env_keys": ["MISTRAL_API_KEY"],
     "url": "https://api.mistral.ai/v1/chat/completions",
     "model": os.getenv("MISTRAL_MODEL", "mistral-small-latest"), "priority": 50},
]


# --------------------------------------------------------------------------- #
def load_keys() -> List[Dict[str, Any]]:
    out = []
    for p in PROVIDERS:
        for env in p["env_keys"]:
            key = os.getenv(env)
            if key:
                out.append({**p, "key": key, "env_used": env})
                break
    return out


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
            url = f"{provider['url']}/{provider['model']}:generateContent?key={provider['key']}"
            r = requests.post(url, json={
                "contents": [{"parts": [{"text": "Say OK"}]}],
                "generationConfig": {"maxOutputTokens": 5},
            }, timeout=15)
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
                timeout=15,
            )

        if r.status_code == 200:
            return {"status": "ok", "detail": "live"}
        if r.status_code == 401:
            return {"status": "auth_error", "detail": "invalid key"}
        if r.status_code == 404:
            return {"status": "model_error", "detail": "model not found"}
        if r.status_code == 429:
            return {"status": "rate_limit", "detail": "quota exceeded"}
        return {"status": "http_error", "detail": f"HTTP {r.status_code}"}
    except requests.Timeout:
        return {"status": "timeout", "detail": "15s timeout"}
    except Exception as exc:
        from pipeline.persistence import redact
        return {"status": "error", "detail": redact(str(exc), os.environ)[:200]}


def atomic_write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    with open(tmp, "rb") as f:
        os.fsync(f.fileno())
    os.replace(tmp, path)


# --------------------------------------------------------------------------- #
def main() -> int:
    logger.info("Model orchestrator starting")
    configured = load_keys()

    if not configured:
        logger.warning("No AI providers configured (no API keys found)")
        report = {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "providers": [],
            "status": "no_providers",
            "note": "Pipeline will run in heuristic-only mode",
        }
        atomic_write(STATUS_FILE, report)
        return 0  # Non-fatal — pipeline can still work without AI

    results = []
    for p in sorted(configured, key=lambda x: x["priority"]):
        logger.info("Checking %s (model=%s)", p["name"], p["model"])
        hc = health_check(p)
        results.append({
            "name": p["name"],
            "model": p["model"],
            "priority": p["priority"],
            "env_used": p["env_used"],
            "health": hc,
        })
        icon = "✅" if hc["status"] in ("ok", "skipped") else "❌"
        logger.info("  %s %s → %s", icon, p["name"], hc["status"])

    healthy = [r for r in results if r["health"]["status"] in ("ok", "skipped")]
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "providers": results,
        "status": "ok" if healthy else "all_failed",
        "healthy_count": len(healthy),
        "total_count": len(results),
    }
    atomic_write(STATUS_FILE, report)

    logger.info("Model status: %d/%d healthy → %s",
                len(healthy), len(results), STATUS_FILE)
    return 0 if healthy else 1


if __name__ == "__main__":
    sys.exit(main())
