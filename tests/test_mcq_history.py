"""Cross-edition MCQ memory (state/mcq_history.json).

Measured over 18 published editions (2026-10-18 → 11-10, 283 questions): zero
duplicates inside any edition, but 11 question texts recurred across editions —
"Which body recommends the Minimum Support Price (MSP)...?" in 3 of the last 4.
Nothing remembered what a previous edition printed, because ``seen_q`` is a fresh
set on every run.

These tests pin the memory itself (windows, re-run determinism, pruning,
fail-open) and, at the end, the stage-16 wiring: a second edition must not print
the first edition's questions, and must relax the filter rather than come up
short.
"""
import importlib.util
import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from pipeline import mcq_history, state
from pipeline.content import _qkey

ROOT = Path(__file__).resolve().parent.parent


def _hist(**questions):
    return {"version": 1, "updated": "", "questions": dict(questions), "concepts": {}}


def _q(day, type_="who-org", concept_id=None, count=1):
    entry = {"last_seen": day, "count": count, "type": type_, "q": "stem"}
    if concept_id:
        entry["concept_id"] = concept_id
    return entry


TODAY = "2026-11-10"


def _days_ago(n, ref=TODAY):
    return (date.fromisoformat(ref) - timedelta(days=n)).isoformat()


# --------------------------------------------------------------------------- #
# 1. Windows
# --------------------------------------------------------------------------- #
def test_a_question_printed_yesterday_is_skipped_today():
    hist = _hist(mspkey=_q(_days_ago(1), "concept", "msp"))
    assert mcq_history.recent_qkeys(hist, TODAY) == {"mspkey"}


def test_concept_questions_stay_blocked_longer_than_news_ones(monkeypatch):
    monkeypatch.setattr(mcq_history, "DAYS_CONCEPT", 30)
    monkeypatch.setattr(mcq_history, "DAYS_NEWS", 14)
    hist = _hist(concept=_q(_days_ago(20), "concept", "msp"),
                 news=_q(_days_ago(20), "who-org"))
    assert mcq_history.recent_qkeys(hist, TODAY) == {"concept"}
    # …and the news one is blocked inside its own window
    hist2 = _hist(news=_q(_days_ago(5), "who-org"))
    assert mcq_history.recent_qkeys(hist2, TODAY) == {"news"}


def test_entries_outside_their_window_are_forgotten(monkeypatch):
    monkeypatch.setattr(mcq_history, "DAYS_CONCEPT", 30)
    hist = _hist(old=_q(_days_ago(31), "concept", "msp"))
    assert mcq_history.recent_qkeys(hist, TODAY) == set()


def test_a_concept_id_alone_selects_the_concept_window(monkeypatch):
    monkeypatch.setattr(mcq_history, "DAYS_CONCEPT", 30)
    monkeypatch.setattr(mcq_history, "DAYS_NEWS", 1)
    hist = _hist(k=_q(_days_ago(10), "llm-schema", "msp"))
    assert mcq_history.recent_qkeys(hist, TODAY) == {"k"}


# --------------------------------------------------------------------------- #
# 2. Re-run determinism
# --------------------------------------------------------------------------- #
def test_an_edition_does_not_skip_its_own_questions_on_a_re_run():
    """A dispatch with reset=true, or a watchdog retry, must reproduce the
    edition it already built instead of skipping everything it printed."""
    hist = _hist(k=_q(TODAY))
    assert mcq_history.recent_qkeys(hist, TODAY) == set()
    assert mcq_history.recent_qkeys(hist, TODAY, include_today=True) == {"k"}


def test_a_future_dated_entry_is_never_treated_as_recent():
    hist = _hist(k=_q(_days_ago(-3)))
    assert mcq_history.recent_qkeys(hist, TODAY) == set()


