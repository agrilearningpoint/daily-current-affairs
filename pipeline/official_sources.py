# -*- coding: utf-8 -*-
"""Official-origin and trusted-publisher detection for aggregator (Google News) items.

Run 41437192142 (2026-11-02) collected 98 PIB releases through the
``site:pib.gov.in`` Google News query.  They were registered under the generic
"Google News Search" aggregator source (level 5, tier 3, publisher
news.google.com), so fact verification found no provenance and rejected all of
them — the edition had no PIB story at all while political sound-bites made the
cut.  These helpers recover the real origin of such items:

* ``official_origin(article)`` -> official domain (``pib.gov.in``, ``mea.gov.in``,
  ``rbi.org.in`` ...) when the link, publisher, Google News ``site:`` query or the
  " - <publisher>" title suffix proves the item comes from an official source;
* ``trusted_publisher(article)`` -> canonical name of a national newsroom
  (Reuters, The Hindu, ...) for Google News top-story items;
* ``strip_publisher_suffix(title)`` removes the Google News " - Publisher" tail.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

# Official domains -> display name (used for source_name of recovered items).
OFFICIAL_DOMAINS: Dict[str, str] = {
    "pib.gov.in": "PIB",
    "pmindia.gov.in": "Prime Minister of India",
    "pmo.gov.in": "Prime Minister's Office",
    "presidentofindia.gov.in": "President of India",
    "mea.gov.in": "Ministry of External Affairs",
    "rbi.org.in": "RBI",
    "isro.gov.in": "ISRO",
    "imd.gov.in": "India Meteorological Department",
    "mausam.imd.gov.in": "India Meteorological Department",
    "sebi.gov.in": "SEBI",
    "drdo.gov.in": "DRDO",
    "icar.org.in": "ICAR",
    "icar.gov.in": "ICAR",
    "nabard.org": "NABARD",
    "eci.gov.in": "Election Commission of India",
    "mospi.gov.in": "MoSPI",
    "agriwelfare.gov.in": "Ministry of Agriculture",
    "india.gov.in": "India.gov.in",
    "mygov.in": "MyGov India",
    "ddnews.gov.in": "DD News",
    "newsonair.gov.in": "All India Radio News",
    "un.org": "United Nations",
    "who.int": "WHO",
    "worldbank.org": "World Bank",
    "imf.org": "IMF",
    "wto.org": "WTO",
    "fao.org": "FAO",
}
# Primary national sources that must be preferred / must-include in selection.
MUST_INCLUDE_DOMAINS = {"pib.gov.in", "pmindia.gov.in", "pmo.gov.in", "mea.gov.in", "rbi.org.in",
                        "isro.gov.in", "imd.gov.in", "mausam.imd.gov.in", "sebi.gov.in",
                        "presidentofindia.gov.in"}
MUST_INCLUDE_NAMES = {"PIB", "Press Information Bureau", "PIB — Press Information Bureau",
                      "Prime Minister of India", "Prime Minister's Office", "PMO",
                      "Ministry of External Affairs", "MEA", "RBI", "Reserve Bank of India",
                      "ISRO", "India Meteorological Department", "IMD", "SEBI", "President of India"}
_OFFICIAL_SUFFIXES = (".gov.in", ".nic.in")

# Google News "<headline> - <Publisher>" -> canonical trusted newsroom name.
TRUSTED_PUBLISHERS: Dict[str, str] = {
    "reuters": "Reuters", "the hindu": "The Hindu", "thehindu": "The Hindu",
    "the indian express": "The Indian Express", "indian express": "The Indian Express",
    "hindustan times": "Hindustan Times", "the times of india": "The Times of India",
    "times of india": "The Times of India", "ndtv": "NDTV", "india today": "India Today",
    "business standard": "Business Standard", "mint": "Mint", "livemint": "Mint",
    "the economic times": "Economic Times", "economic times": "Economic Times",
    "businessline": "BusinessLine", "the hindu businessline": "BusinessLine",
    "dd news": "DD News", "dd india": "DD News", "all india radio": "All India Radio News",
    "pti": "PTI", "press trust of india": "PTI", "ani": "ANI", "ani news": "ANI",
    "deccan herald": "Deccan Herald", "the tribune": "The Tribune", "the print": "ThePrint",
    "theprint": "ThePrint", "down to earth": "Down To Earth", "bbc": "BBC", "bbc news": "BBC",
    "al jazeera": "Al Jazeera", "the new york times": "The New York Times",
    "financial express": "Financial Express", "the financial express": "Financial Express",
    "moneycontrol": "Moneycontrol", "news18": "News18", "firstpost": "Firstpost",
    "live law": "LiveLaw", "livelaw": "LiveLaw", "bar and bench": "Bar and Bench",
}

_SUFFIX_RE = re.compile(r"\s+[-–—|]\s+([^-–—|]{2,60})\s*$")
_DOMAIN_RE = re.compile(r"^(?:www\.)?([a-z0-9-]+(?:\.[a-z0-9-]+)+)$", re.I)


def _host(url: str) -> str:
    try:
        return (urlparse(url or "").hostname or "").lower().removeprefix("www.")
    except Exception:
        return ""


def _official_domain(host: str) -> Optional[str]:
    host = (host or "").lower().removeprefix("www.")
    if not host:
        return None
    for dom in OFFICIAL_DOMAINS:
        if host == dom or host.endswith("." + dom):
            return dom
    if host.endswith(_OFFICIAL_SUFFIXES):
        return host
    return None


def _site_query_domain(feed_url: str) -> Optional[str]:
    """``https://news.google.com/rss/search?q=site:pib.gov.in when:1d`` -> ``pib.gov.in``."""
    try:
        u = urlparse(feed_url or "")
        if "news.google." not in (u.hostname or ""):
            return None
        q = " ".join(parse_qs(u.query).get("q", []))
    except Exception:
        return None
    m = re.search(r"site:([A-Za-z0-9.-]+)", q)
    return m.group(1).lower().removeprefix("www.") if m else None


