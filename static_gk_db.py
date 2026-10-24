#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bilingual Static GK Database & Lookup Engine (English + Hindi)
==============================================================
Provides structured bilingual Static GK facts (Establishment, Headquarters,
Nodal Ministry, Key Heads, Acts, and Schemes) for entities mentioned in
Daily Current Affairs, formatted identically to the Exam Genius Bilingual PDF.
"""

from __future__ import annotations
from typing import Dict, List, Any

# Each entry maps an entity keyword/alias to a list of bilingual pairs:
# {"en": "Bullet in English", "hi": "Bullet in Hindi", "slash": "Combined EN / HI line"}
STATIC_GK_BILINGUAL_DB: Dict[str, List[Dict[str, str]]] = {
    "SBI": [
        {
            "en": "SBI establishment: 1 July 1955.",
            "hi": "SBI की स्थापना: 1 जुलाई 1955।",
        },
        {
            "en": "SBI headquarters: Mumbai, Maharashtra.",
            "hi": "SBI का मुख्यालय: मुंबई, महाराष्ट्र।",
        },
        {
            "en": "SBI nationalisation: 1955.",
            "hi": "SBI का राष्ट्रीयकरण: 1955।",
        },
        {
            "en": "Imperial Bank of India formed: 1921 (merged to form SBI in 1955).",
            "hi": "इम्पीरियल बैंक ऑफ इंडिया का गठन: 1921 (1955 में SBI में विलय)।",
        },
    ],
    "RBI": [
        {
            "en": "RBI establishment: 1 April 1935.",
            "hi": "RBI की स्थापना: 1 अप्रैल 1935।",
        },
        {
            "en": "RBI headquarters: Mumbai, Maharashtra.",
            "hi": "RBI का मुख्यालय: मुंबई, महाराष्ट्र।",
        },
        {
            "en": "Banking Regulation Act: 1949.",
            "hi": "बैंकिंग विनियमन अधिनियम: 1949।",
        },
        {
            "en": "RBI nationalisation: 1 January 1949.",
            "hi": "RBI का राष्ट्रीयकरण: 1 जनवरी 1949।",
        },
        {
            "en": "DICGC establishment: 1978 (Headquarters: Mumbai).",
            "hi": "DICGC की स्थापना: 1978 (मुख्यालय: मुंबई)।",
        },
    ],
    "NABARD": [
        {
            "en": "NABARD full form: National Bank for Agriculture and Rural Development.",
            "hi": "NABARD का पूरा नाम: राष्ट्रीय कृषि और ग्रामीण विकास बैंक।",
        },
        {
            "en": "NABARD establishment: 12 July 1982.",
            "hi": "NABARD की स्थापना: 12 जुलाई 1982।",
        },
        {
            "en": "NABARD headquarters: Mumbai, Maharashtra.",
            "hi": "NABARD का मुख्यालय: मुंबई, महाराष्ट्र।",
        },
        {
            "en": "Recommended by: B. Sivaraman Committee (CRAFICARD).",
            "hi": "किस समिति की सिफारिश पर स्थापना: बी. शिवरामन समिति (CRAFICARD)।",
        },
        {
            "en": "Nodal Ministry: Ministry of Finance, Government of India.",
            "hi": "नोडल मंत्रालय: वित्त मंत्रालय, भारत सरकार।",
        },
    ],
    "ICAR": [
        {
            "en": "ICAR full form: Indian Council of Agricultural Research.",
            "hi": "ICAR का पूरा नाम: भारतीय कृषि अनुसंधान परिषद।",
        },
        {
            "en": "ICAR establishment: 16 July 1929.",
            "hi": "ICAR की स्थापना: 16 जुलाई 1929।",
        },
        {
            "en": "ICAR headquarters: Krishi Bhavan, New Delhi.",
            "hi": "ICAR का मुख्यालय: कृषि भवन, नई दिल्ली।",
        },
        {
            "en": "Nodal Ministry: Ministry of Agriculture and Farmers Welfare.",
            "hi": "नोडल मंत्रालय: कृषि एवं किसान कल्याण मंत्रालय।",
        },
        {
            "en": "Ex-officio President of ICAR: Union Minister of Agriculture and Farmers Welfare.",
            "hi": "ICAR के पदेन अध्यक्ष: केंद्रीय कृषि एवं किसान कल्याण मंत्री।",
        },
    ],
    "APEDA": [
        {
            "en": "APEDA full form: Agricultural and Processed Food Products Export Development Authority.",
            "hi": "APEDA का पूरा नाम: कृषि और प्रसंस्कृत खाद्य उत्पाद निर्यात विकास प्राधिकरण।",
        },
        {
            "en": "APEDA establishment: February 1986 (under APEDA Act, 1985).",
            "hi": "APEDA की स्थापना: फरवरी 1986 (APEDA अधिनियम, 1985 के तहत)।",
        },
        {
            "en": "APEDA headquarters: New Delhi.",
            "hi": "APEDA का मुख्यालय: नई दिल्ली।",
        },
        {
            "en": "Nodal Ministry: Ministry of Commerce and Industry.",
            "hi": "नोडल मंत्रालय: वाणिज्य एवं उद्योग मंत्रालय।",
        },
    ],
    "FCI": [
        {
            "en": "FCI full form: Food Corporation of India.",
            "hi": "FCI का पूरा नाम: भारतीय खाद्य निगम।",
        },
        {
            "en": "FCI establishment: 14 January 1965 (under Food Corporations Act, 1964).",
            "hi": "FCI की स्थापना: 14 जनवरी 1965 (खाद्य निगम अधिनियम, 1964 के तहत)।",
        },
        {
            "en": "FCI headquarters: New Delhi.",
            "hi": "FCI का मुख्यालय: नई दिल्ली।",
        },
        {
            "en": "Nodal Ministry: Ministry of Consumer Affairs, Food and Public Distribution.",
            "hi": "नोडल मंत्रालय: उपभोक्ता मामले, खाद्य एवं सार्वजनिक वितरण मंत्रालय।",
        },
    ],
    "WFP": [
        {
            "en": "World Food Programme (WFP) established: 1961.",
            "hi": "विश्व खाद्य कार्यक्रम (WFP) की स्थापना: 1961।",
        },
        {
            "en": "WFP headquarters: Rome, Italy.",
            "hi": "WFP का मुख्यालय: रोम, इटली।",
        },
        {
            "en": "WFP received the Nobel Peace Prize: 2020.",
            "hi": "WFP को नोबेल शांति पुरस्कार: 2020 में मिला।",
        },
        {
            "en": "National Food Security Act (NFSA): 2013.",
            "hi": "राष्ट्रीय खाद्य सुरक्षा अधिनियम (NFSA): 2013।",
        },
        {
            "en": "PDS nodal ministry: Ministry of Consumer Affairs, Food and Public Distribution.",
            "hi": "PDS का नोडल मंत्रालय: उपभोक्ता मामले, खाद्य एवं सार्वजनिक वितरण मंत्रालय।",
        },
    ],
    "PM-KUSUM": [
        {
            "en": "Nodal Ministry: Ministry of New and Renewable Energy (MNRE).",
            "hi": "नोडल मंत्रालय: नवीन एवं नवीकरणीय ऊर्जा मंत्रालय (MNRE)।",
        },
        {
            "en": "PM-KUSUM launch year: 2019.",
            "hi": "PM-KUSUM की शुरुआत का वर्ष: 2019।",
        },
        {
            "en": "PM-KUSUM Component A: Decentralised grid-connected solar power plants.",
            "hi": "PM-KUSUM घटक A: विकेंद्रीकृत ग्रिड से जुड़े सौर ऊर्जा संयंत्र।",
        },
        {
            "en": "PM-KUSUM Component B: Standalone solar agricultural pumps.",
            "hi": "PM-KUSUM घटक B: स्वतंत्र सौर कृषि पंप।",
        },
        {
            "en": "PM-KUSUM Component C: Solarisation of grid-connected agricultural pumps.",
            "hi": "PM-KUSUM घटक C: ग्रिड से जुड़े कृषि पंपों का सौरकरण।",
        },
        {
            "en": "MNRE Headquarters: New Delhi.",
            "hi": "MNRE का मुख्यालय: नई दिल्ली।",
        },
    ],
    "WORLD BANK": [
        {
            "en": "Organisation – World Bank Group / संगठन – विश्व बैंक समूह",
            "hi": "",
            "mode": "slash",
        },
        {
            "en": "World Bank established – July 1944 (Bretton Woods Conference) / विश्व बैंक की स्थापना – जुलाई 1944",
            "hi": "",
            "mode": "slash",
        },
        {
            "en": "World Bank Headquarters – Washington, D.C., USA / विश्व बैंक का मुख्यालय – वाशिंगटन, डी.सी., अमेरिका",
            "hi": "",
            "mode": "slash",
        },
        {
            "en": "IFC – International Finance Corporation (1956) / IFC – अंतर्राष्ट्रीय वित्त निगम (1956)",
            "hi": "",
            "mode": "slash",
        },
        {
            "en": "MIGA – Multilateral Investment Guarantee Agency (1988) / MIGA – बहुपक्षीय निवेश गारंटी एजेंसी (1988)",
            "hi": "",
            "mode": "slash",
        },
    ],
    "UNESCO": [
        {
            "en": "UNESCO full form: United Nations Educational, Scientific and Cultural Organization.",
            "hi": "UNESCO का पूरा नाम: United Nations Educational, Scientific and Cultural Organization (संयुक्त राष्ट्र शैक्षिक, वैज्ञानिक एवं सांस्कृतिक संगठन)।",
        },
        {
            "en": "UNESCO headquarters: Paris, France.",
            "hi": "UNESCO का मुख्यालय: पेरिस, फ्रांस।",
        },
        {
            "en": "India joined UNESCO: 1946.",
            "hi": "भारत UNESCO में शामिल हुआ: 1946।",
        },
        {
            "en": "World Heritage Convention: 1972 (Ratified by India in 1977).",
            "hi": "विश्व धरोहर अभिसमय: 1972 (भारत ने 1977 में अनुसमर्थन किया)।",
        },
    ],
    "FAO": [
        {
            "en": "FAO full form: Food and Agriculture Organization of the United Nations.",
            "hi": "FAO का पूरा नाम: संयुक्त राष्ट्र खाद्य और कृषि संगठन।",
        },
        {
            "en": "FAO establishment: 16 October 1945 (World Food Day).",
            "hi": "FAO की स्थापना: 16 अक्टूबर 1945 (विश्व खाद्य दिवस)।",
        },
        {
            "en": "FAO headquarters: Rome, Italy.",
            "hi": "FAO का मुख्यालय: रोम, इटली।",
        },
    ],
}

# Legacy compatibility lookup dictionary
STATIC_GK_LOOKUP: Dict[str, Dict[str, str]] = {
    "NABARD": {
        "full_name": "National Bank for Agriculture and Rural Development",
        "established": "12 July 1982",
        "headquarters": "Mumbai, Maharashtra",
        "chairman": "Shaji K V",
    },
    "RBI": {
        "full_name": "Reserve Bank of India",
        "established": "1 April 1935",
        "headquarters": "Mumbai, Maharashtra",
    },
    "ICAR": {
        "full_name": "Indian Council of Agricultural Research",
        "established": "16 July 1929",
        "headquarters": "New Delhi",
    },
    "SBI": {
        "full_name": "State Bank of India",
        "established": "1 July 1955",
        "headquarters": "Mumbai, Maharashtra",
    },
    "APEDA": {
        "full_name": "Agricultural and Processed Food Products Export Development Authority",
        "established": "1986",
        "headquarters": "New Delhi",
    },
    "FCI": {
        "full_name": "Food Corporation of India",
        "established": "14 January 1965",
        "headquarters": "New Delhi",
    },
}


# Curated Bilingual Recent News Headlines by Entity/Theme (Used for the Rounded Blue Revision Box)
RECENT_HEADLINES_BILINGUAL_DB: Dict[str, Dict[str, Any]] = {
    "SBI": {
        "box_title": "Recent News Headlines Related to SBI :",
        "headlines": [
            {
                "en": "SBI Mutual Fund plans to expand its reach in B-30 cities by leveraging the extensive branch network of its parent bank, State Bank of India (SBI).",
                "hi": "SBI म्यूचुअल फंड अपनी मूल बैंक, भारतीय स्टेट बैंक (SBI) के व्यापक शाखा नेटवर्क का उपयोग करके B-30 शहरों में अपनी पहुँच बढ़ाने की योजना बना रहा है।",
            },
            {
                "en": "State Bank of India (SBI), India's largest lender, is spearheading the proposed ₹35,000 crore funding package for Vodafone Idea (Vi), India's third-largest telecom operator.",
                "hi": "भारतीय स्टेट बैंक (SBI), जो भारत का सबसे बड़ा ऋणदाता बैंक है, देश की तीसरी सबसे बड़ी टेलीकॉम कंपनी Vodafone Idea (Vi) के लिए प्रस्तावित ₹35,000 करोड़ के फंडिंग पैकेज का नेतृत्व कर रहा है।",
            },
            {
                "en": "SBI Mutual Fund, India's largest fund house, has launched Aarambh, an assisted digital onboarding service designed to help first-time investors begin their mutual fund journey.",
                "hi": "SBI म्यूचुअल फंड, भारत के सबसे बड़े फंड हाउस, ने Aarambh नामक असिस्टेड डिजिटल ऑनबोर्डिंग सर्विस लॉन्च की है, जिसे पहली बार निवेश करने वालों को म्यूचुअल फंड यात्रा शुरू करने में सहायता देने के लिए बनाया गया है।",
            },
            {
                "en": "State Bank of India (SBI) and its subsidiary SBI Capital Markets Ltd plan to dilute a combined stake of up to 1% in the National Stock Exchange (NSE) through its proposed ₹30,000-crore IPO.",
                "hi": "भारतीय स्टेट बैंक (SBI) और उसकी सहायक कंपनी SBI कैपिटल मार्केट्स लिमिटेड प्रस्तावित ₹30,000 करोड़ के प्रारंभिक सार्वजनिक निर्गम (IPO) के माध्यम से राष्ट्रीय स्टॉक एक्सचेंज (NSE) में संयुक्त रूप से 1% तक हिस्सेदारी बेचने की योजना बना रहे हैं।",
            },
            {
                "en": "State Bank of India (SBI) used Artificial Intelligence (AI) to underwrite nearly ₹1 lakh crore of loans to Micro, Small and Medium Enterprises (MSMEs) during FY2025–26.",
                "hi": "State Bank of India (SBI) ने FY2025–26 के दौरान Micro, Small and Medium Enterprises (MSMEs) के लगभग ₹1 लाख करोड़ के loans का Artificial Intelligence (AI) का उपयोग करके underwriting किया।",
            },
        ],
    },
    "RBI": {
        "box_title": "Recent News Headlines Related to RBI :",
        "headlines": [
            {
                "en": "The Reserve Bank of India (RBI) has approved the amalgamation of the Indian branches of Emirates NBD Bank PJSC with RBL Bank.",
                "hi": "भारतीय रिज़र्व बैंक (RBI) ने Emirates NBD Bank PJSC की भारतीय शाखाओं का RBL Bank में विलय करने की मंजूरी दी है।",
            },
            {
                "en": "According to the Reserve Bank of India (RBI) September 2026 Bulletin, private-sector capital expenditure is projected to rise to ₹3.2 trillion in FY2026–27, compared with ₹2.6 trillion in FY2025–26.",
                "hi": "भारतीय रिज़र्व बैंक (RBI) के सितंबर 2026 बुलेटिन के अनुसार, निजी क्षेत्र का पूंजीगत व्यय वित्त वर्ष 2025–26 के ₹2.6 ट्रिलियन से बढ़कर वित्त वर्ष 2026–27 में ₹3.2 ट्रिलियन होने का अनुमान है।",
            },
            {
                "en": "The RBI set the interest rate on Government of India Floating Rate Bond 2028 (FRB 2028) at 6.45% per annum for the half-year period from October 4, 2026, to April 3, 2027.",
                "hi": "भारतीय रिज़र्व बैंक ने भारत सरकार के फ्लोटिंग रेट बॉन्ड 2028 (FRB 2028) पर 4 अक्टूबर, 2026 से 3 अप्रैल, 2027 तक की छमाही अवधि के लिए ब्याज दर 6.45% प्रतिवर्ष निर्धारित की।",
            },
            {
                "en": "The Reserve Bank of India (RBI) formally removed Paytm Payments Bank Limited (PPBL) from the Second Schedule of the RBI Act, 1934, ending its status as a scheduled bank under the Act.",
                "hi": "भारतीय रिज़र्व बैंक (RBI) ने Paytm Payments Bank Limited (PPBL) को RBI अधिनियम, 1934 की दूसरी अनुसूची से औपचारिक रूप से हटा दिया, जिससे इस अधिनियम के तहत उसका अनुसूचित बैंक का दर्जा समाप्त हो गया।",
            },
            {
                "en": "The Reserve Bank of India (RBI) increased the minimum daily maintenance requirement of the Cash Reserve Ratio (CRR) from 90% to 99%, effective from the fortnight beginning 16 October 2026.",
                "hi": "भारतीय रिज़र्व बैंक (RBI) ने नकद आरक्षित अनुपात (CRR) के लिए न्यूनतम दैनिक रखरखाव की अनिवार्यता 90% से बढ़ाकर 99% कर दी। यह बदलाव 16 अक्टूबर 2026 से शुरू होने वाले पखवाड़े से लागू होगा।",
            },
        ],
    },
    "AGRICULTURE": {
        "box_title": "Recent News Headlines Related to Agriculture & Rural Development :",
        "headlines": [
            {
                "en": "The 10th National Convention of Agrivision–2026 was held on 13–14 October 2026 at the ICAR–National Agricultural Science Complex (NASC), Pusa, New Delhi.",
                "hi": "एग्रीविज़न–2026 का 10वाँ राष्ट्रीय सम्मेलन 13–14 अक्टूबर 2026 को ICAR–नेशनल एग्रीकल्चरल साइंस कॉम्प्लेक्स (NASC), पूसा, नई दिल्ली में आयोजित हुआ।",
            },
            {
                "en": "The Union Cabinet approved the National Mission on Natural Farming (NMNF) with a total outlay of ₹2,481 crore to promote chemical-free sustainable farming across 15,000 clusters.",
                "hi": "केंद्रीय मंत्रिमंडल ने 15,000 क्लस्टरों में रसायन-मुक्त सतत खेती को बढ़ावा देने के लिए ₹2,481 करोड़ के कुल परिव्यय के साथ राष्ट्रीय प्राकृतिक खेती मिशन (NMNF) को मंजूरी दी।",
            },
            {
                "en": "ICAR released 109 climate-resilient, biofortified and high-yielding crop varieties covering cereals, millets, oilseeds, pulses, and horticultural crops.",
                "hi": "ICAR ने अनाज, श्री अन्न (मिलेट्स), तिलहन, दलहन और बागवानी फसलों की 109 जलवायु-अनुकूल, बायोफोर्टिफाइड और उच्च उपज देने वाली किस्में जारी कीं।",
            },
            {
                "en": "Maharashtra inaugurated its first Annapurti Grain ATM in Nashik in collaboration with the United Nations World Food Programme (WFP) for 24×7 PDS ration dispensing.",
                "hi": "महाराष्ट्र ने 24×7 PDS राशन वितरण के लिए संयुक्त राष्ट्र विश्व खाद्य कार्यक्रम (WFP) के सहयोग से नासिक में अपना पहला अन्नपूर्ति ग्रेन ATM शुरू किया।",
            },
            {
                "en": "MNRE announced a dedicated 10 GW Agri-PV (Agrivoltaics) component under PM-KUSUM 2.0 to enable dual use of farmland for solar generation and crop cultivation.",
                "hi": "नवीन एवं नवीकरणीय ऊर्जा मंत्रालय (MNRE) ने सौर ऊर्जा उत्पादन और फसल की खेती के लिए कृषि भूमि के दोहरे उपयोग को सक्षम करने हेतु PM-KUSUM 2.0 के तहत 10 GW के विशेष Agri-PV घटक का प्रस्ताव दिया।",
            },
        ],
    },
    "SUMMITS": {
        "box_title": "Recent News Headlines Related to Summits / Conference :",
        "headlines": [
            {
                "en": "The Capacity Building Commission (CBC) will organise the third regional workshop of Sādhana Śhrinkhla 2026 in Lucknow, Uttar Pradesh, on 23–24 October 2026 under Mission Karmayogi.",
                "hi": "कैपेसिटी बिल्डिंग कमीशन (CBC), मिशन कर्मयोगी के तहत 23–24 अक्टूबर 2026 को उत्तर प्रदेश के लखनऊ में साधना श्रृंखला 2026 की तीसरी क्षेत्रीय कार्यशाला आयोजित करेगा।",
            },
            {
                "en": "The 10th National Convention of Agrivision–2026 was held on 13–14 October 2026 at the ICAR–National Agricultural Science Complex (NASC), Pusa, New Delhi.",
                "hi": "एग्रीविज़न–2026 का 10वाँ राष्ट्रीय सम्मेलन 13–14 अक्टूबर 2026 को ICAR–नेशनल एग्रीकल्चरल साइंस कॉम्प्लेक्स (NASC), पूसा, नई दिल्ली में आयोजित हुआ।",
            },
            {
                "en": "India hosted the first-ever BIMSTEC Home Ministers’ Meeting in New Delhi on 13 October 2026, announced by Union Home Minister Amit Shah.",
                "hi": "भारत ने 13 अक्टूबर 2026 को नई दिल्ली में पहली बार BIMSTEC गृह मंत्रियों की बैठक की मेजबानी की। इसकी घोषणा केंद्रीय गृह मंत्री अमित शाह ने की।",
            },
            {
                "en": "The 5th Kautilya Economic Conclave (KEC 2026) will be held in New Delhi under the theme “Resilience in an Age of Flux.”",
                "hi": "5वां Kautilya Economic Conclave (KEC 2026) नई दिल्ली में “Resilience in an Age of Flux” theme के तहत आयोजित किया जाएगा।",
            },
        ],
    },
    "FIRST_IN_INDIA": {
        "box_title": "Recent News Headlines Related to First in India and World :",
        "headlines": [
            {
                "en": "Union Railway Minister Ashwini Vaishnaw flagged off India’s first stainless-steel salt container freight train from Shivlakha Gati Shakti Cargo Terminal (GCT) in Kachchh, Gujarat, to Mithapur.",
                "hi": "केंद्रीय रेल मंत्री अश्विनी वैष्णव ने गुजरात के कच्छ जिले में स्थित शिवलाखा गति शक्ति कार्गो टर्मिनल (GCT) से मीठापुर के लिए भारत की पहली स्टेनलेस स्टील सॉल्ट कंटेनर मालगाड़ी को रवाना किया।",
            },
            {
                "en": "Keralam launched India’s first statewide Red List Assessment of Ecosystems to evaluate the health of ecosystems and the risk of their collapse.",
                "hi": "केरलम ने पारिस्थितिकी तंत्रों के स्वास्थ्य और उनके नष्ट होने के जोखिम का आकलन करने के लिए भारत का पहला राज्यव्यापी पारिस्थितिकी तंत्र रेड लिस्ट आकलन शुरू किया।",
            },
            {
                "en": "Andhra Pradesh launched India’s first national-level pilot housing project using 3D Concrete Printing (3DCP) technology under Pradhan Mantri Awas Yojana–Gramin (PMAY-G) 2.0.",
                "hi": "आंध्र प्रदेश ने प्रधानमंत्री आवास योजना–ग्रामीण (PMAY-G) 2.0 के तहत 3D कंक्रीट प्रिंटिंग (3DCP) तकनीक से भारत की पहली राष्ट्रीय स्तर की पायलट आवास परियोजना शुरू की।",
            },
            {
                "en": "India’s first port-based e-methanol production facility is being established at Deendayal Port Authority (DPA), Kandla, Gujarat.",
                "hi": "भारत की पहली port-based e-methanol production facility Deendayal Port Authority (DPA), Kandla, Gujarat में स्थापित की जा रही है।",
            },
        ],
    },
    "AWARDS": {
        "box_title": "Recent News Headlines Related to Awards & Winners :",
        "headlines": [
            {
                "en": "International Iconic Scientist Award from Scientific Laurels : Dr. Kannan C.S. Warrier, Director of the Kerala Forest Research Institute (KFRI).",
                "hi": "'साइंटिफिक लॉरेल्स' (Scientific Laurels) की ओर से 'इंटरनेशनल आइकॉनिक साइंटिस्ट अवार्ड' : डॉ. कन्नन सी.एस. वारियर, जो केरल वन अनुसंधान संस्थान (KFRI) के निदेशक हैं।",
            },
            {
                "en": "World’s Best Consumer Bank 2026 by Global Finance magazine : State Bank of India (SBI) for the second consecutive year.",
                "hi": "Global Finance पत्रिका द्वारा लगातार दूसरे वर्ष World’s Best Consumer Bank 2026 : भारतीय स्टेट बैंक (SBI)।",
            },
            {
                "en": "SKOCH Gold Award 2026 in Digital Operational Efficiency : Coal Controller Organisation (CCO) for its in-house digital tool SUVIKALP.",
                "hi": "डिजिटल परिचालन दक्षता श्रेणी में SKOCH गोल्ड अवार्ड 2026 : कोल कंट्रोलर ऑर्गेनाइजेशन (CCO) को उसके इन-हाउस डिजिटल टूल SUVIKALP के लिए।",
            },
            {
                "en": "Chevalier de la Légion d’Honneur (Knight of the Legion of Honour) by French President Emmanuel Macron : Sunil Bharti Mittal, Founder and Chairman of Bharti Enterprises.",
                "hi": "फ्रांसीसी राष्ट्रपति इमैनुएल मैक्रों द्वारा 'शेवेलियर डे ला लीजन डी'ऑनर' सम्मान : सुनील भारती मित्तल, भारती एंटरप्राइजेज के संस्थापक और चेयरमैन।",
            },
        ],
    },
}


def lookup_static_gk(text: str) -> List[Dict[str, str]]:
    """Matches entities in text and returns bilingual Static GK bullet pairs."""
    if not text:
        return []
    upper = text.upper()
    matched: List[Dict[str, str]] = []
    for key, facts in STATIC_GK_BILINGUAL_DB.items():
        if key in upper:
            matched.extend(facts)
            break
    return matched


def lookup_recent_headlines_box(text: str, category: str = "") -> Dict[str, Any] | None:
    """Returns a 'Recent News Headlines Related to ...' box dict if text or category matches."""
    combined = f"{text} {category}".upper()
    if "SBI" in combined or "STATE BANK OF INDIA" in combined:
        return RECENT_HEADLINES_BILINGUAL_DB["SBI"]
    if "RBI" in combined or "RESERVE BANK OF INDIA" in combined:
        return RECENT_HEADLINES_BILINGUAL_DB["RBI"]
    if any(k in combined for k in ["AGRI", "ICAR", "NABARD", "KUSUM", "GRAIN", "WFP", "FARM", "CROP"]):
        return RECENT_HEADLINES_BILINGUAL_DB["AGRICULTURE"]
    if any(k in combined for k in ["SUMMIT", "CONFERENCE", "CONVENTION", "MEETING"]):
        return RECENT_HEADLINES_BILINGUAL_DB["SUMMITS"]
    if any(k in combined for k in ["AWARD", "PURASKAR", "PRIZE", "HONOUR"]):
        return RECENT_HEADLINES_BILINGUAL_DB["AWARDS"]
    if "FIRST" in combined:
        return RECENT_HEADLINES_BILINGUAL_DB["FIRST_IN_INDIA"]
    return None
