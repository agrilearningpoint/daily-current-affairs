# -*- coding: utf-8 -*-
"""
TELEGRAM PUBLISHER + PIN VERIFIER LIBRARY (Agents 22, 23) + Watchdog alerts.
SECURITY: token is read ONLY from env TELEGRAM_BOT_TOKEN — no hardcoded fallback.
Flow: sendDocument → store message_id → pinChatMessage → getChat → verify
pinned_message.message_id == sent id. Pin failure = job NOT complete.
"""
import json, logging, os

import requests

API = "https://api.telegram.org/bot"


def _token():
    t = os.getenv("TELEGRAM_BOT_TOKEN")
    if not t:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing (set it in GitHub Secrets; never hardcode)")
    return t


def call(method, **params):
    r = requests.post(f"{API}{_token()}/{method}", data=params, timeout=30)
    try:
        data = r.json()
    except ValueError:
        raise RuntimeError(f"Telegram {method}: bad response {r.status_code}")
    if not data.get("ok"):
        raise RuntimeError(f"Telegram {method} failed: {data.get('description')}")
    return data["result"]


def _already_published(job_id):
    """Idempotency guard — check persistent published_events.json before upload.
    Prevents duplicate Telegram uploads if runner crashes after send but before state push."""
    try:
        import json as _json, pathlib as _pl
        pf = _pl.Path("state/published_events.json")
        if pf.exists():
            data = _json.loads(pf.read_text(encoding="utf-8"))
            return job_id in data or job_id in str(data)
    except Exception:
        pass
    return False

def send_document(chat_id, pdf_path, caption, job_id=None):
    # P0 #11: atomic idempotency — check before upload
    if job_id and _already_published(job_id):
        raise RuntimeError(f"Telegram idempotency: {job_id} already published (state/published_events.json) — skipping duplicate upload")
    files = {"document": (os.path.basename(pdf_path), open(pdf_path, "rb"), "application/pdf")}
    r = requests.post(f"{API}{_token()}/sendDocument",
                      data={"chat_id": chat_id, "caption": caption[:1024]},
                      files=files, timeout=120)
    try:
        data = r.json()
    except ValueError:
        raise RuntimeError(f"Telegram sendDocument: bad response {r.status_code}")
    if not data.get("ok"):
        raise RuntimeError(f"Telegram sendDocument failed: {data.get('description')}")
    return data["result"]["message_id"]


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
