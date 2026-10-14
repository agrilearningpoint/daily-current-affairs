# -*- coding: utf-8 -*-
"""
Agent Context — Canonical Job Context for All Agents
=====================================================
Single source of truth for job_id, job_type, job_date across all agents.

main.py sets these env vars before spawning each agent subprocess:
    ALP_JOB_ID         — "daily_2026-10-14"
    ALP_JOB_TYPE       — "daily" | "weekly" | "monthly"
    ALP_JOB_DATE       — "2026-10-14"
    ALP_OUTPUT_PREFIX  — same as ALP_JOB_ID
    ALP_STAGE_ID       — current stage id (e.g. "03_news_collection")

Every agent imports this to get a JobContext object and derive paths.

Canonical artifact paths:
    data/raw/{job_id}.json
    data/verified/{job_id}.json
    data/dedup/{job_id}.json
    data/scored/{job_id}.json
    data/selected/{job_id}.json
    data/content/{job_id}.json
    data/mcq/{job_id}.json
    data/mcq/{job_id}_validated.json
    output/{job_id}.pdf
    logs/qa/{job_id}_qa.json

Legacy paths (for backward compat during migration):
    data/raw/news_{date}.json
    data/verified/verified_{date}.json
    data/content/content_{date}.json
    data/mcq/mcq_{date}.json
    output/daily_{date}.pdf

Agents write BOTH canonical + legacy (dual-write) during migration period.
Once all workflows use canonical paths, legacy can be removed.

Usage:
    from pipeline.agent_context import get_context

    ctx = get_context()
    print(ctx.job_id, ctx.job_type, ctx.job_date)

    input_file = ctx.input_path("raw")
    output_file = ctx.output_path("verified")
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("pipeline.agent_context")

# --------------------------------------------------------------------------- #
# Repo root (this file is at pipeline/agent_context.py)
# --------------------------------------------------------------------------- #
REPO_ROOT = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------- #
# Legacy prefix map — for dual-write compatibility
# --------------------------------------------------------------------------- #
LEGACY_PREFIX = {
    "raw": "news_",
    "verified": "verified_",
    "dedup": "dedup_",
    "scored": "scored_",
    "selected": "selected_",
    "content": "content_",
    "mcq": "mcq_",
}


# --------------------------------------------------------------------------- #
# JobContext
# --------------------------------------------------------------------------- #
@dataclass
class JobContext:
    """
    Canonical job context — shared by all agents.
    """
    job_id: str
    job_type: str
    job_date: str
    output_prefix: str
    stage_id: Optional[str] = None
    repo_root: Path = field(default_factory=lambda: REPO_ROOT)

    # ----------------------------------------------------------------------- #
    # Canonical path helpers
    # ----------------------------------------------------------------------- #
    def data_dir(self, stage: str) -> Path:
        """
        Base data directory for a stage.
        e.g. data_dir('raw') → <repo>/data/raw
        """
        return self.repo_root / "data" / stage

    def input_path(self, stage: str, suffix: str = ".json") -> Path:
        """
        Canonical input path: data/{stage}/{job_id}{suffix}
        """
        return self.data_dir(stage) / f"{self.job_id}{suffix}"

    def output_path(self, stage: str, suffix: str = ".json") -> Path:
        """
        Canonical output path: data/{stage}/{job_id}{suffix}
        (same as input_path — agents typically overwrite stage outputs)
        """
        return self.data_dir(stage) / f"{self.job_id}{suffix}"

    def legacy_path(self, stage: str, suffix: str = ".json") -> Optional[Path]:
        """
        Legacy alias path: data/{stage}/{prefix}{date}{suffix}
        Returns None if no legacy prefix configured for stage.
        """
        prefix = LEGACY_PREFIX.get(stage)
        if not prefix:
            return None
        return self.data_dir(stage) / f"{prefix}{self.job_date}{suffix}"

    def output_dir(self, name: str = "output") -> Path:
        """Top-level output dir (e.g. 'output')."""
        return self.repo_root / name

    def pdf_path(self) -> Path:
        """Canonical PDF output: output/{job_id}.pdf"""
        return self.output_dir("output") / f"{self.job_id}.pdf"

    def pdf_path_legacy(self) -> Path:
        """Legacy PDF: output/{job_type}_{date}.pdf (same as canonical since job_id includes type+date)."""
        return self.output_dir("output") / f"{self.job_id}.pdf"

    def qa_report_path(self) -> Path:
        """Canonical QA report: logs/qa/{job_id}_qa.json"""
        return self.repo_root / "logs" / "qa" / f"{self.job_id}_qa.json"

    def state_dir(self) -> Path:
        return self.repo_root / "state"

    def logs_dir(self) -> Path:
        return self.repo_root / "logs"

    # ----------------------------------------------------------------------- #
    # Input discovery (canonical first, legacy fallback, latest fallback)
    # ----------------------------------------------------------------------- #
    def find_input(self, stage: str, suffix: str = ".json") -> Optional[Path]:
        """
        Robustly find input file for a stage:
        1. Canonical:    data/{stage}/{job_id}{suffix}
        2. Legacy:       data/{stage}/{prefix}{date}{suffix}
        3. Latest file:  newest *.json in data/{stage}/
        Returns None if nothing found.
        """
        # 1. Canonical
        canonical = self.input_path(stage, suffix)
        if canonical.exists():
            return canonical

        # 2. Legacy
        legacy = self.legacy_path(stage, suffix)
        if legacy and legacy.exists():
            return legacy

        # 3. Latest file in directory (last resort for dev/testing)
        d = self.data_dir(stage)
        if d.exists():
            candidates = sorted(
                [p for p in d.glob(f"*{suffix}") if p.is_file()],
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if candidates:
                logger.debug(
                    "No canonical/legacy input for %s — using latest: %s",
                    stage, candidates[0].name,
                )
                return candidates[0]

        return None

    # ----------------------------------------------------------------------- #
    # Debug
    # ----------------------------------------------------------------------- #
    def describe(self) -> str:
        return (
            f"JobContext(job_id={self.job_id}, type={self.job_type}, "
            f"date={self.job_date}, stage={self.stage_id})"
        )


# --------------------------------------------------------------------------- #
# get_context — read env vars, build JobContext
# --------------------------------------------------------------------------- #
def get_context(stage_id: Optional[str] = None) -> JobContext:
    """
    Load job context from environment variables.

    Falls back to safe defaults for standalone runs (dev/testing):
    - If ALP_JOB_ID missing, builds "daily_{today}"
    - If ALP_JOB_TYPE missing, defaults to "daily"
    - If ALP_JOB_DATE missing, uses today UTC or extracts from job_id
    """
    job_id = (os.getenv("ALP_JOB_ID") or os.getenv("JOB_ID") or "").strip()
    job_type = (os.getenv("ALP_JOB_TYPE") or os.getenv("JOB_TYPE") or "").strip()
    job_date = (os.getenv("ALP_JOB_DATE") or "").strip()
    output_prefix = (os.getenv("ALP_OUTPUT_PREFIX") or "").strip()
    env_stage = (os.getenv("ALP_STAGE_ID") or "").strip()

    # Infer date from job_id
    if not job_date and job_id and "_" in job_id:
        job_date = job_id.split("_", 1)[1]

    # Infer type from job_id
    if not job_type and job_id:
        for t in ("daily", "weekly", "monthly"):
            if job_id.startswith(f"{t}_"):
                job_type = t
                break

    # Defaults
    if not job_type:
        job_type = "daily"

    if not job_date:
        job_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if not job_id:
        job_id = f"{job_type}_{job_date}"

    if not output_prefix:
        output_prefix = job_id

    ctx = JobContext(
        job_id=job_id,
        job_type=job_type,
        job_date=job_date,
        output_prefix=output_prefix,
        stage_id=stage_id or env_stage or None,
    )

    logger.debug("Loaded %s", ctx.describe())
    return ctx


# --------------------------------------------------------------------------- #
# Convenience for agents — main wrapper
# --------------------------------------------------------------------------- #
def agent_main(agent_fn, stage_id: Optional[str] = None) -> int:
    """
    Standard wrapper for agent entry points.

    Usage:
        if __name__ == "__main__":
            from pipeline.agent_context import agent_main
            sys.exit(agent_main(main))

    Where main() has signature: def main(ctx: JobContext) -> int
    """
    ctx = get_context(stage_id=stage_id)
    logger.info("Starting %s", ctx.describe())
    try:
        return agent_fn(ctx)
    except Exception:
        logger.exception("Agent failed")
        return 1


# --------------------------------------------------------------------------- #
# Smoke test
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ctx = get_context()
    print("Context:", ctx.describe())
    print()
    print("Canonical paths:")
    for stage in ("raw", "verified", "dedup", "scored", "selected", "content", "mcq"):
        print(f"  {stage:12s} → {ctx.input_path(stage)}")
    print()
    print("Special paths:")
    print(f"  pdf            → {ctx.pdf_path()}")
    print(f"  qa_report      → {ctx.qa_report_path()}")
    print()
    print("Legacy paths:")
    for stage in ("raw", "verified", "content", "mcq"):
        lp = ctx.legacy_path(stage)
        print(f"  {stage:12s} → {lp}")
