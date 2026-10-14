"""Regression coverage for the State File Load Test and runtime state reader."""

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

import main


@pytest.fixture
def state_file(tmp_path, monkeypatch):
    path = tmp_path / "jobs.json"
    monkeypatch.setattr(main, "JOBS_STATE_PATH", path)
    return path


@pytest.mark.parametrize("wrapped", [False, True])
def test_load_both_formats_preserves_history(state_file, wrapped):
    jobs = {
        "daily_2026-10-14": {
            "status": "running",
            "last_success_stage": "05_deduplication",
        },
        "weekly_2026-10-11": {
            "status": "FAILED_FINAL",
            "job_type": "weekly",
            "error": "historical failure",
        },
    }
    data = {"jobs": jobs, "version": 1} if wrapped else jobs
    original = json.dumps(data)
    state_file.write_text(original, encoding="utf-8")

    assert main.load_jobs_state(strict=True) == jobs
    assert state_file.read_text(encoding="utf-8") == original


@pytest.mark.parametrize("data", [{}, {"jobs": {}, "version": 1}])
def test_empty_state_is_valid(state_file, data):
    state_file.write_text(json.dumps(data), encoding="utf-8")
    assert main.load_jobs_state(strict=True) == {}


@pytest.mark.parametrize(
    "data",
    [
        [],
        None,
        "not an object",
        {"jobs": []},
        {"jobs": None},
        {"daily_2026-10-14": []},
        {"jobs": {"daily_2026-10-14": None}},
        {"daily_2026-10-14": {}},
        {"daily_2026-10-14": {"status": 1}},
        {"daily_2026-10-14": {"status": "  "}},
    ],
)
def test_strict_load_rejects_invalid_state(state_file, data):
    state_file.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        main.load_jobs_state(strict=True)


def test_strict_load_rejects_invalid_json(state_file):
    state_file.write_text("{invalid", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        main.load_jobs_state(strict=True)


def test_runtime_warns_on_invalid_state(state_file, capsys):
    state_file.write_text("[]", encoding="utf-8")
    assert main.load_jobs_state() == {}
    assert "starting fresh state" in capsys.readouterr().err


def test_missing_state_is_allowed(state_file):
    assert main.load_jobs_state(strict=True) == {}


def test_resume_rewinds_wrapped_state_with_missing_artifacts(state_file):
    state_file.write_text(json.dumps({"jobs": {
        "daily_2026-10-14": {
            "status": "running", "last_success_stage": "05_deduplication",
        },
    }}), encoding="utf-8")
    assert main.resolve_resume_stage("daily_2026-10-14", main.DAILY_STAGES) is None


def test_ci_state_load_step_passes_on_committed_state():
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    step = workflow.split("      - name: Load state/jobs.json\n", 1)[1]
    script = textwrap.dedent(
        step.split("python - <<'PY'\n", 1)[1].split("          PY", 1)[0]
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=root, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    data = json.loads((root / "state/jobs.json").read_text(encoding="utf-8"))
    expected_count = len(main.parse_jobs_state(data))
    assert f"Loaded {expected_count} jobs successfully" in result.stdout
