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



# ─────────────────────────────────────────────────────────────────
# EVENT-LEVEL DEDUP — 3-level pipeline (production)
# Variable quantity, fixed quality architecture as per user spec
# Level 1: Exact duplicate (canonical URL / normalized headline)
# Level 2: Near duplicate (shingle >0.85)
# Level 3: Semantic/event duplicate (fingerprint: title + entities + numbers + date + category + event-type)
# Same event != Same topic — contrastive verbs prevent false merges
# ─────────────────────────────────────────────────────────────────
import re as _re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

# Contrastive action verbs — same topic but different events must NOT merge
CONTRAST_GROUPS = [
    {"cut","decrease","reduce","hike","increase","raise","maintain","hold","keep","unchanged"},
    {"announce","launch","guideline","implementation","guidelines","release","notification"},
    {"approve","clear","reject","defer","withdraw"},
    {"appoint","elect","resign","retire"},
    {"award","honour","confer"},
]
def _contrastive(head_a, head_b):
    la = set(_re.findall(r"[a-z]+", head_a.lower()))
    lb = set(_re.findall(r"[a-z]+", head_b.lower()))
    for grp in CONTRAST_GROUPS:
        a_has = bool(la & grp)
        b_has = bool(lb & grp)
        # If both have contrastive verbs from same group but different specific verbs, don't merge
        if a_has and b_has:
            # Check if they share exact same verb from group -> ok to merge, else contrastive
            shared = (la & grp) & (lb & grp)
            if not shared:
                # One has "cut" other has "maintain" etc — different events
                # Only flag if verbs are antonyms within group
                # Simple: if groups contain both a_has and b_has but no shared verb, treat as contrastive
                # But need finer: "cut" vs "hike" are opposite, "cut" vs "reduce" are similar
                # For now, treat as contrastive if headlines contain different contrastive verbs
                if len((la & grp) ^ (lb & grp)) > 0 and len(la & grp)==1 and len(lb & grp)==1:
                    return True
    # Additional direct antonym check
    antonyms = [("cut","maintain"),("increase","decrease"),("raise","cut"),("approve","reject"),("announce","guideline")]
    for w1,w2 in antonyms:
        if (w1 in la and w2 in lb) or (w2 in la and w1 in lb):
            return True
    return False

def _normalize_url(url):
    try:
        u = urlparse((url or "").strip())
        host = (u.netloc or "").lower().replace("www.","")
        path = _re.sub(r"/+$", "", u.path or "")
        # Remove tracking params
        qs = parse_qs(u.query)
        drop = {"utm_source","utm_medium","utm_campaign","utm_term","utm_content","fbclid","gclid","igshid","mc_cid","mc_eid","ref","src"}
        clean_qs = {k:v for k,v in qs.items() if k.lower() not in drop}
        query = urlencode(clean_qs, doseq=True)
        return urlunparse(("", host, path, "", query, "")).lower()
    except Exception:
        return (url or "").lower().strip()

def _normalize_headline(text):
    text = (text or "").lower()
    text = _re.sub(r"[^a-z0-9]+", " ", text)
    text = _re.sub(r"\s+", " ", text).strip()
    # Expand acronyms for better matching
    for ac, exp in ACRONYM_MAP.items():
        text = _re.sub(rf"\b{ac}\b", exp, text)
    return text

def _entities(text):
    # Use existing _entities + also extract locations/orgs lowercased
    ents = set()
    for m in _re.finditer(r"\b[A-Z][A-Za-z&'-]{2,}(?:[ -][A-Z][A-Za-z&'-]{2,})+\b", text or ""):
        ents.add(m.group(0).lower())
    for m in _re.finditer(r"\b[A-Z]{3,}\b", text or ""):
        ents.add(m.group(0).lower())
    return ents

def _numbers(text):
    out=set()
    s=text or ""
    for m in _re.finditer(r"(?:₹|Rs\.?|INR)\s?([\d][\d,.]*)", s, _re.I):
        out.add(m.group(1))
    for m in _re.finditer(r"\b(\d+(?:[.,]\d+)?)\s?(?:%|percent|crore|lakh|billion|million|bps)\b", s, _re.I):
        out.add(m.group(1))
    for m in _re.finditer(r"\b\d{2,}\b", s):
        out.add(m.group(0))
    return out

def _numbers_set(text):
    return _numbers(text)

