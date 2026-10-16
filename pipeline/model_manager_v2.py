# -*- coding: utf-8 -*-
"""
MODEL MANAGER v2 — Robust AI Model Management with Real Testing
Agri Learning Point Pipeline — Production-Ready

Features:
  ✅ Actual inference testing on startup
  ✅ Configurable model fallback chains
  ✅ Rate-limit tracking with proper cooldown
  ✅ Provider health monitoring
  ✅ No fake fallback — API key ≠ ready provider

Usage:
  from pipeline.model_manager_v2 import ModelManagerV2
  
  manager = ModelManagerV2()
  manager.initialize()
  
  result = manager.call_with_fallback(prompt, task="content")
"""

import os, json, time, logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

class ProviderStatus(Enum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    RATE_LIMITED = "rate_limited"

PROVIDER_CONFIGS = {
    "gemini": {
        "env_key": "GEMINI_API_KEY",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "models": ["gemini-2.5-flash", "gemini-2.0-flash"],
        "rate_limits": {"rpm": 15, "rpd": 250},
        "test_prompt": "Say 'Hello' in one word.",
        "expected_response": ["hello", "hi"],
        "cooldown_seconds": 60,
        "priority": 1,
    },
    "groq": {
        "env_key": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
        "models": ["openai/gpt-oss-120b", "openai/gpt-oss-20b"],
        "rate_limits": {"rpm": 30, "rpd": 14400},
        "test_prompt": "Say 'Hello' in one word.",
        "expected_response": ["hello", "hi"],
        "cooldown_seconds": 30,
        "priority": 2,
    },
    "openrouter": {
        "env_key": "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
        "models": ["meta-llama/llama-4-maverick:free"],
        "rate_limits": {"rpm": 20, "rpd": 500},
        "test_prompt": "Say 'Hello' in one word.",
        "expected_response": ["hello", "hi"],
        "cooldown_seconds": 30,
        "priority": 3,
    },
    "nvidia": {
        "env_key": "NVIDIA_API_KEY",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "models": [os.getenv("NVIDIA_MODEL", "meta/llama-3.3-70b-instruct")],
        "rate_limits": {"rpm": 30, "rpd": 5000},
        "test_prompt": "Say 'Hello' in one word.",
        "expected_response": ["hello", "hi"],
        "cooldown_seconds": 30,
        "priority": 4,
    },
}

TASK_FALLBACK_CHAINS = {
    "content": ["groq", "gemini", "openrouter", "nvidia"],
    "verification": ["groq", "gemini", "openrouter", "nvidia"],
    "bilingual": ["gemini", "groq", "nvidia"],
    "mcq": ["groq", "openrouter", "gemini", "nvidia"],
}


class ProviderHealth:
    def __init__(self, provider_name: str, config: Dict):
        self.name = provider_name
        self.config = config
        self.status = ProviderStatus.UNKNOWN
        self.last_test_time = None
        self.last_test_success = None
        self.last_error = None
        self.cooldown_until = None
        self.request_timestamps = []
        self.daily_request_count = 0
        self.daily_reset_date = datetime.now().date()
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
    
    def can_use(self) -> bool:
        if self.cooldown_until and datetime.now() < self.cooldown_until:
            return False
        
        now = datetime.now()
        
        if now.date() > self.daily_reset_date:
            self.daily_request_count = 0
            self.daily_reset_date = now.date()
        
        recent_requests = [t for t in self.request_timestamps 
                          if (now - t).total_seconds() < 60]
        self.request_timestamps = recent_requests
        
        rpm_limit = self.config["rate_limits"]["rpm"]
        if len(recent_requests) >= rpm_limit * 0.8:
            self.status = ProviderStatus.RATE_LIMITED
            return False
        
        rpd_limit = self.config["rate_limits"]["rpd"]
        if self.daily_request_count >= rpd_limit * 0.8:
            self.status = ProviderStatus.RATE_LIMITED
            return False
        
        if self.status == ProviderStatus.UNHEALTHY:
            return False
        
        return True
    
    def record_request(self, success: bool, error: str = None):
        now = datetime.now()
        self.request_timestamps.append(now)
        self.daily_request_count += 1
        self.total_requests += 1
        
        if success:
            self.successful_requests += 1
            self.status = ProviderStatus.HEALTHY
            self.last_error = None
        else:
            self.failed_requests += 1
            self.last_error = error
            cooldown_seconds = self.config.get("cooldown_seconds", 60)
            self.cooldown_until = now + timedelta(seconds=cooldown_seconds)
            
            if self.failed_requests > 3:
                self.status = ProviderStatus.UNHEALTHY
            else:
                self.status = ProviderStatus.DEGRADED
    
    def record_test(self, success: bool, error: str = None):
        self.last_test_time = datetime.now()
        self.last_test_success = success
        self.last_error = error
        
        if success:
            self.status = ProviderStatus.HEALTHY
        else:
            self.status = ProviderStatus.UNHEALTHY


class ModelManagerV2:
    def __init__(self):
        self.providers: Dict[str, ProviderHealth] = {}
        self._initialized = False
        logger.info("[Model Manager v2] Initialized")
    
    def initialize(self):
        if self._initialized:
            return
        
        logger.info("[Model Manager v2] Initializing and testing providers...")
        
        for name, config in PROVIDER_CONFIGS.items():
            self.providers[name] = ProviderHealth(name, config)
        
        for name, health in self.providers.items():
            self._test_provider(name, health)
        
        self._initialized = True
        
        healthy = sum(1 for h in self.providers.values() if h.status == ProviderStatus.HEALTHY)
        logger.info(f"[Model Manager v2] {healthy}/{len(self.providers)} providers healthy")
    
    def _test_provider(self, name: str, health: ProviderHealth):
        api_key = os.getenv(health.config["env_key"], "")
        if not api_key:
            health.record_test(False, "API key missing")
            return
        
        config = health.config
        test_prompt = config["test_prompt"]
        expected_responses = config["expected_response"]
        
        try:
            for model in config["models"]:
                try:
                    response = self._call_provider(name, model, test_prompt, api_key)
                    response_lower = response.lower().strip()
                    if any(exp in response_lower for exp in expected_responses):
                        health.record_test(True)
                        return
                except Exception as e:
                    continue
            
            health.record_test(False, "All models failed test")
        except Exception as e:
            health.record_test(False, str(e))
    
    def _call_provider(self, provider: str, model: str, prompt: str, api_key: str) -> str:
        import requests
        
        config = PROVIDER_CONFIGS[provider]
        base_url = config["base_url"]
        
        if provider == "gemini":
            url = f"{base_url}/models/{model}:generateContent?key={api_key}"
            body = {"contents": [{"parts": [{"text": prompt}]}]}
            r = requests.post(url, json=body, timeout=30)
            if r.status_code != 200:
                raise Exception(f"Gemini error {r.status_code}")
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        else:
            url = f"{base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            body = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
            }
            r = requests.post(url, headers=headers, json=body, timeout=30)
            if r.status_code != 200:
                raise Exception(f"{provider} error {r.status_code}")
            return r.json()["choices"][0]["message"]["content"]
    
    def call_with_fallback(self, prompt: str, task: str = "content", max_retries: int = 3) -> str:
        if not self._initialized:
            self.initialize()
        
        fallback_chain = TASK_FALLBACK_CHAINS.get(task, TASK_FALLBACK_CHAINS["content"])
        last_error = None
        
        for provider_name in fallback_chain:
            if provider_name not in self.providers:
                continue
            
            health = self.providers[provider_name]
            
            if not health.can_use():
                continue
            
            for model in health.config["models"]:
                for attempt in range(max_retries):
                    try:
                        api_key = os.getenv(health.config["env_key"], "")
                        response = self._call_provider(provider_name, model, prompt, api_key)
                        health.record_request(True)
                        return response
                    except Exception as e:
                        last_error = e
                        error_msg = str(e).lower()
                        
                        if "429" in error_msg or "rate" in error_msg:
                            health.record_request(False, "Rate limited")
                            break
                        elif "404" in error_msg:
                            health.record_request(False, f"Model not found")
                            continue
                        else:
                            health.record_request(False, str(e))
                            if attempt < max_retries - 1:
                                time.sleep(1 + attempt)
                            continue
                break
        
        raise Exception(f"All providers failed. Last error: {last_error}")
    
    def get_health_status(self) -> Dict:
        return {
            "initialized": self._initialized,
            "providers": {name: {
                "status": health.status.value,
                "total_requests": health.total_requests,
                "successful_requests": health.successful_requests,
            } for name, health in self.providers.items()},
        }


_manager_instance = None

def get_model_manager() -> ModelManagerV2:
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = ModelManagerV2()
    return _manager_instance

def call_with_fallback(prompt: str, task: str = "content", **kwargs) -> str:
    return get_model_manager().call_with_fallback(prompt, task, **kwargs)
