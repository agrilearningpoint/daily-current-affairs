# -*- coding: utf-8 -*-
"""
MCQ quality layer (audit 2026-11-04): answer-position balance, known-key
verification, broken-template detection, stale officeholder titles and
conceptual (static-fact) questions.

Everything here is deterministic and offline:

* ``quality_errors`` is called by ``pipeline.content.validate_mcqs`` so every
  MCQ (LLM, bilingual template, legacy template) is checked by stages 16 and 17.
* ``concept_mcqs`` builds static/conceptual questions ("Which body recommends
  MSP?") from a small table of verified mappings.
* ``balance_answer_positions`` reshuffles the final set (seeded by job date +
  question index) so the keyed answer is spread over all option letters.
"""
from __future__ import annotations

import hashlib
import json
import logging
import random
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)

LETTERS = "ABCDE"
_FACTS_PATH = Path(__file__).resolve().parent.parent / "config" / "current_facts.json"

# --------------------------------------------------------------------------- #
# Known mappings: a question about TOPIC that asks for a body must be keyed to
# one of ACCEPT.  ``q`` is the conceptual question built from the mapping.
# --------------------------------------------------------------------------- #
ORG_ASK_RE = re.compile(r"\b(?:organi[sz]ation|body|ministry|institution|entity|agency|regulator|authority|"
                        r"संगठन|संस्था|मंत्रालय|निकाय)\b", re.I)

