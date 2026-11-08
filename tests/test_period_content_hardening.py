"""Weekly/monthly content hardening, built on the real defects of weekly_2026-11-08
(2-8 Nov 2026): headline-only PIB stories, the Tamil Nadu GST event printed twice,
state politics / a US-stocks listicle / a BRICS opinion piece on the cover, stale
events, wrong sections, a wrong BRICS Static GK box and junk Agri-corner lines.

All inputs are mocked daily-edition records (no network): the fetcher is injected.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import exam_relevance as xr  # noqa: E402
from pipeline import freshness as fr  # noqa: E402
from pipeline import period_builder as pb  # noqa: E402

WEEK = ["2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06", "2026-11-07", "2026-11-08"]


def _fake_tr(en: str) -> str:
    """Offline translator stand-in (Devanagari only, every number kept): these tests
    exercise selection, not Hindi, and a live period edition fails without Hindi."""
    import re as _re
    nums = " ".join(_re.findall(r"\d+(?:[.,]\d+)*", en.replace(",", "")))
    return _re.sub(r"\s+", " ", f"यह वाक्य {nums} का हिंदी अनुवाद है।")


@pytest.fixture(autouse=True)
def _offline_translator(monkeypatch):
    monkeypatch.setattr(pb, "_period_translators", lambda: (None, _fake_tr))


@pytest.fixture(autouse=True)
def _live(monkeypatch):
    monkeypatch.delenv("DRY_RUN", raising=False)
    monkeypatch.setenv("ALP_PERIOD_FETCH", "1")


def _module(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _it(eid, head, text="", day="2026-11-04", cat="National", score=60, **kw):
    it = {"event_id": eid, "category": cat, "importance_score": score,
          "headline_en": head, "headline_hi": "परीक्षण शीर्षक " + eid,
          "summary_en": text.split(". ")[0] if text else head, "summary_hi": "",
          "detailed_explanation_en": text, "key_points_en": [], "key_points_hi": [],
          "exam_fact_en": "", "exam_fact_hi": "", "static_gk_pairs": [], "static_facts": {},
          "needs_review": False, "verification_passed": True,
          "source": {"name": "PIB", "url": ""}}
    it.update(kw)
    return it


def _ed(day, items, one_liners=(), agri=(), agri_gk=(), reserve=()):
    return {"date": day, "mcqs": [], "content": {
        "items": list(items), "reserve_items": list(reserve), "one_liners": list(one_liners),
        "agri_corner": {"items": list(agri), "static_gk": list(agri_gk)}}}


def _filler_stories(day, n, start=0):
    topics = ["drip irrigation", "seed testing", "cold storage", "soil testing", "honey processing",
              "fish feed", "dairy cooling", "millet milling", "rice drying", "cotton ginning"]
    out = []
    for k in range(start, start + n):
        t = topics[k % len(topics)]
        out.append(_it(f"f{day}{k}", f"State unit {k} expands {t} facilities in district {k}",
                       f"The state unit number {k} opened new {t} facilities in district {k} this week. "
                       f"Officials said {k * 10 + 7} people would use the {t} centre every month.",
                       day=day, score=40))
    return out


# --------------------------------------------------------------------------- #
# 1. Never a headline-only story
# --------------------------------------------------------------------------- #
MAIZE = ("1st International Maize Conference 2026 Calls for Higher Productivity and Value Addition")
MAIZE_PAGE = ("The 1st International Maize Conference 2026 began on 2 November at the JD Convention Centre in "
              "Hyderabad. Director General of ICAR Dr. M.L. Jat said maize productivity must rise to meet "
              "feed and ethanol demand. The conference brings together scientists, industry and farmers.")


def test_title_only_story_rebuilt_from_daily_fields_or_source_or_dropped():
    # Weekly #22-style item: headline only, but the daily kept whole key points.
    kcc = _it("kcc", "Kisan Credit Card scheme crosses 7.75 crore operative accounts", day="2026-11-06",
              cat="Agriculture", score=80,
              key_points_en=["Operative Kisan Credit Card accounts crossed 7.75 crore with ₹10.05 lakh crore "
                             "outstanding credit as of September 2026"])
    # Weekly #21: headline only, nothing in the daily; the PIB page has the facts.
    maize = _it("maize", MAIZE, day="2026-11-03", cat="Agriculture", score=85,
                source={"name": "PIB", "url": "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2331603"})
    # Weekly #24-style: headline only, no usable data, the source gives nothing either.
    senegal = _it("sen", "Shri Inbasekar Sundaramurthi appointed as the next Ambassador to Senegal",
                  day="2026-11-03", cat="Appointments", score=90,
                  source={"name": "MEA", "url": "https://www.mea.gov.in/press-releases.htm?dtl/1"})
    backup = _it("app2", "Shri A.K. Rao takes charge as Director General of Civil Aviation",
                 "Shri A.K. Rao took charge as Director General of Civil Aviation on Wednesday. "
                 "He succeeds an officer who retired after a three-year term.",
                 day="2026-11-04", cat="Appointments", score=50)
    calls = []

    def fetcher(url):
        calls.append(url)
        return MAIZE_PAGE if "2331603" in url else ""

    eds = [_ed(d, ([kcc, maize, senegal, backup] if d == "2026-11-04" else []) + _filler_stories(d, 4))
           for d in WEEK]
    r = pb.build_period("weekly", "2026-11-08", eds, WEEK, fetcher=fetcher)
    items = {x["event_id"]: x for x in r["content"]["items"]}
    assert all(pb.has_body(x) for x in r["content"]["items"])           # never a headline-only story
    assert items["kcc"]["body_source"] == "daily_fields"
    assert "7.75 crore" in items["kcc"]["summary_pairs"][0]["en"]
    assert items["maize"]["body_source"] == "source_fetch"
    assert any("M.L. Jat" in p["en"] for p in items["maize"]["summary_pairs"])
    assert "sen" not in items and "app2" in items                       # dropped; next-ranked promoted
    assert r["stats"]["title_only_dropped"] >= 1
    assert any("Senegal" in h for h in r["stats"]["title_only_log"])
    assert len(calls) <= 15


def test_fetch_is_offline_in_dry_run(monkeypatch):
    monkeypatch.setenv("DRY_RUN", "1")
    assert pb.fetch_source_text("https://www.pib.gov.in/PressReleasePage.aspx?PRID=2331603") == ""


def test_qa_fails_period_and_warns_daily_on_title_only_story():
    qa = _module("agents/19_pdf_qa.py", "alp_qa19_hardening")
    good = {"headline_en": "RBI proposes ₹100 crore limit", "summary_pairs": [{"en": "The RBI proposed a limit.", "hi": ""}]}
    empty = {"headline_en": "NCSC Intervention Results in Mandatory Reporting", "summary_pairs": []}
    rep = qa.QAReport(pdf_path="x.pdf")
    qa.check_story_bodies(rep, [good, empty], "weekly")
    assert [i.severity for i in rep.issues if i.code == "title_only_stories"] == ["error"] and not rep.passed
    daily_empty = {"headline_en": "Corvette contracts signed", "summary_en": "Corvette contracts signed",
                   "key_points_en": []}
    rep = qa.QAReport(pdf_path="x.pdf")
    qa.check_story_bodies(rep, [daily_empty], "daily")
    assert [i.severity for i in rep.issues if i.code == "title_only_stories"] == ["warning"]
    rep = qa.QAReport(pdf_path="x.pdf")
    qa.check_story_bodies(rep, [good], "weekly")
    assert not rep.issues


# --------------------------------------------------------------------------- #
# 2. Same event from two angles
# --------------------------------------------------------------------------- #
def test_tamil_nadu_gst_stories_are_one_event():
    stalin = _it("st", "Citing GST revenue decline, Stalin says Tamil Nadu is ‘doomed’ under TVK government",
                 "In a social media post, he said the State’s growth rate in Goods and Services Tax (GST) revenue "
                 "had fallen below the national average.", day="2026-11-02")
    eps = _it("eps", "Palaniswami expresses concern over lower growth rate in Tamil Nadu’s GST revenue",
              "The AIADMK general secretary Edappadi K. Palaniswami on Monday expressed concern over the lower "
              "GST growth.", day="2026-11-02")
    national = _it("gst", "GST collections rise 23% to ₹2.31 lakh crore in October",
                   "Gross GST collections rose 23 per cent in October.", day="2026-11-01")
    rbi1 = _it("r1", "RBI starts 3 surveys to capture inflation expectations, consumer confidence", "x.")
    rbi2 = _it("r2", "RBI proposes ₹100 crore limit on bank loans for agri infrastructure", "y.", day="2026-11-06")
    assert pb.same_event(stalin, eps)
    assert not pb.same_event(stalin, national) and not pb.same_event(rbi1, rbi2)
    kept = pb.dedupe([dict(stalin, edition_date="2026-11-02"), dict(eps, edition_date="2026-11-02")])
    assert len(kept) == 1


# --------------------------------------------------------------------------- #
# 3. Relevance for agri / banking exams
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("head,why", [
    ("Citing GST revenue decline, Stalin says Tamil Nadu is ‘doomed’ under TVK government", "state party politics"),
    ("Palaniswami expresses concern over lower growth rate in Tamil Nadu", "state party politics"),
    ("DVAC conducts drone survey of irrigation tank in illegal sand mining charge against DMK’s E.V. Velu",
     "state party politics"),
    ("Pawan attributes ZPTC, MPTC poll victories to welfare, development", "state party politics"),
    ("Investing in US stocks from India: Check how these 5 platforms stack up", "market listicle"),
    ("What the BRICS carbon market partnership needs", "opinion piece"),
    ("Russian strikes hit energy facility in Zaporizhzhia", "foreign conflict without India angle"),
    ("Pakistan receives first spot LNG cargo of winter", "foreign conflict without India angle"),
])
def test_not_exam_news(head, why):
    assert xr.drop_reason({"headline_en": head}) == why


@pytest.mark.parametrize("head", [
    "Cabinet approves VISTAR scheme with an outlay of ₹4,371.10 crore",
    MAIZE,
    "RBI proposes ₹100 crore limit on bank loans for agri infrastructure",
    "Khet Bachaao Abhiyaan - Rabi 2026 launched across 700 districts",
    "Government doubles OMSS rice sale target to 50 LMT for 2026-27",
])
def test_exam_core_is_boosted(head):
    it = {"headline_en": head, "importance_score": 50}
    assert xr.is_boosted(it) and xr.boost(it) >= 15 and not xr.drop_reason(it)


def test_cover_only_from_boosted_set_and_politics_dropped():
    days = WEEK
    eds = []
    for d in days:
        items = _filler_stories(d, 3)
        if d == "2026-11-02":
            items += [_it("st", "Citing GST revenue decline, Stalin says Tamil Nadu is ‘doomed’ under TVK government",
                          "Stalin said the State's GST growth fell below the national average on Monday.",
                          day=d, cat="Economy", score=99),
                      _it("us", "Investing in US stocks from India: Check how these 5 platforms stack up",
                          "More Indian investors are buying US stocks through apps and brokers today.",
                          day=d, cat="Economy", score=98)]
        if d == "2026-11-04":
            items += [_it("cab", "Cabinet approves VISTAR scheme with an outlay of ₹4,371.10 crore",
                          "The Union Cabinet on Tuesday approved the VISTAR scheme with an outlay of ₹4,371.10 crore. "
                          "The scheme will run till 2030-31.", day=d, cat="National", score=60)]
        eds.append(_ed(d, items))
    r = pb.build_period("weekly", "2026-11-08", eds, days, fetcher=lambda u: "")
    heads = [x["headline_en"] for x in r["content"]["items"]]
    assert not any("Stalin" in h or "US stocks" in h for h in heads)
    assert r["stats"]["irrelevant_dropped"] == 2
    cover = sorted((x for x in r["content"]["items"] if x["cover_rank"]), key=lambda x: x["cover_rank"])
    assert cover and cover[0]["event_id"] == "cab"
    assert all(x["exam_boosted"] for x in cover)


# --------------------------------------------------------------------------- #
# 4. Stale news / event dates
# --------------------------------------------------------------------------- #
def test_brics_summit_opinion_and_2025_party_event_are_stale_for_the_week():
    brics = {"headline_en": "BRICS carbon market partnership: next steps",
             "summary_en": "On September 12, at the 18th BRICS Summit in New Delhi, the New Delhi Declaration "
                           "confirmed the partnership.", "edition_date": "2026-11-05"}
    assert "2026-09-12" in fr.period_stale_reason(brics, "2026-11-02", "2026-11-08")
    velu = {"en": "Velu for the party’s Northern Zone Youth Wing Conference held on December 14, 2025.",
            "edition_date": "2026-11-05"}
    assert fr.period_stale_reason(velu, "2026-11-02", "2026-11-08")
    ongoing = {"headline_en": "Khet Bachaao Abhiyaan runs from 22 October to 30 November",
               "edition_date": "2026-11-03"}
    assert fr.period_stale_reason(ongoing, "2026-11-02", "2026-11-08") == ""


def test_event_date_prefers_weekday_over_publish_date():
    it = {"headline_en": "Barclays to invest ₹1,500 crore in India",
          "summary_en": "Barclays on Thursday said it will invest ₹1,500 crore in its India businesses.",
          "edition_date": "2026-11-06"}
    assert fr.event_date(it).isoformat() == "2026-11-05"
    it = {"headline_en": "Stalin", "summary_en": "M.K. Stalin on Monday (November 2, 2026) said ...",
          "edition_date": "2026-11-03"}
    assert fr.event_date(it).isoformat() == "2026-11-02"
    story = pb._story(_it("b", "Barclays to invest ₹1,500 crore in India, boost banking businesses",
                          "Barclays on Thursday said it will invest ₹1,500 crore in India."), "2026-11-06")
    pb._set_event_day(story, "2026-11-02", "2026-11-08")
    assert story["edition_date"] == "2026-11-05" and story["published_edition_date"] == "2026-11-06"


def test_blocklist_catches_nhrc_darbhanga_one_liner():
    pats = pb._blocklist()
    line = ("NHRC, India takes suo motu cognizance of the reported dilapidated Government Primary School roof "
            "supported on benches after the collapse of the main pillar holding it in Darbhanga, Bihar")
    assert any(p.search(line) for p in pats)


# --------------------------------------------------------------------------- #
# 5. Sections
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("head,cat,want", [
    ("India-US trade deal: What midterm elections mean for trade policy, tariffs", "Agriculture", "International"),
    ("NCSC Intervention Results in Mandatory Reporting of SC Beneficiaries", "Agriculture", "National"),
    ("RBI proposes ₹100 crore limit on bank loans for agri infrastructure", "Economy", "Agriculture"),
    ("Barclays to invest ₹1,500 crore in India, boost banking businesses", "International", "Economy"),
    (MAIZE, "Agriculture", "Agriculture"),
    ("Soreng, Sikkim: India’s first notified Organic Fisheries Cluster under PMMSY", "Agriculture", "Agriculture"),
])
def test_sections(head, cat, want):
    assert pb.section_for({"headline_en": head, "category": cat}) == want


def test_daily_category_agriculture_needs_real_agri_terms():
    from pipeline.collector import refine_category
    assert refine_category("Agriculture", "India-US trade deal: what the US midterms mean for trade policy "
                                          "and tariffs on exports") != "Agriculture"
    assert refine_category("Agriculture", "Farmers get MSP for paddy procurement in Punjab") == "Agriculture"


# --------------------------------------------------------------------------- #
# 6. Static GK
# --------------------------------------------------------------------------- #
def test_brics_static_gk_corrected_and_ndb_hq_shanghai():
    v = _module("agents/static_gk_validator.py", "alp_sgv_hardening")
    orgs = v.load_orgs()
    act, fld, val, _hi = v.check_org_line("Member countries", "Brazil, Russia, India, China, South Africa", orgs)
    assert (act, fld) == ("replace", "members")
    assert val.split(", ") == ["Brazil", "Russia", "India", "China", "South Africa", "Egypt", "Ethiopia", "Iran",
                               "United Arab Emirates", "Indonesia"]
    assert v.check_org_line("BRICS Secretariat location", "Shanghai, China", orgs)[0] == "drop"
    assert v.check_org_line("BRICS Headquarters", "Shanghai", orgs)[0] == "drop"
    assert v.check_org_line("NDB Headquarters", "Shanghai", orgs)[0] == "keep"
    assert v.check_org_line("NDB Headquarters", "Beijing", orgs)[:3] == ("replace", "hq", "Shanghai")
    assert v.check_org_line("SCO Secretariat", "Beijing", orgs)[0] == "keep"
    assert v.check_org_line("G20 Secretariat", "New Delhi", orgs)[0] == "drop"
    assert v.check_org_line("ASEAN founded", "1967", orgs)[0] == "keep"
    assert v.check_org_line("BRICS summit frequency", "Annual", orgs)[0] == "keep"
    verdict = v.check_line("Member countries – Brazil, Russia, India, China, South Africa",
                           "सदस्य देश – ब्राज़ील, रूस, भारत, चीन, दक्षिण अफ्रीका", [], orgs=orgs)
    assert verdict.action == "replace" and "Indonesia" in verdict.en and "इंडोनेशिया" in verdict.hi


def test_rbi_box_printed_once_per_edition():
    seen, seen_orgs = [], set()
    s12 = {"headline_en": "RBI tightens rules", "event_id": "a",
           "summary_en": "The Reserve Bank of India in Mumbai issued new rules.",
           "static_gk_pairs": [{"en": "Headquarters of Reserve Bank of India – Mumbai", "hi": ""},
                               {"en": "Establishment Year of Reserve Bank of India – 1935", "hi": ""}]}
    s13 = {"headline_en": "RBI starts 3 surveys to capture inflation expectations", "event_id": "b",
           "summary_en": "The RBI launched the IESH round.",
           "static_gk_pairs": [{"en": "RBI Headquarters – Mumbai, Maharashtra", "hi": ""},
                               {"en": "IESH Coverage – 19 cities", "hi": ""}]}
    s14 = {"headline_en": "RBI proposes ₹100 crore limit on bank loans for agri infrastructure", "event_id": "c",
           "static_gk_pairs": [{"en": "Established – 1935", "hi": ""},
                               {"en": "Founding Act – Reserve Bank of India Act, 1934", "hi": ""}]}
    for s in (s12, s13, s14):
        pb._attach_static_gk(s, {}, seen, set(), seen_orgs)
    assert len(s12["static_gk_pairs"]) == 2
    assert [p["en"] for p in s13["static_gk_pairs"]] == ["IESH Coverage – 19 cities"]
    assert s14["static_gk_pairs"] == []


def test_agri_corner_gk_skips_orgs_boxed_under_stories():
    eds = [_ed("2026-11-03", [], agri_gk=[{"en": "PMMSY launched in 2020", "hi": "पीएमएमएसवाई 2020 में शुरू"},
                                          {"en": "ICAR established on 16 July 1929", "hi": "आईसीएआर 16 जुलाई 1929"}])]
    ac = pb.pick_agri_corner(eds, 10, 6, ("2026-11-02", "2026-11-08"), seen_orgs={"pmmsy"})
    assert [g["en"] for g in ac["static_gk"]] == ["ICAR established on 16 July 1929"]


# --------------------------------------------------------------------------- #
# 7. Agri Corner and one-liners
# --------------------------------------------------------------------------- #
def test_agri_corner_rejects_non_agri_garbled_and_political_lines():
    day = "2026-11-05"
    good = {"en": "Namakkal farmers adopt drone spraying of nano urea on 2,000 acres of maize.",
            "hi": "नामक्कल के किसानों ने 2,000 एकड़ मक्का पर नैनो यूरिया का ड्रोन छिड़काव अपनाया।", "event_id": "g"}
    bad = [{"en": "70-km inter-corridor highway project sanctioned for the National Highway network.",
            "hi": "राष्ट्रीय राजमार्ग नेटवर्क के लिए 70 किमी परियोजना स्वीकृत।"},
           {"en": "Senior officials of the Ministry of Rural Development visited Manipur to monitor schemes.",
            "hi": "ग्रामीण विकास मंत्रालय के अधिकारियों ने मणिपुर का दौरा किया।"},
           {"en": "DVAC conducts drone survey of irrigation tank in illegal sand mining charge against DMK’s "
                  "E.V. Velu. Velu for the party’s Northern Zone Youth Wing Conference held on December 14, 2025.",
            "hi": "डीवीएसी ने वेलु के खिलाफ ड्रोन सर्वेक्षण किया।"},
           {"en": "Khet Bachaao Abhiyaan - Rabi 2026.", "hi": "खेत बचाओ अभियान - रबी 2026।"}]
    ac = pb.pick_agri_corner([_ed(day, [], agri=[good] + bad)], 10, 6, ("2026-11-02", "2026-11-08"))
    assert [x["en"] for x in ac["items"]] == [good["en"]]


def test_one_liners_reject_headings_raw_titles_and_off_syllabus():
    day = "2026-11-04"
    st = _it("ev", "Cabinet approves VISTAR scheme with an outlay of ₹4,371.10 crore",
             "The Union Cabinet approved the VISTAR scheme with an outlay of ₹4,371.10 crore.", day=day)
    verified = {"ev": pb._story(st, day)}
    lines = ["Academic Bank of Credits and APAAR",
             "PM's address at the inauguration of Bharat Renewable Energy Summit & Expo 2026",
             "Pakistan receives first spot LNG cargo of winter from Qatar",
             "Russian strikes hit energy facility in Zaporizhzhia region overnight",
             "Cabinet approves VISTAR scheme with an outlay of ₹4,371.10 crore for 2026-31"]
    eds = [_ed(day, [st], one_liners=[{"text_en": t, "text_hi": "हिंदी पंक्ति " + str(i), "event_id": "ev"}
                                      for i, t in enumerate(lines)])]
    out = pb.pick_one_liners(eds, verified, [], 40, ("2026-11-02", "2026-11-08"))
    assert [o["text_en"] for o in out] == [lines[-1]]


def test_garbled_detection():
    assert pb.garbled("DVAC acts against DMK’s E.V. Velu. Velu for the party’s Northern Zone conference.")
    assert pb.garbled("\"This investment reflects our confidence in the opportunity.")
    assert pb.garbled("Andhra Pradesh Deputy CM K. Photo Jana Sena Party president said the results were good.")
    assert not pb.garbled("APEDA facilitated export of 1.5 MT of kiwi from Arunachal Pradesh to Dubai.")


# --------------------------------------------------------------------------- #
# 8. Coverage: big-ticket PIB items in the dailies' reserves
# --------------------------------------------------------------------------- #
def test_reserve_big_ticket_items_become_stories():
    khet = _it("khet", "Khet Bachaao Abhiyaan - Rabi 2026 launched in 34 States and UTs",
               "The Khet Bachaao Abhiyaan for Rabi 2026 runs from 22 October to 30 November 2026. "
               "It aims to reach about 50 lakh farmers in more than 700 districts.",
               day="2026-11-02", cat="Agriculture", score=45)
    omss = _it("omss", "Government doubles OMSS rice sale target to 50 LMT for 2026-27",
               "The Centre doubled the Open Market Sale Scheme rice target to 50 LMT for 2026-27 on Friday. "
               "The move aims to cool cereal prices.", day="2026-11-06", cat="Economy", score=40)
    eds = []
    for d in WEEK:
        eds.append(_ed(d, _filler_stories(d, 5),
                       reserve=[khet] if d == "2026-11-02" else ([omss] if d == "2026-11-06" else []),
                       one_liners=[{"text_en": "OMSS rice sale target doubled to 50 LMT for 2026-27",
                                    "text_hi": "ओएमएसएस चावल बिक्री लक्ष्य दोगुना", "event_id": "omss"}]
                       if d == "2026-11-06" else []))
    r = pb.build_period("weekly", "2026-11-08", eds, WEEK, fetcher=lambda u: "")
    ids = {x["event_id"] for x in r["content"]["items"]}
    assert {"khet", "omss"} <= ids
    assert r["stats"]["reserve_candidates"] == 2
    secs = {x["event_id"]: x["section"] for x in r["content"]["items"]}
    assert secs["khet"] == "Agriculture"
