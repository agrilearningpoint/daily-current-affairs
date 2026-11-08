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
    override: bool = False      # name comes from a verified override (state/ai_facts_cache.json)
    blocked: bool = False       # today's news reports a change that could not be verified -> drop named lines
    stale_names: List[str] = field(default_factory=list)     # earlier / commonly hallucinated holders
    stale_names_hi: List[str] = field(default_factory=list)
    portfolio: List[str] = field(default_factory=list)       # subjects a minister holds (ministers only)
    rank: str = ""                                            # "cabinet" | "mos_ic" | "mos" (ministers only)

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


def _facts_doc(path: Optional[Path] = None) -> Dict[str, Any]:
    p = Path(path or os.getenv("ALP_CURRENT_FACTS", "") or FACTS_PATH)
    return json.loads(p.read_text(encoding="utf-8"))


def load_facts(path: Optional[Path] = None) -> List[Fact]:
    """Load config/current_facts.json. Returns [] when missing/invalid (callers fail open)."""
    data = _facts_doc(path)
    out: List[Fact] = []
    for f in data.get("facts") or []:
        if not isinstance(f, dict) or not f.get("name") or not f.get("match"):
            continue
        lst = lambda k: [str(x) for x in f.get(k) or []]  # noqa: E731
        fact = Fact(id=str(f.get("id") or f.get("post")), post=str(f.get("post") or ""), name=str(f["name"]),
                    names=lst("names"), aliases=lst("aliases"),
                    name_hi=str(f.get("name_hi") or ""), match=lst("match"), match_hi=lst("match_hi"),
                    stale_names=lst("stale_names"), stale_names_hi=lst("stale_names_hi"),
                    portfolio=lst("portfolio"), rank=str(f.get("rank") or ""))
        fact.rx = _phrase_rx(fact.match)
        fact.rx_hi = _phrase_rx(fact.match_hi, hindi=True)
        out.append(fact)
    return out


# --------------------------------------------------------------------------- #
# Organisation facts (founded year / headquarters / ministry)
# --------------------------------------------------------------------------- #
@dataclass
class OrgFact:
    id: str
    name: str
    match: List[str]
    founded: List[int]
    hq: List[str]
    hq_hi: str
    ministry: List[str]          # accepted ministry / department phrases
    ministry_name: str
    ministry_hi: str
    rx: Optional[re.Pattern] = None
    members: List[str] = field(default_factory=list)      # verified member countries (groupings)
    members_hi: str = ""
    secretariat: List[str] = field(default_factory=list)  # verified secretariat seat(s)
    secretariat_hi: str = ""
    no_secretariat: bool = False                          # e.g. BRICS, G20: no permanent secretariat
    no_hq: bool = False                                   # no headquarters at all (BRICS, G20)


def load_orgs(path: Optional[Path] = None) -> List[OrgFact]:
    """Verified organisation facts ('orgs' in current_facts.json). [] when absent."""
    try:
        data = _facts_doc(path)
    except Exception:
        return []
    out: List[OrgFact] = []
    for o in data.get("orgs") or []:
        if not isinstance(o, dict) or not o.get("match"):
            continue
        org = OrgFact(id=str(o.get("id")), name=str(o.get("name") or ""), match=[str(x) for x in o["match"]],
                      founded=[int(x) for x in o.get("founded") or []], hq=[str(x) for x in o.get("hq") or []],
                      hq_hi=str(o.get("hq_hi") or ""), ministry=[str(x) for x in o.get("ministry") or []],
                      ministry_name=str(o.get("ministry_name") or ""), ministry_hi=str(o.get("ministry_hi") or ""),
                      members=[str(x) for x in o.get("members") or []], members_hi=str(o.get("members_hi") or ""),
                      secretariat=[str(x) for x in o.get("secretariat") or []],
                      secretariat_hi=str(o.get("secretariat_hi") or ""),
                      no_secretariat=bool(o.get("no_secretariat")), no_hq=bool(o.get("no_hq")))
        org.rx = re.compile(r"(?<![A-Za-z])(?:" + "|".join(
            re.escape(m).replace(r"\ ", r"\s+") for m in sorted(org.match, key=len, reverse=True)) + r")(?![A-Za-z])")
        out.append(org)
    return out


FOUNDED_RE = re.compile(r"\b(?:establish(?:ed|ment)?|founded|foundation|set\s+up|incorporat(?:ed|ion)|formed|"
                        r"inception|constituted|year\s+of\s+(?:establishment|incorporation))\b|स्थापना|गठन", re.I)
