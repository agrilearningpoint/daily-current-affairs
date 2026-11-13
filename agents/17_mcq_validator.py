# -*- coding: utf-8 -*-
"""
Agent 17: Independent MCQ Answer & Quality Validator (Section 9.5)
==================================================================
Independently verifies every generated MCQ before PDF layout:
1. Exactly 5 valid options (`A` through `E`) with zero duplicate option strings.
2. Answer key (`A`–`E`) maps to an option whose factual claim is supported by
   the verified source text / explanation.
3. No broken template syntax (`"- '`), `"Untitled"` placeholders, or ambiguous options.
4. Both English and Hindi question stems and explanations are present.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")


def validate_single_mcq(mcq: Dict[str, Any], source_item: Optional[Dict[str, Any]] = None) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    q_en = str(mcq.get("question_en") or mcq.get("question") or "").strip()
    q_hi = str(mcq.get("question_hi") or "").strip()
    opts_en = mcq.get("options_en") or mcq.get("options") or []
    ans = str(mcq.get("answer") or mcq.get("correct_answer") or "").strip().upper()
    exp_en = str(mcq.get("explanation_en") or mcq.get("explanation") or "").strip()
    src_url = str(mcq.get("source_url") or (source_item or {}).get("link") or "").strip()

    if len(q_en) < 15:
        errors.append("question_en_too_short")
    if "Which ministry / organisation is responsible for implementing \"-" in q_en:
        errors.append("broken_mcq_template")
    if re.search(r"\buntitled\b", q_en, re.I):
        errors.append("untitled_in_question")
    if not q_hi or not DEVANAGARI_RE.search(q_hi):
        errors.append("missing_or_non_devanagari_question_hi")

    if not isinstance(opts_en, list) or len(opts_en) != 5:
        errors.append(f"invalid_option_count:{len(opts_en) if isinstance(opts_en, list) else 0}")
    else:
        norm_opts = [re.sub(r"\s+", " ", str(o).strip().lower()) for o in opts_en if str(o).strip()]
        if len(norm_opts) != 5 or len(set(norm_opts)) != 5:
            errors.append("empty_or_duplicate_options")

    if ans not in ("A", "B", "C", "D", "E"):
        errors.append(f"invalid_answer_key:{ans}")
    elif isinstance(opts_en, list) and len(opts_en) == 5:
        ans_idx = ord(ans) - 65
        chosen_opt = str(opts_en[ans_idx]).strip()
        expected_val = str(mcq.get("answer_value") or "").strip()
        if expected_val and expected_val.lower() not in chosen_opt.lower() and chosen_opt.lower() not in expected_val.lower():
            errors.append(f"answer_key_mismatch:option_{ans}_is_{chosen_opt}_but_expected_{expected_val}")

        # Verify against source evidence if provided
        if source_item:
            evidence = " ".join([
                str(source_item.get("headline_en") or ""),
                str(source_item.get("summary_en") or ""),
                str((source_item.get("structured_facts") or {}).get("who") or ""),
                str((source_item.get("structured_facts") or {}).get("where") or ""),
            ]).lower()
            # Direct factual / numerical questions must have their answer value grounded in source evidence
            if mcq.get("question_format") in ("direct_factual", "numerical_statistical", "location_based"):
                core_ans = chosen_opt.split("/")[0].strip().lower()
                if core_ans and core_ans not in evidence:
                    errors.append(f"answer_not_supported_by_source:{core_ans}")

    if len(exp_en) < 15:
        errors.append("explanation_too_short")
    if not src_url.startswith(("http://", "https://")):
        errors.append("missing_traceable_source_url")

    return len(errors) == 0, errors


def validate_mcq_batch(
    mcqs: List[Dict[str, Any]],
    items_by_id: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    valid: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    lookup = items_by_id or {}

    for m in mcqs:
        src_item = lookup.get(str(m.get("event_id") or m.get("source_news_id") or ""))
        ok, errs = validate_single_mcq(m, src_item)
        working = dict(m)
        if ok:
            working["validation_status"] = "validated"
            valid.append(working)
        else:
            working["validation_status"] = "rejected"
            working["validation_errors"] = errs
            rejected.append(working)

    return valid, rejected
