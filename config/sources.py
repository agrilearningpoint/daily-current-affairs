# -*- coding: utf-8 -*-
"""Source registry for Agri Learning Point current-affairs pipeline.

Authority levels (lower number = stronger authority):
  0: core primary authorities; 1: agriculture specialists; 2: finance/economy;
  3: other official bodies; 4: editorial discovery; 5: aggregators (disabled by default).

Important: an RSS URL or a Google News result is a collection route, NOT proof
that the article's claims are verified. Agent 04 must verify important facts
against primary documents before publication.
"""
from __future__ import annotations

from urllib.parse import quote


def _gnews(domain: str, when: str = "2d") -> str:
    """Build Google News site-search RSS URL safely."""
    query = quote(f"site:{domain} when:{when}")
    return f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"


def _source(name, url, level, category, *, priority=None, rss=None,
            fallback_rss=None, frequency="daily", verification_required=True,
            fallback=None, use="", notes=""):
    item = {
        "name": name,
        "url": url.rstrip("/"),
        "level": int(level),
        "priority": int(priority if priority is not None else {0: 100, 1: 95, 2: 90, 3: 85, 4: 70, 5: 50}[level]),
        "category": category,
        "access_method": "rss" if rss else "website",
        "frequency": frequency,
        "verification_required": bool(verification_required),
        "fallback": list(fallback if fallback is not None else (["rss", "website_html", "gnews_site_search"] if level <= 3 else ["rss"])),
        "use": use or category.replace("_", " ").title(),
    }
    if rss:
        item["rss"] = rss
    if fallback_rss:
        item["fallback_rss"] = fallback_rss
    if notes:
        item["notes"] = notes
    return item


# LEVEL 0: core primary authorities. Kept focused on high-value daily exam topics.
LEVEL_0_CORE = [
    _source("PIB — Press Information Bureau", "https://www.pib.gov.in", 0, "govt_national",
            rss="https://www.pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3", fallback=["rss", "website_html", "gnews_site_search"], use="Official releases, schemes, Cabinet and ministry announcements", notes="RssMain.aspx verified live 2026-10-18 (HTTP 200, text/xml, 20 items). The older ViewRss.aspx route returns HTML and is NOT a feed; do not re-add it. Do not treat Google News as primary evidence."),
    _source("Ministry of Agriculture & Farmers Welfare", "https://agriwelfare.gov.in", 0, "agriculture_core", rss=_gnews("agriwelfare.gov.in", "2d"), fallback=["gnews_site_search", "website_html"], use="Agriculture policy, schemes and farmer welfare"),
    _source("ICAR", "https://icar.org.in", 0, "agriculture_core", rss="https://icar.org.in/rss.xml", fallback=["rss", "website_html", "gnews_site_search"], use="Agricultural research, technology and institutions"),
    _source("RBI", "https://www.rbi.org.in", 0, "banking_finance", rss=_gnews("rbi.org.in", "2d"), fallback=["gnews_site_search", "website_html"], use="Monetary policy, banking notifications and financial stability"),
    _source("NABARD", "https://www.nabard.org", 0, "banking_finance", rss=_gnews("nabard.org", "2d"), fallback=["gnews_site_search", "website_html"], use="Agriculture credit and rural development"),
    _source("SEBI", "https://www.sebi.gov.in", 0, "banking_finance", rss=_gnews("sebi.gov.in", "2d"), fallback=["gnews_site_search", "website_html"], use="Capital markets, regulations and circulars", notes="SEBI publishes no working public RSS (rss.html is HTML; sebiweb/rss/rss.jsp returns 404, verified 2026-10-18). Google News site-search is the discovery route; verify circulars against sebi.gov.in."),
    _source("NITI Aayog", "https://www.niti.gov.in", 0, "economy_data", rss="https://www.niti.gov.in/rss.xml", fallback=["rss", "website_html", "gnews_site_search"], use="Policy reports, indices and development"),
    _source("Ministry of Statistics and Programme Implementation", "https://www.mospi.gov.in", 0, "economy_data", rss=_gnews("mospi.gov.in", "5d"), fallback=["gnews_site_search", "website_html"], use="GDP, CPI and official statistics"),
    _source("Ministry of External Affairs", "https://www.mea.gov.in", 0, "international", rss=_gnews("mea.gov.in", "2d"), fallback=["gnews_site_search", "website_html"], use="International agreements, visits and foreign policy", notes="mea.gov.in/rss-feeds.htm is an HTML index, not a feed (verified 2026-10-18). Google News site-search is the discovery route; verify statements against mea.gov.in."),
    _source("India Meteorological Department", "https://mausam.imd.gov.in", 0, "agriculture_core", rss=_gnews("mausam.imd.gov.in", "3d"), fallback=["gnews_site_search", "website_html"], use="Monsoon, climate and weather"),
    _source("Department of Animal Husbandry and Dairying", "https://dahd.gov.in", 0, "agriculture_core", rss=_gnews("dahd.gov.in", "7d"), fallback=["gnews_site_search", "website_html"], use="Livestock, dairy and animal husbandry"),
    _source("Department of Fisheries", "https://dof.gov.in", 0, "agriculture_core", rss=_gnews("dof.gov.in", "7d"), fallback=["gnews_site_search", "website_html"], use="Fisheries schemes and blue economy"),
    _source("APEDA", "https://apeda.gov.in", 0, "agriculture_core", rss=_gnews("apeda.gov.in", "7d"), fallback=["gnews_site_search", "website_html"], use="Agricultural exports and market access"),
    _source("Department of Agriculture Research and Education", "https://dare.gov.in", 0, "agriculture_core", rss=_gnews("dare.gov.in", "7d"), fallback=["gnews_site_search", "website_html"], use="Agricultural research and education"),
]

