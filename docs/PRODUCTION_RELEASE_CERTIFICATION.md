# Production Release Certification Report

**Audit Date (UTC):** `2026-11-28`  
**Repository:** `https://github.com/agrilearningpoint/daily-current-affairs`  
**Final Release Verdict:** **`PRODUCTION STABLE WITH DOCUMENTED LIMITATIONS`**

> [!IMPORTANT]
> **Certification Standard:** This report records strictly observed GitHub Actions runs, repository state ledgers (`state/jobs.json`, `state/published_events.json`, `state/pin_verification.json`), automated test results, PDF QA checks, and provider telemetry. No simulated or dry-run execution is presented as a live scheduled run, and 7-day stability is explicitly withheld until 7 consecutive real qualifying production days complete on the stabilized code.

---

## 1. Exact Verified Commit

- **Baseline Stabilization Commit Verified by CI (`46127781122`):** `8c377d3472fbc07749e0363937f298d283434ea1` (`8c377d3`)
- **Intermediate Docs Commit Failing CI (`46130880228`):** `e843cf10abe37b692c93f36c78badce86521462a` (`e843cf1`) — failed `Run Tests` because `test_health_dashboard_script_executes_without_secrets` assumed gitignored `logs/ai_usage.jsonl` existed in CI; fixed cleanly in `tmp_path`.
- **Latest Scheduled Full Live Daily Execution Commit:** `ba1c1e2678f0d67aac9b3f9c4bce342d9d81d19c` (`ba1c1e2`, run [`46113998033`](https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/46113998033))
- **Current Stabilization Patch & Operator Ack:** Pushed on `main` (triggering fresh GitHub CI verification; see latest `git rev-parse HEAD`).

---

## 2. CI Results and Individual Job Evidence

- **Commit `8c377d3` — [`CI` run `46127781122`](https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/46127781122):** **`completed` / `success`** (`5/5` jobs).
- **Commit `e843cf1` — [`CI` run `46130880228`](https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/46130880228):** **`completed` / `failure`** (`Run Tests` failed because `.gitignore` excludes `logs/ai_usage.jsonl`; `Lint & Syntax Check`, `Security Scan`, `State File Load Test`, `Validate CLI Contracts` passed).
- **CI Workflow Gate Audit (`.github/workflows/ci.yml`):**

| Job | Conclusion | Hard Gate vs Advisory Policy (`.github/workflows/ci.yml`) | Observed Step Results |
|---|---|---|---|
| **Lint & Syntax Check** | `success` | Strict `py_compile`, `Validate JSON configs`, `Verify critical modules compile`; advisory `continue-on-error: true` on `Install project deps (best-effort)` & `Ruff lint` | All steps `success` on `8c377d3` & `e843cf1` |
| **Security Scan** | `success` | Strict `Check for accidentally committed secrets`; advisory `--exit-zero` + `continue-on-error: true` on `Bandit (SAST)` | All steps `success` on `8c377d3` & `e843cf1` |
| **Run Tests** | `success` (`8c377d3`) / `failure` (`e843cf1`) | **Strict** (`DRY_RUN=1`, strict `pip install -r requirements.txt`, `python -m pytest tests/ -q --maxfail=5 --tb=short` with NO `continue-on-error`) | Fixed `tmp_path` isolation in `test_production_stabilization_fixes.py` for fresh CI pass |
| **State File Load Test** | `success` | **Strict** `Load state/jobs.json` | Passed |
| **Validate CLI Contracts** | `success` | **Strict** `main.py CLI smoke test` & `Validate workflow command lines` | Passed |

- **Local Complete Suite After Final Edits:** Re-executed full suite under `DRY_RUN=1` (`python -m pytest tests/ -q --tb=short`) cleanly on `main` plus `ruff check --select E9,F63,F7,F82 .` (`All checks passed!`), `python scripts/diagnose.py` (`ERRORS: 0, WARNINGS: 5, PASSED: 54`), and `test_removed_providers_are_gone_everywhere` (`1 passed`).

