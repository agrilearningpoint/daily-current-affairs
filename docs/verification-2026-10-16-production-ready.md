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

Raw per-run evidence dumps (log excerpts, QA JSON, stage inventory) were removed
from the repository as clutter: every run above keeps its Actions artifacts and
run URL, and only this summary is tracked. Ask the dispatcher for the detailed
document (`COLLECT_RUN_ID=<run>` + push) whenever the raw evidence is needed again.

## 15 October edition: backdated recovery build

`daily_2026-10-15` was never published (the ledger holds 10-10, 10-11, 10-14) and
the live job for that date failed at `12_content_editor` with a 2-item selection.
It was rebuilt twice with `dry_run=true, reset=true`, so nothing was sent to
Telegram.

| build | run | raw → selected | PDF | QA | delivery |
|---|---|---|---|---|---|
| A (before the feed fixes) | 38904929697 | 46 → 46 → 41 → 8 → 8 | 19 pages, 4,903,641 B, sha256 `7c0d127d…` | `passed: true` (low_hindi 5.46 %, overflow pages 6, 18) | draft release `dryrun-daily_2026-10-15` |
| B (current code) | 38906490713 | 38 → 38 → 36 → 6 → 6 | 17 pages, 4,383,171 B, sha256 `a9d8bb7a…` | `passed: true` (low_hindi 5.62 %, overflow page 14) | draft release `dryrun-daily_2026-10-15-r38906490713` |

Both builds finished stage `24_final_health_audit` with `dry_run: true`, and both
log `[DRY-RUN] Would publish daily_2026-10-15.pdf …` plus "No live publication
receipt to pin." — Telegram was never called. MCQs: 15 generated, 17 in the PDF,
15 answers found, no duplicates, no blank pages in either build.

Why the pool is small: collection is windowed to the edition day
(`pipeline/windows.py`), and RSS feeds only retain about a day or two, so a
backdated run sees the tail of 15 October only. Same-day runs collect 400+ raw
items (run 38901156671: raw 406 → selected 19).

Build A's log evidence named the feed failures that were silently shrinking every
edition (fixed in `a915646`, see the commit): PIB and SEBI were rejected by
feedparser as whole feeds (bare `&`, undeclared `&nbsp;`), and Indian Express,
Business Standard, NITI Aayog, MEA and PIB answer HTTP 403 even to the
browser-style user agent.

## Known limitations (not fixed here)

1. **Translation providers are rate-limited or out of credit** (gemini 429,
   groq 429, mistral 429, openrouter 402). `main`'s live runs on 2026-10-15/16
   failed at stage 12 because of this; the parking feature stops the repeated
   dialling but cannot create quota. Hindi coverage stays low (≈ 7 %) while the
   providers refuse, and a live run still fails closed at stage 12 rather than
   publishing unreviewed content.
2. **Residual non-news items** in a same-day edition (~3 of 19): ICAR/IMD feed entries
   that are course/weather bulletins, and titles such as `O & M/PG & RTI` or
   `Division of Biochemistry`. The IMDA feed is mangled at the source
   (`प्रभाि-आधाररत …`), so it should be re-mapped or dropped in
   `pipeline/source_registry`.
3. **Official feeds block the runner's IP** (PIB, SEBI, NITI Aayog, Indian
   Express, Business Standard, MEA: HTTP 403 even with a browser-style user
   agent). The UA retry in `pipeline/01_source_fetch.py` only covers publishers
   that block on the user-agent string; an IP-level block needs a proxy or an
   allowlisted fetcher, or those sources must be marked disabled in the registry
   so they stop counting as silent failures. Until then the tier-1 direct feeds
   over Google News discovery carry the edition.
4. **Two of the six selected items in the 15 October build are still
   non-editorial**: an IMD rainfall table (`Significant Weather Observations
   Stations Rainfall (in mm)`), an India.gov.in listing entry
   (`View Details… Amul Dairy …`) and a CCI legal notice (`General Statement …
   (Settlement) Regulations, 2024`). No further title filter was added on
   purpose: with only six scoring survivors, one more rule can trip
   `min_items = 5` and fail the edition closed. This belongs in
   `pipeline/source_registry` (drop/mark the aggregator pages), not in more
   regexes.
5. **Discovery feeds dominate the raw pool** (`discovery` 198 of 406) and supply
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
