# -*- coding: utf-8 -*-
"""Concept-question phrasing variants (pipeline/mcq_concept_variants.py).

KNOWN_MAPPINGS held one fixed question per known topic, so a topic that stayed in
the news reprinted the identical stem every day — the MSP question appeared in 3
of the last 4 published editions. Each concept now has extra phrasings that
rotate through the cross-edition history, least-recently-used first.

The most important test here is the second one: every authored phrasing is run
through the *real* validators, so a future edit to the bank cannot quietly ship a
question that stage 16 would reject (unsupported key, ambiguous distractor,
explanation that does not name the answer, missing Hindi, stale officeholder).
"""
import pytest

from pipeline import mcq_history as h
from pipeline import mcq_quality as q
from pipeline.content import _evidence_text, validate_mcqs
from pipeline.mcq_concept_variants import CONCEPT_VARIANTS

# One realistic story per concept: enough evidence to fire the trigger, and no
# distractor names in it (a distractor that appears in the story is ambiguous).
ITEMS = {
    "msp": ("Cabinet approves higher MSP for 14 Kharif crops",
            "कैबिनेट ने 14 खरीफ फसलों के लिए उच्च MSP को मंज़ूरी दी",
            "The minimum support price for paddy was raised for the 2026-27 season.",
            "2026-27 सत्र के लिए धान का न्यूनतम समर्थन मूल्य बढ़ाया गया।"),
    "repo": ("Central bank keeps the repo rate unchanged at 6.00 percent",
             "केंद्रीय बैंक ने रेपो दर 6.00 प्रतिशत पर अपरिवर्तित रखी",
             "The Monetary Policy Committee kept the policy repo rate unchanged.",
             "मुद्रा नीति समिति ने नीतिगत रेपो दर अपरिवर्तित रखी।"),
    "gst": ("GST Council recommends rate rationalisation for packaged goods",
            "GST परिषद ने पैकेज्ड वस्तुओं पर दर युक्तिकरण की सिफारिश की",
            "The GST rates on several packaged items were revised.",
            "कई पैकेज्ड वस्तुओं पर GST दरें संशोधित की गईं।"),
    "upi": ("UPI transactions touch a record high in October",
            "अक्टूबर में UPI लेनदेन रिकॉर्ड ऊँचाई पर",
            "Unified Payments Interface volumes rose sharply during the festive month.",
            "त्योहारी महीने में यूनिफाइड पेमेंट्स इंटरफेस लेनदेन में तेज़ वृद्धि हुई।"),
    "jjm": ("Jal Jeevan Mission coverage crosses target in three States",
            "तीन राज्यों में जल जीवन मिशन कवरेज लक्ष्य से पार",
            "Rural households received tap connections under the Jal Jeevan Mission.",
            "जल जीवन मिशन के तहत ग्रामीण परिवारों को नल कनेक्शन मिले।"),
    "mgnrega": ("MGNREGA wage employment demand rises in the kharif season",
                "खरीफ मौसम में मनरेगा मजदूरी रोजगार की मांग बढ़ी",
                "Work demand under Mahatma Gandhi National Rural Employment Guarantee Act rose.",
                "मनरेगा के तहत काम की मांग बढ़ी।"),
    "pmjay": ("PM-JAY hospitalisations cross a milestone in rural districts",
              "ग्रामीण जिलों में PM-JAY अस्पताल भर्ती ने मील का पत्थर पार किया",
              "Ayushman Bharat beneficiaries received cashless treatment.",
              "आयुष्मान भारत लाभार्थियों को कैशलेस इलाज मिला।"),
    "enam": ("e-NAM trade crosses record value in agricultural produce",
             "कृषि उपज में e-NAM व्यापार रिकॉर्ड मूल्य पार",
             "Farmers sold produce through the National Agriculture Market platform.",
             "किसानों ने राष्ट्रीय कृषि बाजार मंच के जरिये उपज बेची।"),
}


def item_for(cid):
    he, hh, ke, kh = ITEMS[cid]
    return {"event_id": f"{cid}1", "headline_en": he, "headline_hi": hh,
            "key_points_en": [ke], "key_points_hi": [kh],
            "source": {"name": "Fixture", "url": "https://example.invalid/x"}}


