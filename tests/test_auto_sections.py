# -*- coding: utf-8 -*-
"""Automatic Quick Bites + Agriculture Corner (pipeline/auto_sections.py, stage 17b).

No network: translation is injected.  Hindi is fail-closed - an item whose Hindi
is missing or fails the translator's validator is dropped, never printed raw.
"""
import importlib.util
import json
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline import auto_sections as A  # noqa: E402

HEADS = [
    ("GST collections surge 23% to Rs 2.31 lakh crore in October", "Economy"),
    ("MoD inks Rs 53,866 crore contracts for 8 Next Generation Corvettes for Indian Navy", "National"),
    ("EAM meets EU foreign policy chief on sidelines of G20 meeting", "International"),
    ("ISRO to launch navigation satellite NVS-03 aboard GSLV-F18 from Sriharikota", "Science & Technology"),
    ("India beat New Zealand to clinch ODI series 2-1 in Ahmedabad", "Sports"),
    ("PM to inaugurate Pune Metro projects worth Rs 21,800 crore on 3 November", "National"),
    ("Centre extends tenure of exam reform panel till January", "National"),
    ("RBI releases Financial Stability Report showing gross NPAs at 2.3%", "Banking & Finance"),
    ("UP begins paddy procurement at MSP of Rs 2,441 per quintal through 4,500 centres", "Agriculture"),
    ("Soreng becomes India's first organic fisheries cluster under PMMSY", "Agriculture"),
    ("Rainfall deficit delays rabi sowing in Rajasthan", "Agriculture"),
    ("Jagan accuses SEC of complicity in civic poll malpractices, says YSRCP will go to court", "National"),
    ("Bid opening meeting link for Procurement of IARI Laboratory Equipment", "Agriculture"),
]


def _cands(n_extra=30):
    out = [{"event_id": f"e{i}", "headline_en": h, "category": c, "student_relevance": 90 - i,
            "raw_facts": "Updated - November 02, 2026 04:49 pm IST. Image used for representational purposes only."}
           for i, (h, c) in enumerate(HEADS)]
    for j in range(n_extra):
        out.append({"event_id": f"x{j}", "headline_en": f"Region{j} approves policy{j} plan for sector{j} growth",
                    "category": "Economy", "student_relevance": 40 - j * 0.1})
    return out


def _fake_hindi(lines, deadline):
    """Plausible validated Hindi: keeps every number and acronym (as the real validator demands)."""
    import re
    out = {}
    for ln in lines:
        keep = " ".join(re.findall(r"[A-Z]{2,8}|\d[\d,.]*", ln))
        out[ln] = f"हिंदी अनुवाद समाचार पंक्ति {keep} के बारे में विस्तृत जानकारी यहाँ दी गई है।"
    return out


def test_builds_bilingual_quick_bites_and_agri_corner_excluding_units():
    content = {"items": [{"event_id": "e0", "headline_en": HEADS[0][0], "headline_hi": "जीएसटी संग्रह 23% बढ़ा", "category": "Economy"}],
               "one_liners": []}
    stats = A.build_sections(content, _cands(), budget_seconds=30, translate=_fake_hindi)
    qb = content["quick_bites"]
    assert A.QB_MIN <= len(qb) <= A.QB_MAX, stats
    texts = " ".join(b["en"] for b in qb)
    assert "GST collections" not in texts                 # MCQ unit never repeated as a bite
    assert "Jagan accuses" not in texts                    # political sound-bite filtered
    assert "Bid opening" not in texts                      # notice filtered
    assert "Updated -" not in texts and "representational" not in texts  # junk summary lines stripped
    assert all(b["hi"] and b["category_hi"] for b in qb)
    assert {b["category_en"] for b in qb} <= {c for c, _h in A.CATEGORIES}
    cats = [A._CAT_ORDER[b["category_en"]] for b in qb]
    assert cats == sorted(cats)                            # grouped by category band
    agri = content["agri_corner"]
    agri_txt = " ".join(i["en"] for i in agri["items"])
    assert "paddy procurement" in agri_txt and "PMMSY" in agri_txt
    assert all("paddy" not in b["en"] for b in qb)        # agri goes to the corner, not bites
    assert agri["static_gk"] and all(g["en"] and g["hi"] for g in agri["static_gk"])
    assert any("CACP" in g["en"] or "MSP" in g["en"] for g in agri["static_gk"])


def test_quick_bite_categories():
    cat = A.quick_bite_category
    assert cat({"headline_en": "India beat New Zealand to clinch ODI series"}) == "Sports"
    assert cat({"headline_en": "MoD inks contracts for corvettes for Indian Navy"}) == "Defence & Awards"
    assert cat({"headline_en": "EAM meets EU foreign policy chief"}) == "International"
    assert cat({"headline_en": "GST collections surge in October"}) == "Economy & Finance"
    assert cat({"headline_en": "ISRO to launch NVS-03 satellite"}) == "Science, Health & Environment"


def test_hindi_is_fail_closed():
    content = {"items": [], "one_liners": []}

    def bad(lines, deadline):
        out = {}
        for i, ln in enumerate(lines):
            if i % 3 == 0:
                out[ln] = ln                                # English echoed back -> invalid
            elif i % 3 == 1:
                out[ln] = "अधूरा अनुवाद"                    # numbers/acronyms missing -> invalid
        return out

    A.build_sections(content, _cands(), budget_seconds=30, translate=bad)
    for b in content.get("quick_bites", []):
        assert A._valid_hindi(b["en"], b["hi"])
    stats = content["auto_sections_stats"]
    assert stats["dropped_no_hindi"] > 0


