# -*- coding: utf-8 -*-
"""
STRICT STATIC GK VALIDATOR — officeholders and stale "latest" facts.

Static GK lines are partly LLM-written (stage 16 MCQ ``static_gk`` rows) and
partly curated.  LLMs recall officeholders from training data, which goes out
of date (wrong RBI Governor / ICAR DG / APEDA Chairman were printed).  This
module checks every Static GK line against ``config/current_facts.json``
(verified officeholders, refreshed weekly by scripts/refresh_current_facts.py):

1. A line that mentions a known post (e.g. "RBI Governor") must carry the
   verified name.  A wrong name is replaced with the verified one (or the line
   is dropped for multi-holder posts, or when the story itself reports a new
   appointment, since the facts file may lag a fresh appointment).
2. A line that names an officeholder for a post we do not track is kept only
   when the person's name is verifiable: it appears in current_facts or in the
   story's own source text.  Otherwise it is dropped.
3. A line presenting a year <= current_year - 2 as "current/latest/present"
   (or a stale FY) is dropped.

Hindi pairs follow the English decision: a dropped English line drops its
Hindi; a corrected English line keeps its Hindi only when the Hindi already
carries the verified Hindi name (or the row's Hindi value is just the name and
is replaced by the verified Hindi name).  Otherwise the Hindi is blanked, so
the renderer's existing Devanagari check (``_hi_or_blank``) leaves the line
English-only rather than printing an unverified Hindi name.

FAIL-OPEN: any error while checking a line drops that line if it is
officeholder-type and keeps it otherwise; nothing here ever raises to the
caller (``validate_edition`` / ``validate_lines``).
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

logger = logging.getLogger("agent.static_gk_validator")

ROOT = Path(__file__).resolve().parent.parent
FACTS_PATH = ROOT / "config" / "current_facts.json"

DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")

# Words that mark a line as being about an officeholder.
ROLE_RE = re.compile(
    r"\b(?:chair(?:man|person|woman)?|governor|director[\s-]general|\bDG\b|CEO|chief\s+executive|"
    r"managing\s+director|\bMD\b|president|prime\s+minister|minister|secretary[\s-]general|"
    r"chief\s+justice|chief\s+of|commissioner|chief|head(?:ed)?\s+by|heads|headed|speaker|"
    r"incumbent|current\s+head|present\s+head)\b", re.I)
ROLE_HI_RE = re.compile(r"अध्यक्ष|गवर्नर|महानिदेशक|मंत्री|प्रमुख|सीईओ|प्रबंध निदेशक|राष्ट्रपति|न्यायाधीश|आयुक्त|सचिव")

CURRENT_RE = re.compile(r"\b(?:current(?:ly)?|latest|present(?:ly)?|now|recent(?:ly)?|incumbent|as\s+of|"
                        r"at\s+present|so\s+far|till\s+date|to\s+date|this\s+year)\b", re.I)
CURRENT_HI_RE = re.compile(r"वर्तमान|नवीनतम|हाल|अब तक|मौजूदा|ताज़ा|ताजा")
YEAR_RE = re.compile(r"(?<!\d)(19\d{2}|20\d{2})(?:\s*[-–/]\s*(\d{2,4}))?(?!\d)")
FY_RE = re.compile(r"\bFY\s*'?(\d{2,4})(?:\s*[-–/]\s*(\d{2,4}))?\b", re.I)

# Country / demonym words that make a generic post phrase ("Army Chief") foreign.
FOREIGN_RE = re.compile(
    r"\b(?:pakistan(?:i)?|china|chinese|u\.?s\.?a?|united\s+states|america(?:n)?|bangladesh(?:i)?|nepal(?:i|ese)?|"
    r"sri\s+lanka(?:n)?|bhutan(?:ese)?|myanmar|japan(?:ese)?|russia(?:n)?|u\.?k\.?|british|britain|france|french|"
    r"german(?:y)?|israel(?:i)?|iran(?:ian)?|afghan(?:istan)?|australia(?:n)?|canada|canadian|korea(?:n)?|"
    r"italy|italian|maldives|maldivian|ukrain(?:e|ian)|brazil(?:ian)?|saudi|uae|egypt(?:ian)?|turkey|turkish)\b",
    re.I)
FOREIGN_HI_RE = re.compile(r"पाकिस्तान|चीन|अमेरिका|बांग्लादेश|नेपाल|श्रीलंका|जापान|रूस|ब्रिटेन|फ्रांस|जर्मनी|इज़राइल|इजराइल|ईरान")

# Capitalised words that are never part of a person's name in these lines.
_NOT_NAME = {
    "the", "of", "and", "for", "in", "on", "at", "to", "by", "a", "an", "is", "was", "as", "its", "his", "her",
    "india", "indian", "bharat", "union", "government", "ministry", "minister", "department", "national", "central",
    "reserve", "bank", "rbi", "sebi", "niti", "aayog", "icar", "dare", "apeda", "nabard", "nddb", "fssai", "iffco",
    "isro", "upsc", "cag", "fao", "wto", "who", "imf", "un", "world", "international", "monetary", "fund", "trade",
    "organization", "organisation", "health", "food", "agriculture", "agricultural", "farmers", "welfare", "rural",
    "development", "council", "research", "board", "authority", "commission", "committee", "corporation",
    "securities", "exchange", "dairy", "export", "products", "processed", "space", "public", "service",
    "governor", "deputy", "chairman", "chairperson", "chair", "chief", "executive", "officer", "director", "general",
    "managing", "secretary", "president", "vice", "prime", "justice", "supreme", "court", "election",
    "commissioner", "comptroller", "auditor", "staff", "army", "navy", "naval", "air", "force", "defence", "head",
    "headquarters", "hq", "established", "founded", "formed", "set", "up", "year", "current", "latest", "present",
    "new", "delhi", "mumbai", "kolkata", "chennai", "bengaluru", "hyderabad", "geneva", "rome", "washington",
    "anand", "gujarat", "established:", "est", "act", "scheme", "mission", "yojana", "pradhan", "mantri",
    "nodal", "parent", "capital", "state", "city", "country", "launched", "launch", "member", "members",
    "rajya", "sabha", "lok", "parliament", "constitution", "article", "ex-officio", "society", "cooperative",
    "fertiliser", "fertilizer", "limited", "ltd", "standards", "safety", "statutory", "body", "apex",
    "regulator", "regulatory", "bureau", "information", "press", "pib", "january", "february", "march", "april",
    "may", "june", "july", "august", "september", "october", "november", "december", "monday", "tuesday",
    "wednesday", "thursday", "friday", "saturday", "sunday", "fy", "gdp", "cpi", "repo", "rate", "policy",
    "jai", "jawan", "kisan", "vigyan", "first", "largest", "highest", "smallest",
    "key", "name", "names", "fact", "facts", "note", "notes", "point", "points", "theme", "exam",
    "south", "north", "east", "west", "block", "bhawan", "bhavan", "road", "marg", "house", "nagar", "office",
    "pmo", "acting", "independent", "charge", "statutory", "norms", "per", "chief", "minister's",
}
_TITLE_RE = r"(?:(?:Shri|Smt|Sri|Dr|Mr|Ms|Mrs|Prof|Gen|General|Adm|Admiral|Air\s+Chief\s+Marshal|Justice|Lt\.?\s*Gen)\.?\s+)?"
_TOK = r"(?:(?:[A-Z]\.\s?){1,4}(?=\s|[A-Z])|[A-Z][a-zA-Z'’\-]+|[A-Z](?=\s))"
NAME_RE = re.compile(_TITLE_RE + r"(" + _TOK + r"(?:\s*" + _TOK + r"){1,4})")
_TITLE_STRIP_RE = re.compile(r"^(?:Shri|Smt|Sri|Dr|Mr|Ms|Mrs|Prof|Gen|General|Adm|Admiral|Air Chief Marshal|Justice|Lt\.?\s*Gen)\.?\s+", re.I)
# Historical lines ("First Chief Justice – H. J. Kania", "Founded by ...", "former Governor") are timeless facts.
HISTORICAL_RE = re.compile(r"\b(?:first|former|founding|founder|founded|established\s+by|set\s+up\s+by|late|"
                           r"erstwhile|ex-|previous|predecessor|succeeded|outgoing|retired|was\s+the|served\s+as|"
                           r"till\s+\d{4}|until\s+\d{4}|from\s+\d{4}\s+to)\b", re.I)
HISTORICAL_HI_RE = re.compile(r"पहले|प्रथम|पूर्व|संस्थापक")
APPOINTMENT_RE = re.compile(r"\b(?:appoint(?:ed|s|ment)|takes?\s+(?:over|charge)|took\s+(?:over|charge)|"
                            r"assume[sd]?\s+(?:charge|office)|sworn|new(?:ly)?\s+(?:appointed|named)|named\s+as|"
                            r"succeed(?:s|ed)?|elected)\b", re.I)


# --------------------------------------------------------------------------- #
# Facts
# --------------------------------------------------------------------------- #
@dataclass
class Fact:
    id: str
    post: str
    name: str
    names: List[str]
    aliases: List[str]
    name_hi: str
    match: List[str]
    match_hi: List[str]
    rx: Optional[re.Pattern] = None
    rx_hi: Optional[re.Pattern] = None

    @property
    def multi(self) -> bool:
        return len(self.names) > 1

    def valid_names(self) -> List[str]:
        return [n for n in dict.fromkeys([self.name, *self.names, *self.aliases]) if n]


def _norm(s: str) -> str:
    s = _TITLE_STRIP_RE.sub("", str(s or "").strip())
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def _phrase_rx(phrases: Sequence[str], hindi: bool = False) -> Optional[re.Pattern]:
    ps = sorted({p for p in phrases if p}, key=len, reverse=True)
    if not ps:
        return None
    body = "|".join(re.escape(p).replace(r"\ ", r"\s+") for p in ps)
    if hindi:
        return re.compile(f"(?:{body})")
    return re.compile(rf"(?<![A-Za-z])(?:{body})(?![A-Za-z])", re.I)


def load_facts(path: Optional[Path] = None) -> List[Fact]:
    """Load config/current_facts.json. Returns [] when missing/invalid (callers fail open)."""
    p = Path(path or os.getenv("ALP_CURRENT_FACTS", "") or FACTS_PATH)
    data = json.loads(p.read_text(encoding="utf-8"))
    out: List[Fact] = []
    for f in data.get("facts") or []:
        if not isinstance(f, dict) or not f.get("name") or not f.get("match"):
            continue
        fact = Fact(id=str(f.get("id") or f.get("post")), post=str(f.get("post") or ""), name=str(f["name"]),
                    names=[str(x) for x in f.get("names") or []], aliases=[str(x) for x in f.get("aliases") or []],
                    name_hi=str(f.get("name_hi") or ""), match=[str(x) for x in f.get("match") or []],
                    match_hi=[str(x) for x in f.get("match_hi") or []])
        fact.rx = _phrase_rx(fact.match)
        fact.rx_hi = _phrase_rx(fact.match_hi, hindi=True)
        out.append(fact)
    return out


# --------------------------------------------------------------------------- #
# Line checks
# --------------------------------------------------------------------------- #
@dataclass
class Verdict:
    action: str                 # keep | replace | drop
    en: str = ""
    hi: str = ""
    reason: str = ""
    fact_id: str = ""
    wrong: str = ""             # the wrong name that was replaced
    new_name: str = ""          # verified name put in (AI lookup; facts use fact.name)
    source: str = ""            # official source of an AI-verified name


@dataclass
class Report:
    checked: int = 0
    kept: int = 0
    replaced: int = 0
    dropped: int = 0
    errors: int = 0
    ai_verified: int = 0
    details: List[Dict[str, str]] = field(default_factory=list)

    def add(self, v: Verdict, en: str) -> None:
        self.checked += 1
        if v.new_name:
            self.ai_verified += 1
        if v.action == "keep":
            self.kept += 1
            return
        if v.action == "replace":
            self.replaced += 1
        else:
            self.dropped += 1
        if len(self.details) < 60:
            self.details.append({"action": v.action, "reason": v.reason, "line": en[:160],
                                 "new": v.en[:160] if v.action == "replace" else ""})

    def as_dict(self) -> Dict[str, Any]:
        out = {"checked": self.checked, "kept": self.kept, "replaced": self.replaced,
               "dropped": self.dropped, "errors": self.errors, "details": self.details}
        if _ACTIVE_LOOKUP is not None:
            out["ai_lookup"] = dict(getattr(_ACTIVE_LOOKUP, "stats", {}) or {})
            out["ai_lookup"]["verified_lines"] = self.ai_verified
        return out


def current_year() -> int:
    d = os.getenv("ALP_JOB_DATE", "")
    m = re.match(r"(\d{4})-\d{2}-\d{2}", d)
    return int(m.group(1)) if m else datetime.now(timezone.utc).year


def _years(text: str) -> List[int]:
    ys: List[int] = []
    for m in YEAR_RE.finditer(text):
        ys.append(int(m.group(1)))
        if m.group(2):
            tail = m.group(2)
            ys.append(int(tail) if len(tail) == 4 else int(m.group(1)[:2] + tail))
    for m in FY_RE.finditer(text):
        for g in m.groups():
            if g:
                ys.append(int(g) if len(g) == 4 else 2000 + int(g))
    return ys


def is_stale_latest(en: str, hi: str = "", year: Optional[int] = None) -> bool:
    """A year <= current_year-2 presented as current / latest / present."""
    year = year or current_year()
    if not (CURRENT_RE.search(en or "") or CURRENT_HI_RE.search(hi or "")):
        return False
    ys = _years(en or "") or _years(hi or "")
    # The newest year in the line decides: "latest (2023-24)" is stale, "since 2019, latest 2026" is not.
    return bool(ys) and max(ys) <= year - 2


def is_officeholder_line(en: str, hi: str = "") -> bool:
    return bool(ROLE_RE.search(en or "") or (not en and ROLE_HI_RE.search(hi or "")))


def _foreign_context(text: str, start: int, end: int) -> bool:
    before = text[max(0, start - 30):start]
    after = text[end:end + 25]
    return bool(FOREIGN_RE.search(before) or FOREIGN_RE.search(after)
                or FOREIGN_HI_RE.search(before) or FOREIGN_HI_RE.search(after))


def _post_hits(en: str, facts: Sequence[Fact]) -> List[Tuple[Fact, int, int]]:
    """Known posts mentioned in the line, longest phrase first, non-overlapping, not foreign."""
    cands: List[Tuple[int, int, Fact]] = []
    for f in facts:
        if not f.rx:
            continue
        for m in f.rx.finditer(en):
            cands.append((m.start(), m.end(), f))
    cands.sort(key=lambda c: (-(c[1] - c[0]), c[0]))
    taken: List[Tuple[int, int]] = []
    out: List[Tuple[Fact, int, int]] = []
    for s, e, f in cands:
        if any(s < te and e > ts for ts, te in taken):
            continue
        taken.append((s, e))
        if _foreign_context(en, s, e):
            continue
        out.append((f, s, e))
    return out


def _contains_name(text: str, names: Iterable[str]) -> bool:
    t = f" {_norm(text)} "
    return any(_norm(n) and f" {_norm(n)} " in t for n in names)


def name_candidates(text: str, mask: Sequence[Tuple[int, int]] = ()) -> List[Tuple[str, int, int]]:
    """Person-name-like spans (2-5 capitalised tokens, not org/post words, outside masked spans)."""
    out: List[Tuple[str, int, int]] = []
    for m in NAME_RE.finditer(text or ""):
        s, e = m.span()
        toks = [t.strip(".,;:()’'") for t in m.group(1).split()]
        def _bad(t: str) -> bool:
            return not t or t.lower().rstrip(".") in _NOT_NAME or bool(FOREIGN_RE.fullmatch(t))
        name_toks = [t for t in toks if not _bad(t)]
        # Rebuild the longest contiguous run of name-like tokens.
        run: List[str] = []
        best: List[str] = []
        for t in toks:
            if not _bad(t):
                run.append(t)
                if len(run) > len(best):
                    best = list(run)
            else:
                run = []
        if len(name_toks) < 2 or len(best) < 2:
            continue
        idx = text.find(best[0], s)
        if idx < 0:
            continue
        last = text.find(best[-1], idx + len(best[0]) - 1 if len(best) > 1 else idx)
        end = (last + len(best[-1])) if last >= 0 else e
        while end < len(text) and text[end] == ".":
            end += 1
        if any(idx < me and end > ms for ms, me in mask):
            continue
        out.append((text[idx:end].strip(), idx, end))
    return out


def _story_has(text: str, story_text: str) -> bool:
    return bool(story_text) and _contains_name(story_text, [text])


def check_line(en: str, hi: str, facts: Sequence[Fact], *, story_text: str = "",
               year: Optional[int] = None, lookup: Any = None) -> Verdict:
    """Decide keep / replace / drop for one bilingual Static GK line. May raise (callers fail open)."""
    en = str(en or "")
    hi = str(hi or "")
    if is_stale_latest(en, hi, year):
        return Verdict("drop", reason="stale year presented as current/latest")
    if HISTORICAL_RE.search(en) or (not en and HISTORICAL_HI_RE.search(hi)):
        return Verdict("keep", en=en, hi=hi, reason="historical fact")
    hits = _post_hits(en, facts)
    if hits:
        mask = [(s, e) for _f, s, e in hits]
        cands = name_candidates(en, mask)
        new_en, new_hi = en, hi
        replaced_any = False
        for f, _s, _e in hits:
            if _contains_name(en, f.valid_names()):
                continue
            wrong = [c for c in cands if not _contains_name(c[0], f.valid_names())]
            if not wrong:
                continue  # post mentioned without any person name ("RBI Governor chairs the MPC")
            w = wrong[0][0]
            if f.multi:
                return Verdict("drop", reason=f"unverified holder for multi-holder post {f.id}", fact_id=f.id, wrong=w)
            if story_text and _story_has(w, story_text) and APPOINTMENT_RE.search(story_text):
                return Verdict("drop", reason=f"story reports a new {f.post}; facts may lag", fact_id=f.id, wrong=w)
            if w not in new_en:
                return Verdict("drop", reason=f"wrong officeholder for {f.id} (could not rewrite)", fact_id=f.id, wrong=w)
            new_en = new_en.replace(w, f.name)
            if f.name_hi and f.name_hi in new_hi:
                pass
            else:
                new_hi = ""
            replaced_any = True
            fid, wname = f.id, w
        if replaced_any:
            return Verdict("replace", en=new_en, hi=new_hi, reason=f"wrong officeholder for {fid}",
                           fact_id=fid, wrong=wname)
        return Verdict("keep", en=en, hi=hi)
    # No tracked post: an officeholder line must name a verifiable person.
    if is_officeholder_line(en, hi):
        cands = name_candidates(en)
        all_names = [n for f in facts for n in f.valid_names()]
        unver = [c for c in cands if not (_contains_name(c[0], all_names) or _story_has(c[0], story_text))]
        if unver:
            v = _ai_verdict(en, hi, unver, lookup if lookup is not None else _ACTIVE_LOOKUP, story_text)
            if v is not None:
                return v
            return Verdict("drop", reason="officeholder name not verifiable", wrong=unver[0][0])
    return Verdict("keep", en=en, hi=hi)


# Set by validate_edition for the run (None = no AI lookup, today's behaviour).
_ACTIVE_LOOKUP: Any = None


def _ai_verdict(en: str, hi: str, unverified: Sequence[Tuple[str, int, int]], lookup: Any,
                story_text: str) -> Optional[Verdict]:
    """Verify an untracked post's holder through the AI lookup. None -> caller drops the line.

    Exactly one unverified person name may remain once name-like words inside the post
    phrase ("Chief Minister of Uttar Pradesh") are set aside; anything else is dropped."""
    if lookup is None:
        return None
    from agents.static_gk_ai_lookup import extract_post, post_spans
    spans = post_spans(en)
    persons = [c for c in unverified if not any(s <= c[1] and c[2] <= e for s, e in spans)]
    if len(persons) != 1:
        return None
    cand = persons[0][0]
    post = extract_post(en, cand)
    if not post:
        return None
    res = lookup(post)
    if not res or not getattr(res, "name", ""):
        return None
    name = res.name
    if _contains_name(cand, [name]) or _contains_name(name, [cand]):
        return Verdict("keep", en=en, hi=hi, reason=f"AI-verified holder of {post}", new_name=name,
                       source=res.source_url)
    if story_text and _story_has(cand, story_text) and APPOINTMENT_RE.search(story_text):
        return None  # the story reports a newer appointment; never overwrite it
    if cand not in en:
        return None
    new_en = en.replace(cand, name)
    # Hindi: the same (Latin) name is replaced; a Devanagari name cannot be verified -> blank (EN-only).
    new_hi = hi.replace(cand, name) if cand and cand in hi else ""
    return Verdict("replace", en=new_en, hi=new_hi, reason=f"AI-verified holder of {post}",
                   fact_id=f"ai:{post}", wrong=cand, new_name=name, source=res.source_url)


def check_row(row: Dict[str, Any], facts: Sequence[Fact], *, story_text: str = "",
              year: Optional[int] = None) -> Tuple[str, Dict[str, Any], Verdict]:
    """MCQ schema row {label_en, value_en, label_hi, value_hi}. Returns (action, new_row, verdict)."""
    le, ve = str(row.get("label_en") or ""), str(row.get("value_en") or "")
    lh, vh = str(row.get("label_hi") or ""), str(row.get("value_hi") or "")
    en = f"{le} – {ve}" if le and ve else (le or ve)
    hi = f"{lh} – {vh}" if lh and vh else (lh or vh)
    v = check_line(en, hi, facts, story_text=story_text, year=year)
    if v.action != "replace":
        return v.action, dict(row), v
    new = dict(row)
    fact = next((f for f in facts if f.id == v.fact_id), None)
    good = v.new_name or (fact.name if fact else "")
    if v.wrong and good and v.wrong in ve:
        new["value_en"] = ve.replace(v.wrong, good)
    elif v.wrong and good and v.wrong in le:
        new["label_en"] = le.replace(v.wrong, good)
    else:
        new["value_en"] = v.en
    if v.new_name and not fact:  # AI-verified: same name replaced in Hindi if written in Latin, else EN-only
        if v.wrong and v.wrong in vh:
            new["value_hi"] = vh.replace(v.wrong, v.new_name)
        else:
            new["value_hi"] = ""
        return "replace", new, v
    # Hindi: a value that was just the (wrong) name becomes the verified Hindi name; otherwise
    # keep it only if it already carries the verified Hindi name, else blank it (EN-only line).
    if fact and fact.name_hi and fact.name_hi in vh:
        pass
    elif fact and fact.name_hi and _norm(ve) == _norm(v.wrong):
        new["value_hi"] = fact.name_hi
    else:
        new["value_hi"] = ""
    return "replace", new, v


# --------------------------------------------------------------------------- #
# Edition-level
# --------------------------------------------------------------------------- #
def _story_text(item: Dict[str, Any]) -> str:
    parts = []
    for k in ("headline_en", "title", "summary_en", "detailed_explanation_en", "question_en"):
        v = item.get(k)
        if isinstance(v, str):
            parts.append(v)
    for k in ("key_points_en",):
        v = item.get(k)
        if isinstance(v, list):
            parts.extend(str(x) for x in v)
    return " ".join(parts)


def _safe_line(fn, en: str, hi: str, report: Report):
    try:
        return fn()
    except Exception as exc:  # fail open: officeholder-type lines are dropped, others kept
        report.errors += 1
        logger.warning("[static-gk] check failed (%s); %s line", exc,
                       "dropping officeholder" if is_officeholder_line(en, hi) else "keeping")
        return None


def validate_pairs(pairs: Any, facts: Sequence[Fact], report: Report, story_text: str = "",
                   year: Optional[int] = None) -> Any:
    """Validate a list of {en, hi} dicts / (en, hi) tuples / strings. Returns the filtered list (same shapes)."""
    if not isinstance(pairs, list):
        return pairs
    out = []
    for p in pairs:
        if isinstance(p, dict):
            en, hi = str(p.get("en") or ""), str(p.get("hi") or "")
        elif isinstance(p, (list, tuple)) and p:
            en, hi = str(p[0] or ""), str(p[1] if len(p) > 1 else "")
        elif isinstance(p, str):
            en, hi = p, ""
        else:
            out.append(p)
            continue
        v = _safe_line(lambda: check_line(en, hi, facts, story_text=story_text, year=year), en, hi, report)
        if v is None:
            v = Verdict("drop" if is_officeholder_line(en, hi) else "keep", en=en, hi=hi, reason="validator error")
        report.add(v, en)
        if v.action == "drop":
            continue
        if v.action == "keep":
            out.append(p)
            continue
        if isinstance(p, dict):
            q = dict(p)
            q["en"], q["hi"] = v.en, v.hi
            out.append(q)
        elif isinstance(p, tuple):
            out.append((v.en, v.hi))
        elif isinstance(p, list):
            out.append([v.en, v.hi])
        else:
            out.append(v.en)
    return out


def validate_rows(rows: Any, facts: Sequence[Fact], report: Report, story_text: str = "",
                  year: Optional[int] = None) -> Any:
    if not isinstance(rows, list):
        return rows
    out = []
    for r in rows:
        if not isinstance(r, dict) or not ("label_en" in r or "value_en" in r):
            if isinstance(r, dict) and ("en" in r or "hi" in r):
                out.extend(validate_pairs([r], facts, report, story_text, year))
            else:
                out.append(r)
            continue
        en = f"{r.get('label_en', '')} – {r.get('value_en', '')}"
        res = _safe_line(lambda: check_row(r, facts, story_text=story_text, year=year), en,
                         f"{r.get('label_hi', '')} {r.get('value_hi', '')}", report)
        if res is None:
            act = "drop" if is_officeholder_line(en) else "keep"
            report.add(Verdict(act, en=en, reason="validator error"), en)
            if act == "keep":
                out.append(r)
            continue
        action, new, v = res
        report.add(v, en)
        if action != "drop":
            out.append(new if action == "replace" else r)
    return out


def validate_static_facts(sf: Any, facts: Sequence[Fact], report: Report, story_text: str = "",
                          year: Optional[int] = None) -> Any:
    if not isinstance(sf, dict):
        return sf
    out = {}
    for k, val in sf.items():
        if not isinstance(k, str) or k.startswith("_") or not isinstance(val, (str, int, float)):
            out[k] = val
            continue
        en = f"{k} – {val}"
        v = _safe_line(lambda: check_line(en, "", facts, story_text=story_text, year=year), en, "", report)
        if v is None:
            v = Verdict("drop" if is_officeholder_line(en) else "keep", reason="validator error")
        report.add(v, en)
        if v.action == "keep":
            out[k] = val
        elif v.action == "replace":
            prefix = f"{k} – "
            out[k] = v.en[len(prefix):] if v.en.startswith(prefix) else v.en
    return out


def _mcq_list(mcq_data: Any) -> List[Dict[str, Any]]:
    if isinstance(mcq_data, list):
        return [m for m in mcq_data if isinstance(m, dict)]
    if isinstance(mcq_data, dict):
        return [m for m in mcq_data.get("mcqs") or [] if isinstance(m, dict)]
    return []


def make_lookup() -> Any:
    """The run's AI lookup (agents/static_gk_ai_lookup.py) or None. Never raises."""
    try:
        from agents.static_gk_ai_lookup import Lookup
        return Lookup()
    except Exception as exc:
        logger.info("[static-gk] AI lookup unavailable: %s", exc)
        return None