HQ_RE = re.compile(r"\b(?:headquarter(?:s|ed)?|HQ|head\s+office|registered\s+office|based\s+(?:in|at))\b|मुख्यालय", re.I)
MINISTRY_FIELD_RE = re.compile(r"\b(?:(?:parent|nodal|administrative|controlling)\s+(?:ministry|department)|"
                               r"under\s+the\s+(?:administrative\s+control\s+of\s+(?:the\s+)?)?(?:ministry|department)|"
                               r"(?:ministry|department)\s*$)", re.I)
FILLER_MINISTRY_RE = re.compile(r"\b(?:parent|nodal|administrative)\s+ministry\b\s*[–:\-]*\s*"
                                r"(?:the\s+)?(?:government\s+of\s+india|union\s+government|central\s+government|"
                                r"goi|n/?a|none|not\s+applicable)\s*\.?$", re.I)


SECRETARIAT_RE = re.compile(r"\bsecretariat\b|सचिवालय", re.I)
MEMBERS_RE = re.compile(r"\bmembers?(?:\s+(?:countries|states|nations))?\b|\bmembership\b|सदस्य", re.I)
# Country names for member lists (members of the tracked groupings + common extras).
_COUNTRY_ALIASES = {
    "brazil": "Brazil", "russia": "Russia", "russian federation": "Russia", "india": "India", "china": "China",
    "south africa": "South Africa", "egypt": "Egypt", "ethiopia": "Ethiopia", "iran": "Iran",
    "uae": "United Arab Emirates", "united arab emirates": "United Arab Emirates", "indonesia": "Indonesia",
    "saudi arabia": "Saudi Arabia", "argentina": "Argentina", "kazakhstan": "Kazakhstan",
    "kyrgyzstan": "Kyrgyzstan", "kyrgyz republic": "Kyrgyzstan", "tajikistan": "Tajikistan",
    "uzbekistan": "Uzbekistan", "pakistan": "Pakistan", "belarus": "Belarus", "brunei": "Brunei Darussalam",
    "brunei darussalam": "Brunei Darussalam", "cambodia": "Cambodia", "laos": "Lao PDR", "lao pdr": "Lao PDR",
    "malaysia": "Malaysia", "myanmar": "Myanmar", "philippines": "Philippines", "singapore": "Singapore",
    "thailand": "Thailand", "vietnam": "Viet Nam", "viet nam": "Viet Nam", "timor-leste": "Timor-Leste",
    "east timor": "Timor-Leste", "turkey": "Turkey", "türkiye": "Turkey", "mongolia": "Mongolia",
    "afghanistan": "Afghanistan", "nepal": "Nepal", "sri lanka": "Sri Lanka", "bangladesh": "Bangladesh",
    "japan": "Japan", "usa": "United States", "united states": "United States",
}
_COUNTRY_RE = re.compile(r"(?<![A-Za-z])(" + "|".join(re.escape(k) for k in sorted(_COUNTRY_ALIASES, key=len,
                                                                                    reverse=True)) + r")(?![A-Za-z])",
                         re.I)


def _countries(text: str) -> set:
    return {_COUNTRY_ALIASES[m.group(1).lower()] for m in _COUNTRY_RE.finditer(text or "")}


def _members_org(countries: set, orgs: Sequence[OrgFact]) -> Optional[OrgFact]:
    """The grouping a bare member list is about (>= 3 of its members named)."""
    best = None
    for o in orgs:
        if o.members:
            n = len(countries & set(o.members))
            if n >= 3 and (best is None or n > best[0]):
                best = (n, o)
    return best[1] if best else None


def _check_grouping(org: OrgFact, head: str, body: str, value: str) -> Optional[Tuple[str, str, str, str]]:
    """Members / secretariat / headquarters of a grouping (BRICS has 10 members, no secretariat)."""
    if SECRETARIAT_RE.search(head) and (org.no_secretariat or org.secretariat):
        if org.no_secretariat:
            return "drop", "secretariat", "", ""
        if not any(re.search(rf"(?<![A-Za-z]){re.escape(x)}(?![A-Za-z])", body, re.I) for x in org.secretariat):
            if value and len(value.split()) <= 4:
                return "replace", "secretariat", org.secretariat[0], org.secretariat_hi
            return "drop", "secretariat", "", ""
        return "keep", "secretariat", "", ""
    if HQ_RE.search(head) and org.no_hq:
        return "drop", "hq", "", ""
    if MEMBERS_RE.search(head) and org.members:
        listed = _countries(body)
        nums = [int(x) for x in re.findall(r"(?<![\d.])(\d{1,2})(?![\d.])", body)]
        if len(listed) >= 2:
            ok = listed == set(org.members)
        elif nums:
            ok = len(org.members) in nums
        else:
            return "keep", "members", "", ""
        if ok:
            return "keep", "members", "", ""
        if value and (len(listed) >= 2 or len(value.split()) <= 4):
            return "replace", "members", ", ".join(org.members), org.members_hi
        return "drop", "members", "", ""
    return None