def _event_fingerprint(item):
    # Fingerprint components for Level 3 semantic clustering
    headline = item.get("headline_en","") or ""
    raw = item.get("raw_facts","") or ""
    return {
        "norm_head": _normalize_headline(headline),
        "entities": _entities(headline + " " + raw),
        "numbers": _numbers_set(headline + " " + raw),
        "cat": item.get("category",""),
        "pub": item.get("pub_time_ist"),
        "url_norm": _normalize_url(item.get("source_url","")),
    }

def _date_proximity(a_pub, b_pub):
    if not a_pub or not b_pub:
        return 0.5  # neutral if missing
    try:
        from dateutil import parser as _dtp
        da = _dtp.parse(a_pub)
        db = _dtp.parse(b_pub)
        delta_h = abs((da - db).total_seconds())/3600
        if delta_h <= 24: return 1.0
        if delta_h <= 48: return 0.6
        if delta_h <= 72: return 0.3
        return 0.0
    except Exception:
        return 0.5

def _semantic_similarity(a, b, fp_a=None, fp_b=None):
    # Combined fingerprint similarity for Level 3
    if fp_a is None: fp_a = _event_fingerprint(a)
    if fp_b is None: fp_b = _event_fingerprint(b)
    # Headline Jaccard (bigrams)
    ha, hb = _bigrams(a["headline_en"]), _bigrams(b["headline_en"])
    head_sim = (len(ha & hb) / len(ha | hb)) if ha and hb else 0.0
    # Entity overlap
    ea, eb = fp_a["entities"], fp_b["entities"]
    ent_sim = (len(ea & eb) / len(ea | eb)) if ea and eb else (0.5 if not ea and not eb else 0.0)
    # Number overlap — crucial for ₹X crore events
    na, nb = fp_a["numbers"], fp_b["numbers"]
    if na and nb:
        num_sim = (len(na & nb) / len(na | nb))
    elif not na and not nb:
        num_sim = 0.5
    else:
        num_sim = 0.0  # one has numbers other not — penalize
    # Category match
    cat_sim = 1.0 if fp_a["cat"] and fp_a["cat"]==fp_b["cat"] else 0.0
    # Date proximity
    date_sim = _date_proximity(fp_a["pub"], fp_b["pub"])
    # URL domain match bonus
    dom_a = fp_a["url_norm"].split("/")[0] if fp_a["url_norm"] else ""
    dom_b = fp_b["url_norm"].split("/")[0] if fp_b["url_norm"] else ""
    dom_sim = 1.0 if dom_a and dom_a==dom_b else 0.0
    # Weighted combine (as per spec: title + entities + numbers + date + category + domain)
    # Title 35%, entities 20%, numbers 20%, category 10%, date 10%, domain 5%
    combined = head_sim*0.22 + ent_sim*0.25 + num_sim*0.18 + cat_sim*0.15 + date_sim*0.15 + dom_sim*0.05
    return combined, head_sim, ent_sim, num_sim

