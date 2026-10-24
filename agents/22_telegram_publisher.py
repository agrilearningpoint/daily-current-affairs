# -*- coding: utf-8 -*-
"""
Telegram Publisher Agent (22)
=============================
PDF + summary ko Telegram channel par publish karta hai.

Production features:
- Idempotent publishing (persistent ledger — crash-safe)
- Rate-limit aware (429 → Retry-After respect)
- Retry with exponential backoff
- Automatic message splitting (4096 char limit)
- Safe HTML escaping (no parse errors)
- Context-managed file handles (no leaks)
- Duplicate detection (by job_id + file hash)
- Dry-run mode
- Atomic ledger writes
- Structured logging

Env:
  TELEGRAM_BOT_TOKEN   (required)
  TELEGRAM_CHAT_ID     (required — @channel or -100...)
  TELEGRAM_PARSE_MODE  (HTML | MarkdownV2 | empty) — default HTML
  TELEGRAM_MAX_PER_RUN (default 5)
  DRY_RUN              (0 | 1)
"""
from __future__ import annotations

import hashlib
import html
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
LOGS_DIR = REPO_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(LOGS_DIR / "telegram_publisher.log"), encoding="utf-8"),
    ],
)
logger = logging.getLogger("agent.22_telegram_publisher")
from pipeline.persistence import install_secret_log_filter, redact
install_secret_log_filter()


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
TELEGRAM_API_BASE = "https://api.telegram.org"
TELEGRAM_MAX_MESSAGE_LEN = 4096
TELEGRAM_SAFE_CHUNK_LEN = 3500  # buffer for formatting
TELEGRAM_CAPTION_MAX_LEN = 1024
RATE_LIMIT_SLEEP = 1.5  # conservative: under 20 msgs/min per group

INPUT_DIRS = [
    REPO_ROOT / "output",
    REPO_ROOT / "data" / "content",
]
LEDGER_FILE = REPO_ROOT / "state" / "published_events.json"

def _load_dotenv() -> None:
    env_file = REPO_ROOT / ".env"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip("'\"")
            if k not in os.environ:
                os.environ[k] = v

_load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
TELEGRAM_PARSE_MODE = os.getenv("TELEGRAM_PARSE_MODE", "HTML").strip()
TELEGRAM_MAX_PER_RUN = int(os.getenv("TELEGRAM_MAX_PER_RUN", "5"))
DRY_RUN = os.getenv("DRY_RUN", "0") == "1"


# --------------------------------------------------------------------------- #
# Custom Exceptions
# --------------------------------------------------------------------------- #
class TelegramRateLimit(Exception):
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Rate limited, retry after {retry_after}s")


class TelegramAPIError(Exception):
    """Non-retryable error (400-level, malformed, blocked, etc.)"""
    pass


# --------------------------------------------------------------------------- #
# Ledger (Idempotency)
# --------------------------------------------------------------------------- #
def _ledger_key(job_id: str, chat_id: str, file_hash: str) -> str:
    return hashlib.sha256(f"{chat_id}|{job_id}|{file_hash}".encode("utf-8")).hexdigest()[:24]


