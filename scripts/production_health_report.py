#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Centralized Production Health Report & Dashboard Generator (Phase 2).

Reads existing repository state and observability files (``state/jobs.json``,
``state/published_events.json``, ``state/healing_history.json``,
``recovery_plan.json``, ``logs/qa/*_qa.json``, ``logs/ai_usage.jsonl``,
``logs/provider_health.json``, ``logs/provider_summary.json``) and produces:
  - ``reports/production_health.json``
  - ``reports/production_health.csv``
  - ``docs/PRODUCTION_HEALTH_DASHBOARD.md``

Never leaks secrets and never fabricates missing live metrics.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.persistence import write_json_atomic  # noqa: E402


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    return default


def _parse_iso(ts: Any) -> Optional[datetime]:
    if not ts or not isinstance(ts, str):
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _duration_sec(job: Dict[str, Any]) -> Optional[float]:
    start = _parse_iso(job.get("started_at"))
    end = _parse_iso(job.get("updated_at"))
    if not start or not end:
        return None
    diff = (end - start).total_seconds()
    return round(diff, 2) if 0.0 <= diff <= 86400.0 * 7 else None


def _job_type(job_id: str, rec: Dict[str, Any]) -> str:
    jt = str(rec.get("job_type") or "").strip().lower()
    if jt in ("daily", "weekly", "monthly"):
        return jt
    for prefix in ("daily", "weekly", "monthly"):
        if job_id.startswith(prefix + "_"):
            return prefix
    return "other"


def collect_production_health(root: Path = ROOT) -> Dict[str, Any]:
    """Assemble consolidated repository telemetry strictly from recorded artifacts."""
    root = Path(root)
    raw_jobs = _read_json(root / "state" / "jobs.json", {})
    jobs_map = raw_jobs.get("jobs", raw_jobs) if isinstance(raw_jobs, dict) else {}
    if not isinstance(jobs_map, dict):
        jobs_map = {}

    # 1. Workflow counts, failure stages, duration & retry stats
    wf_stats: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {
            "total": 0,
            "success": 0,
            "failed": 0,
            "pending_or_other": 0,
            "multi_attempt_recovered": 0,
            "durations_sec": [],
            "single_attempt_durations_sec": [],
        }
    )
    failure_by_stage: Counter = Counter()
    unresolved_jobs: List[Dict[str, Any]] = []
    job_rows: List[Dict[str, Any]] = []

    for jid in sorted(jobs_map.keys()):
        rec = jobs_map.get(jid)
        if not isinstance(rec, dict):
            continue
        jt = _job_type(jid, rec)
        st = str(rec.get("status") or "unknown").lower()
        attempts = int(rec.get("run_attempts") or 1)
        dur = _duration_sec(rec)
        failed_stage = str(rec.get("failed_stage") or "")
        last_stage = str(rec.get("last_success_stage") or "")

        ws = wf_stats[jt]
        ws["total"] += 1
        if st == "success":
            ws["success"] += 1
            if attempts > 1:
                ws["multi_attempt_recovered"] += 1
        elif st in ("failed", "failed_final", "error"):
            ws["failed"] += 1
            if failed_stage:
                failure_by_stage[f"{jt}:{failed_stage}"] += 1
            unresolved_jobs.append({
                "job_id": jid,
                "job_type": jt,
                "status": st,
                "attempts": attempts,
                "failed_stage": failed_stage or None,
                "last_success_stage": last_stage or None,
                "updated_at": rec.get("updated_at"),
            })
        else:
            ws["pending_or_other"] += 1
            if failed_stage:
                failure_by_stage[f"{jt}:{failed_stage}"] += 1

        if dur is not None and st == "success":
            ws["durations_sec"].append(dur)
            if attempts == 1:
                ws["single_attempt_durations_sec"].append(dur)

        job_rows.append({
            "job_id": jid,
            "job_type": jt,
            "status": st,
            "attempts": attempts,
            "last_success_stage": last_stage,
            "failed_stage": failed_stage,
            "duration_sec": dur,
            "updated_at": rec.get("updated_at") or "",
        })

    workflows_out: Dict[str, Dict[str, Any]] = {}
    for jt in ("daily", "weekly", "monthly", "other"):
        ws = wf_stats.get(jt)
        if not ws or ws["total"] == 0:
            continue
        total = ws["total"]
        single_durs = ws["single_attempt_durations_sec"]
        all_durs = ws["durations_sec"]
        workflows_out[jt] = {
            "total_runs": total,
            "success_runs": ws["success"],
            "failed_runs": ws["failed"],
            "pending_or_other_runs": ws["pending_or_other"],
            "success_rate_pct": round((ws["success"] / total) * 100.0, 2) if total else 0.0,
            "failure_rate_pct": round((ws["failed"] / total) * 100.0, 2) if total else 0.0,
            "multi_attempt_recovered": ws["multi_attempt_recovered"],
            "mean_single_attempt_duration_sec": round(sum(single_durs) / len(single_durs), 2) if single_durs else None,
            "mean_end_to_end_duration_sec": round(sum(all_durs) / len(all_durs), 2) if all_durs else None,
        }

    # 2. Auto-Heal & Recovery Plan telemetry
    heal = _read_json(root / "state" / "healing_history.json", {"incidents": [], "budgets": {}})
    incidents = heal.get("incidents") or [] if isinstance(heal, dict) else []
    heal_status_counts: Counter = Counter()
    heal_category_counts: Counter = Counter()
    for inc in incidents:
        if isinstance(inc, dict):
            heal_status_counts[str(inc.get("status") or "unknown")] += 1
            heal_category_counts[str(inc.get("category") or "unknown")] += 1

    rec_plan = _read_json(root / "recovery_plan.json", {})
    rec_manual = rec_plan.get("manual_attention") or [] if isinstance(rec_plan, dict) else []
    # Check whether any job flagged in recovery_plan has since resolved to success in jobs.json
    stale_recovery_items = [
        item.get("job_id")
        for item in rec_manual
        if isinstance(item, dict)
        and str((jobs_map.get(item.get("job_id") or "") or {}).get("status", "")).lower() == "success"
    ]

    # 3. AI Provider & Key-Slot Telemetry (separating live-job telemetry from unisolated test-fixture rows)
    _REAL_PROVIDERS = {
        "gemini", "groq", "mistral", "openrouter", "llm7", "nvidia",
        "cohere", "openai", "huggingface", "pollinations", "siliconflow",
    }
    prov_summary = _read_json(root / "logs" / "provider_summary.json", {}) or {}
    prov_health = _read_json(root / "logs" / "provider_health.json", {}) or {}
    usage_path = root / "logs" / "ai_usage.jsonl"
    usage_rows = 0
    usage_ok = 0
    usage_fail = 0
    usage_rl = 0
    usage_auth_fail = 0
    live_rows = 0
    live_ok = 0
    live_fail = 0
    live_rl = 0
    live_cache = 0
    live_jobs: Dict[str, int] = defaultdict(int)
    live_by_prov: Dict[str, Dict[str, int]] = defaultdict(lambda: {"ok": 0, "fail": 0, "rate_limits": 0})
    mock_rows = 0
    if usage_path.is_file():
        for raw_ln in usage_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not raw_ln.strip():
                continue
            try:
                row = json.loads(raw_ln)
            except ValueError:
                continue
            usage_rows += 1
            is_ok = bool(row.get("ok"))
            if is_ok:
                usage_ok += 1
            else:
                usage_fail += 1
            cat = str(row.get("error_category") or row.get("detail") or "").lower()
            is_rl = "429" in cat or "rate_limit" in cat or "rate limit" in cat
            if is_rl:
                usage_rl += 1
            if "401" in cat or "403" in cat or "auth" in cat:
                usage_auth_fail += 1

            job_val = str(row.get("job") or "").strip()
            prov_val = str(row.get("provider") or "").strip().lower()
            if job_val and prov_val in _REAL_PROVIDERS:
                live_rows += 1
                live_jobs[job_val] += 1
                if is_ok:
                    live_ok += 1
                    live_by_prov[prov_val]["ok"] += 1
                else:
                    live_fail += 1
                    live_by_prov[prov_val]["fail"] += 1
                if is_rl:
                    live_rl += 1
                    live_by_prov[prov_val]["rate_limits"] += 1
                if row.get("cache_hit"):
                    live_cache += 1
            else:
                mock_rows += 1

    # 4. PDF QA Telemetry (logs/qa/*_qa.json)
    qa_dir = root / "logs" / "qa"
    qa_reports: List[Dict[str, Any]] = []
    if qa_dir.is_dir():
        for qpath in sorted(qa_dir.glob("*_qa.json")):
            qdata = _read_json(qpath)
            if not isinstance(qdata, dict):
                continue
            qa_reports.append({
                "job_id": str(qdata.get("job_id") or qpath.stem.replace("_qa", "")),
                "passed": bool(qdata.get("passed")),
                "page_count": qdata.get("page_count"),
                "substantive_pages": qdata.get("substantive_pages"),
                "blank_pages_count": len(qdata.get("blank_pages") or []),
                "near_empty_pages_count": len(qdata.get("near_empty_pages") or []),
                "hindi_pct": qdata.get("hindi_pct"),
                "mcq_count": qdata.get("mcq_count"),
                "duplicate_questions": qdata.get("duplicate_questions"),
                "image_xobjects": qdata.get("image_xobjects"),
                "issue_count": len(qdata.get("issues") or []),
                "checked_at": qdata.get("checked_at"),
            })

    qa_total = len(qa_reports)
    qa_passed = sum(1 for r in qa_reports if r["passed"])
    hindi_vals = [float(r["hindi_pct"]) for r in qa_reports if isinstance(r.get("hindi_pct"), (int, float))]
    page_vals = [int(r["page_count"]) for r in qa_reports if isinstance(r.get("page_count"), int)]

    # 5. Publication Ledger Accuracy (state/published_events.json)
    ledger = _read_json(root / "state" / "published_events.json", {}) or {}
    records = ledger.get("records") if isinstance(ledger, dict) else {}
    if not isinstance(records, dict):
        records = {}
    pub_success = 0
    pub_by_job_hashes: Dict[str, List[str]] = defaultdict(list)
    pub_with_sha = 0
    for rec in records.values():
        if not isinstance(rec, dict):
            continue
        sha_val = str(rec.get("file_sha256") or rec.get("file_hash") or "")
        if sha_val:
            pub_with_sha += 1
        if str(rec.get("status") or "").lower() == "success":
            pub_success += 1
            jid = str(rec.get("job_id") or "")
            if jid:
                pub_by_job_hashes[jid].append(sha_val)
    same_hash_duplicates = {
        k: len(v)
        for k, v in pub_by_job_hashes.items()
        if len(v) > 1 and len(set(v)) < len(v)
    }
    revision_live_sends = {
        k: len(v)
        for k, v in pub_by_job_hashes.items()
        if len(v) > 1 and len(set(v)) == len(v)
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workflows": workflows_out,
        "failure_by_stage": dict(failure_by_stage),
        "unresolved_jobs": unresolved_jobs,
        "auto_heal": {
            "total_incidents": len(incidents),
            "by_status": dict(heal_status_counts),
            "by_category": dict(heal_category_counts),
            "recovery_plan_manual_attention": [
                {"job_id": i.get("job_id"), "reason": i.get("reason")}
                for i in rec_manual
                if isinstance(i, dict)
            ],
            "stale_recovery_plan_jobs": stale_recovery_items,
        },
        "ai_observability": {
            "usage_log_rows": usage_rows,
            "usage_ok": usage_ok,
            "usage_fail": usage_fail,
            "usage_rate_limits": usage_rl,
            "usage_auth_failures": usage_auth_fail,
            "live_job_rows": live_rows,
            "live_job_ok": live_ok,
            "live_job_fail": live_fail,
            "live_job_rate_limits": live_rl,
            "live_job_cache_hits": live_cache,
            "live_jobs_recorded": dict(live_jobs),
            "live_by_provider": {k: dict(v) for k, v in sorted(live_by_prov.items())},
            "test_fixture_rows": mock_rows,
            "provider_summary_snapshot": prov_summary,
            "provider_health_snapshot": prov_health,
        },
        "pdf_qa": {
            "reports_count": qa_total,
            "passed_count": qa_passed,
            "failed_count": qa_total - qa_passed,
            "pass_rate_pct": round((qa_passed / qa_total) * 100.0, 2) if qa_total else 0.0,
            "mean_pages": round(sum(page_vals) / len(page_vals), 2) if page_vals else None,
            "mean_hindi_pct": round(sum(hindi_vals) / len(hindi_vals), 2) if hindi_vals else None,
            "blank_page_alerts": sum(1 for r in qa_reports if r["blank_pages_count"] > 0),
            "near_empty_page_alerts": sum(1 for r in qa_reports if r["near_empty_pages_count"] > 0),
            "editions": qa_reports,
        },
        "publication_ledger": {
            "total_records": len(records),
            "live_success_records": pub_success,
            "records_with_hash": pub_with_sha,
            "same_hash_duplicate_live_sends": same_hash_duplicates,
            "distinct_hash_revisions": revision_live_sends,
        },
        "jobs": job_rows,
    }


def render_dashboard_markdown(health: Dict[str, Any]) -> str:
    lines: List[str] = [
        "# Production Health Dashboard",
        "",
        f"**Generated At (UTC):** `{health['generated_at']}`  ",
        "**Data Sources:** `state/jobs.json`, `state/published_events.json`, `state/healing_history.json`, `recovery_plan.json`, `logs/qa/*_qa.json`, `logs/ai_usage.jsonl`, `logs/provider_health.json`, `logs/provider_summary.json`",
        "",
        "---",
        "",
        "## 1. Workflow Execution Summary",
        "",
        "| Workflow | Total | Success | Failed | Pending / Other | Success Rate | Multi-Attempt Recovered | Mean 1-Attempt Duration (s) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for jt, row in health["workflows"].items():
        dur = "-" if row["mean_single_attempt_duration_sec"] is None else f"{row['mean_single_attempt_duration_sec']:.1f}"
        lines.append(
            f"| `{jt}` | {row['total_runs']} | {row['success_runs']} | {row['failed_runs']} | "
            f"{row['pending_or_other_runs']} | {row['success_rate_pct']}% | "
            f"{row['multi_attempt_recovered']} | {dur} |"
        )

    lines += ["", "## 2. Failures by Stage & Unresolved Escalations", ""]
    if health["failure_by_stage"]:
        lines += ["| Workflow : Stage | Count |", "|---|---:|"]
        for k, v in sorted(health["failure_by_stage"].items()):
            lines.append(f"| `{k}` | {v} |")
    else:
        lines.append("- None recorded in `state/jobs.json`.")

    lines.append("")
    if health["unresolved_jobs"]:
        lines += ["### Currently Failed Jobs in `state/jobs.json`", ""]
        for j in health["unresolved_jobs"]:
            lines.append(
                f"- `{j['job_id']}`: status=`{j['status']}`, attempts=`{j['attempts']}`, "
                f"failed_stage=`{j['failed_stage']}`, updated=`{j['updated_at']}`"
            )
    else:
        lines.append("- No jobs currently marked `failed` in `state/jobs.json`.")

    ah = health["auto_heal"]
    lines += [
        "",
        "## 3. Auto-Heal & Recovery Telemetry",
        "",
        f"- **Total Logged Healing Incidents (`state/healing_history.json`):** `{ah['total_incidents']}`",
        f"- **By Status:** `{json.dumps(ah['by_status'], ensure_ascii=False)}`",
        f"- **By Category:** `{json.dumps(ah['by_category'], ensure_ascii=False)}`",
        f"- **Active Manual-Attention Queue (`recovery_plan.json`):** `{json.dumps(ah['recovery_plan_manual_attention'], ensure_ascii=False)}`",
        f"- **Stale `recovery_plan.json` Entries (Now `success` in `jobs.json`):** `{ah['stale_recovery_plan_jobs']}`",
        "",
        "## 4. AI Provider & Key-Slot Observability",
        "",
    ]
    ai = health["ai_observability"]
    lines += [
        f"- **Logged Live-Job Calls (`logs/ai_usage.jsonl` with real `job` & provider):** `{ai['live_job_rows']}` (`ok={ai['live_job_ok']}`, `fail={ai['live_job_fail']}`, `429/rate_limit={ai['live_job_rate_limits']}`, `cache_hits={ai['live_job_cache_hits']}`, jobs=`{list(ai['live_jobs_recorded'].keys())}`)",
        f"- **Historical Test-Fixture / Unscoped Rows Separated From Live Telemetry:** `{ai['test_fixture_rows']}` (of `{ai['usage_log_rows']}` total rows)",
        f"- **Live Provider Breakdown (`logs/ai_usage.jsonl`):** `{json.dumps(ai['live_by_provider'], ensure_ascii=False)}`",
    ]
    prov_snap = (ai.get("provider_health_snapshot") or {}).get("providers") or {}
    if prov_snap:
        lines += [
            "",
            "| Provider | Slots | Active Model | Available | Shared Quota Flag |",
            "|---|---:|---|---|---|",
        ]
        for pname, pinfo in sorted(prov_snap.items()):
            lines.append(
                f"| `{pname}` | {pinfo.get('configured_slots', 0)} | `{pinfo.get('active_model') or '-'}` | "
                f"`{pinfo.get('available')}` | `{pinfo.get('shared_quota_suspected')}` |"
            )

    pqa = health["pdf_qa"]
    lines += [
        "",
        "## 5. PDF QA Metrics (`logs/qa/*_qa.json`)",
        "",
        f"- **Saved QA Reports:** `{pqa['reports_count']}` (`passed={pqa['passed_count']}`, `failed={pqa['failed_count']}`, `pass_rate={pqa['pass_rate_pct']}%`)",
        f"- **Mean Pages:** `{pqa['mean_pages']}` | **Mean Devanagari Coverage:** `{pqa['mean_hindi_pct']}%`",
        f"- **Blank Page Alerts:** `{pqa['blank_page_alerts']}` | **Near-Empty Page Alerts:** `{pqa['near_empty_page_alerts']}`",
        "",
        "| Edition | QA Passed | Pages | Substantive | Hindi % | MCQs | Images | Near-Empty | Issues |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for ed in pqa["editions"]:
        lines.append(
            f"| `{ed['job_id']}` | `{ed['passed']}` | {ed['page_count']} | {ed['substantive_pages']} | "
            f"{ed['hindi_pct']} | {ed['mcq_count']} | {ed['image_xobjects']} | "
            f"{ed['near_empty_pages_count']} | {ed['issue_count']} |"
        )

    pub = health["publication_ledger"]
    lines += [
        "",
        "## 6. Telegram Publication Ledger (`state/published_events.json`)",
        "",
        f"- **Total Records:** `{pub['total_records']}` | **Live Success Sends:** `{pub['live_success_records']}` | **With Artifact Hash:** `{pub['records_with_hash']}`",
        f"- **Same-Hash Duplicate Live Sends:** `{pub['same_hash_duplicate_live_sends']}`",
        f"- **Distinct-Hash Revision Sends:** `{pub['distinct_hash_revisions']}`",
        "",
    ]
    return "\n".join(lines)


def write_outputs(
    health: Dict[str, Any],
    *,
    json_path: Path,
    csv_path: Path,
    md_path: Path,
) -> None:
    write_json_atomic(json_path, health)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_csv = csv_path.with_suffix(".csv.tmp")
    with tmp_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "job_id", "job_type", "status", "attempts",
                "last_success_stage", "failed_stage", "duration_sec", "updated_at",
            ],
        )
        writer.writeheader()
        for row in health["jobs"]:
            writer.writerow(row)
    os.replace(tmp_csv, csv_path)

    md_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_md = md_path.with_suffix(".md.tmp")
    tmp_md.write_text(render_dashboard_markdown(health), encoding="utf-8")
    os.replace(tmp_md, md_path)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate centralized production health reports.")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--json", default="")
    parser.add_argument("--csv", default="")
    parser.add_argument("--md", default="")
    args = parser.parse_args(argv)

    root = Path(args.root)
    json_path = Path(args.json) if args.json else (root / "reports" / "production_health.json")
    csv_path = Path(args.csv) if args.csv else (root / "reports" / "production_health.csv")
    md_path = Path(args.md) if args.md else (root / "docs" / "PRODUCTION_HEALTH_DASHBOARD.md")

    health = collect_production_health(root)
    write_outputs(health, json_path=json_path, csv_path=csv_path, md_path=md_path)
    print(f"Wrote production health dashboard to {md_path}, {json_path}, {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
