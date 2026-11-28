# Production Certification & Test Verification Report

**Baseline Commit Audited:** `ba1c1e2678f0d67aac9b3f9c4bce342d9d81d19c` (`ba1c1e2` on `main`)  
**Certification Verdict:** **Offline / CI Gates PASSED — Pending Live Scheduled Production Run (`daily.yml` / `weekly.yml`) with Repository Secrets for End-to-End Live API Certification**

This report separates every verification category and cites **only directly observed outputs**. Mocked tests are never reported as live API calls, and fixture runs are distinguished from real saved edition artifacts.

---

## 1. Automated Tests (`DRY_RUN=1`)

- **Command:** `$env:DRY_RUN="1" ; python -m pytest tests/ -q --tb=short`
- **Observed Result:** **`953 passed in 435.32s (0:07:15)`** (`0` failed, `0` skipped, exit code `0`).
- **Static & Repository Health Checks:**
  - `ruff check --select E9,F63,F7,F82 .`: **All checks passed** (`0` critical syntax/undefined-name errors).
  - `python scripts/diagnose.py`: **`ERRORS: 0, WARNINGS: 5, PASSED: 54`** (`271` valid JSON files, `69` feeds / `65` enabled sources).
  - `pytest tests/test_all_keys.py -k "test_removed_providers_are_gone_everywhere"`: **PASSED** across codebase and all `docs/*.md`.

---

## 2. Multi-Key API Slot Audit (Mocked HTTP / Router Calls)

Executed in an isolated temporary directory (`ALP_AI_HEALTH_FILE` + `ALP_AI_USAGE_LOG`, `ALP_MODEL_AUTO_DISCOVERY=0`, `ALP_KEY_SCHEDULING=least_used`) with mocked `_call_provider` responses. **No live provider API calls were made.**

- **Verified Capabilities:**
  - **Key Discovery:** Discovered `gemini` (`4` slots: `GEMINI_API_KEY`, `_1`, `_2`, `_3`), `openai` (`2` slots: `OPENAI_API_KEY`, `_1`), `groq` (`2` slots: `GROQ_API_KEY`, `_1`), `mistral`, `openrouter`, `cohere`, and `nvidia`.
  - **Same-Task 429 Rotation:** `openai:OPENAI_API_KEY` returned `RATE_LIMIT` -> rotated seamlessly in the same task to `openai:OPENAI_API_KEY_1` (`ok-response`, `slot0_blocked=True`, `slot1_blocked=False`).
  - **Auth Error Isolation & Provider Fallback:** `groq:GROQ_API_KEY` returned `AUTH_ERROR` (`86400s` cooldown, `auth_status="invalid"`) -> rotated to `groq:GROQ_API_KEY_1` -> when Groq slots hit 429, fell back cleanly to `mistral:PRIMARY` (`mistral-fallback-ok`).
  - **Shared Project Quota Guard:** `3` Gemini slots hitting `429` within `60s` triggered `shared_quota["gemini"] = True`, halting wasted retries rather than assuming independent quotas across shared GCP keys.
  - **Cooldown Expiry Recovery:** Blocking `nvidia#slot:0` for `1.0s` confirmed `blocked_during=True` and `blocked_after_expiry=False` after `1.15s`.
  - **Cross-Restart Persistence:** After `ai_router._reset_health()` cleared RAM, `_health_load()` restored identical `key_stats` across all `8` active slots (`matches_pre_restart=True`) and `ai_usage.build_provider_summary()` aggregated `9` calls from `ai_usage.jsonl` with **`secrets_leaked=False`**.

### Anonymized Key-Slot Utilization Summary (Mocked Audit Run)

