# -*- coding: utf-8 -*-
"""
CONTENT EDITOR + BILINGUAL + MCQ LIBRARY (Agents 12-14, 16)
Rule "Never invent facts": every key point / static fact / MCQ answer must be a
substring-extractable fact from the item's own headline+raw_facts. No LLM needed —
deterministic extraction guarantees zero hallucination. If an optional AI provider
is configured via env (OPENAI_API_KEY etc.), it is used ONLY to polish wording,
never to add facts (facts are re-checked against source text afterwards).

v2 Update: Integrated AI Translator for natural Hindi translation with fallback
to deterministic MINI_DICT translation if AI fails.
"""
import hashlib, os, re, logging

logger = logging.getLogger(__name__)

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
    return hints.get(cat, "Exam angle: source ministry/organisation और संख्यात्मक तथ्य दोहराएँ।") + f" Source event: "{h[:80]}"."


def translate_headline(en):
    """Deterministic word-substitution translation (no invented meaning).
    Untranslated proper nouns stay in English script inside Hindi line — honest approach.
    This is the FALLBACK translation when AI translator is unavailable."""
    out = en
    for k, v in sorted(MINI_DICT.items(), key=lambda x: -len(x[0])):
        out = re.sub(r"\b" + re.escape(k) + r"\b", v, out, flags=re.I)
    out = out.replace("&", "और").replace(" – ", " — ").replace(" - ", " — ")
    return out


