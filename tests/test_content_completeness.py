# -*- coding: utf-8 -*-
"""Tests for the content-completeness validator (pipeline/completeness.py).

The validator measures whether each selected story carries the educational
fields the master spec requires (bilingual headline, factual body, source
attribution) before the PDF is rendered. It must (a) pass a fully-populated
bilingual story and (b) raise errors when required bilingual content is missing.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.completeness import validate_content_completeness  # noqa: E402


def _full_item():
    return {
        "event_id": "ev-1",
        "category": "Agriculture",
        "headline_en": "Cabinet approves 1,250 crore rupee scheme for 500 credit societies",
        "headline_hi": "मंत्रिमंडल ने 500 साख समितियों के लिए 1,250 करोड़ रुपये की योजना को मंजूरी दी",
        "key_points_en": ["The Union Cabinet approved the scheme for 500 societies."],
        "key_points_hi": ["केंद्रीय मंत्रिमंडल ने 500 समितियों के लिए योजना को मंजूरी दी।"],
        "detailed_explanation_en": "The Union Cabinet approved the scheme and NABARD will implement it by 2027.",
        "detailed_explanation_hi": "केंद्रीय मंत्रिमंडल ने योजना को मंजूरी दी और नाबार्ड 2027 तक इसे लागू करेगा।",
        "static_facts": {"Established": "NABARD — 1982"},
        "source": {"name": "PIB", "url": "https://pib.gov.in/x"},
    }


def _content(items):
    return {"job": {"type": "daily"}, "items": items}


def test_complete_bilingual_story_passes():
    report = validate_content_completeness(_content([_full_item()]))
    assert report.passed, [i.code for i in report.issues]
    assert report.total_items == 1
    assert report.complete_items == 1
    assert report.items_with_detailed_explanation == 1
    assert report.items_with_static_gk == 1
    assert report.items_with_sources == 1


def test_missing_hindi_headline_is_an_error():
    item = _full_item()
    item["headline_hi"] = "English only headline with no Devanagari"
    report = validate_content_completeness(_content([item]))
    assert not report.passed
    assert any(i.code == "missing_headline_hi" for i in report.issues)


def test_missing_body_is_an_error():
    item = _full_item()
    item["key_points_en"] = []
    item["key_points_hi"] = []
    item["detailed_explanation_en"] = ""
    item["detailed_explanation_hi"] = ""
    report = validate_content_completeness(_content([item]))
    assert not report.passed
    assert any(i.code in {"missing_content_en", "missing_content_hi"} for i in report.issues)


def test_zero_items_is_refused():
    report = validate_content_completeness(_content([]))
    assert not report.passed
    assert any(i.code == "zero_items" for i in report.issues)


def test_numeric_divergence_is_reported_not_fatal():
    item = _full_item()
    # Hindi keeps the figure; add an English-only number to trigger the info note.
    item["detailed_explanation_en"] += " The outlay is 4,500 crore in the first phase."
    report = validate_content_completeness(_content([item]))
    # Info-level only: still passes, but the divergence is recorded.
    assert report.passed
    assert any(i.code == "numeric_divergence" and i.severity == "info" for i in report.issues)
