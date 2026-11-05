# -*- coding: utf-8 -*-
"""Static GK stale holders / portfolios / org facts, lookup reason, Hindi post-fix, hyphens (mocked)."""
import copy

import pytest

from agents import static_gk_validator as V
from pipeline import hindi_postfix as H


@pytest.fixture(autouse=True)
def _job_date(monkeypatch):
    monkeypatch.setenv("ALP_JOB_DATE", "2026-11-05")


@pytest.fixture(scope="module")
def facts():
    return V.load_facts()


@pytest.fixture(scope="module")
def orgs():
    return V.load_orgs()


# --------------------------------------------------------------------------- #
# Static GK: officeholders seen in the 4 Nov 2026 edition
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("line,expect", [
    ("Director General of ICAR – Dr. M. K. Ranjitsinh", "Mangi Lal Jat"),
    ("Chief Justice of India (2024) – Dhananjaya Y. Chandrachud", "Surya Kant"),
    ("RBI Governor – Shaktikanta Das", "Sanjay Malhotra"),
    ("Union Minister of New and Renewable Energy – R.K. Singh", "Pralhad Joshi"),
])
def test_stale_holder_replaced(facts, line, expect):
    v = V.check_line(line, "", facts, year=2026)
    assert v.action == "replace" and expect in v.en
    assert "(2024)" not in v.en


@pytest.mark.parametrize("line", [
    "Current Governor – Shaktikanta Das",
    "Current Minister – Raj Kumar Singh",
    "Current RBI Governor (2024) – Shaktikanta Das",
    "Rajiv Ranjan Singh – Union Minister of State (Independent Charge) for Rural Development and Panchayati Raj",
    "Rajiv Ranjan Singh – Union Minister of Rural Development and Panchayati Raj",
])
def test_unverifiable_or_wrong_portfolio_dropped(facts, line):
    assert V.check_line(line, "", facts, year=2026).action == "drop"


def test_correct_portfolio_kept(facts):
    line = "Rajiv Ranjan Singh – Union Minister of Fisheries, Animal Husbandry and Dairying and Panchayati Raj"
    assert V.check_line(line, "", facts, year=2026).action == "keep"


def test_hindi_stale_name_blanked_or_verified(facts):
    v = V.check_line("RBI Governor – Shaktikanta Das", "आरबीआई गवर्नर – शक्तिकांत दास", facts, year=2026)
    assert v.action == "replace" and v.hi == ""          # fail closed: English-only line
    assert V.check_line("", "आरबीआई गवर्नर – शक्तिकांत दास", facts, year=2026).action == "drop"
    rows = [{"label_en": "RBI Governor", "value_en": "Shaktikanta Das", "label_hi": "आरबीआई गवर्नर",
             "value_hi": "शक्तिकांत दास"}]
    out = V.validate_rows(rows, facts, V.Report(), "", 2026)
    assert out[0]["value_en"] == "Sanjay Malhotra" and out[0]["value_hi"] == "संजय मल्होत्रा"
    # Hindi-only line with a tracked post and a name that is not the verified one: fail closed
    v = V.check_line("", "आरबीआई गवर्नर – कोई और", facts, year=2026)
    assert v.action == "drop"
    assert V.check_line("", "आरबीआई गवर्नर – संजय मल्होत्रा", facts, year=2026).action == "keep"


def test_past_year_label_removed_with_correct_name(facts):
    v = V.check_line("Chief Justice of India (2024) – Surya Kant", "", facts, year=2026)
    assert v.action == "replace" and v.en == "Chief Justice of India – Surya Kant"


# --------------------------------------------------------------------------- #
# Static GK: organisation facts
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("line", [
    "MIDHANI was established in 2012.",
    "MIDHANI is headquartered in New Delhi.",
    "MIDHANI Parent Ministry – Ministry of Steel",
    "Parent Ministry – Government of India",
    "ZSI is headquartered in Chennai.",
])
def test_wrong_org_fact_dropped(facts, orgs, line):
    assert V.check_line(line, "", facts, year=2026, orgs=orgs).action == "drop"


@pytest.mark.parametrize("line", [
    "MIDHANI was established in 1973 under the Ministry of Defence.",
    "ZSI was established in 1916 and is headquartered in Kolkata.",
    "BARC–MIDHANI MoU was signed in 2026.",
    "APEDA was set up under an Act of 1985.",
])
def test_right_org_fact_kept(facts, orgs, line):
    assert V.check_line(line, "", facts, year=2026, orgs=orgs).action == "keep"


