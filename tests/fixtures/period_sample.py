"""Synthetic daily editions for the weekly/monthly period builder (NOT real news).

``build_daily_editions(dates, stories_per_day)`` returns what
scripts/fetch_daily_editions.py would leave in data/period_sources: one dict per
day with the daily ``content`` and ``mcqs``.  Every day also carries the cases
the builder must drop: an unverified item, an item whose "Hindi" is English,
and a verified item with an ``Untitled`` headline.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List

_SUBJECTS = [
    ("Union Cabinet", "केंद्रीय मंत्रिमंडल"), ("Reserve Bank of India", "भारतीय रिज़र्व बैंक"),
    ("ISRO", "इसरो"), ("DRDO", "डीआरडीओ"), ("NABARD", "नाबार्ड"), ("ICAR", "भारतीय कृषि अनुसंधान परिषद"),
    ("Agriculture Ministry", "कृषि मंत्रालय"), ("SEBI", "सेबी"), ("Indian Navy", "भारतीय नौसेना"),
    ("Election Commission", "निर्वाचन आयोग"), ("NITI Aayog", "नीति आयोग"), ("World Bank", "विश्व बैंक"),
    ("Sports Authority of India", "भारतीय खेल प्राधिकरण"), ("Supreme Court", "सर्वोच्च न्यायालय"),
    ("Food and Agriculture Organization", "खाद्य एवं कृषि संगठन"), ("Ministry of Jal Shakti", "जल शक्ति मंत्रालय"),
    ("Indian Railways", "भारतीय रेल"), ("APEDA", "एपीडा"), ("Coal Ministry", "कोयला मंत्रालय"),
    ("Health Ministry", "स्वास्थ्य मंत्रालय"),
]
_OBJECTS = [
    ("a ₹2,400 crore millet processing scheme", "₹2,400 करोड़ की मिलेट प्रसंस्करण योजना"),
    ("a satellite for coastal monitoring", "तटीय निगरानी हेतु उपग्रह"),
    ("a digital crop survey portal", "डिजिटल फसल सर्वेक्षण पोर्टल"),
    ("new norms for green bonds", "हरित बॉन्ड के नए मानदंड"),
    ("an indigenous long-range torpedo", "स्वदेशी लंबी दूरी का टारपीडो"),
    ("a drip irrigation mission for 5 lakh hectares", "5 लाख हेक्टेयर के लिए ड्रिप सिंचाई मिशन"),
    ("a national dairy cooperative grid", "राष्ट्रीय डेयरी सहकारी ग्रिड"),
    ("a heatwave action plan for wheat", "गेहूँ हेतु लू कार्य योजना"),
    ("a fisheries export hub", "मत्स्य निर्यात केंद्र"),
    ("a soil health card drive", "मृदा स्वास्थ्य कार्ड अभियान"),
    ("a semiconductor design centre", "सेमीकंडक्टर डिज़ाइन केंद्र"),
    ("a natural farming cluster programme", "प्राकृतिक खेती क्लस्टर कार्यक्रम"),
    ("a coastal shipping corridor", "तटीय नौवहन गलियारा"),
    ("a seed traceability system", "बीज अनुरेखण प्रणाली"),
    ("a rural warehousing fund", "ग्रामीण भंडारण कोष"),
    ("an inland waterways terminal", "अंतर्देशीय जलमार्ग टर्मिनल"),
    ("a youth athletics talent hunt", "युवा एथलेटिक्स प्रतिभा खोज"),
    ("a bamboo value chain mission", "बाँस मूल्य श्रृंखला मिशन"),
    ("a cold chain network for onions", "प्याज के लिए शीत श्रृंखला नेटवर्क"),
    ("a flood forecasting radar network", "बाढ़ पूर्वानुमान रडार नेटवर्क"),
    ("an organic cotton certification", "जैविक कपास प्रमाणन"),
    ("a honey testing laboratory", "शहद परीक्षण प्रयोगशाला"),
    ("a solar pump subsidy round", "सौर पंप सब्सिडी चरण"),
    ("a livestock vaccination campaign", "पशुधन टीकाकरण अभियान"),
    ("a credit guarantee for farmer producer organisations", "किसान उत्पादक संगठनों हेतु ऋण गारंटी"),
    ("a lithium exploration block", "लिथियम अन्वेषण ब्लॉक"),
    ("a mangrove restoration project", "मैंग्रोव पुनर्स्थापन परियोजना"),
    ("a hockey high-performance centre", "हॉकी उच्च प्रदर्शन केंद्र"),
    ("a spice park expansion", "मसाला पार्क विस्तार"),
    ("a weather-indexed crop insurance pilot", "मौसम आधारित फसल बीमा पायलट"),
    ("a tribal forest produce mission", "जनजातीय वन उपज मिशन"),
]
_PLACES = [
    ("in Odisha", "ओडिशा में"), ("in Gujarat", "गुजरात में"), ("in Assam", "असम में"),
    ("in Punjab", "पंजाब में"), ("in Kerala", "केरल में"), ("in Bihar", "बिहार में"),
    ("in Rajasthan", "राजस्थान में"), ("in Karnataka", "कर्नाटक में"), ("in Uttar Pradesh", "उत्तर प्रदेश में"),
    ("in Telangana", "तेलंगाना में"), ("in Maharashtra", "महाराष्ट्र में"),
]
_CATS = ["National", "International", "Economy", "Science & Technology", "Agriculture",
         "Appointments", "Sports", "Defence", "Banking & Finance", "Environment", "Awards", "Agriculture"]


def _hi_headline(i: int) -> tuple[str, str, str, str, str, str]:
    s_en, s_hi = _SUBJECTS[i % len(_SUBJECTS)]
    o_en, o_hi = _OBJECTS[(i * 7) % len(_OBJECTS)]
    p_en, p_hi = _PLACES[(i * 3) % len(_PLACES)]
    return s_en, s_hi, o_en, o_hi, p_en, p_hi


def _story(day: str, i: int, cat: str) -> Dict[str, Any]:
    s_en, s_hi, o_en, o_hi, p_en, p_hi = _hi_headline(i)
    head_en = f"{s_en} launches {o_en} {p_en}"
    head_hi = f"{s_hi} ने {p_hi} {o_hi} की शुरुआत की"
    if cat == "Sports":
        head_en = f"India wins gold as {s_en} backs {o_en} {p_en}"
        head_hi = f"भारत ने स्वर्ण जीता, {s_hi} ने {p_hi} {o_hi} को समर्थन दिया"
    elif cat == "Appointments":
        head_en = f"New chairman appointed at {s_en} to steer {o_en}"
        head_hi = f"{o_hi} के संचालन हेतु {s_hi} में नए अध्यक्ष नियुक्त"
    return {
        "event_id": f"ev-{day}-{i}",
        "category": cat,
        "importance_score": 40 + (i * 37) % 60,
        "headline_en": ">> " + head_en,
        "headline_hi": ">> " + head_hi,
        "summary_en": f"{s_en} announced {o_en} {p_en} on {day}.",
        "summary_hi": f"{s_hi} ने {day} को {p_hi} {o_hi} की घोषणा की।",
        "key_points_en": [f"{s_en} announced {o_en} {p_en}.",
                          f"The {o_en.split(' ', 1)[1]} will start {p_en} with ₹{100 + i} crore of central support.",
                          f"The programme will run for 3 years with ₹{100 + i} crore support.",
                          f"Farmers and youth in the state are the main beneficiaries."],
        "key_points_hi": [f"{s_hi} ने {p_hi} {o_hi} की घोषणा की।",
                          f"{p_hi} {o_hi} ₹{100 + i} करोड़ की केंद्रीय सहायता से शुरू होगी।",
                          f"यह कार्यक्रम 3 वर्ष तक ₹{100 + i} करोड़ की सहायता से चलेगा।",
                          "राज्य के किसान एवं युवा इसके मुख्य लाभार्थी हैं।"],
        "static_gk_pairs": [{"en": f"Headquarters – New Delhi", "hi": "मुख्यालय – नई दिल्ली"},
                            {"en": f"Nodal body – {s_en}", "hi": f"नोडल निकाय – {s_hi}"}],
        "static_facts": {},
        "source": {"name": "PIB", "url": "https://pib.gov.in/"},
        "image_path": "",
        "needs_review": False,
        "verification_passed": True,
    }


def _mcqs(story: Dict[str, Any], i: int) -> List[Dict[str, Any]]:
    s_en, s_hi, o_en, o_hi, p_en, p_hi = _hi_headline(i)
    base = 100 + i
    return [
        {"event_id": story["event_id"],
         "question_en": f"Which body launched {o_en} {p_en}?",
         "question_hi": f"{p_hi} {o_hi} किस संस्था ने शुरू की?",
         "options": [_SUBJECTS[(i + k) % len(_SUBJECTS)][0] for k in range(5)],
         "options_hi": [_SUBJECTS[(i + k) % len(_SUBJECTS)][1] for k in range(5)],
         "correct": "A",
         "static_gk": [{"label_en": "Nodal body", "value_en": s_en, "label_hi": "नोडल निकाय", "value_hi": s_hi}]},
        {"event_id": story["event_id"],
         "question_en": f"What financial support was announced for {o_en} by {s_en}?",
         "question_hi": f"{s_hi} द्वारा {o_hi} के लिए कितनी वित्तीय सहायता घोषित की गई?",
         "options": [f"₹{base + d} crore" for d in (-20, -10, 0, 10, 20)],
         "options_hi": [f"₹{base + d} करोड़" for d in (-20, -10, 0, 10, 20)],
         "correct": "C"},
    ]


def build_daily_editions(dates: List[str], stories_per_day: int = 3) -> List[Dict[str, Any]]:
    eds = []
    n = 0
    for di, day in enumerate(dates):
        items, mcqs = [], []
        for j in range(stories_per_day):
            cat = _CATS[(di * stories_per_day + j) % len(_CATS)]
            st = _story(day, n, cat)
            items.append(st)
            mcqs += _mcqs(st, n)
            n += 1
        # --- cases the builder must drop ---
        bad = _story(day, 900 + di, "National")
        bad["needs_review"] = True
        bad["headline_en"] = f"Unverified claim about a scheme number {di} that must not be printed"
        items.append(bad)
        eng = _story(day, 950 + di, "Economy")
        eng["headline_en"] = f"Fallback translation story {di} with English Hindi field"
        eng["headline_hi"] = eng["headline_en"]  # no Devanagari
        items.append(eng)
        untitled = _story(day, 980 + di, "National")
        untitled["headline_en"] = "Untitled"
        items.append(untitled)
        content = {
            "job": {"id": f"daily_{day}", "type": "daily", "date": day},
            "items": items,
            "one_liners": [{"category": it["category"], "text_en": it["headline_en"].lstrip("> "),
                            "text_hi": it["headline_hi"].lstrip("> "), "event_id": it["event_id"]}
                           for it in items[:stories_per_day]],
            "agri_corner": {"items": [{"en": f"Kisan mela {di} showcased {_OBJECTS[di % len(_OBJECTS)][0]} for farmers",
                                       "hi": f"किसान मेला {di} में किसानों के लिए {_OBJECTS[di % len(_OBJECTS)][1]} प्रदर्शित",
                                       "event_id": f"agri-{day}"}],
                            "static_gk": [{"en": f"ICAR – established 16 July 1929 ({di % 3})",
                                           "hi": f"आईसीएआर – स्थापना 16 जुलाई 1929 ({di % 3})"}]},
        }
        eds.append({"date": day, "content": content, "mcqs": mcqs})
    return eds


def dates_from(start: str, days: int) -> List[str]:
    d = date.fromisoformat(start)
    return [(d + timedelta(days=k)).isoformat() for k in range(days)]
