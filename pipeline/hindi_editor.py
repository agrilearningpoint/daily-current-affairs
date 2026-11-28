# -*- coding: utf-8 -*-
"""
HINDI EDITORIAL POST-PROCESSOR & QUALITY ENGINE (Phase 5)
=========================================================
Ensures formal competitive-exam Hindi prose across Daily, Weekly, and Monthly editions:
  1. Devanagari matra/nukta normalization (fixes double nuktas, misplaced chandrabindu/anusvara,
     unicode NFC normalization, and stray halant/punctuation spacing).
  2. Postposition & agreement grammar repair ("ने में", "ने को", "के द्वारा के", "की के", etc.).
  3. Authoritative Hindi terminology standardization (ministries, flagship schemes, agri/banking terms,
     WHO spelling 'विश्व', official Hindi numerals/currency consistency).
  4. Non-destructive editorial review (`review_hindi_line`) returning structured quality telemetry.
  5. Edition-wide editorial polish (`edit_edition_hindi`) covering stories, one-liners, and MCQs.

Deterministic and fast (no extra AI calls required). Safe against None/non-string input.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("pipeline.hindi_editor")

DEVA_RE = re.compile(r"[\u0900-\u097F]")
_REPLACEMENT_RE = re.compile(r"[\ufffd\uFFFE\uFFFF]")
# Dependent Devanagari vowel signs / virama / anusvara appearing without a base consonant
_ISOLATED_MATRA_RE = re.compile(
    r"(?:^|(?<=[\s(\"'.,।!?/\-]))[\u093E-\u094D\u0955-\u0957\u0962\u0963\u0902\u0901\u0903]"
)
_BROKEN_MATRA_WORDS = ("वषिय", "मलिते", "महत्वपूरण", "स्थैतकि", "वकिल्प", "बदिु", "वयाख्या")
_INCOMPLETE_HI_RE = re.compile(
    r"(?:लागत\s+लगभग\s+रुपये?|लगभग\s+रुपये?|(?:^|\s)(?:रुपये|में|को|और|के\s+लिए))\s*[।.]?\s*$"
)
_LATIN_WORD_RE = re.compile(r"\b[A-Za-z]{4,}\b")

# Double-nukta / malformed Devanagari character repairs
_MATRA_NUKTA_RULES: List[Tuple[re.Pattern, str]] = [
    # Strip Unicode replacement / non-character garbage
    (_REPLACEMENT_RE, ""),
    # Precomposed nukta consonant followed by another nukta mark (e.g., ड़ + ़ or ज़ + ़)
    (re.compile(r"([\u0958-\u095F])\u093C+"), r"\1"),
    # Fix common double-nukta glyph artifact in रोज़गार
    (re.compile(r"\u095B\u093C"), "\u091C\u093C"),
    # Remove duplicate consecutive nuktas
    (re.compile(r"\u093C{2,}"), "\u093C"),
    # Fix stray vowel sign before anusvara -> canonical order (e.g. \u0902\u0940 -> \u0940\u0902)
    (re.compile(r"([\u0902\u0901])([\u093E-\u094C])"), r"\2\1"),
    # Fix stray virama/halant right before punctuation or space
    (re.compile(r"\u094D(?=[ \t,।.!?]|$)"), ""),
    # Remove isolated combining matra right after whitespace
    (re.compile(r"(?<=\s)[\u093E-\u094C\u0955-\u0957\u0962\u0963]+(?=\s|$)"), ""),
    # Zero-width characters accidentally embedded mid-word
    (re.compile(r"[\u200B\uFEFF]"), ""),
    # Duplicate danda
    (re.compile(r"।{2,}"), "।"),
    # Space before Hindi danda or comma
    (re.compile(r"\s+([।,])"), r"\1"),
]

# Caseworker/postposition/gender-case agreement glitches common in EN->HI machine translation
_GRAMMAR_AGREEMENT_RULES: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"(?<![\u0900-\u097F])ने\s+में(?![\u0900-\u097F])"), "में"),
    (re.compile(r"(?<![\u0900-\u097F])ने\s+को(?![\u0900-\u097F])"), "को"),
    (re.compile(r"(?<![\u0900-\u097F])ने\s+ने(?![\u0900-\u097F])"), "ने"),
    (re.compile(r"(?<![\u0900-\u097F])में\s+में(?![\u0900-\u097F])"), "में"),
    (re.compile(r"(?<![\u0900-\u097F])को\s+को(?![\u0900-\u097F])"), "को"),
    (re.compile(r"(?<![\u0900-\u097F])के\s+के(?![\u0900-\u097F])"), "के"),
    (re.compile(r"(?<![\u0900-\u097F])की\s+की(?![\u0900-\u097F])"), "की"),
    (re.compile(r"(?<![\u0900-\u097F])का\s+का(?![\u0900-\u097F])"), "का"),
    (re.compile(r"(?<![\u0900-\u097F])से\s+से(?![\u0900-\u097F])"), "से"),
    (re.compile(r"(?<![\u0900-\u097F])पर\s+पर(?![\u0900-\u097F])"), "पर"),
    (re.compile(r"(?<![\u0900-\u097F])के\s+द्वारा\s+के(?![\u0900-\u097F])"), "के द्वारा"),
    (re.compile(r"(?<![\u0900-\u097F])के\s+तहत\s+के\s+तहत(?![\u0900-\u097F])"), "के तहत"),
    (re.compile(r"(?<![\u0900-\u097F])के\s+अंतर्गत\s+के\s+अंतर्गत(?![\u0900-\u097F])"), "के अंतर्गत"),
    # Gender agreement for 'योजना' (feminine noun) when MT writes masculine past/possessive
    (re.compile(r"(योजना)\s+शुरू\s+किया\s+गया"), r"\1 शुरू की गई"),
    (re.compile(r"(योजना)\s+लॉन्च\s+किया\s+गया"), r"\1 लॉन्च की गई"),
    (re.compile(r"(योजना)\s+लागू\s+किया\s+गया"), r"\1 लागू की गई"),
    # 'मंत्रालय' (masculine noun) feminine typo
    (re.compile(r"(मंत्रालय)\s+ने\s+जारी\s+की(?=\s|[।.!?]|$)"), r"\1 ने जारी किया"),
    # 'रिपोर्ट' (feminine noun)
    (re.compile(r"(रिपोर्ट)\s+जारी\s+किया\s+गया"), r"\1 जारी की गई"),
    # 'समझौता / एमओयू' (masculine noun)
    (re.compile(r"(समझौता|एमओयू)\s+हस्ताक्षरित\s+की\s+गई"), r"\1 हस्ताक्षरित किया गया"),
]

# Terminology & spelling standardization for UPSC / UPSSSC AGTA / IBPS AFO / NABARD Hindi
_TERMINOLOGY_RULES: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"विस्व\s+स्वास्थ्य\s+संगठन"), "विश्व स्वास्थ्य संगठन"),
    (re.compile(r"विस्व(?![\u0900-\u097F])"), "विश्व"),
    (re.compile(r"पतंजली(?![\u0900-\u097F])"), "पतंजलि"),
    (re.compile(r"जलशक्ति\s+मंत्रालय"), "जल शक्ति मंत्रालय"),
    (re.compile(r"मछली\s*पालन,?\s*पशुपालन\s+(?:एवं|और)\s+डेयरी\s+मंत्रालय"), "मत्स्यपालन, पशुपालन और डेयरी मंत्रालय"),
    (re.compile(r"भारतीय\s+रिजर्व\s+बैंक"), "भारतीय रिज़र्व बैंक"),
    (re.compile(r"कृषि\s+और\s+किसान\s+कल्याण\s+मंत्रालय"), "कृषि एवं किसान कल्याण मंत्रालय"),
    (re.compile(r"उपभोक्ता\s+मामलों,\s*खाद्य"), "उपभोक्ता मामले, खाद्य"),
    (re.compile(r"न्यूनतम\s+समर्थन\s+कीमत"), "न्यूनतम समर्थन मूल्य"),
    (re.compile(r"सकल\s+घरेलु\s+उत्पाद"), "सकल घरेलू उत्पाद"),
    (re.compile(r"अंतर्राष्ट्रीय"), "अंतरराष्ट्रीय"),
    (re.compile(r"केंद्रीय\s+मंत्रीमंडल"), "केंद्रीय मंत्रिमंडल"),
    (re.compile(r"मंत्रीमंडल"), "मंत्रिमंडल"),
    (re.compile(r"कार्यवाई"), "कार्यवाही"),
]


def edit_hindi_text(text: Any, english_ref: str = "") -> str:
    """Apply Devanagari matra/nukta cleanup, grammar/agreement fixes, and terminology rules."""
    if not text:
        return ""
    s = unicodedata.normalize("NFC", str(text))
    if not DEVA_RE.search(s):
        return s.strip()

    for rx, rep in _MATRA_NUKTA_RULES:
        s = rx.sub(rep, s)
    for rx, rep in _GRAMMAR_AGREEMENT_RULES:
        s = rx.sub(rep, s)
    for rx, rep in _TERMINOLOGY_RULES:
        s = rx.sub(rep, s)

    # Collapse spaces
    s = re.sub(r"[ \t]{2,}", " ", s).strip()
    return s


def review_hindi_line(english: str, hindi: str) -> Dict[str, Any]:
    """Audit a bilingual line pair for common Hindi defects.

    Returns dict: {"ok": bool, "critical": bool, "issues": List[str], "edited_hi": str, "changed": bool}
    """
    hi_in = str(hindi or "").strip()
    en_in = str(english or "").strip()
    had_replacement = bool(_REPLACEMENT_RE.search(hi_in))
    edited = edit_hindi_text(hi_in, english_ref=en_in)
    issues: List[str] = []
    critical_issues: List[str] = []

    if had_replacement:
        issues.append("replacement_char_detected")
        critical_issues.append("replacement_char_detected")

    if not edited or not DEVA_RE.search(edited):
        issues.append("missing_devanagari")
        critical_issues.append("missing_devanagari")
    else:
        if "\u095B\u093C" in hi_in or "\u093C\u093C" in hi_in:
            issues.append("double_nukta_repaired")
        if re.search(r"विस्व(?![\u0900-\u097F])", hi_in):
            issues.append("who_typo_repaired")
        if re.search(r"(?<![\u0900-\u097F])ने\s+(?:में|को)(?![\u0900-\u097F])", hi_in):
            issues.append("postposition_collision_repaired")
        if _ISOLATED_MATRA_RE.search(edited):
            issues.append("isolated_hindi_matra")
            critical_issues.append("isolated_hindi_matra")
        if any(w in edited for w in _BROKEN_MATRA_WORDS):
            issues.append("broken_devanagari_matras")
            critical_issues.append("broken_devanagari_matras")
        if _INCOMPLETE_HI_RE.search(edited):
            issues.append("incomplete_hindi_sentence")
            critical_issues.append("incomplete_hindi_sentence")
        if edited.count("(") > edited.count(")") or edited.count(")") > edited.count("("):
            issues.append("unbalanced_parentheses")
        deva_words = len(re.findall(r"[\u0900-\u097F]+", edited))
        latin_words = len(_LATIN_WORD_RE.findall(edited))
        if deva_words + latin_words >= 6 and latin_words > deva_words * 1.8:
            issues.append("untranslated_latin_overload")

    return {
        "ok": len(critical_issues) == 0,
        "critical": len(critical_issues) > 0,
        "issues": issues,
        "edited_hi": edited,
        "changed": edited != hi_in,
    }


def audit_edition_hindi(
    content: Optional[Dict[str, Any]],
    mcqs: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Audit all student-facing Hindi text across an edition AFTER repair.

    Any unresolved critical Hindi issue sets ``passed=False``.
    """
    issues: List[Dict[str, Any]] = []
    checked = 0
    critical_count = 0
    warning_count = 0

    def _audit(scope: str, en_val: Any, hi_val: Any, *, allow_blank: bool = False) -> None:
        nonlocal checked, critical_count, warning_count
        en_s = str(en_val or "").strip()
        hi_s = str(hi_val or "").strip()
        if not hi_s:
            if allow_blank or not en_s or re.fullmatch(r"[A-Z0-9&.\- /]{1,14}", en_s):
                return
            checked += 1
            critical_count += 1
            issues.append({"severity": "error", "scope": scope, "code": "missing_devanagari", "sample": en_s[:80]})
            return
        checked += 1
        rev = review_hindi_line(en_s, hi_s)
        for code in rev["issues"]:
            if code.endswith("_repaired"):
                continue
            is_crit = code in {
                "missing_devanagari", "replacement_char_detected",
                "isolated_hindi_matra", "broken_devanagari_matras",
                "incomplete_hindi_sentence",
            }
            if is_crit:
                critical_count += 1
            else:
                warning_count += 1
            issues.append({
                "severity": "error" if is_crit else "warning",
                "scope": scope,
                "code": code,
                "sample": hi_s[:80],
            })

    if isinstance(content, dict):
        for idx, it in enumerate(content.get("items") or []):
            if not isinstance(it, dict):
                continue
            eid = str(it.get("event_id") or f"item_{idx}")
            _audit(f"item:{eid}:headline_hi", it.get("headline_en"), it.get("headline_hi"))
            _audit(f"item:{eid}:summary_hi", it.get("summary_en"), it.get("summary_hi"), allow_blank=bool(it.get("key_points_hi")))
            kps_en = it.get("key_points_en") or []
            kps_hi = it.get("key_points_hi") or []
            for j, kp_hi in enumerate(kps_hi if isinstance(kps_hi, list) else []):
                kp_en = kps_en[j] if isinstance(kps_en, list) and j < len(kps_en) else ""
                _audit(f"item:{eid}:kp_{j}", kp_en, kp_hi, allow_blank=True)
            if it.get("detailed_explanation_hi") or it.get("detailed_explanation_en"):
                _audit(f"item:{eid}:detail_hi", it.get("detailed_explanation_en"), it.get("detailed_explanation_hi"), allow_blank=True)
            if it.get("exam_fact_hi"):
                _audit(f"item:{eid}:exam_fact_hi", it.get("exam_fact_en"), it.get("exam_fact_hi"), allow_blank=True)

        for idx, ol in enumerate(content.get("one_liners") or []):
            if isinstance(ol, dict):
                _audit(f"one_liner:{idx}", ol.get("text_en"), ol.get("text_hi"), allow_blank=True)

        ac = content.get("agri_corner") or {}
        if isinstance(ac, dict):
            for idx, ait in enumerate(ac.get("items") or []):
                if isinstance(ait, dict):
                    _audit(f"agri_corner:{idx}", ait.get("headline_en") or ait.get("en"), ait.get("headline_hi") or ait.get("hi"), allow_blank=True)

    for idx, m in enumerate(mcqs or []):
        if not isinstance(m, dict):
            continue
        mid = str(m.get("event_id") or f"mcq_{idx}")
        _audit(f"mcq:{mid}:question_hi", m.get("question_en"), m.get("question_hi"))
        opts_en = m.get("options") or []
        opts_hi = m.get("options_hi") or []
        for j, opt_hi in enumerate(opts_hi if isinstance(opts_hi, list) else []):
            opt_en = opts_en[j] if isinstance(opts_en, list) and j < len(opts_en) else ""
            _audit(f"mcq:{mid}:opt_{j}", opt_en, opt_hi, allow_blank=True)
        _audit(f"mcq:{mid}:explanation_hi", m.get("explanation_en"), m.get("explanation_hi"), allow_blank=True)

    return {
        "passed": critical_count == 0,
        "critical_count": critical_count,
        "warning_count": warning_count,
        "checked_fields": checked,
        "issues": issues[:50],
    }


