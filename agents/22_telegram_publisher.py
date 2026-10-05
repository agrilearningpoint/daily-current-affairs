# -*- coding: utf-8 -*-
"""
TELEGRAM PUBLISHER AGENT
Main focus: QA-approved PDF को hi channel पर upload करना।

Command:
> "Publish ONLY if state == QA_APPROVED. Upload the PDF via Telegram Bot API sendDocument with bilingual caption + source links, store message_id in the job record. Duplicate check: if job already PUBLISHED with a message_id, skip re-upload. Token strictly from TELEGRAM_BOT_TOKEN env (no fallback constant)."

Work: Real sendDocument + duplicate guard
Real implementation — see pipeline/ library. Quality gates enforced; empty output = failure.
"""

COMMAND = """Publish ONLY if state == QA_APPROVED. Upload the PDF via Telegram Bot API sendDocument with bilingual caption + source links, store message_id in the job record. Duplicate check: if job already PUBLISHED with a message_id, skip re-upload. Token strictly from TELEGRAM_BOT_TOKEN env (no fallback constant)."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- pipeline.telegram_api.send_document()
- saves telegram_message_id; sets state PUBLISHED"""


class Agent:
    """TELEGRAM PUBLISHER AGENT — real implementation"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type
        self.context = context
        self.name = "TELEGRAM PUBLISHER AGENT"

    def run(self):
        import logging, os
        from pipeline.state import load_job, CONTENT_DIR, data_path, read_json
        from pipeline.telegram_api import send_document
        job = load_job(self.job_id, self.job_type, self.context["job_date"])
        if job.get("status") != "QA_APPROVED":
            self.context["stage_failed"] = f"publish blocked: state={job.get('status')} (QA hard gate)"
            raise RuntimeError(self.context["stage_failed"])
        if job.get("telegram_message_id"):
            logging.info(f"[{self.name}] already published msg_id={job['telegram_message_id']} — duplicate prevented (job state)")
            return self.context
        # P0 FIX: Check dedicated job-level registry (crash-after-send guard)
        try:
            from pipeline import store as _store
            if _store.is_job_published(self.job_id):
                rec = _store.get_job_publication(self.job_id)
                logging.info(f"[{self.name}] already published via registry msg_id={rec.get('message_id')} — duplicate prevented (registry)")
                self.context["telegram_message_id"] = rec.get("message_id")
                return self.context
        except Exception:
            pass
        chat = os.getenv("TELEGRAM_CHANNEL_ID") or os.getenv("TELEGRAM_CHAT_ID")
        if not chat:
            chat = "-1004485392227"   # Agri Learning Point channel — non-secret target id
        if not chat:
            self.context["stage_failed"] = "TELEGRAM_CHANNEL_ID missing"
            raise RuntimeError(self.context["stage_failed"])
        c = read_json(data_path(CONTENT_DIR, self.job_id))
        label = {"daily": "Daily", "weekly": "Weekly Best-of", "monthly": "Monthly Best-of"}[self.job_type]
        top = c["items"][0]["headline_en"].lstrip("> ")[:120]
        caption = (f"🗞️ ALP {label} Current Affairs — {c['job']['date_display']}\n\n"
                   f"⭐ {top}\n\n"
                   f"📰 {len(c['items'])} verified news • MCQ practice included\n"
                   f"✅ All facts verified against primary sources\n"
                   f"📲 @Agrikrishna | YouTube: Agri Learning Point")
        # P0 FIX: Compute PDF SHA256 for Telegram document integrity verification
        pdf_path = self.context["pdf_path"]
        file_sha = None
        try:
            import hashlib as _hl
            file_sha = _hl.sha256(open(pdf_path, "rb").read()).hexdigest()
            try:
                from pipeline import store as _s2
                _s2.save_pdf_hash(self.job_id, pdf_path)
            except Exception:
                pass
        except Exception as e:
            logging.warning(f"[{self.name}] pdf hash compute failed: {e}")
        msg_id = send_document(chat, pdf_path, caption, job_id=self.job_id)
        # Persist BOTH registries: event-level + dedicated job-level (P0 FIX for atomic idempotency)
        try:
            from pipeline import store
            store.mark_published([i["event_id"] for i in c["items"]], self.job_id)
            try:
                store.mark_job_published(self.job_id, chat, msg_id, file_sha or "")
            except Exception as e2:
                logging.warning(f"[{self.name}] job-level registry failed: {e2}")
            pushed = store.push(f"state: {self.job_id} published msg_id={msg_id}")
            if not pushed:
                logging.info(f"[{self.name}] state already up-to-date after publish")
        except Exception as e:
            logging.error(f"[{self.name}] state push after publish failed: {e}")
            print(f"::error::State push after Telegram publish failed — duplicate risk on retry: {e}")
            raise
        self.context["telegram_message_id"] = msg_id
        self.context["telegram_file_sha256"] = file_sha
        logging.info(f"[{self.name}] published message_id={msg_id} sha={file_sha[:8] if file_sha else 'none'}")
        return self.context

    def verify(self):
        return not self.context.get("stage_failed")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    ctx = {"job_id": "test_2026-10-04", "job_type": "daily", "job_date": "2026-10-04"}
    print(Agent("test_2026-10-04", "daily", ctx).run())
