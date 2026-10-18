# Production Audit — daily-current-affairs

Edition audited: `main` @ `4af796d` (`state: daily checkpoint: merge state [skip ci]`)
Audit date: 2026-10-18
Auditor role: Principal Python Engineer / SRE / QA Architect
Method: every reported finding was re-verified against the checked-out source
(file + line evidence below) before any change. A finding is only marked *Fixed*
once a deterministic, offline regression test covers it.

---

## 1. Environment & baseline evidence

| Item | Value |
| --- | --- |
| Platform | Windows (`win32`), PowerShell |
| Local interpreter | CPython 3.14.7 (repo targets 3.11; `pyproject.toml` requires `>=3.11`) |
| Initial checkout | `main` @ `4af796d`; existing local hardening changes were preserved |
| `python -m compileall -q .` | exit 0 |
| `python main.py --help` | exit 0 |
| Test suite before this execution | **215 passed, 1 skipped** |
| Test suite final | **228 passed, 0 skipped** |
| Offline subprocess E2E (`test_daily_pipeline_end_to_end_without_external_services`) | **2 passed** |
| `ruff check` (new files) | clean |
| Ruff delta across touched tracked Python files | **−60 findings** vs `HEAD`; legacy repo lint debt remains |

The PDF offline test no longer skips on Windows when Pillow lacks RAQM but the
production `uharfbuzz` + `freetype` shaping backend is available. The exact
Python 3.11 CI run is still an external release gate; local interpreter is 3.14.7.

---

## 2. Findings summary

| ID | Severity | Area | Verdict | Status |
| --- | --- | --- | --- | --- |
| P0-1 | P0 | `pipeline/claim_verifier.py` calls non-existent AI-router API | CONFIRMED | Fixed + tested |
| P0-2 | P0 | `pipeline/telegram_api.py` calls `store.is_job_published` (absent) | CONFIRMED | Fixed + tested |
| P0-3 | P0 | `pipeline/telegram_api.py` leaked an open file handle | CONFIRMED | Fixed + tested |
| P0-4 | P0 | `main.py` completed-edition branch reads PDF unguarded (crash) | CONFIRMED | Fixed + tested |
| P0-5 | P0 | `.env.example` documents variable names the code never reads | CONFIRMED | Fixed + tested |
| P1-1 | P1 | `pipeline/store.py` file lock is a silent no-op on Windows | CONFIRMED | Fixed + tested |
| P1-2 | P1 | `main.py` weekly/monthly via `DAILY_STAGES[8:]` slicing | CONFIRMED | Fixed + tested |
| P1-3 | P1 | Workflow concurrency groups differ → shared-state commit races | CONFIRMED | Fixed |
| P2-1 | P2 | `pipeline/scoring.py` keyword typo `"y ojana"` (+ lint) | CONFIRMED (benign) | Fixed |
| P2-2 | P2 | `src/generate_pdf.py` uses MD5 for a cache key | CONFIRMED (benign) | Fixed |
| P2-3 | P2 | `pipeline/ai_translator.py` LRU cache is not thread-safe | CONFIRMED | Fixed |
| P2-4 | P2 | `pipeline/01_source_fetch.py` declares `ROOT` twice | CONFIRMED (cosmetic) | Fixed |
| — | — | Reported: publishing stages missing from `checkpoints.STAGE_FILES` → duplicate Telegram sends | **NOT A DEFECT** | Verified safe |
| — | — | Reported: completed-job replay uses "existence only" | **PARTLY TRUE** | Hardened |

---

## 3. Detailed findings

### P0-1 — `claim_verifier.py` used a non-existent AI-router API  ✅ Fixed

**Evidence (before):** `pipeline/claim_verifier.py`

```
97:   from pipeline.ai_router import get_router      # no such symbol
98:   self._router = get_router()
109:  content = router.read_url(url)                  # no such method
225:  response = router.generate(prompt, task="verification")   # no such method
```

