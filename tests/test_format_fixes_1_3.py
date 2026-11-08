# -*- coding: utf-8 -*-
"""Regression tests for format fixes 1-3 (Hindi body, unit pairing, Static GK)."""
from __future__ import annotations

import os
import sys
import tempfile

os.environ.setdefault("ALP_ROOT", tempfile.mkdtemp(prefix="alp_test_"))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline import content, scoring  # noqa: E402
from pipeline.completeness import validate_content_completeness  # noqa: E402


def _item(**kw):
    base = {
        "event_id": "x1",
        "category": "Agriculture",
        "headline_en": ">> Cabinet approves new agriculture export scheme for farmers",
        "headline_hi": ">> मंत्रिमंडल ने किसानों के लिए नई कृषि निर्यात योजना को मंज़ूरी दी",
        "key_points_en": ["The Union Cabinet approved the scheme for APEDA export promotion."],
        "key_points_hi": [""],
        "detailed_explanation_en": "The Union Cabinet approved the scheme for export promotion.",
        "detailed_explanation_hi": "",
    }
    base.update(kw)
    return base


# --- Fix 1 -------------------------------------------------------------------
def test_completeness_rejects_list_of_empty_hindi_strings():
    rep = validate_content_completeness({"items": [_item()]})
    codes = [i.code for i in rep.issues]
    assert "missing_content_hi" in codes, codes


def test_build_content_fills_hindi_key_points_and_exam_fact():
    from tests.test_pipeline_offline import make_items

    scored = scoring.score_all(scoring.deduplicate(make_items()))
    c = content.build_content(scored, {"type": "daily", "date_display": "05 October 2026"})
    for it in c["items"]:
        assert all(k.strip() for k in it["key_points_hi"]), it["event_id"]
        assert len(it["key_points_hi"]) == len(it["key_points_en"])
        assert it["exam_fact_hi"].strip()
        assert it["detailed_explanation_hi"].strip()


def test_strict_mode_stays_fail_closed(monkeypatch):
    monkeypatch.setenv("ALP_TRANSLATION_STRICT", "1")
    content._TRANSLATION_CACHE.clear()
    hi, method, _ = content.translate_with_ai_or_fallback("Repo rate kept at 6.50 per cent", task="body")
    assert method == "untranslated"
    assert hi == "Repo rate kept at 6.50 per cent"


def test_body_batch_rejects_invalid_hindi(monkeypatch):
    import pipeline.ai_router as router

    content._TRANSLATION_CACHE.clear()
    monkeypatch.setattr(router, "is_configured", lambda: True)
    monkeypatch.setattr(
        router, "route",
        lambda *a, **k: '{"translations": ["ISRO ने NVS-09 उपग्रह का सफल प्रक्षेपण किया", "still english"]}',
    )
    lines = ["ISRO successfully launched the NVS-09 satellite", "CPI inflation eased in September"]
    saved = content._prefill_body_translation_cache(lines, task="body")
    assert saved == 1
    assert ("body", lines[0]) in content._TRANSLATION_CACHE
    assert ("body", lines[1]) not in content._TRANSLATION_CACHE
    content._TRANSLATION_CACHE.clear()


# --- Fix 2 -------------------------------------------------------------------
def test_units_never_recycle_items():
    from src.generate_pdf import _pair_units

    items = [{"event_id": f"e{i}", "headline_en": f"Story {i}"} for i in range(3)]
    mcqs = [{"q_num": i + 1, "event_id": f"e{i % 3}", "question_en": f"Q {i}"} for i in range(8)]
    units = _pair_units(items, mcqs)
    assert [u[0]["event_id"] for u in units] == ["e0", "e1", "e2"]
    assert sum(len(ms) for _, ms in units) == 8
    for it, ms in units:
        assert all(m["event_id"] == it["event_id"] for m in ms)


def test_units_skip_items_without_mcq_and_positional_fallback():
    from src.generate_pdf import _pair_units

    items = [{"event_id": f"e{i}"} for i in range(5)]
    assert len(_pair_units(items, [{"event_id": "e3", "question_en": "q"}])) == 1
    assert len(_pair_units(items, [{"question_en": "q1"}, {"question_en": "q2"}])) == 2
    assert _pair_units(items, []) == []


# --- Fix 3 -------------------------------------------------------------------
def test_static_gk_uses_bilingual_pairs_and_hides_private_keys():
    from src.generate_pdf import _extract_static_gk_pairs

    item = {
        "static_facts": {"Fact 1": "Rs 5000 Crore",
                         "_static_gk_pairs": [("NABARD HQ: Mumbai", "NABARD मुख्यालय: मुंबई")]},
        "static_gk_pairs": [["NABARD HQ: Mumbai", "NABARD मुख्यालय: मुंबई"]],
    }
    pairs = _extract_static_gk_pairs(item)
    text = " ".join(e + " " + h for e, h in pairs)
    assert "_static_gk_pairs" not in text
    assert "[(" not in text and "[[" not in text
    assert pairs[0] == ("NABARD HQ: Mumbai", "NABARD मुख्यालय: मुंबई")


def test_static_gk_fallback_skips_underscore_keys():
    from src.generate_pdf import _extract_static_gk_pairs

    item = {"static_facts": {"Fact 1": "Rs 5000 Crore", "_static_gk_pairs": [("a", "b")]}}
    pairs = _extract_static_gk_pairs(item)
    assert pairs == [("Fact 1 – ₹5000 crore", "")]  # Rs -> ₹ normalised for display
