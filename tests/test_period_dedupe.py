"""Weekly/monthly summary bullets: whole sentences, no repeats (real-like fixtures).

The fixtures copy the shape of real published daily items (Oct–Nov 2026):
key points cut at ~200 characters and split at every ". " (so they end
mid-sentence and break at initials), "Published – … IST – CITY" datelines,
"Photo Credit: NAME" glued to the next sentence, and generic filler / Static GK
facts repeated across many stories.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import period_builder as pb  # noqa: E402

FILLER = "Key statutory bodies, constitutional appointments, national policies, and governance initiatives."
MEA_GK = "The Ministry of External Affairs (MEA) is responsible for the conduct of India's foreign relations."

TNCC_TEXT = (
    "Published - October 29, 2026 01:00 am IST - Chennai B. Thamodharan Tamil Nadu Congress Committee president "
    "B. Manickam Tagore urged the Congress government in Karnataka to recognise the merit of the petition filed by "
    "the Tamil Nadu government in the Supreme Court and immediately come forward to make up the outstanding water "
    "deficit at Biligundulu in accordance with the Cauvery Water Management Authority’s order. In a statement, "
    "Mr. Tagore said that the livelihood of Tamil Nadu’s Delta farmers should be ensured and that the Samba crops "
    "should be protected. The Karnataka government has a legal obligation to release without obstruction the "
    "rightful share of water to be provided to Tamil Nadu. Although the Cauvery Water Reg"
)
SFI_TEXT = (
    "Published - October 29, 2026 04:35 am IST The Students’ Federation of India (SFI) on Wednesday alleged that "
    "Jawaharlal Nehru University’s (JNU) PhD Admission Prospectus 2026–27 falls short of the prescribed reservation "
    "quotas for Scheduled Castes (SC), Scheduled Tribes (ST) and Persons with Benchmark Disabilities (PwBD). It "
    "called on the university to rectify the shortfall in the seats advertised for the current admission cycle. "
    "However, only 38 seats have been advertised, a shortfall of around 15. Similarly, against the mandated 15% "
    "reservation for Scheduled Castes, approximately 107 seats should be reserved, whereas only 103 have been ad"
)
SHAH_TEXT = (
    "Updated - November 03, 2026 01:48 am IST - HYDERABAD Union Home Minister Amit Shah addresses a public meeting "
    "in Hyderabad on Monday (November 2). Photo Credit: RAMAKRISHNA G Union Home Minister Amit Shah on Monday "
    "alleged that the Election Commission of India’s (ECI) Special Intensive Revision (SIR) exercise had identified "
    "around three crore ‘unaccounted voters’, among the 13 crore names removed from electoral rolls. He asserted "
    "that all such infiltrators would be expelled from the country. Countdown progressing for the next phase of "
    "SIR in Telangana The Election Commission is expected to announce the schedule soon."
)


def _char_limit_points(text: str, limit: int = 200) -> list:
    """What the daily did: split at every '. ' and cut each piece at ~200 characters."""
    out = []
    for piece in text.split(". "):
        piece = piece.strip().rstrip(".")
        if len(piece) > limit:
            piece = piece[:limit].rsplit(" ", 1)[0]
        if piece:
            out.append(piece)
    return out


def _item(eid: str, head: str, text: str, day: str = "2026-10-29", **kw) -> dict:
    it = {
        "event_id": eid, "category": "National", "importance_score": 70,
        "headline_en": head, "headline_hi": "परीक्षण शीर्षक " + eid,
        "summary_en": text.split(". ")[0], "summary_hi": "",
        "detailed_explanation_en": text,
        "key_points_en": _char_limit_points(text)[:4], "key_points_hi": ["", "", "", ""],
        "exam_fact_en": FILLER, "exam_fact_hi": "परीक्षा संदर्भ: " + FILLER,
        "static_gk_pairs": [], "static_facts": {}, "needs_review": False, "verification_passed": True,
        "edition_date": day,
    }
    it.update(kw)
    return it


def _bullets(it: dict) -> list:
    return [p["en"] for p in it["summary_pairs"]]


# --------------------------------------------------------------------------- #
# Sentence splitting
# --------------------------------------------------------------------------- #
def test_split_sentences_respects_initials_abbreviations_numbers_and_danda():
    s = pb.split_sentences("Chennai B. Thamodharan met Mr. Tagore and M.K. Stalin at 3.5 p.m. today. "
                           "The U.S. delegation agreed. It cost Rs. 20 crore")
    assert s == ["Chennai B. Thamodharan met Mr. Tagore and M.K. Stalin at 3.5 p.m. today.",
                 "The U.S. delegation agreed."]  # the unterminated tail is dropped, never shown half
    hi = pb.split_sentences("केंद्र ने योजना शुरू की। इससे 5 लाख किसानों को लाभ होगा। अधूरा वाक्य")
    assert hi == ["केंद्र ने योजना शुरू की।", "इससे 5 लाख किसानों को लाभ होगा।"]


def test_dateline_and_photo_credit_are_removed_without_eating_the_sentence():
    assert pb.clean_source_text(SHAH_TEXT).startswith("Union Home Minister Amit Shah on Monday alleged")
    t = pb.clean_source_text("Published - October 30, 2026 01:50 am IST - Srinagar J&K Deputy CM speaks. "
                             "Photo Credit: Imran Nissar As the BJP launched a meme war, he replied. It ended.")
    assert pb.split_sentences(t) == ["As the BJP launched a meme war, he replied.", "It ended."]
    # A credit whose end cannot be found poisons only the next sentence.
    t = pb.clean_source_text("Caption. Photo Credit: John Doe Rao urged them to act. Then more people came here later.")
    assert [x for x in pb.split_sentences(t) if pb.complete_sentence(x)] == ["Then more people came here later."]


# --------------------------------------------------------------------------- #
# Bug 1: character-limit splitting produced half lines
# --------------------------------------------------------------------------- #
def test_char_limit_key_points_become_whole_sentences_of_the_same_story():
    sfi = _item("sfi", "SFI alleges reservation violations in PhD seat intake at JNU", SFI_TEXT)
    tncc = _item("tncc", "TNCC president asks Karnataka to respect CWMA order", TNCC_TEXT)
    shah = _item("shah", "Amit Shah backs SIR, alleges 3 crore illegal infiltrators", SHAH_TEXT, day="2026-11-03")
    # The raw daily points really are broken: cut mid-sentence and split at an initial.
    assert not pb.complete_sentence(sfi["key_points_en"][0])          # cut mid-sentence, no full stop
    assert "Chennai B" in tncc["key_points_en"][0]
    seen: list = []
    for it in (sfi, tncc, shah):
        it["summary_pairs"] = pb._summary_pairs(it, seen, set())
        body = " ".join(pb.split_sentences(pb.clean_source_text(it["detailed_explanation_en"])))
        assert it["summary_pairs"], it["event_id"]
        for b in _bullets(it):
            assert pb.complete_sentence(b), b                  # starts like a sentence, ends with . ! ? ।
            assert b in body, (it["event_id"], b)              # a whole sentence of THIS story's text
            assert not b[0].islower() and not pb.run_on(b)
    assert _bullets(sfi)[0].endswith("Persons with Benchmark Disabilities (PwBD).")
    assert not any("Thamodharan Tamil Nadu Congress Committee president B" == b for b in _bullets(tncc))
    assert any(b.startswith("B. Manickam Tagore urged") or "Manickam Tagore urged" in b for b in _bullets(tncc))
    # The unterminated last fragment ("... only 103 have been ad") is dropped.
    assert not any(b.endswith("have been ad") or "Water Reg" in b for it in (sfi, tncc) for b in _bullets(it))
    # Caption before a photo credit and the glued "Countdown ... The Election ..." run-on are not bullets.
    assert not any("addresses a public meeting" in b or b.startswith("Countdown") for b in _bullets(shah))


def test_hindi_kept_only_when_the_key_point_was_the_whole_sentence():
    text = ("The Cabinet approved a ₹500 crore seed fund for FPOs. The fund will be run by NABARD from 2027. "
            "Over 10,000 FPOs are expected to benefit in the first phase of the programme.")
    it = _item("fpo", "Cabinet approves seed fund for FPOs", text,
               key_points_en=["The Cabinet approved a ₹500 crore seed fund for FPOs",          # whole sentence
                              "Over 10,000 FPOs are expected to benefit in the first"],      # cut by the daily
               key_points_hi=["कैबिनेट ने एफपीओ के लिए ₹500 करोड़ के बीज कोष को मंज़ूरी दी",
                              "पहले चरण में 10,000 से अधिक एफपीओ को"])
    pairs = pb._summary_pairs(it, [], set())
    by_en = {p["en"]: p["hi"] for p in pairs}
    assert by_en["The Cabinet approved a ₹500 crore seed fund for FPOs."].endswith("मंज़ूरी दी।")
    # Extended from a cut key point: its Hindi translated only half the sentence → English only.
    assert by_en["Over 10,000 FPOs are expected to benefit in the first phase of the programme."] == ""
    assert pairs[0]["hi"]  # bilingual line first


# --------------------------------------------------------------------------- #
# Bug 2: the same sentence repeated across stories
# --------------------------------------------------------------------------- #
def _mea_story(n: int, day: str) -> dict:
    topics = ["pharmaceutical exports", "solar energy", "defence production", "student mobility",
              "maritime security", "lithium mining"]
    cities = ["Yerevan", "Dakar", "Warsaw", "Ottawa", "Mombasa", "Santiago"]
    text = (f"Officials from both sides reviewed cooperation on {topics[n]} during the meeting. {MEA_GK} "
            f"The next meeting will be held in {cities[n]} after the delegations finalise an agenda.")
    heads = ["12th round of India-Armenia Foreign Office Consultations",
             "Shri Inbasekar Sundaramurthi appointed Ambassador to Senegal",
             "Joint Statement on the official visit of the Prime Minister of Poland",
             "Inaugural India–Canada Migration and Mobility Dialogue",
             "EAM Jaishankar meets Kenyan counterpart on maritime security",
             "India and Chile sign MoU on critical minerals exploration"]
    return _item(f"mea{n}", heads[n], text, day=day,
                 static_gk_pairs=[{"en": MEA_GK, "hi": "विदेश मंत्रालय (MEA) भारत के विदेशी संबंधों के संचालन के लिए उत्तरदायी है।"},
                                  {"en": "MEA is headquartered at South Block, New Delhi.", "hi": ""}])


def _editions(items_by_day: dict) -> list:
    return [{"date": d, "content": {"items": its, "one_liners": []}, "mcqs": []} for d, its in items_by_day.items()]


def test_repeated_sentence_filler_and_gk_printed_at_most_once():
    days = ["2026-10-28", "2026-10-29", "2026-10-30"]
    eds = _editions({d: [_mea_story(i * 2 + j, d) for j in range(2)] for i, d in enumerate(days)})
    r = pb.build_period("weekly", "2026-11-04", eds, days)
    items = r["content"]["items"]
    # Stories whose every sentence repeats an earlier story's template text would print
    # headline-only: they are dropped (weekly 2026-11-08 printed 10 such stories).
    assert 2 <= len(items) <= 6 and len(items) + r["stats"]["title_only_dropped"] == 6
    assert all(_bullets(it) for it in items)
    lines = [b for it in items for b in _bullets(it)]
    gk = [p["en"] for it in items for p in it["static_gk_pairs"]]
    assert MEA_GK not in lines                       # filler shared by 6 stories: never a bullet
    assert len(lines) == len(set(lines)) and lines
    assert gk.count(MEA_GK) == 1 and len(gk) == len(set(gk))   # GK fact once, under the first story
    for it in items:                                 # generic exam fact never reaches the renderer
        assert not it["exam_fact_en"] and not it["static_facts"]
        assert FILLER not in " ".join(p["en"] for p in it["static_gk_pairs"])


def test_near_identical_bullets_deduped_within_story_and_across_edition():
    text = ("The RBI kept the repo rate unchanged at 5.5 per cent on Friday. "
            "The RBI kept the repo rate unchanged at 5.5 percent on Friday. "
            "Inflation is projected at 3.1 per cent for the year.")
    a = _item("rbi1", "RBI keeps repo rate unchanged", text)
    b = _item("rbi2", "Monetary policy: growth forecast raised", "Growth is now forecast at 6.8 per cent this year. "
              "The RBI kept the repo rate unchanged at 5.5 per cent on Friday.")
    seen: list = []
    pa, pb_ = pb._summary_pairs(a, seen, set()), pb._summary_pairs(b, seen, set())
    assert [p["en"] for p in pa] == ["The RBI kept the repo rate unchanged at 5.5 per cent on Friday.",
                                     "Inflation is projected at 3.1 per cent for the year."]
    assert [p["en"] for p in pb_] == ["Growth is now forecast at 6.8 per cent this year."]


def test_same_event_across_days_merged_distinct_events_kept():
    s1 = _item("a1", "Government of India Provides US $ 51 million to Sri Lanka - Ministry of External Affairs",
               "India provided US $51 million to Sri Lanka for housing.", day="2026-10-19")
    s2 = _item("a2", "Government of India Provides US $ 51 million to Sri Lanka",
               "India provided US $51 million to Sri Lanka for housing.", day="2026-10-27")
    s3 = _item("b1", "PM inaugurates Bharat Renewable Energy Summit & Expo 2026 - PM India",
               "The PM opened the summit.", day="2026-11-03")
    s4 = _item("b2", "PM’s address at the inauguration of Bharat Renewable Energy Summit & Expo 2026",
               "The PM addressed the summit.", day="2026-11-04")
    c1 = _item("c1", "Chennai Corporation considers new feasibility study for ropeway", "x.", day="2026-10-20")
    c2 = _item("c2", "Corporation RDCs inspect drain cleaning across Chennai", "y.", day="2026-10-21")
    n1 = _item("n1", "NABARD launches a drip irrigation mission in Odisha", "z.", day="2026-10-20")
    n2 = _item("n2", "NABARD launches a soil health card drive in Odisha", "w.", day="2026-10-22")
    stats: dict = {}
    kept = pb.dedupe([s1, s2, s3, s4, c1, c2, n1, n2], stats)
    ids = {k["event_id"] for k in kept}
    assert stats["duplicates_dropped"] == 2
    assert len(ids & {"a1", "a2"}) == 1 and len(ids & {"b1", "b2"}) == 1
    assert {"c1", "c2", "n1", "n2"} <= ids


# --------------------------------------------------------------------------- #
# Renderer + QA
# --------------------------------------------------------------------------- #
def test_renderer_never_falls_back_to_raw_cut_key_points():
    from src import period_pdf
    it = {"summary_pairs": [], "key_points_en": ["Thamodharan Tamil Nadu Congress Committee president B"]}
    assert period_pdf._summary(it, 3) == []
    it = {"summary_pairs": [{"en": "A whole sentence about the story is here.", "hi": ""},
                            {"en": "a cut line without an end", "hi": ""}]}
    assert period_pdf._summary(it, 3) == [("A whole sentence about the story is here.", "")]


def _qa():
    spec = importlib.util.spec_from_file_location("t_qa19_repeat", str(ROOT / "agents" / "19_pdf_qa.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["t_qa19_repeat"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_qa_repeated_lines_warns_but_never_fails(tmp_path, monkeypatch, caplog):
    fitz = pytest.importorskip("fitz")
    qa = _qa()
    doc = fitz.open()
    for _ in range(2):
        page = doc.new_page()
        page.insert_text((40, 30), "AGRI LEARNING POINT | WEEKLY CURRENT AFFAIRS header")   # header band
        y = 120
        for line in [MEA_GK[:80], "A unique line about one particular story number one.", MEA_GK[:80]]:
            page.insert_text((40, y), line, fontsize=9)
            y += 40
    pdf = tmp_path / "w.pdf"
    doc.save(pdf)
    monkeypatch.setenv("PDF_QA_STRICT", "1")
    report = qa.QAReport(pdf_path=str(pdf), checked_at="now")
    with fitz.open(pdf) as d:
        reps = qa.check_repeated_lines(report, d)
    assert reps == [(MEA_GK[:80], 4)]
    assert [i.code for i in report.issues] == ["repeated_lines"] and report.issues[0].severity == "info"
    assert report.passed  # never blocks, even in strict mode
    assert "repeat more than 2 times" in caplog.text
