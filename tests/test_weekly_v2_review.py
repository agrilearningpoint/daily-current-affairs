"""Weekly 2026-11-08 v2 review fixes: headline-echo bullets, off-topic Static GK,
sections, local/foreign drops, blurb MCQs, same-event duplicate MCQs, Hindi slips."""
from datetime import date

import pipeline.period_builder as pb
from pipeline.exam_relevance import drop_reason
from pipeline.text_normalize import resolve_weekdays


def test_headline_echo_bullets_are_not_story_text():
    it = {"headline_en": "Shri Inbasekar Sundaramurthi appointed as the next Ambassador of India to the Republic of Senegal",
          "source": {"name": "Ministry of External Affairs"}}
    assert pb.headline_echo("Senegal Ministry of External, Shri Inbasekar Sundaramurthi.", it)
    assert not pb.headline_echo("He is presently Joint Secretary in the Ministry and served in Paris.", it)
    it2 = {"headline_en": "DARE–ICAR Completes Special Campaign 6.0, Cleans Around 8,000 Sites Across the Country",
           "source": {"name": "PIB"}}
    assert pb.headline_echo("ICAR Completes Special Campaign, Cleans Around.", it2)


def test_static_gk_about_an_org_the_story_does_not_show_is_dropped():
    story = {"event_id": "e", "headline_en": "Centre extends tenure of Nandan Nilekani-led exam reform panel till January",
             "summary_en": "The Centre has extended the tenure of the task force till January 2027.",
             "detailed_explanation_en": "The panel also consulted former ISRO chairman K Radhakrishnan.",
             "summary_pairs": [{"en": "The Centre has extended the tenure of the task force.", "hi": "x"}],
             "static_gk_pairs": [{"en": "ISRO is headquartered in Bengaluru, Karnataka.", "hi": "इसरो"}]}
    pb._attach_static_gk(story, {})
    assert story["static_gk_pairs"] == []
    rbi = {"event_id": "r", "headline_en": "RBI starts 3 surveys to capture inflation expectations",
           "summary_en": "The Reserve Bank on Tuesday announced three surveys.",
           "static_gk_pairs": [{"en": "The Reserve Bank of India (RBI) was established on 1 April 1935.", "hi": "आरबीआई"}]}
    pb._attach_static_gk(rbi, {})
    assert len(rbi["static_gk_pairs"]) == 1


def test_sections_for_misfiled_daily_categories():
    sf = lambda h, c: pb.section_for({"headline_en": h, "category": c, "summary_en": ""})
    assert sf("Russian strikes on Ukrainian aid centre, shelter kill 26", "Banking & Finance") == "International"
    assert sf("US consortium pushes for $4.4 billion LNG project in Pakistan: Report", "Banking & Finance") == "International"
    assert sf("Centre extends tenure of Nandan Nilekani-led exam reform panel till January", "Banking & Finance") == "National"
    assert sf("Cyclone Murasu: Andhra Pradesh CM pegs preliminary damage at ₹1,918.5 crore", "Agriculture") == "National"
    assert sf("Barclays to invest ₹1,500 crore in India, boost banking businesses", "International") == "Economy"
    assert sf("RBI starts 3 surveys to capture inflation expectations, consumer confidence", "Banking & Finance") == "Economy"


def test_foreign_conflict_and_local_desk_drops():
    assert drop_reason({"headline_en": "Russian strikes on Ukrainian aid centre, shelter kill 26, about 20 missing"})
    assert drop_reason({"headline_en": "US consortium pushes for $4.4 billion LNG project in Pakistan: Report"})
    assert drop_reason({"headline_en": "Centre orders rice stock disclosure, allows five states to impose limits"}) == ""
    local = {"headline_en": "MSME training programme held at VIT in Vellore",
             "source": {"url": "https://www.thehindu.com/news/national/tamil-nadu/msme-training-programme-held-at-vit-in-vellore/article1.ece"}}
    assert pb.local_story_reason(local)
    agri = {"headline_en": "Namakkal farmers get crop insurance payout",
            "source": {"url": "https://www.thehindu.com/news/national/tamil-nadu/x/article2.ece"}}
    assert pb.local_story_reason(agri) == ""


def _m(q, opts, correct, eid, expl=""):
    return {"event_id": eid, "question_en": q, "question_hi": "प्रश्न", "options": opts, "correct": correct,
            "explanation_en": expl}


def test_blurb_mcqs_are_junk():
    m = _m("Which institution issued the guidelines mentioned in the RBI Nagpur initiative?",
           ["RBI", "SBI", "PNB", "BoB"], "A", "e", "RBI Nagpur has launched regulator guidelines and PSL quota monitoring.")
    assert pb.blurb_mcq(_m("Which of the following aspects was mentioned alongside regulatory guidelines and "
                           "monetary policy reviews?", ["a", "b", "c", "d"], "A", "e"))
    assert pb.blurb_mcq(dict(m, explanation_en="It covers implementing ministries, financial outlays, target demographics."))
    assert not pb.blurb_mcq(_m("How many applicants were approved?", ["10", "12", "15", "20"], "B", "e"))


def test_same_event_duplicate_or_giveaway_mcqs_are_skipped():
    ed = {"date": "2026-11-05", "content": {"one_liners": []}, "mcqs": [
        _m("In which city will the Skill India International Centre be set up?",
           ["Indore / इंदौर", "Bhopal / भोपाल", "Gwalior / ग्वालियर", "Jabalpur / जबलपुर"], "B", "s"),
        _m("Which city was selected for the establishment of the Skill India International Centre following an MoU?",
           ["Bhopal / भोपाल", "Indore / इंदौर", "Gwalior / ग्वालियर", "Ujjain / उज्जैन"], "A", "s"),
        _m("Where was the Bharat Renewable Energy Summit & Expo inaugurated?",
           ["Mumbai / मुंबई", "Delhi / दिल्ली", "Pune / पुणे", "Goa / गोवा"], "B", "r"),
        _m("Which summit was inaugurated by the Prime Minister in Delhi as per the news report?",
           ["Wind Meet / ए", "Bharat Renewable Energy Summit & Expo / बी", "Solar Forum / सी", "Climate Meet / डी"], "B", "r"),
    ]}
    out = pb.pick_mcqs([ed], {"s", "r"}, ["s", "r"], 10)
    assert [m["event_id"] for m in out] == ["s", "r"]


def test_hindi_recurring_weekday_and_union_minister():
    pub = date(2026, 11, 6)
    assert "हर शुक्रवार" in resolve_weekdays("स्टॉक रखने वाली इकाई को हर शुक्रवार को विवरण अपडेट करना होगा।", pub)
    assert "6 नवंबर को" in resolve_weekdays("केंद्र ने शुक्रवार को आदेश दिया।", pub)
    assert pb._hi_glossary("Union Home Minister Amit Shah said.", "संयुक्त गृह मंत्री अमित शाह ने कहा, ।") \
        == "केंद्रीय गृह मंत्री अमित शाह ने कहा।"
