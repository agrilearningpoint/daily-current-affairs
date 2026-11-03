#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify every pipeline secret with one tiny real request.

Prints a table:  NAME | OK/WARN/FAIL/MISSING | http code | short reason
Secret values are never printed: every configured secret value found in an
error body is masked before printing. No message is ever sent to Telegram
(getMe / getChat only), and LLM checks ask for a few tokens at most.

Usage:
  python scripts/verify_keys.py            # table on stdout (exit 0)
  python scripts/verify_keys.py --strict   # exit 1 when any configured key FAILs
  python scripts/verify_keys.py --markdown # GitHub step-summary table
  python scripts/verify_keys.py --only GROQ_API_KEY,GNEWS_API_KEY

Status meanings:
  OK       the key works (and a model answered, for LLM providers)
  WARN     the key is valid but limited right now (429) or only partly usable
  FAIL     the key is rejected / has no balance / config is broken
  MISSING  the secret is not set (the pipeline keeps that feature OFF)
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Every secret the workflows pass, in report order.
SECRETS = (
    "GROQ_API_KEY", "GEMINI_API_KEY", "OLLAMA_API_KEY", "LL7_API_KEY", "MISTRAL_API_KEY",
    "OPENROUTER_API_KEY", "COHERE_API_KEY", "HUGGINGFACE_API_KEY", "NVIDIA_API_KEY",
    "OPENAI_API_KEY",
    "NEWSDATA_API_KEY", "GNEWS_API_KEY", "SERPER_API_KEY", "JINA_API_KEY",
    "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "TELEGRAM_CHANNEL_ID", "ADMIN_ID",
)
TIMEOUT = float(os.getenv("VERIFY_KEYS_TIMEOUT", "20"))
# Same per-call ceilings as the router (pipeline/ai_router.py _PROVIDER_TIMEOUTS).
LLM7_TIMEOUT = float(os.getenv("AI_ROUTER_TIMEOUT_LLM7", "45"))
NVIDIA_TIMEOUT = float(os.getenv("AI_ROUTER_TIMEOUT_NVIDIA", "40"))
PROMPT = "Reply with OK."

Result = Tuple[str, Optional[int], str]  # status, http code, reason


def env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def mask(text: Any) -> str:
    """Remove every secret value (and long token-like strings) from text."""
    text = str(text or "")
    for name in set(SECRETS) | {"GOOGLE_API_KEY", "LLM7_API_KEY", "HF_TOKEN"}:
        value = env(name)
        if len(value) >= 4:
            text = text.replace(value, "***")
    return re.sub(r"\b(?:sk|gsk|nvapi|hf|jina|csk)[-_][A-Za-z0-9_\-]{12,}", "***", text)


def short(text: Any, n: int = 90) -> str:
    text = " ".join(mask(text).split())
    return text if len(text) <= n else text[: n - 1] + "…"


def _error_reason(r: requests.Response) -> str:
    try:
        data = r.json()
    except ValueError:
        return short(r.text or r.reason)
    if isinstance(data, dict):
        err = data.get("error") if "error" in data else data.get("message") or data.get("errors") or data
        if isinstance(err, dict):
            err = err.get("message") or err.get("code") or err
        if isinstance(err, list) and err:
            err = err[0].get("message") if isinstance(err[0], dict) else err[0]
        return short(err)
    return short(data)


def classify(r: requests.Response, ok_reason: str = "ok") -> Result:
    code = r.status_code
    if code == 200:
        return "OK", code, ok_reason
    reason = _error_reason(r)
    if code == 429:
        return "WARN", code, f"rate limited (key valid): {reason}"
    if code == 402:
        return "FAIL", code, f"no balance / payment required: {reason}"
    if code in (401, 403):
        return "FAIL", code, f"rejected: {reason}"
    return "FAIL", code, reason


