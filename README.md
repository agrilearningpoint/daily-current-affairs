# AGRI LEARNING POINT — DAILY CURRENT AFFAIRS AUTOMATION
**Bilingual • Mobile-First • Exam-Oriented • 24-Agent Pipeline**

> **Master Rule:** Student Value First. Accuracy Before Speed. Quality Before Quantity. Never invent facts. Never fill PDF just to meet target count. Never publish unverified or failed content.

---

## 🚀 FINAL AGENT SETUP — 17 LOGICAL STAGES (audit refactor 2026-10)

> **Refactor summary:** 24 agents → 17 stages. Removed: `01 Master Supervisor` (main.py already
> orchestrates lock/retry/resume/alert). Merged: `02 Scheduler` → `03 News Collection`;
> `08 Agriculture Expert` + `09 Banking Expert` → `07 Student & Domain Relevance` (they were pure
> tagging wrappers); `13 Bilingual Editor` + `14 English Editor` → `12 Content Editor` (inline passes).
> Renamed: `24 Watchdog Recovery` → `24 Final Health Audit` (standalone watchdog = `main.py --watchdog`).
> Original IDs kept with intentional gaps as history markers.

### 1. 🎯 MASTER ORCHESTRATION (`main.py`)
> Manage the complete Current Affairs pipeline. Execute each stage in correct order, track job status, prevent duplicate, retry failed, resume from last success, never publish incomplete. *(formerly Agent 01 — now lives entirely in main.py)*

`COLLECT(+window) → VERIFY → RANK → SELECT → WRITE → MCQ → PDF → QA → TELEGRAM → PIN → AUDIT → COMPLETE`

### 2. 🌐 NEWS COLLECTION (+ scheduler window)
> Collect from reliable/primary sources; compute the Asia/Kolkata collection window for this job type inline. Prioritize Agriculture, Banking, Govt, Economy, National, International, Science, Environment, Awards... Capture headline, time, source, URL, category, raw facts. Collect broadly; do not decide importance. Quality gate: <4 in-window items = failure.

### 3. 🔎 FACT VERIFICATION
> Verify every item via primary/authoritative sources (incl. Google News AES-URL decoding via `pipeline/gnews.py`). Verify dates, numbers, names, orgs, schemes, rankings, appointments, locations. Reject unsupported. Never guess. Quality gate: <4 verified items = failure.

### 4. 🧹 DEDUPLICATION
> Identify and merge same event across sources. Preserve strongest source. Separate only when genuinely different.

### 5. 🧠 NEWS IMPORTANCE (0-100)
> Score 0-100 for overall importance: national significance, govt importance, economic impact, agri/banking relevance, exam potential, future relevance, static value, uniqueness, source reliability. Not just trending.

### 6. 🎓 STUDENT & DOMAIN RELEVANCE ⭐ (merged old 07+08+09)
> Act as expert editor for AGTA/AFO/NABARD/FCI/ICAR/IBPS. Judge worth of limited study time; boost Agriculture/Banking/Schemes, demote crime/politics/ad noise; tag `agri_focus` / `banking_focus` for coverage guarantees. Q: "If student has limited time, should they read this?"

### 7. ⭐ FINAL NEWS SELECTION
> Select only highest-value by merit: daily 10-12 / weekly 15-18 / monthly 20-25 MAX caps, quality floors 25/60/62 on the relevance scale. Never pad with weak news. Ensure ≥2 agri & ≥2 banking visible when available.

### 8. 📈 IMPORTANCE MEMORY
> Track importance over time across ALL scored events (not just selected). Detect RISING/FALLING/NEW trends, remember previously-published ids so Weekly/Monthly reuse the same persistent DB.

### 9. ✍️ CONTENT EDITOR (EN + HI in one stage; merged old 13+14)
> Convert selected verified news to concise exam-oriented bilingual content: Headline → Key Points → Static Facts → Exam Fact. Hindi=Mukta, English=Poppins; word-substitution translation (never invent meaning). Inline English cleanup + verbatim source-link validation.

### 10. 🖼️ IMAGE AGENT
> Only when improves understanding. Prefer official/reliable (source OG image → Wikimedia fallback). Verify represents event/person/place. Never random stock.

### 11. ❓ MCQ GENERATOR
> High-quality MCQs only from verified selected. Prioritize direct, conceptual, statement-based, static-linked for AGTA/AFO/NABARD/FCI/ICAR.

