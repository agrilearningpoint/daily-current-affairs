"""Weekly / monthly editions built from the already-published DAILY editions.

The daily pipeline stays the single place where news is collected, verified,
translated and turned into MCQs.  Weekly and monthly editions only *re-use* the
daily editions' content + MCQ JSON (fetched by scripts/fetch_daily_editions.py
into ``data/period_sources/daily_<date>.json``), so they never re-generate or
re-translate anything:

1. load every daily edition of the period (fail-soft: missing days are skipped);
2. keep only publishable items (``needs_review is False`` and
   ``verification_passed is True``, a real headline, Devanagari Hindi);
3. dedupe across days (same ``event_id``, headline similarity > 0.8, or a
   similar headline naming the same people/places — see ``same_event``);
4. map categories onto the period sections, rank by importance and pick the
   stories, MCQs, one-liners, Agriculture Corner and (monthly) quick tables;
5. rebuild each story's summary bullets as whole sentences of that story's
   own text (never the daily's character-cut key points), drop generic filler
   shared by more than two stories and any line already printed in the
   edition (similarity > 0.85), and print each Static GK fact once.

Outputs (same artifacts the downstream 17c/18/19/22 stages read):
``data/scored/<job>.json``, ``data/selected/<job>.json``,
``data/content/<job>.json`` and ``data/mcq/<job>.json`` (a list).
"""
from __future__ import annotations

import json
import os
import re
from datetime import date, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from pipeline.text_normalize import (caption_residue, exact_money, publish_date, resolve_weekdays,
                                     strip_source_tags, tidy)

ROOT = Path(__file__).resolve().parent.parent
SOURCES_DIRNAME = "data/period_sources"

DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
_PREFIX_RE = re.compile(r"^(?:\s|&gt;|>)+")
_UNTITLED_RE = re.compile(r"\buntitled\b", re.IGNORECASE)

# Section order of the weekly / monthly editions.
SECTIONS: List[str] = [
    "National", "International", "Economy", "Defence & Science", "Agriculture",
    "Appointments & Awards", "Sports", "Important Days",
]
SECTION_HI: Dict[str, str] = {
    "National": "राष्ट्रीय", "International": "अंतरराष्ट्रीय", "Economy": "अर्थव्यवस्था",
    "Defence & Science": "रक्षा एवं विज्ञान", "Agriculture": "कृषि",
    "Appointments & Awards": "नियुक्तियाँ एवं पुरस्कार", "Sports": "खेल",
    "Important Days": "महत्वपूर्ण दिवस",
}

# Monthly quick tables (title, Hindi title, keyword regex on the English text).
QUICK_TABLES: List[Tuple[str, str, re.Pattern]] = [
    ("Appointments", "नियुक्तियाँ", re.compile(r"\b(appoint\w*|named|takes? charge|sworn|elected|new (chief|head|director|governor|chairman|ceo))\b", re.I)),
    ("Awards", "पुरस्कार", re.compile(r"\b(award\w*|prize|honou?r(ed)?|conferred|medal for)\b", re.I)),
    ("Important Days", "महत्वपूर्ण दिवस", re.compile(r"\b(day|diwas|divas|week|observed|anniversary|jayanti)\b", re.I)),
    ("MoUs & Agreements", "समझौता ज्ञापन", re.compile(r"\b(mou|memorandum|agreement|pact|signs?|signed|partnership)\b", re.I)),
    ("Schemes", "योजनाएँ", re.compile(r"\b(scheme|yojana|mission|programme|program|abhiyan|initiative)\b", re.I)),
    ("Reports & Rankings", "रिपोर्ट एवं रैंकिंग", re.compile(r"\b(report|index|ranking|ranked|survey|rank)\b", re.I)),
    ("Sports", "खेल", re.compile(r"\b(wins?|won|gold|silver|bronze|champion\w*|cup|tournament|olympic|games|medal)\b", re.I)),
    ("Obituaries", "निधन", re.compile(r"\b(passes away|passed away|dies|died|death of|obituary|demise)\b", re.I)),
]

SETTINGS = {
    "weekly": {"min_days": 3, "stories": 25, "per_section": 6, "mcqs": 50, "one_liners": 40,
               "agri": 10, "agri_gk": 6, "table_rows": 0},
    "monthly": {"min_days": 10, "stories": 56, "per_section": 12, "mcqs": 100, "one_liners": 80,
                "agri": 16, "agri_gk": 8, "table_rows": 12},
}


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def clean_headline(text: Any) -> str:
    s = re.sub(r"<[^>]+>", " ", str(text or ""))
    s = _PREFIX_RE.sub("", s)
    return re.sub(r"\s+", " ", s).strip()


def has_devanagari(text: Any) -> bool:
    return bool(DEVANAGARI_RE.search(str(text or "")))


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^0-9a-z\u0900-\u097f]+", " ", (text or "").lower())).strip()


def similar(a: str, b: str) -> float:
    return SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def is_similar(a: str, b: str, threshold: float = 0.8) -> bool:
    """similar(a, b) > threshold, with the cheap upper bounds checked first."""
    sm = SequenceMatcher(None, _norm(a), _norm(b))
    return sm.real_quick_ratio() > threshold and sm.quick_ratio() > threshold and sm.ratio() > threshold


_KEYWORD_SECTIONS: List[Tuple[str, re.Pattern]] = [
    ("Important Days", re.compile(r"\b(?:international|world|national)\s+[\w\s'’-]{0,40}\bday\b|\bdiwas\b|\bday\s+(?:is\s+)?observed\b", re.I)),
    ("Appointments & Awards", re.compile(r"\b(?:appointed|appoints|takes\s+charge|sworn\s+in|named\s+(?:as\s+)?(?:new|chief|head)|"
                                         r"awarded|award|prize|conferred|honoured|honored)\b", re.I)),
    ("Sports", re.compile(r"\b(?:cricket|hockey|football|olympics?|medal|tournament|championship|world\s+cup|"
                          r"grand\s+slam|chess|badminton|wrestling|athlete|t20|odi|test\s+match)\b", re.I)),
    ("Defence & Science", re.compile(r"\b(?:isro|drdo|satellite|missile|navy|naval|army|air\s+force|iaf|defence|defense|"
                                     r"orbit|rocket|launch\s+vehicle|gslv|pslv|space|scientists?|research(?:ers)?|"
                                     r"vaccine|climate|species)\b", re.I)),
    ("Economy", re.compile(r"\b(?:rbi|gdp|inflation|repo|bank(?:s|ing)?|gst|tax|exports?|imports?|trade|fdi|investment|"
                           r"market|sebi|budget|fiscal|economy|economic|rupee|ipo|manufacturing\s+facility)\b", re.I)),
    ("Agriculture", re.compile(r"\b(?:farmers?|agri\w*|crops?|kharif|rabi|msp|paddy|wheat|fisher\w*|dairy|"
                               r"livestock|horticulture|icar|nabard|fertili[sz]er|irrigation)\b", re.I)),
    ("International", re.compile(r"\b(?:bilateral|foreign\s+office|state\s+visit|joint\s+statement|summit|"
                                 r"united\s+nations|\bun\b|g20|brics|quad|asean|embassy)\b", re.I)),
]


# Natural disasters (cyclone damage, floods) are National news, not Defence & Science.
_DISASTER_RE = re.compile(r"\b(?:cyclone|cyclonic|earthquake|floods?|landslides?|cloudburst|tsunami|heatwave)\b", re.I)
_ECON_TERMS_RE = re.compile(r"\b(?:rbi|reserve\s+bank|gdp|inflation|repo|banks?|banking|lender|loans?|credit|gst|tax\w*|"
                            r"exports?|imports?|trade|tariffs?|fdi|invest\w*|market|sebi|budget|fiscal|econom\w*|"
                            r"rupee|ipo|crore|lakh|billion|million|\$|₹|rs\.?|statistic\w*|survey|insurance|"
                            r"lng|oil|gas|fund\w*|scheme)\b", re.I)

_POLITY_RE = re.compile(r"\b(?:ncsc|ncst|nhrc|ncw|national\s+commission\s+for\s+(?:scheduled|women|minorities)|"
                        r"scheduled\s+(?:castes?|tribes?)|lok\s+sabha|rajya\s+sabha|election\s+commission|"
                        r"supreme\s+court|high\s+court|constitution\w*)\b", re.I)
_INDIA_INVEST_RE = re.compile(r"\b(?:to\s+invest|invests?|investment|fdi|bank(?:s|ing)?|lender|financial\s+services)\b"
                              r".{0,60}\bindia\b|\bindia\b.{0,60}\b(?:investment|fdi|banking\s+business)", re.I)
_DIPLOMATIC_RE = re.compile(r"\b(?:bilateral|summit|joint\s+statement|state\s+visit|ambassador|foreign\s+secretary|"
                            r"external\s+affairs|trade\s+(?:deal|pact|agreement|talks|negotiations?|policy)|tariffs?|"
                            r"midterms?|election)\b", re.I)


def _agri_evidence(item: Dict[str, Any]) -> bool:
    """Real agriculture terms ("farm" or "trade" alone are not enough): one in the
    headline, or three different ones in the opening text."""
    from pipeline.exam_relevance import agri_terms
    head = str(item.get("headline_en") or "")
    if agri_terms(event_title(head)):
        return True
    body = " ".join(str(item.get(k) or "") for k in ("summary_en", "detailed_explanation_en"))[:600]
    return agri_terms(body) >= 3


def section_for(item: Dict[str, Any]) -> str:
    """Map a daily category onto a period section; generic categories are refined by headline keywords.

    Agriculture needs real agri terms (India-US trade and NCSC stories were filed
    under it); bank credit to agriculture (RBI agri-infra PSL limit) is Agriculture;
    a foreign bank's India investment (Barclays) is Economy; statutory
    commissions (NCSC/NHRC) are National."""
    from pipeline.exam_relevance import BANK_AGRI_RE, agri_terms
    cat = str(item.get("category") or "").lower()
    head = f"{item.get('headline_en', '')}"
    if "important day" in cat:
        return "Important Days"
    if "sport" in cat:
        return "Sports"
    if any(k in cat for k in ("appoint", "award", "person", "obituar")):
        return "Appointments & Awards"
    if BANK_AGRI_RE.search(head) and agri_terms(head):
        return "Agriculture"              # RBI / NABARD credit to agriculture
    agri_cat = any(k in cat for k in ("agri", "rural", "farm", "fisher", "animal", "food"))
    if agri_cat and _agri_evidence(item):
        return "Agriculture"
    if _POLITY_RE.search(head):
        return "National"
    if _DISASTER_RE.search(head):
        return "International" if _foreign(head) else "National"
    if any(k in cat for k in ("defence", "defense", "science", "tech", "space", "environment", "health")):
        return "Defence & Science"
    if _INDIA_INVEST_RE.search(head) and not _DIPLOMATIC_RE.search(head):
        return "Economy"
    if any(k in cat for k in ("econom", "bank", "financ", "business", "budget", "trade", "market")):
        if _foreign(head) and (_DIPLOMATIC_RE.search(head) or not re.search(r"\bindia", head, re.I)):
            return "International"      # a foreign story with no India angle (Pakistan LNG, Ukraine strikes)
        if _ECON_TERMS_RE.search(head):
            return "Economy"
        # filed under an economy category without economy content (exam-reform panel)
    international = any(k in cat for k in ("international", "world", "global", "foreign")) or \
        (agri_cat and _foreign(head))
    for sec, rx in _KEYWORD_SECTIONS:
        if sec == "Agriculture" and not _agri_evidence(item):
            continue
        if rx.search(head) and not (international and sec in ("Economy", "Agriculture")):
            return sec
    return "International" if international else "National"


def _foreign(text: str) -> bool:
    try:
        from pipeline.collector import FOREIGN_RE
    except Exception:  # pragma: no cover
        return False
    return bool(FOREIGN_RE.search(text or ""))


# Notice-board / document titles that sometimes slip through a daily edition.
# The daily filters (pipeline.news_filters) run first; these catch the rest so a
# weekly/monthly digest never amplifies them.
_NOTICE_RE = re.compile(
    r"\b(?:bid\s+number|tender\s+no|gem/\d{4}|apply\s+online|application\s+form|application\s+for\s+the\s+post|"
    r"young\s+professional|advertisement\s+no|notification\s+no|walk[-\s]?in|last\s+date\s+for|"
    r"syllabus|result\s+(?:of|for)\s+the|merit\s+list|training\s+programme\s+on|e-?auction)\b"
    r"|^(?:department|division|directorate|office)\s+of\b[^,:;]*$"
    r"|^[^:|]{2,45}:\s+on\s+"  # editorial titles ("Beyond gullibility: On ...")
    r"|\b(?:fifty|hundred|seventy-five)\s+years\s+ago\b",
    re.IGNORECASE,
)


