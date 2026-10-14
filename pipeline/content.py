# -*- coding: utf-8 -*-
"""
CONTENT EDITOR + BILINGUAL + MCQ LIBRARY (Agents 12-14, 16)

Rule "Never invent facts": every key point / static fact / MCQ answer must be a
substring-extractable fact from the item's own headline + raw_facts. Extraction is
deterministic, so there is zero hallucination. If an optional AI provider is
configured (OPENAI_API_KEY), it is used ONLY to polish wording, and the polished
text is re-checked against the source (numbers + capitalised names must survive).

v4 (production audit) - what changed vs v3
------------------------------------------
Crashes / correctness
- NUM_RE: "5%" was never matched (\\b after '%'); "1,200 crore" was captured as
  "200 crore"; "Farmers 500" matched as "rs 500". All fixed.
- split_sentences(): "Rs. 500 crore" was cut after "Rs." - abbreviations protected.
- build_content(): no more KeyError on missing headline_en / event_id; one bad item
  can no longer kill the whole edition (per-item try/except).
- validate_mcqs(): numeric options such as "Rs 100 crore" vs "Rs 200 crore" were
  rejected as "too similar" - similarity is now checked for text options only.
- MINI_DICT: "Employment" had a double nukta; "New Delhi" became "naya Delhi".

MCQ quality
- English questions no longer contain Hindi text (and vice-versa).
- Rank questions used organisation names as distractors - now ordinal numbers.
- Number questions only use numeric distractors of the same kind (money/percent/..).
- Organisation answers are real organisation names, not 70-char sentence fragments.
- Round-robin generation actually reaches the (min, max) target.
- Distractors that also appear in the source text (= second correct answer) are blocked.

Translation
- AI translator is PRIMARY. Deterministic dictionary is a clearly-flagged fallback
  (item["needs_review"] = True). Set ALP_TRANSLATION_STRICT=1 to disable the
  fallback completely (fail-closed).
- translator import is cached (no log spam), identical strings are cached.

Env switches (all optional)
  OPENAI_API_KEY / ALP_LLM        -> enables AI polishing of English wording
  ALP_DISABLE_POLISH=1            -> never call the polish API
  ALP_TRANSLATION_STRICT=1        -> no deterministic Hindi fallback
  ALP_MEMORY_PATH=<file.json>     -> override importance-memory location
"""
import hashlib
import json
import logging
import os
import re
from difflib import SequenceMatcher
from pathlib import Path

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #
HEADLINE_PREFIX = ">> "
MIN_OPTIONS = 4              # standard exam MCQ = 4 options (A-D); 5 allowed
MAX_OPTIONS = 5
SIMILARITY_LIMIT = 0.85      # text options more similar than this are rejected
MEMORY_DEFAULT_PATH = "state/importance_memory.json"

# Kept only for backward compatibility with older imports (mixed-language, unused).
MCQ_TPL_NUMBER = ("\u0907\u0938 \u0918\u091f\u0928\u093e \u0938\u0947 \u091c\u0941\u0921\u093c\u0940 "
                  "\u0930\u093e\u0936\u093f/\u0938\u0902\u0916\u094d\u092f\u093e \u0915\u094c\u0928-\u0938\u0940 "
                  "\u0939\u0948? Which figure/number is associated with this event?")

# ---- number / entity regexes ------------------------------------------------
_NUM = r"(?:\d{1,3}(?:,\d{2,3})+|\d+)(?:\.\d+)?"
_NUM_RE = re.compile(_NUM)
_CURRENCY = r"(?:\b(?:Rs\.?|INR|USD)|\u20b9|US\$|\$)"
_MONEY_UNITS = r"(?:crore|lakh|billion|million|trillion|thousand|Cr|bn|mn)"
_OTHER_UNITS = (r"(?:percent|per cent|bps|days?|years?|months?|weeks?|tonnes?|hectares?|"
                r"bn|billion|million|trillion|crore|lakh)")
NUM_RE = re.compile(
    "(?:" + _CURRENCY + r"\s?" + _NUM + r"(?:\s?" + _MONEY_UNITS + r"\b)?)"
    + "|"
    + "(?:" + r"\b" + _NUM + r"\s?(?:%|" + _OTHER_UNITS + r"\b))",
    re.I,
)

CAP_RE = re.compile(r"\b[A-Z][A-Za-z&]+(?:[ -][A-Z][A-Za-z&]+)+\b")
ACRONYM_RE = re.compile(r"\b[A-Z]{2,8}\b")
_ORG_WORDS = (r"(?:Ministry|Department|Commission|Authority|Council|Board|Corporation|"
              r"Committee|Mission|Bank|Organisation|Organization)")
ORG_RE = re.compile(
    r"\b(?:"
    + _ORG_WORDS + r"\s+of\s+(?:the\s+)?[A-Z][A-Za-z&]+(?:\s+(?:(?:and|of|&)\s+)?[A-Z][A-Za-z&]+){0,3}"
    + r"|(?:[A-Z][A-Za-z&]+\s+){1,3}(?:" + _ORG_WORDS[3:-1] + r"|Institute|Aayog|Parliament)"
    + r"(?:\s+of\s+[A-Z][A-Za-z&]+)?"
    + r")\b"
)
RANK_RE = re.compile(
    r"\b(\d+(?:st|nd|rd|th))\s+(?:position|rank|place|spot)\b|\branked\s+(\d+(?:st|nd|rd|th))\b",
    re.I,
)

_ABBREV_RE = re.compile(r"\b(Rs|Dr|Mr|Mrs|Ms|Prof|Shri|Smt|Ltd|Pvt|Gen|Lt|Col|Capt)\.")
_INITIALS_RE = re.compile(r"\b(?:[A-Z]\.){2,}")

LEADING_STOP = {"the", "a", "an", "in", "on", "at", "of", "for", "to", "by", "with", "from", "as",
                "and", "&", "after", "over", "amid", "under"}
ACTION_WORDS = {
    "launches", "launched", "approves", "approved", "announces", "announced", "signs", "signed",
    "wins", "won", "releases", "released", "unveils", "unveiled", "hikes", "cuts", "issues",
    "extends", "begins", "starts", "opens", "inaugurates", "inaugurated", "notifies", "reports",
    "says", "becomes", "gets", "gives", "plans", "sets", "launch", "approval", "gains", "rises",
    "falls", "declares", "declared", "clears", "cleared", "allows", "allowed", "bans", "banned",
    "to", "for", "with", "in", "on", "at", "by", "as", "from", "amid", "over",
}
TRAILING_DROP = {"asian", "african", "european", "american", "chinese", "indian"}
ACRONYM_STOP = {"IST", "THE", "AND", "FOR", "NEW", "ALL", "OF", "TO", "IN", "ON", "AT", "BY"}

