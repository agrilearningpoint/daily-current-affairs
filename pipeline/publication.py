"""Shared publication evidence contract; never treat stale/dry-run receipts as live proof."""
import json
from pathlib import Path

PUBLICATION_LEDGER = "published_events.json"
PIN_LEDGER = "pin_verification.json"


def positive_message_id(value):
    return type(value) is int and value > 0


def records_at(path: Path):
    """Missing ledgers are empty; malformed existing ledgers must fail closed.

    Rows left over from the pre-versioned ledger (a job list and a date, no
    chat_id/file_hash/status) carry no verifiable identity, so they are skipped
    here: they can never be treated as a live receipt. ``agents/22`` keeps them
    as ``legacy_history`` and refuses a resend for the editions they list.
    """
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("records"), dict):
        raise ValueError(f"invalid record map in {path.name}")
    if any(not isinstance(record, dict) for record in value["records"].values()):
        raise ValueError(f"invalid record in {path.name}")
    return {key: record for key, record in value["records"].items()
            if record.get("status") is not None}


def publication_issues(root: Path, job_id: str, pdf_sha256: str, chat_id=None):
    """Require a receipt for this PDF and a pin receipt for that same message/chat."""
    try:
        published = records_at(root / "state" / PUBLICATION_LEDGER)
        pinned = records_at(root / "state" / PIN_LEDGER)
    except (OSError, ValueError) as exc:
        return [str(exc)]
    matches = [record for record in published.values()
               if record.get("job_id") == job_id and record.get("status") == "success"
               and not record.get("dry_run") and record.get("file_sha256") == pdf_sha256
               and positive_message_id(record.get("message_id")) and record.get("chat_id")
               and (not chat_id or str(record["chat_id"]) == str(chat_id))]
    if not matches:
        return ["no live publication receipt for the exact PDF/job/chat"]
    for record in matches:
        if any(pin.get("status") == "verified" and not pin.get("dry_run")
               and pin.get("job_id") == job_id
               and positive_message_id(pin.get("message_id"))
               and pin.get("message_id") == record["message_id"]
               and positive_message_id(pin.get("pinned_message_id"))
               and pin.get("pinned_message_id") == record["message_id"]
               and str(pin.get("chat_id")) == str(record["chat_id"])
               for pin in pinned.values()):
            return []
    return ["no verified pin receipt for this published message/job/chat"]
