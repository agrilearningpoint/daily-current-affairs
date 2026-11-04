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
from typing import Any, Dict, Iterable, List, Optional, Tuple

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
                                     r"vaccine|climate|cyclone|earthquake|species)\b", re.I)),
    ("Economy", re.compile(r"\b(?:rbi|gdp|inflation|repo|bank(?:s|ing)?|gst|tax|exports?|imports?|trade|fdi|investment|"
                           r"market|sebi|budget|fiscal|economy|economic|rupee|ipo|manufacturing\s+facility)\b", re.I)),
    ("Agriculture", re.compile(r"\b(?:farmers?|agri\w*|crops?|kharif|rabi|msp|paddy|wheat|fisher\w*|dairy|"
                               r"livestock|horticulture|icar|nabard|fertili[sz]er|irrigation)\b", re.I)),
    ("International", re.compile(r"\b(?:bilateral|foreign\s+office|state\s+visit|joint\s+statement|summit|"
                                 r"united\s+nations|\bun\b|g20|brics|quad|asean|embassy)\b", re.I)),
]


def section_for(item: Dict[str, Any]) -> str:
    """Map a daily category onto a period section; generic categories are refined by headline keywords."""
    cat = str(item.get("category") or "").lower()
    head = f"{item.get('headline_en', '')}"
    if "important day" in cat:
        return "Important Days"
    if "sport" in cat:
        return "Sports"
    if any(k in cat for k in ("appoint", "award", "person", "obituar")):
        return "Appointments & Awards"
    if any(k in cat for k in ("agri", "rural", "farm", "fisher", "animal", "food")):
        return "Agriculture"
    if any(k in cat for k in ("defence", "defense", "science", "tech", "space", "environment", "health")):
        return "Defence & Science"
    if any(k in cat for k in ("econom", "bank", "financ", "business", "budget", "trade", "market")):
        return "Economy"
    international = any(k in cat for k in ("international", "world", "global", "foreign"))
    for sec, rx in _KEYWORD_SECTIONS:
        if rx.search(head) and not (international and sec in ("Economy", "Agriculture")):
            return sec
    return "International" if international else "National"


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
    return it


