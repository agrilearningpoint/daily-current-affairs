# -*- coding: utf-8 -*-
"""MCQ quality fixes (audit 2026-11-04): answer spread, wrong keys, broken templates,
headline-answered questions, stale officeholder titles. All offline / mocked."""
import json

from pipeline import mcq_quality as q
from pipeline.content import validate_mcqs

MSP_ITEM = {
    "event_id": "msp1", "headline_en": "Cabinet approves higher MSP for 14 Kharif crops",
    "headline_hi": "कैबिनेट ने 14 खरीफ फसलों के लिए उच्च MSP को मंज़ूरी दी",
    "key_points_en": ["The MSP for paddy was raised by Rs 69 per quintal for the 2026-27 season, said ICAR officials."],
    "key_points_hi": ["2026-27 सत्र के लिए धान का MSP 69 रुपये प्रति क्विंटल बढ़ाया गया।"],
    "source": {"name": "DD News", "url": "https://x"},
}


def _mcq(options, correct="A", **kw):
    m = {"type": "org-pool", "event_id": "msp1", "question_en": kw.pop("q", "Which organisation is associated with the news about crop prices?"),
         "question_hi": "प्रश्न?", "options": options, "correct": correct,
         "explanation_en": kw.pop("expl", "Paddy support price rose by Rs 69 per quintal this season; answer %s." % options[0].split(" / ")[0])}
    m.update(kw)
    return m


def test_balance_spreads_keys_and_is_deterministic():
    mcqs = [_mcq(["Right%d" % i, "W1", "W2", "W3", "W4"], explanation_en="Option A is right") for i in range(15)]
    for i, m in enumerate(mcqs):
        m["q_num"] = i + 1
    a = q.balance_answer_positions([dict(m) for m in mcqs], "2026-11-04")
    b = q.balance_answer_positions([dict(m) for m in mcqs], "2026-11-04")
    assert [m["options"] for m in a] == [m["options"] for m in b]
    spread = q.letter_spread(a)
    assert max(spread.values()) <= 3 and len(spread) == 5
    for i, m in enumerate(a):
        assert m["options"]["ABCDE".index(m["correct"])] == "Right%d" % i
        assert m["explanation_en"] == "Option %s is right" % m["correct"]
        assert m["q_num"] == i + 1


def test_shuffle_remaps_hindi_options_and_pairs():
    m = {"options": ["CACP", "ICAR", "FCI", "NAFED", "NABARD"], "options_hi": ["क", "ख", "ग", "घ", "ङ"],
         "correct": "A", "explanation_pairs": [{"en": "Answer: (A) CACP", "hi": "उत्तर: (A)"}]}
    s = q.shuffle_mcq(m, "2026-11-04|3", target=3)
    assert s["correct"] == "D" and s["options"][3] == "CACP" and s["options_hi"][3] == "क"
    assert s["explanation_pairs"][0]["en"] == "Answer: (D) CACP"
    assert m["correct"] == "A"  # original untouched


def test_msp_question_keyed_to_icar_is_rejected():
    m = _mcq(["ICAR", "CACP", "FCI", "NAFED", "NABARD"], q="Which organisation is associated with the news \"higher MSP for 14 Kharif crops\"?")
    _, rej = validate_mcqs([m], [MSP_ITEM])
    assert any("wrong key" in e for e in rej[0]["errors"])


def test_concept_question_built_for_msp_story_and_valid():
    from pipeline.content import _evidence_text
    ev = _evidence_text(MSP_ITEM)
    cands = q.concept_mcqs(MSP_ITEM, ev)
    assert cands and cands[0]["concept_id"] == "msp"
    m = cands[0]
    ans = m["options"]["ABCDE".index(m["correct"])]
    assert ans.startswith("Commission for Agricultural Costs and Prices (CACP) / ")
    assert not any(o.startswith("Indian Council of Agricultural Research") for o in m["options"])  # ICAR is in the story
    ok, rej = validate_mcqs([m], [MSP_ITEM])
    assert ok, rej


def test_concept_ranked_before_headline_template():
    from pipeline.mcq_builder import first_valid
    from pipeline.content import _evidence_text
    concept = q.concept_mcqs(MSP_ITEM, _evidence_text(MSP_ITEM))[0]
    headline_q = _mcq(["MSP", "GDP", "CPI", "WPI", "IIP"])  # answer sits in the headline
    m, _ = first_valid([headline_q, concept], MSP_ITEM, set())
    assert m["type"] == "concept"


