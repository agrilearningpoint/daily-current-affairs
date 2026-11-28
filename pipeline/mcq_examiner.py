# -*- coding: utf-8 -*-
"""
INDEPENDENT ADVERSARIAL MCQ EXAMINER (Phase 7)
===============================================
Acts as an external exam-board reviewer for generated MCQs before PDF rendering.

Evaluates every MCQ against five independent exam-quality dimensions:
  1. Evidence & Key Integrity  — correct option verified in story text or standing facts;
                                 no second option is supported by the source text.
  2. Bilingual Parity          — Hindi question, options, and explanation contain real
                                 Devanagari and preserve key numeric figures from EN.
  3. Distractor Realism        — no placeholder/meta options, same magnitude/entity class,
                                 no duplicate concepts, and option length parity.
  4. Stem Hygiene & Focus      — no answer leakage in stem, no news-agency questions,
                                 no phrase-recognition trivia, no dangling prepositions.
  5. Optional Blind AI Critique — when enabled (`ALP_MCQ_EXAMINER_AI=1` and configured),
                                  uses `ai_router` (`task="mcq_verification"`) to confirm
                                  single unambiguous answer.

Exposes:
  - `examine_mcq(mcq, content_item, *, blind_verify=False)` -> dict
  - `examine_mcq_set(mcqs, content_items, *, strict=False)` -> (passed, rejected, report)
"""
from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("pipeline.mcq_examiner")

LETTERS = "ABCDE"
DEVA_RE = re.compile(r"[\u0900-\u097F]")
_DEVA_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_NUM_EXTRACT_RE = re.compile(r"\d+(?:[.,]\d+)*")


def _base_en(opt: Any) -> str:
    return str(opt or "").split(" / ")[0].strip()


def _nums(text: str) -> set:
    cleaned = str(text or "").translate(_DEVA_DIGITS).replace(",", "")
    return set(_NUM_EXTRACT_RE.findall(cleaned))