def collect_verified(editions: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    stats = {"days": len(editions), "items_seen": 0, "unverified_dropped": 0, "non_news_dropped": 0,
             "duplicates_dropped": 0}
    pool: List[Dict[str, Any]] = []
    strict = os.getenv("DRY_RUN", "0") != "1"
    for ed in editions:
        for raw in ed["content"].get("items") or []:
            stats["items_seen"] += 1
            if not is_publishable(raw, require_verified=strict):
                stats["unverified_dropped"] += 1
                continue
            if not looks_like_news(raw.get("headline_en")):
                stats["non_news_dropped"] = stats.get("non_news_dropped", 0) + 1
                continue
            pool.append(_story(raw, ed["date"]))
    return dedupe(pool, stats), stats


def _rank_key(it: Dict[str, Any]) -> Tuple[float, str]:
    try:
        score = float(it.get("importance_score") or 0)
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


def pick_stories(ranked: List[Dict[str, Any]], total: int, per_section: int) -> List[Dict[str, Any]]:
    """Top stories by importance with a per-section cap, returned in section order."""
    chosen: List[Dict[str, Any]] = []
    counts: Dict[str, int] = {}
    # Every section that has news gets its best story first, then importance decides.
    for sec in SECTIONS:
        best = next((x for x in ranked if x["section"] == sec), None)
        if best is not None and len(chosen) < total:
            chosen.append(best)
            counts[sec] = 1
    picked = {id(x) for x in chosen}
    for it in ranked:
        if len(chosen) >= total:
            break
        if id(it) in picked or counts.get(it["section"], 0) >= per_section:
            continue
        counts[it["section"]] = counts.get(it["section"], 0) + 1
        chosen.append(it)
        picked.add(id(it))
    if len(chosen) < total:  # caps left room: fill with the best remaining stories
        ids = {id(x) for x in chosen}
        chosen += [x for x in ranked if id(x) not in ids][: total - len(chosen)]
    order = {s: i for i, s in enumerate(SECTIONS)}
    return sorted(chosen, key=lambda x: (order.get(x["section"], 99), -_rank_key(x)[0]))


_LETTERS = "ABCDE"


def _mcq_ok(m: Dict[str, Any]) -> bool:
    q_en, q_hi = clean_headline(m.get("question_en")), clean_headline(m.get("question_hi"))
    if not q_en or _UNTITLED_RE.search(q_en) or not has_devanagari(q_hi):
        return False
    opts = m.get("options_bi") or m.get("options") or []
    if len(opts) < 4:
        return False
    correct = str(m.get("correct") or "").strip().upper()
    return correct in _LETTERS[:len(opts)]


def pick_mcqs(editions: List[Dict[str, Any]], verified_ids: set, story_ids: List[str],
              limit: int) -> List[Dict[str, Any]]:
    """MCQs of verified events only: selected stories first (round-robin), then the rest."""
    by_event: Dict[str, List[Dict[str, Any]]] = {}
    for ed in editions:
        for m in ed["mcqs"]:
            if m.get("event_id") in verified_ids and _mcq_ok(m):
                by_event.setdefault(m["event_id"], []).append(m)
    seen_q: List[str] = []
    out: List[Dict[str, Any]] = []

    def take(m: Dict[str, Any]) -> None:
        key = _norm(clean_headline(m.get("question_en")))
        if key in seen_q or any(is_similar(key, s, 0.9) for s in seen_q):
            return
        seen_q.append(key)
        out.append(dict(m))

    order = list(story_ids) + [e for e in by_event if e not in set(story_ids)]
    rnd = 0
    while len(out) < limit and any(len(by_event.get(e, [])) > rnd for e in order):
        for e in order:
            ms = by_event.get(e, [])
            if len(ms) > rnd and len(out) < limit:
                take(ms[rnd])
        rnd += 1
    for n, m in enumerate(out, 1):
        m["q_num"] = n
    return out


def pick_one_liners(editions, verified: Dict[str, Dict[str, Any]], story_ids: List[str], limit: int):
    out, seen = [], []
    for ed in editions:
        for ol in ed["content"].get("one_liners") or []:
            if not isinstance(ol, dict) or ol.get("event_id") not in verified:
                continue
            en, hi = clean_headline(ol.get("text_en")), clean_headline(ol.get("text_hi"))
            if not en or _UNTITLED_RE.search(en) or not has_devanagari(hi):
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
            if not any(is_similar(it["headline_en"], s) for s in seen):
                out.append({"category": it["section"], "text_en": it["headline_en"],
                            "text_hi": it["headline_hi"], "event_id": eid})
                seen.append(it["headline_en"])
    # Events not already printed as full stories first (fresh revision lines), then
    # the stories' own one-liners, so the digest repeats as little as possible.
    rank = {e: i for i, e in enumerate(story_ids)}
    out.sort(key=lambda o: (o["event_id"] in rank, rank.get(o["event_id"], 0)))
    return out[:limit]


def pick_agri_corner(editions, limit: int, gk_limit: int) -> Dict[str, Any]:
    items, gk, seen, seen_gk = [], [], [], set()
    for ed in editions:
        ac = ed["content"].get("agri_corner") or {}
        for x in ac.get("items") or []:
            if not isinstance(x, dict):
                continue
            en, hi = clean_headline(x.get("en")), clean_headline(x.get("hi"))
            if not en or _UNTITLED_RE.search(en) or not has_devanagari(hi) or any(is_similar(en, s) for s in seen):
                continue
            seen.append(en)
            items.append({"en": en, "hi": hi, "event_id": x.get("event_id", ""), "date": ed["date"]})
        for g in ac.get("static_gk") or []:
            if not isinstance(g, dict):
                continue
            en, hi = clean_headline(g.get("en")), clean_headline(g.get("hi"))
            if en and has_devanagari(hi) and en.lower() not in seen_gk:
                seen_gk.add(en.lower())
                gk.append({"en": en, "hi": hi})
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


def _summary_pairs(it: Dict[str, Any], seen: Optional[List[str]] = None,
                   filler: Optional[set] = None, limit: int = 3) -> List[Dict[str, str]]:
    """Up to ``limit`` whole-sentence bullets of this story, unique within the
    story and across the edition (``seen``), with generic filler dropped."""
    seen = seen if seen is not None else []
    filler = filler or set()
    head = _norm(it.get("headline_en"))
    out: List[Dict[str, str]] = []
    for p in _candidate_pairs(it):
        n = _norm(p["en"])
        if filler_key(p["en"]) in filler or n == head or (head and (n.startswith(head) or is_similar(n, head, _SIM_BULLET))) \
                or _is_dup_text(p["en"], seen):
            continue
        seen.append(n)
        out.append(p)
        if len(out) >= limit:
            break
    # Bilingual lines first, so the summary carries as much Hindi as the daily had.
    out.sort(key=lambda q: 0 if q["hi"] else 1)
    return out


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
                      seen: Optional[List[str]] = None, filler: Optional[set] = None) -> None:
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
    story["static_facts"] = {}
    story["exam_fact_en"] = story["exam_fact_hi"] = ""


