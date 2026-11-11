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


def clip_dangling(text: str) -> str:
    """Never print a sentence that stops mid-thought: cut at the last complete
    sentence when that keeps most of the line, otherwise mark the truncation."""
    t = (text or "").strip()
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
