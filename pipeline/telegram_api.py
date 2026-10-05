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


def send_document(chat_id, pdf_path, caption):
    with open(pdf_path, "rb") as f:
        res = call("sendDocument", chat_id=chat_id,
                   document=("document", f, "application/pdf"),
                   caption=caption[:1024])
    return res["message_id"]


def pin_message(chat_id, message_id):
    return call("pinChatMessage", chat_id=chat_id, message_id=message_id)


def verify_pin(chat_id, message_id):
    res = call("getChat", chat_id=chat_id)
    pinned = res.get("pinned_message", {}).get("message_id")
    return pinned == int(message_id), pinned


def alert_admin(text):
    """Watchdog alert to admin DM; safe if token missing (logs only)."""
    chat = os.getenv("ADMIN_ID", "")
    if not chat:
        # Fallback: last admin who messaged the bot (discovered via getUpdates).
        # Lets watchdog alerts work even when ADMIN_ID secret isn't set yet.
        try:
            res = call("getUpdates", timeout=3)
            upd = res.get("result") or []
            for u in reversed(upd[-50:]):
                msg = u.get("message") or u.get("edited_message") or {}
                c = msg.get("from") or {}
                if c.get("id"):
                    chat = str(c["id"])
                    break
        except Exception:
            pass
    if not os.getenv("TELEGRAM_BOT_TOKEN") or not chat:
        logging.warning(f"ALERT (no telegram config): {text}")
        return False
    try:
        call("sendMessage", chat_id=chat, text=text[:4000])
        return True
    except Exception as e:
        logging.error(f"Alert delivery failed: {e}")
        return False