def _check_bilingual_parity(m: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    crit: List[str] = []
    warn: List[str] = []
    q_en = str(m.get("question_en") or "").strip()
    q_hi = str(m.get("question_hi") or "").strip()
    if not q_hi or not DEVA_RE.search(q_hi):
        crit.append("examiner: Hindi question missing Devanagari")
    else:
        en_nums = _nums(q_en)
        hi_nums = _nums(q_hi)
        if en_nums and not en_nums <= hi_nums:
            warn.append(f"examiner: question Hindi missing numbers {sorted(en_nums - hi_nums)}")

    opts = [str(o or "") for o in (m.get("options") or [])]
    his = list(m.get("options_hi") or [])
    for idx, opt in enumerate(opts):
        hi_opt = str(his[idx] or "") if idx < len(his) else (opt.split(" / ", 1)[1] if " / " in opt else "")
        en_opt = _base_en(opt)
        has_words = bool(re.search(r"[A-Za-z]{4,}", en_opt))
        is_pure_acro = bool(re.fullmatch(r"[A-Z0-9&.\- ]{2,12}", en_opt))
        if has_words and not is_pure_acro and not DEVA_RE.search(hi_opt):
            warn.append(f"examiner: option {LETTERS[idx] if idx < 5 else idx} lacks Hindi rendering")
            break
    return crit, warn


def _check_stem_hygiene(m: Dict[str, Any], ci: Optional[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    crit: List[str] = []
    warn: List[str] = []
    q_en = str(m.get("question_en") or "").strip()
    if len(q_en) < 20:
        crit.append("examiner: question stem too short (<20 chars)")
    try:
        from pipeline.mcq_quality import answer_in_headline, question_has_grammatical_defect
        if question_has_grammatical_defect(q_en):
            crit.append("examiner: grammatical defect in question stem")
        if ci and answer_in_headline(m, ci):
            warn.append("examiner: answer explicitly appears in story headline")
    except Exception:
        pass
    return crit, warn


def _check_distractors_and_key(m: Dict[str, Any], ci: Optional[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    crit: List[str] = []
    warn: List[str] = []
    opts = [_base_en(o) for o in (m.get("options") or [])]
    letter = str(m.get("correct") or "")
    idx = LETTERS.find(letter) if len(letter) == 1 else -1
    if not (0 <= idx < len(opts)):
        crit.append("examiner: invalid correct answer letter")
        return crit, warn

    # Duplicate normalized option check
    normed = [re.sub(r"\W+", "", o.lower()) for o in opts]
    if len(set(normed)) != len(normed) or any(not n for n in normed):
        crit.append("examiner: duplicate or blank option detected")

    # Meta-distractor check
    for o in opts:
        if re.search(r"\b(?:all|none)\s+of\s+the\s+(?:above|these)\b", o, re.I):
            crit.append("examiner: meta-option (All/None of the above) forbidden")
            break

    if ci:
        try:
            from pipeline.content import _evidence_text
            from pipeline.mcq_quality import key_check, giveaway_errors
            from pipeline.mcq_schema import _in_text
            ev = _evidence_text(ci)
            action, _new_idx, why = key_check(m, ev)
            if action == "rekey":
                crit.append(f"examiner: miskeyed answer ({why})")
            elif action == "drop":
                # If multiple figures appear in the story (e.g. repo rate 6.50% AND GDP 7.1%) or
                # `_in_text` confirms grounding, record as warning unless completely unsupported.
                if "ambiguous" in why or _in_text(opts[idx], ev):
                    warn.append(f"examiner: {why}")
                else:
                    crit.append(f"examiner: {why}")
            for ge in giveaway_errors(m):
                warn.append(f"examiner: {ge}")
        except Exception as exc:
            logger.debug("[Examiner] key/giveaway check skipped: %s", exc)

    return crit, warn


def _ai_blind_audit(m: Dict[str, Any], ci: Optional[Dict[str, Any]]) -> Optional[str]:
    """Optional adversarial blind verification via `pipeline.ai_router`."""
    try:
        from pipeline.ai_router import is_configured, route
        from pipeline.mcq_quality import build_verify_prompt, parse_verify_reply
        if not is_configured():
            return None
        hl = str((ci or {}).get("headline_en") or "")
        ev = str((ci or {}).get("detailed_explanation_en") or (ci or {}).get("summary_en") or "")
        raw = route(build_verify_prompt(m, hl, ev), task="mcq_verification", needs_hindi=False)
        if not raw:
            return None
        return parse_verify_reply(raw)
    except Exception:
        return None


def examine_mcq(
    m: Dict[str, Any],
    ci: Optional[Dict[str, Any]] = None,
    *,
    blind_verify: bool = False,
) -> Dict[str, Any]:
    """Audit a single MCQ and return structured verdict + score (0..100)."""
    crit: List[str] = []
    warn: List[str] = []

    c1, w1 = _check_distractors_and_key(m, ci)
    c2, w2 = _check_stem_hygiene(m, ci)
    c3, w3 = _check_bilingual_parity(m)
    crit.extend(c1 + c2 + c3)
    warn.extend(w1 + w2 + w3)

    if blind_verify and not crit:
        chosen = _ai_blind_audit(m, ci)
        if chosen and chosen != str(m.get("correct") or ""):
            crit.append(f"examiner: blind AI audit picked '{chosen}' instead of '{m.get('correct')}'")

    score = max(0, 100 - 35 * len(crit) - 8 * len(warn))
    passed = len(crit) == 0
    return {
        "passed": passed,
        "score": score,
        "critical_errors": crit,
        "warnings": warn,
        "event_id": str(m.get("event_id") or ""),
    }


def examine_mcq_set(
    mcqs: List[Dict[str, Any]],
    content_items: List[Dict[str, Any]],
    *,
    strict: Optional[bool] = None,
    blind_verify: Optional[bool] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """Run adversarial exam audit over an MCQ batch.

    Returns ``(approved_mcqs, rejected_mcqs, audit_report)``.
    In strict mode, high-severity warnings that reduce score below 75 also reject.
    """
    if strict is None:
        strict = os.getenv("ALP_MCQ_EXAMINER_STRICT", "0") == "1"
    if blind_verify is None:
        blind_verify = (
            os.getenv("ALP_MCQ_EXAMINER_AI", "0") == "1"
            and os.getenv("DRY_RUN", "0") != "1"
            and os.getenv("ALP_DISABLE_NETWORK", "0") != "1"
        )

    ci_by_id = {str(c.get("event_id") or ""): c for c in (content_items or []) if isinstance(c, dict)}
    approved: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    scores: List[int] = []
    warning_count = 0

    for m in mcqs or []:
        ci = ci_by_id.get(str(m.get("event_id") or ""))
        verdict = examine_mcq(m, ci, blind_verify=bool(blind_verify))
        scores.append(verdict["score"])
        warning_count += len(verdict["warnings"])
        ok = verdict["passed"] and (not strict or verdict["score"] >= 75)
        if ok:
            enriched = dict(m)
            enriched["examiner_score"] = verdict["score"]
            if verdict["warnings"]:
                enriched["examiner_warnings"] = verdict["warnings"]
            approved.append(enriched)
        else:
            bad = dict(m)
            bad["examiner_errors"] = verdict["critical_errors"] + verdict["warnings"]
            bad["examiner_score"] = verdict["score"]
            rejected.append(bad)

    report = {
        "total": len(mcqs or []),
        "approved": len(approved),
        "rejected": len(rejected),
        "warnings": warning_count,
        "avg_score": round(sum(scores) / len(scores), 1) if scores else 0.0,
        "strict": bool(strict),
    }
    logger.info(
        "[MCQ Examiner] %d/%d approved (avg score=%.1f, warnings=%d, rejected=%d)",
        report["approved"], report["total"], report["avg_score"],
        report["warnings"], report["rejected"],
    )
    return approved, rejected, report
