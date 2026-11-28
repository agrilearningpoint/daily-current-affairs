# -*- coding: utf-8 -*-
"""Phase 5 regression tests: Hindi Editorial Engine, Glossary, Sanitizer & Content ordering."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestHindiEditor:
    def test_matra_and_nukta_cleanup(self):
        from pipeline.hindi_editor import edit_hindi_text
        # Double nukta glyph in रोजगार + broken danda
        bad = "सरकार ने रोज़\u093Cगार योजना शुरू किया गया।।"
        fixed = edit_hindi_text(bad)
        assert "\u093C\u093C" not in fixed
        assert "।।" not in fixed
        assert "योजना शुरू की गई" in fixed

    def test_postposition_and_terminology_fixes(self):
        from pipeline.hindi_editor import edit_hindi_text
        raw = "विस्व स्वास्थ्य संगठन ने में नया नियम और जलशक्ति मंत्रालय ने जारी की।"
        fixed = edit_hindi_text(raw)
        assert "विश्व स्वास्थ्य संगठन" in fixed
        assert "विस्व" not in fixed
        assert "ने में" not in fixed
        assert "जल शक्ति मंत्रालय" in fixed
        assert "जारी किया" in fixed

    def test_review_hindi_line_telemetry(self):
        from pipeline.hindi_editor import review_hindi_line
        res = review_hindi_line("WHO launches report", "विस्व स्वास्थ्य संगठन ने में रिपोर्ट जारी की।")
        assert res["ok"] is True
        assert "who_typo_repaired" in res["issues"]
        assert "postposition_collision_repaired" in res["issues"]
        assert "विश्व स्वास्थ्य संगठन" in res["edited_hi"]

        bad = review_hindi_line("English headline", "Only English text here")
        assert bad["ok"] is False
        assert "missing_devanagari" in bad["issues"]

    def test_edit_edition_hindi_walks_content_and_mcqs(self):
        from pipeline.hindi_editor import edit_edition_hindi
        content = {
            "items": [{
                "headline_en": "PM launches scheme",
                "headline_hi": "पीएम ने रोज़\u093Cगार योजना शुरू किया गया",
                "summary_en": "WHO alert",
                "summary_hi": "विस्व स्वास्थ्य संगठन ने में चेतावनी जारी की।",
                "key_points_en": ["Point 1"],
                "key_points_hi": ["जलशक्ति मंत्रालय ने रिपोर्ट जारी की।"],
            }],
            "one_liners": [{"text_en": "WHO report", "text_hi": "विस्व रिपोर्ट जारी की।"}],
        }
        mcqs = [{
            "question_en": "Which body?",
            "question_hi": "विस्व स्वास्थ्य संगठन क्या है?",
            "options": ["A", "B", "C", "D", "E"],
            "options_hi": ["विस्व स्वास्थ्य संगठन", "बी", "सी", "डी", "ई"],
            "explanation_en": "Expl",
            "explanation_hi": "जलशक्ति मंत्रालय ने में बताया।",
            "explanation_pairs": [{"en": "One", "hi": "ने में एक।"}],
        }]
        stats = edit_edition_hindi(content, mcqs)
        assert stats["lines_checked"] >= 7
        assert stats["lines_edited"] >= 5
        assert "विश्व स्वास्थ्य संगठन" in content["items"][0]["summary_hi"]
        assert "जल शक्ति मंत्रालय" in content["items"][0]["key_points_hi"][0]
        assert "विश्व रिपोर्ट" in content["one_liners"][0]["text_hi"]
        assert "विश्व स्वास्थ्य संगठन" in mcqs[0]["question_hi"]
        assert "विश्व स्वास्थ्य संगठन" in mcqs[0]["options_hi"][0]
        assert "ने में" not in mcqs[0]["explanation_hi"]
        assert "ने में" not in mcqs[0]["explanation_pairs"][0]["hi"]


class TestAiTranslatorAndSanitizerFixes:
    def test_who_special_acronym_fixed(self):
        from pipeline.ai_translator import _SPECIAL_ACRONYMS
        assert _SPECIAL_ACRONYMS["WHO"] == "विश्व स्वास्थ्य संगठन"

    def test_content_sanitizer_does_not_misfire_on_valid_hindi_words_ending_in_men_ko(self):
        from pipeline.content_sanitizer import DANGLING_SENTENCE_ENDINGS, repair_dangling_sentence
        # "जिसमें" ends with में inside one word, NOT a dangling postposition
        valid_hi = "यह योजना किसानों की आय बढ़ाने के लिए है जिसमें"
        assert not DANGLING_SENTENCE_ENDINGS.search(valid_hi), \
            "Single word ending in 'में' (जिसमें) must not trigger DANGLING_SENTENCE_ENDINGS"
        # Standalone dangling postposition with whitespace SHOULD still match
        dangling_hi = "प्रधानमंत्री ने विकास परियोजनाओं को समर्पित किया जिनकी लागत लगभग रुपये"
        assert DANGLING_SENTENCE_ENDINGS.search(dangling_hi)
        repaired = repair_dangling_sentence(dangling_hi, fallback_title="")
        assert "रुपये" not in repaired or repaired.endswith(".")

    def test_content_polishes_english_before_translation(self):
        from pipeline.content import _build_entry
        calls = []

        def fake_polish(text, source_text):
            calls.append(("polish", text))
            return "Clarified English Headline For Farmers"

        def fake_translate(text, task="general"):
            calls.append(("translate", text))
            return ("किसानों के लिए स्पष्ट समाचार", "ai_translator", 1.0)

        item = {
            "event_id": "ev_order_test",
            "headline_en": "Original Headline For Farmers Today",
            "raw_facts": "Original Headline For Farmers Today. Farmers received MSP support.",
            "source_name": "PIB",
            "source_url": "https://pib.gov.in/1",
            "source_tier": "tier1",
            "is_verified": True,
            "provenance_verified": True,
            "verification_mode": "live",
        }
        stats = {"total_items": 1, "ai_passed": 0, "ai_failed": 0,
                 "deterministic_fallback": 0, "untranslated": 0, "skipped_items": 0}
        with patch("pipeline.content.polish_with_ai", side_effect=fake_polish), \
             patch("pipeline.content.translate_with_ai_or_fallback", side_effect=fake_translate), \
             patch("pipeline.content._prefill_body_translation_cache", return_value=0):
            entry = _build_entry(item, stats)

        assert entry is not None
        assert ("translate", "Clarified English Headline For Farmers") in calls


class TestPhase4AdditionalHardening:
    def test_today_does_not_mask_old_explicit_date_in_stale_reason(self):
        from pipeline.freshness import stale_reason
        old_with_today = {
            "headline_en": "Kharif MSP approved on 13 May 2026 announced today",
            "raw_facts": "Published today about 13 May 2026 Cabinet decision",
        }
        why = stale_reason(old_with_today, "2026-11-28")
        assert "2026-05-13" in why

    def test_wire_agency_syndication_collapsed(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("fv04", str(ROOT / "agents" / "04_fact_verification.py"))
        fv = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fv)
        a1 = {"title": "RBI keeps repo rate unchanged at 5.5 percent (PTI)",
              "summary": "PTI Mumbai report on RBI MPC meeting outcome",
              "link": "https://portal1.example/rbi"}
        a2 = {"title": "RBI keeps repo rate unchanged at 5.5 percent - PTI",
              "summary": "PTI Mumbai report on RBI MPC meeting outcome",
              "link": "https://portal2.example/rbi"}
        a3 = {"title": "RBI keeps repo rate unchanged at 5.5 percent (PTI)",
              "summary": "PTI report from Mumbai on repo rate",
              "link": "https://portal3.example/rbi"}
        _score, corr = fv.cross_source_score(a1, [a1, a2, a3])
        assert corr.count("wire:PTI") == 1
        assert len(corr) == 1
