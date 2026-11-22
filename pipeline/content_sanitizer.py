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
    r"लागत\s+लगभग\s+रुपये?|लगभग\s+रुपये?|रुपये\s*|के\s+लिए\s*|में\s*|को\s*|और\s*)$",
    re.IGNORECASE
)


def repair_dangling_sentence(text: str, fallback_title: str = "") -> str:
    """Detects and repairs truncated sentences ending with dangling currencies, prepositions, or incomplete thoughts."""
    if not text:
        return ""
    t = str(text).strip()
    clean_tail = re.sub(r"[.!?।|\s]+$", "", t).strip()
    if DANGLING_SENTENCE_ENDINGS.search(clean_tail):
        if fallback_title and len(fallback_title) > 25:
            # Reconstruct from complete title
            clean_fb = re.sub(r"^\s*(?:>>|>)\s*", "", fallback_title).strip()
            return clean_fb.rstrip(".") + "."
        repaired = DANGLING_SENTENCE_ENDINGS.sub("", clean_tail).strip()
        if len(repaired) > 25:
            return repaired.rstrip(".,") + "."
        elif fallback_title:
            return fallback_title.strip()
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


DATELINE_RE = re.compile(
    r"^(?:Updated|Published|Posted|Reported)?\s*[-–:]*\s*"
    r"(?:[A-Za-z]+\s+\d{1,2},?\s+\d{4}|\d{1,2}\s+[A-Za-z]+,?\s+\d{4})?\s*"
    r"(?:\d{1,2}:\d{2}\s*(?:am|pm)?\s*(?:IST|UTC|GMT)?)?\s*[-–:]*\s*"
    r"(?:[A-Za-z\s]+[-–:])?\s*",
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
    # Strip explicit datelines like 'Updated - November 17, 2026 12:59 am IST - Bengaluru'
    t = re.sub(
        r"^(?:Updated|Published)?\s*[-–:]*\s*[A-Za-z]+\s+\d{1,2},\s*\d{4}\s*\d{1,2}:\d{2}\s*(?:am|pm)\s*IST\s*[-–:]*\s*[A-Za-z]+\s*",
        "", t, flags=re.I
    ).strip()
    t = DATELINE_RE.sub("", t).strip()
    t = TRAILING_CONCLUSION_RE.sub("", t).strip()
    t = re.sub(r"https?://\S+|www\.\S+", "", t).strip()
    return t

