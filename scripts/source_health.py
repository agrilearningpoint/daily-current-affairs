"""Source-health diagnostic for the canonical RSS registry.

Purpose
-------
Answer the question "which configured sources actually work?" with evidence,
instead of assuming a feed is live because it appears in a config file.

Two modes
---------
1. Offline (default) — no network access:
     * loads the canonical registry via pipeline.source_registry.load_sources()
     * reports tier / category distribution and the resolved source ids
     * detects duplicate RSS URLs (the "would fetch twice" class of bug)
   Exit 0 when the registry is valid, 1 when it cannot be loaded.

2. Live (``--live``) — probes every source over the network:
     * HTTP status and bounded timeout (``--timeout``, default 15s)
     * feed parseability, usable item count and newest timestamp
     * per-source error text is recorded, never discarded
   Exit 0 when at least one source returned usable items, 1 otherwise.
   A single failing source never discards the others' results.

Safety
------
Read-only: no Telegram calls, no state writes, no artifact writes.

Usage
-----
    python scripts/source_health.py                 # offline registry check
    python scripts/source_health.py --live          # probe every source
    python scripts/source_health.py --live --json   # machine-readable report
"""
from __future__ import annotations

import argparse
import contextlib
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

for _stream in (sys.stdout, sys.stderr):
    if _stream and hasattr(_stream, "reconfigure"):
        with contextlib.suppress(Exception):
            _stream.reconfigure(encoding="utf-8", errors="replace")


def _load_registry():
    from pipeline.source_registry import SourceConfigError, load_sources

    try:
        return load_sources(), None
    except SourceConfigError as exc:
        return [], str(exc)


def registry_report(specs) -> dict:
    """Offline summary + duplicate detection."""
    urls = [s.rss_url for s in specs]
    duplicates = sorted({u for u in urls if urls.count(u) > 1})

    by_tier: dict[int, int] = {}
    by_category: dict[str, int] = {}
    for s in specs:
        by_tier[s.tier] = by_tier.get(s.tier, 0) + 1
        by_category[s.category] = by_category.get(s.category, 0) + 1

    return {
        "count": len(specs),
        "by_tier": {str(k): v for k, v in sorted(by_tier.items())},
        "by_category": dict(sorted(by_category.items())),
        "duplicate_urls": duplicates,
        "sources": [
            {
                "source_id": s.source_id,
                "name": s.name,
                "rss_url": s.rss_url,
                "tier": s.tier,
                "category": s.category,
                "official": s.official,
            }
            for s in specs
        ],
    }


def probe_source(spec, timeout: int) -> dict:
    """Probe one feed. Never raises; returns a result dict with 'error' on failure."""
    result = {
        "source_id": spec.source_id,
        "name": spec.name,
        "rss_url": spec.rss_url,
        "tier": spec.tier,
        "http_status": None,
        "entries": 0,
        "usable_items": 0,
        "newest": None,
        "error": None,
    }
    try:
        import feedparser
        import requests
    except ImportError as exc:  # pragma: no cover - environment issue
        result["error"] = f"missing dependency: {exc}"
        return result

    try:
        resp = requests.get(
            spec.rss_url,
            headers={"User-Agent": "alp-source-health/1.0"},
            timeout=timeout,
        )
        result["http_status"] = resp.status_code
        resp.raise_for_status()
        parsed = feedparser.parse(resp.content)
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result

    entries = list(getattr(parsed, "entries", []) or [])
    result["entries"] = len(entries)
    newest = None
    for entry in entries:
        for key in ("published_parsed", "updated_parsed"):
            t = getattr(entry, key, None)
            if not t:
                continue
            try:
                import calendar
                dt = datetime.fromtimestamp(calendar.timegm(t), tz=UTC)
            except Exception:
                continue
            if newest is None or dt > newest:
                newest = dt
    if newest is not None:
        result["newest"] = newest.isoformat()

    recent_cutoff = datetime.now(UTC) - timedelta(days=7)
    usable = 0
    for entry in entries:
        title = str(getattr(entry, "title", "") or "").strip()
        link = str(getattr(entry, "link", "") or "").strip()
        if not title or not link.lower().startswith(("http://", "https://")):
            continue
        usable += 1
    result["usable_items"] = usable
    result["recent_window_items_hint"] = (
        "newest item is within the last 7 days"
        if newest and newest >= recent_cutoff
        else "newest item is older than 7 days (or undated)"
    )
    if parsed.bozo and not entries:
        result["error"] = f"unparseable feed ({getattr(parsed, 'bozo_exception', 'unknown')})"
    return result


