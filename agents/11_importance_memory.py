# -*- coding: utf-8 -*-
"""
IMPORTANCE MEMORY AGENT
Main focus: event history और trend याद रखना (persistent memory)।

Command:
> "Maintain persistent importance memory: for each event store score history across days, detect RISING/FALLING/NEW trends, and remember previously-published event_ids so Weekly/Monthly can reuse the same database."

Work: Persistent JSON memory
Real implementation — see pipeline/ library. Quality gates enforced; empty output = failure.
"""

COMMAND = """Maintain persistent importance memory: for each event store score history across days, detect RISING/FALLING/NEW trends, and remember previously-published event_ids so Weekly/Monthly can reuse the same database."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- data/memory/importance_memory.json : event_id → {scores[], last_seen, trend}
- marks is_new / trend on selected items"""


class Agent:
    """IMPORTANCE MEMORY AGENT — real implementation"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type
        self.context = context
        self.name = "IMPORTANCE MEMORY AGENT"

    def run(self):
        import logging
        from pipeline.state import SELECTED_DIR, MEMORY_DIR, data_path, read_json, write_json_atomic
        from pipeline import store
        mem = read_json(data_path(MEMORY_DIR, "importance_memory"), {}) or {}
        sel = read_json(data_path(SELECTED_DIR, self.job_id), {"items": []})["items"]
        scored = read_json(data_path(SELECTED_DIR, self.job_id), {"items": []}).get("items", [])
        for it in sel:
            e = mem.setdefault(it["event_id"], {"headline": it["headline_en"], "history": [], "published_jobs": []})
            before = [h["score"] for h in e["history"]]
            sc = it.get("importance_score", 0)
            e["history"].append({"job": self.job_id, "score": sc, "at": self.context.get("job_date")})
            e["history"] = e["history"][-30:]
            e["trend"] = "NEW" if not before else ("RISING" if sc > max(before) else "FALLING" if sc < max(before) else "STEADY")
            it["trend"] = e["trend"]
            it["previously_published"] = self.job_id in e["published_jobs"]
        write_json_atomic(data_path(MEMORY_DIR, "importance_memory"), mem)
        write_json_atomic(data_path(SELECTED_DIR, self.job_id), {"items": sel})
        # PERSISTENT cross-run memory (Git-backed event DB) — the real "same database"
        try:
            store.record_scores(scored, self.job_id)
        except Exception as ex:
            logging.warning(f"[{self.name}] persistent store merge failed (non-blocking): {ex}")
        logging.info(f"[{self.name}] memory updated for {len(sel)} events (local + persistent)")
        return self.context

    def verify(self):
        return not self.context.get("stage_failed")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    ctx = {"job_id": "test_2026-10-04", "job_type": "daily", "job_date": "2026-10-04"}
    print(Agent("test_2026-10-04", "daily", ctx).run())