def test_org_rows_corrected_with_context(facts):
    mcq = [{"event_id": "e1", "static_gk": [
        {"label_en": "Full Form", "value_en": "Mishra Dhatu Nigam Limited", "label_hi": "पूरा नाम", "value_hi": "मिश्र धातु निगम"},
        {"label_en": "Established", "value_en": "2012", "label_hi": "स्थापना", "value_hi": "2012"},
        {"label_en": "Headquarters", "value_en": "New Delhi", "label_hi": "मुख्यालय", "value_hi": "नई दिल्ली"},
        {"label_en": "Parent Ministry", "value_en": "Ministry of Steel", "label_hi": "मूल मंत्रालय", "value_hi": "इस्पात मंत्रालय"},
    ]}]
    rep = V.validate_edition({"items": []}, mcq, facts=facts, lookup=None)
    rows = {r["label_en"]: (r["value_en"], r["value_hi"]) for r in mcq[0]["static_gk"]}
    assert rows["Established"] == ("1973", "1973")
    assert rows["Headquarters"] == ("Hyderabad", "हैदराबाद")
    assert rows["Parent Ministry"] == ("Ministry of Defence", "रक्षा मंत्रालय")
    assert rep["replaced"] == 3


def test_current_facts_entries_are_sourced():
    import json
    doc = json.loads(V.FACTS_PATH.read_text(encoding="utf-8"))
    for rec in doc["facts"] + doc["orgs"]:
        assert rec.get("source_url", "").startswith("http") and rec.get("verified_on")


# --------------------------------------------------------------------------- #
# AI lookup always says why it made no calls
# --------------------------------------------------------------------------- #
class _IdleLookup:
    def __init__(self):
        self.stats = {"lookups": 0, "cache_hits": 0, "off_reason": ""}
        self.calls = []

    def status(self):
        return True, ""

    def __call__(self, post, **kw):
        self.calls.append(post)
        return None


def test_lookup_idle_reason_logged(facts):
    content = {"items": [{"event_id": "a", "headline_en": "x",
                          "static_gk_pairs": [["CEO, NITI Aayog – Anurag Jain", "नीति आयोग के सीईओ – अनुराग जैन"]]}]}
    lk = _IdleLookup()
    rep = V.validate_edition(content, None, facts=facts, lookup=lk)
    assert lk.calls == []
    assert rep["ai_lookup"]["off_reason"].startswith("idle:")
    assert rep["ai_lookup"]["officeholder_lines"] == 1


def test_lookup_disabled_and_not_ready_reasons(facts):
    rep = V.validate_edition({"items": []}, None, facts=facts, lookup=None)
    assert rep["ai_lookup"]["off_reason"] == "disabled by caller"

    class NotReady(_IdleLookup):
        def status(self):
            return False, "SERPER_API_KEY missing or Serper off"
    rep = V.validate_edition({"items": []}, None, facts=facts, lookup=NotReady())
    assert rep["ai_lookup"]["off_reason"] == "SERPER_API_KEY missing or Serper off"


def test_lookup_status_method_records_reason(tmp_path):
    from agents.static_gk_ai_lookup import Lookup
    lk = Lookup(ready=lambda: (False, "no LLM provider configured"), cache_path=tmp_path / "c.json")
    assert lk.status() == (False, "no LLM provider configured")
    assert lk.stats["off_reason"] == "no LLM provider configured"


# --------------------------------------------------------------------------- #
# Hindi post-fix
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("en,hi,good,bad", [
    ("Zoological Survey of India held a summit", "भारतीय वन्यजीव सर्वेक्षण ने शिखर सम्मेलन किया", "भारतीय प्राणी सर्वेक्षण", "वन्यजीव"),
    ("APEDA promotes kiwi exports", "एपीडिया ने कीवी निर्यात को बढ़ावा दिया", "एपीडा", "एपीडिया"),
    ("Under which Act was the commission set up?", "आयोग किस विधेयक के तहत गठित हुआ?", "अधिनियम", "विधेयक"),
    ("Parent Ministry", "अधीनस्थ मंत्रालय", "मूल मंत्रालय", "अधीनस्थ"),
    ("Nodal Ministry", "अभिभावक मंत्रालय", "नोडल मंत्रालय", "अभिभावक"),
    ("CACP recommends MSP", "कृषि लागत और मूल्य आयोग एमएसपी की सिफारिश करता है", "कृषि लागत एवं मूल्य आयोग", "और मूल्य"),
    ("Survey in Bengaluru", "Bengaluru में सर्वेक्षण", "बेंगलुरु", "Bengaluru"),
    ("Founded in 1986", "१९८६ में स्थापित", "1986", "१९८६"),
])
def test_glossary(en, hi, good, bad):
    out = H.fix_pair(en, hi)
    assert good in out and bad not in out


def test_bill_kept_when_english_says_bill():
    assert "विधेयक" in H.fix_pair("The Bill was passed", "विधेयक पारित हुआ")


def test_mixed_script_repaired_from_glossary_suffix_or_translator():
    assert H.fix_pair("The protest economy", "प्रोtest अर्थव्यवस्था") == "विरोध अर्थव्यवस्था"
    assert H.fix_pair("reporting and verification", "रिपोर्टing और सत्यापन") == "रिपोर्टिंग और सत्यापन"
    out = H.fix_pair("the quorum rule", "कोरमum नियम", translator=lambda w: "कोरम")
    assert out == "कोरम नियम"


def test_mixed_script_unrepairable_is_blanked():
    st = {}
    assert H.fix_pair("the quorum rule", "कोरमxq नियम", stats=st) == ""
    assert st["blank_mixed"] == 1


