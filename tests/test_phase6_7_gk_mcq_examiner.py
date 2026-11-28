# -*- coding: utf-8 -*-
"""Phase 6-7 regression tests: Static GK Hindi completeness, _qkey collision fix, and MCQ Examiner."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestStaticGKCompleteness:
    def test_current_facts_no_blank_name_hi(self):
        data = json.loads((ROOT / "config" / "current_facts.json").read_text(encoding="utf-8"))
        blanks = [f.get("id") for f in data.get("facts", []) if not (f.get("name_hi") or "").strip()]
        assert blanks == [], f"All facts in current_facts.json must have non-empty name_hi, blanks: {blanks}"

    def test_qkey_no_60char_prefix_collision(self):
        from pipeline.content import _qkey
        q1 = "Which Union Ministry or implementing agency is responsible for administering the National Bamboo Mission?"
        q2 = "Which Union Ministry or implementing agency is responsible for administering the PM-KUSUM Solar Scheme?"
        assert q1[:60] == q2[:60], "Test precondition: first 60 chars identical"
        assert _qkey(q1) != _qkey(q2), "_qkey must not collide on long common prefixes"


class TestMCQExaminer:
    def _sample_item(self):
        return {
            "event_id": "ev_mcq_1",
            "headline_en": "Cabinet approves Rs 2,481 crore National Mission on Natural Farming",
            "summary_en": "The Union Cabinet approved the National Mission on Natural Farming (NMNF) implemented by Ministry of Agriculture and Farmers Welfare across 15,000 clusters.",
            "detailed_explanation_en": "The scheme promotes chemical-free farming across 15,000 clusters with an outlay of Rs 2,481 crore.",
            "key_points_en": ["Ministry of Agriculture and Farmers Welfare will implement NMNF across 15,000 clusters."],
        }

    def test_valid_mcq_passes_examiner(self):
        from pipeline.mcq_examiner import examine_mcq, examine_mcq_set
        ci = self._sample_item()
        mcq = {
            "event_id": "ev_mcq_1",
            "type": "llm-schema",
            "question_en": "How many clusters are targeted under the National Mission on Natural Farming?",
            "question_hi": "राष्ट्रीय प्राकृतिक खेती मिशन के तहत कितने क्लस्टरों को लक्षित किया गया है?",
            "options": ["15,000", "10,000", "20,000", "25,000", "30,000"],
            "options_hi": ["15,000", "10,000", "20,000", "25,000", "30,000"],
            "correct": "A",
            "explanation_en": "NMNF covers 15,000 clusters across India.",
            "explanation_hi": "एनएमएनएफ पूरे भारत में 15,000 क्लस्टरों को कवर करता है।",
        }
        res = examine_mcq(mcq, ci)
        assert res["passed"] is True
        assert res["score"] >= 85
        approved, rejected, report = examine_mcq_set([mcq], [ci])
        assert len(approved) == 1 and len(rejected) == 0
        assert report["approved"] == 1

    def test_examiner_rejects_missing_hindi_or_meta_option(self):
        from pipeline.mcq_examiner import examine_mcq_set
        ci = self._sample_item()
        bad_mcq = {
            "event_id": "ev_mcq_1",
            "question_en": "How many clusters are targeted under the National Mission on Natural Farming?",
            "question_hi": "No Devanagari here",
            "options": ["15,000", "10,000", "20,000", "25,000", "All of the above"],
            "correct": "A",
        }
        approved, rejected, report = examine_mcq_set([bad_mcq], [ci])
        assert len(approved) == 0
        assert len(rejected) == 1
        errs = " ".join(rejected[0]["examiner_errors"])
        assert "Devanagari" in errs and "meta-option" in errs

    def test_examiner_flags_miskeyed_option_to_supported_option(self):
        from pipeline.mcq_examiner import examine_mcq
        ci = self._sample_item()
        miskeyed = {
            "event_id": "ev_mcq_1",
            "question_en": "Which outlay was approved by the Union Cabinet for National Mission on Natural Farming?",
            "question_hi": "केंद्रीय मंत्रिमंडल द्वारा राष्ट्रीय प्राकृतिक खेती मिशन के लिए कितना परिव्यय स्वीकृत किया गया?",
            "options": ["Rs 5,000 crore", "Rs 2,481 crore", "Rs 1,200 crore", "Rs 3,800 crore", "Rs 6,000 crore"],
            "options_hi": ["₹5,000 करोड़", "₹2,481 करोड़", "₹1,200 करोड़", "₹3,800 करोड़", "₹6,000 करोड़"],
            "correct": "A",
        }
        verdict = examine_mcq(miskeyed, ci)
        assert verdict["passed"] is False
        assert any("miskeyed" in e or "key" in e for e in verdict["critical_errors"])