def _org_in(text: str, orgs: Sequence[OrgFact]) -> List[OrgFact]:
    return [o for o in orgs if o.rx and o.rx.search(text or "")]


def check_org_line(label: str, value: str, orgs: Sequence[OrgFact], context: Optional[OrgFact] = None
                   ) -> Tuple[str, str, str, str]:
    """Founded/HQ/ministry check for one line about a tracked organisation.

    Returns (action, field, new_value_en, new_value_hi): action keep | replace | drop.
    ``label``/``value`` are the row parts (a plain sentence goes in ``label`` with value '').
    A line naming two tracked organisations is not judged (keep)."""
    line = f"{label} – {value}" if value else label
    if FILLER_MINISTRY_RE.search(line):
        return "drop", "ministry", "", ""
    hits = _org_in(line, orgs)
    if len(hits) > 1:
        return "keep", "", "", ""
    org = hits[0] if hits else context
    head = label if value else line
    body = value if value else line
    if org is None and MEMBERS_RE.search(head):
        org = _members_org(_countries(body), orgs)
    if org is None:
        return "keep", "", "", ""
    grouping = _check_grouping(org, head, body, value)
    if grouping is not None:
        return grouping
    if FOUNDED_RE.search(head) and org.founded:
        ys = _years(body)
        if ys and not any(y in org.founded for y in ys):
            if value and re.fullmatch(r"\s*(?:in\s+)?(?:19|20)\d{2}\s*\.?\s*", value):
                return "replace", "founded", str(org.founded[0]), str(org.founded[0])
            return "drop", "founded", "", ""
        return "keep", "founded", "", ""
    if HQ_RE.search(head) and org.hq:
        if not any(re.search(rf"(?<![A-Za-z]){re.escape(h)}(?![A-Za-z])", body, re.I) for h in org.hq):
            if value and len(value.split()) <= 4:
                return "replace", "hq", org.hq[0], org.hq_hi
            return "drop", "hq", "", ""
        return "keep", "hq", "", ""
    if (MINISTRY_FIELD_RE.search(head) or (value and re.search(r"\bministry\b", label, re.I))) and org.ministry:
        if re.search(r"\bministry|department\b", body, re.I) and not any(
                re.search(re.escape(m), body, re.I) for m in org.ministry):
            if value and org.ministry_name:
                return "replace", "ministry", org.ministry_name, org.ministry_hi
            return "drop", "ministry", "", ""
        return "keep", "ministry", "", ""
    return "keep", "", "", ""


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


_YEAR_LABEL_RE = re.compile(r"\s*\((?:as\s+of\s+|in\s+)?((?:19|20)\d{2})\)")
_PORTFOLIO_RE = re.compile(r"\bMinister\s+(?:of\s+State\s+)?(?:\(\s*Independent\s+Charge\s*\)\s+)?(?:of|for)\s+(?:the\s+)?"
                           r"(.+?)(?=\s*(?:[–—:;.(]|\s-\s|$))", re.I)
_RUN: Dict[str, int] = {"officeholder_lines": 0, "lookup_candidates": 0}
_ACTIVE_ORGS: List[OrgFact] = []


def strip_year_label(text: str, year: Optional[int] = None) -> str:
    """'Chief Justice of India (2024)' -> 'Chief Justice of India' (a past year labels old data)."""
    year = year or current_year()
    return _YEAR_LABEL_RE.sub(lambda m: "" if int(m.group(1)) < year else m.group(0), text or "")


def _name_rx(names: Sequence[str]) -> Optional[re.Pattern]:
    alts = []
    for n in sorted({n for n in names if n}, key=len, reverse=True):
        toks = [re.escape(t.strip(".")) for t in re.split(r"[\s.]+", _TITLE_STRIP_RE.sub("", n)) if t.strip(".")]
        if toks:
            alts.append(r"[\s.]*".join(toks))
    if not alts:
        return None
    return re.compile(_TITLE_RE + r"(?:" + "|".join(alts) + r")\.?(?![A-Za-z])", re.I)


