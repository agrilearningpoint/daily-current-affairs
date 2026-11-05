# -*- coding: utf-8 -*-
"""Freshness filter, same-event dedupe, opinion/tag cleanup, category rules (audit 2026-11-04)."""
import importlib.util
from pathlib import Path

import pytest

from pipeline import freshness as fr
from pipeline import news_filters as nf
from pipeline.auto_sections import build_sections, is_agri, quick_bite_category, two_line_text
from pipeline.collector import infer_category, refine_category

ROOT = Path(__file__).resolve().parent.parent
JD = "2026-11-04"


def _load_stage10():
    spec = importlib.util.spec_from_file_location("st10", str(ROOT / "agents" / "10_final_news_selection.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------- freshness
@pytest.mark.parametrize("item,why", [
    ({"headline_en": "Cabinet approves MSP for Kharif crops 2026-27", "published": "2026-05-13T10:00:00+05:30"},
     "published"),
    ({"headline_en": "Cabinet extends Jal Jeevan Mission", "date_source": "feed", "published": "2026-11-04T01:00:00Z",
      "link": "https://www.pib.gov.in/PressReleasePage.aspx?PRID=2237548"}, "PIB PRID"),
    ({"headline_en": "Old PIB release", "link": "https://pib.gov.in/PressReleasePage.aspx?PRID=1930000"}, "PIB PRID"),
    ({"headline_en": "Something happened", "link": "https://example.com/news/2026/05/13/story.html"}, "url date"),
    ({"headline_en": "Youth wing conference held", "summary": "The conference was held on December 14, 2025 in Vellore."},
     "event date"),
    ({"headline_en": "President to confer National Teachers Awards today"}, "annual day"),
    ({"headline_en": "Rajasthan Budget 2026-27: CM announces 1 lakh jobs"}, "Budget"),
])
def test_stale_items_detected(item, why):
    assert why in fr.stale_reason(item, JD)


@pytest.mark.parametrize("item", [
    {"headline_en": "RBI keeps repo rate unchanged", "published": "2026-11-03T08:00:00Z"},
    {"headline_en": "No date at all but real news about ISRO launch"},
    {"headline_en": "New PIB release", "link": "https://pib.gov.in/PressReleasePage.aspx?PRID=2321000"},
    {"headline_en": "Panel reviews Budget 2026-27 spending in mid-year review"},
    {"headline_en": "Scheme launched on 3 November 2026 for farmers", "published": "2026-11-03T08:00:00Z"},
])
def test_fresh_or_undatable_items_kept(item):
    assert fr.stale_reason(item, JD) == ""


def test_filter_fresh_can_be_disabled(monkeypatch):
    old = {"headline_en": "x", "published": "2023-06-01T00:00:00Z"}
    monkeypatch.setenv("ALP_FRESHNESS_FILTER", "0")
    assert fr.filter_fresh([old], JD) == ([old], [])
    monkeypatch.setenv("ALP_FRESHNESS_FILTER", "1")
    kept, dropped = fr.filter_fresh([old], JD)
    assert kept == [] and dropped[0][1].startswith("published")


# ---------------------------------------------------------------- opinion / tags
def test_opinion_detection():
    assert nf.is_opinion({"headline_en": "Coming of age: On the Binance hack. But Indian policymakers must"})
    assert nf.is_opinion({"headline_en": "On the Arunachal frontier, silence is not a strategy",
                          "link": "https://www.thehindu.com/opinion/lead/on-the-arunachal/article1.ece"})
    assert nf.is_opinion({"headline_en": "x", "link": "https://indianexpress.com/article/opinion/columns/foo/"})
    assert not nf.is_opinion({"headline_en": "Cabinet approves new metro line for Pune",
                              "link": "https://www.thehindu.com/news/national/foo/article2.ece"})


def test_tag_strip_and_truncation_repair():
    assert nf.strip_tags("Govt launches X scheme - PM India") == "Govt launches X scheme"
    assert nf.strip_tags("Cabinet approves Y (Key: DD News)") == "Cabinet approves Y"
    assert nf.repair_headline({"headline_en": "ICAR signs MoU with …The Division of Soil",
                               "title": "ICAR signs MoU with IISS: The Division of Soil Science gets new lab"}) \
        .startswith("ICAR signs MoU with IISS")
    assert nf.repair_headline({"headline_en": "ICAR signs MoU with ...The Division of Soil…"}) == ""
    assert nf.repair_headline({"headline_en": "Clean full headline here"}) == "Clean full headline here"


# ---------------------------------------------------------------- dedupe
def test_same_event_rare_entity():
    heads = ["Binance hack: $1.5 bn stolen in crypto heist", "Hackers drain Binance hot wallet in hack",
             "EC opens Form 6 enrolment drive for new voters", "Voters can file Form 6 online, EC says",
             "Kerala floods kill four", "Kerala budget session begins"]
    rare = nf.rare_entities(heads)
    assert nf.same_event_entity(heads[0], heads[1], rare)
    assert nf.same_event_entity(heads[2], heads[3], rare)
    assert not nf.same_event_entity(heads[4], heads[5], rare)
    assert not nf.same_event_entity(heads[0], heads[2], rare)


def test_stage10_drops_stale_opinion_and_duplicates(tmp_path, monkeypatch):
    mod = _load_stage10()
    monkeypatch.setenv("ALP_JOB_DATE", JD)
    agent = mod.Agent("daily_" + JD, "daily", {})
    items = [
        {"headline_en": "Binance hack: $1.5 bn stolen in crypto heist", "student_relevance": 80},
        {"headline_en": "Hackers drain Binance hot wallet in hack", "student_relevance": 70},
        {"headline_en": "Cabinet approves MSP for Kharif crops", "published": "2026-05-13T10:00:00Z",
         "student_relevance": 90},
        {"headline_en": "Coming of age: On the Binance hack. But policymakers", "student_relevance": 60},
        {"headline_en": "RBI keeps repo rate unchanged at 5.5 per cent - PM India", "student_relevance": 50},
    ]
    out = agent._clean_candidates(items)
    out = agent._drop_stale(out)
    out.sort(key=lambda x: x["student_relevance"], reverse=True)
    out = agent._dedupe_same_event(out)
    heads = [x["headline_en"] for x in out]
    assert heads == ["Binance hack: $1.5 bn stolen in crypto heist", "RBI keeps repo rate unchanged at 5.5 per cent"]
    assert agent.context["stale_dropped"] == 1 and agent.context["opinion_dropped"] == 1


# ---------------------------------------------------------------- auto sections
def test_agri_corner_rejects_political_and_coop_bank():
    assert not is_agri({"headline_en": "DVAC conducts drone survey of irrigation tank in illegal sand mining "
                                       "charge against DMK's E.V. Velu"})
    assert not is_agri({"headline_en": "RBI's Bank in a Box for urban co-operative banks"})
    assert is_agri({"headline_en": "Cabinet approves MSP hike for rabi crops"})
    assert is_agri({"headline_en": "Centre releases funds for micro irrigation in 5 states"})


def test_two_line_text_skips_spliced_sentence():
    it = {"headline_en": "DVAC conducts drone survey of irrigation tank in Tiruvannamalai",
          "summary": "Velu for the party's Northern Zone Youth Wing Conference held on December 14, 2025."}
    assert "Velu" not in two_line_text(it)


def test_build_sections_freshness_and_dedupe():
    cands = [
        {"event_id": "a", "headline_en": "Binance hack: $1.5 bn stolen in crypto heist", "student_relevance": 80},
        {"event_id": "b", "headline_en": "Hackers drain Binance hot wallet in massive hack", "student_relevance": 70},
        {"event_id": "c", "headline_en": "Rajasthan Budget 2026-27 announces one lakh jobs", "student_relevance": 70},
        {"event_id": "d", "headline_en": "EC opens Form 6 enrolment drive for new voters", "student_relevance": 60},
        {"event_id": "e", "headline_en": "Voters can file Form 6 online for enrolment, EC says", "student_relevance": 55},
        {"event_id": "f", "headline_en": "In Tehran, a search for the future of West Asian security",
         "link": "https://www.thehindu.com/opinion/lead/in-tehran/article3.ece", "student_relevance": 90},
    ]
    content = {"items": []}
    stats = build_sections(content, cands, translate=lambda lines, dl: {l: "हिंदी पंक्ति " + l for l in lines},
                           job_date=JD)
    assert stats["stale_dropped"] == 1
    ids = [b["event_id"] for b in content.get("quick_bites", [])]
    assert "c" not in ids and "f" not in ids and "b" not in ids and "e" not in ids


def test_quick_bite_summit_is_not_international():
    assert quick_bite_category({"headline_en": "PM addresses RE-Invest summit in Gandhinagar on solar push"}) \
        != "International"


# ---------------------------------------------------------------- categories
def test_category_rules():
    assert infer_category("ZSI holds Taxonomy Summit on new species in Kolkata") == "Environment"
    assert refine_category("International", "PM addresses Renewable Energy Investors Summit in New Delhi") \
        != "International"
    assert refine_category("Banking & Finance", "Supreme Court on 'protest economy' in plea over bandhs") \
        not in ("Banking & Finance", "Economy")
    assert refine_category("International", "EAM meets US counterpart in Washington") == "International"
    assert infer_category("Report on school dropouts released") != "Banking & Finance"  # 'repo' != 'report'
    assert infer_category("BARC and MIDHANI sign MoU for nuclear alloys") == "Science & Technology"
    assert refine_category("Agriculture", "Cabinet approves MSP for Kharif crops") == "Agriculture"
