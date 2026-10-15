# -*- coding: utf-8 -*-
"""FINAL NEWS SELECTION AGENT v2 — 25-30 items for 15+ pages"""
import logging

COMMAND = "Select top 25-30 news items with category diversity."
MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity."


class Agent:
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type
        self.context = context
        self.name = "FINAL NEWS SELECTION AGENT v2"

    def run(self):
        from pipeline.artifacts import normalize_category
        from pipeline.state import SCORED_DIR, SELECTED_DIR, data_path, read_json, write_json_atomic
        scored = read_json(data_path(SCORED_DIR, self.job_id), {"items": []})["items"]
        for item in scored:
            item["category"] = normalize_category(item.get("category", ""))
        if not scored:
            self.context["stage_failed"] = "no scored items"
            raise RuntimeError(self.context["stage_failed"])
        target = {"daily": 28, "weekly": 35, "monthly": 40}.get(self.job_type, 28)
        scored.sort(key=lambda x: x.get("importance_score", x.get("student_relevance", 0)), reverse=True)
        selected = self._diverse_selection(scored, target)
        logging.info(f"[{self.name}] selected {len(selected)} items (target={target})")
        cats = {}
        for item in selected:
            cat = item.get("category", "Other")
            cats[cat] = cats.get(cat, 0) + 1
        for cat, cnt in sorted(cats.items(), key=lambda x: -x[1]):
            logging.info(f"  {cat}: {cnt}")
        if len(selected) < 5:
            self.context["stage_failed"] = f"only {len(selected)} selected (min 5)"
            raise RuntimeError(self.context["stage_failed"])
        write_json_atomic(data_path(SELECTED_DIR, self.job_id), {"items": selected})
        self.context["selected_count"] = len(selected)
        return self.context

    def _diverse_selection(self, scored, target):
        selected = []
        by_category = {}
        for item in scored:
            cat = item.get("category", "Other")
            by_category.setdefault(cat, []).append(item)
        priority_cats = ["Agriculture", "Banking & Finance", "Economy", "Government Schemes",
                         "National", "International", "Science & Technology", "Environment"]
        cat_idx = {cat: 0 for cat in priority_cats}
        while len(selected) < target:
            added = False
            for cat in priority_cats:
                if len(selected) >= target:
                    break
                items = by_category.get(cat, [])
                idx = cat_idx[cat]
                if idx < len(items):
                    item = items[idx]
                    if item not in selected:
                        selected.append(item)
                        cat_idx[cat] = idx + 1
                        added = True
            if not added:
                for item in scored:
                    if len(selected) >= target:
                        break
                    if item not in selected:
                        selected.append(item)
                break
        if len(selected) < target:
            for item in scored:
                if len(selected) >= target:
                    break
                if item not in selected:
                    selected.append(item)
        return selected[:target]

    def verify(self):
        return not self.context.get("stage_failed")


# =============================================================================
# STANDALONE ENTRYPOINT (for pipeline integration)
# =============================================================================
if __name__ == "__main__":
    import os
    import sys
    from pathlib import Path

    # Ensure repo root importable
    _REPO = Path(__file__).resolve().parent.parent
    if str(_REPO) not in sys.path:
        sys.path.insert(0, str(_REPO))

    # Basic logging
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )

    # --- Load job context from env (set by main.py) ---
    _job_id = os.getenv("ALP_JOB_ID") or os.getenv("JOB_ID") or ""
    _job_type = os.getenv("ALP_JOB_TYPE") or os.getenv("JOB_TYPE") or "daily"
    _job_date = os.getenv("ALP_JOB_DATE") or ""

    if not _job_date and _job_id and "_" in _job_id:
        _job_date = _job_id.split("_", 1)[1]

    if not _job_date:
        from datetime import datetime, timezone
        _job_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if not _job_id:
        _job_id = f"{_job_type}_{_job_date}"

    print(f"[10_final_news_selection] job={_job_id} type={_job_type} date={_job_date}")

    # --- Run agent ---
    _context = {}
    _exit_code = 0

    try:
        _agent = Agent(job_id=_job_id, job_type=_job_type, context=_context)
        _agent.run()
        print(f"[10] OK — selected_count={_context.get('selected_count', '?')}")
    except SystemExit:
        raise
    except Exception as exc:
        print(f"[10] FAILED: {exc}", file=sys.stderr)
        _exit_code = 1

    sys.exit(_exit_code)