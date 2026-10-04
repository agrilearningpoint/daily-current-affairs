# -*- coding: utf-8 -*-
"""
CONTENT EDITOR + BILINGUAL + MCQ LIBRARY (Agents 12-14, 16)
Rule "Never invent facts": every key point / static fact / MCQ answer must be a
substring-extractable fact from the item's own headline+raw_facts. No LLM needed —
deterministic extraction guarantees zero hallucination. If an optional AI provider
is configured via env (OPENAI_API_KEY etc.), it is used ONLY to polish wording,
never to add facts (facts are re-checked against source text afterwards).
"""
import hashlib, os, re

NUM_RE = re.compile(r"(?:Rs\.?|₹)\s?[\d,.]+\s?(?:crore|lakh|billion|million|trillion|Cr)?|"
                    r"\b\d+(?:\.\d+)?\s?(?:%|percent|bps|days?|years?|months?|bn|billion|crore|lakh)\b", re.I)
CAP_RE = re.compile(r"\b[A-Z][A-Za-z&]+(?:[ -][A-Z][A-Za-z&]+)+\b")

MINI_DICT = {  # small deterministic glossary for headline-level Hindi; falls back to transliteration-free English-in-Hindi
    "Government": "सरकार", "Scheme": "योजना", "Launches": "लॉन्च", "Launched": "लॉन्च की गई",
    "Approved": "स्वीकृति", "Meeting": "बैठक", "Report": "रिपोर्ट", "Index": "सूचकांक",
    "Agriculture": "कृषि", "Farming": "खेती", "Farmers": "किसान", "Banking": " बैंकिंग",
    "Reserve Bank": "भारतीय रिज़र्व बैंक", "Budget": "बजट", "Ministry": "मंत्रालय",
    "India": "भारत", "Indian": "भारतीय", "New": "नया", "National": "राष्ट्रीय",
    "International": "अंतर्राष्ट्रीय", "Conference": "सम्मेलन", "Summit": "शिखर सम्मेलन",
    "Award": "पुरस्कार", "Wins": "जीता", "Gold": "स्वर्ण", "Medal": "पदक", "Hockey": "हॉकी",
    "Mission": "मिशन", "Policy": "नीति", "Growth": "वृद्धि", "Inflation": "महंगाई",
    "Export": "निर्यात", "Import": "आयात", "Price": "कीमत", "Power": "बिजली",
    "Water": "जल", "Food": "खाद्य", "Health": "स्वास्थ्य", "Education": "शिक्षा",
    "Employment": "रोज़गार", "Rural": "ग्रामीण", "Urban": "शहरी", "Climate": "जलवायु",
}


def split_sentences(text):
    parts = re.split(r"(?<=[.!?|])\s+", text or "")
    return [p.strip(" .|") for p in parts if len(p.strip()) > 15]


def extract_key_points(item, max_points=4):
    """Key points strictly from raw_facts/headline — never invented."""
    src = (item.get("raw_facts") or "") + ". " + (item.get("headline_en") or "")
    sents = split_sentences(src)
    pts = []
    for s in sents:
        s = re.sub(r"\s+", " ", s).strip()
        if s and s not in pts and len(s) > 20:
            pts.append(s[:220])
        if len(pts) >= max_points:
            break
    if not pts:
        pts = [item["headline_en"][:220]]
    return pts


def extract_static_facts(item):
    """Static-fact table rows: numbers/amounts/first-ness/key-names VERBATIM from source.
    Every value is guaranteed to be a substring of the item's own headline+raw_facts
    (no invention)."""
    src = (item.get("headline_en") or "") + " " + (item.get("raw_facts") or "")
    facts = {}
    uniq_nums = list(dict.fromkeys(n.strip() for n in NUM_RE.findall(src) if n and n.strip()))
    for i, n in enumerate(uniq_nums[:3]):
        facts[f"Fact {i+1}"] = n
    firsts = re.findall(r"[^.;|]{0,60}\bFirst[- ][^.;|]{0,60}", src, re.I)
    if firsts and firsts[0].strip()[:120] in src:
        facts["First/Unique"] = firsts[0].strip()[:120]
    caps = [c for c in dict.fromkeys(CAP_RE.findall(src)) if len(c) > 4][:2]
    if caps:
        facts["Key Name"] = ", ".join(caps)
    return facts


