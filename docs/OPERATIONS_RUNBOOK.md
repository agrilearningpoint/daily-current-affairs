# Operations Runbook — daily-current-affairs

Audience: on-call operator / SRE. Everything here is copy-pasteable.
See also [`production-audit.md`](production-audit.md) and
[`production-readiness.md`](production-readiness.md),
[`source-registry.md`](source-registry.md), and [`pdf-design.md`](pdf-design.md).

---

## 1. What runs, and when

| Workflow | Schedule (UTC) | IST | Edition |
| --- | --- | --- | --- |
| `daily.yml` | `0 2 * * *` | 07:30 | today (IST) |
| `weekly.yml` | `30 0 * * 0` (Sun) | 06:00 | last 7 days |
| `monthly.yml` | `30 0 1 * *` | 06:00 | previous month |
| `watchdog.yml` | `*/5 * * * *` | every 5 min | detect stuck/failed, commit plan |

All four share `concurrency.group: current-affairs-pipeline` →
**daily, weekly, monthly and watchdog never run at the same time**. A run that
arrives while another is executing waits (it is not cancelled). This is
deliberate: they all commit to the same git-tracked state files.

Pipeline stages (daily): `00 → 01 → 04 → 05 → 06 → 07 → 10 → 11 → 12 → 16 →
17 → 18 → 19 → 22 → 23 → 24`. Weekly/monthly replace the collection/selection
front with `20_weekly_editor` / `21_monthly_editor` and then reuse the same
`12 … 24` tail.

Orchestrator exit codes (`python main.py`):

| Code | Meaning |
| --- | --- |
| `0` | success, or a completed edition with intact checkpoints (no-op) |
| `1` | a critical stage failed, or the job needs recovery / manual reconciliation |
| `2` | bad invocation or fatal configuration error |

---

## 2. Configuration

1. Copy the template and fill real values locally: `cp .env.example .env`
   (never commit `.env`).
2. In GitHub: **Settings → Secrets and variables → Actions**.

Required secrets:

| Secret | Purpose |
| --- | --- |
| `TELEGRAM_BOT_TOKEN` | publishing |
| `TELEGRAM_CHAT_ID` | publishing target |
| `ADMIN_ID` | watchdog alert recipient |

Optional: `GEMINI_API_KEY`, `GROQ_API_KEY`, `OPENAI_API_KEY`,
`OPENROUTER_API_KEY`, `MISTRAL_API_KEY`, `NVIDIA_API_KEY`, `JINA_API_KEY`,
`NEWSDATA_API_KEY`. With none set the pipeline runs heuristic-only.

Common tuning (Repository **Variables** or workflow `env`):

| Var | Default | Effect |
| --- | --- | --- |
| `ALP_STAGE_TIMEOUT` | 900 | seconds per stage before kill |
| `ALP_MAX_RETRIES` | 2 | retries per stage |
| `ALP_RUNNING_STUCK_HOURS` | 6 | watchdog stall threshold |
| `MIN_CONFIDENCE_THRESHOLD` | 0.3 | verification pass bar |
| `ALP_ALLOW_EDITION_REVISION` | 0 | allow re-publishing a changed edition |
| `ALP_ALLOW_FALLBACK_TRANSLATION` | 0 | allow shipping fallback Hindi |
| `DRY_RUN` | 0 | `1` = never touch Telegram |

Legacy aliases (`STAGE_TIMEOUT_SECONDS`, `MAX_STAGE_RETRIES`,
`WATCHDOG_STUCK_HOURS`, `REQUEST_TIMEOUT`) are still honoured; the
`ALP_`-prefixed name always wins.

---

## 3. Everyday operations

### 3.1 Confirm a run succeeded

```bash
python - <<'PY'
import json
from main import load_jobs_state
jobs = load_jobs_state(strict=True)
for job_id, j in sorted(jobs.items())[-5:]:
    print(job_id, j.get("status"), j.get("last_success_stage"),
          j.get("failed_stage", ""), j.get("recovery_blocked", ""))
PY
```

A healthy completed edition has `status: success`,
`last_success_stage: 24_final_health_audit` (or `23_...` just after publish),
and no `recovery_blocked`.

### 3.2 Inspect the pinned post / publication receipt

```bash
python - <<'PY'
from pipeline.publication import records_at, PUBLICATION_LEDGER, PIN_LEDGER
from pathlib import Path
for name in (PUBLICATION_LEDGER, PIN_LEDGER):
    p = Path("state") / name
    print("==", p, "exists:", p.exists())
    if p.exists():
        for k, v in records_at(p).items():
            print("  ", k, {x: v.get(x) for x in ("job_id","status","message_id","dry_run","file_sha256")})
PY
```

### 3.3 Watchdog

```bash
python main.py --watchdog                 # uses ALP_RUNNING_STUCK_HOURS
python main.py --watchdog --stuck-hours 2 # tighten for a manual check
```

Exit `0` all clear · `1` recovery needed (plan written) · `2` recovery budget
exhausted → manual attention. The plan is written to `recovery_plan.json`.

---

## 4. Manual runs

### 4.1 Backfill / specific date

```bash
python main.py --job-type daily   --date 2026-10-04
python main.py --job-type weekly  --date 2026-10-11
python main.py --job-type monthly --date 2026-09-30
```

The requested `--date` is authoritative; backfills never become "today".
In Actions use **Run workflow → date**.

### 4.2 Reset a job from scratch

