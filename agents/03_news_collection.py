# -*- coding: utf-8 -*-
"""
DEPRECATED — Retired in favor of pipeline/01_source_fetch.py
============================================================
Task 01 decision: exactly ONE collection path runs in production.
- pipeline/01_source_fetch.py is the canonical collector (registry-driven,
  job-date aware, enriched article schema).
- agents/03_news_collection.py is retired from the stage list to prevent a
  second competing collector writing different files/schemas.

This shim provides backward compatibility:
- CLI calls: forwards directly to pipeline/01_source_fetch.py
- Import calls: exports clean_text and normalize_url from pipeline.collector
"""
from __future__ import annotations

import logging
import runpy
import sys
import warnings
from pathlib import Path

# Re-export canonical Unicode-safe normalization helpers
from pipeline.collector import clean_text, normalize_url

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent.03_news_collection.deprecated")

TARGET = Path(__file__).resolve().parent.parent / "pipeline" / "01_source_fetch.py"

if __name__ == "__main__":
    warnings.warn(
        "agents/03_news_collection.py is DEPRECATED and retired from production stages. "
        "Forwarding execution to canonical collector pipeline/01_source_fetch.py.",
        DeprecationWarning,
        stacklevel=2,
    )
    logger.warning(
        "[DEPRECATED] agents/03_news_collection.py -> forwarding to pipeline/01_source_fetch.py"
    )
    if not TARGET.exists():
        logger.error("Target canonical collector not found: %s", TARGET)
        sys.exit(1)
    runpy.run_path(str(TARGET), run_name="__main__")
