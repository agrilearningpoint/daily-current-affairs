# -*- coding: utf-8 -*-
"""
BOM Cleanup Utility
===================
Removes UTF-8 BOM (\\ufeff) from Python/shell/YAML files.

Python 3 normally handles BOM in source files, but:
- Some tools (make, bash, sed) choke on BOM
- Direct CLI execution (python script.py) can misbehave
- Git diffs look noisy

Usage:
    python scripts/remove_bom.py --dry-run
    python scripts/remove_bom.py
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
BOM = "\ufeff"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("remove_bom")

# Extensions to check
TARGET_EXTS = {".py", ".sh", ".yml", ".yaml", ".json", ".toml", ".ini", ".cfg", ".md"}

# Directories to skip
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules",
             "build", "dist", ".pytest_cache", ".ruff_cache", ".mypy_cache",
             "data", "output", "logs", "state/backups", "state/archive"}


def should_skip(path: Path) -> bool:
    parts = set(path.parts)
    if parts & SKIP_DIRS:
        return True
    if path.suffix.lower() not in TARGET_EXTS:
        return True
    return False


def has_bom(path: Path) -> bool:
    try:
        with open(path, "rb") as f:
            return f.read(3) == b"\xef\xbb\xbf"
    except Exception:
        return False


def strip_bom(path: Path) -> bool:
    """Remove BOM from file. Returns True if BOM was present and removed."""
    try:
        raw = path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            path.write_bytes(raw[3:])
            return True
    except Exception as exc:
        logger.warning("Failed to process %s: %s", path, exc)
    return False


def find_files() -> List[Path]:
    files: List[Path] = []
    for path in REPO_ROOT.rglob("*"):
        if path.is_file() and not should_skip(path):
            files.append(path)
    return files


def main() -> int:
    p = argparse.ArgumentParser(description="Remove UTF-8 BOM from text files")
    p.add_argument("--dry-run", action="store_true",
                   help="Preview files with BOM (don't modify)")
    args = p.parse_args()

    files = find_files()
    logger.info("Scanning %d files", len(files))

    bom_files: List[Path] = []
    for f in files:
        if has_bom(f):
            bom_files.append(f)

    if not bom_files:
        logger.info("✔ No BOM files found")
        return 0

    logger.info("Found %d file(s) with BOM:", len(bom_files))
    for f in bom_files:
        print(f"  {f.relative_to(REPO_ROOT)}")

    if args.dry_run:
        logger.info("Dry-run — no changes. Run without --dry-run to fix.")
        return 0

    fixed = 0
    for f in bom_files:
        if strip_bom(f):
            fixed += 1
            logger.info("✅ Removed BOM: %s", f.relative_to(REPO_ROOT))

    logger.info("✔ Fixed %d/%d files", fixed, len(bom_files))
    return 0


if __name__ == "__main__":
    sys.exit(main())
