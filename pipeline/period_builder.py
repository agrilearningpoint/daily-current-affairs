"""Weekly / monthly editions built from the already-published DAILY editions.

The daily pipeline stays the single place where news is collected, verified,
translated and turned into MCQs.  Weekly and monthly editions only *re-use* the
daily editions' content + MCQ JSON (fetched by scripts/fetch_daily_editions.py
into ``data/period_sources/daily_<date>.json``), so they never re-generate or
re-translate anything:

1. load every daily edition of the period (fail-soft: missing days are skipped);
2. keep only publishable items (``needs_review is False`` and
   ``verification_passed is True``, a real headline, Devanagari Hindi);
3. dedupe across days (same ``event_id`` or headline similarity > 0.8);
4. map categories onto the period sections, rank by importance and pick the
   stories, MCQs, one-liners, Agriculture Corner and (monthly) quick tables.

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


def is_publishable(item: Any) -> bool:
    """Mirror of the publisher gate with ALP_ALLOW_FALLBACK_TRANSLATION=0, plus real text."""
    if not isinstance(item, dict):
        return False
    if item.get("needs_review") is not False or item.get("verification_passed") is not True:
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
    for ed in editions:
        for raw in ed["content"].get("items") or []:
            stats["items_seen"] += 1
            if not is_publishable(raw):
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


def dedupe(items: List[Dict[str, Any]], stats: Optional[Dict[str, int]] = None,
           threshold: float = 0.8) -> List[Dict[str, Any]]:
    """Same event_id or headline similarity > threshold → keep the higher-ranked copy."""
    kept: List[Dict[str, Any]] = []
    for it in sorted(items, key=_rank_key, reverse=True):
        dup = any((it.get("event_id") and it.get("event_id") == k.get("event_id"))
                  or is_similar(it["headline_en"], k["headline_en"], threshold) for k in kept)
        if dup:
            if stats is not None:
                stats["duplicates_dropped"] = stats.get("duplicates_dropped", 0) + 1
            continue
        kept.append(it)
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
    rank = {e: i for i, e in enumerate(story_ids)}
    out.sort(key=lambda o: rank.get(o["event_id"], len(rank)))
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


_BOILER_RE = re.compile(
    r"^(?:(?:published|updated|last\s+updated)\s*[-:–]\s*[A-Z][a-z]+\s+\d{1,2},\s+\d{4}\s+\d{1,2}:\d{2}\s*[ap]m\s+IST\s*)?"
    r"(?:photo\s*credit\s*:\s*\S+\s+)?",
    re.IGNORECASE,
)
_GENERIC_FACT_RE = re.compile(r"^(?:fact\s*\d+|key\s+name)\b", re.IGNORECASE)


def _clean_point(text: Any) -> str:
    s = clean_headline(text)
    if re.match(r"(?i)^(?:published|updated|last\s+updated|photo\s*credit)", s):
        s = _BOILER_RE.sub("", s).strip()
        s = re.sub(r"^[-–:\s]+", "", s)
        s = re.sub(r"^[A-Z][A-Z .]{2,30}\s(?=[A-Z][a-z])", "", s)  # "NEW DELHI The ..." dateline
    return s


def _summary_pairs(it: Dict[str, Any]) -> List[Dict[str, str]]:
    """Up to three summary lines: (EN, HI) from the daily key points (Hindi only when it is Devanagari)."""
    en = [_clean_point(x) for x in it.get("key_points_en") or []]
    hi = [clean_headline(x) for x in it.get("key_points_hi") or []]
    pairs = [(e, hi[i] if i < len(hi) and has_devanagari(hi[i]) else "") for i, e in enumerate(en)
             if e and len(e.split()) >= 4]
    if not pairs and _clean_point(it.get("summary_en")):
        h = clean_headline(it.get("summary_hi"))
        pairs = [(_clean_point(it.get("summary_en")), h if has_devanagari(h) else "")]
    # Bilingual lines first, so the summary carries as much Hindi as the daily had.
    pairs.sort(key=lambda p: 0 if p[1] else 1)
    return [{"en": e, "hi": h} for e, h in pairs[:3]]


def _attach_static_gk(story: Dict[str, Any], mcqs_by_event: Dict[str, Dict[str, Any]]) -> None:
    """Carry the story's verified Static GK pairs (daily MCQ schema first) as content pairs."""
    pairs: List[Dict[str, str]] = []

    def add(en: Any, hi: Any) -> None:
        en_c, hi_c = clean_headline(en), clean_headline(hi)
        if en_c and not _GENERIC_FACT_RE.match(en_c) and not any(en_c == q["en"] for q in pairs):
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
    story["static_gk_pairs"] = pairs[:3]
    # The renderer falls back to static_facts only when there are no pairs: keep real facts only.
    sf = story.get("static_facts")
    if isinstance(sf, dict):
        story["static_facts"] = {k: v for k, v in sf.items()
                                 if isinstance(k, str) and not k.startswith("_") and not _GENERIC_FACT_RE.match(k)}


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
    for s in stories:
        s["summary_pairs"] = _summary_pairs(s)
        _attach_static_gk(s, first_mcq)
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
