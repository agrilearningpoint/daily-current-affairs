"""
Telegram Publisher Module
-------------------------
Yeh module edited/verified articles ko Telegram channel par publish karta hai.

Production features:
- Idempotent publishing (persistent ledger — same article dobara nahi jayega)
- Automatic message splitting (4096 char Telegram limit)
- Safe HTML escaping (parse errors prevent)
- Rate-limit aware retry (429 → Retry-After header respect)
- Retry with exponential backoff
- Dry-run mode (test without posting)
- Pydantic validation
- Structured logging
"""

import os
import re
import sys
import json
import time
import html
import hashlib
import logging
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import requests
from pydantic import BaseModel, Field, ValidationError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError,
)

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/telegram_publish.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------
TELEGRAM_API_BASE = "https://api.telegram.org"
TELEGRAM_MAX_MESSAGE_LEN = 4096
TELEGRAM_SAFE_CHUNK_LEN = 3800  # buffer for HTML tags & formatting
TELEGRAM_RATE_LIMIT_SLEEP = 1.2  # seconds between messages (safe under 20/min limit)

INPUT_DIR = "data/edited"
WEEKLY_DIR = "data/weekly"
LEDGER_FILE = "state/published_articles.json"
MAX_PER_RUN = int(os.getenv("MAX_PER_RUN", "20"))  # cap posts per run

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_PARSE_MODE = os.getenv("TELEGRAM_PARSE_MODE", "HTML")  # "HTML" | "MarkdownV2" | ""

DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"


# ------------------------------------------------------------------
# Custom Exceptions
# ------------------------------------------------------------------
class TelegramRateLimitError(Exception):
    """Raised on 429; carries retry_after seconds."""
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Rate limited. Retry after {retry_after}s.")


class TelegramAPIError(Exception):
    """Raised on non-retryable Telegram API error."""
    pass


# ------------------------------------------------------------------
# Pydantic Models
# ------------------------------------------------------------------
class PublishedRecord(BaseModel):
    article_id: str
    chat_id: str
    message_id: Optional[int] = None
    published_at: str
    status: str  # "success" | "failed"
    title: str = ""
    error: Optional[str] = None


class PublishedLedger(BaseModel):
    version: int = 1
    records: Dict[str, PublishedRecord] = Field(default_factory=dict)


# ------------------------------------------------------------------
# Ledger (Idempotency)
# ------------------------------------------------------------------
def load_ledger(path: str = LEDGER_FILE) -> PublishedLedger:
    if not os.path.exists(path):
        return PublishedLedger()
    try:
        with open(path, "r", encoding="utf-8") as f:
            return PublishedLedger(**json.load(f))
    except Exception as exc:
        backup = f"{path}.corrupt.{int(time.time())}"
        logger.error("Corrupt ledger; backing up to %s. Error: %s", backup, exc)
        try:
            os.rename(path, backup)
        except OSError:
            pass
        return PublishedLedger()


def save_ledger(ledger: PublishedLedger, path: str = LEDGER_FILE) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(ledger.model_dump(mode="json"), f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def make_ledger_key(article_id: str, chat_id: str) -> str:
    return f"{chat_id}:{article_id}"


def is_already_published(ledger: PublishedLedger, article_id: str, chat_id: str) -> bool:
    key = make_ledger_key(article_id, chat_id)
    rec = ledger.records.get(key)
    return bool(rec and rec.status == "success")


# ------------------------------------------------------------------
# Formatting
# ------------------------------------------------------------------
def escape_html(text: str) -> str:
    """Escape user content for Telegram HTML parse mode."""
    if not text:
        return ""
    # Escape only the 3 chars Telegram cares about
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_message(article: Dict[str, Any]) -> str:
    """
    Build a well-formatted HTML message for Telegram.
    Respects 4096 char limit (caller will chunk if needed).
    """
    title = escape_html(article.get("title", "Untitled").strip())
    summary = escape_html(article.get("summary", "").strip())
    link = article.get("link", "").strip()
    source = escape_html(article.get("source_feed", "").strip())

    parts: List[str] = [f"<b>{title}</b>", ""]

    if summary:
        parts.append(summary)
        parts.append("")

    if source:
        # Trim long feed URLs for readability
        display_source = source if len(source) <= 60 else source[:57] + "..."
        parts.append(f"<i>Source: {display_source}</i>")

    if link and link.startswith(("http://", "https://")):
        safe_link = html.escape(link, quote=True)
        parts.append(f'🔗 <a href="{safe_link}">Read more</a>')

    return "\n".join(parts)


def chunk_message(text: str, max_len: int = TELEGRAM_SAFE_CHUNK_LEN) -> List[str]:
    """
    Split message into chunks that respect Telegram's 4096 limit.
    Splits at newline/space boundaries; preserves HTML-valid chunks.
    """
    if len(text) <= max_len:
        return [text]

    chunks: List[str] = []
    remaining = text
    while len(remaining) > max_len:
        # Find last newline before max_len
        split_at = remaining.rfind("\n", 0, max_len)
        if split_at == -1:
            split_at = remaining.rfind(" ", 0, max_len)
        if split_at == -1:
            split_at = max_len
        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].lstrip()
    if remaining:
        chunks.append(remaining)
    return chunks


