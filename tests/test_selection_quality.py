# -*- coding: utf-8 -*-
"""Important main news must never be blocked (stages 04, 05, 07, 10).

Regression for the 2026-11-02 edition (run 41437192142): all 98 PIB releases
(collected through the site:pib.gov.in Google News query) were rejected by fact
verification, dedup merged "India factory growth slows" with "China factory
growth slows", and party sound-bites outranked the IAF chief, a Rs 53,866 crore
defence contract and GST collections.  The fixture is a subset of that run's raw
collection.
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
FIXTURE = ROOT / "tests" / "fixtures" / "raw_2026-11-02_subset.json"


def _agent(rel, name):
    spec = importlib.util.spec_from_file_location(name, str(ROOT / rel))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def raw():
    from pipeline.artifacts import news_items
    return news_items(json.loads(FIXTURE.read_text(encoding="utf-8")))


def _by(raw, needle):
    return next(a for a in raw if needle in a["title"])


# --------------------------------------------------------------------------- #
# 04 fact verification
# --------------------------------------------------------------------------- #
def test_pib_releases_from_google_news_are_official_and_verified(raw, monkeypatch):
    fact = _agent("agents/04_fact_verification.py", "t_sq_fact")
    monkeypatch.setenv("DRY_RUN", "0")
    monkeypatch.setattr(fact, "DISABLE_LLM", True)
    for needle in ("Corvettes", "AIR CHIEF MARSHAL", "Pune Metro", "GSLV-F18", "RoDTEP"):
        art = _by(raw, needle)
        assert art["source_name"] == "Google News Search"  # how the collector registered it
        out = fact.verify_article(art, raw)
        assert out["is_verified"], (needle, out["flags"], out["confidence_score"])
        assert out["official_domain"] == "pib.gov.in" and out["source_name"] == "PIB"
        assert out["source_level"] == 0 and out["official"] is True
        assert not out["title"].endswith("pib.gov.in")


def test_trusted_newsroom_top_story_from_google_news_is_verified(raw, monkeypatch):
    fact = _agent("agents/04_fact_verification.py", "t_sq_fact2")
    monkeypatch.setenv("DRY_RUN", "0")
    monkeypatch.setattr(fact, "DISABLE_LLM", True)
    out = fact.verify_article(_by(raw, "India evacuates thousands"), raw)
    assert out["is_verified"] and out["source_name"] == "Reuters"
    assert out["title"] == "India evacuates thousands ahead of second cyclone in a week"


def test_llm_cannot_sink_official_or_curated_news(raw, monkeypatch):
    """An LLM with an older cutoff calls new Acts 'implausible'; that must not drop them."""
    fact = _agent("agents/04_fact_verification.py", "t_sq_fact3")
    monkeypatch.setenv("DRY_RUN", "0")
    monkeypatch.setattr(fact, "DISABLE_LLM", False)
    monkeypatch.setattr(fact, "_llm_allowed", lambda: True)
    monkeypatch.setattr(fact, "llm_score", lambda a: (0.05, ["implausible_future_event"]))
    monkeypatch.setattr("pipeline.ai_router.is_configured", lambda: True)
    art = _by(raw, "grievance rules under VB-G")       # Business Standard, single source
    assert fact.verify_article(art, [art])["is_verified"]
    pib = _by(raw, "Corvettes")
    assert fact.verify_article(pib, [pib])["is_verified"]


def test_unknown_aggregator_items_still_need_provenance(monkeypatch):
    fact = _agent("agents/04_fact_verification.py", "t_sq_fact4")
    monkeypatch.setenv("DRY_RUN", "0")
    monkeypatch.setattr(fact, "DISABLE_LLM", True)
    art = {"title": "Celebrity spotted at airport - Some Gossip Blog", "summary": "x" * 40,
           "link": "https://news.google.com/articles/abc", "source_feed": "https://news.google.com/rss?hl=en-IN",
           "source_level": 5, "source_tier": 3, "category": "aggregator", "publisher_url": "https://news.google.com"}
    out = fact.verify_article(art, [art])
    assert not out.get("official_domain")
    assert out["source_name"] if "source_name" in out else True
    assert not out["is_verified"]


# --------------------------------------------------------------------------- #
# 05 dedup: same event only
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("a,b,distinct", [
    ("India factory growth slows in October, export orders jump, PMI shows",
     "China factory growth slows in October as export orders ease, private PMI shows", True),
    ("Visit of Foreign Secretary to Nepal", "Official visit of Foreign Secretary to UAE", True),
    ("Chengalpattu school holiday today, weather IMD alert: Severe cyclonic storm",
     "Chennai school holiday update, weather IMD alert: Severe cyclonic storm", True),
    ("RBI hikes repo rate by 25 bps", "RBI cuts repo rate by 25 bps", True),
    ("Captive, commercial coal production rises 42% to 22.03 MT in October - pib",
     "Captive, commercial coal production rises 42% to 22.03 MT in October", False),
    ("Ambuja Cements to invest $1.5 billion to lift capacity to 155 MTPA by FY30",
     "Ambuja Cements to invest $1.5 bn to lift capacity to 155 MTPA by FY30", False),
    ("US pushes to restore Russian gas sales to Europe via Ukraine, WSJ reports",
     "US pushes to restore Russian gas sales to Europe via Ukraine before winter", False),
    ("India's factory growth slows", "Indian factory growth slows, PMI", False),
])
def test_dedup_merges_only_same_event(a, b, distinct):
    dd = _agent("agents/05_deduplication.py", "t_sq_dedup")
    assert dd.distinct_event_check({"title": a}, {"title": b}) is distinct


def test_dedup_keeps_generic_titled_releases_apart_and_prefers_official():
    dd = _agent("agents/05_deduplication.py", "t_sq_dedup2")
    arts = [
        {"title": "Press Release", "summary": "Cabinet approves new fertiliser subsidy for rabi season", "link": "https://pib.gov.in/1"},
        {"title": "Press Release", "summary": "ISRO schedules GSLV-F18 launch from Sriharikota", "link": "https://pib.gov.in/2"},
    ]
    assert len(dd.dedup_fingerprint(arts)) == 2
    same = [
        {"title": "GST collections surge 23% to Rs 2.31 lakh crore in October", "link": "https://a.example/1",
         "confidence_score": 0.9, "source_level": 4, "source_feed": "a"},
        {"title": "GST collections surge 23% to Rs 2.31 lakh crore in October", "link": "https://pib.gov.in/x",
         "confidence_score": 0.6, "source_level": 0, "official": True, "source_feed": "pib"},
    ]
    out = dd.dedup_fingerprint(same)
    assert len(out) == 1 and out[0]["link"] == "https://pib.gov.in/x"


# --------------------------------------------------------------------------- #
# 10 non-news filter must not catch real news
# --------------------------------------------------------------------------- #
REAL_NEWS = [
    "Procurement of paddy begins in eastern UP; MSP Rs 2,441 per quintal",
    "MoD inks Rs 53,866 crore contracts for 8 Next Generation Corvettes",
    "Cabinet approves Rs 10,000 crore scheme for dairy cooperatives",
    "Air Chief Marshal Ashutosh Dixit assumes charge as 29th Chief of the Air Staff",
    "India, EU sign agreement on semiconductor supply chains",
    "Neeraj Chopra wins gold at Diamond League final",
    "Former PM Manmohan Singh passes away at 92",
    "RBI releases Financial Stability Report; gross NPAs at decade low",
    "Explained: what the new labour codes mean for gig workers",
    "Tender of excuses: Opposition walks out of Lok Sabha",
    "Govt extends RoDTEP scheme till 31 December 2026",
]
NON_NEWS = [
    "Bid opening meeting link for Procurement of IARI- Laboratory Equipment for PUSA Campus",
    "Corrigendum to tender notice for supply of furniture",
    "Today's NYT Strands Hints, Spangram and Answers for Monday, Nov. 2",
    "Shah Rukh Khan Turns 61: A Look At His Net Worth",
    "Movie review: a slow-burn thriller",
    "Agriculture, Rural & Environment - National Portal of India",
    "Live updates: Day 2 of the test match",
]


@pytest.mark.parametrize("headline", REAL_NEWS)
def test_non_news_filter_keeps_real_news(headline):
    from pipeline.news_filters import is_non_news
    assert not is_non_news(headline)


@pytest.mark.parametrize("headline", NON_NEWS)
def test_non_news_filter_drops_notices_and_fluff(headline):
    from pipeline.news_filters import is_non_news
    assert is_non_news(headline)


# --------------------------------------------------------------------------- #
# 07 relevance + 10 selection
# --------------------------------------------------------------------------- #
def _rel_items():
    return [
        {"event_id": "pol1", "headline_en": "Jagan accuses SEC of complicity in civic poll malpractices, says YSRCP will go to court",
         "raw_facts": "", "category": "National", "importance_score": 41, "source_name": "The Hindu"},
        {"event_id": "pol2", "headline_en": "‘Modi, Shah & Nadda have lost sleep over opposition rally’s success,’ says Congress MP",
         "raw_facts": "", "category": "National", "importance_score": 40, "source_name": "The Hindu"},
        {"event_id": "iaf", "headline_en": "Air Chief Marshal Ashutosh Dixit assumes charge as the 29th Chief of the Air Staff",
         "raw_facts": "", "category": "National", "importance_score": 20, "source_name": "PIB", "official_domain": "pib.gov.in"},
        {"event_id": "gst", "headline_en": "GST collections in the country surge by 23% to Rs 2.31 lakh crore in October",
         "raw_facts": "", "category": "Economy", "importance_score": 18, "source_name": "All India Radio News"},
        {"event_id": "pib_low", "headline_en": "GSLV-F18/NVS-03 Mission", "raw_facts": "", "category": "aggregator",
         "importance_score": 3, "source_name": "PIB", "official_domain": "pib.gov.in"},
    ]


def test_relevance_demotes_soundbites_promotes_hard_news_and_keeps_official(tmp_path, monkeypatch):
    rel = _agent("agents/07_student_domain_relevance.py", "t_sq_rel")
    from pipeline import state
    monkeypatch.setattr(state, "SCORED_DIR", tmp_path)
    monkeypatch.setenv("ALP_TARGET_NEWS_COUNT", "2")
    state.write_json_atomic(state.data_path(tmp_path, "daily_2026-11-02"), {"items": _rel_items()})
    rel.Agent("daily_2026-11-02", "daily", {}).run()
    kept = {i["event_id"]: i for i in state.read_json(state.data_path(tmp_path, "daily_2026-11-02"))["items"]}
    assert "pib_low" in kept and kept["pib_low"]["must_include"]          # official: never dropped
    assert kept["iaf"]["student_relevance"] > kept["pol1"]["student_relevance"]
    assert kept["gst"]["student_relevance"] > kept["pol2"]["student_relevance"]
    assert kept["pib_low"]["category"] != "aggregator"                     # category re-inferred


def test_selection_guarantees_official_stories_and_caps_running_topics(monkeypatch):
    sel = _agent("agents/10_final_news_selection.py", "t_sq_sel")
    monkeypatch.setenv("ALP_MIN_OFFICIAL_STORIES", "3")
    items = [{"event_id": f"n{i}", "headline_en": f"Cyclone Murasu: update number {i} on landfall", "category": "National",
              "student_relevance": 80 - i, "source_name": f"Paper{i}"} for i in range(6)]
    items += [{"event_id": f"o{i}", "headline_en": f"Cabinet approves scheme number {i} for farmers", "category": "Government Schemes",
               "student_relevance": 40 + i, "source_name": "PIB", "official_domain": "pib.gov.in"} for i in range(4)]
    items += [{"event_id": f"x{i}", "headline_en": f"Market report number {i} on exports", "category": "Economy",
               "student_relevance": 60 - i, "source_name": f"Desk{i}"} for i in range(6)]
    agent = sel.Agent("daily_x", "daily", {})
    picked = agent._ensure_official(agent._diverse_selection(sorted(items, key=lambda x: -x["student_relevance"]), 9),
                                    items, 9)
    ids = [p["event_id"] for p in picked]
    assert len(ids) == 9
    assert sum(1 for i in ids if i.startswith("o")) >= 3
    assert sum(1 for i in ids if i.startswith("n")) <= 2      # running story capped at 2


def test_two_word_official_title_is_a_valid_candidate():
    sel = _agent("agents/10_final_news_selection.py", "t_sq_sel2")
    assert sel._topic_key({"headline_en": "Cyclone Murasu: red alert"}) == "cyclone murasu"
    from pipeline.official_sources import is_must_include
    assert is_must_include({"source_name": "PIB"})
    assert is_must_include({"source_feed": "https://news.google.com/rss/search?q=site%3Apib.gov.in%20when%3A1d",
                            "title": "GSLV-F18/NVS-03 Mission - pib.gov.in"})
