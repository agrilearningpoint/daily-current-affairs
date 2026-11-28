"""Source-text sanitizer (2026-11-11 PDF review).

Three defects reached the 2026-11-11 edition from dirty source text:

* a Mint paywall boilerplate line became the story summary
  ("This is a Mint Premium article gifted to you" / "Subscribe to enjoy
  similar stories"),
* many "key points" were only the headline plus a bare source attribution
  ("...Maharashtra www.pib.gov.in", "DD News", "Ministry of External Affairs"),
* several bullets were clipped mid-sentence by the source itself
  ("...growers in Marathwada and other regions were allegedly").

Everything here is deterministic line/sentence surgery applied at content
build time, before any translation request is spent on the junk.
"""
from __future__ import annotations

import re
from typing import List

# Paywall / engagement boilerplate, English and Hindi.
PAYWALL_RE = re.compile(
    r"(premium article|gifted to you|subscribe to|sign up for|newsletter|cookie policy|"
    r"privacy policy|read the full|full story here|click here|follow us on|download the app|"
    r"प्रीमियम लेख|उपहार में दिया|सब्सक्राइब करें|न्यूज़लेटर)",
    re.I)

# A line that is nothing but a photo/source credit, a bare domain, or a bare
# attribution ("DD News", "Ministry of External Affairs") - none of these is a fact.
BARE_SOURCE_RE = re.compile(
    r"^(?:photo|image|picture|source|credit|representational image)[:\s-]*.*$|"
    r"^(?:www\.)?[A-Za-z0-9.-]+\.(?:gov\.in|nic\.in|com|co\.in|org|net|in|io)$|"
    r"^(?:ministry|department) of [a-z0-9 &'()-]+$|"
    r"^[a-z]{2,10} (?:news|live|now|today|desk|bureau)$",
    re.I)

# A trailing bare-domain token glued onto an otherwise real sentence.
TRAILING_SOURCE_RE = re.compile(
    r"\s+(?:www\.)?[A-Za-z0-9-]+\.(?:gov\.in|nic\.in|com|co\.in|org|net|in|io)\s*$",
    re.I)

_TERMINALS = (".", "!", "?", "…", "।", '"', "'", ")")

# Below this many English words of body text a source cannot support a story
# (the 2026-11-11 PM E-DRIVE stub had 11 and printed pure boilerplate).
SHALLOW_RAW_WORDS = 20


DANGLING_SENTENCE_ENDINGS = re.compile(
    r"(?:worth\s+around\s+Rs\.?|worth\s+Rs\.?|costing\s+Rs\.?|around\s+Rs\.?|"
    r"\b(?:Rs|₹)\.?|\b(?:at|in|on|with|by|for|of|to|and|the|a|an)\s*|"
    r"(?-i:\s+[b-hj-z]\s*)|"
    r"लागत\s+लगभग\s+रुपये?|लगभग\s+रुपये?|(?:^|\s)(?:रुपये?|के\s+लिए|में|को|और))\s*$",
    re.IGNORECASE
)

_TRAILING_ORPHAN_HI = re.compile(
    r"(?:^|\s)(?:लागत|लगभग|रुपये?|के\s+लिए|की|के|का|में|को|से|पर|और|एवं|जिसकी|जिनकी|जिसके|जिनके|जिसका|जिनका)\s*$"
)


def is_dangling_sentence(text: str) -> bool:
    """Return True if *text* ends mid-thought on a dangling token or incomplete Hindi ending."""
    if not text or not isinstance(text, str):
        return False
    t = str(text).strip()
    if t.endswith("…"):
        return True
    clean_tail = re.sub(r"[.!?।…|\s]+$", "", t).strip()
    return bool(clean_tail and DANGLING_SENTENCE_ENDINGS.search(clean_tail))


def _last_complete_sentence(text: str, min_chars: int = 25) -> str:
    """Return prefix ending at the last complete sentence boundary before a dangling tail."""
    # Temporarily shield decimals and abbreviations such as Rs., Dr., U.S.
    masked = re.sub(r"\b(Rs|Dr|Mr|Mrs|Ms|Prof|Sr|Jr|St|No|vs)\.", lambda m: m.group(1) + "\x00", text)
    masked = re.sub(r"(\d)\.(\d)", lambda m: f"{m.group(1)}\x00{m.group(2)}", masked)
    last_boundary = -1
    for m in re.finditer(r"[।!?](?:\s|$)|\.(?:\s|$)", masked):
        cand = masked[: m.start() + 1].replace("\x00", ".").strip()
        if len(cand) >= min_chars and not is_dangling_sentence(cand):
            last_boundary = m.start() + 1
    if last_boundary > 0:
        return masked[:last_boundary].replace("\x00", ".").strip()
    return ""


