# -*- coding: utf-8 -*-
"""
AI Router — Multi-Provider with Fallback
=========================================
Routes AI tasks across multiple providers (Gemini → Groq → OpenAI → Mistral)
with automatic fallback, rate-limit tracking, and failure classification.

Features:
- Multi-provider fallback chain (configurable priority)
- Per-provider rate-limit tracking (RPM / RPD)
- Failure classification:
    * TRANSIENT       — retry (network, 5xx)
    * RATE_LIMIT      — wait & retry (429)
    * AUTH_ERROR      — skip provider permanently (401/403)
    * MODEL_ERROR     — skip provider permanently (404 model)
    * BAD_REQUEST     — fail fast (400)
    * MALFORMED       — retry or fallback (bad JSON)
- Budget cap (max calls per hour/day)
- Per-provider timeout
- LRU response cache
- Never raises to caller — always returns a string (or raises if all providers fail AND fail_on_all=True)

Env:
  GEMINI_API_KEY, GROQ_API_KEY, OPENAI_API_KEY, MISTRAL_API_KEY,
  OPENROUTER_API_KEY, NVIDIA_API_KEY
  AI_ROUTER_MAX_CALLS_PER_HOUR (default 500)
  AI_ROUTER_TIMEOUT (default 60)
  AI_ROUTER_CACHE_SIZE (default 1000)
  AI_ROUTER_DISABLED (1 = always return None; useful for tests)
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import threading
import time
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger("pipeline.ai_router")

# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
TIMEOUT = int(os.getenv("AI_ROUTER_TIMEOUT", "60"))
MAX_CALLS_PER_HOUR = int(os.getenv("AI_ROUTER_MAX_CALLS_PER_HOUR", "500"))
CACHE_SIZE = int(os.getenv("AI_ROUTER_CACHE_SIZE", "1000"))
DISABLED = os.getenv("AI_ROUTER_DISABLED", "0") == "1"


# --------------------------------------------------------------------------- #
# Failure classification
# --------------------------------------------------------------------------- #
class FailureType:
    TRANSIENT = "transient"          # network, timeout, 5xx — retry
    RATE_LIMIT = "rate_limit"        # 429 — wait & retry
    AUTH_ERROR = "auth_error"        # 401/403 — skip provider
    MODEL_ERROR = "model_error"      # 404 model not found — skip provider
    BAD_REQUEST = "bad_request"      # 400 — fail fast
    MALFORMED = "malformed"          # bad JSON in response — retry/fallback
    UNKNOWN = "unknown"


# --------------------------------------------------------------------------- #
# Provider registry
# --------------------------------------------------------------------------- #
@dataclass
class Provider:
    name: str
    url: str
    key: str
    model: str
    priority: int = 100
    rpm_limit: int = 60              # requests per minute
    rpd_limit: int = 1000            # requests per day
    last_error: Optional[str] = None
    disabled_until: float = 0.0
    call_times: deque = field(default_factory=lambda: deque(maxlen=5000))
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def is_available(self) -> bool:
        if not self.key or not self.url or not self.model:
            return False
        if time.time() < self.disabled_until:
            return False
        # RPM check
        now = time.time()
        recent = [t for t in self.call_times if now - t < 60]
        if len(recent) >= self.rpm_limit:
            return False
        # RPD check
        today = [t for t in self.call_times if now - t < 86400]
        if len(today) >= self.rpd_limit:
            return False
        return True

    def record_call(self) -> None:
        with self._lock:
            self.call_times.append(time.time())

    def mark_disabled(self, reason: str, seconds: int = 300) -> None:
        with self._lock:
            self.disabled_until = time.time() + seconds
            self.last_error = reason
            logger.warning("[Router] Provider %s disabled for %ds: %s",
                           self.name, seconds, reason)


# Live model discovery is deliberately best-effort.  Provider catalogues change
# more often than this repository, so model IDs must not be treated as a
# permanent part of the workflow configuration.
_MODEL_DISCOVERY_TIMEOUT = 8
_PREFERRED_MODELS = {
    "gemini": ("gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash"),
    "groq": ("openai/gpt-oss-120b", "qwen/qwen3.8-27b", "openai/gpt-oss-20b"),
    "nvidia": ("meta/llama-3.3-70b-instruct", "meta/llama-3.1-8b-instruct",
               "nvidia/llama-3.3-nemotron-super-49b-v1.5"),
}


def _catalog_url(provider: Provider) -> str:
    if provider.name == "gemini":
        return provider.url
    marker = "/chat/completions"
    if marker in provider.url:
        return provider.url.split(marker, 1)[0] + "/models"
    return ""


def _live_model_ids(provider: Provider) -> List[str]:
    """Return currently advertised text models without exposing secret values."""
    if os.getenv("ALP_MODEL_AUTO_DISCOVERY", "1") != "1":
        return []
    url = _catalog_url(provider)
    if not url:
        return []
    headers = {"x-goog-api-key": provider.key} if provider.name == "gemini" else {
        "Authorization": f"Bearer {provider.key}"
    }
    try:
        response = requests.get(url, headers=headers, timeout=_MODEL_DISCOVERY_TIMEOUT)
        if response.status_code != 200:
            logger.info("[Router] %s model catalogue unavailable (HTTP %s)", provider.name, response.status_code)
            return []
        data = response.json()
        if provider.name == "gemini":
            models = data.get("models", [])
            return [str(m.get("name", "")).removeprefix("models/") for m in models
                    if "generateContent" in (m.get("supportedGenerationMethods") or [])]
        return [str(m.get("id", "")) for m in data.get("data", []) if m.get("id")]
    except (requests.RequestException, ValueError, TypeError) as exc:
        logger.info("[Router] %s model catalogue lookup skipped: %s", provider.name, type(exc).__name__)
        return []


def _choose_live_model(provider: Provider, available: List[str], exclude: set[str] | None = None) -> str | None:
    exclude = exclude or set()
    candidates = [m for m in available if m and m not in exclude]
    if not candidates:
        return None
    # A configured model wins only when the provider still advertises it.
    if provider.model in candidates:
        return provider.model
    for preferred in _PREFERRED_MODELS.get(provider.name, ()):
        if preferred in candidates:
            return preferred
    text_models = [m for m in candidates if re.search(r"(?:instruct|chat|gpt|llama|qwen|mistral|deepseek|gemini)", m, re.I)
                   and not re.search(r"(?:embed|rerank|guard|vision|audio|image)", m, re.I)]
    return sorted(text_models or candidates)[0]


def _refresh_provider_model(provider: Provider, exclude: set[str] | None = None) -> bool:
    chosen = _choose_live_model(provider, _live_model_ids(provider), exclude)
    if not chosen or chosen == provider.model:
        return False
    old = provider.model
    provider.model = chosen
    logger.info("[Router] %s automatically switched retired model %s -> %s", provider.name, old, chosen)
    return True


# --------------------------------------------------------------------------- #
# Provider discovery
# --------------------------------------------------------------------------- #
def _build_default_providers() -> List[Provider]:
    """Build provider list from env vars, in priority order."""
    providers: List[Provider] = []

    # Gemini (highest priority — per aapke .env.example)
    gem_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gem_key:
        provider = Provider(
            name="gemini",
            url="https://generativelanguage.googleapis.com/v1beta/models",
            key=gem_key,
            # 1.5 Flash was retired from the public endpoint; use a current
            # generateContent-compatible default unless a secret overrides it.
            model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            priority=10, rpm_limit=60, rpd_limit=1500,
        )
        _refresh_provider_model(provider)
        providers.append(provider)

    # Groq (fast fallback)
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        provider = Provider(
            name="groq",
            url="https://api.groq.com/openai/v1/chat/completions",
            key=groq_key,
            # Groq retired llama-3.3-70b-versatile on 2026-08-16.
            model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
            priority=20, rpm_limit=30, rpd_limit=14400,
        )
        _refresh_provider_model(provider)
        providers.append(provider)

    # DeepSeek (high-quality bilingual reasoning & translation)
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    if deepseek_key:
        base = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
        providers.append(Provider(
            name="deepseek",
            url=f"{base}/chat/completions",
            key=deepseek_key,
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            priority=25, rpm_limit=60, rpd_limit=10000,
        ))

    # OpenAI (also used for polish)
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        providers.append(Provider(
            name="openai",
            url=f"{base}/chat/completions",
            key=openai_key,
            model=os.getenv("ALP_LLM", "gpt-4o-mini"),
            priority=30, rpm_limit=500, rpd_limit=10000,
        ))

    # Generic OpenAI-compatible (LLM_API_URL + LLM_API_KEY)
    generic_url = os.getenv("LLM_API_URL")
    generic_key = os.getenv("LLM_API_KEY")
    if generic_url and generic_key:
        providers.append(Provider(
            name="generic-openai",
            url=generic_url,
            key=generic_key,
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            priority=40, rpm_limit=60, rpd_limit=5000,
        ))

    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        providers.append(Provider(name="openrouter", url="https://openrouter.ai/api/v1/chat/completions",
                                  key=openrouter_key, model=os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"),
                                  priority=45, rpm_limit=60, rpd_limit=5000))

    # Mistral (final fallback)
    mistral_key = os.getenv("MISTRAL_API_KEY")
    if mistral_key:
        providers.append(Provider(
            name="mistral",
            url="https://api.mistral.ai/v1/chat/completions",
            key=mistral_key,
            model=os.getenv("MISTRAL_MODEL", "mistral-small-latest"),
            priority=50, rpm_limit=60, rpd_limit=5000,
        ))

    nvidia_key = os.getenv("NVIDIA_API_KEY")
    if nvidia_key:
        provider = Provider(
            name="nvidia",
            url="https://integrate.api.nvidia.com/v1/chat/completions",
            key=nvidia_key,
            model=os.getenv("NVIDIA_MODEL", "meta/llama-3.3-70b-instruct"),
            priority=60, rpm_limit=30, rpd_limit=5000,
        )
        _refresh_provider_model(provider)
        providers.append(provider)

    # Ollama (local/remote OpenAI-compatible server when configured)
    ollama_url = os.getenv("OLLAMA_BASE_URL") or os.getenv("OLLAMA_API_URL")
    ollama_key = os.getenv("OLLAMA_API_KEY")
    if ollama_url:
        endpoint = ollama_url.rstrip("/")
        if not endpoint.endswith("/chat/completions"):
            endpoint = f"{endpoint}/v1/chat/completions" if not endpoint.endswith("/v1") else f"{endpoint}/chat/completions"
        providers.append(Provider(
            name="ollama",
            url=endpoint,
            key=ollama_key or "ollama",
            model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
            priority=70, rpm_limit=30, rpd_limit=5000,
        ))

    providers.sort(key=lambda p: p.priority)
    return providers


_PROVIDERS: Optional[List[Provider]] = None
_PROVIDERS_LOCK = threading.Lock()


def list_providers() -> List[Dict[str, Any]]:
    """Public API — used by ai_translator.py for discovery."""
    providers = _get_providers()
    return [
        {
            "name": p.name,
            "url": p.url,
            "key": p.key,
            "model": p.model,
            "priority": p.priority,
            "available": p.is_available(),
        }
        for p in providers
    ]


def _get_providers() -> List[Provider]:
    global _PROVIDERS
    if _PROVIDERS is None:
        with _PROVIDERS_LOCK:
            if _PROVIDERS is None:
                _PROVIDERS = _build_default_providers()
                logger.info("[Router] %d provider(s) configured: %s",
                            len(_PROVIDERS), [p.name for p in _PROVIDERS])
    return _PROVIDERS


def reset_providers() -> None:
    """Call after rotating keys or changing env."""
    global _PROVIDERS
    with _PROVIDERS_LOCK:
        _PROVIDERS = None
    _CACHE.clear()


# --------------------------------------------------------------------------- #
# Response cache
# --------------------------------------------------------------------------- #
class _LRUCache:
    def __init__(self, max_size: int):
        self.max_size = max_size
        self._data: "OrderedDict[str, str]" = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[str]:
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
                return self._data[key]
        return None

    def put(self, key: str, value: str) -> None:
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
            self._data[key] = value
            while len(self._data) > self.max_size:
                self._data.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def __len__(self) -> int:
        return len(self._data)


_CACHE = _LRUCache(CACHE_SIZE)


def _cache_key(
    prompt: str,
    task: str,
    response_format: Optional[Dict[str, Any]] = None,
    system_prompt: Optional[str] = None,
    needs_hindi: bool = False,
) -> str:
    options = json.dumps(response_format or {}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(
        f"{task}::{options}::{system_prompt or ''}::{needs_hindi}::{prompt}".encode("utf-8")
    ).hexdigest()[:24]


# --------------------------------------------------------------------------- #
# Global call budget
# --------------------------------------------------------------------------- #
_CALL_TIMES: deque = deque(maxlen=10000)
_CALL_LOCK = threading.Lock()


def _within_budget() -> bool:
    with _CALL_LOCK:
        now = time.time()
        hour_ago = now - 3600
        recent = [t for t in _CALL_TIMES if t > hour_ago]
        if len(recent) >= MAX_CALLS_PER_HOUR:
            return False
        _CALL_TIMES.append(now)
        return True


# --------------------------------------------------------------------------- #
# HTTP call per provider
# --------------------------------------------------------------------------- #
def _classify_error(status: int, body: str) -> str:
    if status == 429:
        return FailureType.RATE_LIMIT
    if status in (401, 402, 403):
        return FailureType.AUTH_ERROR
    if status in (404, 410):
        return FailureType.MODEL_ERROR
    if 400 <= status < 500:
        return FailureType.BAD_REQUEST
    if 500 <= status < 600:
        return FailureType.TRANSIENT
    return FailureType.UNKNOWN


def _call_provider(
    provider: Provider,
    prompt: str,
    task: str,
    needs_hindi: bool = False,
    response_format: Optional[Dict[str, Any]] = None,
    system_prompt: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Call one provider. Returns (content, failure_type).
    On success: (content, None)
    On failure: (None, failure_type)
    """
    system_msg = system_prompt or (
        "You are a helpful assistant for an Indian competitive-exam current-affairs bot. "
        "Respond with accurate, factual information. "
        + ("Reply in Hindi (Devanagari)." if needs_hindi else "Reply in English.")
    )

    # Gemini uses a different API shape
    if provider.name == "gemini":
        url = f"{provider.url}/{provider.model}:generateContent"
        payload = {
            "systemInstruction": {"parts": [{"text": system_msg}]},
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2},
        }
        if response_format and response_format.get("type") == "json_object":
            payload["generationConfig"]["responseMimeType"] = "application/json"
        headers = {
            "x-goog-api-key": provider.key,
            "Content-Type": "application/json",
        }
    else:
        url = provider.url
        payload = {
            "model": provider.model,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        if response_format:
            payload["response_format"] = response_format
        headers = {
            "Authorization": f"Bearer {provider.key}",
            "Content-Type": "application/json",
        }

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT)
    except requests.Timeout:
        return None, FailureType.TRANSIENT
    except requests.RequestException as exc:
        logger.debug("[Router] %s network error: %s", provider.name, exc)
        return None, FailureType.TRANSIENT

    if r.status_code >= 400:
        ft = _classify_error(r.status_code, r.text[:200])
        logger.warning("[Router] %s HTTP %d (%s): %s",
                       provider.name, r.status_code, ft, r.text[:200])
        return None, ft

    try:
        data = r.json()
    except ValueError:
        return None, FailureType.MALFORMED

    # Extract content (per-provider shape)
    try:
        if provider.name == "gemini":
            candidates = data.get("candidates", [])
            if not candidates:
                return None, FailureType.MALFORMED
            parts = candidates[0].get("content", {}).get("parts", [])
            content = "".join(p.get("text", "") for p in parts)
        else:
            content = data["choices"][0]["message"]["content"]
        content = (content or "").strip()
        if not content:
            return None, FailureType.MALFORMED
        return content, None
    except (KeyError, IndexError, TypeError) as exc:
        logger.warning("[Router] %s malformed response: %s", provider.name, exc)
        return None, FailureType.MALFORMED