def _stale_holder(en: str, hi: str, facts: Sequence[Fact], year: Optional[int]) -> Optional[Verdict]:
    """A known earlier/hallucinated holder named in EN or HI (e.g. 'RBI Governor – Shaktikanta Das')."""
    for f in facts:
        if not (f.stale_names or f.stale_names_hi) or f.multi:
            continue
        en_hit = bool(f.stale_names) and _contains_name(en, f.stale_names)
        hi_hit = next((n for n in f.stale_names_hi if n and n in hi), "")
        if not (en_hit or hi_hit):
            continue
        post = bool((f.rx and f.rx.search(en)) or (f.rx_hi and f.rx_hi.search(hi)))
        if not post:
            if is_officeholder_line(en, hi) or CURRENT_RE.search(en) or CURRENT_HI_RE.search(hi):
                return Verdict("drop", reason=f"former holder of {f.id} named without the post", fact_id=f.id)
            continue
        new_en = en
        if en_hit:
            rx = _name_rx(f.stale_names)
            if rx is None or not rx.search(en):
                return Verdict("drop", reason=f"former holder of {f.id} (could not rewrite)", fact_id=f.id)
            m = rx.search(en)
            wrong = m.group(0).strip()
            new_en = strip_year_label(rx.sub(f.name, en), year)
        else:
            wrong = hi_hit
        if not en:
            return Verdict("drop", reason=f"former holder of {f.id} in a Hindi-only line", fact_id=f.id)
        # Hindi stays fail-closed: kept only when it already carries the verified Hindi name.
        new_hi = strip_year_label(hi, year) if (hi and not hi_hit and f.name_hi and f.name_hi in hi) else ""
        return Verdict("replace", en=new_en, hi=new_hi, reason=f"former holder for {f.id}", fact_id=f.id,
                       wrong=wrong)
    return None


def _wrong_portfolio(en: str, facts: Sequence[Fact]) -> Optional[Verdict]:
    """A tracked minister named with a ministry or rank they do not hold."""
    if not re.search(r"\bMinister\b", en):
        return None
    for f in facts:
        if not f.portfolio or not _contains_name(en, f.valid_names()):
            continue
        if f.rank == "cabinet" and re.search(r"\bMinister\s+of\s+State\b|\bMoS\b", en):
            return Verdict("drop", reason=f"wrong rank for {f.name}", fact_id=f.id)
        port = [_norm(p) for p in f.portfolio]
        for m in _PORTFOLIO_RE.finditer(en):
            claimed = re.sub(r"^(?:the\s+)?(?:Ministry|Department)\s+of\s+", "", m.group(1).strip(), flags=re.I)
            subjects = [x for x in (_norm(t) for t in re.split(r",|\band\b|&", claimed)) if x]
            for subj in subjects:
                if not any(subj in p or p in subj for p in port):
                    return Verdict("drop", reason=f"wrong portfolio for {f.name}: {subj}", fact_id=f.id)
    return None


