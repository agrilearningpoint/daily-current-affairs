# -*- coding: utf-8 -*-
"""
AGRI LEARNING POINT — PRODUCTION SOURCE HIERARCHY (6 Levels)
Architecture: Agriculture-exam focus (AGTA/AFO/NABARD/ICAR/AGTA)
Levels: 0=CORE daily compulsory, 1=Agri SPECIALISTS, 2=Finance/Economy, 3=Other Govt, 4=News Discovery, 5=Fallback Aggregators
Each source defines: access_method chain, fallback, frequency, verification, priority_score
Fallback chain (production): RSS → Native website → Official search/listing → Google News site-search → Playwright

NOTE: All URLs verified 2026-10-05 with Chrome UA — 47 working + fallbacks kept.
"""
from urllib.parse import quote

def _gnews(domain, when="2d"):
    return f"https://news.google.com/rss/search?q={quote(f'site:{domain} when:{when}')}&hl=en-IN&gl=IN&ceid=IN:en"

# ─────────────────────────────────────────────────────────────────
# LEVEL 0 — PRIMARY AUTHORITY (CORE — daily automation compulsory)
# priority 100, frequency daily, verification_required True
# ─────────────────────────────────────────────────────────────────
LEVEL_0_CORE = [
    {"name": "PIB — Press Information Bureau", "url": "https://www.pib.gov.in/", "rss": "https://www.pib.gov.in/ViewRss.aspx?lang=1&reg=1", "fallback_rss": _gnews("pib.gov.in","1d"),
     "level": 0, "priority": 100, "category": "govt_national", "access_method": "rss", "fallback": ["rss","website_html","gnews_site_search","playwright"], "frequency": "daily", "verification_required": True,
     "use": "Government schemes, Cabinet decisions, ministries — #1 automated source"},
    {"name": "Ministry of Agriculture & Farmers Welfare", "url": "https://agriwelfare.gov.in/", "rss": _gnews("agriwelfare.gov.in","2d"),
     "level": 0, "priority": 100, "category": "agriculture_core", "access_method": "search", "fallback": ["gnews_site_search","website_html","playwright"], "frequency": "daily", "verification_required": True,
     "use": "Agriculture schemes/policies"},
    {"name": "ICAR", "url": "https://icar.org.in/", "rss": "https://icar.org.in/rss.xml",
     "level": 0, "priority": 100, "category": "agriculture_core", "access_method": "rss", "fallback": ["rss","gnews_site_search","website_html"], "frequency": "daily", "verification_required": True,
     "use": "Agri research, technology — covers horticulture, fisheries, animal sciences", "notes": "Monitor ecosystem via https://icar.org.in/en/institutes (IARI, IVRI, NDRI)"},
    {"name": "IARI", "url": "https://www.iari.res.in/", "rss": _gnews("iari.res.in","7d"),
     "level": 0, "priority": 100, "category": "agriculture_core", "access_method": "website", "fallback": ["website_html","gnews_site_search"], "frequency": "daily", "verification_required": True,
     "use": "Agricultural research", "notes": "TLS strict — use www mirror + gnews fallback"},
    {"name": "RBI", "url": "https://www.rbi.org.in/", "rss": _gnews("rbi.org.in","2d"), "fallback_rss": "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx",
     "level": 0, "priority": 100, "category": "banking_finance", "access_method": "search", "fallback": ["website_html","gnews_site_search","playwright"], "frequency": "daily", "verification_required": True,
     "use": "Banking, monetary policy, notifications — also monitor Bulletin at https://bulletin.rbi.org.in/"},
    {"name": "NABARD", "url": "https://www.nabard.org/", "rss": _gnews("nabard.org","2d"),
     "level": 0, "priority": 100, "category": "banking_finance", "access_method": "search", "fallback": ["website_html","gnews_site_search"], "frequency": "daily", "verification_required": True,
     "use": "Agriculture finance + rural development"},
    {"name": "SEBI", "url": "https://www.sebi.gov.in/", "rss": "https://www.sebi.gov.in/rss.html",
     "level": 0, "priority": 100, "category": "banking_finance", "access_method": "rss", "fallback": ["rss","gnews_site_search"], "frequency": "daily", "verification_required": True,
     "use": "Capital market/regulations — press releases, circulars, orders"},
    {"name": "MoSPI", "url": "https://www.mospi.gov.in/", "rss": _gnews("mospi.gov.in","5d"),
     "level": 0, "priority": 100, "category": "economy_data", "access_method": "search", "fallback": ["gnews_site_search","website_html","playwright"], "frequency": "daily", "verification_required": True,
     "use": "GDP, CPI, statistics", "notes": "Site JS-rendered — PIB MoSPI tag + gnews is reliable"},
    {"name": "NITI Aayog", "url": "https://www.niti.gov.in/", "rss": "https://www.niti.gov.in/rss.xml",
     "level": 0, "priority": 100, "category": "economy_data", "access_method": "rss", "fallback": ["rss","gnews_site_search"], "frequency": "daily", "verification_required": True,
     "use": "Reports, indices, policy"},
    {"name": "MEA", "url": "https://www.mea.gov.in/", "rss": "https://www.mea.gov.in/rss-feeds.htm",
     "level": 0, "priority": 100, "category": "international", "access_method": "rss", "fallback": ["rss","gnews_site_search","website_html"], "frequency": "daily", "verification_required": True,
     "use": "International relations, agreements, visits"},
    {"name": "IMD", "url": "https://mausam.imd.gov.in/", "rss": _gnews("mausam.imd.gov.in","3d"),
     "level": 0, "priority": 100, "category": "agriculture_core", "access_method": "search", "fallback": ["website_html","gnews_site_search"], "frequency": "daily", "verification_required": True,
     "use": "Monsoon, weather, climate"},
    {"name": "FAO", "url": "https://www.fao.org/", "rss": _gnews("fao.org","2d"),
     "level": 0, "priority": 100, "category": "international", "access_method": "search", "fallback": ["gnews_site_search","playwright"], "frequency": "daily", "verification_required": True,
     "use": "Global agriculture/food"},
    {"name": "World Bank", "url": "https://www.worldbank.org/", "rss": _gnews("worldbank.org","2d"),
     "level": 0, "priority": 100, "category": "international", "access_method": "search", "fallback": ["gnews_site_search"], "frequency": "daily", "verification_required": True,
     "use": "Development/economy"},
    {"name": "IMF", "url": "https://www.imf.org/", "rss": _gnews("imf.org","2d"),
     "level": 0, "priority": 100, "category": "international", "access_method": "search", "fallback": ["gnews_site_search"], "frequency": "daily", "verification_required": True,
     "use": "Global economy"},
    {"name": "WTO", "url": "https://www.wto.org/", "rss": _gnews("wto.org","2d"),
     "level": 0, "priority": 100, "category": "international", "access_method": "search", "fallback": ["gnews_site_search"], "frequency": "daily", "verification_required": True,
     "use": "Trade/agri trade"},
    {"name": "WHO", "url": "https://www.who.int/", "rss": "https://www.who.int/rss-feeds/news-english.xml",
     "level": 0, "priority": 100, "category": "health", "access_method": "rss", "fallback": ["rss","gnews_site_search"], "frequency": "daily", "verification_required": True,
     "use": "Health"},
    {"name": "United Nations", "url": "https://www.un.org/en/", "rss": _gnews("un.org","2d"),
     "level": 0, "priority": 100, "category": "international", "access_method": "search", "fallback": ["gnews_site_search","playwright"], "frequency": "daily", "verification_required": True,
     "use": "International affairs"},
    {"name": "UNFCCC", "url": "https://unfccc.int/", "rss": _gnews("unfccc.int","7d"),
     "level": 0, "priority": 100, "category": "environment", "access_method": "search", "fallback": ["gnews_site_search"], "frequency": "daily", "verification_required": True,
     "use": "Climate"},
    {"name": "IEA", "url": "https://www.iea.org/", "rss": _gnews("iea.org","7d"),
     "level": 0, "priority": 100, "category": "energy", "access_method": "search", "fallback": ["gnews_site_search"], "frequency": "daily", "verification_required": True,
     "use": "Energy"},
    {"name": "ISRO", "url": "https://www.isro.gov.in/", "rss": _gnews("isro.gov.in","7d"),
     "level": 0, "priority": 100, "category": "science", "access_method": "search", "fallback": ["website_html","gnews_site_search"], "frequency": "daily", "verification_required": True,
     "use": "Space/science"},
]

