# -*- coding: utf-8 -*-
"""
Per-item LLM MCQ schema (reference "Exam Genius" format).

One LLM call per selected news item returns a single JSON object:

    {
      "mcq": {
        "question": {"en": "...", "hi": "..."},
        "options": [{"en": "...", "hi": "..."}, x5],
        "correct": "A".."E"
      },
      "explanation": [{"en": "...", "hi": "..."}, x4-5],
      "static_gk": [{"label_en": "...", "value_en": "...", "label_hi": "...", "value_hi": "..."}, x4-6],
      "theme": "Loans | MoU | Appointments | ...",
      "one_liner": {"en": "...", "hi": "..."}
    }

* ``normalize_item_mcq`` (stage 16) turns that into the flat MCQ dict the rest
  of the pipeline already understands (question_en/hi, options, correct,
  explanation_en/hi) plus the richer fields the PDF renders (options_hi,
  explanation_pairs, static_gk, theme, one_liner).
* ``schema_errors`` (stage 17, via content.validate_mcqs) is fail-closed:
  exactly 5 unique options, Hindi present for question/options/explanation,
  correct answer present in the item's own source text, and no
  "None of the above".

Nothing here invents facts: an item whose LLM answer fails validation simply
falls back to the deterministic generator in pipeline.content.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

LETTERS = "ABCDE"
DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
NONE_OF_ABOVE_RE = re.compile(r"none of (the )?(above|these)|all of (the )?(above|these)|उपर्युक्त में से कोई नहीं|इनमें से कोई नहीं", re.I)
MIN_EXPLANATION, MAX_EXPLANATION = 4, 5
MIN_STATIC_GK, MAX_STATIC_GK = 4, 6

PROMPT_TEMPLATE = """You write one bilingual (English + Hindi) competitive-exam MCQ for an Indian current-affairs booklet.
Use ONLY facts stated in NEWS. Do not add facts that are not in NEWS, except Static GK about the
institutions/schemes named in NEWS: timeless facts only (headquarters, capital, establishment/founding year,
founding Act, parent ministry) that you are certain of.
Static GK must NEVER name a current officeholder (chairman, governor, minister, chief, DG, CEO, MD, head)
from memory: name one only if NEWS states it or it is listed under VERIFIED OFFICEHOLDERS below, exactly as listed.
Never present a year before {stale_year} as "current" or "latest".
VERIFIED OFFICEHOLDERS (as of {facts_date}):
{officeholders}

NEWS (headline): {headline}
NEWS (text): {text}

Rules:
- question: one clear question; it must NOT contain the answer. Do NOT ask for a word or number that is in the
  headline, and do not copy the headline's key noun into the question. Prefer a static/conceptual fact about the
  scheme or body (who recommends/implements/regulates it) or a detail from the NEWS text that the headline lacks.
- distractors: real, related entities of the same kind (other real ministries, bodies, States, schemes). Never
  invent person names. Never give a person a post (minister, governor, chairman...) unless VERIFIED OFFICEHOLDERS
  lists them in it. Percentages must be plausible (never above 100% for a share).
- options: exactly 5, all of the same kind (all names, all numbers, ...), all different. The correct option text
  must be copied exactly from NEWS (or be the well-known body for a static fact, e.g. MSP -> CACP). Never use "None of the above" / "All of the above".
- Hindi: natural exam-style Devanagari. Keep numbers, ₹ amounts, acronyms and proper nouns accurate.
- explanation: 4 or 5 full sentences, each with its Hindi translation.
- static_gk: 4 to 6 short label/value facts in English and Hindi.
- theme: 1-3 words grouping this story with similar ones (e.g. "Loans", "MoU", "Appointments", "Awards", "Agriculture").
- one_liner: one exam-ready sentence summarising the story, English and Hindi.

