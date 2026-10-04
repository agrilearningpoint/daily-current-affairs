# -*- coding: utf-8 -*-
"""
AGRI LEARNING POINT — FINAL SOURCE LIST (Priority Tiers)
Tier-1 = Primary/Official (PIB is nodal), Tier-2 = Trusted News Discovery, Tier-3 = Aggregators
GitHub = Technology only, not factual source
"""

# Tier-1 MUST USE — Highest priority for Fact Verification Agent
# NOTE (2026-10-04 LIVE-VERIFIED round 2): every URL below was fetched with a browser UA.
# Replacements made: iari.res.in (TLS handshake fails from datacenter IPs -> www mirror works),
# cacp.dacnet.nic.in (host unreachable -> CACP releases via PIB; use pib.gov.in + Google News site:pib.gov.in "CACP"),
# mospi.gov.in (JS shell, no static content -> press releases available via PIB MoSPI tag),
# news.un.org (404/anti-bot -> www.un.org/en/news), finmin/dea (nic legacy hosts down -> debtindia.gov.in + indiabudget.gov.in),
# rural/cooperation/dbt/mod/upsc/consumeraffairs (SSL/timeout from CI runners -> kept as canonical reference URLs;
#   collector reaches their CONTENT reliably via config/feeds.py Google-News site-search instead).
TIER_1_SOURCES = {
    "govt_national": [
        {"name": "PIB — Press Information Bureau", "url": "https://www.pib.gov.in/", "rss": "https://news.google.com/rss/search?q=%22Press%20Information%20Bureau%22%20when:1d&hl=en-IN&gl=IN&ceid=IN:en", "use": "Government schemes, Cabinet decisions, ministries, national news", "priority": 100, "notes": "Also backgrounders, factsheets, FAQs, features, infographics for Static Facts/Explanations"},
        {"name": "India.gov.in", "url": "https://www.india.gov.in/", "rss": "https://news.google.com/rss/search?q=site:india.gov.in%20when:7d&hl=en-IN&gl=IN&ceid=IN:en", "use": "Government information", "priority": 100},
        {"name": "MyGov India", "url": "https://www.mygov.in/", "use": "Government campaigns, initiatives", "priority": 100},
        {"name": "PM India", "url": "https://www.pmindia.gov.in/", "use": "PM announcements, speeches, visits", "priority": 100},
        {"name": "Cabinet Secretariat", "url": "https://cabsec.gov.in/", "use": "Cabinet decisions", "priority": 100},
    ],
    "agriculture_core": [
        {"name": "Ministry of Agriculture & Farmers Welfare", "url": "https://agriwelfare.gov.in/", "rss": "https://news.google.com/rss/search?q=site:pib.gov.in%20%22Agriculture%20and%20Farmers%20Welfare%22%20when:2d&hl=en-IN&gl=IN&ceid=IN:en", "use": "Schemes, policies, agriculture news", "priority": 100},
        {"name": "ICAR", "url": "https://icar.org.in/", "rss": "https://icar.org.in/rss.xml", "use": "Research, institutes, technology, agriculture developments — Apex body for agri, horticulture, fisheries, animal sciences", "priority": 100, "notes": "Monitor entire ICAR ecosystem: IARI, IVRI, NDRI, crop/horticulture/fisheries institutes via https://icar.org.in/en/institutes"},
        {"name": "IARI", "url": "https://www.iari.res.in/", "use": "Agricultural research", "priority": 100},
        {"name": "DARE", "url": "https://dare.gov.in/", "rss": "https://news.google.com/rss/search?q=DARE%20%22Department%20of%20Agricultural%20Research%20and%20Education%22%20when:3d&hl=en-IN&gl=IN&ceid=IN:en", "use": "Agricultural research & education (SSL-strict; collector uses Google News site:dare.gov.in)", "priority": 100},
        {"name": "APEDA", "url": "https://apeda.gov.in/", "rss": "https://news.google.com/rss/search?q=APEDA%20when:7d&hl=en-IN&gl=IN&ceid=IN:en", "use": "Agri exports", "priority": 95},
        {"name": "NHB", "url": "https://nhb.gov.in/", "rss": "https://news.google.com/rss/search?q=%22National%20Horticulture%20Board%22%20when:14d&hl=en-IN&gl=IN&ceid=IN:en", "use": "Horticulture", "priority": 95},
        {"name": "FSSAI", "url": "https://www.fssai.gov.in/", "rss": "https://news.google.com/rss/search?q=FSSAI%20when:5d&hl=en-IN&gl=IN&ceid=IN:en", "use": "Food safety", "priority": 95},
        {"name": "DAH&D", "url": "https://dahd.gov.in/", "use": "Dairy, livestock", "priority": 95},
        {"name": "Dept of Fisheries", "url": "https://dof.gov.in/", "rss": "https://news.google.com/rss/search?q=%22Department%20of%20Fisheries%22%20India%20when:14d&hl=en-IN&gl=IN&ceid=IN:en", "use": "Fisheries", "priority": 95},
        {"name": "ICFRE", "url": "https://icfre.gov.in/", "rss": "https://news.google.com/rss/search?q=%22Forest%20Research%20Survey%22%20OR%20ICFRE%20when:30d&hl=en-IN&gl=IN&ceid=IN:en", "use": "Forestry", "priority": 95},
        {"name": "IMD", "url": "https://mausam.imd.gov.in/", "rss": "https://news.google.com/rss/search?q=IMD%20%22India%20Meteorological%20Department%22%20when:3d&hl=en-IN&gl=IN&ceid=IN:en", "use": "Weather, monsoon, climate", "priority": 95},
        {"name": "CACP", "url": "https://cacp.dacnet.nic.in/", "rss": "https://news.google.com/rss/search?q=CACP%20OR%20%22Commission%20for%20Agricultural%20Costs%20and%20Prices%22%20MSP%20when:7d&hl=en-IN&gl=IN&ceid=IN:en", "use": "MSP/agricultural prices — host often unreachable from CI; MSP announcements verified via PIB (site:pib.gov.in CACP)", "priority": 95},
    ],
    "banking_finance": [
        {"name": "RBI", "url": "https://www.rbi.org.in/", "rss": "https://news.google.com/rss/search?q=site:rbi.org.in%20when:2d&hl=en-IN&gl=IN&ceid=IN:en", "use": "Banking, monetary policy, notifications", "priority": 100},
        {"name": "NABARD", "url": "https://www.nabard.org/", "rss": "https://news.google.com/rss/search?q=NABARD%20when:2d&hl=en-IN&gl=IN&ceid=IN:en", "use": "Agriculture finance, rural development", "priority": 100},
        {"name": "SEBI", "url": "https://www.sebi.gov.in/", "rss": "https://news.google.com/rss/search?q=SEBI%20when:2d&hl=en-IN&gl=IN&ceid=IN:en", "use": "Capital markets, regulations — press releases/public notices/speeches", "priority": 100},
        {"name": "Ministry of Finance", "url": "https://www.indiabudget.gov.in/", "rss": "https://news.google.com/rss/search?q=%22Finance%20Minister%22%20India%20Budget%20when:2d&hl=en-IN&gl=IN&ceid=IN:en", "use": "Finance, taxation, policies (finmin.gov.in/finmin.nic.in down — indiabudget is live official portal)", "priority": 100},
        {"name": "DEA", "url": "https://debtindia.gov.in/", "rss": "https://news.google.com/rss/search?q=%22Department%20of%20Economic%20Affairs%22%20when:3d&hl=en-IN&gl=IN&ceid=IN:en", "use": "Economy, Budget, inflation, forex (dea.gov.in SSL/host down; Public Debt Office official mirror; FDI/Macro data via PIB 'Department of Economic Affairs')", "priority": 100},
        {"name": "Dept of Financial Services", "url": "https://financialservices.gov.in/", "rss": "https://news.google.com/rss/search?q=%22Department%20of%20Financial%20Services%22%20India%20when:7d&hl=en-IN&gl=IN&ceid=IN:en", "use": "Banking/financial services", "priority": 95},
        {"name": "NPCI", "url": "https://www.npci.org.in/", "rss": "https://news.google.com/rss/search?q=NPCI%20UPI%20when:5d&hl=en-IN&gl=IN&ceid=IN:en", "use": "UPI, digital payments", "priority": 95},
        {"name": "PFRDA", "url": "https://www.pfrda.org.in/", "rss": "https://news.google.com/rss/search?q=PFRDA%20OR%20%22Atal%20Pension%22%20when:14d&hl=en-IN&gl=IN&ceid=IN:en", "use": "Pension sector", "priority": 95},
        {"name": "IRDAI", "url": "https://irdai.gov.in/", "rss": "https://news.google.com/rss/search?q=IRDAI%20insurance%20when:7d&hl=en-IN&gl=IN&ceid=IN:en", "use": "Insurance", "priority": 95},
        {"name": "IFSCA", "url": "https://ifsca.gov.in/", "rss": "https://news.google.com/rss/search?q=IFSCA%20GIFT%20City%20when:30d&hl=en-IN&gl=IN&ceid=IN:en", "use": "Financial services/IFSC", "priority": 95},
    ],
    "economy_data": [
        {"name": "MoSPI", "url": "https://www.mospi.gov.in/", "rss": "https://news.google.com/rss/search?q=%22Ministry%20of%20Statistics%22%20OR%20MoSPI%20GDP%20OR%20CPI%20when:5d&hl=en-IN&gl=IN&ceid=IN:en", "use": "GDP, CPI, statistics (site is JS-rendered; collector reads MoSPI releases via PIB 'Ministry of Statistics' + Google News site:mospi.gov.in)", "priority": 100},
        {"name": "Economic Survey", "url": "https://www.indiabudget.gov.in/economicsurvey/", "rss": "https://news.google.com/rss/search?q=%22Economic%20Survey%22%20India%20when:30d&hl=en-IN&gl=IN&ceid=IN:en", "use": "Economy", "priority": 100},
        {"name": "Union Budget", "url": "https://www.indiabudget.gov.in/", "rss": "https://news.google.com/rss/search?q=%22Union%20Budget%22%20India%20when:14d&hl=en-IN&gl=IN&ceid=IN:en", "use": "Budget", "priority": 100},
        {"name": "NITI Aayog", "url": "https://www.niti.gov.in/", "rss": "https://www.niti.gov.in/rss.xml", "use": "Reports, indices, policy", "priority": 100},
        {"name": "CCI", "url": "https://www.cci.gov.in/", "rss": "https://news.google.com/rss/search?q=%22Competition%20Commission%20of%20India%22%20when:14d&hl=en-IN&gl=IN&ceid=IN:en", "use": "Competition/economy", "priority": 90},
        {"name": "GST Council", "url": "https://gstcouncil.gov.in/", "use": "GST", "priority": 90},
    ],
    "international_primary": [
        {"name": "United Nations", "url": "https://www.un.org/en/", "rss": "https://news.google.com/rss/search?q=%22United%20Nations%22%20Secretary-General%20when:1d&hl=en&gl=US&ceid=US:en", "use": "UN events, international affairs", "priority": 100},
        {"name": "UN News", "url": "https://press.un.org/en/", "rss": "https://news.google.com/rss/search?q=site:un.org%20OR%20site:press.un.org%20when:2d&hl=en&gl=US&ceid=US:en", "use": "International news (news.un.org anti-bot/404 from CI; press.un.org is official UN newsroom mirror)", "priority": 100},
        {"name": "FAO", "url": "https://www.fao.org/", "rss": "https://news.google.com/rss/search?q=FAO%20food%20agriculture%20report%20when:2d&hl=en&gl=US&ceid=US:en", "use": "Agriculture, food, fisheries", "priority": 100},
        {"name": "World Bank", "url": "https://www.worldbank.org/", "rss": "https://news.google.com/rss/search?q=%22World%20Bank%22%20report%20OR%20loan%20OR%20India%20when:2d&hl=en&gl=US&ceid=US:en", "use": "Economy/development", "priority": 100},
        {"name": "IMF", "url": "https://www.imf.org/", "rss": "https://news.google.com/rss/search?q=IMF%20%22International%20Monetary%20Fund%22%20when:2d&hl=en&gl=US&ceid=US:en", "use": "Global economy/finance — news feed", "priority": 100},
        {"name": "WTO", "url": "https://www.wto.org/", "rss": "https://news.google.com/rss/search?q=WTO%20%22World%20Trade%20Organization%22%20when:3d&hl=en&gl=US&ceid=US:en", "use": "Trade", "priority": 100},
        {"name": "WHO", "url": "https://www.who.int/", "rss": "https://www.who.int/rss-feeds/news-english.xml", "use": "Health — newsroom", "priority": 100},
        {"name": "UNESCO", "url": "https://www.unesco.org/", "rss": "https://news.google.com/rss/search?q=UNESCO%20when:3d&hl=en&gl=US&ceid=US:en", "use": "Education/culture/science", "priority": 100},
        {"name": "UNEP", "url": "https://www.unep.org/", "rss": "https://news.google.com/rss/search?q=UNEnvironment%20OR%20UNEP%20when:3d&hl=en&gl=US&ceid=US:en", "use": "Environment", "priority": 100},
        {"name": "UNDP", "url": "https://www.undp.org/", "rss": "https://news.google.com/rss/search?q=UNDP%20when:5d&hl=en&gl=US&ceid=US:en", "use": "Development", "priority": 100},
        {"name": "ILO", "url": "https://www.ilo.org/", "rss": "https://news.google.com/rss/search?q=%22International%20Labour%20Organization%22%20OR%20ILO%20when:7d&hl=en&gl=US&ceid=US:en", "use": "Labour", "priority": 100},
        {"name": "UNFCCC", "url": "https://unfccc.int/", "rss": "https://news.google.com/rss/search?q=COP31%20OR%20UNFCCC%20climate%20talks%20when:5d&hl=en&gl=US&ceid=US:en", "use": "Climate", "priority": 100},
        {"name": "IEA", "url": "https://www.iea.org/", "rss": "https://news.google.com/rss/search?q=%22International%20Energy%20Agency%22%20when:5d&hl=en&gl=US&ceid=US:en", "use": "Energy", "priority": 100},
    ],
    "ministries": [
        {"name": "Ministry of Rural Development", "url": "https://rural.gov.in/", "rss": "https://news.google.com/rss/search?q=%22Ministry%20of%20Rural%20Development%22%20India%20when:3d&hl=en-IN&gl=IN&ceid=IN:en", "priority": 95},
        {"name": "Ministry of Cooperation", "url": "https://cooperation.gov.in/", "rss": "https://news.google.com/rss/search?q=%22Ministry%20of%20Cooperation%22%20India%20when:3d&hl=en-IN&gl=IN&ceid=IN:en", "priority": 95},
        {"name": "Ministry of Food Processing Industries", "url": "https://mofpi.gov.in/", "rss": "https://news.google.com/rss/search?q=%22Food%20Processing%20Industries%22%20Ministry%20when:3d&hl=en-IN&gl=IN&ceid=IN:en", "priority": 95},
        {"name": "Ministry of Consumer Affairs", "url": "https://consumeraffairs.nic.in/", "rss": "https://news.google.com/rss/search?q=%22Consumer%20Affairs%22%20Ministry%20India%20when:3d&hl=en-IN&gl=IN&ceid=IN:en", "priority": 95},
        {"name": "DST", "url": "https://dst.gov.in/", "rss": "https://news.google.com/rss/search?q=%22Science%20and%20Technology%20Ministry%22%20India%20when:3d&hl=en-IN&gl=IN&ceid=IN:en", "priority": 90},
        {"name": "ISRO", "url": "https://www.isro.gov.in/", "rss": "https://news.google.com/rss/search?q=ISRO%20launch%20OR%20mission%20when:3d&hl=en-IN&gl=IN&ceid=IN:en", "priority": 90},
        {"name": "DBT", "url": "https://dbtindia.gov.in/", "rss": "https://news.google.com/rss/search?q=%22Direct%20Benefit%20Transfer%22%20DBT%20India%20when:7d&hl=en-IN&gl=IN&ceid=IN:en", "priority": 90},
        {"name": "DRDO", "url": "https://www.drdo.gov.in/", "rss": "https://news.google.com/rss/search?q=DRDO%20missile%20OR%20defence%20research%20when:7d&hl=en-IN&gl=IN&ceid=IN:en", "priority": 90},
        {"name": "MoEFCC", "url": "https://moef.gov.in/", "rss": "https://news.google.com/rss/search?q=%22environment%20ministry%22%20OR%20MoEFCC%20India%20when:3d&hl=en-IN&gl=IN&ceid=IN:en", "priority": 90},
        {"name": "CPCB", "url": "https://cpcb.nic.in/", "rss": "https://news.google.com/rss/search?q=CPCB%20OR%20%22Pollution%20Control%20Board%22%20when:7d&hl=en-IN&gl=IN&ceid=IN:en", "priority": 90},
        {"name": "Ministry of Education", "url": "https://www.education.gov.in/", "rss": "https://news.google.com/rss/search?q=%22Education%20Ministry%22%20India%20OR%20NEP%20when:3d&hl=en-IN&gl=IN&ceid=IN:en", "priority": 90},
        {"name": "UGC", "url": "https://www.ugc.gov.in/", "rss": "https://news.google.com/rss/search?q=UGC%20NET%20OR%20%22University%20Grants%20Commission%22%20when:7d&hl=en-IN&gl=IN&ceid=IN:en", "priority": 90},
        {"name": "NTA", "url": "https://nta.ac.in/", "rss": "https://news.google.com/rss/search?q=NTA%20NEET%20OR%20JEE%20when:3d&hl=en-IN&gl=IN&ceid=IN:en", "priority": 90},
        {"name": "Ministry of Defence", "url": "https://mod.gov.in/", "rss": "https://news.google.com/rss/search?q=%22Ministry%20of%20Defence%22%20India%20when:2d&hl=en-IN&gl=IN&ceid=IN:en", "priority": 90},
        {"name": "MEA", "url": "https://www.mea.gov.in/news.htm", "rss": "https://news.google.com/rss/search?q=%22Ministry%20of%20External%20Affairs%22%20India%20when:2d&hl=en-IN&gl=IN&ceid=IN:en", "use": "Bilateral, international visits, treaties — Media Centre", "priority": 100},
    ],
    "awards_appointments": [
        {"name": "Rashtrapati Bhavan", "url": "https://www.presidentofindia.gov.in/en", "priority": 95},
        {"name": "PMO", "url": "https://www.pmindia.gov.in/", "priority": 95},
        {"name": "Election Commission", "url": "https://eci.gov.in/", "rss": "https://news.google.com/rss/search?q=%22Election%20Commission%22%20India%20when:1d&hl=en-IN&gl=IN&ceid=IN:en", "priority": 95},
        {"name": "UPSC", "url": "https://upsc.gov.in/", "rss": "https://news.google.com/rss/search?q=UPSC%20notification%20when:5d&hl=en-IN&gl=IN&ceid=IN:en", "priority": 95},
    ]
}

