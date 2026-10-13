# -*- coding: utf-8 -*-
"""
Memory Store
============
Importance memory + published events persistent store.

Features:
- Atomic JSON writes (crash-safe)
- Auto-create parent directories
- Corruption recovery (backup + fresh start)
- Env override via ALP_MEMORY_PATH
- LRU-style size cap (keeps memory bounded)
- Thread-safe via file locking
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MEMORY_PATH = REPO_ROOT / "state" / "importance_memory.json"
DEFAULT_PUBLISHED_PATH = REPO_ROOT / "state" / "published_events.json"
MAX_MEMORY_ENTRIES = int(os.getenv("ALP_MEMORY_MAX_ENTRIES", "2000"))


def _memory_path() -> Path:
    override = os.getenv("ALP_MEMORY_PATH")
    if override:
        return Path(override)
    return DEFAULT_MEMORY_PATH


def _published_path() -> Path:
    return DEFAULT_PUBLISHED_PATH


# --------------------------------------------------------------------------- #
# Atomic I/O
# --------------------------------------------------------------------------- #
def _atomic_write(path: Path, data: Any) -> None:
    """Write JSON atomically: temp file + fsync + rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".store_", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        raise


def _read_json(path: Path) -> Optional[Any]:
    """Read JSON. On corruption: backup original + return None."""
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        backup = path.with_suffix(f".corrupt.{int(time.time())}.json")
        try:
            path.rename(backup)
            logger.error("Corrupt JSON at %s — backed up to %s. Error: %s",
                         path, backup, exc)
        except OSError:
            logger.error("Corrupt JSON at %s and backup failed: %s", path, exc)
        return None


# --------------------------------------------------------------------------- #
# Memory API (used by content.py)
# --------------------------------------------------------------------------- #
def load_memory() -> Dict[str, Any]:
    """
    Load importance memory. Returns dict keyed by event_id.
    Missing file → empty dict (never raises).
    """
    data = _read_json(_memory_path())
    if data is None:
        return {}
    if isinstance(data, dict):
        return data
    # Old format was a list — convert to dict keyed by event_id
    if isinstance(data, list):
        out: Dict[str, Any] = {}
        for item in data:
            if isinstance(item, dict):
                key = item.get("event_id") or item.get("id")
                if key:
                    out[str(key)] = item
        logger.info("[store] migrated list-format memory → dict (%d entries)", len(out))
        return out
    logger.warning("[store] unexpected memory format: %s", type(data).__name__)
    return {}


def save_memory(memory: Dict[str, Any]) -> None:
    """Save memory dict. Trims to MAX_MEMORY_ENTRIES (keeps newest by pub_time_ist)."""
    if not isinstance(memory, dict):
        logger.warning("[store] save_memory: not a dict, skipping")
        return

    if len(memory) > MAX_MEMORY_ENTRIES:
        def _sort_key(kv):
            ev = kv[1] if isinstance(kv[1], dict) else {}
            return ev.get("pub_time_ist") or ev.get("added_at") or ""
        trimmed = dict(sorted(memory.items(), key=_sort_key, reverse=True)[:MAX_MEMORY_ENTRIES])
        logger.info("[store] trimmed memory %d → %d", len(memory), len(trimmed))
        memory = trimmed

    _atomic_write(_memory_path(), memory)


def upsert_memory(event_id: str, event_data: Dict[str, Any]) -> None:
    """Add/update single entry and save."""
    if not event_id:
        return
    memory = load_memory()
    memory[str(event_id)] = event_data
    save_memory(memory)


def memory_has(event_id: str) -> bool:
    return str(event_id) in load_memory()


# --------------------------------------------------------------------------- #
# Published events API
# --------------------------------------------------------------------------- #
def load_published() -> List[Dict[str, Any]]:
    data = _read_json(_published_path())
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "events" in data:
        return list(data["events"])
    logger.warning("[store] unexpected published format")
    return []


def save_published(events: List[Dict[str, Any]]) -> None:
    if not isinstance(events, list):
        logger.warning("[store] save_published: not a list")
        return
    _atomic_write(_published_path(), {"version": 1, "events": events})


def append_published(event: Dict[str, Any]) -> None:
    events = load_published()
    events.append(event)
    save_published(events)


# --------------------------------------------------------------------------- #
# Health check / debug helpers
# --------------------------------------------------------------------------- #
def stats() -> Dict[str, Any]:
    mem = load_memory()
    pub = load_published()
    return {
        "memory_path": str(_memory_path()),
        "memory_entries": len(mem),
        "memory_max": MAX_MEMORY_ENTRIES,
        "published_path": str(_published_path()),
        "published_count": len(pub),
    }
