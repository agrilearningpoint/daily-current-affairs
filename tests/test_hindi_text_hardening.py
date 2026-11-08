# -*- coding: utf-8 -*-
"""Hindi + text hardening (weekly audit 2026-11-08): real examples, all offline/mocked."""
from __future__ import annotations

import re
from datetime import date

import pytest

from pipeline import period_builder as pb
from pipeline.hindi_postfix import fix_pair, strict_problems
from pipeline.text_normalize import (caption_residue, clip_words, exact_money, garbled_hi, hi_truncated_start,
                                     normalise_money, resolve_weekdays, strip_source_tags, tidy)


def fake_tr(en: str) -> str:
    nums = " ".join(re.findall(r"\d+(?:[.,]\d+)*", en.replace(",", "")))
    return re.sub(r"\s+", " ", f"यह वाक्य {nums} का हिंदी अनुवाद है।")


# --------------------------------------------------------------------------- #
# 2. English left inside Hindi lines
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("en,hi,want", [
    ("All such infiltrators will be sent out of the country.", "ऐसे सभी infiltrators को देश से बाहर भेजा जाएगा।",
     "ऐसे सभी घुसपैठियों को देश से बाहर भेजा जाएगा।"),
    ("Will US President Donald Trump's party recover?", "क्या US President Donald Trump की पार्टी उबरेगी?",
     "क्या अमेरिकी राष्ट्रपति डोनाल्ड ट्रंप की पार्टी उबरेगी?"),
    ("Kisan Credit Card: credit in agriculture", "Kisan Credit Card: कृषि में ऋण", "किसान क्रेडिट कार्ड: कृषि में ऋण"),
    ("The state received the PM Surya Ghar Excellence Award.", "राज्य को PM Surya Ghar Excellence Award से सम्मानित किया गया।",
     "राज्य को पीएम सूर्य घर उत्कृष्टता पुरस्कार से सम्मानित किया गया।"),
    ("He inaugurated the Animal Taxonomy Summit 2026.", "उन्होंने Animal Taxonomy Summit 2026 का उद्घाटन किया।",
     "उन्होंने पशु वर्गिकी शिखर सम्मेलन 2026 का उद्घाटन किया।"),
    ("The Reserve Bank proposed a limit of Rs 100 crore.", "Reserve Bank ने Rs 100 crore की सीमा का प्रस्ताव रखा।",
     "रिज़र्व बैंक ने ₹100 करोड़ की सीमा का प्रस्ताव रखा।"),
    ("Barclays Bank infused Rs 1,500 crore.", "Barclays Bank ने Rs 1,500 करोड़ डाले।", "बार्कलेज़ बैंक ने ₹1,500 करोड़ डाले।"),
])
def test_english_left_in_hindi_is_transliterated_by_glossary(en, hi, want):
    assert fix_pair(en, hi) == want
    assert fix_pair(en, hi, strict=True) == want
    assert not strict_problems(en, want)


def test_strict_mode_retranslates_or_drops_unknown_english():
    en = "The Foo Widget Council met on 3 May."
    hi = "Foo Widget Council की बैठक 3 मई को हुई।"
    assert fix_pair(en, hi) == hi                                   # daily: proper nouns kept
    assert fix_pair(en, hi, strict=True) == ""                       # period: no translator -> dropped
    assert fix_pair(en, hi, strict=True, line_translator=fake_tr) == fake_tr(en)
    assert fix_pair("RBI and GST data", "RBI और GST के आंकड़े", strict=True) == "RBI और GST के आंकड़े"  # acronyms ok


# --------------------------------------------------------------------------- #
# 3. Truncated / garbled Hindi
# --------------------------------------------------------------------------- #
def test_truncated_start_repaired_from_glossary_or_dropped():
    en = "Namakkal farmers oppose the proposed Sankari-Vellakoil NH project."
    hi = "क्कल के किसानों ने प्रस्तावित सांकरी-वेल्लाकोइल एनएच परियोजना का विरोध किया।"
    assert hi_truncated_start(hi) and not hi_truncated_start("नामक्कल के किसान")
    assert fix_pair(en, hi).startswith("नामक्कल के किसानों ने")
    assert fix_pair("Xyzpur farmers protest.", "्कल के किसानों ने विरोध किया।") == ""