# --------------------------------------------------------------------------- #
# Main routing
# --------------------------------------------------------------------------- #
def route(
    prompt: str,
    task: str = "general",
    needs_hindi: bool = False,
    fail_on_all: bool = False,
    response_format: Optional[Dict[str, Any]] = None,
    system_prompt: Optional[str] = None,
) -> Optional[str]:
    """
    Route a prompt across providers with fallback.

    Returns:
        - str  : the AI response
        - None : if all providers failed AND fail_on_all=False (graceful)
        - raises RuntimeError if fail_on_all=True and all providers failed
    """
    if DISABLED:
        logger.debug("[Router] DISABLED via env — skipping")
        if fail_on_all:
            raise RuntimeError("AI router disabled (AI_ROUTER_DISABLED=1)")
        return None

    prompt = (prompt or "").strip()
    if not prompt:
        return "" if not fail_on_all else None

    # Cache check
    ck = _cache_key(prompt, task, response_format, system_prompt, needs_hindi)
    cached = _CACHE.get(ck)
    if cached is not None:
        logger.debug("[Router] Cache hit for task=%s", task)
        return cached

    # Budget check
    if not _within_budget():
        logger.error("[Router] Hourly budget exceeded (%d calls)", MAX_CALLS_PER_HOUR)
        if fail_on_all:
            raise RuntimeError("AI hourly budget exceeded")
        return None

    providers = _get_providers()
    if not providers:
        logger.warning("[Router] No providers configured")
        if fail_on_all:
            raise RuntimeError("No AI providers configured")
        return None

    last_error: Optional[str] = None

    for provider in providers:
        if not provider.is_available():
            logger.debug("[Router] %s skipped (unavailable)", provider.name)
            continue

        logger.debug("[Router] Trying %s (model=%s)", provider.name, provider.model)
        provider.record_call()

        content, failure = _call_provider(
            provider, prompt, task, needs_hindi, response_format, system_prompt
        )

        if content is not None:
            _CACHE.put(ck, content)
            logger.info("[Router] ✔ %s responded (task=%s, %d chars)",
                        provider.name, task, len(content))
            return content

        # A 404/410 can mean only the selected model was retired. Refresh the
        # provider catalogue once before taking the provider out of service.
        if failure == FailureType.MODEL_ERROR and _refresh_provider_model(
            provider, exclude={provider.model}
        ):
            provider.record_call()
            content, failure = _call_provider(
                provider, prompt, task, needs_hindi, response_format, system_prompt
            )
            if content is not None:
                _CACHE.put(ck, content)
                logger.info("[Router] %s responded after model refresh (task=%s)",
                            provider.name, task)
                return content

        # Failure handling
        last_error = f"{provider.name}: {failure}"
        if failure == FailureType.AUTH_ERROR:
            provider.mark_disabled("auth error", 3600)
        elif failure == FailureType.MODEL_ERROR:
            provider.mark_disabled("model not found", 86400)
        elif failure == FailureType.RATE_LIMIT:
            provider.mark_disabled("rate limited", 120)
        # TRANSIENT / MALFORMED / BAD_REQUEST → just try next provider

    logger.error("[Router] All providers failed. Last error: %s", last_error)
    if fail_on_all:
        raise RuntimeError(f"All AI providers failed: {last_error}")
    return None


