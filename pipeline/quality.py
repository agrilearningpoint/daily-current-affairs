"""Content-quality gates applied while candidates are collected.

The 2026-10-16 dry run (run 38896579675) produced a 28-item edition in which 19
"selected" items were site chrome rather than news: ``Hyperlink Policy``,
``Accessibility Help``, ``Untitled - ICAR…``, ``POLICY COORDINATION - Department
of Agriculture & Farmers Welfare``, ``Press Releases - Reserve Bank of India``,
``ECI Candidate Affidavit``, ``F. No. BEDF/… NOTICE INVITING TENDER`` and so on.

Those pages reach the pipeline because Google-News-style discovery feeds
republish them as ``<Title> - <Publisher>`` entries and because official listing
pages expose section labels as anchors. They then survive verification, score
highly on the domain boosts (Agriculture/Banking +25) and crowd real news out of
the edition.

Every rule below is derived from a title observed in that run, so the filter
stays narrow: it drops navigation/policy/section chrome, not headlines.

Kill switch: ``ALP_CHROME_FILTER=0`` disables the filter.
"""
from __future__ import annotations

import os
import re
from typing import Optional

FILTER_ENV = "ALP_CHROME_FILTER"

# Exact labels (normalised: lowercase, punctuation collapsed to single spaces).
NAV_LABELS = frozenset({
    "about", "about us", "archives", "archive", "accessibility",
    "accessibility help", "accessibility statement", "careers", "circulars",
    "contact", "contact us", "copyright policy", "disclaimer", "download",
    "downloads", "faq", "faqs", "feedback", "help", "home", "hyperlink policy",
    "jump to main content", "login", "media gallery", "notifications",
    "photo gallery", "press release", "press releases", "privacy policy",
    "publications", "recruitment", "register", "reports", "right to information",
    "rti", "rti act", "screen reader access", "site map", "sitemap",
    "skip to main content", "statistics", "subscribe", "tender", "tenders",
    "terms and conditions", "terms of use", "untitled", "vacancies",
    "video gallery", "web information manager", "website policies",
    "whats new",
})

# Leading phrases that only ever label a document, never a headline.
NAV_PREFIXES = (
    "about the department", "about the ministry", "about the organisation",
    "about the organization", "candidate affidavit", "notice inviting tender",
    "official website", "press release",
)

# Phrases that identify a page as documentation wherever they appear.
NAV_CONTAINS = (
    "accessibility help", "candidate affidavit", "hyperlink policy",
    "nivachan sadan", "notice inviting tender", "official website",
    "web information manager",
)

# Trailing fragments that mean "this title is just the publisher's own name".
_SITE_TAILS = frozenset({
    "", "government of india", "govt of india", "india", "official",
    "official website", "official website of india",
})

# "…Ashoka Road, New Delhi-110001 No.23/2026-ERS" — an office address, not news.
_ADDRESS_RE = re.compile(
    r"\b(?:road|marg|sadan|bhawan|bhavan|street|lane)\b[^.]{0,60}\b\d{6}\b",
    re.IGNORECASE,
)

_MAX_PUBLISHER_WORDS = 8
_MAX_PUBLISHER_CHARS = 60
# "About Economics and Statistics (Establishment)" is an information page. Idioms
# such as "About time…" and sentences such as "About 300 farmers…" are not.
_ABOUT_STOPWORDS = frozenset({
    "how", "that", "the", "these", "this", "those", "time", "what", "when", "who", "why",
})
_MAX_ABOUT_WORDS = 5

_MAX_LABEL_WORDS = 4
_MAX_LABEL_CHARS = 40


def chrome_filter_enabled() -> bool:
    """Filter is on unless explicitly switched off (``ALP_CHROME_FILTER=0``)."""
    return os.getenv(FILTER_ENV, "1").strip().lower() not in {"0", "false", "no", "off"}


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").casefold()).strip()


def split_publisher(title: str) -> tuple[str, str]:
    """Split a Google-News-style ``<Title> - <Publisher>`` entry.

    Only splits when the trailing part really looks like a publisher name (short,
    no digits, no sentence punctuation) so headlines that legitimately contain a
    dash - e.g. ``Wheat MSP - up Rs 150`` - stay intact.
    """
    text = clean_spaces(title)
    for separator in (" - ", " | ", "|", " – ", " — "):
        if separator not in text:
            continue
        head, _, tail = text.rpartition(separator)
        head, tail = head.strip(), tail.strip()
        if len(head) < 8 or not tail or len(tail) > _MAX_PUBLISHER_CHARS:
            continue
        if len(tail.split()) > _MAX_PUBLISHER_WORDS:
            continue
        if any(char.isdigit() for char in tail) or tail[-1] in ".!?":
            continue
        return head, tail
    return text, ""


def clean_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def _looks_like_section_label(title: str) -> bool:
    """ALL-CAPS short labels such as ``CROP INSURANCE DIVISION``/``HORTICULTURE``."""
    stripped = clean_spaces(title)
    if not stripped or len(stripped) > _MAX_LABEL_CHARS:
        return False
    if any(char.islower() for char in stripped):
        return False
    if any(char.isdigit() for char in stripped):
        return False
    return len(stripped.split()) <= _MAX_LABEL_WORDS


def _looks_like_about_page(title: str) -> bool:
    """``About <something>`` information pages, but not headlines that start with it."""
    normalized = _normalize(title)
    if not normalized.startswith("about "):
        return False
    remainder = normalized[len("about "):]
    words = remainder.split()
    if not words or len(words) > _MAX_ABOUT_WORDS:
        return False
    if any(char.isdigit() for char in remainder) or words[0] in _ABOUT_STOPWORDS:
        return False
    return True


def _is_self_link(title: str, source_name: str) -> bool:
    """``Competition Commission of India, Government of India`` != a headline."""
    normalized, site = _normalize(title), _normalize(source_name)
    if not normalized or not site:
        return False
    if normalized == site:
        return True
    if normalized.startswith(site):
        return normalized[len(site):].strip() in _SITE_TAILS
    return False


def reject_reason(title: str, source_name: str = "") -> Optional[str]:
    """Return why ``title`` is site chrome, or ``None`` when it looks like news."""
    if not chrome_filter_enabled():
        return None
    text = clean_spaces(title)
    if not text:
        return "empty"
    core, _publisher = split_publisher(text)
    for candidate in (text, core):
        normalized = _normalize(candidate)
        if not normalized:
            return "publisher-only"
        if normalized in NAV_LABELS:
            return "nav-label"
        if normalized.startswith(NAV_PREFIXES):
            return "nav-prefix"
        if any(phrase in normalized for phrase in NAV_CONTAINS):
            return "document-page"
        if _looks_like_section_label(candidate):
            return "section-label"
        if _looks_like_about_page(candidate):
            return "about-page"
    if _is_self_link(core, source_name) or _is_self_link(text, source_name):
        return "self-link"
    if _ADDRESS_RE.search(text):
        return "address"
    return None


def is_chrome_title(title: str, source_name: str = "") -> bool:
    """Convenience wrapper for callers that only need the yes/no answer."""
    return reject_reason(title, source_name) is not None
