# -*- coding: utf-8 -*-
"""
DEDUP + IMPORTANCE SCORING LIBRARY (Agents 05, 06)
- Dedup: token-shingle Jaccard similarity > 0.85 => same event; keep strongest source (Tier-1 wins).
- Scoring: multi-factor 0-100 exactly as README:
  national_impact 20 | govt_policy 15 | economy 15 | agriculture 15 | banking 10
  exam_relevance 10 | future_importance 5 | static_fact_value 5 | uniqueness 5
  Final = weighted sum scaled by source reliability (SOURCE_SCORE/100).
"""
import re
try:
    from config.sources import PRIORITY_MAP, LEVEL_NAMES
except Exception:
    PRIORITY_MAP = {0:100,1:95,2:90,3:85,4:80,5:60}
    LEVEL_NAMES = {0:'CORE',1:'AGRI',2:'FINANCE',3:'OTHER',4:'DISCOVERY',5:'FALLBACK'}

# ADOPTED from Pious1918/scrape deduplication — acronym expansion improves banking dedupe
ACRONYM_MAP = {
    'rbi': 'reserve bank india', 'isro': 'indian space research organisation',
    'drdo': 'defence research development organisation', 'sc': 'supreme court',
    'hc': 'high court', 'pm': 'prime minister', 'cm': 'chief minister',
    'mpc': 'monetary policy committee', 'upsc': 'union public service commission',
    'psc': 'public service commission', 'gdp': 'gross domestic product',
    'cpi': 'consumer price index', 'wpi': 'wholesale price index',
    'sebi': 'securities exchange board india', 'pib': 'press information bureau',
    'nabard': 'national bank agriculture rural development', 'fci': 'food corporation india',
    'icar': 'indian council agricultural research', 'iari': 'indian agricultural research institute',
}
def _expand_acronyms(text):
    low = text.lower()
    for ac, exp in ACRONYM_MAP.items():
        import re
        low = re.sub(rf'\b{ac}\b', exp, low)
    return low


TIER_RANK = {"tier1": 3, "tier2": 2, "tier3": 1}
# Level rank for production hierarchy — lower level = higher authority (0 CORE = 6)
LEVEL_RANK = {0: 6, 1: 5, 2: 4, 3: 3, 4: 2, 5: 1}

STOP = set("""the a an and or of in on for to is are was were with by at from as it its this that
new india indian news""".split())


def tokens(text):
    return [t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if t not in STOP and len(t) > 2]


def shingles(text, n=3):
    ts = tokens(text)
    if len(ts) < n:
        return set(tuple(ts)) if ts else set()
    return set(tuple(ts[i:i + n]) for i in range(len(ts) - n + 1))


def _bigrams(text):
    return set(zip(tokens(text), tokens(text)[1:]))


def similarity(a, b):
    """Event similarity = max( headline Jaccard-bigram , full-text shingle Jaccard ).
    Headline comparison catches reworded duplicates; body shingles catch copy-paste."""
    ha, hb = _bigrams(a["headline_en"]), _bigrams(b["headline_en"])
    head_sim = (len(ha & hb) / len(ha | hb)) if ha and hb else 0.0
    sa, sb = shingles(a["headline_en"] + " " + a.get("raw_facts", "")), shingles(b["headline_en"] + " " + b.get("raw_facts", ""))
    body_sim = (len(sa & sb) / len(sa | sb)) if sa and sb else 0.0
    return max(head_sim, body_sim)


def deduplicate(items, threshold=0.85):
    """Greedy clustering: merge items with similarity >= threshold, keep authoritative source."""
    clusters = []
    for it in items:
        placed = False
        for cl in clusters:
            if similarity(it, cl["representative"]) >= threshold:
                cl["members"].append(it)
                # representative = strongest source (level rank first, then tier rank, then priority_score)
                it_rank = LEVEL_RANK.get(it.get("source_level", 5), 0) * 10 + TIER_RANK.get(it["source_tier"], 0)
                rep_rank = LEVEL_RANK.get(cl["representative"].get("source_level", 5), 0) * 10 + TIER_RANK.get(cl["representative"]["source_tier"], 0)
                if it_rank > rep_rank or (it_rank == rep_rank and it.get("priority_score", 0) > cl["representative"].get("priority_score", 0)):
                    cl["representative"] = it
                placed = True
                break
        if not placed:
            clusters.append({"representative": it, "members": [it]})
    out = []
    for cl in clusters:
        rep = dict(cl["representative"])
        rep["duplicate_count"] = len(cl["members"])
        rep["merged_urls"] = [m["source_url"] for m in cl["members"]]
        # union raw facts (never invent — only combine what sources said)
        extra = [m["headline_en"] for m in cl["members"] if m is not rep and m["headline_en"] != rep["headline_en"]]
        if extra:
            rep["raw_facts"] = (rep.get("raw_facts") or "") + " | Also reported: " + "; ".join(extra[:3])
        out.append(rep)
    return out


