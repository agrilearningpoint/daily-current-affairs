# -*- coding: utf-8 -*-
"""PDF-QA visibility into MCQ monotony and cross-edition repeats.

Measured on published editions, the new warnings behave like this:

    edition    questions  distinct 6-word stems  top stem share  warns?
    2026-10-20     18            3                  50%          yes
    2026-10-22     20            4                  65%          yes
    2026-10-27     14            3                  50%          yes
    2026-10-31     15            3                  53%          yes
    2026-11-03     15           13                  20%          no
    2026-11-08     15           15                   7%          no
    2026-11-10     14           13                  14%          no

The October editions were built from three deterministic templates; from
2026-11-02 the LLM schema pass dominates and stems diversify. The 25% threshold
sits between the two regimes, so it flags monotony without nagging about a
healthy edition. Repeats were found too: "Sports Authority of India" and "DST"
(10-20 -> 10-22) and the MSP concept question on 11-08, 11-09 and 11-10.

Warnings only - variety is an editorial signal, not a reason to block a correct
edition.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

from pipeline import mcq_history as h

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def qa():
    spec = importlib.util.spec_from_file_location("pdf_qa_stage", ROOT / "agents" / "19_pdf_qa.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["pdf_qa_stage"] = mod          # @dataclass needs the module registered
    spec.loader.exec_module(mod)
    return mod


def mcq(stem, n=1, concept_id=None, type_="who-org"):
    """``n`` questions sharing one 6-word stem but differing afterwards."""
    out = []
    for i in range(n):
        m = {"type": type_, "question_en": f"{stem} story number {i} in this edition?",
             "question_hi": "प्रश्न?", "options": ["a", "b", "c", "d"], "correct": "A",
             "explanation_en": "e", "explanation_hi": "e", "event_id": f"e{i}"}
        if concept_id:
            m["concept_id"] = concept_id
        out.append(m)
    return out


def codes(report):
    return [i.code for i in report.issues]


# --------------------------------------------------------------------------- #
# 1. Stem measurement
# --------------------------------------------------------------------------- #
def test_stem_of_takes_the_first_words_ignoring_punctuation(qa):
    assert qa.stem_of("Which body recommends the Minimum Support Price (MSP) of notified crops?") == \
        "which body recommends the minimum support"
    assert qa.stem_of("") == ""
    assert qa.stem_of("One two", 6) == "one two"


def test_stem_shares_counts_and_sorts(qa):
    shares = qa.stem_shares(mcq("which institution or entity is centrally", 3)
                            + mcq("what is the key figure reported", 1))
    assert shares[0] == ("which institution or entity is centrally", 3)
    assert shares[1][1] == 1


# --------------------------------------------------------------------------- #
# 2. Monotony warning
# --------------------------------------------------------------------------- #
def test_a_dominant_stem_warns(qa):
    report = qa.QAReport(pdf_path="x")
    qa.check_mcq_variety(report, mcq("which institution or entity is centrally", 9)
                         + mcq("what is the key figure reported", 3),
                         edition_date="2026-11-11", history=h.empty_history())
    assert "mcq_stem_monotony" in codes(report)
    issue = next(i for i in report.issues if i.code == "mcq_stem_monotony")
    assert issue.severity == "warning"
    assert issue.details["count"] == 9 and issue.details["total"] == 12
    assert issue.details["share"] == 0.75
    assert report.mcq_distinct_stems == 2


def test_a_diverse_edition_does_not_warn(qa):
    report = qa.QAReport(pdf_path="x")
    mcqs = [m for i in range(14)
            for m in mcq(f"stem number {i} asks something different", 1)]
    qa.check_mcq_variety(report, mcqs, edition_date="2026-11-11", history=h.empty_history())
    assert "mcq_stem_monotony" not in codes(report)
    assert report.mcq_distinct_stems == 14


def test_a_tiny_edition_is_not_judged_on_stems(qa):
    """Two questions from one template is not monotony, it is a sparse news day."""
    report = qa.QAReport(pdf_path="x")
    qa.check_mcq_variety(report, mcq("which institution or entity is centrally", 4),
                         edition_date="2026-11-11", history=h.empty_history())
    assert "mcq_stem_monotony" not in codes(report)


def test_the_threshold_is_configurable(qa, monkeypatch):
    monkeypatch.setattr(qa, "STEM_SHARE_WARN", 0.9)
    report = qa.QAReport(pdf_path="x")
    qa.check_mcq_variety(report, mcq("which institution or entity is centrally", 9)
                         + mcq("what is the key figure reported", 3),
                         edition_date="2026-11-11", history=h.empty_history())
    assert "mcq_stem_monotony" not in codes(report)


def test_the_kill_switch_silences_both_checks(qa, monkeypatch):
    monkeypatch.setattr(qa, "VARIETY_CHECK", False)
    report = qa.QAReport(pdf_path="x")
    hist = h.empty_history()
    h.record(hist, mcq("which body recommends the minimum support", 1), "2026-11-10")
    qa.check_mcq_variety(report, mcq("which body recommends the minimum support", 9),
                         edition_date="2026-11-11", history=hist)
    assert report.issues == []


# --------------------------------------------------------------------------- #
# 3. Cross-edition repeats
# --------------------------------------------------------------------------- #
def test_a_question_from_an_earlier_edition_warns(qa):
    """The real case: the MSP stem printed on 11-08, 11-09 and 11-10."""
    hist = h.empty_history()
    h.record(hist, mcq("which body recommends the minimum support", 1, concept_id="msp",
                       type_="concept"), "2026-11-09")
    report = qa.QAReport(pdf_path="x")
    qa.check_mcq_variety(report, mcq("which body recommends the minimum support", 1,
                                     concept_id="msp", type_="concept"),
                         edition_date="2026-11-10", history=hist)
    assert "mcq_repeat_from_earlier_edition" in codes(report)
    issue = next(i for i in report.issues if i.code == "mcq_repeat_from_earlier_edition")
    assert issue.details["count"] == 1
    assert issue.details["last_seen"] == ["2026-11-09"]
    assert report.mcq_repeats == 1


def test_this_editions_own_questions_are_not_reported_as_repeats(qa):
    """Stage 16 records the edition before stage 19 runs; entries dated today are
    ignored, so a re-run does not report the edition as repeating itself."""
    hist = h.empty_history()
    today = mcq("which body recommends the minimum support", 2)
    h.record(hist, today, "2026-11-11")
    report = qa.QAReport(pdf_path="x")
    qa.check_mcq_variety(report, today, edition_date="2026-11-11", history=hist)
    assert "mcq_repeat_from_earlier_edition" not in codes(report)


def test_a_question_outside_the_window_is_not_a_repeat(qa, monkeypatch):
    monkeypatch.setattr(h, "DAYS_NEWS", 14)
    hist = h.empty_history()
    h.record(hist, mcq("which ministry launched the new scheme", 1), "2026-10-01")
    report = qa.QAReport(pdf_path="x")
    qa.check_mcq_variety(report, mcq("which ministry launched the new scheme", 1),
                         edition_date="2026-11-11", history=hist)
    assert "mcq_repeat_from_earlier_edition" not in codes(report)


def test_a_broken_history_file_never_fails_qa(qa, monkeypatch):
    def boom():
        raise RuntimeError("state dir unreadable")
    monkeypatch.setattr("pipeline.mcq_history.load", boom)
    report = qa.QAReport(pdf_path="x")
    qa.check_mcq_variety(report, mcq("which body recommends the minimum support", 9),
                         edition_date="2026-11-11")
    # the stem check still ran; only the repeat check was skipped
    assert "mcq_stem_monotony" in codes(report)
    assert "mcq_repeat_from_earlier_edition" not in codes(report)


def test_no_mcqs_means_no_opinion(qa):
    report = qa.QAReport(pdf_path="x")
    qa.check_mcq_variety(report, [], edition_date="2026-11-11", history=h.empty_history())
    assert report.issues == [] and report.mcq_distinct_stems == 0


# --------------------------------------------------------------------------- #
# 4. Reporting surface
# --------------------------------------------------------------------------- #
def test_the_report_serialises_the_new_fields(qa):
    report = qa.QAReport(pdf_path="x")
    qa.check_mcq_variety(report, mcq("which institution or entity is centrally", 9)
                         + mcq("what is the key figure reported", 3),
                         edition_date="2026-11-11", history=h.empty_history())
    data = report.to_dict()
    assert data["mcq_distinct_stems"] == 2
    assert data["mcq_repeats"] == 0


def test_variety_warnings_do_not_fail_qa_by_default(qa):
    report = qa.QAReport(pdf_path="x")
    qa.check_mcq_variety(report, mcq("which institution or entity is centrally", 12),
                         edition_date="2026-11-11", history=h.empty_history())
    assert report.issues and report.passed is True
