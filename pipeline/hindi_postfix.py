# -*- coding: utf-8 -*-
"""
HINDI POST-PROCESSING — glossary, mixed script, English leftovers, name consistency.

Machine translation of official names drifts (ZSI became "भारतीय वन्यजीव सर्वेक्षण",
APEDA "एपीडिया", an Act "विधेयक", Parent Ministry "अधीनस्थ मंत्रालय"), leaves
half-translated words ("प्रोtest"), keeps English phrases inside Hindi lines and
spells one person three ways in one edition.  This module repairs a Hindi line
given its English line, and walks a whole edition (content + MCQ artifacts).

Order for each (en, hi) pair:
1. Devanagari digits -> Arabic digits (one numeral system in the PDF).
2. Glossary: wrong renderings of official names are corrected; known English
   names left in the Hindi line are replaced with their official Hindi form.
3. Person names: when the English line names a person whose Hindi spelling is
   known (glossary, current_facts, or the first verified rendering in this
   edition), a near-miss spelling in the Hindi line is replaced with it.
4. Mixed-script words (Latin letters inside a Devanagari word): the English word
   is found in the English line and re-rendered from the glossary, else through
   the optional ``translator`` (one word, Devanagari-only answer accepted).
5. English leftovers: Latin words other than acronyms, units, numbers and
   parenthesised glosses.  Proper nouns are kept and counted; an untranslated
   phrase means the line was not really translated: it is re-translated through
   ``translator`` when given, and blanked otherwise.  (Untranslated = four or more
   English words in a row that include a function word, or English making up
   40% of a line with four or more such words.)

FAIL-CLOSED: whenever a line cannot be repaired its Hindi is blanked, so the
renderer's Devanagari check prints the line English-only.  Never raises.
"""
from __future__ import annotations

import difflib
import json
import logging
import re
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from pipeline.text_normalize import (garbled_hi, hi_truncated_start, normalise_money, strip_source_tags,
                                     tidy)

logger = logging.getLogger("pipeline.hindi_postfix")

ROOT = Path(__file__).resolve().parent.parent
DEVA_RE = re.compile(r"[\u0900-\u097F]")
LATIN_RE = re.compile(r"[A-Za-z]")
_DEVA_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_DL = "\u0900-\u0963\u0966-\u097F"   # Devanagari letters/marks/digits (no danda)
MIXED_RE = re.compile(rf"[{_DL}]+[A-Za-z]+[{_DL}A-Za-z]*|[A-Za-z]+[{_DL}]+[{_DL}A-Za-z]*")
_PAREN_RE = re.compile(r"\([^()]*\)|\"[^\"]*\"|“[^”]*”|‘[^’]*’|'[^']*'")  # glosses / quoted titles
_SUFFIX_HI = (("ings", "िंग्स"), ("ing", "िंग"), ("tion", "शन"), ("ers", "र्स"), ("er", "र"), ("ed", "ेड"), ("s", "्स"))
# Latin words that are standard in Hindi copy (official names written in Latin).
_ALLOWED_LATIN = {"aayog", "bharat", "yojana", "abhiyan", "mission", "app", "portal"}
_LATIN_WORD_RE = re.compile(r"(?<![A-Za-z0-9@/.])[A-Za-z][A-Za-z'’\-]*(?![A-Za-z0-9@/])")
_URL_RE = re.compile(r"https?://\S+|www\.\S+|\S+@\S+")
_UNITS = {"km", "kg", "mw", "gw", "gwh", "kwh", "mt", "lmt", "rs", "sq", "ha", "cm", "mm", "kms", "mtpa",
          "ltd", "pvt", "vs", "etc", "no", "dr", "shri", "smt", "mr", "ms", "st", "nd", "rd", "th"}

