# -*- coding: utf-8 -*-
"""Offline end-to-end test of the pipeline library (no network, no Telegram).
Run: python -m pytest tests/  OR  python tests/test_pipeline_offline.py"""
import json, os, sys, tempfile

os.environ["ALP_ROOT"] = tempfile.mkdtemp(prefix="alp_test_")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline import state, scoring, content


def make_items():
    base = [
        {"event_id": "e1", "headline_en": "Cabinet Approves New Agriculture Export Scheme with Rs 5000 Crore Outlay",
         "source_name": "PIB", "source_url": "https://pib.gov.in/e1", "source_tier": "tier1",
         "category": "Agriculture", "raw_facts": "Union Cabinet approved scheme. Outlay Rs 5000 Crore for APEDA export promotion.",
         "pub_time_ist": None, "duplicate_count": 1},
        {"event_id": "e1dup", "headline_en": "Cabinet Approves New Agriculture Export Scheme with Rs 5000 Crore outlay today",
         "source_name": "Xinhua", "source_url": "https://xinhua.example/e1", "source_tier": "tier3",
         "category": "Agriculture", "raw_facts": "Same cabinet approval reported.", "pub_time_ist": None, "duplicate_count": 1},
        {"event_id": "e2", "headline_en": "RBI Keeps Repo Rate at 6.00 Percent, CPI Inflation at 4.6 Percent",
         "source_name": "RBI", "source_url": "https://rbi.org.in/e2", "source_tier": "tier1",
         "category": "Banking & Finance", "raw_facts": "MPC unanimous decision. Repo rate 6.00 percent. CPI inflation 4.6 percent.",
         "pub_time_ist": None, "duplicate_count": 1},
        {"event_id": "e3", "headline_en": "ISRO Launches NVS-09 Navigation Satellite from Sriharikota",
         "source_name": "ISRO", "source_url": "https://isro.gov.in/e3", "source_tier": "tier1",
         "category": "Science & Technology", "raw_facts": "NVS-09 launched. 24th NavIC satellite.",
         "pub_time_ist": None, "duplicate_count": 1},
        {"event_id": "e4", "headline_en": "India Wins Gold Medal in Asian Games Hockey Final beating Japan 3-1",
         "source_name": "PIB", "source_url": "https://pib.gov.in/e4", "source_tier": "tier1",
         "category": "Sports", "raw_facts": "India beat Japan 3-1 in the final. Gold medal at Asian Games.",
         "pub_time_ist": None, "duplicate_count": 1},
        {"event_id": "e5", "headline_en": "FAO Releases State of Food and Agriculture Report 2026",
         "source_name": "FAO", "source_url": "https://fao.org/e5", "source_tier": "tier1",
         "category": "International", "raw_facts": "Report says agri GDP growth 3.5 percent.",
         "pub_time_ist": None, "duplicate_count": 1},
        {"event_id": "e6", "headline_en": "NABARD Sanitizes Refinance Facility for Cooperative Banks up to Rs 20000 Crore",
         "source_name": "NABARD", "source_url": "https://nabard.org/e6", "source_tier": "tier1",
         "category": "Banking & Finance", "raw_facts": "Refinance limit raised to Rs 20000 Crore for rural cooperative banks.",
         "pub_time_ist": None, "duplicate_count": 1},
    ]
    return base


def test_dedup_merges_duplicate_keeps_tier1():
    merged = scoring.deduplicate(make_items(), threshold=0.85)
    ids = {m["event_id"] for m in merged}
    assert "e1" in ids and "e1dup" not in ids, "tier3 duplicate must merge into tier1 rep"
    e1 = next(m for m in merged if m["event_id"] == "e1")
    assert e1["source_tier"] == "tier1" and e1["duplicate_count"] == 2


def test_scoring_in_range_and_agri_boosted():
    scored = scoring.score_all(scoring.deduplicate(make_items()))
    assert all(0 <= s["importance_score"] <= 100 for s in scored)
    agri = next(s for s in scored if s["event_id"] == "e1")
    assert agri["factors"]["agriculture"] >= 10


def test_content_no_invention_and_mcq_validation():
    scored = scoring.score_all(scoring.deduplicate(make_items()))
    c = content.build_content(scored, {"type": "daily", "date_display": "05 October 2026"})
    assert len(c["items"]) == len(scored)
    for it in c["items"]:
        assert it["headline_hi"].startswith(">>") and it["key_points_en"]
    mcqs = content.generate_mcqs(c["items"], target=(5, 15))
    valid, rejected = content.validate_mcqs(mcqs, c["items"])
    assert len(valid) >= 5, f"need >=5 valid MCQs, got {len(valid)}; rejected={rejected}"
    for m in valid:
        idx = ord(m["correct"]) - 65
        assert 0 <= idx < len(m["options"])
        assert len(set(m["options"])) == len(m["options"])


def test_pdf_end_to_end_and_qa_checks():
    scored = scoring.score_all(scoring.deduplicate(make_items()))
    c = content.build_content(scored, {"type": "daily", "date": "2026-10-05",
                                       "date_display": "05 October 2026"})
    mcqs = content.generate_mcqs(c["items"], target=(5, 15))
    valid, _ = content.validate_mcqs(mcqs, c["items"])
    from src.generate_pdf import generate_pdf
    pdf = generate_pdf(c, valid)
    import pymupdf, re
    doc = pymupdf.open(pdf)
    txt = "".join(p.get_text() for p in doc)
    assert doc.page_count >= 3
    assert re.search("[\u0900-\u097F]", txt), "Hindi extractable"
    assert "05 October 2026" in re.sub(r"\s+", " ", txt), "date present"
    fonts = set(f[3] for pg in doc for f in pg.get_fonts())
    assert any("Mukta" in f for f in fonts), f"Mukta embedded, got {fonts}"
    assert not any(p for p in doc if len(p.get_text().strip()) < 15), "no blank pages"
    # empty edition must be REFUSED (never publish filler PDF)
    try:
        generate_pdf({"job": {"type": "daily", "date_display": "x"}, "items": []}, [])
        assert False, "should refuse empty"
    except ValueError:
        pass


def test_state_machine_and_lock():
    j = state.load_job("daily_2026-10-05", "daily", "2026-10-05")
    state.save_job(j, state="COLLECTED", stage="03_news_collection")
    j2 = state.read_json(state.job_path("daily_2026-10-05"))
    assert j2["status"] == "COLLECTED" and j2["last_success_stage"] == "03_news_collection"
    lock = state.JobLock("daily_2026-10-05"); assert lock.acquire()
    lock2 = state.JobLock("daily_2026-10-05"); assert not lock2.acquire(), "second process blocked"
    lock.release(); assert state.JobLock("daily_2026-10-05").acquire()


if __name__ == "__main__":
    for fn in [test_dedup_merges_duplicate_keeps_tier1, test_scoring_in_range_and_agri_boosted,
               test_content_no_invention_and_mcq_validation, test_pdf_end_to_end_and_qa_checks,
               test_state_machine_and_lock]:
        fn(); print("PASS:", fn.__name__)
    print("ALL OFFLINE TESTS PASSED")
