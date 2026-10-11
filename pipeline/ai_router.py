# -*- coding: utf-8 -*-
"""
AI ROUTER — Smart load-balanced LLM router for AGRI LEARNING POINT BY SATYAM SIR
6 Free APIs: Gemini, Groq, OpenRouter, Mistral, Jina Reader, NewsData
- Auto-fallback per task   - RPM rate-limit tracking   - Chunked processing
- Self-healing: discovers new free models from provider /models endpoints
"""
import os, time, logging, pathlib
import requests

PROVIDERS = {
    "gemini":     {"rpm": 15, "rpd": 250,   "models": ["gemini-1.5-flash", "gemini-2.0-flash"]},
    "groq":       {"rpm": 30, "rpd": 14400, "models": ["openai/gpt-oss-20b", "qwen/qwen3.8-27b", "openai/gpt-oss-120b"]},
    "openrouter": {"rpm": 20, "rpd": 500,   "models": ["apodex/apodex-1.1-mini:free", "nvidia/nemotron-3.5-lightning:free", "liquid/lfm-2.5-2.6b:free", "google/gemini-flash-1.5:free"]},
    "mistral":    {"rpm": 1,  "rpd": 50,    "models": ["open-mistral-7b", "mistral-small-latest"]},
    "jina":       {"rpm": 20, "rpd": 1000,  "models": []},
    "newsdata":   {"rpm": 10, "rpd": 200,   "models": []},
}
_usage = {k: [] for k in PROVIDERS}

def _env(k):
    v = os.getenv(k, "")
    if not v:
        p = pathlib.Path(".env")
        if p.exists():
            for line in p.read_text().splitlines():
                if line.startswith(k + "="):
                    v = line.split("=", 1)[1].strip()
                    break
    return v.strip().strip('"').strip("'")

def _rate_ok(provider):
    """Track RPM per provider; sleep if near limit."""
    now = time.time()
    _usage[provider] = [t for t in _usage[provider] if now - t < 60]
    if len(_usage[provider]) >= PROVIDERS[provider]["rpm"]:
        sleep = 60 - (now - _usage[provider][0]) + 1
        logging.warning(f"[AI Router] {provider} RPM hit, sleeping {sleep:.1f}s")
        time.sleep(min(max(sleep, 1), 15))
    _usage[provider].append(time.time())

