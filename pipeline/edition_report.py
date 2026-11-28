# -*- coding: utf-8 -*-
"""
EDITION EDITORIAL & RELIABILITY REPORT GENERATOR (Phase 13)
===========================================================
Generates structured Markdown and JSON post-run edition reports at:
  - reports/{job_id}_edition_report.json
  - reports/{job_id}_edition_report.md

Summarizes:
  1. Pipeline Funnel Counts (raw -> verified -> dedup -> scored -> selected -> content -> MCQs)
  2. Bilingual / Hindi Quality & MCQ Examiner Scores
  3. PDF QA Metrics (pages, Devanagari %, images, visual checks, release gate)
  4. AI Usage Summary & Supervisor Repairs (if any)
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    return default


def _item_count(path: Path) -> int:
    data = _read_json(path)
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        for k in ("items", "articles", "mcqs"):
            if isinstance(data.get(k), list):
                return len(data[k])
    return 0


def build_edition_report(
    job_id: str,
    job_type: str = "daily",
    repo_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Assemble and write JSON + Markdown edition report under reports/."""
    from pipeline.persistence import write_json_atomic

    root = Path(repo_root or ROOT)
    reports_dir = root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    funnel = {
        "raw": _item_count(root / "data" / "raw" / f"{job_id}.json"),
        "verified": _item_count(root / "data" / "verified" / f"{job_id}.json"),
        "dedup": _item_count(root / "data" / "dedup" / f"{job_id}.json"),
        "scored": _item_count(root / "data" / "scored" / f"{job_id}.json"),
        "selected": _item_count(root / "data" / "selected" / f"{job_id}.json"),
        "content": _item_count(root / "data" / "content" / f"{job_id}.json"),
        "mcqs": (
            _item_count(root / "data" / "mcq" / f"{job_id}.json")
            or _item_count(root / "data" / "content" / f"mcqs_{job_id}.json")
        ),
    }

    content = _read_json(root / "data" / "content" / f"{job_id}.json", {})
    if not isinstance(content, dict):
        content = {}
    t_stats = content.get("translation_stats") or {}
    img_stats = content.get("image_stats") or {}

    qa = _read_json(root / "logs" / "qa" / f"{job_id}_qa.json", {})
    if not isinstance(qa, dict):
        qa = {}
    health = _read_json(root / "logs" / "qa" / f"{job_id}_health.json", {})
    if not isinstance(health, dict):
        health = {}
    sup = _read_json(root / "logs" / f"{job_id}_supervisor_audit.json", {})
    if not isinstance(sup, dict):
        sup = {}

    report: Dict[str, Any] = {
        "job_id": job_id,
        "job_type": job_type,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": os.getenv("DRY_RUN", "0") == "1",
        "funnel": funnel,
        "translation_stats": t_stats,
        "image_stats": img_stats,
        "pdf_qa": {
            "passed": qa.get("passed"),
            "page_count": qa.get("page_count"),
            "hindi_pct": qa.get("hindi_pct"),
            "mcq_count": qa.get("mcq_count"),
            "duplicate_questions": qa.get("duplicate_questions"),
            "substantive_pages": qa.get("substantive_pages"),
            "visual_qa_passed": (qa.get("visual_qa") or {}).get("passed") if isinstance(qa.get("visual_qa"), dict) else None,
            "release_approved": (qa.get("release_approval") or {}).get("approved") if isinstance(qa.get("release_approval"), dict) else None,
            "issue_count": len(qa.get("issues") or []),
        },
        "health_audit_passed": health.get("passed"),
        "supervisor_repairs": sup.get("repairs_run", 0),
    }

    json_path = reports_dir / f"{job_id}_edition_report.json"
    write_json_atomic(json_path, report)

    md_lines: List[str] = [
        f"# Edition Report — {job_id}",
        "",
        f"- **Job Type:** `{job_type}`",
        f"- **Generated At:** `{report['generated_at']}`",
        f"- **Mode:** `{'DRY_RUN' if report['dry_run'] else 'LIVE'}`",
        "",
        "## Pipeline Funnel",
        "",
        "| Stage | Item Count |",
        "|---|---:|",
        f"| Raw Collected | {funnel['raw']} |",
        f"| Fact Verified | {funnel['verified']} |",
        f"| Deduplicated | {funnel['dedup']} |",
        f"| Relevance Scored | {funnel['scored']} |",
        f"| Selected | {funnel['selected']} |",
        f"| Editorial Content | {funnel['content']} |",
        f"| Validated MCQs | {funnel['mcqs']} |",
        "",
        "## PDF & Quality Gate",
        "",
        f"- **PDF QA Passed:** `{report['pdf_qa']['passed']}`",
        f"- **Pages:** `{report['pdf_qa']['page_count']}` (Substantive: `{report['pdf_qa']['substantive_pages']}`)",
        f"- **Devanagari Coverage:** `{report['pdf_qa']['hindi_pct']}%`",
        f"- **MCQs in PDF:** `{report['pdf_qa']['mcq_count']}` (Duplicates: `{report['pdf_qa']['duplicate_questions']}`)",
        f"- **Visual QA Passed:** `{report['pdf_qa']['visual_qa_passed']}`",
        f"- **Release Approved:** `{report['pdf_qa']['release_approved']}`",
        f"- **Supervisor Repairs:** `{report['supervisor_repairs']}`",
    ]
    md_path = reports_dir / f"{job_id}_edition_report.md"
    tmp_md = md_path.with_suffix(".md.tmp")
    tmp_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    os.replace(tmp_md, md_path)

    return report
