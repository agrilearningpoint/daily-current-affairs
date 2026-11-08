# -*- coding: utf-8 -*-
"""Automatic "Quick Bites" and "Agriculture Corner" sections (stage 17b).

Until now both sections were filled by hand (work/quick_bites_*.py,
work/agri_corner_*.py), so every unattended run (e.g. 2026-11-02, run
41437192142) shipped an MCQ-only edition.  This module builds them from the
edition's own verified, scored stories:

* ``content["quick_bites"]``: 30-40 bilingual two-line items
  ``{"category_en", "category_hi", "en", "hi", "event_id"}`` grouped by exam
  category, from good stories that are NOT MCQ units;
* ``content["agri_corner"]``: ``{"items": [{"en", "hi", "event_id"}],
  "static_gk": [{"en", "hi"}]}`` from agriculture / rural / farmer / food /
  fisheries / animal-husbandry stories (present when >= 1 agri item survives).

Hindi is produced by the existing validated batch translator and is
FAIL-CLOSED: an item whose Hindi does not pass ``ai_translator._validate``
(Devanagari, numbers and acronyms preserved, sane length) is dropped, never
published in English-only or dictionary Hindi.  Everything is fail-soft and
bounded by ``ALP_AUTO_SECTIONS_BUDGET`` seconds of translation time.
"""
from __future__ import annotations

import logging
import os
import re
import time
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

logger = logging.getLogger("pipeline.auto_sections")

QB_MIN = int(os.getenv("ALP_QUICK_BITES_MIN", "30"))
QB_MAX = int(os.getenv("ALP_QUICK_BITES_MAX", "40"))
AGRI_MAX = int(os.getenv("ALP_AGRI_CORNER_MAX", "6"))
MIN_RELEVANCE = float(os.getenv("ALP_QUICK_BITES_MIN_RELEVANCE", "20"))
BATCH_SIZE = int(os.getenv("ALP_AUTO_SECTIONS_BATCH", "10"))
EN_MAX_CHARS = 230

# Exam categories (order = order of the bands in the PDF).
CATEGORIES: List[Tuple[str, str]] = [
    ("National & States", "राष्ट्रीय एवं राज्य"),
    ("Economy & Finance", "अर्थव्यवस्था एवं वित्त"),
    ("International", "अंतरराष्ट्रीय"),
    ("Defence & Awards", "रक्षा एवं पुरस्कार"),
    ("Science, Health & Environment", "विज्ञान, स्वास्थ्य एवं पर्यावरण"),
    ("Sports", "खेल"),
    ("Education, Jobs & Transport", "शिक्षा, रोजगार एवं परिवहन"),
]
_CAT_HI = dict(CATEGORIES)
_CAT_ORDER = {c: i for i, (c, _h) in enumerate(CATEGORIES)}

_DEFENCE_AWARD_RE = re.compile(
    r"\b(?:defen[cs]e|army|navy|naval|air\s+force|air\s+staff|iaf|drdo|missile|corvettes?|warships?|submarine|"
    r"exercise|military|award(?:s|ed)?|prize|medal|honou?r(?:ed|s)?|padma|conferred|doctorate|fellowships?)\b", re.I)
_SPORTS_RE = re.compile(
    r"\b(?:cricket|hockey|football|tennis|badminton|chess|athletics?|olympic\w*|world\s+cup|championship|"
    r"tournament|odi|t20|test\s+match|grand\s+prix|formula\s+one|f1|wrestl\w+|boxing|shooting|archery|"
    r"medal\s+tally|wins?\s+(?:gold|silver|bronze|title))\b", re.I)
_EDU_RE = re.compile(
    r"\b(?:education|school|university|universities|exam|students?|skill\w*|jobs?|employment|recruitment|"
    r"railways?|rail|metro|airport|highway|expressway|transport|vande\s+bharat|bullet\s+train|aviation)\b", re.I)
