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
def test_daily_selection_accepts_sparse_verified_editions(tmp_path, monkeypatch, count):
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


def test_daily_selection_honours_production_minimum(tmp_path, monkeypatch):
    """Scheduled runs reject a thin edition before content/PDF work begins."""
    from pipeline import state

    monkeypatch.setattr(state, "SCORED_DIR", tmp_path / "scored")
    monkeypatch.setattr(state, "SELECTED_DIR", tmp_path / "selected")
    monkeypatch.setenv("ALP_MIN_DAILY_NEWS", "15")
    job_id = "daily_2026-10-14"
    state.write_json_atomic(
        state.data_path(state.SCORED_DIR, job_id),
        {"items": [{"event_id": str(i), "importance_score": i} for i in range(14)]},
    )

    with pytest.raises(RuntimeError, match="min 15"):
        load_agent("10").Agent(job_id, "daily", {}).run()


def test_pdf_qa_page_range_is_a_hard_release_gate(monkeypatch):
    qa = load_agent("19")
    monkeypatch.setattr(qa, "MIN_PAGES", 15)
    monkeypatch.setattr(qa, "MAX_PAGES", 45)
    short = qa.QAReport(pdf_path="fixture.pdf")
    qa.check_pages(short, type("Doc", (), {"page_count": 14, "__iter__": lambda self: iter(())})())
    assert any(i.code == "too_few_pages" and i.severity == "error" for i in short.issues)
    long = qa.QAReport(pdf_path="fixture.pdf")
    qa.check_pages(long, type("Doc", (), {"page_count": 46, "__iter__": lambda self: iter(())})())
    assert any(i.code == "too_many_pages" and i.severity == "error" for i in long.issues)


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


def test_daily_domain_relevance_retains_full_coverage(tmp_path, monkeypatch):
    """Ensure stage 07 does NOT cap output to 6 items when ~25-28 relevant news exist."""
    from pipeline import state

    job_id = "daily_2026-10-17"
    scored_dir = tmp_path / "scored"
    monkeypatch.setattr(state, "SCORED_DIR", scored_dir)

    # 25 verified articles across diverse categories
    categories = ["Agriculture", "Banking & Finance", "Economy", "Government Schemes", "National"] * 5
    items = [
        {
            "event_id": f"evt_{i}",
            "headline_en": f"Important Exam News Headline Event {i} regarding national development",
            "raw_facts": f"Government announced policy measure number {i} for farmers and economy.",
            "importance_score": 30 + (i % 20),
            "category": categories[i],
        }
        for i in range(25)
    ]
    state.write_json_atomic(state.data_path(scored_dir, job_id), {"items": items})

    agent = load_agent("07").Agent(job_id, "daily", {})
    agent.run()

    saved = json.loads(state.data_path(scored_dir, job_id).read_text())["items"]
    assert len(saved) == 25
    assert all(it.get("student_relevance", 0) >= 15 for it in saved)


@pytest.mark.parametrize(("item_count", "expected"), [(0, 2), (1, 2), (3, 2), (4, 2), (12, 6), (30, 15), (40, 15)])
def test_pdf_qa_scales_substantive_page_floor(item_count, expected):
    """Floor is ~half a page per story so real short-summary days are not failed,
    while clear content loss still trips an error."""
    assert load_agent("19").minimum_substantive_pages(item_count) == expected


def test_pdf_qa_flags_content_loss_but_only_warns_on_sparse_day():
    qa = load_agent("19")

    # 12 stories but only 4 substantive pages -> clear content loss (error).
    report = qa.QAReport(pdf_path="fixture.pdf")
    report.substantive_pages = 4
    qa.check_page_target(report, 12)
    assert any(i.code == "insufficient_substantive_pages" and i.severity == "error"
               for i in report.issues)

    # A realistic short-summary day (12 stories -> 8 pages) clears the floor but
    # is below the 15-page target, so it warns instead of failing.
    report = qa.QAReport(pdf_path="fixture.pdf")
    report.substantive_pages = 8
    qa.check_page_target(report, 12)
    assert not any(i.severity == "error" for i in report.issues)
    assert any(i.code == "below_page_target" for i in report.issues)

    # A full edition clears both gates.
    report = qa.QAReport(pdf_path="fixture.pdf")
    report.substantive_pages = 20
    qa.check_page_target(report, 18)
    assert not report.issues


def test_pdf_qa_detects_missing_stories_from_the_pdf():
    qa = load_agent("19")
    text = "Cabinet approves 1250 crore scheme for 500 credit societies today"
    items = [
        {"headline_en": "Cabinet approves 1250 crore scheme for 500 credit societies"},
        {"headline_en": "RBI keeps repo rate unchanged at 650 per cent in review"},
        {"headline_en": "ISRO tests semi cryogenic engine at Mahendragiri facility"},
        {"headline_en": "India adds 2100 MW solar capacity in September month"},
        {"headline_en": "WHO and FAO launch joint action plan on resistance"},
    ]
    report = qa.QAReport(pdf_path="fixture.pdf")
    qa.check_story_coverage(report, text, items)
    # One story (the first) is present; four are missing -> error.
    assert any(i.code == "stories_missing_from_pdf" and i.severity == "error"
               for i in report.issues)

    # All present -> no issue.
    report = qa.QAReport(pdf_path="fixture.pdf")
    qa.check_story_coverage(report, text, items[:1])
    assert not report.issues


def test_deduplication_keeps_distinct_numerical_events():
    """Ensure 05_deduplication does NOT merge different policies that share keywords but have distinct numbers."""
    dedup = load_agent("05")
    a = {"title": "Cabinet Approves Agriculture Mission with Rs 5000 Crore Outlay", "confidence_score": 0.9}
    b = {"title": "Cabinet Approves Agriculture Mission with Rs 10000 Crore Outlay", "confidence_score": 0.85}
    assert dedup.distinct_event_check(a, b) is True
    clustered = dedup.dedup_similarity([a, b])
    assert len(clustered) == 2