def repair_dangling_sentence(
    text: str,
    fallback_title: str = "",
    *,
    drop_if_unrepairable: bool = False,
) -> str:
    """Detects and repairs truncated sentences ending with dangling currencies, prepositions, or incomplete thoughts."""
    if not text:
        return ""
    t = str(text).strip()
    clean_tail = re.sub(r"[.!?।…|\s]+$", "", t).strip()
    if DANGLING_SENTENCE_ENDINGS.search(clean_tail):
        # 1. Prefer clipping back to an earlier complete sentence so we never chop "500 करोड़ रुपये" into "500 करोड़".
        complete_prefix = _last_complete_sentence(t)
        if complete_prefix:
            return complete_prefix
        if fallback_title and len(fallback_title) > 25:
            # Reconstruct from complete title
            clean_fb = re.sub(r"^\s*(?:>>|>)\s*", "", fallback_title).strip()
            return clean_fb.rstrip(".") + "."
        # 2. If dangling tail ends with an incomplete phrase without a complete earlier sentence, strip carefully
        # ONLY if doing so doesn't sever a numeric quantity from its currency unit (e.g. "500 करोड़").
        repaired = DANGLING_SENTENCE_ENDINGS.sub("", clean_tail).strip()
        while repaired and _TRAILING_ORPHAN_HI.search(repaired):
            next_rep = _TRAILING_ORPHAN_HI.sub("", repaired).strip()
            if next_rep == repaired:
                break
            repaired = next_rep
        if len(repaired) > 25 and not re.search(r"\d\s*(?:लाख|करोड़|हजार|अरब|million|billion|crore|lakh)?$", repaired, re.I):
            end_mark = "।" if re.search(r"[\u0900-\u097F]", repaired) else "."
            return repaired.rstrip(".,।") + end_mark
        if fallback_title:
            return fallback_title.strip()
        if drop_if_unrepairable:
            return ""
    return t


def clip_dangling(text: str, fallback_title: str = "") -> str:
    """Never print a sentence that stops mid-thought: cut at the last complete
    sentence when that keeps most of the line, otherwise repair or mark the truncation."""
    t = (text or "").strip()
    if not t:
        return ""
    t = repair_dangling_sentence(t, fallback_title)
    if len(t) < 40 or t.endswith(_TERMINALS):
        return t
    idx = t.rfind(". ")
    if idx >= 0.6 * len(t):
        return t[:idx + 1].strip()
    return t + "…"


def clean_line(line: str) -> str:
    """One key point / fact line: drop paywall sentences, glue-off source
    domains, and repair source-side mid-sentence clips."""
    t = (line or "").strip()
    if not t:
        return ""
    t = " ".join(s.strip() for s in re.split(r"(?<=[.!?।])\s+", t) if not PAYWALL_RE.search(s)).strip()
    t = TRAILING_SOURCE_RE.sub("", t).strip()
    return clip_dangling(t)


def sanitize_lines(lines: List[str], title: str = "", source: str = "") -> List[str]:
    """Key points list: drop paywall/credit/bare-source lines and near-duplicate
    headline echoes, clean the rest, keep order."""
    title_norm = re.sub(r"\s+", " ", (title or "").strip().lower())
    source_norm = re.sub(r"\s+", " ", (source or "").strip().lower())
    out: List[str] = []
    echo_fallback = ""
    for raw in lines or []:
        line = clean_line(raw)
        if not line or PAYWALL_RE.search(line) or BARE_SOURCE_RE.search(line):
            continue
        low = re.sub(r"\s+", " ", line.lower())
        if source_norm and (low == source_norm or (source_norm in low and len(low) - len(source_norm) < 6)):
            continue  # the line is only the source's own name
        if title_norm and (low == title_norm or (low.startswith(title_norm) and len(low) - len(title_norm) < 12)):
            # headline echo: last resort only, and never with a truncation mark
            echo_fallback = echo_fallback or line.rstrip("…").strip()
            continue
        if line not in out:
            out.append(line)
    # A stub story whose only "key point" is its own headline keeps it (cleaned)
    # instead of an empty list - downstream stages require at least one line.
    return out or ([echo_fallback] if echo_fallback else [])


