# -*- coding: utf-8 -*-
"""
FACT VERIFICATION AGENT v3 — Integrated with Claim Verifier
Uses new pipeline.claim_verifier for claim-level verification
with fallback to old pipeline.verify if new module fails.
"""
import logging

COMMAND = "Verify every news item using claim-level verification with structured evidence."
MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts."


class Agent:
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type
        self.context = context
        self.name = "FACT VERIFICATION AGENT v3"

    def run(self):
        from pipeline.state import RAW_DIR, VERIFIED_DIR, data_path, read_json, write_json_atomic
        
        raw = read_json(data_path(RAW_DIR, self.job_id), {"items": []})["items"]
        
        # Budget guard: tier-1 first, cap at 120
        items = sorted(raw, key=lambda x: (x.get("source_tier") != "tier1",
                     -(len(x.get("headline_en") or ""))))[:120]
        
        logging.info(f"[{self.name}] Processing {len(items)} items...")
        
        # Try new claim_verifier first
        verified = []
        dropped = []
        verification_method = "unknown"
        
        try:
            from pipeline.claim_verifier import verify_claims
            
            logging.info(f"[{self.name}] Using claim_verifier_v2...")
            verified_items = verify_claims(items, chunk_size=5, delay=3)
            
            verified = [v for v in verified_items if v.get("verified")]
            dropped = [v for v in verified_items if not v.get("verified")]
            verification_method = "claim_verifier_v2"
            
            logging.info(f"[{self.name}] Claim-level: {len(verified)} verified, {len(dropped)} dropped")
            
            # Log sample for debugging
            for item in verified[:3]:
                status = item.get("verification_status", "UNKNOWN")
                confidence = item.get("overall_confidence", 0)
                claims_v = item.get("claims_verified", 0)
                claims_t = item.get("claims_total", 0)
                logging.info(f"  ✓ {item.get('headline_en', '')[:50]}... [{status}] {claims_v}/{claims_t} claims (conf={confidence:.2f})")
            
        except ImportError as e:
            logging.warning(f"[{self.name}] claim_verifier not available: {e}")
            logging.info(f"[{self.name}] Falling back to pipeline.verify...")
            
            try:
                from pipeline.verify import verify_all
                verified, dropped = verify_all(items)
                verification_method = "pipeline_verify_fallback"
                logging.info(f"[{self.name}] Fallback: {len(verified)} verified, {len(dropped)} dropped")
            except Exception as e2:
                logging.error(f"[{self.name}] Both verification methods failed: {e2}")
                self.context["stage_failed"] = f"All verification methods failed: {e2}"
                raise RuntimeError(self.context["stage_failed"])
        
        except Exception as e:
            logging.error(f"[{self.name}] claim_verifier failed: {e}")
            logging.info(f"[{self.name}] Falling back to pipeline.verify...")
            
            try:
                from pipeline.verify import verify_all
                verified, dropped = verify_all(items)
                verification_method = "pipeline_verify_fallback"
                logging.info(f"[{self.name}] Fallback: {len(verified)} verified, {len(dropped)} dropped")
            except Exception as e2:
                logging.error(f"[{self.name}] Fallback also failed: {e2}")
                self.context["stage_failed"] = f"All verification methods failed"
                raise RuntimeError(self.context["stage_failed"])
        
        # Quality gate
        min_verified = 5 if self.job_type == "daily" else (8 if self.job_type == "weekly" else 10)
        
        if len(verified) < min_verified:
            self.context["stage_failed"] = f"only {len(verified)} verified items (min {min_verified} for {self.job_type})"
            raise RuntimeError(self.context["stage_failed"])
        
        # Save with metadata
        write_json_atomic(data_path(VERIFIED_DIR, self.job_id), {
            "items": verified,
            "dropped": len(dropped),
            "verification_method": verification_method,
            "total_processed": len(items)
        })
        
        logging.info(f"[{self.name}] Complete: {len(verified)} verified using {verification_method}")
        self.context["verification_method"] = verification_method
        
        return self.context

    def verify(self):
        return not self.context.get("stage_failed")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    ctx = {"job_id": "test_2026-10-12", "job_type": "daily", "job_date": "2026-10-12"}
    print(Agent("test_2026-10-12", "daily", ctx).run())
