# -*- coding: utf-8 -*-
"""
Cross-edition MCQ memory (state/mcq_history.json)
=================================================
In-run dedup has always worked — an edition never repeats a question inside
itself.  What nothing remembered is what a *previous* edition printed, because
``seen_q`` is a fresh set on every run (agents/16_mcq_generator.py).  Measured
over 18 published editions (2026-10-18 → 11-10, 283 questions):

  * "Which body recommends the Minimum Support Price (MSP) ...?" appeared in
    3 of the last 4 editions (11-07, 11-08, 11-10);
  * 11 question texts recurred across editions in total;
  * zero duplicates within any single edition.

The eight ``KNOWN_MAPPINGS`` concept entries emit one fixed question whenever
their trigger matches the story evidence, so any topic that stays in the news
(MSP in an agriculture edition) reprints the same question daily.  Distractor
*order* is salted per event, which makes the repeat look like a new question
while the stem and the option set are identical.

This module records what each edition printed and answers "which questions were
used recently", so stage 16 can prefer a fresh one.  It only ever *prefers*: the
stage rebuilds without the filter when using it would leave the edition below
its target, so a sparse news day can never fail a run.

File shape::

    {
      "version": 1,
      "updated": "2026-11-10T21:04:00+05:30",
      "questions": {
        "<qkey>": {"last_seen": "2026-11-10", "count": 3, "type": "concept",
                   "concept_id": "msp", "q": "Which body recommends ..."}
      },
      "concepts": {"msp": {"v1": {"last_seen": "2026-11-10", "count": 1}}}
    }

``last_seen`` is one of the timestamp fields scripts/sync_state.py already
understands, so two concurrent runs union their histories instead of clobbering
each other.  ``qkey`` is ``pipeline.content._qkey`` — the same fingerprint the
in-run dedup uses — so a history hit can be dropped straight into ``seen_q``.

Env switches:
    ALP_MCQ_HISTORY=0                   # disable entirely (old behaviour)
    ALP_MCQ_HISTORY_DAYS_CONCEPT=30     # window for concept/static questions
    ALP_MCQ_HISTORY_DAYS_NEWS=14        # window for news-derived questions
    ALP_MCQ_HISTORY_MAX_ENTRIES=4000    # hard cap on remembered questions
"""
from __future__ import annotations

import logging
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

logger = logging.getLogger(__name__)

ENABLED = os.getenv("ALP_MCQ_HISTORY", "1") == "1"
DAYS_CONCEPT = max(0, int(os.getenv("ALP_MCQ_HISTORY_DAYS_CONCEPT", "30")))
DAYS_NEWS = max(0, int(os.getenv("ALP_MCQ_HISTORY_DAYS_NEWS", "14")))
MAX_ENTRIES = max(50, int(os.getenv("ALP_MCQ_HISTORY_MAX_ENTRIES", "4000")))
VERSION = 1

# Entries are pruned once they are older than the widest window plus this grace
# period, so a widening of the window still finds yesterday's edition.
_GRACE_DAYS = 7


def state_dir() -> Path:
    from pipeline.state import ROOT
    return ROOT / "state"


def history_path() -> Path:
    return state_dir() / "mcq_history.json"


def empty_history() -> Dict[str, Any]:
    return {"version": VERSION, "updated": "", "questions": {}, "concepts": {}}


def _today(edition_date: Optional[str] = None) -> date:
    """The edition's own date when it carries one, else today in Asia/Kolkata."""
    from pipeline.state import TZ
    if edition_date:
        try:
            return date.fromisoformat(str(edition_date)[:10])
        except ValueError:
            pass
    return datetime.now(TZ).date()


def _parse(day: Any) -> Optional[date]:
    try:
        return date.fromisoformat(str(day)[:10])
    except (TypeError, ValueError):
        return None


def load(path: Optional[Path] = None) -> Dict[str, Any]:
    """Read the history; a missing or corrupt file is an empty history.

    Fail-open by design: this file only improves variety, so nothing in it may
    ever be able to stop an edition.
    """
    from pipeline.state import read_json
    hist = empty_history() if not ENABLED else read_json(path or history_path(), None)
    if not isinstance(hist, dict):
        logger.warning("[MCQ history] unreadable history file — starting empty")
        return empty_history()
    hist.setdefault("version", VERSION)
    hist.setdefault("updated", "")
    for key in ("questions", "concepts"):
        if not isinstance(hist.get(key), dict):
            hist[key] = {}
    return hist


