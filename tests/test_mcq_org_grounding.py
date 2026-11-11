"""Org-pool MCQ keys must be grounded in the NEWS text (2026-11-11 ICAR incident).

On 2026-11-11 the sugarcane-price story printed ICAR as "the organisation
associated with this development" although ICAR appeared only in the generic
exam_fact line.  These tests pin the grounding rule, the grounded explanation,
the option-acronym dedupe and the first_valid backstop.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import mcq_builder as mb  # noqa: E402

SUGARCANE_HEADLINE = ("Maharashtra farmers seek uniform sugarcane price, Rs 2 lakh loan incentive")
SUGARCANE_HEADLINE_HI = ("महाराष्ट्र के किसानों ने एकसमान गन्ने के मूल्य, 2 लाख रुपये के ऋण प्रोत्साहन की मांग की")
KP_EN = ("A delegation of farmers met Maharashtra Cooperation Minister Babasaheb Patil in Latur to demand "
         "uniform sugarcane pricing across the state and a Rs 2 lakh incentive for borrowers.")
KP_HI = ("किसानों के एक प्रतिनिधिमंडल ने राज्य भर में गन्ने के लिए एक समान मूल्य और 2 लाख रुपये के प्रोत्साहन की मांग की।")
EXAM_FACT_ICAR = "Key crop statistics, ICAR cultivars, MSP notifications, and central agricultural schemes."


def _ci(**over):
    ci = {
        "event_id": "6b3c282a7162",
        "category": "Agriculture",
        "headline_en": SUGARCANE_HEADLINE,
        "headline_hi": SUGARCANE_HEADLINE_HI,
        "summary_en": KP_EN,
        "summary_hi": KP_HI,
        "key_points_en": [KP_EN],
        "key_points_hi": [KP_HI],
        "detailed_explanation_en": KP_EN,
        "detailed_explanation_hi": KP_HI,
        "exam_fact_en": "Implementing ministries and flagship objectives.",
        "exam_fact_hi": "कार्यान्वयन मंत्रालय और प्रमुख उद्देश्य।",
    }
    ci.update(over)
    return ci


def test_org_only_in_exam_fact_is_not_grounded():
    """The exact 2026-11-11 shape: ICAR named only in exam_fact -> no org-pool MCQ."""
    ci = _ci(exam_fact_en=EXAM_FACT_ICAR)
    ev = mb._ws(KP_EN) + " | " + mb._ws(EXAM_FACT_ICAR)
    assert mb.org_pool_mcq(ci, ev) is None


def test_org_in_news_text_is_grounded_and_explained_by_its_sentence():
    kp = "The delegation urged ICAR and NABARD to back a uniform sugarcane price across Maharashtra."
    kp_hi = "प्रतिनिधिमंडल ने समान गन्ना मूल्य के लिए ICAR और नाबार्ड का समर्थन मांगा।"
    ci = _ci(key_points_en=[KP_EN, kp], key_points_hi=[KP_HI, kp_hi],
             summary_en=KP_EN + " " + kp, detailed_explanation_en=KP_EN + " " + kp)
    m = mb.org_pool_mcq(ci, mb._news_text(ci))
    assert m is not None and m["type"] == "org-pool"
    lab = m["options"]["ABCDE".index(m["correct"])].split(" / ")[0]
    assert "ICAR" in lab or "NABARD" in lab
    # explanation must quote the sentence that names the org
    assert ("ICAR" in m["explanation_en"]) and ("uniform sugarcane price" in m["explanation_en"].lower())


def test_option_acronym_not_printed_twice():
    ci = _ci()
    m = mb._make(ci, "org-pool", "Q?", "प्र?", ("NABARD", "राष्ट्रीय कृषि और ग्रामीण विकास बैंक (NABARD)"),
                 [("ICAR", "भारतीय कृषि अनुसंधान परिषद (ICAR)"),
                  ("NAFED", "राष्ट्रीय कृषि सहकारी विपणन संघ (NAFED)"),
                  ("CACP", "कृषि लागत और मूल्य आयोग (CACP)"),
                  ("NCCF", "राष्ट्रीय सहकारी उपभोक्ता संघ (NCCF)"),
                  ("CWC", "केंद्रीय भंडारण निगम (CWC)")],
                 "e", "h")
    assert m is not None
    for o in m["options"]:
        en, _, hi = o.partition(" / ")
        acr = re.search(r"\(([A-Z]{2,10})\)$", en)
        if acr and en.strip().upper() == acr.group(1):
            assert not hi.rstrip().endswith("(%s)" % acr.group(1)), o


def test_first_valid_backstop_rejects_ungrounded_key():
    ci = _ci(exam_fact_en=EXAM_FACT_ICAR)
    forged = {
        "type": "org-pool",
        "question_en": 'Which organisation is associated with the news "%s"?' % SUGARCANE_HEADLINE,
        "question_hi": "प्रश्न?",
        "options": ["ICAR / भारतीय कृषि अनुसंधान परिषद",
                    "NABARD / राष्ट्रीय कृषि और ग्रामीण विकास बैंक",
                    "NAFED / राष्ट्रीय कृषि सहकारी विपणन संघ",
                    "CACP / कृषि लागत और मूल्य आयोग",
                    "NCCF / राष्ट्रीय सहकारी उपभोक्ता संघ"],
        "correct": "A",
        "explanation_en": KP_EN + " The organisation associated with this development is ICAR.",
        "explanation_hi": KP_HI,
        "event_id": "6b3c282a7162",
    }
    m, reasons = mb.first_valid([forged], ci, set())
    assert m is None
    assert any("not grounded" in r for r in reasons), reasons


def test_first_valid_backstop_accepts_grounded_key():
    kp = "ICAR released a district list for rainfed gram cultivation."
    ci = _ci(key_points_en=[KP_EN, kp], summary_en=KP_EN + " " + kp,
             detailed_explanation_en=KP_EN + " " + kp)
    forged = {
        "type": "org-pool",
        "question_en": 'Which organisation is associated with the news "%s"?' % SUGARCANE_HEADLINE,
        "question_hi": "प्रश्न?",
        "options": ["ICAR / भारतीय कृषि अनुसंधान परिषद",
                    "NABARD / राष्ट्रीय कृषि और ग्रामीण विकास बैंक",
                    "NAFED / राष्ट्रीय कृषि सहकारी विपणन संघ",
                    "CACP / कृषि लागत और मूल्य आयोग",
                    "NCCF / राष्ट्रीय सहकारी उपभोक्ता संघ"],
        "correct": "A",
        "explanation_en": kp,
        "explanation_hi": KP_HI,
        "event_id": "6b3c282a7162",
    }
    m, reasons = mb.first_valid([forged], ci, set())
    assert m is not None, reasons


def test_news_text_excludes_exam_fact():
    ci = _ci(exam_fact_en=EXAM_FACT_ICAR)
    assert "ICAR" not in mb._news_text(ci)
    assert "sugarcane" in mb._news_text(ci)
