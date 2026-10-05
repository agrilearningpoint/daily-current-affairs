# -*- coding: utf-8 -*-
"""
STUDENT RELEVANCE AGENT
Main focus: competitive-exam student perspective से relevance filter करना।

Command:
> "Rate each scored event for relevance to AGTA/AFO/NABARD/FCI/ICAR/IBPS/RBI aspirants. Boost Agriculture, Banking, Government Schemes, Reports, Appointments, Awards; demote pure politics/gossip/crime/local-only items."

Work: Exam-relevance filter
Real implementation — see pipeline/ library. Quality gates enforced; empty output = failure.
"""

COMMAND = """Rate each scored event for relevance to AGTA/AFO/NABARD/FCI/ICAR/IBPS/RBI aspirants. Boost Agriculture, Banking, Government Schemes, Reports, Appointments, Awards; demote pure politics/gossip/crime/local-only items."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- boosts exam-friendly categories, demotes crime/politics/ad noise; adds student_relevance 0-100"""


class Agent:
    """STUDENT RELEVANCE AGENT — real implementation"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type
        self.context = context
        self.name = "STUDENT RELEVANCE AGENT"

    def run(self):
        import logging, re
        from pipeline.state import SCORED_DIR, data_path, read_json, write_json_atomic
        items = read_json(data_path(SCORED_DIR, self.job_id), {"items": []})["items"]
        BOOST = {"Agriculture": 25, "Banking & Finance": 25, "Government Schemes": 20, "Economy": 15,
                 "International": 12, "Science & Technology": 12, "Environment": 12, "Sports": 8, "National": 8}
        DEMOTE = re.compile(r"crime|murder|rape|accident|traffic|celebrity|bollywood|gossip|match-fixing|political party rally", re.I)
        for it in items:
            r = min(100, it.get("importance_score", 0) + BOOST.get(it.get("category", ""), 0))
            if DEMOTE.search(it.get("headline_en", "") + " " + it.get("raw_facts", "")):
                r = max(0, r - 40)
            it["student_relevance"] = r
        items.sort(key=lambda x: -x["student_relevance"])
        keep = [i for i in items if i["student_relevance"] >= 30]
        logging.info(f"[{self.name}] relevant={len(keep)}/{len(items)}")
        if len(keep) < 3:
            self.context["stage_failed"] = f"only {len(keep)} student-relevant events (min 3)"
            raise RuntimeError(self.context["stage_failed"])
        write_json_atomic(data_path(SCORED_DIR, self.job_id), {"items": keep})
        self.context["relevant"] = len(keep)
        return self.context

    def verify(self):
        return not self.context.get("stage_failed")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    ctx = {"job_id": "test_2026-10-04", "job_type": "daily", "job_date": "2026-10-04"}
    print(Agent("test_2026-10-04", "daily", ctx).run())