TIER_2_DISCOVERY = [
    {"name": "Reuters", "url": "https://www.reuters.com/", "priority": 90, "role": "Discovery only — must verify via Tier-1"},
    {"name": "The Hindu", "url": "https://www.thehindu.com/", "priority": 80},
    {"name": "Indian Express", "url": "https://indianexpress.com/", "priority": 80},
    {"name": "Business Standard", "url": "https://www.business-standard.com/", "priority": 80},
    {"name": "Mint", "url": "https://www.livemint.com/", "priority": 80},
    {"name": "Economic Times", "url": "https://economictimes.indiatimes.com/", "priority": 80},
]

TIER_3_AGGREGATORS = [
    {"name": "Google News", "priority": 60},
    {"name": "Google News RSS", "priority": 60},
    {"name": "GDELT", "priority": 60},
    {"name": "NewsAPI", "priority": 60},
]

# Top 10 core monitoring (most important)
TOP_10_CORE = ["PIB", "Ministry of Agriculture", "ICAR", "IARI", "RBI", "NABARD", "SEBI", "MoSPI", "NITI Aayog", "MEA"]

# Source reliability scoring for Final Selection
SOURCE_SCORE = {
    "Official Primary": 100,
    "International Primary": 100,
    "Regulator/Institution": 95,
    "Reuters/Trusted News": 90,
    "Major Newspaper": 80,
    "Aggregator": 60,
    "Social Media": 0,  # Discovery Only
}

# Flow: Secondary News -> Discovery -> Primary Source Search -> Verification -> Only then Student PDF
