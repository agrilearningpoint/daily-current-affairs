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
from urllib.parse import urlsplit

FILTER_ENV = "ALP_CHROME_FILTER"

# Exact labels (normalised: lowercase, punctuation collapsed to single spaces).
NAV_LABELS = frozenset({
    "about", "about us", "archives", "archive", "accessibility", "documents",
    "accessibility help", "accessibility statement", "careers", "circulars",
    "contact", "contact us", "copyright policy", "disclaimer", "download",
    "downloads", "faq", "faqs", "feedback", "help", "home", "hyperlink policy",
    "jump to main content", "login", "media gallery", "notifications",
    "photo gallery", "photos", "press release", "press releases", "privacy policy",
    "publications", "recruitment", "register", "reports", "right to information",
    "forms", "gallery", "guidelines", "important links", "links", "notices",
    "orders", "other links", "programmes", "quick links", "related links",
    "schemes", "useful links", "videos",
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
    "accessibility help", "candidate affidavit", "detailed forecast and warnings",
    "hyperlink policy", "nivachan sadan", "notice inviting tender",
    "official website", "synoptic observations", "web information manager",
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
_MIN_TITLE_CHARS = 12

# ALL-CAPS titles ending in one of these are section/division names, never
# headlines - e.g. "AGRICULTURE TRADE POLICY, PROMOTION AND LOGISTICS
# DEVELOPMENT DIVISION".
SECTION_SUFFIXES = frozenset({
    "authority", "board", "cell", "commission", "corporation", "council",
    "department", "directorate", "division", "ministry", "section", "wing",
})

# A title that is only an organisation name ("Agricultural and Processed Food
# Products Export Development Authority - APEDA") is a site listing, not news -
# unless it also carries a news verb.
ORG_SUFFIXES = frozenset({
    "agency", "association", "authority", "bank", "board", "bureau",
    "commission", "corporation", "council", "department", "development",
    "directorate", "division", "federation", "institute", "limited", "ltd",
    "ministry", "organisation", "organization", "society", "trust", "university",
})
_ORG_STOPWORDS = frozenset({"&", "and", "at", "for", "in", "of", "on", "the", "to"})
NEWS_VERBS = frozenset({
    "announces", "announced", "approves", "approved", "asks", "bans", "banned",
    "clears", "cleared", "cuts", "extends", "flags", "gets", "holds", "inks",
    "issues", "issued", "launches", "launched", "notifies", "notified", "plans",
    "raises", "releases", "released", "rises", "says", "seeks", "sets", "signs",
    "starts", "wins",
})

# Exactly these paths are a site's landing page: a feed entry pointing there is
# the site itself, not an article (e.g. title "- Reserve Bank of India").
# Non-editorial material that official sites publish on the same feeds as news:
# recruitment notices, tenders and routine periodic bulletins. The 2026-10-15
# edition carried a bank pharmacist vacancy and a daily agromet bulletin, which
# is what these two patterns exist to keep out.
NOTICE_RE = re.compile(
    r"\b(?:engagement of\b[^|]{0,90}\bon (?:contract|contractual|deputation|ad-?hoc|consolidated)"
    r"|walk-?in interview"
    r"|invites? applications?"
    r"|applications? (?:are )?invited"
    r"|advt\.?\s*no\.?"
    r"|advertisement no\.?"
    r"|notice inviting (?:tender|quotation|bid|expression)"
    r"|last date (?:for|to) appl(?:y|ication))\b", re.IGNORECASE)
ROUTINE_RE = re.compile(
    r"\b(?:agromet advisory (?:service )?bulletin"
    r"|agromet bulletin"
    r"|(?:daily|weekly|monthly|fortnightly) (?:weather|rainfall|market|price|arrival) "
    r"(?:bulletin|report|summary|advisory))\b", re.IGNORECASE)
MARKUP_RE = re.compile(r"[<>]")

_LANDING_PATHS = frozenset({
    "", "/", "/default.aspx", "/en", "/en/", "/english", "/english/", "/home",
    "/home.aspx", "/index.aspx", "/index.htm", "/index.html", "/index.php",
    "/index.shtml",
})


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
    text = clean_spaces(title).strip("-|–— ")
    for separator in (" - ", " | ", "|", " – ", " — "):
        if separator not in text:
            continue
        head, _, tail = text.rpartition(separator)
        head, tail = head.strip(), tail.strip()
        if len(head) < 4 or not tail or len(tail) > _MAX_PUBLISHER_CHARS:
            continue
        if len(tail.split()) > _MAX_PUBLISHER_WORDS:
            continue
        if any(char.isdigit() for char in tail) or tail[-1] in ".!?":
            continue
        return head, tail
    return text, ""


def clean_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def _ends_with_section_suffix(title: str) -> bool:
    """``CROP INSURANCE DIVISION`` / ``Administration Division``: a section name.

    ALL-CAPS labels are rejected however long they are; title-case names only
    when they are short (<= 3 words), so a headline such as "Cabinet approves
    new division for farmers" is never mistaken for one.
    """
    stripped = clean_spaces(title)
    if not stripped:
        return False
    words = [word for word in stripped.replace(",", " ").split() if word]
    if not words or words[-1].casefold().strip(".?") not in SECTION_SUFFIXES:
        return False
    if any(char.islower() for char in stripped):
        return len(words) <= 3
    return True


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


def _looks_like_org_name(title: str) -> bool:
    """``…Export Development Authority`` is a site listing, not a story.

    Three signals must line up: the title ends in an organisation noun, it reads
    as a proper noun (>= 70 % of its content words capitalised) and it carries no
    news verb and no digits. A headline such as "Government notifies new Food
    Safety Authority" or "RBI imposes penalty on Bank of Baroda" fails at least
    two of them.
    """
    words = [word.strip(".,:;()&") for word in clean_spaces(title).split()]
    words = [word for word in words if word]
    if len(words) < 4 or any(char.isdigit() for char in title):
        return False
    lowered = [word.casefold() for word in words]
    if any(word in NEWS_VERBS for word in lowered):
        return False
    if lowered[-1] not in ORG_SUFFIXES:
        return False
    content = [word for word in words if word.casefold() not in _ORG_STOPWORDS]
    if not content:
        return False
    capitalised = sum(1 for word in content if word[:1].isupper())
    return capitalised / len(content) >= 0.7


def _repeats_itself(title: str) -> bool:
    """``…Authority - …Authority``: the same name twice is not a headline."""
    tokens = _normalize(title).split()
    if len(tokens) < 6:
        return False
    for size in (5, 4, 3):
        head = tokens[:size]
        for start in range(1, len(tokens) - size + 1):
            if tokens[start:start + size] == head:
                return True
    return False


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
    if text[0] in "-|–—":
        return "publisher-only"  # Google News renders a headline-less page this way
    if len(text) < _MIN_TITLE_CHARS:
        return "too-short"
    core, _publisher = split_publisher(text)
    for candidate in (text, core):
        normalized = _normalize(candidate)
        if not normalized:
            return "publisher-only"
        if _ends_with_section_suffix(candidate):
            return "section-label"
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
        if _looks_like_org_name(candidate):
            return "org-name"
        if _repeats_itself(candidate):
            return "duplicate-name"
    _head, publisher = split_publisher(text)
    if publisher and _normalize(_head) == _normalize(publisher):
        return "duplicate-name"  # "…Authority - …Authority": the site listed itself
    if _is_self_link(core, source_name) or _is_self_link(text, source_name):
        return "self-link"
    if _ADDRESS_RE.search(text):
        return "address"
    if NOTICE_RE.search(text):
        return "notice"
    if ROUTINE_RE.search(text):
        return "routine-bulletin"
    if MARKUP_RE.search(text):
        return "markup-leak"  # HTML fragment leaked into the headline field
    return None


def is_landing_link(url: str) -> bool:
    """True when ``url`` is a site root/index page rather than an article."""
    if not url:
        return False
    path = urlsplit(url).path or ""
    if path.endswith("/") and len(path) > 1:
        path = path.rstrip("/")
    return path.casefold() in _LANDING_PATHS


def is_chrome_title(title: str, source_name: str = "") -> bool:
    """Convenience wrapper for callers that only need the yes/no answer."""
    return reject_reason(title, source_name) is not None
