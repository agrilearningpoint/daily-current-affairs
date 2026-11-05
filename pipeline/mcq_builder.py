# -*- coding: utf-8 -*-
"""
One validated MCQ for every final story (stage 16).

Order of preference for each story:

1. the LLM reference-format MCQ (pipeline.mcq_schema), already checked against
   *both* the schema rules and the generic validator;
2. bilingual deterministic templates whose answer is copied from the story's own
   text and whose distractors come from typed, bilingual pools (State/UT,
   country, organisation) — so options are of the same kind and never junk;
3. the older deterministic templates in pipeline.content.

A candidate is accepted only when ``pipeline.content.validate_mcqs`` passes it
(the same fail-closed validator stage 17 runs again).  A story for which no
candidate passes is reported back so the caller can drop it and promote a
reserve story instead of printing a story without its question unit.
"""
from __future__ import annotations

import hashlib
import logging
import re
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)

DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")

INDIAN_STATES: Dict[str, str] = {
    "Andhra Pradesh": "आंध्र प्रदेश", "Arunachal Pradesh": "अरुणाचल प्रदेश", "Assam": "असम",
    "Bihar": "बिहार", "Chhattisgarh": "छत्तीसगढ़", "Goa": "गोवा", "Gujarat": "गुजरात",
    "Haryana": "हरियाणा", "Himachal Pradesh": "हिमाचल प्रदेश", "Jharkhand": "झारखंड",
    "Karnataka": "कर्नाटक", "Kerala": "केरल", "Madhya Pradesh": "मध्य प्रदेश",
    "Maharashtra": "महाराष्ट्र", "Manipur": "मणिपुर", "Meghalaya": "मेघालय", "Mizoram": "मिज़ोरम",
    "Nagaland": "नागालैंड", "Odisha": "ओडिशा", "Punjab": "पंजाब", "Rajasthan": "राजस्थान",
    "Sikkim": "सिक्किम", "Tamil Nadu": "तमिलनाडु", "Telangana": "तेलंगाना", "Tripura": "त्रिपुरा",
    "Uttar Pradesh": "उत्तर प्रदेश", "Uttarakhand": "उत्तराखंड", "West Bengal": "पश्चिम बंगाल",
    "Jammu and Kashmir": "जम्मू और कश्मीर", "Ladakh": "लद्दाख", "Puducherry": "पुडुचेरी",
    "Chandigarh": "चंडीगढ़", "Delhi": "दिल्ली", "Lakshadweep": "लक्षद्वीप", "Andaman and Nicobar Islands": "अंडमान और निकोबार द्वीप समूह",
}
STATE_ALIASES = {"Keralam": "Kerala", "Orissa": "Odisha", "J&K": "Jammu and Kashmir", "Pondicherry": "Puducherry",
                 "Andhra": "Andhra Pradesh", "Bengal": "West Bengal", "Kashmir": "Jammu and Kashmir",
                 "Himachal": "Himachal Pradesh", "Arunachal": "Arunachal Pradesh", "Uttaranchal": "Uttarakhand",
                 "Andaman": "Andaman and Nicobar Islands", "New Delhi": "Delhi", "NCT of Delhi": "Delhi"}

COUNTRIES: Dict[str, str] = {
    "United States": "संयुक्त राज्य अमेरिका", "China": "चीन", "Russia": "रूस", "Japan": "जापान",
    "Germany": "जर्मनी", "France": "फ्रांस", "United Kingdom": "यूनाइटेड किंगडम", "Italy": "इटली",
    "Canada": "कनाडा", "Australia": "ऑस्ट्रेलिया", "Brazil": "ब्राज़ील", "South Africa": "दक्षिण अफ्रीका",
    "Saudi Arabia": "सऊदी अरब", "UAE": "संयुक्त अरब अमीरात", "Israel": "इज़राइल", "Iran": "ईरान",
    "Pakistan": "पाकिस्तान", "Bangladesh": "बांग्लादेश", "Nepal": "नेपाल", "Bhutan": "भूटान",
    "Sri Lanka": "श्रीलंका", "Maldives": "मालदीव", "Myanmar": "म्यांमार", "Afghanistan": "अफ़ग़ानिस्तान",
    "Indonesia": "इंडोनेशिया", "Singapore": "सिंगापुर", "Vietnam": "वियतनाम", "Thailand": "थाईलैंड",
    "Malaysia": "मलेशिया", "Philippines": "फिलीपींस", "South Korea": "दक्षिण कोरिया", "Egypt": "मिस्र",
    "Kenya": "केन्या", "Nigeria": "नाइजीरिया", "Argentina": "अर्जेंटीना", "Mexico": "मेक्सिको",
    "Ukraine": "यूक्रेन", "Romania": "रोमानिया", "New Zealand": "न्यूज़ीलैंड", "Qatar": "क़तर",
    "Oman": "ओमान", "Mauritius": "मॉरीशस", "Greece": "ग्रीस", "Spain": "स्पेन", "Netherlands": "नीदरलैंड",
}
COUNTRY_ALIASES = {"United Arab Emirates": "UAE", "U.S.": "United States", "US": "United States",
                   "USA": "United States", "U.K.": "United Kingdom", "UK": "United Kingdom", "Britain": "United Kingdom"}


