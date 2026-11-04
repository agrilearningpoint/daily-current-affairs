#!/usr/bin/env python3
"""Fetch the published daily editions' content + MCQ JSON for a weekly/monthly edition.

``data/`` is gitignored, so each daily edition's content and MCQs live only in
that run's ``pipeline-checkpoints`` artifact (30-day retention).  state/jobs.json
records ``checkpoint_run_id`` for every daily job.  For each day of the period
this script downloads that artifact through the GitHub API (GITHUB_TOKEN with
``actions: read``) and writes one compact file per day:

    data/period_sources/daily_<YYYY-MM-DD>.json  ->  {date, job_id, source_run_id, content, mcqs}

Those files sit under data/, so they are uploaded with the weekly run's own
``pipeline-checkpoints`` artifact.  The monthly run uses them as a fallback:
for any day whose daily artifact has expired it looks in the weekly runs'
artifacts for the packed copy.

Fail-soft: a missing/expired/unreadable day is skipped and reported.  The
period builder (stage 20/21) fails the weekly/monthly edition when fewer than
3 (weekly) / 10 (monthly) days are available; the daily workflow never runs
this script.  Pass --strict to exit 1 here instead.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import zipfile
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ARTIFACT_NAME = "pipeline-checkpoints"
MIN_DAYS = {"weekly": 3, "monthly": 10}
PUBLISHED_STAGES = {"22_telegram_publisher", "23_telegram_pin_verifier", "24_final_health_audit"}


class GitHub:
    def __init__(self, repo: str, token: str, api: str = "https://api.github.com", session=None):
        import requests
        self.repo, self.api = repo, api.rstrip("/")
        self.s = session or requests.Session()
        self.s.headers.update({"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
        if token:
            self.s.headers["Authorization"] = f"Bearer {token}"

    def run_artifact(self, run_id: str) -> Optional[Dict[str, Any]]:
        r = self.s.get(f"{self.api}/repos/{self.repo}/actions/runs/{run_id}/artifacts",
                       params={"name": ARTIFACT_NAME, "per_page": 20}, timeout=30)
        if r.status_code != 200:
            return None
        arts = [a for a in r.json().get("artifacts") or [] if a.get("name") == ARTIFACT_NAME and not a.get("expired")]
        return arts[0] if arts else None

    def download(self, artifact: Dict[str, Any]) -> Optional[zipfile.ZipFile]:
        # requests drops the Authorization header on the cross-host redirect to blob storage.
        r = self.s.get(artifact["archive_download_url"], timeout=120, allow_redirects=True)
        if r.status_code != 200:
            return None
        try:
            return zipfile.ZipFile(io.BytesIO(r.content))
        except zipfile.BadZipFile:
            return None


def period_dates(job_type: str, job_date: str) -> List[str]:
    from pipeline.period_builder import period_dates as _pd
    return _pd(job_type, job_date)


def load_jobs(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    jobs = data.get("jobs", data) if isinstance(data, dict) else {}
    return jobs if isinstance(jobs, dict) else {}


def is_published(job: Dict[str, Any]) -> bool:
    return isinstance(job, dict) and (job.get("status") == "success"
                                      or job.get("last_success_stage") in PUBLISHED_STAGES)


def _run_id(job: Dict[str, Any]) -> str:
    rid = str(job.get("checkpoint_run_id") or job.get("github_run_id") or "")
    return rid if rid.isdigit() else ""


def _member(zf: zipfile.ZipFile, *names: str) -> Any:
    have = set(zf.namelist())
    for n in names:
        for cand in (n, n.lstrip("./")):
            if cand in have:
                try:
                    return json.loads(zf.read(cand).decode("utf-8"))
                except ValueError:
                    return None
    return None


def extract_daily(zf: zipfile.ZipFile, day: str) -> Optional[Dict[str, Any]]:
    """Content + MCQs of daily_<day> from a daily run's checkpoint artifact."""
    job = f"daily_{day}"
    content = _member(zf, f"data/content/{job}.json")
    if not isinstance(content, dict) or not isinstance(content.get("items"), list):
        return None
    mcq = _member(zf, f"data/mcq/{job}.json", f"data/content/mcqs_{job}.json")
    mcqs = mcq.get("mcqs", []) if isinstance(mcq, dict) else (mcq if isinstance(mcq, list) else [])
    return {"date": day, "job_id": job, "content": content, "mcqs": mcqs}