def check_line(en: str, hi: str, facts: Sequence[Fact], *, story_text: str = "",
               year: Optional[int] = None, lookup: Any = None, orgs: Optional[Sequence[OrgFact]] = None,
               org_ctx: Optional[OrgFact] = None) -> Verdict:
    """Decide keep / replace / drop for one bilingual Static GK line. May raise (callers fail open)."""
    en = str(en or "")
    hi = str(hi or "")
    if is_stale_latest(en, hi, year):
        return Verdict("drop", reason="stale year presented as current/latest")
    orgs = _ACTIVE_ORGS if orgs is None else orgs
    if orgs and en and " – " in en and MEMBERS_RE.search(en.split(" – ", 1)[0]):
        le, ve = en.split(" – ", 1)
        act, fld, nv, nh = check_org_line(le, ve, orgs, org_ctx)
        if act == "replace" and fld == "members":
            lh = hi.split(" – ", 1)[0] if " – " in hi else ""
            return Verdict("replace", en=f"{le} – {nv}", hi=f"{lh} – {nh}" if lh and nh else "",
                           reason="wrong member list for grouping", wrong=ve)
    if orgs and en:
        act, fld, _nv, _nh = check_org_line(en, "", orgs, org_ctx)
        if act != "keep":
            return Verdict("drop", reason=f"wrong {fld} for organisation" if fld != "ministry" or org_ctx
                           or _org_in(en, orgs) else "meaningless parent ministry")
    if HISTORICAL_RE.search(en) or (not en and HISTORICAL_HI_RE.search(hi)):
        return Verdict("keep", en=en, hi=hi, reason="historical fact")
    if is_officeholder_line(en, hi):
        _RUN["officeholder_lines"] += 1
    v = _stale_holder(en, hi, facts, year)
    if v is not None:
        return v
    v = _wrong_portfolio(en, facts)
    if v is not None:
        return v
    if not en and hi:
        for f in facts:
            mh = f.rx_hi.search(hi) if f.rx_hi else None
            if mh and not _foreign_context(hi, mh.start(), mh.end()):
                if f.name_hi and f.name_hi in hi:
                    return Verdict("keep", en=en, hi=hi)
                if re.search(r"[–:\-]\s*\S", hi[mh.end():]):
                    return Verdict("drop", reason=f"Hindi-only {f.id} line without the verified name", fact_id=f.id)
    hits = _post_hits(en, facts)
    if hits:
        label_en, label_hi = strip_year_label(en, year), strip_year_label(hi, year)
        if label_en != en or label_hi != hi:
            v = check_line(label_en, label_hi, facts, story_text=story_text, year=year, lookup=lookup,
                           orgs=orgs, org_ctx=org_ctx)
            if v.action == "keep":
                return Verdict("replace", en=label_en, hi=label_hi, reason="past year label removed",
                               fact_id=hits[0][0].id)
            return v
        mask = [(s, e) for _f, s, e in hits]
        cands = name_candidates(en, mask)
        new_en, new_hi = en, hi
        replaced_any = False
        for f, _s, _e in hits:
            if f.blocked:
                if cands or _contains_name(en, f.valid_names()):
                    return Verdict("drop", reason=f"unverified change of {f.id} reported today", fact_id=f.id)
                continue
            if _contains_name(en, f.valid_names()):
                continue
            wrong = [c for c in cands if not _contains_name(c[0], f.valid_names())]
            if not wrong:
                continue  # post mentioned without any person name ("RBI Governor chairs the MPC")
            w = wrong[0][0]
            if f.multi:
                return Verdict("drop", reason=f"unverified holder for multi-holder post {f.id}", fact_id=f.id, wrong=w)
            if (not f.override and story_text and _story_has(w, story_text)
                    and APPOINTMENT_RE.search(story_text)):
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
    _RUN["lookup_candidates"] += 1
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
              year: Optional[int] = None, org_ctx: Optional[OrgFact] = None) -> Tuple[str, Dict[str, Any], Verdict]:
    """MCQ schema row {label_en, value_en, label_hi, value_hi}. Returns (action, new_row, verdict)."""
    le, ve = str(row.get("label_en") or ""), str(row.get("value_en") or "")
    lh, vh = str(row.get("label_hi") or ""), str(row.get("value_hi") or "")
    en = f"{le} – {ve}" if le and ve else (le or ve)
    hi = f"{lh} – {vh}" if lh and vh else (lh or vh)
    if _ACTIVE_ORGS and not is_stale_latest(en, hi, year):
        act, fld, nv, nh = check_org_line(le, ve, _ACTIVE_ORGS, org_ctx)
        if act == "drop":
            return "drop", dict(row), Verdict("drop", reason=f"wrong or meaningless {fld} (organisation fact)")
        if act == "replace":
            new = dict(row)
            new["value_en"], new["value_hi"] = nv, nh
            return "replace", new, Verdict("replace", en=f"{le} – {nv}", hi=f"{lh} – {nh}" if nh else "",
                                           reason=f"wrong {fld} for organisation", wrong=ve, new_name=nv)
    v = check_line(en, hi, facts, story_text=story_text, year=year, orgs=[])
    if v.action != "replace":
        return v.action, dict(row), v
    new = dict(row)
    if v.reason == "past year label removed":
        for k in ("label_en", "value_en", "label_hi", "value_hi"):
            if isinstance(new.get(k), str):
                new[k] = strip_year_label(new[k], year)
        return "replace", new, v
    new["label_en"], new["label_hi"] = strip_year_label(le, year), strip_year_label(lh, year)
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
# Freshness: verified overrides + today's appointment trigger
# --------------------------------------------------------------------------- #
OVERRIDE_DAYS = 30
APPT_SIGNAL_RE = re.compile(
    r"\b(?:appoint(?:ed|s)|takes?\s+(?:over|charge)|took\s+(?:over|charge)|taking\s+charge|sworn\s+in|"
    r"named\s+(?:as|the)|assume[sd]?\s+(?:office|charge)|assuming\s+(?:office|charge)|succeed(?:s|ed|ing)?|"
    r"in\s+place\s+of|replac(?:es|ed|ing))\b", re.I)