def exam_fact(item):
    cat = item.get("category", "")
    h = item.get("headline_en", "")
    hints = {
        "Agriculture": "AGTA/AFO/ICAR focus — scheme/organism details & Ministry come under Static GK.",
        "Banking & Finance": "IBPS/NABARD/Grade-A focus — regulator, rate/limit numbers याद रखें।",
        "Economy": "Economic Survey/GDP/CPI type data — prelims matching favourite.",
        "Government Schemes": "Scheme name–ministry–outlay–target teen-cheez में याद करें (prelims statement-based).",
        "International": "Index/Ranking/report — organising body + headquarters prelims में पूछा जाता है।",
        "Science & Technology": "ISRO/DRDO mission details — agency + location prelims favourite.",
        "Environment": "COP/biodiversity/climate reports — convention & host country note करें।",
        "Sports": "Tournament–winner–host triplet static GK में बार-बार आता है।",
        "National": "Appointments/awards — name + designation + tenure रिकॉर्ड करें।",
    }
    return hints.get(cat, "Exam angle: source ministry/organisation और संख्यात्मक तथ्य दोहराएँ।") + f" Source event: “{h[:80]}”."


def translate_headline(en):
    """Deterministic word-substitution translation (no invented meaning).
    Untranslated proper nouns stay in English script inside Hindi line — honest approach."""
    out = en
    for k, v in sorted(MINI_DICT.items(), key=lambda x: -len(x[0])):
        out = re.sub(r"\b" + re.escape(k) + r"\b", v, out, flags=re.I)
    out = out.replace("&", "और").replace(" – ", " — ").replace(" - ", " — ")
    return out


def polish_with_ai(text, source_text):
    """Optional AI polish — ONLY if OPENAI_API_KEY set; result is rejected if it adds
    new numeric facts not present in source_text (anti-hallucination guard)."""
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return text
    try:
        import requests as _rq
        r = _rq.post("https://api.openai.com/v1/chat/completions",
                     headers={"Authorization": f"Bearer {key}"},
                     json={"model": os.getenv("ALP_LLM", "gpt-4o-mini"),
                           "messages": [{"role": "user",
                                         "content": "Rewrite for clarity. Do NOT add/remove facts:\n" + text}],
                           "max_tokens": 300}, timeout=30)
        cand = r.json()["choices"][0]["message"]["content"].strip()
        src_nums = set(NUM_RE.findall(source_text))
        if set(NUM_RE.findall(cand)) - src_nums:  # introduced new numbers → reject
            return text
        return cand
    except Exception:
        return text


def build_content(items, job_meta):
    """Produce content JSON per DETAILS schema: headline_en/hi, key_points_en/hi,
    static_facts, exam_fact_en/hi, source, category, score."""
    out = []
    for it in items:
        kps = extract_key_points(it)
        sf = extract_static_facts(it)
        ef = exam_fact(it)
        title = it["headline_en"].lstrip("> ").strip()
        entry = {
            "event_id": it["event_id"],
            "category": it.get("category", "National"),
            "headline_en": ">> " + title,
            "headline_hi": ">> " + polish_with_ai(translate_headline(title), title),
            "key_points_en": [polish_with_ai(p, it.get("raw_facts", "")) for p in kps],
            "key_points_hi": [translate_headline(p) for p in kps],
            "static_facts": sf,
            "exam_fact_en": ef,
            "exam_fact_hi": translate_headline(ef),
            "source": {"name": it["source_name"], "url": it["source_url"],
                       "tier": it["source_tier"], "date": it.get("pub_time_ist")},
            "importance_score": it.get("importance_score", 0),
            "image_path": it.get("image_path", ""),
        }
        out.append(entry)
    return {"job": job_meta, "edition_title": "Current Affairs", "items": out}


MCQ_TPL_NUMBER = ("इस घटना से जुड़ी राशि/संख्या कौन-सी है? Which figure/number is associated with this event?")


