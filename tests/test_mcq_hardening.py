# -*- coding: utf-8 -*-
"""MCQ hardening gates (weekly audit 2026-11-08), with the audited questions as fixtures."""
from pipeline import mcq_quality as q
from pipeline import period_builder as pb

NHRC_STORY = ("NHRC takes suo motu cognizance of a Government Primary School in Darbhanga, Bihar, where the "
              "roof is supported on benches after a pillar collapsed.")
KIWI_STORY = ("APEDA facilitates trial export of 1.5 MT of Arunachal Pradesh kiwi to Dubai; the consignment of "
              "2 containers was flagged off from Itanagar.")
ZSI_STORY = ("Union Environment Minister Shri Bhupender Yadav inaugurates Animal Taxonomy Summit 2026 on 111th "
             "Foundation Day of Zoological Survey of India")


def q24(correct="C"):  # printed key letter in the audit report was C (Gaya)
    return {"type": "llm-schema", "event_id": "nhrc",
            "question_en": "In which district of Bihar did the NHRC recently take suo motu cognizance of a "
                           "dilapidated Government Primary School roof supported on benches after a pillar collapse?",
            "question_hi": "बिहार के किस जिले में NHRC ने हाल ही में जर्जर सरकारी प्राथमिक विद्यालय की छत का स्वतः संज्ञान लिया?",
            "options": ["Darbhanga", "Patna", "Gaya", "Muzaffarpur", "Bhagalpur"],
            "options_hi": ["दरभंगा", "पटना", "गया", "मुजफ्फरपुर", "भागलपुर"], "correct": correct,
            "explanation_en": "NHRC acted on a report about the school roof in Bihar."}


def q28(correct="B"):
    return {"type": "llm-schema", "event_id": "kiwi",
            "question_en": "What was the quantity of Arunachal Pradesh kiwi that APEDA facilitated for trial export to Dubai?",
            "question_hi": "एपीडा ने दुबई को ट्रायल निर्यात के लिए अरुणाचल प्रदेश के कीवी की कितनी मात्रा सुगम की?",
            "options": ["0.5 MT", "2 MT", "1 MT", "1.5 MT", "3 MT"],
            "options_hi": ["0.5 MT", "2 MT", "1 MT", "1.5 MT", "3 MT"], "correct": correct}


Q1 = {"question_en": "Which state is mentioned as having the highest number of MSMEs in the news?",
      "question_hi": "कौन सा राज्य समाचार में सबसे अधिक MSME के साथ उल्लेखित है?",
      "options": ["Karnataka with 50 lakh MSMEs / कर्नाटक 50 लाख MSME के साथ",
                  "Maharashtra leading with one crore MSMEs / महाराष्ट्र एक करोड़ MSME के साथ अग्रणी",
                  "Kerala with 30 lakh MSMEs / केरल 30 लाख MSME के साथ", "Delhi with 20 lakh MSMEs / दिल्ली 20 लाख MSME के साथ",
                  "Gujarat with 40 lakh MSMEs / गुजरात 40 लाख MSME के साथ"], "correct": "B"}
Q27 = {"question_en": "In which village of the southern Zaporizhzhia region did the Russian strikes on an aid centre "
                      "and shelter occur?", "question_hi": "दक्षिणी ज़ापोरिजिया क्षेत्र के किस गाँव में रूसी हमले हुए?",
       "options": ["Kakhovka / काखोव्का", "Komyshuvakha / कोमिशुवाखा", "Oryol / ओर्योल", "Belgorod / बेलगोरोड",
                   "Kursk / कुर्स्क"], "correct": "B"}
Q29 = {"question_en": "Who inaugurated the Animal Taxonomy Summit 2026 on the 111th Foundation Day of the Zoological "
                      "Survey of India?", "question_hi": "किसने एनीमल टैक्सोनॉमी समिट 2026 का उद्घाटन किया?",
       "options": ["Union Home Minister Amit Shah / केंद्रीय गृह मंत्री अमित शाह",
                   "Union Agriculture Minister Narendra Singh Tomar / केंद्रीय कृषि मंत्री नरेंद्र सिंह तोमर",
                   "Union Finance Minister Nirmala Sitharaman / केंद्रीय वित्त मंत्री निर्मला सीतारमण",
                   "Union Environment Minister Shri Bhupender Yadav / केंद्रीय पर्यावरण मंत्री श्री भूपेन्द्र यादव",
                   "Union Health Minister Mansukh Mandaviya / केंद्रीय स्वास्थ्य मंत्री मनसुख मांडविया"], "correct": "D"}