def _ws(t: Any) -> str:
    return re.sub(r"\s+", " ", str(t or "")).strip()


def _plain(h: Any) -> str:
    return re.sub(r"^\s*>>\s*", "", _ws(h))


def _salt_order(names: Iterable[str], salt: str) -> List[str]:
    return sorted(names, key=lambda n: hashlib.sha1((salt + "|" + n).encode("utf-8")).hexdigest())


def _all_named(text: str, table: Dict[str, str], aliases: Dict[str, str]) -> set:
    """Canonical names of every table entry (or alias) mentioned in text."""
    found = set()
    for surface, canon in list(aliases.items()) + [(k, k) for k in table]:
        if re.search(r"(?<![A-Za-z])" + re.escape(surface) + r"(?![A-Za-z])", text):
            found.add(canon)
    return found


def _find_named(text: str, table: Dict[str, str], aliases: Dict[str, str]) -> Tuple[str, str]:
    """(canonical name, the surface form found) for the first table entry present in text."""
    best: Tuple[int, str, str] = (10 ** 9, "", "")
    for surface, canon in list(aliases.items()) + [(k, k) for k in table]:
        m = re.search(r"(?<![A-Za-z])" + re.escape(surface) + r"(?![A-Za-z])", text)
        if m and m.start() < best[0]:
            best = (m.start(), canon, surface)
    return best[1], best[2]


def _strip_term(text: str, terms: Iterable[str]) -> str:
    out = text
    for t in sorted((t for t in terms if t), key=len, reverse=True):
        if t:
            out = re.sub(r"(?<![A-Za-z\u0900-\u097F])" + re.escape(t) + r"(?:'s|’s)?(?![A-Za-z])", "", out, flags=re.I)
    out = re.sub(r"\s+([,.;:])", r"\1", out)
    out = re.sub(r"\s*\|.*$", "", out)  # "... | The Hindu Editorial" publisher suffix
    out = re.sub(r"\s{2,}", " ", out).strip(" ,;:-–—'\"‘’")
    # A stem must not end on a dangling preposition after the answer was removed
    # ("Official visit of Foreign Secretary to" -> "Official visit of Foreign Secretary").
    out = re.sub(r"\s+(?:to|in|of|at|for|from|with|by|on|and|the)$", "", out, flags=re.I)
    return out.strip(" ,;:-–—")


def _clip(t: str, n: int) -> str:
    t = _ws(t)
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def _expl_lines(ci: Dict[str, Any]) -> Tuple[str, str]:
    kps_en = [p for p in (ci.get("key_points_en") or []) if _ws(p)]
    kps_hi = [p for p in (ci.get("key_points_hi") or []) if _ws(p)]
    en = _ws(kps_en[0]) if kps_en else _plain(ci.get("headline_en"))
    hi = _ws(kps_hi[0]) if kps_hi and DEVANAGARI_RE.search(kps_hi[0]) else _plain(ci.get("headline_hi"))
    return en, hi


def _make(ci: Dict[str, Any], mtype: str, q_en: str, q_hi: str, correct: Tuple[str, str],
          distractors: List[Tuple[str, str]], expl_en: str, expl_hi: str) -> Optional[Dict[str, Any]]:
    if len(distractors) < 4:
        return None
    opts = [correct] + distractors[:4]
    salt = str(ci.get("event_id", "")) + mtype
    k = int(hashlib.sha1((salt + "|" + correct[0]).encode("utf-8")).hexdigest(), 16) % len(opts)
    opts = opts[k:] + opts[:k]
    idx = opts.index(correct)
    return {
        "type": mtype,
        "question_en": q_en, "question_hi": q_hi,
        # "EN / हिन्दी" options: the PDF splits them into bilingual option lines and
        # the validator checks the English half against the story text.
        "options": [f"{e} / {h}" if h else e for e, h in opts],
        "correct": "ABCDE"[idx],
        "explanation_en": expl_en, "explanation_hi": expl_hi,
        "exam_point": _clip(ci.get("exam_fact_en") or "", 120),
        "event_id": ci.get("event_id", ""),
        "source_url": (ci.get("source") or {}).get("url", "") if isinstance(ci.get("source"), dict) else "",
    }


