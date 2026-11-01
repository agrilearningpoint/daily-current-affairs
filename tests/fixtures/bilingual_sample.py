"""Deterministic bilingual fixture for PDF generation and QA tests.

This fixture is synthetic and source-grounded: it is NOT real news and must
never be published. It deliberately exercises the parts of the PDF engine that
are easy to break:

* English + Hindi headlines;
* long Hindi paragraphs with conjuncts and matras (क्ष, त्र, श्र, द्ध, ि ा ी ो ौ);
* dates, percentages, currency values and acronyms;
* an official source link (clickable);
* detailed bilingual explanations;
* a Static GK panel per story;
* five-option MCQs with an answer key;
* category one-liners;
* a final revision capsule;
* enough volume to force a 15+ page layout.
"""
from __future__ import annotations

from typing import Any

# (event_id, category, score, headline_en, headline_hi, detail_en, detail_hi,
#  kp_en, kp_hi, static, exam_en, exam_hi, src_name, src_url)
_RAW: list[tuple] = [
    (
        "sample-agri-1", "Agriculture", 92,
        "Cabinet approves ₹1,250 crore scheme to modernise 500 primary agricultural credit societies",
        "मंत्रिमंडल ने 500 प्राथमिक कृषि साख समितियों के आधुनिकीकरण हेतु ₹1,250 करोड़ की योजना को मंज़ूरी दी",
        "The Union Cabinet approved a ₹1,250 crore scheme to modernise 500 primary agricultural "
        "credit societies (PACS) across 12 states. The scheme will fund computerisation, storage "
        "and warehouse capacity at the village level and is scheduled for completion by March 2027. "
        "Funding is shared 60:40 between the Centre and the states, and NABARD will act as the "
        "implementing agency. The decision directly strengthens the short-term cooperative credit "
        "structure that supports small and marginal farmers.",
        "केंद्रीय मंत्रिमंडल ने 12 राज्यों की 500 प्राथमिक कृषि साख समितियों के आधुनिकीकरण के लिए ₹1,250 करोड़ "
        "की योजना को स्वीकृति दी। इस योजना से ग्राम स्तर पर कंप्यूटरीकरण, भंडारण एवं गोदाम क्षमता का विकास "
        "होगा तथा इसे मार्च 2027 तक पूरा करने का लक्ष्य है। वित्तपोषण केंद्र एवं राज्यों के बीच 60:40 के "
        "अनुपात में होगा और कार्यान्वयन एजेंसी नाबार्ड होगी। यह निर्णय लघु एवं सीमांत किसानों को सहयोग देने "
        "वाली अल्पकालिक सहकारी साख संरचना को सुदृढ़ करता है।",
        [
            "The Union Cabinet approved a scheme worth ₹1,250 crore for 500 primary agricultural credit societies (PACS).",
            "The scheme targets computerisation, storage and warehouse capacity in 12 states by March 2027.",
            "Funding is shared 60:40 between the Centre and states; NABARD is the implementing agency.",
        ],
        [
            "केंद्रीय मंत्रिमंडल ने 500 प्राथमिक कृषि साख समितियों के लिए ₹1,250 करोड़ की योजना को मंज़ूरी दी।",
            "योजना का लक्ष्य मार्च 2027 तक 12 राज्यों में कंप्यूटरीकरण, भंडारण एवं गोदाम क्षमता बढ़ाना है।",
            "वित्तपोषण केंद्र और राज्यों के बीच 60:40 अनुपात में होगा; कार्यान्वयन एजेंसी नाबार्ड होगी।",
        ],
        {
            "Established": "NABARD — 12 July 1982",
            "Headquarters": "Mumbai, Maharashtra",
            "Parent body": "Ministry of Finance (Department of Financial Services)",
        },
        "PACS are the smallest and most numerous cooperative credit institutions in India; the scheme strengthens the cooperative credit structure exam candidates are frequently asked about.",
        "प्राथमिक कृषि साख समितियाँ भारत की सबसे छोटी और सर्वाधिक संख्या वाली सहकारी साख संस्थाएँ हैं।",
        "PIB", "https://www.pib.gov.in/PressReleasePage.aspx?PRID=000000",
    ),
    (
        "sample-banking-1", "Banking & Finance", 88,
        "RBI keeps repo rate unchanged at 6.50 per cent; GDP growth projected at 7.1 per cent",
        "आरबीआई ने रेपो दर 6.50 प्रतिशत पर अपरिवर्तित रखी; जीडीपी वृद्धि 7.1 प्रतिशत रहने का अनुमान",
        "The Monetary Policy Committee of the Reserve Bank of India voted 4:2 to keep the repo rate "
        "unchanged at 6.50 per cent. The committee revised its inflation projection for the current "
        "financial year to 4.8 per cent and projected gross domestic product growth of 7.1 per cent "
        "for 2026-27. The standing deposit facility rate and the marginal standing facility rate were "
        "kept unchanged as well. The policy stance remains focused on the durable alignment of "
        "inflation with the target while supporting growth.",
        "भारतीय रिज़र्व बैंक की मौद्रिक नीति समिति ने 4:2 के बहुमत से रेपो दर 6.50 प्रतिशत पर अपरिवर्तित "
        "रखने का निर्णय लिया। समिति ने चालू वित्त वर्ष के लिए मुद्रास्फीति अनुमान 4.8 प्रतिशत तथा वर्ष "
        "2026-27 के लिए सकल घरेलू उत्पाद वृद्धि 7.1 प्रतिशत अनुमानित की। स्थायी जमा सुविधा दर एवं सीमांत "
        "स्थायी सुविधा दर भी अपरिवर्तित रखी गईं। नीति का रुख मुद्रास्फीति को लक्ष्य के अनुरूप बनाए रखते "
        "हुए वृद्धि को सहयोग देने पर केंद्रित है।",
        [
            "The Monetary Policy Committee voted 4:2 to hold the repo rate at 6.50 per cent.",
            "Inflation projection for the current financial year was revised to 4.8 per cent.",
            "Gross domestic product growth for 2026-27 is projected at 7.1 per cent.",
        ],
        [
            "मौद्रिक नीति समिति ने 4:2 के बहुमत से रेपो दर 6.50 प्रतिशत पर बनाए रखने का निर्णय लिया।",
            "चालू वित्त वर्ष के लिए मुद्रास्फीति अनुमान 4.8 प्रतिशत किया गया।",
            "वर्ष 2026-27 के लिए सकल घरेलू उत्पाद वृद्धि 7.1 प्रतिशत अनुमानित है।",
        ],
        {
            "Established": "RBI — 1 April 1935",
            "Governor": "Office-bearer (verify at edition cutoff)",
            "Headquarters": "Mumbai, Maharashtra",
        },
        "Repo rate is the rate at which the RBI lends short-term funds to commercial banks against government securities.",
        "रेपो दर वह दर है जिस पर आरबीआई वाणिज्यिक बैंकों को सरकारी प्रतिभूतियों के आधार पर अल्पकालिक ऋण देता है।",
        "RBI", "https://www.rbi.org.in/Scripts/BS_PressReleaseDisplay.aspx",
    ),
    (
        "sample-science-1", "Science & Technology", 80,
        "ISRO successfully tests indigenous semi-cryogenic engine for future launch vehicles",
        "इसरो ने भावी प्रक्षेपण यानों के लिए स्वदेशी सेमी-क्रायोजेनिक इंजन का सफल परीक्षण किया",
        "The Indian Space Research Organisation completed a 200-second hot test of its indigenous "
        "2,000 kN semi-cryogenic engine at the Mahendragiri test facility in Tamil Nadu. The engine "
        "burns liquid oxygen with kerosene, a non-cryogenic fuel, which improves payload capacity "
        "and reduces cost compared with fully cryogenic stages. The development supports the "
        "Gaganyaan human spaceflight programme and future heavy-lift launch vehicles. ISRO described "
        "the test as a major milestone for self-reliance in propulsion technology.",
        "भारतीय अंतरिक्ष अनुसंधान संगठन ने तमिलनाडु की महेंद्रगिरि परीक्षण सुविधा में अपने स्वदेशी 2,000 "
        "किलोन्यूटन सेमी-क्रायोजेनिक इंजन का 200 सेकंड का गर्म परीक्षण पूरा किया। यह इंजन द्रव ऑक्सीजन के "
        "साथ केरोसिन का उपयोग करता है, जिससे पेलोड क्षमता बढ़ती है तथा लागत घटती है। यह विकास गगनयान मानव "
        "अंतरिक्ष उड़ान कार्यक्रम एवं भावी भारी-भार वहन यानों को सहयोग देगा। इसरो ने परीक्षण को प्रणोदन "
        "प्रौद्योगिकी में आत्मनिर्भरता की दिशा में महत्वपूर्ण उपलब्धि बताया।",
        [
            "The 2,000 kN semi-cryogenic engine completed a 200-second hot test at Mahendragiri.",
            "The engine uses liquid oxygen and kerosene, improving payload capacity.",
            "This supports the Gaganyaan and future heavy-lift programmes.",
        ],
        [
            "2,000 किलोन्यूटन का सेमी-क्रायोजेनिक इंजन महेंद्रगिरि में 200 सेकंड का गर्म परीक्षण पूरा किया।",
            "इंजन द्रव ऑक्सीजन और केरोसिन का उपयोग करता है, जिससे पेलोड क्षमता बढ़ती है।",
            "यह गगनयान तथा भावी भारी-भार वहन कार्यक्रमों को सहयोग देगा।",
        ],
        {
            "Established": "ISRO — 15 August 1969",
            "Headquarters": "Bengaluru, Karnataka",
            "Test facility": "Mahendragiri, Tamil Nadu",
        },
        "A semi-cryogenic engine uses a mixture of liquid oxygen and kerosene, whereas a cryogenic engine uses liquid hydrogen and liquid oxygen.",
        "सेमी-क्रायोजेनिक इंजन में द्रव ऑक्सीजन एवं केरोसिन का मिश्रण प्रयुक्त होता है, जबकि क्रायोजेनिक इंजन में द्रव हाइड्रोजन एवं द्रव ऑक्सीजन।",
        "ISRO", "https://www.isro.gov.in/",
    ),
    (
        "sample-env-1", "Environment", 74,
        "India adds 2,100 MW of solar capacity in September, total crosses 90 GW",
        "सितंबर में भारत ने 2,100 मेगावाट सौर क्षमता जोड़ी, कुल क्षमता 90 गीगावाट के पार",
        "India added 2,100 megawatts of solar capacity in September 2026, taking the cumulative "
        "installed solar capacity beyond 90 gigawatts. Rajasthan, Gujarat and Karnataka remain the "
        "leading states, together accounting for more than half of the national total. The growth is "
        "driven by the National Solar Mission and falling module prices. The Ministry of New and "
        "Renewable Energy underlined that utility-scale and rooftop segments both contributed to the "
        "month's addition.",
        "भारत ने सितंबर 2026 में 2,100 मेगावाट सौर क्षमता जोड़ी, जिससे कुल स्थापित सौर क्षमता 90 गीगावाट "
        "से अधिक हो गई। राजस्थान, गुजरात और कर्नाटक अग्रणी राज्य बने हुए हैं तथा मिलकर राष्ट्रीय कुल का "
        "आधे से अधिक योगदान देते हैं। यह वृद्धि राष्ट्रीय सौर मिशन तथा मॉड्यूल की घटती कीमतों से प्रेरित है।",
        [
            "Solar installations rose by 2,100 MW in September 2026.",
            "Cumulative installed solar capacity crossed 90 GW.",
            "Rajasthan, Gujarat and Karnataka remain the leading states.",
        ],
        [
            "सितंबर 2026 में सौर संस्थापन 2,100 मेगावाट बढ़ा।",
            "कुल स्थापित सौर क्षमता 90 गीगावाट से अधिक हो गई।",
            "राजस्थान, गुजरात और कर्नाटक अग्रणी राज्य बने हुए हैं।",
        ],
        {
            "National Solar Mission": "Launched 11 January 2010",
            "Parent ministry": "Ministry of New and Renewable Energy",
        },
        "The National Solar Mission is one of the eight missions of the National Action Plan on Climate Change.",
        "राष्ट्रीय सौर मिशन जलवायु परिवर्तन पर राष्ट्रीय कार्य योजना के आठ मिशनों में से एक है।",
        "MNRE", "https://mnre.gov.in/",
    ),
    (
        "sample-intl-1", "International", 70,
        "WHO and FAO launch joint action plan on antimicrobial resistance in food systems",
        "डब्ल्यूएचओ और एफएओ ने खाद्य प्रणालियों में रोगाणुरोधी प्रतिरोध पर संयुक्त कार्य योजना शुरू की",
        "The World Health Organization and the Food and Agriculture Organization launched a joint "
        "action plan to tackle antimicrobial resistance in food systems. The plan targets a 30 per "
        "cent reduction in antimicrobial use in agriculture by 2030 and covers surveillance, "
        "stewardship and alternative therapies. India is a signatory through the One Health "
        "framework, which links human, animal and environmental health. The agencies warned that "
        "unchecked resistance could undermine food security and public health gains.",
        "विश्व स्वास्थ्य संगठन और खाद्य एवं कृषि संगठन ने खाद्य प्रणालियों में रोगाणुरोधी प्रतिरोध से "
        "निपटने हेतु संयुक्त कार्य योजना शुरू की। योजना का लक्ष्य 2030 तक कृषि में रोगाणुरोधी उपयोग में 30 "
        "प्रतिशत कमी लाना है तथा इसमें निगरानी, सुव्यवस्थित उपयोग एवं वैकल्पिक चिकित्सा शामिल हैं। भारत वन "
        "हेल्थ ढाँचे के माध्यम से हस्ताक्षरकर्ता है।",
        [
            "The plan targets a 30 per cent reduction in antimicrobial use in agriculture by 2030.",
            "It covers surveillance, stewardship and alternative therapies.",
            "India is a signatory through the One Health framework.",
        ],
        [
            "योजना का लक्ष्य 2030 तक कृषि में रोगाणुरोधी उपयोग में 30 प्रतिशत कमी लाना है।",
            "इसमें निगरानी, सुव्यवस्थित उपयोग एवं वैकल्पिक चिकित्सा शामिल हैं।",
            "भारत वन हेल्थ ढाँचे के माध्यम से हस्ताक्षरकर्ता है।",
        ],
        {
            "WHO established": "7 April 1948",
            "FAO established": "16 October 1945",
            "FAO headquarters": "Rome, Italy",
        },
        "Antimicrobial resistance is a One Health issue linking human, animal and environmental health.",
        "रोगाणुरोधी प्रतिरोध एक वन हेल्थ मुद्दा है जो मानव, पशु एवं पर्यावरणीय स्वास्थ्य को जोड़ता है।",
        "WHO", "https://www.who.int/news",
    ),
    (
        "sample-econ-1", "Economy", 78,
        "Retail inflation eases to 4.2 per cent in September on lower food prices",
        "खाद्य कीमतों में गिरावट से सितंबर में खुदरा मुद्रास्फीति घटकर 4.2 प्रतिशत",
        "Retail inflation measured by the Consumer Price Index eased to 4.2 per cent in September "
        "2026 from 4.9 per cent in the previous month, mainly because of softer vegetable and edible "
        "oil prices. The print stayed within the RBI's tolerance band of 2 to 6 per cent. Core "
        "inflation, which excludes food and fuel, remained firm at 3.8 per cent. Economists said the "
        "reading keeps room open for a gradual policy easing if the trend persists.",
        "उपभोक्ता मूल्य सूचकांक से मापी गई खुदरा मुद्रास्फीति सितंबर 2026 में घटकर 4.2 प्रतिशत रही, जो "
        "पिछले माह 4.9 प्रतिशत थी। इसका मुख्य कारण सब्जी एवं खाद्य तेल की कीमतों में नरमी रही। यह आँकड़ा "
        "आरबीआई की 2 से 6 प्रतिशत की सहनशीलता सीमा के भीतर रहा।",
        [
            "Retail inflation eased to 4.2 per cent in September 2026 from 4.9 per cent in August.",
            "The print remained within the RBI tolerance band of 2 to 6 per cent.",
            "Core inflation held firm at 3.8 per cent.",
        ],
        [
            "सितंबर 2026 में खुदरा मुद्रास्फीति घटकर 4.2 प्रतिशत रही, जो अगस्त में 4.9 प्रतिशत थी।",
            "यह आँकड़ा आरबीआई की 2 से 6 प्रतिशत की सहनशीलता सीमा के भीतर रहा।",
            "मुख्य मुद्रास्फीति 3.8 प्रतिशत पर स्थिर रही।",
        ],
        {
            "Index name": "Consumer Price Index (Combined)",
            "Released by": "National Statistical Office, MoSPI",
            "Base year": "2012",
        },
        "The RBI's flexible inflation targeting framework sets a headline CPI target of 4 per cent with a tolerance band of plus or minus 2 per cent.",
        "आरबीआई के लचीले मुद्रास्फीति लक्ष्यीकरण ढाँचे में मुख्य सीपीआई लक्ष्य 4 प्रतिशत तथा सहनशीलता सीमा 2 प्रतिशत ऊपर-नीचे है।",
        "MoSPI", "https://www.mospi.gov.in/",
    ),
    (
        "sample-national-1", "Government Schemes", 85,
        "PM-KISAN 19th instalment released to 9.6 crore beneficiary farmers",
        "पीएम-किसान की 19वीं किस्त 9.6 करोड़ लाभार्थी किसानों को जारी",
        "The nineteenth instalment of the Pradhan Mantri Kisan Samman Nidhi was released to about "
        "9.6 crore beneficiary farmers. Under the scheme, eligible landholding farmer families "
        "receive ₹6,000 per year in three equal instalments of ₹2,000 directly into their bank "
        "accounts through the Direct Benefit Transfer mechanism. The scheme is fully funded by the "
        "Union Government and is implemented by the Ministry of Agriculture and Farmers Welfare. "
        "Candidates should remember both the annual amount and the instalment structure.",
        "प्रधानमंत्री किसान सम्मान निधि की उन्नीसवीं किस्त लगभग 9.6 करोड़ लाभार्थी किसानों को जारी की गई। "
        "इस योजना के अंतर्गत पात्र भूमिधारक किसान परिवारों को प्रतिवर्ष ₹6,000 तीन समान किस्तों में ₹2,000 "
        "के रूप में प्रत्यक्ष लाभ अंतरण के माध्यम से मिलते हैं। यह योजना पूर्णतः केंद्र सरकार द्वारा "
        "वित्तपोषित है।",
        [
            "PM-KISAN's 19th instalment reached about 9.6 crore beneficiary farmers.",
            "Beneficiaries receive ₹6,000 per year in three equal instalments of ₹2,000.",
            "Payments are made through Direct Benefit Transfer into Aadhaar-linked bank accounts.",
        ],
        [
            "पीएम-किसान की 19वीं किस्त लगभग 9.6 करोड़ लाभार्थी किसानों तक पहुँची।",
            "लाभार्थियों को प्रतिवर्ष ₹6,000 तीन समान किस्तों में ₹2,000 के रूप में मिलते हैं।",
            "भुगतान आधार-लिंक्ड बैंक खातों में प्रत्यक्ष लाभ अंतरण द्वारा किया जाता है।",
        ],
        {
            "Launched": "24 February 2019",
            "Ministry": "Ministry of Agriculture and Farmers Welfare",
            "Benefit": "₹6,000 per year in three instalments",
        },
        "PM-KISAN is a central sector scheme with 100 per cent funding from the Union Government.",
        "पीएम-किसान एक केंद्रीय क्षेत्र की योजना है जिसमें शत-प्रतिशत वित्तपोषण केंद्र सरकार द्वारा किया जाता है।",
        "PIB", "https://www.pib.gov.in/",
    ),
    (
        "sample-defence-1", "Defence", 76,
        "DRDO conducts successful flight test of indigenous cruise missile",
        "डीआरडीओ ने स्वदेशी क्रूज़ मिसाइल का सफल उड़ान परीक्षण किया",
        "The Defence Research and Development Organisation conducted a successful flight test of an "
        "indigenous long-range cruise missile from the Integrated Test Range at Chandipur, Odisha. "
        "The missile demonstrated waypoint navigation and a terminal manoeuvre before hitting the "
        "designated target. The test validated the propulsion, navigation and warhead systems. The "
        "system is intended to enhance stand-off strike capability. DRDO said the trial met all "
        "mission objectives.",
        "रक्षा अनुसंधान एवं विकास संगठन ने ओडिशा के चांदीपुर स्थित एकीकृत परीक्षण रेंज से स्वदेशी लंबी दूरी "
        "की क्रूज़ मिसाइल का सफल उड़ान परीक्षण किया। मिसाइल ने निर्धारित लक्ष्य पर प्रहार से पूर्व वेपॉइंट "
        "नेविगेशन एवं अंतिम पड़ाव का प्रदर्शन किया। परीक्षण से प्रणोदन, नेविगेशन तथा वारहेड प्रणालियों का "
        "सत्यापन हुआ।",
        [
            "DRDO flight-tested an indigenous long-range cruise missile from Chandipur, Odisha.",
            "The missile demonstrated waypoint navigation and a terminal manoeuvre.",
            "The trial validated propulsion, navigation and warhead systems.",
        ],
        [
            "डीआरडीओ ने ओडिशा के चांदीपुर से स्वदेशी लंबी दूरी की क्रूज़ मिसाइल का उड़ान परीक्षण किया।",
            "मिसाइल ने वेपॉइंट नेविगेशन एवं अंतिम पड़ाव का प्रदर्शन किया।",
            "परीक्षण से प्रणोदन, नेविगेशन तथा वारहेड प्रणालियों का सत्यापन हुआ।",
        ],
        {
            "DRDO established": "1958",
            "Headquarters": "New Delhi",
            "Test range": "Integrated Test Range, Chandipur, Odisha",
        },
        "DRDO is the research and development wing of the Ministry of Defence, established in 1958.",
        "डीआरडीओ रक्षा मंत्रालय का अनुसंधान एवं विकास संगठन है, जिसकी स्थापना 1958 में हुई।",
        "PIB", "https://www.pib.gov.in/",
    ),
    (
        "sample-sports-1", "Sports", 68,
        "India wins Asian Games shooting gold with record tally",
        "भारत ने रिकॉर्ड स्कोर के साथ एशियाई खेलों में निशानेबाज़ी का स्वर्ण जीता",
        "India won the gold medal in the 10 metre air rifle mixed team event at the Asian Games, "
        "setting a new games record. The Indian pair finished ahead of China and South Korea on the "
        "medal podium. The result added to India's growing shooting medal tally at the games. "
        "Officials credited structured training and sports authority support for the consistent "
        "performances across events.",
        "भारत ने एशियाई खेलों की 10 मीटर एयर राइफल मिश्रित टीम स्पर्धा में स्वर्ण पदक जीता और नया खेल "
        "रिकॉर्ड बनाया। भारतीय जोड़ी चीन तथा दक्षिण कोरिया से आगे रही। इस परिणाम से खेलों में भारत का "
        "निशानेबाज़ी पदकों का कुल योग बढ़ा।",
        [
            "India won gold in the 10m air rifle mixed team event at the Asian Games.",
            "The pair set a new games record and finished ahead of China and South Korea.",
            "The medal added to India's shooting tally at the games.",
        ],
        [
            "भारत ने एशियाई खेलों की 10 मीटर एयर राइफल मिश्रित टीम स्पर्धा में स्वर्ण जीता।",
            "भारतीय जोड़ी ने नया खेल रिकॉर्ड बनाया तथा चीन एवं दक्षिण कोरिया से आगे रही।",
            "इस पदक से खेलों में भारत का निशानेबाज़ी योग बढ़ा।",
        ],
        {
            "Asian Games 2026 host": "Aichi-Nagoya, Japan",
            "Sport": "10m Air Rifle Mixed Team",
        },
        "The Olympic Council of Asia conducts the Asian Games, held every four years.",
        "एशियाई खेल एशियाई ओलंपिक परिषद द्वारा प्रत्येक चार वर्ष में आयोजित किए जाते हैं।",
        "PIB", "https://www.pib.gov.in/",
    ),
    (
        "sample-award-1", "Awards", 66,
        "Nobel Prize in Economic Sciences awarded for work on inequality",
        "आर्थिक विज्ञान के नोबेल पुरस्कार असमानता पर कार्य के लिए प्रदान",
        "The Royal Swedish Academy of Sciences awarded the Nobel Prize in Economic Sciences to three "
        "researchers for their work on the causes and consequences of economic inequality. The "
        "laureates developed methods to study how long-run differences in income and wealth shape "
        "growth and mobility. The work has informed policy debates on taxation and social security. "
        "The prize carries a cash award and is announced in Stockholm each October.",
        "स्वीडिश शाही विज्ञान अकादमी ने आर्थिक असमानता के कारणों एवं परिणामों पर कार्य करने वाले तीन "
        "शोधकर्ताओं को आर्थिक विज्ञान का नोबेल पुरस्कार प्रदान किया। विजेताओं ने आय एवं संपत्ति के दीर्घकालिक "
        "अंतरों के अध्ययन की विधियाँ विकसित कीं।",
        [
            "The Nobel Prize in Economic Sciences was awarded to three researchers.",
            "The award recognises work on the causes and consequences of economic inequality.",
            "The laureates studied long-run income and wealth differences.",
        ],
        [
            "आर्थिक विज्ञान का नोबेल पुरस्कार तीन शोधकर्ताओं को प्रदान किया गया।",
            "यह पुरस्कार आर्थिक असमानता के कारणों एवं परिणामों पर कार्य को मान्यता देता है।",
            "विजेताओं ने दीर्घकालिक आय एवं संपत्ति के अंतरों का अध्ययन किया।",
        ],
        {
            "Awarded by": "Royal Swedish Academy of Sciences",
            "Announced in": "Stockholm, Sweden (October)",
        },
        "The Nobel Prize in Economic Sciences was established in 1968 by Sweden's central bank in memory of Alfred Nobel.",
        "आर्थिक विज्ञान का नोबेल पुरस्कार 1968 में स्वीडन के केंद्रीय बैंक द्वारा अल्फ्रेड नोबेल की स्मृति में स्थापित किया गया।",
        "Nobel Prize", "https://www.nobelprize.org/",
    ),
    (
        "sample-appoint-1", "Appointments", 64,
        "Government appoints new Secretary in the Department of Agricultural Research",
        "सरकार ने कृषि अनुसंधान विभाग में नए सचिव की नियुक्ति की",
        "The Appointments Committee of the Cabinet appointed a senior officer as Secretary in the "
        "Department of Agricultural Research and Education. The officer will also serve as "
        "Director General of the Indian Council of Agricultural Research. The appointment is for a "
        "fixed tenure in accordance with central staffing norms. Candidates should note the ministry "
        "and the additional charge associated with the post.",
        "मंत्रिमंडल की नियुक्ति समिति ने एक वरिष्ठ अधिकारी को कृषि अनुसंधान एवं शिक्षा विभाग में सचिव "
        "नियुक्त किया। अधिकारी भारतीय कृषि अनुसंधान परिषद के महानिदेशक का अतिरिक्त प्रभार भी संभालेंगे। "
        "यह नियुक्ति केंद्रीय कार्मिक मानदंडों के अनुसार निर्धारित कार्यकाल के लिए की गई है।",
        [
            "A senior officer was appointed Secretary of the Department of Agricultural Research and Education.",
            "The officer will also hold additional charge as Director General of ICAR.",
            "The appointment follows central staffing norms and has a fixed tenure.",
        ],
        [
            "एक वरिष्ठ अधिकारी कृषि अनुसंधान एवं शिक्षा विभाग के सचिव नियुक्त किए गए।",
            "अधिकारी आईसीएआर के महानिदेशक का अतिरिक्त प्रभार भी संभालेंगे।",
            "यह नियुक्ति केंद्रीय कार्मिक मानदंडों एवं निर्धारित कार्यकाल के अनुसार है।",
        ],
        {
            "ICAR established": "16 July 1929",
            "Headquarters": "New Delhi",
            "Parent ministry": "Ministry of Agriculture and Farmers Welfare",
        },
        "ICAR is an autonomous body that coordinates agricultural education and research in India.",
        "आईसीएआर एक स्वायत्त संस्था है जो भारत में कृषि शिक्षा एवं अनुसंधान का समन्वय करती है।",
        "PIB", "https://www.pib.gov.in/",
    ),
    (
        "sample-health-1", "Health", 62,
        "Ayushman Bharat crosses 40 crore Ayushman cards, coverage expanded for seniors",
        "आयुष्मान भारत में 40 करोड़ से अधिक आयुष्मान कार्ड, वरिष्ठ नागरिकों के लिए कवरेज विस्तारित",
        "The Ayushman Bharat Pradhan Mantri Jan Arogya Yojana crossed 40 crore issued Ayushman "
        "cards, the Union Health Ministry said. The scheme provides health cover of ₹5 lakh per "
        "family per year for secondary and tertiary hospitalisation. In a recent expansion, all "
        "senior citizens aged 70 years and above became eligible irrespective of income. The scheme "
        "is cashless and portable across states through empanelled hospitals.",
        "केंद्रीय स्वास्थ्य मंत्रालय के अनुसार आयुष्मान भारत प्रधानमंत्री जन आरोग्य योजना में 40 करोड़ से "
        "अधिक आयुष्मान कार्ड जारी किए जा चुके हैं। योजना में प्रति परिवार प्रति वर्ष ₹5 लाख तक का स्वास्थ्य "
        "कवर मिलता है। हाल के विस्तार में 70 वर्ष एवं उससे अधिक आयु के सभी वरिष्ठ नागरिक आय की परवाह किए "
        "बिना पात्र बन गए हैं।",
        [
            "Ayushman Bharat has issued more than 40 crore Ayushman cards.",
            "The scheme offers ₹5 lakh cover per family per year for hospitalisation.",
            "All senior citizens aged 70 years and above are now eligible irrespective of income.",
        ],
        [
            "आयुष्मान भारत में 40 करोड़ से अधिक आयुष्मान कार्ड जारी हुए हैं।",
            "योजना में प्रति परिवार प्रति वर्ष ₹5 लाख का कवर मिलता है।",
            "70 वर्ष एवं अधिक आयु के सभी वरिष्ठ नागरिक अब आय की परवाह किए बिना पात्र हैं।",
        ],
        {
            "Launched": "23 September 2018",
            "Ministry": "Ministry of Health and Family Welfare",
            "Cover": "₹5 lakh per family per year",
        },
        "Ayushman Bharat PM-JAY is the world's largest publicly funded health assurance scheme.",
        "आयुष्मान भारत पीएम-जय विश्व की सबसे बड़ी सार्वजनिक वित्त पोषित स्वास्थ्य आश्वासन योजना है।",
        "PIB", "https://www.pib.gov.in/",
    ),
    (
        "sample-national-2", "National", 72,
        "President inaugurates new Supreme Court annexe, stresses judicial efficiency",
        "राष्ट्रपति ने सुप्रीम कोर्ट के नए अनुबंध भवन का उद्घाटन किया, न्यायिक दक्षता पर बल",
        "The President of India inaugurated a new annexe building of the Supreme Court of India in "
        "New Delhi, adding courtrooms and digital infrastructure. In the address, the President "
        "emphasised reducing case pendency through technology and alternative dispute resolution. "
        "The building includes e-court facilities and accessible design features. The Chief Justice "
        "of India and the Law Minister were present at the ceremony.",
        "भारत के राष्ट्रपति ने नई दिल्ली स्थित भारत के सर्वोच्च न्यायालय के नए अनुबंध भवन का उद्घाटन किया, "
        "जिसमें अतिरिक्त न्यायालय कक्ष एवं डिजिटल अधोसंरचना शामिल है। राष्ट्रपति ने प्रौद्योगिकी तथा "
        "वैकल्पिक विवाद समाधान के माध्यम से लंबित मामलों को घटाने पर बल दिया।",
        [
            "The President inaugurated a new annexe of the Supreme Court of India in New Delhi.",
            "The building adds courtrooms, e-court facilities and accessible design features.",
            "The address emphasised reducing case pendency through technology.",
        ],
        [
            "राष्ट्रपति ने नई दिल्ली में भारत के सर्वोच्च न्यायालय के नए अनुबंध भवन का उद्घाटन किया।",
            "भवन में न्यायालय कक्ष, ई-कोर्ट सुविधाएँ एवं सुगम्य डिज़ाइन शामिल हैं।",
            "उद्घाटन भाषण में प्रौद्योगिकी से लंबित मामलों को घटाने पर बल दिया गया।",
        ],
        {
            "Supreme Court established": "26 January 1950",
            "Location": "New Delhi",
            "First Chief Justice": "H. J. Kania",
        },
        "The Supreme Court of India is the highest judicial court and the guardian of the Constitution under Article 124.",
        "भारत का सर्वोच्च न्यायालय अनुच्छेद 124 के अंतर्गत सर्वोच्च न्यायिक न्यायालय एवं संविधान का संरक्षक है।",
        "PIB", "https://www.pib.gov.in/",
    ),
]