# 1. key consistency ---------------------------------------------------------
def test_q24_wrong_key_is_rekeyed_to_the_story_answer():
    action, idx, why = q.key_check(q24("C"), NHRC_STORY)
    assert (action, idx) == ("rekey", 0) and "Darbhanga" in why
    fixed, errs = q.harden_mcq(q24("C"), NHRC_STORY)
    assert errs == [] and fixed["correct"] == "A" and fixed["rekeyed"]
    assert q.key_check(q24("A"), NHRC_STORY)[0] == "ok"


def test_q28_number_matched_by_value_and_unit_not_by_a_stray_digit():
    fixed, errs = q.harden_mcq(q28("B"), KIWI_STORY)    # '2 containers' must not support '2 MT'
    assert errs == [] and fixed["correct"] == "D"
    assert q.key_check(q28("D"), "APEDA trial export of 1.5 metric tonnes of kiwi to Dubai")[0] == "ok"


def test_key_contradicted_by_one_liner_is_dropped():
    story = "NHRC notice on a dilapidated school roof in Bihar."
    m = q24("C")
    assert q.key_check(m, story, "NHRC: school roof on benches after pillar collapse, Darbhanga, Bihar")[0] == "drop"
    assert q.harden_mcq(m, story, "NHRC school roof benches Darbhanga Bihar pillar collapse")[0] is None


def test_daily_validator_rejects_a_wrong_key():
    errs = q.quality_errors(q24("C"), {}, NHRC_STORY)
    assert any(e.startswith("wrong key") for e in errs)


# 2. grounding ---------------------------------------------------------------
def test_q1_answer_not_in_story_is_dropped():
    assert q.key_check(Q1, "VIT Vellore signs an MoU to train MSMEs in digital tools.")[0] == "drop"


def test_standing_fact_backs_an_officeholder_key():
    m = {"question_en": "Who is the current Union Agriculture Minister of India?", "question_hi": "कृषि मंत्री कौन हैं?",
         "options": ["Shivraj Singh Chouhan / शिवराज सिंह चौहान", "Amit Shah / अमित शाह", "Rajnath Singh / राजनाथ सिंह",
                     "Piyush Goyal / पीयूष गोयल"], "correct": "A"}
    assert q.key_check(m, "Kharif sowing review held in Delhi.")[0] == "ok"


# 3. give-aways --------------------------------------------------------------
def test_q1_leading_is_a_giveaway():
    assert any("leading" in e for e in q.giveaway_errors(Q1))


def test_audited_giveaways_rejected():
    q17 = {"question_en": "Which location has been notified as India's first Organic Fisheries Cluster under PMMSY?",
           "question_hi": "कौन सा स्थान?", "options": ["Assam", "Madhya Pradesh", "Kerala", "Nagaland", "Soreng, Sikkim"],
           "correct": "E"}
    q36 = {"question_en": "Which of the following initiatives was launched by Union Minister Shri Rajiv Ranjan Singh in Sikkim?",
           "question_hi": "कौन-सी पहल?", "options": ["Agricultural Credit Guarantee", "Digital Literacy Programme",
                                                    "Solar Power Scheme", "Rural Water Supply Project",
                                                    "Churpi Traceability Initiative"], "correct": "E"}
    q6 = {"question_en": "The Indian Foreign Secretary who made an official visit in early November 2026 is an officer "
                         "of which Ministry?", "question_hi": "किस मंत्रालय?",
          "options": ["Ministry of Home Affairs", "Ministry of Finance", "Ministry of Commerce and Industry",
                      "Ministry of External Affairs", "Ministry of Defence"], "correct": "D"}
    q3 = {"question_en": "With which United Nations organ does the Sustainable Development Council hold Special "
                         "Consultative Status?", "question_hi": "किस निकाय?",
          "options": ["World Health Organization (WHO)", "International Labour Organization (ILO)",
                      "United Nations Development Programme (UNDP)", "United Nations Children's Fund (UNICEF)",
                      "United Nations Economic and Social Council (ECOSOC)"], "correct": "E"}
    q33 = {"question_en": "What did the Supreme Court say regarding the duration of occupying a protest site in Delhi?",
           "question_hi": "क्या कहा?", "options": ["Protest site cannot be occupied ‘for all times to come’",
                                                 "Protest sites may be occupied indefinitely",
                                                 "Occupying protest sites is allowed during election periods",
                                                 "The court permits permanent occupation of sites",
                                                 "Sites must be cleared within 24 hours of an order"], "correct": "A"}
    for m in (q17, q36, q6, q3, q33):
        assert q.giveaway_errors(m), m["question_en"]