# ---------- provider calls (all return plain text str) ----------
def call_jina(url):
    """Jina Reader — fetch page as markdown via r.jina.ai (correct reader endpoint)."""
    key = _env("JINA_API_KEY")
    headers = {"Accept": "text/plain", "User-Agent": "AgriLearningPoint/1.0"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    for attempt in range(2):  # auth, then no-auth fallback
        try:
            _rate_ok("jina")
            r = requests.get("https://r.jina.ai/" + url, headers=headers, timeout=30)
            if r.status_code == 200 and len(r.text) > 300:
                return r.text
            if r.status_code in (401, 403):
                headers.pop("Authorization", None)
                continue
        except Exception as e:
            logging.debug(f"[AI Router] jina fail: {e}")
    return None

def call_gemini(prompt):
    key = _env("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY missing")
    _rate_ok("gemini")
    from pipeline.gemini_helper import call_gemini as _call
    text, model = _call(prompt, key)
    return text

def call_groq(prompt, model="openai/gpt-oss-20b"):
    key = _env("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY missing")
    _rate_ok("groq")
    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                      headers={"Authorization": f"Bearer {key}"},
                      json={"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.3},
                      timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()

def call_openrouter(prompt, model="apodex/apodex-1.1-mini:free"):
    key = _env("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY missing")
    _rate_ok("openrouter")
    r = requests.post("https://openrouter.ai/api/v1/chat/completions",
                      headers={"Authorization": f"Bearer {key}", "HTTP-Referer": "https://agrilearningpoint.com"},
                      json={"model": model, "messages": [{"role": "user", "content": prompt}]},
                      timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()

def call_mistral(prompt, model="open-mistral-7b"):
    key = _env("MISTRAL_API_KEY")
    if not key:
        raise RuntimeError("MISTRAL_API_KEY missing")
    _rate_ok("mistral")
    r = requests.post("https://api.mistral.ai/v1/chat/completions",
                      headers={"Authorization": f"Bearer {key}"},
                      json={"model": model, "messages": [{"role": "user", "content": prompt}]},
                      timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()

def discover_openrouter_free():
    """Self-healing: pull current free models from OpenRouter /models."""
    key = _env("OPENROUTER_API_KEY")
    try:
        h = {"Authorization": f"Bearer {key}"} if key else {}
        r = requests.get("https://openrouter.ai/api/v1/models", headers=h, timeout=15)
        if r.status_code == 200:
            data = r.json().get("data", [])
            free = [m["id"] for m in data if m.get("id", "").endswith(":free")]
            if free:
                PROVIDERS["openrouter"]["models"] = free[:5]
                logging.info(f"[AI Router] discovered {len(free)} free OpenRouter models: {free[:3]}")
                return free[:5]
    except Exception as e:
        logging.debug(f"[AI Router] discover fail: {e}")
    return []

# ---------- NewsData.io collection (6th key) ----------
def collect_news(query, language="en", country="in", limit=10):
    """NewsData.io API — paginated (free tier: 10 results/page, 200 credits/day)."""
    key = _env("NEWSDATA_API_KEY")
    if not key:
        raise RuntimeError("NEWSDATA_API_KEY not set")
    articles, page_token = [], None
    for _page in range(min(3, (limit + 9) // 10)):  # max 3 pages = 3 credits per query
        params = {"apikey": key, "q": query, "language": language,
                  "country": country, "size": 10}
        if page_token:
            params["page"] = page_token
        _rate_ok("newsdata")
        try:
            r = requests.get("https://newsdata.io/api/1/news", params=params, timeout=20)
            if r.status_code != 200:
                logging.warning(f"[AI Router] NewsData {r.status_code}: {r.text[:120]}")
                break
            data = r.json()
            articles.extend(data.get("results") or [])
            page_token = data.get("nextPage")
            if not page_token or len(articles) >= limit:
                break
            time.sleep(1.5)  # NewsData free tier is strict between pages
        except Exception as e:
            logging.warning(f"[AI Router] NewsData fail: {e}")
            break
    return articles[:limit]


def read_url(url):
    """Pasted-dashboard API compat: raises on failure instead of returning None."""
    text = call_jina(url)
    if not text:
        raise RuntimeError(f"Jina could not read {url[:80]}")
    return text


# ---------- smart routing ----------
TASK_ORDER = {
    "verify":    ["groq", "gemini", "openrouter", "mistral"],
    "content":   ["groq", "gemini", "openrouter", "mistral"],
    "bilingual": ["gemini", "groq", "mistral"],          # Gemini best Hindi
    "mcq":       ["groq", "openrouter", "gemini"],
    "scoring":   ["gemini", "groq", "openrouter"],
}

def route(prompt, task="content", needs_hindi=False):
    """Pick provider by task, fallback on error, self-heal on 404. Returns text str.
    needs_hindi=True forces Gemini-first (best Devanagari quality)."""
    order = TASK_ORDER.get(task, TASK_ORDER["content"])
    if needs_hindi:
        order = ["gemini"] + [p for p in order if p != "gemini"]
    last_err = None
    for provider in order:
        for model in PROVIDERS[provider]["models"]:
            try:
                if provider == "gemini":
                    return call_gemini(prompt)
                if provider == "groq":
                    return call_groq(prompt, model)
                if provider == "openrouter":
                    return call_openrouter(prompt, model)
                if provider == "mistral":
                    return call_mistral(prompt, model)
            except Exception as e:
                last_err = e
                msg = str(e).lower()
                logging.warning(f"[AI Router] {provider}/{model} fail ({msg[:80]}) -> next")
                if "404" in msg or "model_not_found" in msg or "does not exist" in msg:
                    if provider == "openrouter":
                        discover_openrouter_free()
                    break  # refresh list before retrying provider
                if "429" in msg or "rate" in msg or "quota" in msg:
                    break  # provider exhausted -> next provider
    raise RuntimeError(f"[AI Router] all providers failed for task={task}: {last_err}")

# ---------- chunked processing ----------
def chunked(items, func, chunk_size=5, delay=3):
    """Run func on chunks of items with delay between chunks (rate-limit safe)."""
    out = []
    total = (len(items) + chunk_size - 1) // chunk_size
    for i in range(0, len(items), chunk_size):
        batch = items[i:i + chunk_size]
        logging.info(f"[AI Router] chunk {i // chunk_size + 1}/{total} size={len(batch)}")
        res = func(batch)
        if isinstance(res, list):
            out.extend(res)
        elif res is not None:
            out.append(res)
        if i + chunk_size < len(items):
            time.sleep(delay)
    return out