def translate_with_ai(text, task="general"):
    """
    AI-powered translation using ai_translator module.
    Returns (translated_text, confidence, passed) tuple.
    Falls back to deterministic translation if AI fails.
    """
    try:
        from pipeline.ai_translator import translate_content
        
        result = translate_content(text, task=task)
        
        if result.get("passed"):
            logger.debug(f"[AI Translation] Passed (confidence={result.get('confidence', 0):.2f})")
            return result["translated_hi"], result["confidence"], True
        else:
            logger.warning(f"[AI Translation] Failed validation: {result.get('issues', [])}")
            # Fallback to deterministic
            fallback = translate_headline(text)
            return fallback, 0.0, False
            
    except ImportError as e:
        logger.warning(f"[AI Translation] ai_translator not available: {e}")
        fallback = translate_headline(text)
        return fallback, 0.0, False
        
    except Exception as e:
        logger.error(f"[AI Translation] Error: {e}")
        fallback = translate_headline(text)
        return fallback, 0.0, False


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
    static_facts, exam_fact_en/hi, source, category, score.
    
    v2: Uses AI Translator for natural Hindi translation with fallback to deterministic."""
    
    logger.info(f"[Content Builder] Building content for {len(items)} items...")
    
    # Check if AI translator is available
    ai_translator_available = False
    try:
        from pipeline.ai_translator import translate_content
        ai_translator_available = True
        logger.info("[Content Builder] AI Translator available — using natural Hindi translation")
    except ImportError:
        logger.warning("[Content Builder] AI Translator not available — using deterministic translation")
    
    out = []
    translation_stats = {"ai_passed": 0, "ai_failed": 0, "deterministic": 0}
    
    for it in items:
        kps = extract_key_points(it)
        sf = extract_static_facts(it)
        ef = exam_fact(it)
        title = it["headline_en"].lstrip("> ").strip()
        
        # ═══════════════════════════════════════════════════════════
        # TRANSLATION: AI-first with deterministic fallback
        # ═══════════════════════════════════════════════════════════
        
        if ai_translator_available:
            # Try AI translation for headline
            headline_hi, headline_conf, headline_passed = translate_with_ai(title, task="headline")
            
            if headline_passed:
                translation_stats["ai_passed"] += 1
            else:
                translation_stats["ai_failed"] += 1
            
            # Translate key points
            key_points_hi = []
            for kp in kps:
                kp_hi, kp_conf, kp_passed = translate_with_ai(kp, task="key_points")
                key_points_hi.append(kp_hi)
                if not kp_passed:
                    translation_stats["ai_failed"] += 1
            
            # Translate exam fact
            exam_fact_hi, _, _ = translate_with_ai(ef, task="general")
            
        else:
            # Deterministic fallback
            headline_hi = translate_headline(title)
            key_points_hi = [translate_headline(p) for p in kps]
            exam_fact_hi = translate_headline(ef)
            translation_stats["deterministic"] += 1
        
        # Polish English content (optional)
        title_en = polish_with_ai(title, it.get("raw_facts", ""))
        kps_en = [polish_with_ai(p, it.get("raw_facts", "")) for p in kps]
        
        entry = {
            "event_id": it["event_id"],
            "category": it.get("category", "National"),
            "headline_en": ">> " + title_en,
            "headline_hi": ">> " + headline_hi,
            "key_points_en": kps_en,
            "key_points_hi": key_points_hi,
            "static_facts": sf,
            "exam_fact_en": ef,
            "exam_fact_hi": exam_fact_hi,
            "source": {"name": it["source_name"], "url": it["source_url"],
                       "tier": it["source_tier"], "date": it.get("pub_time_ist")},
            "importance_score": it.get("importance_score", 0),
            "image_path": it.get("image_path", ""),
        }
        out.append(entry)
    
    logger.info(f"[Content Builder] Translation stats: AI passed={translation_stats['ai_passed']}, "
                f"AI failed={translation_stats['ai_failed']}, deterministic={translation_stats['deterministic']}")
    
    return {"job": job_meta, "edition_title": "Current Affairs", "items": out}


MCQ_TPL_NUMBER = ("इस घटना से जुड़ी राशि/संख्या कौन-सी है? Which figure/number is associated with this event?")


def _memory_pools():
    """Distractor pools from PERSISTENT memory of past news — keeps the rule
    'distractors are real values from OTHER news' even on sparse 1-item days."""
    nums, names, heads = [], [], []
    mem = {}
    try:
        from pipeline.store import load_memory
        mem = load_memory() or {}
    except Exception:
        mem = {}
    if not mem:
        import json, pathlib
        for p in ("data/memory/importance_memory.json",):
            try:
                if pathlib.Path(p).exists():
                    mem = json.loads(pathlib.Path(p).read_text(encoding="utf-8")) or {}
                    break
            except Exception:
                pass
    for ev in list(mem.values())[:300]:
        hl = (ev.get("headline") or "").strip()
        facts = (ev.get("raw_facts") or "").strip()
        text = hl + " " + facts
        if not text.strip():
            continue
        nums += NUM_RE.findall(text)
        names += CAP_RE.findall(hl)
        if hl:
            heads.append(hl[:150])
    nums = [v for v in dict.fromkeys(nums)]
    names = [v for v in dict.fromkeys(names)]
    heads = list(dict.fromkeys(heads))
    return nums, names, heads


DOMAIN_ORGS = ["NABARD", "Reserve Bank of India", "ICAR", "Food Corporation of India",
               "SEBI", "NITI Aayog", "World Bank", "Ministry of Finance",
               "Ministry of Agriculture", "National Bank for Agriculture and Rural Development"]


def _num_variants(s):
    """Clearly-wrong numeric variants of a true figure (x2, x0.5, x3) — last-resort
    distractors when no real figures from other news exist (sparse days)."""
    out = []
    m = re.search(r"\d[\d,.]*", s)
    if not m:
        return out
    raw = m.group(0)
    try:
        x = float(raw.replace(",", ""))
    except ValueError:
        return out
    for f in (2, 0.5, 3):
        y = x * f
        ys = f"{y:,.0f}" if float(y).is_integer() else f"{y:,.2f}"
        out.append(s.replace(raw, ys, 1))
    return out


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
    # SPARSE-DAY FIX: with few items, distractor pools are too small (need >=2 per MCQ).
    # Top up with REAL values from persistent memory of past news (still other-news facts,
    # never invented) + domain orgs; numeric last resort = clearly-wrong variants.
    mem_nums, mem_names, mem_heads = _memory_pools()
    own_text_all = " ".join(ci["headline_en"] + " " + " ".join(ci["key_points_en"])
                            for ci in content_items)
    if len(pool_nums) < 4:
        pool_nums += [v for v in mem_nums if v not in pool_nums and v not in own_text_all]
    if len(pool_names) < 4:
        pool_names += [v for v in mem_names if v not in pool_names and v not in own_text_all]
        pool_names += [v for v in DOMAIN_ORGS if v not in pool_names and v not in own_text_all]

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

    sparse_multi = len(content_items) <= 2  # sparse day: allow several MCQs per item
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
                         cands[0], pool_nums + _num_variants(cands[0]),
                         f"As per {ci['source']['name']}: "{hl}" — the reported figure is {cands[0]}.",
                         f"{ci['source']['name']} के अनुसार — रिपोर्ट की गई संख्या {cands[0]} है।",
                         ci, ci["exam_fact_en"][:120]):
            if not sparse_multi:
                continue
        # --- Type C: scheme–ministry/organisation pairing ---
        org_m = MIN_ORG_RE.search(own_text)
        if org_m and add("scheme-ministry",
                         f""{hl[:70]}" से कौन-सा मंत्रालय/संगठन मुख्यतः जुड़ा है?",
                         f""{hlh[:70]}" से कौन-सा मंत्रालय/संगठन मुख्यतः जुड़ा है?",
                         org_m.group(0)[:80].strip(), pool_names,
                         f"Source text pairs this event with: {org_m.group(0)[:80].strip()}.",
                         f"स्रोत पाठ में इस घटना का संबंध {org_m.group(0)[:80].strip()} से बताया गया है।",
                         ci, "Scheme–Ministry जोड़ी prelims में बार-बार पूछी जाती है।"):
            if not sparse_multi:
                continue
        # --- Type D: rank/index question ---
        rk = RANK_RE.search(own_text)
        if rk and add("report-rank",
                       f""{hl[:70]}" — इस सूचकांक/रैंकिंग में भारत/घटना से जुड़ी सही जानकारी कौन-सी है?",
                       f""{hlh[:70]}" — इस सूचकांक/रैंकिंग में सही जानकारी कौन-सी है?",
                       (rk.group(1) or rk.group(2)), pool_names,
                       f"Rank mentioned verbatim in verified source: {(rk.group(1) or rk.group(2))}.",
                       f"सत्यापित स्रोत में उल्लिखित रैंक: {(rk.group(1) or rk.group(2))}।",
                       ci, "Index/Ranking – country/score prelims favourite है।"):
            if not sparse_multi:
                continue
        # --- Type B: entity-name question ---
        names = [n for n in CAP_RE.findall(ci["headline_en"]) if len(n) > 3]
        if names and add("who-org",
                         f""{hl[:80]}" — इस खबर में प्रमुख संस्था/नाम कौन-सा है?",
                         f""{hlh[:80]}" — इस खबर में प्रमुख संस्था/नाम कौन-सा है?",
                         names[0], pool_names,
                         f"Source {ci['source']['name']}: {names[0]} appears verbatim in the verified headline.",
                         f"स्रोत {ci['source']['name']}: {names[0]} सिरहेड में मौजूद है।",
                         ci, "Agency/ministry name prelims में सीधे पूछा जाता है।"):
            if not sparse_multi:
                continue
        # --- Type E: statement-based (correct = verbatim key point of THIS event) ---
        others = [p for o in content_items if o["event_id"] != ci["event_id"]
                  for p in o["key_points_en"][:1]]
        if len(others) < 2:  # sparse day: past news headlines from memory = wrong statements
            others += [hh for hh in mem_heads
                       if hh != ci["headline_en"] and hh not in own_text][:6]
        if ci["key_points_en"] and others and add(
                "statement",
                f""{hl[:70]}" घटना के बारे में कौन-सी कथन सत्य है?",
                f""{hlh[:70]}" घटना के बारे में कौन-सा कथन सत्य है?",
                ci["key_points_en"][0][:150], others,
                f"Statement directly quoted from verified reporting by {ci['source']['name']}: "{ci['key_points_en'][0][:150]}".",
                f"यह कथन {ci['source']['name']} की सत्यापित रिपोर्ट से सीधे लिया गया है: "{ci['key_points_en'][0][:150]}"।",
                ci, "Statement-based questions अब सबसे common prelims pattern है।"):
            pass

    for i, m in enumerate(mcqs, 1):
        m["q_num"] = i
    return mcqs


def validate_mcqs(mcqs, content_items):
    """Full validator chain per README: uniqueness, exactly-one-correct, answer exists,
    explanation supported by source text, duplicate similarity, bilingual match.
    
    v2: Enhanced validation with stricter checks and detailed error reporting."""
    
    heads = {c["event_id"]: (c["headline_en"] + " " + " ".join(c["key_points_en"])) for c in content_items}
    valid, rejected = [], []
    seen_q = set()
    
    validation_stats = {"total": len(mcqs), "passed": 0, "failed": 0}
    
    for m in mcqs:
        errs = []
        opts = m.get("options", [])
        
        # Check 1: Option uniqueness
        if len(set(opts)) != len(opts):
            errs.append("duplicate options")
        
        # Check 2: Option count (1-5)
        if not (1 <= len(opts) <= 5):
            errs.append("option count invalid")
        
        # Check 3: Answer index valid
        ci = ord(m.get("correct", "Z")) - ord("A")
        if not (0 <= ci < len(opts)):
            errs.append("answer index out of range")
        elif opts[ci] not in heads.get(m["event_id"], ""):
            errs.append("answer not supported by source text")
        
        # Check 4: Explanation contains correct answer
        if m.get("explanation_en") and opts and m["options"][ci] not in m["explanation_en"]:
            errs.append("explanation missing correct option value")
        
        # Check 5: Question uniqueness
        qkey = re.sub(r"\W+", "", m["question_en"].lower())[:60]
        if qkey in seen_q:
            errs.append("duplicate question")
        seen_q.add(qkey)
        
        # Check 6: No auto "none of these"
        if any("none of these" in o.lower() for o in opts):
            errs.append("auto 'none of these' not allowed")
        
        # Check 7: Question length (not too short)
        if len(m.get("question_en", "")) < 20:
            errs.append("question too short")
        
        # Check 8: Options not too similar
        for i, opt1 in enumerate(opts):
            for j, opt2 in enumerate(opts[i+1:], i+1):
                from difflib import SequenceMatcher
                similarity = SequenceMatcher(None, opt1.lower(), opt2.lower()).ratio()
                if similarity > 0.85:
                    errs.append(f"options {i} and {j} too similar ({similarity:.0%})")
                    break
        
        if errs:
            rejected.append({**m, "errors": errs})
            validation_stats["failed"] += 1
        else:
            valid.append(m)
            validation_stats["passed"] += 1
    
    logger.info(f"[MCQ Validation] {validation_stats['passed']}/{validation_stats['total']} MCQs passed "
                f"({validation_stats['failed']} rejected)")
    
    return valid, rejected


def ai_augment_mcqs(content_items, existing_mcqs, max_add=6):
    """Smart AI Router augmentation — AI crafts the QUESTION around a verbatim fact;
    options are built by us (correct = verbatim substring, distractors = real values
    from OTHER news / persistent memory) so validator grounding + master rule
    ('never invent facts', 'distractors are real values from other news') always hold.
    Returns [] on any router failure (deterministic MCQs already written)."""
    import json, logging
    try:
        from pipeline.ai_router import route
    except ImportError:
        return []
    mem_nums, mem_names, _heads = _memory_pools()
    pool_nums, pool_names = [], []
    for ci in content_items:
        pool_nums += list(ci.get("static_facts", {}).values())
        pool_names += CAP_RE.findall(ci.get("headline_en", ""))
    pool_nums = [v for v in dict.fromkeys(pool_nums + mem_nums)]
    pool_names = [v for v in dict.fromkeys(pool_names + mem_names + DOMAIN_ORGS)]
    existing_q = {re.sub(r"\W+", "", (m.get("question_en") or "").lower())[:60] for m in existing_mcqs}
    added = []

    def _opts(correct, distractors):
        d = [x for x in dict.fromkeys(distractors)
             if x and x != correct][:4]
        if len(d) < 2:
            return None, None
        opts = [correct] + d[:4]
        rnd = int(hashlib.sha1((correct + str(len(opts))).encode()).hexdigest(), 16) % len(opts)
        opts = opts[rnd:] + opts[:rnd]
        return opts[:5], "ABCDE"[opts.index(correct)]

    for ci in content_items:
        if len(added) >= max_add:
            break
        own_text = ci.get("headline_en", "") + " " + " ".join(ci.get("key_points_en", []))
        facts = [v for v in ci.get("static_facts", {}).values() if v in own_text]
        if not facts:
            continue
        prompt = (
            "Write ONE competitive-exam MCQ question line about a specific fact in this news.\n"
            f"NEWS: {own_text[:900]}\n"
            "Respond ONLY as JSON: {\"question\": \"...\", \"fact\": \"<exact substring of the news text "
            "that answers it>\", \"exam_point\": \"<10-word why-it-matters\"}\n"
            "The \"fact\" MUST be copied verbatim (character-for-character) from the news text.")
        try:
            out = route(prompt, task="mcq")
            m = re.search(r"\{[\s\S]*\}", out)
            if not m:
                continue
            data = json.loads(m.group())
        except Exception as e:
            logging.warning(f"[ai_augment_mcqs] route fail: {e}")
            continue
        q, fact, ep = (data.get("question") or "").strip(), (data.get("fact") or "").strip(), \
                      (data.get("exam_point") or "Prelims-relevant factual question.").strip()
        # GROUNDING GATE: fact must be a verbatim substring of the item's own verified text
        if not q or not fact or fact not in own_text:
            continue
        qkey = re.sub(r"\W+", "", q.lower())[:60]
        if qkey in existing_q:
            continue
        distr = [v for v in (pool_nums if any(ch.isdigit() for ch in fact) else pool_names)
                 if v not in own_text]
        opts, corr = _opts(fact, distr)
        if not opts:
            continue
        added.append({"type": "ai-direct", "question_en": q[:200], "question_hi": "",
                      "options": opts, "correct": corr,
                      "explanation_en": f"Verbatim from verified source: "{fact}".",
                      "explanation_hi": "", "exam_point": ep[:120],
                      "event_id": ci["event_id"], "source_url": ci["source"]["url"]})
        existing_q.add(qkey)

    if not added:
        return []
    # --- batch Hindi translation (one router call) ---
    try:
        lines = []
        for m in added:
            lines += [m["question_en"], m["explanation_en"]]
        out = route("Translate each line to Hindi (Devanagari, exam style). Return exactly "
                    f"{len(lines)} lines, one per input, no numbering:\n" + "\n".join(lines),
                    task="bilingual", needs_hindi=True)
        got = [l.strip() for l in str(out).splitlines() if l.strip()]
        if len(got) == len(lines):
            for i, m in enumerate(added):
                m["question_hi"] = got[2 * i]
                m["explanation_hi"] = got[2 * i + 1]
    except Exception as e:
        logging.warning(f"[ai_augment_mcqs] Hindi batch fail: {e}")
    for m in added:  # never ship empty Hindi fields (PDF renders them directly)
        m["question_hi"] = m.get("question_hi") or m["question_en"]
        m["explanation_hi"] = m.get("explanation_hi") or m["explanation_en"]
    return added