@pytest.mark.parametrize("en,hi,want", [
    ("GST collections in October", "ऑक्टोबर में GST संग्रह", "अक्टूबर में GST संग्रह"),
    ("Ministry of Defence – Headquarters", "मंत्रालय रक्षा – मुख्यालय", "रक्षा मंत्रालय – मुख्यालय"),
    ("Department of Economic Affairs", "विभाग आर्थिक मामलों का", "आर्थिक मामलों का विभाग"),
    ("under the Commissions of Inquiry Act, 1952", "1952 के आयोग अधिनियम के तहत", "जांच आयोग अधिनियम, 1952 के तहत"),
    ("Parent body – ICAR", "अधीनस्थ निकाय – ICAR", "मूल निकाय – ICAR"),
])
def test_word_order_months_and_parent_body(en, hi, want):
    assert fix_pair(en, hi) == want


def test_garbled_one_liner_27_is_rejected_or_retranslated():
    en = ("NITI Aayog and GIZ India Sign Implementation Agreement under Nationally Determined Contribution-Transport "
          "Initiative for Asia Phase II (NDC-TIA II) to Accelerate Road Freight Decarbonisation")
    hi = ("नीति आयोग और GIZ इंडिया ने एशिया चरण II (NDC-TIA II) के तहत राष्ट्रीय रूप से निर्धारित योगदान-परिवहन पहल के "
          "तहत कार्यान्वयन समझौता पर हस्ताक्षर किए, सड़क माल ढुलाई डिकार्बोनाइजेशन को तेज करने के लिए")
    assert garbled_hi(hi)
    assert fix_pair(en, hi, strict=True) == ""
    good = "नीति आयोग और GIZ इंडिया ने NDC-TIA II के अंतर्गत कार्यान्वयन समझौते पर हस्ताक्षर किए।"
    assert fix_pair(en, hi, strict=True, line_translator=lambda _e: good) == good
    assert not garbled_hi("किसानों के लिए नई योजना शुरू की गई।")


# --------------------------------------------------------------------------- #
# 4. Leftovers: source tags and caption residue
# --------------------------------------------------------------------------- #
def test_source_tags_stripped_in_hindi_and_english():
    assert strip_source_tags("दिल्ली में भारत रिन्यूएबल एनर्जी समिट के उद्घाटन पर पीएम का संबोधन - पीएम इंडिया") \
        == "दिल्ली में भारत रिन्यूएबल एनर्जी समिट के उद्घाटन पर पीएम का संबोधन"
    assert strip_source_tags("जीएसटी संग्रह ₹2.31 लाख करोड़ हो गया - एयर पर समाचार") == "जीएसटी संग्रह ₹2.31 लाख करोड़ हो गया"
    assert strip_source_tags("PM's address at Bharat Renewable Energy Summit - PM India") \
        == "PM's address at Bharat Renewable Energy Summit"
    assert fix_pair("GST up", "ऑक्टोबर में GST संग्रह बढ़ा - एयर पर समाचार") == "अक्टूबर में GST संग्रह बढ़ा"


def test_photo_caption_residue_detected():
    assert caption_residue("Andhra Pradesh Deputy CM K. Photo Jana Sena Party (JSP) president and Deputy Chief "
                           "Minister K. Pawan Kalyan attributed the mandate.")
    assert not caption_residue("A photo exhibition on Indian railways opened in Delhi.")


# --------------------------------------------------------------------------- #
# 5. Numbers
# --------------------------------------------------------------------------- #
def test_money_is_never_abbreviated_or_rounded():
    src = "The Union Cabinet approved the VISTAR scheme with an outlay of Rs 4,371.10 crore."
    assert exact_money("Govt clears ₹4K cr VISTAR scheme", src) == "Govt clears ₹4,371.10 crore VISTAR scheme"
    assert exact_money("सरकार ने ₹4,000 करोड़ की विस्तार योजना को मंजूरी दी", src) \
        == "सरकार ने ₹4,371.10 करोड़ की विस्तार योजना को मंजूरी दी"
    assert exact_money("₹9,000 crore", src) == "₹9,000 crore"            # not the same figure: untouched
    assert normalise_money("Rs.2,814 Crore and Rs 53,866.50 crore") == "₹2,814 crore and ₹53,866.50 crore"
    assert normalise_money("कुल Rs 100 crore") == "कुल ₹100 करोड़"


