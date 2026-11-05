"""Static GK freshness: appointment trigger + verified override cache (all lookups mocked)."""
from __future__ import annotations

import json
from datetime import date

import pytest

from agents import static_gk_validator as v
from agents.static_gk_ai_lookup import AIFact

NEW = "Arjun Mehta"  # fictional new governor


@pytest.fixture
def cache(tmp_path, monkeypatch):
    p = tmp_path / "ai_facts_cache.json"
    monkeypatch.setenv("ALP_AI_FACTS_CACHE", str(p))
    monkeypatch.setenv("ALP_JOB_DATE", "2026-11-05")
    return p


class FakeLookup:
    def __init__(self, name):
        self.name, self.calls = name, []

    def __call__(self, post, expect=None, fresh=False):
        self.calls.append((post, expect, fresh))
        if not self.name:
            return None
        return AIFact(post=post, name=self.name, since="2026-11-04", source_url="https://rbi.org.in/x",
                      second_source="https://pib.gov.in/y", verified_on="2026-11-05")


def _edition(headline):
    return {"items": [{"event_id": "e1", "headline_en": headline,
                       "static_gk_pairs": [["RBI Governor: Sanjay Malhotra", "आरबीआई गवर्नर: संजय मल्होत्रा"],
                                           ["RBI HQ: Mumbai", "आरबीआई मुख्यालय: मुंबई"]]}]}


STORY = f"{NEW} appointed as RBI Governor for a three-year term."


def test_confirmed_appointment_uses_new_name_and_writes_override(cache):
    lk = FakeLookup(NEW)
    content = _edition(STORY)
    rep = v.validate_edition(content, None, v.load_facts(), lookup=lk, cache_doc={"records": {}})
    pairs = content["items"][0]["static_gk_pairs"]
    assert pairs[0] == [f"RBI Governor: {NEW}", ""]
    assert pairs[1][0] == "RBI HQ: Mumbai"
    assert lk.calls and lk.calls[0][2] is True and NEW in lk.calls[0][1]
    assert rep["appointments"][0]["outcome"] == "confirmed"
    rec = json.loads(cache.read_text())["records"]["override:rbi_governor"]
    assert rec["name"] == NEW and rec["previous_name"] == "Sanjay Malhotra"
    assert rec["overrides_current_facts"] is True and rec["verified_on"] == "2026-11-05"


def test_unconfirmed_appointment_drops_post_lines(cache):
    content = _edition(STORY)
    rep = v.validate_edition(content, None, v.load_facts(), lookup=FakeLookup(None), cache_doc={"records": {}})
    pairs = content["items"][0]["static_gk_pairs"]
    assert [p[0] for p in pairs] == ["RBI HQ: Mumbai"]
    assert rep["appointments"][0]["outcome"] == "blocked"
    assert not cache.exists()


def test_override_cache_wins_on_later_day(cache):
    doc = {"records": {"override:rbi_governor": {
        "fact_id": "rbi_governor", "name": NEW, "previous_name": "Sanjay Malhotra",
        "verified_on": "2026-11-05", "overrides_current_facts": True}}}
    facts = v.apply_overrides(v.load_facts(), doc, today=date(2026, 11, 20))
    gov = next(f for f in facts if f.id == "rbi_governor")
    assert gov.override and gov.name == NEW
    r = v.check_line("RBI Governor – Sanjay Malhotra", "", facts, year=2026)
    assert r.action == "replace" and r.en == f"RBI Governor – {NEW}"
    # expired after OVERRIDE_DAYS
    old = v.apply_overrides(v.load_facts(), doc, today=date(2026, 12, 31))
    assert next(f for f in old if f.id == "rbi_governor").name == "Sanjay Malhotra"


def test_no_appointment_signal_is_unchanged(cache):
    lk = FakeLookup(NEW)
    content = _edition("RBI keeps repo rate unchanged at 5.5%")
    rep = v.validate_edition(content, None, v.load_facts(), lookup=lk, cache_doc={"records": {}})
    pairs = content["items"][0]["static_gk_pairs"]
    assert pairs[0] == ["RBI Governor: Sanjay Malhotra", "आरबीआई गवर्नर: संजय मल्होत्रा"]
    assert not lk.calls and "appointments" not in rep and "overrides" not in rep
    assert not cache.exists()


def test_lookup_fresh_bypasses_cache_read(tmp_path):
    from agents.static_gk_ai_lookup import Lookup, post_key, save_cache
    p = tmp_path / "c.json"
    post = "Governor, Reserve Bank of India"
    save_cache({"records": {post_key(post): {"post": post, "name": "Sanjay Malhotra",
                                             "verified_on": "2026-11-05"}}}, p)
    lk = Lookup(cache_path=p, today=date(2026, 11, 5), ready=lambda: (False, "off in test"))
    assert lk(post).name == "Sanjay Malhotra"
    assert lk(post, expect=[NEW], fresh=True) is None  # cache skipped; lookup off -> None