_SCIENCE_RE = re.compile(
    r"\b(?:isro|nasa|mars|moon|lunar|satellite|space\w*|gslv|pslv|science|scientists?|research\w*|health|"
    r"disease|vaccine|tb|cancer|medical|hospital|climate|environment\w*|forest|wildlife|tiger|pollution|"
    r"cyclone|monsoon|imd|weather|seismo\w*|earthquake|energy|solar|wind|renewable|nuclear|ai|"
    r"artificial\s+intelligence|semiconductor\w*|cyber\w*)\b", re.I)
_INTL_RE = re.compile(
    r"\b(?:EU|UN|UNESCO|WHO|IMF|WTO|G20|G7|BRICS|SCO|ASEAN|QUAD|bilateral|foreign\s+(?:minister|secretary|policy)|"
    r"ambassador|high\s+commissioner|Brussels|Russia|Ukraine|China|Pakistan|Nepal|Bangladesh|Sri\s+Lanka|"
    r"UAE|Israel|Iran|Gaza|Japan|Europe|European|Macedonia|Bhutan|Oman|Senegal|Africa\w*|Washington|Moscow|"
    r"Beijing|Tokyo|EAM)\b")
# ("summit" alone is not international: the PM's RE summit in Delhi is domestic.)
_ECON_RE = re.compile(
    r"\b(?:gdp|inflation|gst|tax\w*|dut(?:y|ies)|rbi|sebi|bank\w*|econom\w*|fiscal|budget|export\w*|import\w*|"
    r"trade|pmi|iip|rupee|forex|invest\w*|fdi|insolvency|ibc|crore|market\w*|ipo|deposits?|interest\s+rates?|"
    r"fund|loans?|credit|msme|industr\w*|manufactur\w*|coal|power|fuel)\b", re.I)

AGRI_RE = re.compile(
    r"\b(?:agri\w*|farm(?:er|ers|ing|s)?|kisan|krishi|crops?|kharif|rabi|msp|minimum\s+support\s+price|paddy|"
    r"wheat|pulses|oilseeds?|sugarcane|cotton|horticultur\w*|fertili[sz]er\w*|urea|seeds?|soil|irrigation|"
    r"fisheries|aquaculture|fish\s+farm\w*|pmmsy|dairy|milk|livestock|animal\s+husbandry|poultry|cattle|"
    r"veterinary|food\s+processing|food\s+security|foodgrains?|procurement\s+of\s+(?:paddy|wheat|rice)|"
    r"fci|nafed|nabard|icar|iari|kvk|apeda|e-?nam|mandi|rural|cooperatives?|organic|millets?|"
    r"pm-?kisan|pmfby|fasal\s+bima)\b", re.I)
# Agriculture words that are not farm news on their own ("fishermen detained").
AGRI_FALSE_RE = re.compile(r"\bfishermen\b.*\b(?:detain|arrest|navy|coast\s+guard)", re.I)
# Words that make a weak agri match (irrigation tank, rural, co-op bank) political/crime/banking news.
AGRI_OFFTOPIC_RE = re.compile(
    r"\b(?:sand\s+mining|illegal\s+mining|DVAC|vigilance|corruption|bribe\w*|arrest\w*|raids?|FIR|"
    r"chargesheet|CBI|ED\b|enforcement\s+directorate|DMK|AIADMK|BJP|Congress|YSRCP|TMC|AAP|MLA|MP\b|"
    r"youth\s+wing|party|poll\w*|election\w*|murder|police|urban\s+co-?operative\s+banks?|"
    r"bank\s+in\s+a\s+box|co-?operative\s+banks?|UCBs?)\b", re.I)
AGRI_STRONG_RE = re.compile(
    r"\b(?:agri\w*|farm(?:er|ers|ing)|kisan|krishi|crops?|kharif|rabi|msp|minimum\s+support\s+price|paddy|"
    r"wheat|pulses|oilseeds?|sugarcane|horticultur\w*|fertili[sz]er\w*|urea|fisheries|aquaculture|"
    r"livestock|animal\s+husbandry|dairy|icar|iari|kvk|nafed|pm-?kisan|pmfby|fasal\s+bima|millets?|PACS)\b", re.I)