def guarded(fn: Callable[[], Result]) -> Result:
    try:
        return fn()
    except requests.Timeout:
        return "FAIL", None, f"timeout after {TIMEOUT:.0f}s"
    except requests.RequestException as exc:
        return "FAIL", None, f"network error: {type(exc).__name__}"
    except Exception as exc:  # never crash the table
        return "FAIL", None, short(f"{type(exc).__name__}: {exc}")


def preferred(provider: str) -> Tuple[str, ...]:
    try:
        from pipeline.ai_router import _PREFERRED_MODELS
        return tuple(_PREFERRED_MODELS.get(provider, ()))
    except Exception:
        return ()


def chat(url: str, key: str, models: Tuple[str, ...], extra_headers: Optional[dict] = None,
         timeout: float = TIMEOUT) -> Result:
    """Tiny OpenAI-compatible chat; a 404/410 moves to the next model (max 3)."""
    last: Result = ("FAIL", None, "no model to try")
    for model in [m for m in models if m][:3]:
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        headers.update(extra_headers or {})
        r = requests.post(url, headers=headers, timeout=timeout, json={
            "model": model, "max_tokens": 16, "temperature": 0,
            "messages": [{"role": "user", "content": PROMPT}]})
        if r.status_code in (404, 410):
            last = ("FAIL", r.status_code, f"model {model} retired/not found")
            continue
        status, code, reason = classify(r, f"model {model} answered")
        return status, code, reason if status != "FAIL" else f"{model}: {reason}"
    return last


# --------------------------------------------------------------------------- #
# Checks
# --------------------------------------------------------------------------- #
def check_groq() -> Result:
    return chat("https://api.groq.com/openai/v1/chat/completions", env("GROQ_API_KEY"),
                preferred("groq") or ("openai/gpt-oss-20b",))


def guarded_gemini() -> Result:
    # A hung model must not hide the others: a timeout moves on as well.
    key = env("GEMINI_API_KEY")
    base = "https://generativelanguage.googleapis.com/v1beta/models"
    notes = []
    for model in (preferred("gemini") or ("gemini-2.5-flash",))[:4]:
        try:
            r = requests.post(f"{base}/{model}:generateContent", timeout=25,
                              headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                              json={"contents": [{"parts": [{"text": PROMPT}]}],
                                    "generationConfig": {"maxOutputTokens": 16}})
        except requests.Timeout:
            notes.append(f"{model} timeout")
            continue
        if r.status_code in (404, 410):
            notes.append(f"{model} {r.status_code}")
            continue
        status, code, reason = classify(r, f"model {model} answered")
        if notes:
            reason += f" (skipped: {', '.join(notes)})"
        return status, code, reason
    return "FAIL", None, "; ".join(notes) or "no model answered"


def check_ollama() -> Result:
    base = (env("OLLAMA_BASE_URL") or "https://ollama.com").rstrip("/")
    return chat(f"{base}/v1/chat/completions", env("OLLAMA_API_KEY"), preferred("ollama") or ("gpt-oss:20b",))


def check_mistral() -> Result:
    return chat("https://api.mistral.ai/v1/chat/completions", env("MISTRAL_API_KEY"),
                preferred("mistral") or ("mistral-small-latest",))


def check_openrouter() -> Result:
    key = env("OPENROUTER_API_KEY")
    r = requests.get("https://openrouter.ai/api/v1/key", timeout=TIMEOUT,
                     headers={"Authorization": f"Bearer {key}"})
    if r.status_code != 200:
        return classify(r)
    status, code, reason = chat("https://openrouter.ai/api/v1/chat/completions", key,
                                preferred("openrouter") or ("openrouter/free",))
    return status, code, reason


def check_nvidia() -> Result:
    return chat("https://integrate.api.nvidia.com/v1/chat/completions", env("NVIDIA_API_KEY"),
                preferred("nvidia") or ("meta/llama-3.2-90b-vision-instruct",), timeout=NVIDIA_TIMEOUT)


def check_cohere() -> Result:
    return chat("https://api.cohere.ai/compatibility/v1/chat/completions", env("COHERE_API_KEY"),
                preferred("cohere") or ("command-r7b-12-2024",))


