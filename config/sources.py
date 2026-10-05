# -*- coding: utf-8 -*-
"""
AGRI LEARNING POINT — FINAL SOURCE LIST (Priority Tiers) — CLEANED 2026-10-05
Kept only WORKING 47/65 (72.3% alive per live test from E2B with Chrome 127 headers).
DEAD 18 removed (agriwelfare 403, IARI/DARE timeout, CACP, NABARD timeout, FinMin, DEA, NPCI 403, IMF 403, UNDP 403, IEA 403, Cooperation timeout, ConsumerAffairs timeout, DBT timeout, NTA timeout, MOD timeout, MEA 403, UPSC timeout).
RSS feeds added explicitly (feed discovery via Google News RSS search keeps fallback for removed sites via PIB).
Tier-1 = Primary/Official (PIB is nodal), Tier-2 = Trusted News Discovery, Tier-3 = Aggregators
GitHub = Technology only, not factual source
"""

# Tier-1 MUST USE — only WORKING (live test 2026-10-05: 47 alive with Chrome 127 UA)
TIER_1_SOURCES = {
    "govt_national": [
        {"name": "PIB — Press Information Bureau", "url": "https://www.pib.gov.in/", "use": "Government schemes, Cabinet decisions, ministries, national news", "priority": 100, "notes": "Also backgrounders, factsheets, FAQs — RSS: https://www.pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3"},
        {"name": "India.gov.in", "url": "https://www.india.gov.in/", "use": "Government information", "priority": 100},
        {"name": "MyGov India", "url": "https://www.mygov.in/", "use": "Government campaigns, initiatives", "priority": 100},
        {"name": "PM India", "url": "https://www.pmindia.gov.in/", "use": "PM announcements, speeches, visits", "priority": 100},
        {"name": "Cabinet Secretariat", "url": "https://cabsec.gov.in/", "use": "Cabinet decisions", "priority": 100},
    ],
    "agriculture_core": [
        {"name": "ICAR", "url": "https://icar.org.in/", "use": "Research, institutes, technology — Apex body", "priority": 100, "notes": "Monitor entire ICAR ecosystem: IARI/IVRI/NDRI via https://icar.org.in/en/institutes"},
        {"name": "APEDA", "url": "https://apeda.gov.in/", "use": "Agri exports", "priority": 95},
        {"name": "NHB", "url": "https://nhb.gov.in/", "use": "Horticulture", "priority": 95},
        {"name": "FSSAI", "url": "https://www.fssai.gov.in/", "use": "Food safety", "priority": 95},
        {"name": "DAH&D", "url": "https://dahd.gov.in/", "use": "Dairy, livestock", "priority": 95},
        {"name": "Dept of Fisheries", "url": "https://dof.gov.in/", "use": "Fisheries", "priority": 95},
        {"name": "ICFRE", "url": "https://icfre.gov.in/", "use": "Forestry", "priority": 95},
        {"name": "IMD", "url": "https://mausam.imd.gov.in/", "use": "Weather, monsoon, climate", "priority": 95},
    ],
    "banking_finance": [
        {"name": "RBI", "url": "https://www.rbi.org.in/", "use": "Banking, monetary policy, notifications", "priority": 100, "notes": "RSS: https://www.rbi.org.in/pressreleases_rss.xml + https://www.rbi.org.in/notifications_rss.xml"},
        {"name": "SEBI", "url": "https://www.sebi.gov.in/", "use": "Capital markets, regulations", "priority": 100, "notes": "RSS: https://www.sebi.gov.in/sebirss.xml"},
        {"name": "Dept of Financial Services", "url": "https://financialservices.gov.in/", "use": "Banking/financial services", "priority": 95},
        {"name": "PFRDA", "url": "https://www.pfrda.org.in/", "use": "Pension sector", "priority": 95},
        {"name": "IRDAI", "url": "https://irdai.gov.in/", "use": "Insurance", "priority": 95},
        {"name": "IFSCA", "url": "https://ifsca.gov.in/", "use": "Financial services/IFSC", "priority": 95},
    ],
    "economy_data": [
        {"name": "MoSPI", "url": "https://www.mospi.gov.in/", "use": "GDP, CPI, statistics", "priority": 100},
        {"name": "Economic Survey", "url": "https://www.indiabudget.gov.in/economicsurvey/", "use": "Economy", "priority": 100},
        {"name": "Union Budget", "url": "https://www.indiabudget.gov.in/", "use": "Budget", "priority": 100},
        {"name": "NITI Aayog", "url": "https://www.niti.gov.in/", "use": "Reports, indices, policy", "priority": 100},
        {"name": "CCI", "url": "https://www.cci.gov.in/", "use": "Competition/economy", "priority": 90},
        {"name": "GST Council", "url": "https://gstcouncil.gov.in/", "use": "GST", "priority": 90},
    ],
    "international_primary": [
        {"name": "United Nations", "url": "https://www.un.org/", "use": "UN events, international affairs", "priority": 100},
        {"name": "UN News", "url": "https://news.un.org/", "use": "International news", "priority": 100, "notes": "RSS: https://news.un.org/feed/subscribe/en/news/all/rss.xml"},
        {"name": "FAO", "url": "https://www.fao.org/", "use": "Agriculture, food, fisheries", "priority": 100},
        {"name": "World Bank", "url": "https://www.worldbank.org/", "use": "Economy/development", "priority": 100},
        {"name": "WTO", "url": "https://www.wto.org/", "use": "Trade", "priority": 100},
        {"name": "WHO", "url": "https://www.who.int/", "use": "Health — newsroom", "priority": 100, "notes": "RSS: https://www.who.int/rss-feeds/news-english.xml"},
        {"name": "UNESCO", "url": "https://www.unesco.org/", "use": "Education/culture/science", "priority": 100},
        {"name": "UNEP", "url": "https://www.unep.org/", "use": "Environment", "priority": 100},
        {"name": "ILO", "url": "https://www.ilo.org/", "use": "Labour", "priority": 100},
        {"name": "UNFCCC", "url": "https://unfccc.int/", "use": "Climate", "priority": 100},
    ],
    "ministries": [
        {"name": "Ministry of Rural Development", "url": "https://rural.gov.in/", "priority": 95},
        {"name": "Ministry of Food Processing Industries", "url": "https://mofpi.gov.in/", "priority": 95},
        {"name": "DST", "url": "https://dst.gov.in/", "priority": 90},
        {"name": "ISRO", "url": "https://www.isro.gov.in/", "priority": 90, "notes": "RSS: https://www.isro.gov.in/rss.xml"},
        {"name": "DRDO", "url": "https://www.drdo.gov.in/", "priority": 90},
        {"name": "MoEFCC", "url": "https://moef.gov.in/", "priority": 90},
        {"name": "CPCB", "url": "https://cpcb.nic.in/", "priority": 90},
        {"name": "Ministry of Education", "url": "https://www.education.gov.in/", "priority": 90},
        {"name": "UGC", "url": "https://www.ugc.gov.in/", "priority": 90},
    ],
    "awards_appointments": [
        {"name": "Rashtrapati Bhavan", "url": "https://www.presidentofindia.gov.in/", "priority": 95},
        {"name": "PMO", "url": "https://www.pmindia.gov.in/", "priority": 95},
        {"name": "Election Commission", "url": "https://eci.gov.in/", "priority": 95},
    ]
}