_JUNK_SENT_RE = re.compile(
    r"\b(?:updated|image\s+used|representational|photo\s+credit|also\s+read|click\s+here|subscribe|"
    r"read\s+more|follow\s+us|for\s+more|sign\s+up|newsletter|copyright|all\s+rights|dvids)\b|https?://|\bIST\b"
    r"|\[\s*image|\bimage\s+\d+\s+of\s+\d+", re.I)

_SMALL = {"a", "an", "and", "as", "at", "by", "for", "from", "in", "into", "of", "on", "or", "the", "to", "with",
          "under", "over", "via"}
_KEEP_UPPER = {"PIB", "PMO", "MEA", "RBI", "SEBI", "ISRO", "DRDO", "IMD", "ICAR", "IARI", "NABARD", "FCI",
               "GST", "GDP", "UN", "UNESCO", "WHO", "IMF", "WTO", "FAO", "UPI", "NPCI", "IAF", "CDS", "CISF",
               "BSF", "CRPF", "NIA", "CBI", "ED", "SC", "HC", "MSP", "PMMSY", "PM", "CM", "MoU", "MOU", "AI",
               "US", "UK", "UAE", "EU", "G20", "BRICS", "SCO", "ASEAN", "NITI", "IIT", "IIM", "AIIMS",
               "ESIC", "EPFO", "NHAI", "BIS", "NIFT", "MSDE", "RODTEP", "VAYU", "NVS", "GSLV", "PSLV"}


# --------------------------------------------------------------------------- #
# Text helpers
# --------------------------------------------------------------------------- #
def _norm(text: Any) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", str(text or ""))).strip()


def clean_headline(text: Any) -> str:
    """Display headline: no '>>', no ' - Publisher' tail, sentence-cased when ALL CAPS."""
    try:
        from pipeline.official_sources import strip_publisher_suffix
    except Exception:  # pragma: no cover
        strip_publisher_suffix = lambda t: t  # noqa: E731
    t = _norm(text)
    t = re.sub(r"^(?:>>|>|\s)+", "", t)
    t = re.sub(r"^\W+(?=\w)", "", t)  # stray zero-width / bullet characters
    t = strip_publisher_suffix(t)
    t = re.sub(r"\s+[-–|]\s+(?:News\s+On\s+AIR|PM\s+India|DD\s+News|pib\.gov\.in|www\.[\w.]+)\s*$", "", t, flags=re.I)
    try:  # "(Key: DD News)", " - Buffalo Toronto Public Media" and other source tails
        from pipeline.news_filters import strip_tags
        t = strip_tags(t)
    except Exception:  # pragma: no cover
        pass
    letters = [c for c in t if c.isalpha() and c.isascii()]
    if letters and sum(c.isupper() for c in letters) / len(letters) > 0.8:
        words = []
        for i, w in enumerate(t.split()):
            core = re.sub(r"[^A-Za-z0-9-]", "", w)
            if re.fullmatch(r"\d+(?:ST|ND|RD|TH)", core):
                words.append(w.lower())  # 29TH -> 29th
            elif core.upper() in _KEEP_UPPER or any(ch.isdigit() for ch in core):
                words.append(w)
            elif i and core.lower() in _SMALL:
                words.append(w.lower())
            else:
                words.append(w[:1].upper() + w[1:].lower())
        t = " ".join(words)
    return t.strip(" -|:")


def _sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9₹\"'(])", _norm(text)) if s.strip()]


def _tokens(text: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]{3,}", (text or "").lower())}