DOMAIN_ORGS = ["NABARD", "Reserve Bank of India", "ICAR", "Food Corporation of India",
               "SEBI", "NITI Aayog", "World Bank", "Ministry of Finance",
               "Ministry of Agriculture", "National Bank for Agriculture and Rural Development"]

# --------------------------------------------------------------------------- #
# Hindi text blocks (ASCII-escaped on purpose: safe to paste through PowerShell)
# --------------------------------------------------------------------------- #
MINI_DICT = {
    "Government": "\u0938\u0930\u0915\u093e\u0930", "Scheme": "\u092f\u094b\u091c\u0928\u093e",
    "Launches": "\u0932\u0949\u0928\u094d\u091a", "Launched": "\u0932\u0949\u0928\u094d\u091a \u0915\u0940 \u0917\u0908",
    "Approved": "\u0938\u094d\u0935\u0940\u0915\u0943\u0924\u093f", "Meeting": "\u092c\u0948\u0920\u0915",
    "Report": "\u0930\u093f\u092a\u094b\u0930\u094d\u091f", "Index": "\u0938\u0942\u091a\u0915\u093e\u0902\u0915",
    "Agriculture": "\u0915\u0943\u0937\u093f", "Farming": "\u0916\u0947\u0924\u0940",
    "Farmers": "\u0915\u093f\u0938\u093e\u0928", "Banking": "\u092c\u0948\u0902\u0915\u093f\u0902\u0917",
    "Reserve Bank of India": "\u092d\u093e\u0930\u0924\u0940\u092f \u0930\u093f\u091c\u093c\u0930\u094d\u0935 \u092c\u0948\u0902\u0915",
    "Reserve Bank": "\u092d\u093e\u0930\u0924\u0940\u092f \u0930\u093f\u091c\u093c\u0930\u094d\u0935 \u092c\u0948\u0902\u0915",
    "Budget": "\u092c\u091c\u091f", "Ministry": "\u092e\u0902\u0924\u094d\u0930\u093e\u0932\u092f",
    "India": "\u092d\u093e\u0930\u0924", "Indian": "\u092d\u093e\u0930\u0924\u0940\u092f",
    "New": "\u0928\u092f\u093e", "National": "\u0930\u093e\u0937\u094d\u091f\u094d\u0930\u0940\u092f",
    "International": "\u0905\u0902\u0924\u0930\u094d\u0930\u093e\u0937\u094d\u091f\u094d\u0930\u0940\u092f",
    "Conference": "\u0938\u092e\u094d\u092e\u0947\u0932\u0928", "Summit": "\u0936\u093f\u0916\u0930 \u0938\u092e\u094d\u092e\u0947\u0932\u0928",
    "Award": "\u092a\u0941\u0930\u0938\u094d\u0915\u093e\u0930", "Wins": "\u091c\u0940\u0924\u093e",
    "Gold": "\u0938\u094d\u0935\u0930\u094d\u0923", "Medal": "\u092a\u0926\u0915", "Hockey": "\u0939\u0949\u0915\u0940",
    "Mission": "\u092e\u093f\u0936\u0928", "Policy": "\u0928\u0940\u0924\u093f",
    "Growth": "\u0935\u0943\u0926\u094d\u0927\u093f", "Inflation": "\u092e\u0939\u0902\u0917\u093e\u0908",
    "Export": "\u0928\u093f\u0930\u094d\u092f\u093e\u0924", "Import": "\u0906\u092f\u093e\u0924",
    "Price": "\u0915\u0940\u092e\u0924", "Power": "\u092c\u093f\u091c\u0932\u0940",
    "Water": "\u091c\u0932", "Food": "\u0916\u093e\u0926\u094d\u092f",
    "Health": "\u0938\u094d\u0935\u093e\u0938\u094d\u0925\u094d\u092f", "Education": "\u0936\u093f\u0915\u094d\u0937\u093e",
    # FIX: original had U+095B + U+093C (double nukta). Correct = U+091C + U+093C.
    "Employment": "\u0930\u094b\u091c\u093c\u0917\u093e\u0930",
    "Rural": "\u0917\u094d\u0930\u093e\u092e\u0940\u0923", "Urban": "\u0936\u0939\u0930\u0940",
    "Climate": "\u091c\u0932\u0935\u093e\u092f\u0941",
}

# Place names that START with a dictionary word - must never be word-translated.
_PROTECTED_PHRASES = ("New Delhi", "New York", "New Zealand", "New South Wales", "New Jersey",
                      "New Mexico", "New Development Bank", "Reserve Bank of India")

_DICT_PATTERNS = [(re.compile(r"\b" + re.escape(k) + r"\b", re.I), v)
                  for k, v in sorted(MINI_DICT.items(), key=lambda kv: -len(kv[0]))]

EXAM_HINTS = {
    "Agriculture": "AGTA/AFO/ICAR focus -- scheme/organism details & Ministry come under Static GK.",
    "Banking & Finance": "IBPS/NABARD/Grade-A focus -- regulator, rate/limit numbers \u092f\u093e\u0926 \u0930\u0916\u0947\u0902\u0964",
    "Economy": "Economic Survey/GDP/CPI type data -- prelims matching favourite.",
    "Government Schemes": "Scheme name-ministry-outlay-target teen-cheez \u092e\u0947\u0902 \u092f\u093e\u0926 \u0915\u0930\u0947\u0902 (prelims statement-based).",
    "International": "Index/Ranking/report -- organising body + headquarters prelims \u092e\u0947\u0902 \u092a\u0942\u091b\u093e \u091c\u093e\u0924\u093e \u0939\u0948\u0964",
    "Science & Technology": "ISRO/DRDO mission details -- agency + location prelims favourite.",
    "Environment": "COP/biodiversity/climate reports -- convention & host country note \u0915\u0930\u0947\u0902\u0964",
    "Sports": "Tournament-winner-host triplet static GK \u092e\u0947\u0902 \u092c\u093e\u0930-\u092c\u093e\u0930 \u0906\u0924\u093e \u0939\u0948\u0964",
    "National": "Appointments/awards -- name + designation + tenure \u0930\u093f\u0915\u0949\u0930\u094d\u0921 \u0915\u0930\u0947\u0902\u0964",
}
EXAM_HINT_DEFAULT = ("Exam angle: source ministry/organisation \u0914\u0930 "
                     "\u0938\u0902\u0916\u094d\u092f\u093e\u0924\u094d\u092e\u0915 \u0924\u0925\u094d\u092f "
                     "\u0926\u094b\u0939\u0930\u093e\u090f\u0902\u0964")

