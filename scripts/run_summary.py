#!/usr/bin/env python3
"""Print a compact run summary (counts + AI providers) for one edition.

Writes plain text to stdout (job log) and Markdown to $GITHUB_STEP_SUMMARY when
that variable is set. Every input is optional: a stage that did not run simply
shows "-". Never exits non-zero, so it is safe as an `if: always()` step.

Usage: python scripts/run_summary.py --job-id daily_2026-11-03
"""
from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROUTER_OK = re.compile(r"\[Router\] ✔ (\w+) responded \(task=([\w:]+)(?:, model=([^,\)]+))?")


def _load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _count(doc, key="items"):
    if doc is None:
        return None
    if isinstance(doc, list):
        return len(doc)
    if isinstance(doc, dict):
        value = doc.get(key)
        return len(value) if isinstance(value, (list, dict)) else None
    return None


def _pdf_pages(path: Path):
    if not path.is_file():
        return None
    try:
        from pypdf import PdfReader
        return len(PdfReader(str(path)).pages)
    except Exception:  # noqa: BLE001
        try:
            import fitz  # PyMuPDF
            with fitz.open(str(path)) as doc:
                return doc.page_count
        except Exception:  # noqa: BLE001
            return None


def collect_counts(root: Path, job_id: str) -> dict:
    data = root / "data"
    raw = _load(data / "raw" / f"{job_id}.json")
    selected = _load(data / "selected" / f"{job_id}.json")
    content = _load(data / "content" / f"{job_id}.json") or {}
    auto = content.get("auto_sections_stats") or {}
    agri = content.get("agri_corner")
    images = content.get("image_stats") or {}
    recon = content.get("mcq_reconciliation") or {}
    return {
        "raw": (raw or {}).get("article_count", _count(raw, "articles")) if isinstance(raw, dict) else _count(raw),
        "verified": _count(_load(data / "verified" / f"{job_id}.json")),
        "dedup": _count(_load(data / "dedup" / f"{job_id}.json")),
        "scored": _count(_load(data / "scored" / f"{job_id}.json")),
        "selected": _count(selected),
        "reserves": _count(selected, "reserves"),
        "final_stories": _count(content) if content else None,
        "mcqs": _count(_load(data / "mcq" / f"{job_id}.json")),
        "quick_bites": len(content.get("quick_bites") or []) if content else None,
        "agri_items": (len(agri.get("items") or []) if isinstance(agri, dict) else auto.get("agri_items")) if content else None,
        "photos": images.get("attached") if images else None,
        "promoted_reserves": recon.get("promoted_reserves"),
        "pdf_pages": _pdf_pages(root / "output" / f"{job_id}.pdf"),
    }


def collect_providers(root: Path, job_id: str) -> tuple[dict, str]:
    """{(provider, model): Counter(task->ok count), failures} from ai_usage.jsonl,
    falling back to the stage logs' router lines."""
    ok: dict = defaultdict(Counter)
    failed: dict = defaultdict(Counter)
    usage = root / "logs" / "ai_usage.jsonl"
    source = ""
    if usage.is_file():
        for line in usage.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get("job") and row["job"] != job_id:
                continue
            key = (row.get("provider", "?"), row.get("model", ""))
            (ok if row.get("ok") else failed)[key][row.get("task", "?")] += 1
        source = "logs/ai_usage.jsonl"
    if not ok and not failed:
        stage_dir = root / "logs" / "stages" / job_id
        for log in sorted(stage_dir.glob("*.log")) if stage_dir.is_dir() else []:
            for m in ROUTER_OK.finditer(log.read_text(encoding="utf-8", errors="replace")):
                ok[(m.group(1), m.group(3) or "")][m.group(2)] += 1
        source = "stage logs" if ok else "none recorded"
    return {"ok": ok, "failed": failed}, source


def render(job_id: str, job: dict, counts: dict, providers: dict, source: str) -> tuple[str, str]:
    window = job.get("window") or {}
    order = ["raw", "verified", "dedup", "scored", "selected", "reserves", "final_stories", "mcqs",
             "quick_bites", "agri_items", "photos", "promoted_reserves", "pdf_pages"]
    fmt = lambda v: "-" if v is None else str(v)  # noqa: E731
    text = [f"RUN SUMMARY {job_id}: status={job.get('status', '-')} last_stage={job.get('last_success_stage', '-')}",
            f"  window: {window.get('start', '-')} -> {window.get('end', '-')}"]
    if job.get("publish_not_before"):
        text.append(f"  publish not before: {job['publish_not_before']}")
    text.append("  counts: " + ", ".join(f"{k}={fmt(counts.get(k))}" for k in order))
    md = [f"### Run summary `{job_id}`", "",
          f"- **Status:** {job.get('status', '-')} (last stage `{job.get('last_success_stage', '-')}`)",
          f"- **Window (IST):** {window.get('start', '-')} → {window.get('end', '-')}"]
    if job.get("publish_not_before"):
        md.append(f"- **Publish not before:** {job['publish_not_before']}")
    md += ["", "| " + " | ".join(order) + " |", "|" + "---|" * len(order),
           "| " + " | ".join(fmt(counts.get(k)) for k in order) + " |", "",
           f"**AI providers** (source: {source})", ""]
    text.append(f"  AI providers ({source}):")
    if not providers["ok"] and not providers["failed"]:
        text.append("    none")
        md.append("- none")
    for (name, model), tasks in sorted(providers["ok"].items()):
        detail = ", ".join(f"{t}×{n}" for t, n in sorted(tasks.items()))
        text.append(f"    OK   {name} [{model or '?'}]: {detail}")
        md.append(f"- ✅ **{name}** `{model or '?'}`: {detail}")
    for (name, model), tasks in sorted(providers["failed"].items()):
        detail = ", ".join(f"{t}×{n}" for t, n in sorted(tasks.items()))
        text.append(f"    FAIL {name} [{model or '?'}]: {detail}")
        md.append(f"- ❌ {name} `{model or '?'}`: {detail}")
    return "\n".join(text), "\n".join(md) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-id", default=os.getenv("ALP_JOB_ID") or (
        f"daily_{os.environ['EDITION_DATE']}" if os.getenv("EDITION_DATE") else ""))
    parser.add_argument("--root", default=str(ROOT))
    args = parser.parse_args(argv)
    try:
        root = Path(args.root)
        jobs = _load(root / "state" / "jobs.json") or {}
        jobs = jobs.get("jobs", jobs) if isinstance(jobs, dict) else {}
        job = jobs.get(args.job_id) or {}
        counts = collect_counts(root, args.job_id)
        providers, source = collect_providers(root, args.job_id)
        text, md = render(args.job_id, job, counts, providers, source)
        print(text)
        summary = os.getenv("GITHUB_STEP_SUMMARY")
        if summary:
            with open(summary, "a", encoding="utf-8") as handle:
                handle.write(md)
    except Exception as exc:  # noqa: BLE001 - a summary must never fail the job
        print(f"run summary unavailable: {exc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