`pipeline/ai_router.py` exports `route()`, `stats()`, `is_configured()`,
`reset()`, `clear_cache()`, `list_providers()`. There is **no** `get_router`,
`read_url`, or `generate`.

**Impact:** the `ImportError` is swallowed by a bare `except`, so `_get_router()`
returned `None` for every item and verification silently failed closed forever.
The module is not wired into any production stage (verified repo-wide: no
importer), so this was a latent, silently-broken capability rather than a live
outage — but it is still a real defect and a lie in the module contract.

**Fix:** `pipeline/claim_verifier.py` rewritten to:
- use the real `pipeline.ai_router.route()` / `is_configured()`;
- separate page retrieval (`fetch_page`, injectable) from AI adjudication;
- never fabricate a verdict — fetch/AI failure yields `ERROR`/`UNVERIFIED`;
- distinguish `VERIFIED / PARTIAL / UNVERIFIED / CONTRADICTED / ERROR`;
- treat an unsupported claim as `UNVERIFIED`, never automatically false;
- require evidence (page text) before any `VERIFIED`.

**Tests:** `tests/test_claim_verifier.py` (13 cases) — missing URL, unreachable
source, matched numeric claim, unsupported claim, AI unavailable, AI support, AI
contradiction, malformed AI JSON, provider failure, non-HTTP scheme rejection,
claim de-duplication, and `get_router` non-reintroduction.

---

### P0-2 — `telegram_api.py` called `store.is_job_published`, which did not exist  ✅ Fixed

**Evidence (before):** `pipeline/telegram_api.py:38` → `_store.is_job_published(job_id)`.
`pipeline/store.py` defined only `is_published(key)` / `load_published()`.
The `AttributeError` was caught by `except Exception: pass`, after which a
fallback did `job_id in str(data)` over the entire ledger JSON — a substring
search that can match unrelated fields and is not a valid idempotency contract.

**Impact:** the idempotency guard was unreliable. The module is not imported by
any production stage or workflow (verified), so this did not cause a live
duplicate; it is nonetheless a contract defect.

**Fix:**
- added `pipeline.store.is_job_published(job_id)` — scans ledger **records** and
  requires `status == "success"`, `not dry_run`, and a *positive integer*
  `message_id` (same contract as `pipeline/publication.py`);
- `telegram_api._already_published()` now calls it and **fails closed** (treats
  unreadable ledgers as "already published") so a bad ledger can never cause an
  uncontrolled duplicate upload.

**Tests:** `tests/test_telegram_api.py`, `tests/test_store_published.py`
(live success vs dry-run vs `sending` vs zero/`bool` message id; fail-closed).

---

### P0-3 — `telegram_api.py` leaked the PDF file handle  ✅ Fixed

**Evidence (before):** `open(pdf_path, "rb")` was passed straight into
`requests.post(files=...)` with no context manager. On failure the handle was
never closed.

**Fix:** wrapped in `with open(pdf_path, "rb") as handle:` and asserted in
`tests/test_telegram_api.py::test_send_document_closes_file_handle` by capturing
the file object and checking `.closed is True` after the call.

**Also improved in the same file:** HTTP failures are now classified
`TelegramRetryable` (429 with `retry_after`, 5xx, ambiguous) vs
`TelegramPermanent` (400/401/403, missing token).

---

### P0-4 — `main.py` read the completed-edition PDF without an existence check  ✅ Fixed

**Evidence (before):** `main.py`

```python
digest = hashlib.sha256((ROOT / f"output/{job_id}.pdf").read_bytes()).hexdigest()
```

If the PDF was missing or unreadable this raised `FileNotFoundError`/`OSError`
inside `execute_job`, crashing the orchestrator instead of failing the job
cleanly.

**Fix:** the completed-edition branch now
- checks `pdf_path.is_file()` first and fails closed with
  `recovery_blocked = "completed edition PDF missing"`, exit code 1;
