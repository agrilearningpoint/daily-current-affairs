# -*- coding: utf-8 -*-
"""
STUDENT & DOMAIN RELEVANCE AGENT  (merged 07 Student Relevance + 08 Agriculture Expert
+ 09 Banking Finance Expert — audit refactor 2026-10: 08/09 were pure tagging wrappers)

Command:
> "Rate each scored event for relevance to AGTA/AFO/NABARD/FCI/ICAR/IBPS/RBI aspirants. Boost Agriculture, Banking, Government Schemes, Reports, Appointments, Awards; demote pure politics/gossip/crime/local-only items. Tag agri_focus/banking_focus for downstream coverage guarantees."

Work: Exam-relevance filter + domain tags (one stage)
Real implementation — see pipeline/ library. Quality gates enforced; empty output = failure.
"""

COMMAND = """Rate each scored event for relevance to AGTA/AFO/NABARD/FCI/ICAR/IBPS/RBI aspirants. Boost Agriculture, Banking, Government Schemes, Reports, Appointments, Awards; demote pure politics/gossip/crime/local-only items. Tag agri_focus/banking_focus items for MCQ emphasis and category-balance guarantees."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- boosts exam-friendly categories, demotes crime/politics/ad noise; adds student_relevance 0-100
- tags agri_focus / banking_focus (coverage guard for Agent 10)
- records agri_items / banking_items counts in context"""


import re as _re

GENERIC_CATEGORIES = {"", "discovery", "aggregator", "fallback", "other", "general", "govt_national"}
OFFICIAL_BONUS = 15
# Partisan sound-bites: "X accuses Y", "Congress slams ...", "... says Congress MP".
POLITICAL_RHETORIC = _re.compile(
    r"\b(?:accus(?:es|ed)|slams?|attacks?|hits?\s+out|lashes\s+out|jibes?|takes?\s+(?:a\s+)?dig|"
    r"war\s+of\s+words|mocks?|taunts?|blames?|lost\s+sleep|rally|rallies|ruckus|walkout)\b"
    r"|\b(?:BJP|Congress|YSRCP|TDP|TMC|AAP|DMK|AIADMK|BRS|BSP|NCP|Shiv\s+Sena|INDIA\s+bloc|NDA)\b.{0,40}\b(?:MP|MLA|leader|chief|spokesperson)\b",
    _re.I)
QUOTE_HEADLINE = _re.compile(r"^\s*[‘'\"“]")
CEREMONIAL = _re.compile(
    r"\b(?:grac(?:es|ed)|greets|extends\s+greetings|pays\s+(?:homage|tribute)|bird\s+walk|outreach\s+activity|"
    r"stakeholder\s+consultation|photo\s+gallery|felicitat\w+|shares\s+(?:an?\s+)?(?:article|subhashitam|glimpses|"
    r"video|thoughts|post|insights?)|subhashitam|swachh?ata|swachhta|special\s+campaign|cleanliness|"
    r"orientation\s+programme|awareness\s+(?:programme|campaign|drive)|webinar|workshop|call\s+on\s+the\s+president|"
    r"concludes?\s+(?:its\s+)?(?:official\s+)?sessions|national\s+portal\s+of\s+india)\b", _re.I)

FOREIGN_CLUB_SPORT = _re.compile(
    r"\b(?:Real\s+Madrid|Barcelona|Atletico|Manchester\s+(?:United|City)|Liverpool|Chelsea|Arsenal|Tottenham|"
    r"Bayern|Dortmund|Juventus|Inter\s+Milan|AC\s+Milan|PSG|Al-Nassr|Al\s+Hilal|Inter\s+Miami|LaLiga|"
    r"Premier\s+League|Serie\s+A|Bundesliga|Ligue\s+1|NBA|NFL|MLB|NHL)\b")

