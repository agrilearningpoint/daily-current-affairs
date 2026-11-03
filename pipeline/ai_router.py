# -*- coding: utf-8 -*-
"""
AI Router — Multi-Provider with Fallback
=========================================
Routes AI tasks across multiple providers, cheapest and most reliable free
tiers first:
  Groq → Gemini → Ollama Cloud → Cloudflare → SambaNova → Mistral → OpenRouter →
  NVIDIA → (generic) → Cohere → LLM7 → HuggingFace → Cerebras → OpenAI → DeepSeek
with automatic fallback, rate-limit tracking, and failure classification.
Every provider is OFF when its secret is missing; the low-priority ones carry
small daily caps (Cohere trial ≈ 30/day, HuggingFace free credit ≈ 15/day).

Features:
- Multi-provider fallback chain (configurable priority)
- Per-model quota rotation: on providers whose free limits are per model
  (Gemini, Groq, SambaNova) a 429 rotates to the provider's next model before
  the whole provider is cooled down
- Client-side throttling: per-provider minimum spacing (Mistral ~1 RPS) and
  per-model / per-provider RPM + RPD caps (OpenRouter free 20 RPM / 50 RPD)
- Failure classification:
    * TRANSIENT       — next provider; repeated 5xx cools the provider down
    * TIMEOUT         — next provider; repeated timeouts cool it down for long
    * RATE_LIMIT      — 429: honour Retry-After, escalate repeated 429s
    * AUTH_ERROR      — 401/402/403: provider out for the run
    * MODEL_ERROR     — 404/410: that model is retired for the run (never picked
                        again by discovery); rotate to the next model, else out
    * BAD_REQUEST     — 400: next provider
    * MALFORMED       — bad JSON / empty reply: next provider
- Shared provider health: cooldowns are written to a per-job health file so the
  next stage subprocess (and the translator) skip a provider that is known to be
  dead/limited instead of re-learning it (stage 00 seeds it too)
- Stage AI deadline: every stage gets an AI time budget below ALP_STAGE_TIMEOUT;
  after it, route() returns None immediately so callers use their fallback
  instead of the stage being killed by the orchestrator
- Global call budget, LRU response cache
- Never raises to caller unless fail_on_all=True

Env:
  GEMINI_API_KEY, GROQ_API_KEY, OPENAI_API_KEY, MISTRAL_API_KEY,
  OPENROUTER_API_KEY, NVIDIA_API_KEY, OLLAMA_API_KEY/OLLAMA_BASE_URL,
  SAMBANOVA_API_KEY, CLOUDFLARE_ACCOUNT_ID + CLOUDFLARE_API_TOKEN (or CLOUDFLARE_TOKEN),
  COHERE_API_KEY, LL7_API_KEY (or LLM7_API_KEY), HUGGINGFACE_API_KEY (or HF_TOKEN),
  CEREBRAS_API_KEY, OPENAI_API_KEY (real sk- keys only; an OpenRouter sk-or- key is skipped),
  DEEPSEEK_API_KEY (+ ALP_ENABLE_DEEPSEEK=1: paid only, opt-in)
  AI_ROUTER_RPD_<NAME> / AI_ROUTER_RPM_<NAME> override any provider's caps
  AI_ROUTER_TIMEOUT_GEMINI (default 25s per Gemini call)
  AI_ROUTER_MAX_CALLS_PER_HOUR (default 500)
  AI_ROUTER_TIMEOUT (default 60)
  AI_ROUTER_CACHE_SIZE (default 1000)
  AI_ROUTER_DISABLED (1 = always return None; useful for tests)
  ALP_AI_STAGE_BUDGET (seconds of AI time per stage; default 70% of ALP_STAGE_TIMEOUT)
  ALP_AI_HEALTH_FILE (shared health file; default logs/ai_health/<ALP_JOB_ID>.json)
"""
from __future__ import annotations

from pipeline.ai_usage import record_ai_usage
import email.utils
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
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger("pipeline.ai_router")

REPO_ROOT = Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
TIMEOUT = int(os.getenv("AI_ROUTER_TIMEOUT", "60"))
# Short per-task timeouts for high-volume, optional calls (one call per article).
_TASK_TIMEOUTS = {
    "fact_verification": int(os.getenv("AI_ROUTER_TIMEOUT_FACT", "20")),
}
# Per-provider ceilings. Gemini 3.x flash-lite was seen hanging for 40s+ on
# 2026-11-03; a hung model is rotated instead of costing a full minute.
_PROVIDER_TIMEOUTS = {
    "gemini": int(os.getenv("AI_ROUTER_TIMEOUT_GEMINI", "25")),
}


def request_timeout(provider_name: str, task: str = "general") -> float:
    """Per-call timeout: task ceiling, then provider ceiling, then the stage budget."""
    value = float(_TASK_TIMEOUTS.get(task, TIMEOUT))
    if provider_name in _PROVIDER_TIMEOUTS:
        value = min(value, float(_PROVIDER_TIMEOUTS[provider_name]))
    return clip_timeout(value)