- catches `OSError` on `read_bytes()` for the unreadable case.

**Tests:** `tests/test_publication_safety.py::test_completed_edition_with_missing_pdf_fails_closed`.

**Nuance verified:** the replay path already uses **content** hashes, not mere
existence — `pipeline/checkpoints.capture()/resume_after()` record and validate
`sha256` of every declared stage output. A completed job with a *changed* PDF is
therefore not treated as complete; it resumes the tail, and the publisher blocks
a changed edition unless `ALP_ALLOW_EDITION_REVISION=1`. Duplicate Telegram
sends are additionally prevented by the publisher's write-ahead ledger
(status `sending` is persisted **before** the HTTP request). No change was made
to that (correct) design; only the crash was fixed.

---

### P0-5 — `.env.example` documented names the code never reads  ✅ Fixed

**Evidence:** names present in the old `.env.example` but **not read anywhere**:
`STAGE_TIMEOUT_SECONDS`, `MAX_STAGE_RETRIES`, `WATCHDOG_STUCK_HOURS`,
`MAX_RESPONSE_BYTES`, `MAX_ARTICLES_PER_SOURCE`, `NEWS_SOURCES_FILE`, `TEST_DATE`.
Meanwhile the code and workflows read `ALP_STAGE_TIMEOUT`, `ALP_MAX_RETRIES`,
`ALP_RUNNING_STUCK_HOURS`, `ALP_FEED_TIMEOUT`, …

**Impact:** an operator copying `.env.example` to `.env` and tuning
`STAGE_TIMEOUT_SECONDS` would silently change nothing.

**Fix:**
- `.env.example` rewritten so **every active assignment is a name the code
  actually reads** (verified: all 74 names match a real accessor);
- documented that `ALP_STAGE_TIMEOUT` / `ALP_MAX_RETRIES` /
  `ALP_RUNNING_STUCK_HOURS` / `REQUEST_TIMEOUT` have legacy aliases;
- `main.py` gained `_int_env`/`_float_env` so the legacy names still work
  (the `ALP_`-prefixed name wins), and `01_source_fetch.py` accepts
  `REQUEST_TIMEOUT` as an alias for `ALP_FEED_TIMEOUT`;
- the example token placeholder is now obviously fake (`replace_with_...`, no
  `:`), so the CI secret scanner and humans are not misled.

**Tests:** `tests/test_env_example.py` (11 cases) including
`test_every_documented_name_is_actually_read_by_code`, which fails if a future
doc lists a name the code does not read.

Also added: startup validation (`main.validate_settings`) that rejects a
non-positive stage timeout, negative retries, or non-positive stuck-hours, and a
prominent startup warning when a real (non-dry) run lacks Telegram credentials.

---

### P1-1 — `store.py` file lock silently no-op on Windows  ✅ Fixed

**Evidence (before):** `pipeline/store.py::_file_lock` did
`import fcntl` … `except ImportError: pass`, so on Windows (no `fcntl`) it took
no lock at all while still opening the lock file.

**Fix:** delegate to `pipeline.persistence.file_lock`, which uses `fcntl.flock`
on POSIX and `msvcrt.locking` on Windows (both real locks).

**Test:** `tests/test_store_published.py::test_file_lock_delegates_to_persistence`.

---

### P1-2 — weekly/monthly stage selection used positional slicing  ✅ Fixed

**Evidence (before):** `main.py` built `WEEKLY_STAGES`/`MONTHLY_STAGES` as
`DAILY_STAGES[8:]`. `DAILY_STAGES[8:]` happened to be correct, but any insertion
or reorder of a daily stage would silently change what weekly/monthly run.

**Fix:** the shared tail is now selected **by stage name** while preserving
`DAILY_STAGES` order (`main._TAIL_STAGE_NAMES` / `main._POST_SELECTION_STAGES`).

**Test:** `tests/test_stage_selection.py` (6 cases), including a simulated
insertion of a new daily stage that must not alter the weekly/monthly tail.

