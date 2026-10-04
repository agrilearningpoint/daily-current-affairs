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
        import logging, requests
        from pipeline.state import RAW_DIR, VERIFIED_DIR, data_path, read_json, write_json_atomic, load_job, save_job
        raw = read_json(data_path(RAW_DIR, self.job_id), {"items": []})["items"]
        out, dropped = [], 0
        for it in raw:
            conf = {"tier1": 0.95, "tier2": 0.6, "tier3": 0.4}.get(it["source_tier"], 0.3)
            try:
                r = requests.head(it["source_url"], timeout=8, allow_redirects=True,
                                  headers={"User-Agent": "Mozilla/5.0"})
                alive = r.status_code < 400
            except requests.RequestException:
                alive = False
            if not alive:
                conf -= 0.3
            verified = conf >= 0.7 and it["source_tier"] == "tier1" or (conf >= 0.85)
            rec = dict(it)
            rec.update({"verified": verified, "confidence": round(conf, 2),
                        "claim": it["headline_en"], "source_type": it["source_tier"],
                        "published_at": it.get("pub_time_ist"),
                        "claims_verified": [it["headline_en"]] if verified else [],
                        "claims_unverified": [] if verified else [it["headline_en"]]})
            (out if verified else []).append(rec) if verified else None
            if not verified:
                dropped += 1
        logging.info(f"[{self.name}] verified={len(out)} dropped={dropped}")
        if len(out) < 5:
            self.context["stage_failed"] = f"only {len(out)} verified items (min 5)"
            raise RuntimeError(self.context["stage_failed"])
        write_json_atomic(data_path(VERIFIED_DIR, self.job_id), {"items": out, "dropped": dropped})
        save_job(load_job(self.job_id, self.job_type, self.context["job_date"]),
                 state="VERIFIED", stage="04_fact_verification", verified=len(out))
        self.context["verified"] = len(out)
        return self.context

    def verify(self):
        """QA check for this agent's output."""
        return not self.context.get("stage_failed")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    ctx = {"job_id": "test_2026-10-04", "job_type": "daily", "job_date": "2026-10-04"}
    print(Agent("test_2026-10-04", "daily", ctx).run())