# A provider that 5xx's / times out this many times in a row is cooled down so
# every later call in the run does not wait on it again.
TRANSIENT_STRIKES = int(os.getenv("AI_ROUTER_TRANSIENT_STRIKES", "2"))
TRANSIENT_COOLDOWN = int(os.getenv("AI_ROUTER_TRANSIENT_COOLDOWN", "600"))
# Timeouts are far more expensive than 5xx (each costs the full timeout), so a
# provider that keeps timing out is parked for longer (default 30 min ≈ the run).
TIMEOUT_COOLDOWN = int(os.getenv("AI_ROUTER_TIMEOUT_COOLDOWN", "1800"))
RATE_LIMIT_COOLDOWN = int(os.getenv("AI_ROUTER_RATE_LIMIT_COOLDOWN", "120"))
RATE_LIMIT_MAX_COOLDOWN = int(os.getenv("AI_ROUTER_RATE_LIMIT_MAX_COOLDOWN", "1800"))
AUTH_COOLDOWN = int(os.getenv("AI_ROUTER_AUTH_COOLDOWN", "86400"))
MAX_CALLS_PER_HOUR = int(os.getenv("AI_ROUTER_MAX_CALLS_PER_HOUR", "500"))
CACHE_SIZE = int(os.getenv("AI_ROUTER_CACHE_SIZE", "1000"))
DISABLED = os.getenv("AI_ROUTER_DISABLED", "0") == "1"


# --------------------------------------------------------------------------- #
# Failure classification
# --------------------------------------------------------------------------- #
class FailureType:
    TRANSIENT = "transient"          # network, 5xx
    TIMEOUT = "timeout"              # request timed out
    RATE_LIMIT = "rate_limit"        # 429 — cooldown / rotate model
    AUTH_ERROR = "auth_error"        # 401/402/403 — skip provider
    MODEL_ERROR = "model_error"      # 404 model not found — skip provider
    BAD_REQUEST = "bad_request"      # 400 — fail fast
    MALFORMED = "malformed"          # bad JSON in response — retry/fallback
    UNKNOWN = "unknown"


# --------------------------------------------------------------------------- #
# Stage AI deadline
# --------------------------------------------------------------------------- #
_IMPORTED_AT = time.time()
_DEADLINE_LOGGED = [False]


def _stage_deadline() -> Optional[float]:
    """Epoch after which this stage must stop calling AI (None = no deadline)."""
    budget_raw = os.getenv("ALP_AI_STAGE_BUDGET", "").strip()
    try:
        if budget_raw:
            budget = float(budget_raw)
        else:
            stage_timeout = os.getenv("ALP_STAGE_TIMEOUT", "").strip()
            if not stage_timeout:
                return None
            # Leave 30% of the stage for deterministic work + writing outputs.
            budget = 0.7 * float(stage_timeout)
    except ValueError:
        return None
    if budget <= 0:
        return None
    try:
        started = float(os.getenv("ALP_STAGE_STARTED_AT", "") or _IMPORTED_AT)
    except ValueError:
        started = _IMPORTED_AT
    return started + budget


def ai_time_left() -> Optional[float]:
    """Seconds of AI time left in this stage, or None when no deadline applies."""
    deadline = _stage_deadline()
    if deadline is None:
        return None
    return deadline - time.time()


def _deadline_passed() -> bool:
    left = ai_time_left()
    if left is not None and left <= 0:
        if not _DEADLINE_LOGGED[0]:
            _DEADLINE_LOGGED[0] = True
            logger.warning("[Router] stage AI time budget used; further AI calls return None "
                           "(callers use their deterministic / fail-closed path)")
        return True
    return False


def clip_timeout(timeout: float) -> float:
    """Clip a request timeout to the time left in the stage AI budget."""
    left = ai_time_left()
    if left is None:
        return timeout
    return max(1.0, min(float(timeout), left))


# --------------------------------------------------------------------------- #
# Shared provider health (cross-stage, cross-module)
# --------------------------------------------------------------------------- #
_HEALTH_LOCK = threading.RLock()
_HEALTH: Dict[str, Any] = {"blocks": {}, "calls": {}, "strikes": {}}
_HEALTH_LOADED = [None]  # path the in-memory copy was loaded from


def _health_path() -> Optional[Path]:
    explicit = os.getenv("ALP_AI_HEALTH_FILE", "").strip()
    if explicit:
        return Path(explicit)
    job = os.getenv("ALP_JOB_ID", "").strip()
    if job and re.fullmatch(r"[A-Za-z0-9_.-]+", job):
        return REPO_ROOT / "logs" / "ai_health" / f"{job}.json"
    return None


def _health_load() -> None:
    path = _health_path()
    key = str(path) if path else ""
    if _HEALTH_LOADED[0] == key:
        return
    _HEALTH_LOADED[0] = key
    _HEALTH["blocks"], _HEALTH["calls"], _HEALTH["strikes"] = {}, {}, {}
    if not path or not path.is_file():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        now = time.time()
        _HEALTH["blocks"] = {k: v for k, v in (data.get("blocks") or {}).items()
                             if isinstance(v, dict) and float(v.get("until", 0)) > now}
        _HEALTH["calls"] = {k: int(v) for k, v in (data.get("calls") or {}).items()}
        _HEALTH["strikes"] = {k: int(v) for k, v in (data.get("strikes") or {}).items()}
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        logger.info("[Router] provider health file unreadable (%s); starting fresh", type(exc).__name__)


def _health_save() -> None:
    path = _health_path()
    if not path:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(_HEALTH, sort_keys=True, indent=1), encoding="utf-8")
        os.replace(tmp, path)
    except OSError as exc:
        logger.info("[Router] provider health file not written: %s", type(exc).__name__)


def _reset_health() -> None:
    """Tests: forget every cooldown and counter held in memory."""
    with _HEALTH_LOCK:
        _HEALTH["blocks"], _HEALTH["calls"], _HEALTH["strikes"] = {}, {}, {}
        _HEALTH_LOADED[0] = None
    _DEADLINE_LOGGED[0] = False


