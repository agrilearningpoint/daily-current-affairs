# Production Release Certification Report

**Audit Date (UTC):** `2026-11-28`  
**Repository:** `https://github.com/agrilearningpoint/daily-current-affairs`  
**Final Release Verdict:** **`PRODUCTION STABLE WITH DOCUMENTED LIMITATIONS`**

> [!IMPORTANT]
> **Certification Standard:** This report records strictly observed GitHub Actions runs, repository state ledgers (`state/jobs.json`, `state/published_events.json`, `state/pin_verification.json`), automated test results, PDF QA checks, and provider telemetry. No simulated or dry-run execution is presented as a live scheduled run, and 7-day stability is explicitly withheld until 7 consecutive real qualifying production days complete on the stabilized code.

---

## 1. Exact Verified Commits & GitHub Actions CI Status

- **Current Production HEAD Verified by CI ([`46133251929`](https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/46133251929)):**
  - **Commit:** `03308af56ecd0104f93d82f2cec142f985785a62` (`03308af`)
  - **CI Conclusion:** **`completed` / `success`** (`5/5` jobs passed in 3m 32s: `Security Scan`, `Lint & Syntax Check`, `Validate CLI Contracts`, `State File Load Test`, `Run Tests`).
  - **Payload:** Escalate short 429 backoff floor (`15s -> 300s`) on repeated strikes, preserve `:429` strikes across key rotations, isolate CI telemetry tests in `tmp_path`, and add operator `manual_ack` to `daily_2026-11-25`.
- **Baseline Stabilization Commit Verified by CI ([`46127781122`](https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/46127781122)):**
  - **Commit:** `8c377d3472fbc07749e0363937f298d283434ea1` (`8c377d3`)
  - **CI Conclusion:** **`completed` / `success`** (`5/5` jobs passed).
- **Latest Scheduled Full Live Daily Execution Commit:**
  - **Commit:** `ba1c1e2678f0d67aac9b3f9c4bce342d9d81d19c` (`ba1c1e2`, run [`46113998033`](https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/46113998033))
- **Remote Synchronization:** Local `main` is clean, tracked, and identical to `origin/main` at `03308af`.

---

## 2. CI Verification and Individual Job Evidence

The full CI workflow (`.github/workflows/ci.yml`) on `03308af` completed successfully:

| Job | Status | Conclusion | Gate Policy | Observed Results |
|---|---|---|---|---|
| **Lint & Syntax Check** | `completed` | `success` | Strict `py_compile`, JSON verification, and critical module verification; advisory best-effort lint | Passed all compile & schema checks |
| **Security Scan** | `completed` | `success` | Strict committed secrets check; advisory Bandit SAST | Zero secrets detected |
| **Validate CLI Contracts** | `completed` | `success` | Strict CLI smoke test & workflow arg validation | Passed |
| **State File Load Test** | `completed` | `success` | Strict JSON parse & key verification on `state/jobs.json` | Passed |
| **Run Tests** | `completed` | `success` | **Strict Hard Gate** (`DRY_RUN=1`, full `pytest tests/ -q --maxfail=5 --tb=short`) | All tests passed |

Local Verification: Re-executed full test suite under `DRY_RUN=1` (`python -m pytest tests/ -q --tb=short`) with **994 passed** in 7m 30s, `ruff check --select E9,F63,F7,F82 .` (0 errors), `scripts/diagnose.py` (0 errors, 54 passed), and `test_removed_providers_are_gone_everywhere` (1 passed).

---

## 3. Branch Protection and Repository Rulesets Audit

### A. Current Configuration Status
- Inspection of `https://api.github.com/repos/agrilearningpoint/daily-current-affairs/branches/main` shows:
  ```json
  "protected": false
  ```
- Unauthenticated requests to `/branches/main/protection` return `HTTP Error 401: Unauthorized`. The local execution environment does not possess administrative personal access tokens (`GITHUB_TOKEN` or `GH_TOKEN`), preventing programmatic mutation of repository settings.
- In accordance with production security protocol, settings must NOT be modified through unauthorized channels.

### B. Required Manual Configuration Steps for Repository Administrator
To secure the `main` branch against accidental direct pushes or merging unverified commits, the repository administrator should configure branch protection via the GitHub Web UI:

1. Navigate to: `https://github.com/agrilearningpoint/daily-current-affairs/settings/branches`
2. Under **Branch protection rules**, click **Add branch ruleset** (or **Add rule**).
3. Set **Branch name pattern** to: `main`
4. Enable **Require a pull request before merging**:
   - Check **Require approvals** (minimum 1 approval recommended).
   - Check **Dismiss stale pull request approvals when new commits are pushed**.
5. Enable **Require status checks to pass before merging**:
   - Check **Require branches to be up to date before merging**.
   - Search for and add the exact CI job names:
     - `Lint & Syntax Check`
     - `Security Scan`
     - `Validate CLI Contracts`
     - `State File Load Test`
     - `Run Tests`