APPT_SIGNAL_HI_RE = re.compile(r"नियुक्त|कार्यभार|शपथ")
SUCCESSION_RE = re.compile(r"\b(?:succeed(?:s|ed|ing)?|in\s+place\s+of|replac(?:es|ed|ing))\b", re.I)
_NEW_BEFORE_RE = re.compile(r"\bnew(?:ly\s+appointed)?\s+(?:\S+\s+){0,2}$", re.I)
_SENT_SPLIT_RE = re.compile(r"(?<=[.!?।])\s+|\n+")


def _today() -> "datetime.date":
    d = os.getenv("ALP_JOB_DATE", "")
    try:
        return datetime.strptime(d[:10], "%Y-%m-%d").date()
    except ValueError:
        return datetime.now(timezone.utc).date()


def _as_override(f: Fact, name: str) -> Fact:
    """Copy of *f* whose holder is *name* (no Hindi name/aliases: those are unverified)."""
    return Fact(id=f.id, post=f.post, name=name, names=[], aliases=[], name_hi="", match=f.match,
                match_hi=f.match_hi, rx=f.rx, rx_hi=f.rx_hi, override=True)


def _cache_path() -> Path:
    from agents.static_gk_ai_lookup import CACHE_PATH
    return Path(os.getenv("ALP_AI_FACTS_CACHE", "") or CACHE_PATH)


def apply_overrides(facts: Sequence[Fact], cache_doc: Optional[Dict[str, Any]] = None,
                    today: Optional[Any] = None) -> List[Fact]:
    """Facts with verified override records applied. An override holds for OVERRIDE_DAYS from
    verification, and only while current_facts still has the name it replaced. Never raises."""
    out = list(facts)
    try:
        if cache_doc is None:
            from agents.static_gk_ai_lookup import load_cache
            cache_doc = load_cache(_cache_path())
        today = today or _today()
        idx = {f.id: i for i, f in enumerate(out)}
        for rec in (cache_doc.get("records") or {}).values():
            if not isinstance(rec, dict) or not rec.get("overrides_current_facts"):
                continue
            i = idx.get(str(rec.get("fact_id") or ""))
            name = str(rec.get("name") or "")
            if i is None or not name or out[i].multi:
                continue
            try:
                age = (today - datetime.strptime(str(rec.get("verified_on"))[:10], "%Y-%m-%d").date()).days
            except ValueError:
                continue
            if not 0 <= age <= OVERRIDE_DAYS:
                continue
            f = out[i]
            if _norm(f.name) == _norm(name) or _norm(f.name) != _norm(str(rec.get("previous_name") or "")):
                continue  # current_facts already updated (or changed since): override is obsolete
            out[i] = _as_override(f, name)
    except Exception as exc:  # fail open: plain current_facts
        logger.info("[static-gk] overrides not applied: %s", exc)
        return list(facts)
    return out


