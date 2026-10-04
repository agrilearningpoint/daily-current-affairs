# -*- coding: utf-8 -*-
"""
TELEGRAM PIN VERIFIER AGENT
Main focus: pin करने के बाद actual verification — तभी job COMPLETE।

Command:
> "Pin the published document (pinChatMessage) then VERIFY by reading getChat().pinned_message.message_id == our message_id. If pin fails or mismatch → job is NOT complete and stage fails (watchdog will retry)."

Work: Real pin + read-back verification
Real implementation — see pipeline/ library. Quality gates enforced; empty output = failure.
"""

COMMAND = """Pin the published document (pinChatMessage) then VERIFY by reading getChat().pinned_message.message_id == our message_id. If pin fails or mismatch → job is NOT complete and stage fails (watchdog will retry)."""

MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content. Daily, Weekly, Monthly must independently select most valuable news."

DETAILS = """- pipeline.telegram_api.pin_message + verify_pin; sets state PIN_VERIFIED"""


class Agent:
    """TELEGRAM PIN VERIFIER AGENT — real implementation"""
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type
        self.context = context
        self.name = "TELEGRAM PIN VERIFIER AGENT"

    def run(self):
        import logging, os
        from pipeline.state import load_job, save_job
        from pipeline.telegram_api import pin_message, verify_pin
        job = load_job(self.job_id, self.job_type, self.context["job_date"])
        msg_id = job.get("telegram_message_id") or self.context.get("telegram_message_id")
        if not msg_id:
            self.context["stage_failed"] = "nothing published — cannot pin"
            raise RuntimeError(self.context["stage_failed"])
        chat = os.getenv("TELEGRAM_CHANNEL_ID") or os.getenv("TELEGRAM_CHAT_ID")
        if not chat:
            chat = "-1004485392227"   # Agri Learning Point channel — non-secret target id
        try:
            pin_message(chat, msg_id)
        except RuntimeError as e:
            logging.warning(f"[{self.name}] pin call failed (may already be pinned): {e}")
        ok, pinned = verify_pin(chat, msg_id)
        if not ok:
            self.context["stage_failed"] = f"pin verification FAILED: pinned={pinned} expected={msg_id}"
            raise RuntimeError(self.context["stage_failed"])
        save_job(job, state="PIN_VERIFIED", stage="23_telegram_pin_verifier")
        logging.info(f"[{self.name}] pin verified message_id={msg_id}")
        return self.context

    def verify(self):
        return not self.context.get("stage_failed")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    ctx = {"job_id": "test_2026-10-04", "job_type": "daily", "job_date": "2026-10-04"}
    print(Agent("test_2026-10-04", "daily", ctx).run())