Respond with ONLY this JSON (no markdown):
{{"mcq": {{"question": {{"en": "", "hi": ""}}, "options": [{{"en": "", "hi": ""}}, {{"en": "", "hi": ""}}, {{"en": "", "hi": ""}}, {{"en": "", "hi": ""}}, {{"en": "", "hi": ""}}], "correct": "A"}},
 "explanation": [{{"en": "", "hi": ""}}],
 "static_gk": [{{"label_en": "", "value_en": "", "label_hi": "", "value_hi": ""}}],
 "theme": "",
 "one_liner": {{"en": "", "hi": ""}}}}"""


def _ws(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _is_hi(text: Any) -> bool:
    return bool(DEVANAGARI_RE.search(str(text or "")))


def _officeholder_context(text: str) -> Tuple[str, str, int]:
    """(verified officeholder lines, facts date, stale-year cutoff) for the prompt. Never raises."""
    import datetime as _dt
    year = _dt.date.today().year
    m = re.match(r"(\d{4})-", os.getenv("ALP_JOB_DATE", "") or "")
    if m:
        year = int(m.group(1))
    try:
        from agents.static_gk_validator import FACTS_PATH, facts_for_prompt
        lines = facts_for_prompt(text)
        date = json.loads(FACTS_PATH.read_text(encoding="utf-8")).get("updated", "")
    except Exception:
        lines, date = "", ""
    return (lines or "- (none relevant: do not name any officeholder)"), (date or "n/a"), year - 1


def build_prompt(item: Dict[str, Any], source_text: str) -> str:
    headline = re.sub(r"^\s*>>\s*", "", _ws(item.get("headline_en")))
    text = _ws(source_text)[:2500]
    officeholders, facts_date, stale_year = _officeholder_context(f"{headline} {text}")
    return PROMPT_TEMPLATE.format(headline=headline, text=text, officeholders=officeholders,
                                  facts_date=facts_date, stale_year=stale_year)


def parse_llm_json(raw: Any) -> Optional[Dict[str, Any]]:
    """Extract the first JSON object from an LLM reply (tolerates ```json fences)."""
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    txt = str(raw).strip()
    txt = re.sub(r"^```(?:json)?\s*|\s*```$", "", txt)
    start = txt.find("{")
    end = txt.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(txt[start:end + 1])
    except (ValueError, TypeError):
        return None
    return data if isinstance(data, dict) else None


def _pair(obj: Any) -> Tuple[str, str]:
    if isinstance(obj, dict):
        return _ws(obj.get("en")), _ws(obj.get("hi"))
    if isinstance(obj, (list, tuple)) and obj:
        return _ws(obj[0]), _ws(obj[1] if len(obj) > 1 else "")
    return _ws(obj), ""


def normalize_item_mcq(data: Dict[str, Any], item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Stage 16: LLM JSON -> pipeline MCQ dict (flat legacy keys + reference-format keys)."""
    if not isinstance(data, dict):
        return None
    mcq = data.get("mcq") if isinstance(data.get("mcq"), dict) else data
    q_en, q_hi = _pair(mcq.get("question"))
    if not q_en:
        q_en, q_hi = _ws(mcq.get("question_en")), _ws(mcq.get("question_hi"))
    options = [_pair(o) for o in (mcq.get("options") or [])]
    correct = _ws(mcq.get("correct")).upper()[:1]
    if correct not in LETTERS and correct.isdigit():
        idx = int(correct) - 1
        correct = LETTERS[idx] if 0 <= idx < len(LETTERS) else ""

    expl = [_pair(p) for p in (data.get("explanation") or mcq.get("explanation") or [])]
    expl = [(e, h) for e, h in expl if e][:MAX_EXPLANATION]

    gk: List[Dict[str, str]] = []
    for g in data.get("static_gk") or []:
        if not isinstance(g, dict):
            continue
        row = {k: _ws(g.get(k)) for k in ("label_en", "value_en", "label_hi", "value_hi")}
        if row["label_en"] and row["value_en"]:
            gk.append(row)
    gk = gk[:MAX_STATIC_GK]
    if len(gk) < MIN_STATIC_GK:
        # Too few LLM static-GK rows is not a reason to lose the whole question:
        # the PDF then falls back to the story's own verified static GK pairs.
        gk = []

    ol_en, ol_hi = _pair(data.get("one_liner"))
    theme = _ws(data.get("theme"))[:40]

    return {
        "type": "llm-schema",
        "event_id": item.get("event_id", ""),
        "question_en": q_en,
        "question_hi": q_hi,
        "options": [e for e, _ in options],
        "options_hi": [h for _, h in options],
        "correct": correct,
        "explanation_en": " ".join(e for e, _ in expl),
        "explanation_hi": " ".join(h for _, h in expl),
        "explanation_pairs": [{"en": e, "hi": h} for e, h in expl],
        "static_gk": gk,
        "theme": theme,
        "one_liner": {"en": ol_en, "hi": ol_hi},
        "exam_point": ol_en[:120],
        "source_url": (item.get("source") or {}).get("url", ""),
    }


def _in_text(needle: str, text: str) -> bool:
    if not needle or not text:
        return False
    n, t = needle.lower(), text.lower()
    if n in t:
        return True
    # Numbers may be written 1,250 vs 1250 in the source.
    return bool(re.search(r"\d", n)) and n.replace(",", "") in t.replace(",", "")


def _option_hi_ok(en: str, hi: str) -> bool:
    """Hindi option text must be Devanagari, unless the option is a bare number/acronym (₹6,000, DRDO)."""
    if not hi:
        return False
    if _is_hi(hi):
        return True
    return hi.strip() == en.strip() and not re.search(r"\b[a-z]{4,}\b", en)


def _mapped(m: Dict[str, Any], answer: str) -> bool:
    from pipeline.mcq_quality import known_mapping_supports
    return known_mapping_supports(str(m.get("question_en") or ""), answer)


def schema_errors(m: Dict[str, Any], source_text: str) -> List[str]:
    """Stage 17 checks for MCQs that carry the reference-format fields."""
    errs: List[str] = []
    opts = [str(o or "").strip() for o in (m.get("options") or [])]
    his = [str(h or "").strip() for h in (m.get("options_hi") or [])]
    if len(opts) != 5:
        errs.append("schema: exactly 5 options required")
    if len({o.lower() for o in opts}) != len(opts) or any(not o for o in opts):
        errs.append("schema: options must be unique and non-empty")
    if any(NONE_OF_ABOVE_RE.search(o) for o in opts + his):
        errs.append("schema: 'None/All of the above' not allowed")
    if not _is_hi(m.get("question_hi")):
        errs.append("schema: Hindi question missing")
    if len(his) != len(opts) or not all(_option_hi_ok(o, h) for o, h in zip(opts, his)):
        errs.append("schema: Hindi text missing for one or more options")
    letter = str(m.get("correct") or "")
    if len(letter) != 1 or letter not in LETTERS[:len(opts)]:
        errs.append("schema: correct letter out of range")
    elif not _in_text(opts[LETTERS.index(letter)], source_text) and not _mapped(m, opts[LETTERS.index(letter)]):
        errs.append("schema: correct answer not found in source text")
    pairs = m.get("explanation_pairs") or []
    if not (MIN_EXPLANATION <= len(pairs) <= MAX_EXPLANATION):
        errs.append("schema: explanation needs 4-5 sentences")
    if any(not _is_hi(p.get("hi")) for p in pairs if isinstance(p, dict)):
        errs.append("schema: explanation sentence without Hindi")
    gk = m.get("static_gk") or []
    if gk and not (MIN_STATIC_GK <= len(gk) <= MAX_STATIC_GK):
        errs.append("schema: static GK needs 4-6 pairs")
    if any(not (_is_hi(g.get("label_hi")) and g.get("value_hi")) for g in gk):
        errs.append("schema: static GK pair without Hindi")
    return errs


def _self_verify(route: Callable[..., Any], m: Dict[str, Any], item: Dict[str, Any], src: str) -> str:
    """Letter the model picks for its own question ('' when unavailable)."""
    from pipeline.mcq_quality import build_verify_prompt, parse_verify_reply
    try:
        raw = route(build_verify_prompt(m, item.get("headline_en") or "", src), task="mcq", needs_hindi=False)
    except Exception as exc:
        logger.info("[MCQ schema] %s: self-check unavailable: %s", item.get("event_id"), exc)
        return ""
    return parse_verify_reply(raw)


def llm_mode_enabled() -> bool:
    return os.getenv("ALP_MCQ_MODE", "llm").strip().lower() not in ("deterministic", "off", "0")


def generate_llm_mcqs(
    content_items: List[Dict[str, Any]],
    source_text_fn: Callable[[Dict[str, Any]], str],
    route: Optional[Callable[..., Any]] = None,
    attempts: Optional[int] = None,
    extra_check: Optional[Callable[[Dict[str, Any], Dict[str, Any]], List[str]]] = None,
    verify: Optional[bool] = None,
) -> Dict[str, Dict[str, Any]]:
    """Return {event_id: validated MCQ}.  Items that fail are simply absent (caller falls back).

    Every attempt is checked with ``schema_errors`` and, when given, ``extra_check``
    (stage 16 passes the generic fail-closed validator, so an MCQ accepted here is
    never rejected later).  A rejected attempt is retried with the rejection
    reasons appended to the prompt, which fixes most near-misses.

    An accepted MCQ is then self-verified (the model answers its own question
    blind).  On a key mismatch the item is regenerated once; a second mismatch
    drops the LLM question (the caller falls back to templates).  An unusable
    verifier reply does not block the MCQ: the deterministic checks still apply.
    """
    if verify is None:
        verify = os.getenv("ALP_MCQ_SELF_VERIFY", "1").strip().lower() not in ("0", "off", "false", "no")
    if attempts is None:
        try:
            attempts = max(1, int(os.getenv("ALP_MCQ_LLM_ATTEMPTS", "3")))
        except ValueError:
            attempts = 3
    if route is None:
        try:
            from pipeline.ai_router import is_configured, route as _route
        except ImportError:
            return {}
        if not is_configured():
            return {}
        route = _route
    out: Dict[str, Dict[str, Any]] = {}
    for item in content_items or []:
        if not isinstance(item, dict):
            continue
        src = source_text_fn(item)
        prompt = build_prompt(item, src)
        feedback = ""
        max_tries, regenerated, attempt = attempts, False, -1
        while attempt + 1 < max_tries:
            attempt += 1
            ask = prompt
            if attempt:
                ask = prompt + "\nReturn valid JSON only."
                if feedback:
                    ask += ("\nYour previous answer was rejected because: " + feedback +
                            ". Fix exactly these problems. Distractors must NOT appear anywhere in NEWS; "
                            "the question must not contain the answer.")
            try:
                raw = route(ask, task="mcq", needs_hindi=False)
            except Exception as exc:  # provider errors -> deterministic fallback
                logger.warning("[MCQ schema] %s: route failed: %s", item.get("event_id"), exc)
                break
            if raw is None:
                # Every provider failed / is cooling down / the stage AI budget is
                # used: retrying the same item at once only hammers them.
                logger.info("[MCQ schema] %s: no AI reply; using deterministic templates", item.get("event_id"))
                break
            m = normalize_item_mcq(parse_llm_json(raw) or {}, item)
            if not m:
                feedback = "the reply was not the requested JSON object"
                continue
            errs = schema_errors(m, src)
            if not errs and extra_check is not None:
                try:
                    errs = list(extra_check(m, item) or [])
                except Exception as exc:
                    errs = [f"validator error: {exc}"]
            if not errs and verify:
                chosen = _self_verify(route, m, item, src)
                if chosen and chosen != m.get("correct"):
                    logger.info("[MCQ schema] %s self-check picked %s, key is %s", item.get("event_id"),
                                chosen, m.get("correct"))
                    if regenerated:
                        break  # second mismatch: drop the LLM question
                    regenerated = True
                    max_tries = max(max_tries, attempt + 2)
                    feedback = (f"a blind self-check answered {chosen} but the key was {m.get('correct')}; "
                                "key the option that NEWS (or the well-known static fact) actually supports")
                    continue
            if not errs:
                out[str(item.get("event_id", ""))] = m
                break
            feedback = "; ".join(errs[:4])
            logger.info("[MCQ schema] %s attempt %d rejected: %s", item.get("event_id"), attempt + 1, errs)
    logger.info("[MCQ schema] %d/%d items got a validated LLM MCQ", len(out), len(content_items or []))
    return out
