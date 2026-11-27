# Daily schedule: staggered overnight build (01:00–05:30 IST), publish 06:00–07:00 IST

GitHub Actions `schedule` is best effort. On 2026-11-03 a single 04:05 IST
cron (`35 22 * * *`) started late, and burst-calling GNews in a single pass
tripped the 1 req/s rate limit (`HTTP 429`).
The daily workflow therefore starts after midnight (`01:00 IST`), spreads
collection and pipeline stages across calm overnight waves via non-blocking
checkpointed stage gates (`ALP_STAGE_GATES`), and publishes at `06:00–07:00 IST`.

## Triggers (`.github/workflows/daily.yml`)

| UTC cron      | IST   | Purpose |
|---------------|-------|---------|
| `30 19 * * *` | 01:00 | Wave 1: model discovery + RSS/NewsData/Serper + GNews wave 1 |
| `10 20 * * *` | 01:40 | Wave 2: GNews wave 2 slow collection (`ALP_GNEWS_TOPUP`) |
| `30 20 * * *` | 02:00 | Wave 3: GNews wave 3 + fact verification + deduplication |
| `0 21 * * *`  | 02:30 | Wave 4: news importance + domain relevance + selection |
| `30 21 * * *` | 03:00 | Wave 5: bilingual content editor |
| `30 22 * * *` | 04:00 | Wave 6: MCQ generator + validator + quick bites + static GK |
| `30 23 * * *` | 05:00 | Wave 7: PDF design + PDF QA (parks in `awaiting_publish`) |
| `0 0 * * *`   | 05:30 | Wave 8: pre-publish buffer / PDF QA catch-up |
| `30 0 * * *`  | 06:00 | publish window |
| `50 0 * * *`  | 06:20 | publish window backup |
| `10 1 * * *`  | 06:40 | publish window backup |

Every trigger resolves the same edition (`daily_<today in IST>`), refreshes
`state/` from the latest `main`, restores the previous run's checkpoint
artifact and resumes after the last completed stage. When a stage gate in
`ALP_STAGE_GATES` has not opened yet, `main.py` parks cleanly with status
`awaiting_stage` (exit 0); if a cron fires late or manually via
`workflow_dispatch`, past gates pass immediately so the edition catches up in
one run. Once the edition is in the Telegram ledger, later triggers end
immediately ("already published").
All runs share the `current-affairs-pipeline` concurrency group, so they
never overlap; GitHub keeps one pending run, which is fine because any run
can finish the edition.

## Paced API usage & stage gates

* **GNews (`ALP_GNEWS_MIN_INTERVAL: "15"`, `ALP_GNEWS_TOPUP: "1"`):** Calls wait
  at least 15 seconds between requests (never bursting against the 1 req/s free
  limit) and split across three 4-query overnight waves (`01:00`, `01:40`, `02:00`).
* **AI routing (`ALP_MODEL_AUTO_DISCOVERY: "1"`, `ALP_AI_CALL_INTERVAL: "1.5"`):**
  Providers default to `auto`, dynamically select live free/instruct models from
  `/models`, rotate past `404/410` retired models and upstream `429` rate limits,
  and gently space AI calls by `ALP_AI_CALL_INTERVAL` seconds.
* **Stage pacing (`ALP_STAGE_GATES`, `ALP_INTER_STAGE_PAUSE`):** Scheduled runs
  spread heavy stages across `01:00–05:30 IST` without burning failure-recovery
  attempts (`run_attempts` does not increment on planned `awaiting_stage` or
  `awaiting_publish` wakeups).

## Publish gate

`ALP_PUBLISH_NOT_BEFORE: "06:00"` (IST, edition date). If stages 00–19 finish
before 06:00 the orchestrator stops in front of `22_telegram_publisher`, sets
the job to `awaiting_publish`, keeps the checkpoints and exits 0 (green run).
The next trigger at/after 06:00 resumes at stage 22 and sends. There is no
upper bound: after 07:00 a late edition still publishes as soon as possible.
Unset/empty disables the gate (local runs, tests). `DRY_RUN=1` ignores it.
The watchdog flags an `awaiting_stage` or `awaiting_publish` job that is still
parked 90 minutes after its gate opened.

## News window

`ALP_DAILY_CUTOFF: "06:00"`. Edition D covers **D-1 06:00 IST → D 06:00 IST**,
independent of when the run happens:

* a run before 06:00 (the 01:00–05:30 overnight crons) clips the end to the
  run time (it cannot see future news), extending seamlessly as GNews waves top up;
* when the previous day's edition published, the window starts at that
  edition's recorded end, so editions are contiguous: no overlap, no gap;
* the window is recorded in `state/jobs.json` on the first attempt and reused
  by every retry/resume; `--reset` recomputes the same fixed window.

As a second guard, daily selection (stage 10) drops any candidate whose event
id, link or normalised headline was selected by one of the previous three
daily editions (`ALP_REPEAT_LOOKBACK_DAYS`, `ALP_ALLOW_REPEATS=1` disables).

## Run summary

The `Run summary` step prints raw/verified/dedup/scored/selected/reserves,
final stories, MCQs, quick bites, agri items, photos, promoted reserves and
PDF pages, plus which AI provider/model answered which task
(`logs/ai_usage.jsonl`, falling back to the stage logs), to the job log and
`$GITHUB_STEP_SUMMARY`.

## Optional: exact-time external trigger (not required)

If GitHub cron delays become unacceptable, an external scheduler can call
`workflow_dispatch` at exact times. Example with cron-job.org:

1. Create a fine-grained GitHub token limited to this repository with
   **Actions: Read and write** (nothing else).
2. In cron-job.org create a job, e.g. 02:05 and 06:01 Asia/Kolkata:
   * URL: `https://api.github.com/repos/agrilearningpoint/daily-current-affairs/actions/workflows/daily.yml/dispatches`
   * Method: `POST`
   * Headers: `Authorization: Bearer <token>`, `Accept: application/vnd.github+json`,
     `X-GitHub-Api-Version: 2022-11-28`
   * Body: `{"ref":"main"}` (no inputs → today's IST edition, strict translation)
3. Expect HTTP 204. Dispatched runs follow exactly the same idempotent path as
   the crons, so duplicates are harmless.
