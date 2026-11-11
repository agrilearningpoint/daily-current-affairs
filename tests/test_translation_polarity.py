"""Polarity guard tests (2026-11-11: "rate hike" printed as "दर कटौती")."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import ai_translator as at  # noqa: E402

Q2_EN = ("Fed’s Christopher Waller opens door to 50-basis-point December rate hike after hot CPI")
Q2_HI_BAD = ("फेड के क्रिस्टोफर वालर ने गर्म सीपीआई के बाद दिसंबर में 50 आधार अंकों की दर कटौती के द्वार खोले")
Q2_HI_GOOD = ("फेडरल रिजर्व के गवर्नर क्रिस्टोफर वॉलर ने अक्टूबर में अमेरिकी कोर महंगाई में 0.3% की वृद्धि के बाद "
              "दिसंबर में 50-बेसिस-पॉइंट की दर में बढ़ोतरी की संभावना जताई है")


def test_real_q2_headline_pair_is_flagged():
    issues = at.polarity_conflicts(Q2_EN, Q2_HI_BAD)
    assert issues and all(i.startswith("polarity conflict") for i in issues)


def test_real_q2_summary_pair_is_clean():
    assert at.polarity_conflicts(Q2_EN, Q2_HI_GOOD) == []


def test_validate_rejects_inverted_headline():
    passed, _conf, issues = at._validate(Q2_EN, Q2_HI_BAD)
    assert not passed
    assert any(i.startswith("polarity conflict") for i in issues)


def test_polarity_repair_fixes_and_revalidates():
    fixed, swapped = at._repair_polarity(Q2_EN, at._polish_hindi(Q2_HI_BAD))
    assert swapped == ["कटौती->बढ़ोतरी"]
    assert "दर बढ़ोतरी" in fixed
    passed, _conf, issues = at._validate(Q2_EN, fixed)
    assert passed, issues


def test_correct_directions_not_flagged():
    assert at.polarity_conflicts("The RBI announced a rate cut.", "आरबीआई ने दर कटौती की घोषणा की।") == []
    assert at.polarity_conflicts("The RBI announced a rate hike.", "आरबीआई ने दर बढ़ोतरी की घोषणा की।") == []
    assert at.polarity_conflicts("Inflation fell to a five-year low.", "मुद्रास्फीति गिरकर पांच साल के निचले स्तर पर रही।") == []
    assert at.polarity_conflicts("Inflation rose 0.3% in October.", "अक्टूबर में महंगाई में 0.3% की वृद्धि हुई।") == []


def test_approval_pairs_flag_without_auto_swap():
    en = "The Union cabinet approves the new logistics policy."
    hi = "केंद्रीय मंत्रिमंडल ने नई लॉजिस्टिक्स नीति को खारिज कर दिया।"
    issues = at.polarity_conflicts(en, hi)
    assert issues
    fixed, swapped = at._repair_polarity(en, hi)
    assert swapped == [] and fixed == hi  # never auto-rewrite verbs


def test_stutter_collapse_and_allowlist():
    assert at._polish_hindi("प्रमुख प्रमुख योजनाओं में पीएम-किसान शामिल हैं।") == "प्रमुख योजनाओं में पीएम-किसान शामिल हैं।"
    assert at._polish_hindi("धीरे धीरे कीमतें बढ़ीं।") == "धीरे धीरे कीमतें बढ़ीं।"


def test_calque_fix_keeps_acronym():
    out = at._polish_hindi("गर्म सीपीआई के बाद दिसंबर में दर बढ़ोतरी के द्वार खोले")
    assert "उच्च सीपीआई" in out and "गर्म सीपीआई" not in out