def variant_of(cid, vid, edition_date="2026-11-11", history=None):
    """Force one phrasing so each is checked, whatever the rotation would pick."""
    ci = item_for(cid)
    ev = _evidence_text(ci)
    original = q._pick_variant

    def forced(_mp, eligible, _ctx=None):
        pick = [p for p in eligible if p[0]["vid"] == vid]
        assert pick, f"{cid}/{vid} is not eligible (fewer than 4 usable distractors?)"
        return pick[0]

    q._pick_variant = forced
    try:
        out = q.concept_mcqs(ci, ev, {"edition_date": edition_date, "history": history or {}})
    finally:
        q._pick_variant = original
    assert out, f"{cid}/{vid} produced no question"
    return out[0], ci


def all_vids(cid):
    mp = next(m for m in q.KNOWN_MAPPINGS if m["id"] == cid)
    return [v["vid"] for v in q._variant_list(mp)]


# --------------------------------------------------------------------------- #
# 1. The bank itself
# --------------------------------------------------------------------------- #
def test_every_concept_has_extra_phrasings():
    for mp in q.KNOWN_MAPPINGS:
        variants = CONCEPT_VARIANTS.get(mp["id"])
        assert variants, f"{mp['id']} has no variants"
        assert len(variants) >= 2, f"{mp['id']} has only {len(variants)} variant(s)"


def test_variants_attach_to_the_entry_without_the_guards_running_first():
    """Regression: attaching the bank only inside _mapping_pairs left the rotation
    seeing a single phrasing, so every edition printed the same question."""
    fresh = {"id": "msp", "trigger": r"\bMSP\b", "accept": r"CACP",
             "q": ("a", "b"), "answer": ("c", "d"), "expl": ("e", "f"), "distractors": []}
    assert [v["vid"] for v in q._variant_list(fresh)] == ["v0", "v1", "v2"]
    assert fresh["variants"] == CONCEPT_VARIANTS["msp"]


@pytest.mark.parametrize("cid", sorted(CONCEPT_VARIANTS))
def test_variant_shape(cid):
    import re
    for v in CONCEPT_VARIANTS[cid]:
        assert v["vid"] and v["guard"] and v["accept"], v.get("vid")
        assert len(v["q"]) == 2 and all(v["q"]), v["vid"]
        assert len(v["answer"]) == 2 and v["answer"][0], v["vid"]
        assert len(v["expl"]) == 2 and all(v["expl"]), v["vid"]
        assert len(v["distractors"]) >= 5, f"{cid}/{v['vid']} needs 5+ distractors"
        for d in v["distractors"]:
            assert len(d) == 2 and d[0], f"{cid}/{v['vid']} bad distractor {d}"
        re.compile(v["guard"])
        re.compile(v["accept"])
        # the answer must not leak into its own stem
        assert v["answer"][0].split("(")[0].strip().lower() not in v["q"][0].lower()


# --------------------------------------------------------------------------- #
# 2. Every phrasing survives the real validators
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("cid", sorted(CONCEPT_VARIANTS))
def test_every_phrasing_passes_the_real_validators(cid):
    for vid in all_vids(cid):
        m, ci = variant_of(cid, vid)
        assert m["concept_id"] == cid and m["concept_variant"] == vid
        ok, rej = validate_mcqs([m], [ci])
        assert ok, f"{cid}/{vid}: {[r.get('errors') for r in rej]}"
        assert not q.hindi_errors(m), f"{cid}/{vid}: {q.hindi_errors(m)}"
        assert not q.quality_errors(m, ci, _evidence_text(ci)), q.quality_errors(m, ci, _evidence_text(ci))
        assert len(m["options"]) == 5


def test_no_option_is_a_stale_officeholder_title():
    for cid in CONCEPT_VARIANTS:
        for vid in all_vids(cid):
            m, _ci = variant_of(cid, vid)
            for o in m["options"]:
                assert not q.stale_title_error(o), f"{cid}/{vid}: {q.stale_title_error(o)}"


# --------------------------------------------------------------------------- #
# 3. Rotation
# --------------------------------------------------------------------------- #
def test_without_a_context_the_entry_question_still_wins():
    """Weekly/monthly assembly and existing callers pass no context."""
    m = q.concept_mcqs(item_for("msp"), _evidence_text(item_for("msp")))[0]
    assert m["concept_variant"] == "v0"
    assert m["question_en"].startswith("Which body recommends the Minimum Support Price")