FACTOR_KEYWORDS = {
    "national_impact": ["india", "nation", "country", "all states", "pan-india", "parliament", "cabinet",
                        "president", "prime minister", "supreme court", "election", "constitution", "republic"],
    "govt_policy": ["scheme", "policy", "y ojana", "yojana", "mission", "gazette", "notification", "ordinance",
                    "approved", "cabinet", "launched", "amendment", "guidelines", "circular"],
    "economy": ["gdp", "inflation", "budget", "trade", "export", "economic", "growth", "forex", "gst",
                "fiscal", "current account", "investment", "fdi", "survey"],
    "agriculture": ["farm", "agri", "crop", "msp", "icar", "horticulture", "fisheries", "dairy", "monsoon",
                    "food processing", "apeda", "nhb", "irrigation", "seed", "soil", "livestock", "shrimp"],
    "banking": ["rbi", "bank", "nabard", "sebi", "upi", "insurance", "monetary", "repo", "credit",
                "loan", "nbfc", "payment", "irdai", "pfrda"],
    "exam_relevance": ["report", "index", "ranking", "award", "appointment", "mou", "summit", "conference",
                       "committee", "un ", "world bank", "imf", "wto", "fao", "who", "unesco", "day",
                       "established", "headquartered", "launched"],
    "future_importance": ["2027", "2028", "2030", "target", "roadmap", "phase", "expansion", "next",
                          "deadline", "mission", "long-term"],
    "static_fact_value": ["rs", "crore", "lakh crore", "percent", "%", "billion", "bn", "rank", "first",
                     "highest", "largest", "number", "total", "outlay", "beneficiary"],
}

FACTOR_WEIGHTS = {"national_impact": 20, "govt_policy": 15, "economy": 15, "agriculture": 15,
                  "banking": 10, "exam_relevance": 10, "future_importance": 5,
                  "static_fact_value": 5, "uniqueness": 5}


def score_item(item, source_score_map=None):
    """Return dict of factor scores (0..weight each) + total 0-100 (source-reliability weighted)."""
    text = " " + ((item.get("headline_en") or "") + " " + (item.get("raw_facts") or "") + " " + (item.get("category") or "")).lower() + " "
    factors = {}
    for fac, kws in FACTOR_KEYWORDS.items():
        hits = sum(1 for k in kws if k in text)
        w = FACTOR_WEIGHTS[fac]
        factors[fac] = min(w, round(w * min(hits, 4) / 4))  # 0→w graded by keyword hits
    # category boosts (explicit mapping so agri/banking exams get domain weight)
    cat = item.get("category", "")
    if cat == "Agriculture":
        factors["agriculture"] = FACTOR_WEIGHTS["agriculture"]
    if cat == "Banking & Finance":
        factors["banking"] = FACTOR_WEIGHTS["banking"]
    factors["uniqueness"] = FACTOR_WEIGHTS["uniqueness"] if item.get("duplicate_count", 1) <= 2 else 2
    raw_total = sum(factors.values())  # max 100
    # source reliability multiplier — LEVEL-based (0-5) with fallback to tier map
    level = item.get("source_level")
    if level is not None:
        rel = PRIORITY_MAP.get(level, 60) / 100.0
        src_type = LEVEL_NAMES.get(level, "Aggregator")
    else:
        src_type = {"tier1": "Official Primary", "tier2": "Reuters/Trusted News", "tier3": "Aggregator"}.get(
            item.get("source_tier"), "Aggregator")
        rel = (source_score_map or {"Official Primary": 100, "Reuters/Trusted News": 90, "Aggregator": 60}).get(src_type, 60) / 100.0
    total = round(raw_total * rel)
    return {"factors": factors, "raw_total": raw_total, "source_type": src_type,
            "source_reliability": round(rel * 100), "importance_score": min(100, total)}


def score_all(items):
    out = []
    for it in items:
        s = score_item(it)
        it2 = dict(it)
        it2.update(s)
        out.append(it2)
    out.sort(key=lambda x: -x["importance_score"])
    return out