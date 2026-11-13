# Autonomous Self-Healing Guide (`agents/25_auto_healer.py`)

1. **15 Error Classifications**: Classifies failures into `api_auth_failure`, `api_rate_limit`, `api_timeout`, `rss_failure`, `data_validation_failure`, `duplicate_news`, `mcq_validation_failure`, `pdf_generation_failure`, `hindi_font_failure`, `telegram_upload_failure`, `github_actions_failure`, `state_corruption`, `missing_dependency`, `python_exception`, and `workflow_timeout`.
2. **Deterministic Recovery & Repair Budget**: Executes rule-based recovery (key rotation, dead-feed quarantine, corrupt state quarantine, checkpoint resume, Telegram ledger reconciliation) up to `ALP_MAX_HEAL_BUDGET = 3` attempts per job.
3. **Test-Gated Code Changes**: `.github/workflows/auto-heal.yml` runs the automated unit test suite before committing any recovery state or opening a repair PR.