# --------------------------------------------------------------------------- #
# Glossary
# --------------------------------------------------------------------------- #
# English official names -> Hindi (used for leftovers and as translation hints).
EN_TO_HI: Dict[str, str] = {
    # bodies
    "Zoological Survey of India": "भारतीय प्राणी सर्वेक्षण",
    "Botanical Survey of India": "भारतीय वनस्पति सर्वेक्षण",
    "Commission for Agricultural Costs and Prices": "कृषि लागत एवं मूल्य आयोग",
    "Commission for Agricultural Costs & Prices": "कृषि लागत एवं मूल्य आयोग",
    "Agricultural and Processed Food Products Export Development Authority":
        "कृषि एवं प्रसंस्कृत खाद्य उत्पाद निर्यात विकास प्राधिकरण",
    "Indian Council of Agricultural Research": "भारतीय कृषि अनुसंधान परिषद",
    "Reserve Bank of India": "भारतीय रिज़र्व बैंक",
    "Securities and Exchange Board of India": "भारतीय प्रतिभूति और विनिमय बोर्ड",
    "Food Safety and Standards Authority of India": "भारतीय खाद्य सुरक्षा एवं मानक प्राधिकरण",
    "National Bank for Agriculture and Rural Development": "राष्ट्रीय कृषि और ग्रामीण विकास बैंक",
    "National Dairy Development Board": "राष्ट्रीय डेयरी विकास बोर्ड",
    "Food Corporation of India": "भारतीय खाद्य निगम",
    "Competition Commission of India": "भारतीय प्रतिस्पर्धा आयोग",
    "Election Commission of India": "भारत निर्वाचन आयोग",
    "Supreme Court of India": "भारत का सर्वोच्च न्यायालय",
    "Supreme Court": "सर्वोच्च न्यायालय",
    "Mishra Dhatu Nigam Limited": "मिश्र धातु निगम लिमिटेड",
    "Mishra Dhatu Nigam": "मिश्र धातु निगम",
    "Bhabha Atomic Research Centre": "भाभा परमाणु अनुसंधान केंद्र",
    "India Meteorological Department": "भारत मौसम विज्ञान विभाग",
    "Commissions of Inquiry Act": "जांच आयोग अधिनियम",
    "Parent Ministry": "मूल मंत्रालय",
    "Nodal Ministry": "नोडल मंत्रालय",
    # ministries
    "Ministry of Agriculture and Farmers Welfare": "कृषि एवं किसान कल्याण मंत्रालय",
    "Ministry of Agriculture & Farmers Welfare": "कृषि एवं किसान कल्याण मंत्रालय",
    "Ministry of Finance": "वित्त मंत्रालय",
    "Ministry of Defence": "रक्षा मंत्रालय",
    "Ministry of Home Affairs": "गृह मंत्रालय",
    "Ministry of External Affairs": "विदेश मंत्रालय",
    "Ministry of Commerce and Industry": "वाणिज्य एवं उद्योग मंत्रालय",
    "Ministry of Commerce & Industry": "वाणिज्य एवं उद्योग मंत्रालय",
    "Ministry of Environment, Forest and Climate Change": "पर्यावरण, वन एवं जलवायु परिवर्तन मंत्रालय",
    "Ministry of Health and Family Welfare": "स्वास्थ्य एवं परिवार कल्याण मंत्रालय",
    "Ministry of Fisheries, Animal Husbandry and Dairying": "मत्स्यपालन, पशुपालन एवं डेयरी मंत्रालय",
    "Ministry of Fisheries, Animal Husbandry & Dairying": "मत्स्यपालन, पशुपालन एवं डेयरी मंत्रालय",
    "Ministry of Panchayati Raj": "पंचायती राज मंत्रालय",
    "Ministry of Rural Development": "ग्रामीण विकास मंत्रालय",
    "Ministry of New and Renewable Energy": "नवीन एवं नवीकरणीय ऊर्जा मंत्रालय",
    "Ministry of Food Processing Industries": "खाद्य प्रसंस्करण उद्योग मंत्रालय",
    "Ministry of Consumer Affairs, Food and Public Distribution": "उपभोक्ता मामले, खाद्य एवं सार्वजनिक वितरण मंत्रालय",
    "Ministry of Statistics and Programme Implementation": "सांख्यिकी एवं कार्यक्रम कार्यान्वयन मंत्रालय",
    "Ministry of Education": "शिक्षा मंत्रालय",
    "Ministry of Corporate Affairs": "कॉरपोरेट कार्य मंत्रालय",
    "Ministry of Jal Shakti": "जल शक्ति मंत्रालय",
    "Ministry of Cooperation": "सहकारिता मंत्रालय",
    "Ministry of Steel": "इस्पात मंत्रालय",
    "Ministry of Power": "विद्युत मंत्रालय",
    "Ministry of Micro, Small and Medium Enterprises": "सूक्ष्म, लघु एवं मध्यम उद्यम मंत्रालय",
    "Ministry of Earth Sciences": "पृथ्वी विज्ञान मंत्रालय",
    "Ministry of Science and Technology": "विज्ञान एवं प्रौद्योगिकी मंत्रालय",
    "Ministry of Law and Justice": "विधि एवं न्याय मंत्रालय",
    "Ministry of Road Transport and Highways": "सड़क परिवहन एवं राजमार्ग मंत्रालय",
    "Ministry of Railways": "रेल मंत्रालय",
    "Food Processing Ministry": "खाद्य प्रसंस्करण उद्योग मंत्रालय",
    # places
    "New Delhi": "नई दिल्ली", "Bengaluru": "बेंगलुरु", "Bangalore": "बेंगलुरु", "Mumbai": "मुंबई",
    "Kolkata": "कोलकाता", "Chennai": "चेन्नई", "Hyderabad": "हैदराबाद", "Varanasi": "वाराणसी",
    "Lucknow": "लखनऊ", "Gangtok": "गंगटोक", "Namakkal": "नामक्कल",
    # names / titles / schemes seen left in English inside Hindi lines (weekly audit Nov 2026)
    "US President": "अमेरिकी राष्ट्रपति", "U.S. President": "अमेरिकी राष्ट्रपति", "President": "राष्ट्रपति",
    "Vice President": "उपराष्ट्रपति", "Prime Minister": "प्रधानमंत्री", "Donald Trump": "डोनाल्ड ट्रंप",
    "Kisan Credit Card": "किसान क्रेडिट कार्ड", "PM Surya Ghar Excellence Award": "पीएम सूर्य घर उत्कृष्टता पुरस्कार",
    "PM Surya Ghar": "पीएम सूर्य घर", "Excellence Award": "उत्कृष्टता पुरस्कार",
    "Animal Taxonomy Summit": "पशु वर्गिकी शिखर सम्मेलन", "Reserve Bank": "रिज़र्व बैंक",
    "Barclays Bank": "बार्कलेज़ बैंक", "Barclays": "बार्कलेज़", "Fairfax India": "फेयरफैक्स इंडिया",
    "Ministry of Fisheries": "मत्स्यपालन मंत्रालय",
    # common words seen half-translated
    "protest": "विरोध", "protests": "विरोध", "economy": "अर्थव्यवस्था", "inflation": "मुद्रास्फीति",
    "survey": "सर्वेक्षण", "export": "निर्यात", "exports": "निर्यात",
}

