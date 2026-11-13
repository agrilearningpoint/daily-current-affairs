# Persistent Data Storage & Historical Memory Guide

All historical state resides in `state/` and is persisted across GitHub Actions runner lifecycles via atomic file writes (`tempfile.mkstemp` + `os.fsync` + `os.replace`) and `scripts/sync_state.py`:
- `state/news_history.json`: Permanent 4-layer event & URL ledger.
- `state/mcq_history.json`: Permanent MCQ question & semantic fingerprint database (never truncated during migrations).
- `state/fact_ledger.json`: Source-grounded numerical and institutional fact records.
- `state/feed_health.json`: Per-feed ETag, Last-Modified, failure count, and quarantine timestamps.
- `state/api_health.json`: Per-key RPM/RPD counters and cooldown timers.
- `state/published_events.json` & `state/pin_verification.json`: Telegram idempotency and pin ledgers.
- `state/healing_history.json`: Self-healing incident history and per-job repair budgets.
