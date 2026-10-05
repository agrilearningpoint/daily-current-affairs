# -*- coding: utf-8 -*-
"""
NEWS COLLECTION AGENT
Main focus: ज्यादा से ज्यादा relevant raw news collect करना, लेकिन final selection नहीं करना।

Command:
> "Collect current-affairs news from reliable and preferably primary/official sources. Prioritize Agriculture, Banking, Government, Economy, National, International, Science, Environment, Awards, Appointments, Reports and Sports. Capture headline, publication time, source, URL, category and raw facts. Collect broadly; do not decide final importance at this stage."

Work: Tier-1 primary first, then Tier-2 discovery; QUALITY GATE: <1 items = stage failure (sparse live).
Merged (audit refactor 2026-10): Agent 02 Scheduler — collection window is computed here.
Real implementation: pipeline/ library (state machine + quality gates). Empty stage output = FAILURE.
"""

COMMAND = """Collect current-affairs news from reliable and preferably primary/official sources. Prioritize Agriculture, Banking, Government, Economy, National, International, Science, Environment, Awards, Appointments, Reports and Sports. Capture headline, publication time, source, URL, category and raw facts. Collect broadly; do not decide final importance at this stage."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- RSS-first adapters + HTML fallback for all TIER_1_SOURCES (~60) + Tier-2 discovery via Google News site-search
- Writes data/raw/<job_id>.json; raises on empty collection (no silent pass-through)
- Production 6-level hierarchy: CORE daily compulsory (P0), AGRI/FINANCE/GOVT with frequency daily/weekly, DISCOVERY(4) & FALLBACK(5)
- Fallback chain: RSS → Native website → Official search → GNews site-search → Playwright"""


class Agent:
    """NEWS COLLECTION AGENT — real implementation"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type
        self.context = context
        self.name = "NEWS COLLECTION AGENT"

    def run(self):
        import logging
        from pipeline.collector import collect_all, collect_window, in_window
        from pipeline.state import RAW_DIR, data_path, write_json_atomic
        items, errors = collect_all(max_items=140, job_type=self.job_type)
        start, end = collect_window(self.job_type, self.context["job_date"])
        # scheduler context (merged from former Agent 02)
        self.context["window_start"] = start.isoformat()
        self.context["window_end"] = end.isoformat()
        fresh = [i for i in items if in_window(i, start, end)]
        # CORE coverage gate (P0 #6)
        try:
            from pipeline.collector import core_coverage_report
            cov = core_coverage_report(fresh)
            logging.info(f"[{self.name}] CORE coverage: {cov['covered']}/{cov['attempted']} ({cov['coverage_ratio']:.0%}) missing={cov['missing'][:3]}")
            # Log per-source counts for daily debugging
            for name, cnt in cov['core_names'].items():
                status = "✓" if cnt>0 else "✗"
                logging.info(f"  CORE {status} {name}: {cnt} items")
            if cov['coverage_ratio'] < 0.3:
                logging.warning(f"[{self.name}] LOW CORE COVERAGE {cov['coverage_ratio']:.0%} — mostly discovery/fallback, not CORE primary")
        except Exception as e:
            logging.warning(f"CORE coverage check failed: {e}")
        logging.info(f"[{self.name}] collected={len(items)} in-window={len(fresh)} errors={len(errors)}")
        if len(fresh) < 1:
            self.context["stage_failed"] = f"news collection too low: {len(fresh)} items (min 1)"
            raise RuntimeError(self.context["stage_failed"])
        write_json_atomic(data_path(RAW_DIR, self.job_id), {"items": fresh, "errors": errors})
        return self.context

    def verify(self):
        """QA check for this agent's output."""
        return not self.context.get("stage_failed")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    ctx = {"job_id": "test_2026-10-04", "job_type": "daily", "job_date": "2026-10-04"}
    print(Agent("test_2026-10-04", "daily", ctx).run())
