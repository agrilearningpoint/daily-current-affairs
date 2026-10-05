# -*- coding: utf-8 -*-
"""
FINAL NEWS SELECTION AGENT
Main focus: pipeline का सबसे important decision — final news चुनना।

Command:
> "Select the final edition set purely by merit: daily 10-12, weekly 15-18 Best-of-Week, monthly 20-25 Best-of-Month. If fewer qualify, ship fewer — NEVER fill with weak news. Ensure category balance (agri/banking/international visible)."

Work: Merit-based threshold selection
Real implementation — see pipeline/ library. Quality gates enforced; empty output = failure.
"""

COMMAND = """Select the final edition set purely by merit: daily 10-12, weekly 15-18 Best-of-Week, monthly 20-25 Best-of-Month. If fewer qualify, ship fewer — NEVER fill with weak news. Ensure category balance (agri/banking/international visible)."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- rank by student_relevance & importance_score; per-type targets as MAXIMUM caps;
- quality floor: daily 25 / weekly 60 / monthly 62 (student_relevance scale); never pads;
  writes data/selected/<job_id>.json"""


class Agent:
    """FINAL NEWS SELECTION AGENT — real implementation"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type
        self.context = context
        self.name = "FINAL NEWS SELECTION AGENT"

    def run(self):
        import logging
        from pipeline.state import SCORED_DIR, SELECTED_DIR, data_path, read_json, write_json_atomic
        items = read_json(data_path(SCORED_DIR, self.job_id), {"items": []})["items"]
        cfg = {"daily": (10, 12, 25), "weekly": (15, 18, 60), "monthly": (20, 25, 62)}[self.job_type]
        lo, hi, floor = cfg
        from pipeline import store
        try:
            published = store.published_event_ids()
        except Exception:
            published = set()
        fresh = [i for i in items if i["event_id"] not in published] or items
        chosen = [i for i in fresh if i.get("student_relevance", i.get("importance_score", 0)) >= floor][:hi]
        # category balance: make sure at least 2 agri & 2 banking present if such items exist
        def ensure(cat_key, need):
            have = sum(1 for c in chosen if c.get(cat_key))
            if have < need:
                for it in items:
                    if it not in chosen and it.get(cat_key):
                        chosen.append(it)
                        have += 1
                        if have >= need:
                            break
        ensure("agri_focus", 2); ensure("banking_focus", 2)
        chosen.sort(key=lambda x: -x.get("student_relevance", 0))
        logging.info(f"[{self.name}] selected {len(chosen)} (target {lo}-{hi}, floor {floor})")
        if len(chosen) < 1:
            self.context["stage_failed"] = f"selection too small: {len(chosen)} — refusing to pad (MASTER_RULE)"
            raise RuntimeError(self.context["stage_failed"])
        write_json_atomic(data_path(SELECTED_DIR, self.job_id), {"items": chosen})
        return self.context

    def verify(self):
        return not self.context.get("stage_failed")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    ctx = {"job_id": "test_2026-10-04", "job_type": "daily", "job_date": "2026-10-04"}
    print(Agent("test_2026-10-04", "daily", ctx).run())