def _print_offline(report: dict) -> None:
    print("=" * 72)
    print("SOURCE HEALTH — OFFLINE REGISTRY CHECK")
    print("=" * 72)
    print(f"Enabled sources: {report['count']}")
    print(f"By tier:         {report['by_tier']}")
    print(f"By category:     {report['by_category']}")
    if report["duplicate_urls"]:
        print("[X] DUPLICATE RSS URLs (would be fetched twice):")
        for u in report["duplicate_urls"]:
            print(f"      {u}")
    else:
        print("[OK] No duplicate RSS URLs")
    print()
    print("Sources:")
    for s in report["sources"]:
        flag = "official" if s["official"] else "editorial"
        print(f"  [tier{s['tier']:>2}] {s['name'][:42]:42s} {s['category'][:18]:18s} {flag}")
    print("=" * 72)


def _print_live(results: list[dict]) -> None:
    print("=" * 72)
    print("SOURCE HEALTH — LIVE PROBE")
    print("=" * 72)
    ok = [r for r in results if not r["error"] and r["usable_items"] > 0]
    failed = [r for r in results if r["error"]]
    empty = [r for r in results if not r["error"] and r["usable_items"] == 0]
    for r in results:
        if r["error"]:
            status = "FAIL"
        elif r["usable_items"] == 0:
            status = "EMPTY"
        else:
            status = "OK"
        newest = (r["newest"] or "")[:19]
        print(f"  [{status:5}] {r['name'][:38]:38s} http={r['http_status']} "
              f"items={r['usable_items']:>4} newest={newest}")
        if r["error"]:
            print(f"          -> {r['error']}")
    print("-" * 72)
    print(f"OK: {len(ok)}   EMPTY: {len(empty)}   FAIL: {len(failed)}   total: {len(results)}")
    print("=" * 72)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--live", action="store_true", help="probe every source over the network")
    parser.add_argument("--timeout", type=int, default=15, help="per-source HTTP timeout seconds (default 15)")
    parser.add_argument("--json", action="store_true", help="emit a JSON report")
    args = parser.parse_args(argv)

    specs, error = _load_registry()
    if error:
        payload = {"ok": False, "stage": "registry", "error": error}
        print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else f"[X] {error}", file=sys.stderr)
        return 1

    offline = registry_report(specs)
    if offline["duplicate_urls"]:
        # Duplicate URLs are a configuration defect: fetching twice is never intended.
        payload = {"ok": False, "stage": "offline", **offline}
        print(json.dumps(payload, ensure_ascii=False, indent=2) if args.json else "", end="")
        if not args.json:
            _print_offline(offline)
        return 1

    if not args.live:
        if args.json:
            print(json.dumps({"ok": True, "stage": "offline", **offline}, ensure_ascii=False, indent=2))
        else:
            _print_offline(offline)
        return 0

    results = [probe_source(spec, args.timeout) for spec in specs]
    ok = [r for r in results if not r["error"] and r["usable_items"] > 0]
    if args.json:
        print(json.dumps(
            {"ok": bool(ok), "stage": "live", "total": len(results),
             "ok_count": len(ok), "results": results},
            ensure_ascii=False, indent=2,
        ))
    else:
        _print_live(results)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