def _place_mcq(ci: Dict[str, Any], evidence: str, table: Dict[str, str], aliases: Dict[str, str],
               mtype: str, q_en_tpl: str, q_hi_tpl: str, expl_en_tpl: str, expl_hi_tpl: str) -> Optional[Dict[str, Any]]:
    headline = _plain(ci.get("headline_en"))
    headline_hi = _plain(ci.get("headline_hi"))
    if not DEVANAGARI_RE.search(headline_hi):
        return None
    # Ambiguity guard: a story naming two States (or two countries) cannot ask
    # "which State?" - e.g. "Andhra goes ahead ... despite Odisha's plea".
    if len(_all_named(headline, table, aliases)) > 1:
        return None
    canon, surface = _find_named(headline, table, aliases)
    if not canon:
        if len(_all_named(evidence, table, aliases)) != 1:
            return None
        canon, surface = _find_named(evidence, table, aliases)
    if not canon:
        return None
    mentioned = _all_named(evidence, table, aliases)
    hi_name = table[canon]
    stem_en = _strip_term(headline, {surface, canon} | {a for a, c in aliases.items() if c == canon})
    stem_hi = _strip_term(headline_hi, {hi_name, "नई " + hi_name} if canon == "Delhi" else {hi_name})
    if len(stem_en) < 12 or canon.lower() in stem_en.lower():
        return None
    low_ev = evidence.lower()
    others = [n for n in table if n != canon and n not in mentioned and n.lower() not in low_ev
              and not any(a.lower() in low_ev for a, c in aliases.items() if c == n)]
    distractors = [(n, table[n]) for n in _salt_order(others, str(ci.get("event_id", "")))[:4]]
    e_en, e_hi = _expl_lines(ci)
    return _make(ci, mtype,
                 q_en_tpl.format(stem=_clip(stem_en, 110)),
                 q_hi_tpl.format(stem=_clip(stem_hi, 110)),
                 (canon, hi_name), distractors,
                 expl_en_tpl.format(val=canon, point=e_en.rstrip(".")),
                 expl_hi_tpl.format(val=hi_name, point=e_hi.rstrip("।. ")))


def state_mcq(ci: Dict[str, Any], evidence: str) -> Optional[Dict[str, Any]]:
    return _place_mcq(
        ci, evidence, INDIAN_STATES, STATE_ALIASES, "place-state",
        'The news "{stem}" is related to which State / Union Territory?',
        '"{stem}" — यह समाचार किस राज्य / केंद्र शासित प्रदेश से संबंधित है?',
        "{point}. The development reported relates to {val}.",
        "{point}। यह समाचार {val} से संबंधित है।",
    )


def country_mcq(ci: Dict[str, Any], evidence: str) -> Optional[Dict[str, Any]]:
    return _place_mcq(
        ci, evidence, COUNTRIES, COUNTRY_ALIASES, "place-country",
        'The news "{stem}" involves which country?',
        '"{stem}" — यह समाचार किस देश से संबंधित है?',
        "{point}. The country involved in this development is {val}.",
        "{point}। इस घटनाक्रम से संबंधित देश {val} है।",
    )