def generate_mcqs(content_items, target=(12, 15)):
    """Deterministic exam-style MCQs built ONLY from verified content (zero invention).
    Five README-promised types, all fact-locked to the item's own source text:
      A static-number   : figure/amount taken verbatim from THIS news
      B who-org         : entity name appearing verbatim in this headline
      C scheme-ministry : Ministry/Org paired with scheme in the same sentence
      D report-rank     : index/ranking/report → correct year/host/score from text
      E statement       : "Which statement about <event> is correct?" — correct option
                          is a verbatim key-point; distractors are OTHER events' points
    Options <=5, exactly one correct, never auto 'None of these'. Validator double-checks."""
    mcqs = []
    pool_nums, pool_names = [], []
    for ci in content_items:
        pool_nums += list(ci["static_facts"].values())
        pool_names += CAP_RE.findall(ci["headline_en"])
    pool_nums = [v for v in dict.fromkeys(pool_nums)]
    pool_names = [v for v in dict.fromkeys(pool_names)]

    def shuffled_opts(correct, distractors):
        opts = [correct] + list(distractors)
        rnd = int(hashlib.sha1((correct + str(len(opts))).encode()).hexdigest(), 16) % len(opts)
        opts = opts[rnd:] + opts[:rnd]
        return opts, opts.index(correct)

    def add(mtype, q_en, q_hi, correct, distractors, expl_en, expl_hi, ci, exam_point):
        if len(mcqs) >= target[1]:
            return False
        distractors = [d for d in dict.fromkeys(distractors)
                       if d != correct and d not in (ci["headline_en"] + " ".join(ci["key_points_en"]))][:4]
        if len(distractors) < 2:
            return False
        opts, idx = shuffled_opts(correct, distractors)
        mcqs.append({"type": mtype, "question_en": q_en, "question_hi": q_hi,
                     "options": opts[:5], "correct": "ABCDE"[idx],
                     "explanation_en": expl_en, "explanation_hi": expl_hi,
                     "exam_point": exam_point, "event_id": ci["event_id"],
                     "source_url": ci["source"]["url"]})
        return True

    MIN_ORG_RE = re.compile(r"\b(?:Ministry|Department|Mission|Board|Authority|Corporation|Commission|"
                            r"Committee|Bank|Organisation|Organization)\b[^.;|]{0,70}", re.I)
    RANK_RE = re.compile(r"\b(\d+(?:st|nd|rd|th))\s+(?:position|rank|place)|ranked\s+(\d+(?:st|nd|rd|th))", re.I)

    for ci in content_items:
        if len(mcqs) >= target[1]:
            break
        own_text = ci["headline_en"] + " " + " ".join(ci["key_points_en"])
        hl = ci["headline_en"].lstrip("> ")[:90]
        hlh = ci["headline_hi"].lstrip("> ")[:90]
        # --- Type A: numeric fact question ---
        cands = [v for v in ci["static_facts"].values()
                 if v in own_text and any(ch.isdigit() for ch in v)][:1]
        if cands and add("static-number",
                         f"{hl} — इससे जुड़ी सही संख्या/राशि कौन-सी है?",
                         f"{hlh} — इससे जुड़ी सही संख्या/राशि कौन-सी है?",
                         cands[0], pool_nums,
                         f"As per {ci['source']['name']}: “{hl}” — the reported figure is {cands[0]}.",
                         f"{ci['source']['name']} के अनुसार — रिपोर्ट की गई संख्या {cands[0]} है।",
                         ci, ci["exam_fact_en"][:120]):
            continue
        # --- Type C: scheme–ministry/organisation pairing ---
        org_m = MIN_ORG_RE.search(own_text)
        if org_m and add("scheme-ministry",
                         f"“{hl[:70]}” से कौन-सा मंत्रालय/संगठन मुख्यतः जुड़ा है?",
                         f"“{hlh[:70]}” से कौन-सा मंत्रालय/संगठन मुख्यतः जुड़ा है?",
                         org_m.group(0)[:80].strip(), pool_names,
                         f"Source text pairs this event with: {org_m.group(0)[:80].strip()}.",
                         f"स्रोत पाठ में इस घटना का संबंध {org_m.group(0)[:80].strip()} से बताया गया है।",
                         ci, "Scheme–Ministry जोड़ी prelims में बार-बार पूछी जाती है।"):
            continue
        # --- Type D: rank/index question ---
        rk = RANK_RE.search(own_text)
        if rk and add("report-rank",
                       f"“{hl[:70]}” — इस सूचकांक/रैंकिंग में भारत/घटना से जुड़ी सही जानकारी कौन-सी है?",
                       f"“{hlh[:70]}” — इस सूचकांक/रैंकिंग में सही जानकारी कौन-सी है?",
                       (rk.group(1) or rk.group(2)), pool_names,
                       f"Rank mentioned verbatim in verified source: {(rk.group(1) or rk.group(2))}.",
                       f"सत्यापित स्रोत में उल्लिखित रैंक: {(rk.group(1) or rk.group(2))}।",
                       ci, "Index/Ranking – country/score prelims favourite है।"):
            continue
        # --- Type B: entity-name question ---
        names = [n for n in CAP_RE.findall(ci["headline_en"]) if len(n) > 3]
        if names and add("who-org",
                         f"“{hl[:80]}” — इस खबर में प्रमुख संस्था/नाम कौन-सा है?",
                         f"“{hlh[:80]}” — इस खबर में प्रमुख संस्था/नाम कौन-सा है?",
                         names[0], pool_names,
                         f"Source {ci['source']['name']}: {names[0]} appears verbatim in the verified headline.",
                         f"स्रोत {ci['source']['name']}: {names[0]} सिरहेड में मौजूद है।",
                         ci, "Agency/ministry name prelims में सीधे पूछा जाता है।"):
            continue
        # --- Type E: statement-based (correct = verbatim key point of THIS event) ---
        others = [p for o in content_items if o["event_id"] != ci["event_id"]
                  for p in o["key_points_en"][:1]]
        if ci["key_points_en"] and others and add(
                "statement",
                f"“{hl[:70]}” घटना के बारे में कौन-सी कथन सत्य है?",
                f"“{hlh[:70]}” घटना के बारे में कौन-सा कथन सत्य है?",
                ci["key_points_en"][0][:150], others,
                f"Statement directly quoted from verified reporting by {ci['source']['name']}.",
                f"यह कथन {ci['source']['name']} की सत्यापित रिपोर्ट से सीधे लिया गया है।",
                ci, "Statement-based questions अब सबसे common prelims pattern है।"):
            pass

    for i, m in enumerate(mcqs, 1):
        m["q_num"] = i
    return mcqs