6. Enable **Do not allow bypassing the above settings** (enforces rules on administrators as well).
7. Click **Save changes** (or **Create**).

---

## 4. Real Daily Workflow Evidence and Monitoring Plan

### A. Daily Workflow Executions Observed on Nov 28

| Run ID | Commit | Event | Conclusion | Execution Details |
|---|---|---|---|---|
| [`46113998033`](https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/46113998033) | `ba1c1e2` | `schedule` | **`success`** (`05:51:45Z -> 06:12:55Z`) | **Full live execution:** Stages 01–24 executed, uploaded checkpoints (`3.8 MB`) & logs (`58 KB`), state committed (`75517f0`/`d77eff9`), Telegram message published (`message_id=262`), channel pin verified. |
| [`46124668773`](https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/46124668773) | `f4aa6df` | `schedule` | `success` | Backup cron skip (`skip=true`): edition already published at `06:12:42Z`. |
| [`46126086305`](https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/46126086305) | `f4aa6df` | `schedule` | `success` | Backup cron skip (`skip=true`). |
| [`46127867698`](https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/46127867698) | `8c377d3` | `schedule` | `success` (`08:53:03Z -> 08:53:53Z`) | Backup cron skip (`skip=true`): duplicate prevention operational on `8c377d3`. |

### B. Next Real Scheduled Daily Execution (`daily_2026-11-29`)
- **Current Audit Time:** `2026-11-28 15:44 IST` (`10:14 UTC`).
- **Scheduled Window:** Daily staggered crons trigger across `01:00–06:40 IST` (`19:30–01:10 UTC`, first run `2026-11-28 19:30 UTC`).
- **Status:** **Awaiting Scheduled Execution** (Execution has not yet occurred).
- **Audit Verification Checklist for `daily_2026-11-29`:**
  - [ ] Triggered on commit `03308af` (or newer).
  - [ ] Confirmed full live execution (not a backup cron skip, manual no-op, or cached result).
  - [ ] All 24 pipeline stages (01 to 24) complete with status `success`.
  - [ ] `19_pdf_qa` passes with 0 critical defects (zero dangling sentences, valid page counts, >20% Devanagari).
  - [ ] PDF published to Telegram channel with valid `message_id` and SHA-256 registered in `state/published_events.json`.
  - [ ] Telegram pin verified and registered in `state/pin_verification.json`.

---

## 5. Groq HTTP 429 Rate-Limit Telemetry Audit & Structural Fix

### A. Root Cause Analysis of Historical Telemetry
- Telemetry analysis of `logs/ai_usage.jsonl` revealed:
  - **`daily_2026-11-22` Live Job:** 306 successful Groq calls vs 643 failures (including 641 HTTP 429 responses).
  - `04_fact_verification` used a `ThreadPoolExecutor` with multiple concurrent worker threads.
  - Groq returned `Retry-After: 1s–3s` headers (token-per-minute rate limit).
  - When a thread triggered a 429, `ai_router.py` rotated keys via `rotate_key()`, which invoked `_clear_provider_quota_state()`. That function previously erased the `:429` strike counter, resetting strikes back to `1`.
  - Consequently, concurrent threads repeatedly hammered Groq without escalating backoff duration.

### B. Structural Fix Implemented in `03308af` (`PFR-009`)
1. **Preserved 429 Strike History Across Key Rotations:**
   - Modified `_clear_provider_quota_state()` in `pipeline/ai_router.py` to preserve keys ending in `:429` during quota state resets.
2. **Escalated Exponential Backoff Floor on Repeated Strikes:**
   - In `report_failure()`, when `strikes >= 2`, an escalating exponential floor (`15s -> 30s -> 60s -> 120s -> 300s`) is enforced.
   - If Groq returns a tiny `Retry-After` (e.g. 1.2s), the router enforces `max(retry_after, floor)`, preventing tight-loop hammering.
3. **Structured Multi-Provider Fallback:**
   - When Groq remains rate-limited, requests fail over cleanly to Gemini (`gemini-3.5-flash-lite`), Mistral, or OpenRouter while strictly preserving `response_format={"type": "json_object"}` and Hindi language parameters.
4. **Telemetry Separation in Observability Reports:**
   - Updated `scripts/production_health_report.py` to explicitly segregate live production job rows (`1,062` rows) from synthetic test fixture rows (`307` rows).

---

## 6. Weekly and Monthly Workflow Evidence & Eligibility

### A. Schedule Eligibility Verification

| Period Job | Target Period Window | Min Required Days | Qualifying Published Editions in `state/jobs.json` | Next Live Scheduled Trigger | Status |
|---|---|---:|---|---|---|
| `weekly_2026-11-29` | `2026-11-23` to `2026-11-29` | `3` | **`5`** editions (`2026-11-23`, `24`, `26`, `27`, `28` with valid `checkpoint_run_id`; `25` failed and excluded) | Sunday `2026-11-29 02:30 UTC` (`08:00 IST`) | **Eligible / Awaiting Live Cron** |
| `monthly_2026-12-01` | `2026-11-01` to `2026-11-30` | `10` | **`25`** editions with valid `checkpoint_run_id` (Nov 19 missing checkpoint ID; Nov 25 failed) | Tuesday `2026-12-01 03:30 UTC` (`09:00 IST`) | **Eligible / Awaiting Live Cron** |

