"""Atomic JSON writes and POSIX locks for unattended Linux/GitHub runners."""

from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import tempfile


@contextmanager
def file_lock(path: Path, *, blocking=True):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as handle:
        flags = fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB)
        fcntl.flock(handle.fileno(), flags)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def write_json_atomic(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def redact(text: str, environment: dict) -> str:
    """Do not persist provider credentials in errors/checkpoint stage logs."""
    from urllib.parse import quote
    for name, value in environment.items():
        if (name.endswith(("_KEY", "_TOKEN")) or name == "GH_TOKEN") and len(value) >= 6:
            text = text.replace(value, "[REDACTED]").replace(quote(value, safe=""), "[REDACTED]")
    return text


def install_secret_log_filter():
    """Redact handler output as well as orchestrator-captured stdout/stderr."""
    import logging

    class SecretFilter(logging.Filter):
        def filter(self, record):
            record.msg = redact(record.getMessage(), dict(os.environ))
            record.args = ()
            if record.exc_info:
                record.exc_text = redact(logging.Formatter().formatException(record.exc_info), dict(os.environ))
            return True

    for handler in logging.getLogger().handlers:
        if not any(getattr(item, "alp_secret_filter", False) for item in handler.filters):
            filter_ = SecretFilter()
            filter_.alp_secret_filter = True
            handler.addFilter(filter_)
