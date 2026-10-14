# -*- coding: utf-8 -*-
"""
DEPRECATED — Renamed to agents/22_telegram_publisher.py
=======================================================
Yeh file sirf backward compatibility ke liye rakhi gayi hai.

Direct invocation is deprecated. Use:
    python agents/22_telegram_publisher.py

Yeh shim puraane scripts/workflows ke liye forwarding karta hai.
"""
import logging
import runpy
import sys
import warnings
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent.14_telegram_publish.deprecated")

warnings.warn(
    "agents/14_telegram_publish.py is DEPRECATED. "
    "Use agents/22_telegram_publisher.py instead.",
    DeprecationWarning,
    stacklevel=2,
)
logger.warning(
    "⚠️  DEPRECATED: 14_telegram_publish.py — forwarding to 22_telegram_publisher.py"
)

TARGET = Path(__file__).resolve().parent / "22_telegram_publisher.py"

if not TARGET.exists():
    logger.error("Target not found: %s", TARGET)
    sys.exit(1)

# Forward execution to the canonical module
runpy.run_path(str(TARGET), run_name="__main__")