# --------------------------------------------------------------------------- #
# 6. Punctuation
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("raw,want", [
    ("Is there room to negotiate?.", "Is there room to negotiate?"),
    ("US Congress , may push", "US Congress, may push"),
    ("foot march , Mr. Shah said .", "foot march, Mr. Shah said."),
    ('He called it "historic', "He called it historic"),
    ("two  spaces  here", "two spaces here"),
    ("India-US trade deal", "India-US trade deal"),
    ("क्या यह सही है ?", "क्या यह सही है?"),
])
def test_tidy(raw, want):
    assert tidy(raw) == want


def test_clip_words_never_cuts_mid_word():
    assert clip_words("Cabinet approves closure of 4 old units in Maharashtra state today", 30) \
        == "Cabinet approves closure of 4…"


# --------------------------------------------------------------------------- #
# 7. Dates
# --------------------------------------------------------------------------- #
def test_relative_weekday_resolved_against_publish_date():
    pub = date(2026, 11, 6)  # Friday
    assert resolve_weekdays("The RBI said on Thursday that rates stay.", pub) == "The RBI said on 5 November that rates stay."
    assert resolve_weekdays("रिज़र्व बैंक ने गुरुवार प्रस्ताव रखा।", pub) == "रिज़र्व बैंक ने 5 नवंबर को प्रस्ताव रखा।"
    assert resolve_weekdays("गुरुवार की बैठक में", pub) == "5 नवंबर की बैठक में"
    assert resolve_weekdays("The vote is next Monday.", pub) == "The vote is on 9 November."
    assert resolve_weekdays("said on Friday", date(2026, 11, 6)) == "said on 6 November"


# --------------------------------------------------------------------------- #
# 1. Missing Hindi bullets in the period builder + QA
# --------------------------------------------------------------------------- #
TEXT = ("Collector P.S. Leela Alex inspected the paddy procurement centres on Wednesday. "
        "She directed officials to clear payments to 2,400 farmers within a week. "
        "The district has procured 18,500 tonnes of paddy so far this season.")


def _story(**kw):
    it = {"event_id": "ev1", "category": "Agriculture", "importance_score": 70,
          "headline_en": "Collector reviews paddy procurement", "headline_hi": "कलेक्टर ने धान खरीद की समीक्षा की",
          "summary_en": "", "summary_hi": "", "detailed_explanation_en": TEXT,
          "detailed_explanation_hi": "",
          "key_points_en": ["Collector P.S. Leela Alex inspected the paddy procurement centres on Wednesday."],
          "key_points_hi": ["कलेक्टर पी.एस. लीला एलेक्स ने बुधवार को धान खरीद केंद्रों का निरीक्षण किया।"],
          "edition_date": "2026-11-06", "needs_review": False, "verification_passed": True}
    it.update(kw)
    return it


def test_every_bullet_gets_hindi_from_translator():
    qa: dict = {}
    pairs = pb._summary_pairs(_story(), [], set(), hindi=pb.PeriodHindi((None, fake_tr)), qa=qa)
    assert len(pairs) == 3 and all(p["hi"] for p in pairs)
    assert pairs[0]["en"].endswith("on 4 November.")                  # Wednesday before Fri 6 Nov
    assert "4 नवंबर को" in pairs[0]["hi"]
    assert qa["bullets_expected"] == 3 and not qa.get("bullets_missing_hi")


def test_sentence_aligned_daily_hindi_is_carried():
    hi = ("कलेक्टर पी.एस. लीला एलेक्स ने बुधवार को धान खरीद केंद्रों का निरीक्षण किया। "
          "उन्होंने अधिकारियों को एक सप्ताह के भीतर 2,400 किसानों का भुगतान करने का निर्देश दिया। "
          "जिले ने इस सीज़न में अब तक 18,500 टन धान की खरीद की है।")
    calls = []
    pairs = pb._summary_pairs(_story(detailed_explanation_hi=hi), [], set(),
                              hindi=pb.PeriodHindi((None, lambda e: calls.append(e) or "")), qa={})
    assert len(pairs) == 3 and not calls
    assert pairs[1]["hi"].startswith("उन्होंने अधिकारियों को")