### 12. 🧪 MCQ VALIDATOR
> Validate clarity, option uniqueness, correct answer, explanation, accuracy, source support, ambiguity, duplicate, relevance. Reject/regenerate if multiple answers.

### 13. 🎨 PDF DESIGN (Agent 18)
> Clean, colorful, highly readable, mobile-friendly. Controlled colors, clear hierarchy, attractive headings, proper spacing. Every page branding/logo/footer/page number + clickable Telegram channel links (@agrilearningpoint, @agriquizworld). Hindi rendered via Mukta with RAQM shaping + hidden selectable text layer. Never overcrowd or alter facts.

### 14. 🔍 PDF QA (Agent 19) — HARD GATE
> Check missing text, broken Hindi (Mukta), font rendering, **Hindi coverage ratio (extracted vs source Devanagari chars — not just "any char exists")**, dates, duplicates, images, overflow, blank pages, headers/footers, page numbers, MCQ mismatch, bilingual inconsistency. Reject if critical error; REJECTED blocks publish.

### 15. 📅 WEEKLY EDITOR ⭐ (Agent 20)
> Review week, fresh Best-of-Week. Re-rank via cumulative importance, exam/agri/banking relevance, uniqueness, developments. Deduplicate. Not combine daily PDFs.

### 16. 📆 MONTHLY EDITOR ⭐ (Agent 21)
> Review month, fresh Best-of-Month. Re-rank via month-long significance, policy impact, repeated developments, static value, future potential. Not merge.

### 17. 📤 TELEGRAM PUBLISHER + 📌 PIN VERIFIER + 🩺 FINAL HEALTH AUDIT (Agents 22/23/24)
> Publish only QA-approved PDF to Telegram group `-1004485392227`; verify pin (retry until succeed); final health audit checks every artefact (raw→qa report), PDF size, QA approval and state machine before marking COMPLETE. Standalone watchdog (`main.py --watchdog`, every 5 min via workflow) detects stalled/FAILED_FINAL jobs, alerts admin, and re-triggers the FAILED job's own date (recovery_plan.json) — never silently stops.

**Common Master Rule:** Student Value First...

**Flow:**
```
COLLECT(+window) → VERIFY → DEDUP → IMPORTANCE → STUDENT+DOMAIN RELEVANCE → FINAL SELECTOR
   → MEMORY → CONTENT(EN+HI) → IMAGE → MCQ GEN → MCQ VALIDATOR → PDF DESIGN → PDF QA(GATE)
   → PUBLISH → PIN VERIFY → FINAL HEALTH AUDIT → COMPLETE
WATCHDOG (main.py --watchdog): MONITOR → RETRY → RESUME(failed job's own date) → ALERT
```

**Architecture:** Same database, different selection: Daily="Aaj kya zaroor?", Weekly="Is saptah sabse mahatvapurna?", Monthly="Is mahine sabse mahatvapurna?" — Fresh AI editorial, not PDF merging. Like Horizon/SmartReader.

---

## 🌟 SOURCE TIERS

**Tier-1 PRIMARY (100):** PIB (nodal + backgrounders/factsheets), India.gov.in, MyGov, PM India, Cabinet, Agri Ministry, ICAR (full ecosystem), IARI, DARE, APEDA, NHB, FSSAI, DAHD, Fisheries, ICFRE, IMD, CACP, RBI, NABARD, SEBI, FinMin, DEA, Financial Services, NPCI, PFRDA, IRDAI, IFSCA, MoSPI, Economic Survey, Budget, NITI Aayog, UN/UN News/FAO/World Bank/IMF/WTO/WHO/UNESCO/UNEP/UNDP/ILO/UNFCCC/IEA, Ministries (Rural/Cooperation/Food Processing/Consumer Affairs/DST/ISRO/DBT/DRDO/MoEFCC/CPCB/Education/UGC/NTA/Defence/MEA), Rashtrapati/PMO/ECI/UPSC

**Tier-2 DISCOVERY (80-90):** Reuters, The Hindu, Indian Express, Business Standard, Mint, Economic Times

**Tier-3 AGGREGATORS (60):** Google News, GDELT, NewsAPI

**Score:** Official 100 | International 100 | Regulator 95 | Reuters 90 | Major Newspaper 80 | Aggregator 60

**Top 10 Core:** PIB, Agri Ministry, ICAR, IARI, RBI, NABARD, SEBI, MoSPI, NITI Aayog, MEA

---

## 🎨 PDF DESIGN SPEC