def test_no_translation_means_no_sections_and_never_raises():
    content = {"items": [], "one_liners": [], "quick_bites": [{"en": "stale"}]}
    A.build_sections(content, _cands(), budget_seconds=5, translate=lambda l, d: {})
    assert "quick_bites" not in content and "agri_corner" not in content

    def boom(lines, deadline):
        raise RuntimeError("provider down")

    content = {"items": [], "one_liners": []}
    A.build_sections(content, _cands(), budget_seconds=5, translate=boom)
    assert "quick_bites" not in content


def test_batch_translate_respects_deadline(monkeypatch):
    monkeypatch.setattr("pipeline.ai_router.is_configured", lambda: True)
    calls = []
    monkeypatch.setattr("pipeline.content._prefill_body_translation_cache", lambda chunk, task: calls.append(chunk))
    assert A.batch_translate(["a line"] * 3, deadline=time.monotonic() - 1) == {}
    assert calls == []


def test_batch_translate_uses_validated_batches(monkeypatch):
    from pipeline import content as C
    monkeypatch.setattr("pipeline.ai_router.is_configured", lambda: True)

    def fake_prefill(chunk, task):
        for ln in chunk:
            C._TRANSLATION_CACHE[(task, C._norm_ws(ln))] = (f"हिंदी {ln[-2:]}", "ai_translator", 1.0)
    monkeypatch.setattr(C, "_prefill_body_translation_cache", fake_prefill)
    lines = [f"Line number {i:02d}" for i in range(23)]
    out = A.batch_translate(lines, deadline=time.monotonic() + 30, task="qb_test", batch_size=10)
    assert len(out) == 23


def test_trim_quick_bites_keeps_each_category():
    content = {"quick_bites": [{"category_en": c, "en": f"{c} {i}"} for c in ("A", "B", "C") for i in range(10)]}
    assert A.trim_quick_bites(content, 9) == 9
    assert {b["category_en"] for b in content["quick_bites"]} == {"A", "B", "C"}


def test_clean_headline_and_two_line_text():
    assert A.clean_headline(">> AIR CHIEF MARSHAL DIXIT ASSUMES CHARGE AS THE 29TH CHIEF - pib.gov.in") == \
        "Air Chief Marshal Dixit Assumes Charge as the 29th Chief"
    item = {"headline_en": "GST collections surge to Rs 2.31 lakh crore",
            "raw_facts": "Updated - November 02. Gross GST collections rose 23% year-on-year in October 2026, the finance ministry said."}
    txt = A.two_line_text(item)
    assert txt.startswith("GST collections surge") and "23%" in txt and "Updated" not in txt
    assert len(A.two_line_text({"headline_en": "x " * 300})) <= A.EN_MAX_CHARS + 1


def test_same_event_dedup():
    assert A.same_event("Manufacturing PMI eases to 54.7 in October, but overseas demand at six-month high",
                        "Manufacturing PMI dips in October as output, orders see slow growth")
    assert A.same_event("Spandana Sphoorty reports ₹7.8 crore cyber fraud involving 82 accounts",
                        "India's Spandana Sphoorty Financial reports cyberattack involving its bank account")
    assert not A.same_event("President presents Lalit Kala Akademi Awards to selected artists",
                            "President presents Sangeet Natak Akademi Fellowships and Awards for 2024 and 2025")


# --------------------------------------------------------------------------- #
# Stage 17b wiring
# --------------------------------------------------------------------------- #
def _stage():
    spec = importlib.util.spec_from_file_location("t_stage17b", str(ROOT / "agents" / "17b_auto_sections.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_stage_registered_daily_only_and_non_critical():
    import main
    from pipeline.checkpoints import CONTENT_REWRITERS
    from pipeline.state import STAGE_TO_STATE
    daily = [s for s in main.DAILY_STAGES if s[0] == "17b_auto_sections"]
    assert daily and daily[0][2] is False                  # never fails the run
    names = [s[0] for s in main.DAILY_STAGES]
    assert names.index("17_mcq_validator") < names.index("17b_auto_sections") < names.index("18_pdf_design")
    assert "17b_auto_sections" not in [s[0] for s in main.WEEKLY_STAGES + main.MONTHLY_STAGES]
    assert "17b_auto_sections" in CONTENT_REWRITERS and "17b_auto_sections" in STAGE_TO_STATE


def test_stage_is_fail_soft_and_atomic(tmp_path, monkeypatch):
    mod = _stage()
    monkeypatch.setattr(mod, "ROOT", tmp_path)
    assert mod.run("daily_2026-11-02", "daily") == 0        # no content file -> still 0
    assert mod.run("weekly_2026-11-01", "weekly") == 0      # weekly untouched
    content_dir = tmp_path / "data" / "content"
    content_dir.mkdir(parents=True)
    (content_dir / "daily_2026-11-02.json").write_text(json.dumps({"items": [], "one_liners": []}), encoding="utf-8")
    scored = tmp_path / "data" / "scored"
    scored.mkdir(parents=True)
    (scored / "daily_2026-11-02.json").write_text(json.dumps({"items": _cands()}), encoding="utf-8")
    monkeypatch.setattr(A, "batch_translate", lambda lines, deadline: _fake_hindi(lines, deadline))
    assert mod.run("daily_2026-11-02", "daily") == 0
    data = json.loads((content_dir / "daily_2026-11-02.json").read_text(encoding="utf-8"))
    assert len(data["quick_bites"]) >= A.QB_MIN and data["agri_corner"]["items"]

    def boom(*a, **k):
        raise RuntimeError("unexpected")
    monkeypatch.setattr(A, "build_sections", boom)
    assert mod.run("daily_2026-11-02", "daily") == 0