def block(key: str, seconds: float, reason: str) -> float:
    """Block a provider ("name") or one model ("name::model") for `seconds`."""
    with _HEALTH_LOCK:
        _health_load()
        until = time.time() + max(1.0, float(seconds))
        current = _HEALTH["blocks"].get(key) or {}
        if float(current.get("until", 0)) >= until:
            return float(current["until"])
        _HEALTH["blocks"][key] = {"until": until, "reason": str(reason)[:200]}
        _health_save()
    logger.warning("[Router] %s cooled down for %ds: %s", key, int(seconds), reason)
    return until


def blocked_until(key: str) -> float:
    with _HEALTH_LOCK:
        _health_load()
        entry = _HEALTH["blocks"].get(key)
        if not entry:
            return 0.0
        until = float(entry.get("until", 0))
        if until <= time.time():
            _HEALTH["blocks"].pop(key, None)
            return 0.0
        return until


def is_blocked(key: str) -> bool:
    return blocked_until(key) > 0


def _strike(key: str, reset: bool = False) -> int:
    with _HEALTH_LOCK:
        _health_load()
        if reset:
            if _HEALTH["strikes"].pop(key, None) is not None:
                _health_save()
            return 0
        _HEALTH["strikes"][key] = int(_HEALTH["strikes"].get(key, 0)) + 1
        _health_save()
        return _HEALTH["strikes"][key]


def _day() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _calls_today(key: str) -> int:
    with _HEALTH_LOCK:
        _health_load()
        return int(_HEALTH["calls"].get(f"{key}@{_day()}", 0))


def _count_call(key: str) -> None:
    with _HEALTH_LOCK:
        _health_load()
        day = _day()
        _HEALTH["calls"] = {k: v for k, v in _HEALTH["calls"].items() if k.endswith("@" + day)}
        _HEALTH["calls"][f"{key}@{day}"] = int(_HEALTH["calls"].get(f"{key}@{day}", 0)) + 1
        _health_save()


def health_snapshot() -> Dict[str, Any]:
    with _HEALTH_LOCK:
        _health_load()
        now = time.time()
        return {k: {"for_s": int(float(v["until"]) - now), "reason": v.get("reason", "")}
                for k, v in _HEALTH["blocks"].items() if float(v.get("until", 0)) > now}


def parse_retry_after(headers: Any, body: str = "") -> Optional[float]:
    """Seconds from a Retry-After header (seconds or HTTP date) or Gemini RetryInfo."""
    value = None
    try:
        value = (headers or {}).get("retry-after") or (headers or {}).get("Retry-After")
    except AttributeError:
        value = None
    if value:
        try:
            return max(0.0, float(value))
        except (TypeError, ValueError):
            try:
                when = email.utils.parsedate_to_datetime(str(value))
                return max(0.0, when.timestamp() - time.time())
            except (TypeError, ValueError, IndexError):
                pass
    match = re.search(r'"retryDelay"\s*:\s*"(\d+(?:\.\d+)?)s"', body or "")
    if match:
        return float(match.group(1))
    return None


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
    rpm_limit: int = 60              # requests per minute (per model when per_model_quota)
    rpd_limit: int = 1000            # requests per day (per model when per_model_quota)
    models: List[str] = field(default_factory=list)   # rotation order; [model] when empty
    per_model_quota: bool = False    # free limits apply per model (Gemini, Groq, SambaNova)
    min_interval: float = 0.0        # client-side spacing between requests (seconds)
    last_error: Optional[str] = None
    disabled_until: float = 0.0
    consecutive_transient: int = 0
    last_call: float = 0.0
    call_times: deque = field(default_factory=lambda: deque(maxlen=5000))
    model_calls: Dict[str, deque] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def __post_init__(self) -> None:
        if not self.models:
            self.models = [self.model] if self.model else []
        elif self.model and self.model not in self.models:
            self.models.insert(0, self.model)

    # -- quota keys ------------------------------------------------------- #
    def quota_key(self, model: Optional[str] = None) -> str:
        return f"{self.name}::{model or self.model}" if self.per_model_quota else self.name

    def _model_usable(self, model: str) -> bool:
        # name::model is blocked for per-model 429s and, for every provider, when
        # the model was retired (404/410) or hung (timeout) earlier in the run.
        if is_blocked(f"{self.name}::{model}"):
            return False
        now = time.time()
        recent = self.model_calls.get(self.quota_key(model), deque())
        if sum(1 for t in recent if now - t < 60) >= self.rpm_limit:
            return False
        if _calls_today(self.quota_key(model)) >= self.rpd_limit:
            return False
        return True

    def is_available(self) -> bool:
        if not self.key or not self.url or not self.model:
            return False
        if time.time() < self.disabled_until or is_blocked(self.name):
            return False
        if self._model_usable(self.model):
            return True
        # Rotation covers per-model quotas and models retired / hung this run.
        for candidate in self.models:
            if candidate != self.model and self._model_usable(candidate):
                logger.info("[Router] %s rotated model %s -> %s (unavailable)", self.name, self.model, candidate)
                self.model = candidate
                return True
        return False

    def rotate_model(self, force: bool = False) -> bool:
        """Switch to the next model in rotation that is still usable.

        Quota rotation (429) only applies to per-model-quota providers; `force`
        rotates any provider (the current model was retired or hung)."""
        if not self.per_model_quota and not force:
            return False
        order = self.models
        start = order.index(self.model) + 1 if self.model in order else 0
        for candidate in order[start:] + order[:start]:
            if candidate != self.model and self._model_usable(candidate):
                logger.info("[Router] %s rotated model %s -> %s", self.name, self.model, candidate)
                self.model = candidate
                return True
        return False

    def throttle(self) -> None:
        """Client-side spacing (e.g. Mistral free tier ≈ 1 request/second)."""
        if self.min_interval <= 0:
            return
        with self._lock:
            wait = self.last_call + self.min_interval - time.time()
            if wait > 0:
                time.sleep(min(wait, self.min_interval))
            self.last_call = time.time()

    def record_call(self) -> None:
        with self._lock:
            now = time.time()
            self.call_times.append(now)
            self.model_calls.setdefault(self.quota_key(), deque(maxlen=5000)).append(now)
        _count_call(self.quota_key())

    def mark_disabled(self, reason: str, seconds: int = 300) -> None:
        with self._lock:
            self.disabled_until = time.time() + seconds
            self.last_error = reason
        block(self.name, seconds, reason)


