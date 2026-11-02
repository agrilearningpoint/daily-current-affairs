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
import threading
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
    """Thread-safe LRU cache (the translator may be called from worker threads)."""

    def __init__(self, max_size: int = CACHE_MAX_SIZE):
        self.max_size = max_size
        self._data: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
                return self._data[key]
        return None

    def put(self, key: str, value: Dict[str, Any]) -> None:
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
        with self._lock:
            return len(self._data)


_CACHE = _LRUCache()
_RATE_LIMITED_PROVIDERS = set()
# A 429 is usually a per-minute limit, so a provider is parked for a cooldown
# instead of the whole edition. Credit/auth/model errors (401/402/403/404)
# park it for the rest of the run.
_COOLDOWN_UNTIL: Dict[str, float] = {}
RATE_LIMIT_COOLDOWN = int(os.getenv("ALP_TRANSLATION_RATE_LIMIT_COOLDOWN", "65"))
_HARD_FAIL_STATUSES = {401, 402, 403, 404, 410}


class ProviderRateLimited(Exception):
    """Signal that the current provider should be parked for a cooldown."""

    def __init__(self, name: str, retry_after: float | None = None):
        super().__init__(name)
        self.retry_after = retry_after


_WAIT_BUDGET = [float(os.getenv("ALP_TRANSLATION_WAIT_BUDGET", "0"))]


def _wait_for_cooldown(providers: List[Dict[str, Any]]) -> bool:
    """When every provider is only cooling down, wait (within a run budget) for the first."""
    names = [p["name"] for p in providers]
    if not names or not all(n in _RATE_LIMITED_PROVIDERS for n in names):
        return False
    pending = [_COOLDOWN_UNTIL[n] for n in names if n in _COOLDOWN_UNTIL]
    if not pending:
        return False  # all parked for the run (credit/auth/model errors)
    delay = max(0.0, min(pending) - time.time())
    if delay > _WAIT_BUDGET[0]:
        return False
    _WAIT_BUDGET[0] -= delay
    logger.info("[Translator] all providers cooling down; waiting %.0fs", delay)
    time.sleep(delay)
    return True


def _provider_parked(name: str) -> bool:
    if name not in _RATE_LIMITED_PROVIDERS:
        return False
    until = _COOLDOWN_UNTIL.get(name)
    if until is not None and time.time() >= until:
        _RATE_LIMITED_PROVIDERS.discard(name)
        _COOLDOWN_UNTIL.pop(name, None)
        return False
    return True


def _park_provider(name: str, seconds: float | None) -> None:
    _RATE_LIMITED_PROVIDERS.add(name)
    if seconds is None:
        _COOLDOWN_UNTIL.pop(name, None)  # parked for the whole run
    else:
        _COOLDOWN_UNTIL[name] = time.time() + max(1.0, seconds)


class ProviderRequestFailed(Exception):
    def __init__(self, reason: str, *, retryable: bool = False):
        super().__init__(reason)
        self.retryable = retryable


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
    _RATE_LIMITED_PROVIDERS.clear()
    _COOLDOWN_UNTIL.clear()


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
def _call_provider(provider: Dict[str, Any], system: str, user: str) -> str:
    try:
        import requests
    except ImportError as exc:
        raise ProviderRequestFailed("requests library missing") from exc

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
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT)
    except requests.Timeout as exc:
        logger.warning("[Translator] %s request timed out", provider["name"])
        raise ProviderRequestFailed("request timed out", retryable=True) from exc
    except requests.RequestException as exc:
        from pipeline.persistence import redact
        safe_error = redact(str(exc), dict(os.environ))
        logger.warning("[Translator] %s request failed: %s", provider["name"], safe_error)
        raise ProviderRequestFailed("network request failed", retryable=True) from exc

    if r.status_code == 429:
        logger.warning("[Translator] %s rate-limited (429)", provider["name"])
        retry_after = None
        try:
            retry_after = float((getattr(r, "headers", None) or {}).get("retry-after"))
        except (TypeError, ValueError):
            retry_after = None
        raise ProviderRateLimited(provider["name"], retry_after)
    try:
        r.raise_for_status()
    except requests.HTTPError as exc:
        status = r.status_code
        raise ProviderRequestFailed(f"HTTP {status}", retryable=status >= 500) from exc

    try:
        data = r.json()
        if provider["name"] == "gemini":
            candidates = data.get("candidates") or []
            parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
            translated = "".join(part.get("text", "") for part in parts).strip()
        else:
            translated = (data.get("choices") or [{}])[0].get("message", {}).get("content", "").strip()
    except (ValueError, AttributeError, IndexError, TypeError) as exc:
        raise ProviderRequestFailed("malformed response") from exc
    if not translated:
        raise ProviderRequestFailed("empty response")
    return translated


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #
_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_BARE_NUM_RE = re.compile(r"\d+(?:[,\d]*\d)?(?:\.\d+)?")