KNOWN_MAPPINGS: List[Dict[str, Any]] = [
    {"id": "msp", "trigger": r"\bMSP\b|minimum support price",
     "accept": r"\bCACP\b|Commission for Agricultural Costs",
     "q": ("Which body recommends the Minimum Support Price (MSP) of notified crops to the Government of India?",
           "भारत सरकार को अधिसूचित फसलों के न्यूनतम समर्थन मूल्य (MSP) की सिफारिश कौन-सा निकाय करता है?"),
     "answer": ("Commission for Agricultural Costs and Prices (CACP)", "कृषि लागत एवं मूल्य आयोग (CACP)"),
     "expl": ("The MSP of notified crops is announced by the Government on the recommendation of the "
              "Commission for Agricultural Costs and Prices (CACP), an attached office of the Ministry of "
              "Agriculture & Farmers Welfare.",
              "अधिसूचित फसलों का MSP सरकार कृषि लागत एवं मूल्य आयोग (CACP) की सिफारिश पर घोषित करती है, "
              "जो कृषि एवं किसान कल्याण मंत्रालय का संबद्ध कार्यालय है।"),
     "distractors": [("Indian Council of Agricultural Research (ICAR)", "भारतीय कृषि अनुसंधान परिषद (ICAR)"),
                     ("Food Corporation of India (FCI)", "भारतीय खाद्य निगम (FCI)"),
                     ("NABARD", "नाबार्ड (NABARD)"),
                     ("NAFED", "नेफेड (NAFED)"),
                     ("NITI Aayog", "नीति आयोग"),
                     ("Finance Commission", "वित्त आयोग")]},
    {"id": "repo", "trigger": r"\brepo rate\b|\bpolicy rate\b",
     "accept": r"Monetary Policy Committee|\bMPC\b|\bRBI\b|Reserve Bank",
     "q": ("Which body decides the policy repo rate in India?",
           "भारत में नीतिगत रेपो दर का निर्धारण कौन-सा निकाय करता है?"),
     "answer": ("Monetary Policy Committee (MPC)", "मौद्रिक नीति समिति (MPC)"),
     "expl": ("The policy repo rate is fixed by the six-member Monetary Policy Committee (MPC) of the Reserve "
              "Bank of India, set up under the amended RBI Act, 1934.",
              "नीतिगत रेपो दर भारतीय रिज़र्व बैंक की छह सदस्यीय मौद्रिक नीति समिति (MPC) तय करती है, "
              "जिसका गठन संशोधित RBI अधिनियम, 1934 के तहत हुआ।"),
     "distractors": [("Finance Commission", "वित्त आयोग"), ("NITI Aayog", "नीति आयोग"),
                     ("Financial Stability and Development Council (FSDC)", "वित्तीय स्थिरता एवं विकास परिषद (FSDC)"),
                     ("SEBI", "सेबी (SEBI)"), ("GST Council", "जीएसटी परिषद")]},
    {"id": "gst", "trigger": r"\bGST rates?\b|\bGST rate cut",
     "accept": r"GST Council",
     "q": ("Which constitutional body recommends the rates of Goods and Services Tax (GST)?",
           "वस्तु एवं सेवा कर (GST) की दरों की सिफारिश कौन-सा संवैधानिक निकाय करता है?"),
     "answer": ("GST Council", "जीएसटी परिषद"),
     "expl": ("GST rates are recommended by the GST Council, a constitutional body under Article 279A "
              "chaired by the Union Finance Minister.",
              "GST दरों की सिफारिश अनुच्छेद 279A के तहत गठित संवैधानिक निकाय जीएसटी परिषद करती है, "
              "जिसके अध्यक्ष केंद्रीय वित्त मंत्री होते हैं।"),
     "distractors": [("Finance Commission", "वित्त आयोग"), ("NITI Aayog", "नीति आयोग"),
                     ("Central Board of Direct Taxes (CBDT)", "केंद्रीय प्रत्यक्ष कर बोर्ड (CBDT)"),
                     ("Monetary Policy Committee (MPC)", "मौद्रिक नीति समिति (MPC)"),
                     ("Inter-State Council", "अंतर-राज्य परिषद")]},
    {"id": "upi", "trigger": r"\bUPI\b|Unified Payments Interface", "accept": r"\bNPCI\b|National Payments Corporation",
     "strict": False,
     "q": ("Which organisation developed and operates the Unified Payments Interface (UPI)?",
           "एकीकृत भुगतान इंटरफ़ेस (UPI) को किस संगठन ने विकसित किया है और कौन इसका संचालन करता है?"),
     "answer": ("National Payments Corporation of India (NPCI)", "भारतीय राष्ट्रीय भुगतान निगम (NPCI)"),
     "expl": ("UPI was developed and is operated by the National Payments Corporation of India (NPCI), "
              "an umbrella body for retail payments promoted by the RBI and the Indian Banks' Association.",
              "UPI को भारतीय राष्ट्रीय भुगतान निगम (NPCI) ने विकसित किया है और वही इसका संचालन करता है; "
              "NPCI खुदरा भुगतान का शीर्ष संगठन है।"),
     "distractors": [("SIDBI", "सिडबी (SIDBI)"), ("SEBI", "सेबी (SEBI)"), ("NABARD", "नाबार्ड (NABARD)"),
                     ("IRDAI", "आईआरडीएआई (IRDAI)"), ("Exim Bank", "एक्ज़िम बैंक"), ("PFRDA", "पीएफआरडीए (PFRDA)")]},
    {"id": "jjm", "trigger": r"Jal Jeevan Mission|\bJJM\b", "accept": r"Jal Shakti", "strict": False,
     "q": ("Which Union Ministry implements the Jal Jeevan Mission?",
           "जल जीवन मिशन का कार्यान्वयन कौन-सा केंद्रीय मंत्रालय करता है?"),
     "answer": ("Ministry of Jal Shakti", "जल शक्ति मंत्रालय"),
     "expl": ("The Jal Jeevan Mission, launched in 2019 to provide tap water to every rural household, is "
              "implemented by the Ministry of Jal Shakti.",
              "हर ग्रामीण घर तक नल से जल पहुँचाने हेतु 2019 में शुरू जल जीवन मिशन का कार्यान्वयन जल शक्ति मंत्रालय करता है।"),
     "distractors": [("Ministry of Rural Development", "ग्रामीण विकास मंत्रालय"),
                     ("Ministry of Housing and Urban Affairs", "आवासन और शहरी कार्य मंत्रालय"),
                     ("Ministry of Panchayati Raj", "पंचायती राज मंत्रालय"),
                     ("Ministry of Environment, Forest and Climate Change", "पर्यावरण, वन और जलवायु परिवर्तन मंत्रालय"),
                     ("Ministry of Health and Family Welfare", "स्वास्थ्य एवं परिवार कल्याण मंत्रालय")]},
    {"id": "mgnrega", "trigger": r"MGNREGA|MGNREGS|Mahatma Gandhi National Rural Employment", "accept": r"Rural Development",
     "strict": False,
     "q": ("Which Union Ministry administers the Mahatma Gandhi National Rural Employment Guarantee Act (MGNREGA)?",
           "महात्मा गांधी राष्ट्रीय ग्रामीण रोजगार गारंटी अधिनियम (मनरेगा) का प्रशासन कौन-सा केंद्रीय मंत्रालय करता है?"),
     "answer": ("Ministry of Rural Development", "ग्रामीण विकास मंत्रालय"),
     "expl": ("MGNREGA, enacted in 2005, guarantees 100 days of wage employment to rural households and is "
              "administered by the Ministry of Rural Development.",
              "2005 में लागू मनरेगा ग्रामीण परिवारों को 100 दिन के मज़दूरी रोज़गार की गारंटी देता है और इसका प्रशासन "
              "ग्रामीण विकास मंत्रालय करता है।"),
     "distractors": [("Ministry of Labour and Employment", "श्रम एवं रोज़गार मंत्रालय"),
                     ("Ministry of Panchayati Raj", "पंचायती राज मंत्रालय"),
                     ("Ministry of Jal Shakti", "जल शक्ति मंत्रालय"),
                     ("Ministry of Social Justice and Empowerment", "सामाजिक न्याय एवं अधिकारिता मंत्रालय"),
                     ("Ministry of Skill Development and Entrepreneurship", "कौशल विकास एवं उद्यमिता मंत्रालय")]},
    {"id": "pmjay", "trigger": r"PM-JAY|PMJAY|Ayushman Bharat", "accept": r"National Health Authority|\bNHA\b",
     "strict": False,
     "q": ("Which body is the apex implementing agency of Ayushman Bharat Pradhan Mantri Jan Arogya Yojana (AB PM-JAY)?",
           "आयुष्मान भारत प्रधानमंत्री जन आरोग्य योजना (AB PM-JAY) की शीर्ष कार्यान्वयन एजेंसी कौन-सी है?"),
     "answer": ("National Health Authority (NHA)", "राष्ट्रीय स्वास्थ्य प्राधिकरण (NHA)"),
     "expl": ("AB PM-JAY, launched in 2018, is implemented by the National Health Authority (NHA) under the "
              "Ministry of Health and Family Welfare.",
              "2018 में शुरू AB PM-JAY का कार्यान्वयन स्वास्थ्य एवं परिवार कल्याण मंत्रालय के अधीन राष्ट्रीय स्वास्थ्य "
              "प्राधिकरण (NHA) करता है।"),
     "distractors": [("Indian Council of Medical Research (ICMR)", "भारतीय आयुर्विज्ञान अनुसंधान परिषद (ICMR)"),
                     ("National Medical Commission (NMC)", "राष्ट्रीय आयुर्विज्ञान आयोग (NMC)"),
                     ("IRDAI", "आईआरडीएआई (IRDAI)"),
                     ("Central Drugs Standard Control Organisation (CDSCO)", "केंद्रीय औषधि मानक नियंत्रण संगठन (CDSCO)"),
                     ("FSSAI", "भारतीय खाद्य सुरक्षा एवं मानक प्राधिकरण (FSSAI)")]},
    {"id": "enam", "trigger": r"\be-NAM\b|\beNAM\b|National Agriculture Market",
     "accept": r"\bSFAC\b|Small Farmers", "strict": False,
     "q": ("Which agency is the lead implementing agency of the National Agriculture Market (e-NAM)?",
           "राष्ट्रीय कृषि बाज़ार (e-NAM) की प्रमुख कार्यान्वयन एजेंसी कौन-सी है?"),
     "answer": ("Small Farmers' Agribusiness Consortium (SFAC)", "लघु कृषक कृषि-व्यापार संघ (SFAC)"),
     "expl": ("e-NAM, the pan-India electronic trading portal for agricultural commodities launched in 2016, "
              "is implemented by the Small Farmers' Agribusiness Consortium (SFAC) under the Ministry of "
              "Agriculture & Farmers Welfare.",
              "2016 में शुरू कृषि उपज के अखिल भारतीय इलेक्ट्रॉनिक व्यापार पोर्टल e-NAM का कार्यान्वयन कृषि एवं "
              "किसान कल्याण मंत्रालय के अधीन लघु कृषक कृषि-व्यापार संघ (SFAC) करता है।"),
     "distractors": [("NAFED", "नेफेड (NAFED)"), ("NABARD", "नाबार्ड (NABARD)"),
                     ("Food Corporation of India (FCI)", "भारतीय खाद्य निगम (FCI)"),
                     ("APEDA", "एपीडा (APEDA)"), ("Central Warehousing Corporation (CWC)", "केंद्रीय भंडारण निगम (CWC)")]},
]