# Live model discovery is deliberately best-effort.  Provider catalogues change
# more often than this repository, so model IDs must not be treated as a
# permanent part of the workflow configuration.
#
# Every *_MODEL variable accepts the value "auto" (the workflow default).  With
# "auto" the router asks the provider's own /models catalogue which models are
# live and picks the first entry of the free-first preference list below that
# is still advertised.  An explicit model ID is kept only while the provider
# still advertises it; when it is retired the same preference list is used.
# The same list (filtered to live models) is the per-model 429 rotation order.
# Preference lists were checked against each provider's official docs and
# model catalogues on 2026-11-01 (SambaNova / Cloudflare on 2026-11-03).
_MODEL_DISCOVERY_TIMEOUT = 8
AUTO_MODEL = "auto"
_PREFERRED_MODELS = {
    # ai.google.dev/gemini-api/docs/pricing: free tier text models (limits per model).
    "gemini": ("gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.8-flash",
               "gemini-3.6-flash", "gemini-2.5-flash-lite", "gemini-2.5-flash",
               "gemini-3-flash-preview"),
    # console.groq.com/docs/models: production text models (free plan, limits per model).
    "groq": ("openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"),
    # api-docs.deepseek.com: paid only; deepseek-chat is no longer listed.
    "deepseek": ("deepseek-flash", "deepseek-v4-pro"),
    "openai": ("gpt-4o-mini",),
    "generic-openai": ("gpt-4o-mini",),
    # openrouter.ai/api/v1/models: zero-price ":free" variants only.
    "openrouter": ("google/gemma-4-31b-it:free", "nvidia/nemotron-3-ultra-550b-a55b:free",
                   "google/gemma-4-26b-a4b-it:free", "nvidia/nemotron-3.5-lightning:free",
                   "openrouter/free"),
    # docs.mistral.ai models overview (free Experiment plan).
    "mistral": ("mistral-small-latest", "ministral-8b-latest", "mistral-large-latest"),
    # integrate.api.nvidia.com/v1/models (free build.nvidia.com endpoints).
    "nvidia": ("deepseek-ai/deepseek-v4.1-flash", "moonshotai/kimi-k2.6",
               "nvidia/nemotron-3-super-120b-a12b", "mistralai/mistral-large-4-1t-a52b",
               "google/gemma-4-31b-it", "openai/gpt-oss-20b"),
    # ollama.com/api/tags (Ollama Cloud).
    "ollama": ("gpt-oss:120b", "gemma4:31b", "deepseek-v4.1-flash", "gpt-oss:20b"),
    # docs.sambanova.ai/docs/en/models/sambacloud-models: production models
    # (free tier limits per model).
    "sambanova": ("gpt-oss-120b", "Meta-Llama-3.3-70B-Instruct", "DeepSeek-V3.1"),
    # developers.cloudflare.com/workers-ai/models: Cloudflare-hosted models on the
    # free 10k-neurons/day allowance via /ai/v1/chat/completions.
    "cloudflare": ("@cf/meta/llama-3.3-70b-instruct-fp8-fast", "@cf/openai/gpt-oss-120b"),
    # docs.cohere.com/docs/compatibility-api (OpenAI-compatible); command-r7b
    # live-verified on the trial key 2026-11-03 (trial: 20 RPM, 1,000 calls/month).
    "cohere": ("command-r7b-12-2024", "command-a-03-2025"),
    # docs.llm7.io/guides/models: selectors "default"/"fast" route to the free
    # "turbo" models (free token: 1 RPS, 60 RPM, 250/hour, 100k tokens/day).
    "llm7": ("default", "fast"),
    # router.huggingface.co/v1/models (inference providers; tiny free credit).
    "huggingface": ("openai/gpt-oss-20b", "openai/gpt-oss-120b", "meta-llama/Llama-3.3-70B-Instruct"),
    # api.cerebras.ai/public/v1/models
    "cerebras": ("gpt-oss-120b",),
}
# Models a provider still lists but no longer serves (end of life → HTTP 410).
# Discovery never picks these; a fresh 410 adds the model to the run's health file.
_RETIRED_MODELS = {
    "nvidia": ("meta/llama-3.1-8b-instruct", "meta/llama-3.1-70b-instruct", "meta/llama3-8b-instruct",
               "meta/llama3-70b-instruct", "mistralai/mistral-7b-instruct-v0.2"),
    "gemini": ("gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.5-flash-8b"),
}
# Providers whose catalogue lists many paid / retired models: pick only from the
# reviewed preference list, never the alphabetical "any text model" fallback.
_PREFERRED_ONLY = {"nvidia", "huggingface", "llm7", "cohere", "cerebras"}
# Free-only providers: never select a model that bills per token.
_FREE_ONLY = {"openrouter"}
# Providers whose /models listing is not usable for discovery (non-OpenAI shape,
# or paid prices listed for free-tier models): keep the preference list.
_NO_DISCOVERY = {"cloudflare", "sambanova", "llm7", "cohere"}
_NON_TEXT_MODEL = re.compile(
    r"(?:embed|rerank|guard|safety|moderation|vision|-vl|audio|image|tts|transcribe|"
    r"whisper|live|lyria|veo|robotics|omni|parse|reward|ocr|clip|orpheus|detector)",
    re.I,
)


