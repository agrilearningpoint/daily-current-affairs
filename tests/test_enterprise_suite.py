#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enterprise Automated Test Suite (25 Categories + 15 Simulated Failure Scenarios)
================================================================================
Covers every requirement in Master Spec Section 18 & Section 22.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _load(mod_name: str, rel_path: str):
    spec = importlib.util.spec_from_file_location(mod_name, str(REPO_ROOT / rel_path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod.__name__] = mod
    spec.loader.exec_module(mod)
    return mod


windows = _load("windows", "pipeline/windows.py")
store = _load("store", "pipeline/store.py")
source_fetch = _load("source_fetch", "pipeline/01_source_fetch.py")
fact_ver = _load("fact_ver", "agents/04_fact_verification.py")
ai_router = _load("ai_router", "pipeline/ai_router.py")
mcq_gen = _load("mcq_gen", "agents/16_mcq_generator.py")
mcq_val = _load("mcq_val", "agents/17_mcq_validator.py")
pdf_gen = _load("pdf_gen", "src/generate_pdf.py")
pdf_qa = _load("pdf_qa", "agents/19_pdf_qa.py")
tg_pub = _load("tg_pub", "agents/22_telegram_publisher.py")
tg_pin = _load("tg_pin", "agents/23_telegram_pin_verifier.py")
health_audit = _load("health_audit", "agents/24_final_health_audit.py")
auto_healer = _load("auto_healer", "agents/25_auto_healer.py")
verify_keys = _load("verify_keys", "scripts/verify_keys.py")


class TestEnterprisePlatform(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    # 1. API key rotation (Simulated: GEMINI_API_KEY_1 returns 429 -> rotates to GEMINI_API_KEY_2)
    def test_01_api_key_rotation_on_429(self):
        env = {"GEMINI_API_KEY_1": "k1", "GEMINI_API_KEY_2": "k2"}
        calls = []

        def mock_transport(provider, key_id, model, prompt):
            calls.append(key_id)
            if key_id == "GEMINI_API_KEY_1":
                return 429, "Rate limit exceeded", {"Retry-After": "120"}
            return 200, '{"title": "Clean", "summary": "Verified summary"}', {}

        router = ai_router.KeyPoolRouter(env=env, health_path=self.tmp_path / "api.json", transport=mock_transport)
        out = router.complete("Test prompt", task="edit")
        self.assertIsNotNone(out)
        self.assertEqual(calls, ["GEMINI_API_KEY_1", "GEMINI_API_KEY_2"])

    # 2. Provider fallback (Simulated: All Gemini keys return 429 -> falls back to Groq)
    def test_02_provider_fallback_gemini_to_groq(self):
        env = {"GEMINI_API_KEY_1": "g1", "GEMINI_API_KEY_2": "g2", "GROQ_API_KEY_1": "gr1"}
        calls = []

        def mock_transport(provider, key_id, model, prompt):
            calls.append((provider, key_id))
            if provider == "gemini":
                return 429, "Quota exhausted", {}
            return 200, "Translated Hindi text", {}

        router = ai_router.KeyPoolRouter(env=env, health_path=self.tmp_path / "api.json", transport=mock_transport)
        out = router.complete("Translate", task="hindi_translation")
        self.assertEqual(out, "Translated Hindi text")
        self.assertEqual(calls[-1], ("groq", "GROQ_API_KEY_1"))

    # 3. Rate-limit handling & Retry-After header respect
    def test_03_rate_limit_retry_after_header(self):
        cd = ai_router.compute_cooldown_seconds("rate_limit_429", 1, retry_after_header="90")
        self.assertEqual(cd, 90)

    # 4. Cooldown persistence across router restarts
    def test_04_cooldown_persistence_across_restarts(self):
        env = {"GEMINI_API_KEY_1": "g1", "GROQ_API_KEY_1": "gr1"}
        h_file = self.tmp_path / "api_persist.json"
        now = datetime(2026, 11, 13, 10, 0, tzinfo=timezone.utc)
        r1 = ai_router.KeyPoolRouter(env=env, health_path=h_file)
        r1.record_failure({"provider": "gemini", "key_id": "GEMINI_API_KEY_1"}, 429, "Rate limit", retry_after="300", now_utc=now)

        # New instance loads persisted cooldown state
        r2 = ai_router.KeyPoolRouter(env=env, health_path=h_file)
        self.assertFalse(r2.is_key_eligible({"provider": "gemini", "key_id": "GEMINI_API_KEY_1"}, now + timedelta(seconds=60)))
        self.assertTrue(r2.is_key_eligible({"provider": "gemini", "key_id": "GEMINI_API_KEY_1"}, now + timedelta(seconds=360)))

    # 5. RSS collection & ETag 304 caching
    def test_05_rss_collection_and_etag_304_cache(self):
        rss_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0"><channel><title>PIB</title>
        <item>
          <title>Cabinet approves PM Vidyalaxmi and Agri Infrastructure Expansion</title>
          <link>https://pib.gov.in/PressReleasePage.aspx?PRID=2099991</link>
          <description>Cabinet approved Rs 3,600 crore outlay for rural agriculture institutes.</description>
          <pubDate>Fri, 13 Nov 2026 11:00:00 +0530</pubDate>
        </item></channel></rss>"""
        src = {
            "source_id": "test_pib",
            "source_name": "PIB",
            "url": "https://pib.gov.in/rss",
            "domain": "pib.gov.in",
            "category": "Agriculture & Rural Development",
            "reliability_level": "tier1_official",
        }
        health = {}
        now = datetime(2026, 11, 13, 6, 0, tzinfo=timezone.utc)
        items1 = source_fetch.fetch_single_source(
            src, health, now, http_getter=lambda u, h, t: (200, rss_xml, {"etag": '"v1"'})
        )
        self.assertEqual(len(items1), 1)
        self.assertEqual(health["test_pib"]["etag"], '"v1"')

        # Second call returns 304 Not Modified -> serves cached items
        items2 = source_fetch.fetch_single_source(
            src, health, now, http_getter=lambda u, h, t: (304, b"", {})
        )
        self.assertEqual(len(items2), 1)

    # 6. Dead-feed quarantine after 3 consecutive failures (403/timeout) & auto-recovery
    def test_06_dead_feed_quarantine_and_recovery(self):
        src = {"source_id": "dead_feed", "source_name": "Dead", "url": "https://example.com/rss"}
        health = {}
        now = datetime(2026, 11, 13, 6, 0, tzinfo=timezone.utc)

        def fail_getter(u, h, t):
            raise TimeoutError("RSS timeout")

        for _ in range(3):
            source_fetch.fetch_single_source(src, health, now, http_getter=fail_getter, max_retries=0)

        self.assertTrue(source_fetch.is_feed_quarantined(health["dead_feed"], now + timedelta(hours=2)))
        # Auto-recovers after 24 hours
        self.assertFalse(source_fetch.is_feed_quarantined(health["dead_feed"], now + timedelta(hours=25)))

    # 7. Strict 24-hour IST date filtering (rejects previous-window & missing timestamps)
    def test_07_strict_24h_ist_date_filtering(self):
        win = windows.compute_edition_window("2026-11-14", cutoff_hhmm="06:00")
        raw = [
            {"title": "Inside window story on ICAR wheat variety", "original_published_at": "2026-11-13T14:30:00+05:30"},
            {"title": "Stale story before 06:00 IST cutoff", "original_published_at": "2026-11-13T05:59:00+05:30"},
            {"title": "Story with missing timestamp", "updated_at": "2026-11-13T15:00:00+05:30"},
        ]
        accepted, rejected, quarantined = windows.filter_articles_by_window(raw, win)
        self.assertEqual(len(accepted), 1)
        self.assertEqual(len(rejected), 1)
        self.assertEqual(len(quarantined), 1)

    # 8. Timezone conversion & midnight boundary accuracy (UTC -> Asia/Kolkata)
    def test_08_timezone_conversion_midnight_boundary(self):
        # 2026-11-13 00:30 UTC is 2026-11-13 06:00 IST (exact start of 2026-11-14 window)
        win = windows.compute_edition_window("2026-11-14", cutoff_hhmm="06:00")
        dt_utc = datetime(2026, 11, 13, 0, 30, 0, tzinfo=timezone.utc)
        self.assertTrue(win.contains(dt_utc))
        dt_before = datetime(2026, 11, 13, 0, 29, 59, tzinfo=timezone.utc)
        self.assertFalse(win.contains(dt_before))

    # 9. News deduplication (Canonical URL & Normalized Headline)
    def test_09_news_deduplication_url_and_headline(self):
        u1 = store.canonicalize_url("http://www.pib.gov.in/PressRelease?PRID=100&utm_source=twitter")
        u2 = store.canonicalize_url("https://pib.gov.in/PressRelease?PRID=100&fbclid=xyz")
        self.assertEqual(u1, u2)

    # 10. Event deduplication across multiple outlets covering the same government scheme
    def test_10_multi_outlet_same_event_deduplication(self):
        candidates = [
            {
                "headline_en": "Cabinet approves PM Dhan-Dhaanya Krishi Yojana with Rs 24,000 crore outlay",
                "summary_en": "Union Cabinet approved PM Dhan-Dhaanya Krishi Yojana covering 100 agricultural districts.",
                "link": "https://pib.gov.in/release/1",
                "source_name": "PIB",
            },
            {
                "headline_en": "PM Dhan-Dhaanya Krishi Yojana approved by Cabinet with ₹24,000 crore outlay - The Hindu",
                "summary_en": "The government cleared the PM Dhan-Dhaanya Krishi Yojana with Rs 24000 crore for 100 districts.",
                "link": "https://thehindu.com/news/article1",
                "source_name": "The Hindu",
            },
        ]
        kept, dropped = store.deduplicate_news_4layer(candidates, "2026-11-13", history_path=self.tmp_path / "nh.json")
        self.assertEqual(len(kept), 1)
        self.assertEqual(len(dropped), 1)

    # 11. Historical news comparison (prevents re-publishing across days unless verified update)
    def test_11_historical_news_comparison_and_verified_update(self):
        h_path = self.tmp_path / "nh_hist.json"
        day1 = [{
            "headline_en": "NABARD launches Rural Climate Resilience Fund of Rs 5,000 crore",
            "summary_en": "NABARD announced a Rs 5,000 crore fund for climate-smart agriculture.",
            "link": "https://nabard.org/news/101",
        }]
        kept1, _ = store.deduplicate_news_4layer(day1, "2026-11-12", history_path=h_path)
        self.assertEqual(len(kept1), 1)

        # Day 2 repeat without update is blocked
        kept2, dropped2 = store.deduplicate_news_4layer(day1, "2026-11-13", history_path=h_path)
        self.assertEqual(len(kept2), 0)
        self.assertEqual(len(dropped2), 1)

        # Day 3 genuinely new verified update is allowed
        day3_update = [{
            "headline_en": "NABARD expands Rural Climate Resilience Fund with Phase-II guidelines",
            "summary_en": "New Phase-II operational guidelines issued.",
            "link": "https://nabard.org/news/101",
            "is_verified_update": True,
        }]
        kept3, _ = store.deduplicate_news_4layer(day3_update, "2026-11-14", history_path=h_path)
        self.assertEqual(len(kept3), 1)
        self.assertEqual(kept3[0].get("update_badge"), "VERIFIED UPDATE")

    # 12. Fact verification & inter-source contradiction quarantine
    def test_12_fact_verification_and_contradiction_quarantine(self):
        items = [
            {
                "headline_en": "ICAR releases climate-resilient wheat variety HD-3410 with 65 quintal/ha yield",
                "summary_en": "Ministry of Agriculture & Farmers Welfare and ICAR released HD-3410 in New Delhi with 65 quintal/ha yield.",
                "raw_evidence": "Ministry of Agriculture & Farmers Welfare and ICAR released HD-3410 in New Delhi with 65 quintal/ha yield.",
                "link": "https://icar.org.in/hd3410",
                "published_at_ist": "2026-11-13T10:00:00+05:30",
            },
            {
                "headline_en": "Disputed subsidy allocation report",
                "summary_en": "Scheme received Rs 1,500 crore allocation.",
                "raw_evidence": "Scheme received Rs 1,500 crore allocation.",
                "link": "https://example.com/s1",
                "corroborating_reports": [
                    {"headline_en": "Disputed subsidy", "summary_en": "Scheme received Rs 2,800 crore allocation.", "source_name": "SourceB"}
                ],
            },
        ]
        verified, quarantined = fact_ver.verify_and_record_facts(items, ledger_path=self.tmp_path / "facts.json")
        self.assertEqual(len(verified), 1)
        self.assertEqual(len(quarantined), 1)
        self.assertIn("source_contradiction", quarantined[0]["quarantine_reason"])

    # 13. Numerical data validation (blocks AI-invented numbers absent from source evidence)
    def test_13_numerical_hallucination_blocked(self):
        ok, bad = fact_ver.verify_claim_against_source(
            "The scheme outlay is Rs 12,500 crore covering 85% farmers.",
            "The scheme outlay is Rs 12,500 crore for small farmers.",
        )
        self.assertFalse(ok)
        self.assertIn("85", bad)

    # 14. MCQ uniqueness & permanent history persistence
    def test_14_mcq_uniqueness_and_permanent_history(self):
        h_file = self.tmp_path / "mcq_hist.json"
        item = {
            "event_id": "ev_icar_01",
            "headline_en": "ICAR develops genome-edited rice variety Pusa-DST1 for salinity tolerance",
            "headline_hi": "आईसीएआर ने लवणता सहिष्णुता के लिए जीनोम-संपादित धान किस्म पूसा-डीएसटी1 विकसित की",
            "summary_en": "ICAR developed Pusa-DST1 in New Delhi showing 25% higher yield under saline soil.",
            "summary_hi": "आईसीएआर ने नई दिल्ली में पूसा-डीएसटी1 विकसित की जो लवणीय मिट्टी में 25% अधिक उपज देती है।",
            "link": "https://icar.org.in/pusa-dst1",
            "category": "Agriculture & Rural Development",
            "structured_facts": {"who": "ICAR", "where": "New Delhi", "amounts": ["25%"], "schemes": ["Pusa-DST1"]},
        }
        res1 = mcq_gen.generate_mcqs_for_edition([item], "2026-11-13", history_path=h_file)
        self.assertEqual(res1["total_generated"], 1)
        saved = json.loads(h_file.read_text(encoding="utf-8"))
        self.assertEqual(len(saved["mcqs"]), 1)

    # 15. MCQ semantic deduplication (catches active/passive rewrites & reordered options)
    def test_15_mcq_semantic_rewrite_and_option_reorder_detection(self):
        q_a = {
            "question_en": "Which organization launched the PM Matsya Kisan Samridhi Sah-Yojana?",
            "options_en": ["NABARD", "ICAR", "Ministry of Fisheries", "RBI", "SEBI"],
            "answer_value": "Ministry of Fisheries",
            "fact_key": "org|ev_matsya|Ministry of Fisheries",
        }
        q_b = {
            "question_en": "PM Matsya Kisan Samridhi Sah-Yojana was introduced by which organization?",
            "options_en": ["SEBI", "RBI", "Ministry of Fisheries", "ICAR", "NABARD"],
            "answer_value": "Ministry of Fisheries",
            "fact_key": "org|ev_matsya_2|Ministry of Fisheries",
        }
        is_dup, reason = mcq_gen.is_duplicate_mcq(q_b, [q_a])
        self.assertTrue(is_dup)

    # 16. MCQ answer validation (rejects wrong answer key & broken templates)
    def test_16_mcq_independent_answer_validation(self):
        bad_mcq = {
            "question_en": "Which ministry launched the Digital Agriculture Mission?",
            "question_hi": "डिजिटल कृषि मिशन किस मंत्रालय ने शुरू किया?",
            "options_en": ["Ministry of Agriculture", "RBI", "SEBI", "ISRO", "DRDO"],
            "answer": "C",  # Points to SEBI instead of Ministry of Agriculture!
            "answer_value": "Ministry of Agriculture",
            "explanation_en": "Launched by Ministry of Agriculture with Rs 2,817 crore outlay.",
            "source_url": "https://pib.gov.in/digital-agri",
        }
        ok, errs = mcq_val.validate_single_mcq(bad_mcq)
        self.assertFalse(ok)
        self.assertTrue(any("answer_key_mismatch" in e for e in errs))

    # 17. Hindi translation validation (ensures Devanagari script presence)
    def test_17_hindi_translation_validation(self):
        self.assertEqual(pdf_gen._hi_or_blank("English text disguised as Hindi"), "")
        self.assertTrue(len(pdf_gen._hi_or_blank("प्रधानमंत्री किसान सम्मान निधि")) > 0)

    # 18, 19, 20. PDF rendering, Hindi font embedding, and PDF text extraction + QA pass
    def test_18_19_20_pdf_rendering_fonts_and_qa_gate(self):
        sample_items = []
        sample_mcqs = []
        topics = [
            ("Ministry of Agriculture approves Clean Plant Programme with ₹1,765.67 crore outlay",
             "कृषि मंत्रालय ने ₹1,765.67 करोड़ के परिव्यय के साथ क्लीन प्लांट प्रोग्राम को मंजूरी दी",
             "Agriculture & Rural Development", "Ministry of Agriculture & Farmers Welfare", "Maharashtra", "₹1,765.67 crore"),
            ("RBI Monetary Policy Committee keeps Repo Rate unchanged at 6.50% in Mumbai",
             "आरबीआई मौद्रिक नीति समिति ने मुंबई में रेपो दर को 6.50% पर अपरिवर्तित रखा",
             "Economy, Banking & Finance", "Reserve Bank of India (RBI)", "Maharashtra", "6.50%"),
            ("ISRO successfully launches NVS-02 navigation satellite aboard GSLV-F15 from Sriharikota",
             "इसरो ने श्रीहरिकोटा से जीएसएलवी-एफ15 द्वारा एनवीएस-02 नेविगेशन उपग्रह का सफल प्रक्षेपण किया",
             "Science & Technology", "ISRO", "Andhra Pradesh", "2,250 kg"),
            ("Uttar Pradesh Cabinet approves Mukhyamantri Yuva Udyami Vikas Abhiyan with ₹1,000 crore fund",
             "उत्तर प्रदेश कैबिनेट ने ₹1,000 करोड़ के कोष के साथ मुख्यमंत्री युवा उद्यमी विकास अभियान को मंजूरी दी",
             "Uttar Pradesh Special", "Uttar Pradesh Government", "Uttar Pradesh", "₹1,000 crore"),
            ("NABARD sanctions ₹1,972 crore under RIDF for rural irrigation projects in Rajasthan",
             "नाबार्ड ने राजस्थान में ग्रामीण सिंचाई परियोजनाओं के लिए आरआईडीएफ के तहत ₹1,972 करोड़ स्वीकृत किए",
             "Agriculture & Rural Development", "NABARD", "Rajasthan", "₹1,972 crore"),
            ("ICAR-IARI releases climate-resilient wheat variety HD-3385 for North Western Plains",
             "आईसीएआर-आईएआरआई ने उत्तर पश्चिमी मैदानों के लिए जलवायु-अनुकूली गेहूँ किस्म एचडी-3385 जारी की",
             "Agriculture & Rural Development", "ICAR", "New Delhi", "75.2 quintal/ha"),
            ("MoEFCC notifies 3 new Ramsar wetland sites taking India total to 85",
             "पर्यावरण मंत्रालय ने 3 नए रामसर आर्द्रभूमि स्थल अधिसूचित किए जिससे भारत में कुल संख्या 85 हुई",
             "Environment & Ecology", "MoEFCC", "Tamil Nadu", "85 sites"),
            ("DRDO successfully flight-tests Phase-II Ballistic Missile Defence interceptor from Odisha coast",
             "डीआरडीओ ने ओडिशा तट से चरण-II बैलिस्टिक मिसाइल रक्षा इंटरसेप्टर का सफल परीक्षण किया",
             "Defense & Security", "DRDO", "Odisha", "5,000 km"),
            ("NITI Aayog releases SDG India Index 2026 report; Uttarakhand and Kerala top composite rankings",
             "नीति आयोग ने एसडीजी इंडिया इंडेक्स 2026 रिपोर्ट जारी की; उत्तराखंड और केरल शीर्ष स्थान पर रहे",
             "Reports & Indices", "NITI Aayog", "Uttarakhand", "Score 79"),
            ("APEDA facilitates first commercial sea shipment of Indian pomegranates to Australia",
             "एपीडा ने ऑस्ट्रेलिया को भारतीय अनार की पहली वाणिज्यिक समुद्री खेप सुगम बनाई",
             "Agriculture & Rural Development", "APEDA", "Gujarat", "14 metric tonnes"),
        ]
        for i, (h_en, h_hi, cat, who, loc, amt) in enumerate(topics, 1):
            ev_id = f"ev_sample_{i:02d}"
            it = {
                "event_id": ev_id,
                "headline_en": h_en,
                "headline_hi": h_hi,
                "summary_en": (
                    f"{h_en}. Announced by {who} in {loc} with a verified benchmark figure of {amt}. "
                    f"This initiative strengthens rural infrastructure, institutional credit, and examination-relevant policy targets."
                ),
                "summary_hi": (
                    f"{h_hi}। {who} द्वारा {loc} में {amt} के सत्यापित मानक के साथ यह घोषणा की गई। "
                    f"यह पहल ग्रामीण बुनियादी ढांचे, संस्थागत ऋण और कृषि विकास को सुदृढ़ करती है।"
                ),
                "key_points_en": [
                    f"Nodal Authority & Announcement: {who} officially notified '{h_en}' during the current 24-hour IST window.",
                    f"Key Quantitative Benchmark: The verified allocation/parameter recorded in official releases is {amt} focusing on {loc}.",
                    f"Competitive Exam Relevance: Directly important for IBPS AFO, NABARD Grade A/B, UPSSSC AGTA, ICAR JRF, and State PCS.",
                ],
                "key_points_hi": [
                    f"नोडल प्राधिकरण एवं घोषणा: {who} ने वर्तमान 24-घंटे की आईएसटी विंडो में '{h_hi}' को आधिकारिक रूप से अधिसूचित किया।",
                    f"प्रमुख मात्रात्मक मानक: आधिकारिक विज्ञप्ति के अनुसार सत्यापित आँकड़ा/परिव्यय {amt} ({loc}) निर्धारित है।",
                    f"प्रतियोगी परीक्षा उपयोगिता: आईबीपीएस एएफओ, नाबार्ड, यूपीएसएसएससी एजीटीए और राज्य पीसीएस के लिए अत्यंत महत्वपूर्ण।",
                ],
                "static_gk": [
                    {"en": f"Nodal Institution / Ministry: {who} | Focus Region: {loc}", "hi": f"नोडल संस्थान / मंत्रालय: {who} | प्रमुख क्षेत्र: {loc}"},
                    {"en": f"Category: {cat} | Verified Parameter: {amt}", "hi": f"श्रेणी: {cat} | सत्यापित आँकड़ा: {amt}"},
                ],
                "recent_headlines": [
                    {"en": f"Earlier verified update under {cat}: Institutional credit and digital crop survey expanded across states.",
                     "hi": f"{cat} के अंतर्गत पूर्व सत्यापित अपडेट: राज्यों में संस्थागत ऋण और डिजिटल फसल सर्वेक्षण का विस्तार।"}
                ],
                "link": f"https://pib.gov.in/PressReleasePage.aspx?PRID=202611{i:02d}",
                "category": cat,
                "published_at_ist": "2026-11-13T11:30:00+05:30",
                "verification_status": "verified",
                "structured_facts": {"who": who, "where": loc, "amounts": [amt], "schemes": [h_en[:45]]},
            }
            sample_items.append(it)

        mcq_bundle = mcq_gen.generate_mcqs_for_edition(sample_items, "2026-11-13", history_path=self.tmp_path / "m_hist.json")
        valid_mcqs, rejected_mcqs = mcq_val.validate_mcq_batch(mcq_bundle["mcqs"], {x["event_id"]: x for x in sample_items})
        self.assertEqual(len(rejected_mcqs), 0, f"Rejected: {rejected_mcqs}")
        self.assertEqual(len(valid_mcqs), 10)

        out_pdf = self.tmp_path / "test_edition.pdf"
        content_payload = {"job_id": "daily_2026-11-13", "date": "13 November 2026", "items": sample_items}
        pdf_gen.generate_pdf(content_payload, valid_mcqs, output_path=str(out_pdf), date_str="13 November 2026")
        self.assertTrue(out_pdf.is_file())

        qa_rep = pdf_qa.run_qa(out_pdf, min_mcq_count=8, item_count=len(sample_items), selected_items=sample_items)
        self.assertTrue(qa_rep.passed, f"QA failed with issues: {qa_rep.issues}")
        self.assertGreaterEqual(qa_rep.page_count, 10)
        self.assertGreater(qa_rep.devanagari_chars, 500)

    # 21 & 22. Telegram timeout handling & publication reconciliation (prevents duplicate sends)
    def test_21_22_telegram_timeout_and_reconciliation(self):
        dummy_pdf = self.tmp_path / "sample.pdf"
        dummy_pdf.write_bytes(b"%PDF-1.4 sample content")
        ledger_file = self.tmp_path / "pub_ledger.json"

        # Simulate first upload timing out
        def timeout_sender(path, cap):
            raise TimeoutError("Telegram upload timed out after 60s")

        res1 = tg_pub.publish_edition_idempotent("daily_2026-11-13", dummy_pdf, "Caption", sender_fn=timeout_sender, ledger_path=ledger_file)
        self.assertEqual(res1["status"], "uncertain")

        # Simulate retry where channel_inspector discovers message 778899 already arrived on Telegram
        send_calls = []
        res2 = tg_pub.publish_edition_idempotent(
            "daily_2026-11-13",
            dummy_pdf,
            "Caption",
            sender_fn=lambda p, c: send_calls.append(1) or {"message_id": 999},
            channel_inspector=lambda jid, sha: 778899,
            ledger_path=ledger_file,
        )
        self.assertEqual(res2["status"], "published")
        self.assertEqual(res2["message_id"], 778899)
        self.assertTrue(res2["duplicate_prevented"])
        self.assertEqual(len(send_calls), 0)  # Never re-uploaded!

        # Verify pin status
        pin_res = tg_pin.verify_and_pin_message("daily_2026-11-13", 778899, pin_fn=lambda mid: True, pin_state_path=self.tmp_path / "pins.json")
        self.assertTrue(pin_res["pin_verified"])

    # 23 & 24. State integrity & corrupted state file quarantine/recovery
    def test_23_24_corrupted_state_recovery(self):
        corrupt_file = self.tmp_path / "jobs.json"
        corrupt_file.write_text("{broken json: [", encoding="utf-8")
        recovered = store.safe_read_json(corrupt_file, {"jobs": {}})
        self.assertEqual(recovered, {"jobs": {}})
        # Verify corrupt file was quarantined
        quarantined_files = list(self.tmp_path.glob("jobs.corrupt.*.json"))
        self.assertEqual(len(quarantined_files), 1)

    # 25. Autonomous self-healer classification, rule-based recovery & repair budget enforcement
    def test_25_auto_healer_classification_and_budget(self):
        cat = auto_healer.classify_failure("19_pdf_qa: failed: [ERROR] [edition_story_shortfall]")
        self.assertEqual(cat, "pdf_generation_failure")

        for attempt in range(1, 4):
            inc = auto_healer.execute_rule_based_recovery("daily_2026-11-13", cat, "shortfall", state_dir=self.tmp_path)
            self.assertEqual(inc["status"], "recovered")
            self.assertEqual(inc["attempt"], attempt)

        # 4th attempt exceeds MAX_REPAIR_ATTEMPTS (3) -> escalates instead of looping forever
        inc4 = auto_healer.execute_rule_based_recovery("daily_2026-11-13", cat, "shortfall", state_dir=self.tmp_path)
        self.assertEqual(inc4["status"], "escalated_budget_exhausted")

    # 26. Zero-exposure secret monitor verification
    def test_26_secret_monitor_never_exposes_key_values(self):
        fake_secret = "ghp_SUPER_SECRET_VALUE_DO_NOT_LEAK_99999"
        env = {"GEMINI_API_KEY": fake_secret, "GROQ_API_KEY": ""}
        report = verify_keys.check_secrets_safely(env=env, probe_fn=lambda p, v: (401, "API key expired"))
        serialized = json.dumps(report)
        self.assertNotIn(fake_secret, serialized)
        self.assertEqual(report[0]["error_category"], "expired_credential")


if __name__ == "__main__":
    unittest.main(verbosity=2)