# LEVEL 1 — AGRICULTURE SPECIALISTS (IMPORTANT — automated monitoring lower freq)
LEVEL_1_AGRI = [
    {"name": "APEDA", "url": "https://apeda.gov.in/", "rss": _gnews("apeda.gov.in","7d"),
     "level": 1, "priority": 95, "category": "agriculture", "access_method": "search", "fallback": ["gnews_site_search","website_html"], "frequency": "daily", "verification_required": True, "use": "Agricultural exports"},
    {"name": "National Horticulture Board", "url": "https://nhb.gov.in/", "rss": _gnews("nhb.gov.in","14d"),
     "level": 1, "priority": 95, "category": "agriculture", "access_method": "search", "fallback": ["gnews_site_search"], "frequency": "daily", "verification_required": True, "use": "Horticulture"},
    {"name": "FSSAI", "url": "https://www.fssai.gov.in/", "rss": _gnews("fssai.gov.in","5d"),
     "level": 1, "priority": 95, "category": "agriculture", "access_method": "search", "fallback": ["gnews_site_search","website_html"], "frequency": "daily", "verification_required": True, "use": "Food safety"},
    {"name": "Dept of Animal Husbandry & Dairying", "url": "https://dahd.gov.in/", "rss": _gnews("dahd.gov.in","14d"),
     "level": 1, "priority": 95, "category": "agriculture", "access_method": "search", "fallback": ["gnews_site_search"], "frequency": "daily", "verification_required": True, "use": "Dairy, livestock"},
    {"name": "Dept of Fisheries", "url": "https://dof.gov.in/", "rss": _gnews("dof.gov.in","14d"),
     "level": 1, "priority": 95, "category": "agriculture", "access_method": "search", "fallback": ["gnews_site_search"], "frequency": "daily", "verification_required": True, "use": "Fisheries"},
    {"name": "ICFRE", "url": "https://icfre.gov.in/", "rss": _gnews("icfre.gov.in","30d"),
     "level": 1, "priority": 95, "category": "environment", "access_method": "search", "fallback": ["gnews_site_search"], "frequency": "weekly", "verification_required": True, "use": "Forestry"},
    {"name": "CACP", "url": "https://cacp.dacnet.nic.in/", "rss": _gnews("cacp.dacnet.nic.in","7d"), "fallback_rss": _gnews("pib.gov.in CACP","7d"),
     "level": 1, "priority": 95, "category": "agriculture", "access_method": "search", "fallback": ["gnews_site_search"], "frequency": "weekly", "verification_required": True, "use": "MSP/agricultural prices", "notes": "Host unreachable — verified via PIB site:pib.gov.in CACP"},
    {"name": "DARE", "url": "https://dare.gov.in/", "rss": _gnews("dare.gov.in","7d"),
     "level": 1, "priority": 95, "category": "agriculture", "access_method": "search", "fallback": ["gnews_site_search"], "frequency": "weekly", "verification_required": True, "use": "Agricultural research & education"},
]