def is_auto_model(value: Optional[str]) -> bool:
    return not value or value.strip().lower() == AUTO_MODEL


def _env_model(var: str, provider_name: str) -> str:
    """Configured model for a provider; "auto"/empty resolves to the first preference."""
    value = (os.getenv(var) or "").strip()
    if is_auto_model(value):
        return _PREFERRED_MODELS.get(provider_name, ("",))[0]
    return value


def _catalog_url(provider: Provider) -> str:
    if provider.name in _NO_DISCOVERY:
        return ""
    if provider.name == "gemini":
        return provider.url
    marker = "/chat/completions"
    if marker in provider.url:
        return provider.url.split(marker, 1)[0] + "/models"
    return ""


def _is_free_listing(model: Dict[str, Any]) -> bool:
    mid = str(model.get("id", ""))
    if mid.endswith(":free") or mid == "openrouter/free":
        return True
    pricing = model.get("pricing") or {}
    try:
        return float(pricing.get("prompt", 1)) == 0 and float(pricing.get("completion", 1)) == 0
    except (TypeError, ValueError):
        return False


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
        items = data.get("data", []) or data.get("models", [])
        if provider.name in _FREE_ONLY:
            items = [m for m in items if _is_free_listing(m)]
        return [str(m.get("id") or m.get("name") or "") for m in items if (m.get("id") or m.get("name"))]
    except (requests.RequestException, ValueError, TypeError, AttributeError) as exc:
        logger.info("[Router] %s model catalogue lookup skipped: %s", provider.name, type(exc).__name__)
        return []


def _is_retired(provider_name: str, model: str) -> bool:
    return model in _RETIRED_MODELS.get(provider_name, ()) or is_blocked(f"{provider_name}::{model}")


def _choose_live_model(provider: Provider, available: List[str], exclude: set[str] | None = None) -> str | None:
    exclude = exclude or set()
    candidates = [m for m in available if m and m not in exclude and not _is_retired(provider.name, m)]
    if not candidates:
        return None
    # A configured model wins only when the provider still advertises it.
    if provider.model in candidates:
        return provider.model
    for preferred in _PREFERRED_MODELS.get(provider.name, ()):
        if preferred in candidates:
            return preferred
    if provider.name in _PREFERRED_ONLY:
        return None
    text_models = [m for m in candidates if re.search(r"(?:instruct|chat|gpt|llama|qwen|mistral|deepseek|gemini|gemma|nemotron|flash)", m, re.I)
                   and not _NON_TEXT_MODEL.search(m)]
    return sorted(text_models or candidates)[0]


def _rotation_order(provider: Provider, live: List[str]) -> List[str]:
    """Current model first, then the remaining preferred models still advertised."""
    order = [provider.model]
    for model in _PREFERRED_MODELS.get(provider.name, ()):
        if model not in order and (not live or model in live) and not _is_retired(provider.name, model):
            order.append(model)
    return order


def _refresh_provider_model(provider: Provider, exclude: set[str] | None = None,
                            live: Optional[List[str]] = None) -> bool:
    live = _live_model_ids(provider) if live is None else live
    chosen = _choose_live_model(provider, live, exclude)
    if not chosen or chosen == provider.model:
        return False
    old = provider.model
    provider.model = chosen
    if exclude:
        provider.models = [m for m in provider.models if m not in exclude]
    if chosen not in provider.models:
        provider.models.insert(0, chosen)
    logger.info("[Router] %s automatically switched model %s -> %s", provider.name, old, chosen)
    return True


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, "") or default)
    except ValueError:
        return default


def cloudflare_config() -> Tuple[str, str]:
    """(account_id, token). The token falls back to the CLOUDFLARE_TOKEN secret."""
    token = (os.getenv("CLOUDFLARE_API_TOKEN") or os.getenv("CLOUDFLARE_TOKEN") or "").strip()
    account = (os.getenv("CLOUDFLARE_ACCOUNT_ID") or "").strip()
    return account, token


def openai_key_problem(key: Optional[str] = None) -> Optional[str]:
    """Why OPENAI_API_KEY cannot be used against OpenAI (None when it looks usable).

    The secret was seen holding an OpenRouter key (sk-or-...), which OpenAI answers
    with 401 on every call; such a key is skipped instead of failing per call."""
    key = (os.getenv("OPENAI_API_KEY") if key is None else key) or ""
    key = key.strip()
    if not key:
        return None
    base = os.getenv("OPENAI_BASE_URL", "")
    if key.startswith("sk-or-") and "openrouter.ai" not in base:
        return ("openai: OPENAI_API_KEY holds an OpenRouter key (sk-or-...), not an OpenAI key — "
                "provider OFF; put it in OPENROUTER_API_KEY or replace it with a real sk- key")
    return None


def llm7_key() -> str:
    return (os.getenv("LL7_API_KEY") or os.getenv("LLM7_API_KEY") or "").strip()


def huggingface_key() -> str:
    return (os.getenv("HUGGINGFACE_API_KEY") or os.getenv("HF_TOKEN") or "").strip()


def deepseek_enabled() -> bool:
    """DeepSeek has no free tier (HTTP 402 without balance): opt-in only."""
    return bool(os.getenv("DEEPSEEK_API_KEY")) and os.getenv("ALP_ENABLE_DEEPSEEK", "0") == "1"


