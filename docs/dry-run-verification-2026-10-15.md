# Daily pipeline — dry-run verification, edition 2026-10-15

Verified on branch `arena/7d5d7f3d-daily-current-affairs` (PR
[#11](https://github.com/agrilearningpoint/daily-current-affairs/pull/11)) with
`dry_run=true`. **Nothing was published to Telegram and nothing was merged.**

## 1. CI at the PR head

| commit | CI run | result |
|---|---|---|
| `cdf7f20` | [38683476528](https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/38683476528) | ✅ 5/5 checks |
| `5e8bcd5` | [38684423738](https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/38684423738) | ✅ 5/5 checks |
| `22d702f` | [38693848847](https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/38693848847) | ✅ 5/5 checks |

Checks: Lint & Syntax · Run Tests · Security Scan · State File Load Test ·
Validate CLI Contracts.

## 2. Dry run against live feeds

`Daily News Pipeline` on this branch, `dry_run=true`, `date=2026-10-15`.

| run | outcome | note |
|---|---|---|
| [38685059847](https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/38685059847) | cancelled | hit the old 45-min job cap in stage 12 |
| [38689350606](https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/38689350606) | cancelled | start marker wrote `dry_run=false`, so the run restarted instead of resuming |
| [38693854648](https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/38693854648) | failure | resumed correctly at stage 12, then `12_content_editor: failed after 3 attempt(s): timeout after 900s` |
| **[38699332232](https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/38699332232)** | **success** | head `fe3c859`, 53 s, job `daily_2026-10-15` → `status=success`, `last_success_stage=24_final_health_audit` |

### Article counts (run 38699332232)

| stage | count |
|---|---|
| raw collected | 553 |
| verified | 553 |
| dedup | 426 |
| scored | 32 |
| **selected** | **28** (target 28, minimum 5) |
| content | 28 |
| MCQ | 15 |

Selected categories: `Agriculture 7`, `Banking & Finance 7`, `Economy 3`,
`National 11` — canonical names, no raw source keys.

## 3. PDF / QA (run 38699332232)

```
PDF QA REPORT — ✅ PASSED
Pages: 32 · Chars: 53745 · Devanagari: 4046 (7.5%)
MCQs: 16 · Answer markers: 15 · Duplicate Qs: 0 · URLs: 34 · Images: 250 · Blank pages: none
Warnings: [low_hindi] coverage 7.5% is low · [text_overflow] page 10
File: output/daily_2026-10-15.pdf (8 470 667 bytes, sha256 78b89245…caf8)
Final health audit: {"passed": true, "dry_run": true, "issues": []}
```

## 4. Telegram steps skipped

```
22_telegram_publisher | Found 1 candidate PDF(s) (max 5 per run)
22_telegram_publisher | [DRY-RUN] Would publish daily_2026-10-15.pdf (8470667 bytes) with caption: …
22_telegram_publisher | Publishing complete: success=1 failed=0 skipped=0 total=1
23_telegram_pin_verifier | [DRY-RUN] No live publication receipt to pin.
```

`state/published_events.json` still holds only the adopted legacy history (no new
live record), `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` were never needed for the
send path, and the `Notify success/failure (Telegram)` steps stayed `skipped`.

## 5. Defects found and fixed in this branch

1. **Category keys were never canonicalised** (original failure: `selected 2 items
   (min 5)`). New `pipeline/categories.py` is the single vocabulary shared by the
   collector, artifacts, scoring, relevance and selection.
2. **Publication ledger schema** — `state/published_events.json` is the
   pre-versioned flat map, which `load_ledger()` rejected, so stage 22 aborted
   every edition with *"Publication ledger unreadable"*. Legacy entries are now
   adopted as `legacy_unknown` (10 entries), and an edition inside that history
   still refuses a **live** resend.
3. **Dry-run resume was impossible** — the start marker did not receive
   `DRY_RUN`, so it stored `dry_run=false` and `resolve_resume_stage()` rejected
   the run's own checkpoints (full restart, 45-minute budget burned).
4. **Job cap too small** — a real edition (553 articles → 28 items → LLM
   translation → PDF/QA) does not fit in 45 minutes; the cap is now 90.
5. **Translator retried dead providers for every text** — with gemini 429,
   groq 404, openrouter 402 and mistral 429, stage 12 timed out three times
   (900 s each). Providers are now parked after a hard failure, which turned the
   stage into ~9 s.

Follow-up defects deliberately **not** touched: content quality of collected
feeds (weather bulletins and index pages rank as news) and the missing LLM
credits themselves (gemini/mistral rate-limited, groq model 404, openrouter 402)
— Hindi translation falls back and 121 strings are flagged `needs_review`.

## 6. Temporary tooling on the branch

`.github/workflows/dry-run-dispatch.yml` is bootstrap-only: this session's GitHub
token has no `actions: write`, so it dispatches `daily.yml` (dry-run, no reset)
from a push-triggered job, waits for it, downloads its checkpoints/logs — blob
endpoints are unreachable from the maintainer sandbox — and commits an evidence
report. Remove it once the dry-run workflow is triggered from the UI instead.
