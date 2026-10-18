# 🌾 Agri Learning Point — Daily Current Affairs Automation

Production-grade pipeline that collects, verifies, and publishes daily/weekly/monthly current-affairs content for competitive exam students (AGTA, AFO, ICAR, IBPS, NABARD).

**What it does:**
1. Fetches news from RSS feeds + APIs (rolling 24–36h window, 00:00 IST previous day onwards)
2. Fact-checks claims via cross-source corroboration + heuristic + optional LLM
3. Deduplicates + ranks by importance
4. Builds bilingual (English + Hindi) content
5. Generates exam-oriented MCQs (4-5 options, validated)
6. Renders a professional PDF (Hindi + English)
7. Publishes to Telegram + pins to channel
8. Runs daily/weekly/monthly on GitHub Actions

---

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Pipeline Stages](#pipeline-stages)
- [Installation](#installation)
- [Configuration](#configuration)
- [CLI Reference](#cli-reference)
- [GitHub Actions](#github-actions)
- [State Management](#state-management)
- [Troubleshooting](#troubleshooting)
- [Maintenance](#maintenance)
- [Testing](#testing)

---

## 🚀 Quick Start

```bash
# 1. Clone
git clone https://github.com/agrilearningpoint/daily-current-affairs.git
cd daily-current-affairs

# 2. Setup Python 3.11
python3.11 -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate          # Windows

# 3. Install deps
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# 4. Configure
cp .env.example .env
# Edit .env — fill TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, and (optionally) LLM keys

# 5. Run a daily job (dry-run style — skips real Telegram publishing if DRY_RUN=1)
DRY_RUN=1 python main.py --job-type daily --date 2026-10-14
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  GitHub Actions (scheduled)                                     │
│  daily.yml · weekly.yml · monthly.yml · watchdog.yml            │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  main.py  (orchestrator)                                        │
│  - Job locking (fcntl)                                          │
│  - Atomic state writes                                          │
│  - Stage resolution (agents/ + pipeline/)                       │
│  - Retry + timeout per stage                                    │
│  - Resume-from-last-success                                     │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Agents (agents/*.py)                                           │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐  │
│  │ 03 News      │ 04 Fact      │ 12 Content   │ 16 MCQ       │  │
│  │   Collection │   Verification│  Editor     │   Generator  │  │
│  ├──────────────┼──────────────┼──────────────┼──────────────┤  │
│  │ 17 MCQ       │ 18 PDF       │ 19 PDF       │ 22 Telegram  │  │
│  │   Validator  │   Design     │   QA         │   Publisher  │  │
│  ├──────────────┼──────────────┼──────────────┼──────────────┤  │
│  │ 23 Pin       │ 24 Final     │ 20 Weekly    │ 21 Monthly   │  │
│  │   Verifier   │   Audit      │   Editor     │   Editor     │  │
│  └──────────────┴──────────────┴──────────────┴──────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  pipeline/  (shared library)                                    │
│  - ai_router.py      Multi-provider LLM fallback                │
│  - ai_translator.py  EN→HI with validation                      │
│  - state.py          Job state machine + atomic I/O             │
│  - store.py          Importance memory persistence              │
│  - content.py        Content formatting helpers                 │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
data/raw/        ← Agent 03 (News Collection)
data/verified/   ← Agent 04 (Fact Verification)
data/dedup/      ← Agent 05 (Deduplication)
data/scored/     ← Agent 06 + 07 (Importance + Domain relevance)
data/selected/   ← Agent 10 (Final selection)
data/content/    ← Agent 12 (Content editor, bilingual)
data/mcq/        ← Agent 16 + 17 (MCQ gen + validate)
output/          ← Agent 18 (Final PDF)
state/           ← Persistent state (jobs.json, ledgers, memory)
```

---

## 🔄 Pipeline Stages

### Daily (16 stages)

The authoritative list is `DAILY_STAGES` in `main.py`; this table mirrors it.

| # | Stage | Critical | Purpose |
|---|---|---|---|
| 00 | `00_model_orchestrator` | ✅ | Resolve LLM providers for the run |
| 01 | `01_source_fetch` | ✅ | Fetch the canonical RSS registry |
| 04 | `04_fact_verification` | ✅ | Confidence scoring + cross-source checks |
| 05 | `05_deduplication` | ✅ | Event-level dedup |
| 06 | `06_news_importance` | ✅ | Importance scoring |
| 07 | `07_student_domain_relevance` | ✅ | Exam relevance |
| 10 | `10_final_news_selection` | ✅ | Top-N selection |
| 11 | `11_importance_memory` | ✅ | Persist to memory |
| 12 | `12_content_editor` | ✅ | Bilingual content |
| 16 | `16_mcq_generator` | ✅ | Generate MCQs |
| 17 | `17_mcq_validator` | ✅ | Validate (no dupes, source-backed) |
| 18 | `18_pdf_design` | ✅ | Render the bilingual PDF |
| 19 | `19_pdf_qa` | ✅ | QA gate (fails the run on defects) |
| 22 | `22_telegram_publisher` | ✅ | Publish PDF |
| 23 | `23_telegram_pin_verifier` | ✅ | Pin + verify receipt |
| 24 | `24_final_health_audit` | ✅ | Final health audit |

### Weekly (10 stages)
`00_model_orchestrator` → `20_weekly_editor` → `12` → `16` → `17` → `18` → `19` → `22` → `23` → `24`

### Monthly (10 stages)
`00_model_orchestrator` → `21_monthly_editor` → `12` → `16` → `17` → `18` → `19` → `22` → `23` → `24`

The weekly/monthly tail is selected **by stage name** (`_TAIL_STAGE_NAMES` in
`main.py`), so re-ordering or inserting a daily stage can never silently change
what weekly/monthly run.

**Critical** stages: a missing script → **job FAILED** (never silently skipped).

---

## 🛠️ Installation

### Prerequisites

- Python **3.11+**
- pip **23+**
- Git
- Telegram Bot (created via [@BotFather](https://t.me/BotFather))
- (Optional) LLM API keys — Gemini / Groq / OpenAI / Mistral

### Steps

```bash
# 1. Clone
git clone https://github.com/agrilearningpoint/daily-current-affairs.git
cd daily-current-affairs

# 2. Virtual env
python3.11 -m venv .venv
source .venv/bin/activate

# 3. Upgrade pip
pip install --upgrade pip setuptools wheel

# 4. Install prod deps
pip install -r requirements.txt

# (Optional) Dev deps — for testing/linting
pip install -r requirements-dev.txt

# 5. Configure
cp .env.example .env
nano .env      # Fill in real values

# 6. Verify
python -c "from main import load_state; print('✅ Imports OK')"
```

---

## ⚙️ Configuration

### Required Environment Variables

| Variable | Purpose | Example |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Bot token | `123456:ABC...` |
| `TELEGRAM_CHAT_ID` | Target channel | `@your_channel` or `-1001234...` |

### Key Optional Variables

| Variable | Default | Purpose |
|---|---|---|
| `LLM_API_URL` | — | OpenAI-compatible endpoint |
| `LLM_API_KEY` | — | API key |
| `LLM_MODEL` | `gpt-4o-mini` | Model name |
| `GEMINI_API_KEY` | — | Gemini (primary in fallback) |
| `GROQ_API_KEY` | — | Groq (fast fallback) |
| `OPENROUTER_API_KEY` | — | OpenRouter fallback |
| `MISTRAL_API_KEY` | — | Mistral fallback |
| `NVIDIA_API_KEY` | — | NVIDIA NIM fallback; store it as a GitHub Actions secret |
| `NVIDIA_MODEL` | `meta/llama-3.3-70b-instruct` | NVIDIA NIM model |
| `MIN_CONFIDENCE_THRESHOLD` | `0.3` | Verification threshold (0–1) |
| `MIN_VERIFIED_COUNT` | `1` | Min items to proceed |
| `TELEGRAM_PARSE_MODE` | `HTML` | Message format |
| `TELEGRAM_MAX_PER_RUN` | `5` | Max PDFs per run |
| `STAGE_TIMEOUT_SECONDS` | `900` | Kill hung stages |
| `MAX_STAGE_RETRIES` | `3` | Retries per stage |
| `WATCHDOG_STUCK_HOURS` | `2` | Stuck threshold |
| `DRY_RUN` | `0` | Skip real publishing |
| `LOG_LEVEL` | `INFO` | `DEBUG`/`INFO`/`WARNING`/`ERROR` |

Full list: see [`.env.example`](.env.example).

---

## 💻 CLI Reference

### `main.py`

```bash
# Help
python main.py --help

# Run daily pipeline (today UTC)
python main.py --job-type daily

# Run daily for specific date
python main.py --job-type daily --date 2026-10-14

# Force re-run (ignore existing state)
python main.py --job-type daily --reset

# Weekly (Sunday)
python main.py --job-type weekly

# Monthly
python main.py --job-type monthly --date 2026-10-01

# Watchdog mode (detect stuck jobs + write recovery plan)
python main.py --watchdog

# Watchdog with custom threshold
python main.py --watchdog --stuck-hours 4

# --type is accepted as alias for --job-type (backward compat)
python main.py --type daily
```

### State cleanup

```bash
# Preview migration (no writes)
python maintenance/migrate_state.py --dry-run

# Apply cleanup (reset FAILED_FINAL for retry)
python maintenance/migrate_state.py --reset-failed-final

# Force reset a single job
python maintenance/migrate_state.py --reset-job daily_2026-10-13
```

### Individual agents (for debugging)

```bash
# Each agent can run standalone
python agents/03_news_collection.py
python agents/04_fact_verification.py
python agents/22_telegram_publisher.py

# Dry-run publishing
DRY_RUN=1 python agents/22_telegram_publisher.py
```

### Diagnostics & preview tools

```bash
# Full environment + pipeline diagnostic (checks [1]-[14])
python scripts/diagnose.py

# Source registry: offline invariants (duplicate URLs, tiers, categories)
python scripts/source_health.py

# Source registry: live reachability / parseability probe for every source
python scripts/source_health.py --live
python scripts/source_health.py --live --json

# Generate a sample bilingual edition, run the real PDF QA gate,
# and render representative pages to PNG for visual inspection
python scripts/pdf_preview.py --out output/sample_preview.pdf --png-dir output/preview
```

`source_health.py` and `pdf_preview.py` are read-only: they never publish to
Telegram and never write pipeline state.

### Documentation

| Document | Contents |
| --- | --- |
| [`docs/production-audit.md`](docs/production-audit.md) | Every audited defect, with file/line evidence and the regression test that covers it |
| [`docs/production-readiness.md`](docs/production-readiness.md) | Go-live gates and the operator pilot checklist |
| [`docs/source-registry.md`](docs/source-registry.md) | Canonical source registry, `official` semantics, how to add/retire a source |
| [`docs/pdf-design.md`](docs/pdf-design.md) | PDF palette, typography, Devanagari pipeline, glyph guard, content-aware QA gate |
| [`docs/content-quality-audit.md`](docs/content-quality-audit.md) | Stage-by-stage audit of the earlier 5-page output and the fixes that raise a daily edition to 15–25 substantive pages |
| [`docs/OPERATIONS_RUNBOOK.md`](docs/OPERATIONS_RUNBOOK.md) | Day-2 operations and recovery |

---

## 🔁 GitHub Actions

### Workflows

| Workflow | Schedule | Purpose |
|---|---|---|
| `daily.yml` | `0 2 * * *` (07:30 IST) | Daily pipeline |
| `weekly.yml` | `0 3 * * 0` (Sun 08:30 IST) | Weekly digest |
| `monthly.yml` | `0 4 1 * *` (1st 09:30 IST) | Monthly compilation |
| `watchdog.yml` | `0 */6 * * *` (every 6h) | Stuck job recovery |
| `ci.yml` | On PR/push | Lint + tests + security |

### Manual Trigger

**Actions** tab → select workflow → **Run workflow** → optionally override:
- `date` (YYYY-MM-DD)
- `reset` (boolean)
- `debug` (boolean)

### Required Repository Secrets

**Settings → Secrets and variables → Actions → New repository secret:**

| Secret | Required |
|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ |
| `TELEGRAM_CHAT_ID` | ✅ |
| `LLM_API_URL` | optional |
| `LLM_API_KEY` | optional |
| `LLM_MODEL` | optional |

**Non-sensitive vars can be added as Variables** (same page → Variables tab):
- `MIN_CONFIDENCE_THRESHOLD`
- `MIN_VERIFIED_COUNT`
- `STAGE_TIMEOUT_SECONDS`
- `WATCHDOG_STUCK_HOURS`

---

## 💾 State Management

### Files

| Path | Purpose | Git-tracked |
|---|---|---|
| `state/jobs.json` | Job status per pipeline | ✅ Yes |
| `state/published_events.json` | Telegram publish ledger | ✅ Yes |
| `state/importance_memory.json` | Long-term importance DB | ✅ Yes |
| `state/pin_verification.json` | Pin verify ledger | ✅ Yes |
| `state/backups/` | Migration backups | ❌ No |
| `state/archive/` | Append-only history | ❌ No |
| `state/locks/` | Job locks (ephemeral) | ❌ No |
| `state/metrics/` | Per-job metrics | ❌ No |

### Job Status Values

**Orchestrator statuses** (main.py):
- `PENDING` → `RUNNING` → `SUCCESS` / `FAILED` / `FAILED_FINAL`

**Pipeline states** (pipeline/state.py):
- `CREATED` → `COLLECTING` → `COLLECTED` → ... → `COMPLETE`
- Failure paths: `FAILED` → `RETRYING` → `FAILED_FINAL`

`main.py` normalizes legacy statuses (`COLLECTED`, `QA_REJECTED`, etc.) → `FAILED` for retry.

---

## 🔧 Troubleshooting

### Job shows `FAILED_FINAL`

```bash
# Reset and retry
python main.py --job-type daily --reset

# Or use migration script
python maintenance/migrate_state.py --reset-job daily_2026-10-13
```

### `only 0 verified items` error

1. **Lower threshold**:
   ```bash
   export MIN_CONFIDENCE_THRESHOLD=0.25
   export MIN_VERIFIED_COUNT=1
   ```

2. **Check collection**:
   ```bash
   python -c "
   from agents.03_news_collection import clean_text
   print(clean_text('कैबिनेट ने MSP बढ़ाया'))  # Should print Hindi
   "
   ```
   Agar Hindi chars missing hain → Unicode bug (see `test_unicode_safety.py`).

3. **Check LLM config** (if you want AI verification):
   ```bash
   echo $LLM_API_KEY | head -c 8   # Should show something
   ```

### Telegram publishing fails

```bash
# Verify credentials
curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe" | python -m json.tool

# Verify chat access
curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getChat?chat_id=${TELEGRAM_CHAT_ID}" | python -m json.tool

# Dry-run
DRY_RUN=1 python agents/22_telegram_publisher.py
```

Common issues:
- **401 Unauthorized** → Wrong `TELEGRAM_BOT_TOKEN`
- **400 chat not found** → Wrong `TELEGRAM_CHAT_ID` or bot not member
- **403 not enough rights** → Bot needs admin in channel
- **429 Too Many Requests** → Rate limit; publisher auto-waits

### Watchdog not recovering stuck jobs

```bash
# Manual run
python main.py --watchdog --stuck-hours 2

# Check recovery plan
cat recovery_plan.json
```

### State file corruption

`main.py` auto-backs-up corrupt state to `state/jobs.json.corrupt.<timestamp>` and starts fresh. To recover:

```bash
# List backups
ls -la state/*.corrupt.*

# Restore manually
cp state/jobs.json.corrupt.1234567890 state/jobs.json

# Or run migration
python maintenance/migrate_state.py --dry-run
```

---

## 🧰 Maintenance

### Weekly

```bash
# Cleanup old backups (keep last 10)
ls -t state/backups/*.json | tail -n +11 | xargs rm -f

# Check disk usage
du -sh data/ output/ logs/ state/
```

### Monthly

```bash
# Rotate logs
mv logs/orchestrator.log logs/orchestrator.$(date +%Y%m).log

# Archive old data (optional)
tar -czf archive_$(date +%Y%m).tar.gz data/raw/ data/verified/
```

### Dependency updates

```bash
# Preview updates
pip list --outdated

# Update one package
pip install --upgrade requests

# Or edit requirements.txt and reinstall
pip install -r requirements.txt --upgrade
```

---

## 🧪 Testing

```bash
# Install dev deps
pip install -r requirements-dev.txt

# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=agents --cov=pipeline --cov=main --cov-report=term-missing

# Specific file
pytest tests/test_unicode_safety.py -v

# Only fast tests (skip slow)
pytest tests/ -v -m "not slow"
```

### Key test files

| File | Purpose |
|---|---|
| `test_unicode_safety.py` | Hindi/Devanagari preservation |
| `test_orchestrator.py` | `main.py` CLI + legacy state compat |
| `test_migration.py` | `migrate_state.py` safety |
| `test_ai_router.py` | Multi-provider fallback |
| `test_state_machine.py` | State transitions |
| `test_pipeline_offline.py` | End-to-end offline (incl. real generate→QA PDF path) |
| `test_pdf_hindi.py` | Devanagari shaping + extractable Unicode forms |
| `test_pdf_sample_qa.py` | Real PDF generation + real QA gate on the bilingual fixture, incl. the 15-page daily target |
| `test_content_completeness.py` | Bilingual story completeness validator (required fields, Devanagari, numeric drift) |
| `test_selection.py` | Stage 07/10 coverage, dedup numeric guards, QA MCQ + substantive-page floors |
| `test_source_registry.py` | Canonical registry: duplicate URLs, tiers, coverage |
| `test_module_consolidation.py` | Locks the removal of duplicate modules |
| `test_publication_safety.py` | Publish guards (missing PDF, dry-run, ledger) |
| `test_telegram_api.py`, `test_store_published.py`, `test_claim_verifier.py`, `test_env_example.py`, `test_stage_selection.py` | Hardened infrastructure contracts added in this branch |

Test fixtures live in `tests/fixtures/` (see `bilingual_sample.py`).

---

## 📊 Monitoring

### Logs

| Log | Location |
|---|---|
| Orchestrator | `logs/orchestrator.log` |
| Each agent | `logs/<agent_name>.log` |
| State migration | `logs/state_migration.log` |

### Metrics

Per-job metrics in `state/metrics/<job_id>.json`:
```json
{
  "job_id": "daily_2026-10-14",
  "status": "SUCCESS",
  "last_success_stage": "24_final_health_audit",
  "attempts": 1,
  "error": null
}
```

### Health check

```bash
# Quick health
python -c "
from main import load_state
from datetime import datetime, timedelta, timezone
s = load_state()
now = datetime.now(timezone.utc)
for jid, j in sorted(s.jobs.items(), reverse=True)[:7]:
    print(f'{jid:25s} {j.status:12s} {j.updated_at[:19]}')
"
```

---

## 🚨 Known Limitations

1. **Agent file names start with digits** (`03_news_collection.py`) — Python modules can't be imported directly. `main.py` uses subprocess + `importlib.util` for dynamic loading.

2. **Hindi rendering in PDF** requires specific fonts (`src/fonts/Mukta-*.ttf`). Missing fonts → empty PDF.

3. **AI provider availability and quotas** — the router tries each configured provider in priority order, including Gemini, Groq, OpenAI-compatible endpoints, OpenRouter, Mistral, and NVIDIA NIM. Each provider still needs a valid key, accessible model, and available quota. Configure keys locally in `.env` and in GitHub Actions repository secrets; never commit credentials.

4. **Telegram message limit** — 4096 chars. Publisher auto-chunks long summaries.

5. **Fact verification is heuristic-first** — without LLM, some false positives may pass. Set `MIN_CONFIDENCE_THRESHOLD=0.5` for stricter filtering.

---

## 📜 License

See [LICENSE](LICENSE) (if present) or contact maintainers.

## 🤝 Contributing

1. Fork → branch → commit → PR
2. CI must pass (`lint`, `test`, `cli-contract`, `security`, `state-load`)
3. Follow existing code style (`ruff check .`)

## 📧 Contact

- Maintainer: [@agrilearningpoint](https://github.com/agrilearningpoint)
- Issues: [GitHub Issues](https://github.com/agrilearningpoint/daily-current-affairs/issues)

---

**Built with ❤️ for competitive exam students in India**


## Pipeline reliability and safe verification

- Install `libfribidi0` on Linux (`sudo apt-get install libfribidi0`) before rendering
  Hindi PDFs. Pillow's RAQM/HarfBuzz guard stays mandatory; it is not disabled to
  make tests pass. CI and the daily workflow install this native dependency.
- `pipeline.agent_context` owns job dates and paths. `pipeline.content` owns the
  source-grounded bilingual editor and MCQ APIs (restored from repository history).
- The collector, verifier and deduplicator now write edition-specific canonical
  JSON. Readers accept legacy lists and `items`/`articles` wrappers without using
  a different edition's latest file.
- Live content requires validated Hindi translation. Configure a supported LLM
  provider; missing/failed translation is a deliberate fail-closed quality gate.
  Offline `DRY_RUN=1` previews may use flagged dictionary fallback, but cannot
  create real Telegram publication records.
- Publishing requires a passing QA report for the same job **and the exact PDF
  SHA-256**, and rejects content needing translation review.
- `pytest tests/` now fails CI on errors rather than masking them with `|| true`.
  `tests/test_daily_integration.py` runs the real daily stage subprocesses using
  a local synthetic RSS feed through PDF, QA and Telegram dry-run. It makes no
  external news/AI/Telegram calls and does not modify the committed state.

```bash
python -m pytest tests/ -v
```

A green offline CI run verifies code/artifact contracts; it does not prove that
live feed endpoints, API quotas or Telegram channel permissions are available.


## Latest unattended verification and safe recovery

See [the 15 October 2026 detailed verification report](docs/verification-2026-10-15.md)
and its committed stage evidence/test logs. The opt-in offline verification guard
can exercise tests and inherited Python stage subprocesses without external DNS
or socket connections:

```bash
PYTHONPATH="$PWD/scripts/offline_network_guard:$PWD" \
  ALP_DISABLE_POLISH=1 ALP_DISABLE_LLM_VERIFY=1 python -m pytest -q
```

Synthetic dry-run PDFs are diagnostics, not real news or publication-ready Hindi.
Live publication requires exact PDF QA, verified provenance, completed translation
review, and matching document/pin receipts in `state/published_events.json` and
`state/pin_verification.json`.

A lost send acknowledgement is **not** automatically resent: reconcile the
pending/uncertain receipt against the actual channel first. Corrected PDFs for an
already-published edition require the manual workflow input `allow_revision`
(or `ALP_ALLOW_EDITION_REVISION=1` locally); this never overrides an uncertain send.
Model IDs can be set through the workflow repository variables shown in
`.env.example`. Live provider/Telegram health must be verified in deployment.