```bash
python main.py --job-type daily --date 2026-10-04 --reset
```

`--reset` clears that one job's state only and re-runs from the first stage.
Use it after code/content fixes.

### 4.3 Publish a corrected (revised) edition

1. Re-run with `--reset` (local) or the workflow `reset=true`, **and**
2. `ALP_ALLOW_EDITION_REVISION=1` (or workflow `allow_revision=true`).

Without both, the publisher records `blocked_revision` and the job fails closed
— this is intentional. Revision approval never overrides an *uncertain* send.

### 4.4 Dry run (published nothing)

```bash
DRY_RUN=1 python main.py --job-type daily --date 2026-10-04   # bash
$env:DRY_RUN=1; python main.py --job-type daily --date 2026-10-04   # PowerShell
```

---

## 5. Recovery playbook

### 5.1 A job failed / is stuck

1. Read the plan and the failing stage log:

```bash
python main.py --watchdog
Get-Content logs/stages/<job_id>/<failed_stage>.log -Tail 100   # PowerShell
tail -n 100 logs/stages/<job_id>/<failed_stage>.log             # bash
```

2. If it is a transient failure, simply re-run the same edition — the
   orchestrator resumes after the last stage whose outputs are intact
   (verified by SHA-256, not by existence):

```bash
python main.py --job-type daily --date 2026-10-04
```

3. If `recovery_blocked` is set, **do not** force a replay. This means the
   edition may already be published (or its PDF is gone). Reconcile manually:

```bash
python - <<'PY'
from main import load_jobs_state
j = load_jobs_state(strict=True)["daily_2026-10-04"]
print(j.get("status"), j.get("recovery_blocked"), j.get("last_error"))
PY
```

   - If the edition **is** live and correct: clear the block by re-running the
     watchdog path (`python main.py --watchdog`) — a live publication receipt
     makes `execute_job` a clean no-op returning `0`.
   - If a correction is genuinely needed: follow §4.3.

4. `recovery_plan.json` actions are executed by the daily workflow. To inspect
   or replay them manually:

```bash
python scripts/recover_jobs.py --plan recovery_plan.json --ref main --dry-run
```

### 5.2 Two runs collided on state commits

`scripts/sync_state.py` does a conflict-safe merge (it unions per-job entries and
never discards the other side's jobs). After any overlap:

```bash
python scripts/sync_state.py --branch main --message "state: manual reconcile"
```

### 5.3 State schema drift

```bash
python maintenance/migrate_state.py --dry-run
python maintenance/migrate_state.py --reset-failed-final --stuck-hours 6
```

---

## 6. Offline dry run (no network, no Telegram, no credits)

The full pipeline is exercised end-to-end against a local synthetic RSS feed:

```bash
python -m pytest -q tests/test_daily_integration.py::test_daily_pipeline_end_to_end_without_external_services
```

Library-level end-to-end (dedup → score → content → MCQ → PDF → QA):

```bash
python -m pytest -q tests/test_pipeline_offline.py
```

Verify a produced edition's artifacts/ledgers (used inside CI):

```bash
python scripts/verify_e2e.py --job-type daily --date 2026-10-04 --root .
```

Diagnostics / setup hints:

```bash
python scripts/diagnose.py --fix-hints
```

---

## 7. Troubleshooting

| Symptom | Likely cause | Action |
| --- | --- | --- |
| `stage 01_source_fetch: ... exit code 2` | zero usable articles (all feeds down / window empty) | check source health (`state/source_health.json`), retry later, verify `ALP_FEED_TIMEOUT` |
| Job fails at `22_telegram_publisher` with `TELEGRAM_BOT_TOKEN is missing` | secret not set | add the secret or run `DRY_RUN=1` |
| Job fails with `blocked_revision` | a changed edition and no approval | §4.3 if the change is intended; otherwise investigate why the PDF changed |
| Job fails with `publication evidence missing` | ledger lost/rotated after a publish | reconcile per §5.1 — never blind-replay |
| Job stuck `running` > `ALP_RUNNING_STUCK_HOURS` | runner died mid-stage | `--watchdog`, then re-run same date |
| `completed edition PDF missing` | `output/<job>.pdf` absent | restore from the checkpoint artifact, or `--reset` to regenerate |
| Text renders without Hindi shaping | Pillow without RAQM (local Windows) | install `libraqm`/HarfBuzz, or set `ALP_ALLOW_UNSHAPED_DEV_PDF=1` **for dev only** |
| `ruff` shows errors in CI | repo has pre-existing lint debt; step is non-blocking | run `ruff` locally on the files you changed |
| `main.py: invalid ALP_STAGE_TIMEOUT` | non-integer value | fix the variable; startup validation now fails loudly |

---

## 8. Escalation / manual reconciliation checklist

When automatic recovery is refused (`recovery_blocked`):

- [ ] Confirm whether the edition is **actually live** on the channel
      (`state/published_events.json` + `state/pin_verification.json`, §3.2).
- [ ] If live and correct → no action; the next run is a clean no-op.
- [ ] If live but wrong → decide: revise (§4.3) or ask an admin to delete the
      message, then revise.
- [ ] If **not** live → safe to re-run the same date (§5.1 step 2).
- [ ] Record the decision in the issue/PR so the audit trail is explicit.

Never clear `recovery_blocked` by editing `state/jobs.json` by hand; re-run via
the orchestrator so checkpoints/ledgers stay consistent.