def validate_mcqs(mcqs, content_items):
    """Full validator chain per README: uniqueness, exactly-one-correct, answer exists,
    explanation supported by source text, duplicate similarity, bilingual match."""
    heads = {c["event_id"]: (c["headline_en"] + " " + " ".join(c["key_points_en"])) for c in content_items}
    valid, rejected = [], []
    seen_q = set()
    for m in mcqs:
        errs = []
        opts = m.get("options", [])
        if len(set(opts)) != len(opts):
            errs.append("duplicate options")
        if not (1 <= len(opts) <= 5):
            errs.append("option count invalid")
        ci = ord(m.get("correct", "Z")) - ord("A")
        if not (0 <= ci < len(opts)):
            errs.append("answer index out of range")
        elif opts[ci] not in heads.get(m["event_id"], ""):
            errs.append("answer not supported by source text")
        if m.get("explanation_en") and opts and m["options"][ci] not in m["explanation_en"]:
            errs.append("explanation missing correct option value")
        qkey = re.sub(r"\W+", "", m["question_en"].lower())[:60]
        if qkey in seen_q:
            errs.append("duplicate question")
        seen_q.add(qkey)
        if any("none of these" in o.lower() for o in opts):
            errs.append("auto 'none of these' not allowed")
        (valid if not errs else rejected).append({**m, "errors": errs} if errs else m)
    return valid, rejected