# Hindi question parts (English questions are written in English only)
HI_Q_NUMBER = ("\u0907\u0938\u0938\u0947 \u091c\u0941\u0921\u093c\u0940 \u0938\u0939\u0940 "
               "\u0938\u0902\u0916\u094d\u092f\u093e/\u0930\u093e\u0936\u093f \u0915\u094c\u0928-\u0938\u0940 \u0939\u0948?")
HI_Q_ORG = ("\u0938\u0947 \u0915\u094c\u0928-\u0938\u093e \u092e\u0902\u0924\u094d\u0930\u093e\u0932\u092f/"
            "\u0938\u0902\u0917\u0920\u0928 \u092e\u0941\u0916\u094d\u092f\u0924\u0903 \u091c\u0941\u0921\u093c\u093e \u0939\u0948?")
HI_Q_RANK = ("\u0907\u0938 \u0938\u0942\u091a\u0915\u093e\u0902\u0915/\u0930\u0948\u0902\u0915\u093f\u0902\u0917 "
             "\u092e\u0947\u0902 \u0938\u0939\u0940 \u0930\u0948\u0902\u0915 \u0915\u094c\u0928-\u0938\u0940 \u0939\u0948?")
HI_Q_WHO = ("\u0907\u0938 \u0916\u092c\u0930 \u092e\u0947\u0902 \u092a\u094d\u0930\u092e\u0941\u0916 "
            "\u0938\u0902\u0938\u094d\u0925\u093e/\u0928\u093e\u092e \u0915\u094c\u0928-\u0938\u093e \u0939\u0948?")
HI_Q_STATEMENT = ("\u0918\u091f\u0928\u093e \u0915\u0947 \u092c\u093e\u0930\u0947 \u092e\u0947\u0902 "
                  "\u0915\u094c\u0928-\u0938\u093e \u0915\u0925\u0928 \u0938\u0924\u094d\u092f \u0939\u0948?")

HI_EXPL_NUMBER = ("{src} \u0915\u0947 \u0905\u0928\u0941\u0938\u093e\u0930 -- \u0930\u093f\u092a\u094b\u0930\u094d\u091f "
                  "\u0915\u0940 \u0917\u0908 \u0938\u0902\u0916\u094d\u092f\u093e {val} \u0939\u0948\u0964")
HI_EXPL_ORG = ("\u0938\u094d\u0930\u094b\u0924 \u092a\u093e\u0920 \u092e\u0947\u0902 \u0907\u0938 \u0918\u091f\u0928\u093e "
               "\u0915\u093e \u0938\u0902\u092c\u0902\u0927 {val} \u0938\u0947 \u092c\u0924\u093e\u092f\u093e \u0917\u092f\u093e \u0939\u0948\u0964")
HI_EXPL_RANK = ("\u0938\u0924\u094d\u092f\u093e\u092a\u093f\u0924 \u0938\u094d\u0930\u094b\u0924 \u092e\u0947\u0902 "
                "\u0909\u0932\u094d\u0932\u093f\u0916\u093f\u0924 \u0930\u0948\u0902\u0915: {val}\u0964")
HI_EXPL_WHO = ("\u0938\u094d\u0930\u094b\u0924 {src}: {val} \u0938\u093f\u0930\u0939\u0947\u0921 "
               "\u092e\u0947\u0902 \u092e\u094c\u091c\u0942\u0926 \u0939\u0948\u0964")
HI_EXPL_STATEMENT = ("\u092f\u0939 \u0915\u0925\u0928 {src} \u0915\u0940 \u0938\u0924\u094d\u092f\u093e\u092a\u093f\u0924 "
                     "\u0930\u093f\u092a\u094b\u0930\u094d\u091f \u0938\u0947 \u0938\u0940\u0927\u0947 \u0932\u093f\u092f\u093e "
                     "\u0917\u092f\u093e \u0939\u0948: \"{val}\"\u0964")

HI_POINT_ORG = ("Scheme-Ministry \u091c\u094b\u0921\u093c\u0940 prelims \u092e\u0947\u0902 "
                "\u092c\u093e\u0930-\u092c\u093e\u0930 \u092a\u0942\u091b\u0940 \u091c\u093e\u0924\u0940 \u0939\u0948\u0964")
HI_POINT_RANK = "Index/Ranking - country/score prelims favourite \u0939\u0948\u0964"
HI_POINT_WHO = ("Agency/ministry name prelims \u092e\u0947\u0902 \u0938\u0940\u0927\u0947 "
                "\u092a\u0942\u091b\u093e \u091c\u093e\u0924\u093e \u0939\u0948\u0964")
HI_POINT_STATEMENT = ("Statement-based questions \u0905\u092c \u0938\u092c\u0938\u0947 common prelims "
                      "pattern \u0939\u0948\u0964")


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def _norm_ws(text):
    return re.sub(r"\s+", " ", text or "").strip()


def _plain_headline(text):
    """Remove the '>> ' display prefix and normalise whitespace."""
    return re.sub(r"^[>\s]+", "", _norm_ws(text))


def _clip(text, limit):
    """Clip at a word boundary (the result is always a prefix of the input)."""
    text = _norm_ws(text)
    if len(text) <= limit:
        return text
    cut = text[:limit]
    sp = cut.rfind(" ")
    if sp >= int(limit * 0.6):
        cut = cut[:sp]
    return cut.rstrip(" ,;:-")