def _base(o: Any) -> str:
    return str(o or "").split(" / ")[0].strip()


def _ws(t: Any) -> str:
    return re.sub(r"\s+", " ", str(t or "")).strip()


def mapping_for(text: str) -> Optional[Dict[str, Any]]:
    for mp in KNOWN_MAPPINGS:
        if re.search(mp["trigger"], text or "", re.I):
            return mp
    return None


def known_mapping_supports(question: str, answer: str) -> bool:
    """True when ``answer`` is the verified key for the topic the question asks about."""
    q = question or ""
    for mp in KNOWN_MAPPINGS:
        if re.search(mp["trigger"], q, re.I) and re.search(mp["accept"], answer or "", re.I):
            return True
    return False


def mapping_conflict(question: str, answer: str) -> str:
    """Error text when an organisation question about a known topic is keyed to the wrong body."""
    q = question or ""
    if not ORG_ASK_RE.search(q):
        return ""
    for mp in KNOWN_MAPPINGS:
        if mp.get("strict", True) is False:
            continue
        if re.search(mp["trigger"], q, re.I) and not re.search(mp["accept"], answer or "", re.I):
            return f"wrong key: a {mp['id'].upper()} question must be keyed to {mp['answer'][0]}"
    return ""


def concept_mcqs(ci: Dict[str, Any], evidence: str) -> List[Dict[str, Any]]:
    """Static/conceptual MCQs for the known topics the story mentions (exam value beyond the headline)."""
    from pipeline.mcq_builder import _make
    out = []
    low = (evidence or "").lower()
    for mp in KNOWN_MAPPINGS:
        if not re.search(mp["trigger"], evidence or "", re.I):
            continue
        ds = [d for d in mp["distractors"]
              if d[0].lower() not in low and not any(p.lower() in low for p in re.findall(r"\(([A-Z]{2,8})\)", d[0]))]
        ds = sorted(ds, key=lambda d: hashlib.sha1((str(ci.get("event_id")) + d[0]).encode()).hexdigest())
        if len(ds) < 4:
            continue
        m = _make(ci, "concept", mp["q"][0], mp["q"][1], mp["answer"], ds[:4], mp["expl"][0], mp["expl"][1])
        if m:
            m["concept_id"] = mp["id"]
            out.append(m)
    return out


# --------------------------------------------------------------------------- #
# Current officeholders (config/current_facts.json)
# --------------------------------------------------------------------------- #
_FACTS: List[Dict[str, Any]] = []


def _facts() -> List[Dict[str, Any]]:
    if not _FACTS:
        try:
            _FACTS.extend(json.loads(_FACTS_PATH.read_text(encoding="utf-8")).get("facts") or [])
        except Exception:
            logger.warning("[MCQ quality] current_facts.json unavailable")
    return _FACTS


def _holder_names(f: Dict[str, Any]) -> List[str]:
    return [n for n in [f.get("name")] + list(f.get("names") or []) + list(f.get("aliases") or []) if n]


def known_person(name: str) -> bool:
    n = _norm_name(name)
    return bool(n) and any(_norm_name(h) == n for f in _facts() for h in _holder_names(f))


def _norm_name(s: str) -> str:
    s = re.sub(r"^(?:Dr|Mr|Ms|Mrs|Shri|Smt|Prof|Sh)\.?\s+", "", _ws(s), flags=re.I)
    return re.sub(r"[^a-z]", "", s.lower())


def stale_title_error(option: str) -> str:
    """'Union Agriculture Minister Narendra Singh Tomar' -> error (the post is now held by someone else)."""
    o = _base(option)
    for f in _facts():
        for phrase in f.get("match") or []:
            if len(phrase) < 4 or not re.search(r"\b" + re.escape(phrase) + r"\b", o, re.I):
                continue
            rest = re.sub(re.escape(phrase), " ", o, flags=re.I)
            rest = re.sub(r"\b(?:Union|the|of|India|Shri|Smt|Dr|Mr|Ms)\b\.?", " ", rest)
            name = _ws(re.sub(r"[,()\-–]", " ", rest))
            if not re.search(r"[A-Z][a-z]+", name):
                continue
            holders = [_norm_name(h) for h in _holder_names(f)]
            if _norm_name(name) not in holders and not any(h and h in _norm_name(name) for h in holders):
                return f"stale officeholder title: '{o}' ({f.get('post')} is {f.get('name')})"
    return ""