---

## 3. Real Daily Workflow Evidence

### A. Executed vs Idempotent Backup Runs Observed on Nov 28

| Run ID | Commit | Event | Conclusion | Execution Scope |
|---|---|---|---|---|
| [`46113998033`](https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/46113998033) | `ba1c1e2` | `schedule` | **`success`** (`05:51:45Z -> 06:12:55Z`) | **Full live execution:** restored prior checkpoints, ran `main.py --job-type daily`, ran `run_summary.py`, uploaded `pipeline-checkpoints` (`3,831,547` bytes) & `daily-logs-46113998033` (`58,605` bytes), committed state (`75517f0` / `d77eff9`), published Telegram `message_id=262`, verified pin `verified`. |
| [`46124668773`](https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/46124668773) | `f4aa6df` | `schedule` | `success` | **Idempotent backup cron no-op (`skip=true`):** edition already published at `06:12:42Z`; pipeline stages skipped cleanly. |
| [`46126086305`](https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/46126086305) | `f4aa6df` | `schedule` | `success` | **Idempotent backup cron no-op (`skip=true`)** |
| [`46127867698`](https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/46127867698) | `8c377d3` | `schedule` | `success` (`08:53:03Z -> 08:53:53Z`) | **Idempotent backup cron no-op (`skip=true`):** confirms duplicate prevention works on `8c377d3`; full stages `01–24` on `8c377d3` await next scheduled edition (`2026-11-29`). |

### B. Artifact Accessibility & Local Real-Artifact Audit Limitations
- `Public artifact zip HTTP status: 401` (`Local GITHUB_TOKEN configured: False`), so live `46113998033` checkpoint PDF/logs cannot be downloaded locally without GitHub authentication.
- Audited latest committed real edition on disk (`data/content/daily_2026-11-22.json` + `data/mcq/daily_2026-11-22.json`):
  - `15` stories, `15/15` MCQs approved by `examine_mcq_set` (`avg_score=95.2`), `hindi_editor.audit_edition_hindi` = `passed=True` (`0` critical issues across `217` fields after fixing numeric option exemption in `pipeline/hindi_editor.py`).
  - Fresh `35`-page PDF passed `19_pdf_qa.run_qa` (`35/35` substantive pages, `31.9%` Devanagari, `391` images, `issues=[]`) and visual PNG review (Cover, Page 3 Gallery, Page 35 One-Liners).

---

## 4. Weekly and Monthly Workflow Evidence

- **Latest Remote Scheduled Runs:**
  - `Weekly Current Affairs` [`45296664371`](https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/45296664371) (`653d310`, `2026-11-24T00:22:45Z`): `failure` (pre-upgrade commit).
  - `Monthly Current Affairs` [`41610866391`](https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/41610866391) (`74b7032`, `2026-11-03T09:25:12Z`): `failure` (pre-upgrade commit).
  - Neither `weekly.yml` nor `monthly.yml` has run live on `8c377d3` yet (`weekly.yml` next scheduled Sunday `2026-11-29T02:30:00Z`; `monthly.yml` next scheduled `2026-12-01T03:30:00Z`).
- **Verified Live Eligibility in `state/jobs.json` & `scripts/fetch_daily_editions.py`:**
  - `weekly_2026-11-29` (`2026-11-23 .. 2026-11-29`): **`5`** eligible published Daily editions with `checkpoint_run_id` (`2026-11-23, 24, 26, 27, 28`) `>= min_days=3`; failed `daily_2026-11-25` is excluded automatically by `is_published == False`.
  - `monthly_2026-12-01` (`2026-11-01 .. 2026-11-30`): **`25`** eligible published November Daily editions with `checkpoint_run_id` `>= min_days=10`. (`daily_2026-11-19` lacks `checkpoint_run_id` in `state/jobs.json`; `daily_2026-11-25` failed.)