def test_untranslatable_bullets_dropped_as_pair_and_qa_fails_edition():
    qa: dict = {}
    pairs = pb._summary_pairs(_story(), [], set(), hindi=pb.PeriodHindi((None, None)), qa=qa)
    assert len(pairs) == 1 and pairs[0]["hi"]                          # only the daily-translated bullet
    pb.period_hindi_qa(qa)
    assert qa["bullets_missing_hi"] == 2 and not qa["passed"] and qa["warnings"]
    ok = pb.period_hindi_qa({"bullets_expected": 30, "bullets_missing_hi": 3})
    assert ok["passed"]                                                # exactly 10% is allowed
    assert not pb.period_hindi_qa({"bullets_expected": 30, "bullets_missing_hi": 4})["passed"]


def test_build_period_fails_when_hindi_missing(monkeypatch):
    monkeypatch.delenv("DRY_RUN", raising=False)
    days = ["2026-11-04", "2026-11-05", "2026-11-06"]
    eds = []
    for i, d in enumerate(days):
        st = [_story(event_id=f"e{i}{j}", headline_en=f"Collector {i}{j} reviews paddy procurement in district {j}",
                     headline_hi=f"कलेक्टर {i}{j} ने जिले {j} में धान खरीद की समीक्षा की", key_points_hi=[""],
                     edition_date=d) for j in range(2)]
        eds.append({"date": d, "content": {"items": st, "one_liners": []}, "mcqs": []})
    with pytest.raises(ValueError, match="no clean Hindi"):
        pb.build_period("weekly", "2026-11-08", eds, days, translators=(None, None))
    r = pb.build_period("weekly", "2026-11-08", eds, days, translators=(None, fake_tr))
    assert r["content"]["period_qa"]["passed"]
    assert all(p["hi"] for it in r["content"]["items"] for p in it["summary_pairs"])


def test_one_liners_cleaned_and_dropped_when_hindi_bad():
    verified = {"v": {"event_id": "v", "section": "Economy",
                      "summary_en": "The Cabinet cleared VISTAR with an outlay of Rs 4,371.10 crore."}}
    ols = [{"event_id": "v", "category": "Economy", "text_en": "Govt clears ₹4K cr VISTAR scheme - PM India",
            "text_hi": "सरकार ने ₹4K करोड़ की विस्तार योजना को मंजूरी दी - पीएम इंडिया"},
           {"event_id": "v", "category": "Economy", "text_en": "Another line about the Widget Board",
            "text_hi": "Widget Board के बारे में एक और पंक्ति"}]
    qa: dict = {}
    out = pb._clean_one_liners(ols, verified, pb.PeriodHindi((None, None)), 10, qa)
    assert len(out) == 1 and qa["one_liners_dropped"] == 1
    assert out[0]["text_en"] == "Govt clears ₹4,371.10 crore VISTAR scheme"
    assert out[0]["text_hi"] == "सरकार ने ₹4,371.10 करोड़ की विस्तार योजना को मंजूरी दी"


def test_dry_run_keeps_marked_en_only_bullets_live_never(monkeypatch):
    from src import period_pdf
    it = {"summary_pairs": [{"en": "A whole sentence about the story is here.", "hi": "", "en_only_dry_run": True}]}
    assert period_pdf._summary(it, 3) == [("A whole sentence about the story is here.", "")]
    monkeypatch.setenv("DRY_RUN", "1")
    qa: dict = {}
    story = _story(summary_pairs=[{"en": "She directed officials to clear payments to 2,400 farmers within a week.",
                                   "hi": ""}])
    out = pb._bilingual_pairs(story, pb.PeriodHindi((None, None)), qa)
    assert out and out[0].get("en_only_dry_run") and qa["bullets_missing_hi"] == 1
    monkeypatch.delenv("DRY_RUN")
    assert pb._bilingual_pairs(story, pb.PeriodHindi((None, None)), {}) == []
