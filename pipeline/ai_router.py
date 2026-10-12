# -*- coding: utf-8 -*-
"""SMART AI ROUTER — Intelligent Multi-Provider Load Balancer"""
import os, json, time, logging, re
from datetime import datetime
from typing import Optional, Dict, List, Callable

logger = logging.getLogger(__name__)

PROVIDERS = {
    "gemini": {
        "name": "Google Gemini", "env_key": "GEMINI_API_KEY",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "free_models": ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash-8b"],
        "rate_limits": {"rpm": 15, "rpd": 250},
        "strengths": ["content", "translation", "bilingual", "hindi", "mcq", "summary", "verification"],
        "hindi_quality": 0.95, "priority": 1,
    },
    "groq": {
        "name": "Groq", "env_key": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
        "free_models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"],
        "rate_limits": {"rpm": 30, "rpd": 14400},
        "strengths": ["verification", "mcq", "scoring", "fast_parallel", "content", "summary"],
        "hindi_quality": 0.75, "priority": 2,
    },
    "openrouter": {
        "name": "OpenRouter", "env_key": "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
        "free_models": ["meta-llama/llama-4-maverick:free", "deepseek/deepseek-r1:free",
                        "qwen/qwen-2.5-72b-instruct:free", "google/gemma-3-27b-it:free"],
        "rate_limits": {"rpm": 20, "rpd": 500},
        "strengths": ["fallback", "content", "verification", "diversity", "bilingual", "mcq"],
        "hindi_quality": 0.80, "priority": 3,
    },
    "mistral": {
        "name": "Mistral", "env_key": "MISTRAL_API_KEY",
        "base_url": "https://api.mistral.ai/v1",
        "free_models": ["mistral-small-latest", "open-mistral-7b"],
        "rate_limits": {"rpm": 1, "rpd": 50},
        "strengths": ["structure", "mcq", "validation", "content"],
        "hindi_quality": 0.60, "priority": 4,
    },
    "jina": {
        "name": "Jina Reader", "env_key": "JINA_API_KEY",
        "base_url": "https://r.jina.ai",
        "free_models": ["reader"],
        "rate_limits": {"rpm": 20, "rpd": 1000},
        "strengths": ["web_scraping", "content_extraction", "search"],
        "hindi_quality": 0.0, "priority": 1,
    },
    "newsdata": {
        "name": "NewsData", "env_key": "NEWSDATA_API_KEY",
        "base_url": "https://newsdata.io/api/1",
        "free_models": ["news"],
        "rate_limits": {"rpm": 2, "rpd": 200},
        "strengths": ["news_collection", "india_news", "hindi_news"],
        "hindi_quality": 0.0, "priority": 1,
    },
}

class RateLimitTracker:
    def __init__(self):
        self.usage = {}
        self._state_file = os.path.join(os.getcwd(), "data", "ai_router_state.json")
        self._load_state()

    def _load_state(self):
        try:
            if os.path.exists(self._state_file):
                with open(self._state_file) as f:
                    self.usage = json.load(f)
        except Exception:
            self.usage = {}

    def _save_state(self):
        try:
            os.makedirs(os.path.dirname(self._state_file), exist_ok=True)
            with open(self._state_file, "w") as f:
                json.dump(self.usage, f)
        except Exception:
            pass

    def can_use(self, provider: str) -> bool:
        limits = PROVIDERS[provider]["rate_limits"]
        now = datetime.now()
        if provider not in self.usage:
            self.usage[provider] = {"requests": [], "date": now.strftime("%Y-%m-%d")}
        state = self.usage[provider]
        if state.get("date") != now.strftime("%Y-%m-%d"):
            state["requests"] = []
            state["date"] = now.strftime("%Y-%m-%d")
        recent = [t for t in state["requests"] if (now - datetime.fromisoformat(t)).total_seconds() < 60]
        state["requests"] = recent
        if len(recent) >= limits["rpm"] * 0.8:
            return False
        if len(state["requests"]) >= limits["rpd"] * 0.8:
            return False
        return True

    def record_usage(self, provider: str):
        now = datetime.now()
        if provider not in self.usage:
            self.usage[provider] = {"requests": [], "date": now.strftime("%Y-%m-%d")}
        state = self.usage[provider]
        if state.get("date") != now.strftime("%Y-%m-%d"):
            state["requests"] = []
            state["date"] = now.strftime("%Y-%m-%d")
        state["requests"].append(now.isoformat())
        self._save_state()