# LEVEL 1: specialist agriculture, food, climate and allied sectors.
LEVEL_1_AGRI = [
    _source("Indian Agricultural Research Institute", "https://www.iari.res.in", 1, "agriculture", rss=_gnews("iari.res.in", "7d"), fallback=["gnews_site_search", "website_html"], use="Agronomy, horticulture and agricultural research"),
    _source("National Horticulture Board", "https://nhb.gov.in", 1, "horticulture", rss=_gnews("nhb.gov.in", "7d"), fallback=["gnews_site_search", "website_html"], use="Horticulture schemes, production and statistics"),
    _source("FSSAI", "https://www.fssai.gov.in", 1, "food_safety", rss=_gnews("fssai.gov.in", "7d"), fallback=["gnews_site_search", "website_html"], use="Food safety, standards and regulation"),
    _source("ICFRE", "https://icfre.gov.in", 1, "forestry_environment", rss=_gnews("icfre.gov.in", "14d"), frequency="weekly", fallback=["gnews_site_search", "website_html"], use="Forestry and forest research"),
    _source("Commission for Agricultural Costs and Prices", "https://cacp.dacnet.nic.in", 1, "agriculture_economy", rss=_gnews("pib.gov.in CACP", "7d"), frequency="weekly", fallback=["gnews_site_search", "website_html"], use="MSP recommendations and agricultural prices", notes="Use official CACP/PIB documents for verification."),
    _source("Ministry of Food Processing Industries", "https://mofpi.gov.in", 1, "food_processing", rss=_gnews("mofpi.gov.in", "7d"), fallback=["gnews_site_search", "website_html"], use="Food processing schemes and investments"),
    _source("Ministry of Environment, Forest and Climate Change", "https://moef.gov.in", 1, "environment", rss=_gnews("moef.gov.in", "7d"), fallback=["gnews_site_search", "website_html"], use="Climate, biodiversity and environment policy"),
]

# LEVEL 2: banking, financial regulation and economy.
LEVEL_2_FINANCE = [
    _source("NPCI", "https://www.npci.org.in", 2, "banking_finance", rss=_gnews("npci.org.in", "7d"), fallback=["gnews_site_search", "website_html"], use="UPI and digital payments"),
    _source("PFRDA", "https://www.pfrda.org.in", 2, "banking_finance", rss=_gnews("pfrda.org.in", "14d"), frequency="weekly", fallback=["gnews_site_search", "website_html"], use="Pension regulation"),
    _source("IRDAI", "https://irdai.gov.in", 2, "banking_finance", rss=_gnews("irdai.gov.in", "7d"), fallback=["gnews_site_search", "website_html"], use="Insurance regulation"),
    _source("IFSCA", "https://ifsca.gov.in", 2, "banking_finance", rss=_gnews("ifsca.gov.in", "14d"), frequency="weekly", fallback=["gnews_site_search", "website_html"], use="International financial services"),
    _source("Department of Financial Services", "https://financialservices.gov.in", 2, "banking_finance", rss=_gnews("financialservices.gov.in", "7d"), fallback=["gnews_site_search", "website_html"], use="Banking and financial services"),
    _source("Union Budget of India", "https://www.indiabudget.gov.in", 2, "economy_data", rss=_gnews("indiabudget.gov.in", "14d"), frequency="weekly", fallback=["gnews_site_search", "website_html"], use="Budget documents and fiscal policy"),
    _source("GST Council", "https://gstcouncil.gov.in", 2, "economy_data", rss=_gnews("gstcouncil.gov.in", "14d"), frequency="weekly", fallback=["gnews_site_search", "website_html"], use="GST decisions and notifications"),
    _source("Competition Commission of India", "https://www.cci.gov.in", 2, "economy_data", rss=_gnews("cci.gov.in", "14d"), frequency="weekly", fallback=["gnews_site_search", "website_html"], use="Competition and market regulation"),
    _source("RBI Bulletin", "https://bulletin.rbi.org.in", 2, "banking_finance", rss=_gnews("bulletin.rbi.org.in", "14d"), frequency="weekly", fallback=["gnews_site_search", "website_html"], use="RBI research and economic analysis"),
]