def check_llm7() -> Result:
    key = env("LL7_API_KEY") or env("LLM7_API_KEY")
    try:
        return chat("https://api.llm7.io/v1/chat/completions", key, preferred("llm7") or ("default",),
                    timeout=LLM7_TIMEOUT)
    except requests.Timeout:
        return "FAIL", None, f"timeout after {LLM7_TIMEOUT:.0f}s"


def check_huggingface() -> Result:
    # whoami only: the free inference credit is too small to spend on checks.
    r = requests.get("https://huggingface.co/api/whoami-v2", timeout=TIMEOUT,
                     headers={"Authorization": f"Bearer {env('HUGGINGFACE_API_KEY')}"})
    return classify(r, "token valid (whoami)")


def check_openai() -> Result:
    key = env("OPENAI_API_KEY")
    if key.startswith("sk-or-"):
        return "FAIL", None, "holds an OpenRouter key (sk-or-…), not an OpenAI key — router skips it"
    r = requests.get("https://api.openai.com/v1/models", timeout=TIMEOUT,
                     headers={"Authorization": f"Bearer {key}"})
    return classify(r, "key valid (models list)")


def check_newsdata() -> Result:
    r = requests.get("https://newsdata.io/api/1/latest", timeout=TIMEOUT,
                     params={"apikey": env("NEWSDATA_API_KEY"), "country": "in", "language": "en"})
    if r.status_code == 200:
        try:
            n = len(r.json().get("results") or [])
        except ValueError:
            n = 0
        return "OK", 200, f"{n} India articles (1 credit)"
    return classify(r)


def check_gnews() -> Result:
    r = requests.get("https://gnews.io/api/v4/top-headlines", timeout=TIMEOUT,
                     params={"apikey": env("GNEWS_API_KEY"), "country": "in", "lang": "en", "max": 1})
    if r.status_code == 200:
        try:
            total = r.json().get("totalArticles")
        except ValueError:
            total = "?"
        return "OK", 200, f"top-headlines ok (totalArticles={total}; 1 of 100/day)"
    return classify(r)


def check_serper() -> Result:
    r = requests.post("https://google.serper.dev/search", timeout=TIMEOUT,
                      headers={"X-API-KEY": env("SERPER_API_KEY"), "Content-Type": "application/json"},
                      json={"q": "PIB India", "gl": "in", "num": 1})
    if r.status_code == 200:
        try:
            credits = r.json().get("credits")
        except ValueError:
            credits = None
        return "OK", 200, f"search ok ({credits if credits is not None else 1} credit used)"
    return classify(r)


def check_jina() -> Result:
    r = requests.get("https://r.jina.ai/https://example.com", timeout=TIMEOUT,
                     headers={"Authorization": f"Bearer {env('JINA_API_KEY')}", "Accept": "text/plain"})
    status, code, reason = classify(r, "reader ok")
    if status == "FAIL" and code == 402:
        reason += " (pipeline drops the key for the run and uses the keyless reader)"
    return status, code, reason


def _telegram(method: str, **params) -> requests.Response:
    return requests.get(f"https://api.telegram.org/bot{env('TELEGRAM_BOT_TOKEN')}/{method}",
                        params=params, timeout=TIMEOUT)


def check_telegram_bot() -> Result:
    r = _telegram("getMe")
    if r.status_code == 200:
        return "OK", 200, "getMe ok"
    return classify(r)


def check_telegram_chat(name: str) -> Callable[[], Result]:
    def run() -> Result:
        if not env("TELEGRAM_BOT_TOKEN"):
            return "FAIL", None, "TELEGRAM_BOT_TOKEN missing, cannot check"
        r = _telegram("getChat", chat_id=env(name))
        if r.status_code == 200:
            kind = (r.json().get("result") or {}).get("type", "chat")
            note = " (not read by the pipeline; it uses TELEGRAM_CHAT_ID)" if name == "TELEGRAM_CHANNEL_ID" else ""
            return "OK", 200, f"getChat ok ({kind}){note}"
        status, code, reason = classify(r)
        if name == "ADMIN_ID" and code == 400:
            reason += " — the admin must /start the bot once"
        return status, code, reason
    return run


