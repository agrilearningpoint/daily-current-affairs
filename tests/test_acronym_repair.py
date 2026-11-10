"""Acronym auto-repair (2026-11-10).

Run 42789471273 lost 6 of 15 stories to "missing acronyms" on translations that
were actually correct: the sources were ALL-CAPS headlines, so ordinary words
(BATCH, CONDUCT, DELHI, INDIA, NEW) were demanded back in Latin spelling and
every provider was rejected for the same line. These tests pin both halves of the
fix — smarter matching, and a capped repair that never rewrites prose — and the
gates that must keep failing closed.

No network: providers are faked at the _call_provider level.
"""
import pytest

from pipeline import ai_translator


def configure_providers(monkeypatch, names=("groq",)):
    providers = [
        {"name": n, "url": f"https://{n}.example/v1/chat/completions",
         "key": f"test-key-{n}", "model": f"{n}-model"}
        for n in names
    ]
    monkeypatch.setattr(ai_translator, "_PROVIDERS_CACHE", providers)
    ai_translator.clear_cache()
    ai_translator._RATE_LIMITED_PROVIDERS.clear()
    return providers


# --------------------------------------------------------------------------- #
# 1. Matching: a correct translation is no longer rejected
# --------------------------------------------------------------------------- #
def test_all_caps_headline_does_not_demand_latin_words_back():
    """The real line from run #358: PRESIDENT OF INDIA … IN NEW DELHI."""
    en = "PRESIDENT OF INDIA INAUGURATES 'SAUSHRUTAM 2026' IN NEW DELHI"
    hi = "भारत के राष्ट्रपति ने नई दिल्ली में 'सौश्रुतम् 2026' का उद्घाटन किया।"
    passed, conf, issues = ai_translator._validate(en, hi)
    assert passed, issues
    assert conf == 1.0
    assert ai_translator._source_is_all_caps(en)


def test_mixed_case_source_still_enforces_curated_acronyms():
    """Sentence-case sources keep the strict check: an uppercase token there is
    an acronym, not a word."""
    en = "The SEBI board approved the new disclosure norms"
    hi = "बोर्ड ने नए खुलासा मानदंड मंजूर किए।"
    passed, _conf, issues = ai_translator._validate(en, hi)
    assert not passed and any("missing acronyms" in i for i in issues), issues
    assert not ai_translator._source_is_all_caps(en)


def test_an_acronym_spelled_out_in_hindi_counts_as_present():
    """समर्थन मूल्य *is* MSP; demanding the Latin letters would be the old bug."""
    en = "The MSP for kharif crops was raised by the Centre"
    hi = "खरीफ फसलों के लिए न्यूनतम समर्थन मूल्य बढ़ाया गया।"
    passed, _conf, issues = ai_translator._validate(en, hi)
    assert passed, issues


def test_natural_transliterations_are_not_reported_missing():
    for acr, hi in (("TRAI", "ट्राई ने आदेश जारी किया।"),
                    ("BRICS", "ब्रिक्स शिखर सम्मेलन हुआ।"),
                    ("NAFED", "नाफेद ने खरीद शुरू की।"),
                    ("NITI", "नीति आयोग की रिपोर्ट।")):
        assert ai_translator._acronym_matched_in_hindi(acr, hi), acr


def test_dotted_transliteration_matches_the_acronym():
    """पी.टी.आई. is PTI; punctuation must not decide the verdict."""
    assert ai_translator._acronym_matched_in_hindi("PTI", "पी.टी.आई. ने रिपोर्ट दी।")
    assert ai_translator._acronym_matched_in_hindi("PTI", "पी टी आई की रिपोर्ट")
    assert ai_translator._acronym_matched_in_hindi("PTI", "PTI की रिपोर्ट")
    assert not ai_translator._acronym_matched_in_hindi("PTI", "एक एजेंसी ने रिपोर्ट दी।")


def test_place_names_and_caps_words_count_as_translated():
    assert ai_translator._acronym_matched_in_hindi("CHENNAI", "चेन्नई में अभ्यास हुआ।")
    assert ai_translator._acronym_matched_in_hindi("BATCH", "यूरिया की खेप पहुंची।")
    assert ai_translator._acronym_matched_in_hindi("CONDUCT", "अभ्यास का संचालन किया गया।")
    assert ai_translator._acronym_matched_in_hindi("DELHI", "दिल्ली में बैठक हुई।")
    # …but a word that is genuinely absent is still reported
    assert not ai_translator._acronym_matched_in_hindi("CHENNAI", "उत्तर में अभ्यास हुआ।")


def test_known_acronyms_are_enforced_inside_an_all_caps_source():
    en = "TRAI NOTIFIES NEW TARIFF ORDER FOR BROADCASTERS"
    assert ai_translator._source_is_all_caps(en)
    assert ai_translator._missing_acronyms(en, "नया टैरिफ आदेश जारी किया गया।") == ["TRAI"]
    # the same line with the acronym kept passes
    assert ai_translator._missing_acronyms(en, "ट्राई ने नया टैरिफ आदेश जारी किया।") == []