def unconfigured_notes() -> List[str]:
    """Human-readable reasons a known provider is off although part of it is configured."""
    notes = []
    account, token = cloudflare_config()
    if token and not account:
        notes.append("cloudflare: CLOUDFLARE_ACCOUNT_ID is missing (token present) — provider OFF; "
                     "add the CLOUDFLARE_ACCOUNT_ID secret to enable Workers AI")
    elif account and not token:
        notes.append("cloudflare: CLOUDFLARE_API_TOKEN / CLOUDFLARE_TOKEN is missing — provider OFF")
    problem = openai_key_problem()
    if problem:
        notes.append(problem)
    if os.getenv("DEEPSEEK_API_KEY") and not deepseek_enabled():
        notes.append("deepseek: DEEPSEEK_API_KEY present but provider OFF (paid only; set ALP_ENABLE_DEEPSEEK=1 to opt in)")
    return notes


# --------------------------------------------------------------------------- #
# Provider discovery
# --------------------------------------------------------------------------- #
def _build_default_providers() -> List[Provider]:
    """Build provider list from env vars, in priority order.

    Free-tier providers come first (Groq, Gemini, Ollama, Cloudflare, SambaNova,
    Mistral, OpenRouter, NVIDIA), then capped trial/credit providers (Cohere,
    LLM7, HuggingFace, Cerebras), then OpenAI; DeepSeek (paid only, opt-in) last.
    """
    providers: List[Provider] = []

    def add(provider: Provider) -> None:
        name = provider.name.upper().replace("-", "_")
        provider.rpm_limit = _env_int(f"AI_ROUTER_RPM_{name}", provider.rpm_limit)
        provider.rpd_limit = _env_int(f"AI_ROUTER_RPD_{name}", provider.rpd_limit)
        live = _live_model_ids(provider)
        _refresh_provider_model(provider, live=live)
        # Every provider keeps a rotation list: per-model quotas rotate on 429,
        # and any provider rotates past a model retired (404/410) or hung this run.
        provider.models = _rotation_order(provider, live)
        providers.append(provider)

    # Priorities: lower runs first. Free and reliable first, trial / tiny-credit
    # / paid-ish last. Caps are per job run (shared health file), overridable
    # with AI_ROUTER_RPD_<NAME> / AI_ROUTER_RPM_<NAME>.
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        # Free plan, per model: 30 RPM, 1,000 RPD, 200k tokens/day.
        add(Provider(name="groq", url="https://api.groq.com/openai/v1/chat/completions",
                     key=groq_key, model=_env_model("GROQ_MODEL", "groq"),
                     priority=10, rpm_limit=30, rpd_limit=1000, per_model_quota=True))

    gem_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gem_key:
        add(Provider(name="gemini", url="https://generativelanguage.googleapis.com/v1beta/models",
                     key=gem_key, model=_env_model("GEMINI_MODEL", "gemini"),
                     priority=15, rpm_limit=60, rpd_limit=1500, per_model_quota=True))

    # Ollama: OLLAMA_API_KEY alone means Ollama Cloud (https://ollama.com).
    ollama_key = os.getenv("OLLAMA_API_KEY")
    ollama_url = os.getenv("OLLAMA_BASE_URL") or os.getenv("OLLAMA_API_URL") or (
        "https://ollama.com" if ollama_key else "")
    if ollama_url:
        endpoint = ollama_url.rstrip("/")
        if not endpoint.endswith("/chat/completions"):
            endpoint = f"{endpoint}/v1/chat/completions" if not endpoint.endswith("/v1") else f"{endpoint}/chat/completions"
        add(Provider(name="ollama", url=endpoint, key=ollama_key or "ollama",
                     model=_env_model("OLLAMA_MODEL", "ollama"),
                     priority=20, rpm_limit=30, rpd_limit=5000))

    cf_account, cf_token = cloudflare_config()
    if cf_account and cf_token:
        # Free allowance: 10k neurons/day (account-wide).
        add(Provider(name="cloudflare",
                     url=f"https://api.cloudflare.com/client/v4/accounts/{cf_account}/ai/v1/chat/completions",
                     key=cf_token, model=_env_model("CLOUDFLARE_MODEL", "cloudflare"),
                     priority=30, rpm_limit=30, rpd_limit=1000))

    sambanova_key = os.getenv("SAMBANOVA_API_KEY")
    if sambanova_key:
        # Free tier, per model: 20 RPM, 20 RPD, 200k tokens/day.
        base = os.getenv("SAMBANOVA_BASE_URL", "https://api.sambanova.ai/v1").rstrip("/")
        add(Provider(name="sambanova", url=f"{base}/chat/completions", key=sambanova_key,
                     model=_env_model("SAMBANOVA_MODEL", "sambanova"),
                     priority=35, rpm_limit=20, rpd_limit=20, per_model_quota=True))

    mistral_key = os.getenv("MISTRAL_API_KEY")
    if mistral_key:
        # Free Experiment plan ≈ 1 request/second.
        add(Provider(name="mistral", url="https://api.mistral.ai/v1/chat/completions",
                     key=mistral_key, model=_env_model("MISTRAL_MODEL", "mistral"),
                     priority=40, rpm_limit=60, rpd_limit=5000, min_interval=1.1))

    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        # Free tier: 20 RPM, 50 requests/day (account-wide).
        add(Provider(name="openrouter", url="https://openrouter.ai/api/v1/chat/completions",
                     key=openrouter_key, model=_env_model("OPENROUTER_MODEL", "openrouter"),
                     priority=45, rpm_limit=20, rpd_limit=50, min_interval=3.0))

    nvidia_key = os.getenv("NVIDIA_API_KEY")
    if nvidia_key:
        add(Provider(name="nvidia", url="https://integrate.api.nvidia.com/v1/chat/completions",
                     key=nvidia_key, model=_env_model("NVIDIA_MODEL", "nvidia"),
                     priority=50, rpm_limit=30, rpd_limit=5000))

    generic_url = os.getenv("LLM_API_URL")
    generic_key = os.getenv("LLM_API_KEY")
    if generic_url and generic_key:
        add(Provider(name="generic-openai", url=generic_url, key=generic_key,
                     model=_env_model("LLM_MODEL", "generic-openai"),
                     priority=55, rpm_limit=60, rpd_limit=5000))

    cohere_key = os.getenv("COHERE_API_KEY", "").strip()
    if cohere_key:
        # Trial key: 20 RPM, 1,000 calls/month → last-resort, ~30 calls/day.
        base = os.getenv("COHERE_BASE_URL", "https://api.cohere.ai/compatibility/v1").rstrip("/")
        add(Provider(name="cohere", url=f"{base}/chat/completions", key=cohere_key,
                     model=_env_model("COHERE_MODEL", "cohere"),
                     priority=60, rpm_limit=10, rpd_limit=30, min_interval=3.0))

    l7_key = llm7_key()
    if l7_key:
        # Free token: 1 RPS, 60 RPM, 250/hour, 100k tokens per 24h.
        base = os.getenv("LLM7_BASE_URL", "https://api.llm7.io/v1").rstrip("/")
        add(Provider(name="llm7", url=f"{base}/chat/completions", key=l7_key,
                     model=_env_model("LLM7_MODEL", "llm7"),
                     priority=65, rpm_limit=30, rpd_limit=60, min_interval=1.1))

    hf_key = huggingface_key()
    if hf_key:
        # Inference Providers free credit is tiny (cents/month): keep it rare.
        add(Provider(name="huggingface", url="https://router.huggingface.co/v1/chat/completions",
                     key=hf_key, model=_env_model("HUGGINGFACE_MODEL", "huggingface"),
                     priority=70, rpm_limit=10, rpd_limit=15))

    cerebras_key = os.getenv("CEREBRAS_API_KEY", "").strip()
    if cerebras_key:
        # 402 payment_required = no access on this account → out for the run.
        add(Provider(name="cerebras", url="https://api.cerebras.ai/v1/chat/completions",
                     key=cerebras_key, model=_env_model("CEREBRAS_MODEL", "cerebras"),
                     priority=75, rpm_limit=30, rpd_limit=500))

    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    if openai_key and not openai_key_problem(openai_key):
        base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        add(Provider(name="openai", url=f"{base}/chat/completions", key=openai_key,
                     model=_env_model("ALP_LLM", "openai"),
                     priority=80, rpm_limit=500, rpd_limit=10000))

    if deepseek_enabled():
        base = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
        add(Provider(name="deepseek", url=f"{base}/chat/completions", key=os.environ["DEEPSEEK_API_KEY"],
                     model=_env_model("DEEPSEEK_MODEL", "deepseek"),
                     priority=90, rpm_limit=60, rpd_limit=10000))

    for note in unconfigured_notes():
        logger.info("[Router] %s", note)
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