_ITEMS: list[dict[str, Any]] = [
    {
        "event_id": r[0],
        "category": r[1],
        "importance_score": r[2],
        "headline_en": r[3],
        "headline_hi": r[4],
        "detailed_explanation_en": r[5],
        "detailed_explanation_hi": r[6],
        "key_points_en": r[7],
        "key_points_hi": r[8],
        "static_facts": r[9],
        "exam_fact_en": r[10],
        "exam_fact_hi": r[11],
        "source": {"name": r[12], "url": r[13]},
        "image_path": "",
        "image_caption": "",
    }
    for r in _RAW
]

_ONE_LINERS: list[dict[str, Any]] = [
    {"category": it["category"], "text_en": it["headline_en"],
     "text_hi": it["headline_hi"], "event_id": it["event_id"]}
    for it in _ITEMS
]

_MCQS: list[dict[str, Any]] = [
    {
        "q_num": 1,
        "event_id": "sample-agri-1",
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
        "event_id": "sample-agri-1",
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
        "event_id": "sample-banking-1",
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
        "event_id": "sample-science-1",
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
        "event_id": "sample-env-1",
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
        "event_id": "sample-intl-1",
        "question_en": "The joint WHO-FAO action plan targets what reduction in antimicrobial use in agriculture by 2030?",
        "question_hi": "संयुक्त डब्ल्यूएचओ-एफएओ कार्य योजना 2030 तक कृषि में रोगाणुरोधी उपयोग में कितनी कमी का लक्ष्य रखती है?",
        "options": ["10 per cent", "20 per cent", "30 per cent", "40 per cent", "50 per cent"],
        "correct": "C",
        "explanation_en": "The plan targets a 30 per cent reduction in antimicrobial use in agriculture by 2030.",
        "explanation_hi": "योजना 2030 तक कृषि में रोगाणुरोधी उपयोग में 30 प्रतिशत कमी का लक्ष्य रखती है।",
        "exam_point": "WHO: 7 April 1948. FAO: 16 October 1945, headquarters Rome.",
    },
    {
        "q_num": 7,
        "event_id": "sample-econ-1",
        "question_en": "Retail inflation eased to which level in September 2026?",
        "question_hi": "सितंबर 2026 में खुदरा मुद्रास्फीति किस स्तर तक घटी?",
        "options": ["3.8 per cent", "4.2 per cent", "4.9 per cent", "5.2 per cent", "5.6 per cent"],
        "correct": "B",
        "explanation_en": "Retail inflation eased to 4.2 per cent in September 2026 from 4.9 per cent in August.",
        "explanation_hi": "सितंबर 2026 में खुदरा मुद्रास्फीति अगस्त के 4.9 प्रतिशत से घटकर 4.2 प्रतिशत रही।",
        "exam_point": "RBI inflation target is 4 per cent with a +/-2 per cent band.",
    },
    {
        "q_num": 8,
        "event_id": "sample-national-1",
        "question_en": "Under PM-KISAN, how much does an eligible farmer family receive per year?",
        "question_hi": "पीएम-किसान के अंतर्गत पात्र किसान परिवार को प्रतिवर्ष कितनी राशि मिलती है?",
        "options": ["₹4,000", "₹5,000", "₹6,000", "₹8,000", "₹10,000"],
        "correct": "C",
        "explanation_en": "PM-KISAN provides ₹6,000 per year in three equal instalments of ₹2,000.",
        "explanation_hi": "पीएम-किसान में प्रतिवर्ष ₹6,000 तीन समान किस्तों में ₹2,000 के रूप में मिलते हैं।",
        "exam_point": "PM-KISAN is a central sector scheme launched on 24 February 2019.",
    },
    {
        "q_num": 9,
        "event_id": "sample-defence-1",
        "question_en": "From which test range did DRDO flight-test the indigenous long-range cruise missile?",
        "question_hi": "डीआरडीओ ने स्वदेशी लंबी दूरी की क्रूज़ मिसाइल का उड़ान परीक्षण किस परीक्षण रेंज से किया?",
        "options": ["Integrated Test Range, Chandipur", "Satish Dhawan Space Centre, Sriharikota", "Pokhran Field Firing Range", "Thumba Equatorial Launching Station", "Abdul Kalam Island, Balasore"],
        "correct": "A",
        "explanation_en": "The cruise missile was flight-tested from the Integrated Test Range at Chandipur, Odisha.",
        "explanation_hi": "क्रूज़ मिसाइल का उड़ान परीक्षण ओडिशा के चांदीपुर स्थित एकीकृत परीक्षण रेंज से किया गया।",
        "exam_point": "DRDO was established in 1958 and is headquartered in New Delhi.",
    },
    {
        "q_num": 10,
        "event_id": "sample-sports-1",
        "question_en": "In which event did India win gold with a games record at the Asian Games?",
        "question_hi": "एशियाई खेलों में भारत ने किस स्पर्धा में खेल रिकॉर्ड के साथ स्वर्ण जीता?",
        "options": ["50m rifle three positions", "10m air rifle mixed team", "25m rapid fire pistol", "Trap mixed team", "10m air pistol men"],
        "correct": "B",
        "explanation_en": "India won gold in the 10 metre air rifle mixed team event with a new games record.",
        "explanation_hi": "भारत ने 10 मीटर एयर राइफल मिश्रित टीम स्पर्धा में नए खेल रिकॉर्ड के साथ स्वर्ण जीता।",
        "exam_point": "The Olympic Council of Asia conducts the Asian Games every four years.",
    },
    {
        "q_num": 11,
        "event_id": "sample-award-1",
        "question_en": "Which body awards the Nobel Prize in Economic Sciences?",
        "question_hi": "अर्थशास्त्र का नोबेल पुरस्कार कौन-सी संस्था प्रदान करती है?",
        "options": ["Norwegian Nobel Committee", "Karolinska Institute", "Royal Swedish Academy of Sciences", "Swedish Academy", "Nobel Foundation Board"],
        "correct": "C",
        "explanation_en": "The Royal Swedish Academy of Sciences awards the Nobel Prize in Economic Sciences, announced in Stockholm each October.",
        "explanation_hi": "अर्थशास्त्र का नोबेल पुरस्कार रॉयल स्वीडिश एकेडमी ऑफ साइंसेज प्रदान करती है, जिसकी घोषणा प्रत्येक अक्टूबर स्टॉकहोम में होती है।",
        "exam_point": "The 2026 prize recognised work on economic inequality.",
    },
    {
        "q_num": 12,
        "event_id": "sample-appoint-1",
        "question_en": "The Secretary of the Department of Agricultural Research and Education also serves as the Director General of which body?",
        "question_hi": "कृषि अनुसंधान एवं शिक्षा विभाग के सचिव किस संस्था के महानिदेशक भी होते हैं?",
        "options": ["NABARD", "APEDA", "FCI", "ICAR", "NAFED"],
        "correct": "D",
        "explanation_en": "The DARE Secretary also serves as the Director General of the Indian Council of Agricultural Research.",
        "explanation_hi": "डेयर के सचिव भारतीय कृषि अनुसंधान परिषद के महानिदेशक भी होते हैं।",
        "exam_point": "ICAR was established on 16 July 1929 and is headquartered in New Delhi.",
    },
    {
        "q_num": 13,
        "event_id": "sample-health-1",
        "question_en": "What health cover does Ayushman Bharat PM-JAY provide per family per year?",
        "question_hi": "आयुष्मान भारत पीएम-जेएवाई प्रति परिवार प्रतिवर्ष कितना स्वास्थ्य कवर देती है?",
        "options": ["₹1 lakh", "₹2 lakh", "₹3 lakh", "₹4 lakh", "₹5 lakh"],
        "correct": "E",
        "explanation_en": "PM-JAY provides cashless cover of ₹5 lakh per family per year for secondary and tertiary hospitalisation.",
        "explanation_hi": "पीएम-जेएवाई द्वितीयक एवं तृतीयक अस्पताल उपचार के लिए प्रति परिवार प्रतिवर्ष ₹5 लाख का कैशलेस कवर देती है।",
        "exam_point": "Ayushman Bharat PM-JAY was launched on 23 September 2018.",
    },
    {
        "q_num": 14,
        "event_id": "sample-national-2",
        "question_en": "Who was the first Chief Justice of India?",
        "question_hi": "भारत के पहले मुख्य न्यायाधीश कौन थे?",
        "options": ["M. Patanjali Sastri", "H. J. Kania", "Mehr Chand Mahajan", "B. K. Mukherjea", "S. R. Das"],
        "correct": "B",
        "explanation_en": "H. J. Kania was the first Chief Justice of India when the Supreme Court was established on 26 January 1950.",
        "explanation_hi": "26 जनवरी 1950 को सर्वोच्च न्यायालय की स्थापना के समय एच. जे. कानिया भारत के पहले मुख्य न्यायाधीश थे।",
        "exam_point": "The Supreme Court of India was established on 26 January 1950.",
    },
]


