# -*- coding: utf-8 -*-
"""Strict Static GK validator (agents/static_gk_validator.py, stage 17c) + facts refresh script."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from agents import static_gk_validator as v

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def facts():
    return v.load_facts()


def test_current_facts_file_is_complete_and_sourced():
    doc = json.loads((ROOT / "config" / "current_facts.json").read_text(encoding="utf-8"))
    ids = {f["id"] for f in doc["facts"]}
    for must in ("rbi_governor", "icar_dg", "apeda_chair", "president_india", "prime_minister_india", "cji"):
        assert must in ids
    for f in doc["facts"]:
        assert f["name"] and f["post"] and f["verified_on"]
        assert f["source_url"].startswith("https://")
        assert f["match"], f["id"]


def test_wrong_rbi_governor_is_replaced(facts):
    r = v.check_line("RBI Governor – Shaktikanta Das", "आरबीआई गवर्नर – शक्तिकांत दास", facts, year=2026)
    assert r.action == "replace" and r.en == "RBI Governor – Sanjay Malhotra"
    assert r.hi == ""  # unverified Hindi name never survives a correction
    row = {"label_en": "RBI Governor", "value_en": "Shaktikanta Das",
           "label_hi": "आरबीआई गवर्नर", "value_hi": "शक्तिकांत दास"}
    action, new, _ = v.check_row(row, facts, year=2026)
    assert action == "replace" and new["value_en"] == "Sanjay Malhotra" and new["value_hi"] == "संजय मल्होत्रा"


def test_correct_holders_and_timeless_lines_are_kept(facts):
    for en in ("Governor of the Reserve Bank of India: Sanjay Malhotra", "APEDA Chairman – Abhishek Dev",
               "Headquarters – Mumbai, Maharashtra", "Established – 12 July 1982",
               "RBI Governor chairs the Monetary Policy Committee", "Founded by Verghese Kurien",
               "Union Minister of Agriculture serves as President of ICAR Society"):
        assert v.check_line(en, "", facts, year=2026).action == "keep", en


def test_icar_dg_and_apeda_chair_corrected(facts):
    assert v.check_line("ICAR Director General – Dr. Himanshu Pathak", "", facts).en.endswith("Mangi Lal Jat")
    assert v.check_line("APEDA Chairperson – M. Angamuthu", "", facts).en == "APEDA Chairperson – Abhishek Dev"


def test_unverifiable_names_are_dropped(facts):
    assert v.check_line("Chairman of Coir Board – Vipul Goyal", "", facts).action == "drop"
    assert v.check_line("Prime Minister – Manmohan Singh", "", facts).action == "drop"
    # Multi-holder post with an unknown name is dropped, not "corrected".
    assert v.check_line("Deputy Governor of RBI – Michael Debabrata Patra", "", facts).action == "drop"
    assert v.check_line("RBI Deputy Governor – Poonam Gupta", "", facts).action == "keep"
    # Foreign posts are never rewritten to Indian holders.
    r = v.check_line("Pakistan Army Chief – Asim Munir", "", facts)
    assert r.action == "drop" and "Dhiraj" not in r.en


def test_name_verified_by_story_text_is_kept(facts):
    story = "Union Minister Jayant Chaudhary signed the MoU in Bhopal."
    assert v.check_line("Union Minister for MSDE – Jayant Chaudhary", "", facts, story_text=story).action == "keep"


def test_new_appointment_story_is_not_overwritten(facts):
    story = "Shri X Y Newman appointed as the new RBI Governor, takes charge on Monday."
    r = v.check_line("RBI Governor – X Y Newman", "", facts, story_text=story)
    assert r.action == "drop"


def test_stale_latest_lines_are_dropped(facts):
    assert v.check_line("Latest GDP growth (2023-24) – 8.2%", "", facts, year=2026).action == "drop"
    assert v.check_line("Current repo rate as of 2024: 6.5%", "", facts, year=2026).action == "drop"
    assert v.check_line("Latest GDP data FY24 – 8.2%", "", facts, year=2026).action == "drop"
    assert v.check_line("Established in 2024 – new body", "", facts, year=2026).action == "keep"
    assert v.check_line("Latest data (2025-26) – 7.4%", "", facts, year=2026).action == "keep"


def test_validate_edition_fixes_content_and_mcq_pairs(facts):
    content = {"items": [{"event_id": "e1", "headline_en": "RBI policy",
                          "static_gk_pairs": [["RBI Governor: Shaktikanta Das", "आरबीआई गवर्नर: शक्तिकांत दास"],
                                              ["RBI HQ: Mumbai", "आरबीआई मुख्यालय: मुंबई"]],
                          "static_facts": {"Head": "Chairman of Coir Board Vipul Goyal", "HQ": "Mumbai"}}],
               "agri_corner": {"static_gk": [{"en": "ICAR DG – Dr. Himanshu Pathak", "hi": "आईसीएआर महानिदेशक – डॉ. हिमांशु पाठक"},
                                             {"en": "ICAR established – 1929", "hi": "आईसीएआर स्थापना – 1929"}]}}
    mcq = [{"event_id": "e1", "static_gk": [
        {"label_en": "RBI Governor", "value_en": "Shaktikanta Das", "label_hi": "आरबीआई गवर्नर", "value_hi": "शक्तिकांत दास"},
        {"label_en": "Latest inflation (2023)", "value_en": "5.4%", "label_hi": "नवीनतम मुद्रास्फीति", "value_hi": "5.4%"},
        {"label_en": "Founded", "value_en": "1935", "label_hi": "स्थापना", "value_hi": "1935"}]}]
    rep = v.validate_edition(content, mcq, facts)
    it = content["items"][0]
    assert it["static_gk_pairs"][0] == ["RBI Governor: Sanjay Malhotra", ""]
    assert it["static_gk_pairs"][1][0] == "RBI HQ: Mumbai"
    assert it["static_facts"] == {"HQ": "Mumbai"}
    assert content["agri_corner"]["static_gk"][0]["en"].endswith("Mangi Lal Jat")
    assert content["agri_corner"]["static_gk"][0]["hi"] == ""
    assert [r["value_en"] for r in mcq[0]["static_gk"]] == ["Sanjay Malhotra", "1935"]
    assert rep["replaced"] == 3 and rep["dropped"] == 2


def test_validator_fails_open(monkeypatch, facts, tmp_path):
    content = {"items": [{"static_gk_pairs": [["RBI Governor – Shaktikanta Das", ""], ["HQ – Mumbai", ""]]}]}
    monkeypatch.setattr(v, "check_line", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    rep = v.validate_edition(content, None, facts)
    assert rep["errors"] == 2
    assert content["items"][0]["static_gk_pairs"] == [["HQ – Mumbai", ""]]   # officeholder line dropped
    # Missing facts file: officeholder-type lines are dropped, the rest kept, nothing raises.
    content = {"items": [{"static_gk_pairs": [["RBI Governor – Anyone", ""], ["HQ – Mumbai", ""]]}]}
    monkeypatch.setenv("ALP_CURRENT_FACTS", str(tmp_path / "missing.json"))
    rep = v.validate_edition(content, None)
    assert rep.get("fallback") and content["items"][0]["static_gk_pairs"] == [["HQ – Mumbai", ""]]


def _stage():
    spec = importlib.util.spec_from_file_location("t_stage17c", str(ROOT / "agents" / "17c_static_gk_validator.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_stage_registered_after_static_gk_generation_and_non_critical():
    import main
    from pipeline.checkpoints import CONTENT_REWRITERS, STAGE_FILES
    from pipeline.state import STAGE_TO_STATE
    names = [s[0] for s in main.DAILY_STAGES]
    assert names.index("17b_auto_sections") < names.index("17c_static_gk_validator") < names.index("18_pdf_design")
    assert [s for s in main.DAILY_STAGES if s[0] == "17c_static_gk_validator"][0][2] is False
    assert "17c_static_gk_validator" in [s[0] for s in main.WEEKLY_STAGES]
    assert "17c_static_gk_validator" in CONTENT_REWRITERS and "17c_static_gk_validator" in STAGE_TO_STATE
    assert STAGE_FILES["17c_static_gk_validator"] == "data/mcq/{job}.json"


def test_stage_rewrites_artifacts_and_is_fail_open(tmp_path, monkeypatch):
    mod = _stage()
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    job = "daily_2026-11-04"
    (tmp_path / "data/content").mkdir(parents=True)
    (tmp_path / "data/mcq").mkdir(parents=True)
    (tmp_path / f"data/content/{job}.json").write_text(json.dumps({"items": [
        {"event_id": "e1", "static_gk_pairs": [["RBI Governor – Shaktikanta Das", ""]]}]}), encoding="utf-8")
    (tmp_path / f"data/mcq/{job}.json").write_text(json.dumps([{"event_id": "e1", "static_gk": [
        {"label_en": "ICAR DG", "value_en": "Himanshu Pathak", "label_hi": "", "value_hi": ""}]}]), encoding="utf-8")
    assert mod.run(job) == 0
    c = json.loads((tmp_path / f"data/content/{job}.json").read_text(encoding="utf-8"))
    m = json.loads((tmp_path / f"data/mcq/{job}.json").read_text(encoding="utf-8"))
    assert c["items"][0]["static_gk_pairs"][0][0].endswith("Sanjay Malhotra")
    assert m[0]["static_gk"][0]["value_en"] == "Mangi Lal Jat"
    assert c["static_gk_validation"]["replaced"] == 2
    # Unreadable content: exit 0, nothing raised.
    (tmp_path / f"data/content/{job}.json").write_text("{not json", encoding="utf-8")
    assert mod.run(job) == 0


def test_mcq_prompt_forbids_officeholders_from_memory():
    from pipeline.mcq_schema import build_prompt
    p = build_prompt({"headline_en": "RBI keeps repo rate unchanged"}, "The RBI Monetary Policy Committee met.")
    assert "NEVER name a current officeholder" in p and "Sanjay Malhotra" in p


def test_refresh_script_strict_on_page_check():
    spec = importlib.util.spec_from_file_location("t_refresh", str(ROOT / "scripts" / "refresh_current_facts.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    doc = {"facts": [
        {"id": "a", "post": "Chairman, APEDA", "name": "Old Name", "match": ["APEDA Chairman"], "source_url": "u1",
         "verified_on": "2026-01-01"},
        {"id": "b", "post": "Chairman, NDDB", "name": "Meenesh Shah", "match": ["NDDB Chairman"], "source_url": "u2",
         "verified_on": "2026-01-01"},
        {"id": "c", "post": "Governor, RBI", "name": "Sanjay Malhotra", "match": ["RBI Governor"], "source_url": "u3",
         "verified_on": "2026-01-01"},
        {"id": "d", "post": "CEO", "name": "X", "match": ["CEO"], "source_url": "u4", "verified_on": "2026-01-01"},
    ]}
    pages = {"u1": "<p>Shri New Person, IAS — Chairman, APEDA</p>", "u2": "<b>Dr Meenesh Shah</b>, Chairman NDDB",
             "u3": "<p>Governor of the Reserve Bank</p>"}

    def fetch(url):
        if url in pages:
            return 200, pages[url]
        raise OSError("down")

    answers = {"Chairman, APEDA": '{"name": "New Person", "since": null}',
               "Governor, RBI": '{"name": "Invented Name", "since": null}'}

    def llm(prompt):
        return next(a for k, a in answers.items() if k in prompt)

    res = mod.refresh(doc, fetch=fetch, llm=llm, today="2026-11-04")
    a, b, c, d = doc["facts"]
    assert a["name"] == "New Person" and a["verified_on"] == "2026-11-04"      # confirmed on page
    assert b["verified_on"] == "2026-11-04"                                     # still on page
    assert c["name"] == "Sanjay Malhotra" and c["verified_on"] == "2026-01-01"  # hallucination rejected
    assert d["name"] == "X" and res["unreachable"]
    assert len(res["changed"]) == 1 and res["review"]


def test_historical_officeholder_lines_are_timeless(facts):
    for en in ("First Chief Justice – H. J. Kania", "First RBI Governor – Osborne Smith",
               "Founded by Verghese Kurien (former NDDB Chairman)"):
        r = v.check_line(en, "", facts, year=2026)
        assert r.action == "keep" and r.en == en, en