def title_suffix(title: str) -> str:
    m = _SUFFIX_RE.search(title or "")
    return m.group(1).strip() if m else ""


def official_origin(article: Dict[str, Any]) -> Optional[str]:
    """Official domain the item really comes from, or None."""
    for url in (article.get("link"), article.get("source_url"), article.get("publisher_url")):
        dom = _official_domain(_host(str(url or "")))
        if dom:
            return dom
    suffix = title_suffix(str(article.get("title") or article.get("headline_en") or ""))
    m = _DOMAIN_RE.match(suffix)
    if m:
        dom = _official_domain(m.group(1))
        if dom:
            return dom
    site = _site_query_domain(str(article.get("source_feed") or ""))
    if site:
        dom = _official_domain(site)
        # A site: query only returns pages of that site; require the title suffix
        # to agree when it names a domain, so a mismatching suffix never upgrades.
        if dom and (not m or _official_domain(m.group(1)) == dom):
            return dom
    return None


def trusted_publisher(article: Dict[str, Any]) -> Optional[str]:
    """Canonical trusted newsroom named by a Google News title suffix, or None."""
    link_host = _host(str(article.get("link") or ""))
    if "news.google." not in link_host and "news.google." not in _host(str(article.get("source_feed") or "")):
        return None
    suffix = title_suffix(str(article.get("title") or "")).lower().strip(" .")
    return TRUSTED_PUBLISHERS.get(suffix)


def strip_publisher_suffix(title: str) -> str:
    """Drop a Google News " - Publisher" tail when it names a domain or a known newsroom."""
    t = (title or "").strip()
    suf = title_suffix(t)
    if not suf:
        return t
    if _DOMAIN_RE.match(suf) or suf.lower().strip(" .") in TRUSTED_PUBLISHERS:
        return _SUFFIX_RE.sub("", t).strip()
    return t


def is_must_include(item: Dict[str, Any]) -> bool:
    """True for items from PIB / PMO / MEA / RBI / ISRO / IMD / SEBI / President."""
    dom = str(item.get("official_domain") or "") or (official_origin(item) or "")
    if dom in MUST_INCLUDE_DOMAINS:
        return True
    return str(item.get("source_name") or "") in MUST_INCLUDE_NAMES
