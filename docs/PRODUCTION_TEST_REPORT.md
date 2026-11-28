# Production Certification & Hardening Verification Report

**Prior Audited Commits:** `ba1c1e2678f0d67aac9b3f9c4bce342d9d81d19c` (`ba1c1e2`), `5f69eb2f14a7add6eadceeebff84a9e452433362` (`5f69eb2`)  
**Hardening Pass Target Branch:** `main` (pushed cleanly after all local checks exited `0`)  
**Final Status:** **`PRODUCTION READY WITH DOCUMENTED LIMITATIONS`**

This report separates every verification category and cites **only directly observed tool outputs**. Mocked tests are never reported as live API calls, and offline/clone fixtures are never presented as live production runs.

---

## 1. Hardening Changes Implemented (Priorities 1–4 & 7)

| Area | Files Modified | Targeted Changes |
|---|---|---|
| **Priority 1 — Hindi Editorial Quality Gate** | `pipeline/hindi_editor.py`, `pipeline/completeness.py`, `agents/12_content_editor.py`, `agents/17c_static_gk_validator.py`, `agents/19_pdf_qa.py` | Strip/flag `\ufffd`/`\uFFFE`/`\uFFFF`, isolated combining Devanagari matras, broken matra sequences, and incomplete Hindi endings (`review_hindi_line`, `audit_edition_hindi`); block in `validate_content_completeness` (`corrupt_hindi_unicode`) and `19_pdf_qa` (`isolated_hindi_matra`, `critical_hindi_defect`). |
| **Priority 2 — News Category Accuracy** | `pipeline/collector.py`, `agents/07_student_domain_relevance.py`, `pipeline/period_builder.py` | Prevent cultural/film/peace medals (`IFFI`, `ICFT-UNESCO Gandhi Medal`, `Nobel`, `Padma`, `Dadasaheb Phalke`, `Sahitya Akademi`) from routing to `Sports`; add `Awards & Honours` & `Important Days` (`_IMPORTANT_DAY_RE`) support across all 10 exam domains; add `classify_category_with_confidence` flagging uncertain/tied classifications (`category_uncertain=True`). |
| **Priority 3 — Static GK & Repetition Control** | `agents/static_gk_validator.py`, `pipeline/period_builder.py`, `src/generate_pdf.py`, `src/period_pdf.py` | Added edition-wide exact + semantic (`>=0.80` token overlap) deduplication in `deduplicate_edition_static_gk` (preserving parent story `event_id` pairing while stripping cross-story duplicates); added `seen_edition_facts` dedup across story units in `src/generate_pdf.py` & `src/period_pdf.py`; respected builder `static_gk_deduped=True`. |
| **Priority 4 — Headline & PDF Clipping + Layout** | `agents/19_pdf_qa.py`, `pipeline/supervisor.py`, `src/generate_pdf.py` | Added `check_headline_clipping` (distinguishes intentional cover/TOC `…` preview ellipses from clipped story headlines or dangling prepositions); promoted `visual_edge_clipping` to blocking `error`; routed `clipped_headline` / `critical_hindi_defect` -> `12_content_editor` and `visual_edge_clipping` -> `18_pdf_design`; guarded trailing `Join Us` box and `ol_hi` break (`CondPageBreak(PAGE_H * 0.65)`) against near-empty final pages. |
| **Hardening Regression Suite** | `tests/test_production_hardening_gate.py` | Added `18` targeted regression tests covering Priorities 1–5 & 7. |

---

## 2. Before vs After Defect Counts (Directly Observed)

| Finding | Before (`ba1c1e2` Audit) | After Hardening Pass |
|---|---|---|
| Unicode `\ufffd` + broken matra handling in `hindi_editor` | `\ufffd` left unstripped; `review_hindi_line` returned `ok=True` | `\ufffd` stripped & flagged `critical=True` (`replacement_char_detected`, `isolated_hindi_matra`); blocked in `completeness.py` & `19_pdf_qa` |
| IFFI headline (`10 Films to Compete for ICFT-UNESCO Gandhi Medal at 57th IFFI`) | Misclassified under `SPORTS (1)` | Classified as `Awards & Honours` (`collector`) and `APPOINTMENTS & AWARDS (2)` (`period_builder` / Weekly TOC) |
| Weekly PDF repeated Static GK / boilerplate lines (`weekly_2026-11-22`) | `7` non-header lines repeated `>2x`; RBI 1935 box printed **`3`x**; `40` pages | **`0` `qa_issues`**; RBI 1935 box printed **`1`x**; **`38` pages** |
| Daily PDF duplicate Static GK (`daily_2026-11-22`) | `39` pages, `423` image objects | **`35` pages** (cross-story duplicate GK removed cleanly), `391` image objects, `0` QA issues |
| Clipped headline (`...scheme for...`) in `19_pdf_qa` | `qa_detected_codes: []` | **`[["clipped_headline", "error"]]`** while valid cover ellipses pass |
| Daily sample layout (`test_pdf_sample_qa`) | `near_empty_pages: [19]` after Static GK shift | **`near_empty_pages: []`** (`16/16` in `test_pdf_sample_qa.py` + `test_pdf_v5_layout.py` passed) |