def test_english_leftover_phrase_blanked_or_retranslated():
    en = "Probe under the Commissions of Inquiry Act and the Rules of Procedure of the House"
    hi = "जांच Rules of Procedure of the House के तहत"
    assert H.fix_pair(en, hi) == ""
    assert H.fix_pair(en, hi, line_translator=lambda t: "सदन के प्रक्रिया नियमों के तहत जांच") \
        == "सदन के प्रक्रिया नियमों के तहत जांच"
    # proper nouns alone are kept (counted, not blanked); acronyms and glosses are fine
    st = {}
    assert H.fix_pair("CCI approves Kotak deal", "CCI ने Kotak सौदे को मंज़ूरी दी", stats=st)
    assert st.get("leftover_kept") == 1
    assert H.leftover_words("आईआईसीए ने वैकल्पिक विवाद समाधान (Alternative Dispute Resolution) को बढ़ाया") == []


def test_person_name_spelling_consistent():
    names = H.load_name_map()
    en = "Health Secretary Punya Salila Srivastava reviewed the plan"
    for wrong in ("स्वास्थ्य सचिव पुय़ा सलीला श्रीवास्तव ने योजना की समीक्षा की",
                  "स्वास्थ्य सचिव पुन्हा सालिला श्रीवास्तव ने योजना की समीक्षा की"):
        assert "पुण्य सलिला श्रीवास्तव" in H.fix_names(en, wrong, names)
    out = H.fix_names("Mansukh Mandaviya spoke", "मनुश मंडविया ने कहा", names)
    assert out == "मनसुख मांडविया ने कहा"
    # a name the English line does not mention is never touched
    assert H.fix_names("The minister spoke", "मनुश मंडविया ने कहा", names) == "मनुश मंडविया ने कहा"


def test_fix_edition_walks_content_and_mcq():
    content = {"items": [{"headline_en": "ZSI summit in Kolkata", "headline_hi": "भारतीय वन्यजीव सर्वेक्षण शिखर सम्मेलन",
                          "key_points_en": ["APEDA exports"], "key_points_hi": ["एपीडिया निर्यात"],
                          "static_gk_pairs": [["Parent Ministry – MoEFCC", "अधीनस्थ मंत्रालय – MoEFCC"]]}],
               "quick_bites": [{"en": "Protest economy", "hi": "प्रोtest अर्थव्यवस्था"}]}
    mcq = [{"question_en": "Which Act?", "question_hi": "कौन सा विधेयक?", "options": ["Protest"], "options_hi": ["प्रोtest"],
            "static_gk": [{"label_en": "Parent Ministry", "value_en": "x", "label_hi": "माता मंत्रालय", "value_hi": "य"}]}]
    st = H.fix_edition(content, mcq)
    it = content["items"][0]
    assert it["headline_hi"].startswith("भारतीय प्राणी सर्वेक्षण")
    assert it["key_points_hi"] == ["एपीडा निर्यात"]
    assert it["static_gk_pairs"][0][1].startswith("मूल मंत्रालय")
    assert content["quick_bites"][0]["hi"] == "विरोध अर्थव्यवस्था"
    assert mcq[0]["question_hi"] == "कौन सा अधिनियम?" and mcq[0]["options_hi"] == ["विरोध"]
    assert mcq[0]["static_gk"][0]["label_hi"] == "मूल मंत्रालय"
    assert st["lines"] >= 6


def test_translator_rejects_mixed_script_and_applies_glossary():
    from pipeline.ai_translator import _build_prompt, _validate
    assert not _validate("The protest economy", "प्रोtest अर्थव्यवस्था")[0]
    system, _ = _build_prompt("ZSI and the Zoological Survey of India", "general")
    assert "भारतीय प्राणी सर्वेक्षण" in system


# --------------------------------------------------------------------------- #
# Hyphens survive the PDF glyph guard
# --------------------------------------------------------------------------- #
def test_non_breaking_hyphen_kept_as_hyphen():
    from src.generate_pdf import _safe, _strip_html, sanitize_glyphs
    assert sanitize_glyphs("part\u2011time net\u2010zero self\u2011reliance") == "part-time net-zero self-reliance"
    assert _strip_html("AI\u2011driven state\u2011level") == "AI-driven state-level"
    assert _safe("Q2\u2011FY27") == "Q2-FY27"
    assert sanitize_glyphs("co\u00adoperation") == "cooperation"


def test_fallback_and_quoted_titles_not_blanked():
    # content.translate_headline_deterministic output (labelled English) is left alone
    assert H.fix_pair("Union Cabinet approved a scheme", "परीक्षा संदर्भ: Union Cabinet approved a scheme") \
        == "परीक्षा संदर्भ: Union Cabinet approved a scheme"
    hi = '"Cabinet Approves Agriculture Export Scheme with Rs 5000 Crore Outlay" से संबंधित प्रश्न'
    assert H.fix_pair("Question on the export scheme", hi) == hi      # quoted title kept verbatim