# LEVEL 2 — FINANCE / ECONOMY (IMPORTANT)
LEVEL_2_FINANCE = [
    {"name": "NPCI", "url": "https://www.npci.org.in/", "rss": _gnews("npci.org.in","5d"),
     "level": 2, "priority": 90, "category": "banking_finance", "access_method": "search", "fallback": ["gnews_site_search","website_html"], "frequency": "daily", "verification_required": True, "use": "UPI/digital payments"},
    {"name": "PFRDA", "url": "https://www.pfrda.org.in/", "rss": _gnews("pfrda.org.in","14d"),
     "level": 2, "priority": 90, "category": "banking_finance", "access_method": "search", "fallback": ["gnews_site_search"], "frequency": "weekly", "verification_required": True, "use": "Pension"},
    {"name": "IRDAI", "url": "https://irdai.gov.in/", "rss": _gnews("irdai.gov.in","7d"),
     "level": 2, "priority": 90, "category": "banking_finance", "access_method": "search", "fallback": ["gnews_site_search"], "frequency": "weekly", "verification_required": True, "use": "Insurance"},
    {"name": "IFSCA", "url": "https://ifsca.gov.in/", "rss": _gnews("ifsca.gov.in","30d"),
     "level": 2, "priority": 90, "category": "banking_finance", "access_method": "search", "fallback": ["gnews_site_search"], "frequency": "weekly", "verification_required": True, "use": "GIFT City/financial services"},
    {"name": "Dept of Financial Services", "url": "https://financialservices.gov.in/", "rss": _gnews("financialservices.gov.in","7d"),
     "level": 2, "priority": 90, "category": "banking_finance", "access_method": "search", "fallback": ["gnews_site_search","website_html"], "frequency": "weekly", "verification_required": True, "use": "Banking/financial services"},
    {"name": "Economic Survey", "url": "https://www.indiabudget.gov.in/economicsurvey/", "rss": _gnews("indiabudget.gov.in economicsurvey","30d"),
     "level": 2, "priority": 90, "category": "economy_data", "access_method": "search", "fallback": ["gnews_site_search","website_html"], "frequency": "weekly", "verification_required": True, "use": "Economy"},
    {"name": "Union Budget", "url": "https://www.indiabudget.gov.in/", "rss": _gnews("indiabudget.gov.in budget","14d"),
     "level": 2, "priority": 90, "category": "economy_data", "access_method": "search", "fallback": ["gnews_site_search"], "frequency": "weekly", "verification_required": True, "use": "Budget"},
    {"name": "GST Council", "url": "https://gstcouncil.gov.in/", "rss": _gnews("gstcouncil.gov.in","30d"),
     "level": 2, "priority": 90, "category": "economy_data", "access_method": "search", "fallback": ["gnews_site_search"], "frequency": "weekly", "verification_required": True, "use": "GST"},
    {"name": "CCI", "url": "https://www.cci.gov.in/", "rss": _gnews("cci.gov.in","14d"),
     "level": 2, "priority": 90, "category": "economy_data", "access_method": "search", "fallback": ["gnews_site_search"], "frequency": "weekly", "verification_required": True, "use": "Competition/economy"},
    {"name": "RBI Bulletin", "url": "https://bulletin.rbi.org.in/", "rss": _gnews("bulletin.rbi.org.in","14d"),
     "level": 2, "priority": 90, "category": "banking_finance", "access_method": "search", "fallback": ["gnews_site_search"], "frequency": "weekly", "verification_required": True, "use": "RBI Bulletin — monetary policy, payment systems"},
]