def load_ledger() -> Dict[str, Any]:
    """Never replace unreadable publication history with an empty retry ledger."""
    if not LEDGER_FILE.exists():
        return {"version": 1, "records": {}}
    data = json.loads(LEDGER_FILE.read_text(encoding="utf-8"))
    if isinstance(data, list):
        records = {}
        for record in data:
            if not isinstance(record, dict):
                raise ValueError("invalid legacy publication record")
            key = record.get("key")
            if not key and all(record.get(field) for field in ("job_id", "chat_id", "file_hash")):
                key = _ledger_key(record["job_id"], record["chat_id"], record["file_hash"])
            if not key:
                raise ValueError("legacy publication record has no stable identity")
            records[key] = record
        data = {"version": 1, "records": records}
    if isinstance(data, dict) and "records" not in data and data:
        legacy = all(
            isinstance(key, str) and len(key) == 16
            and all(char in "0123456789abcdef" for char in key)
            and isinstance(record, dict)
            and isinstance(record.get("jobs"), list) and record["jobs"]
            and all(isinstance(job, str) and job for job in record["jobs"])
            and isinstance(record.get("last_published"), str)
            for key, record in data.items()
        )
        if legacy:
            for record in data.values():
                datetime.strptime(record["last_published"], "%Y-%m-%d")
            return {"version": 1, "records": {}, "legacy_history": data}
    if not isinstance(data, dict) or not isinstance(data.get("records"), dict):
        raise ValueError("invalid publication ledger; manual reconciliation required")
    if any(not isinstance(record, dict) for record in data["records"].values()):
        raise ValueError("invalid publication record; manual reconciliation required")
    return data


def save_ledger(ledger: Dict[str, Any]) -> None:
    from pipeline.persistence import write_json_atomic
    write_json_atomic(LEDGER_FILE, ledger)


def is_published(ledger: Dict[str, Any], key: str) -> bool:
    from pipeline.publication import positive_message_id
    rec = ledger.get("records", {}).get(key)
    return bool(isinstance(rec, dict) and rec.get("status") == "success"
                and not rec.get("dry_run") and positive_message_id(rec.get("message_id")))


# --------------------------------------------------------------------------- #
# File Hashing
# --------------------------------------------------------------------------- #
def file_hash(path: Path, chunk_size: int = 65536) -> str:
    """Stream-hash a file without loading it fully into memory."""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                h.update(chunk)
        return h.hexdigest()[:16]
    except Exception as exc:
        logger.warning("Hash failed for %s: %s", path, exc)
        return ""


# --------------------------------------------------------------------------- #
# Message Formatting
# --------------------------------------------------------------------------- #
def escape_html(text: str) -> str:
    if not text:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_caption(title: str, summary: str = "", link: str = "", source: str = "") -> str:
    """Build HTML caption (≤1024 chars) formatted with bold, italic, and sign format."""
    clean_title = re.sub(r"^>+\s*", "", title).strip()
    date_display = ""
    m_iso = re.search(r"(\d{4}-\d{2}-\d{2})", clean_title)
    if m_iso:
        try:
            dt = datetime.strptime(m_iso.group(1), "%Y-%m-%d")
            date_display = dt.strftime("%d %b %Y").lstrip("0")
        except Exception:
            date_display = m_iso.group(1)
    else:
        m_human = re.search(r"(\d{1,2}\s+[A-Za-z]+\s+\d{4})", clean_title)
        if m_human:
            try:
                raw_d = m_human.group(1)
                for fmt in ("%d %B %Y", "%d %b %Y"):
                    try:
                        dt = datetime.strptime(raw_d, fmt)
                        date_display = dt.strftime("%d %b %Y").lstrip("0")
                        break
                    except ValueError:
                        pass
                if not date_display:
                    date_display = raw_d
            except Exception:
                date_display = m_human.group(1)
        else:
            job_date = os.getenv("ALP_JOB_DATE", "")
            if job_date:
                try:
                    dt = datetime.strptime(job_date, "%Y-%m-%d")
                    date_display = dt.strftime("%d %b %Y").lstrip("0")
                except Exception:
                    date_display = job_date
            else:
                date_display = datetime.now().strftime("%d %b %Y").lstrip("0")

    caption_lines = [
        f"🌾 <b>agri learning point  {date_display}</b> <i>Genius Current Affairs Top Notch MCQs</i>",
        "",
        "• <b>India's No.1 Current Affairs PDF</b>",
        "• <i>Research With Unique Facts</i>",
        "• <b>English &amp; Hindi  Language</b>",
        "• <i>One Liner Current Affairs</i>",
        "• <b>Best Explanations</b>",
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        "🎯 <i>UPSSSC AGTA • IBPS AFO • ICAR • NABARD • STATE PCS</i>",
        "🔗 <b>Official Channels:</b>",
        "  👉 <a href='https://t.me/agrilearningpoint'>Agri Learning Point</a> (Current Affairs)",
        "  👉 <a href='https://t.me/agriquizworld'>Agri Quiz World</a> (Daily Quizzes)",
        "  👉 <a href='https://www.youtube.com/@Agrilearningpoint'>YouTube: Agri Learning Point</a>",
    ]
    caption = "\n".join(caption_lines)
    if len(caption) > TELEGRAM_CAPTION_MAX_LEN:
        caption = caption[: TELEGRAM_CAPTION_MAX_LEN - 3] + "..."
    return caption


