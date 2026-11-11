#!/usr/bin/env python3
"""Seed state/mcq_history.json from already-published editions.

The cross-edition MCQ memory (pipeline/mcq_history.py) starts empty, so the
first edition after deployment had nothing to avoid repeating - on 2026-11-11
the MSP concept question printed for the 4th time in five editions anyway.
This one-off tool folds every downloadable past edition into the history so
the rotation/repeat guards work from day one.

Usage:
    python scripts/backfill_mcq_history.py DIR_OR_ZIP [MORE...] [--write]

Accepts ``daily_YYYY-MM-DD.json`` MCQ files (top-level list) or pipeline
artifact zips containing ``data/mcq/daily_YYYY-MM-DD.json``.  Editions are
folded oldest-first; without --write it only prints what would change.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import mcq_history as mh  # noqa: E402

DATE_RE = re.compile(r"daily_(\d{4}-\d{2}-\d{2})")


def _expand(paths: list[Path]) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        if p.is_dir():
            out.extend(sorted(p.glob("*.zip")) + sorted(p.glob("daily_*.json")))
        else:
            out.append(p)
    return out


def _editions_from(paths: list[Path]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for p in _expand(paths):
        blobs: list[tuple[str, bytes]] = []
        if p.suffix == ".zip":
            with zipfile.ZipFile(p) as z:
                for n in z.namelist():
                    m = DATE_RE.search(n)
                    if m and "/mcq/" in n and n.endswith(".json"):
                        blobs.append((m.group(1), z.read(n)))
        else:
            m = DATE_RE.search(p.name)
            if m:
                blobs.append((m.group(1), p.read_bytes()))
        for day, raw in blobs:
            try:
                data = json.loads(raw.decode("utf-8"))
            except Exception:
                continue
            mcqs = data if isinstance(data, list) else data.get("mcqs") or []
            if mcqs:
                out.setdefault(day, []).extend(m for m in mcqs if isinstance(m, dict))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+", type=Path)
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    eds = _editions_from(args.paths)
    if not eds:
        print("no editions found in the given paths")
        return 1
    history = mh.empty_history()
    for day in sorted(eds):
        n = mh.record(history, eds[day], edition_date=day)
        print(f"  {day}: {len(eds[day]):2} mcqs folded ({n} entries touched)")
    removed = mh.prune(history)
    st = mh.stats(history)
    print(f"pruned {removed} stale entries; final: {st}")
    if args.write:
        ok = mh.save(history)
        print("written:", ok, mh.history_path())
        return 0 if ok else 1
    print("(dry run - pass --write to save)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
