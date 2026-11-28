# -*- coding: utf-8 -*-
"""Regression suite for Phase 2 Production Stabilization fixes."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_agent(prefix: str):
    name = f"stab_agent_{prefix}"
    if name in sys.modules:
        return sys.modules[name]
    path = next((ROOT / "agents").glob(f"{prefix}_*.py"))
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class TestPhase1TruncatedDanglingSentenceFix:
    def test_qa_blocks_sentence_ending_in_rupaye(self):
        a19 = _load_agent("19")
        rep = a19.QAReport("test.pdf")
        pdf_text = (
            "1. विकास परियोजनाओं का शुभारंभ\n"
            "• प्रधानमंत्री ने विभिन्न विकास परियोजनाओं को समर्पित किया जिनकी लागत लगभग रुपये।\n"
            "Exam Angle\n"
            "कृषि क्षेत्र के लिए महत्वपूर्ण।\n"
        )
        a19.check_editorial_quality(rep, pdf_text)
        assert any(i.code == "truncated_dangling_sentence" and i.severity == "error" for i in rep.issues)

        # Also block narrative sentence ending bare in "रुपये" at paragraph end without amount/wrap
        rep2 = a19.QAReport("test2.pdf")
        a19.check_editorial_quality(
            rep2,
            "• किसानों को सरकार द्वारा वितरित किए जाने वाले रुपये\n• अगली खबर यहाँ शुरू होती है।\n",
        )
        assert any(i.code == "truncated_dangling_sentence" and i.severity == "error" for i in rep2.issues)

    def test_qa_blocks_sentence_ending_in_ke_liye(self):
        a19 = _load_agent("19")
        rep = a19.QAReport("test.pdf")
        a19.check_editorial_quality(
            rep,
            "• सरकार ने किसानों की आय दोगुनी करने के लिए।\n• अगली योजना शुरू हुई।\n",
        )
        assert any(i.code == "truncated_dangling_sentence" and i.severity == "error" for i in rep.issues)

    def test_qa_blocks_incomplete_hindi_fragment(self):
        a19 = _load_agent("19")
        rep = a19.QAReport("test.pdf")
        a19.check_editorial_quality(
            rep,
            "• नई कृषि निर्यात नीति के अंतर्गत और\n\nExam Fact\n• संस्थान – आईसीएआर\n",
        )
        assert any(i.code == "truncated_dangling_sentence" and i.severity == "error" for i in rep.issues)

    def test_qa_allows_valid_monetary_sentence_containing_rupaye_wrapped_or_inline(self):
        a19 = _load_agent("19")
        rep = a19.QAReport("test.pdf")
        valid_pdf_text = (
            "• पीएम-किसान योजना के तहत प्रति परिवार 5 लाख रुपये की स्वास्थ्य सहायता प्रदान की गई।\n"
            "• केंद्र सरकार ने वैशाली परियोजना के लिए 34,470 करोड़ रुपये\n"
            "की विकास निधि स्वीकृत की है।\n"
            "(B) 5 लाख रुपये\n"
        )
        a19.check_editorial_quality(rep, valid_pdf_text)
        assert not any(i.code == "truncated_dangling_sentence" for i in rep.issues)

    def test_qa_allows_intentional_cover_ellipsis(self):
        a19 = _load_agent("19")
        rep = a19.QAReport("test.pdf")
        full_en = "Prime Minister Modi Launches Soil Health Mission Nationwide Across Districts"
        pdf_text = (
            "Inside This Issue\n"
            "• Prime Minister Modi Launches Soil Health Mission…\n\n"
            f"Story 1\n{full_en}\n"
            "किसानों के लिए मृदा स्वास्थ्य कार्ड जारी किए गए।\n"
        )
        a19.check_headline_clipping(
            rep,
            pdf_text,
            [{
                "headline_en": full_en,
                "headline_hi": "प्रधानमंत्री मोदी ने राष्ट्रव्यापी मृदा स्वास्थ्य मिशन शुरू किया",
            }],
        )
        a19.check_editorial_quality(rep, pdf_text)
        assert not any(i.code in ("clipped_headline", "truncated_dangling_sentence") for i in rep.issues)

    def test_qa_allows_valid_short_one_liner(self):
        a19 = _load_agent("19")
        rep = a19.QAReport("test.pdf")
        a19.check_editorial_quality(
            rep,
            "One-Liners\n1. आरबीआई ने रेपो दर 6.5 प्रतिशत पर अपरिवर्तित रखी।\n"
            "2. किसानों को 6,000 रुपये प्रति वर्ष सहायता मिलती है।\n",
        )
        assert not any(i.code == "truncated_dangling_sentence" for i in rep.issues)

    def test_upstream_sanitizer_and_content_do_not_cut_rs_amounts(self):
        from pipeline.content import extract_key_points
        from pipeline.content_sanitizer import repair_dangling_sentence

        # Sentence with Rs. inside must not be split or mangled
        item = {
            "headline_en": "Cabinet approves Rs. 500 crore soil health scheme for farmers",
            "raw_facts": "The Union Cabinet approved projects worth around Rs. 500 crore across 12 states for soil testing.",
        }
        kps = extract_key_points(item)
        assert any("500 crore" in kp for kp in kps)
        assert not any(kp.rstrip(".").endswith("Rs") for kp in kps)

        # Unrepairable dangling Hindi fragment drops cleanly when requested instead of persisting
        assert repair_dangling_sentence("योजना की लागत लगभग रुपये", drop_if_unrepairable=True) == ""
        # Prefix complete sentence is preserved instead of chopping numeric currency
        kept = repair_dangling_sentence(
            "सरकार ने 500 करोड़ रुपये की योजना शुरू की। परियोजना की लागत लगभग रुपये",
            drop_if_unrepairable=True,
        )
        assert kept == "सरकार ने 500 करोड़ रुपये की योजना शुरू की।"


class TestPhase3FaultInjectionAndRecovery:
    """12 deterministic fault-injection scenarios across routing, editorial, PDF, supervisor, and Telegram."""

    def test_01_gemini_429_rotates_slot_and_falls_back(self, tmp_path, monkeypatch):
        from pipeline import ai_router

        monkeypatch.setenv("ALP_AI_HEALTH_FILE", str(tmp_path / "health.json"))
        monkeypatch.setenv("ALP_AI_USAGE_LOG", str(tmp_path / "usage.jsonl"))
        monkeypatch.setenv("ALP_PROVIDER_HEALTH_PATH", str(tmp_path / "provider_health.json"))
        monkeypatch.setenv("ALP_PROVIDER_SUMMARY_PATH", str(tmp_path / "provider_summary.json"))
        monkeypatch.setenv("ALP_MODEL_AUTO_DISCOVERY", "0")
        monkeypatch.setenv("ALP_AI_CALL_INTERVAL", "0")
        monkeypatch.setenv("GEMINI_API_KEY", "AIzaFakeSlot0Key0000000000000000")
        monkeypatch.setenv("GEMINI_API_KEY_1", "AIzaFakeSlot1Key0000000000000000")
        monkeypatch.setenv("GROQ_API_KEY", "gsk_fakeslot0_000000000000000000")
        monkeypatch.setenv("DRY_RUN", "0")
        ai_router.reset()

        calls = []

        def _fake_call(provider, prompt, task, needs_hindi, response_format, system_prompt):
            calls.append((provider.name, provider.current_slot))
            if provider.name == "gemini":
                return None, "rate_limit"
            return "पर्यावरण संरक्षण के लिए नई पहल शुरू की गई।", None

        monkeypatch.setattr(ai_router, "_call_provider", _fake_call)
        try:
            out = ai_router.route("Translate soil scheme news", task="translation")
            assert out and "पर्यावरण" in out
            assert any(p == "gemini" and s == "gemini:GEMINI_API_KEY" for p, s in calls)
            assert any(p == "gemini" and s == "gemini:GEMINI_API_KEY_1" for p, s in calls)
            assert ("groq", "groq:GROQ_API_KEY") in calls
        finally:
            ai_router.reset()

    def test_02_provider_timeout_backoff_and_healer_routing(self, tmp_path):
        a25 = _load_agent("25")
        cat = a25.classify_failure("Read timed out after 30s (504 gateway timeout)")
        assert cat == "api_timeout"
        res = a25.execute_rule_based_recovery("daily_2026-11-28", cat, "Read timed out", state_dir=tmp_path)
        assert res["status"] == "recovered"
        assert res["backoff_seconds"] == 5.0
        assert res["resume_stage"] == "last_completed_checkpoint"

    def test_03_invalid_json_preserves_state_and_does_not_corrupt(self, tmp_path):
        import json as _json
        a25 = _load_agent("25")
        valid_jobs = {"daily_2026-11-28": {"status": "success"}}
        (tmp_path / "jobs.json").write_text(_json.dumps(valid_jobs), encoding="utf-8")
        cat = a25.classify_failure("JSONDecodeError: Expecting value: line 1 column 1 in LLM output")
        assert cat == "state_corruption"
        res = a25.execute_rule_based_recovery("daily_2026-11-28", cat, "JSONDecodeError in LLM", state_dir=tmp_path)
        assert res["status"] == "recovered"
        assert _json.loads((tmp_path / "jobs.json").read_text(encoding="utf-8")) == valid_jobs

    def test_04_empty_source_article_skipped_safely(self):
        from pipeline.content import _build_entry
        stats = {"total_items": 1, "ai_passed": 0, "ai_failed": 0, "deterministic_fallback": 0, "untranslated": 0, "skipped_items": 0}
        assert _build_entry({"headline_en": "", "raw_facts": ""}, stats) is None
        assert _build_entry({"headline_en": "Short", "raw_facts": ""}, stats) is None

    def test_05_missing_news_image_falls_back_gracefully_in_pdf_qa(self, tmp_path):
        from src.generate_pdf import generate_pdf
        a19 = _load_agent("19")
        pdf_path = tmp_path / "missing_img.pdf"
        content = {
            "edition_title": "Daily Current Affairs",
            "items": [{
                "event_id": "img-missing-1",
                "category": "Agriculture",
                "headline_en": "Union Government Approves Integrated Fertilizer Subsidy Release Across States",
                "headline_hi": "केंद्र सरकार ने राज्यों में एकीकृत उर्वरक सब्सिडी जारी करने को मंजूरी दी",
                "summary_en": "The Ministry of Chemicals and Fertilizers released Rs. 1,500 crore for Kharif distribution.",
                "summary_hi": "रसायन एवं उर्वरक मंत्रालय ने खरीफ वितरण के लिए 1,500 करोड़ रुपये जारी किए।",
                "key_points_en": ["The Ministry of Chemicals and Fertilizers released Rs. 1,500 crore for Kharif distribution."],
                "key_points_hi": ["रसायन एवं उर्वरक मंत्रालय ने खरीफ वितरण के लिए 1,500 करोड़ रुपये जारी किए।"],
                "detailed_explanation_en": "The Ministry of Chemicals and Fertilizers released Rs. 1,500 crore across major agricultural districts.",
                "detailed_explanation_hi": "रसायन एवं उर्वरक मंत्रालय ने प्रमुख कृषि जिलों में 1,500 करोड़ रुपये जारी किए।",
                "image_path": str(tmp_path / "nonexistent_photo.jpg"),
            }],
        }
        mcqs = [{
            "event_id": "img-missing-1",
            "question_en": "Which ministry released Rs. 1,500 crore for Kharif fertilizer distribution?",
            "question_hi": "खरीफ उर्वरक वितरण के लिए किस मंत्रालय ने 1,500 करोड़ रुपये जारी किए?",
            "options": ["Ministry of Chemicals and Fertilizers", "Ministry of Finance", "Ministry of Textiles", "Ministry of Defence"],
            "answer": "Ministry of Chemicals and Fertilizers",
            "explanation_en": "The Ministry of Chemicals and Fertilizers released Rs. 1,500 crore for Kharif distribution.",
            "explanation_hi": "रसायन एवं उर्वरक मंत्रालय ने खरीफ वितरण के लिए 1,500 करोड़ रुपये जारी किए।",
        }]
        generate_pdf(content, mcqs, str(pdf_path), edition_date="2026-11-28", edition_type="daily")
        assert pdf_path.is_file() and pdf_path.stat().st_size > 1000
        rep = a19.QAReport(str(pdf_path))
        a19.check_editorial_quality(rep, "Daily Edition")
        assert not any(i.severity == "error" for i in rep.issues)

    def test_06_broken_hindi_unicode_detected_and_blocked(self):
        from pipeline.hindi_editor import review_hindi_line
        from pipeline.completeness import validate_content_completeness
        rev = review_hindi_line("Scheme launched", "योजना \ufffd शुरू की गई")
        assert rev["critical"] is True
        comp = validate_content_completeness({
            "items": [{
                "event_id": "u1",
                "headline_en": "Cabinet approved agricultural credit reform",
                "headline_hi": "मंत्रिमंडल ने कृषि साख \ufffd सुधार को मंजूरी दी",
                "key_points_en": ["Cabinet cleared reform."],
                "key_points_hi": ["मंत्रिमंडल ने सुधार को मंजूरी दी।"],
            }]
        })
        assert comp.passed is False
        assert any(i.code == "corrupt_hindi_unicode" for i in comp.issues)

    def test_07_wrong_mcq_answer_detected_and_routed_to_mcq_generator(self, tmp_path):
        from pipeline.supervisor import MasterSupervisor
        from pipeline.mcq_examiner import examine_mcq
        bad_mcq = {
            "question_en": "Which institution launched the soil carbon portal?",
            "question_hi": "मृदा कार्बन पोर्टल किस संस्थान ने लॉन्च किया?",
            "options": ["ICAR", "NABARD", "FCI", "APEDA"],
            "options_hi": ["ICAR", "NABARD", "FCI", "APEDA"],
            "answer": "ISRO",  # Not even in options!
            "explanation_en": "ISRO launched the portal.",
            "explanation_hi": "ISRO ने पोर्टल लॉन्च किया।",
        }
        res = examine_mcq(bad_mcq)
        assert res["passed"] is False and any("answer" in str(e).lower() for e in res["critical_errors"])
        sup = MasterSupervisor(tmp_path, "daily_2026-11-28", "daily", "2026-11-28")
        assert sup._infer_qa_repair_target({"issues": [{"code": "answer_key_mismatch", "severity": "error"}]}) == "16_mcq_generator"

    def test_08_corrupt_pdf_detected_and_routed_to_pdf_design(self, tmp_path):
        from pipeline.supervisor import MasterSupervisor
        a19 = _load_agent("19")
        bad_pdf = tmp_path / "corrupt.pdf"
        bad_pdf.write_bytes(b"NOT_A_VALID_PDF")
        rep = a19.run_qa(bad_pdf)
        assert rep.passed is False
        sup = MasterSupervisor(tmp_path, "daily_2026-11-28", "daily", "2026-11-28")
        assert sup._infer_qa_repair_target({"issues": [{"code": "corrupt_pdf", "severity": "error"}]}) == "18_pdf_design"

    def test_09_clipped_headline_detected_and_routed_to_content_editor(self, tmp_path):
        from pipeline.supervisor import MasterSupervisor
        a19 = _load_agent("19")
        rep = a19.QAReport("test.pdf")
        a19.check_headline_clipping(
            rep,
            "STORY 1\nCabinet Approves Scheme For...",
            [{"headline_en": "Cabinet Approves Scheme For..."}],
        )
        assert any(i.code == "clipped_headline" and i.severity == "error" for i in rep.issues)
        sup = MasterSupervisor(tmp_path, "daily_2026-11-28", "daily", "2026-11-28")
        assert sup._infer_qa_repair_target({"issues": [{"code": "clipped_headline", "severity": "error"}]}) == "12_content_editor"

    def test_10_stale_qa_report_hash_mismatch_blocks_release(self, tmp_path):
        import hashlib, json as _json
        from pipeline.supervisor import MasterSupervisor
        pdf_path = tmp_path / "output" / "daily_2026-11-28.pdf"
        qa_path = tmp_path / "logs" / "qa" / "daily_2026-11-28_qa.json"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        qa_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_path.write_bytes(b"%PDF-1.4\nfresh-pdf-bytes")
        qa_path.write_text(_json.dumps({
            "job_id": "daily_2026-11-28",
            "passed": True,
            "file_sha256": hashlib.sha256(b"%PDF-1.4\nstale-old-bytes").hexdigest(),
            "issues": [],
        }), encoding="utf-8")
        sup = MasterSupervisor(tmp_path, "daily_2026-11-28", "daily", "2026-11-28")
        dec = sup.issue_release_decision(strict_files=True)
        assert dec["approved"] is False
        assert any("hash does not match" in r for r in dec["reasons"])
        assert sup._infer_qa_repair_target({"issues": [{"code": "stale_qa_report", "severity": "error"}]}) == "19_pdf_qa"

    def test_11_telegram_api_failure_marks_uncertain_and_blocks_blind_resend(self, tmp_path, monkeypatch):
        import hashlib, json as _json
        import requests
        a19 = _load_agent("19")
        a22 = _load_agent("22")
        a25 = _load_agent("25")
        pdf = tmp_path / "output" / "daily_2026-11-28.pdf"
        pdf.parent.mkdir(parents=True)
        pdf.write_bytes(b"%PDF-1.4\nbody")
        sha = hashlib.sha256(b"%PDF-1.4\nbody").hexdigest()
        qa = tmp_path / "logs" / "qa" / "daily_2026-11-28_qa.json"
        qa.parent.mkdir(parents=True)
        sig = a19.release_signature_for("daily_2026-11-28", sha, True, True)
        qa.write_text(_json.dumps({
            "job_id": "daily_2026-11-28", "passed": True, "file_sha256": sha,
            "issues": [], "release_approval": {"approved": True, "visual_passed": True, "signature": sig},
        }), encoding="utf-8")
        (tmp_path / "data" / "content").mkdir(parents=True)
        (tmp_path / "data" / "content" / "daily_2026-11-28.json").write_text(
            _json.dumps({"items": [{"needs_review": False, "verification_passed": True}]}),
            encoding="utf-8",
        )
        ledger_path = tmp_path / "state" / "published_events.json"
        ledger_path.parent.mkdir(parents=True)

        orig = (a22.REPO_ROOT, a22.DRY_RUN, a22.send_document, a22.LEDGER_FILE, a22.TELEGRAM_CHAT_ID)
        a22.REPO_ROOT = tmp_path
        a22.DRY_RUN = False
        a22.LEDGER_FILE = ledger_path
        a22.TELEGRAM_CHAT_ID = "-100123456"

        def _timeout_post(*a, **kw):
            raise requests.Timeout("Telegram read timed out")

        a22.send_document = _timeout_post
        try:
            monkeypatch.setenv("ALP_PUBLISHED_PATH", str(ledger_path))
            monkeypatch.setenv("DRY_RUN", "0")
            monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "dummy-token")
            monkeypatch.setenv("TELEGRAM_CHAT_ID", "-100123456")
            ledger = {"records": {}}
            ok = a22.publish_pdf(pdf, ledger)
            assert ok is False
            assert any(r.get("status") == "uncertain" for r in (ledger.get("records") or {}).values())
            # Retry while uncertain must stay blocked without hitting Telegram
            called = []
            a22.send_document = lambda *a, **kw: called.append(1) or {"ok": True}
            assert a22.publish_pdf(pdf, ledger) is False
            assert called == []
            assert a25.classify_failure("Publication outcome uncertain") == "telegram_upload_failure"
        finally:
            a22.REPO_ROOT, a22.DRY_RUN, a22.send_document, a22.LEDGER_FILE, a22.TELEGRAM_CHAT_ID = orig

    def test_12_duplicate_publication_attempt_blocked_with_zero_api_calls(self, tmp_path, monkeypatch):
        import hashlib, json as _json
        a19 = _load_agent("19")
        a22 = _load_agent("22")
        pdf = tmp_path / "output" / "daily_2026-11-28.pdf"
        pdf.parent.mkdir(parents=True)
        pdf.write_bytes(b"%PDF-1.4\nbody")
        sha = hashlib.sha256(b"%PDF-1.4\nbody").hexdigest()
        qa = tmp_path / "logs" / "qa" / "daily_2026-11-28_qa.json"
        qa.parent.mkdir(parents=True)
        sig = a19.release_signature_for("daily_2026-11-28", sha, True, True)
        qa.write_text(_json.dumps({
            "job_id": "daily_2026-11-28", "passed": True, "file_sha256": sha,
            "issues": [], "release_approval": {"approved": True, "visual_passed": True, "signature": sig},
        }), encoding="utf-8")
        ledger_path = tmp_path / "state" / "published_events.json"
        ledger_path.parent.mkdir(parents=True)
        ledger = {
            "version": 1,
            "records": {
                "rec-1": {
                    "job_id": "daily_2026-11-28",
                    "chat_id": "-100123456",
                    "message_id": 999,
                    "file_hash": sha[:16],
                    "file_sha256": sha,
                    "status": "success",
                    "dry_run": False,
                }
            },
        }
        called = []
        orig = (a22.REPO_ROOT, a22.DRY_RUN, a22.send_document, a22.LEDGER_FILE, a22.TELEGRAM_CHAT_ID)
        a22.REPO_ROOT = tmp_path
        a22.DRY_RUN = False
        a22.LEDGER_FILE = ledger_path
        a22.TELEGRAM_CHAT_ID = "-100123456"
        a22.send_document = lambda *a, **kw: called.append(1) or {"ok": True}
        (tmp_path / "data" / "content").mkdir(parents=True)
        (tmp_path / "data" / "content" / "daily_2026-11-28.json").write_text(
            _json.dumps({"items": [{"needs_review": False, "verification_passed": True}]}),
            encoding="utf-8",
        )
        try:
            monkeypatch.setenv("ALP_PUBLISHED_PATH", str(ledger_path))
            monkeypatch.setenv("DRY_RUN", "0")
            res = a22.publish_pdf(pdf, ledger)
            assert res is False  # duplicate live send blocked cleanly without allow_revision
            assert called == []
        finally:
            a22.REPO_ROOT, a22.DRY_RUN, a22.send_document, a22.LEDGER_FILE, a22.TELEGRAM_CHAT_ID = orig

    def test_health_dashboard_script_executes_without_secrets(self, tmp_path):
        from scripts.production_health_report import collect_production_health, write_outputs
        health = collect_production_health(ROOT)
        assert "daily" in health["workflows"]
        assert "publication_ledger" in health
        jp = tmp_path / "h.json"
        cp = tmp_path / "h.csv"
        mp = tmp_path / "h.md"
        write_outputs(health, json_path=jp, csv_path=cp, md_path=mp)
        assert jp.is_file() and cp.is_file() and mp.is_file()
        assert "TELEGRAM_BOT_TOKEN" not in mp.read_text(encoding="utf-8")

