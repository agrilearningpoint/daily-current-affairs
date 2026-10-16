# Production-readiness verification — 2026-10-16

Branch: `arena/7d5d7f3d-daily-current-affairs` → PR
[#11](https://github.com/agrilearningpoint/daily-current-affairs/pull/11)
Merged with `main` @ `88965b7` (conflicts in `pipeline/ai_translator.py`,
`agents/22_telegram_publisher.py`, `state/importance_memory.json` all resolved).

## What this branch changes relative to `main`

| Area | Change |
|---|---|
| Collection quality | `pipeline/quality.py` + wiring in `pipeline/01_source_fetch.py` and `pipeline/collector.py`: site chrome (nav/policy/section labels, publisher-only titles, organisation names, landing links, truncated fragments) is dropped before verification. Kill switch: `ALP_CHROME_FILTER=0`. |
| Category normalisation | `pipeline/categories.py` (single alias map) used by collection, verification, scoring, relevance and selection, so `economy_data`, `govt_national`, `agriculture_core` … become real categories instead of being silently skipped. |
| Selection floor | `agents/10_final_news_selection.py`: `min_items = 5` for every edition type (main had `1` for daily). A thin edition fails loudly instead of shipping. |
| Translation resilience | `pipeline/ai_translator.py`: providers rejected with 401/402/403/404 (or a non-retryable transport failure) are parked for `ALP_TRANSLATION_PROVIDER_COOLDOWN` seconds, so one dead provider cannot burn the whole stage budget; `result["exhausted"]` reports "nothing left to dial". |
| Publication ledger | `agents/22_telegram_publisher.py` + `pipeline/publication.py`: unverifiable legacy rows (job list + date, no chat_id/file_hash/status) are adopted as `legacy_history` and can never authorise or hide a live send. |
| Dry-run safety | `daily.yml` gained a `dry_run` input: Telegram notify steps are skipped and `DRY_RUN=1` reaches every stage; timeout raised 45 → 90 min. |
| Tooling | `.github/workflows/dry-run-dispatch.yml`: dry-run-only dispatcher/evidence collector (`workflow_dispatch`, or automatically when `pipeline/quality.py` changes). |

## Test + CI status

- `pytest tests/` locally: **257 passed, 1 skipped** (the sandbox needs a
  Pillow-RAQM shim; CI has `libfribidi0` and passes without it).
- CI (lint, security, tests, state-file load, CLI contracts): **5/5 green** on
  every head, latest at the time of writing `c210c56`.

## End-to-end dry-run verification (live feeds, `dry_run=true`, `reset=true`)

| run | edition | raw | verified | dedup | scored | selected | content | mcq | PDF QA | result |
|---|---|---|---|---|---|---|---|---|---|---|
| [38901156671](https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/38901156671) (final) | 2026-10-16 | 406 | 406 | 390 | 19 | **19** | 19 | 15 | passed, 30 pages, 8,455,278 B, Devanagari 6.93 % | success |
| [38900647035](https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/38900647035) | 2026-10-16 | 401 | 401 | 386 | 16 | 16 | 16 | 15 | passed | success |
| [38899269269](https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/38899269269) | 2026-10-16 | 534 | 534 | 430 | 19 | 19 | 19 | 15 | passed | success |
| [38897677177](https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/38897677177) | 2026-10-16 | 574 | 574 | 458 | 42 | 28 (19 chrome) | 28 | 14 | passed | success |
| [38896579675](https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/38896579675) | 2026-10-16 | 562 | 562 | 446 | 41 | 28 (19 chrome) | 28 | 14 | passed | success |

Every run: `[DRY-RUN] Would publish daily_2026-10-16.pdf …` from agent 22,
`[DRY-RUN] No live publication receipt to pin.` from agent 23, both Telegram
`Notify …` steps reported `skipped`, health audit `{"passed": true, "dry_run": true}`.
No live Telegram publication happened in this session.

Chrome reduction: `raw 574 → 406` and non-news selected items `19/28 → ~3/19`,
with per-feed telemetry in the stage log (`… 81 chrome skipped` for IFSCA,
`14` for Department of Financial Services, …) and `chrome_rejected_count` in the
edition JSON.

## Known limitations (not fixed here)

1. **Translation providers are rate-limited or out of credit** (gemini 429,
   groq 429, mistral 429, openrouter 402). `main`'s live runs on 2026-10-15/16
   failed at stage 12 because of this; the parking feature stops the repeated
   dialling but cannot create quota. Hindi coverage stays low (≈ 7 %) while the
   providers refuse, and a live run still fails closed at stage 12 rather than
   publishing unreviewed content.
2. **Residual non-news items** in a 19-item edition (~3): ICAR/IMD feed entries
   that are course/weather bulletins, and titles such as `O & M/PG & RTI` or
   `Division of Biochemistry`. The IMDA feed is mangled at the source
   (`प्रभाि-आधाररत …`), so it should be re-mapped or dropped in
   `pipeline/source_registry`.
3. **Discovery feeds dominate the raw pool** (`discovery` 198 of 406) and supply
   most chrome; a source-level review of `pipeline/source_registry` would raise
   yield per run.

## Merge checklist

- [ ] Merge commit (not squash): `state/**` and `recovery_plan.json` are pinned to
      `main`'s current content, and `main`'s live workflow rewrites them on every
      run. If `main` advances before merging, re-sync with
      `git checkout origin/main -- state/ recovery_plan.json` and merge *without*
      squashing, or GitHub reports a conflict on those two files.
- [ ] Decide whether to keep `.github/workflows/dry-run-dispatch.yml`
      (dry-run only, path-filtered to its own file and `pipeline/quality.py`).
- [ ] Decide the fate of `ALP_CHROME_FILTER` (on by default; `0` disables).