class AIRouter:
    def __init__(self):
        self.tracker = RateLimitTracker()
        self.failed_models = {}
        self._available = self._check_providers()
        logger.info(f"[AI Router] Available: {list(self._available.keys())}")

    def _check_providers(self):
        available = {}
        for name, cfg in PROVIDERS.items():
            key = os.environ.get(cfg["env_key"], "")
            if key and len(key) > 5:
                available[name] = cfg
        return available

    def _select_provider(self, task: str, needs_hindi: bool = False):
        candidates = []
        for name, cfg in self._available.items():
            if name in ("jina", "newsdata"):
                continue
            if task not in cfg["strengths"] and "fallback" not in cfg["strengths"]:
                continue
            if needs_hindi and cfg["hindi_quality"] < 0.5:
                continue
            if not self.tracker.can_use(name):
                continue
            score = (1.0 / cfg["priority"])
            if needs_hindi:
                score *= cfg["hindi_quality"]
            candidates.append((name, score))
        if not candidates:
            for name in self._available:
                if name not in ("jina", "newsdata") and self.tracker.can_use(name):
                    candidates.append((name, 0.1))
        if not candidates:
            return None
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def _select_model(self, provider: str):
        models = PROVIDERS[provider]["free_models"]
        for model in models:
            if self.failed_models.get(model, 0) < 3:
                return model
        return None

    def _call_gemini(self, model, prompt, system=""):
        import requests
        key = os.environ["GEMINI_API_KEY"]
        url = f"{PROVIDERS['gemini']['base_url']}/models/{model}:generateContent?key={key}"
        body = {"contents": [{"parts": [{"text": prompt}]}]}
        if system:
            body["system_instruction"] = {"parts": [{"text": system}]}
        r = requests.post(url, json=body, timeout=60)
        if r.status_code != 200:
            raise Exception(f"Gemini {r.status_code}: {r.text[:200]}")
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]

    def _call_openai_compat(self, provider, model, prompt, system=""):
        import requests
        cfg = PROVIDERS[provider]
        key = os.environ[cfg["env_key"]]
        url = f"{cfg['base_url']}/chat/completions"
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        if provider == "openrouter":
            headers["HTTP-Referer"] = "https://agrilearningpoint.github.io"
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        r = requests.post(url, headers=headers, json={"model": model, "messages": messages, "temperature": 0.3}, timeout=60)
        if r.status_code != 200:
            raise Exception(f"{provider} {r.status_code}: {r.text[:200]}")
        return r.json()["choices"][0]["message"]["content"]

    def generate(self, prompt, task="content", system="", needs_hindi=False, max_retries=3):
        task_systems = {
            "content": "You are a bilingual current affairs writer for competitive exam students. Write clear, accurate content. Never invent facts.",
            "verification": "You are a fact-checker. Verify claims strictly. Respond in JSON: {verified: bool, confidence: float, claims_verified: [], claims_unverified: [], reason: str}",
            "bilingual": "Translate to Hindi (Devanagari). Keep numbers/names as-is. Return same number of lines as input.",
            "mcq": "Create MCQs for Indian competitive exams. 4 options, exactly 1 correct. Include explanation. Respond in JSON array.",
            "summary": "Summarize news concisely. Extract key facts, dates, numbers.",
            "translation": "Translate accurately. Use Devanagari for Hindi.",
            "scoring": "Rate importance 0-100 based on exam relevance, student impact, policy significance.",
        }
        if not system:
            system = task_systems.get(task, "")
        last_error = None
        for attempt in range(max_retries):
            provider = self._select_provider(task, needs_hindi)
            if not provider:
                if attempt < max_retries - 1:
                    time.sleep(5)
                    continue
                raise Exception("All AI providers exhausted")
            model = self._select_model(provider)
            if not model:
                continue
            try:
                logger.info(f"[AI Router] {provider}/{model} (task={task})")
                if provider == "gemini":
                    result = self._call_gemini(model, prompt, system)
                else:
                    result = self._call_openai_compat(provider, model, prompt, system)
                self.tracker.record_usage(provider)
                if model in self.failed_models:
                    del self.failed_models[model]
                return result
            except Exception as e:
                last_error = e
                self.failed_models[model] = self.failed_models.get(model, 0) + 1
                self.tracker.record_usage(provider)
                time.sleep(1 + attempt)
        raise Exception(f"AI generation failed: {last_error}")

    def read_url(self, url):
        import requests
        key = os.environ.get("JINA_API_KEY", "")
        headers = {"Accept": "text/markdown"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        r = requests.get(f"https://r.jina.ai/{url}", headers=headers, timeout=30)
        if r.status_code == 200:
            self.tracker.record_usage("jina")
            return r.text
        raise Exception(f"Jina error: {r.status_code}")

    def collect_news(self, query, language="en", country="in", limit=50):
        import requests
        key = os.environ.get("NEWSDATA_API_KEY", "")
        if not key:
            raise Exception("NEWSDATA_API_KEY not set")
        url = f"{PROVIDERS['newsdata']['base_url']}/news"
        params = {"apikey": key, "q": query, "language": language, "country": country, "size": min(limit, 10)}
        articles = []
        data = {}
        for _ in range((limit + 9) // 10):
            if _ > 0 and not data.get("nextPage"):
                break
            if _ > 0:
                params["page"] = data["nextPage"]
                time.sleep(1)
            try:
                r = requests.get(url, params=params, timeout=15)
                if r.status_code != 200:
                    break
                data = r.json()
                articles.extend(data.get("results", []))
                self.tracker.record_usage("newsdata")
            except Exception:
                break
        return articles[:limit]

_router_instance = None

def get_router():
    global _router_instance
    if _router_instance is None:
        _router_instance = AIRouter()
    return _router_instance

def route(prompt, task="content", needs_hindi=False, **kwargs):
    return get_router().generate(prompt, task=task, needs_hindi=needs_hindi, **kwargs)

def chunked(items, process_fn, chunk_size=5, delay=3):
    results = []
    total = (len(items) + chunk_size - 1) // chunk_size
    for i in range(0, len(items), chunk_size):
        chunk = items[i:i + chunk_size]
        n = (i // chunk_size) + 1
        logger.info(f"[AI Router] Chunk {n}/{total} ({len(chunk)} items)")
        try:
            result = process_fn(chunk)
            if isinstance(result, list):
                results.extend(result)
            else:
                results.append(result)
        except Exception as e:
            logger.error(f"[AI Router] Chunk {n} failed: {e}")
        if i + chunk_size < len(items):
            time.sleep(delay)
    return results

def read_url(url):
    return get_router().read_url(url)

def collect_news(query, **kwargs):
    return get_router().collect_news(query, **kwargs)
