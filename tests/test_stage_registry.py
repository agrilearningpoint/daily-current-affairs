"""Enforce exact 1:1 registry parity across main.py, config/workflow.py, checkpoints, and supervisor policy."""

from __future__ import annotations

import json
from pathlib import Path

import config.workflow as workflow
import main
from pipeline import checkpoints

ROOT = Path(__file__).resolve().parents[1]


def test_workflow_matches_main_stages_exactly():
    assert workflow.DAILY_AGENTS == [n for n, _, _ in main.DAILY_STAGES]
    assert workflow.WEEKLY_AGENTS == [n for n, _, _ in main.WEEKLY_STAGES]
    assert workflow.MONTHLY_AGENTS == [n for n, _, _ in main.MONTHLY_STAGES]
    assert workflow.WORKFLOWS_BY_TYPE["daily"] == workflow.DAILY_AGENTS
    assert workflow.WORKFLOWS_BY_TYPE["weekly"] == workflow.WEEKLY_AGENTS
    assert workflow.WORKFLOWS_BY_TYPE["monthly"] == workflow.MONTHLY_AGENTS


def test_supervisor_policy_and_checkpoints_cover_every_stage():
    policy = json.loads((ROOT / "config" / "supervisor_policy.json").read_text(encoding="utf-8"))
    contracts = policy["stage_contracts"]
    all_stages = set(workflow.WORKFLOW_ORDER)
    assert all_stages <= set(contracts), f"missing supervisor contracts: {all_stages - set(contracts)}"
    assert (ROOT / "agents" / "26_master_supervisor.py").is_file()
    for stage_name in checkpoints.STAGE_FILES:
        assert stage_name in contracts
    assert "03_news_collection" not in workflow.DAILY_AGENTS
    assert "00 MODEL ORCHESTRATOR" in workflow.PIPELINE_FLOW
    assert "26 MASTER SUPERVISOR RELEASE GATE" in workflow.PIPELINE_FLOW