def looks_like_news(headline: str) -> bool:
    """Reject notice-board titles and garbled PDF extraction in an English headline."""
    from pipeline.news_filters import is_non_news
    h = clean_headline(headline)
    if is_non_news(h) or _NOTICE_RE.search(h) or has_devanagari(h) or re.search(r"[~{}\\]", h):
        return False
    letters = sum(ch.isalpha() for ch in h)
    return len(h) > 0 and letters / len(h) >= 0.6


def is_publishable(item: Any, require_verified: bool = True) -> bool:
    """Mirror of the publisher gate with ALP_ALLOW_FALLBACK_TRANSLATION=0, plus real text.

    ``require_verified=False`` only for DRY_RUN, where the publisher skips the
    same gate (offline fixtures have no live verification)."""
    if not isinstance(item, dict):
        return False
    if require_verified and (item.get("needs_review") is not False or item.get("verification_passed") is not True):
        return False
    head = clean_headline(item.get("headline_en"))
    if not head or _UNTITLED_RE.search(head) or len(head.split()) < 3:
        return False
    hi = clean_headline(item.get("headline_hi"))
    if not hi or not has_devanagari(hi) or _UNTITLED_RE.search(hi):
        return False
    return True


_BLOCKLIST_PATH = ROOT / "config" / "period_blocklist.json"


