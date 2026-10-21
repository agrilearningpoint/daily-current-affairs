# -*- coding: utf-8 -*-
"""
STATIC GK KNOWLEDGE BASE (Bilingual Indian & International Institutions)
Authoritative, verified factual reference for competitive exam current affairs.
Matches UPSC, UPSSSC AGTA, IBPS AFO, ICAR, NABARD, FCI, and State PCS coaching standards.
"""
from __future__ import annotations
from typing import Dict, List, Tuple, Any

# Master Entity Database: (English Name, Hindi Name, Paired Static GK Facts)
# Each fact is a tuple: (English statement, Hindi statement)
ENTITY_STATIC_DB: Dict[str, Dict[str, Any]] = {
    "ICAR": {
        "name_en": "Indian Council of Agricultural Research (ICAR)",
        "name_hi": "भारतीय कृषि अनुसंधान परिषद (ICAR)",
        "facts": [
            ("The Indian Council of Agricultural Research (ICAR) was established on 16 July 1929.",
             "भारतीय कृषि अनुसंधान परिषद (ICAR) की स्थापना 16 जुलाई 1929 को हुई थी।"),
            ("ICAR is headquartered in New Delhi.",
             "ICAR का मुख्यालय नई दिल्ली में स्थित है।"),
            ("ICAR functions under the Department of Agricultural Research and Education (DARE), Ministry of Agriculture and Farmers Welfare.",
             "ICAR कृषि एवं किसान कल्याण मंत्रालय के कृषि अनुसंधान और शिक्षा विभाग (DARE) के अंतर्गत कार्य करता है।"),
            ("The Union Minister of Agriculture serves as the President of the ICAR Society.",
             "केंद्रीय कृषि मंत्री ICAR सोसाइटी के अध्यक्ष के रूप में कार्य करते हैं।"),
            ("ICAR is the apex body for coordinating, guiding and managing research and education in agriculture in India.",
             "ICAR भारत में कृषि अनुसंधान और शिक्षा के समन्वय, मार्गदर्शन और प्रबंधन के लिए सर्वोच्च निकाय है।"),
        ]
    },
    "IARI": {
        "name_en": "ICAR-Indian Agricultural Research Institute (IARI)",
        "name_hi": "ICAR-भारतीय कृषि अनुसंधान संस्थान (IARI)",
        "facts": [
            ("ICAR-Indian Agricultural Research Institute (IARI) was established in 1905 at Pusa, Bihar, and later relocated to New Delhi in 1936.",
             "ICAR-भारतीय कृषि अनुसंधान संस्थान (IARI) की स्थापना 1905 में पूसा, बिहार में हुई थी, जिसे 1936 में नई दिल्ली स्थानांतरित किया गया।"),
            ("IARI is popularly known as the 'Pusa Institute'.",
             "IARI को लोकप्रिय रूप से 'पूसा संस्थान' के रूप में जाना जाता है।"),
            ("IARI is located in Pusa, New Delhi.",
             "IARI पूसा, नई दिल्ली में स्थित है।"),
            ("IARI is India's premier national institute for agricultural research, education and extension.",
             "IARI कृषि अनुसंधान, शिक्षा और विस्तार के लिए भारत का प्रमुख राष्ट्रीय संस्थान है।"),
            ("The institute is responsible for the research leading to the Green Revolution in India in the 1970s.",
             "यह संस्थान 1970 के दशक में भारत में हरित क्रांति लाने वाले ऐतिहासिक अनुसंधानों के लिए जाना जाता है।"),
        ]
    },
    "NABARD": {
        "name_en": "National Bank for Agriculture and Rural Development (NABARD)",
        "name_hi": "राष्ट्रीय कृषि और ग्रामीण विकास बैंक (NABARD)",
        "facts": [
            ("National Bank for Agriculture and Rural Development (NABARD) was established on 12 July 1982.",
             "राष्ट्रीय कृषि और ग्रामीण विकास बैंक (NABARD) की स्थापना 12 जुलाई 1982 को हुई थी।"),
            ("NABARD was established on the recommendations of the B. Sivaraman Committee.",
             "NABARD की स्थापना बी. शिवरामन समिति की सिफारिशों के आधार पर की गई थी।"),
            ("NABARD was set up under the National Bank for Agriculture and Rural Development Act, 1981.",
             "NABARD की स्थापना राष्ट्रीय कृषि और ग्रामीण विकास बैंक अधिनियम, 1981 के तहत की गई थी।"),
            ("NABARD is headquartered in Mumbai, Maharashtra.",
             "NABARD का मुख्यालय मुंबई, महाराष्ट्र में स्थित है।"),
            ("NABARD provides refinance support for agriculture, rural infrastructure development (RIDF), and microfinance.",
             "NABARD कृषि, ग्रामीण अवसंरचना विकास (RIDF) और सूक्ष्म वित्त के लिए पुनर्वित्त सहायता प्रदान करता है।"),
        ]
    },
    "FCI": {
        "name_en": "Food Corporation of India (FCI)",
        "name_hi": "भारतीय खाद्य निगम (FCI)",
        "facts": [
            ("Food Corporation of India (FCI) was established on 14 January 1965 under the Food Corporations Act, 1964.",
             "भारतीय खाद्य निगम (FCI) की स्थापना खाद्य निगम अधिनियम, 1964 के तहत 14 जनवरी 1965 को हुई थी।"),
            ("FCI is headquartered in New Delhi.",
             "FCI का मुख्यालय नई दिल्ली में स्थित है।"),
            ("FCI functions under the Ministry of Consumer Affairs, Food and Public Distribution.",
             "FCI उपभोक्ता मामले, खाद्य एवं सार्वजनिक वितरण मंत्रालय के अंतर्गत कार्य करता है।"),
            ("FCI is responsible for procuring foodgrains at Minimum Support Price (MSP), maintaining buffer stocks, and distribution via PDS.",
             "FCI न्यूनतम समर्थन मूल्य (MSP) पर खाद्यान्न की खरीद, बफर स्टॉक का रखरखाव और सार्वजनिक वितरण प्रणाली (PDS) के जरिए वितरण हेतु जिम्मेदार है।"),
        ]
    },
    "APEDA": {
        "name_en": "Agricultural and Processed Food Products Export Development Authority (APEDA)",
        "name_hi": "कृषि एवं प्रसंस्कृत खाद्य उत्पाद निर्यात विकास प्राधिकरण (APEDA)",
        "facts": [
            ("APEDA was established by the Government of India under the APEDA Act passed by Parliament in December 1985.",
             "APEDA की स्थापना भारत सरकार द्वारा दिसंबर 1985 में संसद द्वारा पारित APEDA अधिनियम के तहत की गई थी।"),
            ("APEDA functions under the Ministry of Commerce and Industry.",
             "APEDA वाणिज्य एवं उद्योग मंत्रालय के अंतर्गत कार्य करता है।"),
            ("APEDA is headquartered in New Delhi.",
             "APEDA का मुख्यालय नई दिल्ली में स्थित है।"),
            ("APEDA is responsible for export promotion and development of scheduled agro-products including Basmati rice, fruits, and meat products.",
             "APEDA बासमती चावल, फल और मांस उत्पादों सहित अनुसूचित कृषि उत्पादों के निर्यात संवर्धन और विकास के लिए जिम्मेदार है।"),
        ]
    },
    "NAFED": {
        "name_en": "National Agricultural Cooperative Marketing Federation of India (NAFED)",
        "name_hi": "भारतीय राष्ट्रीय कृषि सहकारी विपणन संघ (NAFED)",
        "facts": [
            ("NAFED was established on 2 October 1958 on the auspicious occasion of Gandhi Jayanti.",
             "NAFED की स्थापना 2 अक्टूबर 1958 को गांधी जयंती के शुभ अवसर पर हुई थी।"),
            ("NAFED is registered under the Multi-State Co-operative Societies Act.",
             "NAFED बहु-राज्य सहकारी सोसायटी अधिनियम के तहत पंजीकृत है।"),
            ("NAFED is headquartered in New Delhi.",
             "NAFED का मुख्यालय नई दिल्ली में स्थित है।"),
            ("NAFED is one of the central nodal agencies for procurement of oilseeds, pulses and copra under Price Support Scheme (PSS).",
             "NAFED मूल्य समर्थन योजना (PSS) के तहत तिलहन, दलहन और खोपरा की खरीद के लिए प्रमुख केंद्रीय नोडल एजेंसियों में से एक है।"),
        ]
    },
    "RBI": {
        "name_en": "Reserve Bank of India (RBI)",
        "name_hi": "भारतीय रिज़र्व बैंक (RBI)",
        "facts": [
            ("The Reserve Bank of India (RBI) was established on 1 April 1935 under the Reserve Bank of India Act, 1934.",
             "भारतीय रिज़र्व बैंक (RBI) की स्थापना भारतीय रिज़र्व बैंक अधिनियम, 1934 के तहत 1 अप्रैल 1935 को हुई थी।"),
            ("RBI was established on the recommendations of the Hilton Young Commission (Royal Commission on Indian Currency and Finance).",
             "RBI की स्थापना हिल्टन यंग कमीशन (रॉयल कमीशन ऑन इंडियन करेंसी एंड फाइनेंस) की सिफारिशों पर की गई थी।"),
            ("RBI was nationalised on 1 January 1949.",
             "RBI का राष्ट्रीयकरण 1 जनवरी 1949 को किया गया था।"),
            ("RBI is headquartered in Mumbai, Maharashtra.",
             "RBI का मुख्यालय मुंबई, महाराष्ट्र में स्थित है।"),
            ("The Central Office of RBI was initially established in Calcutta but was permanently moved to Mumbai in 1937.",
             "RBI का केंद्रीय कार्यालय प्रारंभ में कलकत्ता में स्थापित किया गया था लेकिन 1937 में इसे स्थायी रूप से मुंबई स्थानांतरित कर दिया गया।"),
        ]
    },
    "SEBI": {
        "name_en": "Securities and Exchange Board of India (SEBI)",
        "name_hi": "भारतीय प्रतिभूति और विनिमय बोर्ड (SEBI)",
        "facts": [
            ("The Securities and Exchange Board of India (SEBI) was established in 1988 as a non-statutory body.",
             "भारतीय प्रतिभूति और विनिमय बोर्ड (SEBI) की स्थापना 1988 में एक गैर-सांविधिक निकाय के रूप में हुई थी।"),
            ("SEBI was accorded statutory status on 30 January 1992 through the SEBI Act, 1992.",
             "SEBI को SEBI अधिनियम, 1992 के माध्यम से 30 जनवरी 1992 को वैधानिक दर्जा प्रदान किया गया।"),
            ("SEBI is headquartered in Mumbai, Maharashtra.",
             "SEBI का मुख्यालय मुंबई, महाराष्ट्र में स्थित है।"),
            ("SEBI regulates the securities and commodities market in India to protect the interests of investors.",
             "SEBI भारत में निवेशकों के हितों की रक्षा के लिए प्रतिभूति और कमोडिटी बाजार का विनियमन करता है।"),
        ]
    },
    "IRDAI": {
        "name_en": "Insurance Regulatory and Development Authority of India (IRDAI)",
        "name_hi": "भारतीय बीमा विनियामक और विकास प्राधिकरण (IRDAI)",
        "facts": [
            ("The Insurance Regulatory and Development Authority of India (IRDAI) was established in 1999 following the recommendations of the Malhotra Committee.",
             "भारतीय बीमा विनियामक और विकास प्राधिकरण (IRDAI) की स्थापना मल्होत्रा समिति की सिफारिशों के बाद 1999 में हुई थी।"),
            ("IRDAI was constituted as an autonomous statutory body under the Insurance Regulatory and Development Authority Act, 1999.",
             "IRDAI को बीमा विनियामक और विकास प्राधिकरण अधिनियम, 1999 के तहत एक स्वायत्त वैधानिक निकाय के रूप में गठित किया गया था।"),
            ("IRDAI is headquartered in Hyderabad, Telangana.",
             "IRDAI का मुख्यालय हैदराबाद, तेलंगाना में स्थित है।"),
            ("IRDAI regulates and promotes the insurance and re-insurance industries in India.",
             "IRDAI भारत में बीमा और पुनर्बीमा उद्योगों का विनियमन और संवर्धन करता है।"),
        ]
    },
    "WORLD_BANK": {
        "name_en": "World Bank",
        "name_hi": "विश्व बैंक (World Bank)",
        "facts": [
            ("The World Bank was established in July 1944 at the Bretton Woods Conference alongside the IMF.",
             "विश्व बैंक की स्थापना जुलाई 1944 में आईएमएफ के साथ ब्रेटन वुड्स सम्मेलन में हुई थी।"),
            ("Headquarters of the World Bank is located in Washington, D.C., United States.",
             "विश्व बैंक का मुख्यालय वॉशिंगटन, डी.सी., संयुक्त राज्य अमेरिका में स्थित है।"),
            ("The World Bank Group comprises five institutions: IBRD, IDA, IFC, MIGA, and ICSID.",
             "विश्व बैंक समूह में पाँच संस्थाएँ शामिल हैं: IBRD, IDA, IFC, MIGA और ICSID।"),
            ("The International Bank for Reconstruction and Development (IBRD) has 189 member countries.",
             "अंतर्राष्ट्रीय पुनर्निर्माण और विकास बैंक (IBRD) के 189 सदस्य देश हैं।"),
        ]
    },
    "FAO": {
        "name_en": "Food and Agriculture Organization (FAO)",
        "name_hi": "खाद्य एवं कृषि संगठन (FAO)",
        "facts": [
            ("The Food and Agriculture Organization (FAO) was established on 16 October 1945 in Quebec City, Canada.",
             "खाद्य एवं कृषि संगठन (FAO) की स्थापना 16 अक्टूबर 1945 को क्यूबेक सिटी, कनाडा में हुई थी।"),
            ("FAO is headquartered in Rome, Italy.",
             "FAO का मुख्यालय रोम, इटली में स्थित है।"),
            ("World Food Day is celebrated every year on 16 October to mark the founding anniversary of FAO.",
             "FAO के स्थापना दिवस के उपलक्ष्य में प्रत्येक वर्ष 16 अक्टूबर को विश्व खाद्य दिवस मनाया जाता है।"),
            ("FAO leads international efforts to defeat hunger, improve nutrition and enhance food security.",
             "FAO भूख को समाप्त करने, पोषण में सुधार लाने और खाद्य सुरक्षा बढ़ाने के अंतरराष्ट्रीय प्रयासों का नेतृत्व करता है।"),
        ]
    },
    "MEA": {
        "name_en": "Ministry of External Affairs (MEA)",
        "name_hi": "विदेश मंत्रालय (MEA)",
        "facts": [
            ("The Ministry of External Affairs (MEA) is responsible for the conduct of India's foreign relations.",
             "विदेश मंत्रालय (MEA) भारत के विदेशी संबंधों के संचालन के लिए उत्तरदायी है।"),
            ("MEA is headquartered at South Block, New Delhi.",
             "MEA का मुख्यालय साउथ ब्लॉक, नई दिल्ली में स्थित है।"),
            ("The Ministry represents India in the United Nations and other multilateral international bodies.",
             "यह मंत्रालय संयुक्त राष्ट्र और अन्य बहुपक्षीय अंतरराष्ट्रीय निकायों में भारत का प्रतिनिधित्व करता है।"),
        ]
    },
    "MOA": {
        "name_en": "Ministry of Agriculture & Farmers Welfare (MoA&FW)",
        "name_hi": "कृषि एवं किसान कल्याण मंत्रालय",
        "facts": [
            ("The Ministry of Agriculture and Farmers Welfare is the apex government ministry for agriculture policy in India.",
             "कृषि एवं किसान कल्याण मंत्रालय भारत में कृषि नीति के लिए सर्वोच्च सरकारी मंत्रालय है।"),
            ("The Ministry comprises two departments: Department of Agriculture & Farmers Welfare (DA&FW) and DARE.",
             "मंत्रालय में दो विभाग शामिल हैं: कृषि एवं किसान कल्याण विभाग (DA&FW) और DARE।"),
            ("The Ministry is headquartered at Krishi Bhawan, New Delhi.",
             "मंत्रालय का मुख्यालय कृषि भवन, नई दिल्ली में स्थित है।"),
            ("Key flagship schemes include PM-KISAN, PM Fasal Bima Yojana (PMFBY), and Agriculture Infrastructure Fund (AIF).",
             "प्रमुख प्रमुख योजनाओं में पीएम-किसान, पीएम फसल बीमा योजना (PMFBY) और कृषि अवसंरचना कोष (AIF) शामिल हैं।"),
        ]
    },
    "MEITY": {
        "name_en": "Ministry of Electronics and Information Technology (MeitY)",
        "name_hi": "इलेक्ट्रॉनिक्स और सूचना प्रौद्योगिकी मंत्रालय (MeitY)",
        "facts": [
            ("MeitY is responsible for IT policy, digital governance, cyber security and electronics manufacturing in India.",
             "MeitY भारत में आईटी नीति, डिजिटल शासन, साइबर सुरक्षा और इलेक्ट्रॉनिक्स विनिर्माण के लिए जिम्मेदार है।"),
            ("MeitY is headquartered at Electronics Niketan, CGO Complex, New Delhi.",
             "MeitY का मुख्यालय इलेक्ट्रॉनिक्स निकेतन, सीजीओ कॉम्प्लेक्स, नई दिल्ली में स्थित है।"),
            ("National e-Governance Division (NeGD) and Digital India Corporation function under MeitY.",
             "राष्ट्रीय ई-गवर्नेंस प्रभाग (NeGD) और डिजिटल इंडिया कॉर्पोरेशन MeitY के तहत कार्य करते हैं।"),
            ("DigiLocker is a flagship digital document wallet platform developed under the Digital India Programme.",
             "डिजिलॉकर डिजिटल इंडिया कार्यक्रम के तहत विकसित एक प्रमुख डिजिटल दस्तावेज़ वॉलेट प्लेटफ़ॉर्म है।"),
        ]
    },
    "ISRO": {
        "name_en": "Indian Space Research Organisation (ISRO)",
        "name_hi": "भारतीय अंतरिक्ष अनुसंधान संगठन (ISRO)",
        "facts": [
            ("Indian Space Research Organisation (ISRO) was founded on 15 August 1969.",
             "भारतीय अंतरिक्ष अनुसंधान संगठन (ISRO) की स्थापना 15 अगस्त 1969 को हुई थी।"),
            ("ISRO superseded the erstwhile INCOSPAR (Indian National Committee for Space Research) set up in 1962.",
             "ISRO ने 1962 में स्थापित तत्कालीन INCOSPAR (भारतीय राष्ट्रीय अंतरिक्ष अनुसंधान समिति) का स्थान लिया था।"),
            ("ISRO is headquartered in Bengaluru, Karnataka.",
             "ISRO का मुख्यालय बेंगलुरु, कर्नाटक में स्थित है।"),
            ("ISRO operates under the Department of Space (DoS), which is directly overseen by the Prime Minister.",
             "ISRO अंतरिक्ष विभाग (DoS) के अंतर्गत कार्य करता है, जो सीधे प्रधानमंत्री द्वारा देखा जाता है।"),
            ("NewSpace India Limited (NSIL) is the commercial arm of ISRO, incorporated in March 2019.",
             "न्यूस्पेस इंडिया लिमिटेड (NSIL) ISRO की वाणिज्यिक शाखा है, जिसे मार्च 2019 में निगमित किया गया था।"),
        ]
    },
    "DRDO": {
        "name_en": "Defence Research and Development Organisation (DRDO)",
        "name_hi": "रक्षा अनुसंधान एवं विकास संगठन (DRDO)",
        "facts": [
            ("Defence Research and Development Organisation (DRDO) was established in 1958.",
             "रक्षा अनुसंधान एवं विकास संगठन (DRDO) की स्थापना 1958 में हुई थी।"),
            ("DRDO was formed by amalgamating the Defence Science Organisation (DSO) with the Technical Development Establishments.",
             "DRDO का गठन रक्षा विज्ञान संगठन (DSO) को तकनीकी विकास प्रतिष्ठानों के साथ मिलाकर किया गया था।"),
            ("DRDO is headquartered in DRDO Bhawan, New Delhi.",
             "DRDO का मुख्यालय DRDO भवन, नई दिल्ली में स्थित है।"),
            ("DRDO operates under the Department of Defence R&D, Ministry of Defence.",
             "DRDO रक्षा मंत्रालय के रक्षा अनुसंधान एवं विकास विभाग के तहत कार्य करता है।"),
        ]
    },
    "SAI": {
        "name_en": "Sports Authority of India (SAI)",
        "name_hi": "भारतीय खेल प्राधिकरण (SAI)",
        "facts": [
            ("Sports Authority of India (SAI) was established in 1984 under the Ministry of Youth Affairs and Sports.",
             "भारतीय खेल प्राधिकरण (SAI) की स्थापना 1984 में युवा मामले और खेल मंत्रालय के तहत हुई थी।"),
            ("SAI is headquartered at Jawaharlal Nehru Stadium Complex, New Delhi.",
             "SAI का मुख्यालय जवाहरलाल नेहरू स्टेडियम परिसर, नई दिल्ली में स्थित है।"),
            ("SAI was created to maintain and utilize the sports infrastructure built for the 1982 Asian Games in New Delhi.",
             "SAI का गठन नई दिल्ली में 1982 के एशियाई खेलों के लिए निर्मित खेल अवसंरचना के रखरखाव और उपयोग के लिए किया गया था।"),
        ]
    },
    "SIOFA": {
        "name_en": "Southern Indian Ocean Fisheries Agreement (SIOFA)",
        "name_hi": "दक्षिणी हिंद महासागर मत्स्य समझौता (SIOFA)",
        "facts": [
            ("The Southern Indian Ocean Fisheries Agreement (SIOFA) was signed in Rome in July 2006 and entered into force in June 2012.",
             "दक्षिणी हिंद महासागर मत्स्य समझौता (SIOFA) जुलाई 2006 में रोम में हस्ताक्षरित हुआ और जून 2012 में लागू हुआ।"),
            ("SIOFA headquarters and secretariat is located on Réunion Island, France.",
             "SIOFA का मुख्यालय और सचिवालय रीयूनियन द्वीप, फ्रांस में स्थित है।"),
            ("SIOFA is a legally binding regional agreement aimed at the conservation and sustainable management of non-tuna fishery resources.",
             "SIOFA गैर-टूना मत्स्य संसाधनों के संरक्षण और सतत प्रबंधन के उद्देश्य से बनाया गया एक कानूनी रूप से बाध्यकारी क्षेत्रीय समझौता है।"),
        ]
    },
    "AIIA": {
        "name_en": "All India Institute of Ayurveda (AIIA)",
        "name_hi": "अखिल भारतीय आयुर्वेद संस्थान (AIIA)",
        "facts": [
            ("The All India Institute of Ayurveda (AIIA) was dedicated to the nation on 17 October 2017 (National Ayurveda Day).",
             "अखिल भारतीय आयुर्वेद संस्थान (AIIA) को 17 अक्टूबर 2017 (राष्ट्रीय आयुर्वेद दिवस) पर राष्ट्र को समर्पित किया गया था।"),
            ("AIIA is located in Sarita Vihar, New Delhi.",
             "AIIA सरिता विहार, नई दिल्ली में स्थित है।"),
            ("AIIA functions as an apex autonomous institute under the Ministry of Ayush.",
             "AIIA आयुष मंत्रालय के अंतर्गत एक शीर्ष स्वायत्त संस्थान के रूप में कार्य करता है।"),
            ("AIIA was established on the lines of AIIMS to bring synergy between traditional Ayurveda and modern diagnostic technology.",
             "पारंपरिक आयुर्वेद और आधुनिक निदान तकनीक के बीच समन्वय स्थापित करने के लिए AIIMS की तर्ज पर AIIA की स्थापना की गई थी।"),
        ]
    },
    "BIMSTEC": {
        "name_en": "Bay of Bengal Initiative for Multi-Sectoral Technical and Economic Cooperation (BIMSTEC)",
        "name_hi": "बंगाल की खाड़ी बहु-क्षेत्रीय तकनीकी और आर्थिक सहयोग पहल (BIMSTEC)",
        "facts": [
            ("BIMSTEC was founded on 6 June 1997 through the Bangkok Declaration.",
             "BIMSTEC की स्थापना 6 जून 1997 को बैंकॉक घोषणा के माध्यम से हुई थी।"),
            ("BIMSTEC has 7 member states: Bangladesh, Bhutan, India, Myanmar, Nepal, Sri Lanka, and Thailand.",
             "BIMSTEC के 7 सदस्य देश हैं: बांग्लादेश, भूटान, भारत, म्यांमार, नेपाल, श्रीलंका और थाईलैंड।"),
            ("BIMSTEC Secretariat is located in Dhaka, Bangladesh.",
             "BIMSTEC का स्थायी सचिवालय ढाका, बांग्लादेश में स्थित है।"),
        ]
    },
    "SCO": {
        "name_en": "Shanghai Cooperation Organisation (SCO)",
        "name_hi": "शंघाई सहयोग संगठन (SCO)",
        "facts": [
            ("The Shanghai Cooperation Organisation (SCO) was founded on 15 June 2001 in Shanghai, China.",
             "शंघाई सहयोग संगठन (SCO) की स्थापना 15 जून 2001 को शंघाई, चीन में हुई थी।"),
            ("SCO Secretariat is located in Beijing, China.",
             "SCO का सचिवालय बीजिंग, चीन में स्थित है।"),
            ("India and Pakistan became full permanent members of the SCO on 9 June 2017 at the Astana Summit.",
             "भारत और पाकिस्तान 9 जून 2017 को अस्ताना शिखर सम्मेलन में SCO के पूर्ण स्थायी सदस्य बने।"),
        ]
    },
}