---

### P1-3 — Workflow concurrency groups allowed shared-state commit races  ✅ Fixed

**Evidence (before):** `daily.yml → group: daily-pipeline`,
`weekly.yml → current-affairs-weekly`, `monthly.yml → current-affairs-monthly`,
`watchdog.yml → current-affairs-watchdog`. All four commit to the same
git-tracked state (`state/jobs.json`, publication/pin ledgers,
`recovery_plan.json`) via `scripts/sync_state.py`. Distinct groups meant a
scheduled weekly and daily run could overlap and race on those commits.

**Fix:** all four workflows now share `concurrency.group: current-affairs-pipeline`
(`cancel-in-progress: false`), so runs serialise. The application-level
`pipeline.lock` / `state.lock` still guard same-runner re-entry.

> Note: correcting a large same-file line-ending/encoding issue was intentionally
> out of scope; only the concurrency key changed.

---

### P2 findings

| ID | Finding | Fix |
| --- | --- | --- |
| P2-1 | `pipeline/scoring.py:325` keyword list contained the typo `"y ojana"` immediately before the correct `"yojana"` (benign), plus an inline redundant `import re` and 6 pre-existing `E701`/`W292` lint errors | typo removed, inline import removed, lint fixed; file now `ruff`-clean |
| P2-2 | `src/generate_pdf.py:527` used `hashlib.md5(...)` for a temp-file cache key | switched to SHA-256 (cache key only; no compatibility concern) |
| P2-3 | `pipeline/ai_translator.py::_LRUCache` had no lock (unlike `ai_router`'s cache) | added `threading.Lock` |
| P2-4 | `pipeline/01_source_fetch.py` declared `ROOT` twice (lines 39 and 45) | removed the duplicate |

---

## 4. Findings that did **not** hold up

### "Publishing stages (00/22/23) missing from `checkpoints.STAGE_FILES` → resume after publish duplicates Telegram messages" — **NOT A DEFECT**

Verified behaviour instead of assuming:

1. `capture()` for a stage with no `STAGE_FILES` entry is a **no-op** (it returns
   the artifact map unchanged), so publish stages simply declare no checkpoint.
2. `resume_after()` validates the `sha256` of every *declared* artifact and, when
   all are valid, returns the **last successful stage** (`23_telegram_pin_verifier`),
   so the orchestrator resumes at `24_final_health_audit` and never re-enters a
   pre-QA stage.
3. Even if a publish stage is re-entered, `agents/22_telegram_publisher.py`
   persists a write-ahead ledger record (`status: sending`) **before** the HTTP
   call and refuses to re-send once a live receipt exists; `agents/23` verifies
   the pin against the sent `message_id`.
4. `agents/24_final_health_audit.py` requires `resume_after(...) == "23_telegram_pin_verifier"`
   **and** `publication_issues(...) == []` before declaring success.

`tests/test_publication_safety.py` (25 cases) pins this contract, including
"lost publication evidence is not replayed", "confirmed rate limit is retryable",
and "uncertain sends are never auto-retried".

### "Completed-job replay uses existence only" — **PARTLY TRUE**

Replay state stores `sha256` digests (`pipeline/checkpoints.py`), and the
completed-edition branch hashes the PDF. The genuine gap was the **crash** on a
missing PDF (P0-4); the digest logic itself is content-based and correct.

---

## 5. Deferred / not-changed (documented, out of scope by design)

| Item | Why not changed |
| --- | --- |
| ~~Duplicate/parallel modules~~ — **resolved in this pass** | `pipeline/mcq_validator.py` and `pipeline/model_manager_v2.py` were **removed** after a full reference proof (no importer, no CI/tool/doc existence list). Locked by `tests/test_module_consolidation.py`. See §7. |
| Retained non-stage modules — `pipeline/verify.py`, `pipeline/claim_verifier.py`, `pipeline/telegram_api.py` | **Deliberately kept.** `pipeline/verify.py` is a documented standalone operator utility (referenced by `.env.example`). `claim_verifier.py` / `telegram_api.py` were repaired in this branch and carry fail-closed logic + tests; deleting tested failure-handling would be a net loss. Each is now explicitly documented in §7. |
| `pipeline/state.py` uses `pytz` while the rest uses `zoneinfo` | `pytz` is pinned in `requirements.txt`; low risk; consolidation would touch 6 agents. |
| `ruff` is `continue-on-error: true` in CI, and the repo has ~150 pre-existing lint errors (test style, legacy scripts) | Making lint blocking now would fail unrelated code. The two worst offenders (`model_manager_v2.py`, `mcq_validator.py`) were removed in this pass. Recommended as a follow-up (see `production-readiness.md`). |
| Large repeated watermark on content pages | Measured: peak deviation from white ≤ ~1 RGB unit at 7 % alpha (see `pdf-design.md`); it does not obscure text, so it was left in place rather than risk a layout change. |
| Local Windows PDF rendering without RAQM | **Resolved as a test gap**: the offline PDF E2E test previously skipped on `win32` whenever Pillow lacked RAQM, even though the `uharfbuzz`+`freetype` shaping path was available. The guard now checks the *real* shaping backend, so the test runs and passes on this host (see §7). |

---

## 6. Files changed

```
.env.example                             (rewritten: names aligned with code)
.github/workflows/daily.yml              (unified concurrency group)
.github/workflows/weekly.yml             (unified concurrency group)
.github/workflows/monthly.yml            (unified concurrency group)
.github/workflows/watchdog.yml           (unified concurrency group)
main.py                                  (PDF guard, env aliases+validation, named tail)
pipeline/01_source_fetch.py              (dedupe ROOT, REQUEST_TIMEOUT alias)
pipeline/ai_translator.py                (thread-safe LRU cache)
pipeline/claim_verifier.py               (repaired AI-router integration, statuses)
pipeline/scoring.py                      (typo + lint)
pipeline/store.py                        (real file lock, is_job_published)
pipeline/telegram_api.py                 (ledger contract, file handle, error classes)
src/generate_pdf.py                      (MD5 → SHA-256 cache key; Part 8 palette/typography)
tests/test_claim_verifier.py             (new)
tests/test_env_example.py                (new)
tests/test_stage_selection.py            (new)
tests/test_store_published.py            (new)
tests/test_telegram_api.py               (new)
tests/test_publication_safety.py         (added missing-PDF guard test)
```

Files changed in the **second pass** (Parts 2–17) are listed in §8.

---

## 7. Second pass — verified findings and fixes (Parts 2–17)

Every item below was reproduced against the checked-out tree before the change and
re-verified after it. Evidence commands are shown so the result can be re-run.

### 7.1 Source registry — duplicate publisher fetch (fixed)

* **Finding.** `config/feeds.py::VERIFIED_RSS` listed *The Hindu* as
  `https://www.thehindu.com/news/national/feeder/default.rss` while
  `config/sources.py::ALL_SOURCES` listed it as
  `https://www.thehindu.com/feeder/default.rss`. `pipeline/source_registry.py`
  dedupes the merged registry **by exact RSS URL**, so both URLs survived and the
  same publisher was fetched twice per edition.
* **Fix.** The URL in `VERIFIED_RSS` was made byte-identical to the `ALL_SOURCES`
  entry, with a comment stating the invariant.
* **Regression test.** `tests/test_source_registry.py::test_verified_rss_and_all_sources_agree_on_shared_publishers`
  fails if any publisher shared between the two files uses different URLs. Proven
  to have teeth: feeding the old URL through the detector returns
  `['https://www.thehindu.com/feeder/default.rss']` → `would_flag: True`.

### 7.2 Source registry — dead / non-feed URLs (fixed, live-verified)

Live HTTP probe on 2026-10-18 (`scripts/source_health.py`, `requests`+`feedparser`):

| Source | Old URL | Result | New URL |
| --- | --- | --- | --- |
| PIB | `ViewRss.aspx?lang=1&reg=1` | HTTP 200, `text/html`, **0 entries, bozo** | `RssMain.aspx?ModId=6&Lang=1&Regid=3` — HTTP 200, `text/xml`, **20 entries** |
| SEBI | `sebi.gov.in/rss.html` | HTTP 200, `text/html`, **0 entries, bozo** | Google News site-search (`site:sebi.gov.in`) |
| Ministry of External Affairs | `mea.gov.in/rss-feeds.htm` | HTTP 200, `text/html`, **0 entries, bozo** | Google News site-search (`site:mea.gov.in`) |
| Reuters | `reutersagency.com/feed/?best-topics=tech…` | **HTTP 404** (and wrong topic) | Google News site-search (`site:reuters.com`) |

After the fix all nine *direct* feeds probe clean:

```
200 entries= 10 bozo=0  ICAR
200 entries=173 bozo=0  WHO News
200 entries= 60 bozo=0  The Hindu National
200 entries=200 bozo=0  Indian Express
200 entries= 20 bozo=0  PIB — Press Information Bureau
200 entries= 10 bozo=0  NITI Aayog
200 entries=100 bozo=0  Business Standard
200 entries= 35 bozo=0  Mint
200 entries= 76 bozo=0  Economic Times
```

**Deliberate consequence.** Routing SEBI / MEA / Reuters through Google News
changes their `official` flag to `False` (the `official` flag requires the feed
host to match the publisher host). This is the *conservative* direction: results
found via Google News are treated as discovery and still require corroboration,
which the policy demands. This is documented, not accidental.

* **New tool.** `scripts/source_health.py` (offline registry check by default,
  `--live` probe, `--json` report, read-only — no Telegram, no writes).
* **New test.** `tests/test_source_registry.py::test_canonical_registry_loads_and_has_no_duplicate_rss_urls`.

### 7.3 PDF — missing-glyph (tofu) defects (fixed)

The bundled fonts (Poppins, Mukta) **do not contain** several decorative symbols
used by the generator. Rendering them produced visible tofu boxes.

```
Poppins-Regular/Bold/SemiBold + Mukta-Regular MISSING:
  0x25b6 (▶) 0x2714 (✔) 0x258c (▌) 0x2192 (→) 0x2713 (✓) 0x25cf (●) 0x25a0 (■) 0x2605 (★) 0x2794 (➔)
```

* **Fix (defence in depth).**
  1. Literal symbols in `src/generate_pdf.py` replaced with font-supported
     equivalents (`▶ → »`, `✔ → ·`, `→ → »`, emoji → `·`/`»`).
  2. The category side-bar `▌` glyph was replaced by a **filled table cell**
     (`BACKGROUND` = category colour) — font-independent, so the defect cannot
     recur.
  3. A new `sanitize_glyphs()` guard runs inside `_strip_html()` (the single
     chokepoint for every string that reaches a Paragraph or a Hindi image). Any
     codepoint the bundled fonts cannot draw is replaced with a supported
     equivalent or dropped — so **input data can never introduce tofu**.
  4. `agents/19_pdf_qa.py` gained `check_glyph_integrity()`: the QA gate now
     fails on U+FFFD / U+25A1 replacement characters and on the known-unsupported
     symbol set.
* **Tests.** `tests/test_pdf_sample_qa.py` (5 tests, all passing) asserts the QA
  gate passes on a real generated PDF, that no story/MCQ is missing, that no
  broken glyph survives, and that `sanitize_glyphs` maps/preserves as specified.

### 7.4 PDF — spec alignment (Part 8) and new capabilities

* Palette retargeted to the spec: navy `#123B5D`, teal `#087E8B`, gold `#E7B44A`
  (highlight) with `#B45309` for warning text, body `#222B36`, near-white page.
* Typography raised into the specified ranges (section 16, headline 15,
  EN/HI body 12, metadata 9–10, MCQ 10.5–11.5). See `docs/pdf-design.md`.
* Per-story **clickable source links** added (`<link href=…>` + printed URL).
* PDF **metadata** extended with `subject`, `creator`, `keywords`.
* Full detail, rendered-page evidence and remaining cosmetic caveats are in
  `docs/pdf-design.md`.

### 7.5 Redundant modules — removed with proof

| Module | Duplicate of | Reference proof | Action |
| --- | --- | --- | --- |
| `pipeline/mcq_validator.py` | `pipeline/content.validate_mcqs` (used by agents 16 + 17) | repo-wide search for `mcq_validator`: only its own docstring, a log *label* in agents/16–17, and the audit docs. No importer / CI / tool / existence list. | **removed** |
| `pipeline/model_manager_v2.py` | `pipeline/ai_router` (`route`/`is_configured`, used by agents 00/04/12/20/21, `content.py`, `claim_verifier.py`) | repo-wide search for `model_manager`: only its own file. | **removed** |
| `pipeline/verify.py` | partially `pipeline/gnews.decode_article_url` | referenced by `.env.example` as a documented standalone operator tool | **kept**, documented |
| `pipeline/claim_verifier.py` | — | imported by `tests/test_claim_verifier.py`; repaired this branch | **kept** (optional adapter) |
| `pipeline/telegram_api.py` | — | imported by `tests/test_telegram_api.py`; carries ledger/idempotency logic | **kept** (optional adapter) |
| `agents/03_news_collection.py` | `pipeline/01_source_fetch.py` | referenced by `ci.yml`, `scripts/preflight_check.sh`, `scripts/diagnose.py`, `README`, `tests/test_unicode_safety.py` | **kept** (deprecated shim, tested) |

Locked by `tests/test_module_consolidation.py`.

### 7.6 Test-coverage gap — PDF E2E silently skipped (fixed)

`tests/test_pipeline_offline.py::test_pdf_end_to_end_and_qa_checks` skipped
whenever `sys.platform == "win32" and not features.check("raqm")`, even though the
production shaping path (`uharfbuzz` + `freetype`, `_render_hindi_hb_ft`) was
available. The guard now probes the **real** backend, so the test executes on
this host. Result: the offline suite went from `6 passed, 1 skipped` to
`7 passed` for the PDF-offline test files — real coverage, not a threshold change.

---

## 8. Second-pass files changed

```
config/feeds.py            (The Hindu duplicate URL removed, invariant comment)
config/sources.py          (PIB/SEBI/MEA/Reuters feed URLs corrected, evidence notes)
agents/19_pdf_qa.py        (check_glyph_integrity wired into the QA gate)
scripts/diagnose.py        (canonical-registry + duplicate-URL check added)
src/generate_pdf.py        (Part 8 palette/typography, glyph guard, clickable
                            source links, PDF metadata, UI-symbol fixes)
tests/test_pipeline_offline.py      (real shaping-backend skip guard)
tests/test_source_registry.py       (+3 canonical-registry invariant tests)
tests/test_pdf_sample_qa.py         (new — real generate + real QA gate)
tests/test_module_consolidation.py  (new — locks the consolidation)
tests/fixtures/__init__.py          (new)
tests/fixtures/bilingual_sample.py  (new — deterministic bilingual fixture)
scripts/source_health.py   (new — offline/live source diagnostic)
scripts/pdf_preview.py     (new — generate + QA + render pages to PNG)
docs/source-registry.md    (new)
docs/pdf-design.md         (new)
docs/production-audit.md   (renamed from PRODUCTION_AUDIT.md, updated)
docs/production-readiness.md (renamed from PRODUCTION_READINESS.md)
pipeline/mcq_validator.py       (deleted — proven duplicate)
pipeline/model_manager_v2.py    (deleted — proven duplicate)
```