def _to_float(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _dedupe(seq):
    return list(dict.fromkeys(seq))


def _has_digit(s):
    return any(ch.isdigit() for ch in str(s))


def _similar(a, b):
    return SequenceMatcher(None, str(a).lower(), str(b).lower()).ratio()


def _too_similar(a, b):
    """Numeric options differ by design (100 vs 200 crore) - only text options are compared."""
    a, b = str(a), str(b)
    if _has_digit(a) and _has_digit(b):
        return a.lower() == b.lower()
    return _similar(a, b) > SIMILARITY_LIMIT


def _qkey(question):
    return re.sub(r"\W+", "", (question or "").lower())[:60]


def _canon(s):
    """'Rs. 1,200 crore' and 'Rs 1,200 crore' are the same value."""
    return re.sub(r"\s+", "", str(s).lower()).replace("rs.", "rs")


def _clean_nums(text):
    out, seen = [], set()
    for n in NUM_RE.findall(text or ""):
        n = _norm_ws(n).strip(" .,;:")
        if n and _canon(n) not in seen:
            seen.add(_canon(n))
            out.append(n)
    return out


def _own_text(ci):
    """Text that every MCQ answer MUST be found in."""
    return _norm_ws(_plain_headline(ci.get("headline_en")) + " | " + " | ".join(ci.get("key_points_en") or []))


# --------------------------------------------------------------------------- #
# Entities (organisations / names) - deterministic, substring-safe
# --------------------------------------------------------------------------- #
def _trim_entity(phrase):
    toks = _norm_ws(phrase).split(" ")
    while toks and toks[0].lower() in LEADING_STOP:
        toks.pop(0)
    for i, tok in enumerate(toks):
        if tok.lower() in ACTION_WORDS:
            toks = toks[:i]
            break
    while toks and (toks[-1].lower() in LEADING_STOP or toks[-1].lower() in TRAILING_DROP):
        toks.pop()
    out = " ".join(toks).strip(" ,;:-")
    return out if len(out) > 3 else ""


def _extract_entities(text):
    """Organisation phrases first, then acronyms, then capitalised names. Always substrings of text."""
    text = _norm_ws(text)
    found = []
    for m in ORG_RE.finditer(text):
        e = _trim_entity(m.group(0))
        if e:
            found.append(e)
    if not text.isupper():
        for m in ACRONYM_RE.finditer(text):
            if m.group(0) not in ACRONYM_STOP:
                found.append(m.group(0))
    for m in CAP_RE.finditer(text):
        e = _trim_entity(m.group(0))
        if e and len(e.split()) >= 2:
            found.append(e)
    found = _dedupe(found)
    # drop entities that are only a fragment of a longer one ("Reserve Bank" vs "Reserve Bank of India")
    return [e for e in found if not any(e != o and e.lower() in o.lower() for o in found)]


def _first_org(text):
    for m in ORG_RE.finditer(_norm_ws(text)):
        e = _trim_entity(m.group(0))
        if e:
            return e
    return ""


def _entity_kind(e):
    return "acr" if re.fullmatch(r"[A-Z]{2,8}", e or "") else "phrase"


# --------------------------------------------------------------------------- #
# Extraction (key points / static facts / exam angle)
# --------------------------------------------------------------------------- #
def split_sentences(text):
    text = text or ""
    text = _ABBREV_RE.sub(lambda m: m.group(1) + "\x00", text)            # Rs. Dr. Mr. ...
    text = _INITIALS_RE.sub(lambda m: m.group(0).replace(".", "\x00"), text)  # U.S. A.P.
    parts = re.split(r"(?<=[.!?|\u0964])\s+", text)
    out = []
    for p in parts:
        p = p.replace("\x00", ".").strip(" .|\u0964")
        if len(p) > 15:
            out.append(p)
    return out


def extract_key_points(item, max_points=4):
    item = item or {}
    headline = _plain_headline(item.get("headline_en"))
    src = (item.get("raw_facts") or "") + ". " + headline
    pts = []
    for s in split_sentences(src):
        s = _norm_ws(s)
        if len(s) <= 20:
            continue
        if any(_similar(s, p) > 0.9 for p in pts):      # exact or near duplicate
            continue
        pts.append(_clip(s, 220))
        if len(pts) >= max_points:
            break
    if not pts and headline:
        pts = [_clip(headline, 220)]
    return pts


def extract_static_facts(item):
    item = item or {}
    src = _norm_ws(_plain_headline(item.get("headline_en")) + " | " + (item.get("raw_facts") or ""))
    facts = {}
    for i, n in enumerate(_clean_nums(src)[:3]):
        facts["Fact %d" % (i + 1)] = n
    firsts = re.findall(r"[^.;|]{0,60}\bFirst[- ][^.;|]{0,60}", src, re.I)
    if firsts and _norm_ws(firsts[0]):
        facts["First/Unique"] = _clip(firsts[0], 120)
    ents = [e for e in _extract_entities(src) if len(e) > 4][:2]
    if ents:
        facts["Key Name"] = ", ".join(ents)      # display only - never used as an MCQ answer
    return facts


def exam_fact(item):
    item = item or {}
    hint = EXAM_HINTS.get(item.get("category", ""), EXAM_HINT_DEFAULT)
    return hint + ' Source event: "' + _clip(_plain_headline(item.get("headline_en")), 80) + '".'


# --------------------------------------------------------------------------- #
# Translation (AI primary, deterministic flagged fallback)
# --------------------------------------------------------------------------- #
def translate_headline_deterministic(en):
    """Dictionary-only Hindi. Mixed Hindi/English output - ALWAYS flagged needs_review."""
    out = en or ""
    holders = []
    for phrase in _PROTECTED_PHRASES:
        if phrase in out:
            holders.append(phrase)
            out = out.replace(phrase, "\x01%d\x01" % (len(holders) - 1))
    for pattern, hindi in _DICT_PATTERNS:
        out = pattern.sub(lambda m, h=hindi: h, out)
    out = re.sub(r"\s&\s", " \u0914\u0930 ", out)
    out = out.replace(" - ", " -- ")
    for i, phrase in enumerate(holders):
        if phrase == "Reserve Bank of India":
            phrase = MINI_DICT["Reserve Bank of India"]
        out = out.replace("\x01%d\x01" % i, phrase)
    return out


def translate_headline(text):
    """Backward-compatible alias - agents/12_content_editor.py imports this name."""
    return translate_headline_deterministic(text)


_AI_TRANSLATE_FN = None
_AI_IMPORT_FAILED = False
_TRANSLATION_CACHE = {}


def _get_ai_translate_fn():
    global _AI_TRANSLATE_FN, _AI_IMPORT_FAILED
    if _AI_TRANSLATE_FN is not None:
        return _AI_TRANSLATE_FN
    if _AI_IMPORT_FAILED:
        return None
    try:
        from pipeline.ai_translator import translate_content
        _AI_TRANSLATE_FN = translate_content
        return _AI_TRANSLATE_FN
    except ImportError:
        _AI_IMPORT_FAILED = True
        logger.warning("[Translation] pipeline.ai_translator not available - fallback mode")
        return None


def translate_with_ai_or_fallback(text, task="general"):
    """
    Returns (hindi_text, method, confidence).
    method: "ai_translator" | "deterministic_fallback" | "untranslated" (strict mode) | "empty"
    """
    text = _norm_ws(text)
    if not text:
        return "", "empty", 0.0
    key = (task, text)
    if key in _TRANSLATION_CACHE:
        return _TRANSLATION_CACHE[key]

    reason = "ai_translator module not available"
    fn = _get_ai_translate_fn()
    if fn is not None:
        try:
            res = fn(text, task=task) or {}
            hindi = (res.get("translated_hi") or "").strip()
            if res.get("passed") and hindi:
                conf = _to_float(res.get("confidence"))
                logger.debug("[Translation] AI passed (confidence=%.2f)", conf)
                if len(_TRANSLATION_CACHE) > 2000:
                    _TRANSLATION_CACHE.clear()
                _TRANSLATION_CACHE[key] = (hindi, "ai_translator", conf)
                return _TRANSLATION_CACHE[key]
            reason = "validation failed: %s" % (res.get("issues") or "no translation returned")
        except Exception as exc:  # network / provider / parsing errors
            reason = "error: %s" % exc

    log = logger.debug if fn is None else logger.warning     # module missing: warned once at import
    log("[Translation] AI unavailable for task=%s (%s)", task, reason)
    if os.getenv("ALP_TRANSLATION_STRICT", "0") == "1":
        return text, "untranslated", 0.0          # fail-closed: never ship dictionary Hindi
    return translate_headline_deterministic(text), "deterministic_fallback", 0.0


# --------------------------------------------------------------------------- #
# Optional AI polish (English wording only) - facts re-verified afterwards
# --------------------------------------------------------------------------- #
def _bare_numbers(text):
    return set(_NUM_RE.findall(text or ""))


def _facts_preserved(candidate, original, source_text):
    """Polished text may NOT add numbers or names, and may NOT drop numbers."""
    if not _bare_numbers(original) <= _bare_numbers(candidate):
        return False
    allowed = _bare_numbers(original + " " + source_text)
    if _bare_numbers(candidate) - allowed:
        return False
    if set(NUM_RE.findall(candidate)) - set(NUM_RE.findall(original + " " + source_text)):
        return False
    src_words = set(w.lower() for w in re.findall(r"[A-Za-z][A-Za-z&-]*", original + " " + source_text))
    for word in re.findall(r"\b[A-Z][A-Za-z]{2,}\b", candidate):
        if word.lower() not in src_words:
            return False
    return True


def polish_with_ai(text, source_text):
    key = os.getenv("OPENAI_API_KEY")
    if not key or os.getenv("ALP_DISABLE_POLISH", "0") == "1" or not text:
        return text
    try:
        import requests as _rq
        r = _rq.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": "Bearer " + key},
            json={"model": os.getenv("ALP_LLM", "gpt-4o-mini"),
                  "temperature": 0,
                  "messages": [
                      {"role": "system",
                       "content": "You are a copy editor. Rewrite for clarity only. Never add, remove or "
                                  "change any fact, number or name. Reply with the rewritten text only."},
                      {"role": "user", "content": text}],
                  "max_tokens": 300},
            timeout=30)
        r.raise_for_status()
        cand = _norm_ws(r.json()["choices"][0]["message"]["content"]).strip("\"'")
    except Exception as exc:
        logger.warning("[Polish] skipped: %s", exc)
        return text
    if not cand or len(cand) > max(int(len(text) * 1.5), len(text) + 60):
        return text
    if not _facts_preserved(cand, text, source_text or ""):
        logger.info("[Polish] rejected - fact check failed")
        return text
    return cand