def org_pool_mcq(ci: Dict[str, Any], evidence: str) -> Optional[Dict[str, Any]]:
    """Organisation named in the story, distractors from the same bilingual pool."""
    try:
        from pipeline.static_gk_db import SEMANTIC_OPTION_POOLS
    except Exception:
        return None
    headline = _plain(ci.get("headline_en"))
    headline_hi = _plain(ci.get("headline_hi"))
    if not DEVANAGARI_RE.search(headline_hi):
        return None
    low_ev = evidence.lower()
    for pool_name in ("financial_regulators", "agri_orgs", "defence_tech", "global_orgs", "ministries", "research_institutes"):
        pool = SEMANTIC_OPTION_POOLS.get(pool_name) or []
        for en, hi in pool:
            acr = re.search(r"\(([A-Z][A-Za-z-]{1,9})\)", en)
            short = acr.group(1) if acr else ""
            full = re.sub(r"\s*\([^)]*\)", "", en).split(",")[0].strip()
            hit = ""
            if short and re.search(r"(?<![A-Za-z])" + re.escape(short) + r"(?![A-Za-z])", evidence):
                hit = short
            elif full and full.lower() in low_ev:
                hit = full
            if not hit:
                continue
            correct = (hit, hi)
            stem_en = _strip_term(headline, {hit, full, short})
            stem_hi = _strip_term(headline_hi, {short, hi.split("(")[0].strip()})
            if len(stem_en) < 12 or hit.lower() in stem_en.lower():
                continue
            use_acr = bool(short) and hit == short
            others = []
            for e2, h2 in pool:
                if e2 == en:
                    continue
                a2 = re.search(r"\(([A-Z][A-Za-z-]{1,9})\)", e2)
                label = a2.group(1) if (use_acr and a2) else re.sub(r"\s*\([^)]*\)", "", e2).split(",")[0].strip()
                if not label or label.lower() in low_ev:
                    continue
                others.append((label, h2))
            others = [o for o in others if o[0] and o[0].lower() != hit.lower()]
            others = sorted(others, key=lambda o: hashlib.sha1((str(ci.get("event_id")) + o[0]).encode()).hexdigest())
            e_en, e_hi = _expl_lines(ci)
            m = _make(ci, "org-pool",
                      'Which organisation is associated with the news "%s"?' % _clip(stem_en, 110),
                      '"%s" — यह समाचार किस संगठन से संबंधित है?' % _clip(stem_hi, 110),
                      correct, others,
                      "%s. The organisation associated with this development is %s." % (e_en.rstrip("."), hit),
                      "%s। इस घटनाक्रम से संबंधित संगठन %s है।" % (e_hi.rstrip("।. "), correct[1]))
            if m:
                return m
    return None


BILINGUAL_TEMPLATES: List[Callable[[Dict[str, Any], str], Optional[Dict[str, Any]]]] = [
    state_mcq, country_mcq, org_pool_mcq,
]