def validate_edition(content: Dict[str, Any], mcq_data: Any = None,
                     facts: Optional[Sequence[Fact]] = None, lookup: Any = "auto") -> Dict[str, Any]:
    """Validate every Static GK line of an edition in place. Never raises; returns a report dict.

    ``lookup``: "auto" builds the AI lookup for untracked posts (a no-op without
    SERPER_API_KEY / an LLM provider / network, and under pytest); None disables it."""
    global _ACTIVE_LOOKUP
    _ACTIVE_LOOKUP = make_lookup() if lookup == "auto" else lookup
    try:
        return _validate_edition(content, mcq_data, facts)
    finally:
        _ACTIVE_LOOKUP = None


def _validate_edition(content: Dict[str, Any], mcq_data: Any = None,
                      facts: Optional[Sequence[Fact]] = None) -> Dict[str, Any]:
    report = Report()
    year = current_year()
    try:
        if facts is None:
            facts = load_facts()
    except Exception as exc:
        logger.warning("[static-gk] current_facts unavailable (%s): dropping officeholder-type lines", exc)
        return drop_officeholder_lines(content, mcq_data, reason=f"facts unavailable: {exc}")
    try:
        items = [it for it in (content.get("items") or []) if isinstance(it, dict)]
        by_event = {str(it.get("event_id")): it for it in items}
        for it in items:
            st = _story_text(it)
            for key in ("static_gk_pairs", "static_gk"):
                if key in it:
                    it[key] = (validate_rows if key == "static_gk" else validate_pairs)(it[key], facts, report, st, year)
            if "static_facts" in it:
                it["static_facts"] = validate_static_facts(it["static_facts"], facts, report, st, year)
        ac = content.get("agri_corner")
        if isinstance(ac, dict) and "static_gk" in ac:
            ac["static_gk"] = validate_pairs(ac["static_gk"], facts, report, "", year)
        for m in _mcq_list(mcq_data):
            st = _story_text(by_event.get(str(m.get("event_id")), {})) + " " + str(m.get("question_en") or "")
            if "static_gk" in m:
                m["static_gk"] = validate_rows(m["static_gk"], facts, report, st, year)
    except Exception as exc:  # last-resort fail-open
        logger.warning("[static-gk] validator aborted (%s): dropping officeholder-type lines", exc)
        return drop_officeholder_lines(content, mcq_data, reason=f"validator error: {exc}")
    out = report.as_dict()
    logger.info("[static-gk] checked=%d kept=%d replaced=%d dropped=%d errors=%d",
                report.checked, report.kept, report.replaced, report.dropped, report.errors)
    return out


