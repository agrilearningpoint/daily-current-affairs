"""The numbers gate in pipeline/ai_translator.py (widened 2026-11-10).

Two silent holes: `\\d{1,3}` never matched an ungrouped 4+ digit figure ("5000
crore"), and the trailing `\\b` can never match after `%`, so no percentage was
ever demanded from a translation. Both are closed here; measured against 512 real
EN/HI pairs from four published editions the change flags zero additional lines.

No network.
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


# --------------------------------------------------------------------------- #
# 1. What the gate now demands
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("phrase", [
    "25%", "6.5%", "5000 crore", "12500 crore", "3500 tonnes", "1200 hectares",
    "Rs. 5,000 crore", "$250 million", "5 per cent", "1.5 lakh",
])
def test_figures_that_must_survive_translation(phrase):
    assert ai_translator._NUM_RE.findall(f"the report cites {phrase} this year"), phrase


@pytest.mark.parametrize("text", [
    # percent-encoded URL escapes are not figures
    "thumb/8/80/Vienna_Allied_sectors_%281945-1955%29.png",
    # bare numbers with no unit were never in scope and stay out of it
    "section 12 of the act", "the 2026 budget session",
])
def test_text_that_must_not_be_treated_as_a_figure(text):
    assert ai_translator._NUM_RE.findall(text) == []


def test_ungrouped_and_comma_grouped_figures_are_treated_alike():
    """The old gate depended on how the source happened to be punctuated."""
    assert ai_translator._NUM_RE.findall("a 5000 crore fund") == ["5000 crore"]
    assert ai_translator._NUM_RE.findall("a 5,000 crore fund") == ["5,000 crore"]
    assert (ai_translator._numeric_values("5000 crore")
            == ai_translator._numeric_values("5,000 crore") == {"5000"})


# --------------------------------------------------------------------------- #
# 2. Validation verdicts
# --------------------------------------------------------------------------- #
def test_dropped_percentage_is_now_caught():
    en = "Retail inflation eased to 6.5% in October"
    passed, _conf, issues = ai_translator._validate(en, "अक्टूबर में खुदरा मुद्रास्फीति घटी।")
    assert not passed and any("missing numbers" in i for i in issues), issues


def test_percentage_written_in_devanagari_passes():
    en = "Retail inflation eased to 6.5% in October"
    passed, conf, issues = ai_translator._validate(en, "अक्टूबर में खुदरा मुद्रास्फीति ६.५% पर आई।")
    assert passed, issues
    assert conf == 1.0


def test_dropped_four_digit_figure_is_now_caught():
    en = "The government allocated 5000 crore for irrigation projects"
    passed, _conf, issues = ai_translator._validate(en, "सरकार ने सिंचाई परियोजनाओं के लिए राशि आवंटित की।")
    assert not passed and any("missing numbers" in i for i in issues), issues


def test_four_digit_figure_kept_in_hindi_passes():
    en = "The government allocated 5000 crore for irrigation projects"
    passed, _conf, issues = ai_translator._validate(en, "सरकार ने सिंचाई परियोजनाओं के लिए 5000 करोड़ आवंटित किए।")
    assert passed, issues


def test_comma_grouped_figure_behaviour_is_unchanged():
    """This case already worked before the fix; it must keep working."""
    en = "The government allocated Rs. 5,000 crore for irrigation"
    assert not ai_translator._validate(en, "सरकार ने राशि आवंटित की।")[0]
    assert ai_translator._validate(en, "सरकार ने ₹5,000 करोड़ आवंटित किए।")[0]


# --------------------------------------------------------------------------- #
# 3. End to end: a dropped figure is never rescued by the acronym repair
# --------------------------------------------------------------------------- #
def test_missing_figure_rejects_and_is_not_repaired(monkeypatch):
    configure_providers(monkeypatch)
    monkeypatch.setattr(ai_translator, "_call_provider",
                        lambda p, s, u: "सरकार ने सिंचाई परियोजनाओं के लिए राशि आवंटित की।")
    res = ai_translator.translate_content(
        "TRAI said the government allocated 5000 crore for irrigation projects")
    assert res["passed"] is False
    assert res.get("repaired", []) == []


def test_figure_kept_and_acronym_dropped_is_repaired(monkeypatch):
    """The repair still fires when the acronym is the only remaining problem."""
    configure_providers(monkeypatch)
    monkeypatch.setattr(ai_translator, "_call_provider",
                        lambda p, s, u: "सरकार ने सिंचाई परियोजनाओं के लिए 5000 करोड़ आवंटित किए।")
    res = ai_translator.translate_content(
        "TRAI said the government allocated 5000 crore for irrigation projects")
    assert res["passed"] is True
    assert res["repaired"] == ["TRAI"]
    assert res["translated_hi"].endswith("(TRAI)।")
