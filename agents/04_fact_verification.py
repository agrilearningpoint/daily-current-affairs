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
        # Smart AI Router + Jina Reader (chunked, rate-limit safe)
        try:
            from pipeline.ai_router import chunked, call_jina
            from pipeline.verify import verify_all
            HAS_ROUTER = True
        except ImportError:
            from pipeline.verify import verify_all
            HAS_ROUTER = False
        raw = read_json(data_path(RAW_DIR, self.job_id), {"items": []})["items"]
        # budget guard: tier-1 first, cap at 120
        items = sorted(raw, key=lambda x: (x.get("source_tier") != "tier1",
                                           -(len(x.get("headline_en") or ""))))[:120]
        if HAS_ROUTER and len(items) > 5:
            # Chunked verification: 5 items/chunk, 3s delay — avoids 429
            def _verify_batch(batch):
                v, d = verify_all(batch)
                return v
            verified_chunks = chunked(items, _verify_batch, chunk_size=5, delay=3)
            # Flatten and dedup by event_id
            seen = set()
            verified = []
            for v in verified_chunks:
                if v.get("event_id") not in seen:
                    seen.add(v["event_id"])
                    verified.append(v)
            dropped = [i for i in items if i["event_id"] not in seen]
        else:
            verified, dropped = verify_all(items)
        logging.info(f"[{self.name}] verified={len(verified)} dropped={len(dropped)} (AI Router chunked={HAS_ROUTER})")
        # --- Jina Reader rescue pass: direct HTTP fail (JS-heavy/403) but page may resolve via r.jina.ai ---
        if HAS_ROUTER and len(verified) < (12 if self.job_type == "daily" else 20) and dropped:
            rescued = 0
            for rec in list(dropped)[:8]:  # cap 8 rescues to respect Jina 20 RPM
                url = rec.get("source_url") or rec.get("url")
                if not url or not str(url).startswith("http"):
                    continue
                try:
                    page = call_jina(url)
                except Exception as e:
                    logging.warning(f"[{self.name}] jina rescue fail {url[:60]}: {e}")
                    continue
                if not page or len(page) < 400:
                    continue
                # keyword check: >=50% of headline tokens must appear in page text
                import re as _re
                page_low = page.lower()
                tokens = [t for t in _re.findall(r"[a-zA-Z\u0900-\u097F]{4,}",
                          (rec.get("headline_en") or rec.get("claim") or "").lower())]
                if tokens and sum(1 for t in tokens if t in page_low) / len(tokens) >= 0.5:
                    rec.update({"verified": True, "confidence": max(rec.get("confidence", 0), 0.7),
                                "source_type": rec.get("source_type", "") + "+jina"})
                    verified.append(rec)
                    dropped.remove(rec)
                    rescued += 1
            if rescued:
                logging.info(f"[{self.name}] Jina rescue: +{rescued} verified (total {len(verified)})")
        # P0 FIX: variable quantity — daily sparse allowed (user: gates <1 allow 1-item sparse daily)
        # Previously 5 was too strict for stale windows / degraded CORE → 0 verified failure
        min_verified = 1 if self.job_type == "daily" else (5 if self.job_type == "weekly" else 8)
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