# --------------------------------------------------------------------------- #
# 3. record / prune
# --------------------------------------------------------------------------- #
def test_record_folds_an_edition_and_counts_repeats():
    hist = _hist()
    mcqs = [{"question_en": "Which body recommends the MSP?", "type": "concept", "concept_id": "msp"},
            {"question_en": "Which ministry launched the scheme?", "type": "scheme-ministry"}]
    assert mcq_history.record(hist, mcqs, TODAY) == 2
    key = _qkey(mcqs[0]["question_en"])
    entry = hist["questions"][key]
    assert entry["last_seen"] == TODAY and entry["count"] == 1
    assert entry["concept_id"] == "msp" and entry["type"] == "concept"
    assert entry["q"].startswith("Which body")
    # the same question printed again the next day accumulates
    mcq_history.record(hist, mcqs[:1], _days_ago(-1))
    assert hist["questions"][key]["count"] == 2
    assert hist["questions"][key]["last_seen"] == _days_ago(-1)


def test_record_tracks_concept_variants_for_rotation():
    hist = _hist()
    mcq_history.record(hist, [{"question_en": "Q", "type": "concept", "concept_id": "msp",
                              "concept_variant": "v1"}], TODAY)
    assert mcq_history.variant_used_within(hist, "msp", "v1", _days_ago(-1)) is True
    assert mcq_history.variant_used_within(hist, "msp", "v0", _days_ago(-1)) is False


def test_prune_drops_stale_entries_and_respects_the_cap(monkeypatch):
    monkeypatch.setattr(mcq_history, "DAYS_CONCEPT", 30)
    monkeypatch.setattr(mcq_history, "DAYS_NEWS", 14)
    monkeypatch.setattr(mcq_history, "MAX_ENTRIES", 50)
    hist = _hist()
    hist["questions"]["stale"] = _q(_days_ago(200))
    hist["questions"]["fresh"] = _q(_days_ago(1))
    hist["concepts"]["msp"] = {"v0": {"last_seen": _days_ago(200), "count": 1},
                               "v1": {"last_seen": _days_ago(1), "count": 1}}
    for i in range(80):
        hist["questions"][f"bulk{i}"] = _q(_days_ago(i % 5))
    mcq_history.prune(hist, TODAY)
    assert "stale" not in hist["questions"] and "fresh" in hist["questions"]
    assert len(hist["questions"]) <= 50
    assert hist["concepts"]["msp"] == {"v1": {"last_seen": _days_ago(1), "count": 1}}


# --------------------------------------------------------------------------- #
# 4. Fail-open and the kill switch
# --------------------------------------------------------------------------- #
def test_a_missing_or_corrupt_history_file_is_an_empty_history(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "ROOT", tmp_path)
    assert mcq_history.load() == mcq_history.empty_history()
    path = tmp_path / "state" / "mcq_history.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not json", encoding="utf-8")
    assert mcq_history.load()["questions"] == {}
    path.write_text(json.dumps({"questions": "nope", "concepts": 3}), encoding="utf-8")
    loaded = mcq_history.load()
    assert loaded["questions"] == {} and loaded["concepts"] == {}


def test_save_and_load_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "ROOT", tmp_path)
    hist = mcq_history.load()
    mcq_history.record(hist, [{"question_en": "Which body decides the repo rate?",
                               "type": "concept", "concept_id": "repo"}], TODAY)
    assert mcq_history.save(hist) is True
    again = mcq_history.load()
    assert again["questions"] == hist["questions"]
    assert again["updated"]


def test_the_kill_switch_restores_the_old_behaviour(monkeypatch):
    monkeypatch.setattr(mcq_history, "ENABLED", False)
    hist = _hist(k=_q(_days_ago(1)))
    assert mcq_history.load() == mcq_history.empty_history()
    assert mcq_history.recent_qkeys(hist, TODAY) == set()
    assert mcq_history.record(hist, [{"question_en": "Q"}], TODAY) == 0
    assert mcq_history.save(hist) is False
    assert mcq_history.should_relax(set(), 0, 5, 0) is False