def save(history: Dict[str, Any], path: Optional[Path] = None) -> bool:
    from pipeline.state import now_iso, write_json_atomic
    if not ENABLED:
        return False
    target = path or history_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        history["version"] = VERSION
        history["updated"] = now_iso()
        write_json_atomic(target, history)
        return True
    except Exception as exc:                    # never fail the stage over memory
        logger.warning("[MCQ history] could not write %s: %s", target, exc)
        return False


def days_for(entry: Dict[str, Any]) -> int:
    """Concept/static questions stay fresh longer than news-derived ones."""
    kind = str(entry.get("type") or "").lower()
    if kind == "concept" or entry.get("concept_id"):
        return DAYS_CONCEPT
    return DAYS_NEWS


def recent_qkeys(history: Dict[str, Any], edition_date: Optional[str] = None,
                 include_today: bool = False) -> Set[str]:
    """Fingerprints printed within their own window — seed for ``seen_q``.

    Entries dated *today* are skipped unless ``include_today``: a re-run of the
    same date (dispatch with reset=true, watchdog retry) must reproduce the
    edition it already built instead of skipping its own questions.  Once the
    edition has actually been published (stage 22 marks it), its questions are
    no longer "our own draft" - students have seen them - so a same-date
    re-run avoids them like any other recent repeat.
    """
    if not ENABLED or not isinstance(history, dict):
        return set()
    today = _today(edition_date)
    out: Set[str] = set()
    for qkey, entry in (history.get("questions") or {}).items():
        if not isinstance(entry, dict):
            continue
        seen = _parse(entry.get("last_seen"))
        if seen is None:
            continue
        if not include_today and seen >= today and not entry.get("published"):
            continue
        age = (today - seen).days
        if 0 <= age < days_for(entry):
            out.add(str(qkey))
    return out


def should_relax(recent: Set[str], stories_built: int, target: int, mcqs_built: int) -> bool:
    """True when skipping recent repeats left the edition short.

    Stage 16 then rebuilds the assignment with an empty seed — the pre-history
    behaviour — because a stale-free edition is worth less than a complete one.
    The floors mirror the stage's own: every selected story wants a question
    unit, and the stage fails below ``min(8, target)`` validated MCQs.
    """
    if not recent:
        return False
    return stories_built < target or mcqs_built < min(8, target)


def concept_uses(history: Dict[str, Any], concept_id: str) -> Dict[str, Any]:
    """Per-variant use log for one concept (``{"v1": {"last_seen": ..., "count": n}}``)."""
    if not isinstance(history, dict):
        return {}
    uses = (history.get("concepts") or {}).get(str(concept_id))
    return dict(uses) if isinstance(uses, dict) else {}


def variant_used_within(history: Dict[str, Any], concept_id: str, variant_id: str,
                        edition_date: Optional[str] = None) -> bool:
    """True when this concept phrasing was already printed inside the concept window."""
    if not ENABLED:
        return False
    today = _today(edition_date)
    entry = concept_uses(history, concept_id).get(str(variant_id))
    if not isinstance(entry, dict):
        return False
    seen = _parse(entry.get("last_seen"))
    if seen is None:
        return False
    if seen >= today and not entry.get("published"):
        return False  # this run's own draft, not something students saw
    return 0 <= (today - seen).days < DAYS_CONCEPT


def record(history: Dict[str, Any], mcqs: Iterable[Dict[str, Any]],
           edition_date: Optional[str] = None) -> int:
    """Fold one edition's validated MCQs into the history; returns entries touched."""
    from pipeline.content import _qkey
    if not ENABLED or not isinstance(history, dict):
        return 0
    day = _today(edition_date).isoformat()
    questions = history.setdefault("questions", {})
    concepts = history.setdefault("concepts", {})
    touched = 0
    for m in mcqs or []:
        if not isinstance(m, dict):
            continue
        key = _qkey(m.get("question_en"))
        if not key:
            continue
        entry = questions.get(key)
        if not isinstance(entry, dict):
            entry = {"count": 0}
        entry["last_seen"] = day
        entry["count"] = int(entry.get("count") or 0) + 1
        entry["type"] = str(m.get("type") or "")[:24]
        if m.get("concept_id"):
            entry["concept_id"] = str(m.get("concept_id"))[:32]
        else:
            entry.pop("concept_id", None)
        entry["q"] = str(m.get("question_en") or "")[:110]
        entry["published"] = False  # stage 22 flips this once students see it
        questions[key] = entry
        cid = str(m.get("concept_id") or "")
        vid = m.get("concept_variant")
        if cid and vid is not None:
            per = concepts.setdefault(cid, {})
            ventry = per.get(str(vid)) if isinstance(per.get(str(vid)), dict) else {"count": 0}
            ventry["last_seen"] = day
            ventry["count"] = int(ventry.get("count") or 0) + 1
            ventry["published"] = False
            per[str(vid)] = ventry
        touched += 1
    prune(history, day)
    return touched


