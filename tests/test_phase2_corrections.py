# -*- coding: utf-8 -*-
"""
Regression test suite for Second-Phase Correction & Premium PDF Quality Upgrade.
Covers all 12 defect areas from DEF-01 to DEF-12.
"""
import re
from typing import Any, Dict, List
import pytest

from pipeline.content import clean_hindi_editorial, _build_category_one_liners, exam_fact
from pipeline.mcq_builder import state_mcq, country_mcq
from pipeline.mcq_quality import quality_errors, PHRASE_RECOG_RE, HINDI_BROKEN_RE
from pipeline.mcq_schema import schema_errors
from pipeline.static_gk_db import lookup_static_gk_for_text
from src.generate_pdf import (
    BANNED_STATIC_GK_RE,
    _clean_one_liner_str,
    _build_gallery_table,
    _toc_story,
)


# 1. Table of Contents: 15 stories fit on one page without splitting onto page 3
def test_toc_layout_fits_one_page():
    units = [
        ({"headline_en": f"Story Title Number {i}", "headline_hi": f"कहानी शीर्षक संख्या {i}", "page_num": i + 3}, None)
        for i in range(1, 16)
    ]
    flowables = _toc_story(units, {}, "15 November 2026")
    from reportlab.platypus import PageBreak
    page_breaks = [f for f in flowables if isinstance(f, PageBreak)]
    assert len(page_breaks) == 1, "15 items should fit on single TOC page with exactly 1 trailing page break"

    # For >16 items, it should split evenly across 2 pages (1 internal break + 1 trailing break)
    units_20 = [
        ({"headline_en": f"Story Title Number {i}", "headline_hi": f"कहानी शीर्षक संख्या {i}", "page_num": i + 3}, None)
        for i in range(1, 21)
    ]
    flowables_20 = _toc_story(units_20, {}, "15 November 2026")
    page_breaks_20 = [f for f in flowables_20 if isinstance(f, PageBreak)]
    assert len(page_breaks_20) == 2, "20 items should split cleanly across 2 pages with 1 internal + 1 trailing PageBreak"


# 2. News in Pictures layout: 8 cards split 4+4, not 6+2
def test_news_in_pictures_balanced_grid():
    from src.generate_pdf import _news_in_pictures_story
    units = [
        (
            {
                "headline_en": f"Photo Story Headline {i}",
                "headline_hi": f"चित्र समाचार शीर्षक {i}",
                "image_path": "assets/logo.png",
                "category": "National",
            },
            None,
        )
        for i in range(1, 9)
    ]
    from reportlab.platypus import PageBreak, Table
    flowables = _news_in_pictures_story(units)
    tables = [f for f in flowables if isinstance(f, Table)]
    breaks = [f for f in flowables if isinstance(f, PageBreak)]
    # 8 items must yield exactly 2 tables (4 cards each in a 2x2 grid) and 2 page breaks
    assert len(tables) == 2, f"8 images should produce 2 balanced page tables, got {len(tables)}"
    assert len(breaks) == 2, f"Expected 2 page breaks for 2-page gallery, got {len(breaks)}"
    # Verify each table has 2 rows of 2 columns
    assert len(tables[0]._cellvalues) == 2, "Table 1 should have 2 rows (2x2 grid)"
    assert len(tables[1]._cellvalues) == 2, "Table 2 should have 2 rows (2x2 grid)"


# 3. Weak Export Growth MCQ: rejects phrase-matching questions
def test_export_growth_rejects_phrase_recognition():
    bad_mcq = {
        "type": "llm-schema",
        "question_en": "Which component is explicitly mentioned in the PIB release about the PM E-DRIVE Scheme?",
        "question_hi": "पीएम ई-ड्राइव योजना के बारे में पीआईबी विज्ञप्ति में किस घटक का स्पष्ट रूप से उल्लेख किया गया है?",
        "options": ["Subsidies", "Charging Infra", "Testing Agency", "Battery Standards", "Manufacturing Plants"],
        "options_hi": ["सब्सिडी", "चार्जिंग इंफ्रा", "परीक्षण एजेंसी", "बैटरी मानक", "विनिर्माण संयंत्र"],
        "correct": "A",
        "explanation_en": "Subsidies are mentioned in the release. The scheme provides financial assistance for electric vehicles. Multiple categories are covered.",
        "explanation_hi": "विज्ञप्ति में सब्सिडी का उल्लेख किया गया है। यह योजना इलेक्ट्रिक वाहनों के लिए वित्तीय सहायता प्रदान करती है। कई श्रेणियां शामिल हैं।",
        "explanation_pairs": [{"en": "Subsidies are mentioned in the release.", "hi": "विज्ञप्ति में सब्सिडी का उल्लेख है."}],
    }
    errs = schema_errors(bad_mcq, "Subsidies are mentioned in the release")
    assert any("phrase-recognition" in e for e in errs), "schema_errors should reject phrase-recognition questions"

    q_errs = quality_errors(bad_mcq, {}, "Subsidies are mentioned in the release")
    assert any("phrase-recognition" in e for e in q_errs), "quality_errors should reject phrase-recognition questions"


