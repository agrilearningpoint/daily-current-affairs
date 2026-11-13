# -*- coding: utf-8 -*-
"""
Agent 23: Telegram Pin Status Verifier (Section 12)
===================================================
Verifies that a confirmed published `message_id` is pinned in the target channel
and records the verification result in `state/pin_verification.json`.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from pipeline.store import STATE_DIR, atomic_write_json, safe_read_json

PIN_STATE_PATH = STATE_DIR / "pin_verification.json"


def verify_and_pin_message(
    job_id: str,
    message_id: int,
    pin_fn: Callable[[int], bool],
    check_pinned_fn: Optional[Callable[[], Optional[int]]] = None,
    pin_state_path: Optional[Path] = None,
) -> Dict[str, Any]:
    p_path = pin_state_path or PIN_STATE_PATH
    state = safe_read_json(p_path, {"pins": {}})
    now_iso = datetime.now(timezone.utc).isoformat()

    already_pinned = False
    if check_pinned_fn is not None:
        current_pinned = check_pinned_fn()
        if current_pinned == int(message_id):
            already_pinned = True

    if not already_pinned:
        already_pinned = bool(pin_fn(int(message_id)))

    record = {
        "job_id": job_id,
        "message_id": int(message_id),
        "pin_verified": already_pinned,
        "verified_at": now_iso,
    }
    state.setdefault("pins", {})[job_id] = record
    atomic_write_json(p_path, state)
    return record