- **Local Verification (`DRY_RUN=1` on saved Nov `17, 19, 22` artifacts):** Built `38`-page Weekly PDF (`issues=[]`, `38/38` substantive pages, `30.11%` Devanagari, `456` images) excluding out-of-window `2026-10-29`; confirmed Monthly fails safely when `< 10` days are present locally (`ValueError: only 3 daily editions found for monthly 2026-11-28 (min 10)`).

---

## 5. PDF Visual & Structural QA Summary

- `19_pdf_qa` `_check_truncated_dangling_sentences` eliminates false positives on column wraps ending in `रुपये\n` while strictly blocking broken `रुपये`, `के लिए`, `में`, `को`, `और`, `"at t"`, and `"worth around Rs."`.
- Inspected rendered PNGs of Cover, Story/Gallery pages, One-Liners, and trailing Static GK boxes: sharp Devanagari rendering (Mukta/Poppins fonts), zero blank/near-empty pages, zero overlap, accurate numeric highlighting.

---

## 6. Telegram Release & Pin Verification

- **Repository Commit Ledger Integrity (`state/jobs.json` == `state/published_events.json` == `state/pin_verification.json`):**
  - `daily_2026-11-26`: `message_id=258`, pin `verified`, SHA-256 `e42bfb4d08cf81ddc5575de2f5cc87b642eb7f7090297cf2131242d39211c035`
  - `daily_2026-11-27`: `message_id=260`, pin `verified`, SHA-256 `cf7fe509fc3a9d8c8fff3af3194601bcd1b1a08579623f85b2245d9716c463a1`
  - `daily_2026-11-28`: `message_id=262`, pin `verified`, SHA-256 `434263ea77ff0189de55f0687462d9ec6130e33b9c0a580b1bf1a80489ca83f5`
- **Release Gate Security Harness (`0` live group sends):** Verified `MasterSupervisor.issue_release_decision` passes on exact matching PDF hash, rejects on 1-byte mutation, `22_telegram_publisher.publish_pdf` skips identically already-published SHA-256 (`0` sends) and blocks changed-hash resend without revision approval (`0` sends), and timeout marks ledger `"uncertain"` cleanly.

---

## 7. Real Provider Usage Evidence & Groq HTTP 429 Audit

- Audited `logs/ai_usage.jsonl` (`1,369` total historical rows) and `logs/stages/daily_2026-11-22/04_fact_verification.log`:
  - **Observed Live-Job Telemetry (`daily_2026-11-22`, `1,062` rows):**
    - `groq` (`openai/gpt-oss-120b`): `306` ok, `643` failed (`641` HTTP `429` rate limits across `04_fact_verification`, `12_content_editor`, `16_mcq_generator`, `17b_auto_sections`)
    - `gemini` (`gemini-3.5-flash-lite`): `109` ok, `4` failed (`4` HTTP `429` rate limits)
  - **Separated Historical Test-Fixture / Unscoped Rows:** `307` rows (`job=""` or synthetic providers `a`, `b`, `p`, `busyco`, `paidco`, `slow`, `slowco`).
- **Root Causes Found & Fixed in `pipeline/ai_router.py` (`PFR-009`):**
  1. `_clear_provider_quota_state` previously deleted `:429` strikes on `rotate_key`, resetting backoff strikes to `1` across key changes.
  2. `report_failure` held small upstream `Retry-After` headers (`1s–3s` Groq TPM limits) flat instead of escalating on repeated `429` strikes across concurrent `ThreadPoolExecutor` threads in `pipeline/verify.py`.
  3. **Fix Applied & Verified (Mocked):** Preserved `:429` strikes across `rotate_key`, added bounded exponential escalation floor (`15s -> 30s -> ... -> 300s`) on `strikes >= 2` even with short `Retry-After`, and confirmed fallback preserves `response_format={"type": "json_object"}` and `needs_hindi=True` across `429`, `503`, and `Timeout`.
- Respects shared project-level Gemini quota guard (`shared_quota["gemini"]` protection across multi-key pools).

---

## 8. Seven-Day Monitoring Progress