# Lowercase English words left alone between Hindi words ("ऐसे सभी infiltrators को").
LEFTOVER_WORD_HI: Dict[str, str] = {
    "infiltrators": "घुसपैठियों", "infiltrator": "घुसपैठिया", "infiltration": "घुसपैठ",
    "crore": "करोड़", "crores": "करोड़", "lakh": "लाख", "lakhs": "लाख", "fodder": "चारा",
    "protest": "विरोध", "protests": "विरोध", "economy": "अर्थव्यवस्था", "inflation": "मुद्रास्फीति",
    "survey": "सर्वेक्षण", "export": "निर्यात", "exports": "निर्यात", "summit": "शिखर सम्मेलन",
    "mandate": "जनादेश", "farmers": "किसान", "scheme": "योजना", "award": "पुरस्कार",
}
# Proper-noun brand names that Hindi copy commonly keeps in Latin script.
ALLOWED_BRANDS = {"google", "whatsapp", "youtube", "iphone", "android", "chatgpt", "openai", "microsoft",
                  "instagram", "facebook", "nvidia", "starlink", "paytm", "phonepe", "bhim", "aadhaar",
                  "digilocker", "umang", "swayam", "diksha", "meta", "apple", "amazon", "tesla"}

# Wrong Hindi renderings -> correct ones.  (pattern, replacement, english condition or None)
_HI_FIX_RULES: List[Tuple[str, str, Optional[str]]] = [
    (r"भारतीय\s+(?:वन्यजीव|वन्य\s*जीव|जंतु|जन्तु|प्राणीशास्त्र|प्राणिशास्त्र|प्राणि|जूलॉजिकल)\s+सर्वे(?:क्षण)?",
     "भारतीय प्राणी सर्वेक्षण", r"Zoological\s+Survey|\bZSI\b"),
    (r"जूलॉजिकल\s+सर्वे\s+ऑफ\s+इंडिया", "भारतीय प्राणी सर्वेक्षण", None),
    (r"एपीडिया|एपेडा|अपेडा|एपिडा", "एपीडा", None),
    (r"कृषि\s+लागत\s+(?:और|एवं|तथा|व)\s+(?:मूल्य|कीमत|कीमतों|मूल्यों)\s+(?:के\s+लिए\s+)?आयोग", "कृषि लागत एवं मूल्य आयोग", None),
    (r"(?:अधीनस्थ|अभिभावक|माता|मातृ|पैरेंट|पेरेंट|जनक)\s+मंत्रालय", "मूल मंत्रालय", r"\bParent\b"),
    (r"(?:अधीनस्थ|अभिभावक|माता|मातृ|पैरेंट|पेरेंट|जनक|मूल)\s+मंत्रालय", "नोडल मंत्रालय", r"\bNodal\b"),
    (r"आंकड़े\s+(?:एवं|और)\s+कार्यक्रम\s+कार्यान्वयन", "सांख्यिकी एवं कार्यक्रम कार्यान्वयन", None),
    (r"(?:अधीनस्थ|अभिभावक|माता|मातृ|पैरेंट|पेरेंट|जनक)\s+(निकाय|संगठन|संस्था|संस्थान|कंपनी|विभाग)", r"मूल \1",
     r"\bparent\b"),
    # English month names transliterated instead of translated
    (r"ऑक्टोबर|अक्टोबर|ओक्टोबर", "अक्टूबर", None), (r"नोवेंबर|नवेम्बर|नोवेम्बर", "नवंबर", None),
    (r"डिसेंबर|डिसेम्बर", "दिसंबर", None), (r"सेप्टेंबर|सेप्टेम्बर|सितम्बर", "सितंबर", None),
    (r"ऑगस्ट|ऑगस्त", "अगस्त", None), (r"फेब्रुअरी|फ़ेब्रुअरी|फरवारी", "फरवरी", None), (r"जनुअरी|जैनुअरी", "जनवरी", None),
    # English word order copied into Hindi ("Ministry of Defence" -> "मंत्रालय रक्षा")
    (r"(^|[(–:,;।]\s*)मंत्रालय\s+(रक्षा|गृह|वित्त|विदेश|कृषि|शिक्षा|रेल|विद्युत|इस्पात|सहकारिता|पर्यटन|संस्कृति|खान|कोयला|"
     r"श्रम|विधि|स्वास्थ्य|वाणिज्य|पर्यावरण|संचार|सूचना)(?=\s*(?:[–\-,।:)]|$))", r"\1\2 मंत्रालय", None),
    (r"(^|[(–:,;।]\s*)विभाग\s+((?:[\u0900-\u097F]+\s+){1,3}?(?:का|के))(?=\s*(?:[–\-,।:)]|$))", r"\1\2 विभाग", None),
    (r"(\d{4})\s+के\s+((?:[\u0900-\u097F]+\s+){0,3}?अधिनियम)(?![\u0900-\u097F])", r"\2, \1", None),
    (r"(?<!जांच )(?<!जाँच )आयोग\s+अधिनियम", "जांच आयोग अधिनियम", r"Commissions?\s+of\s+Inquiry"),
    (r"मछली\s+पालन,\s+पशुपालन\s+(?:एवं|और)\s+डेयरी\s+मंत्रालय", "मत्स्यपालन, पशुपालन और डेयरी मंत्रालय", None),
    (r"संयुक्त\s+राज्य\s+अमेरिका\s+डॉलर", "अमेरिकी डॉलर", None),
    (r"इंडिया-यूएस", "भारत-अमेरिका", None),
]
_HI_FIX_RX = [(re.compile(p), r, re.compile(c, re.I) if c else None) for p, r, c in _HI_FIX_RULES]
_BILL_HI_RE = re.compile(r"विधेयक")
_ACT_EN_RE = re.compile(r"\bAct\b")
_BILL_EN_RE = re.compile(r"\bBill\b", re.I)