# --------------------------------------------------------------------------- #
# 2. Repair: capped, appended, prose untouched
# --------------------------------------------------------------------------- #
def test_repair_appends_a_parenthetical_and_never_rewrites_prose():
    en = "TRAI released the new tariff order for broadcasters"
    hi = "नया टैरिफ आदेश जारी किया गया।"
    fixed, injected = ai_translator._repair_missing_acronyms(en, hi, ["TRAI"])
    assert injected == ["TRAI"]
    assert fixed.endswith("(TRAI)।")
    # the Hindi itself is byte-identical: the token is appended, not woven in
    assert fixed[:-len(" (TRAI)।")] + "।" == hi


def test_repair_is_capped_at_max_acronym_repairs(monkeypatch):
    monkeypatch.setattr(ai_translator, "MAX_ACRONYM_REPAIRS", 2)
    en = "TRAI and SEBI and RBI issued circulars"
    hi = "तीनों संस्थाओं ने सर्कुलर जारी किए।"
    _fixed, injected = ai_translator._repair_missing_acronyms(en, hi, ["RBI", "SEBI", "TRAI"])
    assert len(injected) == 2
    # three missing acronyms cannot be repaired -> the line is still rejected
    passed, _conf, _issues = ai_translator._validate(en, _fixed)
    assert not passed


def test_repair_skips_tokens_already_present_in_any_form():
    hi = "ट्राई ने आदेश जारी किया।"
    _fixed, injected = ai_translator._repair_missing_acronyms("TRAI order", hi, ["TRAI"])
    assert injected == [] and _fixed == hi


def test_empty_translation_is_never_repaired():
    assert ai_translator._repair_missing_acronyms("TRAI order", "", ["TRAI"]) == ("", [])


# --------------------------------------------------------------------------- #
# 3. End to end through translate_content
# --------------------------------------------------------------------------- #
def test_line_rejected_only_for_an_acronym_is_repaired_and_accepted(monkeypatch):
    configure_providers(monkeypatch)
    monkeypatch.setattr(ai_translator, "_call_provider",
                        lambda p, s, u: "नया टैरिफ आदेश प्रसारकों के लिए जारी किया गया।")
    res = ai_translator.translate_content("TRAI released the new tariff order for broadcasters")
    assert res["passed"] is True
    assert res["repaired"] == ["TRAI"]
    assert res["translated_hi"].endswith("(TRAI)।")
    # a repaired line never claims full confidence
    assert res["confidence"] <= ai_translator.REPAIRED_CONFIDENCE_CAP


def test_repair_never_rescues_a_line_with_another_problem(monkeypatch):
    """No Devanagari at all: fail closed, exactly as before."""
    configure_providers(monkeypatch)
    monkeypatch.setattr(ai_translator, "_call_provider",
                        lambda p, s, u: "TRAI released the new tariff order")
    res = ai_translator.translate_content("TRAI released the new tariff order today")
    assert res["passed"] is False
    assert res.get("repaired", []) == []
    # every provider was walked and rejected; nothing was repaired
    assert res["issues"] == ["groq: validation failed"]


def test_numbers_gate_still_wins_over_repair(monkeypatch):
    """A dropped figure is a factual problem: no acronym repair may hide it."""
    configure_providers(monkeypatch)
    monkeypatch.setattr(ai_translator, "_call_provider",
                        lambda p, s, u: "किसानों को सहायता दी गई।")
    res = ai_translator.translate_content("TRAI announced Rs. 500 crore support for farmers")
    assert res["passed"] is False
    assert res.get("repaired", []) == []
    assert res["issues"] == ["groq: validation failed"]


def test_kill_switch_restores_reject_only_behaviour(monkeypatch):
    configure_providers(monkeypatch)
    monkeypatch.setattr(ai_translator, "AUTO_REPAIR", False)
    monkeypatch.setattr(ai_translator, "_call_provider",
                        lambda p, s, u: "नया टैरिफ आदेश प्रसारकों के लिए जारी किया गया।")
    res = ai_translator.translate_content("TRAI released the new tariff order for broadcasters")
    assert res["passed"] is False
    assert res["issues"] == ["groq: validation failed"]


def test_repair_stops_the_provider_walk_instead_of_burning_quota(monkeypatch):
    """One repaired line must not walk every provider (the old failure mode)."""
    configure_providers(monkeypatch, ("a", "b", "c"))
    attempted = []

    def call(provider, system, user):
        attempted.append(provider["name"])
        return "नया टैरिफ आदेश प्रसारकों के लिए जारी किया गया।"

    monkeypatch.setattr(ai_translator, "_call_provider", call)
    res = ai_translator.translate_content("TRAI released the new tariff order for broadcasters")
    assert res["passed"] is True and res["provider"] == "a"
    assert attempted == ["a"]

def test_every_curated_hindi_variant_actually_matches():
    """Guard against a typo in the maps: ड/द look alike and silently never match.

    Each curated Hindi form must be recognised for its own acronym, and must not
    be so short that it matches unrelated text."""
    bad = []
    for acr, forms in ai_translator._ACRONYM_HI_VARIANTS.items():
        for form in forms:
            if not ai_translator._acronym_matched_in_hindi(acr, f"{form} ने यह घोषणा की।"):
                bad.append((acr, form))
    assert not bad, bad


def test_caps_word_map_entries_are_recognised():
    bad = [(w, h) for w, forms in ai_translator._CAPS_WORD_HI.items()
           for h in forms
           if len(h) > 2 and not ai_translator._acronym_matched_in_hindi(w, f"{h} में बैठक हुई।")]
    assert not bad, bad[:10]
