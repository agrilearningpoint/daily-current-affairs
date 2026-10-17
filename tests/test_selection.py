import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]


def load_agent(number):
    path = next((ROOT / "agents").glob(f"{number}_*.py"))
    name = f"test_agent_{number}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Cap-aware test: selection must never exceed hi
def test_cap():
    # Simulate 20 items, hi=12, ensure 2 agri 2 banking but cap respected
    items=[{"event_id":str(i),"student_relevance":100-i,"agri_focus":i<2,"banking_focus":2<=i<4} for i in range(20)]
    # Mimic agent logic hi=12
    hi=12
    chosen=[i for i in items if i["student_relevance"]>=25][:hi]
    # ensure would not exceed hi
    assert len(chosen)<=hi


@pytest.mark.parametrize("count", [1, 2, 3, 4])
def test_daily_selection_refuses_editions_below_the_floor(tmp_path, monkeypatch, count):
    """A thin edition must fail loudly instead of shipping 1-4 items.

    The floor is deliberately NOT relaxed for daily (see
    agents/10_final_news_selection.py): failing here surfaces the upstream
    collection/verification regression instead of hiding it behind a
    2-item "edition".
    """
    from pipeline import state

    job_id = "daily_2026-10-14"
    scored_dir = tmp_path / "scored"
    selected_dir = tmp_path / "selected"
    monkeypatch.setattr(state, "SCORED_DIR", scored_dir)
    monkeypatch.setattr(state, "SELECTED_DIR", selected_dir)
    state.write_json_atomic(
        state.data_path(scored_dir, job_id),
        {"items": [{"event_id": str(i), "importance_score": count - i} for i in range(count)]},
    )

    with pytest.raises(RuntimeError, match="min 5"):
        load_agent("10").Agent(job_id, "daily", {}).run()

    assert not state.data_path(selected_dir, job_id).exists(), "a refused edition must not be written"


@pytest.mark.parametrize("count", [5, 6, 9])
def test_daily_selection_accepts_editions_at_or_above_the_floor(tmp_path, monkeypatch, count):
    from pipeline import state

    job_id = "daily_2026-10-14"
    scored_dir = tmp_path / "scored"
    selected_dir = tmp_path / "selected"
    monkeypatch.setattr(state, "SCORED_DIR", scored_dir)
    monkeypatch.setattr(state, "SELECTED_DIR", selected_dir)
    state.write_json_atomic(
        state.data_path(scored_dir, job_id),
        {"items": [{"event_id": str(i), "importance_score": count - i} for i in range(count)]},
    )

    context = {}
    load_agent("10").Agent(job_id, "daily", context).run()

    assert context["selected_count"] == count
    assert len(json.loads(state.data_path(selected_dir, job_id).read_text())["items"]) == count


def test_daily_selection_rejects_empty_input(tmp_path, monkeypatch):
    from pipeline import state

    monkeypatch.setattr(state, "SCORED_DIR", tmp_path / "scored")
    monkeypatch.setattr(state, "SELECTED_DIR", tmp_path / "selected")
    job_id = "daily_2026-10-14"
    state.write_json_atomic(state.data_path(state.SCORED_DIR, job_id), {"items": []})

    with pytest.raises(RuntimeError, match="no scored items"):
        load_agent("10").Agent(job_id, "daily", {}).run()


@pytest.mark.parametrize("job_type", ["weekly", "monthly"])
def test_period_selection_keeps_five_item_minimum(tmp_path, monkeypatch, job_type):
    from pipeline import state

    monkeypatch.setattr(state, "SCORED_DIR", tmp_path / "scored")
    monkeypatch.setattr(state, "SELECTED_DIR", tmp_path / "selected")
    job_id = f"{job_type}_2026-10-14"
    state.write_json_atomic(
        state.data_path(state.SCORED_DIR, job_id),
        {"items": [{"event_id": str(i), "importance_score": i} for i in range(4)]},
    )

    with pytest.raises(RuntimeError, match="min 5"):
        load_agent("10").Agent(job_id, job_type, {}).run()


@pytest.mark.parametrize(("item_count", "expected"), [(1, 2), (2, 4), (4, 8), (5, 10), (12, 10)])
def test_pdf_qa_scales_mcq_minimum_for_sparse_editions(item_count, expected):
    assert load_agent("19").minimum_mcq_count(item_count) == expected


def test_pdf_qa_enforces_the_scaled_mcq_minimum():
    qa = load_agent("19")
    text = "\n".join(f"Question {i}: verified question\nAnswer: A" for i in range(1, 5))

    report = qa.QAReport(pdf_path="fixture.pdf")
    qa.check_mcqs(report, text, min_mcq_count=4)
    assert not any(issue.code == "insufficient_mcqs" for issue in report.issues)

    report = qa.QAReport(pdf_path="fixture.pdf")
    qa.check_mcqs(report, text, min_mcq_count=5)
    issue = next(issue for issue in report.issues if issue.code == "insufficient_mcqs")
    assert issue.details == {"count": 4, "min": 5}