# People whose Hindi spelling must be fixed (on top of config/current_facts.json).
PERSON_HI: Dict[str, str] = {
    "Punya Salila Srivastava": "पुण्य सलिला श्रीवास्तव",
    "Mansukh Mandaviya": "मनसुख मांडविया",
    "Chirag Paswan": "चिराग पासवान",
    "Shivraj Singh Chouhan": "शिवराज सिंह चौहान",
    "Rajiv Ranjan Singh": "राजीव रंजन सिंह",
    "Pralhad Joshi": "प्रल्हाद जोशी",
    "Jagat Prakash Nadda": "जगत प्रकाश नड्डा",
    "J. P. Nadda": "जे.पी. नड्डा",
}


def _en_rx(phrase: str) -> re.Pattern:
    body = re.escape(phrase).replace(r"\ ", r"\s+")
    return re.compile(rf"(?<![A-Za-z]){body}(?![A-Za-z])", re.I if phrase.islower() else 0)


# Leftover replacement uses names only (multi-word or capitalised); lowercase single words
# ("export") are for mixed-script repair, never swapped into an English phrase.
_EN_TO_HI_RX = [(_en_rx(k), v) for k, v in sorted(EN_TO_HI.items(), key=lambda kv: -len(kv[0]))
                if " " in k or k[:1].isupper()]
_WORD_HI = {k.lower(): v for k, v in EN_TO_HI.items() if " " not in k}


def glossary_hint(en: str, limit: int = 8) -> str:
    """'English = हिंदी' lines for official names in *en* (translation prompt hint)."""
    out = []
    for rx, hi in _EN_TO_HI_RX:
        m = rx.search(en or "")
        if m and " " in m.group(0):
            out.append(f"{m.group(0)} = {hi}")
        if len(out) >= limit:
            break
    return "\n".join(out)