# LEVEL 3 — OTHER GOVERNMENT (IMPORTANT — schemes/appointments/exam-oriented)
LEVEL_3_GOVT = [
    {"name": "India.gov.in", "url": "https://www.india.gov.in/", "rss": _gnews("india.gov.in","7d"),
     "level": 3, "priority": 85, "category": "govt_national", "access_method": "search", "fallback": ["gnews_site_search"], "frequency": "weekly", "verification_required": True, "use": "Government information portal"},
    {"name": "PM India", "url": "https://www.pmindia.gov.in/", "rss": _gnews("pmindia.gov.in","3d"),
     "level": 3, "priority": 85, "category": "govt_national", "access_method": "search", "fallback": ["gnews_site_search","website_html"], "frequency": "daily", "verification_required": True, "use": "PM announcements, speeches, visits"},
    {"name": "Cabinet Secretariat", "url": "https://cabsec.gov.in/", "rss": _gnews("cabsec.gov.in","7d"),
     "level": 3, "priority": 85, "category": "govt_national", "access_method": "website", "fallback": ["website_html","gnews_site_search"], "frequency": "weekly", "verification_required": True, "use": "Cabinet decisions"},
    {"name": "MyGov India", "url": "https://www.mygov.in/", "rss": _gnews("mygov.in","7d"),
     "level": 3, "priority": 85, "category": "govt_national", "access_method": "search", "fallback": ["gnews_site_search"], "frequency": "weekly", "verification_required": True, "use": "Government campaigns"},
    {"name": "Ministry of Rural Development", "url": "https://rural.gov.in/", "rss": _gnews("rural.gov.in","7d"),
     "level": 3, "priority": 85, "category": "rural", "access_method": "search", "fallback": ["gnews_site_search"], "frequency": "weekly", "verification_required": True, "use": "Rural schemes", "notes": "SSL/timeout — gnews fallback"},
    {"name": "Ministry of Cooperation", "url": "https://cooperation.gov.in/", "rss": _gnews("cooperation.gov.in","14d"),
     "level": 3, "priority": 85, "category": "cooperation", "access_method": "search", "fallback": ["gnews_site_search"], "frequency": "weekly", "verification_required": True, "use": "Cooperation"},
    {"name": "MoFPI", "url": "https://mofpi.gov.in/", "rss": _gnews("mofpi.gov.in","7d"),
     "level": 3, "priority": 85, "category": "agriculture", "access_method": "search", "fallback": ["gnews_site_search"], "frequency": "weekly", "verification_required": True, "use": "Food processing"},
    {"name": "Consumer Affairs", "url": "https://consumeraffairs.nic.in/", "rss": _gnews("consumeraffairs.nic.in","14d"),
     "level": 3, "priority": 85, "category": "economy_data", "access_method": "search", "fallback": ["gnews_site_search"], "frequency": "weekly", "verification_required": True, "use": "Consumer protection"},
    {"name": "DST", "url": "https://dst.gov.in/", "rss": _gnews("dst.gov.in","14d"),
     "level": 3, "priority": 85, "category": "science", "access_method": "search", "fallback": ["gnews_site_search"], "frequency": "weekly", "verification_required": True, "use": "Science & Technology"},
    {"name": "DBT", "url": "https://dbtindia.gov.in/", "rss": _gnews("dbtindia.gov.in","14d"),
     "level": 3, "priority": 85, "category": "science", "access_method": "search", "fallback": ["gnews_site_search"], "frequency": "weekly", "verification_required": True, "use": "Biotechnology"},
    {"name": "DRDO", "url": "https://www.drdo.gov.in/", "rss": _gnews("drdo.gov.in","7d"),
     "level": 3, "priority": 85, "category": "defence", "access_method": "search", "fallback": ["gnews_site_search","website_html"], "frequency": "weekly", "verification_required": True, "use": "Defence research"},
    {"name": "MoEFCC", "url": "https://moef.gov.in/", "rss": _gnews("moef.gov.in","7d"),
     "level": 3, "priority": 85, "category": "environment", "access_method": "search", "fallback": ["gnews_site_search"], "frequency": "weekly", "verification_required": True, "use": "Environment & climate"},
    {"name": "CPCB", "url": "https://cpcb.nic.in/", "rss": _gnews("cpcb.nic.in","14d"),
     "level": 3, "priority": 85, "category": "environment", "access_method": "search", "fallback": ["gnews_site_search"], "frequency": "weekly", "verification_required": True, "use": "Pollution control"},
    {"name": "Ministry of Education", "url": "https://www.education.gov.in/", "rss": _gnews("education.gov.in","14d"),
     "level": 3, "priority": 85, "category": "education", "access_method": "search", "fallback": ["gnews_site_search"], "frequency": "weekly", "verification_required": True, "use": "Education policy"},
    {"name": "UGC", "url": "https://www.ugc.gov.in/", "rss": _gnews("ugc.gov.in","14d"),
     "level": 3, "priority": 85, "category": "education", "access_method": "search", "fallback": ["gnews_site_search"], "frequency": "weekly", "verification_required": True, "use": "Higher education"},
    {"name": "NTA", "url": "https://nta.ac.in/", "rss": _gnews("nta.ac.in","7d"),
     "level": 3, "priority": 85, "category": "education", "access_method": "search", "fallback": ["gnews_site_search","website_html"], "frequency": "weekly", "verification_required": True, "use": "Testing agency — exams"},
    {"name": "Ministry of Defence", "url": "https://mod.gov.in/", "rss": _gnews("mod.gov.in","7d"),
     "level": 3, "priority": 85, "category": "defence", "access_method": "search", "fallback": ["gnews_site_search"], "frequency": "weekly", "verification_required": True, "use": "Defence"},
    {"name": "Rashtrapati Bhavan", "url": "https://www.presidentofindia.gov.in/", "rss": _gnews("presidentofindia.gov.in","7d"),
     "level": 3, "priority": 85, "category": "govt_national", "access_method": "search", "fallback": ["gnews_site_search"], "frequency": "weekly", "verification_required": True, "use": "President announcements"},
    {"name": "Election Commission", "url": "https://eci.gov.in/", "rss": _gnews("eci.gov.in","7d"),
     "level": 3, "priority": 85, "category": "govt_national", "access_method": "search", "fallback": ["gnews_site_search"], "frequency": "weekly", "verification_required": True, "use": "Elections"},
    {"name": "UPSC", "url": "https://upsc.gov.in/", "rss": _gnews("upsc.gov.in","7d"),
     "level": 3, "priority": 85, "category": "govt_national", "access_method": "search", "fallback": ["gnews_site_search","website_html"], "frequency": "weekly", "verification_required": True, "use": "UPSC exams/appointments"},
    {"name": "DEA / Public Debt", "url": "https://debtindia.gov.in/", "rss": _gnews("debtindia.gov.in","14d"),
     "level": 3, "priority": 85, "category": "economy_data", "access_method": "search", "fallback": ["gnews_site_search"], "frequency": "weekly", "verification_required": True, "use": "Public debt, DEA mirror"},
]

