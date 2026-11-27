# -*- coding: utf-8 -*-
"""
LLM HELPER — Multi-provider fallback for AGRI LEARNING POINT
Chain: Gemini → Groq → OpenRouter → Mistral → NVIDIA NIM (all from env, never hardcoded)
SECURITY: keys from env only (GitHub Secrets in prod, .env locally)
"""
import os, requests, logging

def _env(key):
    v = os.getenv(key, "").strip()
    # Also try loading from .env if not in env
    if not v:
        try:
            import pathlib
            p = pathlib.Path(".env")
            if p.exists():
                for line in p.read_text().splitlines():
                    if line.startswith(key+"="):
                        v = line.split("=",1)[1].strip()
                        break
        except Exception:
            pass
    return v

def _resolve_model(provider_name: str, env_var: str) -> str:
    """Resolve explicit model or 'auto' to live best free model via ai_router."""
    configured = _env(env_var)
    if configured and configured.lower() != "auto":
        return configured
    from pipeline import ai_router
    if os.getenv("ALP_MODEL_AUTO_DISCOVERY", "0") == "1":
        for p in ai_router._build_default_providers():
            if p.name == provider_name and p.model:
                return p.model
    return ai_router._PREFERRED_MODELS[provider_name][0]


def call_groq(prompt, model=None):
    key = _env("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY missing")
    model = model or _resolve_model("groq", "GROQ_MODEL")
    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": model, "messages": [{"role":"user","content": prompt}], "temperature": 0.3},
        timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip(), f"groq/{model}"

def call_openrouter(prompt, model=None):
    key = _env("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY missing")
    model = model or _resolve_model("openrouter", "OPENROUTER_MODEL")
    r = requests.post("https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "HTTP-Referer":"https://agrilearningpoint.com","X-Title":"AGRI Learning Point"},
        json={"model": model, "messages": [{"role":"user","content": prompt}]},
        timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip(), f"openrouter/{model}"

def call_mistral(prompt, model=None):
    key = _env("MISTRAL_API_KEY")
    if not key:
        raise RuntimeError("MISTRAL_API_KEY missing")
    model = model or _resolve_model("mistral", "MISTRAL_MODEL")
    r = requests.post("https://api.mistral.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={"model": model, "messages": [{"role":"user","content": prompt}]},
        timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip(), f"mistral/{model}"

def call_nvidia(prompt, model=None):
    model = model or _resolve_model("nvidia", "NVIDIA_MODEL")
    key = _env("NVIDIA_API_KEY")
    if not key:
        raise RuntimeError("NVIDIA_API_KEY missing")
    r = requests.post("https://integrate.api.nvidia.com/v1/chat/completions",
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        json={"model": model, "messages": [{"role":"user","content": prompt}], "temperature": 0.3},
        timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip(), f"nvidia/{model}"

def call_jina_reader(url):
    """Article text via Jina Reader (r.jina.ai). JINA_API_KEY is used while it has
    balance; a 401/402/403 turns the key off for the run and the keyless reader is
    used instead. Returns text or None; never raises."""
    try:
        from pipeline.discovery_api import jina_read
        text, _image = jina_read(url)
        return text or None
    except Exception as e:  # pragma: no cover - optional helper
        logging.debug(f"jina fetch failed {str(url)[:60]}: {type(e).__name__}")
        return None

def fetch_newsdata(query="agriculture india", language="en"):
    """NewsData.io latest India news (env-gated; [] without NEWSDATA_API_KEY)."""
    try:
        from pipeline.discovery_api import newsdata_latest
        return newsdata_latest(query=query, language=language)[:10]
    except Exception as e:  # pragma: no cover - optional helper
        logging.debug(f"newsdata failed: {type(e).__name__}")
        return []

def call_llm(prompt, prefer="gemini"):
    """Multi-provider LLM with fallback — uses ai_router live auto-models first."""
    try:
        from pipeline import ai_router
        if ai_router.is_configured():
            txt = ai_router.route(prompt, task="general")
            if txt:
                return txt, "ai_router"
    except Exception:
        pass
    errors = []
    # 1. Gemini (existing)
    try:
        gem_key = _env("GEMINI_API_KEY")
        if gem_key:
            from pipeline.gemini_helper import call_gemini
            txt, mdl = call_gemini(prompt, gem_key)
            return txt, mdl
    except Exception as e:
        errors.append(f"gemini:{e}")
    # 2. Groq
    try:
        return call_groq(prompt)
    except Exception as e:
        errors.append(f"groq:{e}")
    # 3. OpenRouter
    try:
        return call_openrouter(prompt)
    except Exception as e:
        errors.append(f"openrouter:{e}")
    # 4. Mistral
    try:
        return call_mistral(prompt)
    except Exception as e:
        errors.append(f"mistral:{e}")
    try:
        return call_nvidia(prompt)
    except Exception as e:
        errors.append(f"nvidia:{e}")
    raise RuntimeError(f"All LLM providers failed: {'; '.join(errors[:3])}")