def _blocklist() -> List[re.Pattern]:
    """Editor vetoes for period editions (stale/republished events): headline regexes."""
    try:
        data = json.loads(_BLOCKLIST_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    out = []
    for row in data.get("headline_patterns") or []:
        pat = row.get("pattern") if isinstance(row, dict) else row
        try:
            out.append(re.compile(str(pat), re.I))
        except re.error:
            continue
    return out


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def period_dates(job_type: str, job_date: str) -> List[str]:
    from pipeline.windows import collect_window
    start, end = collect_window(job_type, job_date)
    d, out = start.date(), []
    while d <= end.date():
        out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def load_daily_editions(dates: Iterable[str], root: Path = ROOT) -> List[Dict[str, Any]]:
    """[{date, content, mcqs}] for every day that has a readable edition (others skipped)."""
    src_dir = Path(os.getenv("ALP_PERIOD_SOURCES_DIR") or (root / SOURCES_DIRNAME))
    out = []
    for d in dates:
        content, mcqs = None, []
        packed = _read_json(src_dir / f"daily_{d}.json")
        if isinstance(packed, dict) and isinstance(packed.get("content"), dict):
            content, mcqs = packed["content"], packed.get("mcqs") or []
        else:  # a local checkout that still has the daily run's data/
            content = _read_json(root / "data" / "content" / f"daily_{d}.json")
            m = _read_json(root / "data" / "mcq" / f"daily_{d}.json")
            mcqs = m.get("mcqs", []) if isinstance(m, dict) else (m or [])
        if not isinstance(content, dict) or not isinstance(content.get("items"), list):
            continue
        out.append({"date": d, "content": content, "mcqs": [x for x in mcqs if isinstance(x, dict)]})
    return out


# --------------------------------------------------------------------------- #
# Selection
# --------------------------------------------------------------------------- #
def _story(item: Dict[str, Any], day: str) -> Dict[str, Any]:
    it = dict(item)
    it["headline_en"] = clean_headline(item.get("headline_en"))
    it["headline_hi"] = clean_headline(item.get("headline_hi"))
    it["edition_date"] = day
    it["section"] = section_for(it)
    if not it.get("event_id"):
        it["event_id"] = f"{day}:{_norm(it['headline_en'])[:60]}"
    from pipeline.exam_relevance import exam_score, is_boosted
    it["exam_score"] = exam_score(it)
    it["exam_boosted"] = is_boosted(it)
    return it


def _period_bounds(editions: List[Dict[str, Any]], period: Optional[Tuple[str, str]]) -> Tuple[str, str]:
    if period:
        return period
    days = sorted(e["date"] for e in editions if e.get("date"))
    return (days[0], days[-1]) if days else ("", "")


_STATE_DESK_RE = re.compile(r"thehindu\.com/news/(?:cities|national/(?!world)[a-z-]+)/", re.I)


def local_story_reason(it: Dict[str, Any]) -> str:
    """A state/city-desk report (a college training camp, a local protest, a rally speech)
    is not weekly exam news unless it is agricultural or an official/national decision."""
    from pipeline.exam_relevance import AGRI_MINISTRY_RE, CABINET_RE, agri_terms
    src = it.get("source") if isinstance(it.get("source"), dict) else {}
    url = str(src.get("url") or it.get("source_url") or it.get("link") or "")
    if not _STATE_DESK_RE.search(url):
        return ""
    head = str(it.get("headline_en") or "")
    if agri_terms(head) or AGRI_MINISTRY_RE.search(head) or CABINET_RE.search(head) \
            or re.search(r"\b(?:supreme\s+court|high\s+court|election\s+commission|rbi|isro|drdo|icar)\b", head, re.I):
        return ""
    return "state/city-desk local news"


def collect_verified(editions: List[Dict[str, Any]], period: Optional[Tuple[str, str]] = None
                     ) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Publishable, fresh, exam-relevant stories of the period (the dailies' printed
    stories and their prepared reserve stories), deduped at event level and ranked
    by exam score."""
    from pipeline.exam_relevance import drop_reason
    from pipeline.freshness import period_stale_reason
    stats = {"days": len(editions), "items_seen": 0, "unverified_dropped": 0, "non_news_dropped": 0,
             "duplicates_dropped": 0, "stale_dropped": 0, "irrelevant_dropped": 0, "reserve_candidates": 0}
    pool: List[Dict[str, Any]] = []
    strict = os.getenv("DRY_RUN", "0") != "1"
    blocked = _blocklist()
    start, end = _period_bounds(editions, period)
    drops: List[Dict[str, str]] = []
    for ed in editions:
        printed = [(x, False) for x in ed["content"].get("items") or []]
        reserve = [(x, True) for x in ed["content"].get("reserve_items") or [] if isinstance(x, dict)]
        for raw, is_reserve in printed + reserve:
            stats["items_seen"] += 1
            if not is_publishable(raw, require_verified=strict):
                stats["unverified_dropped"] += 1
                continue
            if not looks_like_news(raw.get("headline_en")):
                stats["non_news_dropped"] = stats.get("non_news_dropped", 0) + 1
                continue
            if any(b.search(clean_headline(raw.get("headline_en"))) for b in blocked):
                stats["blocklisted_dropped"] = stats.get("blocklisted_dropped", 0) + 1
                continue
            it = _story(raw, ed["date"])
            why = drop_reason(it) or local_story_reason(it)
            if why:
                stats["irrelevant_dropped"] += 1
                drops.append({"headline": it["headline_en"][:90], "reason": why})
                continue
            if start and end:
                why = period_stale_reason(it, start, end)
                if why:
                    stats["stale_dropped"] += 1
                    drops.append({"headline": it["headline_en"][:90], "reason": f"stale: {why}"})
                    continue
                _set_event_day(it, start, end)
            if is_reserve:
                it["from_reserve"] = True
                stats["reserve_candidates"] += 1
            pool.append(it)
    stats["drop_log"] = drops[:60]
    return dedupe(pool, stats), stats


def _set_event_day(it: Dict[str, Any], start: str, end: str) -> None:
    """Date the story by its event (\"on Thursday\" -> that Thursday), not by the
    daily edition that carried it; kept only when the event falls in the period."""
    from pipeline.freshness import event_date
    try:
        ed = event_date(it, date.fromisoformat(it["edition_date"]))
    except (KeyError, ValueError):
        return
    if ed and start <= ed.isoformat() <= end and ed.isoformat() != it["edition_date"]:
        it["published_edition_date"] = it["edition_date"]
        it["edition_date"] = ed.isoformat()


def _rank_key(it: Dict[str, Any]) -> Tuple[float, str]:
    """Exam score (importance + agri/banking boost) when known, else importance."""
    try:
        score = float(it.get("exam_score") if it.get("exam_score") is not None else it.get("importance_score") or 0)
    except (TypeError, ValueError):
        score = 0.0
    return (score, it.get("edition_date", ""))


_STOP_ENT = {"The", "A", "An", "In", "On", "At", "Of", "For", "To", "And", "With", "By", "From", "As", "After",
             "Over", "Amid", "Its", "His", "Her", "New", "India", "Indian", "Govt", "Government", "Centre", "State",
             "States", "Minister", "Chief", "President", "Says", "Said", "Report", "Day", "Mr", "Ms", "Dr"}


_SITE_SUFFIX_RE = re.compile(r"\s+[-–|]\s+[^-–|]{2,90}$")
_SITE_WORDS_RE = re.compile(r"(?i)\b(?:ministry|department|government|authority|commission|pib|pm\s+india|"
                            r"institute|council|board|organisation|organization)\b")


def event_title(text: Any) -> str:
    """Headline without a trailing "- Ministry of External Affairs , Government of India" site suffix."""
    t = clean_headline(text)
    m = _SITE_SUFFIX_RE.search(t)
    if m and _SITE_WORDS_RE.search(m.group(0)) and m.start() > 15:
        t = t[:m.start()]
    return t


_MONTHS = {"january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
           "november", "december"}


_GENERIC_ENT = {"affairs", "external", "of", "india", "shri", "smt", "h.e", "mr", "briefing", "special", "visit",
                "statement", "joint", "transcript", "mea", "official", "state", "press", "release", "pm", "union",
                "national", "first", "meeting", "conference", "address", "remarks"}


def entities(it: Dict[str, Any]) -> set:
    """Proper nouns, acronyms and numbers of the headline + first summary sentence."""
    head = event_title(it.get("headline_en"))
    first = (split_sentences(clean_source_text(it.get("summary_en"))) or [""])[0]
    first = "" if _norm(first).startswith(_norm(head)[:40]) else first
    toks = re.findall(r"[A-Z][A-Za-z&’'.-]+|\d[\d,.]*%?", f"{head} {first}")
    out = set()
    for t in toks:
        t = t.strip(".,’'-")
        low = t.lower()
        if not t or t in _STOP_ENT or low in _MONTHS or _SITE_WORDS_RE.fullmatch(t) \
                or low in _GENERIC_ENT or re.fullmatch(r"(?:19|20)\d\d", t):
            continue
        out.add(low)
    return out


def same_event(a: Dict[str, Any], b: Dict[str, Any], threshold: float = 0.8) -> bool:
    """Same event_id, near-identical headline, or (across days) a similar headline
    that names the same people/places/numbers."""
    if a.get("event_id") and a.get("event_id") == b.get("event_id"):
        return True
    if same_topic_event(a, b):
        return True
    ha, hb = a.get("headline_en", ""), b.get("headline_en", "")
    if is_similar(ha, hb, threshold):
        return True
    ha, hb = event_title(ha), event_title(hb)
    if is_similar(ha, hb, threshold):
        return True
    sim = similar(ha, hb)
    if sim < 0.3:
        return False
    ea, eb = a.get("_ents") or entities(a), b.get("_ents") or entities(b)
    shared = ea & eb
    ratio = len(shared) / max(1, min(len(ea), len(eb)))
    ca, cb = _content_words(ha), _content_words(hb)
    words = len(ca & cb) / max(1, len(ca | cb))
    # Similar wording + the same names + the same subject matter (so "NABARD
    # launches X in Odisha" and "NABARD launches Y in Odisha" stay two stories).
    return ((len(shared) >= 2 and sim >= 0.5 and ratio >= 0.5 and words >= 0.4)
            or (len(shared) >= 3 and ratio >= 0.66 and words >= 0.3))


# Subject keys of an event: two stories about the same subject, place/body and
# days are one event even when different people comment on it (Stalin and
# Palaniswami on Tamil Nadu's October GST growth, both 2 Nov).
_TOPIC_KEYS = re.compile(
    r"\b(?:gst|msp|repo\s+rate|inflation|cpi|wpi|gdp|iip|pmi|forex|fdi|exports?|imports?|monsoon|cyclone|"
    r"earthquake|floods?|budget|tariffs?|trade\s+deal|kcc|kisan\s+credit|pmmsy|pm-?kisan|pmfby|omss|"
    r"maize\s+conference|khet\s+bachaa?o|semicon\w*|agniveer|vistar|surya\s+ghar|corvettes?|torpedo\w*|"
    r"organic\s+fisheries|hackathon|carbon\s+market\w*|kiwi|elections?|polls?|summit)\b", re.I)
_PLACE_STOP = {"india", "indian", "new", "delhi", "union", "centre", "government", "minister", "ministry", "chief",
               "state", "national", "president", "prime", "rs", "crore", "lakh", "per", "cent"}


def _topic_keys(it: Dict[str, Any]) -> set:
    text = f"{event_title(it.get('headline_en'))} {(split_sentences(clean_source_text(it.get('summary_en'))) or [''])[0]}"
    return {re.sub(r"\s+", " ", m.group(0).lower()).rstrip("s") for m in _TOPIC_KEYS.finditer(text)}


def same_topic_event(a: Dict[str, Any], b: Dict[str, Any], max_days: int = 3) -> bool:
    """Same subject (topic key) + the same named place/body + within ``max_days``."""
    try:
        gap = abs((date.fromisoformat(a.get("edition_date", "")[:10]) -
                   date.fromisoformat(b.get("edition_date", "")[:10])).days)
    except ValueError:
        gap = 0
    if gap > max_days:
        return False
    ta, tb = _topic_keys(a), _topic_keys(b)
    if not (ta & tb):
        return False
    ea, eb = a.get("_ents") or entities(a), b.get("_ents") or entities(b)
    def norm(ents: set) -> set:
        return {re.sub(r"[’']s$", "", e) for e in ents}
    shared = {e for e in (norm(ea) & norm(eb)) if e not in _PLACE_STOP and not re.fullmatch(r"[\d,.%]+", e)}
    shared -= {k for k in ta & tb}
    if len(shared) >= 2:
        return True
    return len(shared) >= 1 and (gap <= 1 or len(ta & tb) >= 2)


_WORD_STOP = {"with", "from", "that", "this", "over", "after", "into", "their", "will", "have", "says", "said",
              "about", "under", "amid", "more", "than", "india", "indian", "ministry", "external", "affairs",
              "government", "october", "november", "december", "september", "2026", "2025", "2027"}


def _content_words(title: str) -> set:
    return {w for w in _norm(title).split() if len(w) >= 4 and w not in _WORD_STOP}


def dedupe(items: List[Dict[str, Any]], stats: Optional[Dict[str, int]] = None,
           threshold: float = 0.8) -> List[Dict[str, Any]]:
    """Same event (see same_event) → keep the higher-ranked copy."""
    kept: List[Dict[str, Any]] = []
    for it in sorted(items, key=_rank_key, reverse=True):
        it["_ents"] = entities(it)
        if any(same_event(it, k, threshold) for k in kept):
            if stats is not None:
                stats["duplicates_dropped"] = stats.get("duplicates_dropped", 0) + 1
            continue
        kept.append(it)
    for it in kept:
        it.pop("_ents", None)
    return kept


def pick_stories(ranked: List[Dict[str, Any]], total: int, per_section: int,
                 accept: Optional[Any] = None) -> List[Dict[str, Any]]:
    """Top stories by exam score with a per-section cap, returned in section order.

    ``accept(story) -> bool`` is asked before a story is taken (it rebuilds or
    fetches a missing body); a refused story is skipped and the next-ranked one
    is promoted in its place, so the edition never prints a headline-only story."""
    chosen: List[Dict[str, Any]] = []
    counts: Dict[str, int] = {}
    refused: set = set()

    def ok(it: Dict[str, Any]) -> bool:
        if id(it) in refused:
            return False
        if accept is None or accept(it):
            return True
        refused.add(id(it))
        return False

    # Every section that has news gets its best story first, then importance decides.
    for sec in SECTIONS:
        for x in ranked:
            if len(chosen) >= total:
                break
            if x["section"] == sec and ok(x):
                chosen.append(x)
                counts[sec] = 1
                break
    picked = {id(x) for x in chosen}
    for it in ranked:
        if len(chosen) >= total:
            break
        if id(it) in picked or counts.get(it["section"], 0) >= per_section:
            continue
        if not ok(it):
            continue
        counts[it["section"]] = counts.get(it["section"], 0) + 1
        chosen.append(it)
        picked.add(id(it))
    if len(chosen) < total:  # caps left room: fill with the best remaining stories
        for x in ranked:
            if len(chosen) >= total:
                break
            if id(x) not in picked and ok(x):
                chosen.append(x)
                picked.add(id(x))
    order = {s: i for i, s in enumerate(SECTIONS)}
    return sorted(chosen, key=lambda x: (order.get(x["section"], 99), -_rank_key(x)[0]))


_LETTERS = "ABCDE"


# Template fallback questions whose "answer" is a guess, not a fact from the story
# (e.g. "Which organisation is associated with the news ..." -> ICAR for an MSP story).
# Kept only when the story itself names the keyed answer.
_TEMPLATE_Q_RE = re.compile(
    r"(?i)^which organi[sz]ation is associated with the news"
    r"|is related to which state\s*/\s*union territory|involves which country")
# Never kept: built from boilerplate, not from the story.
_JUNK_Q_RE = re.compile(
    r"(?i)what is the key figure\s*/\s*financial outlay associated with"
    r"|\bPIB (?:updates|release)\b.*\b(?:alongside|along with)\b"
    r"|along with regulator guidelines"
    r"|highlighted in the recent PIB release"
    r"|\bcultivars (?:are|is) (?:mentioned|highlighted)\b|organi[sz]ation's cultivars")


# Fragments of the feed's category blurbs (pipeline.content.EXAM_HINTS): an MCQ whose
# question / options / explanation / exam point quotes them was built from the blurb,
# not from the news ("RBI Nagpur ... regulator guidelines and PSL quotas").
_BLURB_FRAG_RE = re.compile(
    r"(?i)\b(?:PSL\)?\s+quotas?|monetary\s+policy\s+reviews|regulator(?:y)?\s+guidelines,|ICAR\s+cultivars|"
    r"MSP\s+notifications|key\s+crop\s+statistics|flagship\s+objectives|target\s+demographics|"
    r"implementing\s+ministries|financial\s+outlays,|macroeconomic\s+indicators,|global\s+indices|"
    r"ISRO/DRDO\s+breakthroughs|statutory\s+bodies,\s+constitutional|factual\s+metrics)")


def blurb_mcq(m: Dict[str, Any]) -> bool:
    """The blurb woven into the question (not just the verbatim blurb sentence that the
    daily appends to an explanation, which is stripped first)."""
    from pipeline.content import EXAM_HINT_DEFAULT, EXAM_HINTS
    parts = [m.get("question_en"), m.get("explanation_en"), m.get("exam_point")]
    ol = m.get("one_liner")
    parts.append(ol.get("en") if isinstance(ol, dict) else ol)
    parts += [_opt_text(o) for o in (m.get("options_bi") or m.get("options") or [])]
    text = " ".join(str(x or "") for x in parts)
    for hint in list(EXAM_HINTS.values()) + [EXAM_HINT_DEFAULT]:
        text = text.replace(hint, " ")
    return bool(_BLURB_FRAG_RE.search(text))


# Template give-aways (the stem quotes the headline that names the answer): used only to
# reach the QA floor of a thin edition, never ahead of a real question.
# The "associated with the news" / "related to which State" / "involves which country"
# templates key a guess (ICAR for a Tamil Nadu laptop scheme, RBI for a SEBI IPO nod,
# Delhi for a national panel), so they also wait for the floor - and even then only
# when the story names the keyed answer.
_WEAK_Q_RE = re.compile(r"(?i)centrally featured in|organi[sz]ation is associated with the news|"
                        r"is related to which state|involves which country")
_MCQ_FLOOR = 10


def _story_text(it: Optional[Dict[str, Any]]) -> str:
    if not it:
        return ""
    # Not exam_fact/key points/detail: for feed items those can carry the feed's own
    # category blurb ("Key crop statistics, ICAR cultivars, MSP notifications ..."),
    # which is not news and once keyed ICAR as the body behind an MSP story.
    parts = [it.get("headline_en"), it.get("summary_en"),
             " ".join(map(str, it.get("organizations") or []))]
    return " ".join(str(p) for p in parts if p)


def _answer_in_story(answer: str, story: str) -> bool:
    """The keyed option (its English name or its bracketed acronym) appears in the story."""
    en = answer.split(" / ")[0].strip()
    names = {en} | set(re.findall(r"\(([^)]+)\)", answer))
    return any(n and re.search(rf"(?<!\w){re.escape(n.strip())}(?!\w)", story, re.I) for n in names)


def _opt_text(o: Any) -> str:
    return clean_headline(o.get("en") if isinstance(o, dict) else o)


def _mcq_ok(m: Dict[str, Any], story: Optional[str] = None) -> bool:
    q_en, q_hi = clean_headline(m.get("question_en")), clean_headline(m.get("question_hi"))
    if not q_en or _UNTITLED_RE.search(q_en) or not has_devanagari(q_hi):
        return False
    if _JUNK_Q_RE.search(q_en) or blurb_mcq(m):
        return False
    opts = m.get("options_bi") or m.get("options") or []
    if len(opts) < 4:
        return False
    texts = [_norm(_opt_text(o)) for o in opts]
    if len(set(texts)) < len(texts) or not all(texts):
        return False
    correct = str(m.get("correct") or "").strip().upper()
    if correct not in _LETTERS[:len(opts)]:
        return False
    if story is not None and _TEMPLATE_Q_RE.search(q_en):
        return _answer_in_story(_opt_text(opts[_LETTERS.index(correct)]), story)
    return True


_LETTER_REF_RE = re.compile(r"\b[Oo]ption\s*[A-E]\b|\([A-E]\)|विकल्प\s*[A-E]")


def balance_answers(mcqs: List[Dict[str, Any]], seed: str) -> None:
    """Spread correct letters evenly (deterministic per edition) by swapping the
    correct option into a target slot; every option list moves in parallel."""
    import random
    movable = [m for m in mcqs
               if not _LETTER_REF_RE.search(f"{m.get('explanation_en', '')} {m.get('explanation_hi', '')}")]
    if not movable:
        return
    n_opts = min(len(m.get("options_bi") or m.get("options") or []) for m in movable)
    letters = _LETTERS[:max(4, min(5, n_opts))]
    targets = [letters[i % len(letters)] for i in range(len(movable))]
    random.Random(seed).shuffle(targets)
    for m, tgt in zip(movable, targets):
        cur = _LETTERS.index(str(m["correct"]).strip().upper())
        new = _LETTERS.index(tgt)
        lists = [k for k in ("options", "options_hi", "options_bi") if isinstance(m.get(k), list)]
        if any(new >= len(m[k]) or cur >= len(m[k]) for k in lists if m[k]):
            continue
        for k in lists:
            if m[k]:
                m[k] = list(m[k])
                m[k][cur], m[k][new] = m[k][new], m[k][cur]
        m["correct"] = tgt


def _mcq_evidence(it: Dict[str, Any]) -> str:
    """Story text an MCQ key must be found in (the daily validator's evidence + summary pairs)."""
    from pipeline.content import _evidence_text
    pairs = " ".join(str(p.get("en") or "") for p in it.get("summary_pairs") or [] if isinstance(p, dict))
    return " | ".join(x for x in (_evidence_text(it), _story_text(it), pairs) if x)


def _cross_check_text(editions: List[Dict[str, Any]], verified: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
    """Per event: the editions' one-liners and Static GK lines (an MCQ key they contradict is dropped)."""
    out: Dict[str, List[str]] = {}
    for ed in editions:
        for ol in (ed.get("content") or {}).get("one_liners") or []:
            if isinstance(ol, dict) and ol.get("event_id") in verified:
                out.setdefault(ol["event_id"], []).append(str(ol.get("text_en") or ""))
    for eid, it in verified.items():
        for p in it.get("static_gk_pairs") or []:
            en = p.get("en") if isinstance(p, dict) else (p[0] if isinstance(p, (list, tuple)) and p else "")
            if en:
                out.setdefault(eid, []).append(str(en))
    return {k: " | ".join(v) for k, v in out.items()}


def _reserve_mcqs(verified: Dict[str, Dict[str, Any]], order: List[str], cross: Dict[str, str],
                  want: int) -> List[Dict[str, Any]]:
    """Validated, hardened template questions for verified stories (selected stories first)."""
    from pipeline.content import _build_pools, _evidence_text, validate_mcqs
    from pipeline.mcq_builder import candidates_for_item
    from pipeline.mcq_quality import harden_mcq
    items = list(verified.values())
    ids = list(dict.fromkeys(list(order) + list(verified)))
    try:
        pools = _build_pools(items)
    except Exception:
        return []
    out: List[Dict[str, Any]] = []
    for eid in ids:
        it = verified.get(eid)
        if not it or len(out) >= want:
            continue
        try:
            cands = candidates_for_item(it, _evidence_text(it), pools, items, None)
        except Exception:
            continue
        for c in cands:
            if not _mcq_ok(c) or not validate_mcqs([c], [it])[0]:
                continue
            h, _why = harden_mcq(c, _mcq_evidence(it), cross.get(eid, ""), it)
            if h is not None:
                out.append(dict(h, event_id=eid, reserve=True))
    return out


def pick_mcqs(editions: List[Dict[str, Any]], verified_ids: set, story_ids: List[str],
              limit: int, verified: Optional[Dict[str, Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """MCQs of verified events only: selected stories first (round-robin), then the rest."""
    from pipeline.mcq_quality import harden_mcq
    by_event: Dict[str, List[Dict[str, Any]]] = {}
    unconfirmed: List[Dict[str, Any]] = []   # template MCQs whose key the story does not name
    cross = _cross_check_text(editions, verified) if verified is not None else {}
    for ed in editions:
        for m in ed["mcqs"]:
            if m.get("event_id") not in verified_ids or not _mcq_ok(m):
                continue
            story = _story_text((verified or {}).get(m.get("event_id"))) if verified is not None else None
            if verified is not None:
                # Hardening gates (audit 2026-11-08): key must match the story (re-key or
                # drop), grounded answer, no give-away / mixed-type options, full Hindi,
                # current officeholders.  A failed question is replaced by the next one.
                it = verified.get(m.get("event_id")) or {}
                m, why = harden_mcq(m, _mcq_evidence(it), cross.get(m.get("event_id"), ""), it)
                if m is None:
                    continue
            if _mcq_ok(m, story):
                by_event.setdefault(m["event_id"], []).append(m)
            else:
                unconfirmed.append(m)
    seen_q: List[str] = []
    out: List[Dict[str, Any]] = []

    taken_by_event: Dict[str, List[Tuple[str, str]]] = {}

    def _answer(m: Dict[str, Any]) -> str:
        opts = m.get("options_bi") or m.get("options") or []
        c = str(m.get("correct") or "").strip().upper()
        i = _LETTERS.index(c) if c in _LETTERS else -1
        return _norm(_opt_text(opts[i]).split(" / ")[0]) if 0 <= i < len(opts) else ""

    weak: List[Dict[str, Any]] = []

    def take(m: Dict[str, Any], allow_weak: bool = False) -> None:
        if not allow_weak and _WEAK_Q_RE.search(str(m.get("question_en") or "")):
            weak.append(m)
            return
        key = _norm(clean_headline(m.get("question_en")))
        if key in seen_q or any(is_similar(key, s, 0.9) for s in seen_q):
            return
        # Same event: never the same answer twice (Q13/Q48 "Skill India centre -> Bhopal"),
        # and never one question giving away another's answer ("... in Delhi" / "where?").
        ans = _answer(m)
        for q_prev, a_prev in taken_by_event.get(str(m.get("event_id")), []):
            if (ans and ans == a_prev) or (a_prev and re.search(rf"(?<!\w){re.escape(a_prev)}(?!\w)", key)) \
                    or (ans and re.search(rf"(?<!\w){re.escape(ans)}(?!\w)", q_prev)):
                return
        seen_q.append(key)
        taken_by_event.setdefault(str(m.get("event_id")), []).append((key, ans))
        out.append(dict(m))

    order = list(story_ids) + [e for e in by_event if e not in set(story_ids)]
    rnd = 0
    while len(out) < limit and any(len(by_event.get(e, [])) > rnd for e in order):
        for e in order:
            ms = by_event.get(e, [])
            if len(ms) > rnd and len(out) < limit:
                take(ms[rnd])
        rnd += 1
    # Shortfall after the hardening drops: reserve questions built fresh from the
    # verified stories (concept / bilingual templates, same validator + gates).
    if verified is not None and len(out) < limit:
        for m in _reserve_mcqs(verified, order, cross, limit - len(out) + 10):
            if len(out) >= limit:
                break
            take(m)
    # Last resort only (a thin period that would otherwise fail the MCQ minimum).
    for m in unconfirmed:
        if len(out) >= limit:
            break
        take(m)
    named = lambda m: verified is not None and _mcq_ok(m, _story_text(verified.get(m.get("event_id"))))
    for m in sorted(weak, key=lambda m: not named(m)):     # the story names the key first
        if len(out) >= min(limit, _MCQ_FLOOR):
            break
        take(m, allow_weak=True)
    for n, m in enumerate(out, 1):
        m["q_num"] = n
    return out


_KEY_TAG_RE = re.compile(r"\s*\(Key:[^)]*\)?\s*$")
_SOURCE_TAIL_RE = re.compile(r"\s+[-–|]\s+(?:PM India|PIB(?: Delhi)?|DD News|AIR News|Akashvani News|"
                             r"News On AIR|Mint|The Hindu|Business Standard|Report)\s*$", re.I)


def clean_one_liner(text: Any) -> str:
    """Drop the daily "(Key: ...)" tag and trailing source names from a revision line."""
    t = clean_headline(text)
    for _ in range(2):
        t = _KEY_TAG_RE.sub("", t)
        t = _SOURCE_TAIL_RE.sub("", t).strip()
    return t


def heading_only(en: str) -> bool:
    """A backgrounder title ("UPI: Transforming India's Payment Landscape"), not a fact."""
    if re.match(r"^[A-Z][\w\s'’&-]{2,80}\bAct,?\s+\d{4}$", en):      # a bare act name
        return True
    if re.match(r"(?i)^(?:the\s+)?new era of\b", en) and len(en.split()) <= 12:
        return True
    return bool(re.match(r"^[^:]{2,45}:\s", en)) and not re.search(r"\d", en) and len(en.split()) <= 12


_RAW_PIB_TITLE_RE = re.compile(r"^(?:PM['’]s|Prime\s+Minister['’]s|President['’]s|Vice\s+President['’]s|Text\s+of|"
                               r"English\s+rendering|Transcript)\b.{0,20}\b(?:address|remarks|speech|statement)\b", re.I)
_VERB_RE = re.compile(r"\b(?:is|are|was|were|has|have|had|will|would|can|may|be|been|being|"
                      r"[a-z]{2,}(?:ed|es|ing)|[a-z]{2,}[^s\W]s)\b")
_REPEAT_JOIN_RE = re.compile(r"\b([A-Z][\w.]{2,})\.\s+\1\b")


def garbled(text: Any) -> bool:
    """Scraper joins and broken sentences: a name repeated across a sentence break
    ("... E.V. Velu. Velu for the party's ..."), unbalanced quotes, glued texts,
    a lowercase start or a photo-caption residue."""
    t = str(text or "").strip()
    if not t:
        return True
    if _REPEAT_JOIN_RE.search(t) or run_on(t) or t[:1].islower():
        return True
    if t.count("“") != t.count("”") or t.count('"') % 2:
        return True
    return bool(re.search(r"\b[A-Z]\.\s+Photo\b|\bPhoto\s*:\s|\bFile\s+photo\b", t))


def fact_line_ok(en: str) -> bool:
    """A one-liner / Agri-corner line must state a fact: a sentence with a verb,
    not a heading ("Academic Bank of Credits and APAAR", "Khet Bachaao Abhiyaan -
    Rabi 2026.") or a raw PIB title ("PM's address at the inauguration of ...")."""
    en = (en or "").strip()
    if len(en.split()) < 6 or _RAW_PIB_TITLE_RE.search(en) or garbled(en):
        return False
    return bool(_VERB_RE.search(en))


def _line_dropped(en: str, day: str, period: Optional[Tuple[str, str]], blocked: List[re.Pattern]) -> str:
    """Why a revision line is not printed ("" = keep)."""
    from pipeline.exam_relevance import drop_reason
    from pipeline.freshness import period_stale_reason
    if any(b.search(en) for b in blocked):
        return "blocklisted"
    why = drop_reason({"headline_en": en})
    if why:
        return why
    if period and period[0]:
        why = period_stale_reason({"headline_en": en, "edition_date": day}, period[0], period[1])
        if why:
            return f"stale: {why}"
    return ""


def pick_one_liners(editions, verified: Dict[str, Dict[str, Any]], story_ids: List[str], limit: int,
                    period: Optional[Tuple[str, str]] = None, stats: Optional[Dict[str, Any]] = None):
    out, seen = [], []
    blocked = _blocklist()
    dropped = 0
    for ed in editions:
        for ol in ed["content"].get("one_liners") or []:
            if not isinstance(ol, dict) or ol.get("event_id") not in verified:
                continue
            en, hi = clean_one_liner(ol.get("text_en")), clean_one_liner(ol.get("text_hi"))
            if not en or _UNTITLED_RE.search(en) or not has_devanagari(hi) or heading_only(en):
                continue
            if not fact_line_ok(en) or _line_dropped(en, ed["date"], period, blocked):
                dropped += 1
                continue
            if any(is_similar(en, s) for s in seen):
                continue
            seen.append(en)
            out.append({"category": verified[ol["event_id"]]["section"], "text_en": en, "text_hi": hi,
                        "event_id": ol["event_id"]})
    # Stories without a daily one-liner fall back to their headline pair.
    have = {o["event_id"] for o in out}
    for eid in story_ids:
        if eid not in have and eid in verified:
            it = verified[eid]
            hen = clean_one_liner(it["headline_en"])
            if hen and not heading_only(hen) and fact_line_ok(hen) and not any(is_similar(hen, s) for s in seen):
                out.append({"category": it["section"], "text_en": hen,
                            "text_hi": clean_one_liner(it["headline_hi"]), "event_id": eid})
                seen.append(hen)
    # Events not already printed as full stories first (fresh revision lines), then
    # the stories' own one-liners, so the digest repeats as little as possible.
    # Exam-core events (Cabinet, agriculture, RBI agri credit, schemes) lead each group.
    from pipeline.exam_relevance import boost
    rank = {e: i for i, e in enumerate(story_ids)}
    out.sort(key=lambda o: (o["event_id"] in rank, -boost({"headline_en": o["text_en"]}), rank.get(o["event_id"], 0)))
    if stats is not None:
        stats["one_liners_dropped"] = dropped
    return out[:limit]


def pick_agri_corner(editions, limit: int, gk_limit: int, period: Optional[Tuple[str, str]] = None,
                     seen_orgs: Optional[set] = None, seen_gk: Optional[List[str]] = None,
                     stats: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Agriculture Corner: real agri facts only (no NH projects, PMAY-G visits or a
    DVAC raid), whole sentences, fresh, blocklist-clean; its Static GK skips
    organisations already boxed under a story."""
    from pipeline.exam_relevance import agri_terms
    items, gk, seen, seen_gk_l = [], [], [], set()
    blocked = _blocklist()
    seen_orgs = seen_orgs if seen_orgs is not None else set()
    seen_gk = seen_gk if seen_gk is not None else []
    dropped = 0
    for ed in editions:
        ac = ed["content"].get("agri_corner") or {}
        for x in ac.get("items") or []:
            if not isinstance(x, dict):
                continue
            en, hi = clean_headline(x.get("en")), clean_headline(x.get("hi"))
            if not en or _UNTITLED_RE.search(en) or not has_devanagari(hi) or any(is_similar(en, s) for s in seen):
                continue
            if not agri_terms(en) or not fact_line_ok(en) or _line_dropped(en, ed["date"], period, blocked):
                dropped += 1
                continue
            seen.append(en)
            items.append({"en": en, "hi": hi, "event_id": x.get("event_id", ""), "date": ed["date"]})
        for g in ac.get("static_gk") or []:
            if not isinstance(g, dict):
                continue
            en, hi = clean_headline(g.get("en")), clean_headline(g.get("hi"))
            if en and has_devanagari(hi) and en.lower() not in seen_gk_l:
                if (gk_orgs(en) & seen_orgs) or _is_dup_text(en, seen_gk):
                    continue
                seen_gk_l.add(en.lower())
                gk.append({"en": en, "hi": hi})
    from pipeline.exam_relevance import boost
    items.sort(key=lambda i: -boost({"headline_en": i["en"]}))
    if stats is not None:
        stats["agri_corner_dropped"] = dropped
    return {"items": items[:limit], "static_gk": gk[:gk_limit]}


def build_quick_tables(pool: List[Dict[str, Any]], rows_per_table: int) -> List[Dict[str, Any]]:
    """Monthly quick tables; an item lands in the first matching table only, empty tables are skipped."""
    tables = {t: [] for t, _h, _r in QUICK_TABLES}
    for it in sorted(pool, key=lambda x: x.get("edition_date", "")):
        text = f"{it['headline_en']} {it.get('summary_en', '')}"
        dedicated = it["section"] if it["section"] in ("Sports", "Important Days") else None
        for title, _hi, rx in QUICK_TABLES:
            if dedicated:  # sports / days stories go to their own table (or obituaries)
                hit = title == dedicated or (title == "Obituaries" and rx.search(text))
            else:
                hit = title not in ("Sports", "Important Days") and rx.search(text)
            if hit:
                if len(tables[title]) < rows_per_table:
                    tables[title].append({"date": it.get("edition_date", ""), "en": it["headline_en"],
                                          "hi": it["headline_hi"], "event_id": it.get("event_id", "")})
                break
    return [{"title_en": t, "title_hi": h, "rows": tables[t]} for t, h, _r in QUICK_TABLES if tables[t]]


# --------------------------------------------------------------------------- #
# Summary bullets: whole sentences from the story's own text, never cut
# --------------------------------------------------------------------------- #
# The daily key points are cut at ~200 characters and split at every ". ", so
# they end mid-sentence ("... the prescribed reservation") and break at
# initials ("president B" / "Manickam Tagore urged ...").  The period builder
# therefore rebuilds each bullet as a complete sentence of the same story's own
# article text (detailed_explanation_en, then summary_en), split at sentence
# boundaries only (". ! ?" and the Devanagari danda "।").  A key point is used to
# choose which sentence; the sentence itself always comes from the story record.
_DATELINE_RE = re.compile(
    r"^\s*(?i:published|updated|last\s+updated)\s*[-:–]\s*[A-Z][a-z]+\s+\d{1,2},\s+\d{4}\s+\d{1,2}:\d{2}\s*(?i:[ap]m)\s+IST"
    r"(?:\s*[-–]\s*(?:NEW\s+DELHI|New\s+Delhi|NAVI\s+MUMBAI|Navi\s+Mumbai|[A-Z][A-Z.&'-]+(?=\s)|[A-Z][a-z]+(?=\s+[A-Z\"“‘'])))?\s*"
)
_DATELINE_LOOSE_RE = re.compile(r"^\s*(?:published|updated|last\s+updated)\s*[-:–][^.]*?\bIST\b\s*", re.I)
_CREDIT_RE = re.compile(r"\b(?:photo|image|file\s+photo)\s*credit\s*:\s*", re.I)
_CREDIT_TOKEN_RE = re.compile(r"^(?:[A-Z][A-Z.&'/-]*|PTI|ANI|IANS|AFP|AP|Reuters|Getty\s+Images|Special\s+Arrangement|"
                              r"The\s+Hindu|File|Special|Arrangement|Bureau|Handout|Twitter|X|@\S+|X/@\S+|Facebook|Instagram|by\s+arrangement)$")
_OPENERS = {"The", "A", "An", "As", "In", "On", "At", "After", "With", "While", "Amid", "Following", "Speaking",
            "According", "This", "It", "He", "She", "They", "Union", "Chief", "Prime", "President", "Former",
            "Addressing", "Under", "During", "For", "From", "Over", "India", "India's", "India’s"}
_HI_BOILER_RE = re.compile(r"(?:अपडेटेड|प्रकाशित|फ़ोटो\s*क्रेडिट|फोटो\s*क्रेडिट|photo\s*credit|published|updated)\s*[-:–]", re.I)
_ABBREV = {"mr", "mrs", "ms", "dr", "prof", "st", "sr", "jr", "no", "nos", "vs", "v", "gen", "lt", "col", "capt",
           "maj", "brig", "hon", "rs", "govt", "dept", "inc", "ltd", "co", "corp", "e.g", "i.e", "etc", "approx",
           "fig", "jan", "feb", "mar", "apr", "aug", "sep", "sept", "oct", "nov", "dec", "km", "sq", "sh", "smt",
           "shri", "u.s", "u.k", "u.n", "rev", "adv", "est", "a.m", "p.m", "ph.d", "art", "sec", "cl"}
_END_RE = re.compile(r"[.!?।]+[\"”’')\]]*")
_TERMINAL_RE = re.compile(r"[.!?।][\"”’')\]]*$")
_BAD = "\x00"  # marks text that must never be shown (a photo credit we could not strip cleanly)
_GENERIC_FACT_RE = re.compile(r"^(?:fact\s*\d+|key\s+name)\b", re.IGNORECASE)
_SIM_BULLET = 0.85


def split_sentences(text: Any) -> List[str]:
    """Split at real sentence ends only. Returns complete sentences (with their
    terminal punctuation); a trailing fragment without one is dropped."""
    s = re.sub(r"\s+", " ", str(text or "")).strip()
    out: List[str] = []
    start = 0
    for m in _END_RE.finditer(s):
        end = m.end()
        nxt = s[end:end + 2]
        if end < len(s) and not (nxt[:1] == " " and re.match(r"[A-Z0-9\"“‘'(\u0900-\u097F₹]", nxt[1:2] or "")):
            continue  # "3.5", "Rs.20", "x.com", lowercase continuation
        if "।" not in m.group(0) and "!" not in m.group(0) and "?" not in m.group(0):
            word = re.search(r"([A-Za-z][A-Za-z.]*)\.$", s[start:m.start() + 1])
            w = (word.group(1) if word else "").rstrip(".").lower()
            if word and (len(w) == 1 or w in _ABBREV or re.fullmatch(r"(?:[a-z]\.)+[a-z]", w)):
                continue  # initials (B. Thamodharan, M.K. Stalin) and abbreviations (Mr., Dr., U.S.)
        sent = s[start:end].strip()
        if sent:
            out.append(sent)
        start = end
    return out


def _strip_credit(text: str) -> str:
    """Remove "Photo Credit: NAME" without eating the sentence that follows it.
    When the credit's end cannot be told apart from the next sentence, the
    text is marked bad so it is never shown half-cut."""
    def fix(m: re.Match) -> str:
        rest = text[m.end():]
        toks = rest.split(" ")
        i = 0
        while i < len(toks) and i < 6:
            two = " ".join(toks[i:i + 2])
            if _CREDIT_TOKEN_RE.match(two) and " " in two:
                i += 2
                continue
            if toks[i] and _CREDIT_TOKEN_RE.match(toks[i]) and not (toks[i] in _OPENERS):
                i += 1
                continue
            break
        if i == 0:  # "Imran Nissar As the BJP ..." → name words before an opener
            for j in (1, 2, 3):
                if j < len(toks) and all(t[:1].isupper() for t in toks[:j]) and toks[j] in _OPENERS:
                    i = j
                    break
        if 0 < i < len(toks) and re.fullmatch(r"[A-Z]\.", toks[i - 1]) and re.match(r"[A-Z][a-z]+$", toks[i]) \
                and i + 1 < len(toks) and toks[i + 1][:1].isupper():
            i += 1  # "R. Ashok DMK …": initial + surname
        while 0 < i < len(toks) and toks[i][:1].islower():
            i -= 1  # "Arrangement BRS working president": BRS starts the sentence
        if i == 0 or i >= len(toks):
            # Credit end unknown: poison only the sentence right after it.
            return "\x01" + _BAD + " ".join(toks)
        return "\x01" + " ".join(toks[i:])
    m = _CREDIT_RE.search(text)
    if not m:
        return text
    head = text[:m.start()].rstrip()
    tail = fix(m)
    # The sentence right before a photo credit is the photo caption: drop it.
    sents = split_sentences(head)
    head = " ".join(sents[:-1]) if sents and not head.endswith(_BAD) else head
    return (head + " " + _strip_credit(tail[1:])).strip()


def clean_source_text(text: Any) -> str:
    """Article text without the "Published – … IST – CITY" dateline and photo credits."""
    s = re.sub(r"\s+", " ", str(text or "")).strip()
    if not s:
        return ""
    m = _DATELINE_RE.match(s)
    dated = bool(m)
    if m:
        s = s[m.end():]
    elif _DATELINE_LOOSE_RE.match(s):
        dated = True
        s = _DATELINE_LOOSE_RE.sub("", s, count=1)
        s = re.sub(r"^[-–:\s]+", "", s)
    s = re.sub(r"^[-–:\s]+", "", s)
    if dated:
        s = _strip_lead_credit(s)
    return _strip_credit(s).strip()


_BYLINE_RE = re.compile(r"^(?:(?:Sports|Our|Special|Staff|Legal|Business|City)\s+)?(?:Bureau|Correspondent|Reporter|Desk)\s+(?=[A-Z])")
_LEAD_CREDIT_RE = re.compile(r"^(?:[A-Z]\.\s?){1,2}[A-Z][a-z]+\s+(?=[A-Z][a-z])")


def _strip_lead_credit(s: str) -> str:
    """Right after a dateline: a byline ("Sports Bureau"), an unlabelled photo credit
    ("B. Thamodharan Tamil Nadu …") or a short caption followed by its credit
    ("DMK president M.K. Stalin. Ashok DMK president and …")."""
    s = _BYLINE_RE.sub("", s)
    s = _LEAD_CREDIT_RE.sub("", s, count=1)
    sents = split_sentences(s)
    if len(sents) >= 2 and len(sents[0].split()) <= 10 and not _CREDIT_RE.search(sents[1]):
        cap = _norm(sents[0])
        toks = sents[1].split()
        for j in (1, 2):
            if len(toks) > j + 2 and all(t[:1].isupper() for t in toks[:j]) \
                    and _norm(" ".join(toks[j:j + 2])) in cap and _norm(" ".join(toks[:j])) not in cap:
                rest = s[len(sents[0]):].lstrip()
                return " ".join(rest.split()[j:])
    return s


_RUNON_RE = re.compile(r"(\S+)\s(?:The|A|An)\s[A-Z0-9]")
_RUNON_OK = {"of", "in", "at", "by", "to", "from", "for", "with", "said", "told", "on", "and", "or", "like", "via",
             "reads", "titled", "called", "named", "is", "was", "be", "into", "as", "than", "about", "film", "book"}


def run_on(s: str) -> bool:
    """Two texts glued without punctuation, e.g. a related-story link title followed
    by the next sentence ("... carrying navigation satellite NVS-03 The GSLV-F18 ...")."""
    for m in _RUNON_RE.finditer(s or ""):
        prev = m.group(1)
        if m.start() == 0 or re.search(r"[.!?:;,\"“”'‘’(]$", prev) or prev.lower() in _RUNON_OK:
            continue
        return True
    return False


_MID_DATELINE_RE = re.compile(r"\b(?:Published|Updated)\s*[-:–]\s*[A-Z][a-z]+\s+\d{1,2},\s+\d{4}")


def complete_sentence(s: str) -> bool:
    """A bullet must be a whole sentence: starts like a sentence and ends with terminal punctuation."""
    s = (s or "").strip()
    if _BAD in s or len(s.split()) < 5 or len(s) > 420:
        return False
    if _MID_DATELINE_RE.search(s) or " / " in s:   # a dateline or "party / state politics / …" tag footer
        return False
    if not re.match(r"[A-Z0-9\"“‘'(₹\u0900-\u097F]", s) or run_on(s):
        return False
    return bool(_TERMINAL_RE.search(s))


def _hi_ok(hi: str) -> bool:
    return bool(hi) and has_devanagari(hi) and not _HI_BOILER_RE.search(hi) and _BAD not in hi


def _close_hi(hi: str) -> str:
    hi = hi.strip()
    return hi if re.search(r"[.!?।][\"”’')]*$", hi) else hi + "।"


def story_sentences(it: Dict[str, Any]) -> List[str]:
    """Complete sentences of the story's own text (detailed explanation first)."""
    seen: List[str] = []
    out: List[str] = []
    for key in ("detailed_explanation_en", "summary_en"):
        for snt in split_sentences(clean_source_text(it.get(key))):
            n = _norm(snt)
            if complete_sentence(snt) and n not in seen:
                seen.append(n)
                out.append(snt)
    return out


def _candidate_pairs(it: Dict[str, Any]) -> List[Dict[str, str]]:
    """Ordered (EN, HI) bullet candidates, all whole sentences of THIS story.

    The daily key points pick the sentence (in their order); the full sentence
    is taken from the story text.  Hindi is kept only when the key point was
    already the whole sentence (so the daily translated all of it) and carries
    no dateline/credit; otherwise the bullet is English-only rather than
    misaligned."""
    sents = story_sentences(it)
    nsents = [_norm(x) for x in sents]
    kp_en = [str(x or "") for x in it.get("key_points_en") or []]
    kp_hi = [str(x or "") for x in it.get("key_points_hi") or []]
    out: List[Dict[str, str]] = []
    used: set = set()
    for i, raw in enumerate(kp_en):
        cleaned = clean_source_text(raw)
        if _BAD in cleaned:
            continue
        kc = _norm(cleaned)
        if len(kc) < 15:
            continue
        hit = next((j for j, n in enumerate(nsents) if j not in used and n.startswith(kc)), None)
        if hit is None:
            # Not found in the story text: only a key point that is itself a whole
            # sentence (the daily kept it intact, terminal punctuation included).
            if complete_sentence(cleaned) and not _is_dup_text(cleaned, [_norm(x["en"]) for x in out]):
                hi = kp_hi[i] if i < len(kp_hi) else ""
                out.append({"en": cleaned, "hi": _close_hi(hi) if _hi_ok(hi) and cleaned == raw.strip() else ""})
            continue
        used.add(hit)
        whole = nsents[hit] == kc and cleaned.strip() == re.sub(r"\s+", " ", raw).strip()
        hi = kp_hi[i] if i < len(kp_hi) else ""
        out.append({"en": sents[hit], "hi": _close_hi(hi) if whole and _hi_ok(hi) else ""})
    for j, snt in enumerate(sents):
        if j not in used:
            out.append({"en": snt, "hi": ""})
    return out


_ECHO_SKIP = {"the", "and", "for", "with", "from", "under", "into", "www", "gov", "pib", "shri", "smt", "ministry",
              "external", "affairs", "press", "release", "joint", "of", "to", "in", "on", "at", "by", "as", "an"}


def headline_echo(sentence: Any, it: Dict[str, Any]) -> bool:
    """A "bullet" that only re-strings words of the headline / source name
    ("Union Minister Ashwini Vaishnaw, Web Application Portal.", "Senegal Ministry of
    External, Shri ...") - built from a headline-only feed item, not story text."""
    src = it.get("source") if isinstance(it.get("source"), dict) else {}
    ref = f"{it.get('headline_en', '')} {src.get('name', '')}"
    ref_words = {w[:6] for w in re.findall(r"[a-z0-9]+", ref.lower())}
    words = [w for w in re.findall(r"[a-z0-9]+", str(sentence or "").lower()) if w not in _ECHO_SKIP and len(w) > 1]
    if not words:
        return True
    return sum(1 for w in words if w[:6] in ref_words) / len(words) >= 0.9


def _is_dup_text(text: str, pool: List[str], threshold: float = _SIM_BULLET) -> bool:
    n = _norm(text)
    return any(n == q or is_similar(n, q, threshold) for q in pool)


def filler_key(text: Any) -> str:
    """Normalised text with numbers masked, so "… ₹112 crore support" and "… ₹131 crore
    support" count as the same template sentence."""
    return re.sub(r"\d+", "#", _norm(str(text or "")))


def filler_sentences(items: List[Dict[str, Any]], max_stories: int = 2) -> set:
    """Sentences/facts (as filler_key) that appear in more than ``max_stories`` different stories."""
    where: Dict[str, set] = {}
    for idx, it in enumerate(items):
        texts = set(filler_key(s) for s in story_sentences(it))
        texts |= {filler_key(clean_source_text(k)) for k in it.get("key_points_en") or [] if k}
        texts |= {filler_key(clean_headline(it.get(k))) for k in ("exam_fact_en",) if it.get(k)}
        for p in it.get("static_gk_pairs") or []:
            en = p.get("en") if isinstance(p, dict) else (p[0] if isinstance(p, (list, tuple)) and p else "")
            texts.add(filler_key(clean_headline(en)))
        for k, v in (it.get("static_facts") or {}).items() if isinstance(it.get("static_facts"), dict) else []:
            texts.add(filler_key(f"{k} {v}"))
        for t in texts:
            if t:
                where.setdefault(t, set()).add(idx)
    return {t for t, s in where.items() if len(s) > max_stories}


_HI_UNION_RE = re.compile(r"संयुक्त(\s+(?:गृह|वित्त|शिक्षा|कृषि|रक्षा|स्वास्थ्य|विदेश)?\s*)मंत्री")


def _hi_glossary(en: str, hi: str) -> str:
    """Deterministic repairs of recurring MT slips: "Union Minister" -> "संयुक्त मंत्री"
    (= joint minister), "presidential address" -> "राष्ट्रपति संबोधन", ", ।"."""
    if not hi:
        return hi
    if re.search(r"\bUnion\b", en):
        hi = _HI_UNION_RE.sub(lambda m: "केंद्रीय" + (m.group(1) if m.group(1).strip() else " ") + "मंत्री", hi)
    if re.search(r"(?i)\bpresidential\s+address\b", en):
        hi = hi.replace("राष्ट्रपति संबोधन", "अध्यक्षीय संबोधन")
    hi = re.sub(r"\s*,\s*([।.])", r"\1", hi)
    return hi


class PeriodHindi:
    """Hindi for the period edition's bullets / one-liners: carried from the daily data,
    repaired by ``hindi_postfix`` in strict mode, translated here when missing.

    FAIL-CLOSED: a line whose Hindi cannot be made clean is dropped as a pair (the
    edition never prints an English-only bullet)."""

    def __init__(self, translators: Optional[Tuple[Optional[Callable[[str], str]],
                                                   Optional[Callable[[str], str]]]] = None):
        from pipeline.hindi_postfix import load_name_map
        try:
            self.name_map = load_name_map()
        except Exception:
            self.name_map = {}
        self.word_tr, self.line_tr = translators if translators is not None else _period_translators()
        self.stats: Dict[str, int] = {}

    def fix(self, en: str, hi: str) -> str:
        from pipeline.hindi_postfix import fix_pair
        hi = str(hi or "")
        if hi and has_devanagari(hi):
            out = fix_pair(en, hi, name_map=self.name_map, translator=self.word_tr,
                           line_translator=self.line_tr, stats=self.stats, strict=True)
            if out:
                out = _hi_glossary(en, out)
                return _close_hi(out) if _TERMINAL_RE.search(en) else out
            return ""
        if self.line_tr is None:
            return ""
        try:
            new = str(self.line_tr(en) or "")
        except Exception:
            new = ""
        if not has_devanagari(new):
            self.stats["translate_failed"] = self.stats.get("translate_failed", 0) + 1
            return ""
        self.stats["translated"] = self.stats.get("translated", 0) + 1
        out = fix_pair(en, new, name_map=self.name_map, translator=self.word_tr,
                       line_translator=None, stats=self.stats, strict=True)
        out = _hi_glossary(en, out) if out else out
        return (_close_hi(out) if _TERMINAL_RE.search(en) else out) if out else ""


def _period_translators():
    """(word, line) translators for the period stage (budgeted; (None, None) offline/pytest)."""
    try:
        from pipeline.hindi_postfix import budgeted_translators
        return budgeted_translators(max_calls=int(os.getenv("ALP_PERIOD_TRANSLATE_CALLS", "90")),
                                    budget_s=float(os.getenv("ALP_PERIOD_TRANSLATE_BUDGET_S", "240")))
    except Exception:
        return None, None


def story_pub_date(it: Dict[str, Any]):
    return publish_date(it.get("published") or it.get("pub_time_ist") or it.get("published_at"),
                        it.get("edition_date"))


def story_source_text(it: Dict[str, Any]) -> str:
    parts = [str(it.get(k) or "") for k in ("detailed_explanation_en", "summary_en", "headline_en")]
    parts += [str(x or "") for x in it.get("key_points_en") or []]
    return " ".join(parts)


def clean_line(text: Any, it: Optional[Dict[str, Any]], hindi: bool) -> str:
    """Display text of one bullet / one-liner: no source tag, exact ₹ figure, ₹ not Rs,
    relative weekday resolved to the event date, tidy punctuation."""
    s = strip_source_tags(clean_headline(text))
    if it:
        s = exact_money(s, story_source_text(it), hindi)
        s = resolve_weekdays(s, story_pub_date(it))
    else:
        s = exact_money(s, "", hindi)
    return tidy(s)


_HI_SPLIT_RE = re.compile(r"(?<=[।!?])\s+")


def _hi_sentence_map(it: Dict[str, Any]) -> Dict[str, str]:
    """EN sentence (normalised) -> HI sentence of the daily's own translation, when the
    EN and HI texts split into the same number of sentences."""
    out: Dict[str, str] = {}
    for ek, hk in (("detailed_explanation_en", "detailed_explanation_hi"), ("summary_en", "summary_hi")):
        en_s = split_sentences(clean_source_text(it.get(ek)))
        hi_s = [x.strip() for x in _HI_SPLIT_RE.split(re.sub(r"\s+", " ", str(it.get(hk) or "")).strip()) if x.strip()]
        if en_s and len(en_s) == len(hi_s) and all(has_devanagari(h) for h in hi_s):
            for e, h in zip(en_s, hi_s):
                out.setdefault(_norm(e), h)
    return out


def _summary_pairs(it: Dict[str, Any], seen: Optional[List[str]] = None,
                   filler: Optional[set] = None, limit: int = 3,
                   hindi: Optional[PeriodHindi] = None, qa: Optional[Dict[str, Any]] = None
                   ) -> List[Dict[str, str]]:
    """Up to ``limit`` whole-sentence bilingual bullets of this story, unique within the
    story and across the edition (``seen``), with generic filler dropped.  Every bullet's
    Hindi comes from the daily data (key point, then the sentence-aligned daily
    translation) or is translated here; a bullet whose Hindi cannot be made clean is
    dropped as a pair and counted in ``qa``."""
    seen = seen if seen is not None else []
    filler = filler or set()
    head = _norm(it.get("headline_en"))
    hi_map = _hi_sentence_map(it)
    out: List[Dict[str, str]] = []
    eligible = 0
    for p in _candidate_pairs(it):
        n = _norm(p["en"])
        if filler_key(p["en"]) in filler or n == head or (head and (n.startswith(head) or is_similar(n, head, _SIM_BULLET))) \
                or _is_dup_text(p["en"], seen) or caption_residue(p["en"]) or headline_echo(p["en"], it):
            continue
        en = clean_line(p["en"], it, False)
        if not complete_sentence(en):
            continue
        eligible += 1
        hi_src = p.get("hi") or hi_map.get(n, "")
        hi = clean_line(hi_src, it, True) if hi_src else ""
        hi = hi if _hi_ok(hi) else ""
        if hindi is None:      # selection-only call (no Hindi stage): keep the EN line as-is
            hi = _close_hi(hi) if hi else ""
        else:
            hi = hindi.fix(en, hi)
            if not hi:
                continue
        seen.append(n)
        out.append({"en": en, "hi": hi})
        if len(out) >= limit:
            break
    if qa is not None:
        expected = min(limit, eligible)
        qa["bullets_expected"] = qa.get("bullets_expected", 0) + expected
        short = expected - len(out)
        if short > 0:
            qa["bullets_missing_hi"] = qa.get("bullets_missing_hi", 0) + short
            qa.setdefault("stories_short", []).append(
                {"event_id": it.get("event_id", ""), "headline_en": it.get("headline_en", ""),
                 "en_bullets": expected, "hi_bullets": len(out)})
    return out


def _bilingual_pairs(it: Dict[str, Any], hindi: PeriodHindi, qa: Dict[str, Any],
                    limit: int = 3) -> List[Dict[str, str]]:
    """Make the story's chosen bullets (``ensure_body``) bilingual: Hindi carried from the
    daily data (key point / sentence-aligned translation) or translated here; a bullet
    whose Hindi cannot be made clean is dropped as a pair and counted in ``qa``."""
    hi_map = _hi_sentence_map(it)
    for e_raw in [x for x in split_sentences(clean_source_text(it.get("detailed_explanation_en")))] + \
            [x for x in split_sentences(clean_source_text(it.get("summary_en")))]:
        h = hi_map.get(_norm(e_raw))
        if h:
            hi_map.setdefault(_norm(clean_line(e_raw, it, False)), h)
    out: List[Dict[str, str]] = []
    expected = 0
    for p in (it.get("summary_pairs") or [])[:limit]:
        if not isinstance(p, dict):
            continue
        en = clean_line(p.get("en"), it, False)
        if not en or caption_residue(en) or not complete_sentence(en) or headline_echo(en, it):
            continue
        expected += 1
        hi_src = p.get("hi") or hi_map.get(_norm(p.get("en"))) or hi_map.get(_norm(en), "")
        hi = clean_line(hi_src, it, True) if hi_src else ""
        hi = hindi.fix(en, hi if _hi_ok(hi) else "")
        if hi:
            out.append({"en": en, "hi": hi})
        elif os.getenv("DRY_RUN", "0") == "1":
            # Offline dry run (no translator): keep the EN line, marked, so dev PDFs show
            # bodies; a live edition never carries it (dropped as a pair).
            out.append({"en": en, "hi": "", "en_only_dry_run": True})
    qa["bullets_expected"] = qa.get("bullets_expected", 0) + expected
    have = sum(1 for p in out if p["hi"])
    if expected > have:
        qa["bullets_missing_hi"] = qa.get("bullets_missing_hi", 0) + expected - have
        qa.setdefault("stories_short", []).append(
            {"event_id": it.get("event_id", ""), "headline_en": it.get("headline_en", ""),
             "en_bullets": expected, "hi_bullets": have})
    return out


def period_hindi_qa(qa: Dict[str, Any], max_missing: Optional[float] = None) -> Dict[str, Any]:
    """Bilingual completeness of the period edition's story bullets.

    A story whose English has more bullets than its Hindi is a warning; the edition
    fails when more than ``max_missing`` (default 10%) of the bullets lack Hindi."""
    limit = float(os.getenv("ALP_PERIOD_HI_MAX_MISSING", "0.10")) if max_missing is None else max_missing
    exp, miss = int(qa.get("bullets_expected", 0)), int(qa.get("bullets_missing_hi", 0))
    ratio = miss / exp if exp else 0.0
    qa["missing_ratio"] = round(ratio, 3)
    qa["warnings"] = [f"story '{s['headline_en'][:60]}': {s['en_bullets']} EN bullets, {s['hi_bullets']} HI"
                      for s in qa.get("stories_short", [])]
    qa["passed"] = ratio <= limit
    return qa


# --------------------------------------------------------------------------- #
# Never a headline-only story: rebuild the body from the daily's own fields,
# then from the source page, else drop the story (the next-ranked one is taken).
# --------------------------------------------------------------------------- #
_CUT_RE = re.compile(r"(?:…|\.\.\.|\s(?:of|the|and|for|to|with|in|on|a|an|at|by|from|its|their))\s*$", re.I)


def _as_sentence(text: Any) -> str:
    """A daily key point / fact as a whole sentence, or "" when it looks cut."""
    t = clean_source_text(text)
    if not t or _BAD in t or len(t.split()) < 6 or len(t) >= 195 or _CUT_RE.search(t):
        return ""
    if not _TERMINAL_RE.search(t):
        t += "."
    return t if complete_sentence(t) else ""


def rebuild_text(it: Dict[str, Any]) -> str:
    """Sentences for a story whose printed bullets came out empty, from the daily
    artifact's full data: summary, key points, exam fact, static facts."""
    parts: List[str] = []
    for key in ("summary_en", "detailed_explanation_en", "what_happened_en", "why_it_matters_en", "background_en"):
        parts += [x for x in split_sentences(clean_source_text(it.get(key))) if complete_sentence(x)]
    for kp in it.get("key_points_en") or []:
        parts.append(_as_sentence(kp))
    parts.append(_as_sentence(it.get("exam_fact_en")))
    sf = it.get("static_facts")
    for k, v in (sf.items() if isinstance(sf, dict) else []):
        if isinstance(k, str) and not k.startswith("_") and isinstance(v, str):
            parts.append(_as_sentence(v))
    for f in it.get("facts_en") or it.get("key_facts_en") or []:
        parts.append(_as_sentence(f))
    out: List[str] = []
    for x in parts:
        if x and not _is_dup_text(x, [_norm(y) for y in out]):
            out.append(x)
    return " ".join(out)


def source_url(it: Dict[str, Any]) -> str:
    src = it.get("source") if isinstance(it.get("source"), dict) else {}
    for u in (src.get("url"), it.get("source_url"), it.get("link"), it.get("url")):
        u = str(u or "").strip()
        if u.startswith(("http://", "https://")) and re.sub(r"https?://[^/]+/?", "", u):
            return u
    return ""


_JUNK_PARA_RE = re.compile(r"(?i)cookie|subscribe|sign\s+in|log\s*in|copyright|all\s+rights\s+reserved|"
                           r"terms\s+of\s+use|follow\s+us|download\s+the\s+app|advertisement|read\s+more|"
                           r"click\s+here|share\s+this|whatsapp|posted\s+on:|release\s+id:")


def fetch_source_text(url: str, timeout: float = 8.0) -> str:
    """Article text of *url* as stage 01/04 read it: og:description / meta description
    plus the page's paragraphs. "" on any failure, offline (DRY_RUN /
    ALP_DISABLE_NETWORK) or when disabled (ALP_PERIOD_FETCH=0)."""
    if not url or os.getenv("ALP_PERIOD_FETCH", "1") == "0" or os.getenv("DRY_RUN", "0") == "1" \
            or os.getenv("ALP_DISABLE_NETWORK", "0") == "1":
        return ""
    try:
        import requests
        from bs4 import BeautifulSoup
        r = requests.get(url, timeout=timeout, allow_redirects=True,
                         headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                                  "Accept-Language": "en-IN,en;q=0.9"})
        if r.status_code != 200 or not r.text:
            return ""
        soup = BeautifulSoup(r.content[:400_000], "html.parser")
        desc = ""
        for attrs in ({"property": "og:description"}, {"name": "description"}, {"name": "twitter:description"}):
            tag = soup.find("meta", attrs=attrs)
            if tag and tag.get("content"):
                desc = re.sub(r"\s+", " ", tag["content"]).strip()
                break
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "aside", "form"]):
            tag.decompose()
        paras = []
        for p in soup.find_all("p"):
            t = re.sub(r"\s+", " ", p.get_text(" ", strip=True))
            if len(t) > 40 and not _JUNK_PARA_RE.search(t):
                paras.append(t)
        text = " ".join(([desc] if desc and len(desc.split()) >= 8 else []) + paras)
        return text[:4000]
    except Exception:
        return ""


def ensure_body(it: Dict[str, Any], seen: List[str], filler: set, budget: Dict[str, int],
                fetcher: Optional[Any] = None) -> bool:
    """Give *it* summary bullets: its own text first, then the daily artifact's full
    data, then the source page. False = still headline-only (the caller drops it)."""
    pairs = _summary_pairs(it, seen, filler)
    if pairs:
        it["summary_pairs"] = pairs
        return True
    text = rebuild_text(it)
    if text:
        probe = dict(it, detailed_explanation_en=text, summary_en="", key_points_en=[], key_points_hi=[])
        pairs = _summary_pairs(probe, seen, filler)
        if pairs:
            it["summary_pairs"] = pairs
            it["body_source"] = "daily_fields"
            return True
    url = source_url(it)
    if url and budget.get("fetch", 0) > 0:
        budget["fetch"] -= 1
        fetched = (fetcher or fetch_source_text)(url)
        if fetched:
            probe = dict(it, detailed_explanation_en=fetched, summary_en="", key_points_en=[], key_points_hi=[])
            pairs = _summary_pairs(probe, seen, filler)
            if pairs:
                it["summary_pairs"] = pairs
                it["detailed_explanation_en"] = fetched
                it["body_source"] = "source_fetch"
                return True
    it["summary_pairs"] = []
    return False


def has_body(it: Dict[str, Any]) -> bool:
    """A story prints at least one bullet (summary pair, key point or summary line)."""
    for p in it.get("summary_pairs") or []:
        if isinstance(p, dict) and str(p.get("en") or "").strip():
            return True
    if "summary_pairs" in it:
        return False
    head = _norm(it.get("headline_en"))
    for k in it.get("key_points_en") or []:
        if _norm(clean_headline(k)) and _norm(clean_headline(k)) != head:
            return True
    sm = _norm(clean_headline(it.get("summary_en")))
    return bool(sm) and sm != head and not head.startswith(sm)


# --------------------------------------------------------------------------- #
# Static GK: one box per organisation per edition
# --------------------------------------------------------------------------- #
_ORG_ALIASES: Dict[str, Tuple[str, ...]] = {
    "rbi": ("RBI", "Reserve Bank of India", "Reserve Bank"), "sebi": ("SEBI", "Securities and Exchange Board"),
    "nabard": ("NABARD",), "icar": ("ICAR", "Indian Council of Agricultural Research"),
    "cacp": ("CACP", "Commission for Agricultural Costs and Prices"),
    "pmmsy": ("PMMSY", "Pradhan Mantri Matsya Sampada Yojana"), "kcc": ("KCC", "Kisan Credit Card"),
    "mea": ("Ministry of External Affairs", "MEA"), "mod": ("Ministry of Defence", "MoD"),
    "brics": ("BRICS",), "ndb": ("NDB", "New Development Bank"), "sco": ("SCO", "Shanghai Cooperation"),
    "g20": ("G20", "G-20"), "asean": ("ASEAN",), "aiib": ("AIIB", "Asian Infrastructure Investment Bank"),
    "apeda": ("APEDA",), "fci": ("FCI", "Food Corporation of India"), "isro": ("ISRO",), "drdo": ("DRDO",),
    "niti": ("NITI Aayog",), "csir": ("CSIR",), "neeri": ("NEERI",), "ncsc": ("NCSC",), "nhrc": ("NHRC",),
    "pmkisan": ("PM-KISAN", "PM Kisan"), "wto": ("WTO", "World Trade Organization"), "imf": ("IMF",),
    "world_bank": ("World Bank",), "fao": ("FAO", "Food and Agriculture Organization"),
}
_ORG_RX: Optional[List[Tuple[str, re.Pattern]]] = None


def _org_patterns() -> List[Tuple[str, re.Pattern]]:
    global _ORG_RX
    if _ORG_RX is None:
        table = {k: list(v) for k, v in _ORG_ALIASES.items()}
        try:
            facts = json.loads((ROOT / "config" / "current_facts.json").read_text(encoding="utf-8"))
            for o in facts.get("orgs") or []:
                if isinstance(o, dict) and o.get("id") and o.get("match"):
                    table.setdefault(str(o["id"]), []).extend(str(m) for m in o["match"])
        except (OSError, ValueError):
            pass
        _ORG_RX = []
        for key, names in table.items():
            alts = "|".join(re.escape(n).replace(r"\ ", r"\s+") for n in sorted(set(names), key=len, reverse=True))
            _ORG_RX.append((key, re.compile(r"(?<![A-Za-z])(?:" + alts + r")(?![A-Za-z])")))
    return _ORG_RX


# Unnamed organisation-attribute lines ("Established – 1935", "Role – Central bank of India").
_ORG_ATTR_RE = re.compile(r"(?i)^(?:year\s+of\s+)?(?:established|establishment|founded|foundation|set\s+up|"
                          r"headquarter\w*|hq|head\s+office|role|function|founding\s+act|governing\s+act|"
                          r"parent\s+(?:body|organi[sz]ation|ministry)|nodal\s+(?:ministry|body)|governor|"
                          r"chair(?:man|person)?|head|ceo|type|status|regulator\s+of)\b")


def gk_orgs(text: Any) -> set:
    """Organisations / schemes a Static GK line (or a story) names."""
    t = str(text or "")
    return {k for k, rx in _org_patterns() if rx.search(t)}


_GK_GENERIC = {"ministry", "india", "indian", "national", "year", "established", "establishment", "headquarters",
               "headquartered", "founded", "full", "form", "minister", "current", "parent", "capital", "state",
               "country", "currency", "first", "unique", "launch", "launched", "under", "which", "with", "from",
               "body", "nodal", "president", "chairman", "chief", "head", "government", "union", "department",
               "organisation", "organization", "responsible", "conduct", "functions", "operates", "directly",
               "erstwhile", "committee", "council", "affairs", "external", "delhi", "known", "also", "that", "this"}


def _gk_relevant(en: str, story_words: set) -> bool:
    """A Static GK fact must name something the story itself mentions (the daily
    sometimes attaches another event's facts, e.g. ISRO facts to an exam-reform story)."""
    words = [w for w in _norm(en).split() if len(w) >= 4 and w not in _GK_GENERIC and not w.isdigit()]
    if not words:
        return True
    return any(w[:5] in story_words for w in words)


def _attach_static_gk(story: Dict[str, Any], mcqs_by_event: Dict[str, Dict[str, Any]],
                      seen: Optional[List[str]] = None, filler: Optional[set] = None,
                      seen_orgs: Optional[set] = None) -> None:
    """Carry the story's verified Static GK pairs (daily MCQ schema first) as content pairs.

    The builder decides the final list (the renderer's static_facts / exam-fact
    fallbacks are cleared): a fact already printed under an earlier story of
    the edition (``seen``) or one that is generic filler shared by more than two
    stories (``filler``, checked for the generic exam-fact / static_facts
    fallbacks) is dropped.  A real Static GK fact shared by several stories is
    printed once, under the first of them."""
    seen = seen if seen is not None else []
    filler = filler or set()
    pairs: List[Dict[str, str]] = []
    text = " ".join(str(story.get(k) or "") for k in ("headline_en", "summary_en", "detailed_explanation_en"))
    text += " " + " ".join(str(x or "") for x in story.get("key_points_en") or [])
    story_words = {w[:5] for w in _norm(text).split() if len(w) >= 4}
    seen_orgs = seen_orgs if seen_orgs is not None else set()
    story_orgs = gk_orgs(text)
    # What the reader sees (headline, summary, printed bullets): a GK box about an
    # organisation only mentioned in passing deep in the source text ("former ISRO
    # chairman" in an exam-reform story) is off-topic.
    shown = " ".join([str(story.get("headline_en") or ""), str(story.get("summary_en") or "")]
                     + [str(p.get("en") or "") for p in story.get("summary_pairs") or [] if isinstance(p, dict)])
    shown_orgs = gk_orgs(shown)

    def add(en: Any, hi: Any) -> None:
        en_c, hi_c = clean_headline(en), clean_headline(hi)
        if not en_c or _GENERIC_FACT_RE.match(en_c):
            return
        value = en_c.split(" – ", 1)[-1].strip()
        head = _norm(story.get("headline_en"))
        if value[:1].islower() or (head and (_norm(value) == head or is_similar(_norm(value), head, _SIM_BULLET))):
            return  # cut mid-word by the daily, or just the headline again
        if not _gk_relevant(en_c, story_words):
            return
        if _is_dup_text(en_c, seen) or _is_dup_text(en_c, [_norm(q["en"]) for q in pairs]):
            return
        named = gk_orgs(en_c)
        if named and not named & shown_orgs:
            return  # about an organisation the printed story does not name
        if named & seen_orgs:
            return  # this organisation's box was already printed under an earlier story
        if not named and story_orgs and story_orgs <= seen_orgs and _ORG_ATTR_RE.match(en_c):
            return  # an unnamed attribute line ("Established – 1935") of an organisation already boxed
        pairs.append({"en": en_c, "hi": hi_c if has_devanagari(hi_c) else ""})

    m = mcqs_by_event.get(story.get("event_id"))
    for g in (m or {}).get("static_gk") or []:
        if isinstance(g, dict) and g.get("label_en") and g.get("value_en"):
            hi = f"{g['label_hi']} – {g['value_hi']}" if g.get("label_hi") and g.get("value_hi") else ""
            add(f"{g['label_en']} – {g['value_en']}", hi)
    for p in story.get("static_gk_pairs") or []:
        if isinstance(p, dict):
            add(p.get("en"), p.get("hi"))
        elif isinstance(p, (list, tuple)) and p:
            add(p[0], p[1] if len(p) > 1 else "")
    if not pairs:  # the renderer's own fallbacks, decided here so they are deduped too
        sf = story.get("static_facts")
        for k, v in (sf.items() if isinstance(sf, dict) else []):
            if isinstance(k, str) and not k.startswith("_") and not _GENERIC_FACT_RE.match(k) and v \
                    and filler_key(f"{k} {v}") not in filler:
                add(f"{clean_headline(k)} – {clean_headline(v)}", "")
        ef = clean_headline(story.get("exam_fact_en"))
        if not pairs and ef and filler_key(ef) not in filler:
            hi = clean_headline(story.get("exam_fact_hi"))
            add(f"Exam Fact – {ef}", f"परीक्षा तथ्य – {hi}" if has_devanagari(hi) else "")
    story["static_gk_pairs"] = pairs[:3]
    seen.extend(_norm(q["en"]) for q in story["static_gk_pairs"])
    for q in story["static_gk_pairs"]:
        seen_orgs.update(gk_orgs(q["en"]) or (story_orgs if len(story_orgs) == 1 else set()))
    story["static_facts"] = {}
    story["exam_fact_en"] = story["exam_fact_hi"] = ""


# --------------------------------------------------------------------------- #
# Public entry points
# --------------------------------------------------------------------------- #
def _fmt(d: str, with_year: bool) -> str:
    x = date.fromisoformat(d)
    return f"{x.day} {x.strftime('%B')}" + (f" {x.year}" if with_year else "")


def _clean_one_liners(ols: List[Dict[str, Any]], verified: Dict[str, Dict[str, Any]],
                      hindi: PeriodHindi, limit: int, qa: Dict[str, Any]) -> List[Dict[str, Any]]:
    out = []
    for o in ols:
        it = verified.get(o.get("event_id"))
        en = clean_line(o.get("text_en"), it, False)
        if not en or caption_residue(en):
            qa["one_liners_dropped"] = qa.get("one_liners_dropped", 0) + 1
            continue
        hi = hindi.fix(en, clean_line(o.get("text_hi"), it, True))
        if not hi:
            qa["one_liners_dropped"] = qa.get("one_liners_dropped", 0) + 1
            continue
        out.append({**o, "text_en": en, "text_hi": hi})
        if len(out) >= limit:
            break
    return out


def _clean_agri(agri: Dict[str, Any], hindi: PeriodHindi, qa: Dict[str, Any]) -> Dict[str, Any]:
    items = []
    for x in agri.get("items") or []:
        en = clean_line(x.get("en"), None, False)
        hi = hindi.fix(en, clean_line(x.get("hi"), None, True)) if en and not caption_residue(en) else ""
        if hi:
            items.append({**x, "en": en, "hi": hi})
        else:
            qa["agri_dropped"] = qa.get("agri_dropped", 0) + 1
    return {**agri, "items": items}


def _clean_headlines(stories: List[Dict[str, Any]], hindi: PeriodHindi) -> None:
    from pipeline.hindi_postfix import fix_pair
    for s in stories:
        en = tidy(exact_money(strip_source_tags(s.get("headline_en")), story_source_text(s), False))
        s["headline_en"] = en or s.get("headline_en", "")
        hi = tidy(exact_money(strip_source_tags(s.get("headline_hi")), story_source_text(s), True))
        fixed = hindi.fix(en, hi)
        if not fixed:  # keep the story (selection is decided elsewhere); repair what we can
            fixed = fix_pair(en, hi, name_map=hindi.name_map) or hi
        s["headline_hi"] = fixed.rstrip("।") if not _TERMINAL_RE.search(en) else fixed


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _mark_cover(stories: List[Dict[str, Any]]) -> None:
    """Cover "TOP STORIES" come from the boosted set (Cabinet, agriculture, RBI
    agri credit, schemes), best exam score first; the renderer reads these keys."""
    boosted = sorted((s for s in stories if s.get("exam_boosted")), key=lambda x: -_rank_key(x)[0])
    for s in stories:
        s["cover_eligible"] = bool(s.get("exam_boosted"))
        s["cover_rank"] = 0
    for i, s in enumerate(boosted, 1):
        s["cover_rank"] = i


def promote_big_ticket(stories: List[Dict[str, Any]], ranked: List[Dict[str, Any]],
                       editions: List[Dict[str, Any]], accept: Any, limit: int = 4) -> List[Dict[str, Any]]:
    """Big-ticket exam items of the period (Cabinet decisions, Khet Bachaao Abhiyaan,
    International Maize Conference, OMSS, Semicon ...) must be stories: one the caps
    left out — or that a daily printed only as a one-liner / Agri-corner line whose
    story is in the pool — replaces the weakest story outside the boosted set."""
    from pipeline.exam_relevance import BIG_TICKET_RE, CABINET_RE
    if not stories:
        return stories
    chosen = {id(x) for x in stories}
    ids = {x.get("event_id") for x in stories}
    by_event = {x.get("event_id"): x for x in ranked}
    wanted: List[Dict[str, Any]] = []
    for it in ranked:
        if id(it) not in chosen and (BIG_TICKET_RE.search(it["headline_en"]) or CABINET_RE.search(it["headline_en"])):
            wanted.append(it)
    for ed in editions:   # one-liner / Agri-corner lines whose event has a full story in the pool
        lines = [(o.get("text_en"), o.get("event_id")) for o in ed["content"].get("one_liners") or []
                 if isinstance(o, dict)]
        lines += [(o.get("en"), o.get("event_id")) for o in (ed["content"].get("agri_corner") or {}).get("items") or []
                  if isinstance(o, dict)]
        for text, eid in lines:
            it = by_event.get(eid)
            if it is not None and eid not in ids and id(it) not in chosen and it not in wanted \
                    and (BIG_TICKET_RE.search(str(text or "")) or CABINET_RE.search(str(text or ""))):
                wanted.append(it)
    out = list(stories)
    done = 0
    for it in wanted:
        if done >= limit:
            break
        if any(same_event(it, s) for s in out):
            continue
        weak = [s for s in out if not s.get("exam_boosted")]
        if not weak or not accept(it):
            continue
        victim = min(weak, key=lambda x: _rank_key(x)[0])
        out[out.index(victim)] = it
        it["promoted"] = True
        done += 1
    order = {s: i for i, s in enumerate(SECTIONS)}
    return sorted(out, key=lambda x: (order.get(x["section"], 99), -_rank_key(x)[0]))


def build_period(job_type: str, job_date: str, editions: List[Dict[str, Any]],
                 dates: List[str], fetcher: Optional[Any] = None, translators=None) -> Dict[str, Any]:
    """Pure function: daily editions in → {content, mcqs, selected, scored, stats}."""
    if job_type not in SETTINGS:
        raise ValueError(f"period builder needs weekly/monthly, got {job_type!r}")
    cfg = SETTINGS[job_type]
    if len(editions) < cfg["min_days"]:
        raise ValueError(f"only {len(editions)} daily editions found for {job_type} {job_date} "
                         f"(min {cfg['min_days']})")
    period = (dates[0], dates[-1])
    ranked, stats = collect_verified(editions, period)
    if not ranked:
        raise ValueError(f"no verified stories in the {job_type} period")
    verified = {it["event_id"]: it for it in ranked}
    filler = filler_sentences(ranked)
    seen_lines: List[str] = []
    budget = {"fetch": _env_int("ALP_PERIOD_FETCH_MAX", 15)}
    title_only: List[str] = []

    def accept(it: Dict[str, Any]) -> bool:
        if ensure_body(it, seen_lines, filler, budget, fetcher):
            return True
        title_only.append(it["headline_en"][:90])
        return False

    stories = pick_stories(ranked, cfg["stories"], cfg["per_section"], accept=accept)
    stories = promote_big_ticket(stories, ranked, editions, accept)
    stats["title_only_dropped"] = len(title_only)
    stats["title_only_log"] = title_only[:30]
    stats["bodies_rebuilt"] = sum(1 for x in stories if x.get("body_source") == "daily_fields")
    stats["bodies_fetched"] = sum(1 for x in stories if x.get("body_source") == "source_fetch")
    _mark_cover(stories)
    story_ids = [s["event_id"] for s in stories]
    mcqs = pick_mcqs(editions, set(verified), story_ids, cfg["mcqs"], verified)
    balance_answers(mcqs, f"{job_type}_{job_date}")
    first_mcq = {}
    for m in mcqs:
        first_mcq.setdefault(m.get("event_id"), m)
    seen_gk: List[str] = []
    hindi = PeriodHindi(translators)
    qa: Dict[str, Any] = {}
    _clean_headlines(stories, hindi)
    seen_orgs: set = set()
    for s in stories:
        s["summary_pairs"] = _bilingual_pairs(s, hindi, qa)
        _attach_static_gk(s, first_mcq, seen_gk, filler, seen_orgs)
    # A story left with no bilingual bullet would print headline-only: drop it (counted above).
    empty = [x for x in stories if not x.get("summary_pairs")]
    if empty:
        qa["stories_dropped_no_hindi"] = [x.get("headline_en", "")[:90] for x in empty]
        stories = [x for x in stories if x.get("summary_pairs")]
        story_ids = [x["event_id"] for x in stories]
    period_hindi_qa(qa)
    for w in qa["warnings"]:
        print(f"[period-qa] WARNING {w}")
    if not qa["passed"] and os.getenv("DRY_RUN", "0") == "1":
        # Offline dry runs have no translator (and fallback Hindi): report, don't block.
        print(f"[period-qa] WARNING dry run: {qa['bullets_missing_hi']} of {qa['bullets_expected']} bullets "
              f"lack clean Hindi (would fail a live edition)")
    elif not qa["passed"]:
        raise ValueError(f"{job_type} {job_date}: {qa['bullets_missing_hi']} of {qa['bullets_expected']} story "
                         f"bullets have no clean Hindi ({qa['missing_ratio']:.0%} > allowed); edition not built")
    start, end = dates[0], dates[-1]
    if job_type == "weekly":
        title_range = f"{_fmt(start, False)} – {_fmt(end, True)}"
        title = f"Weekly Current Affairs {title_range}"
    else:
        x = date.fromisoformat(start)
        title_range = f"{x.strftime('%B')} {x.year}"
        title = f"Monthly Current Affairs {title_range}"
    content: Dict[str, Any] = {
        "job": {"id": f"{job_type}_{job_date}", "type": job_type, "date": job_date,
                "date_display": title_range, "period_start": start, "period_end": end},
        "edition_title": title,
        "items": stories,
        "one_liners": _clean_one_liners(
            pick_one_liners(editions, verified, story_ids, cfg["one_liners"] * 2, period, stats),
            verified, hindi, cfg["one_liners"], qa),
        "agri_corner": _clean_agri(
            pick_agri_corner(editions, cfg["agri"], cfg["agri_gk"], period, seen_orgs, seen_gk, stats), hindi, qa),
        "source_days": [e["date"] for e in editions],
        "missing_days": [d for d in dates if d not in {e["date"] for e in editions}],
    }
    if job_type == "monthly":
        content["quick_tables"] = build_quick_tables(ranked, cfg["table_rows"])
    stats.update({"verified_unique": len(ranked), "stories": len(stories), "mcqs": len(mcqs),
                  "one_liners": len(content["one_liners"])})
    content["period_stats"] = stats
    qa["hindi_postfix"] = dict(hindi.stats)
    content["period_qa"] = qa
    period = {"start": start, "end": end, "type": job_type}
    return {"content": content, "mcqs": mcqs, "stats": stats,
            "selected": {"items": stories, "period": period},
            "scored": {"items": ranked, "period": period}}


def build(ctx) -> int:
    """Stage entry (agents/20_weekly_editor.py, agents/21_monthly_editor.py)."""
    from pipeline.persistence import write_json_atomic
    dates = period_dates(ctx.job_type, ctx.job_date)
    editions = load_daily_editions(dates)
    result = build_period(ctx.job_type, ctx.job_date, editions, dates)
    write_json_atomic(ctx.output_path("scored"), result["scored"])
    write_json_atomic(ctx.output_path("selected"), result["selected"])
    write_json_atomic(ctx.output_path("content"), result["content"])
    write_json_atomic(ctx.output_path("mcq"), result["mcqs"])
    s = result["stats"]
    print(f"{ctx.job_type} {ctx.job_date}: {s['days']} daily editions, {s['verified_unique']} verified unique, "
          f"{s['stories']} stories, {s['mcqs']} MCQs (dropped {s['unverified_dropped']} unverified, "
          f"{s['duplicates_dropped']} duplicates); missing days: {result['content']['missing_days']}")
    return 0
