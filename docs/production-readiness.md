# Production Readiness — daily-current-affairs

Companion to [`production-audit.md`](production-audit.md).
Assessed: 2026-10-18, `main` @ `4af796d` + local hardening changes.

**Verdict: CONDITIONALLY READY FOR CONTROLLED PRODUCTION.**
All P0/P1 findings are fixed and covered by deterministic offline tests; the
suite is green and the offline end-to-end pipeline runs. Two checks could not be
executed in this environment (exact Python 3.11 run and local Hindi PDF shaping)
and one class of check must **never** be automated (live publishing / live AI
calls). Those are gates for the operator, listed in §5.

---

## 1. How to reproduce the evidence

```bash
# syntax / import surface
python -m compileall -q agents pipeline src config scripts tests main.py
python main.py --help

# full deterministic suite (offline: no network, no Telegram, no API credits)
python -m pytest -q

# the end-to-end offline dry run: real stage subprocesses, synthetic RSS feed
python -m pytest -q tests/test_daily_integration.py::test_daily_pipeline_end_to_end_without_external_services

# lint new files (modified legacy files still contain unrelated historical findings)
python -m ruff check scripts/source_health.py scripts/pdf_preview.py \
  tests/test_pdf_sample_qa.py tests/test_module_consolidation.py \
  tests/fixtures/bilingual_sample.py

# source registry offline validation
python scripts/source_health.py

# deterministic bilingual PDF generation + real QA + PNG render
python scripts/pdf_preview.py --out output/sample_preview.pdf --png-dir output/preview
```

---

## 2. Gate matrix

| Gate | Result | Evidence |
| --- | --- | --- |
| Syntax/bytecode compiles | **PASS** | `python -m compileall -q .` → exit 0 |
| CLI contract intact | **PASS** | `python main.py --help` → exit 0; `--job-type/--type/--date/--watchdog/--reset` present |
| Unit + integration suite | **PASS** | `228 passed, 0 skipped` (local CPython 3.14.7) |
| Regression coverage for fixes | **PASS** | New/extended source, PDF, module-consolidation and infrastructure tests |
| Offline end-to-end pipeline | **PASS** | Full suite includes both `[False]` and `[True]` synthetic runs |
| Determinism / offline purity | **PASS** | tests use fixtures, temp dirs, synthetic RSS, stubbed HTTP; no live calls |
| New-file lint | **PASS** | `ruff check` clean on `scripts/source_health.py`, `scripts/pdf_preview.py`, fixture and new PDF/consolidation tests |
| Existing lint debt | **CONDITIONAL** | Legacy findings remain; net findings across touched tracked Python files decreased by 60; CI ruff remains non-blocking |
| PDF Hindi shaping (local) | **PASS** | HarfBuzz + FreeType backend; `test_pdf_hindi.py`, offline PDF E2E and sample PDF QA executed |
| Exact Python 3.11 run | **BLOCKED (env)** | local interpreter is 3.14.7; confirm CI pinned to `3.11` before release |
| Live Telegram publish | **NOT RUN (by policy)** | must not be automated against the real channel |
| Live AI providers | **NOT RUN (by policy)** | no API credits spent in tests |

---

## 3. Safety properties that matter in production

| Property | Status | Where enforced |
| --- | --- | --- |
| Never publish an invalid/empty edition | Enforced | `src/generate_pdf.py` refuses empty content; `agents/19_pdf_qa.py` gate |
| Never publish an unreviewed translation | Enforced | `ALP_ALLOW_FALLBACK_TRANSLATION=0`; `agents/22` pre-publish gate |
| Revision of a published edition requires explicit approval | Enforced | `ALP_ALLOW_EDITION_REVISION`; write-ahead ledger (`blocked_revision`) |
| Uncertain sends are never auto-retried | Enforced | publisher ledger `sending`/`uncertain` states; `pipeline/publication.py` |
| Completed job not re-published on lost evidence | Enforced | `main.execute_job` + `publication_issues`; tests in `test_publication_safety.py` |
| Missing/corrupt PDF fails closed (no crash) | Enforced | `main.execute_job` guard (P0-4) |
| Fact verification fail-closed on fetch/AI failure | Enforced | `pipeline/claim_verifier.py`; `agents/04` heuristics fallback |
| Idempotent publishing across crashes | Enforced | ledger keyed by `(chat, job, sha256(pdf))` |
| Concurrent runs cannot race shared state | Enforced | repo-wide `current-affairs-pipeline` concurrency group + `state.lock`/`pipeline.lock` |
| Secrets never hardcoded | Enforced | token read only from env; CI secret-pattern scan; `.env.example` placeholders |

---

## 4. Security posture

- **Secrets:** `TELEGRAM_BOT_TOKEN` and provider keys are read only from the
  environment; no hardcoded fallback (`pipeline/telegram_api.py`, `agents/22`).
  `.env.example` ships obvious placeholders (no `:`-shaped token).
- **CI:** `bandit` SAST (non-blocking) + a regex secret scanner that fails the
  build. `permissions: contents: read` for CI; publish workflows use
  `contents: write` only to commit state.
- **Log redaction:** `main.redact()` and the log filter in `agents/00` scrub
  API keys/tokens; verified the filter replaces the formatted message and clears
  `args` so the secret cannot reappear.
- **Input handling:** collection validates/normalizes every article at the stage
  boundary; `claim_verifier.fetch_page` rejects non-HTTP(S) schemes and caps
  response size (`ALP_CLAIM_MAX_BYTES`).
- **Not addressed (out of scope):** third-party Actions are used at floating
  major tags (`@v4`/`@v5`); pinning to SHAs is recommended hardening.

---

## 5. Residual risks & required pre-launch actions

| # | Risk / gate | Owner action before first live run |
| --- | --- | --- |
| 1 | Not verified on exact Python **3.11** | Merge and confirm the `CI` workflow (`python-version: 3.11`, Ubuntu with RAQM) is green. |
| 2 | Python 3.11 CI has not run in this local session | Confirm CI's Python 3.11 job is green before first live run. |
| 3 | Live publish path untested | Perform one **manual** `workflow_dispatch` with `DRY_RUN=0` for a throwaway/backfill date and confirm the pin receipt in `state/pin_verification.json`. |
| 4 | Live AI providers untested | Run once with providers configured; confirm `00_model_orchestrator` health check and `ai_router` fallback logs. |
| 5 | Repo-wide lint debt remains | Follow-up PR; then set `ruff` CI step to blocking. |
| 6 | Source URLs are point-in-time health observations | Run `python scripts/source_health.py --live` periodically; a green historical probe is not a future availability guarantee. |
| 7 | Third-party Actions not SHA-pinned | Pin `actions/*` and `appleboy/telegram-action` to commit SHAs. |
| 8 | `pipeline/state.py` vs `main.py` state coexistence | Track as tech-debt; currently non-conflicting because agents use `state.py` only for paths/IO. |

---

## 6. Rollback

The pipeline is state-in-git. To roll back an edition:

1. Revert the offending commit(s) on the state branch (`git revert <sha>`), or
2. Re-run the workflow for the edition with `reset=true` **and**
   `allow_revision=true` to publish a corrected PDF, or
3. If a bad PDF was already sent and must not be revised automatically, leave
   `ALP_ALLOW_EDITION_REVISION=0`; the job will stay `recovery_blocked` and the
   watchdog will surface it rather than auto-republish.

See [`OPERATIONS_RUNBOOK.md`](OPERATIONS_RUNBOOK.md) for the exact commands.