### B. Local Rebuild Verification
- Weekly PDF generation tested locally with saved artifacts (`daily_2026-11-17, 19, 22`): 38 pages generated, 0 QA defects, clean Devanagari rendering, out-of-window editions properly excluded.
- Monthly fail-closed guard tested: verified raising `ValueError` when fewer than 10 daily editions are available.

---

## 7. Artifact Accessibility and QA Inspection

### A. GitHub Actions Artifact Access Boundary
- Calls to `https://api.github.com/repos/agrilearningpoint/daily-current-affairs/actions/artifacts/{id}/zip` return `HTTP Error 401: Unauthorized` without authenticated credentials.
- Remote artifacts for `46113998033` are therefore documented as **uninspected locally**, while their successful publication and sha256 checksums were validated through the Telegram channel ledger.

### B. Local Master Edition Inspection
- The latest fully committed master edition on disk (`daily_2026-11-22.json`):
  - 15 stories, 15/15 MCQs approved (`examine_mcq_set` avg score: 95.2).
  - `hindi_editor.audit_edition_hindi` passed with 0 critical issues across 217 fields.
  - Re-rendered 35-page PDF passed `19_pdf_qa` with 0 issues (35/35 substantive pages, 31.9% Devanagari coverage, 391 images).
  - Visual review of rendered page PNGs (Cover, Table of Contents, Category Gallery, Story spreads, One-Liners) confirmed clean typography, zero font clipping, and proper alignment.

---

## 8. Seven-Day Monitoring Ledger

| Day | Date | Production Commit | Run ID | Pipeline Status | PDF SHA-256 (prefix) | Telegram / Pin | Operational Status |
|---|---|---|---|---|---|---|---|
| **Day 0** | `2026-11-28` | `ba1c1e2` (full) / `8c377d3` (backup skip) | `46113998033` / `46127867698` | `success` | `434263ea77ff0189` | `msg 262` / `verified` | Pre-stabilization execution; backup skip verified on `8c377d3` |
| **Day 1** | `2026-11-29` | `03308af+` | *Pending* | *Pending* | - | - | Awaiting scheduled run (`01:00–06:40 IST`) |
| **Day 2** | `2026-11-30` | `03308af+` | *Pending* | *Pending* | - | - | Awaiting scheduled run |
| **Day 3** | `2026-12-01` | `03308af+` | *Pending* | *Pending* | - | - | Awaiting scheduled run |
| **Day 4** | `2026-12-02` | `03308af+` | *Pending* | *Pending* | - | - | Awaiting scheduled run |
| **Day 5** | `2026-12-03` | `03308af+` | *Pending* | *Pending* | - | - | Awaiting scheduled run |
| **Day 6** | `2026-12-04` | `03308af+` | *Pending* | *Pending* | - | - | Awaiting scheduled run |
| **Day 7** | `2026-12-05` | `03308af+` | *Pending* | *Pending* | - | - | Awaiting scheduled run |

**Completed Qualifying Days on Stabilized Code (`03308af+`):** **`0 / 7`**

---

## 9. Failure Register & Open Limitations

1. **Seven-Day Stability Window Pending:** `0 / 7` days completed on the stabilized codebase (`03308af`). Full Daily execution scheduled to begin `2026-11-29 01:00 IST`.
2. **Weekly & Monthly Scheduled Execution Pending:** First post-stabilization weekly run scheduled for Sunday `2026-11-29 02:30 UTC`; monthly run scheduled for Tuesday `2026-12-01 03:30 UTC`.
3. **Branch Protection Pending Manual Configuration:** Repository administrator must manually apply the recommended branch ruleset in GitHub settings.
4. **Historical Watchdog Backlog Handled:** `daily_2026-11-25` failure preserved in `jobs.json` with `manual_ack=True`. Watchdog returns `rc=0` with `manual_attention=[]`.
5. **Local Artifact Access Boundary:** Remote artifact inspection from local environment remains gated by GitHub API authentication requirements.

---

## 10. Final Release Recommendation & Verdict

**Final Verdict:** **`PRODUCTION STABLE WITH DOCUMENTED LIMITATIONS`**

### Summary Rationale:
- The system is architecturally complete, with 994 passing tests and a successful GitHub CI run (`46133251929`) on commit `03308af`.
- All identified root causes (dangling Hindi sentence detection, numeric MCQ option false positives, Groq HTTP 429 tight-loop hammering, and watchdog recovery reconciliation) have been resolved and verified with regression tests.
- In accordance with rigorous production engineering standards, the certification verdict cannot be upgraded to `PRODUCTION CERTIFIED` until 7 consecutive real scheduled daily executions and live weekly/monthly runs successfully execute and pass all quality gates.