def _jaccard(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    return len(ta & tb) / max(1, len(ta | tb)) if ta and tb else 0.0


def _signature(text: str) -> set:
    """Acronyms, numbers and long words: what makes two headlines the same event."""
    t = re.sub(r"[‐-―−-]", " ", text or "")
    sig = {w.lower() for w in re.findall(r"\b[A-Z][A-Z0-9]{1,}\b", t)}
    sig |= set(re.findall(r"\d[\d,.]*", t))
    sig |= {w.lower() for w in re.findall(r"\b[A-Z][a-z]{3,}\b", t)
            if w.lower() not in _GENERIC_PROPER}
    return sig


_GENERIC_PROPER = {"union", "minister", "ministry", "government", "india", "indian", "national", "shri",
                   "president", "prime", "chief", "state", "states", "central", "centre", "department",
                   "october", "november", "december", "january", "february", "march", "april", "june",
                   "july", "august", "september", "scheme", "mission", "report", "board", "commission",
                   "award", "awards", "presents", "addresses", "inaugurates", "launches", "holds"}


def same_event(a: str, b: str) -> bool:
    j = _jaccard(a, b)
    if j >= 0.5:
        return True
    shared = _signature(a) & _signature(b)
    common = _tokens(a) & _tokens(b)
    hard = {w for w in shared if not w.isalpha() or w.upper() in (a + " " + b)}  # acronyms / figures
    # "Manufacturing PMI eases to 54.7 in October" ~ "Manufacturing PMI dips in October"
    return (j >= 0.2 and len(shared) >= 2) or (j >= 0.15 and len(hard) >= 1 and len(common) >= 3)


def two_line_text(item: Dict[str, Any], limit: int = EN_MAX_CHARS) -> str:
    """Headline sentence + (when it adds facts) one clean summary sentence, <= limit chars."""
    head = clean_headline(item.get("headline_en") or item.get("title"))
    if not head:
        return ""
    out = head.rstrip(" ;:") if head.rstrip().endswith(("!", "?", ".")) else head.rstrip(" .;:") + "."
    summary = _norm(item.get("raw_facts") or item.get("summary") or "")
    summary = summary.split(" | Also reported:")[0]
    head_words = {w for w in _tokens(head) if len(w) >= 4}
    for sent in _sentences(summary)[:3]:
        if len(sent) < 40 or _JUNK_SENT_RE.search(sent) or _jaccard(sent, head) > 0.55:
            continue
        if head_words and not (head_words & _tokens(sent)):
            break  # a sentence from another paragraph/story (spliced "Velu for the party's ..." line)
        if len(out) + 1 + len(sent) <= limit and sent.endswith((".", "!", "?")):
            out = f"{out} {sent}"
        break
    if len(out) > limit:
        cut = out[:limit].rsplit(" ", 1)[0].rstrip(",;:-")
        out = cut + "…"
    return out


def quick_bite_category(item: Dict[str, Any]) -> str:
    text = f"{item.get('headline_en') or item.get('title') or ''}"
    cat = str(item.get("category") or "")
    if _SPORTS_RE.search(text) or cat == "Sports":
        return "Sports"
    if _DEFENCE_AWARD_RE.search(text) or cat in ("Defence", "Awards & Honours"):
        return "Defence & Awards"
    if _SCIENCE_RE.search(text):
        return "Science, Health & Environment"
    if _INTL_RE.search(text) or cat == "International":
        return "International"
    if _ECON_RE.search(text) or cat in ("Economy", "Banking & Finance"):
        return "Economy & Finance"
    if cat in ("Science & Technology", "Environment", "Health"):
        return "Science, Health & Environment"
    if _EDU_RE.search(text) or cat == "Education":
        return "Education, Jobs & Transport"
    return "National & States"


def is_agri(item: Dict[str, Any]) -> bool:
    text = f"{item.get('headline_en') or item.get('title') or ''}"
    if AGRI_FALSE_RE.search(text) or re.search(r"\bseed\s+(?:fund\w*|round|capital)\b", text, re.I):
        return False
    if not AGRI_RE.search(text):  # the headline itself must be about farm/rural/food
        return False
    if AGRI_OFFTOPIC_RE.search(text) and not AGRI_STRONG_RE.search(re.sub(
            r"co-?operative\s+banks?", " ", text, flags=re.I)):
        return False  # "irrigation tank ... sand mining charge against DMK's Velu"
    return True


def _bad_candidate(item: Dict[str, Any]) -> bool:
    from pipeline.news_filters import is_non_news
    head = clean_headline(item.get("headline_en") or item.get("title"))
    if len(head) < 20 or len(head.split()) < 4 or is_non_news(head):
        return True
    if re.search(r"[\u0900-\u097F]", head):  # Hindi-only feed titles have no EN line
        return True
    try:  # state party politics, listicles, opinion, crime (pipeline/exam_relevance.py)
        from pipeline.exam_relevance import drop_reason
        if drop_reason({"headline_en": head, "summary_en": item.get("summary_en") or item.get("raw_facts") or ""}):
            return True
    except Exception:
        pass
    try:  # same demotions as stage 07 (sound-bites, ceremonies, market chatter)
        import importlib.util
        from pathlib import Path
        global _REL_MOD
        if _REL_MOD is None:
            path = Path(__file__).resolve().parent.parent / "agents" / "07_student_domain_relevance.py"
            spec = importlib.util.spec_from_file_location("alp_rel07", str(path))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
            _REL_MOD = mod
        m = _REL_MOD
        if (m.POLITICAL_RHETORIC.search(head) or m.QUOTE_HEADLINE.match(head) or m.CEREMONIAL.search(head)
                or m.MARKET_CHATTER.search(head) or m.FOREIGN_CLUB_SPORT.search(head)):
            return True
    except Exception:
        pass
    return False


_REL_MOD = None


def _garbled_agri(en: Any) -> bool:
    """Agri-corner line that is a scraper join / broken sentence ("... E.V. Velu. Velu for
    the party's ... Conference held on December 14, 2025."). Fail-open."""
    try:
        from pipeline.period_builder import garbled
        return garbled(en)
    except Exception:
        return False


def _relevance(item: Dict[str, Any]) -> float:
    try:
        return float(item.get("student_relevance", item.get("importance_score", 0)) or 0)
    except (TypeError, ValueError):
        return 0.0


def _pick(pool: Iterable[Dict[str, Any]], exclude_texts: Sequence[str], limit: int,
          topic_cap: int = 2, rare: Optional[set] = None) -> List[Dict[str, Any]]:
    """Best-first, de-duplicated (same event / shared rare entity / running topic) list."""
    from pipeline.news_filters import same_event_entity, topic_key
    rare = rare or set()
    chosen: List[Dict[str, Any]] = []
    seen_texts = [t for t in exclude_texts if t]
    topics: Dict[str, int] = {}
    for it in pool:
        head = clean_headline(it.get("headline_en") or it.get("title"))
        if any(same_event(head, t) or same_event_entity(head, t, rare) for t in seen_texts):
            continue
        tk = topic_key(it)
        if tk and topics.get(tk, 0) >= topic_cap:
            continue
        chosen.append(it)
        seen_texts.append(head)
        if tk:
            topics[tk] = topics.get(tk, 0) + 1
        if len(chosen) >= limit:
            break
    return chosen


# --------------------------------------------------------------------------- #
# Translation (batched, validated, fail-closed)
# --------------------------------------------------------------------------- #
def batch_translate(lines: Sequence[str], deadline: float, task: str = "quick_bite",
                    batch_size: int = BATCH_SIZE) -> Dict[str, str]:
    """English line -> validated Hindi, for the lines that passed.  Never raises.

    Uses the content builder's indexed JSON batch request (one LLM call per
    ``batch_size`` lines) and its fail-closed validator; lines whose Hindi fails
    validation are simply absent from the result.  One retry pass is made for
    failed lines while time remains.
    """
    out: Dict[str, str] = {}
    try:
        from pipeline import content as content_mod
        from pipeline.ai_router import is_configured
    except Exception as exc:  # pragma: no cover
        logger.warning("[AutoSections] translator unavailable: %s", exc)
        return out
    if not is_configured():
        logger.warning("[AutoSections] no AI provider configured; Hindi unavailable -> sections skipped")
        return out
    todo = [ln for ln in dict.fromkeys(l for l in lines if l)]
    for attempt in range(2):
        pending = [ln for ln in todo if ln not in out]
        for i in range(0, len(pending), max(1, batch_size)):
            if time.monotonic() > deadline:
                logger.warning("[AutoSections] translation budget used; %d line(s) left untranslated",
                               len([ln for ln in todo if ln not in out]))
                return out
            chunk = pending[i:i + batch_size]
            try:
                content_mod._prefill_body_translation_cache(chunk, task=task)
            except Exception as exc:
                logger.warning("[AutoSections] batch failed: %s", exc)
                continue
            for ln in chunk:
                hit = content_mod._TRANSLATION_CACHE.get((task, content_mod._norm_ws(ln)))
                if hit and hit[1] == "ai_translator" and hit[0]:
                    out[ln] = hit[0]
        if all(ln in out for ln in todo):
            break
    return out


def _valid_hindi(en: str, hi: str) -> bool:
    try:
        from pipeline.ai_translator import _validate
        ok, _c, _i = _validate(en, hi)
        return bool(ok)
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# Agriculture static GK
# --------------------------------------------------------------------------- #
AGRI_GK_EXTRA: Dict[str, List[Tuple[str, str]]] = {
    "CACP": [
        ("The Commission for Agricultural Costs and Prices (CACP), set up in 1965, recommends Minimum Support Prices (MSP).",
         "कृषि लागत एवं मूल्य आयोग (CACP), जिसकी स्थापना 1965 में हुई थी, न्यूनतम समर्थन मूल्य (MSP) की सिफारिश करता है।"),
    ],
    "PMKISAN": [
        ("PM-KISAN was launched on 24 February 2019; eligible farmers get ₹6,000 a year in three instalments of ₹2,000.",
         "पीएम-किसान योजना 24 फरवरी 2019 को शुरू हुई; पात्र किसानों को ₹2,000 की तीन किस्तों में प्रति वर्ष ₹6,000 मिलते हैं।"),
    ],
    "PMFBY": [
        ("Pradhan Mantri Fasal Bima Yojana (PMFBY) was launched in 2016; farmers pay 2% premium for Kharif and 1.5% for Rabi crops.",
         "प्रधानमंत्री फसल बीमा योजना (PMFBY) 2016 में शुरू हुई; किसान खरीफ फसलों के लिए 2% और रबी फसलों के लिए 1.5% प्रीमियम देते हैं।"),
    ],
    "PMMSY": [
        ("Pradhan Mantri Matsya Sampada Yojana (PMMSY) was launched in 2020 for the development of the fisheries sector.",
         "प्रधानमंत्री मत्स्य संपदा योजना (PMMSY) मत्स्य पालन क्षेत्र के विकास के लिए 2020 में शुरू की गई थी।"),
    ],
    "NDDB": [
        ("The National Dairy Development Board (NDDB) was set up in 1965 and is headquartered at Anand, Gujarat.",
         "राष्ट्रीय डेयरी विकास बोर्ड (NDDB) की स्थापना 1965 में हुई थी और इसका मुख्यालय आणंद, गुजरात में है।"),
    ],
    "ENAM": [
        ("The National Agriculture Market (e-NAM) electronic trading portal was launched on 14 April 2016.",
         "राष्ट्रीय कृषि बाजार (e-NAM) इलेक्ट्रॉनिक व्यापार पोर्टल 14 अप्रैल 2016 को शुरू किया गया था।"),
    ],
}
_AGRI_GK_TRIGGERS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\b(?:msp|minimum\s+support\s+price|procurement|kharif|rabi)\b", re.I), "CACP"),
    (re.compile(r"\b(?:pm-?kisan|kisan\s+samman)\b", re.I), "PMKISAN"),
    (re.compile(r"\b(?:pmfby|fasal\s+bima|crop\s+insurance)\b", re.I), "PMFBY"),
    (re.compile(r"\b(?:fisheries|fish|aquaculture|pmmsy|matsya)\b", re.I), "PMMSY"),
    (re.compile(r"\b(?:dairy|milk|nddb)\b", re.I), "NDDB"),
    (re.compile(r"\b(?:e-?nam|mandi|agri(?:cultural)?\s+market)\b", re.I), "ENAM"),
]
_AGRI_DB_KEYS = ("ICAR", "IARI", "NABARD", "FCI", "APEDA", "NAFED", "MOA", "FAO")


