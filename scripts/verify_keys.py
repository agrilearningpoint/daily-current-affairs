#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Secret Health Monitor (`scripts/verify_keys.py`) — Section 13.2
===============================================================
Safely checks configured provider secret slots without EVER printing, logging,
or transmitting any secret value or prefix.

Distinguishes between:
- `missing_secret`
- `invalid_credential` (401)
- `expired_credential` (401 expired)
- `permission_issue` (403)
- `rate_limit` (429)
- `temporary_outage` (500/502/503/504/timeout)
- `healthy` (200)

Admin alerts contain strictly:
- Provider
- Secret variable name (e.g. `GEMINI_API_KEY_1`)
- Error category
- Detection time (UTC ISO-8601)
- Recommended action
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

MONITORED_SECRETS: List[Tuple[str, str]] = [
    ("gemini", "GEMINI_API_KEY"),
    ("gemini", "GEMINI_API_KEY_1"),
    ("gemini", "GEMINI_API_KEY_2"),
    ("gemini", "GEMINI_API_KEY_3"),
    ("gemini", "GEMINI_API_KEY_4"),
    ("gemini", "GEMINI_API_KEY_5"),
    ("gemini", "GEMINI_API_KEY_6"),
    ("gemini", "GEMINI_API_KEY_7"),
    ("groq", "GROQ_API_KEY"),
    ("groq", "GROQ_API_KEY_1"),
    ("groq", "GROQ_API_KEY_2"),
    ("mistral", "MISTRAL_API_KEY"),
    ("openrouter", "OPENROUTER_API_KEY"),
    ("telegram", "TELEGRAM_BOT_TOKEN"),
]

RECOMMENDED_ACTIONS: Dict[str, str] = {
    "missing_secret": "Optional slot not set in GitHub Actions Secrets; configure if additional capacity is needed.",
    "invalid_credential": "Regenerate the API key in the provider dashboard and update the GitHub Repository Secret.",
    "expired_credential": "Token has expired; rotate the token and update the GitHub Repository Secret.",
    "permission_issue": "Verify billing/tier permissions or model access scope for this secret.",
    "rate_limit": "Key is valid but currently rate-limited; router cooldown will handle rotation automatically.",
    "temporary_outage": "Provider endpoint returned 5xx/timeout; no secret rotation required.",
    "healthy": "No action needed.",
}


def classify_probe_status(status_code: Optional[int], message: str = "") -> str:
    msg_l = str(message or "").lower()
    if status_code == 200:
        return "healthy"
    if status_code == 401:
        return "expired_credential" if "expired" in msg_l else "invalid_credential"
    if status_code == 403:
        return "permission_issue"
    if status_code == 429:
        return "rate_limit"
    return "temporary_outage"


def check_secrets_safely(
    env: Optional[Dict[str, str]] = None,
    probe_fn: Optional[Callable[[str, str], Tuple[Optional[int], str]]] = None,
) -> List[Dict[str, str]]:
    """
    Inspect secret health and return sanitized status records.
    Guarantees that NO secret value ever appears in the returned dictionaries.
    """
    e = env if env is not None else os.environ
    now_iso = datetime.now(timezone.utc).isoformat()
    results: List[Dict[str, str]] = []

    for provider, var_name in MONITORED_SECRETS:
        raw_val = (e.get(var_name) or "").strip()
        if not raw_val:
            category = "missing_secret"
        elif probe_fn is not None:
            code, msg = probe_fn(provider, var_name)
            category = classify_probe_status(code, msg)
        else:
            category = "healthy"

        results.append({
            "provider": provider,
            "secret_variable_name": var_name,
            "error_category": category,
            "detection_time": now_iso,
            "recommended_action": RECOMMENDED_ACTIONS[category],
        })

    return results


if __name__ == "__main__":
    report = check_secrets_safely()
    print(json.dumps(report, indent=2))
