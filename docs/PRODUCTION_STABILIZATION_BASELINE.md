# Production Stabilization Baseline

**Audit Timestamp (UTC):** `2026-11-28`  
**Repository:** `https://github.com/agrilearningpoint/daily-current-affairs`  
**Verified HEAD / `origin/main` Commit:** `f4aa6df715b4255a50d9ef60b363e4d81dbbc9a9` (`f4aa6df`)  
**Working Tree Status (Baseline):** Clean (`0` uncommitted changes)  
**Prior Audit Report Status:** `PRODUCTION READY WITH DOCUMENTED LIMITATIONS` ([PRODUCTION_TEST_REPORT.md](file:///C:/Users/lenovo/dailycurrent%20affairs%20repo/daily-current-affairs/docs/PRODUCTION_TEST_REPORT.md))

---

## 1. Exact Commit vs Workflow Run Mapping

Recent GitHub Actions runs verified from the live GitHub API (`repos/agrilearningpoint/daily-current-affairs/actions/runs`):

| Run ID | Workflow | Commit SHA | Event | Status / Conclusion | Timestamp (UTC) | Notes |
|---|---|---|---|---|---|---|
| `46123057076` | `CI` | `f4aa6df` | `push` | `completed` / **`success`** | `2026-11-28T07:50:46Z` | All 5 jobs passed (`Security Scan`, `Lint & Syntax Check`, `Run Tests`, `State File Load Test`, `Validate CLI Contracts`). Latest hardening commit verified by CI. |
| `46116996405` | `CI` | `5f69eb2` | `push` | `completed` / **`success`** | `2026-11-28T06:31:24Z` | Docs update commit before `f4aa6df`. |
| `46115569462` | `Autonomous Self-Healing & Recovery Agent` | `d77eff9` | `workflow_run` | `completed` / `skipped` | `2026-11-28T06:12:59Z` | Correctly skipped because `46113998033` succeeded. |
| `46113998033` | `Daily News Pipeline` | `ba1c1e2` | `schedule` | `completed` / **`success`** | `2026-11-28T05:51:45Z` | Live `daily_2026-11-28` succeeded through `24_final_health_audit`. Predates `f4aa6df`. |
| `46110164947` | `CI` | `ba1c1e2` | `push` | `completed` / **`success`** | `2026-11-28T05:01:09Z` | Phase 0-15 architecture upgrade commit. |
| `46109271881` | `Autonomous Self-Healing & Recovery Agent` | `4c41c02` | `workflow_run` | `completed` / `success` | `2026-11-28T04:48:59Z` | Ran on pre-upgrade `46109187666` failure; logged `escalated_budget_exhausted` in `state/healing_history.json`. |
| `46109187666` | `Daily News Pipeline` | `9905e74` | `schedule` | `completed` / **`failure`** | `2026-11-28T04:47:50Z` | **Pre-upgrade failure:** `19_pdf_qa` failed 3 attempts with `[ERROR] [truncated_dangling_sentence] PDF contains truncated sentence ending mid-thought: 'रुपये'`. |
| `46108929346` | `Watchdog` | `6752fa1` | `schedule` | `completed` / **`failure`** | `2026-11-28T04:44:28Z` | Failed at `Report state errors or exhausted recovery budget` due to `daily_2026-11-25` and `daily_2026-11-28` in `recovery_plan.json`. |
| `46105777208` | `Daily News Pipeline` | `d6692ce` | `schedule` | `completed` / **`failure`** | `2026-11-28T04:03:55Z` | Earlier Nov 28 attempt (`4c41c02` diff shows same `truncated_dangling_sentence`: `'रुपये'`). |
| `45296664371` | `Weekly Current Affairs` | `653d310` | `schedule` | `completed` / **`failure`** | `2026-11-24T00:22:45Z` | **Pre-upgrade commit:** `weekly_2026-11-22` failed `19_pdf_qa` (`news-agency recognition`, `dangling_preposition_in_mcq`, `explanation_dateline_leakage`). |
| `41610866391` | `Monthly Current Affairs` | `74b7032` | `schedule` | `completed` / **`failure`** | `2026-11-03T09:25:12Z` | **Pre-upgrade commit:** workflow failed to start jobs; `monthly_2026-11-01` remains `pending` in `state/jobs.json`. |

> [!IMPORTANT]
> No scheduled `Daily News Pipeline`, `Weekly Current Affairs`, or `Monthly Current Affairs` live run has executed on commit `f4aa6df` yet. `Daily News Pipeline` `46113998033` succeeded on `ba1c1e2`, and `CI` `46123057076` succeeded on `f4aa6df`.

---

## 2. State & Job Ledger Snapshot (`state/jobs.json` & `recovery_plan.json`)

- **Recent Daily Jobs:**
  - `daily_2026-11-20` through `daily_2026-11-24`: `success` (`24_final_health_audit`, `1` attempt each)
  - `daily_2026-11-25`: **`failed`** (`7` attempts, last success `18_pdf_design`, failed stage `19_pdf_qa`)
  - `daily_2026-11-26`: `success` (`24_final_health_audit`, `1` attempt)
  - `daily_2026-11-27`: `success` (`24_final_health_audit`, `1` attempt)
  - `daily_2026-11-28`: **`success`** (`8` total attempts; failed on pre-`ba1c1e2` runs through `04:48Z`, then succeeded on run `46113998033` at `06:12Z`)
- **Weekly & Monthly Jobs:**
  - `weekly_2026-11-01`, `weekly_2026-11-15`: `success`
  - `weekly_2026-11-08`: `pending` (stopped at `22_telegram_publisher`)
  - `weekly_2026-11-22`: **`failed`** (`6` attempts, failed stage `19_pdf_qa` on pre-upgrade `653d310`)
  - `monthly_2026-11-01`: `pending` (`6` attempts, stopped at `19_pdf_qa` on `2026-11-02`)
- **Stale `recovery_plan.json`:** Still lists `daily_2026-11-28` under `recent_failed_final` / `manual_attention` (timestamp `2026-11-28T04:44:38Z`), even though `daily_2026-11-28` subsequently recovered to `success` at `06:12:47Z`.

---

## 3. Root Cause Analysis of 28 November `truncated_dangling_sentence` Failure

Inspected from git commit `4c41c02` (`state/jobs.json` for `daily_2026-11-28` at `04:04:49Z` & `04:48:43Z`):
- **Observed QA Error:** `[ERROR] [truncated_dangling_sentence] PDF contains truncated sentence ending mid-thought: 'रुपये'` (PDF had `32` pages, `59544` chars, `15` MCQs, `383` images, `0` blank pages).
- **Root Causes in Code (`agents/19_pdf_qa.py`, `pipeline/content.py`, `pipeline/content_sanitizer.py`, `src/generate_pdf.py`):**
  1. **PDF line-wrap regex collision in `agents/19_pdf_qa.py:729-733`:** `dangling_sentence_re` matches `r"रुपये\s*(?:\n|$)"` across extracted PDF page text. Whenever ReportLab wraps a completely valid Hindi monetary sentence immediately after `रुपये` (e.g., `"5 लाख रुपये\nका स्वास्थ्य कवर..."`), `\n` triggers a false-positive `truncated_dangling_sentence` block.
  2. **Genuine upstream incomplete-Hindi / dangling-token risk:** `pipeline/content.py` / `agents/12_content_editor.py` / `src/generate_pdf.py` did not uniformly strip/repair dangling Hindi endings (`लागत लगभग रुपये`, standalone `रुपये`, `के लिए`, incomplete postpositions) across every student-facing text field (`summary_hi`, `key_points_hi`, `detailed_explanation_hi`, `one_liner_hi`, `exam_fact_hi`, MCQ explanations) before PDF rendering, nor trigger reserve replacement if content remained malformed.
  3. **Diagnostic message specificity:** `19_pdf_qa.py` did not print surrounding context or preserve which line triggered `truncated_dangling_sentence`, making automated repair routing harder.

---

## 4. Documented Limitations & Stabilization Backlog

1. **Daily Truncation Fix Needed (Phase 1):** Fix dangling `रुपये` / incomplete Hindi endings at source editorial/sanitizer stages AND distinguish genuine dangling sentence endings from valid wrapped lines ending in `रुपये\n` inside `19_pdf_qa.py`.
2. **Observability Fragmentation (Phase 2):** Telemetry exists across `state/jobs.json`, `state/published_events.json`, `logs/qa/`, `logs/provider_health.json`, `logs/provider_summary.json`, and `scripts/run_summary.py`, but lacks a centralized dashboard & CSV/JSON export (`docs/PRODUCTION_HEALTH_DASHBOARD.md`).
3. **Auto-Heal & Watchdog Alignment (Phase 3):**
   - `auto-heal.yml` runs `unittest discover -s tests -p "test_enterprise_*.py"` (no matching files in `tests/`, so `0` tests executed during auto-heal gating).
   - `agents/25_auto_healer.py` classifies `truncated_dangling_sentence` as generic `github_actions_failure` instead of a recoverable editorial/QA repair routing back through `12_content_editor` -> `18_pdf_design` -> `19_pdf_qa`.
   - `recovery_plan.json` / `watchdog` does not clear resolved jobs cleanly or keep bounded retry telemetry in `state/jobs.json`.
   - Scheduled `daily_2026-11-28` recovered only after manual architecture push (`ba1c1e2`), not via automated Stage-19 -> Stage-12 repair loop on the earlier failures.
4. **Pending Live Weekly/Monthly & 7-Day Track Record (Phases 7 & 9):** Live `weekly.yml` (Sunday `02:30 UTC`), `monthly.yml` (1st of month `03:30 UTC`), and 7 consecutive clean daily production runs remain to be observed in real time after stabilization changes deploy.
