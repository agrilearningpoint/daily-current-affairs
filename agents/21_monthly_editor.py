# -*- coding: utf-8 -*-
"""
MONTHLY EDITOR AGENT
Main focus: महीने की सर्वश्रेष्ठ news का fresh Best-of-Month edition बनाना (1st)।

Command:
> "On monthly jobs, re-select across the month using importance memory history: 'Is poore mahine me sabse mahatvapurna kya raha?' 20-25 items, fresh editorial decision, never a combine of dailies."

Work: Best-of-Month re-selection
Real implementation — see pipeline/ library. Quality gates enforced; empty output = failure.
"""

COMMAND = """On monthly jobs, re-select across the month using importance memory history: 'Is poore mahine me sabse mahatvapurna kya raha?' 20-25 items, fresh editorial decision, never a combine of dailies."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- memory-driven month ranking; overrides selected set for monthly job"""


class Agent:
    """MONTHLY EDITOR AGENT — real implementation"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type
        self.context = context
        self.name = "MONTHLY EDITOR AGENT"

    def run(self):
        import logging
        if self.job_type != "monthly":
            logging.info(f"[{self.name}] skipped (job_type={self.job_type})")
            return self.context
        from pipeline.state import SELECTED_DIR, SCORED_DIR, MEMORY_DIR, data_path, read_json, write_json_atomic
        mem = read_json(data_path(MEMORY_DIR, "importance_memory"), {}) or {}
        items = read_json(data_path(SCORED_DIR, self.job_id), {"items": []})["items"]
        for it in items:
            e = mem.get(it["event_id"], {})
            hist = [h["score"] for h in e.get("history", [])]
            it["monthly_score"] = round((max([it.get("student_relevance", 0)] + hist) * 0.7
                                         + (sum(hist)/len(hist) if hist else 0) * 0.3))
        items.sort(key=lambda x: -x["monthly_score"])
        chosen = [i for i in items if i["monthly_score"] >= 62][:25]
        if len(chosen) < 5:
            self.context["stage_failed"] = f"Monthly selection too small ({len(chosen)})"
            raise RuntimeError(self.context["stage_failed"])
        write_json_atomic(data_path(SELECTED_DIR, self.job_id), {"items": chosen})
        logging.info(f"[{self.name}] Best-of-Month: {len(chosen)} items")
        self.context["monthly_selected"] = len(chosen)
        return self.context

    def verify(self):
        return not self.context.get("stage_failed")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    ctx = {"job_id": "test_2026-10-04", "job_type": "daily", "job_date": "2026-10-04"}
    print(Agent("test_2026-10-04", "daily", ctx).run())