---

## 3. Automated Tests & Diagnostics (`DRY_RUN=1`)

| Check | Command | Observed Result |
|---|---|---|
| Complete Automated Test Suite | `$env:DRY_RUN="1" ; python -m pytest tests/ -q --tb=short` | **`971 passed in 481.77s (0:08:01)`** (`0` failed, `0` skipped, includes `18/18` new hardening tests) |
| Critical Syntax / Undefined Names | `ruff check --select E9,F63,F7,F82 .` | **All checks passed** (`0` errors) |
| Repository Health Diagnostic | `python scripts/diagnose.py` | **`PASSED: 54`, `WARNINGS: 5`, `ERRORS: 0`** (`271` valid JSON configs, `69` feeds / `65` enabled sources) |
| Removed Provider Hygiene | `python -m pytest tests/test_all_keys.py -k "test_removed_providers_are_gone_everywhere" -v` | **`1 passed`** (verified on final commit docs & code) |

---

## 4. Daily, Weekly & Monthly PDF QA Results (`DRY_RUN=1`, No Telegram Sends)

- **Daily (`data/content/daily_2026-11-22.json` + `data/mcq/daily_2026-11-22.json`):**
  - `15` stories, `15` MCQs, `35` pages, `391` embedded image objects, `devanagari_present=True`
  - `19_pdf_qa.run_qa`: `passed=True`, **`issues=[]`** | `inspect_pdf_visuals`: `passed=True`, `blank_visual_pages=[]`, `edge_clip_pages=[]`.
- **Weekly (`weekly_2026-11-22` built from real saved `2026-11-17`, `2026-11-19`, `2026-11-22` + out-of-window `2026-10-29`):**
  - Boundaries `2026-11-16..2026-11-22` (Mon–Sun); `4` missing days handled cleanly (`2026-11-16, 18, 20, 21`); `2026-10-29` excluded (`out_of_window_excluded=True`).
  - `22` stories, `44` MCQs, `28` one-liners, **`38` pages**, `458` image objects, `devanagari_present=True`.
  - `19_pdf_qa.run_qa`: `passed=True`, **`issues=[]`** | `inspect_pdf_visuals`: `passed=True`, `blank_visual_pages=[]`, `edge_clip_pages=[]`.
  - Visual PNG verification (pages `3` & `38`): `APPOINTMENTS & AWARDS (2)` cleanly holds both IFFI stories; Agri Static GK & footer clean.
- **Monthly (`2026-11-01..2026-11-28`, `min_days=10`):**
  - Only `3` November daily JSONs exist on disk (`2026-11-17, 19, 22`), so `build_period("monthly", ...)` cleanly enforces `min_days=10` unless seeded across `>=10` days.
  - Using `10` Nov dates cloned from saved daily artifacts (`18` missing days, Oct `2026-10-29` excluded): built `22` stories, `46` MCQs, `34` pages, `qa_passed=True`, `visual_qa_passed=True` (`blank_visual_pages=[]`, `edge_clip_pages=[]`), with `1` layout warning `near_empty_pages: [16]` and `2` `repeated_lines` info items (`cloned fixture` MCQ stems).

---

## 5. Multi-Key API Routing & Publication Security Evidence