# --------------------------------------------------------------------------- #
# Broken-template checks
# --------------------------------------------------------------------------- #
PLACEHOLDER_RE = re.compile(r"\bFact\s*\d\b|\(Key\s*:|\bKey\s*:|\{\w*\}|_{3,}|\[(?:number|name|value|x)\]|"
                            r"\bXX+\b|\bN/A\b|\bTBD\b|<[a-z_]+>|\blorem\b", re.I)
MISSING_NUM_RE = re.compile(
    r"(?:₹|Rs\.?|INR|US\$|\$)\s*(?:crore|lakh|billion|million|trillion|cr)\b"
    r"|(?:^|[\s(])(?:per cent|percent|%)(?=[\s,.)]|$)"
    r"|\b(?:cover|reach|touch|cross|exceed)\s+of\b"
    r"|\b(?:could|would|will|may|might|can)\s+be\s+(?:of|in|at)\b"
    r"|\b(?:of|to|by|at|from)\s+(?:of|to|by)\s", re.I)
PERSON_RE = re.compile(r"^(?:Dr|Mr|Ms|Mrs|Shri|Smt|Prof)\.?\s+[A-Z][a-z]+(?:\s+[A-Z]\.?[a-z]*){0,3}$")
_PCT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:%|per\s*cent|percent)", re.I)
_STOP = set("""a an the of to in on for and or by with from at as is are was were be been its it this that
these those has have had will would can could per cent percent crore lakh rs india indian govt government
news reported report reports reporting verified source official according as per figure development
associated organisation organization key correct answer option statement directly taken features this
""".split())


def _tokens(s: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if w not in _STOP and len(w) > 1}


def explanation_is_headline_only(expl: str, headline: str, answer: str, src_name: str = "") -> bool:
    e = _ws(expl)
    if not e:
        return False
    if src_name:
        e = re.sub(re.escape(src_name), " ", e, flags=re.I)
    extra = _tokens(e) - _tokens(headline) - _tokens(answer)
    return len(extra) < 3


def quality_errors(m: Dict[str, Any], ci: Optional[Dict[str, Any]] = None, evidence: str = "") -> List[str]:
    """Audit checks shared by stages 16/17. Empty list = OK."""
    ci = ci or {}
    errs: List[str] = []
    opts = [str(o) for o in (m.get("options") or [])]
    opts_en = [_base(o) for o in opts]
    letter = str(m.get("correct") or "")
    idx = LETTERS.find(letter) if len(letter) == 1 else -1
    answer = opts_en[idx] if 0 <= idx < len(opts_en) else ""
    q_en = _ws(m.get("question_en"))
    texts = [q_en, _ws(m.get("question_hi")), _ws(m.get("explanation_en")), _ws(m.get("explanation_hi"))] + opts
    texts += [_ws(h) for h in (m.get("options_hi") or [])]

    if any(PLACEHOLDER_RE.search(t) for t in texts if t):
        errs.append("placeholder text (Fact N / Key: / blank)")
    if MISSING_NUM_RE.search(q_en):
        errs.append("question stem has a missing number")
    canon = [re.sub(r"[^a-z0-9%.]", "", o.lower()) for o in opts_en]
    if len(set(canon)) != len(canon) or any(not c for c in canon):
        errs.append("duplicate or empty options")

    pcts = [(_PCT_RE.search(o)) for o in opts_en]
    if answer and all(pcts) and float(pcts[idx].group(1)) <= 100 and any(float(p.group(1)) > 100 for p in pcts):
        if not re.search(r"\b(?:growth|increase|rise|jump|surge|change)\b", q_en, re.I):
            errs.append("percentage option above 100%")

    low_ev = evidence.lower()
    for i, o in enumerate(opts_en):
        if i == idx:
            continue
        if PERSON_RE.match(o) and o.lower() not in low_ev and not known_person(o):
            errs.append(f"fabricated person distractor: '{o}'")
            break
    for o in opts_en:
        e = stale_title_error(o)
        if e:
            errs.append(e)
            break

    conflict = mapping_conflict(q_en, answer)
    if conflict:
        errs.append(conflict)

    src_name = ((ci.get("source") or {}).get("name") if isinstance(ci.get("source"), dict) else "") or ""
    headline = _ws(ci.get("headline_en"))
    if headline and m.get("type") != "concept" and explanation_is_headline_only(
            m.get("explanation_en") or "", headline, answer, src_name):
        errs.append("explanation only repeats the headline")
    errs.extend(hardening_errors(m, evidence))
    return errs


def answer_in_headline(m: Dict[str, Any], ci: Dict[str, Any]) -> bool:
    opts = m.get("options") or []
    letter = str(m.get("correct") or "")
    if len(letter) != 1 or LETTERS.find(letter) < 0 or LETTERS.find(letter) >= len(opts):
        return False
    ans = _base(opts[LETTERS.index(letter)]).lower()
    h = _ws(ci.get("headline_en")).lower()
    if not ans or not h:
        return False
    if ans in h:
        return True
    acr = re.findall(r"\(([A-Za-z-]{2,10})\)", _base(opts[LETTERS.index(letter)]))
    return any(re.search(r"\b" + re.escape(a.lower()) + r"\b", h) for a in acr)


# --------------------------------------------------------------------------- #
# Answer-position balance
# --------------------------------------------------------------------------- #
_LETTER_REF_RE = re.compile(r"(\b(?:[Oo]ption|[Aa]nswer|विकल्प|उत्तर)\s*[:\-]?\s*\(?)([A-E])(\)?)")