# --------------------------------------------------------------------------- #
# build_content
# --------------------------------------------------------------------------- #
def _track(stats, flags, method):
    if method == "ai_translator":
        stats["ai_passed"] += 1
    elif method == "deterministic_fallback":
        stats["deterministic_fallback"] += 1
        flags.append(method)
    elif method == "untranslated":
        stats["untranslated"] += 1
        flags.append(method)


def _translate_tracked(text, task, stats, flags):
    hindi, method, _conf = translate_with_ai_or_fallback(text, task=task)
    _track(stats, flags, method)
    return hindi


def _build_entry(it, stats):
    if not isinstance(it, dict):
        return None
    title = _plain_headline(it.get("headline_en"))
    if not title:
        logger.warning("[Content Builder] skipped item without headline_en: %s", it.get("event_id"))
        return None
    event_id = str(it.get("event_id") or "ev_" + hashlib.sha1(title.encode("utf-8")).hexdigest()[:12])
    work = dict(it)
    work["headline_en"] = title
    work["event_id"] = event_id
    raw_facts = it.get("raw_facts") or ""

    kps = extract_key_points(work)
    sf = extract_static_facts(work)
    ef = exam_fact(work)

    flags = []
    headline_hi = _translate_tracked(title, "headline", stats, flags)
    key_points_hi = [_translate_tracked(kp, "key_points", stats, flags) for kp in kps]
    exam_fact_hi = _translate_tracked(ef, "general", stats, flags)

    title_en = polish_with_ai(title, raw_facts)
    kps_en = [polish_with_ai(p, raw_facts) for p in kps]

    return {
        "event_id": event_id,
        "category": it.get("category") or "National",
        "headline_en": HEADLINE_PREFIX + title_en,
        "headline_hi": HEADLINE_PREFIX + headline_hi,
        "key_points_en": kps_en,
        "key_points_hi": key_points_hi,
        "static_facts": sf,
        "exam_fact_en": ef,
        "exam_fact_hi": exam_fact_hi,
        "source": {"name": it.get("source_name", ""), "url": it.get("source_url", ""),
                   "tier": it.get("source_tier", ""), "date": it.get("pub_time_ist")},
        "importance_score": it.get("importance_score", 0),
        "image_path": it.get("image_path", ""),
        "needs_review": bool(flags),          # True => Hindi came from the dictionary fallback
    }


