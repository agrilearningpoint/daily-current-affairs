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
        "repaired": list[str],     # acronyms appended by auto-repair (may be absent)
    }

Acronym validation (2026-11-10, run 42789471273):
    An ALL-CAPS source is a headline, not an acronym list — "PRESIDENT OF INDIA
    INAUGURATES ... IN NEW DELHI" made the validator demand DELHI/INDIA/NEW back
    in Latin, every provider was rejected for the same correct line, and the run
    fell below the QA floor. So: ALL-CAPS sources only enforce the curated
    _KNOWN_ACRONYMS list, Hindi renderings of caps words/place names count as
    matched, and natural transliterations (ट्राई for TRAI) count as matched.
    If a curated acronym is genuinely absent and it is the *only* problem, it is
    appended as one trailing parenthetical and the line is re-validated; anything
    else (missing numbers, no Devanagari, English left over) still fails closed.

Env switches:
    ALP_TRANSLATION_STRICT=1     # fail-closed (no dictionary fallback)
    ALP_TRANSLATION_TIMEOUT=45   # per-provider timeout (seconds)
    ALP_TRANSLATION_MAX_RETRIES=2
    ALP_TRANSLATION_AUTO_REPAIR=0        # disable the acronym repair (kill switch)
    ALP_TRANSLATION_MAX_ACRONYM_REPAIRS=2  # acronyms appended per line (0 = off)