# Distractor Semantic Pools for 5-Option Bilingual MCQs
SEMANTIC_OPTION_POOLS: Dict[str, List[Tuple[str, str]]] = {
    "agri_orgs": [
        ("Food Corporation of India (FCI)", "भारतीय खाद्य निगम (FCI)"),
        ("National Agricultural Cooperative Marketing Federation (NAFED)", "राष्ट्रीय कृषि सहकारी विपणन संघ (NAFED)"),
        ("Central Warehousing Corporation (CWC)", "केंद्रीय भंडारण निगम (CWC)"),
        ("National Cooperative Consumers’ Federation (NCCF)", "राष्ट्रीय सहकारी उपभोक्ता संघ (NCCF)"),
        ("Agricultural and Processed Food Products Export Development Authority (APEDA)", "कृषि एवं प्रसंस्कृत खाद्य उत्पाद निर्यात विकास प्राधिकरण (APEDA)"),
        ("Indian Council of Agricultural Research (ICAR)", "भारतीय कृषि अनुसंधान परिषद (ICAR)"),
        ("National Bank for Agriculture and Rural Development (NABARD)", "राष्ट्रीय कृषि और ग्रामीण विकास बैंक (NABARD)"),
        ("Commission for Agricultural Costs and Prices (CACP)", "कृषि लागत और मूल्य आयोग (CACP)"),
    ],
    "ministries": [
        ("Ministry of Agriculture & Farmers Welfare", "कृषि एवं किसान कल्याण मंत्रालय"),
        ("Ministry of Consumer Affairs, Food & Public Distribution", "उपभोक्ता मामले, खाद्य एवं सार्वजनिक वितरण मंत्रालय"),
        ("Ministry of Fisheries, Animal Husbandry & Dairying", "मत्स्यपालन, पशुपालन एवं डेयरी मंत्रालय"),
        ("Ministry of Rural Development", "ग्रामीण विकास मंत्रालय"),
        ("Ministry of Environment, Forest & Climate Change", "पर्यावरण, वन एवं जलवायु परिवर्तन मंत्रालय"),
        ("Ministry of Commerce and Industry", "वाणिज्य एवं उद्योग मंत्रालय"),
        ("Ministry of Finance", "वित्त मंत्रालय"),
        ("Ministry of External Affairs", "विदेश मंत्रालय"),
    ],
    "financial_regulators": [
        ("Reserve Bank of India (RBI)", "भारतीय रिज़र्व बैंक (RBI)"),
        ("Securities and Exchange Board of India (SEBI)", "भारतीय प्रतिभूति और विनिमय बोर्ड (SEBI)"),
        ("Insurance Regulatory and Development Authority of India (IRDAI)", "भारतीय बीमा विनियामक और विकास प्राधिकरण (IRDAI)"),
        ("Pension Fund Regulatory and Development Authority (PFRDA)", "पेंशन निधि विनियामक और विकास प्राधिकरण (PFRDA)"),
        ("Insolvency and Bankruptcy Board of India (IBBI)", "भारतीय दिवाला और शोधन अक्षमता बोर्ड (IBBI)"),
        ("National Bank for Agriculture and Rural Development (NABARD)", "राष्ट्रीय कृषि और ग्रामीण विकास बैंक (NABARD)"),
    ],
    "defence_tech": [
        ("Defence Research and Development Organisation (DRDO)", "रक्षा अनुसंधान एवं विकास संगठन (DRDO)"),
        ("Indian Space Research Organisation (ISRO)", "भारतीय अंतरिक्ष अनुसंधान संगठन (ISRO)"),
        ("Bharat Dynamics Limited (BDL)", "भारत डायनामिक्स लिमिटेड (BDL)"),
        ("Hindustan Aeronautics Limited (HAL)", "हिंदुस्तान एयरोनॉटिक्स लिमिटेड (HAL)"),
        ("Bharat Electronics Limited (BEL)", "भारत इलेक्ट्रॉनिक्स लिमिटेड (BEL)"),
        ("NewSpace India Limited (NSIL)", "न्यूस्पेस इंडिया लिमिटेड (NSIL)"),
    ],
    "schemes_agri": [
        ("PM-KISAN (Pradhan Mantri Kisan Samman Nidhi)", "पीएम-किसान (प्रधानमंत्री किसान सम्मान निधि)"),
        ("PMFBY (Pradhan Mantri Fasal Bima Yojana)", "पीएमएफबीवाई (प्रधानमंत्री फसल बीमा योजना)"),
        ("KERA Project (Kerala Climate Resilient Agri-Value Chain)", "केरा परियोजना (KERA Project)"),
        ("RKVY (Rashtriya Krishi Vikas Yojana)", "आरकेवीवाई (राष्ट्रीय कृषि विकास योजना)"),
        ("Digital Agriculture Mission", "डिजिटल कृषि मिशन"),
        ("PM Dhan-Dhaanya Krishi Yojana (PMDDKY)", "पीएम धन-धान्य कृषि योजना (PMDDKY)"),
        ("Agriculture Infrastructure Fund (AIF)", "कृषि अवसंरचना कोष (AIF)"),
    ],
}


