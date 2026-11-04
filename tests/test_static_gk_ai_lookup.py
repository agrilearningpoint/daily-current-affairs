# -*- coding: utf-8 -*-
"""AI lookup for untracked officeholder posts (agents/static_gk_ai_lookup.py). All HTTP/LLM mocked."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from agents import static_gk_ai_lookup as lk
from agents import static_gk_validator as v

TODAY = date(2026, 11, 4)
OFFICIAL = "https://www.up.gov.in/en/page/chief-minister"
NEWS = "https://www.thehindu.com/news/national/up-cm-story.ece"
PAGE = ("Government of Uttar Pradesh. Hon'ble Chief Minister of Uttar Pradesh Shri Yogi Adityanath "
        "chaired a review meeting on agriculture. ") * 3


def _results(news_name="Yogi Adityanath", news_date="2 weeks ago"):
    return [
        {"title": "Chief Minister | Government of Uttar Pradesh", "link": OFFICIAL,
         "snippet": "Hon'ble Chief Minister Shri Yogi Adityanath"},
        {"title": "UP CM reviews kharif procurement", "link": NEWS, "date": news_date,
         "snippet": f"Chief Minister {news_name} on Monday reviewed ..."},
    ]


def _llm(name="Yogi Adityanath", conf="high"):
    return lambda prompt: json.dumps({"post": "Chief Minister of Uttar Pradesh", "name": name, "since": None,
                                      "source_url": OFFICIAL, "confidence": conf})


def _mk(tmp_path, *, search=None, fetch=None, llm=None, ready=None, **kw):
    calls = {"search": 0, "fetch": 0, "llm": 0}

    def _s(q):
        calls["search"] += 1
        return (search or (lambda q: _results()))(q)

    def _f(u):
        calls["fetch"] += 1
        return (fetch or (lambda u: PAGE))(u)

    def _l(p):
        calls["llm"] += 1
        return (llm or _llm())(p)

    look = lk.Lookup(search=_s, fetch=_f, llm=_l, ready=ready or (lambda: (True, "")),
                     cache_path=tmp_path / "ai_facts_cache.json", today=TODAY, **kw)
    return look, calls


def test_accepts_when_page_and_second_source_agree(tmp_path):
    look, calls = _mk(tmp_path)
    res = look("Chief Minister of Uttar Pradesh")
    assert res and res.name == "Yogi Adityanath" and res.source_url == OFFICIAL and res.second_source == NEWS
    assert calls["search"] == 2 and look.stats["accepted"] == 1
    cache = json.loads((tmp_path / "ai_facts_cache.json").read_text(encoding="utf-8"))
    rec = cache["records"]["chief minister of uttar pradesh"]
    assert rec["name"] == "Yogi Adityanath" and rec["verified_on"] == "2026-11-04" and rec["source_url"] == OFFICIAL
    # The validator then keeps a correct line and fixes a wrong one (Hindi Latin name replaced too).
    facts = v.load_facts()
    assert v.check_line("Chief Minister of Uttar Pradesh – Yogi Adityanath", "", facts, lookup=look).action == "keep"
    r = v.check_line("Chief Minister of Uttar Pradesh – Akhilesh Yadav", "उत्तर प्रदेश के मुख्यमंत्री – Akhilesh Yadav",
                     facts, lookup=look, year=2026)
    assert r.action == "replace" and r.en.endswith("Yogi Adityanath") and r.hi.endswith("Yogi Adityanath")
    r = v.check_line("Chief Minister of Uttar Pradesh – Akhilesh Yadav", "उत्तर प्रदेश के मुख्यमंत्री – अखिलेश यादव",
                     facts, lookup=look, year=2026)
    assert r.action == "replace" and r.hi == ""  # unverified Devanagari name never survives
    # A name glued into the post phrase cannot be told apart -> dropped, never kept unverified.
    assert v.check_line("Akhilesh Yadav Chief Minister of Uttar Pradesh", "", facts, lookup=look).action == "drop"
    assert calls["search"] == 2  # memoised: one lookup per post per run


def test_row_replacement_via_active_lookup(tmp_path):
    look, _ = _mk(tmp_path)
    content = {"items": [{"event_id": "e1", "headline_en": "UP launches scheme",
                          "static_gk": [{"label_en": "Chief Minister of Uttar Pradesh", "value_en": "Akhilesh Yadav",
                                         "label_hi": "उत्तर प्रदेश के मुख्यमंत्री", "value_hi": "अखिलेश यादव"}]}]}
    rep = v.validate_edition(content, None, lookup=look)
    row = content["items"][0]["static_gk"][0]
    assert row["value_en"] == "Yogi Adityanath" and row["value_hi"] == ""
    assert rep["replaced"] == 1 and rep["ai_lookup"]["accepted"] == 1 and rep["ai_lookup"]["verified_lines"] == 1
    assert v._ACTIVE_LOOKUP is None


def test_rejects_when_name_not_on_page(tmp_path):
    look, _ = _mk(tmp_path, fetch=lambda u: "Government of Uttar Pradesh. Chief Minister portal. " * 10)
    assert look("Chief Minister of Uttar Pradesh") is None
    assert not (tmp_path / "ai_facts_cache.json").exists()
    assert v.check_line("Chief Minister of Uttar Pradesh – Yogi Adityanath", "", v.load_facts(),
                        lookup=look).action == "drop"


def test_rejects_llm_name_from_memory_or_low_confidence(tmp_path):
    look, _ = _mk(tmp_path, llm=_llm(name="Someone Else"))
    assert look("Chief Minister of Uttar Pradesh") is None
    look, _ = _mk(tmp_path, llm=_llm(conf="medium"))
    assert look("Chief Minister of Uttar Pradesh") is None
    look, _ = _mk(tmp_path, llm=_llm(name="unknown"))
    assert look("Chief Minister of Uttar Pradesh") is None


def test_rejects_on_one_source_only(tmp_path):
    # Only the official result names him; the news hit names someone else.
    look, _ = _mk(tmp_path, search=lambda q: _results(news_name="Keshav Prasad Maurya"))
    assert look("Chief Minister of Uttar Pradesh") is None
    # Second source on the same site does not count as independent.
    same = [_results()[0], dict(_results()[1], link="https://cmup.up.gov.in/story")]
    look, _ = _mk(tmp_path, search=lambda q: same)
    assert look("Chief Minister of Uttar Pradesh") is None
    # A second source older than ~6 months does not count.
    look, _ = _mk(tmp_path, search=lambda q: _results(news_date="Jan 5, 2025"))
    assert look("Chief Minister of Uttar Pradesh") is None


def test_rejects_without_official_result(tmp_path):
    look, calls = _mk(tmp_path, search=lambda q: [_results()[1]])
    assert look("Chief Minister of Uttar Pradesh") is None and calls["fetch"] == 0


def test_budget_cap_respected(tmp_path):
    look, calls = _mk(tmp_path, search=lambda q: [])
    for i in range(12):
        assert look(f"Chairman of Board Number {i}") is None
    assert look.stats["lookups"] == 8 and calls["search"] == 16 and look.stats["serper_calls"] == 16
    assert look.stats["skipped"] == 4
    look, calls = _mk(tmp_path, search=lambda q: [], budget_s=0.0)
    assert look("Chairman of Coir Board") is None and calls["search"] == 0


def test_fail_open_on_exceptions_and_missing_key(tmp_path, monkeypatch):
    def boom(*_a):
        raise RuntimeError("429 Too Many Requests")
    for kw in ({"search": boom}, {"fetch": boom}, {"llm": boom}):
        look, _ = _mk(tmp_path, **kw)
        assert look("Chief Minister of Uttar Pradesh") is None
    look, _ = _mk(tmp_path, llm=lambda p: "not json at all")
    assert look("Chief Minister of Uttar Pradesh") is None
    # Missing key: the real readiness check turns the lookup off, no I/O at all.
    monkeypatch.setattr(lk, "ALLOW_IN_TESTS", True)
    monkeypatch.delenv("SERPER_API_KEY", raising=False)
    monkeypatch.delenv("ALP_DISABLE_NETWORK", raising=False)
    look, calls = _mk(tmp_path, ready=lk.default_ready)
    assert look("Chief Minister of Uttar Pradesh") is None
    assert calls["search"] == 0 and "SERPER" in look.stats["off_reason"]
    # Under pytest without opt-in it is always off.
    monkeypatch.setattr(lk, "ALLOW_IN_TESTS", False)
    monkeypatch.setenv("SERPER_API_KEY", "x" * 20)
    assert lk.default_ready()[0] is False
    # The validator still drops the line exactly as before.
    assert v.check_line("Chairman of Coir Board – Vipul Goyal", "", v.load_facts(), lookup=look).action == "drop"


def test_cache_hit_skips_lookup(tmp_path):
    (tmp_path / "ai_facts_cache.json").write_text(json.dumps({"version": 1, "records": {
        "chief minister of uttar pradesh": {"post": "Chief Minister of Uttar Pradesh", "name": "Yogi Adityanath",
                                            "source_url": OFFICIAL, "verified_on": "2026-11-01"}}}), encoding="utf-8")
    look, calls = _mk(tmp_path, ready=lambda: (False, "no key"))
    res = look("Chief Minister of Uttar Pradesh")
    assert res and res.from_cache and res.name == "Yogi Adityanath"
    assert calls == {"search": 0, "fetch": 0, "llm": 0} and look.stats["cache_hits"] == 1
    # Expired (> 7 days) entries are not used.
    (tmp_path / "ai_facts_cache.json").write_text(json.dumps({"version": 1, "records": {
        "chief minister of uttar pradesh": {"post": "x", "name": "Yogi Adityanath", "verified_on": "2026-10-20"}}}),
        encoding="utf-8")
    look, calls = _mk(tmp_path, ready=lambda: (False, "no key"))
    assert look("Chief Minister of Uttar Pradesh") is None and calls["search"] == 0


def test_extract_post_and_helpers():
    assert lk.extract_post("Defence Minister – Rajnath Singh", "Rajnath Singh") == "Defence Minister"
    assert lk.extract_post("Chief Minister of Uttar Pradesh – Yogi Adityanath", "Yogi Adityanath") == \
        "Chief Minister of Uttar Pradesh"
    assert lk.extract_post("Chairman – Vipul Goyal", "Vipul Goyal") == ""  # too vague to search
    assert lk.name_in_text("Dr. S. Jaishankar", "headed by Dr S Jaishankar, who")
    assert not lk.name_in_text("Amit Shah", "Amit Shahi visited")
    assert lk.is_official("https://pib.gov.in/x") and lk.is_official("https://mod.gov.in/")
    assert not lk.is_official("https://www.thehindu.com/x")
    assert lk.result_age_days("3 days ago", TODAY) == 3


def test_validate_edition_default_is_noop_under_pytest():
    content = {"items": [{"static_gk_pairs": [{"en": "Chairman of Coir Board – Vipul Goyal", "hi": ""}]}]}
    rep = v.validate_edition(content)
    assert content["items"][0]["static_gk_pairs"] == [] and rep["dropped"] == 1
    assert rep.get("ai_lookup", {}).get("lookups", 0) == 0


def test_seeded_union_ministers():
    facts = {f.id: f for f in v.load_facts()}
    assert facts["defence_minister"].name == "Rajnath Singh"
    assert facts["external_affairs_minister"].name == "S. Jaishankar"
    assert facts["home_minister"].name == "Amit Shah"
    F = list(facts.values())
    assert v.check_line("Defence Minister – Nirmala Sitharaman", "", F, year=2026).en.endswith("Rajnath Singh")
    assert v.check_line("External Affairs Minister: Dr. S. Jaishankar", "", F, year=2026).action == "keep"
    # A state home minister is not the Union Home Minister.
    assert v.check_line("Home Minister of Maharashtra – Devendra Fadnavis", "", F, year=2026).action == "drop"


def test_refresh_promotes_fresh_cache_entries():
    import importlib.util
    spec = importlib.util.spec_from_file_location("rcf", Path(__file__).resolve().parent.parent /
                                                  "scripts" / "refresh_current_facts.py")
    rcf = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rcf)
    doc = {"facts": [{"id": "x", "post": "Union Finance Minister", "name": "N", "match": ["Union Finance Minister"]}]}
    cache = {"records": {
        "a": {"post": "Chief Minister of Uttar Pradesh", "name": "Yogi Adityanath", "source_url": OFFICIAL,
              "verified_on": "2026-11-01"},
        "b": {"post": "Union Finance Minister", "name": "X Y", "source_url": OFFICIAL, "verified_on": "2026-11-01"},
        "c": {"post": "Chairman of Coir Board", "name": "Gone Name", "source_url": OFFICIAL, "verified_on": "2026-11-01"},
    }}
    added = rcf.promote_cache(doc, cache, fetch=lambda u: (200, f"<p>{PAGE}</p>"), today="2026-11-04")
    assert len(added) == 1 and doc["facts"][-1]["name"] == "Yogi Adityanath"
    assert doc["facts"][-1]["origin"] == "ai_facts_cache" and doc["facts"][-1]["match"]
