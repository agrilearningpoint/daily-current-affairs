# -*- coding: utf-8 -*-
"""
AGRI LEARNING POINT — FINAL SOURCE LIST (Priority Tiers)
Tier-1 = Primary/Official (PIB is nodal), Tier-2 = Trusted News Discovery, Tier-3 = Aggregators
GitHub = Technology only, not factual source
"""

# Tier-1 MUST USE — Highest priority for Fact Verification Agent
TIER_1_SOURCES = {
    "govt_national": [
        {"name": "PIB — Press Information Bureau", "url": "https://www.pib.gov.in/", "use": "Government schemes, Cabinet decisions, ministries, national news", "priority": 100, "notes": "Also backgrounders, factsheets, FAQs, features, infographics for Static Facts/Explanations"},
        {"name": "India.gov.in", "url": "https://www.india.gov.in/", "use": "Government information", "priority": 100},
        {"name": "MyGov India", "url": "https://www.mygov.in/", "use": "Government campaigns, initiatives", "priority": 100},
        {"name": "PM India", "url": "https://www.pmindia.gov.in/", "use": "PM announcements, speeches, visits", "priority": 100},
        {"name": "Cabinet Secretariat", "url": "https://cabsec.gov.in/", "use": "Cabinet decisions", "priority": 100},
    ],
    "agriculture_core": [
        {"name": "Ministry of Agriculture & Farmers Welfare", "url": "https://agriculture.gov.in/", "use": "Schemes, policies, agriculture news", "priority": 100},
        {"name": "ICAR", "url": "https://www.icar.gov.in/", "use": "Research, institutes, technology, agriculture developments — Apex body for agri, horticulture, fisheries, animal sciences", "priority": 100, "notes": "Monitor entire ICAR ecosystem: IARI, IVRI, NDRI, crop/horticulture/fisheries institutes via https://icar.gov.in/en/institutes"},
        {"name": "IARI", "url": "https://iari.res.in/", "use": "Agricultural research", "priority": 100},
        {"name": "DARE", "url": "https://dare.gov.in/", "use": "Agricultural research & education", "priority": 100},
        {"name": "APEDA", "url": "https://apeda.gov.in/", "use": "Agri exports", "priority": 95},
        {"name": "NHB", "url": "https://nhb.gov.in/", "use": "Horticulture", "priority": 95},
        {"name": "FSSAI", "url": "https://www.fssai.gov.in/", "use": "Food safety", "priority": 95},
        {"name": "DAH&D", "url": "https://dahd.nic.in/", "use": "Dairy, livestock", "priority": 95},
        {"name": "Dept of Fisheries", "url": "https://dof.gov.in/", "use": "Fisheries", "priority": 95},
        {"name": "ICFRE", "url": "https://icfre.gov.in/", "use": "Forestry", "priority": 95},
        {"name": "IMD", "url": "https://mausam.imd.gov.in/", "use": "Weather, monsoon, climate", "priority": 95},
        {"name": "CACP", "url": "https://cacp.dacnet.nic.in/", "use": "MSP/agricultural prices", "priority": 95},
    ],
    "banking_finance": [
        {"name": "RBI", "url": "https://www.rbi.org.in/", "use": "Banking, monetary policy, notifications", "priority": 100},
        {"name": "NABARD", "url": "https://www.nabard.org/", "use": "Agriculture finance, rural development", "priority": 100},
        {"name": "SEBI", "url": "https://www.sebi.gov.in/", "use": "Capital markets, regulations — press releases/public notices/speeches", "priority": 100},
        {"name": "Ministry of Finance", "url": "https://finmin.gov.in/", "use": "Finance, taxation, policies", "priority": 100},
        {"name": "DEA", "url": "https://dea.gov.in/", "use": "Economy, Budget, inflation, forex, Union Budget", "priority": 100},
        {"name": "Dept of Financial Services", "url": "https://financialservices.gov.in/", "use": "Banking/financial services", "priority": 95},
        {"name": "NPCI", "url": "https://www.npci.org.in/", "use": "UPI, digital payments", "priority": 95},
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
        {"name": "UN News", "url": "https://news.un.org/", "use": "International news", "priority": 100},
        {"name": "FAO", "url": "https://www.fao.org/", "use": "Agriculture, food, fisheries", "priority": 100},
        {"name": "World Bank", "url": "https://www.worldbank.org/", "use": "Economy/development", "priority": 100},
        {"name": "IMF", "url": "https://www.imf.org/", "use": "Global economy/finance — news feed", "priority": 100},
        {"name": "WTO", "url": "https://www.wto.org/", "use": "Trade", "priority": 100},
        {"name": "WHO", "url": "https://www.who.int/", "use": "Health — newsroom", "priority": 100},
        {"name": "UNESCO", "url": "https://www.unesco.org/", "use": "Education/culture/science", "priority": 100},
        {"name": "UNEP", "url": "https://www.unep.org/", "use": "Environment", "priority": 100},
        {"name": "UNDP", "url": "https://www.undp.org/", "use": "Development", "priority": 100},
        {"name": "ILO", "url": "https://www.ilo.org/", "use": "Labour", "priority": 100},
        {"name": "UNFCCC", "url": "https://unfccc.int/", "use": "Climate", "priority": 100},
        {"name": "IEA", "url": "https://www.iea.org/", "use": "Energy", "priority": 100},
    ],
    "ministries": [
        {"name": "Ministry of Rural Development", "url": "https://rural.gov.in/", "priority": 95},
        {"name": "Ministry of Cooperation", "url": "https://cooperation.gov.in/", "priority": 95},
        {"name": "Ministry of Food Processing Industries", "url": "https://mofpi.gov.in/", "priority": 95},
        {"name": "Ministry of Consumer Affairs", "url": "https://consumeraffairs.nic.in/", "priority": 95},
        {"name": "DST", "url": "https://dst.gov.in/", "priority": 90},
        {"name": "ISRO", "url": "https://www.isro.gov.in/", "priority": 90},
        {"name": "DBT", "url": "https://dbtindia.gov.in/", "priority": 90},
        {"name": "DRDO", "url": "https://www.drdo.gov.in/", "priority": 90},
        {"name": "MoEFCC", "url": "https://moef.gov.in/", "priority": 90},
        {"name": "CPCB", "url": "https://cpcb.nic.in/", "priority": 90},
        {"name": "Ministry of Education", "url": "https://www.education.gov.in/", "priority": 90},
        {"name": "UGC", "url": "https://www.ugc.gov.in/", "priority": 90},
        {"name": "NTA", "url": "https://nta.ac.in/", "priority": 90},
        {"name": "Ministry of Defence", "url": "https://www.mod.gov.in/", "priority": 90},
        {"name": "MEA", "url": "https://www.mea.gov.in/news.htm", "use": "Bilateral, international visits, treaties — Media Centre", "priority": 100},
    ],
    "awards_appointments": [
        {"name": "Rashtrapati Bhavan", "url": "https://www.presidentofindia.gov.in/", "priority": 95},
        {"name": "PMO", "url": "https://www.pmindia.gov.in/", "priority": 95},
        {"name": "Election Commission", "url": "https://www.eci.gov.in/", "priority": 95},
        {"name": "UPSC", "url": "https://upsc.gov.in/", "priority": 95},
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