def apply_glossary(en: str, hi: str) -> str:
    """Correct wrong renderings and replace known English names left in *hi*."""
    if not hi:
        return hi
    out = hi.translate(_DEVA_DIGITS)
    for rx, rep, cond in _HI_FIX_RX:
        if cond is not None and en and not cond.search(en):
            continue
        out = rx.sub(rep, out)
    if en and _ACT_EN_RE.search(en) and not _BILL_EN_RE.search(en):
        out = _BILL_HI_RE.sub("अधिनियम", out)
    if DEVA_RE.search(out):
        quoted = [m.span() for m in _PAREN_RE.finditer(out) if not m.group(0).startswith("(")]
        for rx, rep in _EN_TO_HI_RX:
            out = rx.sub(lambda m: m.group(0) if any(a <= m.start() < b for a, b in quoted) else rep, out)
            if quoted:
                quoted = [m.span() for m in _PAREN_RE.finditer(out) if not m.group(0).startswith("(")]
        out = _outside_quotes(out, lambda t: _replace_lone_words(normalise_money(t, True)))
        out = tidy(strip_source_tags(out))
    return out


def _outside_quotes(text: str, fn: Callable[[str], str]) -> str:
    """Apply *fn* to the parts of *text* outside quoted titles (kept verbatim)."""
    spans = [m.span() for m in _PAREN_RE.finditer(text) if not m.group(0).startswith("(")]
    if not spans:
        return fn(text)
    out, pos = [], 0
    for a, b in spans:
        out.append(fn(text[pos:a]) + text[a:b])
        pos = b
    out.append(fn(text[pos:]))
    return "".join(out)


_LONE_WORD_RE = re.compile(r"(?<![A-Za-z0-9])([A-Za-z]+)(?![A-Za-z0-9])")


def _replace_lone_words(hi: str) -> str:
    """Swap a lowercase English word that sits between Hindi words for its Hindi form."""
    def rep(m: re.Match) -> str:
        w = m.group(1)
        h = LEFTOVER_WORD_HI.get(w.lower()) if w[:1].islower() else None
        if not h:
            return w
        before = hi[max(0, m.start() - 12):m.start()]
        after = hi[m.end():m.end() + 12]
        prev_latin = re.search(r"[A-Za-z][\s,]*$", before)
        next_latin = re.match(r"[\s,]*[A-Za-z]", after)
        return w if (prev_latin or next_latin) else h
    return _LONE_WORD_RE.sub(rep, hi)


def repair_truncated_start(en: str, hi: str) -> str:
    """'क्कल के किसानों ने' + 'Namakkal farmers …' -> 'नामक्कल के किसानों ने'. '' when unrepairable."""
    if not hi_truncated_start(hi):
        return hi
    first = re.match(r"\s*([\u0900-\u097F]+)", hi)
    if not first or not en:
        return ""
    frag = first.group(1)
    for rx, full in _EN_TO_HI_RX:
        m = rx.search(en)
        if m and m.start() < 40:
            for word in full.split():
                if word.endswith(frag) and word != frag:
                    return hi[:first.start(1)] + word + hi[first.end(1):]
    return ""


# --------------------------------------------------------------------------- #
# Person names
# --------------------------------------------------------------------------- #
_SKEL_DROP = re.compile(r"[\u093A-\u094F\u0900-\u0903\u0955-\u0957\u0962\u0963\u093C\u200c\u200d.]")


def _skeleton(s: str) -> str:
    return re.sub(r"\s+", " ", _SKEL_DROP.sub("", s)).strip()


def _norm_en(s: str) -> str:
    s = re.sub(r"^(?:Shri|Smt|Sri|Dr|Mr|Ms|Mrs|Prof|Justice)\.?\s+", "", str(s or "").strip(), flags=re.I)
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def load_name_map(facts_path: Optional[Path] = None) -> Dict[str, str]:
    """English name -> verified Hindi spelling (PERSON_HI + current_facts names/aliases)."""
    out = dict(PERSON_HI)
    try:
        p = Path(facts_path or ROOT / "config" / "current_facts.json")
        data = json.loads(p.read_text(encoding="utf-8"))
        for f in data.get("facts") or []:
            hi = str(f.get("name_hi") or "")
            if not hi or f.get("names"):
                continue
            for n in [f.get("name"), *(f.get("aliases") or [])]:
                if n and len(_norm_en(n)) >= 5:
                    out.setdefault(str(n), hi)
    except Exception as exc:  # glossary alone is fine
        logger.debug("[hindi] current_facts names unavailable: %s", exc)
    return out


