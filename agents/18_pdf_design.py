# -*- coding: utf-8 -*-
"""
PDF DESIGN AGENT
Main focus: data-driven premium PDF design system को JSON content से apply करना।

Command:
> "Render the edition via src/generate_pdf.generate_pdf(content, mcqs) — Mukta+Poppins fonts, Hindi 12.5pt / English 12pt, headline 18pt, 13mm margins, single column, category banners, Static Facts tables, Exam Fact yellow boxes, controlled colours, no filler pages. Output goes to output/ inside the workspace."

Work: Dynamic generator invocation (no hardcoded sample)
Real implementation — see pipeline/ library. Quality gates enforced; empty output = failure.
"""

COMMAND = """Render the edition via src/generate_pdf.generate_pdf(content, mcqs) — Mukta+Poppins fonts, Hindi 12.5pt / English 12pt, headline 18pt, 13mm margins, single column, category banners, Static Facts tables, Exam Fact yellow boxes, controlled colours, no filler pages. Output goes to output/ inside the workspace."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- calls dynamic generate_pdf() on data/content + data/mcq/_validated JSON
- refuses empty editions; writes output/<edition>.pdf"""


class Agent:
    """PDF DESIGN AGENT — real implementation"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type
        self.context = context
        self.name = "PDF DESIGN AGENT"

    def run(self):
        import logging, os
        from src.generate_pdf import generate_pdf
        from pipeline.state import CONTENT_DIR, MCQ_DIR, OUTPUT_DIR, data_path, read_json
        c = read_json(data_path(CONTENT_DIR, self.job_id))
        mcqs = read_json(data_path(MCQ_DIR, self.job_id, "_validated"), [])
        if not mcqs:
            self.context["stage_failed"] = "no validated MCQs — refusing to build PDF without MCQ section"
            raise RuntimeError(self.context["stage_failed"])
        out = generate_pdf(c, mcqs)
        if not os.path.exists(out) or os.path.getsize(out) < 20000:
            self.context["stage_failed"] = f"PDF missing/too small: {out}"
            raise RuntimeError(self.context["stage_failed"])
        self.context["pdf_path"] = out
        # PDF SHA256 for health audit + Telegram integrity (P2)
        try:
            from pipeline import store as _store
            h = _store.save_pdf_hash(self.job_id, out)
            self.context["pdf_sha256"] = h
            logging.info(f"[{self.name}] PDF built: {out} ({os.path.getsize(out)//1024} KB) sha={h[:12] if h else 'none'}")
        except Exception as e:
            logging.warning(f"[{self.name}] pdf hash save failed: {e}")
            logging.info(f"[{self.name}] PDF built: {out} ({os.path.getsize(out)//1024} KB)")
        return self.context

    def verify(self):
        return not self.context.get("stage_failed")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    ctx = {"job_id": "test_2026-10-04", "job_type": "daily", "job_date": "2026-10-04"}
    print(Agent("test_2026-10-04", "daily", ctx).run())
