# -*- coding: utf-8 -*-
"""
Memory Store — Importance Memory + Published Events
====================================================
Persistent state for:
- Importance memory (used by MCQ distractor pools + weekly/monthly editors)
- Published events (idempotency ledger)
- Source health tracking

Production features:
- Atomic writes (tempfile + fsync + os.replace)
- File-level locking (fcntl on POSIX, msvcrt on Windows)
- Corruption recovery (auto-backup + fresh start)
- Legacy format migration (list → dict)
- Size cap (LRU eviction of oldest entries)
- Schema validation
- Thread-safe operations
- Env override for file location

Env:
  ALP_MEMORY_PATH        — override importance memory location
  ALP_MEMORY_MAX_ENTRIES — max entries before trimming (default 2000)
  ALP_PUBLISHED_PATH     — override published events location
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Union

logger = logging.getLogger("pipeline.store")

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
REPO_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_MEMORY_PATH = REPO_ROOT / "state" / "importance_memory.json"
DEFAULT_PUBLISHED_PATH = REPO_ROOT / "state" / "published_events.json"
DEFAULT_SOURCE_HEALTH_PATH = REPO_ROOT / "state" / "source_health.json"

MAX_MEMORY_ENTRIES = int(os.getenv("ALP_MEMORY_MAX_ENTRIES", "2000"))
MAX_PUBLISHED_ENTRIES = int(os.getenv("ALP_PUBLISHED_MAX_ENTRIES", "10000"))


def _memory_path() -> Path:
    override = os.getenv("ALP_MEMORY_PATH")
    return Path(override) if override else DEFAULT_MEMORY_PATH


def _published_path() -> Path:
    override = os.getenv("ALP_PUBLISHED_PATH")
    return Path(override) if override else DEFAULT_PUBLISHED_PATH


# --------------------------------------------------------------------------- #
# Cross-platform file lock
# --------------------------------------------------------------------------- #
@contextmanager
def _file_lock(path: Path) -> Iterator[None]:
    """
    Exclusive file lock for cross-process safety.

    Delegates to pipeline.persistence.file_lock so POSIX uses fcntl.flock and
    Windows uses msvcrt.locking — both real locks. (The previous local version
    silently skipped locking off-POSIX, so concurrent Windows writers were not
    actually serialised.) The lock lives in a sibling ``<name>.lock`` file so the
    data file itself is never held open by a waiter.
    """
    from pipeline.persistence import file_lock

    lock_path = path.with_suffix(path.suffix + ".lock")
    with file_lock(lock_path):
        yield


# --------------------------------------------------------------------------- #
# Atomic I/O
# --------------------------------------------------------------------------- #
def _atomic_write_json(path: Path, data: Any) -> None:
    """Write JSON atomically: temp + fsync + os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        prefix=f".{path.stem}_", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass
        raise


def _read_json(path: Path) -> Optional[Any]:
    """
    Read JSON. On corruption:
    - Backup original to <path>.corrupt.<timestamp>
    - Return None (caller falls back to default)
    """
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        backup = path.with_suffix(f"{path.suffix}.corrupt.{int(time.time())}")
        try:
            path.rename(backup)
            logger.error("Corrupt JSON at %s → backed up to %s: %s",
                         path, backup, exc)
        except OSError as rename_exc:
            logger.error("Corrupt JSON at %s (backup failed: %s): %s",
                         path, rename_exc, exc)
        return None
    except OSError as exc:
        logger.error("Cannot read %s: %s", path, exc)
        return None


# --------------------------------------------------------------------------- #
# Importance Memory
# --------------------------------------------------------------------------- #
def load_memory() -> Dict[str, Any]:
    """
    Load importance memory as a dict keyed by event_id.

    Returns empty dict if:
    - File doesn't exist
    - File is corrupt (auto-backed up)
    - File format unrecognized

    Never raises.
    """
    data = _read_json(_memory_path())
    if data is None:
        return {}
    if isinstance(data, dict):
        # Support {"events": {...}} wrapper
        if "events" in data and isinstance(data["events"], dict):
            return dict(data["events"])
        return data
    if isinstance(data, list):
        # Legacy list format — migrate to dict
        out: Dict[str, Any] = {}
        for item in data:
            if not isinstance(item, dict):
                continue
            key = item.get("event_id") or item.get("id") or item.get("fingerprint")
            if key:
                out[str(key)] = item
        logger.info("[store] migrated list → dict (%d entries)", len(out))
        return out
    logger.warning("[store] unrecognized memory format: %s", type(data).__name__)
    return {}