def chunk_message(text: str, max_len: int = TELEGRAM_SAFE_CHUNK_LEN) -> List[str]:
    """Split long text at natural boundaries."""
    if len(text) <= max_len:
        return [text]
    chunks: List[str] = []
    remaining = text
    while len(remaining) > max_len:
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


# --------------------------------------------------------------------------- #
# Telegram API
# --------------------------------------------------------------------------- #
def _api_url(method: str) -> str:
    return f"{TELEGRAM_API_BASE}/bot{TELEGRAM_BOT_TOKEN}/{method}"


def _handle_response(r: requests.Response, ctx: str) -> Dict[str, Any]:
    if r.status_code == 429:
        retry_after = int(r.headers.get("Retry-After", "5"))
        try:
            data = r.json()
            retry_after = int(data.get("parameters", {}).get("retry_after", retry_after))
        except (ValueError, TypeError, AttributeError):
            pass
        raise TelegramRateLimit(min(max(retry_after, 1), 60))
    try:
        data = r.json()
    except ValueError as exc:
        raise requests.RequestException(f"{ctx}: ambiguous non-JSON response ({r.status_code})") from exc
    if not isinstance(data, dict):
        raise requests.RequestException(f"{ctx}: ambiguous response shape")
    if data.get("ok") is not True:
        desc = data.get("description", "unknown error")
        if 400 <= r.status_code < 500:
            raise TelegramAPIError(f"{ctx}: {desc} (HTTP {r.status_code})")
        raise requests.RequestException(f"{ctx}: ambiguous API failure (HTTP {r.status_code})")
    result = data.get("result")
    if not isinstance(result, dict):
        raise requests.RequestException(f"{ctx}: ambiguous result shape")
    return result


def send_message(chat_id: str, text: str, parse_mode: str = "") -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    r = requests.post(_api_url("sendMessage"), json=payload, timeout=30)
    return _handle_response(r, "sendMessage")


def send_document(
    chat_id: str,
    doc_path: Path,
    caption: str = "",
    parse_mode: str = "",
) -> Dict[str, Any]:
    """Send document using context-managed file handle (no leaks)."""
    data: Dict[str, Any] = {"chat_id": chat_id}
    if caption:
        data["caption"] = caption[:TELEGRAM_CAPTION_MAX_LEN]
    if parse_mode:
        data["parse_mode"] = parse_mode

    # Context manager ensures file handle is closed even on exception
    with open(doc_path, "rb") as f:
        files = {"document": (doc_path.name, f, "application/pdf")}
        r = requests.post(_api_url("sendDocument"), data=data, files=files, timeout=120)
    return _handle_response(r, "sendDocument")


# --------------------------------------------------------------------------- #
# Retry Wrapper
# --------------------------------------------------------------------------- #
def call_with_retry(fn, *args, max_attempts: int = 5, retry_network: bool = True, **kwargs):
    """Retry on network/rate-limit. Non-retryable errors propagate immediately."""
    last_exc: Optional[Exception] = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn(*args, **kwargs)
        except TelegramRateLimit as exc:
            logger.warning("Rate limited. Sleeping %ds (attempt %d/%d)",
                           exc.retry_after, attempt, max_attempts)
            time.sleep(exc.retry_after)
            last_exc = exc
        except TelegramAPIError:
            raise  # never retry API 400-level errors
        except requests.RequestException as exc:
            if not retry_network:
                raise
            wait = 2 ** attempt
            logger.warning("Network error: %s (retry in %ds, attempt %d/%d)",
                           exc, wait, attempt, max_attempts)
            time.sleep(wait)
            last_exc = exc

    if last_exc:
        raise last_exc
    raise RuntimeError("call_with_retry: exhausted")


