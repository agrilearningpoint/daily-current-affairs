"""Deterministic bilingual fixture for PDF generation and QA tests.

This fixture is synthetic and source-grounded: it is NOT real news and must
never be published. It deliberately exercises the parts of the PDF engine that
are easy to break:

* English + Hindi headlines;
* long Hindi paragraphs with conjuncts and matras (क्ष, त्र, श्र, ि ा ी ो ौ);
* dates, percentages, currency values and acronyms;
* an official source link (clickable);
* detailed explanations;
* a Static GK panel;
* five-option MCQs with an answer key;
* category one-liners;
* enough volume to force a multi-page layout.
"""
from __future__ import annotations

from typing import Any

_ITEMS: list[dict[str, Any]] = [
    {
        "event_id": "sample-agri-1",
        "category": "Agriculture",
        "importance_score": 92,
        "headline_en": "Cabinet approves ₹1,250 crore scheme to modernise 500 primary agricultural credit societies",
        "headline_hi": "मंत्रिमंडल ने 500 प्राथमिक कृषि साख समितियों के आधुनिकीकरण हेतु ₹1,250 करोड़ की योजना को मंज़ूरी दी",
        "key_points_en": [
            "The Union Cabinet approved a scheme worth ₹1,250 crore for 500 primary agricultural credit societies (PACS).",
            "The scheme targets computerisation, storage and warehouse capacity in 12 states by March 2027.",
            "Funding is shared 60:40 between the Centre and states; NABARD will be the implementing agency.",
        ],
        "key_points_hi": [
            "केंद्रीय मंत्रिमंडल ने 500 प्राथमिक कृषि साख समितियों के लिए ₹1,250 करोड़ की योजना को मंज़ूरी दी।",
            "योजना का लक्ष्य मार्च 2027 तक 12 राज्यों में कंप्यूटरीकरण, भंडारण एवं गोदाम क्षमता बढ़ाना है।",
            "वित्तपोषण केंद्र और राज्यों के बीच 60:40 अनुपात में होगा; कार्यान्वयन एजेंसी नाबार्ड होगी।",
        ],
        "static_facts": {
            "Established": "NABARD — 12 July 1982",
            "Headquarters": "Mumbai, Maharashtra",
            "Parent body": "Ministry of Finance (Department of Financial Services)",
        },
        "exam_fact_en": "PACS are the smallest and most numerous cooperative credit institutions in India; the scheme strengthens the cooperative credit structure exam candidates are frequently asked about.",
        "exam_fact_hi": "प्राथमिक कृषि साख समितियाँ भारत की सबसे छोटी और सर्वाधिक संख्या वाली सहकारी साख संस्थाएँ हैं।",
        "source": {"name": "PIB", "url": "https://www.pib.gov.in/PressReleasePage.aspx?PRID=000000"},
        "image_path": "",
        "image_caption": "",
    },
    {
        "event_id": "sample-banking-1",
        "category": "Banking & Finance",
        "importance_score": 88,
        "headline_en": "RBI keeps repo rate unchanged at 6.50 per cent; GDP growth projected at 7.1 per cent",
        "headline_hi": "आरबीआई ने रेपो दर 6.50 प्रतिशत पर अपरिवर्तित रखी; जीडीपी वृद्धि 7.1 प्रतिशत रहने का अनुमान",
        "key_points_en": [
            "The Monetary Policy Committee voted 4:2 to hold the repo rate at 6.50 per cent.",
            "Inflation projection for the current financial year was revised to 4.8 per cent.",
            "Gross domestic product growth for 2026-27 is projected at 7.1 per cent.",
        ],
        "key_points_hi": [
            "मौद्रिक नीति समिति ने 4:2 के बहुमत से रेपो दर 6.50 प्रतिशत पर बनाए रखने का निर्णय लिया।",
            "चालू वित्त वर्ष के लिए मुद्रास्फीति अनुमान 4.8 प्रतिशत किया गया।",
            "वर्ष 2026-27 के लिए सकल घरेलू उत्पाद वृद्धि 7.1 प्रतिशत अनुमानित है।",
        ],
        "static_facts": {
            "Established": "RBI — 1 April 1935",
            "Governor": "Office-bearer (verify at edition cutoff)",
            "Headquarters": "Mumbai, Maharashtra",
        },
        "exam_fact_en": "Repo rate is the rate at which the RBI lends short-term funds to commercial banks against government securities.",
        "exam_fact_hi": "रेपो दर वह दर है जिस पर आरबीआई वाणिज्यिक बैंकों को सरकारी प्रतिभूतियों के आधार पर अल्पकालिक ऋण देता है।",
        "source": {"name": "RBI", "url": "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx"},
        "image_path": "",
        "image_caption": "",
    },
    {
        "event_id": "sample-science-1",
        "category": "Science & Technology",
        "importance_score": 80,
        "headline_en": "ISRO successfully tests indigenous semi-cryogenic engine for future launch vehicles",
        "headline_hi": "इसरो ने भावी प्रक्षेपण यानों के लिए स्वदेशी सेमी-क्रायोजेनिक इंजन का सफल परीक्षण किया",
        "key_points_en": [
            "The 2,000 kN semi-cryogenic engine completed a 200-second hot test at Mahendragiri.",
            "The engine uses liquid oxygen and kerosene, improving payload capacity.",
            "This supports the Gaganyaan and future heavy-lift programmes.",
        ],
        "key_points_hi": [
            "2,000 किलोन्यूटन का सेमी-क्रायोजेनिक इंजन महेंद्रगिरि में 200 सेकंड का गर्म परीक्षण पूरा किया।",
            "इंजन द्रव ऑक्सीजन और केरोसिन का उपयोग करता है, जिससे पेलोड क्षमता बढ़ती है।",
            "यह गगनयान तथा भावी भारी-भार वहन कार्यक्रमों को सहयोग देगा।",
        ],
        "static_facts": {
            "Established": "ISRO — 15 August 1969",
            "Headquarters": "Bengaluru, Karnataka",
            "Test facility": "Mahendragiri, Tamil Nadu",
        },
        "exam_fact_en": "A semi-cryogenic engine uses a mixture of liquid oxygen and kerosene, whereas a cryogenic engine uses liquid hydrogen and liquid oxygen.",
        "exam_fact_hi": "सेमी-क्रायोजेनिक इंजन में द्रव ऑक्सीजन एवं केरोसिन का मिश्रण प्रयुक्त होता है, जबकि क्रायोजेनिक इंजन में द्रव हाइड्रोजन एवं द्रव ऑक्सीजन।",
        "source": {"name": "ISRO", "url": "https://www.isro.gov.in/"},
        "image_path": "",
        "image_caption": "",
    },
    {
        "event_id": "sample-env-1",
        "category": "Environment",
        "importance_score": 74,
        "headline_en": "India adds 2,100 MW of solar capacity in September, total crosses 90 GW",
        "headline_hi": "सितंबर में भारत ने 2,100 मेगावाट सौर क्षमता जोड़ी, कुल क्षमता 90 गीगावाट के पार",
        "key_points_en": [
            "Solar installations rose by 2,100 MW in September 2026.",
            "Cumulative installed solar capacity crossed 90 GW.",
            "Rajasthan, Gujarat and Karnataka remain the leading states.",
        ],
        "key_points_hi": [
            "सितंबर 2026 में सौर संस्थापन 2,100 मेगावाट बढ़ा।",
            "कुल स्थापित सौर क्षमता 90 गीगावाट से अधिक हो गई।",
            "राजस्थान, गुजरात और कर्नाटक अग्रणी राज्य बने हुए हैं।",
        ],
        "static_facts": {
            "National Solar Mission": "Launched 11 January 2010",
            "Parent ministry": "Ministry of New and Renewable Energy",
        },
        "exam_fact_en": "The National Solar Mission is one of the eight missions of the National Action Plan on Climate Change.",
        "exam_fact_hi": "राष्ट्रीय सौर मिशन जलवायु परिवर्तन पर राष्ट्रीय कार्य योजना के आठ मिशनों में से एक है।",
        "source": {"name": "MNRE", "url": "https://mnre.gov.in/"},
        "image_path": "",
        "image_caption": "",
    },
    {
        "event_id": "sample-intl-1",
        "category": "International",
        "importance_score": 70,
        "headline_en": "WHO and FAO launch joint action plan on antimicrobial resistance in food systems",
        "headline_hi": "डब्ल्यूएचओ और एफएओ ने खाद्य प्रणालियों में रोगाणुरोधी प्रतिरोध पर संयुक्त कार्य योजना शुरू की",
        "key_points_en": [
            "The plan targets a 30 per cent reduction in antimicrobial use in agriculture by 2030.",
            "It covers surveillance, stewardship and alternative therapies.",
            "India is a signatory through the One Health framework.",
        ],
        "key_points_hi": [
            "योजना का लक्ष्य 2030 तक कृषि में रोगाणुरोधी उपयोग में 30 प्रतिशत कमी लाना है।",
            "इसमें निगरानी, सुव्यवस्थित उपयोग एवं वैकल्पिक चिकित्सा शामिल हैं।",
            "भारत वन हेल्थ ढाँचे के माध्यम से हस्ताक्षरकर्ता है।",
        ],
        "static_facts": {
            "WHO established": "7 April 1948",
            "FAO established": "16 October 1945",
            "FAO headquarters": "Rome, Italy",
        },
        "exam_fact_en": "Antimicrobial resistance is a One Health issue linking human, animal and environmental health.",
        "exam_fact_hi": "रोगाणुरोधी प्रतिरोध एक वन हेल्थ मुद्दा है जो मानव, पशु एवं पर्यावरणीय स्वास्थ्य को जोड़ता है।",
        "source": {"name": "WHO", "url": "https://www.who.int/news"},
        "image_path": "",
        "image_caption": "",
    },
]

