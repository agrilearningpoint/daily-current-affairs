# -*- coding: utf-8 -*-
"""
FACT VERIFICATION AGENT
Main focus: हर news को primary source से verify करना; unverified कभी आगे न जाएँ।

Command:
> "Verify every news item against its primary/official source. Check the source URL resolves, record source tier, published time and confidence. Tier-2/3 items must be traceable to a primary source or are marked unverified and dropped."

Work: Primary-source gate
Real implementation: pipeline/ library (state machine + quality gates). Empty stage output = FAILURE.
"""

COMMAND = """Verify every news item against its primary/official source. Check the source URL resolves, record source tier, published time and confidence. Tier-2/3 items must be traceable to a primary source or are marked unverified and dropped."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- HTTP-resolve each source_url (confidence by status + tier)
- Emits per-item verification record {event_id, claim, source_url, source_type, published_at, verified, confidence}
- Unverifiable Tier-2/3 items are DROPPED (never published)"""


class Agent:
    """FACT VERIFICATION AGENT — real implementation"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type
        self.context = context
        self.name = "FACT VERIFICATION AGENT"

    def run(self):
        import logging
        from pipeline.state import RAW_DIR, VERIFIED_DIR, data_path, read_json, write_json_atomic
        from pipeline.verify import verify_all
        raw = read_json(data_path(RAW_DIR, self.job_id), {"items": []})["items"]
        # budget guard: tier-1 first, cap at 120 so verification fits runner time
        items = sorted(raw, key=lambda x: (x.get("source_tier") != "tier1",
                                           -(len(x.get("headline_en") or ""))))[:120]
        verified, dropped = verify_all(items)
        logging.info(f"[{self.name}] verified={len(verified)} dropped={len(dropped)}")
        # P0 FIX: dynamic threshold — daily needs >=5 verified to ensure quality (was 1 too permissive)
        min_verified = 5 if self.job_type == "daily" else (8 if self.job_type == "weekly" else 10)
        if len(verified) < min_verified:
            self.context["stage_failed"] = f"only {len(verified)} content-verified items (min {min_verified} for {self.job_type})"
            raise RuntimeError(self.context["stage_failed"])
        write_json_atomic(data_path(VERIFIED_DIR, self.job_id), {"items": verified, "dropped": len(dropped)})
        return self.context

    def verify(self):
        """QA check for this agent's output."""
        return not self.context.get("stage_failed")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    ctx = {"job_id": "test_2026-10-04", "job_type": "daily", "job_date": "2026-10-04"}
    print(Agent("test_2026-10-04", "daily", ctx).run())
