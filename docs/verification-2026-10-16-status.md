# Status & verification — 2026-10-16

Verification pass over this branch (PR [#11](https://github.com/agrilearningpoint/daily-current-affairs/pull/11)) and over
what production (`main`) is currently doing. Nothing here was merged or published.

## 1. This branch

| item | state |
|---|---|
| head | `b7c8d86` (pushed; only docs/CI/state changed since the verified code head `fe3c859`) |
| CI | [38699827829](https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/38699827829) ✅ 5/5 at `0b5f3ad`; newer heads produce no run because the PR is `CONFLICTING` |
| PR state | OPEN, `mergeStateStatus=DIRTY`, `mergeable=CONFLICTING` (main moved; state files + a now-duplicated ledger fix) |
| local tests | 161 passed / 5 failed without RAQM shim (all 5 are the sandbox Pillow gap) · **166 passed** with the sandbox-only shim; CI runs the same suite on ubuntu-latest + `libfribidi0` and is green |
| dry run (live feeds) | [38699332232](https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/38699332232) ✅ success — raw 553 → verified 553 → dedup 426 → scored 32 → selected 28; PDF QA passed; Telegram `[DRY-RUN]` only |
| merge with main | `0b5f3ad` brought in **only** `state/jobs.json` + `recovery_plan.json` — no main code (today's main commits are not on this branch) |

## 2. Production (`main`) — how it is actually running

Latest live editions (`main` `state/jobs.json`):

| edition | status | last stage | failed stage |
|---|---|---|---|
| daily_2026-10-14 | **success** (live) | 24_final_health_audit | — |
| daily_2026-10-15 | failed | 11_importance_memory | 12_content_editor |
| daily_2026-10-16 | failed | 11_importance_memory | 12_content_editor |

* Live publication **does work**: `state/published_events.json` holds one live receipt —
  `daily_2026-10-14`, `message_id=39`, published `2026-10-16T07:37:43Z` — and
  `state/pin_verification.json` confirms it was pinned (`status=verified`, message 39).
  Main's own ledger migration (`3797baa`) covers what this branch implemented for the same defect.
* **Current blocker = AI providers, not the pipeline structure.** Evidence collected from the failing
  runs (see `docs/verification-dryrun-38879885706.md`, `docs/verification-dryrun-38879882929.md`):

  ```
  [Translator] gemini rate-limited (429) · mistral rate-limited (429)
  [Translator] groq validation failed: ['no Devanagari characters'] / ['unusual length ratio 0.06']
  [Translation] AI unavailable ... (validation failed: ['gemini: rate limited', 'groq: validation failed',
                                                        'openrouter: HTTP 402', 'mistral: rate limited'])
  [Content Builder] 3 translations need review (AI did not pass)
  ERROR | __main__ | Translation validation failed; refusing to publish unreviewed content
  ```

  Live mode is fail-closed (`ALP_TRANSLATION_STRICT=1`), so an edition with even 2–3 untranslated strings
  is refused — correct behaviour, but it means no edition can publish until a provider answers properly.
* **Article funnel in live mode is very thin** (run 38879882929): raw **551** → verified **3** → dedup 2 →
  selected 2 → content 2. The provenance gate in `04_fact_verification` rejects nearly everything on live
  data. This is independent of the category defect and worth its own investigation.
* **The category defect this PR fixes is still live on main**: in that run's `selected` artifact the
  categories are `Agriculture` and **`economy_data`** — a raw registry key leaking into the final selection,
  exactly the mismatch (`economy_data`, `govt_national`, `agriculture_core`, `banking_finance`, …) that keeps
  scoring/selection boosts from matching. Main still has no `pipeline/categories.py`
  (`pipeline/artifacts.py` uses `CATEGORY_NAMES.get(...)` only).
* **Minimum-selection threshold on main was lowered** to `min_items = 1 if job_type == "daily" else 5`
  (`agents/10_final_news_selection.py`). Standing instruction for this session was to *not* lower it; this
  branch keeps `min 5`. With min 1, main no longer fails at stage 10 but can ship 2-item editions.

## 3. What the branch still contributes on top of today's main

1. `pipeline/categories.py` + normalisation in `04_fact_verification`, `pipeline/scoring`, `agents/07`,
   `agents/10` — **absent on main** (raw keys still reach `selected`).
2. Minimum selection threshold preserved at 5 for daily (main has 1).
3. `dry_run` workflow input + Telegram notify guards + `DRY_RUN` passed to the start marker
   (**absent on main** — main's `daily.yml` has no dry-run switch), plus the 90-minute job budget.
4. Translator provider circuit breaker (`pipeline/ai_translator.py`) — main added router-level disabling and
   provider-error reporting instead; the two are complementary (mine stops the per-text re-dialling that
   caused three 900 s stage timeouts).
5. Tests: `tests/test_publication_ledger_legacy.py`, `tests/test_translator_circuit_breaker.py`.
   The ledger change itself is now redundant with main.

## 4. Recommended next steps

1. Rebase this branch onto current `main`, dropping the redundant ledger fix, keeping the category fix,
   min-5 and the dry-run switch, then re-run `daily.yml` with `dry_run=true` to verify on top of main's code.
2. Decide the daily minimum-selection policy (session instruction: keep 5).
3. Fix the live funnel (551 → 3 verified) and the provider credentials/quotas — without them no edition can
   publish, regardless of code.
