# -*- coding: utf-8 -*-
"""
MCQ VALIDATOR AGENT v4 — FAIL-CLOSED Standalone Validation
CRITICAL FIX: This agent performs ADDITIONAL validation on MCQs from Agent 16.
If validation fails, pipeline STOPS. No unvalidated MCQs can pass.
"""
import logging

COMMAND = "Validate MCQs for quality, correctness, and exam-readiness. Failure = pipeline failure."
MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity."


class Agent:
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type
        self.context = context
        self.name = "MCQ VALIDATOR AGENT v4 (FAIL-CLOSED)"

    def run(self):
        from pipeline.state import MCQ_DIR, CONTENT_DIR, data_path, read_json, write_json_atomic
        
        mcqs = read_json(data_path(MCQ_DIR, self.job_id), [])
        content = read_json(data_path(CONTENT_DIR, self.job_id))
        items = content.get("items", [])
        
        if not mcqs:
            error_msg = "No MCQs to validate - Agent 16 should have generated MCQs"
            logging.error(f"[{self.name}] {error_msg}")
            self.context["stage_failed"] = error_msg
            raise RuntimeError(error_msg)
        
        logging.info(f"[{self.name}] Validating {len(mcqs)} MCQs from Agent 16...")
        
        # ═══════════════════════════════════════════════════════════
        # CRITICAL: FAIL-CLOSED VALIDATION
        # If validation module fails or returns 0 valid MCQs, pipeline STOPS
        # ═══════════════════════════════════════════════════════════
        
        validation_method = "none"
        validated_mcqs = []
        
        try:
            from pipeline.content import validate_mcqs
            
            logging.info(f"[{self.name}] Running mcq_validator (FAIL-CLOSED)...")
            validated_mcqs, rejected_mcqs = validate_mcqs(mcqs, items)
            validation_method = "mcq_validator_v2"
            
            rejected = len(mcqs) - len(validated_mcqs)
            logging.info(f"[{self.name}] Validation: {len(validated_mcqs)}/{len(mcqs)} passed ({rejected} rejected)")
            
            # CRITICAL: If validation returns 0 MCQs, this is a FAILURE
            if len(validated_mcqs) == 0:
                error_msg = f"MCQ validation returned 0 valid MCQs out of {len(mcqs)} provided"
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
        min_mcqs = min(8, len(items))
        
        if len(validated_mcqs) < min_mcqs:
            error_msg = f"only {len(validated_mcqs)} valid MCQs after validation (need >={min_mcqs}). Validation is working correctly - rejecting low quality."
            logging.error(f"[{self.name}] {error_msg}")
            self.context["stage_failed"] = error_msg
            raise RuntimeError(error_msg)
        
        # Save ONLY validated MCQs
        write_json_atomic(data_path(MCQ_DIR, self.job_id), validated_mcqs)
        
        logging.info(f"[{self.name}] ✓ Final: {len(validated_mcqs)} VALIDATED MCQs using {validation_method}")
        self.context["mcqs_validated"] = len(validated_mcqs)
        self.context["validation_method"] = validation_method
        self.context["validation_status"] = "PASSED"
        
        return self.context

    def verify(self):
        return not self.context.get("stage_failed")


if __name__ == "__main__":
    import logging
    from pipeline.artifacts import run_agent
    logging.basicConfig(level=logging.INFO)
    run_agent(Agent)