# --- Reference-format enrichment (LLM MCQ schema fields) -------------------
# Hindi option text (A-E), a headline-box theme and verified bilingual Static GK
# for the first MCQ of each story.  Mirrors what stage 16 produces from the
# per-item JSON schema (see pipeline/mcq_schema.py).
_OPTIONS_HI: dict[int, list[str]] = {
    1: ["₹950 करोड़", "₹1,100 करोड़", "₹1,250 करोड़", "₹1,400 करोड़", "₹1,600 करोड़"],
    2: ["सिडबी", "नाबार्ड", "भारतीय रिज़र्व बैंक", "सेबी", "नैबकॉन्स"],
    3: ["6.00 प्रतिशत", "6.25 प्रतिशत", "6.50 प्रतिशत", "6.75 प्रतिशत", "7.00 प्रतिशत"],
    4: ["द्रव हाइड्रोजन और द्रव ऑक्सीजन", "द्रव ऑक्सीजन और केरोसिन", "ठोस प्रणोदक और द्रव ऑक्सीजन",
        "नाइट्रोजन टेट्रॉक्साइड और हाइड्राज़ीन", "द्रव मीथेन और द्रव ऑक्सीजन"],
    5: ["60 गीगावाट", "70 गीगावाट", "80 गीगावाट", "90 गीगावाट", "100 गीगावाट"],
    6: ["10 प्रतिशत", "20 प्रतिशत", "30 प्रतिशत", "40 प्रतिशत", "50 प्रतिशत"],
    7: ["3.8 प्रतिशत", "4.2 प्रतिशत", "4.9 प्रतिशत", "5.2 प्रतिशत", "5.6 प्रतिशत"],
    8: ["₹4,000", "₹5,000", "₹6,000", "₹8,000", "₹10,000"],
    9: ["एकीकृत परीक्षण रेंज, चांदीपुर", "सतीश धवन अंतरिक्ष केंद्र, श्रीहरिकोटा", "पोखरण फील्ड फायरिंग रेंज",
        "थुंबा भूमध्यरेखीय प्रक्षेपण केंद्र", "अब्दुल कलाम द्वीप, बालासोर"],
    10: ["50 मीटर राइफल थ्री पोज़िशन", "10 मीटर एयर राइफल मिश्रित टीम", "25 मीटर रैपिड फायर पिस्टल",
         "ट्रैप मिश्रित टीम", "10 मीटर एयर पिस्टल पुरुष"],
    11: ["नॉर्वेजियन नोबेल समिति", "कैरोलिंस्का संस्थान", "रॉयल स्वीडिश एकेडमी ऑफ साइंसेज",
         "स्वीडिश एकेडमी", "नोबेल फाउंडेशन बोर्ड"],
    12: ["नाबार्ड", "एपीडा", "भारतीय खाद्य निगम", "भारतीय कृषि अनुसंधान परिषद", "नेफेड"],
    13: ["₹1 लाख", "₹2 लाख", "₹3 लाख", "₹4 लाख", "₹5 लाख"],
    14: ["एम. पतंजलि शास्त्री", "एच. जे. कानिया", "मेहर चंद महाजन", "बी. के. मुखर्जी", "एस. आर. दास"],
}

