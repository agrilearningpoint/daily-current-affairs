# -*- coding: utf-8 -*-
"""
WEEKLY EDITOR AGENT
Main focus: सप्ताह की सर्वश्रेष्ठ news का fresh Best-of-Week edition बनाना (Sunday)।

Command:
> "On weekly jobs, re-select from the whole week's importance memory + this run's scored pool: 'Is poore saptah me sabse mahatvapurna kya tha?' 15-18 items, NOT a combine of daily PDFs. Runs BEFORE content/PDF so selection flows into the edition."

Work: Best-of-Week re-selection
Real implementation — see pipeline/ library. Quality gates enforced; empty output = failure.
"""

COMMAND = """On weekly jobs, re-select from the whole week's importance memory + this run's scored pool: 'Is poore saptah me sabse mahatvapurna kya tha?' 15-18 items, NOT a combine of daily PDFs. Runs BEFORE content/PDF so selection flows into the edition."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- reads data/memory/importance_memory.json + week window
- overrides data/selected/<job_id>.json with fresh weekly ranking"""


class Agent:
    """WEEKLY EDITOR AGENT — real implementation"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type
        self.context = context
        self.name = "WEEKLY EDITOR AGENT"

    def run(self):
        import logging
        if self.job_type != "weekly":
            logging.info(f"[{self.name}] skipped (job_type={self.job_type})")
            return self.context
        from pipeline.state import SELECTED_DIR, SCORED_DIR, MEMORY_DIR, data_path, read_json, write_json_atomic
        from pipeline import store
        mem = read_json(data_path(MEMORY_DIR, "importance_memory"), {}) or {}
        pmem = store.load_memory()          # PERSISTENT (Git-backed) cross-run memory
        items = read_json(data_path(SCORED_DIR, self.job_id), {"items": []})["items"]
        # same-database principle: boost events whose memory shows high scores earlier in the week
        for it in items:
            e = mem.get(it["event_id"], {})
            hist = [h["score"] for h in e.get("history", [])]
            p = pmem.get(it["event_id"], {})
            hist += [s["score"] for s in p.get("scores", [])]   # history from previous daily runs
            it["trend"] = p.get("trend", "")
            it["weekly_score"] = max([it.get("student_relevance", 0)] + hist)
        items.sort(key=lambda x: -x["weekly_score"])
        chosen = [i for i in items if i["weekly_score"] >= 60][:18]
        if len(chosen) < 5:
            self.context["stage_failed"] = f"Weekly selection too small ({len(chosen)}) — refusing weak filler"
            raise RuntimeError(self.context["stage_failed"])
        write_json_atomic(data_path(SELECTED_DIR, self.job_id), {"items": chosen})
        logging.info(f"[{self.name}] Best-of-Week: {len(chosen)} items")
        self.context["weekly_selected"] = len(chosen)
        return self.context

    def verify(self):
        return not self.context.get("stage_failed")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    ctx = {"job_id": "test_2026-10-04", "job_type": "daily", "job_date": "2026-10-04"}
    print(Agent("test_2026-10-04", "daily", ctx).run())