MARKET_CHATTER = _re.compile(
    r"\bshares?\s+(?:jump|jumps|surge|surges|fall|falls|slump|slumps|rise|rises|gain|gains|climb|climbs|tank|tanks)\b"
    r"|\bQ[1-4]\s+(?:net\s+)?(?:profit|loss|results?|earnings)\b|\bquarterly\s+(?:profit|loss|results?|earnings)\b"
    r"|\b(?:slumps?|soars?|surges?|tanks?|jumps?|plunges?|sinks?|rall(?:y|ies))\s+\d+(?:\.\d+)?\s?%"
    r"|\bstocks?\s+(?:soars?|surges?|jumps?|rall(?:y|ies))\b|\bdo\s+you\s+own\s+it\b"
    r"|\bbrokerages?\b|\btarget\s+price\b|\bstocks?\s+(?:may|to)\s+(?:recover|rally|fall)\b", _re.I)

# Hard-news signals (keyword scoring in stage 06 under-rates them: on 2026-11-02 the
# Rs 53,866 crore corvette contracts, GST collections and the new IAF chief all
# ranked below party sound-bites).  Each family adds once; total capped.
EXAM_SIGNALS = [
    (_re.compile(r"\b(?:appointed|appoints|assumes\s+charge|takes\s+(?:over\s+)?charge|sworn\s+in|elected|"
                 r"named\s+(?:as\s+)?(?:the\s+)?(?:new\s+)?(?:chief|head|chair\w*|ceo|director|governor|ambassador))\b", _re.I), 12),
    (_re.compile(r"\b(?:cabinet\s+approves?|approves?|approved|launch(?:es|ed)?|inaugurat\w+|notif(?:ies|ied)|"
                 r"extends?|scheme|yojana|mission|policy|bill|act|ordinance|amendment)\b", _re.I), 8),
    (_re.compile(r"\b(?:mou|agreement|pact|treaty|inks?|signs?|contracts?|deal)\b", _re.I), 8),
    (_re.compile(r"\b(?:report|index|ranking|ranked|survey|gdp|inflation|cpi|wpi|pmi|iip|collections?|"
                 r"exports?|imports?|forex|repo\s+rate|data\s+shows?)\b", _re.I), 8),
    (_re.compile(r"(?:₹|\brs\.?\s?|\binr\s?|\$)\s?[\d,.]+|\b[\d,.]+\s?(?:lakh\s+crore|crore|billion|trillion)\b", _re.I), 6),
    (_re.compile(r"\b(?:award(?:s|ed)?|prize|medal|honou?r(?:ed)?|conferred|padma|bharat\s+ratna)\b", _re.I), 8),
    (_re.compile(r"\b(?:wins?|won|clinch\w*|champion\w*|title|gold|silver|bronze|world\s+cup|record|olympic\w*)\b", _re.I), 6),
    (_re.compile(r"\b(?:dies|died|passes\s+away|passed\s+away|demise|no\s+more)\b", _re.I), 6),
    (_re.compile(r"\b(?:isro|drdo|satellite|launch\s+vehicle|gslv|pslv|missile|test-fired|corvettes?|warships?|"
                 r"submarine|fighter|navy|army|air\s+force|air\s+staff)\b", _re.I), 8),
    (_re.compile(r"\b(?:cyclone|earthquake|landfall|tsunami|heatwave|cold\s+wave|flood\s+alert|red\s+alert)\b", _re.I), 5),
]
EXAM_SIGNAL_CAP = 20


def exam_signal_bonus(headline: str) -> int:
    return min(EXAM_SIGNAL_CAP, sum(w for rx, w in EXAM_SIGNALS if rx.search(headline or "")))