def test_saving_never_raises_when_the_state_dir_is_unwritable(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "ROOT", tmp_path / "missing")
    blocker = tmp_path / "missing"
    blocker.write_text("not a directory", encoding="utf-8")
    assert mcq_history.save(_hist(k=_q(TODAY))) is False


# --------------------------------------------------------------------------- #
# 5. The relax decision (the safety property)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("recent,built,target,mcqs,expected", [
    (set(), 5, 10, 5, False),          # no history -> nothing to relax
    ({"a"}, 10, 10, 10, False),        # complete edition keeps its fresh questions
    ({"a"}, 9, 10, 9, True),           # a story lost its question unit
    ({"a"}, 10, 10, 7, True),          # below the stage's own min(8, target) floor
    ({"a"}, 3, 3, 3, False),           # small edition, still complete
    ({"a"}, 3, 3, 2, True),            # …but short of its floor
])
def test_should_relax(recent, built, target, mcqs, expected):
    assert mcq_history.should_relax(recent, built, target, mcqs) is expected


def test_repeats_against_reports_cross_edition_duplicates():
    hist = _hist()
    stem = "Which body recommends the Minimum Support Price (MSP)?"
    hist["questions"][_qkey(stem)] = _q(_days_ago(2), "concept", "msp", count=3)
    found = mcq_history.repeats_against(hist, [{"question_en": stem, "type": "concept"}], TODAY)
    assert len(found) == 1
    assert found[0]["count"] == 3 and found[0]["concept_id"] == "msp"
    assert found[0]["last_seen"] == _days_ago(2)


# --------------------------------------------------------------------------- #
# 6. State synchronisation between CI runs
# --------------------------------------------------------------------------- #
def _sync_state():
    spec = importlib.util.spec_from_file_location("sync_state", ROOT / "scripts" / "sync_state.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_the_history_file_is_part_of_state_sync():
    """GitHub Actions runners are ephemeral: an unsynchronised history would be
    rewritten from scratch every run and the feature would do nothing."""
    assert "state/mcq_history.json" in _sync_state().FILES


def test_state_sync_unions_histories_keeping_the_newer_entry():
    mod = _sync_state()
    local = {"version": 1, "updated": "2026-11-11T01:00:00+05:30",
             "questions": {"abc": _q("2026-11-11", "concept", "msp")}, "concepts": {}}
    remote = {"version": 1, "updated": "2026-11-10T01:00:00+05:30",
              "questions": {"abc": _q("2026-11-08", "concept", "msp", count=2),
                            "xyz": _q("2026-11-09")},
              "concepts": {}}
    merged = mod.merge_document("state/mcq_history.json", local, remote)
    assert merged["questions"]["abc"]["last_seen"] == "2026-11-11"   # newer wins
    assert merged["questions"]["xyz"]["last_seen"] == "2026-11-09"   # remote-only kept
    assert merged["updated"] == "2026-11-11T01:00:00+05:30"


def test_the_committed_history_file_is_a_valid_seeded_history():
    """state/mcq_history.json ships pre-seeded from published editions via
    scripts/backfill_mcq_history.py (an empty memory let the MSP question
    reprint on 2026-11-11).  Pin the schema load() relies on, not emptiness."""
    import re as _re
    path = ROOT / "state" / "mcq_history.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["version"] == 1
    assert isinstance(data.get("questions"), dict)
    assert isinstance(data.get("concepts"), dict)
    for key, entry in data["questions"].items():
        assert isinstance(entry, dict) and int(entry.get("count", 0)) >= 1
        assert _re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(entry.get("last_seen", ""))), key
    for cid, variants in data["concepts"].items():
        assert isinstance(variants, dict)
        for vid, entry in variants.items():
            assert _re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(entry.get("last_seen", ""))), (cid, vid)
    assert mcq_history.load(path)["version"] == 1