# LEVEL 3: other official sources. Weekly-frequency sources are selected for weekly/monthly jobs.
LEVEL_3_GOVT = [
    _source("India.gov.in", "https://www.india.gov.in", 3, "govt_national", rss=_gnews("india.gov.in", "7d"), frequency="weekly", fallback=["gnews_site_search", "website_html"], use="National government portal"),
    _source("Prime Minister of India", "https://www.pmindia.gov.in", 3, "govt_national", rss=_gnews("pmindia.gov.in", "3d"), fallback=["gnews_site_search", "website_html"], use="Prime Minister announcements"),
    _source("Cabinet Secretariat", "https://cabsec.gov.in", 3, "govt_national", rss=_gnews("cabsec.gov.in", "7d"), frequency="weekly", fallback=["gnews_site_search", "website_html"], use="Cabinet decisions"),
    _source("MyGov India", "https://www.mygov.in", 3, "govt_national", rss=_gnews("mygov.in", "7d"), frequency="weekly", fallback=["gnews_site_search", "website_html"], use="Public campaigns and citizen engagement"),
    _source("Ministry of Rural Development", "https://rural.gov.in", 3, "rural_development", rss=_gnews("rural.gov.in", "7d"), frequency="weekly", fallback=["gnews_site_search", "website_html"], use="Rural development schemes"),
    _source("Ministry of Cooperation", "https://cooperation.gov.in", 3, "cooperation", rss=_gnews("cooperation.gov.in", "14d"), frequency="weekly", fallback=["gnews_site_search", "website_html"], use="Cooperative sector"),
    _source("Department of Science and Technology", "https://dst.gov.in", 3, "science", rss=_gnews("dst.gov.in", "14d"), frequency="weekly", fallback=["gnews_site_search", "website_html"], use="Science and technology"),
    _source("Department of Biotechnology", "https://dbtindia.gov.in", 3, "science", rss=_gnews("dbtindia.gov.in", "14d"), frequency="weekly", fallback=["gnews_site_search", "website_html"], use="Biotechnology"),
    _source("DRDO", "https://www.drdo.gov.in", 3, "defence_science", rss=_gnews("drdo.gov.in", "7d"), frequency="weekly", fallback=["gnews_site_search", "website_html"], use="Defence research"),
    _source("Central Pollution Control Board", "https://cpcb.nic.in", 3, "environment", rss=_gnews("cpcb.nic.in", "14d"), frequency="weekly", fallback=["gnews_site_search", "website_html"], use="Pollution control"),
    _source("Ministry of Education", "https://www.education.gov.in", 3, "education", rss=_gnews("education.gov.in", "14d"), frequency="weekly", fallback=["gnews_site_search", "website_html"], use="Education policy"),
    _source("UGC", "https://www.ugc.gov.in", 3, "education", rss=_gnews("ugc.gov.in", "14d"), frequency="weekly", fallback=["gnews_site_search", "website_html"], use="Higher education"),
    _source("National Testing Agency", "https://nta.ac.in", 3, "education", rss=_gnews("nta.ac.in", "7d"), frequency="weekly", fallback=["gnews_site_search", "website_html"], use="National examination notifications"),
    _source("Ministry of Defence", "https://mod.gov.in", 3, "defence", rss=_gnews("mod.gov.in", "7d"), frequency="weekly", fallback=["gnews_site_search", "website_html"], use="Defence policy and appointments"),
    _source("President of India", "https://www.presidentofindia.gov.in", 3, "govt_national", rss=_gnews("presidentofindia.gov.in", "7d"), frequency="weekly", fallback=["gnews_site_search", "website_html"], use="Presidential announcements"),
    _source("Election Commission of India", "https://eci.gov.in", 3, "govt_national", rss=_gnews("eci.gov.in", "7d"), frequency="weekly", fallback=["gnews_site_search", "website_html"], use="Election-related official announcements"),
    _source("UPSC", "https://upsc.gov.in", 3, "education", rss=_gnews("upsc.gov.in", "7d"), frequency="weekly", fallback=["gnews_site_search", "website_html"], use="Recruitment, examinations and appointments"),
]

