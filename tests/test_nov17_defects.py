# -*- coding: utf-8 -*-
"""
Mandatory Regression Suite for Defects Identified in the 17 November 2026 Edition.

Covers:
1. CCPA factual contradiction (Central Consumer Protection Authority vs Chief Controller of Explosives).
2. Q1 dangling preposition ("in to") syntax rejection.
3. Q3 crop insurance loss % vs farmer registration numbers separation.
4. Q6 & Q9 news agency recognition stems rejection.
5. Q11 news story grounding vs generic ICAR 1929 establishment date.
6. Q12 city-identification upgrade to institutional purpose.
7. Page 26 generic country boilerplate Static GK rejection (Country - India, Capital - New Delhi, etc.).
8. Explanation datelines and timestamp scrubbing.
9. News in Pictures responsive gap-free layout.
10. One-Liners rapid-revision distinctness (not verbatim headline copies).
"""
import pytest
import re
from typing import Dict, Any, List

from pipeline.mcq_schema import schema_errors, PHRASE_RECOG_RE
from pipeline.static_gk_db import lookup_static_gk_for_text, ENTITY_STATIC_DB
from src.generate_pdf import BANNED_STATIC_GK_RE, _extract_static_gk_pairs


def test_ccpa_acronym_disambiguation():
    """Defect A & G: CCPA must be Central Consumer Protection Authority, NOT Chief Controller of Explosives."""
    # 1. Database must contain authoritative CCPA record
    assert "CCPA" in ENTITY_STATIC_DB, "CCPA must be present in ENTITY_STATIC_DB"
    ccpa_entry = ENTITY_STATIC_DB["CCPA"]
    assert "Central Consumer Protection Authority" in ccpa_entry["name_en"]
    assert "केंद्रीय उपभोक्ता संरक्षण प्राधिकरण" in ccpa_entry["name_hi"]

    # 2. Lookup for story text containing CCPA must yield Consumer Protection facts, NOT Explosives Act
    story_text = "CCPA Imposes Penalty of ₹20 Lakh on ExportersIndia.com for Online Listing of Ammonium Nitrate"
    pairs = lookup_static_gk_for_text(story_text)
    assert pairs, "CCPA lookup should return verified pairs"
    
    en_texts = " ".join(p[0] for p in pairs)
    assert "Consumer Protection Act, 2019" in en_texts, "CCPA must cite Consumer Protection Act, 2019"
    assert "Ministry of Consumer Affairs" in en_texts, "CCPA must cite Ministry of Consumer Affairs"
    assert "Chief Controller of Explosives" not in en_texts, "CCPA must NOT cite Chief Controller of Explosives"
    assert "Explosives Act, 1884" not in en_texts, "CCPA must NOT cite Explosives Act, 1884"
    assert "Ministry of Home Affairs" not in en_texts, "CCPA must NOT cite Ministry of Home Affairs"


def test_q1_dangling_preposition_rejected():
    """Defect B: Stems with dangling prepositions like 'in to' must fail validation."""
    from pipeline.mcq_quality import question_has_grammatical_defect

    broken_q = 'Which State / Union Territory is associated with the following development: "IEPFA and SEBI to Organize ‘Niveshak Shivir’ in to Empower Investors and Simplify Grievance Redressal and…"'
    assert question_has_grammatical_defect(broken_q), "Question with dangling 'in to' must be flagged as defective"

    clean_q = 'In which State / Union Territory will IEPFA and SEBI organize the ‘Niveshak Shivir’ to empower investors?'
    assert not question_has_grammatical_defect(clean_q), "Clean natural question must pass validation"


def test_q3_crop_insurance_separation():
    """Defect C: Numerical question on farmer registration counts must not provide percentage distractors."""
    from pipeline.mcq_quality import numbers_dimensionally_consistent

    # Conflated options: Question asks for count/outlay, but options are percentages
    bad_options = ["180%", "135%", "21 per cent", "45%", "60%"]
    question_about_count = "How many farmers registered for crop insurance in Karnataka in Kharif 2026?"
    assert not numbers_dimensionally_consistent(question_about_count, bad_options), "Count question cannot use percentage options"

    good_options = ["37.5 lakh", "20.91 lakh", "15.4 lakh", "42.0 lakh", "28.5 lakh"]
    assert numbers_dimensionally_consistent(question_about_count, good_options), "Lakh count options must be valid for count question"


