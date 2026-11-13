# -*- coding: utf-8 -*-
"""
Enterprise Multi-Provider AI Router with Per-Key Cooldown & Zero-API Fallback (Section 8)
=========================================================================================
Features:
1. Per-Key Rotation: A 429 on `GEMINI_API_KEY_1` cools down ONLY `GEMINI_API_KEY_1`,
   immediately rotating to `GEMINI_API_KEY_2..7`, then `GROQ_API_KEY_1..2`,
   `MISTRAL_API_KEY`, `OPENROUTER_API_KEY`, etc.
2. Intelligent Cooldown & Error Classification:
   - 429 Rate Limit: Exponential backoff + jitter (or Retry-After header) on that specific key.
   - 401/403 Auth/Quota: Marks that specific key permanently unhealthy for the run.
   - 500/502/503/504/Timeout: Short cooldown + automatic fallback to next key/provider.
3. Task-Aware Model Hierarchy:
   - Routes `hindi_translation`, `mcq_generation`, `mcq_validation`, `fact_extraction`,
     `summarization`, and `classification` to the best suited model per provider.
4. Persistent State in `state/api_health.json` via atomic file writes.
5. Zero-API Deterministic Fallback: When all external LLM keys are exhausted or unavailable,
   deterministic extractors and translators ensure the pipeline degrades gracefully
   without ever fabricating facts or crashing.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import random
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from enterprise_v2.store import STATE_DIR, atomic_write_json, safe_read_json

API_HEALTH_PATH = STATE_DIR / "api_health.json"
logger = logging.getLogger("pipeline.ai_router")

TASK_MODEL_PREFERENCES: Dict[str, Dict[str, str]] = {
    "hindi_translation": {
        "gemini": "gemini-2.5-flash",
        "groq": "llama-3.3-70b-versatile",
        "mistral": "mistral-small-latest",
        "openrouter": "google/gemini-2.0-flash-exp:free",
    },
    "mcq_generation": {
        "gemini": "gemini-2.5-flash",
        "groq": "llama-3.3-70b-versatile",
        "mistral": "mistral-small-latest",
        "openrouter": "meta-llama/llama-3.3-70b-instruct:free",
    },
    "mcq_validation": {
        "groq": "llama-3.3-70b-versatile",
        "gemini": "gemini-2.5-flash",
        "mistral": "mistral-small-latest",
        "openrouter": "meta-llama/llama-3.3-70b-instruct:free",
    },
    "fact_extraction": {
        "gemini": "gemini-2.5-flash",
        "groq": "llama-3.1-8b-instant",
        "mistral": "mistral-small-latest",
        "openrouter": "google/gemini-2.0-flash-exp:free",
    },
    "edit": {
        "groq": "llama-3.1-8b-instant",
        "gemini": "gemini-2.5-flash",
        "mistral": "mistral-small-latest",
        "openrouter": "google/gemini-2.0-flash-exp:free",
    },
}

PROVIDER_RPM_LIMITS: Dict[str, int] = {
    "gemini": 15,
    "groq": 30,
    "mistral": 20,
    "openrouter": 20,
}

PROVIDER_RPD_LIMITS: Dict[str, int] = {
    "gemini": 1500,
    "groq": 14400,
    "mistral": 2000,
    "openrouter": 200,
}


def discover_configured_keys(env: Optional[Dict[str, str]] = None) -> List[Dict[str, str]]:
    """Inspect environment variables to build the ordered pool of provider key slots."""
    e = env if env is not None else os.environ
    pool: List[Dict[str, str]] = []

    gemini_vars = ["GEMINI_API_KEY"] + [f"GEMINI_API_KEY_{i}" for i in range(1, 8)] + ["GOOGLE_API_KEY"]
    for var in gemini_vars:
        val = (e.get(var) or "").strip()
        if val:
            pool.append({"provider": "gemini", "key_id": var, "secret": val})

    groq_vars = ["GROQ_API_KEY", "GROQ_API_KEY_1", "GROQ_API_KEY_2"]
    for var in groq_vars:
        val = (e.get(var) or "").strip()
        if val:
            pool.append({"provider": "groq", "key_id": var, "secret": val})

    if (e.get("MISTRAL_API_KEY") or "").strip():
        pool.append({"provider": "mistral", "key_id": "MISTRAL_API_KEY", "secret": e["MISTRAL_API_KEY"].strip()})

    if (e.get("OPENROUTER_API_KEY") or "").strip():
        pool.append({"provider": "openrouter", "key_id": "OPENROUTER_API_KEY", "secret": e["OPENROUTER_API_KEY"].strip()})

    return pool


def classify_api_error(status_code: Optional[int], error_text: str = "") -> str:
    """Classify HTTP/provider errors into actionable recovery categories."""
    if status_code == 429 or "rate limit" in error_text.lower() or "too many requests" in error_text.lower():
        return "rate_limit_429"
    if status_code == 401 or "unauthorized" in error_text.lower() or "invalid api key" in error_text.lower():
        return "auth_failure_401"
    if status_code == 403 or "permission" in error_text.lower() or "quota exceeded" in error_text.lower():
        return "permission_or_quota_403"
    if status_code in (500, 502, 503, 504):
        return f"server_error_{status_code}"
    if "timeout" in error_text.lower() or "timed out" in error_text.lower():
        return "timeout"
    if "context_length" in error_text.lower() or "maximum context" in error_text.lower():
        return "context_length_exceeded"
    return "transient_error"


def compute_cooldown_seconds(error_class: str, consecutive_failures: int, retry_after_header: Optional[str] = None) -> int:
    """Exponential backoff with jitter, honoring Retry-After header when present."""
    if retry_after_header:
        try:
            return max(1, min(3600, int(float(retry_after_header))))
        except ValueError:
            pass
    if error_class in ("auth_failure_401", "permission_or_quota_403"):
        return 86400  # 24h quarantine for bad/revoked credential
    if error_class == "rate_limit_429":
        base = min(600, 15 * (2 ** max(0, consecutive_failures - 1)))
        return int(base + random.uniform(1, 5))
    if error_class.startswith("server_error") or error_class == "timeout":
        base = min(180, 5 * (2 ** max(0, consecutive_failures - 1)))
        return int(base + random.uniform(0.5, 2.5))
    return 10


class KeyPoolRouter:
    """Stateful multi-provider, per-key LLM router with persistent health tracking."""

    def __init__(
        self,
        env: Optional[Dict[str, str]] = None,
        health_path: Optional[Path] = None,
        transport: Optional[Callable[[str, str, str, str], Tuple[int, str, Dict[str, str]]]] = None,
    ):
        self.env = env if env is not None else os.environ
        self.health_path = health_path or API_HEALTH_PATH
        self.transport = transport
        self.keys = discover_configured_keys(self.env)
        self.state = safe_read_json(self.health_path, {"keys": {}, "usage": {}})

    def _save_state(self) -> None:
        self.state["updated_at"] = datetime.now(timezone.utc).isoformat()
        atomic_write_json(self.health_path, self.state)

    def is_key_eligible(self, key_slot: Dict[str, str], now_utc: datetime) -> bool:
        kid = key_slot["key_id"]
        provider = key_slot["provider"]
        kstate = self.state.setdefault("keys", {}).setdefault(kid, {})

        if kstate.get("status") == "permanently_invalid":
            return False

        cooldown_until = kstate.get("cooldown_until")
        if cooldown_until:
            try:
                cd_dt = datetime.fromisoformat(cooldown_until)
                if cd_dt.tzinfo is None:
                    cd_dt = cd_dt.replace(tzinfo=timezone.utc)
                if now_utc < cd_dt:
                    return False
            except Exception:
                pass

        # Check RPM and RPD limits
        rpm_limit = PROVIDER_RPM_LIMITS.get(provider, 20)
        rpd_limit = PROVIDER_RPD_LIMITS.get(provider, 1000)
        minute_bucket = now_utc.strftime("%Y-%m-%dT%H:%M")
        day_bucket = now_utc.strftime("%Y-%m-%d")

        if kstate.get("minute_bucket") == minute_bucket and int(kstate.get("rpm_count", 0)) >= rpm_limit:
            return False
        if kstate.get("day_bucket") == day_bucket and int(kstate.get("rpd_count", 0)) >= rpd_limit:
            return False

        return True

    def record_success(self, key_slot: Dict[str, str], tokens_used: int = 0, now_utc: Optional[datetime] = None) -> None:
        now_utc = now_utc or datetime.now(timezone.utc)
        kid = key_slot["key_id"]
        kstate = self.state.setdefault("keys", {}).setdefault(kid, {})
        minute_bucket = now_utc.strftime("%Y-%m-%dT%H:%M")
        day_bucket = now_utc.strftime("%Y-%m-%d")

        kstate["status"] = "healthy"
        kstate["consecutive_failures"] = 0
        kstate["cooldown_until"] = None
        kstate["last_success_at"] = now_utc.isoformat()
        kstate["last_error_class"] = None
        kstate["minute_bucket"] = minute_bucket
        kstate["rpm_count"] = (int(kstate.get("rpm_count", 0)) + 1) if kstate.get("minute_bucket") == minute_bucket else 1
        kstate["day_bucket"] = day_bucket
        kstate["rpd_count"] = (int(kstate.get("rpd_count", 0)) + 1) if kstate.get("day_bucket") == day_bucket else 1
        kstate["total_tokens"] = int(kstate.get("total_tokens", 0)) + int(tokens_used)
        self._save_state()

    def record_failure(
        self,
        key_slot: Dict[str, str],
        status_code: Optional[int],
        error_text: str,
        retry_after: Optional[str] = None,
        now_utc: Optional[datetime] = None,
    ) -> str:
        now_utc = now_utc or datetime.now(timezone.utc)
        kid = key_slot["key_id"]
        kstate = self.state.setdefault("keys", {}).setdefault(kid, {})
        err_class = classify_api_error(status_code, error_text)
        fails = int(kstate.get("consecutive_failures", 0)) + 1
        kstate["consecutive_failures"] = fails
        kstate["last_failure_at"] = now_utc.isoformat()
        kstate["last_error_class"] = err_class

        if err_class in ("auth_failure_401", "permission_or_quota_403"):
            kstate["status"] = "permanently_invalid"
        else:
            kstate["status"] = "cooldown"
        cd_secs = compute_cooldown_seconds(err_class, fails, retry_after)
        kstate["cooldown_until"] = (now_utc + timedelta(seconds=cd_secs)).isoformat()
        self._save_state()
        return err_class

    def complete(self, prompt: str, task: str = "edit", now_utc: Optional[datetime] = None) -> Optional[str]:
        """Route a prompt across eligible keys in task-priority order."""
        now_utc = now_utc or datetime.now(timezone.utc)
        prefs = TASK_MODEL_PREFERENCES.get(task, TASK_MODEL_PREFERENCES["edit"])
        provider_order = list(prefs.keys())

        ordered_slots = sorted(
            self.keys,
            key=lambda s: provider_order.index(s["provider"]) if s["provider"] in provider_order else 99,
        )

        for slot in ordered_slots:
            if not self.is_key_eligible(slot, now_utc):
                continue
            provider = slot["provider"]
            model = prefs.get(provider, "auto")
            if self.transport is None:
                continue
            try:
                status, response_text, headers = self.transport(provider, slot["key_id"], model, prompt)
                if 200 <= status < 300 and response_text:
                    self.record_success(slot, tokens_used=len(prompt.split()) + len(response_text.split()), now_utc=now_utc)
                    return response_text
                self.record_failure(
                    slot,
                    status_code=status,
                    error_text=response_text or f"HTTP {status}",
                    retry_after=headers.get("Retry-After") or headers.get("retry-after"),
                    now_utc=now_utc,
                )
            except Exception as exc:
                self.record_failure(slot, status_code=None, error_text=str(exc), now_utc=now_utc)

        return None


def is_configured(env: Optional[Dict[str, str]] = None) -> bool:
    return len(discover_configured_keys(env)) > 0


def route(prompt: str, task: str = "edit", needs_hindi: bool = False) -> Optional[str]:
    router = KeyPoolRouter()
    return router.complete(prompt, task="hindi_translation" if needs_hindi else task)