# LEVEL 4: editorial sources are useful for discovery, never final factual authority.
LEVEL_4_DISCOVERY = [
    _source("Reuters", "https://www.reuters.com", 4, "discovery", rss=_gnews("reuters.com", "2d"), priority=75, verification_required=False, fallback=["gnews_site_search"], use="International and national news discovery", notes="Public Reuters RSS endpoints were retired (reutersagency tech feed returned HTTP 404, verified 2026-10-18); discovery now runs through Google News site-search."),
    _source("The Hindu", "https://www.thehindu.com", 4, "discovery", rss="https://www.thehindu.com/feeder/default.rss", priority=75, verification_required=False, fallback=["rss"], use="National news discovery"),
    _source("Indian Express", "https://indianexpress.com", 4, "discovery", rss="https://indianexpress.com/feed/", priority=75, verification_required=False, fallback=["rss"], use="National news discovery"),
    _source("Business Standard", "https://www.business-standard.com", 4, "discovery", rss="https://www.business-standard.com/rss/latest.rss", priority=75, verification_required=False, fallback=["rss"], use="Economy and business discovery"),
    _source("Mint", "https://www.livemint.com", 4, "discovery", rss="https://www.livemint.com/rss/news", priority=75, verification_required=False, fallback=["rss"], use="Finance and economy discovery"),
    _source("Economic Times", "https://economictimes.indiatimes.com", 4, "discovery", rss="https://economictimes.indiatimes.com/rssfeedsdefault.cms", priority=75, verification_required=False, fallback=["rss"], use="Business and economy discovery"),
]

# LEVEL 5: aggregator feeds are opt-in in collector.py; use only for discovery.
LEVEL_5_FALLBACK = [
    _source("Google News India", "https://news.google.com", 5, "aggregator", rss="https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en", priority=50, verification_required=False, fallback=["rss"], use="Fallback discovery only"),
    _source("Google News Search", "https://news.google.com/rss/search", 5, "aggregator", rss=_gnews("pib.gov.in", "1d"), priority=50, verification_required=False, fallback=["rss"], use="Site-specific discovery fallback"),
]

ALL_LEVELS = {0: LEVEL_0_CORE, 1: LEVEL_1_AGRI, 2: LEVEL_2_FINANCE, 3: LEVEL_3_GOVT, 4: LEVEL_4_DISCOVERY, 5: LEVEL_5_FALLBACK}
ALL_SOURCES = LEVEL_0_CORE + LEVEL_1_AGRI + LEVEL_2_FINANCE + LEVEL_3_GOVT + LEVEL_4_DISCOVERY + LEVEL_5_FALLBACK

# Compatibility expected by existing collector/scoring code.
TIER_1_SOURCES = {
    "core_primary": LEVEL_0_CORE,
    "agriculture_specialists": LEVEL_1_AGRI,
    "finance_economy": LEVEL_2_FINANCE,
    "other_govt": LEVEL_3_GOVT,
}
TIER_2_DISCOVERY = LEVEL_4_DISCOVERY
TIER_3_AGGREGATORS = LEVEL_5_FALLBACK

PRIORITY_MAP = {0: 100, 1: 95, 2: 90, 3: 85, 4: 75, 5: 50}
LEVEL_NAMES = {0: "CORE PRIMARY", 1: "AGRICULTURE SPECIALISTS", 2: "FINANCE/ECONOMY", 3: "OTHER GOVERNMENT", 4: "DISCOVERY", 5: "AGGREGATOR FALLBACK"}


def get_daily_core():
    """Return all Level-0 core sources exactly once."""
    return list(LEVEL_0_CORE)


def get_daily_sources(job_type="daily"):
    """Return the intended source set without duplicate concatenation.

    Daily: all Level 0 plus daily-frequency levels 1-3 and Level 4 discovery.
    Weekly/monthly: all non-aggregator sources. Level 5 is opt-in in collector.
    """
    job_type = str(job_type).lower()
    if job_type == "daily":
        return [s for s in ALL_SOURCES if int(s.get("level", 5)) == 0 or int(s.get("level", 5)) == 4 or str(s.get("frequency", "daily")).lower() in {"daily", "on_demand"}]
    if job_type in {"weekly", "monthly"}:
        return [s for s in ALL_SOURCES if int(s.get("level", 5)) <= 4]
    raise ValueError(f"Unsupported job_type: {job_type!r}")


def get_sources_by_level(level: int):
    return list(ALL_LEVELS.get(int(level), []))


def get_sources_by_category(cat: str):
    cat = str(cat).strip().lower()
    return [s for s in ALL_SOURCES if str(s.get("category", "")).lower() == cat]