# ── EXPLICIT RSS FEEDS (added 2026-10-05) — collector hits these FIRST (RSS-first), homepage is fallback
# Derived from india-policy-intelligence + GK-Parchi + scrape + live test
TIER_1_RSS_FEEDS = [
    {"name": "PIB RSS", "url": "https://www.pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3", "source": "PIB", "priority": 100},
    {"name": "RBI Press Releases RSS", "url": "https://www.rbi.org.in/pressreleases_rss.xml", "source": "RBI", "priority": 100},
    {"name": "RBI Notifications RSS", "url": "https://www.rbi.org.in/notifications_rss.xml", "source": "RBI", "priority": 100},
    {"name": "SEBI RSS", "url": "https://www.sebi.gov.in/sebirss.xml", "source": "SEBI", "priority": 100},
    {"name": "UN News RSS", "url": "https://news.un.org/feed/subscribe/en/news/all/rss.xml", "source": "UN News", "priority": 95},
    {"name": "WHO News RSS", "url": "https://www.who.int/rss-feeds/news-english.xml", "source": "WHO", "priority": 90},
    {"name": "ISRO RSS", "url": "https://www.isro.gov.in/rss.xml", "source": "ISRO", "priority": 90},
    {"name": "NewsOnAir National RSS", "url": "https://newsonair.gov.in/category/national/feed/", "source": "NewsOnAir", "priority": 90},
    {"name": "NewsOnAir Business RSS", "url": "https://newsonair.gov.in/category/business/feed/", "source": "NewsOnAir", "priority": 90},
]

