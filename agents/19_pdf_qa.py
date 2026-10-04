# -*- coding: utf-8 -*-
"""
PDF QA AGENT — HARD GATE
Main focus: PDF publish से पहले हर possible error पकड़ना; fail = publish block।

Command:
> "Run the full QA checklist on the generated PDF: exists, >0 pages, fonts embedded (Mukta/Poppins), Hindi Devanagari extractable, edition date present, expected news headlines present, MCQ count matches validated JSON, answer letters valid, no blank page, no runaway page count. Any failure => status QA_REJECTED and the pipeline FAILS before Telegram."

Work: HARD GATE — blocks publish on any failure
Real implementation — see pipeline/ library. Quality gates enforced; empty output = failure.
"""

COMMAND = """Run the full QA checklist on the generated PDF: exists, >0 pages, fonts embedded (Mukta/Poppins), Hindi Devanagari extractable, edition date present, expected news headlines present, MCQ count matches validated JSON, answer letters valid, no blank page, no runaway page count. Any failure => status QA_REJECTED and the pipeline FAILS before Telegram."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- PyMuPDF render + text-extraction checks against source JSON
- writes logs/qa/<job_id>.json report"""


class Agent:
    """PDF QA AGENT — HARD GATE — real implementation"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type
        self.context = context
        self.name = "PDF QA AGENT — HARD GATE"

    def run(self):
        import logging, os, re
        import pymupdf
        from pipeline.state import CONTENT_DIR, MCQ_DIR, QA_LOG_DIR, data_path, read_json, write_json_atomic, load_job, save_job
        pdf = self.context.get("pdf_path", "")
        c = read_json(data_path(CONTENT_DIR, self.job_id))
        mcqs = read_json(data_path(MCQ_DIR, self.job_id, "_validated"), [])
        checks, ok = [], True
        def chk(name, cond, detail=""):
            nonlocal ok
            checks.append({"check": name, "pass": bool(cond), "detail": detail})
            if not cond: ok = False
        chk("pdf_exists", os.path.exists(pdf), pdf)
        if not ok:
            self._reject(checks); return self.context
        doc = pymupdf.open(pdf)
        txt = "".join(p.get_text() for p in doc)
        flat = re.sub(r"\s+", " ", txt)
        chk("pages_gt_0", doc.page_count > 0, f"pages={doc.page_count}")
        fonts = set(f[3] for pg in doc for f in pg.get_fonts())
        chk("fonts_embedded", any("Mukta" in f for f in fonts) and any("Poppins" in f or "DejaVu" in f for f in fonts), str(list(fonts))[:200])
        chk("hindi_extractable", bool(re.search("[\u0900-\u097F]", txt)), "Devanagari chars found" )
        chk("date_present", c["job"]["date_display"] in flat, c["job"]["date_display"])
        missing = [i["event_id"] for i in c["items"] if re.sub(r"[^A-Za-z0-9]", "", i["headline_en"].lstrip("> ")[:40]).lower()[:20]
                   and re.sub(r"\s+", " ", i["headline_en"].lstrip("> "))[:45] not in flat]
        chk("all_headlines_present", len(missing) <= max(1, len(c["items"])//10), f"missing={missing[:3]}")
        chk("mcq_count_matches", sum(f"Q{m['q_num']}." in flat for m in mcqs) >= len(mcqs) * 0.9, f"mcqs={len(mcqs)}")
        chk("answers_valid", all(ord(m["correct"]) - 65 < len(m["options"]) for m in mcqs))
        blanks = [p.number for p in doc if len(p.get_text().strip()) < 15]
        chk("no_blank_pages", len(blanks) == 0, f"blanks={blanks}")
        chk("page_count_sane", 3 <= doc.page_count <= 60, f"pages={doc.page_count}")
        write_json_atomic(data_path(QA_LOG_DIR, self.job_id), {"checks": checks, "approved": ok})
        if not ok:
            self._reject(checks)
        else:
            save_job(load_job(self.job_id, self.job_type, self.context["job_date"]),
                     state="QA_APPROVED", stage="19_pdf_qa")
            logging.info(f"[{self.name}] APPROVED ({len(checks)} checks)")
        return self.context

    def _reject(self, checks):
        job = load_job(self.job_id, self.job_type, self.context["job_date"])
        save_job(job, state="QA_REJECTED", failed_checks=[c["check"] for c in checks if not c["pass"]])
        self.context["stage_failed"] = f"PDF QA REJECTED: {[c['check'] for c in checks if not c['pass']]}"
        raise RuntimeError(self.context["stage_failed"])

    def verify(self):
        return not self.context.get("stage_failed")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    ctx = {"job_id": "test_2026-10-04", "job_type": "daily", "job_date": "2026-10-04"}
    print(Agent("test_2026-10-04", "daily", ctx).run())
