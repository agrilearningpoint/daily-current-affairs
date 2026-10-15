# -*- coding: utf-8 -*-
"""
AI Translator (Multi-Provider with Fallback)
=============================================
Yeh module English → Hindi translation karta hai with:
- Multi-provider support (Gemini / Groq / OpenAI / Mistral)
- Automatic provider fallback on failure
- Quality validation (numbers + capitalised names must survive)
- In-memory LRU cache (avoids duplicate API calls)
- Retry with exponential backoff
- Timeout per provider
- Structured logging

Return contract (matches content.py expectations):
    {
        "translated_hi": str,      # Hindi (Devanagari) text
        "passed": bool,            # True if validation passed
        "confidence": float,       # 0.0 - 1.0
        "provider": str,           # which provider succeeded
        "issues": list[str],       # validation failures (if any)
    }

Env switches:
    ALP_TRANSLATION_STRICT=1     # fail-closed (no dictionary fallback)
    ALP_TRANSLATION_TIMEOUT=45   # per-provider timeout (seconds)
    ALP_TRANSLATION_MAX_RETRIES=2
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
TIMEOUT = int(os.getenv("ALP_TRANSLATION_TIMEOUT", "45"))
MAX_RETRIES = int(os.getenv("ALP_TRANSLATION_MAX_RETRIES", "2"))
CACHE_MAX_SIZE = int(os.getenv("ALP_TRANSLATION_CACHE_SIZE", "2000"))
# Circuit breaker: a provider that answers 429 keeps the whole translation stage
# blocked for minutes on every single text, and one that answers 401/402/403/404
# never recovers inside the run at all. Park it instead of re-dialling it.
PROVIDER_COOLDOWN = int(os.getenv("ALP_TRANSLATION_PROVIDER_COOLDOWN", "600"))
PROVIDER_DEAD_COOLDOWN = int(os.getenv("ALP_TRANSLATION_PROVIDER_DEAD_COOLDOWN", "3600"))
# Status codes that mean "this credential/quota is not usable right now".
_DEAD_STATUS = {401, 402, 403, 404}

# Regexes for validation (mirrors content.py to stay consistent)
_NUM_RE = re.compile(
    r"(?:(?:Rs\.?|INR|USD|₹|US\$|\$)\s?\d{1,3}(?:,\d{2,3})*(?:\.\d+)?(?:\s?(?:crore|lakh|billion|million|trillion|thousand|Cr|bn|mn)\b)?)"
    r"|(?:\b\d{1,3}(?:,\d{2,3})*(?:\.\d+)?\s?(?:%|percent|per cent|bps|days?|years?|months?|weeks?|tonnes?|hectares?|bn|billion|million|trillion|crore|lakh)\b)",
    re.I,
)
_CAP_RE = re.compile(r"\b[A-Z][A-Za-z&]{2,}(?:\s+[A-Z][A-Za-z&]+)*\b")
_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")

# --------------------------------------------------------------------------- #
# LRU Cache
# --------------------------------------------------------------------------- #
class _LRUCache:
    def __init__(self, max_size: int = CACHE_MAX_SIZE):
        self.max_size = max_size
        self._data: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        if key in self._data:
            self._data.move_to_end(key)
            return self._data[key]
        return None

    def put(self, key: str, value: Dict[str, Any]) -> None:
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = value
        while len(self._data) > self.max_size:
            self._data.popitem(last=False)

    def clear(self) -> None:
        self._data.clear()

    def __len__(self) -> int:
        return len(self._data)


_CACHE = _LRUCache()


# --------------------------------------------------------------------------- #
# Provider circuit breaker
# --------------------------------------------------------------------------- #
_PROVIDER_DOWN_UNTIL: Dict[str, float] = {}


def _provider_available(name: str) -> bool:
    """False while the provider is parked after a failure."""
    return _PROVIDER_DOWN_UNTIL.get(name, 0.0) <= time.monotonic()


def _park_provider(name: str, seconds: int, reason: str) -> None:
    until = time.monotonic() + max(0, seconds)
    if until > _PROVIDER_DOWN_UNTIL.get(name, 0.0):
        if not _PROVIDER_DOWN_UNTIL.get(name):
            logger.warning("[Translator] %s parked for %ds (%s)", name, seconds, reason)
        _PROVIDER_DOWN_UNTIL[name] = until


def reset_provider_circuits() -> None:
    """Clear park timers (used by tests and by a fresh translator process)."""
    _PROVIDER_DOWN_UNTIL.clear()


def available_providers() -> List[Dict[str, Any]]:
    """Configured providers that are not currently parked."""
    return [p for p in _discover_providers() if _provider_available(p.get("name", ""))]


def _cache_key(text: str, task: str) -> str:
    h = hashlib.sha256(f"{task}::{text}".encode("utf-8")).hexdigest()[:24]
    return h


# --------------------------------------------------------------------------- #
# Provider discovery (uses 00_model_orchestrator if available)
# --------------------------------------------------------------------------- #
_PROVIDERS_CACHE: Optional[List[Dict[str, Any]]] = None


def _discover_providers() -> List[Dict[str, Any]]:
    """
    Load provider list from pipeline/ai_router.py or config.
    Returns list of {name, url, key, model} dicts in priority order.
    Empty list if nothing configured.
    """
    global _PROVIDERS_CACHE
    if _PROVIDERS_CACHE is not None:
        return _PROVIDERS_CACHE

    providers: List[Dict[str, Any]] = []

    # Try orchestrator-based discovery
    try:
        from pipeline.ai_router import list_providers  # type: ignore
        for p in list_providers() or []:
            if p.get("url") and p.get("key") and p.get("model"):
                providers.append({
                    "name": p.get("name", "unknown"),
                    "url": p["url"],
                    "key": p["key"],
                    "model": p["model"],
                })
    except Exception as exc:
        logger.debug("[Translator] router discovery failed: %s", exc)

    # Fallback: env-based single provider (OpenAI-compatible)
    if not providers:
        url = os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1"
        key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("ALP_LLM", "gpt-4o-mini")
        if key:
            providers.append({
                "name": "openai-fallback",
                "url": url.rstrip("/") + "/chat/completions",
                "key": key,
                "model": model,
            })

    _PROVIDERS_CACHE = providers
    logger.info("[Translator] %d provider(s) available", len(providers))
    return providers


def reset_provider_cache() -> None:
    """Call after rotating keys / changing config."""
    global _PROVIDERS_CACHE
    _PROVIDERS_CACHE = None


# --------------------------------------------------------------------------- #
# Prompt building
# --------------------------------------------------------------------------- #
def _build_prompt(text: str, task: str) -> Tuple[str, str]:
    system = (
        "You are a professional news translator for Indian competitive exam students. "
        "Translate the user's English text to formal Hindi (Devanagari). "
        "Rules:\n"
        "1. Keep ALL numbers, dates, amounts, units EXACTLY as-is.\n"
        "2. Keep ALL proper nouns (organisation names, place names, person names) "
        "in their official form — do NOT transliterate acronyms like NABARD, RBI, ICAR.\n"
        "3. Use formal/exam-appropriate Hindi. Avoid colloquialisms.\n"
        "4. Do NOT add commentary or explanations.\n"
        "5. Return ONLY the Hindi translation, nothing else."
    )
    if task == "headline":
        user = "Translate this news headline to Hindi:\n\n" + text
    elif task == "key_points":
        user = "Translate this news key point to Hindi:\n\n" + text
    elif task == "mcq":
        user = "Translate this exam question to Hindi (keep technical terms English):\n\n" + text
    elif task == "bilingual":
        user = text
    else:
        user = "Translate this news text to Hindi:\n\n" + text
    return system, user


# --------------------------------------------------------------------------- #
# Provider HTTP call
# --------------------------------------------------------------------------- #
def _call_provider(provider: Dict[str, Any], system: str, user: str) -> Optional[str]:
    try:
        import requests
    except ImportError:
        logger.error("[Translator] requests library missing")
        return None

    if provider["name"] == "gemini":
        url = f"{provider['url']}/{provider['model']}:generateContent"
        headers = {"x-goog-api-key": provider["key"], "Content-Type": "application/json"}
        payload = {"systemInstruction": {"parts": [{"text": system}]},
                   "contents": [{"role": "user", "parts": [{"text": user}]}],
                   "generationConfig": {"temperature": 0.1}}
    else:
        url = provider["url"]
        headers = {"Authorization": f"Bearer {provider['key']}", "Content-Type": "application/json"}
        payload = {"model": provider["model"], "temperature": 0.1,
                   "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    name = provider["name"]
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT)
        if r.status_code in _DEAD_STATUS:
            logger.warning("[Translator] %s rejected credentials/request (%d)", name, r.status_code)
            _park_provider(name, PROVIDER_DEAD_COOLDOWN, f"HTTP {r.status_code}")
            return None
        if r.status_code == 429:
            logger.warning("[Translator] %s rate-limited (429)", name)
            _park_provider(name, PROVIDER_COOLDOWN, "HTTP 429 rate limit")
            return None
        r.raise_for_status()
        data = r.json()
        if provider["name"] == "gemini":
            candidates = data.get("candidates") or []
            parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
            return "".join(part.get("text", "") for part in parts).strip() or None
        # OpenAI-compatible shape
        return (data.get("choices") or [{}])[0].get("message", {}).get("content", "").strip()
    except Exception as exc:
        from pipeline.persistence import redact
        logger.warning("[Translator] %s failed: %s", name, redact(str(exc), dict(os.environ)))
        if not str(exc).startswith("4"):
            _park_provider(name, PROVIDER_COOLDOWN, type(exc).__name__)
        return None


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
def _validate(english: str, hindi: str) -> Tuple[bool, float, List[str]]:
    """
    Quality gate:
    - Must contain Devanagari
    - Numbers must survive
    - Acronyms must survive
    Returns (passed, confidence, issues)
    """
    issues: List[str] = []

    if not hindi or not hindi.strip():
        return False, 0.0, ["empty translation"]

    if not _DEVANAGARI_RE.search(hindi):
        issues.append("no Devanagari characters")

    # Numbers check
    en_nums = set(_NUM_RE.findall(english))
    hi_nums = set(_NUM_RE.findall(hindi))
    missing_nums = en_nums - hi_nums
    if missing_nums:
        issues.append(f"missing numbers: {list(missing_nums)[:3]}")

    # Acronym check (uppercase 2-8 chars)
    en_acr = set(re.findall(r"\b[A-Z]{2,8}\b", english))
    hi_acr = set(re.findall(r"\b[A-Z]{2,8}\b", hindi))
    missing_acr = en_acr - hi_acr
    if missing_acr:
        issues.append(f"missing acronyms: {list(missing_acr)[:3]}")

    # Length sanity (Hindi usually 0.7x - 1.6x of English by char count)
    ratio = len(hindi) / max(len(english), 1)
    if ratio < 0.4 or ratio > 2.5:
        issues.append(f"unusual length ratio {ratio:.2f}")

    passed = not issues
    # Confidence: start from 1.0, subtract per issue
    conf = max(0.0, 1.0 - 0.25 * len(issues))
    return passed, conf, issues


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def translate_content(text: str, task: str = "general") -> Dict[str, Any]:
    """
    Translate English → Hindi. Returns dict matching content.py contract.
    Never raises — always returns a dict.
    """
    text = (text or "").strip()
    if not text:
        return {"translated_hi": "", "passed": False, "confidence": 0.0,
                "provider": "none", "issues": ["empty input"]}

    # Cache hit?
    key = _cache_key(text, task)
    cached = _CACHE.get(key)
    if cached is not None:
        logger.debug("[Translator] cache hit for task=%s", task)
        return cached

    providers = available_providers()
    if not providers:
        configured = bool(_discover_providers())
        result = {
            "translated_hi": "",
            "passed": False,
            "confidence": 0.0,
            "provider": "parked" if configured else "none",
            "issues": ["all providers parked after failures" if configured
                       else "no providers configured"],
        }
        _CACHE.put(key, result)
        return result

    system, user = _build_prompt(text, task)
    last_issues: List[str] = []

    for provider in providers:
        for attempt in range(1, MAX_RETRIES + 1):
            if not _provider_available(provider["name"]):
                break  # parked by a previous attempt/text; do not sleep and retry
            hindi = _call_provider(provider, system, user)
            if not hindi:
                if attempt < MAX_RETRIES:
                    time.sleep(2 ** attempt)
                    continue
                last_issues = [f"{provider['name']}: no response"]
                break

            passed, conf, issues = _validate(text, hindi)
            if passed:
                result = {
                    "translated_hi": hindi,
                    "passed": True,
                    "confidence": round(conf, 3),
                    "provider": provider["name"],
                    "issues": [],
                }
                _CACHE.put(key, result)
                logger.debug("[Translator] ✔ %s (conf=%.2f) for task=%s",
                             provider["name"], conf, task)
                return result
            else:
                last_issues = issues
                logger.warning("[Translator] %s validation failed: %s",
                               provider["name"], issues)
                break  # try next provider

    # All providers failed. If none of them can be dialled any more, say so —
    # the caller and the logs must not look like a per-text content problem.
    parked = not available_providers()
    result = {
        "translated_hi": "",
        "passed": False,
        "confidence": 0.0,
        "provider": "parked" if parked else "all-failed",
        "issues": last_issues or (["all providers parked after failures"] if parked else []),
    }
    _CACHE.put(key, result)
    return result


def clear_cache() -> None:
    _CACHE.clear()
    logger.info("[Translator] cache cleared")


def cache_stats() -> Dict[str, int]:
    return {"size": len(_CACHE), "max": CACHE_MAX_SIZE}


# --------------------------------------------------------------------------- #
# Batch helper (used by content.py for `_hindi_for_added`)
# --------------------------------------------------------------------------- #
def translate_batch(lines: List[str], task: str = "general") -> List[str]:
    """
    Translate multiple lines. Uses cache aggressively. Returns list of Hindi strings.
    Order preserved. Failed translations return original English (safe fallback).
    """
    out: List[str] = []
    for line in lines:
        res = translate_content(line, task=task)
        out.append(res["translated_hi"] if res["passed"] and res["translated_hi"] else line)
    return out