# --------------------------------------------------------------------------- #
# 7. Stage 16 wiring — two editions in a row
# --------------------------------------------------------------------------- #
def _load_stage16():
    spec = importlib.util.spec_from_file_location(
        "stage16_mcq_generator", ROOT / "agents" / "16_mcq_generator.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _candidate(event_id, stem, type_="who-org"):
    return {"type": type_, "event_id": event_id, "question_en": stem,
            "question_hi": stem, "options": ["a", "b", "c", "d"], "correct": "A",
            "explanation_en": "e", "explanation_hi": "e"}


@pytest.fixture
def stage16(tmp_path, monkeypatch):
    """Stage 16 in a sandbox root with the MCQ validators stubbed out.

    The stubs keep the test on the wiring under test — which fingerprints the
    stage feeds into ``first_valid`` — instead of re-testing MCQ validation.
    """
    from pipeline import content, mcq_builder, mcq_quality, mcq_schema

    monkeypatch.setattr(state, "ROOT", tmp_path)
    monkeypatch.setattr(state, "CONTENT_DIR", tmp_path / "data" / "content")
    monkeypatch.setattr(state, "MCQ_DIR", tmp_path / "data" / "mcq")
    (tmp_path / "data" / "content").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "mcq").mkdir(parents=True, exist_ok=True)
    (tmp_path / "state").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(mcq_schema, "llm_mode_enabled", lambda: False)
    monkeypatch.setattr(content, "validate_mcqs", lambda mcqs, items: (list(mcqs), []))
    monkeypatch.setattr(content, "renumber_mcqs", lambda mcqs: None)
    monkeypatch.setattr(content, "refresh_content_summaries", lambda c: None)
    monkeypatch.setattr(content, "_build_pools", lambda items: {})
    monkeypatch.setattr(content, "_evidence_text", lambda ci: "")
    monkeypatch.setattr(mcq_quality, "balance_answer_positions", lambda mcqs, d: mcqs)
    monkeypatch.setattr(mcq_quality, "letter_spread", lambda mcqs: {})

    seen_seeds = []

    def fake_first_valid(cands, ci, seen_q):
        seen_seeds.append(set(seen_q))
        for c in cands:
            if content._qkey(c.get("question_en")) not in seen_q:
                return c, []
        return None, ["every candidate was printed recently"]

    monkeypatch.setattr(mcq_builder, "first_valid", fake_first_valid)
    monkeypatch.setattr(mcq_builder, "candidates_for_item",
                        lambda ci, ev, pools, all_items, llm=None, variant_ctx=None: ci["_candidates"])

    mod = _load_stage16()
    return mod, seen_seeds


def _run_stage(mod, job_id, items):
    content_path = state.data_path(state.CONTENT_DIR, job_id)
    state.write_json_atomic(content_path, {"job": {"date": job_id.split("_", 1)[1]},
                                           "items": items, "reserve_items": []})
    ctx = mod.Agent(job_id, "daily", {}).run()
    return ctx, json.loads(state.data_path(state.MCQ_DIR, job_id).read_text(encoding="utf-8"))


def test_the_next_edition_does_not_reprint_the_previous_one(stage16):
    mod, seen_seeds = stage16
    stems = {1: ["Which body recommends the MSP?", "Which commission reviews crop costs?",
                 "Who announces notified crop prices?"],
             2: ["Which body decides the repo rate?", "Which committee sets the policy rate?",
                 "Who regulates monetary policy?"]}

    def items_for():
        return [{"event_id": i, "headline_en": f"story {i}", "_candidates":
                 [_candidate(i, s) for s in stems[i]]} for i in (1, 2)]

    _ctx1, mcq1 = _run_stage(mod, "daily_2026-11-07", items_for())
    first = {m["question_en"] for m in mcq1}
    assert first, "the first edition printed nothing"
    assert seen_seeds[0] == set(), "a first edition has no history to skip"

    # the history now knows what edition one printed
    assert mcq_history.recent_qkeys(mcq_history.load(), "2026-11-08")

    _ctx2, mcq2 = _run_stage(mod, "daily_2026-11-08", items_for())
    second = {m["question_en"] for m in mcq2}
    assert second and not (first & second), f"edition two reprinted {first & second}"
    # …and the fingerprints edition one printed were handed to the validator as skips
    assert {_qkey(q) for q in first} <= seen_seeds[-1]