# 4. Broken Hindi MCQ test: rejects 'ने में' grammar
def test_broken_hindi_grammar_rejected():
    bad_mcq = {
        "type": "llm-schema",
        "question_en": "Which development was reviewed recently?",
        "question_hi": "डॉ. जितेंद्र सिंह ने में उत्साही भागीदारी के साथ विश्व मधुमेह दिवस मनाया — यह समाचार किससे संबंधित है?",
        "options": ["Option A", "Option B", "Option C", "Option D", "Option E"],
        "options_hi": ["विकल्प A", "विकल्प B", "विकल्प C", "विकल्प D", "विकल्प E"],
        "correct": "A",
        "explanation_en": "Review was conducted. Details were shared with stakeholders. Progress was noted.",
        "explanation_hi": "समीक्षा की गई थी। हितधारकों के साथ विवरण साझा किए गए। प्रगति दर्ज की गई।",
    }
    errs = quality_errors(bad_mcq, {}, "Review was conducted.")
    assert any("broken Hindi grammar" in e for e in errs), "quality_errors should detect 'ने में' broken construct"


# 5. Domestic news MCQ test: rejects country question for domestic Indian event
def test_domestic_news_rejects_country_mcq():
    ci = {
        "headline_en": "Union Minister Dr. Jitendra Singh Celebrates World Diabetes Day in New Delhi",
        "headline_hi": "केंद्रीय मंत्री डॉ. जितेंद्र सिंह ने नई दिल्ली में विश्व मधुमेह दिवस मनाया",
        "summary_en": "Union Minister Dr. Jitendra Singh addressed medical experts on World Diabetes Day.",
        "key_points_en": ["Minister urged public awareness regarding diabetes care in India."],
        "key_points_hi": ["मंत्री ने भारत में मधुमेह देखभाल को लेकर जन जागरूकता का आह्वान किया।"],
    }
    res = country_mcq(ci, "Union Minister Dr. Jitendra Singh in New Delhi India")
    assert res is None, "country_mcq must be None for domestic Indian ministerial governance news"


# 6. Weak Static GK test: rejects boilerplate filler
def test_weak_static_gk_rejected():
    banned_samples = [
        "Exam Fact – Key statutory bodies, constitutional appointments, national policies, and governance initiatives.",
        "Implementing ministries, financial outlays, target demographics, and flagship objectives.",
        "PIB Headquarters – New Delhi",
        "Government of India Established – 1947",
    ]
    for sample in banned_samples:
        assert BANNED_STATIC_GK_RE.search(sample) is not None, f"BANNED_STATIC_GK_RE should match '{sample}'"


# 7. Valid Static GK test: verified facts exist for critical entities
def test_verified_static_gk_lookups():
    entities = [
        ("PM E-DRIVE scheme for electric vehicles", ["Ministry of Heavy Industries", "FAME-II"]),
        ("PMDDKY Pradhan Mantri Dhan-Dhanya Krishi Yojana", ["Ministry of Agriculture & Farmers Welfare"]),
        ("National Film Awards ceremony", ["1954", "Dadasaheb Phalke Award"]),
        ("PMAY-G Pradhan Mantri Awaas Yojana Gramin", ["Ministry of Rural Development", "20 November 2016"]),
        ("Patanjali Yogpeeth and Ayurvedic research", ["Maharishi Patanjali", "Yoga Sutras"]),
        ("Ministry of Jal Shakti water conservation", ["May 2019", "Jal Jeevan Mission"]),
    ]
    for text, expected_keywords in entities:
        pairs = lookup_static_gk_for_text(text)
        assert len(pairs) > 0, f"Expected verified static facts for '{text}'"
        all_vals = " ".join(f"{k} {v}" for k, v in pairs)
        for kw in expected_keywords:
            assert kw.lower() in all_vals.lower(), f"Expected keyword '{kw}' in static GK for '{text}'"