def find_provider(name: str) -> Optional[Provider]:
    """The router's live Provider object (without building the registry)."""
    for provider in _PROVIDERS or []:
        if provider.name == name:
            return provider
    return None


def provider_ready(name: str) -> bool:
    """Shared health check used by the translator: not cooled down, has quota."""
    provider = find_provider(name)
    if provider is not None:
        return provider.is_available()
    return not is_blocked(name)


def current_model(name: str) -> Optional[str]:
    provider = find_provider(name)
    return provider.model if provider is not None else None


def note_call(name: str) -> None:
    """Count a request made outside route() (translator) against quotas + spacing."""
    provider = find_provider(name)
    if provider is not None:
        provider.throttle()
        provider.record_call()


def report_success(name: str, provider: Optional[Provider] = None) -> None:
    provider = provider or find_provider(name)
    if provider is not None:
        provider.consecutive_transient = 0
        _strike(f"{provider.quota_key()}:429", reset=True)
    _strike(f"{name}:429", reset=True)
    _strike(f"{name}:timeout", reset=True)


def report_failure(name: str, failure: str, retry_after: Optional[float] = None,
                   provider: Optional[Provider] = None) -> bool:
    """Apply the router's cooldown policy for a failure seen anywhere.

    Returns True when the provider can be retried right away with another model
    (per-model quota rotation after a 429), False when it should be skipped.
    Repeated 429s on the same model/provider double the cooldown (no hammering);
    a longer Retry-After / Gemini retryDelay always wins.
    """
    provider = provider or find_provider(name)
    if failure == FailureType.RATE_LIMIT:
        per_model = provider is not None and provider.per_model_quota and len(provider.models) > 1
        key = f"{name}::{provider.model}" if per_model else name
        strikes = _strike(f"{key}:429")
        cooldown = min(RATE_LIMIT_MAX_COOLDOWN,
                       max(float(retry_after or 0), RATE_LIMIT_COOLDOWN * (2 ** min(strikes - 1, 6))))
        if per_model:
            block(key, cooldown, "rate limited (model quota)")
            if provider.rotate_model():
                return True
            # Every model is out: the provider is unavailable until the first returns.
            until = min(blocked_until(f"{name}::{m}") or (time.time() + 1) for m in provider.models)
            block(name, max(1.0, until - time.time()), "rate limited (all models)")
            return False
        if provider is not None:
            provider.mark_disabled("rate limited", int(cooldown))
        else:
            block(name, cooldown, "rate limited")
        return False
    if failure == FailureType.AUTH_ERROR:
        # 401/403 bad key, 402 no balance / payment required: out for the run.
        if provider is not None:
            provider.mark_disabled("auth/credit error", AUTH_COOLDOWN)
        else:
            block(name, AUTH_COOLDOWN, "auth/credit error")
        return False
    if failure == FailureType.MODEL_ERROR:
        # 404/410: this model is retired (e.g. NVIDIA meta/llama-3.1-8b-instruct
        # EOL, Gemini 2.5-flash-lite for new keys). Retire it for the run and
        # rotate; only when no model is left is the provider out.
        if provider is None:
            block(name, AUTH_COOLDOWN, "model not found")
            return False
        block(f"{name}::{provider.model}", AUTH_COOLDOWN, "model retired / not found (404/410)")
        if provider.rotate_model(force=True):
            return True
        if _refresh_provider_model(provider, exclude={provider.model}):
            return True
        provider.mark_disabled("model not found", AUTH_COOLDOWN)
        return False
    if failure == FailureType.TIMEOUT and provider is not None and len(provider.models) > 1 \
            and name in _PROVIDER_TIMEOUTS:
        # A hung model (Gemini 3.5-flash-lite, 40s+) is parked; the next call
        # uses the next model instead of waiting on the same one again.
        block(f"{name}::{provider.model}", TIMEOUT_COOLDOWN, "model timed out")
        if provider.rotate_model(force=True):
            return False  # next provider for this call; later calls use the new model
    if failure == FailureType.TIMEOUT:
        if _strike(f"{name}:timeout") >= TRANSIENT_STRIKES:
            _strike(f"{name}:timeout", reset=True)
            if provider is not None:
                provider.mark_disabled("repeated timeouts", TIMEOUT_COOLDOWN)
            else:
                block(name, TIMEOUT_COOLDOWN, "repeated timeouts")
        return False
    if failure == FailureType.TRANSIENT and provider is not None:
        provider.consecutive_transient += 1
        if provider.consecutive_transient >= TRANSIENT_STRIKES:
            provider.consecutive_transient = 0
            provider.mark_disabled("repeated timeouts/5xx", TRANSIENT_COOLDOWN)
    return False


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
        # 402 = no credit / paid model; treated like auth: provider is out for the run.
        return FailureType.AUTH_ERROR
    if status in (404, 410):
        return FailureType.MODEL_ERROR
    if 400 <= status < 500:
        return FailureType.BAD_REQUEST
    if 500 <= status < 600:
        return FailureType.TRANSIENT
    return FailureType.UNKNOWN


