# Production Health Dashboard

**Generated At (UTC):** `2026-11-28T10:14:01.017819+00:00`  
**Data Sources:** `state/jobs.json`, `state/published_events.json`, `state/healing_history.json`, `recovery_plan.json`, `logs/qa/*_qa.json`, `logs/ai_usage.jsonl`, `logs/provider_health.json`, `logs/provider_summary.json`

---

## 1. Workflow Execution Summary

| Workflow | Total | Success | Failed | Pending / Other | Success Rate | Multi-Attempt Recovered | Mean 1-Attempt Duration (s) |
|---|---:|---:|---:|---:|---:|---:|---:|
| `daily` | 54 | 41 | 1 | 12 | 75.93% | 8 | 498.1 |
| `weekly` | 7 | 2 | 1 | 4 | 28.57% | 0 | 86.0 |
| `monthly` | 1 | 0 | 0 | 1 | 0.0% | 0 | - |

## 2. Failures by Stage & Unresolved Escalations

| Workflow : Stage | Count |
|---|---:|
| `daily:03_news_collection` | 2 |
| `daily:04_fact_verification` | 4 |
| `daily:12_content_editor` | 3 |
| `daily:19_pdf_qa` | 1 |
| `daily:22_telegram_publisher` | 3 |
| `monthly:19_pdf_qa` | 1 |
| `weekly:12_content_editor` | 1 |
| `weekly:19_pdf_qa` | 2 |
| `weekly:20_weekly_editor` | 1 |
| `weekly:22_telegram_publisher` | 1 |

### Currently Failed Jobs in `state/jobs.json`

- `daily_2026-11-25`: status=`failed`, attempts=`7`, failed_stage=`19_pdf_qa`, updated=`2026-11-25T09:48:53.488411+00:00`
- `weekly_2026-11-22`: status=`failed`, attempts=`6`, failed_stage=`19_pdf_qa`, updated=`2026-11-24T00:23:36.576401+00:00`

## 3. Auto-Heal & Recovery Telemetry

- **Total Logged Healing Incidents (`state/healing_history.json`):** `39`
- **By Status:** `{"recovered": 8, "escalated_budget_exhausted": 25, "requires_test_gated_pr": 6}`
- **By Category:** `{"pdf_generation_failure": 19, "github_actions_failure": 20}`
- **Active Manual-Attention Queue (`recovery_plan.json`):** `[]`
- **Stale `recovery_plan.json` Entries (Now `success` in `jobs.json`):** `[]`

## 4. AI Provider & Key-Slot Observability

- **Logged Live-Job Calls (`logs/ai_usage.jsonl` with real `job` & provider):** `1062` (`ok=415`, `fail=647`, `429/rate_limit=645`, `cache_hits=0`, jobs=`['daily_2026-11-22']`)
- **Historical Test-Fixture / Unscoped Rows Separated From Live Telemetry:** `307` (of `1369` total rows)
- **Live Provider Breakdown (`logs/ai_usage.jsonl`):** `{"gemini": {"ok": 109, "fail": 4, "rate_limits": 4}, "groq": {"ok": 306, "fail": 643, "rate_limits": 641}}`

| Provider | Slots | Active Model | Available | Shared Quota Flag |
|---|---:|---|---|---|
| `gemini` | 4 | `gemini-3.5-flash-lite` | `False` | `True` |

## 5. PDF QA Metrics (`logs/qa/*_qa.json`)

- **Saved QA Reports:** `7` (`passed=6`, `failed=1`, `pass_rate=85.71%`)
- **Mean Pages:** `32.14` | **Mean Devanagari Coverage:** `22.77%`
- **Blank Page Alerts:** `0` | **Near-Empty Page Alerts:** `0`

| Edition | QA Passed | Pages | Substantive | Hindi % | MCQs | Images | Near-Empty | Issues |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `daily_2026-10-20` | `True` | 29 | 29 | 5.57 | 18 | 95 | 0 | 2 |
| `daily_2026-10-24` | `True` | 32 | 32 | 10.36 | 29 | 99 | 0 | 0 |
| `daily_2026-10-29` | `True` | 23 | 23 | 20.81 | 14 | 45 | 0 | 1 |
| `daily_2026-11-17` | `True` | 34 | 34 | 30.62 | 15 | 379 | 0 | 1 |
| `daily_2026-11-19` | `False` | 28 | 28 | 29.74 | 11 | 301 | 0 | 2 |
| `daily_2026-11-22` | `True` | 39 | 39 | 32.07 | 15 | 428 | 0 | 2 |
| `weekly_2026-11-22` | `True` | 40 | 40 | 30.22 | 43 | 480 | 0 | 2 |

## 6. Telegram Publication Ledger (`state/published_events.json`)

- **Total Records:** `65` | **Live Success Sends:** `60` | **With Artifact Hash:** `65`
- **Same-Hash Duplicate Live Sends:** `{}`
- **Distinct-Hash Revision Sends:** `{'daily_2026-10-17': 2, 'daily_2026-10-20': 2, 'daily_2026-10-24': 8, 'daily_2026-11-02': 2, 'daily_2026-11-11': 2, 'daily_2026-11-15': 4, 'daily_2026-11-22': 2}`