_THEMES: dict[str, str] = {
    "sample-agri-1": "Agriculture", "sample-national-1": "Agriculture", "sample-appoint-1": "Agriculture",
    "sample-banking-1": "Banking & Economy", "sample-econ-1": "Banking & Economy",
    "sample-science-1": "Science & Defence", "sample-defence-1": "Science & Defence",
    "sample-sports-1": "Awards & Sports", "sample-award-1": "Awards & Sports",
    "sample-env-1": "Health & Environment", "sample-intl-1": "Health & Environment",
    "sample-health-1": "Health & Environment", "sample-national-2": "National",
}


def _gk(*rows: tuple[str, str, str, str]) -> list[dict[str, str]]:
    return [{"label_en": a, "value_en": b, "label_hi": c, "value_hi": d} for a, b, c, d in rows]


_STATIC_GK: dict[str, list[dict[str, str]]] = {
    "sample-agri-1": _gk(("Institution", "NABARD", "संस्था", "नाबार्ड"),
                         ("Established", "12 July 1982", "स्थापना", "12 जुलाई 1982"),
                         ("Headquarters", "Mumbai, Maharashtra", "मुख्यालय", "मुंबई, महाराष्ट्र"),
                         ("Parent body", "Ministry of Finance", "मूल निकाय", "वित्त मंत्रालय")),
    "sample-banking-1": _gk(("Institution", "Reserve Bank of India", "संस्था", "भारतीय रिज़र्व बैंक"),
                            ("Established", "1 April 1935", "स्थापना", "1 अप्रैल 1935"),
                            ("Headquarters", "Mumbai, Maharashtra", "मुख्यालय", "मुंबई, महाराष्ट्र"),
                            ("MPC members", "6", "एमपीसी सदस्य", "6")),
    "sample-science-1": _gk(("Organisation", "ISRO", "संगठन", "इसरो"),
                            ("Established", "15 August 1969", "स्थापना", "15 अगस्त 1969"),
                            ("Headquarters", "Bengaluru, Karnataka", "मुख्यालय", "बेंगलुरु, कर्नाटक"),
                            ("Test facility", "Mahendragiri, Tamil Nadu", "परीक्षण केंद्र", "महेंद्रगिरि, तमिलनाडु")),
    "sample-env-1": _gk(("Mission", "National Solar Mission", "मिशन", "राष्ट्रीय सौर मिशन"),
                        ("Launched", "11 January 2010", "शुरुआत", "11 जनवरी 2010"),
                        ("Ministry", "New and Renewable Energy", "मंत्रालय", "नवीन एवं नवीकरणीय ऊर्जा"),
                        ("Installed solar capacity", "Over 90 GW", "स्थापित सौर क्षमता", "90 गीगावाट से अधिक")),
    "sample-intl-1": _gk(("WHO established", "7 April 1948", "डब्ल्यूएचओ स्थापना", "7 अप्रैल 1948"),
                         ("WHO headquarters", "Geneva, Switzerland", "डब्ल्यूएचओ मुख्यालय", "जिनेवा, स्विट्ज़रलैंड"),
                         ("FAO established", "16 October 1945", "एफएओ स्थापना", "16 अक्टूबर 1945"),
                         ("FAO headquarters", "Rome, Italy", "एफएओ मुख्यालय", "रोम, इटली")),
    "sample-econ-1": _gk(("Index", "Consumer Price Index (Combined)", "सूचकांक", "उपभोक्ता मूल्य सूचकांक (संयुक्त)"),
                         ("Released by", "National Statistical Office, MoSPI", "जारीकर्ता", "राष्ट्रीय सांख्यिकी कार्यालय, MoSPI"),
                         ("Base year", "2012", "आधार वर्ष", "2012"),
                         ("RBI target", "4 per cent (±2)", "आरबीआई लक्ष्य", "4 प्रतिशत (±2)")),
    "sample-national-1": _gk(("Scheme", "PM-KISAN", "योजना", "पीएम-किसान"),
                             ("Launched", "24 February 2019", "शुरुआत", "24 फरवरी 2019"),
                             ("Ministry", "Agriculture and Farmers Welfare", "मंत्रालय", "कृषि एवं किसान कल्याण"),
                             ("Benefit", "₹6,000 per year", "लाभ", "₹6,000 प्रति वर्ष")),
    "sample-defence-1": _gk(("Organisation", "DRDO", "संगठन", "डीआरडीओ"),
                            ("Established", "1958", "स्थापना", "1958"),
                            ("Headquarters", "New Delhi", "मुख्यालय", "नई दिल्ली"),
                            ("Test range", "Chandipur, Odisha", "परीक्षण रेंज", "चांदीपुर, ओडिशा")),
    "sample-sports-1": _gk(("Event", "Asian Games 2026", "आयोजन", "एशियाई खेल 2026"),
                           ("Host", "Aichi-Nagoya, Japan", "मेज़बान", "आइची-नागोया, जापान"),
                           ("Governing body", "Olympic Council of Asia", "शासी निकाय", "एशिया ओलंपिक परिषद"),
                           ("Event won", "10m Air Rifle Mixed Team", "जीता गया इवेंट", "10 मीटर एयर राइफल मिश्रित टीम")),
    "sample-award-1": _gk(("Awarded by", "Royal Swedish Academy of Sciences", "प्रदानकर्ता", "रॉयल स्वीडिश एकेडमी ऑफ साइंसेज"),
                          ("Instituted", "1968", "स्थापना", "1968"),
                          ("Announced in", "Stockholm, Sweden", "घोषणा स्थल", "स्टॉकहोम, स्वीडन")),
    "sample-appoint-1": _gk(("Institution", "ICAR", "संस्था", "भारतीय कृषि अनुसंधान परिषद"),
                            ("Established", "16 July 1929", "स्थापना", "16 जुलाई 1929"),
                            ("Headquarters", "New Delhi", "मुख्यालय", "नई दिल्ली"),
                            ("Ministry", "Agriculture and Farmers Welfare", "मंत्रालय", "कृषि एवं किसान कल्याण")),
    "sample-health-1": _gk(("Scheme", "Ayushman Bharat PM-JAY", "योजना", "आयुष्मान भारत पीएम-जय"),
                           ("Launched", "23 September 2018", "शुरुआत", "23 सितंबर 2018"),
                           ("Ministry", "Health and Family Welfare", "मंत्रालय", "स्वास्थ्य एवं परिवार कल्याण"),
                           ("Cover", "₹5 lakh per family per year", "कवर", "₹5 लाख प्रति परिवार प्रति वर्ष")),
    "sample-national-2": _gk(("Institution", "Supreme Court of India", "संस्था", "भारत का सर्वोच्च न्यायालय"),
                             ("Established", "26 January 1950", "स्थापना", "26 जनवरी 1950"),
                             ("Location", "New Delhi", "स्थान", "नई दिल्ली"),
                             ("First Chief Justice", "H. J. Kania", "प्रथम मुख्य न्यायाधीश", "एच. जे. कानिया")),
}

_seen_events: set[str] = set()
for _m in _MCQS:
    _m["options_hi"] = _OPTIONS_HI[_m["q_num"]]
    _m["theme"] = _THEMES.get(_m["event_id"], "National")
    if _m["event_id"] not in _seen_events:
        _seen_events.add(_m["event_id"])
        _m["static_gk"] = _STATIC_GK.get(_m["event_id"], [])


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
        "one_liners": [dict(ol) for ol in _ONE_LINERS],
    }


def build_sample_mcqs() -> list[dict[str, Any]]:
    """Return synthetic five-option MCQs with an answer key."""
    return [dict(m) for m in _MCQS]