def fix_names(en: str, hi: str, name_map: Dict[str, str]) -> str:
    """Replace near-miss Hindi spellings of people the English line names."""
    if not hi or not en:
        return hi
    t = f" {_norm_en(en)} "
    for en_name, canon in name_map.items():
        n = _norm_en(en_name)
        if not n or f" {n} " not in t or canon in hi:
            continue
        k = len(canon.split())
        toks = hi.split(" ")
        best, best_i, cs = 0.0, -1, _skeleton(canon)
        for i in range(0, max(0, len(toks) - k) + 1):
            win = " ".join(toks[i:i + k])
            core = re.sub(r"[^\u0900-\u097F ]", "", win)
            if not core or not cs or core[:1] != canon[:1]:
                continue
            r = difflib.SequenceMatcher(None, _skeleton(core), cs).ratio()
            if r > best:
                best, best_i = r, i
        if best >= 0.7 and best_i >= 0:
            win = " ".join(toks[best_i:best_i + k])
            core = re.match(r"^[\u0900-\u097F ]+", win)
            if core:
                toks[best_i:best_i + k] = [canon + win[len(core.group(0).rstrip()):]]
                hi = " ".join(toks)
    return hi


# --------------------------------------------------------------------------- #
# Mixed script and leftovers
# --------------------------------------------------------------------------- #
def mixed_words(hi: str) -> List[str]:
    return MIXED_RE.findall(hi or "")


def leftover_words(hi: str) -> List[str]:
    """Latin words in a Hindi line that are not acronyms, units, numbers or initials."""
    text = _PAREN_RE.sub(" ", _URL_RE.sub(" ", hi or ""))  # '(Alternative Dispute Resolution)' is a gloss
    out = []
    for m in _LATIN_WORD_RE.finditer(text):
        w = m.group(0).strip("'’-")
        if len(w) < 3 or w.lower() in _UNITS:
            continue
        letters = re.sub(r"[^A-Za-z]", "", w)
        if letters.isupper() or w.lower() in _ALLOWED_LATIN or w.lower() in ALLOWED_BRANDS:  # acronym (RBI)
            continue
        if re.fullmatch(r"[A-Z][a-z]?[A-Z][A-Za-z]*", w) and sum(c.isupper() for c in w) >= 2:
            continue                        # mixed-case acronyms (DoT, MoEFCC, IoT)
        out.append(w)
    return out


_FALLBACK_RE = re.compile(r"^\s*(?:परीक्षा संदर्भ|मुख्य बिंदु):|— समसामयिक (?:घटनाक्रम|विवरण)")
_RUN_RE = re.compile(r"[A-Za-z][A-Za-z'’\-]*(?:[\s,]+[A-Za-z][A-Za-z'’\-]*){3,}")
_FUNCTION_WORDS = {"of", "and", "the", "for", "in", "to", "on", "with", "by", "from", "a", "an", "is", "are", "was"}


def untranslated_run(hi: str) -> bool:
    """Four or more consecutive English words that include a function word ('Commissions of
    Inquiry Act'): an untranslated phrase, not a proper noun."""
    text = _PAREN_RE.sub(" ", _URL_RE.sub(" ", hi or ""))
    for m in _RUN_RE.finditer(text):
        toks = re.split(r"[\s,]+", m.group(0))
        if any(t.lower() in _FUNCTION_WORDS for t in toks) or sum(t[:1].islower() for t in toks) >= 2:
            return True
    return False


def _deva_only(s: Any) -> str:
    s = str(s or "").strip().strip("।.\"'")
    return s if s and DEVA_RE.search(s) and not LATIN_RE.search(s) and len(s) <= 40 else ""


def _fix_mixed(en: str, hi: str, translator: Optional[Callable[[str], str]]) -> Optional[str]:
    """Re-render each mixed-script word from the English line. None -> could not repair."""
    for word in mixed_words(hi):
        latin = "".join(re.findall(r"[A-Za-z]+", word)).lower()
        cands = [w for w in re.findall(r"[A-Za-z][A-Za-z\-]+", en or "")
                 if latin and (w.lower().endswith(latin) or w.lower().startswith(latin) or latin in w.lower())]
        cands.sort(key=lambda w: (w.lower() != latin, -len(w)))
        rep = ""
        for c in cands:
            rep = _WORD_HI.get(c.lower(), "")
            if not rep and translator is not None:
                try:
                    rep = _deva_only(translator(c))
                except Exception:
                    rep = ""
            if rep:
                break
        if not rep:
            m = re.fullmatch(rf"([{_DL}]+)([A-Za-z]+)", word)
            if m:
                rep = next((m.group(1) + h for suf, h in _SUFFIX_HI if m.group(2).lower() == suf), "")
        if not rep:
            return None
        hi = hi.replace(word, rep, 1)
    return hi


def _numbers(s: str) -> set:
    return set(re.findall(r"\d+(?:[.,]\d+)*", (s or "").translate(_DEVA_DIGITS).replace(",", "")))


