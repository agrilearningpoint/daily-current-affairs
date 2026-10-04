# -*- coding: utf-8 -*-
"""
AGRI LEARNING POINT — VERIFIED WORKING FEEDS (live-tested 2026-10-04)
Only feeds that returned HTTP 200 AND parsed with real entries are listed here.
Collector uses these FIRST (fast, reliable), then falls back to HTML scraping of config/sources.py sites.

Notes from live verification:
- ICAR rss.xml works but titles are HINDI -> collector translates via MINI_DICT pipeline.
- PIB has NO working RSS feed (RssMain.aspx returns HTML) -> must use HTML adapter.
- UN News / FAO / IMF / UNEP / ILO / IEA / WTO block bots (403/404) -> Google News site-search RSS is the reliable discovery route; Tier-1 verification still happens against official pages where possible.
- RBI / NABARD / MoFPI / DBT / PRS have no parseable public RSS -> HTML adapters.
"""

VERIFIED_RSS = [
    # name                              url                                                            tier   category hint
    ("ICAR",            "https://icar.org.in/rss.xml",                                              "tier1", "agriculture"),
    ("WHO News",        "https://www.who.int/rss-feeds/news-english.xml",                           "tier1", "national"),
    ("The Hindu National","https://www.thehindu.com/news/national/feeder/default.rss",              "tier2", "national"),
]
# NITI rss.xml now declared per-source in sources.py (rss key) — no duplicate needed here.

# Google News site-search RSS — verified pattern, used for sources whose own feeds are blocked/absent.
# Query template: https://news.google.com/rss/search?q=site:{domain} when:2d&hl=en-IN&gl=IN&ceid=IN:en
GOOGLE_NEWS_SITES = {
    # Tier-1 official bodies without usable native RSS (bot-blocked or none)
    "pib.gov.in":            "tier1",
    "rbi.org.in":            "tier1",
    "nabard.org":            "tier1",
    "sebi.gov.in":           "tier1",
    "fao.org":               "tier1",
    "imf.org":               "tier1",
    "worldbank.org":         "tier1",
    "wto.org":               "tier1",
    "unep.org":              "tier1",
    "ilo.org":               "tier1",
    "unesco.org":            "tier1",
    "iea.org":               "tier1",
    "un.org":                "tier1",
    "presidentofindia.gov.in":"tier1",
    "pmindia.gov.in":        "tier1",
    "mea.gov.in":            "tier1",
    "agriwelfare.gov.in":    "tier1",
    "dare.gov.in":           "tier1",
    "iari.res.in":           "tier1",
    "mofpi.gov.in":          "tier1",
    "isro.gov.in":           "tier1",
    "drdo.gov.in":           "tier1",
    "moef.gov.in":           "tier1",
    "upsc.gov.in":           "tier1",
    "nta.ac.in":             "tier1",
    "financialservices.gov.in":"tier1",
    "irdai.gov.in":          "tier1",
    "npci.org.in":           "tier1",
    "niftem.ac.in":          "tier1",
    # Tier-2 discovery
    "reuters.com":           "tier2",
    "indianexpress.com":     "tier2",
    "livemint.com":          "tier2",
    "business-standard.com": "tier2",
    "economictimes.indiatimes.com": "tier2",
}

def gnews_url(domain):
    from urllib.parse import quote
    return ("https://news.google.com/rss/search?q=" + quote(f"site:{domain} when:2d")
            + "&hl=en-IN&gl=IN&ceid=IN:en")
