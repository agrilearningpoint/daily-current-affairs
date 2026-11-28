# -*- coding: utf-8 -*-
"""
BOUNDED SELF-IMPROVEMENT & TELEMETRY LEARNING ENGINE (Phase 12)
===============================================================
Analyzes accumulated pipeline execution telemetry across:
  - state/jobs.json (stage failures, retries, durations)
  - logs/qa/*_qa.json (recurring warnings/errors, Hindi coverage, MCQ variety)
  - logs/ai_usage.jsonl (provider success rates, latency, rate-limit hotspots)

Produces non-destructive, strictly bounded operational guidance in:
  - state/metrics/self_improvement_recommendations.json
  - state/metrics/learning_history.json

Never modifies source code or weakens fail-closed editorial/factual gates.
"""
from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("pipeline.self_improvement")
ROOT = Path(__file__).resolve().parent.parent


def _read_json(path: Path, default: Any) -> Any:
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    return default


def analyze_history(repo_root: Optional[Path] = None, max_qa: int = 30) -> Dict[str, Any]:
    """Inspect historical jobs, QA reports, and AI usage to synthesize actionable hints."""
    root = Path(repo_root or ROOT)
    jobs_doc = _read_json(root / "state" / "jobs.json", {})
    jobs = jobs_doc.get("jobs", jobs_doc) if isinstance(jobs_doc, dict) else {}
    if not isinstance(jobs, dict):
        jobs = {}

    failed_stages: Counter[str] = Counter()
    success_jobs = 0
    failed_jobs = 0
    for j in jobs.values():
        if not isinstance(j, dict):
            continue
        st = str(j.get("status") or "")
        if st == "success":
            success_jobs += 1
        elif st == "failed":
            failed_jobs += 1
            fs = str(j.get("failed_stage") or "unknown")
            failed_stages[fs] += 1

    # QA issue trends
    qa_issues: Counter[str] = Counter()
    hindi_pcts: List[float] = []
    qa_dir = root / "logs" / "qa"
    if qa_dir.is_dir():
        qa_files = sorted(qa_dir.glob("*_qa.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:max_qa]
        for qf in qa_files:
            qdata = _read_json(qf, {})
            if not isinstance(qdata, dict):
                continue
            if isinstance(qdata.get("hindi_pct"), (int, float)):
                hindi_pcts.append(float(qdata["hindi_pct"]))
            for iss in qdata.get("issues") or []:
                if isinstance(iss, dict) and iss.get("code"):
                    qa_issues[str(iss["code"])] += 1

    # AI usage telemetry trends
    prov_calls: Counter[str] = Counter()
    prov_failures: Counter[str] = Counter()
    for cand_path in (root / "state" / "metrics" / "ai_usage.jsonl", root / "logs" / "ai_usage.jsonl"):
        if cand_path.is_file():
            try:
                lines = cand_path.read_text(encoding="utf-8", errors="replace").splitlines()[-500:]
                for ln in lines:
                    if not ln.strip():
                        continue
                    try:
                        rec = json.loads(ln)
                        p = str(rec.get("provider") or "unknown")
                        prov_calls[p] += 1
                        if rec.get("success") is False or rec.get("status") == "error":
                            prov_failures[p] += 1
                    except ValueError:
                        continue
            except OSError:
                pass
            break

    recommendations: List[Dict[str, str]] = []
    for stage, count in failed_stages.most_common(3):
        recommendations.append({
            "area": "reliability",
            "target": stage,
            "priority": "high" if count >= 3 else "medium",
            "action": f"Stage '{stage}' failed {count} time(s); review retry/timeout budget in config/supervisor_policy.json.",
        })
    for code, count in qa_issues.most_common(5):
        recommendations.append({
            "area": "editorial_qa",
            "target": code,
            "priority": "high" if count >= 3 else "low",
            "action": f"QA issue '{code}' appeared in {count} recent edition(s); tighten upstream filter/repair rule.",
        })
    for prov, fails in prov_failures.most_common(3):
        calls = max(1, prov_calls[prov])
        rate = fails / calls
        if rate >= 0.35 and calls >= 5:
            recommendations.append({
                "area": "ai_routing",
                "target": prov,
                "priority": "medium",
                "action": f"Provider '{prov}' failure rate {rate:.0%} ({fails}/{calls}); check quota/key pool or model preference.",
            })

    avg_hi = round(sum(hindi_pcts) / len(hindi_pcts), 2) if hindi_pcts else 0.0
    total_jobs = success_jobs + failed_jobs
    reliability_pct = round(100.0 * success_jobs / total_jobs, 1) if total_jobs else 100.0

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "jobs_analyzed": total_jobs,
        "success_jobs": success_jobs,
        "failed_jobs": failed_jobs,
        "reliability_pct": reliability_pct,
        "avg_hindi_coverage_pct": avg_hi,
        "top_failed_stages": dict(failed_stages.most_common(5)),
        "top_qa_issues": dict(qa_issues.most_common(8)),
        "provider_calls": dict(prov_calls),
        "provider_failures": dict(prov_failures),
        "recommendations": recommendations,
    }


def record_learning_cycle(
    job_id: str,
    repo_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Run history analysis and persist bounded recommendations & cycle log atomically."""
    from pipeline.persistence import write_json_atomic
    root = Path(repo_root or ROOT)
    metrics_dir = root / "state" / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)

    summary = analyze_history(root)
    summary["last_job_id"] = job_id

    rec_path = metrics_dir / "self_improvement_recommendations.json"
    write_json_atomic(rec_path, summary)

    hist_path = metrics_dir / "learning_history.json"
    hist = _read_json(hist_path, {"cycles": []})
    if not isinstance(hist, dict) or not isinstance(hist.get("cycles"), list):
        hist = {"cycles": []}
    hist["cycles"].append({
        "job_id": job_id,
        "recorded_at": summary["generated_at"],
        "reliability_pct": summary["reliability_pct"],
        "recommendation_count": len(summary["recommendations"]),
    })
    hist["cycles"] = hist["cycles"][-60:]
    write_json_atomic(hist_path, hist)
    return summary