# 8. One-Liner format test: strips '(Key: ...)'
def test_one_liner_format_clean():
    raw_str = "Government launches PM E-DRIVE scheme with ₹10,900 crore outlay (Key: ₹10,900 crore)"
    cleaned = _clean_one_liner_str(raw_str)
    assert "(Key:" not in cleaned, "One-liner cleaner should strip (Key: ...)"
    assert "₹10,900 crore" in cleaned

    items = [
        {
            "headline_en": "Cabinet approves PM E-DRIVE Scheme",
            "headline_hi": "मंत्रिमंडल ने पीएम ई-ड्राइव योजना को मंजूरी दी",
            "category": "National",
            "static_facts": {"Key Outlay": "₹10,900 crore"},
            "event_id": "ev_01",
        }
    ]
    one_liners = _build_category_one_liners(items)
    assert len(one_liners) == 1
    assert "(Key:" not in one_liners[0]["text_en"], "_build_category_one_liners should not output (Key: ...)"


# 9. Hindi editorial quality cleaning
def test_hindi_editorial_cleaning():
    text_bad = "डॉ. जितेंद्र सिंह ने में पतंजली अनुसंधान और PM E-DRIVE योजना पर चर्चा की।"
    cleaned = clean_hindi_editorial(text_bad)
    assert "पतंजलि" in cleaned, "Should correct 'पतंजली' to 'पतंजलि'"
    assert "ने में" not in cleaned, "Should remove broken 'ने में'"
    assert "पीएम ई-ड्राइव" in cleaned, "Should Hindi-transliterate PM E-DRIVE"


# 10. Exam fact does not return generic category descriptions
def test_exam_fact_not_boilerplate():
    item = {
        "category": "National",
        "headline_en": "Cabinet approves new railway line in Bihar",
        "raw_facts": "Cabinet Committee on Economic Affairs approved project.",
        "key_points_en": ["The project will enhance connectivity in northern Bihar."],
    }
    fact = exam_fact(item)
    assert "Key statutory bodies" not in fact, "exam_fact should never return generic category descriptions"
    assert "The project will enhance" in fact or len(fact) > 0


# 11. QA gate flags boilerplate filler
def test_qa_gate_boilerplate_detection():
    import importlib
    pdf_qa_mod = importlib.import_module("agents.19_pdf_qa")
    report = pdf_qa_mod.QAReport(pdf_path="test.pdf")
    bad_pdf_text = "Some intro text... Key statutory bodies, constitutional appointments, national policies..."
    pdf_qa_mod.check_editorial_quality(report, bad_pdf_text)
    assert any(i.code == "boilerplate_filler" for i in report.issues), "QA should flag boilerplate filler as error"


# 12. State MCQ natural exam phrasing
def test_state_mcq_natural_phrasing():
    ci = {
        "headline_en": "Odisha launches innovative organic farming initiative for tribal areas",
        "headline_hi": "ओडिशा ने जनजातीय क्षेत्रों के लिए नवीन जैविक खेती पहल शुरू की",
        "summary_en": "The state government announced financial incentives.",
        "key_points_en": ["Incentives of ₹10,000 per hectare provided to tribal farmers."],
        "key_points_hi": ["जनजातीय किसानों को प्रति हेक्टेयर ₹10,000 की प्रोत्साहन राशि।"],
        "event_id": "ev_odisha",
    }
    mcq = state_mcq(ci, "Odisha launches organic farming initiative")
    assert mcq is not None
    assert "Which State / Union Territory is associated with the following development" in mcq["question_en"]
    assert "ओडिशा" in str(mcq["options"])
    assert "The news" not in mcq["question_en"]
    # Verify dangling postposition 'ने' was cleanly stripped from Hindi stem
    assert not mcq["question_hi"].startswith('"ने ')