_LAST = threading.local()  # retry_after of the last 429 seen by this thread


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
    _LAST.retry_after = None
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
        r = requests.post(url, headers=headers, json=payload,
                          timeout=request_timeout(provider.name, task))
    except requests.Timeout:
        return None, FailureType.TIMEOUT
    except requests.RequestException as exc:
        logger.debug("[Router] %s network error: %s", provider.name, type(exc).__name__)
        return None, FailureType.TRANSIENT

    if r.status_code >= 400:
        body = getattr(r, "text", "") or ""
        ft = _classify_error(r.status_code, body[:200])
        if ft == FailureType.RATE_LIMIT:
            _LAST.retry_after = parse_retry_after(getattr(r, "headers", None), body[:4000])
        logger.warning("[Router] %s HTTP %d (%s, model=%s): %s",
                       provider.name, r.status_code, ft, provider.model, body[:200])
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

    if _deadline_passed():
        if fail_on_all:
            raise RuntimeError("stage AI time budget used")
        return None

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
        rotations = 0
        while True:
            if _deadline_passed():
                break
            if not provider.is_available():
                logger.debug("[Router] %s skipped (unavailable)", provider.name)
                break

            logger.debug("[Router] Trying %s (model=%s)", provider.name, provider.model)
            provider.throttle()
            provider.record_call()

            content, failure = _call_provider(
                provider, prompt, task, needs_hindi, response_format, system_prompt
            )

            if content is not None:
                report_success(provider.name, provider)
                _CACHE.put(ck, content)
                logger.info("[Router] ✔ %s responded (task=%s, model=%s, %d chars)",
                            provider.name, task, provider.model, len(content))
                record_ai_usage(provider.name, provider.model, task, True)
                return content

            # Failure handling
            last_error = f"{provider.name}: {failure}"
            record_ai_usage(provider.name, provider.model, task, False, str(failure))
            retry_after = getattr(_LAST, "retry_after", None)
            if report_failure(provider.name, failure, retry_after, provider) and rotations < len(provider.models):
                rotations += 1
                continue  # same provider, next model (per-model quota / retired model)
            break
        # TIMEOUT / TRANSIENT / MALFORMED / BAD_REQUEST → next provider

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
                "models": list(p.models),
                "available": p.is_available(),
                "disabled_for": max(0, int(max(p.disabled_until, blocked_until(p.name)) - now)),
                "last_error": p.last_error,
                "calls_last_hour": sum(1 for t in p.call_times if now - t < 3600),
                "rpm_limit": p.rpm_limit,
                "rpd_limit": p.rpd_limit,
            }
            for p in providers
        ],
        "health": health_snapshot(),
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
    """Full reset — clear cache, providers, call counts, health. For tests."""
    _CACHE.clear()
    with _CALL_LOCK:
        _CALL_TIMES.clear()
    reset_providers()
    _reset_health()


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
