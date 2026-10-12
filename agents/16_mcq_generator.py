# -*- coding: utf-8 -*-
"""
MCQ GENERATOR AGENT v3 — Integrated with MCQ Validator
Generates MCQs and validates them using new pipeline.mcq_validator
with fallback to unvalidated MCQs if validator fails.
"""
import logging

COMMAND = "Generate 12-15 MCQs with strict quality validation."
MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity."


class Agent:
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type
        self.context = context
        self.name = "MCQ GENERATOR AGENT v3"

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
        
        # Validate using new mcq_validator
        valid_mcqs = []
        validation_method = "none"
        
        try:
            from pipeline.mcq_validator import validate_mcqs
            
            logging.info(f"[{self.name}] Validating MCQs with mcq_validator...")
            valid_mcqs = validate_mcqs(all_mcqs, items)
            validation_method = "mcq_validator_v2"
            
            rejected = len(all_mcqs) - len(valid_mcqs)
            logging.info(f"[{self.name}] Validation: {len(valid_mcqs)}/{len(all_mcqs)} passed ({rejected} rejected)")
            
        except ImportError as e:
            logging.warning(f"[{self.name}] mcq_validator not available: {e}")
            logging.info(f"[{self.name}] Using unvalidated MCQs (fallback)")
            valid_mcqs = all_mcqs
            validation_method = "unvalidated_fallback"
            
        except Exception as e:
            logging.error(f"[{self.name}] mcq_validator failed: {e}")
            logging.info(f"[{self.name}] Using unvalidated MCQs (fallback)")
            valid_mcqs = all_mcqs
            validation_method = "unvalidated_fallback"
        
        # Quality gate
        min_mcqs = min(8, n_items)
        
        if len(valid_mcqs) < min_mcqs:
            self.context["stage_failed"] = f"only {len(valid_mcqs)} MCQs (need >={min_mcqs})"
            raise RuntimeError(self.context["stage_failed"])
        
        # Save with metadata
        write_json_atomic(data_path(MCQ_DIR, self.job_id), valid_mcqs)
        
        logging.info(f"[{self.name}] Final: {len(valid_mcqs)} MCQs using {validation_method}")
        self.context["mcqs_generated"] = len(valid_mcqs)
        self.context["validation_method"] = validation_method
        
        return self.context

    def verify(self):
        return not self.context.get("stage_failed")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    ctx = {"job_id": "test_2026-10-12", "job_type": "daily", "job_date": "2026-10-12"}
    print(Agent("test_2026-10-12", "daily", ctx).run())