def drop_officeholder_lines(content: Dict[str, Any], mcq_data: Any = None, reason: str = "") -> Dict[str, Any]:
    """Fail-open fallback: remove every officeholder-type Static GK line (regex only). Never raises."""
    dropped = 0

    def keep_pair(p: Any) -> bool:
        nonlocal dropped
        try:
            if isinstance(p, dict):
                en = str(p.get("en") or f"{p.get('label_en', '')} {p.get('value_en', '')}")
                hi = str(p.get("hi") or f"{p.get('label_hi', '')} {p.get('value_hi', '')}")
            elif isinstance(p, (list, tuple)) and p:
                en, hi = str(p[0] or ""), str(p[1] if len(p) > 1 else "")
            else:
                en, hi = str(p or ""), ""
            if is_officeholder_line(en, hi):
                dropped += 1
                return False
        except Exception:
            return True
        return True

    try:
        for it in content.get("items") or []:
            if not isinstance(it, dict):
                continue
            for key in ("static_gk_pairs", "static_gk"):
                if isinstance(it.get(key), list):
                    it[key] = [p for p in it[key] if keep_pair(p)]
            if isinstance(it.get("static_facts"), dict):
                it["static_facts"] = {k: v for k, v in it["static_facts"].items()
                                      if not isinstance(v, str) or keep_pair(f"{k} – {v}")}
        ac = content.get("agri_corner")
        if isinstance(ac, dict) and isinstance(ac.get("static_gk"), list):
            ac["static_gk"] = [p for p in ac["static_gk"] if keep_pair(p)]
        for m in _mcq_list(mcq_data):
            if isinstance(m.get("static_gk"), list):
                m["static_gk"] = [p for p in m["static_gk"] if keep_pair(p)]
    except Exception as exc:  # pragma: no cover
        logger.warning("[static-gk] fallback drop failed: %s", exc)
    return {"checked": 0, "kept": 0, "replaced": 0, "dropped": dropped, "errors": 1,
            "fallback": True, "reason": reason, "details": []}


# --------------------------------------------------------------------------- #
# Prompt helper (stage 16)
# --------------------------------------------------------------------------- #
def facts_for_prompt(text: str, limit: int = 8, facts: Optional[Sequence[Fact]] = None) -> str:
    """Verified officeholders relevant to *text*, one per line, for the MCQ prompt ('' on any error)."""
    try:
        facts = facts if facts is not None else load_facts()
        rel = []
        for f in facts:
            acr = {w for ph in f.match for w in re.findall(r"\b[A-Z]{3,}\b", ph)}
            if (f.rx and f.rx.search(text or "")) or any(re.search(rf"\b{re.escape(w)}\b", text or "") for w in acr):
                names = ", ".join(f.names) if f.multi else f.name
                rel.append(f"- {f.post}: {names}")
            if len(rel) >= limit:
                break
        return "\n".join(rel)
    except Exception:
        return ""