def save_memory(memory: Dict[str, Any]) -> None:
    """
    Save memory. Trims to MAX_MEMORY_ENTRIES, keeping newest by pub_time_ist.
    Uses file lock + atomic write.
    """
    if not isinstance(memory, dict):
        logger.warning("[store] save_memory: not a dict, skipping")
        return

    if len(memory) > MAX_MEMORY_ENTRIES:
        def _sort_key(kv):
            ev = kv[1] if isinstance(kv[1], dict) else {}
            return (
                ev.get("pub_time_ist") or
                ev.get("added_at") or
                ev.get("updated") or
                ""
            )
        sorted_items = sorted(memory.items(), key=_sort_key, reverse=True)
        memory = dict(sorted_items[:MAX_MEMORY_ENTRIES])
        logger.info("[store] trimmed memory to %d entries", MAX_MEMORY_ENTRIES)

    with _file_lock(_memory_path()):
        _atomic_write_json(_memory_path(), memory)


def _merge_dicts(local: Dict[str, Any], remote: Dict[str, Any]) -> Dict[str, Any]:
    """Union event maps; the entry with the newest known timestamp wins."""
    from datetime import datetime, timezone

    def stamp(entry):
        if not isinstance(entry, dict):
            return datetime.min.replace(tzinfo=timezone.utc)
        for key in ("last_seen", "updated_at", "updated", "pub_time_ist", "added_at"):
            try:
                dt = datetime.fromisoformat(str(entry.get(key, "")).replace("Z", "+00:00"))
                return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
            except ValueError:
                continue
        return datetime.min.replace(tzinfo=timezone.utc)

    merged = dict(remote)
    for key, value in local.items():
        if key not in merged or stamp(value) >= stamp(merged[key]):
            merged[key] = value
    return merged