def _edition_texts(content: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for it in content.get("items") or []:
        if not isinstance(it, dict):
            continue
        for k in ("headline_en", "title", "headline_hi", "title_hi", "summary_en", "summary_hi",
                  "detailed_explanation_en", "detailed_explanation_hi", "body", "content"):
            v = it.get(k)
            if isinstance(v, str) and v:
                out.append(v)
        for k in ("key_points_en", "key_points_hi"):
            v = it.get(k)
            if isinstance(v, list):
                out.extend(str(x) for x in v if x)
    return out


def detect_appointments(texts: Sequence[str], facts: Sequence[Fact]) -> Dict[str, List[str]]:
    """Tracked posts that today's stories report as changing hands: {fact_id: [new names]}.

    A sentence counts when it names a tracked post and carries an appointment signal
    (appointed, takes charge, sworn in, named as, new <post>, assumes office; Hindi नियुक्त,
    कार्यभार, शपथ). A sentence that names the current holder counts only with a succession
    word (succeeds / replaces / in place of), so "Governor X appointed Y as ED" is ignored.
    Names are person names near the post that are not the current holder ([] = none given)."""
    found: Dict[str, List[str]] = {}
    for text in texts:
        for sent in _SENT_SPLIT_RE.split(str(text or "")):
            if not sent or len(sent) < 12:
                continue
            for f in facts:
                if f.multi:
                    continue
                m = f.rx.search(sent) if f.rx else None
                if m and not _foreign_context(sent, m.start(), m.end()):
                    sig = APPT_SIGNAL_RE.search(sent) or _NEW_BEFORE_RE.search(sent[:m.start()])
                    if not sig:
                        continue
                    if _contains_name(sent, f.valid_names()) and not SUCCESSION_RE.search(sent):
                        continue
                    names = [c[0] for c in name_candidates(sent, [(m.start(), m.end())])
                             if not _contains_name(c[0], f.valid_names())
                             and min(abs(c[1] - m.end()), abs(m.start() - c[2])) <= 80]
                    lst = found.setdefault(f.id, [])
                    lst.extend(n for n in names if n not in lst)
                    continue
                mh = f.rx_hi.search(sent) if f.rx_hi else None
                if mh and APPT_SIGNAL_HI_RE.search(sent) and not (f.name_hi and f.name_hi in sent):
                    found.setdefault(f.id, [])
    return found


def _call_lookup(lookup: Any, post: str, expect: Sequence[str]) -> Any:
    try:
        return lookup(post, expect=list(expect), fresh=True)
    except TypeError:
        return lookup(post)


def _save_override(f: Fact, res: Any, today: Any) -> None:
    try:
        from agents.static_gk_ai_lookup import load_cache, save_cache
        path = _cache_path()
        doc = load_cache(path)
        doc.setdefault("records", {})[f"override:{f.id}"] = {
            "post": f.post, "fact_id": f.id, "name": res.name, "previous_name": f.name,
            "since": getattr(res, "since", None), "source_url": getattr(res, "source_url", ""),
            "second_source": getattr(res, "second_source", ""), "verified_on": today.isoformat(),
            "overrides_current_facts": True, "method": "appointment-trigger+serper+official-page+llm"}
        doc["updated"] = today.isoformat()
        save_cache(doc, path)
    except Exception as exc:
        logger.info("[static-gk] override not cached: %s", exc)


def resolve_appointments(facts: Sequence[Fact], appts: Dict[str, List[str]], lookup: Any,
                         today: Optional[Any] = None) -> Tuple[List[Fact], List[Dict[str, str]]]:
    """Apply today's appointment signals. For each signalled post the strict AI lookup decides:
    confirmed new holder -> override fact (cached for later days); story named nobody and the
    lookup confirms the current holder -> unchanged; anything else -> post blocked (lines dropped)."""
    today = today or _today()
    out = list(facts)
    log: List[Dict[str, str]] = []
    for i, f in enumerate(out):
        if f.id not in appts:
            continue
        names = appts[f.id]
        res = None
        if lookup is not None:
            try:
                res = _call_lookup(lookup, f.post, names)
            except Exception as exc:
                logger.info("[static-gk] appointment lookup failed for %s: %s", f.id, exc)
        got = str(getattr(res, "name", "") or "") if res else ""
        if got and names and any(_contains_name(got, [n]) or _contains_name(n, [got]) for n in names):
            outcome = "confirmed"
        elif got and not names and not _contains_name(got, f.valid_names()):
            outcome = "confirmed"
        elif got and not names and _contains_name(got, f.valid_names()):
            outcome = "unchanged"
        else:
            outcome = "blocked"
        if outcome == "confirmed":
            if not _contains_name(got, f.valid_names()):
                _save_override(f, res, today)
                out[i] = _as_override(f, got)
        elif outcome == "blocked":
            nf = Fact(**{k: getattr(f, k) for k in f.__dataclass_fields__})
            nf.blocked = True
            out[i] = nf
        log.append({"fact_id": f.id, "story_names": ", ".join(names), "lookup": got, "outcome": outcome})
        logger.info("[static-gk] appointment signal for %s (story: %s) -> %s %s", f.id, names or "-", outcome, got)
    return out, log


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
    ctx: Optional[OrgFact] = None
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
        here = _org_in(en, _ACTIVE_ORGS) if _ACTIVE_ORGS else []
        ctx = here[0] if len(here) == 1 else (None if here else ctx)
        v = _safe_line(lambda: check_line(en, hi, facts, story_text=story_text, year=year, org_ctx=ctx),
                       en, hi, report)
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
    ctx: Optional[OrgFact] = None
    for r in rows:
        if not isinstance(r, dict) or not ("label_en" in r or "value_en" in r):
            if isinstance(r, dict) and ("en" in r or "hi" in r):
                out.extend(validate_pairs([r], facts, report, story_text, year))
            else:
                out.append(r)
            continue
        en = f"{r.get('label_en', '')} – {r.get('value_en', '')}"
        here = _org_in(en, _ACTIVE_ORGS) if _ACTIVE_ORGS else []
        ctx = here[0] if len(here) == 1 else (None if here else ctx)
        res = _safe_line(lambda: check_row(r, facts, story_text=story_text, year=year, org_ctx=ctx), en,
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
        _LOOKUP_ERR[0] = f"{type(exc).__name__}: {exc}"[:120]
        logger.info("[static-gk] AI lookup unavailable: %s", exc)
        return None


def validate_edition(content: Dict[str, Any], mcq_data: Any = None,
                     facts: Optional[Sequence[Fact]] = None, lookup: Any = "auto",
                     cache_doc: Optional[Dict[str, Any]] = None,
                     orgs: Optional[Sequence[OrgFact]] = None) -> Dict[str, Any]:
    """Validate every Static GK line of an edition in place. Never raises; returns a report dict.

    ``lookup``: "auto" builds the AI lookup for untracked posts (a no-op without
    SERPER_API_KEY / an LLM provider / network, and under pytest); None disables it."""
    global _ACTIVE_LOOKUP, _ACTIVE_ORGS
    _LOOKUP_ERR[0] = ""
    _ACTIVE_LOOKUP = make_lookup() if lookup == "auto" else lookup
    try:
        _ACTIVE_ORGS = load_orgs() if orgs is None else list(orgs)
    except Exception:
        _ACTIVE_ORGS = []
    _RUN.update(officeholder_lines=0, lookup_candidates=0)
    try:
        out = _validate_edition(content, mcq_data, facts, cache_doc)
        _explain_lookup(out, lookup)
        return out
    finally:
        _ACTIVE_LOOKUP = None
        _ACTIVE_ORGS = []


_LOOKUP_ERR = [""]


def _explain_lookup(out: Dict[str, Any], requested: Any) -> None:
    """Always say why the AI lookup made no calls (it is lazy: only an untracked post with an
    unverifiable holder name triggers it)."""
    ai = out.setdefault("ai_lookup", {})
    ai["officeholder_lines"] = _RUN["officeholder_lines"]
    ai["lookup_candidates"] = _RUN["lookup_candidates"]
    lk = _ACTIVE_LOOKUP
    if lk is None:
        ai.setdefault("lookups", 0)
        ai["off_reason"] = ("disabled by caller" if requested is None
                            else f"unavailable: {_LOOKUP_ERR[0] or 'not constructed'}")
    elif not ai.get("lookups") and not ai.get("cache_hits") and not ai.get("off_reason"):
        ready, why = (True, "")
        try:
            ready, why = lk.status() if hasattr(lk, "status") else (True, "")
        except Exception as exc:
            ready, why = False, f"status error: {type(exc).__name__}"
        if not ready:
            ai["off_reason"] = why
        elif not _RUN["lookup_candidates"]:
            ai["off_reason"] = (f"idle: none of {_RUN['officeholder_lines']} officeholder line(s) needed a lookup "
                                "(tracked posts checked against current_facts; other names verified by the story)")
        else:
            ai["off_reason"] = "idle: candidate lines had no searchable post"
    if ai.get("off_reason"):
        logger.info("[static-gk] AI lookup: %s", ai["off_reason"])


def _validate_edition(content: Dict[str, Any], mcq_data: Any = None,
                      facts: Optional[Sequence[Fact]] = None,
                      cache_doc: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    report = Report()
    year = current_year()
    try:
        if facts is None:
            facts = load_facts()
    except Exception as exc:
        logger.warning("[static-gk] current_facts unavailable (%s): dropping officeholder-type lines", exc)
        return drop_officeholder_lines(content, mcq_data, reason=f"facts unavailable: {exc}")
    appt_log: List[Dict[str, str]] = []
    overridden: List[str] = []
    try:
        facts = apply_overrides(facts, cache_doc)
        overridden = [f.id for f in facts if f.override]
        appts = detect_appointments(_edition_texts(content), facts)
        if appts:
            facts, appt_log = resolve_appointments(facts, appts, _ACTIVE_LOOKUP)
    except Exception as exc:  # fail open: block every signalled post is not possible here; plain facts
        logger.warning("[static-gk] freshness step failed (%s); using current_facts", exc)
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
    if overridden:
        out["overrides"] = overridden
    if appt_log:
        out["appointments"] = appt_log
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
        facts = facts if facts is not None else apply_overrides(load_facts())
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