def strict_problems(en: str, hi: str) -> List[str]:
    """Why a Hindi line is not printable in a strict (period) edition; [] = fine."""
    out: List[str] = []
    if not hi or not DEVA_RE.search(hi):
        return ["no hindi"]
    if leftover_words(hi):
        out.append("english: " + ", ".join(leftover_words(hi)[:3]))
    if mixed_words(hi) or untranslated_run(hi):
        out.append("mixed/untranslated")
    if hi_truncated_start(hi):
        out.append("truncated start")
    if garbled_hi(hi):
        out.append("garbled")
    if en and not _numbers(en) <= _numbers(hi):
        out.append("numbers differ")
    return out


def _retranslate(en: str, name_map: Optional[Dict[str, str]],
                 line_translator: Optional[Callable[[str], str]]) -> str:
    if line_translator is None or not en:
        return ""
    try:
        cand = str(line_translator(en) or "")
    except Exception:
        return ""
    if not cand or not DEVA_RE.search(cand):
        return ""
    cand = apply_glossary(en, cand)
    if name_map:
        cand = fix_names(en, cand, name_map)
    return cand


def fix_pair(en: str, hi: str, *, name_map: Optional[Dict[str, str]] = None,
             translator: Optional[Callable[[str], str]] = None,
             line_translator: Optional[Callable[[str], str]] = None,
             stats: Optional[Dict[str, int]] = None, strict: bool = False) -> str:
    """Repaired Hindi for one line ('' = blank, render English-only). Never raises.

    ``strict`` (period editions): any English word left (beyond acronyms, units and
    allowed brand names), a truncated start, a garbled structure or a number that
    differs from the English line makes the line be re-translated through
    ``line_translator``; if that fails too the line is blanked (the caller drops it)."""
    st = stats if stats is not None else {}
    try:
        if not hi or not DEVA_RE.search(str(hi)):
            return hi
        en, hi0 = str(en or ""), str(hi)
        out = apply_glossary(en, hi0)
        if name_map:
            out = fix_names(en, out, name_map)
        if hi_truncated_start(out):
            fixed = repair_truncated_start(en, out)
            if not fixed:
                new = _retranslate(en, name_map, line_translator)
                if new and not strict_problems(en, new):
                    st["retranslated"] = st.get("retranslated", 0) + 1
                    return new
                st["blank_truncated"] = st.get("blank_truncated", 0) + 1
                logger.info("[hindi] truncated Hindi line blanked: %s", hi0[:80])
                return ""
            out = fixed
            st["truncation_fixed"] = st.get("truncation_fixed", 0) + 1
        if mixed_words(out):
            fixed = _fix_mixed(en, out, translator)
            if fixed is None:
                st["blank_mixed"] = st.get("blank_mixed", 0) + 1
                logger.info("[hindi] mixed-script line blanked: %s", hi0[:80])
                return ""
            out = fixed
            st["mixed_fixed"] = st.get("mixed_fixed", 0) + 1
        if _FALLBACK_RE.search(out) and not strict:
            # content.translate_headline_deterministic's labelled English (offline/AI-down
            # fallback) is a deliberate format, not a broken translation: leave it.
            st["fallback_kept"] = st.get("fallback_kept", 0) + 1
            return out
        left = leftover_words(out)
        words = max(1, len(out.split()))
        if strict and (strict_problems(en, out) or _FALLBACK_RE.search(out)):
            new = _retranslate(en, name_map, line_translator)
            if new and not strict_problems(en, new):
                st["retranslated"] = st.get("retranslated", 0) + 1
                return new
            st["blank_strict"] = st.get("blank_strict", 0) + 1
            logger.info("[hindi] strict: line dropped (%s): %s", "; ".join(strict_problems(en, out)), hi0[:80])
            return ""
        if untranslated_run(out) or (len(left) >= 4 and len(left) / words >= 0.4):
            new = _retranslate(en, name_map, line_translator)
            if new and not mixed_words(new) and not untranslated_run(new):
                st["retranslated"] = st.get("retranslated", 0) + 1
                return new
            st["blank_english"] = st.get("blank_english", 0) + 1
            logger.info("[hindi] English left in Hindi line (%s); blanked", ", ".join(left[:4]))
            return ""
        if left:
            st["leftover_kept"] = st.get("leftover_kept", 0) + 1
        if out != hi0:
            st["changed"] = st.get("changed", 0) + 1
        return out
    except Exception as exc:  # fail closed
        logger.info("[hindi] post-fix error (%s); line blanked", exc)
        st["errors"] = st.get("errors", 0) + 1
        return ""


# --------------------------------------------------------------------------- #
# Edition walk
# --------------------------------------------------------------------------- #
_PAIR_KEYS = (("headline_en", "headline_hi"), ("title", "title_hi"), ("summary_en", "summary_hi"),
              ("detailed_explanation_en", "detailed_explanation_hi"), ("exam_fact_en", "exam_fact_hi"),
              ("question_en", "question_hi"), ("explanation_en", "explanation_hi"), ("text_en", "text_hi"),
              ("label_en", "label_hi"), ("value_en", "value_hi"), ("en", "hi"), ("category_en", "category_hi"))