def test_balanced_question_has_no_giveaway():
    m = {"question_en": "Which state hosted the first International Maize Conference 2026?", "question_hi": "किस राज्य?",
         "options": ["Telangana", "Karnataka", "Bihar", "Punjab", "Odisha"], "correct": "A"}
    assert q.giveaway_errors(m) == []


# 4. absurd options / entity types ------------------------------------------
def test_q27_russian_cities_for_a_zaporizhzhia_village():
    assert any("absurd" in e for e in q.giveaway_errors(Q27))


def test_numbers_need_same_unit_and_magnitude():
    base = {"question_en": "What is the outlay of the scheme?", "question_hi": "परिव्यय?", "correct": "A"}
    assert q.type_errors(dict(base, options=["₹500 crore", "₹600 crore", "₹700 crore", "₹800 crore"])) == []
    assert q.type_errors(dict(base, options=["₹500 crore", "45%", "₹700 crore", "₹800 crore"]))
    assert q.type_errors(dict(base, options=["₹500 crore", "₹6 lakh crore", "₹700 crore", "₹800 crore"]))
    assert q.type_errors(dict(base, options=["Bihar", "Gujarat", "Nepal", "Kerala"]))


# 5. stale ministers ---------------------------------------------------------
def test_q29_outdated_ministers_rejected_and_mandaviya_alone_too():
    assert any("stale officeholder" in e for e in q.quality_errors(Q29, {}, ZSI_STORY))
    assert "stale" in q.stale_title_error("Union Health Minister Mansukh Mandaviya")
    assert q.stale_title_error("Union Health Minister J.P. Nadda") == ""
    assert q.stale_title_error("Union Environment Minister Shri Bhupender Yadav") == ""


# 6. Hindi ---------------------------------------------------------------------
def test_hindi_required_for_stem_and_every_option():
    m = dict(Q27, options=["Kakhovka / काखोव्का", "Komyshuvakha", "Melitopol / मेलिटोपोल", "Vasylivka / वासिलिव्का"])
    assert q.hindi_errors(m)
    assert q.hindi_errors(dict(Q27, question_hi="")) == ["Hindi missing: question"]
    assert q.hindi_errors(q28()) == []          # bare quantities may stay as they are
    assert q.hindi_errors(Q27) == []


# 7. shortfall: a bad question is replaced, never kept --------------------------
def _ed(mcqs, one_liners=()):
    return {"date": "2026-11-03", "content": {"one_liners": list(one_liners)}, "mcqs": mcqs}


def test_period_pick_drops_bad_rekeys_wrong_and_fills_from_reserves():
    verified = {
        "nhrc": {"event_id": "nhrc", "headline_en": "NHRC notice on Darbhanga school roof", "summary_en": NHRC_STORY},
        "kiwi": {"event_id": "kiwi", "headline_en": "APEDA kiwi export to Dubai", "summary_en": KIWI_STORY},
        "zsi": {"event_id": "zsi", "headline_en": "Animal Taxonomy Summit 2026", "summary_en": ZSI_STORY},
    }
    bad = dict(Q29, event_id="zsi", options_hi=None)
    reserve_kiwi = q28("D")
    eds = [_ed([q24("C"), bad, reserve_kiwi])]
    out = pb.pick_mcqs(eds, set(verified), ["nhrc", "zsi"], 3, verified)
    assert [m["event_id"] for m in out] == ["nhrc", "kiwi"]
    assert out[0]["correct"] == "A" and out[1]["correct"] == "D"


# 8. layout --------------------------------------------------------------------
def test_pack_order_fills_pages_and_keeps_every_question():
    hs = [300, 300, 300, 100, 100, 300]
    from src.period_pdf import _pack_order
    order = _pack_order(hs, 700, 700)
    assert sorted(order) == list(range(6))
    assert order[:4] == [0, 1, 3, 4] or order[:3] == [0, 1, 3]


def test_short_options_use_columns():
    from src.period_pdf import _options_grid
    grid = _options_grid([("Darbhanga", "दरभंगा"), ("Patna", "पटना"), ("Gaya", "गया"), ("Muzaffarpur", "मुजफ्फरपुर"),
                          ("Bhagalpur", "भागलपुर")])
    assert len(grid._cellvalues[0]) == 3
    long = _options_grid([("Labour-intensive exporters in textiles, apparel, and gems and jewellery", "श्रम-प्रधान निर्यातक")] * 4)
    assert len(long._cellvalues[0]) == 1
