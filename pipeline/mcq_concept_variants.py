# -*- coding: utf-8 -*-
"""
Phrasing variants for the concept MCQ bank
==========================================
``KNOWN_MAPPINGS`` (pipeline/mcq_quality.py) holds one fixed question per known
topic, emitted whenever the topic's trigger matches a story.  That is why the MSP
question reprinted in 3 of the last 4 published editions: the topic never left
agri news, and there was only one way to ask it.  Distractor *order* is salted
per event, so the repeat looked new while the stem and the option set were
identical.

Each entry here is an alternative way to ask the same verified topic, with its
own ``guard`` and ``accept`` pair:

``guard``
    Matches **this phrasing only** — deliberately narrower than the entry's
    ``trigger``.  ``mapping_conflict`` and ``known_mapping_supports`` iterate
    every (guard, accept) pair, so a loose guard would let an unrelated — and
    wrong — answer through the answer guard.  Two variants of the same concept
    must not match each other's question either.
``accept``
    The verified key for that phrasing.  A concept question whose key does not
    occur in the story text survives ``key_check`` only because it is "backed"
    by a mapping pair, so a variant without an accept regex would be dropped.

Facts are statutory or historical (scheme design, mandates, launch years), never
"latest" figures, so nothing here goes stale with the news cycle.  Distractors
avoid officeholder titles: ``stale_title_error`` rejects an option that pairs a
post from config/current_facts.json with any other name-like words.

Options may carry an empty Hindi string when the English is a bare number or
year ("2019"); ``hindi_errors`` exempts those, and printing "2019 / 2019" would
only add noise.
"""
from __future__ import annotations

from typing import Any, Dict, List