def candidates_for_item(ci: Dict[str, Any], evidence: str, pools: Dict[str, Any],
                        all_items: List[Dict[str, Any]], llm_mcq: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """All MCQ candidates for one story, best first (LLM, bilingual templates, legacy templates)."""
    from pipeline.content import _build_item_candidates
    from pipeline.mcq_quality import concept_mcqs
    out: List[Dict[str, Any]] = []
    if llm_mcq:
        out.append(llm_mcq)
    try:
        out.extend(concept_mcqs(ci, evidence))
    except Exception:
        logger.exception("[MCQ builder] concept candidates failed for %s", ci.get("event_id"))
    for fn in BILINGUAL_TEMPLATES:
        try:
            m = fn(ci, evidence)
        except Exception:
            logger.exception("[MCQ builder] %s failed for %s", fn.__name__, ci.get("event_id"))
            m = None
        if m:
            out.append(m)
    try:
        for m in _build_item_candidates(ci, pools, all_items):
            m = _legacy_fix(m, ci)
            if m is not None and _legacy_ok(m):
                out.append(_bilingualize(m))
    except Exception:
        logger.exception("[MCQ builder] legacy candidates failed for %s", ci.get("event_id"))
    return out


_LEGACY_EXPL = {
    "static-number": "{point}. The figure reported is {val}.",
    "scheme-ministry": "{point}. The ministry / organisation involved is {val}.",
    "report-rank": "{point}. The rank / position reported is {val}.",
    "who-org": "{point}. The institution featured is {val}.",
}
_LEGACY_EXPL_HI = {
    "static-number": "{point}। रिपोर्ट किया गया आंकड़ा {val} है।",
    "scheme-ministry": "{point}। संबंधित मंत्रालय/संगठन {val} है।",
    "report-rank": "{point}। रिपोर्ट की गई रैंक/स्थिति {val} है।",
    "who-org": "{point}। संबंधित संस्था {val} है।",
}


def _legacy_fix(m: Dict[str, Any], ci: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Legacy templates: drop number questions whose number was cut out of the headline
    (the stem then reads "could cover of exports"), and replace the
    "headline + source name" explanation with the story's first key point."""
    opts = m.get("options") or []
    letter = str(m.get("correct") or "")
    if len(letter) != 1 or "ABCDE".find(letter) < 0 or "ABCDE".find(letter) >= len(opts):
        return None
    ans = str(opts["ABCDE".index(letter)]).split(" / ")[0].strip()
    mtype = m.get("type")
    if mtype == "static-number":
        digits = re.findall(r"\d+(?:[.,]\d+)*", ans)
        if any(d in _plain(ci.get("headline_en")) for d in digits):
            return None
    tpl = _LEGACY_EXPL.get(mtype)
    if not tpl:
        return m
    p_en, p_hi = _expl_lines(ci)
    if not p_en or p_en == _plain(ci.get("headline_en")):
        return None  # nothing beyond the headline to explain with
    out = dict(m)
    out["explanation_en"] = tpl.format(point=p_en.rstrip("."), val=ans)
    if p_hi and DEVANAGARI_RE.search(p_hi):
        out["explanation_hi"] = _LEGACY_EXPL_HI[mtype].format(point=p_hi.rstrip("।. "), val=ans)
    return out


_ORG_WORD_RE = re.compile(r"\b(?:Ministry|Department|Commission|Bank|Authority|Council|Board|Corporation|"
                          r"Organisation|Organization|Institute|Agency|Federation|Court|Tribunal|Bureau|Mission)\b")


def _legacy_ok(m: Dict[str, Any]) -> bool:
    """Legacy entity templates pair any capitalised phrase with fixed organisation
    distractors ("PM", "What India", "CEO John Ternus" vs NABARD/FCI) - keep them
    only when the answer really is an organisation of the same kind."""
    if m.get("type") == "statement":
        # number-mutated statements produce junk such as "November 1.5, 2026"
        return False
    if m.get("type") not in ("who-org", "scheme-ministry"):
        return True
    opts = m.get("options") or []
    letter = str(m.get("correct") or "")
    if len(letter) != 1 or "ABCDE".find(letter) >= len(opts):
        return False
    ans = str(opts["ABCDE".index(letter)]).split(" / ")[0].strip()
    if _ORG_WORD_RE.search(ans):
        return True
    return bool(re.fullmatch(r"[A-Z]{3,8}", ans)) and ans in _bilingual_lookup()


_LOOKUP: Dict[str, str] = {}


def _bilingual_lookup() -> Dict[str, str]:
    if not _LOOKUP:
        try:
            from pipeline.static_gk_db import SEMANTIC_OPTION_POOLS
            for pool in SEMANTIC_OPTION_POOLS.values():
                for en, hi in pool:
                    _LOOKUP[en] = hi
                    _LOOKUP[re.sub(r"\s*\([^)]*\)", "", en).split(",")[0].strip()] = hi
                    acr = re.search(r"\(([A-Z][A-Za-z-]{1,9})\)", en)
                    if acr:
                        _LOOKUP[acr.group(1)] = hi
        except Exception:
            pass
        _LOOKUP.update(INDIAN_STATES)
        _LOOKUP.update(COUNTRIES)
    return _LOOKUP


def _bilingualize(m: Dict[str, Any]) -> Dict[str, Any]:
    """Add Hindi to legacy text options ("EN / हिन्दी") when every option has a known
    Hindi name; numbers and statements are left as they are."""
    opts = [str(o) for o in (m.get("options") or [])]
    if not opts or any(" / " in o or re.search(r"\d", o) for o in opts):
        return m
    table = _bilingual_lookup()
    his = [table.get(o.strip()) for o in opts]
    if not all(his):
        return m
    out = dict(m)
    out["options"] = [f"{o} / {h}" for o, h in zip(opts, his)]
    return out


def first_valid(cands: List[Dict[str, Any]], ci: Dict[str, Any], seen_q: set) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """First candidate that passes the fail-closed validator and is not a repeated question."""
    from pipeline.content import _qkey, validate_mcqs
    from pipeline.mcq_quality import answer_in_headline
    reasons: List[str] = []
    # Prefer questions the headline does not answer (static / body facts); stable order otherwise.
    # LLM (when the headline does not answer it) > concept > LLM > other templates.
    def _rank(c):
        hl = answer_in_headline(c, ci)
        if c.get("type") == "llm-schema":
            return 2 if hl else 0
        if c.get("type") == "concept":
            return 1
        return 4 if hl else 3
    cands = sorted(cands, key=_rank)
    for c in cands:
        if _qkey(c.get("question_en")) in seen_q:
            reasons.append(f"{c.get('type')}: duplicate question")
            continue
        ok, rej = validate_mcqs([c], [ci])
        if ok:
            return ok[0], reasons
        reasons.append(f"{c.get('type')}: {', '.join(rej[0].get('errors', [])[:3])}")
    return None, reasons