# --------------------------------------------------------------------------- #
# Discovery
# --------------------------------------------------------------------------- #
def find_pdfs() -> List[Path]:
    """Find candidate PDFs, newest first."""
    job_id = os.getenv("ALP_JOB_ID")
    if job_id:
        path = REPO_ROOT / "output" / f"{job_id}.pdf"
        return [path] if path.is_file() else []
    job_date = os.getenv("ALP_JOB_DATE")
    if job_date:
        path = REPO_ROOT / "output" / f"daily_{job_date}.pdf"
        if path.is_file():
            return [path]
    candidates: List[Path] = []
    for d in INPUT_DIRS:
        if not d.exists():
            continue
        candidates.extend(p for p in d.glob("*.pdf") if p.is_file())
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates


def find_meta_for_pdf(pdf_path: Path) -> Dict[str, Any]:
    """Look for a matching content_*.json for title/summary."""
    meta_dirs = [
        REPO_ROOT / "data" / "content",
        REPO_ROOT / "data" / "selected",
    ]
    for d in meta_dirs:
        if not d.exists():
            continue
        candidates = [d / f"{pdf_path.stem}.json"]
        for meta_file in candidates:
            try:
                data = json.loads(meta_file.read_text(encoding="utf-8"))
            except Exception:
                continue
            if isinstance(data, dict):
                items = data.get("items") or data.get("articles") or []
                if isinstance(items, list) and items:
                    first = items[0]
                    job_info = data.get("job", {})
                    date_display = job_info.get("date_display", "")
                    title = f"Agri Learning Point — Daily Current Affairs ({date_display})" if date_display else (first.get("headline_en", "") or first.get("title", ""))
                    headlines = []
                    for it in items:
                        hl = re.sub(r"^>+\s*", "", it.get("headline_en", "") or it.get("title", "")).strip()
                        hl = re.sub(r"<[^>]+>", "", hl).strip()
                        if hl and hl.lower() != "estic" and not hl.startswith("http") and not hl.startswith("Untitled"):
                            headlines.append(f"• {hl}")
                    summary = "📰 Today's Key Exam Headlines:\n" + "\n".join(headlines[:5])
                    return {
                        "title": title,
                        "summary": summary,
                        "source": "Agri Learning Point | 100% Verified Sources",
                        "link": "https://t.me/agrilearningpoint",
                    }
            if isinstance(data, list) and data:
                first = data[0]
                if isinstance(first, dict):
                    return {
                        "title": first.get("headline_en", "") or first.get("title", ""),
                        "summary": first.get("summary", ""),
                        "source": first.get("source_feed", ""),
                        "link": first.get("link", ""),
                    }
    return {}