def test_broken_templates_rejected():
    item = dict(MSP_ITEM)
    checks = [
        (_mcq(["75%", "150%", "112.5%", "93.75%", "37.5%"], q="What is the key figure associated with: \"FTA pipeline could cover of exports\"?"),
         ["missing number", "above 100%"]),
        (_mcq(["Fact 1", "B2", "C3", "D4", "E5"]), ["placeholder"]),
        (_mcq(["NABARD", "SIDBI", "Exim Bank", "NHB", "SIDBI"]), ["duplicate"]),
        (_mcq(["NABARD", "Dr. Neha Sharma", "SIDBI", "Exim Bank", "NHB"]), ["fabricated person"]),
        (_mcq(["NABARD", "SIDBI", "Exim Bank", "NHB", "IFCI"], expl="NABARD (Key: DD News)"), ["placeholder"]),
        (_mcq(["NABARD", "SIDBI", "Exim Bank", "NHB", "IFCI"],
              expl="As per DD News: Cabinet approves higher MSP for 14 Kharif crops NABARD."), ["repeats the headline"]),
        (_mcq(["NABARD", "Union Agriculture Minister Narendra Singh Tomar", "SIDBI", "Exim Bank", "NHB"]), ["stale officeholder"]),
    ]
    for m, wants in checks:
        errs = q.quality_errors(m, item, "")
        for w in wants:
            assert any(w in e for e in errs), (w, errs)


def test_current_officeholder_title_is_fine():
    assert q.stale_title_error("Union Agriculture Minister Shivraj Singh Chouhan") == ""
    assert q.stale_title_error("NABARD") == ""
    assert q.quality_errors(_mcq(["NABARD", "SIDBI", "Exim Bank / एक्ज़िम बैंक", "NHB", "IFCI"]), MSP_ITEM, "") == []


def test_legacy_number_template_dropped_when_number_was_in_headline():
    from pipeline.mcq_builder import _legacy_fix
    item = {"headline_en": "FTA pipeline could cover 75% of exports", "key_points_en": ["Talks cover the EU and UK."]}
    m = {"type": "static-number", "options": ["75%", "50%", "60%", "80%", "90%"], "correct": "A"}
    assert _legacy_fix(m, item) is None
    m2 = {"type": "who-org", "options": ["NABARD", "SIDBI", "Exim Bank", "NHB", "IFCI"], "correct": "A",
          "explanation_en": "Verified reporting by DD News features NABARD in this development."}
    fixed = _legacy_fix(m2, item)
    assert fixed["explanation_en"].startswith("Talks cover the EU and UK") and "NABARD" in fixed["explanation_en"]


def _llm_reply(correct="A"):
    return {"mcq": {"question": {"en": "Which State's cyclone relief is reported?", "hi": "किस राज्य?"},
                    "options": [{"en": x, "hi": h} for x, h in [("Telangana", "तेलंगाना"), ("Kerala", "केरल"),
                                                                ("Bihar", "बिहार"), ("Goa", "गोवा"), ("Assam", "असम")]],
                    "correct": correct},
            "explanation": [{"en": f"Telangana relief fact {i}.", "hi": f"तेलंगाना तथ्य {i}।"} for i in range(4)]}


def test_llm_self_verify_mismatch_regenerates_once_then_drops():
    from pipeline.mcq_schema import generate_llm_mcqs
    calls = []

    def route(prompt, **kw):
        calls.append(prompt)
        if "MCQ SELF-CHECK" in prompt:
            return '{"answer": "B"}'
        return json.dumps(_llm_reply())

    out = generate_llm_mcqs([{"event_id": "c", "headline_en": "x"}], lambda i: "Telangana cyclone", route=route, attempts=1)
    assert out == {}
    gen = [p for p in calls if "MCQ SELF-CHECK" not in p]
    assert len(gen) == 2 and "self-check" in gen[1]


def test_llm_self_verify_match_accepts():
    from pipeline.mcq_schema import generate_llm_mcqs

    def route(prompt, **kw):
        return '{"answer": "A"}' if "MCQ SELF-CHECK" in prompt else json.dumps(_llm_reply())

    out = generate_llm_mcqs([{"event_id": "c", "headline_en": "x"}], lambda i: "Telangana cyclone", route=route, attempts=1)
    assert "c" in out


def test_parse_verify_reply():
    assert q.parse_verify_reply('{"answer": "c"}') == "C"
    assert q.parse_verify_reply("B)") == "B"
    assert q.parse_verify_reply('{"mcq": {"correct": "A"}}') == ""
    assert q.parse_verify_reply(None) == ""


def test_job_date_of():
    assert q.job_date_of("daily_2026-11-04") == "2026-11-04"
    assert q.job_date_of("x", {"job": {"date": "2026-11-03"}}) == "2026-11-03"