def lookup_static_gk_for_text(text: str) -> List[Tuple[str, str]]:
    """Scan text for known statutory / institutional entities and return paired bilingual facts."""
    t_upper = text.upper()
    results: List[Tuple[str, str]] = []
    seen_keys = set()

    # Direct keyword matching
    matches = [
        ("ICAR-IARI", "IARI"), ("IARI", "IARI"),
        ("ICAR", "ICAR"), ("NABARD", "NABARD"),
        ("FOOD CORPORATION", "FCI"), ("FCI", "FCI"),
        ("APEDA", "APEDA"), ("NAFED", "NAFED"),
        ("RESERVE BANK", "RBI"), ("RBI", "RBI"),
        ("SEBI", "SEBI"), ("IRDAI", "IRDAI"),
        ("WORLD BANK", "WORLD_BANK"),
        ("FAO", "FAO"), ("FOOD AND AGRICULTURE ORGANIZATION", "FAO"),
        ("EXTERNAL AFFAIRS", "MEA"), ("MINISTRY OF EXTERNAL", "MEA"),
        ("MINISTRY OF AGRICULTURE", "MOA"), ("AGRICULTURE MINISTRY", "MOA"),
        ("MEITY", "MEITY"), ("ELECTRONICS AND INFORMATION", "MEITY"), ("DIGILOCKER", "MEITY"),
        ("ISRO", "ISRO"), ("DRDO", "DRDO"), ("SPORTS AUTHORITY", "SAI"), ("SAI", "SAI"),
        ("SIOFA", "SIOFA"), ("AIIA", "AIIA"), ("AYURVEDA", "AIIA"),
        ("BIMSTEC", "BIMSTEC"), ("SCO", "SCO"),
    ]

    for needle, key in matches:
        if needle in t_upper and key not in seen_keys:
            seen_keys.add(key)
            data = ENTITY_STATIC_DB.get(key)
            if data and "facts" in data:
                results.extend(data["facts"][:4])
            if len(results) >= 6:
                break

    return results