def _remap_refs(text: Any, mapping: Dict[str, str]) -> Any:
    if not isinstance(text, str) or not text:
        return text
    return _LETTER_REF_RE.sub(lambda mo: mo.group(1) + mapping.get(mo.group(2), mo.group(2)) + mo.group(3), text)


def shuffle_mcq(m: Dict[str, Any], seed: str, target: Optional[int] = None) -> Dict[str, Any]:
    """Return a copy of ``m`` with options permuted (deterministic for ``seed``).
    ``target`` forces the correct option's new position.  Hindi options, the key
    and option-letter references in explanations are remapped."""
    opts = list(m.get("options") or [])
    n = len(opts)
    letter = str(m.get("correct") or "")
    if n < 2 or len(letter) != 1 or not (0 <= LETTERS.find(letter) < n):
        return m
    ci = LETTERS.index(letter)
    rng = random.Random(int(hashlib.sha256(seed.encode("utf-8")).hexdigest(), 16))
    others = [i for i in range(n) if i != ci]
    rng.shuffle(others)
    pos = target % n if target is not None else rng.randrange(n)
    order = others[:pos] + [ci] + others[pos:]          # order[new] = old index
    out = dict(m)
    out["options"] = [opts[i] for i in order]
    his = m.get("options_hi")
    if isinstance(his, list) and len(his) == n:
        out["options_hi"] = [his[i] for i in order]
    out["correct"] = LETTERS[pos]
    mapping = {LETTERS[old]: LETTERS[new] for new, old in enumerate(order)}
    for k in ("explanation_en", "explanation_hi"):
        if k in out:
            out[k] = _remap_refs(out[k], mapping)
    if isinstance(m.get("explanation_pairs"), list):
        out["explanation_pairs"] = [
            {kk: _remap_refs(vv, mapping) for kk, vv in p.items()} if isinstance(p, dict) else p
            for p in m["explanation_pairs"]]
    return out


def job_date_of(job_id: str, content: Optional[Dict[str, Any]] = None) -> str:
    job = (content or {}).get("job") if isinstance(content, dict) else None
    for v in ((job or {}).get("date"), (job or {}).get("job_date"), job_id):
        mo = re.search(r"\d{4}-\d{2}-\d{2}", str(v or ""))
        if mo:
            return mo.group(0)
    return str(job_id or "")


def balance_answer_positions(mcqs: List[Dict[str, Any]], job_date: str) -> List[Dict[str, Any]]:
    """Shuffle every MCQ's options, seeded by job date + question index, with the
    keyed positions drawn from a balanced (date-shuffled) sequence so no letter
    dominates.  Mutates and returns the list (q_num kept)."""
    n = len(mcqs)
    if not n:
        return mcqs
    seq = [i % len(LETTERS) for i in range(n)]
    random.Random(int(hashlib.sha256(("pos|" + job_date).encode()).hexdigest(), 16)).shuffle(seq)
    for i, m in enumerate(mcqs):
        if not isinstance(m, dict):
            continue
        k = len(m.get("options") or [])
        if k < 2:
            continue
        mcqs[i] = shuffle_mcq(m, f"{job_date}|{i}", target=seq[i] % k)
    return mcqs