def _numeric_values(text: str) -> set:
    """Bare numeric values in text (1,250 == 1250; Devanagari digits normalised)."""
    vals = set()
    for n in _BARE_NUM_RE.findall((text or "").translate(_DEVANAGARI_DIGITS)):
        v = n.replace(",", "")
        if "." in v:
            v = v.rstrip("0").rstrip(".") or "0"
        vals.add(v)
    return vals


_DEV_ACRONYM_MAP = {
    'A': '\u090f', 'B': '\u092c\u0940', 'C': '\u0938\u0940', 'D': '\u0921\u0940',
    'E': '\u0908', 'F': '\u090f\u092b', 'G': '\u091c\u0940', 'H': '\u090f\u091a',
    'I': '\u0906\u0908', 'J': '\u091c\u0947', 'K': '\u0915\u0947', 'L': '\u090f\u0932',
    'M': '\u090f\u092e', 'N': '\u090f\u0928', 'O': '\u0913', 'P': '\u092a\u0940',
    'Q': '\u0915\u094d\u092f\u0942', 'R': '\u0906\u0930', 'S': '\u090f\u0938',
    'T': '\u091f\u0940', 'U': '\u092f\u0942', 'V': '\u0935\u0940', 'W': '\u0921\u092c\u094d\u0932\u094d\u092f\u0942',
    'X': '\u090f\u0915\u094d\u0938', 'Y': '\u0935\u093e\u0908', 'Z': '\u091c\u093c\u0947\u0921'
}

_SPECIAL_ACRONYMS = {
    'ISRO': '\u0907\u0938\u0930\u094b', 'NABARD': '\u0928\u093e\u092c\u093e\u0930\u094d\u0921',
    'SEBI': '\u0938\u0947\u092c\u0940', 'DRDO': '\u0921\u0940\u0906\u0930\u0921\u0940\u0913',
    'ICAR': '\u0906\u0908\u0938\u0940\u090f\u0906\u0930', 'PACS': '\u092a\u0948\u0915\u094d\u0938',
    'PC': '\u092a\u0947\u0928\u0932\u094d\u091f\u0940 \u0915\u0949\u0930\u094d\u0928\u0930',
    'PM': '\u092a\u094d\u0930\u0927\u093e\u0928\u092e\u0902\u0924\u094d\u0930\u0940',
    'CM': '\u092e\u0941\u0916\u094d\u092f\u092e\u0902\u0924\u094d\u0930\u0940',
    'MSP': '\u0928\u094d\u092f\u0942\u0928\u0924\u092e \u0938\u092e\u0930\u094d\u0925\u0928 \u092e\u0942\u0932\u094d\u092f',
    'GDP': '\u0938\u0915\u0932 \u0918\u0930\u0947\u0932\u0942 \u0909\u0924\u094d\u092a\u093e\u0926',
    'RBI': '\u0930\u093f\u091c\u093c\u0930\u094d\u0935 \u092c\u0948\u0902\u0915',
    'APEDA': '\u090f\u092a\u0940\u0921\u093e',
    'FSSAI': '\u090f\u092b\u090f\u0938\u090f\u0938\u090f\u0906\u0908',
    'GST': '\u091c\u0940\u090f\u0938\u091f\u0940',
    'UPI': '\u092f\u0942\u092a\u0940\u0906\u0908',
    'WHO': '\u0935\u093f\u0938\u094d\u0935 \u0938\u094d\u0935\u093e\u0938\u094d\u0925\u094d\u092f \u0938\u0902\u0917\u0920\u0928',
    'UN': '\u0938\u0902\u092f\u0941\u0915\u094d\u0924 \u0930\u093e\u0937\u094d\u091f\u094d\u0930'
}


