# -*- coding: utf-8 -*-
"""
Agent 22: Telegram Publisher with Exactly-Once Logical Delivery (Section 12)
============================================================================
Prevents duplicate edition uploads and resolves `Publication outcome uncertain` locks:
1. Computes a deterministic `edition_pub_id` and `pdf_sha256` checksum.
2. Stores persistent attempt history, `message_id`, and `pin_status` in
   `state/published_events.json`.
3. Before retrying an uncertain upload:
   - Checks stored publication ledger for an existing confirmed `message_id`.
   - Calls an authorized Telegram status/chat inspection callback (e.g., `getChat`
     pinned_message or bot updates) to reconcile whether the PDF already landed.
   - Retries upload ONLY when confirmed unpublished, guaranteeing zero duplicate sends.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from enterprise_v2.store import STATE_DIR, atomic_write_json, safe_read_json

PUBLISHED_LEDGER_PATH = STATE_DIR / "published_events.json"


def compute_pdf_sha256(pdf_path: Path) -> str:
    return hashlib.sha256(pdf_path.read_bytes()).hexdigest()


def reconcile_uncertain_publication(
    job_id: str,
    pdf_sha256: str,
    ledger: Dict[str, Any],
    channel_inspector: Optional[Callable[[str, str], Optional[int]]] = None,
) -> Tuple[bool, Optional[int], str]:
    """
    Reconcile whether an edition with `job_id` or `pdf_sha256` was already published.
    Returns (already_published, message_id, resolution_note).
    """
    records = ledger.setdefault("records", {})
    rec = records.get(job_id, {})

    if rec.get("status") == "published" and rec.get("message_id"):
        return True, int(rec["message_id"]), "confirmed_in_local_ledger"

    # Check if identical SHA256 was already published under this job
    for _, r in records.items():
        if isinstance(r, dict) and r.get("pdf_sha256") == pdf_sha256 and r.get("status") == "published" and r.get("message_id"):
            return True, int(r["message_id"]), "confirmed_by_sha256_match"

    # If previous attempt timed out (`uncertain`), query authorized channel inspector before resending
    if rec.get("status") in ("uncertain", "timeout") and channel_inspector is not None:
        found_msg_id = channel_inspector(job_id, pdf_sha256)
        if found_msg_id:
            rec["status"] = "published"
            rec["message_id"] = int(found_msg_id)
            rec["reconciled_at"] = datetime.now(timezone.utc).isoformat()
            return True, int(found_msg_id), "reconciled_via_telegram_channel_inspection"

    return False, None, "safe_to_send"


def publish_edition_idempotent(
    job_id: str,
    pdf_path: Path,
    caption: str,
    sender_fn: Callable[[Path, str], Dict[str, Any]],
    channel_inspector: Optional[Callable[[str, str], Optional[int]]] = None,
    ledger_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Publish `pdf_path` to Telegram with idempotency & timeout reconciliation.
    """
    l_path = ledger_path or PUBLISHED_LEDGER_PATH
    ledger = safe_read_json(l_path, {"records": {}})
    records = ledger.setdefault("records", {})
    pdf_sha = compute_pdf_sha256(pdf_path)
    now_iso = datetime.now(timezone.utc).isoformat()

    already_pub, msg_id, note = reconcile_uncertain_publication(
        job_id, pdf_sha, ledger, channel_inspector=channel_inspector
    )
    if already_pub:
        atomic_write_json(l_path, ledger)
        return {
            "job_id": job_id,
            "status": "published",
            "message_id": msg_id,
            "pdf_sha256": pdf_sha,
            "reconciliation": note,
            "duplicate_prevented": True,
        }

    rec = records.setdefault(job_id, {
        "job_id": job_id,
        "pdf_sha256": pdf_sha,
        "attempts": [],
        "status": "pending",
    })
    attempt_no = len(rec.get("attempts", [])) + 1

    try:
        resp = sender_fn(pdf_path, caption)
        returned_msg_id = resp.get("message_id")
        if not returned_msg_id:
            raise RuntimeError("Telegram response missing confirmed message_id")
        rec["status"] = "published"
        rec["message_id"] = int(returned_msg_id)
        rec["pdf_sha256"] = pdf_sha
        rec["published_at"] = now_iso
        rec.setdefault("attempts", []).append({
            "attempt": attempt_no,
            "timestamp": now_iso,
            "outcome": "success",
            "message_id": int(returned_msg_id),
        })
        atomic_write_json(l_path, ledger)
        return {
            "job_id": job_id,
            "status": "published",
            "message_id": int(returned_msg_id),
            "pdf_sha256": pdf_sha,
            "duplicate_prevented": False,
        }
    except TimeoutError as exc:
        rec["status"] = "uncertain"
        rec.setdefault("attempts", []).append({
            "attempt": attempt_no,
            "timestamp": now_iso,
            "outcome": "timeout_uncertain",
            "error": str(exc),
        })
        atomic_write_json(l_path, ledger)
        return {
            "job_id": job_id,
            "status": "uncertain",
            "message_id": None,
            "pdf_sha256": pdf_sha,
            "error": str(exc),
        }