def agri_static_gk(texts: Sequence[str], limit: int = 5) -> List[Dict[str, str]]:
    """Verified bilingual static GK pairs for the agri stories (curated, never generated)."""
    blob = " ".join(texts)
    pairs: List[Tuple[str, str]] = []
    for rx, key in _AGRI_GK_TRIGGERS:
        if rx.search(blob):
            pairs.extend(AGRI_GK_EXTRA[key][:1])
    try:
        from pipeline.static_gk_db import ENTITY_STATIC_DB, lookup_static_gk_for_text
        for en, hi in lookup_static_gk_for_text(blob):
            if any(en in [f[0] for f in (ENTITY_STATIC_DB.get(k) or {}).get("facts", [])] for k in _AGRI_DB_KEYS):
                pairs.append((en, hi))
        if len(pairs) < 2:  # always give agri aspirants the two anchor institutions
            for key in ("ICAR", "NABARD"):
                facts = (ENTITY_STATIC_DB.get(key) or {}).get("facts", [])
                pairs.extend(facts[:1])
    except Exception:
        pass
    out, seen = [], set()
    for en, hi in pairs:
        if en not in seen and hi:
            seen.add(en)
            out.append({"en": en, "hi": hi})
        if len(out) >= limit:
            break
    return out


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #
def build_sections(content: Dict[str, Any], candidates: Sequence[Dict[str, Any]],
                   budget_seconds: Optional[float] = None,
                   translate: Optional[Callable[[Sequence[str], float], Dict[str, str]]] = None,
                   job_date: Optional[str] = None) -> Dict[str, Any]:
    """Add ``quick_bites`` and ``agri_corner`` to *content* in place; return stats.

    *candidates* are scored/selected/reserve stories (any order).  MCQ units
    (``content["items"]``) never become Quick Bites; agriculture stories go to
    the Agriculture Corner instead of Quick Bites.  Never raises.
    """
    t0 = time.monotonic()
    budget = float(os.getenv("ALP_AUTO_SECTIONS_BUDGET", "240")) if budget_seconds is None else budget_seconds
    deadline = t0 + max(0.0, budget)
    translate = translate or (lambda lines, dl: batch_translate(lines, dl))
    stats: Dict[str, Any] = {"candidates": len(candidates)}
    units = [i for i in (content.get("items") or []) if isinstance(i, dict)]
    unit_ids = {str(i.get("event_id") or "") for i in units}
    unit_heads = [clean_headline(i.get("headline_en")) for i in units]

    from pipeline.freshness import filter_fresh
    from pipeline.news_filters import is_opinion, rare_entities, repair_headline
    seen_ids, pool = set(), []
    for it in sorted((c for c in candidates if isinstance(c, dict)), key=_relevance, reverse=True):
        eid = str(it.get("event_id") or "")
        if eid and (eid in unit_ids or eid in seen_ids):
            continue
        seen_ids.add(eid)
        if is_opinion(it):
            continue
        fixed = repair_headline(it)
        if not fixed:
            continue  # truncated headline with no full title to repair it from
        if fixed != (it.get("headline_en") or it.get("title")):
            it = dict(it, headline_en=fixed)
        if _bad_candidate(it):
            continue
        pool.append(it)
    pool, stale = filter_fresh(pool, job_date)  # months-old news (MSP of May, a Feb Budget) is not a Quick Bite
    stats["stale_dropped"] = len(stale)
    rare = rare_entities([clean_headline(it.get("headline_en") or it.get("title")) for it in pool]
                         + [h for h in unit_heads if h])

    # ---- Agriculture Corner ------------------------------------------------
    agri_pool = [it for it in pool if is_agri(it)]
    agri_new = _pick(agri_pool, unit_heads, AGRI_MAX, rare=rare)
    agri_unit_rows = []
    for u in units:
        if is_agri(u) and len(agri_unit_rows) + len(agri_new) < AGRI_MAX + 2:
            en = clean_headline(u.get("headline_en"))
            hi = re.sub(r"^\s*(?:>>|>)\s*", "", _norm(u.get("headline_hi")))
            ol = next((o for o in content.get("one_liners") or [] if isinstance(o, dict)
                       and o.get("event_id") == u.get("event_id")), None)
            if en and hi and re.search(r"[\u0900-\u097F]", hi):
                agri_unit_rows.append({"en": en.rstrip(".") + ".", "hi": hi.rstrip("।. ") + "।",
                                       "event_id": u.get("event_id"), "from_unit": True})

    # ---- Quick Bites pool (non-agri, relevance floor) -----------------------
    qb_pool = [it for it in pool if not is_agri(it) and _relevance(it) >= MIN_RELEVANCE]
    if len(qb_pool) < QB_MIN:  # thin day: relax the floor rather than ship a short section
        qb_pool = [it for it in pool if not is_agri(it)]
    agri_heads = [clean_headline(a.get("headline_en") or a.get("title")) for a in agri_new]
    qb_cands = _pick(qb_pool, unit_heads + agri_heads, QB_MAX + 8, rare=rare)

    # ---- one batched, validated translation pass ---------------------------
    rows_qb = [(it, two_line_text(it)) for it in qb_cands]
    rows_ag = [(it, two_line_text(it, 300)) for it in agri_new]
    lines = [t for _it, t in rows_ag + rows_qb if t]
    hi_map: Dict[str, str] = {}
    if lines:
        try:
            hi_map = translate(lines, deadline) or {}
        except Exception as exc:
            logger.warning("[AutoSections] translation failed: %s", exc)
            hi_map = {}

    def _hi(en: str) -> str:
        hi = _norm(hi_map.get(en, ""))
        return hi if hi and _valid_hindi(en, hi) else ""

    bites, dropped = [], 0
    for it, en in rows_qb:
        hi = _hi(en) if en else ""
        if not hi:
            dropped += 1
            continue
        cat = quick_bite_category(it)
        bites.append({"category_en": cat, "category_hi": _CAT_HI[cat], "en": en, "hi": hi,
                      "event_id": it.get("event_id")})
        if len(bites) >= QB_MAX:
            break
    bites.sort(key=lambda b: _CAT_ORDER.get(b["category_en"], 99))  # stable: relevance order within a band
    agri_items = []
    for it, en in rows_ag:
        hi = _hi(en) if en else ""
        if hi:
            agri_items.append({"en": en, "hi": hi, "event_id": it.get("event_id")})
        else:
            dropped += 1
    agri_items = [a for a in agri_items + agri_unit_rows if not _garbled_agri(a.get("en"))][:AGRI_MAX]

    if bites:
        content["quick_bites"] = bites
    else:
        content.pop("quick_bites", None)
    if agri_items:
        texts = [a["en"] for a in agri_items]
        content["agri_corner"] = {"items": agri_items, "static_gk": agri_static_gk(texts)}
    else:
        content.pop("agri_corner", None)
    stats.update(quick_bites=len(bites), agri_items=len(agri_items), translation_requested=len(lines),
                 translated=len(hi_map), dropped_no_hindi=dropped,
                 seconds=round(time.monotonic() - t0, 1),
                 categories={c: sum(1 for b in bites if b["category_en"] == c) for c, _h in CATEGORIES})
    if 0 < len(bites) < QB_MIN:
        logger.warning("[AutoSections] only %d Quick Bites (target %d-%d)", len(bites), QB_MIN, QB_MAX)
    content["auto_sections_stats"] = stats
    return stats


def trim_quick_bites(content: Dict[str, Any], keep: int) -> int:
    """Keep the first *keep* bites per category order (used when the PDF is over the page cap)."""
    bites = content.get("quick_bites") or []
    if keep >= len(bites):
        return len(bites)
    # Drop from the tail of each band evenly: keep the best (earliest) items per category.
    by_cat: Dict[str, List[Dict[str, Any]]] = {}
    for b in bites:
        by_cat.setdefault(str(b.get("category_en")), []).append(b)
    kept: List[Dict[str, Any]] = []
    while len(kept) < keep and any(by_cat.values()):
        for k in list(by_cat):
            if by_cat[k] and len(kept) < keep:
                kept.append(by_cat[k].pop(0))
    order = {id(b): i for i, b in enumerate(bites)}
    content["quick_bites"] = sorted(kept, key=lambda b: order[id(b)])
    return len(content["quick_bites"])