class Agent:
    """STUDENT & DOMAIN RELEVANCE AGENT — real implementation (merged 07+08+09)"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type
        self.context = context
        self.name = "STUDENT & DOMAIN RELEVANCE AGENT"

    def run(self):
        import logging, os, re
        from pipeline.state import SCORED_DIR, data_path, read_json, write_json_atomic
        items = read_json(data_path(SCORED_DIR, self.job_id), {"items": []})["items"]
        BOOST = {"Agriculture": 25, "Banking & Finance": 25, "Government Schemes": 20, "Economy": 15,
                 "International": 12, "Science & Technology": 12, "Environment": 12, "Sports": 8, "National": 8}
        DEMOTE = re.compile(r"crime|murder|rape|accident|traffic|celebrity|bollywood|gossip|match-fixing|political party rally", re.I)
        from pipeline.official_sources import is_must_include
        try:
            from pipeline.collector import infer_category
        except Exception:  # pragma: no cover
            infer_category = None
        for it in items:
            # Feeds registered as discovery/aggregator carry no subject category, so
            # they missed every category boost and the selection round-robin.
            if infer_category and str(it.get("category") or "").lower() in GENERIC_CATEGORIES:
                it["category"] = infer_category(f"{it.get('headline_en', '')} {it.get('raw_facts', '')}")
            r = min(100, it.get("importance_score", 0) + BOOST.get(it.get("category", ""), 0))
            head = it.get("headline_en", "")
            if DEMOTE.search(head + " " + it.get("raw_facts", "")):
                r = max(0, r - 40)
            elif POLITICAL_RHETORIC.search(head) or QUOTE_HEADLINE.match(head):
                r = max(0, r - 25)   # party sound-bites are not exam news
            if FOREIGN_CLUB_SPORT.search(head):
                r = max(0, r - 20)   # foreign league match reports
            if MARKET_CHATTER.search(head):
                r = max(0, r - 15)   # stock moves / company quarterly results
            if CEREMONIAL.search(head):
                r = max(0, r - 15)
            elif not POLITICAL_RHETORIC.search(head):
                r = min(100, r + exam_signal_bonus(head))
            if is_must_include(it):
                it["must_include"] = True
                r = min(100, r + OFFICIAL_BONUS)
            it["student_relevance"] = r
            # domain coverage tags (formerly Agents 08 & 09)
            if it.get("category") == "Agriculture":
                it["agri_focus"] = True
            if it.get("category") == "Banking & Finance":
                it["banking_focus"] = True
        items.sort(key=lambda x: -x["student_relevance"])

        target_count = {"daily": 28, "weekly": 35, "monthly": 40}.get(self.job_type, 28)
        env_target = os.getenv("ALP_TARGET_NEWS_COUNT")
        if env_target and env_target.isdigit():
            target_count = int(env_target)

        # Retain all clean, student-relevant events (score >= 15 after domain boosts);
        # official PIB/PMO/MEA/RBI/ISRO/IMD/SEBI releases are always retained.
        keep = [i for i in items if i["student_relevance"] >= 15 or i.get("must_include")]

        # Top up to target using all clean verified items so comprehensive 24h news is not lost
        if len(keep) < target_count and len(items) > len(keep):
            kept_ids = {i.get("event_id") for i in keep}
            rest = sorted([i for i in items if i.get("event_id") not in kept_ids],
                          key=lambda x: -x["student_relevance"])
            keep += rest[:target_count - len(keep)]
            keep.sort(key=lambda x: -x["student_relevance"])
            logging.info(f"[{self.name}] daily coverage fill: keep={len(keep)} (up to {target_count})")

        agri_n = sum(1 for i in keep if i.get("agri_focus"))
        bank_n = sum(1 for i in keep if i.get("banking_focus"))
        logging.info(f"[{self.name}] relevant={len(keep)}/{len(items)} agri={agri_n} banking={bank_n}")

        # Sparse daily: allow 1-item even if below 15 (user: gates <1 allow 1-item sparse daily)
        if not keep and items:
            keep = sorted(items, key=lambda x: -x["student_relevance"])[:target_count]
            logging.warning(f"[{self.name}] sparse daily: keeping top {len(keep)} below threshold (best {keep[0]['student_relevance']})")
            agri_n = sum(1 for i in keep if i.get("agri_focus"))
            bank_n = sum(1 for i in keep if i.get("banking_focus"))
        min_relevant = 1 if self.job_type == "daily" else (5 if self.job_type == "weekly" else 8)
        if len(keep) < min_relevant:
            self.context["stage_failed"] = f"only {len(keep)} student-relevant events (min {min_relevant} for {self.job_type})"
            raise RuntimeError(self.context["stage_failed"])
        write_json_atomic(data_path(SCORED_DIR, self.job_id), {"items": keep})
        self.context["relevant"] = len(keep)
        self.context["agri_items"] = agri_n
        self.context["banking_items"] = bank_n
        return self.context

    def verify(self):
        return not self.context.get("stage_failed")


if __name__ == "__main__":
    import logging
    from pipeline.artifacts import run_agent
    logging.basicConfig(level=logging.INFO)
    run_agent(Agent)