# ------------------------------------------------------------------
# Telegram API Client
# ------------------------------------------------------------------
def _api_url(method: str) -> str:
    return f"{TELEGRAM_API_BASE}/bot{TELEGRAM_BOT_TOKEN}/{method}"


def _handle_response(response: requests.Response, context: str) -> Dict[str, Any]:
    if response.status_code == 429:
        retry_after = int(response.headers.get("Retry-After", "5"))
        # Try to parse JSON for parameters.retry_after
        try:
            data = response.json()
            retry_after = int(data.get("parameters", {}).get("retry_after", retry_after))
        except Exception:
            pass
        raise TelegramRateLimitError(retry_after)

    try:
        data = response.json()
    except ValueError:
        raise TelegramAPIError(f"{context}: non-JSON response ({response.status_code})")

    if not data.get("ok"):
        desc = data.get("description", "unknown error")
        # 400-level errors are typically non-retryable (bad format, blocked, etc.)
        if 400 <= response.status_code < 500:
            raise TelegramAPIError(f"{context}: {desc} (status={response.status_code})")
        raise requests.RequestException(f"{context}: {desc}")

    return data["result"]


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=60),
    retry=retry_if_exception_type((requests.RequestException, TelegramRateLimitError)),
    reraise=True,
)
def send_message(
    chat_id: str,
    text: str,
    parse_mode: str = TELEGRAM_PARSE_MODE,
    disable_web_page_preview: bool = False,
) -> Dict[str, Any]:
    """Send a single text message with retry. Raises on final failure."""
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not configured")

    payload: Dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": disable_web_page_preview,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode

    try:
        response = requests.post(_api_url("sendMessage"), json=payload, timeout=30)
        return _handle_response(response, "sendMessage")
    except TelegramRateLimitError as exc:
        logger.warning("Rate limited. Sleeping %ds before retry.", exc.retry_after)
        time.sleep(exc.retry_after)
        raise  # let tenacity retry


# ------------------------------------------------------------------
# Publishing Logic
# ------------------------------------------------------------------
def publish_article(
    article: Dict[str, Any],
    chat_id: str,
    ledger: PublishedLedger,
) -> Tuple[bool, Optional[str]]:
    """
    Publish one article. Returns (success, error_message).
    Updates ledger in place.
    """
    article_id = article.get("article_id") or _fallback_article_id(article)
    key = make_ledger_key(article_id, chat_id)

    if is_already_published(ledger, article_id, chat_id):
        logger.info("Article %s already published. Skipping.", article_id)
        return True, None

    message = build_message(article)
    chunks = chunk_message(message)

    if DRY_RUN:
        logger.info("[DRY-RUN] Would publish %s in %d chunk(s):\n%s",
                    article_id, len(chunks), chunks[0][:200])
        ledger.records[key] = PublishedRecord(
            article_id=article_id, chat_id=chat_id,
            published_at=datetime.now(timezone.utc).isoformat(),
            status="success", title=article.get("title", ""),
        )
        return True, None

    message_ids: List[int] = []
    try:
        for i, chunk in enumerate(chunks):
            if i > 0:
                time.sleep(TELEGRAM_RATE_LIMIT_SLEEP)
            result = send_message(chat_id, chunk)
            message_ids.append(result.get("message_id", 0))

        ledger.records[key] = PublishedRecord(
            article_id=article_id,
            chat_id=chat_id,
            message_id=message_ids[0] if message_ids else None,
            published_at=datetime.now(timezone.utc).isoformat(),
            status="success",
            title=article.get("title", ""),
        )
        logger.info("✔ Published %s (%d chunk(s)) → msg_id=%s",
                    article_id, len(chunks), message_ids)
        return True, None

    except TelegramAPIError as exc:
        # Non-retryable — record as failed, don't retry next run
        ledger.records[key] = PublishedRecord(
            article_id=article_id, chat_id=chat_id,
            published_at=datetime.now(timezone.utc).isoformat(),
            status="failed", title=article.get("title", ""),
            error=str(exc)[:500],
        )
        logger.error("✘ Permanent failure for %s: %s", article_id, exc)
        return False, str(exc)

    except (requests.RequestException, RetryError) as exc:
        # Transient — do NOT record in ledger, so next run retries
        logger.error("✘ Transient failure for %s (will retry next run): %s", article_id, exc)
        return False, str(exc)