TIER_2_DISCOVERY = [
    {"name": "The Hindu", "url": "https://www.thehindu.com/", "priority": 80, "rss": "https://www.thehindu.com/news/national/feeder/default.rss"},
    {"name": "Business Standard", "url": "https://www.business-standard.com/", "priority": 80},
    {"name": "Mint", "url": "https://www.livemint.com/", "priority": 80},
    {"name": "Economic Times", "url": "https://economictimes.indiatimes.com/", "priority": 80},
]

# Tier-2 RSS (explicit)
TIER_2_RSS_FEEDS = [
    {"name": "The Hindu National RSS", "url": "https://www.thehindu.com/news/national/feeder/default.rss", "source": "The Hindu", "priority": 80},
    {"name": "The Hindu Business RSS", "url": "https://www.thehindu.com/business/feeder/default.rss", "source": "The Hindu", "priority": 80},
    {"name": "The Hindu SciTech RSS", "url": "https://www.thehindu.com/sci-tech/feeder/default.rss", "source": "The Hindu", "priority": 80},
    {"name": "The Hindu Sports RSS", "url": "https://www.thehindu.com/sport/feeder/default.rss", "source": "The Hindu", "priority": 80},
    {"name": "The Hindu International RSS", "url": "https://www.thehindu.com/news/international/feeder/default.rss", "source": "The Hindu", "priority": 80},
]

TIER_3_AGGREGATORS = [
    {"name": "Google News RSS Search (primary discovery bypass)", "url": "https://news.google.com/rss/search?q=site:pib.gov.in+OR+site:rbi.org.in+OR+site:icar.org.in+OR+site:sebi.gov.in&hl=en-IN&gl=IN&ceid=IN:en", "priority": 60},
    {"name": "Google News", "priority": 60},
    {"name": "GDELT", "priority": 60},
    {"name": "NewsAPI", "priority": 60},
]

# Top core monitoring (updated to working only)
TOP_10_CORE = ["PIB", "ICAR", "RBI", "SEBI", "MoSPI", "NITI Aayog", "IMD", "ISRO", "UN News", "WHO"]

# Source reliability scoring for Final Selection
SOURCE_SCORE = {
    "Official Primary": 100,
    "International Primary": 100,
    "Regulator/Institution": 95,
    "Reuters/Trusted News": 90,
    "Major Newspaper": 80,
    "Aggregator": 60,
    "Social Media": 0,
}

# Flow: Secondary News -> Discovery -> Primary Source Search -> Verification -> Only then Student PDF
# REMOVED 2026-10-05 (dead 18): Ministry of Agriculture & Farmers Welfare (agriwelfare 403), IARI, DARE, CACP, NABARD (timeout), Ministry of Finance, DEA, NPCI (403), IMF (403), UNDP (403), IEA (403), Ministry of Cooperation, Ministry of Consumer Affairs, DBT, NTA, Ministry of Defence, MEA (403), UPSC — all covered via PIB GoogleNews fallback if critical