def build_content(items, job_meta):
    items = list(items or [])
    logger.info("[Content Builder] Building content for %d items...", len(items))
    stats = {"total_items": len(items), "ai_passed": 0, "ai_failed": 0,
             "deterministic_fallback": 0, "untranslated": 0, "skipped_items": 0}
    out = []
    for idx, it in enumerate(items):
        try:
            entry = _build_entry(it, stats)
        except Exception:
            logger.exception("[Content Builder] item #%d failed and was skipped", idx)
            entry = None
        if entry is None:
            stats["skipped_items"] += 1
        else:
            out.append(entry)

    stats["ai_failed"] = stats["deterministic_fallback"] + stats["untranslated"]
    total = stats["ai_passed"] + stats["ai_failed"]
    ai_pct = (stats["ai_passed"] / total * 100.0) if total else 0.0
    logger.info("[Content Builder] Translation stats: ai=%d fallback=%d untranslated=%d (AI success %.1f%%)",
                stats["ai_passed"], stats["deterministic_fallback"], stats["untranslated"], ai_pct)
    if stats["ai_failed"]:
        logger.warning("[Content Builder] %d translations need review (AI did not pass)", stats["ai_failed"])
    if stats["skipped_items"]:
        logger.warning("[Content Builder] %d items skipped", stats["skipped_items"])

    meta = job_meta if isinstance(job_meta, dict) else {}
    return {"job": job_meta,
            "edition_title": meta.get("edition_title") or "Current Affairs",
            "items": out,
            "translation_stats": stats}


# --------------------------------------------------------------------------- #
# MCQ helpers
# --------------------------------------------------------------------------- #
def _memory_pools():
    """(numbers, entity names, headlines) from the importance memory - used only to fill distractors."""
    mem = {}
    try:
        from pipeline.store import load_memory
        mem = load_memory() or {}
    except Exception:
        mem = {}
    if not mem:
        paths = [os.getenv("ALP_MEMORY_PATH") or MEMORY_DEFAULT_PATH,
                 str(Path(__file__).resolve().parent.parent / MEMORY_DEFAULT_PATH)]
        for p in paths:
            try:
                if Path(p).exists():
                    mem = json.loads(Path(p).read_text(encoding="utf-8")) or {}
                    break
            except Exception as exc:
                logger.warning("[MCQ] memory file unreadable (%s): %s", p, exc)
    if isinstance(mem, dict):
        events = list(mem.values())
    elif isinstance(mem, list):
        events = list(mem)
    else:
        events = []
    nums, names, heads = [], [], []
    for ev in [e for e in events if isinstance(e, dict)][:300]:
        hl = _norm_ws(ev.get("headline"))
        facts = _norm_ws(ev.get("raw_facts"))
        if not (hl or facts):
            continue
        nums += _clean_nums(hl + " " + facts)
        names += _extract_entities(hl)
        if hl:
            heads.append(_clip(hl, 150))
    return _dedupe(nums), _dedupe(names), _dedupe(heads)


def _build_pools(content_items):
    mem_nums, mem_names, mem_heads = _memory_pools()
    nums, ents = [], []
    for ci in content_items or []:
        nums += [v for k, v in (ci.get("static_facts") or {}).items() if k.startswith("Fact")]
        ents += _extract_entities(_own_text(ci))
    return {"nums": _dedupe(nums + mem_nums),
            "ents": _dedupe(ents + mem_names + DOMAIN_ORGS),
            "heads": mem_heads}


def _num_kind(s):
    t = _norm_ws(s).lower()
    unit = re.search(r"(crore|lakh|billion|million|trillion|thousand|cr|bn|mn)$", t)
    if re.match(r"^(?:rs\.?|inr|usd|us\$|\$|\u20b9)", t):
        return "money:" + (unit.group(1) if unit else "")
    if "%" in t or "percent" in t or "per cent" in t:
        return "percent"
    m = re.search(r"([a-z]+)$", t)
    return m.group(1) if m else "plain"


def _group_digits(int_part, indian):
    if len(int_part) <= 3:
        return int_part
    if not indian:
        return "{:,}".format(int(int_part))
    head, tail = int_part[:-3], int_part[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts + [tail])


def _format_like(raw, value):
    text = ("%.2f" % value).rstrip("0").rstrip(".")
    int_part, _, dec = text.partition(".")
    base = float(raw.replace(",", ""))
    if "," in raw or (value >= 1000 and base < 1000):
        indian = bool(re.fullmatch(r"\d{1,2}(?:,\d{2})+,\d{3}", raw.split(".")[0]))
        int_part = _group_digits(int_part, indian)
    return int_part + ("." + dec if dec else "")


def _num_variants(s):
    """Plausible wrong numbers in the SAME format/unit as s (x2, x0.5, x3, x1.5)."""
    m = _NUM_RE.search(s or "")
    if not m:
        return []
    raw = m.group(0)
    try:
        x = float(raw.replace(",", ""))
    except ValueError:
        return []
    out = []
    for factor in (2, 0.5, 3, 1.5):
        y = x * factor
        if y <= 0:
            continue
        out.append(s.replace(raw, _format_like(raw, y), 1))
    return _dedupe(out)


