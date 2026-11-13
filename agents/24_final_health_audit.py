# -*- coding: utf-8 -*-
"""
Agent 24: Independent Final Content & System Health Audit (Section 15 & 19)
===========================================================================
Executes the pre-publication quality gate across News, MCQs, and PDF reports,
and writes:
- `reports/daily_quality_report.json`
- `reports/daily_health_report.json`
A single critical failure blocks publication.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pipeline.store import ROOT_DIR, atomic_write_json

REPORTS_DIR = ROOT_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def run_final_content_audit(
    edition_date: str,
    window_label: str,
    verified_news: List[Dict[str, Any]],
    validated_mcqs: List[Dict[str, Any]],
    pdf_qa_dict: Dict[str, Any],
    api_health_dict: Optional[Dict[str, Any]] = None,
    feed_health_dict: Optional[Dict[str, Any]] = None,
    out_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    r_dir = out_dir or REPORTS_DIR
    r_dir.mkdir(parents=True, exist_ok=True)
    now_iso = datetime.now(timezone.utc).isoformat()

    critical_failures: List[str] = []
    warnings: List[str] = []

    # 1. News Audit
    if not verified_news:
        critical_failures.append("zero_verified_news_items")
    for idx, item in enumerate(verified_news, 1):
        if not item.get("published_at_ist"):
            critical_failures.append(f"news_{idx}_missing_verified_ist_timestamp")
        if item.get("verification_status") != "verified":
            critical_failures.append(f"news_{idx}_unverified_status")
        if not str(item.get("link") or item.get("canonical_url") or "").startswith(("http://", "https://")):
            critical_failures.append(f"news_{idx}_missing_source_url")

    # 2. MCQ Audit
    if not validated_mcqs:
        critical_failures.append("zero_validated_mcqs")
    formats_seen = {m.get("question_format") for m in validated_mcqs if m.get("question_format")}
    if len(validated_mcqs) >= 4 and len(formats_seen) < 2:
        warnings.append("mcq_format_variety_low")
    for idx, m in enumerate(validated_mcqs, 1):
        if m.get("validation_status") != "validated":
            critical_failures.append(f"mcq_{idx}_not_validated")
        if len(m.get("options_en") or m.get("options") or []) != 5:
            critical_failures.append(f"mcq_{idx}_not_5_options")

    # 3. PDF Audit
    if not pdf_qa_dict.get("passed", False):
        critical_failures.append("pdf_qa_gate_failed")
    if pdf_qa_dict.get("blank_pages"):
        critical_failures.append(f"pdf_has_blank_pages:{pdf_qa_dict['blank_pages']}")

    passed = len(critical_failures) == 0

    quality_report = {
        "edition_date": edition_date,
        "research_window": window_label,
        " audited_at": now_iso,
        "passed": passed,
        "critical_failures": critical_failures,
        "warnings": warnings,
        "metrics": {
            "verified_news_count": len(verified_news),
            "validated_mcq_count": len(validated_mcqs),
            "distinct_mcq_formats": sorted(list(formats_seen)),
            "pdf_page_count": pdf_qa_dict.get("page_count", 0),
            "pdf_hindi_pct": pdf_qa_dict.get("hindi_pct", 0.0),
            "pdf_substantive_pages": pdf_qa_dict.get("substantive_pages", 0),
        },
    }

    health_report = {
        "edition_date": edition_date,
        "generated_at": now_iso,
        "pipeline_status": "healthy" if passed else "blocked_by_quality_gate",
        "active_feeds_tracked": len(feed_health_dict or {}),
        "quarantined_feeds": [
            k for k, v in (feed_health_dict or {}).items()
            if isinstance(v, dict) and v.get("quarantined_until")
        ],
        "api_keys_tracked": len((api_health_dict or {}).get("keys", {})),
        "healthy_api_keys": [
            k for k, v in ((api_health_dict or {}).get("keys", {})).items()
            if isinstance(v, dict) and v.get("status") == "healthy"
        ],
        "cooldown_api_keys": [
            k for k, v in ((api_health_dict or {}).get("keys", {})).items()
            if isinstance(v, dict) and v.get("status") == "cooldown"
        ],
    }

    atomic_write_json(r_dir / "daily_quality_report.json", quality_report)
    atomic_write_json(r_dir / "daily_health_report.json", health_report)
    return quality_report
