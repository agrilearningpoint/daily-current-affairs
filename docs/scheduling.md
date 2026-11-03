# Daily schedule: generate 02:00–04:00 IST, publish 06:00–07:00 IST

GitHub Actions `schedule` is best effort. On 2026-11-03 the single 04:05 IST
cron (`35 22 * * *`) started at 09:09 IST and the PDF reached Telegram at 09:17.
The daily workflow therefore uses several idempotent triggers plus a publish gate.

## Triggers (`.github/workflows/daily.yml`)

| UTC cron      | IST   | Purpose |
|---------------|-------|---------|
| `30 20 * * *` | 02:00 | generation |
| `0 21 * * *`  | 02:30 | generation backup |
| `30 21 * * *` | 03:00 | generation backup |
| `30 22 * * *` | 04:00 | generation backup |
| `30 0 * * *`  | 06:00 | publish window |
| `50 0 * * *`  | 06:20 | publish window backup |
| `10 1 * * *`  | 06:40 | publish window backup |

Every trigger resolves the same edition (`daily_<today in IST>`), refreshes
`state/` from the latest `main`, restores the previous run's checkpoint
artifact and resumes after the last completed stage. Once the edition is in
the Telegram ledger, later triggers end immediately ("already published").
All runs share the `current-affairs-pipeline` concurrency group, so they
never overlap; GitHub keeps one pending run, which is fine because any run
can finish the edition.

## Publish gate

`ALP_PUBLISH_NOT_BEFORE: "06:00"` (IST, edition date). If stages 00–19 finish
before 06:00 the orchestrator stops in front of `22_telegram_publisher`, sets
the job to `awaiting_publish`, keeps the checkpoints and exits 0 (green run).
The next trigger at/after 06:00 resumes at stage 22 and sends. There is no
upper bound: after 07:00 a late edition still publishes as soon as possible.
Unset/empty disables the gate (local runs, tests). `DRY_RUN=1` ignores it.
The watchdog flags an `awaiting_publish` job that is still parked 90 minutes
after its gate opened.

## News window

`ALP_DAILY_CUTOFF: "06:00"`. Edition D covers **D-1 06:00 IST → D 06:00 IST**,
independent of when the run happens:

* a run before 06:00 (the 02:00–04:00 generation crons) clips the end to the
  run time (it cannot see future news);
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