**Fonts:** Hindi → Mukta (Regular/Bold/SemiBold), English → Poppins/Inter (Regular/Bold/SemiBold), **Max 2 families**

**Hierarchy:**
- Main title 18-20pt Bold, Hindi headline 17-19pt Bold (Mukta), Section 15-17pt (16pt), Sub-heading 13-14pt Semi, Body 11.5-12.5pt (Poppins 12pt / Mukta 12.5pt), Static 11.5-12pt, Exam Fact 12-13pt Bold, MCQ Q 12-13pt (12.5pt), Options 11.5-12pt, Explanation 11-12pt, Footer 8.5-9.5pt (9pt), Watermark 8-10pt very subtle (0.09 alpha, PAID BATCHES logo 90mm centered)

**Line spacing 1.25-1.35, Single-column mobile-first, Margins 12-15mm (actual 13mm), Max useful info + readability, No orphan heading, Smart page fill, Tables compact mobile-readable, Colors controlled (Agri Green, Banking Blue, National Orange, etc.), Header compact, Footer compact, Watermark every page, Double border Red+Green, No blank/or orphan/tiny text.**

**Previous best colors kept as final.**

---

## ⚙️ DEPLOYMENT

- **GitHub:** `agrilearningpoint/daily-current-affairs`
- **Workflows:** `daily.yml` (00:30 UTC = 06:00 IST daily), `weekly.yml` (Sunday), `monthly.yml` (last date)
- **Secrets:** `TELEGRAM_BOT_TOKEN`, `ADMIN_ID=1138783169`, `CLOUDFLARE_TOKEN`
- **Telegram:** Private group `-1004485392227` (CURRENT AFFAIRS WORLD) — Daily + Weekly (Sun) + Monthly (last date) + auto-pin, storage delete after monthly (GitHub/R2 only, group keeps all)
- **Fonts:** `src/fonts/Mukta-*.ttf` + `Poppins-*.ttf`
- **Watermark:** `assets/watermark_logo.png` (PAID BATCHES logo)

## 📱 MOBILE PDF
21 pages, 3.7MB, 18pt headline / 12.5pt Hindi / 13mm margin, 20 one-liners spaced, single-column, premium book-like, not AI.

---

## 🔧 Run Locally
```bash
pip install -r requirements.txt
python main.py --type daily --date 2026-10-04
python main.py --type weekly --date 2026-10-05
python main.py --type monthly --date 2026-10-31
```


---

## ✅ v2 PRODUCTION UPDATE (04 Oct 2026) — Code Audit Fixes

All P0/P1 issues from the code review are now FIXED in this branch:

| # | Issue | Fix |
|---|-------|-----|
| 1 | **Hardcoded Telegram Bot Token** | ❌ Removed everywhere. Token is read ONLY from `TELEGRAM_BOT_TOKEN` env (GitHub Secrets); missing token = hard error. ⚠️ **You must still revoke the old token via @BotFather → Revoke** and add the new one to Secrets (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL_ID`, `ADMIN_ID`). Old tokens may persist in Git history even after deletion. |
| 2 | **24 dummy agents (time.sleep pass-through)** | All 24 agents now have REAL implementations backed by the new `pipeline/` library. Empty/failing stage output raises an error — an empty pipeline can no longer report success. |
| 3 | **No real news collection** | `pipeline/collector.py`: RSS-first + HTML-fallback adapters for all Tier-1 sources (PIB/ICAR/RBI/NABARD/SEBI/FAO/WB/IMF…), Tier-2 discovery, IST time-window per job type, quality gate (<5 items = failure). |
| 4 | **No verification/dedup/scoring** | Agent 04 verifies source URLs live + confidence records; Agent 05 merges events at similarity ≥0.85 keeping authoritative source; Agent 06 implements the exact README factor weights (20/15/15/15/10/10/5/5/5 × source reliability). |
| 5 | **MCQ generator/validator were dummies** | `pipeline/content.py`: deterministic fact-grounded MCQs (answer verbatim from that news's own text, distractors from other news, never auto "None of these") + full validator chain (option uniqueness, exactly-one-correct, answer supported by source, explanation check, duplicate-question check). Invalid MCQs are rejected before PDF. |
| 6 | **PDF QA was pass-through** | Agent 19 is now a **HARD GATE**: PyMuPDF checks — pages>0, Mukta/Poppins embedded, Devanagari extractable, date present, headlines present, MCQ count matches JSON, answers valid, no blank pages. Any failure ⇒ `QA_REJECTED`; Agent 22 refuses to publish unless state == `QA_APPROVED`. |
| 7 | **generate_pdf.py was a hardcoded 04-Oct sample** | Now a fully **dynamic data-driven generator**: `generate_pdf(content_json, mcq_json)` reads `data/content/<job>.json` + `data/mcq/<job>_validated.json`. Refuses empty editions. Same premium design system (Mukta+Poppins, 13mm margins, banners, Static Facts, Exam Fact boxes). |
| 8 | **Font path bug (`BASE_DIR/fonts`)** | Fixed to `src/fonts/` — and font registration failure now RAISES instead of silently falling back to Helvetica. |
| 9 | **External image paths (/home/user/…)** | Agent 15 downloads og-image/Wikimedia images into workspace `assets/images/<job_id>/` with Pillow validation (≥500px, JPEG/PNG). No external absolute paths. |
| 10 | **Weekly workflow ran a duplicate daily** | `weekly.yml` now runs ONLY the weekly job (daily.yml already publishes Sunday's daily). Monthly likewise. All workflows have `concurrency:` groups. |
| 11 | **No job locking / race conditions** | `pipeline/state.py`: atomic `JobLock` (O_CREAT|O_EXCL lockfile + stale-lock recovery) + COMPLETE-status skip. Two processes can never run the same job. |
| 12 | **No retry backoff** | `main.py` retries each agent 3× with real exponential backoff **2s → 4s → 8s**, then FAILED_FINAL + admin alert. |
| 13 | **Watchdog didn't exist** | New `.github/workflows/watchdog.yml` runs `python main.py --watchdog` **every 5 minutes**: detects stalled/FAILED_FINAL jobs, alerts admin DM, triggers resume-from-last-stage recovery. Agent 24 does the end-of-run artefact audit. |
| 14 | **Full state machine** | CREATED→COLLECTING→COLLECTED→VERIFYING→VERIFIED→DEDUPLICATED→SCORED→SELECTED→CONTENT_READY→MCQ_READY→MCQ_VALIDATED→PDF_GENERATED→QA_APPROVED→PUBLISHED→PIN_VERIFIED→COMPLETE (+ FAILED/RETRYING/RECOVERED/FAILED_FINAL/QA_REJECTED), persisted atomically in `data/jobs/<job>.json`, supports resume. |
| 15 | **Telegram publish/pin were dummies** | Agents 22–23 use the real Bot API: sendDocument → store message_id → pinChatMessage → getChat read-back verification (pinned id must match). Pin mismatch ⇒ job NOT complete. Duplicate-publish guard included. |
| 16 | **Weekly/Monthly ran after PDF** | Workflow order corrected: editors 20/21 now run BEFORE content→PDF, so Best-of-Week/Month re-selection actually flows into the edition (same-database principle via importance memory). |
| 17 | **Importance memory missing** | `data/memory/importance_memory.json`: event_id → score history → RISING/FALLING/NEW trend, reused by weekly/monthly selection. |
| 18 | **DATE not persisted between workflow steps** | Workflows export `DATE` via `$GITHUB_ENV`. Push-failures surface as failures (no `|| echo` masking). |

### 🆕 Repo layout additions
```
pipeline/            # shared real implementation library
  state.py           #   state machine + atomic JSON + JobLock
  collector.py       #   RSS/HTML source adapters, windows, categories
  scoring.py         #   dedup (0.85 Jaccard/bigram) + 0-100 factor scoring
  content.py         #   key points/static facts/exam fact + bilingual + MCQ gen/validate
  telegram_api.py    #   sendDocument / pinChatMessage / verify_pin / alerts
agents/*.py          # ALL 24 rewritten — real logic, quality gates, no pass-through
tests/test_pipeline_offline.py   # offline E2E test suite (all passing)
.github/workflows/watchdog.yml   # every-5-min monitor + recovery
```

### 🔐 Required GitHub Secrets (set before first run)
`TELEGRAM_BOT_TOKEN` (new revoked-and-regenerated token), `TELEGRAM_CHANNEL_ID`, optionally `ADMIN_ID` for watchdog alerts. No fallback values exist in code — missing secrets fail loudly, which is correct behaviour.

### Run locally
```bash
pip install -r requirements.txt
python tests/test_pipeline_offline.py        # offline verification
python main.py --type daily --date 2026-10-05
python main.py --watchdog
```