| Slot ID | Requests | Successes | Failures | Rate Limits | Tokens Total | Auth Status | Error Category |
|---|---:|---:|---:|---:|---:|---|---|
| `openai:OPENAI_API_KEY` | 1 | 0 | 1 | 1 | 0 | `healthy` (cooled) | `rate_limit` |
| `openai:OPENAI_API_KEY_1` | 1 | 1 | 0 | 0 | 35 | `healthy` | `null` |
| `groq:GROQ_API_KEY` | 1 | 0 | 1 | 0 | 0 | `invalid` (`86400s`) | `auth_error` |
| `groq:GROQ_API_KEY_1` | 2 | 1 | 1 | 1 | 35 | `healthy` (cooled) | `rate_limit` |
| `mistral:PRIMARY` | 1 | 1 | 0 | 0 | 45 | `healthy` | `null` |
| `gemini:GEMINI_API_KEY` | 1 | 0 | 1 | 1 | 0 | `healthy` (shared quota) | `rate_limit` |
| `gemini:GEMINI_API_KEY_1` | 1 | 0 | 1 | 1 | 0 | `healthy` (shared quota) | `rate_limit` |
| `gemini:GEMINI_API_KEY_2` | 1 | 0 | 1 | 1 | 0 | `healthy` (shared quota) | `rate_limit` |
| `gemini:GEMINI_API_KEY_3` | 0 | 0 | 0 | 0 | 0 | `unknown` (spared) | `null` |

---

## 3. Fault-Injection Results (13 Injected Defects + Repair Lifecycle)

All 13 defects were injected against the actual committed modules in isolated temp workspaces:

| # | Injected Defect | Observed Result | Responsible Agent / Module | Notes |
|---|---|---|---|---|
| 1 | Incorrect MCQ answer | **Blocked** | `16_mcq_generator` / `17_mcq_validator` / `mcq_examiner` | Rejected by both `validate_mcqs` and `examine_mcq_set` (`score=65`, `wrong key` diagnostic). |
| 2 | Duplicate MCQ | **Blocked** | `16_mcq_generator` / `17_mcq_validator` | Rejected by `validate_mcqs` (`rejected_count=2`). |
| 3 | Missing Hindi translation | **Blocked** | `12_content_editor` / `completeness` / `22_telegram_publisher` | `validate_content_completeness` returned `passed=False` (`missing_headline_hi`); live publish blocks when `needs_review=True`. |
| 4 | Broken Devanagari text | **Partial** | `hindi_editor` / `19_pdf_qa` | `hindi_editor` collapsed double-halant (`\u094d\u094d` -> `\u094d`), but did not strip `\ufffd`; `\ufffd` is blocked at PDF QA via `check_glyph_integrity`. |
| 5 | Missing news image | **Graceful Degrade** | `18_pdf_design` / `19_pdf_qa` | `image_stats.skipped_no_image` increments cleanly; PDF renders and passes QA without crash. |
| 6 | Irrelevant image / bad logo URL | **Blocked** | `news_images` (`18_pdf_design`) | `commons_title_matches` rejected mismatched title; `plausible_image_url` rejected `default-avatar-logo-placeholder.png`. |
| 7 | Unsupported numerical claim | **Flagged Unverified** | `04_fact_verification` (`ClaimVerifier`) | `"9.75%"` vs `"6.50%"` returned `verified=False` (`"0/1 numeric claims matched in source"`). Spelled-out `"9.75 percent"` (without `%`) is not extracted as checkable numeric claim, still failing closed as `verified=False`. |
| 8 | Duplicate Static GK | **Partial** | `17c_static_gk_validator` / `19_pdf_qa` / `20_weekly_editor` | Generic filler (`Currency – Indian Rupee`) is rejected (`passed=False`) by `19_pdf_qa`; `period_builder.pick_agri_corner` deduplicated `2 -> 1`. Daily `17c` validates factual truth against `current_facts.json` rather than cross-story non-filler deduplication. |
| 9 | Missing Agriculture Corner | **Blocked (Strict)** | `17b_auto_sections` / `MasterSupervisor` | In `DRY_RUN=0`, `MasterSupervisor.observe_and_critique("17b_auto_sections")` flagged `REPAIR_REQUIRED` with `repair_target="17b_auto_sections"`. |
| 10 | Clipped headline | **Partial** | `content_sanitizer` / `19_pdf_qa` | `repair_dangling_sentence` repairs trailing prepositions (`" in"`), and `19_pdf_qa` blocks mid-thought monetary truncations (`truncated_dangling_sentence`), while `"..."` alone in story headline text yielded `qa_detected_codes=[]`. |
| 11 | Corrupt PDF | **Blocked** | `18_pdf_design` / `19_pdf_qa` / `MasterSupervisor` | With `config/supervisor_policy.json`, `MasterSupervisor` returned `REPAIR_REQUIRED` (`"invalid PDF header"`, target `18_pdf_design`), and `19_pdf_qa.run_qa` failed. |
| 12 | Missing QA report | **Blocked** | `19_pdf_qa` / `22_telegram_publisher` | `publish_pdf` returned `False`. |
| 13 | Stale QA report (wrong SHA-256) | **Blocked** | `19_pdf_qa` / `22_telegram_publisher` | `publish_pdf` returned `False`. |
| — | **Supervisor Repair & Lockout** | **Verified** | `MasterSupervisor` | Corrupt PDF invalidated `["18_pdf_design", "19_pdf_qa", "22_telegram_publisher"]`; regenerated PDF passed `18` & dependent `19_pdf_qa`; persistent corrupt PDF exceeding `max_repairs=3` locked in `FAILED_FINAL` and kept release rejected. |

