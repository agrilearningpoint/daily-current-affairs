"""Shared publication evidence contract; never treat stale/dry-run receipts as live proof."""
import json
from pathlib import Path

PUBLICATION_LEDGER = "published_events.json"
PIN_LEDGER = "pin_verification.json"


def positive_message_id(value):
    return type(value) is int and value > 0


def migrate_legacy_flat_ledger(value: dict):
    """Adopt the pre-versioned flat ledger ``{key: {jobs: [...], last_published}}``.

    Identity (chat_id/file_hash) cannot be recovered from that format, so the
    entries are preserved as ``legacy_unknown`` records: they are never treated
    as live receipts, but the editions they list can never be silently resent.
    Returns ``None`` when ``value`` is not that legacy shape.
    """
    if not isinstance(value, dict) or "records" in value or "version" in value or not value:
        return None
    records = {}
    for key, entry in value.items():
        if not isinstance(entry, dict) or not isinstance(entry.get("jobs", []), list):
            return None
        jobs = [str(job) for job in entry.get("jobs") or []]
        records[str(key)] = {
            "job_id": jobs[-1] if jobs else None,
            "jobs": jobs,
            "last_published": entry.get("last_published"),
            "status": "legacy_unknown",
            "legacy_migrated": True,
        }
    return {"version": 1, "records": records}


def records_at(path: Path):
    """Missing ledgers are empty; malformed existing ledgers must fail closed."""
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    legacy = migrate_legacy_flat_ledger(value)
    if legacy is not None:
        value = legacy
    if not isinstance(value, dict) or not isinstance(value.get("records"), dict):
        raise ValueError(f"invalid record map in {path.name}")
    if any(not isinstance(record, dict) for record in value["records"].values()):
        raise ValueError(f"invalid record in {path.name}")
    return value["records"]


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