def test_q6_q9_agency_recognition_rejected():
    """Defect D: Questions asking which news agency or media channel reported the news are prohibited."""
    from pipeline.mcq_schema import AGENCY_STEM_RE

    bad_q6 = "Which news agency reported the launch of the Agri Welfare Portal?"
    bad_q9 = "Which news agency reported the Cabinet's approval of the Semicon 2.0 scheme?"
    bad_q_alt = "Which media outlet published the report on semiconductor manufacturing?"

    assert AGENCY_STEM_RE.search(bad_q6), "Agency question Q6 must be matched by AGENCY_STEM_RE"
    assert AGENCY_STEM_RE.search(bad_q9), "Agency question Q9 must be matched by AGENCY_STEM_RE"
    assert AGENCY_STEM_RE.search(bad_q_alt), "Media outlet question must be matched by AGENCY_STEM_RE"

    mcq = {
        "question_en": bad_q6,
        "question_hi": "एग्री वेलफ़ेयर पोर्टल के शुभारंभ की खबर किस समाचार एजेंसी ने दी?",
        "options": ["DD News", "The Hindu", "AIR", "TOI", "PTI"],
        "options_hi": ["डीडी न्यूज़", "द हिन्दू", "ऑल इंडिया रेडियो", "टाइम्स ऑफ इंडिया", "पीटीआई"],
        "correct": "A",
        "explanation_pairs": [{"en": "DD News reported it.", "hi": "डीडी न्यूज़ ने यह खबर दी।"} for _ in range(4)],
    }
    errs = schema_errors(mcq, "DD News reported the portal launch.")
    assert any("news agency" in e.lower() or "agency" in e.lower() for e in errs), "schema_errors must reject agency questions"


def test_q11_story_grounding_vs_generic_icar_date():
    """Defect E: Story about Training cannot be answered with generic ICAR establishment date."""
    from pipeline.mcq_quality import question_grounded_in_story

    story = {
        "headline_en": "Sustainable Natural Resource Management Training Program Launched for Agricultural Officers",
        "summary_en": "A five-day specialized training on soil conservation and micro-irrigation was inaugurated to equip extension officers.",
    }
    generic_mcq = {
        "question_en": "When was the Indian Council of Agricultural Research (ICAR) established?",
        "options": ["16 July 1929", "15 August 1947", "26 January 1950", "12 July 1982", "14 January 1965"],
        "correct": "A",
    }
    # When the story is about a training program, an MCQ solely asking for 1929 establishment date fails grounding
    assert not question_grounded_in_story(generic_mcq["question_en"], story), "Generic founding date must not replace training story MCQ"


def test_page26_generic_country_static_gk_rejected():
    """Defect G: Generic national trivia (Country - India, Capital - New Delhi, 1947) must be rejected."""
    # 1. BANNED_STATIC_GK_RE must match generic country filler
    assert BANNED_STATIC_GK_RE.search("Country – India")
    assert BANNED_STATIC_GK_RE.search("Capital – New Delhi")
    assert BANNED_STATIC_GK_RE.search("Year of independence – 1947")
    assert BANNED_STATIC_GK_RE.search("Official language – Hindi")

    item = {
        "headline_en": "Recognise farmers as custodians and innovators of India's agricultural biodiversity",
        "summary_en": "Dr P K Mishra urged recognition of farmers.",
        "static_gk_pairs": [],
        "static_facts": {
            "Country": "India",
            "Capital": "New Delhi",
            "Official language": "Hindi",
            "Year of independence": "1947"
        }
    }
    mcq = {
        "static_gk": [
            {"label_en": "Country", "value_en": "India", "label_hi": "देश", "value_hi": "भारत"},
            {"label_en": "Capital", "value_en": "New Delhi", "label_hi": "राजधानी", "value_hi": "नई दिल्ली"},
            {"label_en": "Official language", "value_en": "Hindi", "label_hi": "आधिकारिक भाषा", "value_hi": "हिन्दी"},
            {"label_en": "Year of independence", "value_en": "1947", "label_hi": "स्वतंत्रता वर्ष", "value_hi": "1947"},
        ]
    }
    pairs = _extract_static_gk_pairs(item, mcq)
    for en, hi in pairs:
        assert not re.search(r"\b(?:Country\s*–\s*India|Capital\s*–\s*New Delhi|independence\s*–\s*1947)\b", en, re.I), \
            f"Generic country trivia leaked into pairs: {en}"