---

## 4. Actual Daily & Weekly Integration (Real Saved Artifacts, `DRY_RUN=1`)

Generated locally in an isolated scratch directory using real saved JSON/image artifacts (no Telegram broadcasts issued).

- **Real Daily Edition Artifact (`data/content/daily_2026-11-22.json` + `data/mcq/daily_2026-11-22.json`):**
  - Stories: `15` (Sources: `All India Radio News`, `Business Standard`, `Economic Times`, `Ministry of External Affairs`, `PIB`, `The Hindu`) | MCQs: `15`
  - Embedded PDF images: `423` image objects | Pages: `39`
  - `19_pdf_qa.run_qa`: `passed=True`, `issues=[]`, `devanagari_present=True`
- **Real Weekly Edition Build (Real saved `daily_2026-11-17`, `2026-11-19`, `2026-11-22` + out-of-window `2026-10-29`):**
  - Window boundaries (`period_dates`): `2026-11-16` through `2026-11-22` (Mon–Sun)
  - Missing days cleanly skipped/logged: `["2026-11-16", "2026-11-18", "2026-11-20", "2026-11-21"]`
  - Out-of-window exclusion: `2026-10-29` strictly excluded (`out_of_window_excluded=True`)
  - Stories selected: `22` | MCQs selected: `44` | One-liners: `28` | Embedded images: `480` | Pages: `40`
  - `19_pdf_qa.run_qa`: `passed=True`, `issues=[('info', 'repeated_lines', '7 non-header line(s) repeat more than 2 times')]`
  - `DRY_RUN` Period QA Warning: `12 of 54 bullets lack clean Hindi (would fail a live edition)` (offline translator lacks live LLM translation for residual proper nouns).

---

## 5. PDF Visual Inspection (`inspect_pdf_visuals` + PNG Review)

- **Daily (`daily_2026-11-22`, 39 pages):** `available=True`, `passed=True`, `pages_rendered=39`, `blank_visual_pages=[]`, `edge_clip_pages=[]`. Direct PNG inspection of pages `1`, `2`, `3`, and `39` confirmed crisp cover masthead, hero & 2x2 photo gallery attribution (`Image: Business Standard`, `Photo: PIB`), bilingual TOC (`Q1`–`Q15`), Devanagari HarfBuzz shaping, highlighted EN/HI one-liners, and clean bottom footer.
- **Weekly (`weekly_2026-11-22`, 40 pages):** `available=True`, `passed=True`, `pages_rendered=40`, `blank_visual_pages=[]`, `edge_clip_pages=[]`. Direct PNG inspection of pages `1`, `2`, `3`, and `40` confirmed Weekly cover (`16 November – 22 November 2026`), categorized TOC, Agri Static GK box, and footer. Minor categorization note observed visually on page 3: `10 Films to Compete for ICFT-UNESCO Gandhi Medal at 57th IFFI` rendered under `SPORTS (1)` because `"compete"` matched sports regex before cultural fallback.