"""
from __future__ import annotations

from pipeline.ai_usage import record_ai_usage
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
# Two silent holes closed (2026-11-10, measured against 512 real EN/HI pairs from
# published editions - zero new rejections):
#   1. \d{1,3} never matched an ungrouped 4+ digit figure, so "5000 crore",
#      "12500 crore" and "3500 tonnes" were not required in the Hindi at all.
#      Comma-grouped figures ("Rs. 5,000 crore") were, so the gate depended on how
#      the source happened to be punctuated.
#   2. The trailing \b could never match after "%", a non-word character followed by
#      a space - so no percentage was ever demanded. Word units are unaffected, and
#      mcq_quality.py:_NUM_RE already uses a lookahead for the same reason.
#      %(?![0-9A-Fa-f]{2}) keeps percent-encoded URL escapes ("%281945") out.
_NUM_RE = re.compile(
    r"(?:(?:Rs\.?|INR|USD|₹|US\$|\$)\s?\d+(?:,\d{2,3})*(?:\.\d+)?(?:\s?(?:crore|lakh|billion|million|trillion|thousand|Cr|bn|mn)\b)?)"
    r"|(?:\b\d+(?:,\d{2,3})*(?:\.\d+)?\s?"
    r"(?:%(?![0-9A-Fa-f]{2})|\b(?:percent|per cent|bps|days?|years?|months?|weeks?|tonnes?|hectares?|bn|billion|million|trillion|crore|lakh)\b))",
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
    router = _router()
    left = router.ai_time_left() if router is not None else None
    if left is not None and delay >= left:
        return False  # waiting would run past the stage AI budget
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
    def __init__(self, reason: str, *, retryable: bool = False, timeout: bool = False):
        super().__init__(reason)
        self.retryable = retryable
        self.timeout = timeout


# A translation that fails validation on this many providers is content-specific
# (e.g. an all-caps word read as an acronym), not a provider problem: stop instead
# of walking every provider (run 41513421804 spent minutes per line doing that).
MAX_VALIDATION_FAILS = int(os.getenv("ALP_TRANSLATION_MAX_VALIDATION_FAILS", "2"))


def _router():
    try:
        from pipeline import ai_router
        return ai_router
    except Exception:  # pragma: no cover - router module missing
        return None


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

    # Fallback: env-based single provider (generic OpenAI-compatible endpoint).
    # Only used when the router yields nothing at all; LLM_API_URL/LLM_API_KEY are
    # the same vars the router's "generic-openai" provider reads.
    if not providers:
        url = os.getenv("LLM_API_URL")
        key = os.getenv("LLM_API_KEY")
        model = os.getenv("ALP_LLM") or os.getenv("LLM_MODEL") or "auto"
        if url and key:
            endpoint = url.rstrip("/")
            if not endpoint.endswith("/chat/completions"):
                endpoint = f"{endpoint}/chat/completions"
            providers.append({
                "name": "generic-fallback",
                "url": endpoint,
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
    try:  # official Hindi names (ZSI = भारतीय प्राणी सर्वेक्षण, Act = अधिनियम ...)
        from pipeline.hindi_postfix import glossary_hint
        hint = glossary_hint(text)
    except Exception:
        hint = ""
    if hint:
        system += "\n6. Use these official Hindi names exactly:\n" + hint
    system += ("\n7. Never mix scripts inside a word; translate 'Act' as अधिनियम (विधेयक only for a Bill) "
               "and 'Parent Ministry' as मूल मंत्रालय."
               "\n8. Preserve direction/polarity exactly: hike is not cut, approve is not reject, "
               "rise is not fall; render 'hot CPI/inflation' as उच्च मुद्रास्फीति, never word-for-word.")
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
        router = _router()
        timeout = min(TIMEOUT, router.request_timeout(provider["name"])) if router else TIMEOUT
        r = requests.post(url, headers=headers, json=payload, timeout=timeout)
    except requests.Timeout as exc:
        logger.warning("[Translator] %s request timed out", provider["name"])
        raise ProviderRequestFailed("request timed out", timeout=True) from exc
    except requests.RequestException as exc:
        from pipeline.persistence import redact
        safe_error = redact(str(exc), dict(os.environ))
        logger.warning("[Translator] %s request failed: %s", provider["name"], safe_error)
        raise ProviderRequestFailed("network request failed", retryable=True) from exc

    if r.status_code == 429:
        logger.warning("[Translator] %s rate-limited (429)", provider["name"])
        retry_after = None
        router = _router()
        if router is not None:
            retry_after = router.parse_retry_after(getattr(r, "headers", None),
                                                   str(getattr(r, "text", "") or "")[:4000])
        else:
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


# Natural Hindi transliterations news copy actually uses. The letter-by-letter
# map above only produces टीआरएआई; a correct line saying ट्राई must match too,
# otherwise the line is rejected — or "repaired" with a token it already has.
_ACRONYM_HI_VARIANTS = {
    'TRAI': ('ट्राई', 'ट्राइ'),
    'GIZ': ('जीआईजेड', 'जीआईज़ेड'),
    'NITI': ('नीति', 'नीति आयोग'),
    'HADR': ('हाद्र',),
    'BRICS': ('ब्रिक्स',),
    'SAARC': ('सार्क',),
    'OPEC': ('ओपेक',),
    'NATO': ('नाटो',),
    'NAFED': ('नाफेद', 'नाफेड'),
    'PACS': ('पैक्स',),
    'IRDAI': ('इरदाई', 'इरडाई'),
    'SIDBI': ('सिडबी',),
    'ECI': ('चुनाव आयोग',),
    'KCC': ('किसान क्रेडिट कार्ड',),
    'PDS': ('सार्वजनिक वितरण प्रणाली',),
    'RBI': ('आरबीआई',),
    'MSP': ('समर्थन मूल्य', 'न्यूनतम समर्थन मूल्य'),
    'FCI': ('खाद्य निगम',),
    'CACP': ('कृषि लागत और मूल्य आयोग',),
    'FSSAI': ('खाद्य सुरक्षा प्राधिकरण',),
    'ISRO': ('अंतरिक्ष अनुसंधान संगठन',),
    'NDRF': ('आपदा मोचन बल',),
    'MGNREGA': ('मनरेगा',),
    'UPSC': ('संघ लोक सेवा आयोग',),
    'GST': ('वस्तु एवं सेवा कर',),
    'UPI': ('यूपीआई',),
    'UN': ('संयुक्त राष्ट्र',),
    'WHO': ('विश्व स्वास्थ्य संगठन',),
    'WTO': ('विश्व व्यापार संगठन',),
}

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


# --------------------------------------------------------------------------- #
# Acronym auto-repair (added 2026-11-10)
# --------------------------------------------------------------------------- #
# Run 42789471273 lost 6 of 15 stories to "missing acronyms" although every one
# of those translations was correct: the sources were ALL-CAPS headlines, so the
# uppercase-token check flagged ordinary words (BATCH, CONDUCT, DELHI, INDIA,
# NEW) and every provider was rejected for the same line.  Two conservative fixes:
#
# 1. matching is punctuation-tolerant (PTI also matches an answer written with
#    dots between the letters) and accepts the Hindi rendering of an ALL-CAPS
#    English word or place name (BATCH -> batch-word, CHENNAI -> the city name);
#    nothing is rewritten in this step;
# 2. a genuinely absent acronym is appended as one parenthetical and the line is
#    re-validated.  Repairs are capped, and never bypass another gate:
#    Devanagari, numbers, garbled text and length all still have to pass.
#
# Kill switch: ALP_TRANSLATION_AUTO_REPAIR=0 restores the old reject-only behaviour.
AUTO_REPAIR = os.getenv("ALP_TRANSLATION_AUTO_REPAIR", "1") == "1"
MAX_ACRONYM_REPAIRS = int(os.getenv("ALP_TRANSLATION_MAX_ACRONYM_REPAIRS", "2"))
REPAIRED_CONFIDENCE_CAP = 0.9

# ALL-CAPS English words / place names that reach the validator from
# headline-style sources, with the Hindi renderings that prove the token was
# translated rather than dropped.
_CAPS_WORD_HI = {
    "ACCIDENT": ("\u0926\u0941\u0930\u094d\u0918\u091f\u0928\u093e",),
    "ACCIDENTS": ("\u0926\u0941\u0930\u094d\u0918\u091f\u0928\u093e\u090f\u0902",),
    "AFGHANISTAN": ("\u0905\u092b\u0917\u093e\u0928\u093f\u0938\u094d\u0924\u093e\u0928",),
    "AGARTALA": ("\u0905\u0917\u0930\u0924\u0932\u093e",),
    "AGRA": ("\u0906\u0917\u0930\u093e",),
    "AGREEMENT": ("\u0938\u092e\u091d\u094c\u0924\u093e", "\u0915\u0930\u093e\u0930",),
    "AGRICULTURE": ("\u0915\u0943\u0937\u093f", "\u0916\u0947\u0924\u0940",),
    "AHMEDABAD": ("\u0905\u0939\u092e\u0926\u093e\u092c\u093e\u0926",),
    "AIRPORT": ("\u0939\u0935\u093e\u0908 \u0905\u0921\u094d\u0921\u093e",),
    "AIZAWL": ("\u0906\u0907\u091c\u094b\u0932",),
    "AMERICA": ("\u0905\u092e\u0947\u0930\u093f\u0915\u093e",),
    "AMRITSAR": ("\u0905\u092e\u0943\u0924\u0938\u0930",),
    "ANDAMAN": ("\u0905\u0902\u0921\u092e\u093e\u0928",),
    "ANDHRA": ("\u0906\u0902\u0927\u094d\u0930",),
    "ANNOUNCED": ("\u0918\u094b\u0937\u0923\u093e", "\u0918\u094b\u0937\u093f\u0924",),
    "ANNOUNCEMENT": ("\u0918\u094b\u0937\u0923\u093e",),
    "APPROVAL": ("\u0938\u094d\u0935\u0940\u0915\u0943\u0924\u093f", "\u092e\u0902\u091c\u0942\u0930\u0940",),
    "APPROVED": ("\u0938\u094d\u0935\u0940\u0915\u0943\u0924", "\u092e\u0902\u091c\u0942\u0930", "\u0938\u094d\u0935\u0940\u0915\u0943\u0924\u093f",),
    "ARMY": ("\u0938\u0947\u0928\u093e",),
    "ASSAM": ("\u0905\u0938\u092e",),
    "ASSEMBLY": ("\u0935\u093f\u0927\u093e\u0928\u0938\u092d\u093e",),
    "AUTHORITY": ("\u092a\u094d\u0930\u093e\u0927\u093f\u0915\u0930\u0923",),
    "AWARD": ("\u092a\u0941\u0930\u0938\u094d\u0915\u093e\u0930", "\u0938\u092e\u094d\u092e\u093e\u0928",),
    "AWARDS": ("\u092a\u0941\u0930\u0938\u094d\u0915\u093e\u0930", "\u0938\u092e\u094d\u092e\u093e\u0928",),
    "AYODHYA": ("\u0905\u092f\u094b\u0927\u094d\u092f\u093e",),
    "BANGLADESH": ("\u092c\u093e\u0902\u0917\u094d\u0932\u093e\u0926\u0947\u0936",),
    "BANK": ("\u092c\u0948\u0902\u0915",),
    "BATCH": ("\u092c\u0948\u091a", "\u0916\u0947\u092a",),
    "BEIJING": ("\u092c\u0940\u091c\u093f\u0902\u0917",),
    "BENGALURU": ("\u092c\u0947\u0902\u0917\u0932\u0941\u0930\u0941",),
    "BHOPAL": ("\u092d\u094b\u092a\u093e\u0932",),
    "BHUBANESWAR": ("\u092d\u0941\u0935\u0928\u0947\u0936\u094d\u0935\u0930",),
    "BHUTAN": ("\u092d\u0942\u091f\u093e\u0928",),
    "BIHAR": ("\u092c\u093f\u0939\u093e\u0930",),
    "BILLION": ("\u0905\u0930\u092c",),
    "BOARD": ("\u092c\u094b\u0930\u094d\u0921",),
    "BOMBAY": ("\u092e\u0941\u0902\u092c\u0908",),
    "BROADCASTERS": ("\u092a\u094d\u0930\u0938\u093e\u0930\u0915",),
    "CABINET": ("\u0915\u0948\u092c\u093f\u0928\u0947\u091f",),
    "CALCUTTA": ("\u0915\u094b\u0932\u0915\u093e\u0924\u093e",),
    "CENTER": ("\u0915\u0947\u0902\u0926\u094d\u0930",),
    "CENTRE": ("\u0915\u0947\u0902\u0926\u094d\u0930",),
    "CHAIRS": ("\u0905\u0927\u094d\u092f\u0915\u094d\u0937\u0924\u093e",),
    "CHANDIGARH": ("\u091a\u0902\u0921\u0940\u0917\u0922\u093c",),
    "CHENNAI": ("\u091a\u0947\u0928\u094d\u0928\u0908",),
    "CHHATTISGARH": ("\u091b\u0924\u094d\u0924\u0940\u0938\u0917\u0922\u093c",),
    "CHILKA": ("\u091a\u093f\u0932\u094d\u0915\u093e", "\u091a\u093f\u0932\u0915\u093e",),
    "CHINA": ("\u091a\u0940\u0928",),
    "CLIMATE": ("\u091c\u0932\u0935\u093e\u092f\u0941",),
    "COIMBATORE": ("\u0915\u094b\u092f\u0902\u092c\u091f\u0942\u0930",),
    "COMMISSION": ("\u0906\u092f\u094b\u0917",),
    "COMMITTEE": ("\u0938\u092e\u093f\u0924\u093f",),
    "COMPENSATION": ("\u092e\u0941\u0906\u0935\u091c\u093e",),
    "CONDUCT": ("\u0938\u0902\u091a\u093e\u0932\u0928", "\u0906\u092f\u094b\u091c\u093f\u0924", "\u0906\u092f\u094b\u091c\u0928", "\u0915\u0930\u093e\u092f\u093e", "\u0915\u093f\u092f\u093e",),
    "CONDUCTED": ("\u0938\u0902\u091a\u093e\u0932\u093f\u0924", "\u0906\u092f\u094b\u091c\u093f\u0924", "\u0915\u0930\u093e\u092f\u093e",),
    "COOPERATIVE": ("\u0938\u0939\u0915\u093e\u0930\u0940",),
    "COOPERATIVES": ("\u0938\u0939\u0915\u093e\u0930\u0940",),
    "CORRIDOR": ("\u0915\u0949\u0930\u093f\u0921\u094b\u0930",),
    "COUNTRY": ("\u0926\u0947\u0936",),
    "CROP": ("\u092b\u0938\u0932",),
    "CROPS": ("\u092b\u0938\u0932",),
    "CRORE": ("\u0915\u0930\u094b\u0921\u093c",),
    "CRORES": ("\u0915\u0930\u094b\u0921\u093c",),
    "CUSTOMS": ("\u0938\u0940\u092e\u093e \u0936\u0941\u0932\u094d\u0915",),
    "DAILY": ("\u0926\u0948\u0928\u093f\u0915",),
    "DAMAN": ("\u0926\u092e\u0928",),
    "DEFENCE": ("\u0930\u0915\u094d\u0937\u093e",),
    "DEHRADUN": ("\u0926\u0947\u0939\u0930\u093e\u0926\u0942\u0928",),
    "DELHI": ("\u0926\u093f\u0932\u094d\u0932\u0940",),
    "DEPARTMENT": ("\u0935\u093f\u092d\u093e\u0917",),
    "DISTRICT": ("\u091c\u093f\u0932\u093e",),
    "DISTRICTS": ("\u091c\u093f\u0932\u093e",),
    "DROUGHT": ("\u0938\u0942\u0916\u093e",),
    "DUBAI": ("\u0926\u0941\u092c\u0908",),
    "DUTY": ("\u0936\u0941\u0932\u094d\u0915",),
    "EDUCATION": ("\u0936\u093f\u0915\u094d\u0937\u093e",),
    "ELECTION": ("\u091a\u0941\u0928\u093e\u0935",),
    "ELECTIONS": ("\u091a\u0941\u0928\u093e\u0935",),
    "ENERGY": ("\u090a\u0930\u094d\u091c\u093e",),
    "EUROPE": ("\u092f\u0942\u0930\u094b\u092a",),
    "EXERCISE": ("\u0905\u092d\u094d\u092f\u093e\u0938",),
    "EXPORT": ("\u0928\u093f\u0930\u094d\u092f\u093e\u0924",),
    "EXPORTS": ("\u0928\u093f\u0930\u094d\u092f\u093e\u0924",),
    "EXPRESSWAY": ("\u090f\u0915\u094d\u0938\u092a\u094d\u0930\u0947\u0938\u0935\u0947",),
    "FARMER": ("\u0915\u093f\u0938\u093e\u0928",),
    "FARMERS": ("\u0915\u093f\u0938\u093e\u0928",),
    "FIRST": ("\u092a\u0939\u0932\u0940", "\u092a\u0939\u0932\u093e", "\u092a\u094d\u0930\u0925\u092e",),
    "FISH": ("\u092e\u0924\u094d\u0938\u094d\u092f", "\u092e\u091b\u0932\u0940",),
    "FISHERIES": ("\u092e\u0924\u094d\u0938\u094d\u092f", "\u092e\u091b\u0932\u0940",),
    "FLIGHT": ("\u0909\u0921\u093c\u093e\u0928",),
    "FLOOD": ("\u092c\u093e\u0922\u093c",),
    "FLOODS": ("\u092c\u093e\u0922\u093c",),
    "FOOD": ("\u0916\u093e\u0926\u094d\u092f", "\u092d\u094b\u091c\u0928",),
    "FOREIGN": ("\u0935\u093f\u0926\u0947\u0936\u0940",),
    "FUND": ("\u0915\u094b\u0937", "\u0928\u093f\u0927\u093f", "\u092b\u0902\u0921",),
    "FUNDS": ("\u0915\u094b\u0937", "\u0928\u093f\u0927\u093f", "\u092b\u0902\u0921",),
    "GANGTOK": ("\u0917\u0902\u0917\u091f\u094b\u0915",),
    "GAZA": ("\u0917\u093e\u091c\u093e",),
    "GLOBAL": ("\u0935\u0948\u0936\u094d\u0935\u093f\u0915",),
    "GOA": ("\u0917\u094b\u0935\u093e",),
    "GOVERNMENT": ("\u0938\u0930\u0915\u093e\u0930", "\u0936\u093e\u0938\u0928", "\u0938\u0930\u0915\u093e\u0930\u0940",),
    "GUJARAT": ("\u0917\u0941\u091c\u0930\u093e\u0924",),
    "GUWAHATI": ("\u0917\u0941\u0935\u093e\u0939\u093e\u091f\u0940",),
    "HARYANA": ("\u0939\u0930\u093f\u092f\u093e\u0923\u093e",),
    "HEALTH": ("\u0938\u094d\u0935\u093e\u0938\u094d\u0925\u094d\u092f",),
    "HIGHEST": ("\u0909\u091a\u094d\u091a\u0924\u092e", "\u0938\u0930\u094d\u0935\u094b\u091a\u094d\u091a",),
    "HIGHWAY": ("\u0930\u093e\u091c\u092e\u093e\u0930\u094d\u0917",),
    "HIMACHAL": ("\u0939\u093f\u092e\u093e\u091a\u0932",),
    "HOLDS": ("\u092c\u0948\u0920\u0915", "\u0906\u092f\u094b\u091c\u093f\u0924",),
    "HYDERABAD": ("\u0939\u0948\u0926\u0930\u093e\u092c\u093e\u0926",),
    "IMPHAL": ("\u0907\u092e\u094d\u092b\u093e\u0932",),
    "IMPLEMENTATION": ("\u0915\u094d\u0930\u093f\u092f\u093e\u0928\u094d\u0935\u092f\u0928",),
    "IMPORT": ("\u0906\u092f\u093e\u0924",),
    "IMPORTS": ("\u0906\u092f\u093e\u0924",),
    "INAUGURATED": ("\u0909\u0926\u094d\u0918\u093e\u091f\u0928",),
    "INAUGURATES": ("\u0909\u0926\u094d\u0918\u093e\u091f\u0928",),
    "INDIA": ("\u092d\u093e\u0930\u0924", "\u0939\u093f\u0902\u0926\u0941\u0938\u094d\u0924\u093e\u0928", "\u092d\u093e\u0930\u0924\u0940\u092f",),
    "INDIAN": ("\u092d\u093e\u0930\u0924\u0940\u092f", "\u092d\u093e\u0930\u0924",),
    "INDORE": ("\u0907\u0902\u0926\u094c\u0930",),
    "INSTITUTE": ("\u0938\u0902\u0938\u094d\u0925\u093e\u0928",),
    "INSURANCE": ("\u092c\u0940\u092e\u093e",),
    "INTERNATIONAL": ("\u0905\u0902\u0924\u0930\u0930\u093e\u0937\u094d\u091f\u094d\u0930\u0940\u092f", "\u0905\u0928\u094d\u0924\u0930\u094d\u0930\u093e\u0937\u094d\u091f\u094d\u0930\u0940\u092f",),
    "IRAN": ("\u0908\u0930\u093e\u0928",),
    "IRAQ": ("\u0907\u0930\u093e\u0915",),
    "ISRAEL": ("\u0907\u091c\u0930\u093e\u0907\u0932",),
    "JAIPUR": ("\u091c\u092f\u092a\u0941\u0930",),
    "JAMMU": ("\u091c\u092e\u094d\u092e\u0942",),
    "JHARKHAND": ("\u091d\u093e\u0930\u0916\u0902\u0921",),
    "JOBS": ("\u0930\u094b\u091c\u0917\u093e\u0930", "\u0928\u094c\u0915\u0930\u0940",),
    "KANPUR": ("\u0915\u093e\u0928\u092a\u0941\u0930",),
    "KARNATAKA": ("\u0915\u0930\u094d\u0928\u093e\u091f\u0915",),
    "KASHMIR": ("\u0915\u0936\u094d\u092e\u0940\u0930",),
    "KERALA": ("\u0915\u0947\u0930\u0932",),
    "KOCHI": ("\u0915\u094b\u091a\u094d\u091a\u093f",),
    "KOHIMA": ("\u0915\u094b\u0939\u093f\u092e\u093e",),
    "KOLKATA": ("\u0915\u094b\u0932\u0915\u093e\u0924\u093e",),
    "KYIV": ("\u0915\u0940\u0935",),
    "LADAKH": ("\u0932\u0926\u094d\u0926\u093e\u0916",),
    "LAKH": ("\u0932\u093e\u0916",),
    "LAKHS": ("\u0932\u093e\u0916",),
    "LAUNCH": ("\u0936\u0941\u0930\u0942", "\u0932\u0949\u0928\u094d\u091a", "\u0909\u0926\u094d\u0918\u093e\u091f\u0928", "\u0936\u0941\u092d\u093e\u0930\u0902\u092d",),
    "LAUNCHED": ("\u0936\u0941\u0930\u0942", "\u0932\u0949\u0928\u094d\u091a", "\u0909\u0926\u094d\u0918\u093e\u091f\u0928", "\u0936\u0941\u092d\u093e\u0930\u0902\u092d",),
    "LOAN": ("\u090b\u0923",),
    "LOANS": ("\u090b\u0923",),
    "LONDON": ("\u0932\u0902\u0926\u0928",),
    "LUCKNOW": ("\u0932\u0916\u0928\u090a",),
    "LUDHIANA": ("\u0932\u0941\u0927\u093f\u092f\u093e\u0928\u093e",),
    "MADHYA": ("\u092e\u0927\u094d\u092f",),
    "MAHARASHTRA": ("\u092e\u0939\u093e\u0930\u093e\u0937\u094d\u091f\u094d\u0930",),
    "MANDI": ("\u092e\u0902\u0921\u0940",),
    "MANIPUR": ("\u092e\u0923\u093f\u092a\u0941\u0930",),
    "MARKET": ("\u092c\u093e\u091c\u093e\u0930",),
    "MATHURA": ("\u092e\u0925\u0941\u0930\u093e",),
    "MEERUT": ("\u092e\u0947\u0930\u0920",),
    "MEETING": ("\u092c\u0948\u0920\u0915",),
    "MEGHALAYA": ("\u092e\u0947\u0918\u093e\u0932\u092f",),
    "MELA": ("\u092e\u0947\u0932\u093e",),
    "MILK": ("\u0926\u0942\u0927",),
    "MINIMUM": ("\u0928\u094d\u092f\u0942\u0928\u0924\u092e",),
    "MINISTRY": ("\u092e\u0902\u0924\u094d\u0930\u093e\u0932\u092f",),
    "MISSION": ("\u092e\u093f\u0936\u0928", "\u0905\u092d\u093f\u092f\u093e\u0928",),
    "MIZORAM": ("\u092e\u093f\u091c\u094b\u0930\u092e",),
    "MONTHLY": ("\u092e\u093e\u0938\u093f\u0915",),
    "MORNING": ("\u0938\u0941\u092c\u0939",),
    "MOSCOW": ("\u092e\u0949\u0938\u094d\u0915\u094b",),
    "MUMBAI": ("\u092e\u0941\u0902\u092c\u0908",),
    "MYANMAR": ("\u092e\u094d\u092f\u093e\u0902\u092e\u093e\u0930",),
    "MYSURU": ("\u092e\u0948\u0938\u0942\u0930",),
    "NAGALAND": ("\u0928\u0917\u093e\u0932\u0948\u0902\u0921",),
    "NAGPUR": ("\u0928\u093e\u0917\u092a\u0941\u0930",),
    "NASHIK": ("\u0928\u093e\u0936\u093f\u0915",),
    "NATIONAL": ("\u0930\u093e\u0937\u094d\u091f\u094d\u0930\u0940\u092f",),
    "NEPAL": ("\u0928\u0947\u092a\u093e\u0932",),
    "NEW": ("\u0928\u0908", "\u0928\u092f\u093e", "\u0928\u092f\u0947", "\u0928\u090f", "\u0928\u0935",),
    "NICOBAR": ("\u0928\u093f\u0915\u094b\u092c\u093e\u0930",),
    "NOTIFIED": ("\u0905\u0927\u093f\u0938\u0942\u091a\u093f\u0924",),
    "ODISHA": ("\u0913\u0921\u093f\u0936\u093e",),
    "ORDER": ("\u0906\u0926\u0947\u0936",),
    "ORGANIC": ("\u091c\u0948\u0935\u093f\u0915",),
    "PAKISTAN": ("\u092a\u093e\u0915\u093f\u0938\u094d\u0924\u093e\u0928",),
    "PANAJI": ("\u092a\u0923\u091c\u0940",),
    "PANCHAYAT": ("\u092a\u0902\u091a\u093e\u092f\u0924",),
    "PARIS": ("\u092a\u0947\u0930\u093f\u0938",),
    "PARLIAMENT": ("\u0938\u0902\u0938\u0926",),
    "PATNA": ("\u092a\u091f\u0928\u093e",),
    "PERCENT": ("\u092a\u094d\u0930\u0924\u093f\u0936\u0924",),
    "POLICY": ("\u0928\u0940\u0924\u093f",),
    "PORT": ("\u092c\u0902\u0926\u0930\u0917\u093e\u0939",),
    "POWER": ("\u092c\u093f\u091c\u0932\u0940", "\u090a\u0930\u094d\u091c\u093e", "\u0936\u0915\u094d\u0924\u093f",),
    "PRADESH": ("\u092a\u094d\u0930\u0926\u0947\u0936",),
    "PRAYAGRAJ": ("\u092a\u094d\u0930\u092f\u093e\u0917\u0930\u093e\u091c",),
    "PRESIDENT": ("\u0930\u093e\u0937\u094d\u091f\u094d\u0930\u092a\u0924\u093f", "\u0905\u0927\u094d\u092f\u0915\u094d\u0937",),
    "PRICE": ("\u092e\u0942\u0932\u094d\u092f", "\u0915\u0940\u092e\u0924", "\u0926\u093e\u092e",),
    "PRICES": ("\u092e\u0942\u0932\u094d\u092f", "\u0915\u0940\u092e\u0924\u0947\u0902", "\u0926\u093e\u092e",),
    "PRIME": ("\u092a\u094d\u0930\u0927\u093e\u0928",),
    "PROGRAM": ("\u0915\u093e\u0930\u094d\u092f\u0915\u094d\u0930\u092e",),
    "PROGRAMME": ("\u0915\u093e\u0930\u094d\u092f\u0915\u094d\u0930\u092e",),
    "PROJECT": ("\u092a\u0930\u093f\u092f\u094b\u091c\u0928\u093e",),
    "PROTEST": ("\u0935\u093f\u0930\u094b\u0927", "\u092a\u094d\u0930\u0926\u0930\u094d\u0936\u0928",),
    "PROTESTS": ("\u0935\u093f\u0930\u094b\u0927", "\u092a\u094d\u0930\u0926\u0930\u094d\u0936\u0928",),
    "PUNE": ("\u092a\u0941\u0923\u0947",),
    "PUNJAB": ("\u092a\u0902\u091c\u093e\u092c",),
    "RAIL": ("\u0930\u0947\u0932",),
    "RAILWAY": ("\u0930\u0947\u0932\u0935\u0947", "\u0930\u0947\u0932",),
    "RAILWAYS": ("\u0930\u0947\u0932\u0935\u0947", "\u0930\u0947\u0932",),
    "RAIN": ("\u092c\u093e\u0930\u093f\u0936",),
    "RAINS": ("\u092c\u093e\u0930\u093f\u0936",),
    "RAIPUR": ("\u0930\u093e\u092f\u092a\u0941\u0930",),
    "RAJASTHAN": ("\u0930\u093e\u091c\u0938\u094d\u0925\u093e\u0928",),
    "RALLY": ("\u0930\u0948\u0932\u0940",),
    "RANCHI": ("\u0930\u093e\u0902\u091a\u0940",),
    "RECORD": ("\u0930\u093f\u0915\u0949\u0930\u094d\u0921",),
    "RELEASE": ("\u091c\u093e\u0930\u0940",),
    "RELEASED": ("\u091c\u093e\u0930\u0940", "\u0930\u093f\u0932\u0940\u091c",),
    "REPORT": ("\u0930\u093f\u092a\u094b\u0930\u094d\u091f",),
    "RESCUE": ("\u092c\u091a\u093e\u0935",),
    "RESULT": ("\u092a\u0930\u093f\u0923\u093e\u092e", "\u0928\u0924\u0940\u091c\u093e",),
    "RESULTS": ("\u092a\u0930\u093f\u0923\u093e\u092e", "\u0928\u0924\u0940\u091c\u0947",),
    "REVENUE": ("\u0930\u093e\u091c\u0938\u094d\u0935",),
    "REVIEW": ("\u0938\u092e\u0940\u0915\u094d\u0937\u093e",),
    "RICE": ("\u091a\u093e\u0935\u0932", "\u0927\u093e\u0928",),
    "ROAD": ("\u0938\u0921\u093c\u0915",),
    "ROADS": ("\u0938\u0921\u093c\u0915",),
    "RURAL": ("\u0917\u094d\u0930\u093e\u092e\u0940\u0923",),
    "RUSSIA": ("\u0930\u0942\u0938",),
    "SCHEME": ("\u092f\u094b\u091c\u0928\u093e",),
    "SECURITY": ("\u0938\u0941\u0930\u0915\u094d\u0937\u093e",),
    "SEED": ("\u092c\u0940\u091c",),
    "SEEDS": ("\u092c\u0940\u091c",),
    "SHILLONG": ("\u0936\u093f\u0932\u093e\u0902\u0917",),
    "SHIMLA": ("\u0936\u093f\u092e\u0932\u093e",),
    "SIGN": ("\u0939\u0938\u094d\u0924\u093e\u0915\u094d\u0937\u0930",),
    "SIGNED": ("\u0939\u0938\u094d\u0924\u093e\u0915\u094d\u0937\u0930",),
    "SIGNS": ("\u0939\u0938\u094d\u0924\u093e\u0915\u094d\u0937\u0930",),
    "SIKKIM": ("\u0938\u093f\u0915\u094d\u0915\u093f\u092e",),
    "SILIGURI": ("\u0938\u093f\u0932\u0940\u0917\u0941\u0921\u093c\u0940",),
    "SOLAR": ("\u0938\u094c\u0930",),
    "SRI": ("\u0936\u094d\u0930\u0940",),
    "SRILANKA": ("\u0936\u094d\u0930\u0940\u0932\u0902\u0915\u093e",),
    "SRINAGAR": ("\u0936\u094d\u0930\u0940\u0928\u0917\u0930",),
    "STATE": ("\u0930\u093e\u091c\u094d\u092f",),
    "STATEMENT": ("\u092c\u092f\u093e\u0928",),
    "STUDENTS": ("\u091b\u093e\u0924\u094d\u0930", "\u0935\u093f\u0926\u094d\u092f\u093e\u0930\u094d\u0925\u0940",),
    "SUBSIDIES": ("\u0938\u092c\u094d\u0938\u093f\u0921\u0940",),
    "SUBSIDY": ("\u0938\u092c\u094d\u0938\u093f\u0921\u0940",),
    "SUGAR": ("\u091a\u0940\u0928\u0940",),
    "SUMMIT": ("\u0936\u093f\u0916\u0930 \u0938\u092e\u094d\u092e\u0947\u0932\u0928", "\u0938\u092e\u094d\u092e\u0947\u0932\u0928",),
    "SUPPORT": ("\u0938\u092e\u0930\u094d\u0925\u0928", "\u0938\u0939\u093e\u092f\u0924\u093e",),
    "SURAT": ("\u0938\u0942\u0930\u0924",),
    "TARGET": ("\u0932\u0915\u094d\u0937\u094d\u092f",),
    "TARIFF": ("\u091f\u0948\u0930\u093f\u092b", "\u0936\u0941\u0932\u094d\u0915",),
    "TAX": ("\u0915\u0930",),
    "TELANGANA": ("\u0924\u0947\u0932\u0902\u0917\u093e\u0928\u093e",),
    "TENDER": ("\u091f\u0947\u0902\u0921\u0930",),
    "THIRUVANANTHAPURAM": ("\u0924\u093f\u0930\u0941\u0935\u0928\u0902\u0924\u092a\u0941\u0930\u092e",),
    "TODAY": ("\u0906\u091c",),
    "TOKYO": ("\u091f\u094b\u0915\u094d\u092f\u094b",),
    "TRADE": ("\u0935\u094d\u092f\u093e\u092a\u093e\u0930",),
    "TRAIN": ("\u091f\u094d\u0930\u0947\u0928",),
    "TRIPURA": ("\u0924\u094d\u0930\u093f\u092a\u0941\u0930\u093e",),
    "UDAIPUR": ("\u0909\u0926\u092f\u092a\u0941\u0930",),
    "UKRAINE": ("\u092f\u0942\u0915\u094d\u0930\u0947\u0928",),
    "UNION": ("\u0938\u0902\u0918",),
    "UNIVERSITY": ("\u0935\u093f\u0936\u094d\u0935\u0935\u093f\u0926\u094d\u092f\u093e\u0932\u092f",),
    "USA": ("\u0905\u092e\u0947\u0930\u093f\u0915\u093e", "\u092f\u0942\u090f\u0938\u090f",),
    "UTTAR": ("\u0909\u0924\u094d\u0924\u0930",),
    "UTTARAKHAND": ("\u0909\u0924\u094d\u0924\u0930\u093e\u0916\u0902\u0921",),
    "UTTRAKHAND": ("\u0909\u0924\u094d\u0924\u0930\u093e\u0916\u0902\u0921",),
    "VARANASI": ("\u0935\u093e\u0930\u093e\u0923\u0938\u0940",),
    "VIJAYAWADA": ("\u0935\u093f\u091c\u092f\u0935\u093e\u0921\u093c\u093e",),
    "VISAKHAPATNAM": ("\u0935\u093f\u0936\u093e\u0916\u093e\u092a\u0924\u094d\u0924\u0928\u092e",),
    "VISIT": ("\u0926\u094c\u0930\u093e", "\u0926\u094c\u0930\u0947",),
    "WAREHOUSE": ("\u0917\u094b\u0926\u093e\u092e",),
    "WASHINGTON": ("\u0935\u0949\u0936\u093f\u0902\u0917\u091f\u0928",),
    "WATER": ("\u091c\u0932", "\u092a\u093e\u0928\u0940",),
    "WEATHER": ("\u092e\u094c\u0938\u092e",),
    "WEST": ("\u092a\u0936\u094d\u091a\u093f\u092e",),
    "WHEAT": ("\u0917\u0947\u0939\u0942\u0902",),
    "WOMEN": ("\u092e\u0939\u093f\u0932\u093e", "\u092e\u0939\u093f\u0932\u093e\u0913\u0902",),
    "WORLD": ("\u0935\u093f\u0936\u094d\u0935", "\u0926\u0941\u0928\u093f\u092f\u093e",),
    "YEAR": ("\u0935\u0930\u094d\u0937", "\u0938\u093e\u0932",),
    "YEARS": ("\u0935\u0930\u094d\u0937", "\u0938\u093e\u0932",),
    "YOUTH": ("\u092f\u0941\u0935\u093e",),
}

# Acronyms with exam value: these are enforced even when the whole source line is
# uppercase (where every other uppercase token is an ordinary word).
_KNOWN_ACRONYMS = frozenset({
    "ADB", "AIIMS", "ANI", "APEDA", "BRICS", "BSF", "CACP", "CBSE", "CRPF",
    "CSIR", "DRDO", "ECI", "EEPC", "FAO", "FCI", "FSSAI", "G20", "GST",
    "IANS", "IBPS", "ICAR", "ICMR", "IIM", "IIT", "IMF", "IRDAI", "ISRO",
    "JJM", "KCC", "MEA", "MGNREGA", "MHA", "MPC", "MPEDA", "MSP", "NABARD",
    "NAFED", "NCDRC", "NDRF", "NFSA", "NHAI", "NITI", "NPCI", "PACS", "PDS",
    "PMKSY", "PMO", "PTI", "RBI", "SEBI", "SFAC", "SIDBI", "TRAI", "UN",
    "UNESCO", "UNICEF", "UPI", "UPSC", "WHO", "WTO",
})


def _norm_for_match(text: str) -> str:
    """Punctuation/space-insensitive form, so a dotted transliteration still matches."""
    return re.sub(r"[\s.\-\u2013\u2014\u00b7|/\\(),:;!?'\"\u2018\u2019\u201c\u201d\u0964]+",
                  "", text or "")


def _source_is_all_caps(english: str) -> bool:
    """True for headline-style sources where every word looks like an acronym."""
    letters = [c for c in (english or "") if c.isascii() and c.isalpha()]
    if len(letters) < 12:
        return False
    return sum(1 for c in letters if c.isupper()) / len(letters) >= 0.75


def _missing_acronyms(english: str, hindi: str) -> List[str]:
    """Uppercase source tokens the Hindi text does not carry.

    For an ALL-CAPS source only curated acronyms count: demanding the Latin form
    of an ordinary word (BATCH, DELHI, NEW) rejects correct translations."""
    tokens = set(re.findall(r"\b[A-Z]{2,8}\b", english or ""))
    if _source_is_all_caps(english):
        tokens = {t for t in tokens if t.upper() in _KNOWN_ACRONYMS}
    return sorted(t for t in tokens if not _acronym_matched_in_hindi(t, hindi))


def _acronym_matched_in_hindi(acr: str, hindi: str) -> bool:
    """Check if an English acronym is preserved in Hindi (Latin, Devanagari, known expansion).

    Punctuation is ignored on both sides, so a model that writes the acronym with
    dots between letters passes instead of being rejected (run 42789471273)."""
    if not acr:
        return True
    if acr in hindi:
        return True
    up = acr.upper()
    hi = _norm_for_match(hindi)
    lat = _norm_for_match(acr)
    if lat and lat in hi:
        return True
    dev = _norm_for_match("".join(_DEV_ACRONYM_MAP.get(c, "") for c in up))
    if dev and dev in hi:
        return True
    special = _SPECIAL_ACRONYMS.get(up)
    if special and _norm_for_match(special) in hi:
        return True
    # Natural transliterations (ट्राई for TRAI, ब्रिक्स for BRICS): the letter
    # map above only produces the spelling-out form.
    for variant in _ACRONYM_HI_VARIANTS.get(up, ()):
        if _norm_for_match(variant) and _norm_for_match(variant) in hi:
            return True
    # An ALL-CAPS English word or place name rendered in Hindi was translated,
    # not dropped — never demand the Latin spelling back.
    if any(_norm_for_match(w) in hi for w in _CAPS_WORD_HI.get(up, ())):
        return True
    # Short 2-letter common abbreviations (PC, PM, CM, IT, AI, etc.) never block valid translations
    if len(acr) <= 2:
        return True
    return False


# Direction/polarity guard.  On 2026-11-11 the headline "…December rate hike
# after hot CPI" was printed as "…दर कटौती के द्वार खोले" while the same story's
# summary correctly said "बढ़ोतरी" - the PDF contradicted itself on its cover.
# Each entry: (english window, forbidden hindi window, deterministic swaps).
# Windows keep the check collocated ("दर … कटौती") so an unrelated "कमी"
# elsewhere in the paragraph cannot trip it.  Pairs with empty swaps only
# reject (and retry on another provider); they are never auto-rewritten.
_POLARITY_PAIRS = [
    (r"\b(?:rate|rates)\b[^.!?\u0964]{0,40}?\b(?:hike|hikes|increase|increases|rise|rises|raise|raises)\b",
     r"(?:दर|रेट|ब्याज)[^.!?\u0964]{0,40}?(?:कटौती|कमी|घटा)",
     (("कटौती", "बढ़ोतरी"), ("कमी", "बढ़ोतरी"))),
    (r"\b(?:rate|rates)\b[^.!?\u0964]{0,40}?\b(?:cut|cuts|reduction|decrease|decreases|lower|lowers)\b",
     r"(?:दर|रेट|ब्याज)[^.!?\u0964]{0,40}?(?:बढ़ोतरी|वृद्धि)",
     (("बढ़ोतरी", "कटौती"), ("वृद्धि", "कटौती"))),
    (r"\b(?:inflation|CPI|prices|price)\b[^.!?\u0964]{0,40}?\b(?:rose|rise|rises|climbed|jumped|surged|increased|higher|hot)\b",
     r"(?:महंगाई|मुद्रास्फीति|कीमत|सीपीआई)[^.!?\u0964]{0,40}?(?:गिरावट|कमी|घटा)",
     (("गिरावट", "वृद्धि"), ("कमी", "वृद्धि"))),
    (r"\b(?:inflation|CPI|prices|price)\b[^.!?\u0964]{0,40}?\b(?:fell|fall|falls|dropped|declined|decelerated|cooled|lower)\b",
     r"(?:महंगाई|मुद्रास्फीति|कीमत|सीपीआई)[^.!?\u0964]{0,40}?(?:बढ़ोतरी|वृद्धि)",
     (("बढ़ोतरी", "गिरावट"), ("वृद्धि", "गिरावट"))),
    (r"\b(?:cabinet|government|ministry|authority|regulator|committee)\b[^.!?\u0964]{0,60}?\b(?:approves|approved|approval|clearance|clears|nod)\b",
     r"(?:मंत्रिमंडल|सरकार|मंत्रालय|प्राधिकरण|समित)[^.!?\u0964]{0,60}?(?:खारिज|अस्वीकार|इनकार)",
     ()),
    (r"\b(?:cabinet|government|ministry|authority|regulator|committee)\b[^.!?\u0964]{0,60}?\b(?:rejects|rejected|rejection|turns down|refuses)\b",
     r"(?:मंत्रिमंडल|सरकार|मंत्रालय|प्राधिकरण|समित)[^.!?\u0964]{0,60}?(?:मंजूरी|स्वीकृति|अनुमोदन)",
     ()),
]

# Literal calques that read wrong in exam Hindi; the replacement keeps any
# acronym the validator expects ("गर्म सीपीआई" -> "उच्च सीपीआई").
_CALQUE_FIXES = {
    "गर्म सीपीआई": "उच्च सीपीआई",
    "गर्म मुद्रास्फीति": "उच्च मुद्रास्फीति",
    "गर्म महंगाई": "उच्च महंगाई",
}

# Legitimate Hindi reduplication the stutter-collapse must keep.
_HI_STUTTER_ALLOW = {"धीरे", "जोर", "बार", "दिन", "रात", "समय", "जगह", "बात", "पल"}
_HI_STUTTER_RE = re.compile(r"\b([\u0900-\u097F]{3,})\s+\1\b")


def polarity_conflicts(english: str, hindi: str) -> List[str]:
    """Direction words that disagree between the two sides (empty = OK)."""
    out: List[str] = []
    for en_re, hi_re, _swaps in _POLARITY_PAIRS:
        me = re.search(en_re, english or "", re.I)
        mh = re.search(hi_re, hindi or "")
        if me and mh:
            out.append("polarity conflict: '%s' vs '%s'"
                       % (me.group(0).strip()[:40], mh.group(0).strip()[:30]))
    return out


def _repair_polarity(english: str, hindi: str) -> Tuple[str, List[str]]:
    """Swap the Hindi direction noun inside the conflicting window only.

    Called only when polarity is the *sole* problem and the pair carries a
    safe noun swap; the result is re-validated by the caller.
    """
    out = (hindi or "").strip()
    swapped: List[str] = []
    for en_re, hi_re, fixes in _POLARITY_PAIRS:
        if not fixes or not re.search(en_re, english or "", re.I):
            continue
        m = re.search(hi_re, out)
        if not m:
            continue
        win, new = m.group(0), m.group(0)
        for wrong, right in fixes:
            if wrong in new:
                new = new.replace(wrong, right, 1)
                swapped.append(f"{wrong}->{right}")
                break
        if new != win:
            out = out[:m.start()] + new + out[m.end():]
    return out, swapped


def _polish_hindi(hi: str) -> str:
    """Deterministic cleanups applied to every accepted translation:
    collapse an accidental repeated word ("प्रमुख प्रमुख योजनाओं") and fix
    word-for-word calques ("गर्म सीपीआई")."""
    if not hi:
        return hi

    def _sub(m: "re.Match[str]") -> str:
        return m.group(0) if m.group(1) in _HI_STUTTER_ALLOW else m.group(1)

    hi = _HI_STUTTER_RE.sub(_sub, hi)
    for wrong, right in _CALQUE_FIXES.items():
        hi = hi.replace(wrong, right)
    return hi


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
    try:
        from pipeline.hindi_postfix import mixed_words, untranslated_run
        from pipeline.text_normalize import garbled_hi, hi_truncated_start
        mixed = mixed_words(hindi)
        if untranslated_run(hindi):
            issues.append("untranslated English phrase")
        if hi_truncated_start(hindi):
            issues.append("truncated start")
        if garbled_hi(hindi):
            issues.append("garbled structure")
    except Exception:
        mixed = []
    if mixed:
        issues.append(f"mixed-script words: {mixed[:3]}")

    # Numbers check
    en_vals = _numeric_values(" ".join(_NUM_RE.findall(english)))
    hi_vals = _numeric_values(hindi)
    missing_nums = en_vals - hi_vals
    if missing_nums:
        issues.append(f"missing numbers: {sorted(missing_nums)[:3]}")

    # Acronym check (uppercase 2-8 chars; an ALL-CAPS source only enforces
    # curated acronyms, see _missing_acronyms)
    missing_acr = _missing_acronyms(english, hindi)
    if missing_acr:
        issues.append(f"missing acronyms: {missing_acr[:3]}")

    # Direction/polarity (hike vs कटौती ...) - see _POLARITY_PAIRS
    issues.extend(polarity_conflicts(english, hindi))

    # Length sanity (Hindi usually 0.7x - 1.6x of English by char count)
    ratio = len(hindi) / max(len(english), 1)
    if ratio < 0.4 or ratio > 2.5:
        issues.append(f"unusual length ratio {ratio:.2f}")

    passed = not issues
    # Confidence: start from 1.0, subtract per issue
    conf = max(0.0, 1.0 - 0.25 * len(issues))
    return passed, conf, issues


def _repair_missing_acronyms(english: str, hindi: str,
                             missing: List[str]) -> Tuple[str, List[str]]:
    """Append genuinely-absent acronyms as one parenthetical; never rewrite prose.

    Returns (text, injected).  An earlier draft inserted each acronym at its
    relative position in the sentence, which produced unreadable hybrids inside a
    compound noun; a single trailing parenthetical keeps the exam-relevant token
    in the PDF without touching the Hindi.  Called only when the acronym check is
    the *only* problem, and the result is re-validated, so a repair can never
    smuggle in a line that fails another gate.
    """
    out = (hindi or "").strip()
    if not out:
        return hindi, []
    # Ask the same matcher the validator uses: a line that already says ट्राई
    # has not dropped TRAI, and injecting it again only adds noise.
    add = [a for a in missing[:max(0, MAX_ACRONYM_REPAIRS)]
           if a and not _acronym_matched_in_hindi(a, out)]
    if not add:
        return hindi, []
    tag = " (%s)" % ", ".join(add)
    if out.endswith("\u0964"):
        out = f"{out[:-1].rstrip()}{tag}\u0964"
    elif out.endswith((".", "!", "?")):
        out = f"{out[:-1].rstrip()}{tag}{out[-1]}"
    else:
        out = f"{out}{tag}"
    return out, add



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
    router = _router()
    validation_fails = 0
    for provider in providers:
        name = provider["name"]
        if _provider_parked(name):
            logger.info("[Translator] skipping %s (parked after rate limit / credit error)", name)
            continue
        if router is not None:
            left = router.ai_time_left()
            if left is not None and left <= 0:
                provider_issues.append("stage AI time budget used")
                return None
            if not router.provider_ready(name):
                # Shared health: cooled down by the router / an earlier stage.
                logger.info("[Translator] skipping %s (cooled down in shared provider health)", name)
                continue
        logger.info("[Translator] trying provider %s", name)
        for attempt in range(1, MAX_RETRIES + 1):
            live = dict(provider)
            if router is not None:
                live["model"] = router.current_model(name) or provider.get("model", "")
                _cur_key = getattr(router, "current_key", None)
                if callable(_cur_key):
                    # Key-rotation aware: after a 429/402 the router may have
                    # switched this provider to its next verified API key.
                    live["key"] = _cur_key(name) or provider.get("key", "")
                router.note_call(name)
            try:
                hindi = _call_provider(live, system, user)
            except ProviderRateLimited as exc:
                rotated = bool(router and router.report_failure(name, "rate_limit", exc.retry_after))
                if rotated and attempt < MAX_RETRIES:
                    logger.info("[Translator] %s 429 on one model; retrying with %s", name,
                                router.current_model(name))
                    continue
                _park_provider(name, max(RATE_LIMIT_COOLDOWN, exc.retry_after or 0))
                provider_issues.append(f"{name}: rate limited")
                logger.info("[Translator] moving to the next configured provider")
                break
            except ProviderRequestFailed as exc:
                if exc.timeout:
                    # A timeout costs the full timeout: never retry the same provider.
                    if router is not None:
                        router.report_failure(name, "timeout")
                    provider_issues.append(f"{name}: {exc}")
                    break
                if exc.retryable and attempt < MAX_RETRIES:
                    time.sleep(2 ** attempt)
                    continue
                if str(exc) in ("HTTP 404", "HTTP 410") and router is not None:
                    # Retired model: the router retires it for the run and
                    # rotates; retry once more on the provider's next model.
                    if router.report_failure(name, "model_error") and attempt < MAX_RETRIES:
                        continue
                    provider_issues.append(f"{name}: {exc}")
                    break
                if any(str(exc) == f"HTTP {code}" for code in _HARD_FAIL_STATUSES):
                    _park_provider(name, None)
                    if router is not None and str(exc) in ("HTTP 401", "HTTP 402", "HTTP 403"):
                        router.report_failure(name, "auth_error")
                elif exc.retryable and router is not None:
                    router.report_failure(name, "transient")
                provider_issues.append(f"{name}: {exc}")
                break

            if router is not None:
                router.report_success(name)
            try:
                from pipeline.hindi_postfix import apply_glossary
                hindi = apply_glossary(text, hindi)
            except Exception:
                pass
            hindi = _polish_hindi(hindi)
            passed, conf, issues = _validate(text, hindi)
            repaired: List[str] = []
            # Acronym auto-repair: an otherwise clean line rejected *only* for a
            # missing acronym gets the token appended and is re-validated.
            # Everything else (no Devanagari, missing numbers, garbled text, bad
            # length) still fails closed exactly as before.
            if (not passed and AUTO_REPAIR and issues
                    and all(i.startswith("missing acronyms") for i in issues)):
                fixed, injected = _repair_missing_acronyms(
                    text, hindi, _missing_acronyms(text, hindi))
                if injected:
                    retry_passed, retry_conf, _retry_issues = _validate(text, fixed)
                    if retry_passed:
                        logger.info("[Translator] %s auto-repaired %s (was rejected: %s)",
                                    name, injected, issues)
                        hindi, passed = fixed, True
                        conf = min(retry_conf, REPAIRED_CONFIDENCE_CAP)
                        issues, repaired = [], injected
            # Polarity auto-repair: same fail-closed shape - only when the
            # direction conflict is the sole problem and a safe noun swap exists.
            if (not passed and AUTO_REPAIR and issues
                    and all(i.startswith("polarity conflict") for i in issues)):
                fixed, swapped = _repair_polarity(text, hindi)
                if swapped:
                    retry_passed, retry_conf, _retry_issues = _validate(text, fixed)
                    if retry_passed:
                        logger.info("[Translator] %s polarity-repaired %s (was rejected: %s)",
                                    name, swapped, issues)
                        hindi, passed = fixed, True
                        conf = min(retry_conf, REPAIRED_CONFIDENCE_CAP)
                        issues, repaired = [], swapped
            detail = ("acronym auto-repair: " + ",".join(repaired)) if repaired else (
                "" if passed else "validation rejected")
            record_ai_usage(name, live.get("model", ""), f"translator:{task}", passed, detail)
            if passed:
                result = {
                    "translated_hi": hindi,
                    "passed": True,
                    "confidence": round(conf, 3),
                    "provider": name,
                    "issues": [],
                    "repaired": repaired,
                }
                _CACHE.put(key, result)
                logger.debug("[Translator] ✔ %s (conf=%.2f) for task=%s",
                             name, conf, task)
                return result
            provider_issues.append(f"{name}: validation failed")
            logger.warning("[Translator] %s validation failed: %s", name, issues)
            validation_fails += 1
            if validation_fails >= MAX_VALIDATION_FAILS:
                logger.warning("[Translator] %d providers rejected by validation; not trying more "
                               "providers for this line", validation_fails)
                return None
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
