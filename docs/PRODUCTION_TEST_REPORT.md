# Production Test & Verification Report

This report records the observed verification outputs executed on the final upgraded **Agri Learning Point** codebase (`main` branch) prior to release. All test and rendering runs were executed locally with `DRY_RUN=1` to avoid emitting live Telegram messages.

---

## 1. Full Automated Test Suite

- **Command:**
  ```powershell
  $env:DRY_RUN="1" ; python -m pytest tests/ -q --tb=short
  ```
- **Observed Result:** **`953 passed in 435.32s (0:07:15)`** (0 failed, 0 skipped, exit code `0`).
- **Scope Verified:**
  - Core pipeline contracts & stage registry (`test_stage_registry.py`, `test_supervisor.py`)
  - AI routing, key pools, overnight pacing & provider policy (`test_all_keys.py`, `test_ai_key_pools_and_openai.py`, `test_ai_resilience.py`, `test_overnight_pacing.py`)
  - Research, collection window, freshness wrap, claim verification & scoring (`test_phase4_research_verification.py`, `test_collection_window.py`, `test_claim_verifier.py`, `test_selection.py`, `test_selection_quality.py`)
  - Hindi editorial stack, terminology & sanitizer hardening (`test_phase5_hindi_editor.py`, `test_content_sanitizer.py`, `test_hindi_staticgk_fixes.py`, `test_hindi_text_hardening.py`)
  - Static GK completeness & independent MCQ Examiner (`test_phase6_7_gk_mcq_examiner.py`, `test_mcq_quality.py`, `test_static_gk_validator.py`)
  - Visual PDF QA, cryptographic release signature & self-improvement telemetry (`test_phase8_to_13.py`, `test_pdf_sample_qa.py`, `test_pdf_v5_layout.py`)
  - End-to-end 18-stage offline daily orchestrator (`tests/test_daily_integration.py`) including interrupted-feed recovery, supervisor checks, checkpointing, PDF generation, and SHA-256 QA approval.

---

## 2. Static Analysis & Repository Diagnostics

| Check | Command | Observed Result |
|---|---|---|
| Critical Syntax / Undefined Names | `ruff check --select E9,F63,F7,F82 .` | **All checks passed** (`0` errors, exit code `0`) |
| Repository Health Diagnostic | `python scripts/diagnose.py` | **PASSED: 54**, **WARNINGS: 5** (non-blocking style items & `pull`/`push`/`prune` optional notices), **ERRORS: 0**, **271 valid JSON configs**, **69 feeds / 65 enabled sources** |
| Removed Provider Hygiene | `pytest tests/test_all_keys.py::test_removed_providers_are_gone_everywhere` | **PASSED** (verifies zero stale provider names across code, workflows, configs, and docs) |

---

## 3. Bilingual PDF & Visual Inspection (`DRY_RUN=1`)

Sample fixture editions (`tests/fixtures/bilingual_sample.py`) were rendered through `src/generate_pdf.py` and verified pixel-by-pixel with `pipeline/pdf_visual_qa.py` (`inspect_pdf_visuals` via PyMuPDF):

### Daily Edition (`daily_2026-11-28_verify.pdf`)
- **MCQ Examiner (`examine_mcq_set`):** `13/14` sample MCQs approved (`avg_score: 93.5`); `sample-national-2` (a Static GK CJI item whose target key is not in the news snippet text) was accurately caught and rejected (`'examiner: answer not supported by the story text'`).
- **Rendered Pages:** `18` pages rendered cleanly.
- **Visual QA Verdict:** `available=True`, `passed=True`, `blank_visual_pages=[]`, `edge_clip_pages=[]`, `issues=[]`.
- **Manual PNG Inspection:** Cover, TOC (`CONTENTS / विषय-सूची`), bilingual story cards, highlight boxes, bottom footer (`Page 18 of 18`), and HarfBuzz Devanagari shaping verified clean with zero box-overlap or glyph corruption.

### Weekly Edition (`weekly_2026-11-28_verify.pdf`)
- **Rendered Pages:** `15` pages rendered cleanly (`WEEKLY CURRENT AFFAIRS / साप्ताहिक करंट अफेयर्स`).
- **Visual QA Verdict:** `available=True`, `passed=True`, `blank_visual_pages=[]`, `edge_clip_pages=[]`, `issues=[]`.
- **Manual PNG Inspection:** Weekly cover banner, bilingual summary pills, TOC index, and Hindi/English sections verified clean.

---

## 4. Production Readiness & Safety Status

- **Safety Guarantees Verified (`DRY_RUN=1`):** Dry runs leave `state/published_events.json` untouched and never issue Telegram API calls (`send_document`).
- **Release Gate Verified:** `agents/22_telegram_publisher.py` enforces exact `job_id`, `file_sha256`, and `release_approval` signature verification alongside `logs/qa/<job_id>_qa.json`.
- **Production Note:** End-to-end live provider fetches (RSS/GNews/LLM keys and live Telegram broadcast) execute exclusively inside GitHub Actions workflows with configured repository secrets rather than in local `DRY_RUN=1` tests.
