# -*- coding: utf-8 -*-
"""
MODEL MANAGER — Self-healing LLM model registry with load distribution
- Manages 6 providers: Gemini, Groq, OpenRouter, Mistral, Jina, NewsData
- On model error: fetches provider's /models endpoint, picks FREE models matching task
- Load distribution: round-robin + per-provider RPM tracking + exponential backoff
- Batch division: news work split into 5-10 item chunks to avoid burst limits
"""
import os, time, json, logging, requests, pathlib

PROVIDER_MODELS = {
    "gemini": ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-flash-latest", "gemini-2.5-flash"],
    "groq": ["openai/gpt-oss-20b", "qwen/qwen3.8-27b", "openai/gpt-oss-120b"],
    "openrouter": ["apodex/apodex-1.1-mini:free", "nvidia/nemotron-3.5-lightning:free", "liquid/lfm-2.5-2.6b:free", "google/gemini-flash-1.5:free"],
    "mistral": ["mistral-small-latest", "mistral-large-latest", "open-mistral-7b", "open-mixtral-8x7b"],
}

# RPM limits (conservative)
RPM_LIMITS = {"gemini": 60, "groq": 30, "openrouter": 20, "mistral": 30, "jina": 100, "newsdata": 10}
_usage = {k: [] for k in RPM_LIMITS}  # timestamps of recent calls

def _env(k):
    v = os.getenv(k, "").strip()
    if not v:
        try:
            p = pathlib.Path(".env")
            if p.exists():
                for line in p.read_text().splitlines():
                    if line.startswith(k+"="):
                        v = line.split("=",1)[1].strip()
                        break
        except: pass
    return v

def _check_rate_limit(provider):
    now = time.time()
    window = [t for t in _usage[provider] if now - t < 60]
    _usage[provider] = window
    if len(window) >= RPM_LIMITS.get(provider, 30):
        sleep = 60 - (now - window[0]) + 1
        logging.warning(f"[model_manager] {provider} RPM limit hit, sleep {sleep:.0f}s")
        time.sleep(min(sleep, 10))
        return False
    _usage[provider].append(now)
    return True

def _fetch_available_models(provider):
    """Fetch free models from provider's /models endpoint"""
    try:
        if provider == "groq":
            key = _env("GROQ_API_KEY")
            if not key: return []
            r = requests.get("https://api.groq.com/openai/v1/models", headers={"Authorization": f"Bearer {key}"}, timeout=15)
            if r.status_code == 200:
                return [m["id"] for m in r.json().get("data", []) if "whisper" not in m["id"]]
        elif provider == "openrouter":
            key = _env("OPENROUTER_API_KEY")
            r = requests.get("https://openrouter.ai/api/v1/models", headers={"Authorization": f"Bearer {key}"} if key else {}, timeout=15)
            if r.status_code == 200:
                # Prefer free models
                free = [m["id"] for m in r.json().get("data", []) if ":free" in m["id"]]
                return free[:6] if free else [m["id"] for m in r.json().get("data", [])][:4]
        elif provider == "gemini":
            key = _env("GEMINI_API_KEY")
            if not key: return []
            r = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={key}", timeout=15)
            if r.status_code == 200:
                return [m["name"].replace("models/","") for m in r.json().get("models",[]) if "generateContent" in m.get("supportedGenerationMethods",[])]
        elif provider == "mistral":
            key = _env("MISTRAL_API_KEY")
            if not key: return []
            r = requests.get("https://api.mistral.ai/v1/models", headers={"Authorization": f"Bearer {key}"}, timeout=15)
            if r.status_code == 200:
                return [m["id"] for m in r.json().get("data",[])]
    except Exception as e:
        logging.debug(f"[model_manager] fetch {provider} failed: {e}")
    return []

def get_models(provider, refresh=False):
    """Get models, auto-refresh on error"""
    if refresh:
        fetched = _fetch_available_models(provider)
        if fetched:
            PROVIDER_MODELS[provider] = fetched
            logging.info(f"[model_manager] {provider} refreshed: {fetched[:3]}")
    return PROVIDER_MODELS.get(provider, [])

def call_with_fallback(prompt, task="content", batch_size=5):
    """
    Load-distributed LLM call with batching
    - task: content/mcq/translation/scoring
    - batch_size: items per call (5-10 to avoid limit)
    - Tries providers in priority order, rotates on 429/500, refreshes model list on 404
    """
    providers = ["gemini", "groq", "openrouter", "mistral"]
    # For translation/content prefer groq (fast), for scoring prefer gemini
    if task in ("translation", "bilingual"):
        providers = ["groq", "gemini", "openrouter", "mistral"]
    elif task == "scoring":
        providers = ["gemini", "groq", "mistral", "openrouter"]
    
    last_err = None
    for provider in providers:
        _check_rate_limit(provider)
        models = get_models(provider)
        for model in models:
            try:
                logging.info(f"[model_manager] trying {provider}/{model} for {task}")
                if provider == "gemini":
                    from pipeline.gemini_helper import call_gemini
                    key = _env("GEMINI_API_KEY")
                    txt, used = call_gemini(prompt, key)
                    return txt, used
                elif provider == "groq":
                    from pipeline.llm_helper import call_groq
                    txt, used = call_groq(prompt, model)
                    return txt, used
                elif provider == "openrouter":
                    from pipeline.llm_helper import call_openrouter
                    txt, used = call_openrouter(prompt, model)
                    return txt, used
                elif provider == "mistral":
                    from pipeline.llm_helper import call_mistral
                    txt, used = call_mistral(prompt, model)
                    return txt, used
            except Exception as e:
                err = str(e).lower()
                last_err = e
                # On 404/model not found → refresh model list from website
                if "404" in err or "not found" in err or "model" in err:
                    logging.warning(f"[model_manager] {provider}/{model} 404 → refreshing free models from {provider} website")
                    get_models(provider, refresh=True)
                # On 429/rate limit → try next provider
                if "429" in err or "rate" in err or "limit" in err:
                    logging.warning(f"[model_manager] {provider} rate limited, next provider")
                    break
                # On 500 → retry next model
                continue
    raise RuntimeError(f"All providers failed for {task}: {last_err}")

def batch_process(items, func, batch_size=7, delay=1.5):
    """
    Divide work into multiple batches to avoid burst limits
    func: callable(batch) -> results
    """
    results = []
    for i in range(0, len(items), batch_size):
        batch = items[i:i+batch_size]
        logging.info(f"[model_manager] batch {i//batch_size+1}/{(len(items)+batch_size-1)//batch_size} size {len(batch)}")
        try:
            out = func(batch)
            results.extend(out if isinstance(out, list) else [out])
        except Exception as e:
            logging.error(f"batch {i} failed: {e}")
            # Retry with smaller batch
            if len(batch) > 3:
                results.extend(batch_process(batch, func, batch_size=3, delay=delay))
            else:
                raise
        if i + batch_size < len(items):
            time.sleep(delay)  # gap between batches
    return results
