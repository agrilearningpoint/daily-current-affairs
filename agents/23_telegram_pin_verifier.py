# -*- coding: utf-8 -*-
"""
Telegram Pin Verifier Agent (23)
================================
Publish ke baad verify karta hai ki message actually pinned hai.

Production features:
- Verify pin state via getChat (pinned_message)
- Graceful handling of "already pinned" (400 error)
- Retry pin with exponential backoff
- Old pin unpin (optional, controlled via env)
- Persistent verification ledger (idempotent)
- Handles missing admin credentials (clear error)
- Handles ambiguous API responses (timeout → verify, don't retry blindly)
- Structured logging + run summary
- Atomic ledger writes

Env:
  TELEGRAM_BOT_TOKEN          (required)
  TELEGRAM_CHAT_ID            (required)
  TELEGRAM_UNPIN_OLD          (0|1, default 0) — unpin old before new
  TELEGRAM_PIN_NOTIFY         (0|1, default 1) — send notify to chat
  TELEGRAM_PIN_VERIFY_RETRIES (default 3)
  DRY_RUN                     (0|1)
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
REPO_ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = REPO_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(LOGS_DIR / "pin_verifier.log"), encoding="utf-8"),
    ],
)
logger = logging.getLogger("agent.23_telegram_pin_verifier")

# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
TELEGRAM_API_BASE = "https://api.telegram.org"
PUBLISHED_LEDGER = REPO_ROOT / "state" / "published_events.json"
PIN_LEDGER = REPO_ROOT / "state" / "pin_verification.json"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
UNPIN_OLD = os.getenv("TELEGRAM_UNPIN_OLD", "0") == "1"
PIN_NOTIFY = os.getenv("TELEGRAM_PIN_NOTIFY", "1") == "1"
PIN_VERIFY_RETRIES = int(os.getenv("TELEGRAM_PIN_VERIFY_RETRIES", "3"))
DRY_RUN = os.getenv("DRY_RUN", "0") == "1"


# --------------------------------------------------------------------------- #
# Exceptions
# --------------------------------------------------------------------------- #
class PinVerifyError(Exception):
    """Recoverable error — retry."""
    pass


class PinVerifyPermanent(Exception):
    """Non-retryable — permissions, invalid chat, etc."""
    pass


# --------------------------------------------------------------------------- #
# Ledger I/O
# --------------------------------------------------------------------------- #
def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def atomic_write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    with open(tmp, "rb") as f:
        os.fsync(f.fileno())
    os.replace(tmp, path)


# --------------------------------------------------------------------------- #
# Telegram API
# --------------------------------------------------------------------------- #
def _api_url(method: str) -> str:
    return f"{TELEGRAM_API_BASE}/bot{TELEGRAM_BOT_TOKEN}/{method}"


def _call_api(method: str, payload: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
    """POST to Telegram API. Raises typed exceptions."""
    if not TELEGRAM_BOT_TOKEN:
        raise PinVerifyPermanent("TELEGRAM_BOT_TOKEN not configured")

    try:
        r = requests.post(_api_url(method), json=payload, timeout=timeout)
    except requests.RequestException as exc:
        raise PinVerifyError(f"Network error calling {method}: {exc}")

    if r.status_code == 429:
        retry_after = int(r.headers.get("Retry-After", "5"))
        raise PinVerifyError(f"Rate limited ({retry_after}s)")

    try:
        data = r.json()
    except ValueError:
        raise PinVerifyError(f"{method}: non-JSON response ({r.status_code})")

    if not data.get("ok"):
        desc = (data.get("description") or "").lower()
        code = data.get("error_code", r.status_code)

        # Known non-retryable conditions
        permanent_markers = (
            "not enough rights", "chat_admin_required", "not an administrator",
            "chat not found", "bot was kicked", "user is not a member",
            "message to pin not found", "message can't be pinned",
        )
        if any(m in desc for m in permanent_markers):
            raise PinVerifyPermanent(f"{method}: {data.get('description')}")

        # "message is already pinned" — not really an error
        if "already pinned" in desc:
            return {"ok": True, "result": True, "already_pinned": True}

        raise PinVerifyError(f"{method}: {data.get('description')} (code {code})")

    return data


# --------------------------------------------------------------------------- #
# Pin Operations
# --------------------------------------------------------------------------- #
def get_chat_state() -> Dict[str, Any]:
    """Get chat info including pinned_message if any."""
    r = _call_api("getChat", {"chat_id": TELEGRAM_CHAT_ID})
    return r.get("result", {})


def get_pinned_message_id() -> Optional[int]:
    """Return current pinned message_id or None."""
    try:
        chat = get_chat_state()
        pinned = chat.get("pinned_message")
        if isinstance(pinned, dict):
            return pinned.get("message_id")
        return None
    except PinVerifyPermanent:
        raise
    except Exception as exc:
        logger.warning("Could not fetch chat state: %s", exc)
        return None


def pin_message(message_id: int, disable_notification: bool = True) -> Dict[str, Any]:
    """Pin a message. Returns API result."""
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "message_id": message_id,
        "disable_notification": disable_notification,
    }
    return _call_api("pinChatMessage", payload)


def unpin_message(message_id: Optional[int] = None) -> Dict[str, Any]:
    """Unpin specific message or all."""
    payload: Dict[str, Any] = {"chat_id": TELEGRAM_CHAT_ID}
    if message_id is not None:
        payload["message_id"] = message_id
    return _call_api("unpinChatMessage", payload)


# --------------------------------------------------------------------------- #
# Verification Logic
# --------------------------------------------------------------------------- #
def verify_pin_with_retry(
    message_id: int,
    max_attempts: int = PIN_VERIFY_RETRIES,
) -> bool:
    """
    After pinning, verify via getChat. Retry on transient failures.
    Returns True if message is pinned.
    """
    for attempt in range(1, max_attempts + 1):
        try:
            current = get_pinned_message_id()
            if current == message_id:
                return True
            logger.warning(
                "Pin verify attempt %d/%d: expected=%s got=%s",
                attempt, max_attempts, message_id, current,
            )
        except PinVerifyError as exc:
            logger.warning("Pin verify attempt %d/%d failed: %s",
                           attempt, max_attempts, exc)
        except PinVerifyPermanent as exc:
            logger.error("Pin verify permanent error: %s", exc)
            return False

        if attempt < max_attempts:
            wait = 2 ** attempt
            time.sleep(wait)

    return False


def notify_channel(text: str) -> None:
    """Send a small notification message to the channel."""
    if DRY_RUN or not PIN_NOTIFY:
        return
    try:
        _call_api("sendMessage", {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "disable_notification": True,
            "disable_web_page_preview": True,
        })
    except Exception as exc:
        logger.warning("Could not send notification: %s", exc)


# --------------------------------------------------------------------------- #
# Pipeline
# --------------------------------------------------------------------------- #
def get_latest_unpinned_from_ledger() -> Optional[Dict[str, Any]]:
    """
    Read published_events.json, find most recent successful record
    that isn't already pin-verified.
    """
    pub = load_json(PUBLISHED_LEDGER, {"records": {}})
    records = pub.get("records", {})
    if not records:
        return None

    pin_ledger = load_json(PIN_LEDGER, {"records": {}})

    # Sort records by published_at desc
    sorted_recs = sorted(
        records.values(),
        key=lambda r: r.get("published_at", ""),
        reverse=True,
    )

    for rec in sorted_recs:
        if os.getenv("ALP_JOB_ID") and rec.get("job_id") != os.getenv("ALP_JOB_ID"):
            continue
        if rec.get("status") != "success":
            continue
        msg_id = rec.get("message_id")
        if not msg_id:
            continue

        # Unique key: chat_id + message_id
        pin_key = hashlib.sha256(
            f"{rec.get('chat_id')}|{msg_id}".encode("utf-8")
        ).hexdigest()[:24]
        if pin_ledger.get("records", {}).get(pin_key, {}).get("status") == "verified":
            continue

        rec = dict(rec)
        rec["_pin_key"] = pin_key
        return rec
    return None


def process_verification(record: Dict[str, Any]) -> bool:
    """Verify + pin one record. Returns True on success."""
    msg_id = record.get("message_id")
    chat_id = record.get("chat_id")
    job_id = record.get("job_id", "unknown")
    pin_key = record.get("_pin_key") or hashlib.sha256(
        f"{chat_id}|{msg_id}".encode("utf-8")
    ).hexdigest()[:24]

    if not msg_id or not chat_id:
        logger.warning("Record missing message_id/chat_id — skipping")
        return False

    pin_ledger = load_json(PIN_LEDGER, {"version": 1, "records": {}})
    pin_ledger.setdefault("records", {})

    # Already verified?
    existing = pin_ledger["records"].get(pin_key, {})
    if existing.get("status") == "verified":
        logger.info("Already verified: job=%s msg_id=%s", job_id, msg_id)
        return True

    if DRY_RUN:
        logger.info("[DRY-RUN] Would verify + pin msg_id=%s (job=%s)", msg_id, job_id)
        return True

    # ---- Step 1: Check current pin ----
    try:
        current_pinned = get_pinned_message_id()
    except PinVerifyPermanent as exc:
        logger.error("Permanent error fetching chat state: %s", exc)
        _record_failure(pin_ledger, pin_key, record, str(exc))
        return False
    except PinVerifyError as exc:
        logger.warning("Transient error fetching chat state: %s", exc)
        current_pinned = None

    # ---- Step 2: Already pinned? ----
    if current_pinned == msg_id:
        logger.info("Message %s is already the pinned message — verified.", msg_id)
        _record_success(pin_ledger, pin_key, record, current_pinned)
        return True

    # ---- Step 3: Optional — unpin old ----
    if UNPIN_OLD and current_pinned and current_pinned != msg_id:
        try:
            logger.info("Unpinning old message %s", current_pinned)
            unpin_message(current_pinned)
        except Exception as exc:
            logger.warning("Failed to unpin old message %s: %s", current_pinned, exc)

    # ---- Step 4: Pin new message ----
    try:
        result = pin_message(msg_id, disable_notification=True)
        if result.get("already_pinned"):
            logger.info("Already pinned (per API): %s", msg_id)
        else:
            logger.info("✔ Pinned message_id=%s (job=%s)", msg_id, job_id)
    except PinVerifyPermanent as exc:
        logger.error("Permanent pin failure for %s: %s", msg_id, exc)
        _record_failure(pin_ledger, pin_key, record, str(exc))
        return False
    except PinVerifyError as exc:
        logger.warning("Transient pin error for %s: %s — will verify anyway", msg_id, exc)

    # ---- Step 5: Verify ----
    ok = verify_pin_with_retry(msg_id)

    if ok:
        _record_success(pin_ledger, pin_key, record, msg_id)
        notify_channel(f"📌 Latest edition pinned (job: {job_id})")
        return True
    else:
        _record_failure(pin_ledger, pin_key, record, "pin verification failed after retries")
        return False


def _record_success(ledger: Dict[str, Any], key: str,
                    record: Dict[str, Any], pinned_id: int) -> None:
    ledger["records"][key] = {
        "job_id": record.get("job_id"),
        "chat_id": record.get("chat_id"),
        "message_id": record.get("message_id"),
        "pinned_message_id": pinned_id,
        "status": "verified",
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }
    atomic_write(PIN_LEDGER, ledger)


def _record_failure(ledger: Dict[str, Any], key: str,
                    record: Dict[str, Any], error: str) -> None:
    ledger["records"][key] = {
        "job_id": record.get("job_id"),
        "chat_id": record.get("chat_id"),
        "message_id": record.get("message_id"),
        "status": "failed",
        "error": error[:500],
        "failed_at": datetime.now(timezone.utc).isoformat(),
    }
    atomic_write(PIN_LEDGER, ledger)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> int:
    if not DRY_RUN:
        if not TELEGRAM_BOT_TOKEN:
            logger.error("TELEGRAM_BOT_TOKEN not set")
            return 1
        if not TELEGRAM_CHAT_ID:
            logger.error("TELEGRAM_CHAT_ID not set")
            return 1

    record = get_latest_unpinned_from_ledger()
    if record is None:
        logger.info("No pending pin verification — nothing to do.")
        return 0

    logger.info(
        "Verifying pin | job=%s msg_id=%s chat=%s",
        record.get("job_id"), record.get("message_id"), record.get("chat_id"),
    )

    try:
        ok = process_verification(record)
    except Exception as exc:
        logger.exception("Unexpected error in pin verification: %s", exc)
        return 1

    if ok:
        logger.info("✔ Pin verification complete.")
        return 0
    logger.error("✘ Pin verification failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