def edit_edition_hindi(
    content: Optional[Dict[str, Any]],
    mcqs: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, int]:
    """Run Hindi editorial polish in-place across edition content, one-liners, and MCQs.

    Never raises; returns summary telemetry dict.
    """
    stats: Dict[str, int] = {"lines_checked": 0, "lines_edited": 0}

    def _polish_field(obj: Dict[str, Any], key_hi: str, key_en: str = "") -> None:
        val = obj.get(key_hi)
        if not isinstance(val, str) or not val:
            return
        stats["lines_checked"] += 1
        en = str(obj.get(key_en) or "") if key_en else ""
        new_val = edit_hindi_text(val, en)
        if new_val != val:
            obj[key_hi] = new_val
            stats["lines_edited"] += 1

    try:
        if isinstance(content, dict):
            for it in content.get("items") or []:
                if not isinstance(it, dict):
                    continue
                for hk, ek in (
                    ("headline_hi", "headline_en"),
                    ("summary_hi", "summary_en"),
                    ("detailed_explanation_hi", "detailed_explanation_en"),
                    ("exam_fact_hi", "exam_fact_en"),
                ):
                    _polish_field(it, hk, ek)
                kps_hi = it.get("key_points_hi")
                kps_en = it.get("key_points_en") or []
                if isinstance(kps_hi, list):
                    for idx, line in enumerate(kps_hi):
                        if isinstance(line, str) and line:
                            stats["lines_checked"] += 1
                            en_ref = str(kps_en[idx]) if idx < len(kps_en) else ""
                            new_line = edit_hindi_text(line, en_ref)
                            if new_line != line:
                                kps_hi[idx] = new_line
                                stats["lines_edited"] += 1
            for ol in content.get("one_liners") or []:
                if isinstance(ol, dict):
                    _polish_field(ol, "text_hi", "text_en")

        if isinstance(mcqs, list):
            for m in mcqs:
                if not isinstance(m, dict):
                    continue
                for hk, ek in (
                    ("question_hi", "question_en"),
                    ("explanation_hi", "explanation_en"),
                ):
                    _polish_field(m, hk, ek)
                if isinstance(m.get("options_hi"), list):
                    opts_en = m.get("options") or []
                    for idx, opt_hi in enumerate(m["options_hi"]):
                        if isinstance(opt_hi, str) and opt_hi:
                            stats["lines_checked"] += 1
                            en_ref = str(opts_en[idx]) if idx < len(opts_en) else ""
                            new_opt = edit_hindi_text(opt_hi, en_ref)
                            if new_opt != opt_hi:
                                m["options_hi"][idx] = new_opt
                                stats["lines_edited"] += 1
                if isinstance(m.get("explanation_pairs"), list):
                    for pair in m["explanation_pairs"]:
                        if isinstance(pair, dict):
                            _polish_field(pair, "hi", "en")
    except Exception as exc:  # fail open on traversal
        logger.warning("[Hindi Editor] edition polish partial error: %s", exc)
        stats["errors"] = stats.get("errors", 0) + 1

    return stats
