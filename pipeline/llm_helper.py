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

def call_groq(prompt, model="openai/gpt-oss-20b"):
    key = _env("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY missing")
    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": model, "messages": [{"role":"user","content": prompt}], "temperature": 0.3},
        timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip(), f"groq/{model}"

def call_openrouter(prompt, model="google/gemini-flash-1.5"):
    key = _env("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY missing")
    r = requests.post("https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "HTTP-Referer":"https://agrilearningpoint.com","X-Title":"AGRI Learning Point"},
        json={"model": model, "messages": [{"role":"user","content": prompt}]},
        timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip(), f"openrouter/{model}"

def call_mistral(prompt, model="mistral-large-latest"):
    key = _env("MISTRAL_API_KEY")
    if not key:
        raise RuntimeError("MISTRAL_API_KEY missing")
    r = requests.post("https://api.mistral.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={"model": model, "messages": [{"role":"user","content": prompt}]},
        timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip(), f"mistral/{model}"

def call_nvidia(prompt, model=None):
    model = model or _env("NVIDIA_MODEL") or "meta/llama-3.3-70b-instruct"
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
    """Fetch URL via Jina Reader API (correct endpoint: r.jina.ai, better JS handling)"""
    key = _env("JINA_API_KEY")
    headers = {"Accept": "text/plain", "User-Agent": "AgriLearningPoint/1.0"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    for attempt in range(2):  # auth first, then no-auth fallback
        try:
            r = requests.get(f"https://r.jina.ai/{url}", headers=headers, timeout=30)
            if r.status_code == 200 and len(r.text) > 300:
                return r.text
            if r.status_code in (401, 403):
                headers.pop("Authorization", None)
                continue
        except Exception as e:
            logging.debug(f"jina fetch failed {url[:60]}: {e}")
    return None

def fetch_newsdata(query="agriculture india", language="en"):
    """NewsData.io fetch for AGRI news"""
    key = _env("NEWSDATA_API_KEY")
    if not key:
        return []
    try:
        r = requests.get("https://newsdata.io/api/1/news",
            params={"apikey": key, "q": query, "language": language, "country":"in", "category":"business,politics"},
            timeout=20)
        if r.status_code == 200:
            return r.json().get("results", [])[:10]
    except Exception as e:
        logging.debug(f"newsdata failed: {e}")
    return []

def call_llm(prompt, prefer="gemini"):
    """Multi-provider LLM with fallback — tries all keys from env"""
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