def letter_spread(mcqs: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for m in mcqs:
        out[str(m.get("correct"))] = out.get(str(m.get("correct")), 0) + 1
    return out


# --------------------------------------------------------------------------- #
# LLM self-verification
# --------------------------------------------------------------------------- #
VERIFY_MARK = "MCQ SELF-CHECK"
VERIFY_PROMPT = VERIFY_MARK + """: answer this exam question using ONLY the NEWS below plus well-established static
facts (e.g. MSP is recommended by CACP; the repo rate is set by the RBI Monetary Policy Committee).
NEWS (headline): {headline}
NEWS (text): {text}

QUESTION: {question}
{options}

Respond with ONLY this JSON: {{"answer": "<letter>"}}"""


def build_verify_prompt(m: Dict[str, Any], headline: str, text: str) -> str:
    opts = "\n".join(f"{LETTERS[i]}) {_base(o)}" for i, o in enumerate(m.get("options") or []))
    return VERIFY_PROMPT.format(headline=_ws(headline), text=_ws(text)[:2000],
                                question=_ws(m.get("question_en")), options=opts)


def parse_verify_reply(raw: Any) -> str:
    """Letter the verifier chose, or '' when the reply is unusable."""
    s = str(raw or "").strip()
    if not s:
        return ""
    mo = re.search(r'"answer"\s*:\s*"?\(?([A-Ea-e])\b', s)
    if mo:
        return mo.group(1).upper()
    mo = re.fullmatch(r"\(?([A-Ea-e])\)?[.)]?", s)
    return mo.group(1).upper() if mo else ""


# --------------------------------------------------------------------------- #
# Hardening gates (weekly audit 2026-11-08): key consistency, grounding,
# give-aways, option entity types and complete Hindi.  Shared by the daily
# validator (quality_errors) and the weekly/monthly assembly (harden_mcq).
# --------------------------------------------------------------------------- #
_DEV_RE = re.compile(r"[\u0900-\u097F]")
_MULT = {"k": 1e3, "thousand": 1e3, "lakh": 1e5, "lakhs": 1e5, "crore": 1e7, "crores": 1e7, "cr": 1e7,
         "million": 1e6, "mn": 1e6, "billion": 1e9, "bn": 1e9, "trillion": 1e12, "trn": 1e12, "tn": 1e12}
_UNIT = {"%": "%", "per cent": "%", "percent": "%", "mt": "t", "tonne": "t", "tonnes": "t", "ton": "t",
         "tons": "t", "metric tonne": "t", "metric tonnes": "t", "mmt": "mt", "lmt": "lt", "kg": "kg", "km": "km", "gw": "gw", "mw": "mw", "ha": "ha",
         "hectare": "ha", "hectares": "ha", "year": "yr", "years": "yr", "day": "day", "days": "day"}
_UNIT_SCALE = {"mt": ("t", 1e6), "lt": ("t", 1e5)}
_NUM_RE = re.compile(
    r"(?<![\w.,])(₹|rs\.?|inr|us\$|\$)?\s*(\d+(?:,\d{2,3})*(?:\.\d+)?)\s*"
    r"(k|thousand|lakhs?|crores?|cr|million|mn|billion|bn|trillion|trn|tn)?\.?\s*"
    r"(%|per\s*cent|percent|mmt|lmt|mt|metric\s*tonnes?|tonnes?|tons?|kg|km|gw|mw|ha|hectares?|years?|days?)?(?![\w])", re.I)


def _parse_num(mo: "re.Match") -> Tuple[float, str, bool]:
    cur, num, mult, unit = mo.group(1), mo.group(2), (mo.group(3) or "").lower(), (mo.group(4) or "").lower()
    v = float(num.replace(",", "")) * _MULT.get(mult, 1.0)
    u = _UNIT.get(re.sub(r"\s+", " ", unit), unit)
    if u in _UNIT_SCALE:
        u, sc = _UNIT_SCALE[u]
        v *= sc
    return v, u, bool(cur)


def option_number(o: str) -> Optional[Tuple[float, str, bool]]:
    """(value, unit, is_money) when the option is a bare quantity ('1.5 MT', '₹8 crore', '12%')."""
    s = _base(o)
    mo = _NUM_RE.search(s)
    if not mo:
        return None
    rest = _ws(s[:mo.start()] + " " + s[mo.end():])
    if len(re.findall(r"[A-Za-z]{2,}", rest)) > 2:
        return None
    return _parse_num(mo)


def _num_supported(n: Tuple[float, str, bool], text: str) -> bool:
    v, u, _money = n
    for mo in _NUM_RE.finditer(text or ""):
        tv, tu, _tm = _parse_num(mo)
        if u and tu and u != tu:
            continue
        if u and not tu:
            continue
        if abs(tv - v) <= max(1e-9, abs(v) * 0.005):
            return True
    return False


def _name_variants(o: str) -> List[str]:
    s = _base(o)
    out = [s]
    out += re.findall(r"\(([^)]{2,40})\)", s)
    main = _ws(re.sub(r"\([^)]*\)", " ", s))
    if main != s and len(main) > 4:
        out.append(main)
    if "," in main:
        out.append(main.split(",")[0].strip())
    # 'Union Environment Minister Shri Bhupender Yadav' -> 'Bhupender Yadav'
    mo = re.search(r"(?:Minister|Secretary|Governor|Chairman|Chairperson|Chief|Director|President|"
                   r"Shri|Smt|Dr|Mr|Ms)\.?\s+((?:[A-Z][\w.'-]*\s*){2,4})$", main)
    if mo:
        out.append(_ws(re.sub(r"^(?:Shri|Smt|Dr|Mr|Ms)\.?\s+", "", mo.group(1))))
    return [x for x in out if len(x.strip()) >= 2]


def option_spans(o: str, text: str) -> List[Tuple[int, int]]:
    """Where the option occurs in ``text`` (word-boundary, case-insensitive; numbers by value)."""
    if not text:
        return []
    n = option_number(o)
    if n is not None:
        spans = []
        for mo in _NUM_RE.finditer(text):
            if _num_supported(n, mo.group(0)):
                spans.append(mo.span())
        return spans
    spans = []
    for v in _name_variants(o):
        for mo in re.finditer(r"(?<!\w)" + re.escape(v) + r"(?!\w)", text, re.I):
            spans.append(mo.span())
        if spans:
            break
    return spans


_GENERIC_STEM = set("""which what when where who whom whose following recently recent news according india indian
government union central state states scheme ministry minister national question mentioned reported
announced launched under about their there these those being during other among amount quantity total
number value""".split())


def _stem_keys(q: str) -> set:
    return {w[:5] for w in re.findall(r"[a-z]{4,}", (q or "").lower()) if w not in _GENERIC_STEM}


def _near_stem(spans: List[Tuple[int, int]], text: str, q: str, window: int = 110) -> bool:
    keys = _stem_keys(q)
    if not keys:
        return bool(spans)
    for a, b in spans:
        ctx = text[max(0, a - window):b + window].lower()
        ctx_keys = {w[:5] for w in re.findall(r"[a-z]{4,}", ctx)}
        if len(keys & ctx_keys) >= min(2, len(keys)):
            return True
    return False


def standing_fact_supports(question: str, answer: str) -> bool:
    """A verified standing fact (config/current_facts.json officeholder) backs the key."""
    q, a = question or "", _base(answer)
    for f in _facts():
        if any(len(p) >= 4 and re.search(r"\b" + re.escape(p) + r"\b", q, re.I) for p in f.get("match") or []):
            if any(_norm_name(h) and _norm_name(h) in _norm_name(a) for h in _holder_names(f)):
                return True
    return False


def key_check(m: Dict[str, Any], story: str, cross: str = "") -> Tuple[str, int, str]:
    """('ok'|'rekey'|'drop', key index, reason).

    The keyed option must occur in the story; when another option is the one the
    story supports (it occurs next to the stem's subject) the key moves to it; a
    key nothing in the story supports is dropped unless a verified mapping /
    standing fact backs it; a one-liner / Static GK line that supports a
    different option is a contradiction (drop)."""
    opts = [_base(o) for o in (m.get("options") or [])]
    letter = str(m.get("correct") or "")
    idx = LETTERS.find(letter) if len(letter) == 1 else -1
    if not (0 <= idx < len(opts)):
        return "drop", idx, "key out of range"
    q = _ws(m.get("question_en"))
    backed = known_mapping_supports(q, opts[idx]) or standing_fact_supports(q, opts[idx])
    spans = {i: option_spans(o, story) for i, o in enumerate(opts)}
    sup = [i for i, s in spans.items() if s]
    new = idx
    if sup:
        near = [i for i in sup if _near_stem(spans[i], story, q)]
        cand = near or sup
        if idx in cand and len(cand) == 1:
            new = idx
        elif len(cand) == 1 and not backed:
            new = cand[0]
        elif idx in cand or backed:
            if len(cand) > 1 and not backed:
                return "drop", idx, "ambiguous: several options occur in the story"
        else:
            return "drop", idx, "ambiguous key"
    elif not backed:
        return "drop", idx, "answer not supported by the story text"
    if cross:
        cs = [i for i, o in enumerate(opts) if _near_stem(option_spans(o, cross), cross, q)]
        if cs and new not in cs:
            return "drop", new, f"key contradicts the edition's one-liner/Static GK (supports {LETTERS[cs[0]]})"
    if new != idx:
        return "rekey", new, f"key moved {LETTERS[idx]}->{LETTERS[new]}: the story supports '{opts[new]}'"
    return "ok", idx, ""


# ---- give-aways and entity types ------------------------------------------ #
GIVEAWAY_WORDS_RE = re.compile(r"\b(?:leading|first|only|highest|largest|biggest|top|best|most|record|sole|"
                               r"unique|maximum|lowest|smallest)\b", re.I)
_QUOTE_RE = re.compile(r"[‘’“”\"]|(?<!\w)'|'(?!\w)")
_ROLE_MINISTRY_RE = re.compile(r"\b(?:Foreign|External Affairs|Home|Defence|Finance|Health|Agriculture|"
                               r"Environment|Commerce|Railway|Education|Law)\s+(?:Secretary|Minister)\b", re.I)
_ASKS_MINISTRY_RE = re.compile(r"\bwhich\s+(?:union\s+)?ministry\b|\bof which ministry\b", re.I)
UN_ORGANS_RE = re.compile(r"General Assembly|Security Council|Economic and Social Council|\bECOSOC\b|"
                          r"Trusteeship Council|International Court of Justice|\bICJ\b|UN Secretariat", re.I)
UN_BODIES_RE = re.compile(r"\b(?:WHO|UNESCO|ILO|UNDP|UNICEF|FAO|WFP|UNEP|UNHCR|IFAD|UNIDO|UNCTAD|ITU|IMO|ICAO|"
                          r"WMO|WIPO|IAEA|UNFPA)\b|World Health Organi[sz]ation|Programme\b", re.I)
REGION_COUNTRY = {"zaporizhzhia": "ukraine", "kherson": "ukraine", "donetsk": "ukraine", "luhansk": "ukraine",
                  "kharkiv": "ukraine", "kyiv": "ukraine", "odesa": "ukraine", "dnipro": "ukraine",
                  "sumy": "ukraine", "ukraine": "ukraine", "gaza": "palestine", "west bank": "palestine",
                  "kursk region": "russia", "belgorod region": "russia"}
CITY_COUNTRY = {"oryol": "russia", "belgorod": "russia", "kursk": "russia", "bryansk": "russia",
                "moscow": "russia", "voronezh": "russia", "rostov": "russia", "st petersburg": "russia",
                "kyiv": "ukraine", "kharkiv": "ukraine", "odesa": "ukraine", "lviv": "ukraine",
                "tel aviv": "israel", "haifa": "israel", "tehran": "iran", "isfahan": "iran",
                "lahore": "pakistan", "karachi": "pakistan", "islamabad": "pakistan", "dhaka": "bangladesh"}
_SUBSTATE_ASK_RE = re.compile(r"\b(?:which|what)\s+(?:district|city|town|village|block|tehsil)\b", re.I)


def _tables() -> Tuple[Dict[str, str], Dict[str, str]]:
    from pipeline.mcq_builder import COUNTRIES, COUNTRY_ALIASES, INDIAN_STATES, STATE_ALIASES
    st = {k.lower(): k for k in INDIAN_STATES}
    st.update({k.lower(): v for k, v in STATE_ALIASES.items()})
    co = {k.lower(): k for k in COUNTRIES}
    co.update({k.lower(): v for k, v in COUNTRY_ALIASES.items()})
    return st, co


def option_type(o: str) -> str:
    s = _base(o)
    n = option_number(s)
    if n is not None:
        return "num:" + (n[1] or ("money" if n[2] else ""))
    st, co = _tables()
    low = s.lower().strip()
    if low in st:
        return "state"
    if low in co:
        return "country"
    if "," in s:
        tail = s.rsplit(",", 1)[1].strip().lower()
        if tail in st:
            return "place+state"
        if tail in co:
            return "place+country"
    if low in CITY_COUNTRY:
        return "city:" + CITY_COUNTRY[low]
    if UN_ORGANS_RE.search(s):
        return "un_organ"
    if UN_BODIES_RE.search(s) and re.search(r"United Nations|\bUN\b|World|International", s):
        return "un_body"
    return "text"


def type_errors(m: Dict[str, Any]) -> List[str]:
    opts = [_base(o) for o in (m.get("options") or [])]
    letter = str(m.get("correct") or "")
    idx = LETTERS.find(letter) if len(letter) == 1 else -1
    if not (0 <= idx < len(opts)) or len(opts) < 4:
        return []
    q = _ws(m.get("question_en")).lower()
    types = [option_type(o) for o in opts]
    ct, others = types[idx], [t for i, t in enumerate(types) if i != idx]
    errs: List[str] = []
    if ct.startswith("num:"):
        nums = [option_number(o) for o in opts]
        if any(t != ct for t in others):
            errs.append("option types differ: every option must be a number with the same unit")
        else:
            vals = [abs(x[0]) for x in nums if x and x[0]]
            if vals and max(vals) / min(vals) > 50:
                errs.append("option magnitudes differ by more than 50x")
    elif ct in ("state", "country") and any(t != ct for t in others):
        errs.append(f"option types differ: correct is a {ct}, a distractor is not")
    elif ct != "text" and len(set(others)) == 1 and others[0] != ct:
        errs.append(f"give-away: only the correct option is a {ct} (others: {others[0]})")
    elif ct == "text" and len(set(others)) == 1 and others[0] in ("state", "country") \
            and not _SUBSTATE_ASK_RE.search(q):
        errs.append(f"give-away: only the correct option is not a {others[0]}")
    if _SUBSTATE_ASK_RE.search(q) and any(t == "state" for t in types):
        errs.append("absurd option: a state offered for a district/city/village question")
    stem_country = next((c for r, c in REGION_COUNTRY.items() if re.search(r"\b" + re.escape(r) + r"\b", q)), "")
    if stem_country and any(t.startswith("city:") and t != "city:" + stem_country for t in types):
        errs.append(f"absurd option: a city outside {stem_country} for a question about {stem_country}")
    return errs


def giveaway_errors(m: Dict[str, Any]) -> List[str]:
    opts = [_base(o) for o in (m.get("options") or [])]
    letter = str(m.get("correct") or "")
    idx = LETTERS.find(letter) if len(letter) == 1 else -1
    if not (0 <= idx < len(opts)) or len(opts) < 4 or m.get("type") == "concept":
        return []   # concept MCQs: verified mapping with curated, same-kind distractors
    q = _ws(m.get("question_en"))
    ans, others = opts[idx], [o for i, o in enumerate(opts) if i != idx]
    errs: List[str] = []
    w = GIVEAWAY_WORDS_RE.search(ans)
    if w and not any(GIVEAWAY_WORDS_RE.search(o) for o in others):
        errs.append(f"give-away: only the correct option says '{w.group(0)}'")
    keys = _stem_keys(q)
    def hits(o: str) -> set:
        return {t[:5] for t in re.findall(r"[a-z]{4,}", o.lower()) if t not in _GENERIC_STEM} & keys
    if hits(ans) and not any(hits(o) for o in others):
        errs.append(f"give-away: the correct option repeats a stem word ({sorted(hits(ans))[0]})")
    if _QUOTE_RE.search(ans) and not any(_QUOTE_RE.search(o) for o in others):
        errs.append("give-away: only the correct option is a quotation")
    lens = sorted(len(o) for o in others)
    if len(ans) >= 1.5 * max(lens) and len(ans) - max(lens) >= 15:
        errs.append("give-away: the correct option is uniquely longer")
    if _ASKS_MINISTRY_RE.search(q) and _ROLE_MINISTRY_RE.search(q):
        errs.append("give-away: the stem's job title names the ministry")
    return errs + type_errors(m)


def option_hindi(m: Dict[str, Any]) -> List[str]:
    opts = [str(o or "") for o in (m.get("options") or [])]
    his = list(m.get("options_hi") or [])
    out = []
    for i, o in enumerate(opts):
        h = str(his[i] or "") if i < len(his) else ""
        if not h and " / " in o:
            h = o.split(" / ", 1)[1]
        out.append(h)
    return out


def hindi_errors(m: Dict[str, Any]) -> List[str]:
    """An MCQ is printed only with a Hindi stem and Hindi for every option
    (bare numbers / acronyms may stay as they are)."""
    if not _DEV_RE.search(str(m.get("question_hi") or "")):
        return ["Hindi missing: question"]
    for o, h in zip(m.get("options") or [], option_hindi(m)):
        if _DEV_RE.search(h):
            continue
        en = _base(o)
        if option_number(en) is not None or not re.search(r"[A-Za-z]", en) \
                or re.fullmatch(r"[A-Z0-9&.\- ]{2,12}", en.strip()):
            continue
        return [f"Hindi missing: option '{en[:40]}'"]
    return []


def hardening_errors(m: Dict[str, Any], evidence: str = "", cross: str = "") -> List[str]:
    """All hardening gates (no re-key): used by the fail-closed daily validator."""
    errs: List[str] = []
    if evidence or cross:
        action, new, why = key_check(m, evidence, cross)
        if action != "ok":
            errs.append(("wrong key: " if action == "rekey" else "") + why)
    return errs + giveaway_errors(m) + hindi_errors(m)


def harden_mcq(m: Dict[str, Any], story: str, cross: str = "",
               ci: Optional[Dict[str, Any]] = None) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """Weekly/monthly gate: returns (fixed copy, []) or (None, reasons).
    A key the story contradicts is moved to the supported option (explanations
    that named the old answer are cleared); everything else that fails is dropped."""
    action, new, why = key_check(m, story, cross)
    if action == "drop":
        return None, [why]
    out = dict(m)
    if action == "rekey":
        old = _base((m.get("options") or [])[LETTERS.index(str(m.get("correct")))])
        out["correct"] = LETTERS[new]
        out["rekeyed"] = why
        if old.lower() in (str(m.get("explanation_en") or "") + " " + str(m.get("explanation_pairs") or "")).lower():
            out["explanation_en"], out["explanation_hi"], out["explanation_pairs"] = "", "", []
    errs = [e for e in quality_errors(out, ci or {}, story) if not e.startswith("explanation only")]
    return (None, errs) if errs else (out, [])