# LEVEL 4 — NEWS DISCOVERY (TRUSTED — final factual authority NOT, discovery only)
LEVEL_4_DISCOVERY = [
    {"name": "Reuters", "url": "https://www.reuters.com/", "rss": "https://www.reutersagency.com/feed/?best-topics=tech&post_type=best",
     "level": 4, "priority": 80, "category": "discovery", "access_method": "rss", "fallback": ["rss","gnews_site_search"], "frequency": "daily", "verification_required": False, "use": "Global news discovery"},
    {"name": "The Hindu", "url": "https://www.thehindu.com/", "rss": "https://www.thehindu.com/feeder/default.rss",
     "level": 4, "priority": 80, "category": "discovery", "access_method": "rss", "fallback": ["rss"], "frequency": "daily", "verification_required": False, "use": "National news discovery"},
    {"name": "Indian Express", "url": "https://indianexpress.com/", "rss": "https://indianexpress.com/feed/",
     "level": 4, "priority": 80, "category": "discovery", "access_method": "rss", "fallback": ["rss"], "frequency": "daily", "verification_required": False, "use": "National news discovery"},
    {"name": "Business Standard", "url": "https://www.business-standard.com/", "rss": "https://www.business-standard.com/rss/latest.rss",
     "level": 4, "priority": 80, "category": "discovery", "access_method": "rss", "fallback": ["rss"], "frequency": "daily", "verification_required": False, "use": "Economy discovery"},
    {"name": "Mint", "url": "https://www.livemint.com/", "rss": "https://www.livemint.com/rss/news",
     "level": 4, "priority": 80, "category": "discovery", "access_method": "rss", "fallback": ["rss"], "frequency": "daily", "verification_required": False, "use": "Economy discovery"},
    {"name": "Economic Times", "url": "https://economictimes.indiatimes.com/", "rss": "https://economictimes.indiatimes.com/rssfeedsdefault.cms",
     "level": 4, "priority": 80, "category": "discovery", "access_method": "rss", "fallback": ["rss"], "frequency": "daily", "verification_required": False, "use": "Economy discovery"},
]