# --------------------------------------------------------------------------- #
# Publish One PDF
# --------------------------------------------------------------------------- #
def publish_pdf(pdf_path: Path, ledger: Dict[str, Any]) -> bool:
    """Publish one PDF + caption. Returns True on success or already-published."""
    fh = file_hash(pdf_path)
    if not fh:
        logger.error("Cannot hash %s — skipping", pdf_path.name)
        return False

    # Bind the publish gate to this exact PDF, not a stale QA report.
    job_id = pdf_path.stem
    qa_path = REPO_ROOT / "logs" / "qa" / f"{job_id}_qa.json"
    try:
        qa = json.loads(qa_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        logger.error("No valid QA approval for %s", job_id)
        return False
    if (qa.get("passed") is not True or qa.get("job_id") != job_id
            or qa.get("file_sha256") != hashlib.sha256(pdf_path.read_bytes()).hexdigest()):
        logger.error("QA gate rejected %s (failed, wrong job, or PDF changed)", job_id)
        return False
    if not DRY_RUN:
        try:
            content = json.loads((REPO_ROOT / "data/content" / f"{job_id}.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return False
        allow_fallback = os.getenv("ALP_ALLOW_FALLBACK_TRANSLATION", "0") == "1"
        if not content.get("items") or any(
            not isinstance(i, dict)
            or (not allow_fallback and (i.get("needs_review") is not False or i.get("verification_passed") is not True))
            for i in content["items"]
        ):
            logger.error("Content lacks verified provenance or completed translation review; publish blocked")
            return False
    if any(job_id in record.get("jobs", [])
           for record in ledger.get("legacy_history", {}).values()
           if isinstance(record, dict)):
        logger.error("Legacy publication history contains %s without a verifiable receipt; manual reconciliation required",
                     job_id)
        return False
    key = _ledger_key(job_id, TELEGRAM_CHAT_ID, fh)

    allow_revision = os.getenv("ALP_ALLOW_EDITION_REVISION", "0") == "1"
    if any(isinstance(record, dict) and record.get("job_id") == job_id
           and str(record.get("chat_id")) == str(TELEGRAM_CHAT_ID)
           and (record.get("status") in {"sending", "uncertain"}
                or record.get("status") == "blocked_revision" and not allow_revision)
           for record in ledger.get("records", {}).values()):
        logger.error("Publication outcome uncertain for %s; manual reconciliation required, refusing resend", job_id)
        return False

    if is_published(ledger, key):
        record = ledger["records"][key]
        if not record.get("file_sha256"):
            record["file_sha256"] = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
            save_ledger(ledger)
        logger.info("Already published: %s — skipping", pdf_path.name)
        return True

    if not DRY_RUN and not allow_revision and any(isinstance(record, dict) and record.get("job_id") == job_id
                           and str(record.get("chat_id")) == str(TELEGRAM_CHAT_ID)
                           and record.get("status") == "success" and not record.get("dry_run")
                           for record in ledger.get("records", {}).values()):
        ledger["records"][key] = {"job_id": job_id, "chat_id": TELEGRAM_CHAT_ID, "file_hash": fh,
                                  "file_sha256": hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
                                  "status": "blocked_revision", "published_at": datetime.now(timezone.utc).isoformat()}
        save_ledger(ledger)
        logger.error("A different PDF for this edition was already published; manual reconciliation required")
        return False

    meta = find_meta_for_pdf(pdf_path)
    caption = build_caption(
        title=meta.get("title", pdf_path.stem),
        summary=meta.get("summary", ""),
        source=meta.get("source", ""),
        link=meta.get("link", ""),
    )

    if DRY_RUN:
        logger.info("[DRY-RUN] Would publish %s (%d bytes) with caption:\n%s",
                    pdf_path.name, pdf_path.stat().st_size, caption[:200])
        ledger["records"][key] = {
            "job_id": job_id, "chat_id": TELEGRAM_CHAT_ID, "file_hash": fh,
            "published_at": datetime.now(timezone.utc).isoformat(),
            "status": "success", "dry_run": True,
            "file": pdf_path.name,
        }
        return True

    if os.getenv("ALP_JOB_ID"):
        from main import load_jobs_state, STAGES_BY_TYPE
        from pipeline.checkpoints import resume_after
        entry = load_jobs_state(strict=True).get(job_id, {})
        names = [stage[0] for stage in STAGES_BY_TYPE.get(os.getenv("ALP_JOB_TYPE", "daily"), [])]
        if (os.getenv("ALP_JOB_ID") != job_id or entry.get("dry_run") is not False
                or not entry.get("artifacts") or resume_after(REPO_ROOT, job_id, entry, names) != "19_pdf_qa"):
            logger.error("Pre-publication checkpoint evidence changed or incomplete; refusing send")
            return False

    # Write ahead before a side-effecting request: interrupted/ambiguous sends
    # must be reconciled, never blindly retried as if Telegram rejected them.
    ledger["records"][key] = {
        "job_id": job_id, "chat_id": TELEGRAM_CHAT_ID, "file_hash": fh,
        "file_sha256": hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
        "file": pdf_path.name, "status": "sending",
        "published_at": datetime.now(timezone.utc).isoformat(),
    }
    save_ledger(ledger)
    try:
        result = call_with_retry(
            send_document,
            TELEGRAM_CHAT_ID, pdf_path,
            caption=caption, parse_mode=TELEGRAM_PARSE_MODE, retry_network=False,
        )
        msg_id = result.get("message_id")
        if type(msg_id) is not int or msg_id <= 0:
            raise requests.RequestException("sendDocument returned no valid message_id")
        ledger["records"][key] = {
            "job_id": job_id,
            "chat_id": TELEGRAM_CHAT_ID,
            "message_id": msg_id,
            "file_hash": fh,
            "file_sha256": hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
            "file": pdf_path.name,
            "published_at": datetime.now(timezone.utc).isoformat(),
            "status": "success",
        }
        save_ledger(ledger)  # persist immediately (crash-safe)
        logger.info("[OK] Published %s -> message_id=%s", pdf_path.name, msg_id)
        return True

    except TelegramRateLimit as exc:
        ledger["records"][key].update(status="failed", error=str(exc),
                                      published_at=datetime.now(timezone.utc).isoformat())
        save_ledger(ledger)
        return False

    except TelegramAPIError as exc:
        # Permanent — do NOT record as success so it won't be silently skipped
        logger.error("✘ Permanent failure for %s: %s", pdf_path.name, exc)
        ledger["records"][key] = {
            "job_id": job_id, "chat_id": TELEGRAM_CHAT_ID, "file_hash": fh,
            "file": pdf_path.name,
            "published_at": datetime.now(timezone.utc).isoformat(),
            "status": "failed", "error": redact(str(exc), dict(os.environ))[:300],
        }
        save_ledger(ledger)
        return False

    except requests.RequestException as exc:
        ledger["records"][key].update(status="uncertain", error=redact(str(exc), dict(os.environ))[:300],
                                      published_at=datetime.now(timezone.utc).isoformat())
        save_ledger(ledger)
        logger.error("Publication outcome uncertain for %s; manual reconciliation required, refusing resend", job_id)
        return False


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

    pdfs = find_pdfs()
    if not pdfs:
        logger.warning("No PDFs found in %s", [str(d) for d in INPUT_DIRS])
        return 1

    logger.info("Found %d candidate PDF(s) (max %d per run)",
                len(pdfs), TELEGRAM_MAX_PER_RUN)

    try:
        ledger = load_ledger()
    except (ValueError, OSError):
        logger.error("Publication ledger unreadable; manual reconciliation required, refusing send")
        return 1
    success = failed = skipped = 0

    for idx, pdf in enumerate(pdfs[: TELEGRAM_MAX_PER_RUN], 1):
        try:
            logger.info("[%d/%d] %s",
                        idx, min(len(pdfs), TELEGRAM_MAX_PER_RUN), pdf.name)
            ok = publish_pdf(pdf, ledger)
            if ok:
                success += 1
            else:
                failed += 1
            if not DRY_RUN and idx < len(pdfs):
                time.sleep(RATE_LIMIT_SLEEP)  # respect rate limits
        except Exception as exc:
            failed += 1
            logger.exception("Unexpected error for %s: %s", pdf.name, exc)

    logger.info(
        "Publishing complete: success=%d failed=%d skipped=%d total=%d",
        success, failed, skipped, min(len(pdfs), TELEGRAM_MAX_PER_RUN),
    )

    # Exit 0 if at least one succeeded (or nothing to do)
    return 0 if success > 0 and failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