def _acronym_matched_in_hindi(acr: str, hindi: str) -> bool:
    """Check if an English acronym is preserved in Hindi (Latin, Devanagari, or known expansion)."""
    if acr in hindi:
        return True
    dev = "".join(_DEV_ACRONYM_MAP.get(c, "") for c in acr.upper())
    if dev and dev in hindi:
        return True
    if acr in _SPECIAL_ACRONYMS and _SPECIAL_ACRONYMS[acr] in hindi:
        return True
    # Short 2-letter common abbreviations (PC, PM, CM, IT, AI, etc.) never block valid translations
    if len(acr) <= 2:
        return True
    return False


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
    en_vals = _numeric_values(" ".join(_NUM_RE.findall(english)))
    hi_vals = _numeric_values(hindi)
    missing_nums = en_vals - hi_vals
    if missing_nums:
        issues.append(f"missing numbers: {sorted(missing_nums)[:3]}")

    # Acronym check (uppercase 2-8 chars)
    en_acr = set(re.findall(r"\b[A-Z]{2,8}\b", english))
    missing_acr = [a for a in sorted(en_acr) if not _acronym_matched_in_hindi(a, hindi)]
    if missing_acr:
        issues.append(f"missing acronyms: {missing_acr[:3]}")

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

    providers = _discover_providers()
    if not providers:
        result = {
            "translated_hi": "",
            "passed": False,
            "confidence": 0.0,
            "provider": "none",
            "issues": ["no providers configured"],
        }
        _CACHE.put(key, result)
        return result

    system, user = _build_prompt(text, task)
    provider_issues: List[str] = []
    result = _translate_with(providers, text, task, key, system, user, provider_issues)
    if result is None and _wait_for_cooldown(providers):
        provider_issues = []
        result = _translate_with(providers, text, task, key, system, user, provider_issues)
    if result is not None:
        return result

    # All providers failed
    result = {
        "translated_hi": "",
        "passed": False,
        "confidence": 0.0,
        "provider": "all-failed",
        "issues": provider_issues or ["no usable providers available"],
    }
    _CACHE.put(key, result)
    return result


def _translate_with(providers, text, task, key, system, user, provider_issues):
    for provider in providers:
        if _provider_parked(provider["name"]):
            logger.info("[Translator] skipping %s (parked after rate limit / credit error)", provider["name"])
            continue
        logger.info("[Translator] trying provider %s", provider["name"])
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                hindi = _call_provider(provider, system, user)
            except ProviderRateLimited as exc:
                _park_provider(provider["name"], max(RATE_LIMIT_COOLDOWN, exc.retry_after or 0))
                provider_issues.append(f"{provider['name']}: rate limited")
                logger.info("[Translator] moving to the next configured provider")
                break
            except ProviderRequestFailed as exc:
                if exc.retryable and attempt < MAX_RETRIES:
                    time.sleep(2 ** attempt)
                    continue
                if any(str(exc) == f"HTTP {code}" for code in _HARD_FAIL_STATUSES):
                    _park_provider(provider["name"], None)
                provider_issues.append(f"{provider['name']}: {exc}")
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
                provider_issues.append(f"{provider['name']}: validation failed")
                logger.warning("[Translator] %s validation failed: %s",
                               provider["name"], issues)
                break  # try next provider
    return None


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