def deduplicate(items, threshold=0.85):
    """Event-level deduplication — 3-level pipeline:
    L1 exact (canonical URL / normalized headline) → immediate merge
    L2 near duplicate (shingle >=0.85) → candidate
    L3 semantic/event duplicate (fingerprint combined >=0.68) → cluster, unless contrastive verbs
    Produces ONE canonical event per cluster with supporting_sources[].
    """
    if not items:
        return []
    # Precompute fingerprints
    fps = [_event_fingerprint(it) for it in items]
    clusters = []  # each: {"representative": item, "members": [items], "fps": [fps]}
    for idx, it in enumerate(items):
        fp = fps[idx]
        placed = False
        url_norm = fp["url_norm"]
        norm_head = fp["norm_head"]
        for cl in clusters:
            rep = cl["representative"]
            rep_fp = cl["fps"][0]  # rep fingerprint
            # L1: exact duplicate
            if url_norm and rep_fp["url_norm"] and url_norm == rep_fp["url_norm"]:
                cl["members"].append(it)
                cl["fps"].append(fp)
                # Keep strongest as representative
                it_rank = LEVEL_RANK.get(it.get("source_level", 5), 0) * 10 + TIER_RANK.get(it["source_tier"], 0)
                rep_rank = LEVEL_RANK.get(rep.get("source_level", 5), 0) * 10 + TIER_RANK.get(rep["source_tier"], 0)
                if it_rank > rep_rank or (it_rank == rep_rank and it.get("priority_score",0) > rep.get("priority_score",0)):
                    cl["representative"] = it
                    cl["fps"][0] = fp
                placed = True
                break
            if norm_head and rep_fp["norm_head"] and norm_head == rep_fp["norm_head"]:
                cl["members"].append(it)
                cl["fps"].append(fp)
                it_rank = LEVEL_RANK.get(it.get("source_level", 5), 0) * 10 + TIER_RANK.get(it["source_tier"], 0)
                rep_rank = LEVEL_RANK.get(rep.get("source_level", 5), 0) * 10 + TIER_RANK.get(rep["source_tier"], 0)
                if it_rank > rep_rank or (it_rank == rep_rank and it.get("priority_score",0) > rep.get("priority_score",0)):
                    cl["representative"] = it
                    cl["fps"][0] = fp
                placed = True
                break
            # Contrastive check — same topic but different event → never merge
            if _contrastive(it.get("headline_en",""), rep.get("headline_en","")):
                continue
            # L2: near duplicate via original similarity
            if similarity(it, rep) >= 0.65:  # L2 near-duplicate lowered from 0.85 for reworded headlines
                cl["members"].append(it)
                cl["fps"].append(fp)
                it_rank = LEVEL_RANK.get(it.get("source_level", 5), 0) * 10 + TIER_RANK.get(it["source_tier"], 0)
                rep_rank = LEVEL_RANK.get(rep.get("source_level", 5), 0) * 10 + TIER_RANK.get(rep["source_tier"], 0)
                if it_rank > rep_rank or (it_rank == rep_rank and it.get("priority_score",0) > rep.get("priority_score",0)):
                    cl["representative"] = it
                    cl["fps"][0] = fp
                placed = True
                break
            # L3: semantic/event duplicate
            combined, head_sim, ent_sim, num_sim = _semantic_similarity(it, rep, fp, rep_fp)
            # Require high combined and at least moderate headline or entity overlap
            if combined >= 0.60 and (head_sim >= 0.30 or ent_sim >= 0.35) and not _contrastive(it.get("headline_en",""), rep.get("headline_en","")):
                # Additional guard: if numbers exist and zero overlap, likely different amount → don't merge
                if fp["numbers"] and rep_fp["numbers"] and len(fp["numbers"] & rep_fp["numbers"])==0:
                    # Different ₹X crore amounts → different events (e.g., ₹X vs ₹Y scheme)
                    continue
                cl["members"].append(it)
                cl["fps"].append(fp)
                it_rank = LEVEL_RANK.get(it.get("source_level", 5), 0) * 10 + TIER_RANK.get(it["source_tier"], 0)
                rep_rank = LEVEL_RANK.get(rep.get("source_level", 5), 0) * 10 + TIER_RANK.get(rep["source_tier"], 0)
                if it_rank > rep_rank or (it_rank == rep_rank and it.get("priority_score",0) > rep.get("priority_score",0)):
                    cl["representative"] = it
                    cl["fps"][0] = fp
                placed = True
                break
        if not placed:
            clusters.append({"representative": it, "members": [it], "fps": [fp]})
    out = []
    for cl in clusters:
        rep = dict(cl["representative"])
        members = cl["members"]
        rep["duplicate_count"] = len(members)
        rep["merged_urls"] = [m["source_url"] for m in members]
        rep["supporting_sources"] = [m["source_name"] for m in members if m["source_name"] != rep["source_name"]]
        rep["supporting_source_levels"] = [m.get("source_level",5) for m in members if m["source_name"] != rep["source_name"]]
        rep["duplicate_articles"] = [{"headline_en": m["headline_en"], "source_name": m["source_name"], "source_url": m["source_url"], "source_level": m.get("source_level",5)} for m in members]
        rep["source_count"] = len(members)
        rep["canonical_source"] = rep["source_name"]
        # Verification strength boost: if multiple primary sources report same event, increase confidence
        primary_count = sum(1 for m in members if m.get("source_level",5) <=2)
        if primary_count >=2:
            rep["verification_boost"] = min(10, primary_count*2)  # up to +10
        else:
            rep["verification_boost"] = 0
        # Union raw facts (never invent)
        extra = [m["headline_en"] for m in members if m is not rep and m["headline_en"] != rep["headline_en"]]
        if extra:
            rep["raw_facts"] = (rep.get("raw_facts") or "") + " | Also reported: " + "; ".join(extra[:3])
        # Store cluster size for diversity scoring
        rep["event_cluster_size"] = len(members)
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
    # Event verification boost: +2 per additional primary source reporting same event (max +10)
    boost = item.get("verification_boost", 0)
    if boost:
        total = min(100, total + boost)
    # Cluster size bonus: events reported by many sources are more important nationally (max +5)
    cluster_bonus = min(5, max(0, item.get("event_cluster_size",1)-1))
    total = min(100, total + cluster_bonus)
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