_LIST_KEYS = (("key_points_en", "key_points_hi"), ("options", "options_hi"), ("options_en", "options_hi"))


def _learn_names(mcqs: Iterable[Dict[str, Any]], name_map: Dict[str, str]) -> None:
    """First verified rendering of a bare-name Static GK value becomes the edition's spelling."""
    from agents.static_gk_validator import name_candidates  # lazy: avoids an import cycle
    for m in mcqs:
        for r in m.get("static_gk") or []:
            if not isinstance(r, dict):
                continue
            ve, vh = str(r.get("value_en") or "").strip(), str(r.get("value_hi") or "").strip()
            if not ve or not vh or LATIN_RE.search(vh) or not DEVA_RE.search(vh):
                continue
            c = name_candidates(ve)
            if len(c) == 1 and _norm_en(c[0][0]) == _norm_en(ve) and not any(
                    _norm_en(k) == _norm_en(ve) for k in name_map):
                name_map[ve] = vh


def _walk(node: Any, fix: Callable[[str, str], str]) -> None:
    if isinstance(node, dict):
        for ek, hk in _PAIR_KEYS:
            if hk in node and isinstance(node.get(hk), str) and isinstance(node.get(ek, ""), str):
                node[hk] = fix(node.get(ek) or "", node[hk])
        for ek, hk in _LIST_KEYS:
            ens, his = node.get(ek), node.get(hk)
            if isinstance(ens, list) and isinstance(his, list):
                for i, h in enumerate(his):
                    if isinstance(h, str):
                        his[i] = fix(str(ens[i]) if i < len(ens) else "", h)
        for k, v in node.items():
            if isinstance(v, (dict, list)) and k not in ("source", "job"):
                _walk(v, fix)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            if (isinstance(v, (list, tuple)) and len(v) == 2 and all(isinstance(x, str) for x in v)
                    and DEVA_RE.search(v[1] or "")):
                new = fix(v[0], v[1])
                node[i] = (v[0], new) if isinstance(v, tuple) else [v[0], new]
            elif isinstance(v, (dict, list)):
                _walk(v, fix)


def fix_edition(content: Dict[str, Any], mcq_data: Any = None, *,
                translator: Optional[Callable[[str], str]] = None,
                line_translator: Optional[Callable[[str], str]] = None,
                facts_path: Optional[Path] = None) -> Dict[str, int]:
    """Repair every Hindi line of an edition in place. Returns stats. Never raises."""
    stats: Dict[str, int] = {}
    try:
        name_map = load_name_map(facts_path)
        mcqs = mcq_data if isinstance(mcq_data, list) else (
            (mcq_data or {}).get("mcqs") if isinstance(mcq_data, dict) else [])
        mcqs = [m for m in mcqs or [] if isinstance(m, dict)]
        try:
            _learn_names(mcqs, name_map)
        except Exception:
            pass

        def fix(en: str, hi: str) -> str:
            stats["lines"] = stats.get("lines", 0) + 1
            return fix_pair(en, hi, name_map=name_map, translator=translator,
                            line_translator=line_translator, stats=stats)

        if isinstance(content, dict):
            _walk({k: v for k, v in content.items() if k not in ("reserve_items",)}, fix)
        _walk(mcqs, fix)
    except Exception as exc:  # pragma: no cover - fail open on the walk itself
        logger.warning("[hindi] edition post-fix aborted: %s", exc)
        stats["errors"] = stats.get("errors", 0) + 1
    logger.info("[hindi] post-fix: %s", stats)
    return stats


def budgeted_translators(max_calls: int = 20, budget_s: float = 45.0
                         ) -> Tuple[Optional[Callable[[str], str]], Optional[Callable[[str], str]]]:
    """(word, line) translators over pipeline.ai_translator with a shared call/time budget.
    (None, None) under pytest or when the translator is unavailable."""
    import os
    import time
    if os.getenv("PYTEST_CURRENT_TEST") or os.getenv("ALP_HINDI_POSTFIX_AI", "1") == "0":
        return None, None
    try:
        from pipeline.ai_translator import translate_content
    except Exception:
        return None, None
    box = {"n": 0, "t0": time.monotonic()}

    def _tr(text: str) -> str:
        if box["n"] >= max_calls or time.monotonic() - box["t0"] > budget_s:
            return ""
        box["n"] += 1
        res = translate_content(text, task="general")
        return res.get("translated_hi", "") if res.get("passed") else ""

    return _tr, _tr