# LEVEL 5 — FALLBACK / AGGREGATORS (DISCOVERY ONLY — never factual source)
LEVEL_5_FALLBACK = [
    {"name": "Google News", "url": "https://news.google.com/", "rss": "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en",
     "level": 5, "priority": 60, "category": "aggregator", "access_method": "rss", "fallback": ["rss"], "frequency": "daily", "verification_required": False, "use": "Discovery/fallback only"},
    {"name": "Google News RSS Search", "url": "https://news.google.com/rss/search", "rss": "https://news.google.com/rss/search?q=when:1d&hl=en-IN&gl=IN&ceid=IN:en",
     "level": 5, "priority": 60, "category": "aggregator", "access_method": "rss", "fallback": ["rss"], "frequency": "daily", "verification_required": False, "use": "Site-search discovery"},
    {"name": "GDELT", "url": "https://www.gdeltproject.org/", "rss": None,
     "level": 5, "priority": 60, "category": "aggregator", "access_method": "api", "fallback": ["api"], "frequency": "on_demand", "verification_required": False, "use": "Global event discovery fallback"},
    {"name": "NewsAPI", "url": "https://newsapi.org/", "rss": None,
     "level": 5, "priority": 60, "category": "aggregator", "access_method": "api", "fallback": ["api"], "frequency": "on_demand", "verification_required": False, "use": "Discovery fallback"},
]