def record_scores(items, job_id):
    """Persist all scored events for later edition selection without git side effects."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    with _file_lock(_memory_path()):
        memory = load_memory()
        for item in items:
            event = dict(item, last_seen=now, last_job_id=job_id)
            memory[item["event_id"]] = event
        newest = sorted(memory.items(), key=lambda kv: kv[1].get("last_seen", "")
                        if isinstance(kv[1], dict) else "", reverse=True)
        _atomic_write_json(_memory_path(), dict(newest[:MAX_MEMORY_ENTRIES]))


def upsert_memory(event_id: str, event_data: Dict[str, Any]) -> None:
    """Insert or update a single memory entry."""
    if not event_id:
        return
    memory = load_memory()
    memory[str(event_id)] = event_data
    save_memory(memory)


def memory_has(event_id: str) -> bool:
    return str(event_id) in load_memory()


def memory_size() -> int:
    return len(load_memory())


# --------------------------------------------------------------------------- #
# Published Events (Idempotency Ledger)
# --------------------------------------------------------------------------- #
def load_published() -> Dict[str, Any]:
    """
    Load published events ledger.

    Canonical shape: {"version": 1, "records": {key: {...}}}
    Legacy list also accepted — migrated to dict.
    """
    data = _read_json(_published_path())
    if data is None:
        return {"version": 1, "records": {}}
    if isinstance(data, dict):
        if "records" not in data:
            data["records"] = {}
        return data
    if isinstance(data, list):
        out = {"version": 1, "records": {}}
        for item in data:
            if not isinstance(item, dict):
                continue
            key = item.get("key") or item.get("id")
            if key:
                out["records"][str(key)] = item
        logger.info("[store] migrated published list → dict (%d entries)", len(out["records"]))
        return out
    return {"version": 1, "records": {}}


def save_published(ledger: Dict[str, Any]) -> None:
    """Save published ledger with lock + atomic write."""
    if not isinstance(ledger, dict):
        logger.warning("[store] save_published: not a dict, skipping")
        return
    if "records" not in ledger:
        ledger["records"] = {}

    # Trim oldest if too large
    records = ledger["records"]
    if len(records) > MAX_PUBLISHED_ENTRIES:
        def _sort_key(kv):
            v = kv[1] if isinstance(kv[1], dict) else {}
            return v.get("published_at") or v.get("at") or ""
        sorted_items = sorted(records.items(), key=_sort_key, reverse=True)
        ledger["records"] = dict(sorted_items[:MAX_PUBLISHED_ENTRIES])
        logger.info("[store] trimmed published ledger to %d entries",
                    MAX_PUBLISHED_ENTRIES)

    with _file_lock(_published_path()):
        _atomic_write_json(_published_path(), ledger)


def append_published(record: Dict[str, Any]) -> bool:
    """
    Append a published record. Returns True if newly added,
    False if already present (idempotent).
    """
    if not isinstance(record, dict):
        return False
    key = record.get("key") or record.get("id")
    if not key:
        logger.warning("[store] append_published: no key in record")
        return False

    ledger = load_published()
    if key in ledger["records"]:
        logger.debug("[store] already published: %s", key)
        return False

    ledger["records"][str(key)] = record
    save_published(ledger)
    return True


def is_published(key: str) -> bool:
    return str(key) in load_published().get("records", {})


def is_job_published(job_id: str) -> bool:
    """True when the ledger holds a *live* success receipt for this job_id.

    Distinct from ``is_published(key)``: the ledger key is a hash of
    (chat_id, job_id, file_hash), so job-level lookups must scan records.
    A record only counts when it is a non-dry-run success with a positive
    message_id — the same contract used by pipeline.publication.
    """
    from pipeline.publication import positive_message_id

    records = load_published().get("records", {})
    wanted = str(job_id)
    return any(
        isinstance(record, dict)
        and str(record.get("job_id")) == wanted
        and record.get("status") == "success"
        and not record.get("dry_run")
        and positive_message_id(record.get("message_id"))
        for record in records.values()
    )


# --------------------------------------------------------------------------- #
# Source Health Tracking
# --------------------------------------------------------------------------- #
def _source_health_path() -> Path:
    override = os.getenv("ALP_SOURCE_HEALTH_PATH")
    return Path(override) if override else DEFAULT_SOURCE_HEALTH_PATH


def load_source_health() -> Dict[str, Any]:
    data = _read_json(_source_health_path())
    if data is None:
        return {"version": 1, "sources": {}}
    if isinstance(data, dict):
        data.setdefault("sources", {})
        return data
    return {"version": 1, "sources": {}}


def save_source_health(health: Dict[str, Any]) -> None:
    if not isinstance(health, dict):
        return
    health.setdefault("sources", {})
    with _file_lock(_source_health_path()):
        _atomic_write_json(_source_health_path(), health)


def update_source_health(
    source_url: str,
    success: bool,
    article_count: int = 0,
    error: Optional[str] = None,
) -> None:
    """Track per-source health. Called by agent 03."""
    health = load_source_health()
    sources = health.setdefault("sources", {})
    entry = sources.setdefault(source_url, {
        "success_count": 0,
        "failure_count": 0,
        "consecutive_failures": 0,
        "last_success_at": None,
        "last_failure_at": None,
        "last_error": None,
        "last_article_count": 0,
    })

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    if success:
        entry["success_count"] = int(entry.get("success_count", 0)) + 1
        entry["consecutive_failures"] = 0
        entry["last_success_at"] = now
        entry["last_article_count"] = article_count
        entry["last_error"] = None
    else:
        entry["failure_count"] = int(entry.get("failure_count", 0)) + 1
        entry["consecutive_failures"] = int(entry.get("consecutive_failures", 0)) + 1
        entry["last_failure_at"] = now
        entry["last_error"] = (error or "")[:500]

    save_source_health(health)


# --------------------------------------------------------------------------- #
# Health check / stats
# --------------------------------------------------------------------------- #
def stats() -> Dict[str, Any]:
    """Return store stats — useful for health checks."""
    mem = load_memory()
    pub = load_published()
    health = load_source_health()
    return {
        "memory": {
            "path": str(_memory_path()),
            "entries": len(mem),
            "max": MAX_MEMORY_ENTRIES,
            "exists": _memory_path().exists(),
        },
        "published": {
            "path": str(_published_path()),
            "entries": len(pub.get("records", {})),
            "max": MAX_PUBLISHED_ENTRIES,
            "exists": _published_path().exists(),
        },
        "source_health": {
            "path": str(_source_health_path()),
            "sources": len(health.get("sources", {})),
            "exists": _source_health_path().exists(),
        },
    }


# --------------------------------------------------------------------------- #
# Smoke test
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import json
    print(json.dumps(stats(), indent=2, default=str))