CONCEPT_VARIANTS: Dict[str, List[Dict[str, Any]]] = {
    # ── MSP ────────────────────────────────────────────────────────────────
    "msp": [
        {"vid": "v1",
         "guard": r"(?:who|which)[^?]{0,60}(?:announc|declare)[^?]*(?:\bMSP\b|minimum support price)"
                   r"|(?:\bMSP\b|minimum support price)[^?]{0,60}(?:announc|declare)"
                   r"|न्यूनतम समर्थन मूल्य[^?]*घोषणा",
         "accept": r"Government of India|Central Government|Union Government|केंद्र सरकार",
         "q": ("Who announces the Minimum Support Price (MSP) for notified crops in India?",
               "भारत में अधिसूचित फसलों के लिए न्यूनतम समर्थन मूल्य (MSP) की घोषणा कौन करता है?"),
         "answer": ("The Government of India (Central Government)", "भारत सरकार (केंद्र सरकार)"),
         "expl": ("MSP for notified crops is announced by the Government of India, on the "
                  "recommendation of the Commission for Agricultural Costs and Prices (CACP).",
                  "अधिसूचित फसलों के लिए न्यूनतम समर्थन मूल्य की घोषणा भारत सरकार, कृषि लागत एवं "
                  "मूल्य आयोग (CACP) की सिफारिश पर करती है।"),
         "distractors": [
             ("Commission for Agricultural Costs and Prices (CACP)", "कृषि लागत एवं मूल्य आयोग (CACP)"),
             ("Reserve Bank of India (RBI)", "भारतीय रिज़र्व बैंक (RBI)"),
             ("NITI Aayog", "नीति आयोग"),
             ("Food Corporation of India (FCI)", "भारतीय खाद्य निगम (FCI)"),
             ("Finance Commission", "वित्त आयोग"),
             ("Indian Council of Agricultural Research (ICAR)", "भारतीय कृषि अनुसंधान परिषद (ICAR)"),
         ]},
        {"vid": "v2",
         "guard": r"(?:\bCACP\b|Commission for Agricultural Costs)[^?]{0,80}ministry"
                   r"|ministry[^?]{0,80}(?:\bCACP\b|Commission for Agricultural Costs)"
                   r"|(?:\bCACP\b|कृषि लागत एवं मूल्य आयोग)[^?]*मंत्रालय",
         "accept": r"Agriculture (?:and|&) Farmers Welfare|Ministry of Agriculture|कृषि एवं किसान कल्याण",
         "q": ("The Commission for Agricultural Costs and Prices (CACP) works under which Union Ministry?",
               "कृषि लागत एवं मूल्य आयोग (CACP) किस केंद्रीय मंत्रालय के अंतर्गत कार्य करता है?"),
         "answer": ("Ministry of Agriculture and Farmers Welfare", "कृषि एवं किसान कल्याण मंत्रालय"),
         "expl": ("The Commission for Agricultural Costs and Prices (CACP) is an attached office of the "
                  "Ministry of Agriculture and Farmers Welfare, and recommends MSP for notified crops.",
                  "कृषि लागत एवं मूल्य आयोग (CACP) कृषि एवं किसान कल्याण मंत्रालय का संबद्ध कार्यालय है "
                  "और अधिसूचित फसलों के लिए MSP की सिफारिश करता है।"),
         "distractors": [
             ("Ministry of Finance", "वित्त मंत्रालय"),
             ("Ministry of Consumer Affairs, Food and Public Distribution",
              "उपभोक्ता मामले, खाद्य एवं सार्वजनिक वितरण मंत्रालय"),
             ("Ministry of Commerce and Industry", "वाणिज्य एवं उद्योग मंत्रालय"),
             ("Ministry of Rural Development", "ग्रामीण विकास मंत्रालय"),
             ("Ministry of Food Processing Industries", "खाद्य प्रसंस्करण उद्योग मंत्रालय"),
         ]},
    ],

    # ── Repo rate ──────────────────────────────────────────────────────────
    "repo": [
        {"vid": "v1",
         "guard": r"committee[^?]{0,60}(?:\brepo rate\b|\bpolicy rate\b)"
                   r"|(?:\brepo rate\b|\bpolicy rate\b)[^?]{0,60}committee|रेपो दर[^?]*समिति",
         "accept": r"Monetary Policy Committee|\bMPC\b|मुद्रा नीति समिति",
         "q": ("Which committee of the Reserve Bank of India decides the policy repo rate?",
               "भारतीय रिज़र्व बैंक की कौन-सी समिति नीतिगत रेपो दर तय करती है?"),
         "answer": ("Monetary Policy Committee (MPC)", "मुद्रा नीति समिति (MPC)"),
         "expl": ("The Monetary Policy Committee (MPC) of the Reserve Bank of India decides the policy "
                  "repo rate; it has six members, three from the RBI and three appointed by the Government.",
                  "भारतीय रिज़र्व बैंक की मुद्रा नीति समिति (MPC) नीतिगत रेपो दर तय करती है; इसके छह "
                  "सदस्य होते हैं — तीन RBI से और तीन सरकार द्वारा नियुक्त।"),
         "distractors": [
             ("Financial Stability and Development Council (FSDC)", "वित्तीय स्थिरता एवं विकास परिषद (FSDC)"),
             ("RBI Central Board of Directors", "RBI केंद्रीय निदेशक मंडल"),
             ("Securities and Exchange Board of India (SEBI)", "भारतीय प्रतिभूति एवं विनिमय बोर्ड (SEBI)"),
             ("Insolvency and Bankruptcy Board of India (IBBI)", "दिवाला एवं शोधन अक्षमता बोर्ड (IBBI)"),
             ("Standing Committee on Finance", "वित्त संबंधी स्थायी समिति"),
         ]},
        {"vid": "v2",
         "guard": r"how many members[^?]{0,60}(?:\bMPC\b|Monetary Policy Committee)"
                   r"|(?:\bMPC\b|Monetary Policy Committee)[^?]{0,60}how many members"
                   r"|मुद्रा नीति समिति[^?]*कितने सदस्य",
         "accept": r"\bSix\b|\b6\b|छह",
         "q": ("The Monetary Policy Committee (MPC) that decides the policy repo rate has how many members?",
               "नीतिगत रेपो दर तय करने वाली मुद्रा नीति समिति (MPC) में कितने सदस्य होते हैं?"),
         "answer": ("Six members", "छह सदस्य"),
         "expl": ("The Monetary Policy Committee has six members: the RBI Governor, the Deputy Governor in "
                  "charge of monetary policy, one officer of the RBI nominated by its Central Board, and "
                  "three members appointed by the Government of India.",
                  "मुद्रा नीति समिति में छह सदस्य होते हैं: RBI गवर्नर, मुद्रा नीति प्रभारी डिप्टी गवर्नर, "
                  "केंद्रीय बोर्ड द्वारा नामित एक RBI अधिकारी, तथा भारत सरकार द्वारा नियुक्त तीन सदस्य।"),
         "distractors": [
             ("Four members", "चार सदस्य"),
             ("Five members", "पाँच सदस्य"),
             ("Seven members", "सात सदस्य"),
             ("Eight members", "आठ सदस्य"),
             ("Nine members", "नौ सदस्य"),
         ]},
    ],

    # ── GST ────────────────────────────────────────────────────────────────
    "gst": [
        {"vid": "v1",
         "guard": r"amendment[^?]{0,60}(?:\bGST\b|Goods and Services Tax)"
                   r"|(?:\bGST\b|Goods and Services Tax)[^?]{0,60}amendment"
                   r"|(?:\bGST\b|वस्तु एवं सेवा कर)[^?]*संशोधन",
         "accept": r"101st|101वाँ|101वें",
         "q": ("Which constitutional amendment introduced the Goods and Services Tax (GST) in India?",
               "भारत में वस्तु एवं सेवा कर (GST) किस संवैधानिक संशोधन द्वारा लाया गया?"),
         "answer": ("The 101st Constitutional Amendment Act, 2016",
                    "101वाँ संवैधानिक संशोधन अधिनियम, 2016"),
         "expl": ("GST was introduced by the Constitution (One Hundred and First Amendment) Act, 2016 — "
                  "the 101st Constitutional Amendment Act, 2016 — and came into effect on 1 July 2017.",
                  "GST को 101वें संवैधानिक संशोधन अधिनियम, 2016 द्वारा लाया गया और यह 1 जुलाई 2017 से "
                  "लागू हुआ।"),
         "distractors": [
             ("The 42nd Constitutional Amendment Act, 1976", "42वाँ संवैधानिक संशोधन अधिनियम, 1976"),
             ("The 73rd Constitutional Amendment Act, 1992", "73वाँ संवैधानिक संशोधन अधिनियम, 1992"),
             ("The 103rd Constitutional Amendment Act, 2019", "103वाँ संवैधानिक संशोधन अधिनियम, 2019"),
             ("The 44th Constitutional Amendment Act, 1978", "44वाँ संवैधानिक संशोधन अधिनियम, 1978"),
             ("The 122nd Constitutional Amendment Bill, 2014", "122वाँ संवैधानिक संशोधन विधेयक, 2014"),
         ]},
        {"vid": "v2",
         "guard": r"chairs?[^?]{0,40}GST Council|GST Council[^?]{0,40}chair"
                   r"|GST परिषद[^?]*अध्यक्षता",
         "accept": r"Union Finance Minister|Finance Minister|केंद्रीय वित्त मंत्री",
         "q": ("Who chairs the GST Council that recommends rates of Goods and Services Tax (GST)?",
               "GST दरों की सिफारिश करने वाली GST परिषद की अध्यक्षता कौन करता है?"),
         "answer": ("Union Finance Minister", "केंद्रीय वित्त मंत्री"),
         "expl": ("The GST Council is chaired by the Union Finance Minister; State Finance Ministers are "
                  "its members, and the Council recommends the rates of Goods and Services Tax (GST).",
                  "GST परिषद की अध्यक्षता केंद्रीय वित्त मंत्री करते हैं; राज्यों के वित्त मंत्री इसके सदस्य "
                  "होते हैं और परिषद वस्तु एवं सेवा कर (GST) की दरों की सिफारिश करती है।"),
         "distractors": [
             ("Prime Minister of India", "भारत के प्रधानमंत्री"),
             ("The Central Board of Direct Taxes", "केंद्रीय प्रत्यक्ष कर बोर्ड"),
             ("The Secretary, Department of Revenue", "राजस्व विभाग के सचिव"),
             ("Comptroller and Auditor General of India", "भारत के नियंत्रक एवं महालेखा परीक्षक"),
             ("The NITI Aayog", "नीति आयोग"),
         ]},
    ],

    # ── UPI ────────────────────────────────────────────────────────────────
    "upi": [
        {"vid": "v1",
         "guard": r"(?:\bUPI\b|Unified Payments Interface)[^?]{0,60}(?:built on|infrastructure)"
                   r"|(?:built on|infrastructure)[^?]{0,60}(?:\bUPI\b|Unified Payments Interface)"
                   r"|(?:\bUPI\b|यूपीआई)[^?]*अवसंरचना",
         "accept": r"Immediate Payment Service|ImPS|इमिडिएट पेमेंट",
         "q": ("The Unified Payments Interface (UPI) is built on which existing payment infrastructure?",
               "यूनिफाइड पेमेंट्स इंटरफेस (UPI) किस मौजूदा भुगतान अवसंरचना पर बना है?"),
         "answer": ("Immediate Payment Service (ImPS)", "इमिडिएट पेमेंट सर्विस (ImPS)"),
         "expl": ("UPI, operated by the National Payments Corporation of India (NPCI), is built on the "
                  "Immediate Payment Service (ImPS) infrastructure, which allows round-the-clock interbank "
                  "transfers.",
                  "NPCI द्वारा संचालित UPI इमिडिएट पेमेंट सर्विस (ImPS) अवसंरचना पर बना है, जो "
                  "चौबीसों घंटे इंटरबैंक लेनदेन की सुविधा देती है।"),
         "distractors": [
             ("Real Time Gross Settlement (RTGS)", "रियल टाइम ग्रॉस सेटलमेंट (RTGS)"),
             ("National Electronic Funds Transfer (NEFT)", "नेशनल इलेक्ट्रॉनिक फंड ट्रांसफर (NEFT)"),
             ("Electronic Clearing Service (ECS)", "इलेक्ट्रॉनिक क्लियरिंग सर्विस (ECS)"),
             ("Bharat Bill Payment System (BBPS)", "भारत बिल भुगतान प्रणाली (BBPS)"),
             ("Core Banking Solution (CBS)", "कोर बैंकिंग सॉल्यूशन (CBS)"),
         ]},
        {"vid": "v2",
         "guard": r"Payment and Settlement Systems Act|regulates payment systems"
                   r"|भुगतान एवं निपटान प्रणाली अधिनियम",
         "accept": r"Reserve Bank|\bRBI\b|भारतीय रिज़र्व बैंक",
         "q": ("Which body regulates payment systems in India under the Payment and Settlement Systems "
               "Act, 2007?",
               "भुगतान एवं निपटान प्रणाली अधिनियम, 2007 के तहत भारत में भुगतान प्रणालियों का विनियमन "
               "कौन करता है?"),
         "answer": ("The Reserve Bank of India (RBI)", "भारतीय रिज़र्व बैंक (RBI)"),
         "expl": ("Under the Payment and Settlement Systems Act, 2007, the Reserve Bank of India (RBI) "
                  "regulates payment systems in India, including the Unified Payments Interface operated "
                  "by NPCI.",
                  "भुगतान एवं निपटान प्रणाली अधिनियम, 2007 के तहत भारतीय रिज़र्व बैंक (RBI) भारत में "
                  "भुगतान प्रणालियों का विनियमन करता है, जिसमें NPCI द्वारा संचालित UPI भी शामिल है।"),
         "distractors": [
             ("National Payments Corporation of India (NPCI)", "नेशनल पेमेंट्स कॉर्पोरेशन ऑफ इंडिया (NPCI)"),
             ("Securities and Exchange Board of India (SEBI)", "भारतीय प्रतिभूति एवं विनिमय बोर्ड (SEBI)"),
             ("Ministry of Electronics and Information Technology", "इलेक्ट्रॉनिक्स एवं सूचना प्रौद्योगिकी मंत्रालय"),
             ("Indian Banks' Association (IBA)", "इंडियन बैंक्स एसोसिएशन (IBA)"),
             ("Insurance Regulatory and Development Authority of India (IRDAI)", "इरदाई (IRDAI)"),
         ]},
    ],

    # ── Jal Jeevan Mission ─────────────────────────────────────────────────
    "jjm": [
        {"vid": "v1",
         "guard": r"Jal Jeevan Mission[^?]{0,80}(?:aims? to provide|objective|target)"
                   r"|(?:aims? to provide|objective)[^?]{0,80}Jal Jeevan Mission"
                   r"|जल जीवन मिशन[^?]*लक्ष्य",
         "accept": r"Functional Household Tap Connection|FHTC|नल कनेक्शन",
         "q": ("The Jal Jeevan Mission aims to provide which of the following to every rural household?",
               "जल जीवन मिशन का लक्ष्य हर ग्रामीण परिवार को निम्नलिखित में से क्या उपलब्ध कराना है?"),
         "answer": ("Functional Household Tap Connection (FHTC) for safe drinking water",
                    "सुरक्षित पेयजल के लिए कार्यात्मक घरेलू नल कनेक्शन (FHTC)"),
         "expl": ("Jal Jeevan Mission, implemented by the Ministry of Jal Shakti, aims to provide a "
                  "Functional Household Tap Connection (FHTC) delivering safe drinking water to every "
                  "rural household.",
                  "जल शक्ति मंत्रालय द्वारा क्रियान्वित जल जीवन मिशन का लक्ष्य हर ग्रामीण परिवार को सुरक्षित "
                  "पेयजल के लिए कार्यात्मक घरेलू नल कनेक्शन (FHTC) उपलब्ध कराना है।"),
         "distractors": [
             ("A subsidised electric connection", "रियायती बिजली कनेक्शन"),
             ("A pucca house under a rural housing scheme", "ग्रामीण आवास योजना के तहत पक्का मकान"),
             ("An LPG connection", "एक एलपीजी कनेक्शन"),
             ("A bank account with overdraft facility", "ओवरड्राफ्ट सुविधा वाला बैंक खाता"),
             ("Free health insurance cover", "मुफ़्त स्वास्थ्य बीमा कवर"),
         ]},
        {"vid": "v2",
         "guard": r"Jal Jeevan Mission[^?]{0,60}which year|which year[^?]{0,60}Jal Jeevan Mission"
                   r"|जल जीवन मिशन[^?]*किस वर्ष",
         "accept": r"\b2019\b",
         "q": ("In which year was the Jal Jeevan Mission launched?",
               "जल जीवन मिशन किस वर्ष शुरू किया गया?"),
         "answer": ("2019", ""),
         "expl": ("Jal Jeevan Mission was launched on 15 August 2019 to provide a Functional Household Tap "
                  "Connection to every rural household.",
                  "जल जीवन मिशन 15 अगस्त 2019 को शुरू किया गया, जिसका लक्ष्य हर ग्रामीण परिवार को नल "
                  "कनेक्शन उपलब्ध कराना है।"),
         "distractors": [("2015", ""), ("2016", ""), ("2017", ""), ("2020", ""), ("2021", "")]},
    ],

    # ── MGNREGA ────────────────────────────────────────────────────────────
    "mgnrega": [
        {"vid": "v1",
         "guard": r"MGNREGA[S]?[^?]{0,80}(?:guarantees?|how many days)[^?]{0,40}(?:days|employment)"
                   r"|मनरेगा[^?]*कितने दिन",
         "accept": r"\b100\b",
         "q": ("MGNREGA guarantees how many days of wage employment per household in a financial year?",
               "मनरेगा एक वित्त वर्ष में प्रति परिवार कितने दिनों के मजदूरी रोजगार की गारंटी देता है?"),
         "answer": ("100 days", "100 दिन"),
         "expl": ("MGNREGA guarantees 100 days of unskilled manual wage employment per household in a "
                  "financial year, and is administered by the Ministry of Rural Development.",
                  "मनरेगा प्रति परिवार एक वित्त वर्ष में 100 दिनों के अकुशल शारीरिक मजदूरी रोजगार की गारंटी "
                  "देता है; इसका संचालन ग्रामीण विकास मंत्रालय करता है।"),
         "distractors": [("60 days", "60 दिन"), ("90 days", "90 दिन"), ("120 days", "120 दिन"),
                         ("150 days", "150 दिन"), ("200 days", "200 दिन")]},
        {"vid": "v2",
         "guard": r"within how many days|within[^?]{0,40}days of[^?]{0,40}demand"
                   r"|कितने दिनों के भीतर",
         "accept": r"\b15\b",
         "q": ("Under MGNREGA, work must be provided to an applicant within how many days of the demand "
               "for work?",
               "मनरेगा के तहत काम की मांग के कितने दिनों के भीतर आवेदक को रोजगार देना अनिवार्य है?"),
         "answer": ("15 days", "15 दिन"),
         "expl": ("Under MGNREGA work must be provided within 15 days of the demand for work; if it is not, "
                  "the applicant is entitled to an unemployment allowance.",
                  "मनरेगा के तहत काम की मांग के 15 दिनों के भीतर रोजगार देना अनिवार्य है; ऐसा न होने पर "
                  "आवेदक बेरोजगारी भत्ते का हकदार होता है।"),
         "distractors": [("7 days", "7 दिन"), ("10 days", "10 दिन"), ("30 days", "30 दिन"),
                         ("45 days", "45 दिन"), ("60 days", "60 दिन")]},
    ],

    # ── PM-JAY ─────────────────────────────────────────────────────────────
    "pmjay": [
        {"vid": "v1",
         "guard": r"(?:\bPM-JAY\b|\bPMJAY\b|Ayushman Bharat)[^?]{0,60}(?:cover|sum insured)"
                   r"|(?:cover|sum insured)[^?]{0,60}(?:\bPM-JAY\b|\bPMJAY\b|Ayushman Bharat)"
                   r"|(?:PM-JAY|आयुष्मान भारत)[^?]*कवर",
         "accept": r"5 lakh|\u20b95|Rs\.?\s?5",
         "q": ("What is the annual health cover provided per family under PM-JAY?",
               "PM-JAY के तहत प्रति परिवार वार्षिक स्वास्थ्य बीमा कवर कितना है?"),
         "answer": ("Rs. 5 lakh per family per year", "प्रति परिवार प्रति वर्ष 5 लाख रुपये"),
         "expl": ("PM-JAY provides a health cover of Rs. 5 lakh per family per year for secondary and "
                  "tertiary care hospitalisation, and is implemented by the National Health Authority.",
                  "PM-JAY प्रति परिवार प्रति वर्ष 5 लाख रुपये का स्वास्थ्य कवर देता है, जो द्वितीयक एवं "
                  "तृतीयक देखभाल अस्पताल भर्ती के लिए है; इसे राष्ट्रीय स्वास्थ्य प्राधिकरण क्रियान्वित "
                  "करता है।"),
         "distractors": [
             ("Rs. 1 lakh per family per year", "प्रति परिवार प्रति वर्ष 1 लाख रुपये"),
             ("Rs. 2 lakh per family per year", "प्रति परिवार प्रति वर्ष 2 लाख रुपये"),
             ("Rs. 3 lakh per family per year", "प्रति परिवार प्रति वर्ष 3 लाख रुपये"),
             ("Rs. 7.5 lakh per family per year", "प्रति परिवार प्रति वर्ष 7.5 लाख रुपये"),
             ("Rs. 10 lakh per family per year", "प्रति परिवार प्रति वर्ष 10 लाख रुपये"),
         ]},
        {"vid": "v2",
         "guard": r"(?:\bPM-JAY\b|\bPMJAY\b|Ayushman Bharat)[^?]{0,80}(?:identified|database|basis)"
                   r"|(?:PM-JAY|आयुष्मान भारत)[^?]*डेटाबेस",
         "accept": r"Socio-Economic Caste Census|SECC|सामाजिक-आर्थिक जाति जनगणना",
         "q": ("Beneficiaries of PM-JAY are identified on the basis of which database?",
               "PM-JAY के लाभार्थियों की पहचान किस डेटाबेस के आधार पर की जाती है?"),
         "answer": ("Socio-Economic Caste Census (SECC)", "सामाजिक-आर्थिक जाति जनगणना (SECC)"),
         "expl": ("PM-JAY beneficiaries are identified on the basis of the Socio-Economic Caste Census "
                  "(SECC); the scheme is implemented by the National Health Authority.",
                  "PM-JAY के लाभार्थियों की पहचान सामाजिक-आर्थिक जाति जनगणना (SECC) के आधार पर की जाती है; "
                  "योजना का क्रियान्वयन राष्ट्रीय स्वास्थ्य प्राधिकरण करता है।"),
         "distractors": [
             ("Aadhaar enrolment data", "आधार नामांकन डेटा"),
             ("National Population Register", "राष्ट्रीय जनसंख्या रजिस्टर"),
             ("Census of India 2011", "भारत जनगणना 2011"),
             ("National Sample Survey data", "राष्ट्रीय प्रतिदर्श सर्वेक्षण डेटा"),
             ("NITI Aayog multidimensional poverty index", "नीति आयोग बहुआयामी गरीबी सूचकांक"),
         ]},
    ],

    # ── e-NAM ──────────────────────────────────────────────────────────────
    "enam": [
        {"vid": "v1",
         "guard": r"(?:e-NAM|\beNAM\b|National Agriculture Market)[^?]{0,80}(?:integrates|single national market)"
                   r"|(?:e-NAM|ई-नाम)[^?]*जोड़ता है",
         "accept": r"APMC|Agricultural Produce Market|एपीएमसी",
         "q": ("The e-NAM platform integrates which of the following into a single national market?",
               "e-NAM प्लेटफ़ॉर्म निम्नलिखित में से किसे एक राष्ट्रीय बाजार में जोड़ता है?"),
         "answer": ("APMC mandis (Agricultural Produce Market Committees)",
                    "एपीएमसी मंडियाँ (कृषि उत्पाद बाजार समितियाँ)"),
         "expl": ("e-NAM, whose lead implementing agency is the Small Farmers' Agribusiness Consortium "
                  "(SFAC), integrates APMC mandis (Agricultural Produce Market Committees) into a single "
                  "national market for agricultural produce.",
                  "e-NAM, जिसकी प्रमुख क्रियान्वयन एजेंसी लघु किसान कृषि व्यवसाय कंसोर्टियम (SFAC) है, "
                  "एपीएमसी मंडियों (कृषि उत्पाद बाजार समितियों) को कृषि उपज के लिए एक राष्ट्रीय बाजार में "
                  "जोड़ता है।"),
         "distractors": [
             ("Retail supermarket chains", "खुदरा सुपरमार्केट श्रृंखलाएँ"),
             ("Cooperative credit societies", "सहकारी ऋण समितियाँ"),
             ("Food processing units", "खाद्य प्रसंस्करण इकाइयाँ"),
             ("Warehouses of the Food Corporation of India", "भारतीय खाद्य निगम के गोदाम"),
             ("Rural haats only", "केवल ग्रामीण हाट"),
         ]},
        {"vid": "v2",
         "guard": r"(?:e-NAM|\beNAM\b|National Agriculture Market)[^?]{0,60}which year"
                   r"|which year[^?]{0,60}(?:e-NAM|\beNAM\b|National Agriculture Market)"
                   r"|(?:e-NAM|ई-नाम)[^?]*किस वर्ष",
         "accept": r"\b2016\b",
         "q": ("In which year was the National Agriculture Market (e-NAM) launched?",
               "राष्ट्रीय कृषि बाजार (e-NAM) किस वर्ष शुरू किया गया?"),
         "answer": ("2016", ""),
         "expl": ("The National Agriculture Market (e-NAM) was launched in April 2016, with the Small "
                  "Farmers' Agribusiness Consortium (SFAC) as its lead implementing agency.",
                  "राष्ट्रीय कृषि बाजार (e-NAM) अप्रैल 2016 में शुरू किया गया, जिसकी प्रमुख क्रियान्वयन "
                  "एजेंसी लघु किसान कृषि व्यवसाय कंसोर्टियम (SFAC) है।"),
         "distractors": [("2014", ""), ("2015", ""), ("2017", ""), ("2018", ""), ("2019", "")]},
    ],
}
