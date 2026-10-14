# -*- coding: utf-8 -*-
"""Feed routes and Google News discovery mappings for Agri Learning Point.

VERIFIED_RSS is intentionally conservative: these are declared candidate feeds
that the collector can try directly. Network reachability and parseability vary
by deployment, so health must be measured at runtime; this file does not claim
that every endpoint is currently live.

A Google News result is discovery metadata, not a primary-source verification.
"""
from __future__ import annotations
from urllib.parse import quote

# Tuple contract required by pipeline.collector:
# (display_name, feed_url, tier, category_hint)
# tier1 means primary/official publisher feed; tier2 means editorial discovery.
VERIFIED_RSS = [
    ("ICAR", "https://icar.org.in/rss.xml", "tier1", "agriculture"),
    ("WHO News", "https://www.who.int/rss-feeds/news-english.xml", "tier1", "health"),
    ("The Hindu National", "https://www.thehindu.com/news/national/feeder/default.rss", "tier2", "national"),
    ("Indian Express", "https://indianexpress.com/feed/", "tier2", "national"),
]

# Map source domains to intended authority classes for discovery routing.
# The collector must still validate the final article URL and its provenance.
GOOGLE_NEWS_SITES = {
    # Official / primary domains
    "pib.gov.in": "tier1",
    "agriwelfare.gov.in": "tier1",
    "icar.org.in": "tier1",
    "iari.res.in": "tier1",
    "rbi.org.in": "tier1",
    "nabard.org": "tier1",
    "sebi.gov.in": "tier1",
    "niti.gov.in": "tier1",
    "mospi.gov.in": "tier1",
    "mea.gov.in": "tier1",
    "mausam.imd.gov.in": "tier1",
    "dahd.gov.in": "tier1",
    "dof.gov.in": "tier1",
    "apeda.gov.in": "tier1",
    "dare.gov.in": "tier1",
    "nhb.gov.in": "tier1",
    "fssai.gov.in": "tier1",
    "icfre.gov.in": "tier1",
    "cacp.dacnet.nic.in": "tier1",
    "mofpi.gov.in": "tier1",
    "moef.gov.in": "tier1",
    "npci.org.in": "tier1",
    "pfrda.org.in": "tier1",
    "irdai.gov.in": "tier1",
    "ifsca.gov.in": "tier1",
    "financialservices.gov.in": "tier1",
    "indiabudget.gov.in": "tier1",
    "gstcouncil.gov.in": "tier1",
    "cci.gov.in": "tier1",
    "bulletin.rbi.org.in": "tier1",
    "india.gov.in": "tier1",
    "pmindia.gov.in": "tier1",
    "cabsec.gov.in": "tier1",
    "mygov.in": "tier1",
    "rural.gov.in": "tier1",
    "cooperation.gov.in": "tier1",
    "dst.gov.in": "tier1",
    "dbtindia.gov.in": "tier1",
    "drdo.gov.in": "tier1",
    "cpcb.nic.in": "tier1",
    "education.gov.in": "tier1",
    "ugc.gov.in": "tier1",
    "nta.ac.in": "tier1",
    "mod.gov.in": "tier1",
    "presidentofindia.gov.in": "tier1",
    "eci.gov.in": "tier1",
    "upsc.gov.in": "tier1",
    "fao.org": "tier1",
    "worldbank.org": "tier1",
    "imf.org": "tier1",
    "wto.org": "tier1",
    "un.org": "tier1",
    "unfccc.int": "tier1",
    "iea.org": "tier1",
    "isro.gov.in": "tier1",
    "who.int": "tier1",
    # Editorial discovery only; never treat as primary verification
    "reuters.com": "tier2",
    "thehindu.com": "tier2",
    "indianexpress.com": "tier2",
    "business-standard.com": "tier2",
    "livemint.com": "tier2",
    "economictimes.indiatimes.com": "tier2",
}


def gnews_url(domain: str, when: str = "2d") -> str:
    """Return a Google News RSS site-search URL for a hostname or query.

    Pass only a trusted configured domain; don't pass a full article URL.
    """
    domain = str(domain or "").strip().lower()
    if not domain:
        raise ValueError("domain must be a non-empty hostname or search query")
    when = str(when or "2d").strip().lower()
    if when not in {"1d", "2d", "3d", "5d", "7d", "14d", "30d"}:
        when = "2d"
    query = quote(f"site:{domain} when:{when}", safe="")
    return f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
