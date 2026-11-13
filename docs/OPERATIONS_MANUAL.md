# Daily Operations & Troubleshooting Manual

1. **Automated Schedule**:
   - **02:00–04:00 IST (`daily.yml`)**: Collects, verifies, deduplicates, translates, generates MCQs, builds the PDF, runs QA, and parks the job as `awaiting_publish`.
   - **06:00–06:40 IST (`daily.yml`)**: Publishes the verified PDF to Telegram (`@agrilearningpoint`) and verifies the channel pin.
   - **On Failure (`auto-heal.yml`)**: Triggers `agents/25_auto_healer.py` to classify the failure, heal recoverable state, run unit tests, and resume.
   - **Every 1st & 15th (`keepalive.yml`)**: Runs `scripts/verify_keys.py` and commits a heartbeat only when repository inactivity exceeds 50 days.
2. **Quality & Health Reports**:
   - Inspect `reports/daily_quality_report.json` and `reports/daily_health_report.json` after each run.
