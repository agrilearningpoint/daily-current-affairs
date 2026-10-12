# -*- coding: utf-8 -*-
"""
MCQ GENERATOR AGENT v4 — FAIL-CLOSED Validation
CRITICAL FIX: Validation failure now BLOCKS pipeline, not bypasses it.
No unvalidated MCQs can pass to next stage.
"""
import logging

COMMAND = "Generate 12-15 MCQs with STRICT quality validation. Validation failure = pipeline failure."
MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts."


class Agent:
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type
        self.context = context
        self.name = "MCQ GENERATOR AGENT v4 (FAIL-CLOSED)"

    def run(self):
        from pipeline.state import CONTENT_DIR, MCQ_DIR, data_path, read_json, write_json_atomic
        
        content = read_json(data_path(CONTENT_DIR, self.job_id))
        items = content.get("items", [])
        n_items = len(items)
        
        logging.info(f"[{self.name}] Generating MCQs for {n_items} items...")
        
        # Generate MCQs using existing method
        from pipeline.content import generate_mcqs
        all_mcqs = generate_mcqs(items)
        
        logging.info(f"[{self.name}] Generated {len(all_mcqs)} raw MCQs")
        
        # ═══════════════════════════════════════════════════════════
        # CRITICAL: FAIL-CLOSED VALIDATION
        # If validation module fails or returns 0 valid MCQs, pipeline STOPS
        # ═══════════════════════════════════════════════════════════
        
        validation_method = "none"
        valid_mcqs = []
        
        try:
            from pipeline.mcq_validator import validate_mcqs
            
            logging.info(f"[{self.name}] Running mcq_validator (FAIL-CLOSED)...")
            valid_mcqs = validate_mcqs(all_mcqs, items)
            validation_method = "mcq_validator_v2"
            
            rejected = len(all_mcqs) - len(valid_mcqs)
            logging.info(f"[{self.name}] Validation: {len(valid_mcqs)}/{len(all_mcqs)} passed ({rejected} rejected)")
            
            # CRITICAL: If validation returns 0 MCQs, this is a FAILURE
            if len(valid_mcqs) == 0:
                error_msg = f"MCQ validation returned 0 valid MCQs out of {len(all_mcqs)} generated"
                logging.error(f"[{self.name}] {error_msg}")
                self.context["stage_failed"] = error_msg
                raise RuntimeError(error_msg)
            
        except ImportError as e:
            # CRITICAL: If mcq_validator module not found, this is a FAILURE
            error_msg = f"mcq_validator module not available: {e}. Cannot proceed without validation."
            logging.error(f"[{self.name}] {error_msg}")
            self.context["stage_failed"] = error_msg
            raise RuntimeError(error_msg)
            
        except Exception as e:
            # CRITICAL: If validation throws exception, this is a FAILURE
            error_msg = f"MCQ validation failed with exception: {e}. Cannot proceed with unvalidated MCQs."
            logging.error(f"[{self.name}] {error_msg}")
            self.context["stage_failed"] = error_msg
            raise RuntimeError(error_msg)
        
        # Quality gate: minimum MCQs required
        min_mcqs = min(8, n_items)
        
        if len(valid_mcqs) < min_mcqs:
            error_msg = f"only {len(valid_mcqs)} valid MCQs generated for {n_items} news (need >={min_mcqs}). Validation is working correctly - rejecting low quality."
            logging.error(f"[{self.name}] {error_msg}")
            self.context["stage_failed"] = error_msg
            raise RuntimeError(error_msg)
        
        # Save ONLY validated MCQs
        write_json_atomic(data_path(MCQ_DIR, self.job_id), valid_mcqs)
        
        logging.info(f"[{self.name}] ✓ Final: {len(valid_mcqs)} VALIDATED MCQs using {validation_method}")
        self.context["mcqs_generated"] = len(valid_mcqs)
        self.context["validation_method"] = validation_method
        self.context["validation_status"] = "PASSED"
        
        return self.context

    def verify(self):
        return not self.context.get("stage_failed")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    ctx = {"job_id": "test_2026-10-12", "job_type": "daily", "job_date": "2026-10-12"}
    print(Agent("test_2026-10-12", "daily", ctx).run())