def sanitize_raw_facts(text: str) -> str:
    """Raw evidence blob: remove paywall sentences and bare credits so they can
    never become a summary, key point, Static GK or exam fact."""
    t = (text or "").strip()
    if not t:
        return t
    kept = [s.strip() for s in re.split(r"(?<=[.!?।])\s+", t)
            if s.strip() and not PAYWALL_RE.search(s) and not BARE_SOURCE_RE.search(s.strip())]
    return " ".join(kept)


def raw_word_count(item) -> int:
    """English body words available from the source (headline excluded)."""
    facts = sanitize_raw_facts(item.get("raw_facts") or "") if isinstance(item, dict) else ""
    return len(facts.split())


def is_shallow(item) -> bool:
    return raw_word_count(item) < SHALLOW_RAW_WORDS


MAJOR_INDIAN_CITIES = (
    "Bengaluru|Bangalore|New Delhi|Delhi|Mumbai|Chennai|Kolkata|Calcutta|"
    "Hyderabad|Ahmedabad|Pune|Lucknow|Jaipur|Bhopal|Patna|Chandigarh|Shimla|"
    "Srinagar|Guwahati|Dehradun|Ranchi|Raipur|Bhubaneswar|Thiruvananthapuram|"
    "Gandhinagar|Agartala|Aizawl|Imphal|Kohima|Shillong|Gangtok|Itanagar"
)

DATELINE_SUB_RE = re.compile(
    r"\b(?:Updated|Published|Posted|Reported)\s*[-–—:]*\s*"
    r"(?:(?:January|February|March|April|May|June|July|August|September|October|November|December|"
    r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}|"
    r"\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|"
    r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec),?\s+\d{4})\b"
    r"(?:\s*\d{1,2}:\d{2}\s*(?:am|pm)?\s*(?:IST|UTC|GMT)?)?"
    r"(?:\s*[-–—:]\s*(?:" + MAJOR_INDIAN_CITIES + r")\b)?"
    r"\s*[-–—:]*\s*",
    re.I
)

DATELINE_RE = re.compile(
    r"^(?:(?:Updated|Published|Posted|Reported)\s*[-–—:]*\s*)?"
    r"(?:(?:January|February|March|April|May|June|July|August|September|October|November|December|"
    r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}|"
    r"\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|"
    r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec),?\s+\d{4})\s*"
    r"(?:\d{1,2}:\d{2}\s*(?:am|pm)?\s*(?:IST|UTC|GMT)?)?\s*"
    r"(?:[-–—:]\s*(?:" + MAJOR_INDIAN_CITIES + r")\b\s*)?",
    re.I
)

TRAILING_CONCLUSION_RE = re.compile(
    r"\s*(?:Therefore|Hence|Thus|As a result|So),?\s+(?:Option\s+[A-E]|.*?\s+is\s+the\s+correct\s+answer)[.!]?\s*$|"
    r"\s*(?:अतः|इसलिए|इस प्रकार),?\s+(?:विकल्प\s+[A-E]|.*?\s+सही\s+उत्तर\s+है)[.।]?\s*$",
    re.I
)


def clean_explanation_text(text: str) -> str:
    """Scrub news timestamps, datelines, raw URLs and empty conclusion boilerplate."""
    if not text or not isinstance(text, str):
        return ""
    t = text.strip()
    # Strip explicit datelines anywhere in text (e.g. after 'Exam Fact – ')
    t = DATELINE_SUB_RE.sub("", t).strip()
    t = DATELINE_RE.sub("", t).strip()
    t = re.sub(
        r"^(?:Updated|Published|Posted|Reported)\s*[-–—:]*\s*[A-Za-z]+\s+\d{1,2},\s*\d{4}\s*",
        "", t, flags=re.I
    ).strip()
    t = re.sub(r"^[-–—:]\s*", "", t).strip()
    t = re.sub(r"–\s*–", "–", t).strip()
    t = TRAILING_CONCLUSION_RE.sub("", t).strip()
    t = re.sub(r"https?://\S+|www\.\S+", "", t).strip()
    return t