def extract_packed(zf: zipfile.ZipFile, day: str) -> Optional[Dict[str, Any]]:
    """The compact copy a weekly run saved (data/period_sources/daily_<day>.json)."""
    packed = _member(zf, f"data/period_sources/daily_{day}.json")
    return packed if isinstance(packed, dict) and isinstance(packed.get("content"), dict) else None


def _write(out_dir: Path, packed: Dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = out_dir / f".daily_{packed['date']}.json.tmp"
    tmp.write_text(json.dumps(packed, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, out_dir / f"daily_{packed['date']}.json")


def fetch(job_type: str, job_date: str, gh: GitHub, jobs: Dict[str, Any], out_dir: Path) -> Dict[str, Any]:
    dates = period_dates(job_type, job_date)
    report: Dict[str, Any] = {"type": job_type, "date": job_date, "period": [dates[0], dates[-1]],
                              "found": [], "from_weekly": [], "already_present": [], "missing": {}}
    pending: List[str] = []
    for d in dates:
        if (out_dir / f"daily_{d}.json").is_file():
            report["already_present"].append(d)
            continue
        job = jobs.get(f"daily_{d}")
        if not is_published(job or {}):
            report["missing"][d] = "no published daily job"
            pending.append(d)
            continue
        rid = _run_id(job)
        art = gh.run_artifact(rid) if rid else None
        zf = gh.download(art) if art else None
        packed = extract_daily(zf, d) if zf else None
        if packed is None:
            report["missing"][d] = "artifact expired/unavailable" if not zf else "content not in artifact"
            pending.append(d)
            continue
        packed["source_run_id"] = rid
        _write(out_dir, packed)
        report["found"].append(d)

    # Fallback: compact copies saved in weekly runs' artifacts (monthly after daily artifacts expire).
    if pending:
        first, last = date.fromisoformat(dates[0]), date.fromisoformat(dates[-1]) + timedelta(days=6)
        weekly = sorted((k for k in jobs if k.startswith("weekly_")
                         and first.isoformat() <= k[len("weekly_"):] <= last.isoformat()), reverse=True)
        for wk in weekly:
            if not pending:
                break
            rid = _run_id(jobs[wk])
            art = gh.run_artifact(rid) if rid else None
            zf = gh.download(art) if art else None
            if zf is None:
                continue
            for d in list(pending):
                packed = extract_packed(zf, d)
                if packed is not None:
                    packed["source_run_id"] = packed.get("source_run_id") or rid
                    packed["via_weekly_run"] = rid
                    _write(out_dir, packed)
                    report["from_weekly"].append(d)
                    report["missing"].pop(d, None)
                    pending.remove(d)
    report["available"] = len(report["found"]) + len(report["from_weekly"]) + len(report["already_present"])
    report["min_required"] = MIN_DAYS.get(job_type, 1)
    return report


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--type", required=True, choices=sorted(MIN_DAYS))
    ap.add_argument("--date", required=True, help="edition date YYYY-MM-DD (IST)")
    ap.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY", ""))
    ap.add_argument("--jobs", default=str(ROOT / "state" / "jobs.json"))
    ap.add_argument("--out", default=str(ROOT / "data" / "period_sources"))
    ap.add_argument("--strict", action="store_true", help="exit 1 when fewer than the minimum days are found")
    args = ap.parse_args(argv)
    date.fromisoformat(args.date)
    token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN") or ""
    if not args.repo or not token:
        print("fetch_daily_editions: GITHUB_REPOSITORY/GITHUB_TOKEN missing; nothing fetched", file=sys.stderr)
        return 1 if args.strict else 0
    gh = GitHub(args.repo, token, os.getenv("GITHUB_API_URL", "https://api.github.com"))
    report = fetch(args.type, args.date, gh, load_jobs(Path(args.jobs)), Path(args.out))
    print(json.dumps(report, indent=1))
    ok = report["available"] >= report["min_required"]
    if not ok:
        print(f"fetch_daily_editions: only {report['available']} day(s) available "
              f"(min {report['min_required']}); the {args.type} edition will fail at the period builder",
              file=sys.stderr)
    return 1 if (args.strict and not ok) else 0


if __name__ == "__main__":
    sys.exit(main())