def mark_published(history: Dict[str, Any], edition_date: Optional[str] = None) -> int:
    """Flag everything an edition printed as seen-by-students.

    Called by stage 22 after a successful Telegram publish.  Without it a
    same-date re-run (reset=true) would treat the published questions as its
    own draft and reprint them - on 2026-11-11 that meant the MSP concept
    question surviving its own correction run.
    """
    if not ENABLED or not isinstance(history, dict):
        return 0
    day = _today(edition_date).isoformat()
    touched = 0
    for entry in (history.get("questions") or {}).values():
        if isinstance(entry, dict) and entry.get("last_seen") == day and not entry.get("published"):
            entry["published"] = True
            touched += 1
    for variants in (history.get("concepts") or {}).values():
        if not isinstance(variants, dict):
            continue
        for ventry in variants.values():
            if isinstance(ventry, dict) and ventry.get("last_seen") == day and not ventry.get("published"):
                ventry["published"] = True
                touched += 1
    return touched


def prune(history: Dict[str, Any], edition_date: Optional[str] = None) -> int:
    """Drop stale entries and enforce MAX_ENTRIES (oldest first). Returns removed count."""
    if not isinstance(history, dict):
        return 0
    today = _today(edition_date)
    horizon = today - timedelta(days=max(DAYS_CONCEPT, DAYS_NEWS) + _GRACE_DAYS)
    questions = history.get("questions") or {}
    stale = [k for k, v in questions.items()
             if not isinstance(v, dict) or (_parse(v.get("last_seen")) or horizon) < horizon]
    for k in stale:
        questions.pop(k, None)
    if len(questions) > MAX_ENTRIES:
        oldest = sorted(questions.items(),
                        key=lambda kv: str((kv[1] or {}).get("last_seen") or ""))
        for k, _ in oldest[:len(questions) - MAX_ENTRIES]:
            questions.pop(k, None)
    # concept use logs age out with the same horizon
    concepts = history.get("concepts") or {}
    for cid in list(concepts):
        per = concepts.get(cid)
        if not isinstance(per, dict):
            concepts.pop(cid, None)
            continue
        for vid in list(per):
            entry = per.get(vid)
            seen = _parse((entry or {}).get("last_seen")) if isinstance(entry, dict) else None
            if seen is None or seen < horizon:
                per.pop(vid, None)
        if not per:
            concepts.pop(cid, None)
    history["questions"] = questions
    history["concepts"] = concepts
    return len(stale)


def stats(history: Dict[str, Any], edition_date: Optional[str] = None) -> Dict[str, Any]:
    """Small summary for the run context / logs."""
    questions = (history or {}).get("questions") or {}
    repeated = [v for v in questions.values() if isinstance(v, dict) and int(v.get("count") or 0) > 1]
    return {
        "enabled": ENABLED,
        "remembered": len(questions),
        "recent": len(recent_qkeys(history, edition_date)),
        "printed_more_than_once": len(repeated),
        "days_concept": DAYS_CONCEPT,
        "days_news": DAYS_NEWS,
    }


def repeats_against(history: Dict[str, Any], mcqs: Iterable[Dict[str, Any]],
                    edition_date: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
    """Questions in ``mcqs`` that a previous edition already printed (QA reporting)."""
    from pipeline.content import _qkey
    recent = recent_qkeys(history, edition_date)
    questions = (history or {}).get("questions") or {}
    out = []
    for m in mcqs or []:
        if not isinstance(m, dict):
            continue
        key = _qkey(m.get("question_en"))
        if key and key in recent:
            entry = questions.get(key) or {}
            out.append({
                "q": str(m.get("question_en") or "")[:110],
                "last_seen": entry.get("last_seen"),
                "count": int(entry.get("count") or 0),
                "concept_id": entry.get("concept_id"),
                "type": m.get("type"),
            })
        if len(out) >= limit:
            break
    return out
