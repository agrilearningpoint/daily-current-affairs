"""Weekly/monthly editions built from the published daily editions (synthetic data only).

Covers pipeline/period_builder.py (filtering, dedupe, Untitled drop, MCQ count,
minimum days), scripts/fetch_daily_editions.py (artifact download + weekly
fallback, fail-soft) and src/period_pdf.py (small renders: shaped Hindi, no
'Untitled', answer key, daily header untouched, page-limit compaction).
"""
from __future__ import annotations

import importlib.util
import io
import json
import re
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import period_builder as pb  # noqa: E402
from tests.fixtures.period_sample import build_daily_editions, dates_from  # noqa: E402


def _module(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


WEEK = dates_from("2026-10-26", 7)          # Mon..Sun -> weekly_2026-11-01
MONTH = dates_from("2026-10-01", 31)        # October  -> monthly_2026-11-01


@pytest.fixture(scope="module")
def weekly():
    with pytest.MonkeyPatch.context() as mp:
        mp.delenv("DRY_RUN", raising=False)
        eds = build_daily_editions(WEEK, 3)
        return eds, pb.build_period("weekly", "2026-11-01", eds, WEEK)


@pytest.fixture(scope="module")
def monthly():
    with pytest.MonkeyPatch.context() as mp:
        mp.delenv("DRY_RUN", raising=False)
        eds = build_daily_editions(MONTH[:30], 3)
        return eds, pb.build_period("monthly", "2026-11-01", eds, MONTH)


@pytest.fixture(autouse=True)
def _live_mode(monkeypatch):
    monkeypatch.delenv("DRY_RUN", raising=False)


# --------------------------------------------------------------------------- #
# Builder
# --------------------------------------------------------------------------- #
def test_period_dates_match_collection_windows():
    assert pb.period_dates("weekly", "2026-11-01") == WEEK
    assert pb.period_dates("monthly", "2026-11-01") == MONTH


def test_weekly_keeps_only_verified_devanagari_titled_items(weekly):
    _eds, r = weekly
    items = r["content"]["items"]
    assert items and len(items) <= 25
    for it in items:
        assert it["needs_review"] is False and it["verification_passed"] is True
        assert pb.has_devanagari(it["headline_hi"])
        assert "untitled" not in it["headline_en"].lower()
        assert not it["headline_en"].startswith(">")
    heads = " ".join(i["headline_en"] for i in r["scored"]["items"])
    assert "Unverified claim" not in heads and "Fallback translation story" not in heads
    st = r["stats"]
    assert st["days"] == 7 and st["unverified_dropped"] == 7 * 3  # unverified + English "Hindi" + Untitled
    # the publisher gate (ALP_ALLOW_FALLBACK_TRANSLATION=0) accepts every item
    assert all(i.get("needs_review") is False and i.get("verification_passed") is True for i in items)


def test_untitled_and_empty_headlines_are_dropped():
    good = {"headline_en": "ISRO launches a navigation satellite from Sriharikota",
            "headline_hi": "इसरो ने श्रीहरिकोटा से नेविगेशन उपग्रह प्रक्षेपित किया",
            "needs_review": False, "verification_passed": True}
    assert pb.is_publishable(good)
    for bad in ({"headline_en": "Untitled"}, {"headline_en": ">> "}, {"headline_en": ""},
                {"headline_en": "Untitled story about farmers today"}, {"headline_hi": "Untitled"},
                {"needs_review": None}, {"verification_passed": False}, {"headline_hi": "No Hindi here at all"}):
        assert not pb.is_publishable({**good, **bad}), bad


def test_verification_gate_is_relaxed_only_in_dry_run(monkeypatch):
    eds = build_daily_editions(WEEK[:3], 1)
    live = pb.build_period("weekly", "2026-11-01", eds, WEEK)
    monkeypatch.setenv("DRY_RUN", "1")
    dry = pb.build_period("weekly", "2026-11-01", eds, WEEK)
    assert all(i["needs_review"] is False for i in live["scored"]["items"])
    assert any(i["needs_review"] is True for i in dry["scored"]["items"])
    # English-only "Hindi" and Untitled headlines are dropped even in dry-run.
    assert not any("Fallback translation" in i["headline_en"] or i["headline_en"] == "Untitled"
                   for i in dry["scored"]["items"])


def test_dedupe_by_event_id_and_title_similarity():
    eds = build_daily_editions(WEEK[:3], 2)
    first = eds[0]["content"]["items"][0]
    same_id = dict(first, headline_en=first["headline_en"] + " (repeat)", importance_score=1)
    near = dict(first, event_id="other-id", importance_score=2,
                headline_en=first["headline_en"].replace("launches", "launched"))
    eds[1]["content"]["items"].append(same_id)
    eds[2]["content"]["items"].append(near)
    r = pb.build_period("weekly", "2026-11-01", eds, WEEK)
    clean = pb.clean_headline(first["headline_en"])
    hits = [i for i in r["scored"]["items"] if pb.similar(i["headline_en"], clean) > 0.8]
    assert len(hits) == 1 and hits[0]["importance_score"] == first["importance_score"]
    assert r["stats"]["duplicates_dropped"] >= 2


def test_weekly_mcqs_belong_to_verified_events_and_are_numbered(weekly):
    _eds, r = weekly
    mcqs = r["mcqs"]
    verified = {i["event_id"] for i in r["scored"]["items"]}
    assert 0 < len(mcqs) <= 50
    assert [m["q_num"] for m in mcqs] == list(range(1, len(mcqs) + 1))
    assert all(m["event_id"] in verified for m in mcqs)
    assert all(pb.has_devanagari(m["question_hi"]) for m in mcqs)
    assert len({m["question_en"] for m in mcqs}) == len(mcqs)


def test_weekly_sections_and_static_gk(weekly):
    _eds, r = weekly
    sections = [i["section"] for i in r["content"]["items"]]
    assert set(sections) <= set(pb.SECTIONS)
    assert sections == sorted(sections, key=pb.SECTIONS.index)  # grouped in edition order
    gk_seen = []
    for it in r["content"]["items"]:
        assert 1 <= len(it["summary_pairs"]) <= 3
        # Template sentences shared by every story are filler and never printed.
        assert not any("will run for 3 years" in p["en"] for p in it["summary_pairs"])
        assert len(it["static_gk_pairs"]) <= 3
        gk_seen += [p["en"] for p in it["static_gk_pairs"]]
    # A Static GK fact shared by several stories is printed once in the edition.
    assert gk_seen and len(gk_seen) == len(set(gk_seen))


def test_monthly_counts_and_quick_tables(monthly):
    _eds, r = monthly
    c = r["content"]
    assert 50 <= len(c["items"]) <= 60
    assert len(r["mcqs"]) == 100
    assert c["quick_tables"] and all(t["rows"] for t in c["quick_tables"])
    assert c["missing_days"] == ["2026-10-31"]
    assert c["job"]["type"] == "monthly" and c["job"]["date_display"] == "October 2026"


@pytest.mark.parametrize("kind,days", [("weekly", 2), ("monthly", 9)])
def test_too_few_days_fails_the_period_edition(kind, days):
    dates = WEEK if kind == "weekly" else MONTH
    eds = build_daily_editions(dates[:days], 2)
    with pytest.raises(ValueError, match="daily editions"):
        pb.build_period(kind, "2026-11-01", eds, dates)


def test_build_stage_writes_artifacts(tmp_path, monkeypatch):
    src = tmp_path / "sources"
    src.mkdir()
    for ed in build_daily_editions(WEEK, 2):
        (src / f"daily_{ed['date']}.json").write_text(json.dumps(ed, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv("ALP_PERIOD_SOURCES_DIR", str(src))

    class Ctx:
        job_type, job_date, job_id = "weekly", "2026-11-01", "weekly_2026-11-01"

        def output_path(self, stage):
            return tmp_path / "data" / stage / f"{self.job_id}.json"

    assert pb.build(Ctx()) == 0
    content = json.loads((tmp_path / "data/content/weekly_2026-11-01.json").read_text(encoding="utf-8"))
    mcqs = json.loads((tmp_path / "data/mcq/weekly_2026-11-01.json").read_text(encoding="utf-8"))
    selected = json.loads((tmp_path / "data/selected/weekly_2026-11-01.json").read_text(encoding="utf-8"))
    assert content["job"]["type"] == "weekly" and isinstance(mcqs, list) and mcqs
    assert [i["event_id"] for i in selected["items"]] == [i["event_id"] for i in content["items"]]


# --------------------------------------------------------------------------- #
# Fetch script
# --------------------------------------------------------------------------- #
class _Resp:
    def __init__(self, status, payload=None, content=b""):
        self.status_code, self._payload, self.content = status, payload, content

    def json(self):
        return self._payload


def _zip(files: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in files.items():
            zf.writestr(name, json.dumps(data, ensure_ascii=False))
    return buf.getvalue()


class _FakeSession:
    def __init__(self, runs: dict):
        self.headers, self.runs = {}, runs  # run_id -> zip bytes (None = expired)

    def get(self, url, params=None, timeout=None, allow_redirects=True):
        m = re.search(r"/actions/runs/(\d+)/artifacts$", url)
        if m:
            rid = m.group(1)
            if rid not in self.runs:
                return _Resp(404, {})
            return _Resp(200, {"artifacts": [{"name": "pipeline-checkpoints", "expired": self.runs[rid] is None,
                                              "archive_download_url": f"https://dl/{rid}.zip"}]})
        m = re.search(r"https://dl/(\d+)\.zip", url)
        return _Resp(200, content=self.runs[m.group(1)]) if m else _Resp(404)


def test_fetch_downloads_daily_artifacts_with_weekly_fallback(tmp_path):
    fetch = _module("scripts/fetch_daily_editions.py", "fetch_daily_editions")
    eds = {e["date"]: e for e in build_daily_editions(WEEK, 1)}
    runs, jobs = {}, {}
    for n, d in enumerate(WEEK[:5]):
        rid = str(1000 + n)
        jobs[f"daily_{d}"] = {"status": "success", "checkpoint_run_id": rid}
        runs[rid] = _zip({f"data/content/daily_{d}.json": eds[d]["content"],
                          f"data/mcq/daily_{d}.json": eds[d]["mcqs"]})
    runs["1004"] = None                                         # expired daily artifact ...
    jobs[f"daily_{WEEK[5]}"] = {"status": "failed", "checkpoint_run_id": "1005"}  # never published
    jobs["weekly_2026-11-01"] = {"status": "success", "checkpoint_run_id": "2000"}
    runs["2000"] = _zip({f"data/period_sources/daily_{WEEK[4]}.json": dict(eds[WEEK[4]], job_id="x")})
    gh = fetch.GitHub("o/r", "t", session=_FakeSession(runs))
    out = tmp_path / "ps"
    report = fetch.fetch("weekly", "2026-11-01", gh, jobs, out)
    assert report["found"] == WEEK[:4]
    assert report["from_weekly"] == [WEEK[4]]                  # ... recovered from the weekly copy
    assert set(report["missing"]) == {WEEK[5], WEEK[6]}
    assert report["available"] == 5 and report["min_required"] == 3
    packed = json.loads((out / f"daily_{WEEK[0]}.json").read_text(encoding="utf-8"))
    assert packed["source_run_id"] == "1000" and packed["mcqs"] and packed["content"]["items"]


def test_fetch_is_fail_soft_without_token(monkeypatch, capsys):
    fetch = _module("scripts/fetch_daily_editions.py", "fetch_daily_editions")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    assert fetch.main(["--type", "weekly", "--date", "2026-11-01", "--repo", "o/r"]) == 0
    assert fetch.main(["--type", "weekly", "--date", "2026-11-01", "--repo", "o/r", "--strict"]) == 1


# --------------------------------------------------------------------------- #
# Workflows
# --------------------------------------------------------------------------- #
def _wf(name: str) -> str:
    return (ROOT / ".github/workflows" / name).read_text(encoding="utf-8")


@pytest.mark.parametrize("name,cron,group", [("weekly.yml", "30 2 * * 0", "weekly-pipeline"),
                                             ("monthly.yml", "30 3 1 * *", "monthly-pipeline")])
def test_period_workflows(name, cron, group):
    text = _wf(name)
    kind = name.split(".")[0]
    assert f"cron: '{cron}'" in text
    assert f"group: {group}" in text and "current-affairs-pipeline" not in text
    assert "actions: read" in text
    assert 'ALP_ALLOW_FALLBACK_TRANSLATION: "0"' in text and 'ALP_DISABLE_POLISH: "1"' in text
    fetch_at = text.index(f"scripts/fetch_daily_editions.py --type {kind}")
    assert fetch_at < text.index(f"python main.py --type {kind}")
    assert ('PDF_QA_MAX_PAGES: "100"' in text) == (kind == "monthly")
    assert "agents/22" not in text and "TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}" in text


def test_daily_workflow_keeps_shared_group():
    assert "group: current-affairs-pipeline" in _wf("daily.yml")


def test_qa_page_limits_follow_env(monkeypatch):
    monkeypatch.setenv("PDF_QA_MAX_PAGES", "100")
    qa = _module("agents/19_pdf_qa.py", "pdf_qa_for_period_test")
    assert qa.MAX_PAGES == 100


# --------------------------------------------------------------------------- #
# Rendering (small fixtures: CI pytest runs serially)
# --------------------------------------------------------------------------- #
def _check_pdf(path: str, n_mcq: int):
    import fitz
    qa = _module("agents/19_pdf_qa.py", "pdf_qa_render_check")
    doc = fitz.open(path)
    text = "\n".join(p.get_text() for p in doc)
    report = qa.QAReport(pdf_path=path)
    qa.check_devanagari_shaping(report, doc, text)
    qa.check_editorial_quality(report, text)
    qa.check_glyph_integrity(report, text)
    qa.check_html_leakage(report, text)
    errors = [i for i in report.issues if i.severity == "error"]
    assert not errors, [(i.code, i.message) for i in errors]
    assert len(re.findall(r"\bAns:\s*[A-E]\b", text)) == n_mcq
    return doc, text


def test_weekly_render_small(tmp_path, weekly):
    import src.generate_pdf as G
    _eds, r = weekly
    content = dict(r["content"], items=r["content"]["items"][:8], one_liners=r["content"]["one_liners"][:6])
    content["items"].append(dict(content["items"][0], headline_en="Untitled", event_id="untitled-x"))
    mcqs = r["mcqs"][:6]
    out = G.generate_pdf(content, mcqs, output_path=str(tmp_path / "weekly.pdf"))
    doc, text = _check_pdf(out, len(mcqs))
    assert "Weekly Current Affairs 26 October – 1 November 2026" in text
    assert "WEEKLY CURRENT AFFAIRS" in text and "@agriquizworld" in text and "AGRICULTURE CORNER" in text
    norm = re.sub(r"\s+", " ", text)
    for it in content["items"][:8]:
        assert it["headline_en"][:40] in norm
    assert G.HEADER_LABEL == G.DAILY_HEADER_LABEL == "AGRI LEARNING POINT  |  DAILY CURRENT AFFAIRS"
    links = [l for p in doc for l in p.get_links()]
    assert any(l.get("uri", "").startswith("https://t.me/") for l in links)
    assert sum(1 for l in links if l.get("kind") in (1, 4)) >= 8   # internal index jumps


def test_monthly_render_small_with_tables(tmp_path, monthly, monkeypatch):
    import src.generate_pdf as G
    monkeypatch.setenv("PDF_QA_MAX_PAGES", "100")
    _eds, r = monthly
    tables = [dict(t, rows=t["rows"][:3]) for t in r["content"]["quick_tables"]][:2]
    tables.append({"title_en": "Obituaries", "title_hi": "निधन", "rows": []})  # empty -> skipped
    content = dict(r["content"], items=r["content"]["items"][:6], one_liners=r["content"]["one_liners"][:4],
                   quick_tables=tables)
    mcqs = r["mcqs"][:5]
    out = G.generate_pdf(content, mcqs, output_path=str(tmp_path / "monthly.pdf"))
    _doc, text = _check_pdf(out, len(mcqs))
    assert "Monthly Current Affairs October 2026" in text and "QUICK REVISION TABLES" in text
    assert tables[0]["title_en"] in text and "Obituaries" not in text


def test_period_pdf_compacts_to_page_limit(monkeypatch, tmp_path):
    import src.generate_pdf as G
    import src.period_pdf as P
    calls = []
    monkeypatch.setattr(P, "_build_once", lambda c, m, o, compact, cap: calls.append((compact, cap)) or o)
    pages = iter([52, 47, 44])
    monkeypatch.setattr(G, "_pdf_page_count", lambda _p: next(pages))
    monkeypatch.setenv("PDF_QA_MAX_PAGES", "45")
    content = {"job": {"type": "weekly"}, "one_liners": [{}] * 40}
    P.generate_period_pdf(content, [], output_path=str(tmp_path / "x.pdf"))
    assert calls == [(False, None), (True, None), (True, 20)]


# --------------------------------------------------------------------------- #
# Editorial filters (weekly 2026-11-08 review)
# --------------------------------------------------------------------------- #
def test_one_liner_cleanup_strips_key_tags_and_source_tails():
    from pipeline import period_builder as pb
    assert pb.clean_one_liner("US consortium pushes for $4.4 billion LNG project (Key: $4.4 billion)") == \
        "US consortium pushes for $4.4 billion LNG project"
    assert pb.clean_one_liner("PM's address at the Summit in Delhi - PM India (Key: Delhi PM India)") == \
        "PM's address at the Summit in Delhi"
    assert pb.clean_one_liner("Russian strikes kill 26 (Key: sident Volodymyr Zelenskyy said") == "Russian strikes kill 26"
    assert pb.heading_only("UPI: Transforming India's Payment Landscape")
    assert pb.heading_only("Bankers Books Evidence Act, 2026")
    assert not pb.heading_only("Cabinet approves extension of Jal Jeevan Mission till December 2028")


def _mcq(q, opts, correct="A", **kw):
    return dict(question_en=q, question_hi="प्रश्न", options=opts, correct=correct, **kw)


def test_template_and_giveaway_mcqs_are_rejected():
    from pipeline import period_builder as pb
    opts = ["ICAR", "CACP", "NAFED", "APEDA", "CWC"]
    assert pb._mcq_ok(_mcq("Who chairs X?", opts))
    assert not pb._mcq_ok(_mcq('Which organisation is associated with the news "Cabinet approves MSP"?', opts))
    assert not pb._mcq_ok(_mcq('The news "AIDSO protests" is related to which State / Union Territory?', opts))
    assert not pb._mcq_ok(_mcq("Which state has most MSMEs?",
                               ["Maharashtra leading with one crore MSMEs", "Kerala", "Delhi", "Goa", "Bihar"]))
    assert not pb._mcq_ok(_mcq("Dup?", ["A1", "A1", "B", "C", "D"]))


def test_balance_answers_spreads_letters_and_keeps_answer_text():
    from collections import Counter
    from pipeline import period_builder as pb
    ms = [_mcq(f"Q{i}?", [f"right{i}", "w1", "w2", "w3", "w4"]) for i in range(50)]
    pb.balance_answers(ms, "weekly_2026-11-08")
    counts = Counter(m["correct"] for m in ms)
    assert set(counts) == set("ABCDE") and max(counts.values()) == 10
    assert all(m["options"]["ABCDE".index(m["correct"])] == f"right{i}" for i, m in enumerate(ms))
    again = [_mcq(f"Q{i}?", [f"right{i}", "w1", "w2", "w3", "w4"]) for i in range(50)]
    pb.balance_answers(again, "weekly_2026-11-08")
    assert [m["correct"] for m in again] == [m["correct"] for m in ms]      # deterministic


def test_blocklist_drops_stale_events(tmp_path, monkeypatch):
    from pipeline import period_builder as pb
    path = tmp_path / "bl.json"
    path.write_text('{"headline_patterns": [{"pattern": "MSP for 14 Kharif crops"}]}', encoding="utf-8")
    monkeypatch.setattr(pb, "_BLOCKLIST_PATH", path)
    assert pb._blocklist()[0].search("Cabinet approves higher MSP for 14 Kharif crops for 2026-27")