def _ordinal(n):
    if 11 <= n % 100 <= 13:
        return "%dth" % n
    return "%d%s" % (n, {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


def _rank_variants(rank_text):
    m = re.match(r"\d+", rank_text)
    if not m:
        return []
    k = int(m.group(0))
    return [_ordinal(k + d) for d in (1, -1, 2, -2, 3, 5, 10) if k + d >= 1]


def _filter_distractors(correct, candidates, forbidden_text, limit=MAX_OPTIONS - 1):
    """Keep distractors that are distinct, not near-duplicates and NOT present in the source text."""
    forb = (forbidden_text or "").lower()
    chosen = []
    for d in candidates:
        d = _norm_ws(str(d))
        if not d or _canon(d) == _canon(correct) or d.lower() in forb:
            continue
        if any(_canon(d) == _canon(x) for x in chosen):
            continue
        if any(_too_similar(d, x) for x in chosen + [correct]):
            continue
        chosen.append(d)
        if len(chosen) >= limit:
            break
    return chosen


def _shuffle_options(correct, distractors, salt=""):
    """Deterministic (re-runnable) shuffle - answer position depends on salt + answer."""
    opts = [correct] + list(distractors)
    h = int(hashlib.sha1((salt + "|" + correct).encode("utf-8")).hexdigest(), 16)
    k = h % len(opts)
    opts = opts[k:] + opts[:k]
    return opts, opts.index(correct)


def _make_mcq(ci, mtype, q_en, q_hi, correct, distractors, expl_en, expl_hi, exam_point):
    if len(distractors) < MIN_OPTIONS - 1:
        return None
    opts, idx = _shuffle_options(correct, distractors[:MAX_OPTIONS - 1],
                                 salt=str(ci.get("event_id", "")) + mtype + q_en)
    return {"type": mtype, "question_en": q_en, "question_hi": q_hi,
            "options": opts, "correct": "ABCDE"[idx],
            "explanation_en": expl_en, "explanation_hi": expl_hi,
            "exam_point": exam_point, "event_id": ci.get("event_id", ""),
            "source_url": (ci.get("source") or {}).get("url", "")}


def _build_item_candidates(ci, pools, all_items):
    """All MCQs that can be built for one item, in priority order (every answer is in the source text)."""
    cands = []
    headline = _plain_headline(ci.get("headline_en"))
    headline_hi = _plain_headline(ci.get("headline_hi"))
    kps = ci.get("key_points_en") or []
    own_text = _own_text(ci)
    src_name = (ci.get("source") or {}).get("name") or "the source"
    h90, h80, h70 = _clip(headline, 90), _clip(headline, 80), _clip(headline, 70)
    hh90, hh80, hh70 = _clip(headline_hi, 90), _clip(headline_hi, 80), _clip(headline_hi, 70)

    # 1) static number ---------------------------------------------------------
    nums = [v for k, v in (ci.get("static_facts") or {}).items()
            if k.startswith("Fact") and v in own_text and _has_digit(v)]
    if nums:
        fact = nums[0]
        same_kind = [n for n in pools["nums"] if _num_kind(n) == _num_kind(fact)]
        distractors = _filter_distractors(fact, same_kind[:2] + _num_variants(fact) + same_kind[2:], own_text)
        mcq = _make_mcq(
            ci, "static-number",
            'Which figure is associated with the news: "%s"?' % h90,
            hh90 + " -- " + HI_Q_NUMBER,
            fact, distractors,
            'As per %s: "%s" -- the reported figure is %s.' % (src_name, h90, fact),
            HI_EXPL_NUMBER.format(src=src_name, val=fact),
            _clip(ci.get("exam_fact_en") or "", 120))
        if mcq:
            cands.append(mcq)

    # 2) scheme -> ministry / organisation ---------------------------------------
    org = _first_org(own_text)
    if org:
        pool = sorted(pools["ents"], key=lambda e: _entity_kind(e) != _entity_kind(org))
        mcq = _make_mcq(
            ci, "scheme-ministry",
            'Which ministry/organisation is mainly associated with "%s"?' % h70,
            '"' + hh70 + '" ' + HI_Q_ORG,
            org, _filter_distractors(org, pool, own_text),
            "Source text pairs this event with: %s." % org,
            HI_EXPL_ORG.format(val=org),
            HI_POINT_ORG)
        if mcq:
            cands.append(mcq)

    # 3) report rank -------------------------------------------------------------
    rk = RANK_RE.search(own_text)
    if rk:
        rank = rk.group(1) or rk.group(2)
        mcq = _make_mcq(
            ci, "report-rank",
            'Which rank is mentioned in the report/news: "%s"?' % h70,
            '"' + hh70 + '" -- ' + HI_Q_RANK,
            rank, _filter_distractors(rank, _rank_variants(rank), own_text),
            "Rank mentioned verbatim in verified source: %s." % rank,
            HI_EXPL_RANK.format(val=rank),
            HI_POINT_RANK)
        if mcq:
            cands.append(mcq)

    # 4) who / organisation name -------------------------------------------------
    names = [e for e in _extract_entities(headline) + _extract_entities(own_text)
             if e != org and e in own_text]
    if names:
        name = names[0]
        pool = sorted(pools["ents"], key=lambda e: _entity_kind(e) != _entity_kind(name))
        mcq = _make_mcq(
            ci, "who-org",
            'Which organisation/name is central to the news: "%s"?' % h80,
            '"' + hh80 + '" -- ' + HI_Q_WHO,
            name, _filter_distractors(name, pool, own_text),
            "Source %s: %s appears verbatim in the verified headline/key points." % (src_name, name),
            HI_EXPL_WHO.format(src=src_name, val=name),
            HI_POINT_WHO)
        if mcq:
            cands.append(mcq)

    # 5) statement ---------------------------------------------------------------
    if kps:
        correct = _clip(kps[0], 150)
        others = [_clip(p, 150) for o in all_items if o.get("event_id") != ci.get("event_id")
                  for p in (o.get("key_points_en") or [])[:1]]
        others += pools["heads"]
        mcq = _make_mcq(
            ci, "statement",
            'Which statement about "%s" is correct?' % h70,
            '"' + hh70 + '" ' + HI_Q_STATEMENT,
            correct, _filter_distractors(correct, others, own_text),
            'Statement directly taken from verified reporting by %s: "%s".' % (src_name, correct),
            HI_EXPL_STATEMENT.format(src=src_name, val=correct),
            HI_POINT_STATEMENT)
        if mcq:
            cands.append(mcq)
    return cands


def generate_mcqs(content_items, target=(12, 15)):
    """
    Round-robin over items so the day's MCQs are spread across all news
    (1st MCQ of every item, then the 2nd of every item ...) until `target[1]`.
    """
    min_t, max_t = target
    content_items = [c for c in (content_items or []) if isinstance(c, dict)]
    if not content_items:
        return []
    pools = _build_pools(content_items)
    per_item = []
    for ci in content_items:
        try:
            per_item.append(_build_item_candidates(ci, pools, content_items))
        except Exception:
            logger.exception("[MCQ] candidate build failed for %s", ci.get("event_id"))
            per_item.append([])

    mcqs, rnd = [], 0
    while len(mcqs) < max_t:
        progressed = False
        for cands in per_item:
            if rnd < len(cands):
                mcqs.append(cands[rnd])
                progressed = True
                if len(mcqs) >= max_t:
                    break
        if not progressed:
            break
        rnd += 1

    if len(mcqs) < min_t:
        logger.warning("[MCQ] generated %d MCQs, below the minimum target of %d", len(mcqs), min_t)
    renumber_mcqs(mcqs)
    return mcqs


def renumber_mcqs(mcqs):
    """Set q_num = 1..N (call again after merging ai_augment_mcqs output)."""
    for i, m in enumerate(mcqs, 1):
        m["q_num"] = i
    return mcqs


def validate_mcqs(mcqs, content_items):
    src_by_event = {}
    for c in content_items or []:
        src_by_event[c.get("event_id")] = _own_text(c)
    valid, rejected, seen_q = [], [], set()
    stats = {"total": len(mcqs or []), "passed": 0, "failed": 0}

    for m in mcqs or []:
        errs = []
        opts = [str(o) for o in (m.get("options") or [])]

        if len(set(o.lower() for o in opts)) != len(opts):
            errs.append("duplicate options")
        if not (MIN_OPTIONS <= len(opts) <= MAX_OPTIONS):
            errs.append("option count invalid")

        letter = m.get("correct", "")
        ci_idx = ord(letter) - ord("A") if isinstance(letter, str) and len(letter) == 1 else -1
        if not (0 <= ci_idx < len(opts)):
            errs.append("answer index out of range")
        else:
            src_text = src_by_event.get(m.get("event_id"), "")
            correct = opts[ci_idx]
            if correct not in src_text:
                errs.append("answer not supported by source text")
            if any(o.lower() in src_text.lower() for i, o in enumerate(opts) if i != ci_idx):
                errs.append("a distractor also appears in the source text (ambiguous answer)")
            if m.get("explanation_en") and correct not in m["explanation_en"]:
                errs.append("explanation missing correct option value")

        qkey = _qkey(m.get("question_en"))
        if qkey in seen_q:
            errs.append("duplicate question")
        if any("none of these" in o.lower() for o in opts):
            errs.append("auto 'none of these' not allowed")
        if len(m.get("question_en") or "") < 20:
            errs.append("question too short")
        if not (m.get("question_hi") or "").strip():
            errs.append("missing Hindi question")

        similar_pair = None
        for i in range(len(opts)):
            for j in range(i + 1, len(opts)):
                if _too_similar(opts[i], opts[j]):
                    similar_pair = (i, j)
                    break
            if similar_pair:
                break
        if similar_pair:
            errs.append("options %d and %d too similar" % similar_pair)

        if errs:
            rejected.append(dict(m, errors=errs))
            stats["failed"] += 1
        else:
            seen_q.add(qkey)
            valid.append(m)
            stats["passed"] += 1

    logger.info("[MCQ Validation] %d/%d MCQs passed (%d rejected)",
                stats["passed"], stats["total"], stats["failed"])
    return valid, rejected


# --------------------------------------------------------------------------- #
# Optional AI-assisted MCQs (the AI only writes the question line)
# --------------------------------------------------------------------------- #
def _ai_mcq_for_item(ci, pools, existing_q, route):
    own_text = _own_text(ci)
    nums = [v for k, v in (ci.get("static_facts") or {}).items()
            if k.startswith("Fact") and v in own_text and _has_digit(v)]
    ents = [e for e in _extract_entities(own_text) if e in own_text][:3]
    candidates = nums + ents
    if not candidates:
        return None
    prompt = (
        "Write ONE competitive-exam MCQ question line (English, max 200 characters). Its correct answer "
        "must be exactly ONE of the CANDIDATES below. Do NOT put the answer inside the question.\n"
        "NEWS: " + own_text[:900] + "\n"
        "CANDIDATES: " + json.dumps(candidates, ensure_ascii=False) + "\n"
        'Respond ONLY as JSON: {"question": "...", "fact": "<one candidate, copied exactly>", '
        '"exam_point": "<max 10 words>"}')
    out = route(prompt, task="mcq")
    m = re.search(r"\{[\s\S]*\}", str(out))
    if not m:
        return None
    data = json.loads(m.group())
    q = _norm_ws(data.get("question"))
    fact = _norm_ws(data.get("fact"))
    ep = _norm_ws(data.get("exam_point")) or "Prelims-relevant factual question."
    if not q or len(q) < 20 or fact not in candidates:
        return None
    if fact.lower() in q.lower():                       # question must not leak the answer
        return None
    if _qkey(q) in existing_q:
        return None
    if _has_digit(fact):
        same_kind = [n for n in pools["nums"] if _num_kind(n) == _num_kind(fact)]
        pool = same_kind[:2] + _num_variants(fact) + same_kind[2:]
    else:
        pool = sorted(pools["ents"], key=lambda e: _entity_kind(e) != _entity_kind(fact))
    distractors = _filter_distractors(fact, pool, own_text)
    if len(distractors) < MIN_OPTIONS - 1:
        return None
    opts, idx = _shuffle_options(fact, distractors, salt=str(ci.get("event_id", "")) + q)
    return {"type": "ai-direct", "question_en": q[:200], "question_hi": "",
            "options": opts[:MAX_OPTIONS], "correct": "ABCDE"[idx],
            "explanation_en": 'Verbatim from verified source: "%s".' % fact,
            "explanation_hi": "", "exam_point": ep[:120],
            "event_id": ci.get("event_id", ""),
            "source_url": (ci.get("source") or {}).get("url", "")}


def _hindi_for_added(added, route):
    lines = []
    for m in added:
        lines += [m["question_en"], m["explanation_en"]]
    got = []
    try:
        out = route("Translate each line to Hindi (Devanagari, exam style). Return exactly "
                    + str(len(lines)) + " lines, one per input, no numbering:\n" + "\n".join(lines),
                    task="bilingual", needs_hindi=True)
        got = [ln.strip() for ln in str(out).splitlines() if ln.strip()]
    except Exception as exc:
        logger.warning("[ai_augment_mcqs] Hindi batch failed: %s", exc)
    batch_ok = len(got) == len(lines)
    for i, m in enumerate(added):
        if batch_ok:
            m["question_hi"], m["explanation_hi"] = got[2 * i], got[2 * i + 1]
            m["hi_is_fallback"] = False
            continue
        q_hi, q_method, _ = translate_with_ai_or_fallback(m["question_en"], task="general")
        e_hi, e_method, _ = translate_with_ai_or_fallback(m["explanation_en"], task="general")
        m["question_hi"] = q_hi or m["question_en"]
        m["explanation_hi"] = e_hi or m["explanation_en"]
        m["hi_is_fallback"] = not (q_method == "ai_translator" and e_method == "ai_translator")


def ai_augment_mcqs(content_items, existing_mcqs, max_add=6):
    try:
        from pipeline.ai_router import route
    except ImportError:
        return []
    content_items = [c for c in (content_items or []) if isinstance(c, dict)]
    pools = _build_pools(content_items)
    existing_q = {_qkey(m.get("question_en")) for m in (existing_mcqs or [])}
    added = []
    for ci in content_items:
        if len(added) >= max_add:
            break
        try:
            mcq = _ai_mcq_for_item(ci, pools, existing_q, route)
        except Exception as exc:
            logger.warning("[ai_augment_mcqs] item %s skipped: %s", ci.get("event_id"), exc)
            continue
        if mcq:
            added.append(mcq)
            existing_q.add(_qkey(mcq["question_en"]))
    if added:
        _hindi_for_added(added, route)
    return added


# Compatibility: context helpers used to occupy this module.
from pipeline.agent_context import JobContext, agent_main, get_context  # noqa: F401