### Live Provider Evidence vs Mocked Evidence
- **Mocked Multi-Key Audit (`ALP_AI_HEALTH_FILE` + `ALP_AI_USAGE_LOG`, `0` live keys locally):** Verified key discovery across Gemini (`4` slots), OpenAI (`2`), Groq (`2`), Mistral, OpenRouter, Cohere, NVIDIA; same-task 429 rotation (`openai:OPENAI_API_KEY` -> `openai:OPENAI_API_KEY_1`); 401 slot isolation (`groq:GROQ_API_KEY` -> `invalid`, `86400s` cooldown) + fallback (`groq` -> `mistral:PRIMARY`); Gemini shared-project quota guard (`3` slot 429s in `60s` sets `shared_quota["gemini"]=True`); cooldown expiry recovery; and restart persistence across `ai_router._reset_health()` (`8` slots, `secrets_leaked=False`).
- **Live Provider Execution Evidence (GitHub Actions Secrets):** Live run `46113998033` (`Daily News Pipeline` on `ba1c1e2`, `2026-11-28T05:51:47Z–06:12:54Z`) executed end-to-end with **`Run daily pipeline: success`**, **`Run summary (counts + AI providers): success`**, checkpointing `state/jobs.json` through **`24_final_health_audit`** (`output/daily_2026-11-28.pdf`, `logs/qa/daily_2026-11-28_qa.json`, `logs/qa/daily_2026-11-28_health.json`) and saving artifacts `daily-logs-46113998033` and `pipeline-checkpoints`. *(Per-slot live token telemetry lives inside workflow artifacts accessible only with GitHub authentication.)*

### Release Gate Security Regression (`agents/22_telegram_publisher.py` + `MasterSupervisor`)
All invalid release states blocked with **`0` Telegram API calls** (`sent == []`):
- Missing PDF -> `False`
- Missing QA report -> `False`
- Stale QA / SHA-256 hash mismatch -> `False`
- Unresolved P0/P1 defect (`passed=False`) -> `False`
- Tampered `release_approval` signature -> `False`
- Existing live entry in idempotency ledger (`state/published_events.json` `records`) -> `store.is_job_published` `True`, modified PDF publish `False`
- Corrupt PDF (`NOT_A_PDF`) -> `MasterSupervisor` returned `REPAIR_REQUIRED` (`repair_target="18_pdf_design"`), preventing release.

---

## 6. GitHub Actions Verification Links

| Workflow / Commit | Run URL | Status / Conclusion | Scope / Notes |
|---|---|---|---|
| `CI` (`ba1c1e2`) | https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/46110164947 | `completed` / **`success`** | `5/5` jobs passed (`Security Scan`, `Lint & Syntax Check`, `Run Tests`, `State File Load Test`, `Validate CLI Contracts`). |
| `Daily News Pipeline` (`ba1c1e2`) | https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/46113998033 | `completed` / **`success`** | Live daily pipeline run completed through `24_final_health_audit`. |
| `CI` (`5f69eb2`) | https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/46116996405 | Checked mid-run (`4/5` passed, `Run Tests` running) | Triggered on docs report commit `5f69eb2`. |
| `Weekly` (latest historical pre-upgrade `653d310`) | https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/45296664371 | `completed` / `failure` | Predates upgrade (`ba1c1e2`); next live weekly run awaits schedule/dispatch. |
| `Monthly` (latest historical pre-upgrade `74b7032`) | https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/41610866391 | `completed` / `failure` | Predates upgrade (`ba1c1e2`); next live monthly run awaits schedule/dispatch. |

---

## 7. Remaining Limitations

1. **Live Weekly & Monthly Scheduled Runs Post-Hardening:** Live scheduled `weekly.yml` and `monthly.yml` workflows on GitHub Actions have not yet executed since commit `ba1c1e2` / this hardening pass (latest remote `weekly.yml`/`monthly.yml` runs were prior failures from pre-upgrade commits).
2. **Offline Local Key Isolation:** Local environment has `0` AI/News provider keys, so live multi-key per-slot latency/quota logs are generated only inside GitHub Actions runs (`daily-logs-*` artifacts).
3. **Numerical & Approval Edge Behaviors:** `ClaimVerifier` requires explicit `%` notation rather than spelled-out `"percent"` for percentage extraction (spelled-out claims fall back fail-closed to `verified=False`); `22_telegram_publisher.py` verifies `qa["release_approval"]` SHA-256 signature directly rather than calling `supervisor.verify_release_approval(..., require_approval_file=True)`.
4. **Advisory Diagnostics:** `diagnose.py` reports `5` non-blocking warnings (`189` Ruff style/unused-import items and optional `store.pull`/`push`/`prune` helpers), and `.github/workflows/ci.yml` keeps `Ruff lint` and `Bandit` as `continue-on-error: true` advisories.
