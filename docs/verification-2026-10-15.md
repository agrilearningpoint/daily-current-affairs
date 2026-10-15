# Detailed unattended verification — 15 October 2026

## Scope and result

**144 tests passed with outbound Python network connections blocked**, including stage subprocesses. Local RSS fixtures were allowed; provider and Telegram HTTP responses were mocked. The twelve-step preflight, fatal Ruff checks (`F821,F822,F823`), Python compilation and workflow YAML/shell/embedded-Python validation also passed.

This is synthetic/offline verification, **not a live news, provider-credential, Telegram delivery or pinning test**. No real Telegram message was sent. No PAT was requested, used or stored.

Evidence is committed alongside this report:

- `docs/verification/2026-10-15-pytest.txt`
- `docs/verification/2026-10-15-preflight.txt`
- `docs/verification/2026-10-15-fatal-lint.txt`
- `docs/verification/2026-10-15-stage-evidence.json`

The preceding 14 October report is a historical checkpoint, not the latest result.

## Genuine defects found and fixed in this pass

1. **Wrong live publication ledger in final audit.** Publisher/pin use `published_events.json`; audit and E2E verification incorrectly required `published_jobs.json`. A shared publication-evidence contract now validates the canonical ledger.
2. **Weak receipt binding.** An old same-job success or unrelated pin could satisfy the audit. Proof now requires the exact full PDF SHA256, job, chat, positive integer message ID, and a matching verified pin receipt. Dry-run receipts cannot satisfy live proof.
3. **Blind retries after ambiguous document sends.** A timeout can mean Telegram accepted the document but its response was lost. Publication now writes a pending receipt before the request, disables blind network retries for `sendDocument`, and holds ambiguous outcomes for manual reconciliation. The watchdog does not redispatch these holds. Confirmed rate limits remain safely retryable.
4. **Corrupt ledgers silently becoming empty publication history.** Existing malformed ledgers now fail closed and remain intact; they cannot silently authorize a duplicate send. Valid legacy list receipts are still migrated.
5. **Pin cache mistaken for current state.** The live pin stage rechecks Telegram state even with a cached verified receipt. It rejects foreign-chat, invalid-message, stale-PDF and missing publication evidence. An accepted pin with a lost acknowledgement is checked through `getChat`, not treated as automatic failure.
6. **Publishing after checkpoint evidence changed.** The live orchestrated publisher now verifies intact pre-publication checkpoint evidence before a new send. Hashless legacy output cannot authorize skipping earlier producers. Period scored output is required alongside selected output.
7. **Completed jobs with lost shared receipts could silently remain successful.** They now fail with an explicit reconciliation hold instead of being automatically replayed.
8. **Automatic revised-PDF sends could duplicate an already-published edition.** Revised PDFs require explicit operator approval (`ALP_ALLOW_EDITION_REVISION=1` or the workflow's `allow_revision` input). This does not override uncertain sends. Scheduled runs keep revision approval off.
9. **Provider setup/translation mismatch.** Setup now uses the router's provider registry, including generic OpenAI-compatible and OpenRouter settings. Gemini translation uses its native request/response format instead of OpenAI `messages/choices`. Provider-model settings and secrets are consistently exposed by all three edition workflows. Model IDs remain configurable; live availability was not probed.
10. **Credential-bearing exception output.** Shared log-handler filtering redacts messages and tracebacks, and stored publication/pin errors are redacted. An empty HTTP-200 provider reply no longer counts as healthy.
11. **Stale recovery plans could dispatch old actions.** Real dispatch now requires a timezone-aware plan generated within fifteen minutes; duplicate actions are removed and exact edition dates are retained. Legacy/old plans can still be inspected with `--dry-run`.

## Full edition stage verification

Two independent RSS scenarios each produce daily, weekly and monthly editions: **six full synthetic pipeline runs**. Every resulting PDF has 15 pages and 15 validated MCQs for these fixtures. The stage-evidence JSON records job status, all stage names, artifact count, saved window, PDF SHA256, page count, question count and exact QA/health results.

| Stage | What ran / what was verified |
|---|---|
| 00 model setup | Real subprocess and dry configuration path; separate mocked provider-response classification tests |
| 01 collection | Actual local RSS fetch, historical edition window, forced initial socket closure, safe failure and recovery |
| 04 verification | Real dry-run verifier; live provenance rules separately tested without claiming fixture news is real |
| 05 deduplication | Actual canonical deduplicated output |
| 06 importance | Actual scoring output |
| 07 relevance | Actual student-domain relevance update and checkpoint digest |
| 10 selection | Actual canonical selected news |
| 11 memory | Local/shared memory persistence, feeding the period editions |
| 12 content | Actual bilingual diagnostic content; dictionary fallback stays marked for review and cannot satisfy live publication |
| 16 generation | Actual source-grounded MCQ generation and validation |
| 17 validation | Actual repeated MCQ gate and output |
| 18 design | Actual native Hindi-shaped PDF generation; cover/body render visually inspected |
| 19 QA | Actual PDF checks and exact SHA256/job-bound approval |
| 22 publish | Dry-run in full edition tests; separate non-dry code-path tests intercept every HTTP request |
| 23 pin | Dry-run in full edition tests; separate non-dry pin/permission/lost-response/cache-state tests |
| 24 audit | Actual artifact-hash/QA audit, plus separate canonical live-receipt rejection tests |
| 20 weekly | Actual verified-memory period selection and shared content-to-audit tail |
| 21 monthly | Actual verified-memory period selection and shared content-to-audit tail |

Weekly/monthly run after the fixture RSS server has been shut down. Both are also checked by the standalone canonical E2E verifier. Synthetic fallback translations visible in diagnostic PDFs are deliberately **not** represented as publication-ready Hindi.

## Recovery and side-effect scenarios

- Initial RSS socket closure: job fails at collection, publishes nothing, recovers on the next run with the same saved window.
- Completed intact edition: same-mode rerun is a no-op and leaves state bytes unchanged.
- Interruption after QA: resumes the tail without re-fetching RSS.
- **Actual process termination:** the orchestrator and paused stage process group are killed with SIGTERM, leaving a running checkpoint. The next actual orchestrator process acquires the released lock, preserves the window and successfully resumes after QA.
- Mocked successful publication → pin → final audit: exact receipt binding passes without the obsolete ledger.
- Pin permission error: stops at stage 23; fixing the mocked permission resumes without a second document send.
- Lost pin acknowledgement: current state confirms the successful pin.
- Lost document acknowledgement: only one send attempt occurs; repeated runs and revision approval cannot bypass the hold. A simulated operator receipt reconciliation resumes safely without resending.
- Source output tampering, missing period output, missing/hashless digests and escaping paths: cannot authorize skipped work or new publication.
- Old-PDF, dry-run, wrong-chat, wrong-message, absent-pin and corrupt receipts: final audit fails.
- Local bare Git concurrency, unrelated-source-change refusal, legacy ledger union and source-health union: retained regression coverage.
- Corrupt counters, exhausted budgets, stale/future/naive plans and duplicate dispatch actions: fail closed or deduplicate as appropriate.

## Reproduce offline verification

Install the repository dependencies, pytest and the native FriBidi/RAQM runtime first. Then:

```bash
PYTHONPATH="$PWD/scripts/offline_network_guard:$PWD" \
  ALP_DISABLE_POLISH=1 ALP_DISABLE_LLM_VERIFY=1 \
  python -m pytest -q

bash scripts/preflight_check.sh
ruff check main.py agents pipeline scripts tests --select F821,F822,F823
python scripts/recover_jobs.py --ref YOUR_CHECKED_OUT_BRANCH --dry-run
```

The opt-in `sitecustomize.py` guard blocks external Python `getaddrinfo` and socket connections in the test process and inherited stage subprocesses; loopback fixture traffic remains permitted. It is a verification aid, not an OS security sandbox. It is **not enabled by production workflows**.

This sandbox used `LD_LIBRARY_PATH=.venv/lib/x86_64-linux-gnu` for the locally built shaping library. Its optional build-tool chardet mismatch was corrected in the diagnostic environment; final tests emit no dependency warning.

## Operational limits — do not overstate success

- Live source reachability, current model availability, repository secrets, actual Hindi translation quality and real Telegram permissions still require a controlled deployment validation. No synthetic result proves those external services are healthy.
- Browser disconnection does not stop an already-running hosted job. External service outages still use bounded retries and recovery; indefinite execution without internet is not promised.
- Pending/uncertain publication receipts must be reconciled against the real channel and exact original PDF. **Do not simply delete them to force a resend.** A completed-job `recovery_blocked` hold should only be cleared after the missing receipts are restored and checked.
- Write-ahead local receipts protect retries while that state survives. Telegram has no idempotency token in this implementation: catastrophic runner loss before durable state upload/push remains a manual-reconciliation risk. Exactly-once delivery across such failures is not claimed.
- Checkpoint archives have 30-day retention. Expired/unavailable evidence safely rewinds; unavailable historical feeds may require intervention rather than invented backfill content.
- Changes remain on the session branch/PR #10; this work does not merge or publish to production. Hosted CI is checked separately from these local results.