def test_a_topic_in_the_news_rotates_instead_of_reprinting():
    """The complaint: the MSP question printed on 3 of the last 4 editions."""
    ci = item_for("msp")
    ev = _evidence_text(ci)
    hist = h.empty_history()
    picks = []
    for day in range(1, 10):
        date = f"2026-11-{day:02d}"
        m = q.concept_mcqs(ci, ev, {"edition_date": date, "history": hist})[0]
        picks.append(m["concept_variant"])
        h.record(hist, [m], date)
    assert len(set(picks)) == len(CONCEPT_VARIANTS["msp"]) + 1
    # never the same phrasing twice in a row once the bank is exhausted
    assert all(a != b for a, b in zip(picks, picks[1:])), picks


def test_the_pick_is_deterministic_for_a_date_and_history():
    ci, ev = item_for("gst"), _evidence_text(item_for("gst"))
    picks = {q.concept_mcqs(ci, ev, {"edition_date": "2026-11-12", "history": h.empty_history()})[0]["concept_variant"]
             for _ in range(4)}
    assert len(picks) == 1


def test_a_variant_printed_recently_is_passed_over():
    cid = "upi"
    ci, ev = item_for(cid), _evidence_text(item_for(cid))
    hist = h.empty_history()
    first = q.concept_mcqs(ci, ev, {"edition_date": "2026-11-11", "history": hist})[0]
    h.record(hist, [first], "2026-11-11")
    second = q.concept_mcqs(ci, ev, {"edition_date": "2026-11-12", "history": hist})[0]
    assert second["concept_variant"] != first["concept_variant"]


# --------------------------------------------------------------------------- #
# 4. The answer guard stays tight
# --------------------------------------------------------------------------- #
def test_each_guard_matches_its_own_question():
    import re
    for cid in CONCEPT_VARIANTS:
        for v in CONCEPT_VARIANTS[cid]:
            assert re.search(v["guard"], v["q"][0], re.I), f"{cid}/{v['vid']}: guard misses its own stem"
            assert q.known_mapping_supports(v["q"][0], v["answer"][0]), f"{cid}/{v['vid']} is not backed"


def test_a_variants_guard_does_not_back_another_phrasings_answer():
    """Variant guards are phrasing-specific on purpose: a loose one would let a
    wrong key through (asking who *announces* MSP and answering CACP, or asking
    about the amendment and answering the GST Council).

    The check is on the variant pair itself, not on known_mapping_supports: the
    entry's own trigger is deliberately broad ("repo rate") and legitimately
    backs the entry's answer for any stem about that topic."""
    import re
    for cid in CONCEPT_VARIANTS:
        variants = CONCEPT_VARIANTS[cid]
        for a in variants:
            for b in variants:
                if a is b:
                    continue
                assert not (re.search(a["guard"], b["q"][0], re.I)
                            and re.search(a["accept"], b["answer"][0], re.I)), \
                    f"{cid}: {a['vid']} guard backs {b['vid']}'s answer"


def test_a_wrong_key_on_the_entry_question_is_still_rejected():
    conflict = q.mapping_conflict(
        "Which body recommends the Minimum Support Price (MSP) of notified crops?", "NITI Aayog")
    assert "wrong key" in conflict and "MSP" in conflict


def test_a_wrong_key_on_a_strict_variant_question_is_still_rejected():
    """msp is a strict concept and this variant's stem asks for an organisation, so
    the conflict guard applies to it exactly as it does to the entry question."""
    stem = "The Commission for Agricultural Costs and Prices (CACP) works under which Union Ministry?"
    assert q.known_mapping_supports(stem, "Ministry of Agriculture and Farmers Welfare")
    for wrong in ("Ministry of Finance", "NITI Aayog"):
        conflict = q.mapping_conflict(stem, wrong)
        assert "wrong key" in conflict, (wrong, conflict)
        assert not q.known_mapping_supports(stem, wrong), wrong


# --------------------------------------------------------------------------- #
# 5. stale_title_error: a post with no name attached is not a stale officeholder
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("option", [
    "The Prime Minister of India",
    "Prime Minister of India",
    "The Comptroller and Auditor General of India",
    "Union Finance Minister",
    "Ministry of Agriculture and Farmers Welfare",
])
def test_a_bare_post_is_not_a_stale_title(option):
    assert q.stale_title_error(option) == ""


def test_a_post_paired_with_the_wrong_name_is_still_stale():
    err = q.stale_title_error("The Union Agriculture Minister Narendra Singh Tomar")
    assert "stale officeholder title" in err, err
