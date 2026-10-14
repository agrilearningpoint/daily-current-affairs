# Unattended pipeline verification — 14 October 2026

## Result

- Final full suite: **103 passed, 1 nonfatal dependency warning** in 50.37 seconds.
- Fatal Ruff checks (`F821,F822,F823`): passed.
- Python compilation, workflow YAML parsing and embedded Python compilation: passed.
- Twelve-step preflight: passed (95-test checkpoint, before the final eight regressions were added).
- Daily **16 stages**, weekly **10 stages**, monthly **10 stages** exercised using actual stage subprocesses, isolated repositories and synthetic inputs.
- **No real Telegram document was sent or pinned. No PAT was used or stored.**

The synthetic articles are test fixtures, not real current affairs. Dry-run success is not a claim that live news or provider credentials have been validated.

## Stage evidence

`tests/test_daily_integration.py::test_daily_pipeline_end_to_end_without_external_services` runs twice: normal RSS and a forcibly dropped first RSS connection.

| Stage | Verification performed |
|---|---|
| 00 model orchestrator | Dry-run configuration/startup; real provider probes intentionally bypassed |
| 01 source fetch | Local synthetic RSS, exact historical date window; connection-drop failure and subsequent recovery |
| 04 fact verification | Explicitly labelled dry-run verification; separate unit tests enforce live provenance |
| 05 deduplication | Canonical deduplicated edition output produced |
| 06 importance scoring | Canonical scored events produced |
| 07 student relevance | Scored output updated; latest digest captured while preserving earliest producer |
| 10 final selection | Canonical selected edition produced |
| 11 importance memory | Local history and shared event database written; persistence failure now critical |
| 12 content editor | Bilingual diagnostic content produced; fallback translation remains flagged for review |
| 16 MCQ generator | Source-grounded questions generated and validated |
| 17 MCQ validator | Validation rerun; canonical validated MCQ output produced |
| 18 PDF design | Actual PDF generated with native Hindi shaping runtime |
| 19 PDF QA | Exact job ID and PDF SHA256 approval checked |
| 22 publisher | Dry-run only; missing/failed/wrong-job/changed-PDF approvals rejected in separate tests |
| 23 pin verifier | Dry-run only; stage is critical in production |
| 24 final health audit | Edition checkpoint hashes and exact PDF QA checked; health report required for success |
| 20 weekly editor | Verified shared database, exact weekly range, independent period selection |
| 21 monthly editor | Verified shared database, exact monthly range, independent period selection |

Weekly/monthly execute the shared content → MCQ → PDF → QA → dry publish → dry pin → audit tail **after the RSS server has been shut down**. The canonical `scripts/verify_e2e.py` separately verifies both resulting editions.

## Failure, recovery and safety checks

- Abrupt RSS socket closure stops the critical collection stage without writing a publication success ledger. A subsequent run succeeds and retains the saved window.
- Simulated interruption immediately after PDF QA resumes from QA with RSS unavailable; raw source output remains unchanged.
- Repeating a completed, intact same-mode daily edition is a genuine no-op: job state bytes do not change.
- Missing/tampered output rewinds to its earliest producer. Escaping checkpoint paths are rejected.
- Concurrent pipeline lock acquisition is refused without entering the pipeline or creating job state.
- Provider-key redaction covers both plain and URL-encoded values in persisted orchestrator output.
- Live verification rejects a lone ordinary feed, sibling publisher subdomains and contradictory headline numbers. An official same-publisher primary source or two independent corroborating publishers is required.
- Live publication requires explicit verified provenance and completed translation review. Boolean, missing, negative, zero and string Telegram message IDs cannot become publication successes.
- Period selection rejects records without live provenance outside dry-run.
- Watchdog uses a six-execution recovery budget by default. Exhausted/invalid counters produce a manual-attention result, not an unlimited dispatch loop.
- Recovery plan parser dispatches deduplicated, canonical exact-date daily/weekly/monthly jobs to the correct workflow.
- State synchronization was tested against **isolated local bare Git repositories**, with conflicting concurrent job updates: both jobs survive and no force push is used. Unrelated source modifications are refused. Legacy ledgers and nested source-health maps are preserved.

## Workflow repairs

- Removed calls to nonexistent `store.pull/push/prune` APIs.
- Watchdog consumes the root structured recovery plan and dispatches exact edition dates.
- Daily/weekly/monthly persist start markers before execution, so a hosted hard interruption is visible to watchdog.
- Edition checkpoint archives cover data, PDFs and QA evidence, with 30-day retention. The uploaded archive reference is recorded only after an artifact is created.
- Subsequent runs restore the recorded archive before resuming. Missing/expired/unavailable archives safely rewind rather than authorizing skipped work.
- State-only fetch/merge/push retries are bounded and preserve local generated state. Publication/pin ledgers are included, not just jobs.json.
- Weekly/monthly install the native Hindi shaping dependency and run their full canonical publication pipeline.
- Workflow date inputs travel through environment variables rather than direct shell interpolation.
- Preflight no longer masks import failures or failed pytest exits, and the E2E verifier no longer requires obsolete uppercase statuses or legacy duplicate artifacts.

## Reproduce

```bash
ALP_DISABLE_POLISH=1 ALP_DISABLE_LLM_VERIFY=1 python -m pytest -q
ruff check main.py agents pipeline scripts tests --select F821,F822,F823
bash scripts/preflight_check.sh
python scripts/verify_e2e.py --job-type daily --date YYYY-MM-DD
python scripts/recover_jobs.py --ref YOUR_CHECKED_OUT_BRANCH --dry-run
```

PDF tests need FriBidi/RAQM. This sandbox used an isolated virtual environment and `LD_LIBRARY_PATH=.venv/lib/x86_64-linux-gnu`; hosted workflows install the native library using apt.

## Limits and remaining live validation

- No live news-provider, LLM-provider, Telegram delivery or Telegram pinning test was performed. Their credentials/services must be available for production; synthetic dry-run flags cannot satisfy the live publish gate.
- User-browser disconnection does not interrupt an already-running hosted Actions job. Provider/network outages still use bounded retry/recovery; **indefinite execution without internet is not promised**.
- Archive retention is finite. If evidence cannot be restored and source feeds no longer expose historical articles, a backfill may fail safely and require intervention.
- Requests emitted a nonfatal compatibility warning for the sandbox's installed chardet version. Broad advisory Ruff cleanliness is not claimed.
- Changes are on the session branch and PR #10, not merged into the production branch. Hosted CI results must be checked separately from these local results.
