# -*- coding: utf-8 -*-
"""
TELEGRAM PUBLISHER + PIN VERIFIER LIBRARY (Agents 22, 23) + Watchdog alerts.
SECURITY: token is read ONLY from env TELEGRAM_BOT_TOKEN — no hardcoded fallback.
Flow: sendDocument → store message_id → pinChatMessage → getChat → verify
pinned_message.message_id == sent id. Pin failure = job NOT complete.

NOTE (production audit): the daily/weekly/monthly stage list does NOT import this
module — `agents/22_telegram_publisher.py` and `agents/23_telegram_pin_verifier.py`
carry their own hardened implementations. This module is kept as a standalone
watchdog/alert helper and is maintained to the same ledger + error contracts so a
future caller cannot inherit the old `is_job_published` / file-handle defects.
"""
import logging
import os

import requests

API = "https://api.telegram.org/bot"

# Bounded timeouts so a hung Telegram connection cannot wedge a scheduled run.
API_TIMEOUT = 30
UPLOAD_TIMEOUT = 120


class TelegramError(RuntimeError):
    """Base error for Telegram API failures."""


class TelegramRetryable(TelegramError):
    """Transient failure (429 / 5xx / network) — safe to retry with backoff."""

    def __init__(self, message, retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after


class TelegramPermanent(TelegramError):
    """Permanent failure (auth/config/400) — retrying cannot help."""


def _token():
    t = os.getenv("TELEGRAM_BOT_TOKEN")
    if not t:
        raise TelegramPermanent("TELEGRAM_BOT_TOKEN is missing (set it in GitHub Secrets; never hardcode)")
    return t


def _raise_for_response(method, r):
    """Translate a Telegram HTTP response into a classified exception."""
    if r.status_code == 429:
        retry_after = r.headers.get("Retry-After", "5")
        try:
            retry_after = r.json().get("parameters", {}).get("retry_after", retry_after)
        except ValueError:
            pass
        raise TelegramRetryable(f"Telegram {method}: rate limited", retry_after=int(retry_after))
    try:
        data = r.json()
    except ValueError:
        if r.status_code >= 500:
            raise TelegramRetryable(f"Telegram {method}: ambiguous {r.status_code}")
        raise TelegramPermanent(f"Telegram {method}: bad response {r.status_code}")
    if data.get("ok"):
        return data["result"]
    description = data.get("description", "unknown error")
    if 400 <= r.status_code < 500:
        raise TelegramPermanent(f"Telegram {method} failed: {description}")
    raise TelegramRetryable(f"Telegram {method} failed: {description}")


def call(method, **params):
    r = requests.post(f"{API}{_token()}/{method}", data=params, timeout=API_TIMEOUT)
    return _raise_for_response(method, r)


def _already_published(job_id):
    """Idempotency guard — is there a live success receipt for this job_id?

    Uses the canonical published-events ledger via pipeline.store. Unreadable
    ledgers fail CLOSED (treated as "already published") so an idempotency
    check can never cause an uncontrolled duplicate upload.
    """
    try:
        from pipeline import store as _store
        return _store.is_job_published(job_id)
    except Exception as exc:  # unreadable ledger / bad on-disk state
        logging.error("Published-ledger check failed for %s (%s); treating as published", job_id, exc)
        return True


def send_document(chat_id, pdf_path, caption, job_id=None):
    # Idempotency: never re-upload an edition that already has a live receipt.
    if job_id and _already_published(job_id):
        raise TelegramPermanent(
            f"Telegram idempotency: {job_id} already published — skipping duplicate upload")
    # Context-managed handle: the file is closed even when the request raises.
    with open(pdf_path, "rb") as handle:
        files = {"document": (os.path.basename(pdf_path), handle, "application/pdf")}
        r = requests.post(f"{API}{_token()}/sendDocument",
                          data={"chat_id": chat_id, "caption": caption[:1024]},
                          files=files, timeout=UPLOAD_TIMEOUT)
    return _raise_for_response("sendDocument", r)["message_id"]


def pin_message(chat_id, message_id):
    return call("pinChatMessage", chat_id=chat_id, message_id=message_id)


def verify_pin(chat_id, message_id):
    res = call("getChat", chat_id=chat_id)
    pinned = res.get("pinned_message", {}).get("message_id")
    return pinned == int(message_id), pinned


def alert_admin(text):
    """Watchdog alert to admin DM — ADMIN_ID is required (production safety).
    Auto-discovery via getUpdates is disabled (unsafe/ambiguous in production).
    If ADMIN_ID or token missing, log warning and mark workflow as CONFIG ERROR."""
    chat = os.getenv("ADMIN_ID", "")
    if not chat:
        logging.error(f"ALERT CONFIG ERROR — ADMIN_ID missing (set GitHub Secret ADMIN_ID): {text}")
        # Do not attempt getUpdates fallback — production requires explicit ADMIN_ID
        return False
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        logging.error(f"ALERT CONFIG ERROR — TELEGRAM_BOT_TOKEN missing: {text}")
        return False
    try:
        call("sendMessage", chat_id=chat, text=text[:4000])
        return True
    except Exception as e:
        logging.error(f"Alert delivery failed: {e}")
        return False