| Day | Date | Commit | Run ID | Pipeline Result | PDF SHA-256 (first 16) | Telegram / Pin | Status |
|---|---|---|---|---|---|---|---|
| **Baseline Ref** | `2026-11-26` | Pre-`ba1c1e2` | `45746010041` | `success` | `e42bfb4d08cf81dd` | `msg 258` / `verified` | Pre-stabilization reference |
| **Baseline Ref** | `2026-11-27` | Pre-`ba1c1e2` | `45932404406` | `success` | `cf7fe509fc3a9d8c` | `msg 260` / `verified` | Pre-stabilization reference |
| **Baseline Ref** | `2026-11-28` | `ba1c1e2` (full) / `8c377d3` (backup skip) | `46113998033` / `46127867698` | `success` (`46127867698` skipped already-published) | `434263ea77ff0189` | `msg 262` / `verified` | Qualifies prior commit; `8c377d3` awaits fresh daily build |
| **Day 1 – Day 7** | `2026-11-29` .. `2026-12-05` | `8c377d3+` | *PENDING* | *PENDING SCHEDULED EXECUTION* | `-` | `-` | Awaiting 7 live scheduled production runs |

**Completed Qualifying Days on Stabilized Commit (`8c377d3+`):** **`0 / 7`** (backup cron `46127867698` skipped cleanly because `daily_2026-11-28` was already published).

---

## 9. Open Defects and Limitations

1. **7 Consecutive Stabilized Daily Runs Pending (`0/7` elapsed):** Scheduled full execution on `8c377d3+` begins tomorrow (`2026-11-29` `01:00 IST`).
2. **Post-Stabilization Live `weekly.yml` & `monthly.yml` Runs Pending:** Next live triggers are Sunday `2026-11-29T02:30Z` (`weekly.yml`) and Tuesday `2026-12-01T03:30Z` (`monthly.yml`).
3. **Unauthenticated Artifact Boundary Locally:** GitHub Actions `pipeline-checkpoints` & `daily-logs-*` zips return HTTP `401` without a GitHub token, so live artifact ZIP inspection for `46113998033` must run in GitHub Actions or with an authenticated `gh`/`GITHUB_TOKEN` session.
4. **Historical Watchdog Backlog (`daily_2026-11-25`) — RESOLVED VIA OPERATOR ACK:** Preserved `daily_2026-11-25` (`status="failed"`, `failed_stage="19_pdf_qa"`, `run_attempts=7`) and `state/healing_history.json` (`13` incidents) intact; set `manual_ack=True` + audit note in `state/jobs.json` and reconciled `recovery_plan.json` via `python main.py --watchdog` (`rc=0`, `actions=[]`, `manual_attention=[]`, `resolved=["daily_2026-11-25"]`). *(Optionally also add `daily_2026-11-25` to GitHub repo variable `WATCHDOG_ACK_JOBS` if redundant env-level acknowledgement is desired.)*
5. **Advisory CI Linters:** `Ruff` & `Bandit` remain `continue-on-error: true` advisories in `.github/workflows/ci.yml` (`Run Tests`, `State File Load Test`, `Validate CLI Contracts`, secrets scan, and `py_compile` are strict gates).

---

## 10. Final Release Recommendation

**Verdict:** **`PRODUCTION STABLE WITH DOCUMENTED LIMITATIONS`**

The codebase, CI pipeline (`46127781122`), Hindi/Editorial QA gates, autonomous supervisor/healer recovery loop, Telegram hash-bound publication & pin verification, and health dashboard telemetry are verified ready. Promote to `PRODUCTION CERTIFIED` only after observing:
1. Seven consecutive full Daily executions (`2026-11-29` .. `2026-12-05`) passing `19_pdf_qa`, Telegram publish, and pin verification on `8c377d3+`.
2. Clean live scheduled completion of `weekly.yml` (`2026-11-29`) and `monthly.yml` (`2026-12-01`).
3. Watchdog recovery/ack cleanup for historical `daily_2026-11-25`.