# --------------------------------------------------------------------------- #
# Debug helpers
# --------------------------------------------------------------------------- #
def stats() -> Dict[str, Any]:
    """Return router stats — useful for health checks and debugging."""
    providers = _get_providers()
    now = time.time()
    return {
        "providers": [
            {
                "name": p.name,
                "model": p.model,
                "available": p.is_available(),
                "disabled_for": max(0, int(p.disabled_until - now)),
                "last_error": p.last_error,
                "calls_last_hour": sum(1 for t in p.call_times if now - t < 3600),
                "rpm_limit": p.rpm_limit,
            }
            for p in providers
        ],
        "cache_size": len(_CACHE),
        "cache_max": CACHE_SIZE,
        "calls_last_hour": sum(1 for t in _CALL_TIMES if now - t < 3600),
        "hourly_budget": MAX_CALLS_PER_HOUR,
    }


def is_configured() -> bool:
    """Whether at least one provider has usable key, endpoint, and model configuration."""
    return bool(_get_providers())


def clear_cache() -> None:
    _CACHE.clear()


def reset() -> None:
    """Full reset — clear cache, providers, call counts. For tests."""
    _CACHE.clear()
    with _CALL_LOCK:
        _CALL_TIMES.clear()
    reset_providers()


# --------------------------------------------------------------------------- #
# Smoke test
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("=== Router Stats ===")
    print(json.dumps(stats(), indent=2))
    print("\n=== Test Call ===")
    out = route("What is the capital of India? Reply in one word.", task="test")
    print("Response:", out)