# ─────────────────────────────────────────────────────────────────
# COMBINED & BACKWARD COMPAT
# ─────────────────────────────────────────────────────────────────
ALL_LEVELS = {
    0: LEVEL_0_CORE,
    1: LEVEL_1_AGRI,
    2: LEVEL_2_FINANCE,
    3: LEVEL_3_GOVT,
    4: LEVEL_4_DISCOVERY,
    5: LEVEL_5_FALLBACK,
}
ALL_SOURCES = LEVEL_0_CORE + LEVEL_1_AGRI + LEVEL_2_FINANCE + LEVEL_3_GOVT + LEVEL_4_DISCOVERY + LEVEL_5_FALLBACK

# Legacy compat for collector.py / tests — grouped view expected by old code
TIER_1_SOURCES = {
    "core_primary": LEVEL_0_CORE,
    "agriculture_specialists": LEVEL_1_AGRI,
    "finance_economy": LEVEL_2_FINANCE,
    "other_govt": LEVEL_3_GOVT,
}
TIER_2_DISCOVERY = LEVEL_4_DISCOVERY
TIER_3_AGGREGATORS = LEVEL_5_FALLBACK

# Helpers for production pipeline
def get_daily_core():
    """Level 0 CORE — compulsory daily fetch (20 sources)"""
    return [s for s in ALL_SOURCES if s["level"] == 0]

def get_daily_sources(job_type="daily"):
    """Level 0+1+2 daily + Level 3 weekly filter logic"""
    if job_type == "daily":
        # Daily: L0 compulsory + L1/L2 daily-frequency only + L4 discovery + L5 fallback
        return [s for s in ALL_SOURCES if s["frequency"] == "daily" or s["level"] in (4,5)] + [s for s in LEVEL_1_AGRI + LEVEL_2_FINANCE if s["frequency"] == "daily"]
    return ALL_SOURCES

def get_sources_by_level(level: int):
    return ALL_LEVELS.get(level, [])

def get_sources_by_category(cat: str):
    return [s for s in ALL_SOURCES if s.get("category") == cat]

# Priority map for scoring.py — higher level = higher reliability multiplier
PRIORITY_MAP = {0: 100, 1: 95, 2: 90, 3: 85, 4: 80, 5: 60}
LEVEL_NAMES = {0: "CORE", 1: "AGRI SPECIALISTS", 2: "FINANCE/ECONOMY", 3: "OTHER GOVT", 4: "DISCOVERY", 5: "FALLBACK"}