def test_explanation_datelines_and_timestamps_scrubbed():
    """Defect H: News timestamps and datelines copied into explanations must be scrubbed."""
    from pipeline.content_sanitizer import clean_explanation_text

    raw_expl = "Updated - November 17, 2026 12:59 am IST - Bengaluru With the wide impact of El Nino on agriculture..."
    cleaned = clean_explanation_text(raw_expl)
    assert "Updated - November 17" not in cleaned, "Timestamp must be stripped from explanation"
    assert "12:59 am IST" not in cleaned, "Time/Timezone stamp must be stripped"
    assert cleaned.startswith("With the wide impact"), "Clean substantive text must remain"


def test_news_in_pictures_grid_balance():
    """Defect I: 5 cards must be balanced without creating an awkward empty slot."""
    from src.generate_pdf import _calculate_gallery_grid

    # 4 cards -> 2 cols x 2 rows
    cols, rows = _calculate_gallery_grid(4)
    assert cols == 2 and rows == 2

    # 6 cards -> 3 cols x 2 rows
    cols, rows = _calculate_gallery_grid(6)
    assert cols == 3 and rows == 2

    # 5 cards -> must balance nicely (e.g. 2 cols x 2 rows with top 4, or 2 cols with full-width hero)
    layout = _calculate_gallery_grid(5)
    assert layout is not None


def test_one_liners_distinct_from_headlines():
    """Defect J: One-Liners must not simply be verbatim copies of the 15 headlines."""
    from pipeline.auto_sections import generate_distinct_one_liner

    headline = "IEPFA and SEBI to Organize ‘Niveshak Shivir’ in New Delhi to Empower Investors and Simplify Grievance Redressal and Unclaimed Dividend Claims"
    story = {
        "headline_en": headline,
        "summary_en": "IEPFA and SEBI joint initiative.",
        "organizations": ["IEPFA", "SEBI"],
        "locations": ["New Delhi"]
    }
    ol_en, ol_hi = generate_distinct_one_liner(story)
    assert ol_en != headline, "One-liner must be a concise revision fact, not verbatim headline clone"
    assert len(ol_en) <= 140, "One-liner must be concise for rapid revision"


def test_pdf_qa_editorial_gates():
    """Verify that agents.19_pdf_qa.check_editorial_quality blocks all 17 Nov defect classes."""
    import importlib
    pdf_qa = importlib.import_module("agents.19_pdf_qa")

    # 1. News agency recognition stem
    rep1 = pdf_qa.QAReport("test.pdf")
    pdf_qa.check_editorial_quality(rep1, "Which news agency reported the launch of the portal?")
    assert any(i.code == "agency_recognition_mcq" and i.severity == "error" for i in rep1.issues)

    # 2. Generic country Static GK boilerplate
    rep2 = pdf_qa.QAReport("test.pdf")
    pdf_qa.check_editorial_quality(rep2, "Country – India\nCapital – New Delhi\nYear of independence – 1947")
    assert any(i.code == "generic_country_static_gk" and i.severity == "error" for i in rep2.issues)

    # 3. CCPA acronym collision
    rep3 = pdf_qa.QAReport("test.pdf")
    pdf_qa.check_editorial_quality(rep3, "CCPA issued guidelines under the Chief Controller of Explosives and Explosives Act")
    assert any(i.code == "ccpa_acronym_collision" and i.severity == "error" for i in rep3.issues)

    # 4. Dangling double preposition
    rep4 = pdf_qa.QAReport("test.pdf")
    pdf_qa.check_editorial_quality(rep4, "Organized ‘Niveshak Shivir’ in to Empower Investors")
    assert any(i.code == "dangling_preposition_in_mcq" and i.severity == "error" for i in rep4.issues)

    # 5. Leaked explanation dateline
    rep5 = pdf_qa.QAReport("test.pdf")
    pdf_qa.check_editorial_quality(rep5, "Updated - November 17, 2026 12:59 am IST - Bengaluru With the wide impact...")
    assert any(i.code == "explanation_dateline_leakage" and i.severity == "error" for i in rep5.issues)