---

## 6. Publication Security (`agents/22_telegram_publisher.py` + `MasterSupervisor`)

Verified with `DRY_RUN=0` against a stubbed `send_document` spy (`0` network calls fired):

1. Missing PDF -> Blocked (`publish_pdf` returned `False`)
2. Missing QA report -> Blocked (`publish_pdf` returned `False`)
3. PDF hash changed after QA -> Blocked (`publish_pdf` returned `False`)
4. Remaining P0/P1 defect (`passed=False`) -> Blocked (`publish_pdf` returned `False`)
5. Tampered `release_approval` signature -> Blocked (`publish_pdf` returned `False`); `MasterSupervisor.issue_release_decision` before QA/PDF also returned `approved=False`
6. Existing live entry in idempotency ledger (`state/published_events.json` schema `records`) -> `store.is_job_published` returned `True`, and `publish_pdf` blocked live re-publish of a modified PDF (`False`)
7. Valid QA + intact signature under `DRY_RUN=1` -> Returned `True` with `0` Telegram API calls.

---

## 7. GitHub Actions CI Verification

- **Run URL:** https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/46110164947
- **Commit Audited:** `ba1c1e2678f0d67aac9b3f9c4bce342d9d81d19c` (`main`, `event=push`, `2026-11-28T05:01:09Z` – `05:05:52Z`)
- **Final Conclusion:** `completed` / **`success`**
- **Jobs Executed:** `Security Scan` (`9` steps), `Lint & Syntax Check` (`12` steps), `Run Tests` (`11` steps), `State File Load Test` (`8` steps), `Validate CLI Contracts` (`9` steps) — all `5/5` succeeded.
- **Skipped Step:** Only `Upload test logs on failure` (`if: failure()`) was skipped; zero critical jobs or steps skipped.
- **`continue-on-error: true` Audit in `.github/workflows/ci.yml`:** Advisory steps `Install project deps (best-effort)`, `Ruff lint`, and `Bandit (SAST)` (`--exit-zero`) permit warnings, whereas `py_compile`, JSON validation, secrets regex scan, `pytest`, CLI contracts, and `state/jobs.json` load are strict blocking gates.

---

## 8. Live API Tests & Remaining Limitations

- **Live API Tests Status:** **Not executed locally.** Local environment holds `0` AI/News provider keys (`GEMINI_API_KEY*`, `GROQ_API_KEY*`, `OPENAI_API_KEY*`, `MISTRAL_API_KEY`, `OPENROUTER_API_KEY`, `NVIDIA_API_KEY`, `COHERE_API_KEY`, `GNEWS_API_KEY`, `SERPER_API_KEY`, `TAVILY_API_KEY` all unset locally; stored exclusively in GitHub Actions Secrets).
- **Scheduled Live Production Pipelines:** Prior `Daily News Pipeline` run `46109187666` failed at `04:47:50Z` on earlier commit `9905e74` (before `ba1c1e2`). No scheduled live run of `daily.yml` or `weekly.yml` has executed yet on commit `ba1c1e2`.
- **Additional Observed Code Limitations:**
  1. `hindi_editor.edit_hindi_text` fixes double-halant but relies on `19_pdf_qa.check_glyph_integrity` to reject Unicode replacement characters (`\ufffd`).
  2. `17c_static_gk_validator` validates factual correctness against `current_facts.json`; cross-story duplicate Static GK lines are deduplicated by `period_builder` and flagged by `19_pdf_qa` when generic filler or `>2x` repetition occurs, leaving `2x` non-filler daily duplicates unblocked.
  3. `agents/22_telegram_publisher.py` verifies `qa["release_approval"]` SHA-256 signature directly rather than requiring `logs/qa/<job_id>_supervisor_release.json` via `verify_release_approval(..., require_approval_file=True)`.
  4. `ClaimVerifier` requires numeric `%` symbols for percentage extraction (`"9.75 percent"` spelled out fell back cleanly to `verified=False`).
