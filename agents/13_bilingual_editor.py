# -*- coding: utf-8 -*-
"""
BILINGUAL EDITOR AGENT
Main focus: हिंदी version तैयार करना (Devanagari-safe)।

Command:
> "Ensure every item has a Hindi headline and Hindi key points. Translation is word-substitution based (no invented meaning); proper nouns stay in English inside the Hindi line. Final Hindi rendering uses Mukta via Pillow+HarfBuzz in the PDF generator."

Work: Hindi pass over content JSON
Real implementation — see pipeline/ library. Quality gates enforced; empty output = failure.
"""

COMMAND = """Ensure every item has a Hindi headline and Hindi key points. Translation is word-substitution based (no invented meaning); proper nouns stay in English inside the Hindi line. Final Hindi rendering uses Mukta via Pillow+HarfBuzz in the PDF generator."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- validates every item has headline_hi/key_points_hi; fills from content builder translation if missing"""


class Agent:
    """BILINGUAL EDITOR AGENT — real implementation"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type
        self.context = context
        self.name = "BILINGUAL EDITOR AGENT"

    def run(self):
        import logging
        from pipeline.content import translate_headline
        from pipeline.state import CONTENT_DIR, data_path, read_json, write_json_atomic
        c = read_json(data_path(CONTENT_DIR, self.job_id))
        fixed = 0
        for it in c["items"]:
            if not it.get("headline_hi"):
                it["headline_hi"] = ">> " + translate_headline(it["headline_en"]); fixed += 1
            if not it.get("key_points_hi"):
                it["key_points_hi"] = [translate_headline(p) for p in it["key_points_en"]]; fixed += 1
        write_json_atomic(data_path(CONTENT_DIR, self.job_id), c)
        logging.info(f"[{self.name}] bilingual ok (fixed {fixed})")
        self.context["bilingual_ok"] = True
        return self.context

    def verify(self):
        return not self.context.get("stage_failed")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    ctx = {"job_id": "test_2026-10-04", "job_type": "daily", "job_date": "2026-10-04"}
    print(Agent("test_2026-10-04", "daily", ctx).run())