_MCQS: list[dict[str, Any]] = [
    {
        "q_num": 1,
        "question_en": "The Union Cabinet approved a scheme worth how much for the modernisation of 500 primary agricultural credit societies?",
        "question_hi": "केंद्रीय मंत्रिमंडल ने 500 प्राथमिक कृषि साख समितियों के आधुनिकीकरण के लिए कितनी राशि की योजना को मंज़ूरी दी?",
        "options": ["₹950 crore", "₹1,100 crore", "₹1,250 crore", "₹1,400 crore", "₹1,600 crore"],
        "correct": "C",
        "explanation_en": "The Cabinet approved ₹1,250 crore for 500 PACS, to be shared 60:40 between the Centre and states.",
        "explanation_hi": "मंत्रिमंडल ने 500 प्राथमिक कृषि साख समितियों के लिए ₹1,250 करोड़ मंज़ूर किए, जिनका बँटवारा केंद्र एवं राज्यों के बीच 60:40 होगा।",
        "exam_point": "Remember the scheme amount and the 60:40 funding pattern.",
    },
    {
        "q_num": 2,
        "question_en": "Who is the implementing agency for the approved modernisation scheme for primary agricultural credit societies?",
        "question_hi": "प्राथमिक कृषि साख समितियों की स्वीकृत आधुनिकीकरण योजना की कार्यान्वयन एजेंसी कौन है?",
        "options": ["SIDBI", "NABARD", "RBI", "SEBI", "NABCONS"],
        "correct": "B",
        "explanation_en": "NABARD (established 12 July 1982, headquarters Mumbai) is the implementing agency.",
        "explanation_hi": "नाबार्ड (स्थापना 12 जुलाई 1982, मुख्यालय मुंबई) कार्यान्वयन एजेंसी है।",
        "exam_point": "NABARD was set up on the recommendation of the Sivaraman Committee.",
    },
    {
        "q_num": 3,
        "question_en": "In its latest monetary policy review, the RBI kept the repo rate unchanged at:",
        "question_hi": "अपनी नवीनतम मौद्रिक नीति समीक्षा में आरबीआई ने रेपो दर को किस स्तर पर अपरिवर्तित रखा?",
        "options": ["6.00 per cent", "6.25 per cent", "6.50 per cent", "6.75 per cent", "7.00 per cent"],
        "correct": "C",
        "explanation_en": "The Monetary Policy Committee held the repo rate at 6.50 per cent by a 4:2 vote.",
        "explanation_hi": "मौद्रिक नीति समिति ने 4:2 मत से रेपो दर 6.50 प्रतिशत पर बनाए रखी।",
        "exam_point": "Repo rate is the RBI's policy lending rate against government securities.",
    },
    {
        "q_num": 4,
        "question_en": "Which fuel combination is used in a semi-cryogenic engine?",
        "question_hi": "सेमी-क्रायोजेनिक इंजन में किस ईंधन संयोजन का उपयोग होता है?",
        "options": [
            "Liquid hydrogen and liquid oxygen",
            "Liquid oxygen and kerosene",
            "Solid propellant and liquid oxygen",
            "Nitrogen tetroxide and hydrazine",
            "Liquid methane and liquid oxygen",
        ],
        "correct": "B",
        "explanation_en": "A semi-cryogenic engine burns liquid oxygen with kerosene (a non-cryogenic fuel).",
        "explanation_hi": "सेमी-क्रायोजेनिक इंजन द्रव ऑक्सीजन के साथ केरोसिन जलाता है।",
        "exam_point": "Cryogenic = liquid hydrogen + liquid oxygen; semi-cryogenic = liquid oxygen + kerosene.",
    },
    {
        "q_num": 5,
        "question_en": "India's cumulative installed solar capacity crossed which milestone in September 2026?",
        "question_hi": "सितंबर 2026 में भारत की कुल स्थापित सौर क्षमता ने कौन-सा आँकड़ा पार किया?",
        "options": ["60 GW", "70 GW", "80 GW", "90 GW", "100 GW"],
        "correct": "D",
        "explanation_en": "Solar capacity crossed 90 GW after adding 2,100 MW in September 2026.",
        "explanation_hi": "सितंबर 2026 में 2,100 मेगावाट जुड़ने के बाद सौर क्षमता 90 गीगावाट के पार पहुँच गई।",
        "exam_point": "Track state leaders: Rajasthan, Gujarat and Karnataka.",
    },
    {
        "q_num": 6,
        "question_en": "The joint WHO-FAO action plan targets what reduction in antimicrobial use in agriculture by 2030?",
        "question_hi": "संयुक्त डब्ल्यूएचओ-एफएओ कार्य योजना 2030 तक कृषि में रोगाणुरोधी उपयोग में कितनी कमी का लक्ष्य रखती है?",
        "options": ["10 per cent", "20 per cent", "30 per cent", "40 per cent", "50 per cent"],
        "correct": "C",
        "explanation_en": "The plan targets a 30 per cent reduction in antimicrobial use in agriculture by 2030.",
        "explanation_hi": "योजना 2030 तक कृषि में रोगाणुरोधी उपयोग में 30 प्रतिशत कमी का लक्ष्य रखती है।",
        "exam_point": "WHO: 7 April 1948. FAO: 16 October 1945, headquarters Rome.",
    },
]


def build_sample_content() -> dict[str, Any]:
    """Return a synthetic bilingual `content` document for the PDF engine."""
    return {
        "job": {
            "id": "daily_sample_2026-10-18",
            "type": "daily",
            "date": "2026-10-18",
            "date_display": "18 October 2026",
        },
        "items": [dict(it) for it in _ITEMS],
    }


def build_sample_mcqs() -> list[dict[str, Any]]:
    """Return synthetic five-option MCQs with an answer key."""
    return [dict(m) for m in _MCQS]