# --------------------------------------------------------------------------- #
# Public entry points
# --------------------------------------------------------------------------- #
def _fmt(d: str, with_year: bool) -> str:
    x = date.fromisoformat(d)
    return f"{x.day} {x.strftime('%B')}" + (f" {x.year}" if with_year else "")


def build_period(job_type: str, job_date: str, editions: List[Dict[str, Any]],
                 dates: List[str]) -> Dict[str, Any]:
    """Pure function: daily editions in → {content, mcqs, selected, scored, stats}."""
    if job_type not in SETTINGS:
        raise ValueError(f"period builder needs weekly/monthly, got {job_type!r}")
    cfg = SETTINGS[job_type]
    if len(editions) < cfg["min_days"]:
        raise ValueError(f"only {len(editions)} daily editions found for {job_type} {job_date} "
                         f"(min {cfg['min_days']})")
    ranked, stats = collect_verified(editions)
    if not ranked:
        raise ValueError(f"no verified stories in the {job_type} period")
    verified = {it["event_id"]: it for it in ranked}
    stories = pick_stories(ranked, cfg["stories"], cfg["per_section"])
    story_ids = [s["event_id"] for s in stories]
    mcqs = pick_mcqs(editions, set(verified), story_ids, cfg["mcqs"])
    first_mcq = {}
    for m in mcqs:
        first_mcq.setdefault(m.get("event_id"), m)
    filler = filler_sentences(ranked)
    seen_lines: List[str] = []
    seen_gk: List[str] = []
    for s in stories:
        s["summary_pairs"] = _summary_pairs(s, seen_lines, filler)
        _attach_static_gk(s, first_mcq, seen_gk, filler)
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
        "one_liners": pick_one_liners(editions, verified, story_ids, cfg["one_liners"]),
        "agri_corner": pick_agri_corner(editions, cfg["agri"], cfg["agri_gk"]),
        "source_days": [e["date"] for e in editions],
        "missing_days": [d for d in dates if d not in {e["date"] for e in editions}],
    }
    if job_type == "monthly":
        content["quick_tables"] = build_quick_tables(ranked, cfg["table_rows"])
    stats.update({"verified_unique": len(ranked), "stories": len(stories), "mcqs": len(mcqs),
                  "one_liners": len(content["one_liners"])})
    content["period_stats"] = stats
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
