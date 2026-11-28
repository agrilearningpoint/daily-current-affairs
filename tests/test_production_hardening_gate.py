# -*- coding: utf-8 -*-
"""Regression suite for Production Hardening (Priorities 1-7)."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_agent(prefix: str):
    name = f"hardening_agent_{prefix}"
    if name in sys.modules:
        return sys.modules[name]
    path = next((ROOT / "agents").glob(f"{prefix}_*.py"))
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# =============================================================================
# PRIORITY 1 — Hindi Editorial Quality Gate
# =============================================================================
class TestHindiEditorialQualityGate:
    def test_detects_and_repairs_unicode_corruption_and_incomplete_sentences(self):
        from pipeline.hindi_editor import edit_hindi_text, review_hindi_line, audit_edition_hindi

        # 1. Replacement char + double halant + isolated matra
        dirty = "सरका\ufffd ने \u094d\u094d 500 करोड़ ा योजना शुरू की"
        repaired = edit_hindi_text(dirty, "Govt launched Rs 500 crore scheme")
        assert "\ufffd" not in repaired
        assert "\u094d\u094d" not in repaired
        # review_hindi_line still flags replacement_char_detected as critical because original text lost characters
        rev = review_hindi_line("Govt launched Rs 500 crore scheme", dirty)
        assert rev["critical"] is True
        assert "replacement_char_detected" in rev["issues"]

        # 2. Incomplete Hindi sentence flagged as critical
        rev_inc = review_hindi_line("Scheme cost around Rs 500", "योजना की लागत लगभग रुपये")
        assert rev_inc["critical"] is True
        assert "incomplete_hindi_sentence" in rev_inc["issues"]

        # 3. Clean Hindi passes edition audit
        good_content = {
            "items": [{
                "event_id": "e1",
                "headline_en": "Cabinet approves agriculture credit scheme",
                "headline_hi": "मंत्रिमंडल ने कृषि साख योजना को मंज़ूरी दी",
                "summary_en": "Union Cabinet cleared a scheme for farmers.",
                "summary_hi": "केंद्रीय मंत्रिमंडल ने किसानों के लिए योजना को स्वीकृति दी।",
            }],
            "one_liners": [{"text_en": "MSP increased.", "text_hi": "एमएसपी में वृद्धि की गई।"}],
        }
        good_mcqs = [{
            "event_id": "e1",
            "question_en": "Which scheme was approved?",
            "question_hi": "किस योजना को मंज़ूरी दी गई?",
            "options": ["Option A", "Option B"],
            "options_hi": ["विकल्प A", "विकल्प B"],
            "explanation_hi": "मंत्रिमंडल ने किसानों के लिए योजना को स्वीकृति दी।",
        }]
        rep_ok = audit_edition_hindi(good_content, good_mcqs)
        assert rep_ok["passed"] is True
        assert rep_ok["critical_count"] == 0

    def test_completeness_and_pdf_qa_block_critical_hindi_defects(self):
        from pipeline.completeness import validate_content_completeness

        bad_content = {
            "items": [{
                "event_id": "h1",
                "headline_en": "RBI keeps repo rate unchanged at 6.50 percent",
                "headline_hi": "आरबीआई ने रेपो दर \ufffd 6.50 प्रतिशत पर स्थिर रखी",
                "key_points_en": ["Monetary Policy Committee held the rate."],
                "key_points_hi": ["मौद्रिक नीति समिति ने दर को स्थिर रखा।"],
            }]
        }
        creport = validate_content_completeness(bad_content)
        assert creport.passed is False
        assert any(i.code == "corrupt_hindi_unicode" for i in creport.issues)

        a19 = _load_agent("19")
        qa_rep = a19.QAReport(pdf_path="diag.pdf", checked_at="2026-11-28T00:00:00Z")
        a19.check_hindi_edition_quality(qa_rep, bad_content, [], strict=True)
        assert qa_rep.passed is False
        assert any(i.code == "critical_hindi_defect" for i in qa_rep.issues)


# =============================================================================
# PRIORITY 2 — News Category Accuracy (All 10 Categories + Confidence Flag)
# =============================================================================
class TestNewsCategoryAccuracy:
    def test_iffi_film_headline_not_classified_as_sports(self):
        from pipeline.collector import infer_category
        import pipeline.period_builder as pb

        hl = "10 Films to Compete for ICFT-UNESCO Gandhi Medal at 57th IFFI"
        assert infer_category(hl) == "Awards & Honours"
        assert pb.section_for({"headline_en": hl, "category": "Sports"}) == "Appointments & Awards"
        assert pb.section_for({"headline_en": hl, "category": "National"}) == "Appointments & Awards"

    @pytest.mark.parametrize("headline,expected", [
        ("Cabinet approves MSP hike for Kharif crops and ICAR seed mission", "Agriculture"),
        ("India GDP growth projected at 7.1 percent as CPI inflation eases", "Economy"),
        ("RBI Monetary Policy keeps repo rate steady; NABARD widens NBFC credit", "Banking & Finance"),
        ("ISRO successfully launches navigation satellite with indigenous quantum payload", "Science & Technology"),
        ("MOEFCC releases biodiversity report on forest conservation and wildlife carbon sinks", "Environment"),
        ("Supreme Court Constitution Bench delivers verdict on electoral tribunal petition", "National"),
        ("India and Japan hold bilateral foreign ministerial summit in Tokyo", "International"),
        ("India wins Asian Games gold medal in 10m air rifle hockey tournament", "Sports"),
        ("Sahitya Akademi and Padma Bhushan awards conferred in New Delhi ceremony", "Awards & Honours"),
        ("World Soil Day observed across India with special awareness theme", "Important Days"),
    ])
    def test_ten_exam_categories(self, headline, expected):
        from pipeline.collector import infer_category
        assert infer_category(headline) == expected

    def test_ambiguous_classification_flagged_for_review(self):
        from pipeline.collector import classify_category_with_confidence

        res_zero = classify_category_with_confidence("General update on local civic meeting today")
        assert res_zero["uncertain"] is True
        assert res_zero["needs_review"] is True

        res_tie = classify_category_with_confidence("Cabinet agricultural subsidy loan bank budget")
        # Even if ties occur cleanly, verify score/confidence telemetry structure is populated
        assert 0.0 <= res_tie["confidence"] <= 1.0
        assert "reason" in res_tie


# =============================================================================
# PRIORITY 3 — Static GK & Repetition Control
# =============================================================================
class TestStaticGKRepetitionControl:
    def test_daily_exact_and_semantic_duplicate_static_gk_removed(self):
        from agents.static_gk_validator import validate_edition

        content = {
            "items": [
                {
                    "event_id": "s1",
                    "headline_en": "RBI issues liquidity guidelines",
                    "static_gk_pairs": [
                        {"en": "Reserve Bank of India (RBI) was established on 1 April 1935.", "hi": "आरबीआई की स्थापना 1 अप्रैल 1935 को हुई।"},
                    ],
                },
                {
                    "event_id": "s2",
                    "headline_en": "RBI updates repo survey",
                    "static_gk_pairs": [
                        {"en": "Reserve Bank of India (RBI) was established on 1 April 1935.", "hi": "आरबीआई की स्थापना 1 अप्रैल 1935 को हुई।"},
                        {"en": "Reserve Bank of India RBI established on 1 April 1935", "hi": "आरबीआई स्थापना"},
                    ],
                },
                {
                    "event_id": "s3",
                    "headline_en": "NABARD rural scheme",
                    "static_gk_pairs": [
                        {"en": "NABARD is headquartered in Mumbai, Maharashtra.", "hi": "नाबार्ड का मुख्यालय मुंबई में है।"},
                    ],
                },
            ]
        }
        rep = validate_edition(content, mcq_data=None, lookup=None)
        assert rep["duplicates_removed"] == 2
        assert len(content["items"][0]["static_gk_pairs"]) == 1
        assert len(content["items"][1]["static_gk_pairs"]) == 0
        assert len(content["items"][2]["static_gk_pairs"]) == 1

    def test_renderer_deduplicates_static_gk_across_edition_and_respects_builder_dedup(self):
        from src.generate_pdf import _extract_static_gk_pairs

        it1 = {
            "headline_en": "RBI releases annual report on banking trends",
            "summary_en": "The Reserve Bank of India (RBI) published financial stability data.",
            "static_gk_pairs": [{"en": "RBI Headquarters – Mumbai, Maharashtra", "hi": "मुख्यालय – मुंबई"}],
        }
        it2 = {
            "headline_en": "RBI conducts inflation expectations survey",
            "summary_en": "The Reserve Bank of India (RBI) launched quarterly household surveys.",
            "static_gk_pairs": [{"en": "RBI Headquarters – Mumbai, Maharashtra", "hi": "मुख्यालय – मुंबई"}],
        }
        seen_edition: list[str] = []
        p1 = _extract_static_gk_pairs(it1, seen_edition_facts=seen_edition)
        p2 = _extract_static_gk_pairs(it2, seen_edition_facts=seen_edition)
        assert len(p1) > 0
        # Nothing printed in p1 may repeat in p2
        p1_norms = {en.lower() for en, _ in p1}
        p2_norms = {en.lower() for en, _ in p2}
        assert not (p1_norms & p2_norms)

        # Builder-deduped period story with static_gk_deduped=True must not re-inject DB GK
        period_story_empty = {
            "headline_en": "RBI third mention",
            "summary_en": "Reserve Bank of India note.",
            "static_gk_pairs": [],
            "static_gk_deduped": True,
        }
        assert _extract_static_gk_pairs(period_story_empty, seen_edition_facts=seen_edition) == []


# =============================================================================
# PRIORITY 4 — Headline & PDF Clipping Guard
# =============================================================================
class TestHeadlineAndPdfClipping:
    def test_distinguishes_cover_ellipsis_from_story_headline_clipping(self):
        a19 = _load_agent("19")

        # 1. Cover ellipsis + FULL headline rendered in body -> MUST NOT FAIL
        item_full = {"headline_en": "Cabinet approves comprehensive cooperative agriculture credit modernisation mission for farmers"}
        pdf_text_ok = (
            "Cover preview: Cabinet approves comprehensive cooperative agriculture…\n"
            "STORY 1 OF 1\n"
            "Cabinet approves comprehensive cooperative agriculture credit modernisation mission for farmers\n"
        )
        rep_ok = a19.QAReport(pdf_path="ok.pdf", checked_at="2026-11-28T00:00:00Z")
        a19.check_headline_clipping(rep_ok, pdf_text_ok, [item_full])
        assert rep_ok.passed is True

        # 2. Story headline truncated mid-sentence -> MUST FAIL & route to 12_content_editor
        item_clipped = {"headline_en": "Cabinet approves comprehensive cooperative agriculture credit modernisation mission for..."}
        rep_bad = a19.QAReport(pdf_path="bad.pdf", checked_at="2026-11-28T00:00:00Z")
        a19.check_headline_clipping(rep_bad, pdf_text_ok, [item_clipped])
        assert rep_bad.passed is False
        assert any(i.code == "clipped_headline" for i in rep_bad.issues)

        from pipeline.supervisor import MasterSupervisor
        sup = MasterSupervisor(ROOT, "daily_2026-11-28", "daily", "2026-11-28")
        assert sup._infer_qa_repair_target({"issues": [{"code": "clipped_headline"}]}) == "12_content_editor"
        assert sup._infer_qa_repair_target({"issues": [{"code": "visual_edge_clipping"}]}) == "18_pdf_design"


# =============================================================================
# PRIORITY 5 & 7 — Release Gate & Corrupt PDF Security Regression
# =============================================================================
class TestReleaseGateRegression:
    def test_release_gate_blocks_all_invalid_states_without_sending(self, tmp_path):
        a19 = _load_agent("19")
        a22 = _load_agent("22")
        from pipeline import store
        from pipeline.supervisor import MasterSupervisor, STAGE_STATUS_REPAIR

        (tmp_path / "config").mkdir(parents=True)
        (tmp_path / "config/supervisor_policy.json").write_text(
            (ROOT / "config/supervisor_policy.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        pdf = tmp_path / "output/daily_2026-11-28.pdf"
        pdf.parent.mkdir(parents=True)
        pdf.write_bytes(b"%PDF-1.4\n%%EOF")
        sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
        qa_path = tmp_path / "logs/qa/daily_2026-11-28_qa.json"
        qa_path.parent.mkdir(parents=True)
        pub_ledger = tmp_path / "state/published_events.json"

        sent = []
        orig = (a22.REPO_ROOT, a22.DRY_RUN, a22.send_document, a22.LEDGER_FILE)
        a22.REPO_ROOT = tmp_path
        a22.DRY_RUN = False
        a22.LEDGER_FILE = pub_ledger
        a22.send_document = lambda *a, **k: sent.append(a) or {"ok": True, "message_id": 100}
        try:
            with patch.dict(os.environ, {"ALP_PUBLISHED_PATH": str(pub_ledger), "DRY_RUN": "0"}):
                # Missing PDF & missing QA
                assert a22.publish_pdf(tmp_path / "output/missing.pdf", {"records": {}}) is False
                assert a22.publish_pdf(pdf, {"records": {}}) is False

                # Hash mismatch
                qa_path.write_text(json.dumps({"passed": True, "job_id": "daily_2026-11-28", "file_sha256": "0" * 64}), encoding="utf-8")
                assert a22.publish_pdf(pdf, {"records": {}}) is False

                # Unresolved P0 defect
                qa_path.write_text(json.dumps({"passed": False, "job_id": "daily_2026-11-28", "file_sha256": sha}), encoding="utf-8")
                assert a22.publish_pdf(pdf, {"records": {}}) is False

                # Tampered release_approval signature
                qa_path.write_text(json.dumps({
                    "passed": True, "job_id": "daily_2026-11-28", "file_sha256": sha,
                    "release_approval": {"approved": True, "visual_passed": True, "signature": "f" * 64},
                }), encoding="utf-8")
                assert a22.publish_pdf(pdf, {"records": {}}) is False

                # Idempotency block for modified PDF when live record exists
                ledger_data = {"records": {"k": {
                    "job_id": "daily_2026-11-28", "chat_id": str(a22.TELEGRAM_CHAT_ID),
                    "status": "success", "dry_run": False, "message_id": 55,
                }}}
                store._atomic_write_json(pub_ledger, ledger_data)
                (tmp_path / "data/content").mkdir(parents=True)
                (tmp_path / "data/content/daily_2026-11-28.json").write_text(
                    json.dumps({"items": [{"needs_review": False, "verification_passed": True}]}),
                    encoding="utf-8",
                )
                sig = a19.release_signature_for("daily_2026-11-28", sha, True, True)
                qa_path.write_text(json.dumps({
                    "passed": True, "job_id": "daily_2026-11-28", "file_sha256": sha,
                    "release_approval": {"approved": True, "visual_passed": True, "signature": sig},
                }), encoding="utf-8")
                assert a22.publish_pdf(pdf, ledger_data) is False
                assert sent == []

                # Corrupt PDF detected by MasterSupervisor
                pdf.write_bytes(b"NOT_A_PDF")
                sup = MasterSupervisor(tmp_path, "daily_2026-11-28", "daily", "2026-11-28")
                c_bad = sup.observe_and_critique("18_pdf_design", exit_ok=True, msg="", duration_s=0.1, strict_files=True)
                assert c_bad.status == STAGE_STATUS_REPAIR
                assert c_bad.repair_target == "18_pdf_design"
        finally:
            a22.REPO_ROOT, a22.DRY_RUN, a22.send_document, a22.LEDGER_FILE = orig
