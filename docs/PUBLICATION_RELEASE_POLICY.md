# Publication & Release Gate Policy

Implemented across [`agents/19_pdf_qa.py`](../agents/19_pdf_qa.py), [`agents/22_telegram_publisher.py`](../agents/22_telegram_publisher.py), [`agents/23_telegram_pin_verifier.py`](../agents/23_telegram_pin_verifier.py), and [`agents/24_final_health_audit.py`](../agents/24_final_health_audit.py).

---

## 1. Pre-Publish Release Gate Requirements

No PDF may be transmitted to live Telegram channels unless **all** of the following hold:

1. **Full Pre-Publish Checkpoint Chain:** `state/jobs.json` records verified SHA-256 hashes for all prerequisite stage artifacts up through `19_pdf_qa`, verified by `pipeline.checkpoints.resume_after()`.
2. **QA & Visual Audit Approval:** `logs/qa/<job_id>_qa.json` has `passed: true`, matching `job_id`, exact matching `file_sha256` against `output/<job_id>.pdf`, and passes `release_approval` signature verification (`alp-release-v1` SHA-256 signature binding `job_id`, `file_sha256`, `passed`, and `visual_passed`).
3. **Strict Live Provenance Check:** Every story in `data/content/<job_id>.json` carries `verification_passed: true` and `needs_review: false` (unless explicitly overridden by dev `ALP_ALLOW_FALLBACK_TRANSLATION=1` in non-production workflows).
4. **Master Supervisor Pre-Publish Gate:** When `MasterSupervisor` runs in live mode, unresolved `P0` defects or missing release approval fail closed prior to stage `22_telegram_publisher`.
5. **Schedule Window Guard:** Daily Telegram publication waits until `ALP_PUBLISH_NOT_BEFORE` (`06:00` IST). Earlier runs terminate green with status `awaiting_publish`.

---

## 2. Idempotency & Crash-Safe Ledger Protection

- **Write-Ahead Intent (`status: "sending"`):** Recorded atomically to `state/published_events.json` *before* calling `sendDocument` with `retry_network=False`.
- **Ambiguous Outcome Freeze:** If a network timeout leaves delivery uncertain (`status: "uncertain"`), all automatic retries refuse to re-send until manual reconciliation clears the record.
- **Duplicate Edition Guard:** A different PDF hash for an already-published `job_id` enters `blocked_revision` unless explicitly authorized with `allow_revision=true`.
- **Pin Verification & Final Health Audit:** Stage `23_telegram_pin_verifier` verifies channel message reachability and pinning, and Stage `24_final_health_audit` produces `logs/qa/<job_id>_health.json` alongside `reports/<job_id>_edition_report.{json,md}`.