def _fallback_article_id(article: Dict[str, Any]) -> str:
    raw = f"{article.get('link', '')}|{article.get('title', '')}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


# ------------------------------------------------------------------
# Input Discovery
# ------------------------------------------------------------------
def discover_articles(input_dir: str, latest_only: bool = True) -> List[Dict[str, Any]]:
    """
    Load edited articles. If latest_only, only the most recent edited_*.json.
    """
    if not os.path.isdir(input_dir):
        logger.error("Input directory not found: %s", input_dir)
        return []

    files = sorted(
        [f for f in os.listdir(input_dir) if f.startswith("edited_") and f.endswith(".json")],
        reverse=True,
    )
    if not files:
        logger.warning("No edited files found in %s", input_dir)
        return []

    selected = [files[0]] if latest_only else files
    articles: List[Dict[str, Any]] = []
    for fname in selected:
        try:
            with open(os.path.join(input_dir, fname), "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                articles.extend(data)
        except Exception as exc:
            logger.error("Failed to read %s: %s", fname, exc)
    logger.info("Loaded %d articles from %d file(s).", len(articles), len(selected))
    return articles


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Telegram publisher")
    p.add_argument("--chat-id", default=TELEGRAM_CHAT_ID,
                   help="Target chat/channel ID (default from env)")
    p.add_argument("--dry-run", action="store_true", help="Simulate without sending")
    p.add_argument("--limit", type=int, default=MAX_PER_RUN, help="Max articles this run")
    p.add_argument("--all", action="store_true",
                   help="Publish from all edited files, not just latest")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    global DRY_RUN
    if args.dry_run:
        DRY_RUN = True

    chat_id = args.chat_id
    if not chat_id and not DRY_RUN:
        logger.error("TELEGRAM_CHAT_ID not set. Use --chat-id or env var.")
        return 1

    if not DRY_RUN and not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set.")
        return 1

    articles = discover_articles(INPUT_DIR, latest_only=not args.all)
    if not articles:
        logger.warning("No articles to publish. Exiting gracefully.")
        return 0

    # Cap
    articles = articles[: args.limit]

    ledger = load_ledger()
    success = 0
    failed = 0
    skipped = 0

    for idx, article in enumerate(articles, 1):
        article_id = article.get("article_id") or _fallback_article_id(article)
        if is_already_published(ledger, article_id, chat_id or "dry-run"):
            skipped += 1
            continue

        try:
            ok, err = publish_article(article, chat_id or "dry-run", ledger)
            if ok:
                success += 1
            else:
                failed += 1
            # Save ledger after each publish (crash-safe)
            save_ledger(ledger)
            # Respect rate limit even between articles
            if idx < len(articles) and not DRY_RUN:
                time.sleep(TELEGRAM_RATE_LIMIT_SLEEP)
        except Exception as exc:
            logger.exception("Unexpected error for %s: %s", article_id, exc)
            failed += 1

    logger.info(
        "Publishing complete: success=%d failed=%d skipped=%d total=%d",
        success, failed, skipped, len(articles),
    )

    # Success if we didn't have unexpected crash
    return 0 if success > 0 or skipped > 0 else (1 if failed > 0 else 0)


if __name__ == "__main__":
    sys.exit(main())