def test_a_short_edition_relaxes_the_filter_instead_of_failing(stage16):
    """When every candidate was printed recently, the stage must rebuild without
    the history filter: a stale-free edition is worth less than a complete one."""
    mod, _seen = stage16
    only = [{"event_id": 1, "headline_en": "story 1", "_candidates": [_candidate(1, "Which body recommends the MSP?")]},
            {"event_id": 2, "headline_en": "story 2", "_candidates": [_candidate(2, "Which body decides the repo rate?")]}]
    import copy
    _ctx1, mcq1 = _run_stage(mod, "daily_2026-11-07", copy.deepcopy(only))
    ctx2, mcq2 = _run_stage(mod, "daily_2026-11-08", copy.deepcopy(only))
    assert ctx2.get("mcq_history_relaxed") is True
    assert {m["question_en"] for m in mcq2} == {m["question_en"] for m in mcq1}
    assert ctx2["mcq_history_recent"] == 2


def test_history_recording_survives_a_broken_state_file(stage16, monkeypatch):
    """Fail-open: a history problem must never take the edition down."""
    mod, _seen = stage16
    monkeypatch.setattr(mcq_history, "record", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    items = [{"event_id": 1, "headline_en": "story 1",
              "_candidates": [_candidate(1, "Which body recommends the MSP?")]}]
    ctx, mcqs = _run_stage(mod, "daily_2026-11-07", items)
    assert mcqs and ctx.get("stage_failed") is None


# --------------------------------------------------------------------------- #
# 8. published flag - same-date re-runs must not reprint what students saw
# --------------------------------------------------------------------------- #
def test_same_day_unpublished_entries_are_still_ignored():
    hist = {"version": 1, "questions": {"k": {"count": 1, "last_seen": TODAY, "type": "llm-schema"}},
            "concepts": {}}
    assert mcq_history.recent_qkeys(hist, TODAY) == set()
    assert mcq_history.recent_qkeys(hist, TODAY, include_today=True) == {"k"}


def test_mark_published_makes_same_day_questions_recent():
    hist = {"version": 1,
            "questions": {"k": {"count": 1, "last_seen": TODAY, "type": "llm-schema"},
                          "old": {"count": 1,
                                  "last_seen": (date.fromisoformat(TODAY) - timedelta(days=3)).isoformat(),
                                  "type": "concept"}},
            "concepts": {"msp": {"v0": {"count": 1, "last_seen": TODAY}}}}
    assert mcq_history.mark_published(hist, TODAY) == 2
    assert hist["questions"]["k"]["published"] is True
    assert hist["concepts"]["msp"]["v0"]["published"] is True
    assert "k" in mcq_history.recent_qkeys(hist, TODAY)
    assert mcq_history.variant_used_within(hist, "msp", "v0", TODAY) is True
    # idempotent
    assert mcq_history.mark_published(hist, TODAY) == 0
    # other dates untouched
    assert hist["questions"]["old"].get("published") is None


def test_record_resets_published_for_new_drafts():
    hist = {"version": 1, "questions": {}, "concepts": {}}
    mcq_history.record(hist, [{"question_en": "Which body recommends the Minimum Support Price (MSP)?"}],
                       edition_date=TODAY)
    entry = next(iter(hist["questions"].values()))
    assert entry["published"] is False
    assert mcq_history.recent_qkeys(hist, TODAY) == set()