CHECKS: Dict[str, Callable[[], Result]] = {
    "GROQ_API_KEY": check_groq,
    "GEMINI_API_KEY": guarded_gemini,
    "OLLAMA_API_KEY": check_ollama,
    "LL7_API_KEY": check_llm7,
    "MISTRAL_API_KEY": check_mistral,
    "OPENROUTER_API_KEY": check_openrouter,
    "COHERE_API_KEY": check_cohere,
    "HUGGINGFACE_API_KEY": check_huggingface,
    "NVIDIA_API_KEY": check_nvidia,
    "OPENAI_API_KEY": check_openai,
    "NEWSDATA_API_KEY": check_newsdata,
    "GNEWS_API_KEY": check_gnews,
    "SERPER_API_KEY": check_serper,
    "JINA_API_KEY": check_jina,
    "TELEGRAM_BOT_TOKEN": check_telegram_bot,
    "TELEGRAM_CHAT_ID": check_telegram_chat("TELEGRAM_CHAT_ID"),
    "TELEGRAM_CHANNEL_ID": check_telegram_chat("TELEGRAM_CHANNEL_ID"),
    "ADMIN_ID": check_telegram_chat("ADMIN_ID"),
}


def run_checks(names: List[str]) -> List[Dict[str, Any]]:
    rows: Dict[str, Dict[str, Any]] = {}
    todo = []
    for name in names:
        if not env(name):
            rows[name] = {"name": name, "status": "MISSING", "code": None, "reason": "secret not set (feature OFF)"}
        else:
            todo.append(name)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(guarded, CHECKS[name]): name for name in todo}
        for future in concurrent.futures.as_completed(futures):
            name = futures[future]
            status, code, reason = future.result()
            rows[name] = {"name": name, "status": status, "code": code, "reason": short(reason, 110)}
    return [rows[name] for name in names]


def render(rows: List[Dict[str, Any]], markdown: bool = False) -> str:
    lines = []
    if markdown:
        lines += ["| NAME | STATUS | HTTP | REASON |", "|---|---|---|---|"]
        for r in rows:
            lines.append(f"| {r['name']} | {r['status']} | {r['code'] or '-'} | {r['reason'].replace('|', '/')} |")
    else:
        width = max(len(r["name"]) for r in rows)
        lines.append(f"{'NAME'.ljust(width)} | STATUS  | HTTP | REASON")
        lines.append("-" * (width + 40))
        for r in rows:
            lines.append(f"{r['name'].ljust(width)} | {r['status'].ljust(7)} | {str(r['code'] or '-').ljust(4)} | {r['reason']}")
    missing = [r["name"] for r in rows if r["status"] == "MISSING"]
    failed = [r["name"] for r in rows if r["status"] == "FAIL"]
    lines.append("")
    lines.append(f"Missing: {', '.join(missing) or 'none'}")
    lines.append(f"Failing: {', '.join(failed) or 'none'}")
    return mask("\n".join(lines))


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--strict", action="store_true", help="exit 1 when a configured key fails")
    parser.add_argument("--markdown", action="store_true", help="print a Markdown table")
    parser.add_argument("--json", dest="json_path", help="also write the rows as JSON to this path")
    parser.add_argument("--only", help="comma-separated secret names")
    args = parser.parse_args(argv)
    names = [n.strip() for n in (args.only or "").split(",") if n.strip()] or list(SECRETS)
    unknown = [n for n in names if n not in CHECKS]
    if unknown:
        print(f"unknown secret name(s): {', '.join(unknown)}", file=sys.stderr)
        return 2
    rows = run_checks(names)
    print(render(rows, markdown=args.markdown))
    if args.json_path:
        Path(args.json_path).write_text(json.dumps(rows, indent=2), encoding="utf-8")
    if args.strict and any(r["status"] == "FAIL" for r in rows):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
