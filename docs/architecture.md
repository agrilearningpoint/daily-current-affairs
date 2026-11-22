# AGRI LEARNING POINT — COMPLETE SYSTEM ARCHITECTURE SPECIFICATION
**Version:** 3.0 Production  
**Environment:** Cloud / GitHub Actions / Local Antigravity  
**Target Examinations:** UPSSSC AGTA, IBPS AFO, ICAR T-3/T-4, ICAR JRF, NABARD Grade A/B, FCI, State PCS Agriculture

---

## 1. Architectural Principles
1. **Student Value First:** Content must directly benefit agricultural and competitive examination candidates.
2. **Fail-Closed QA Gates:** Incomplete sentences, wrong answer keys, unverified claims, or truncated PDFs must never be published.
3. **Deterministic Verification Before LLM:** Algorithmic verification, deduplication, and schema validation supersede LLM confidence.
4. **Resilient Autonomous Self-Healing:** Checkpoints and bounded retries route errors back to the appropriate stage (e.g. reserve backfill at Stage 12 instead of looping on Stage 18).
5. **No Hallucination / Zero Fabrication:** No phantom officeholders, fake numbers, or unverified schemes.

---

## 2. Stage-by-Stage Architecture Specification

### Stage 00: Model Orchestrator (`agents/00_model_orchestrator.py`)
- **Input:** Environment variables (`GEMINI_API_KEY`, `GROQ_API_KEY`, `OPENAI_API_KEY`, etc.).
- **Output:** Live provider health status, prioritized model routing table.
- **LLM Calls:** 1-token health ping.
- **Timeout:** 10s per provider.
- **Failure Policy:** Failover from Gemini -> Groq -> OpenRouter -> Offline deterministic fallback.

### Stage 01: Source Fetch (`pipeline/01_source_fetch.py`)
- **Input:** RSS feeds, PIB releases, Google News feeds, Official Ministry APIs (`config/sources.py`).
- **Output:** `data/raw/daily_YYYY-MM-DD.json` (Normalized article stream).
- **External Calls:** HTTP GET with ETag / 304 caching.
- **Timeout:** 15s per source, overall budget 180s.
- **Failure Policy:** Quarantine dead feeds; minimum 50 articles required to proceed.

### Stage 04: Fact Verification (`agents/04_fact_verification.py`)
- **Input:** `data/raw/daily_YYYY-MM-DD.json`.
- **Output:** `data/verified/daily_YYYY-MM-DD.json` (Claims tagged with verification status & confidence).
- **Verification Hierarchy:** Official gazettes / PIB -> Official institutional domains -> National news agencies -> Quarantine unverified claims.
- **Failure Policy:** Unverified claims downgraded; non-verifiable breaking rumors quarantined.

### Stage 05: Deduplication (`agents/05_deduplication.py`)
- **Input:** `data/verified/daily_YYYY-MM-DD.json`.
- **Output:** `data/dedup/daily_YYYY-MM-DD.json` (Unique event clusters).
- **Algorithms:** URL canonicalization, Jaccard title token similarity (threshold 0.65), entity-date-location event clustering.
- **Historical Comparison:** Cross-check against `state/published_events.json` (30-day window).

### Stage 06: News Importance Scoring (`agents/06_news_importance.py`)
- **Input:** `data/dedup/daily_YYYY-MM-DD.json`.
- **Output:** `data/scored/daily_YYYY-MM-DD.json` (Scored articles: 0–100 scale).
- **Scoring Dimensions:** Geographic scope (25%), Authority & Source tier (25%), Socio-economic outlay (25%), Policy significance (25%).

### Stage 07: Student Domain Relevance (`agents/07_student_domain_relevance.py`)
- **Input:** `data/scored/daily_YYYY-MM-DD.json`.
- **Output:** Domain-weighted scoring.
- **Domain Multipliers:** Agriculture & Rural Economy (1.5x), National Schemes & Polity (1.3x), Science & Health (1.2x), International & Multilateral (1.1x).

### Stage 10: Final News Selection (`agents/10_final_news_selection.py`)
- **Input:** Scored & weighted articles.
- **Output:** `data/selected/daily_YYYY-MM-DD.json` (15 primary stories + 10 reserve candidates).
- **Category Balancing:** Minimum 3–5 Agriculture stories, balanced National, Schemes, Science, and International.

### Stage 12: Content Editor (`agents/12_content_editor.py`)
- **Input:** `data/selected/daily_YYYY-MM-DD.json`.
- **Output:** `data/content/daily_YYYY-MM-DD.json` (Bilingual content: Headline, What Happened, Key Points, Explanation, Static Facts).
- **Bilingual Processing:** Mukta-compatible natural Hindi, proper noun transliteration protection, grammatical case alignment.
- **Sanitization:** Strict sentence completion check (no truncated feed summaries ending with `Rs.` or prepositions).

### Stage 16: MCQ Generator (`agents/16_mcq_generator.py`)
- **Input:** `data/content/daily_YYYY-MM-DD.json`.
- **Output:** `data/mcq/daily_YYYY-MM-DD.json` (15 validated bilingual MCQs).
- **MCQ Specification:** Exactly 5 options (A–E), verifiable answer, 4–5 bullet bilingual explanation, contextual Static GK.
- **Deduplication:** Intra-edition concept uniqueness check (no duplicate answers/stems in same edition).

### Stage 17: MCQ Validator (`agents/17_mcq_validator.py`)
- **Input:** `data/mcq/daily_YYYY-MM-DD.json` & `data/content/daily_YYYY-MM-DD.json`.
- **Output:** Verified MCQ stream or rejection with reserve backfill trigger.
- **Validation Gates:** 5 distinct options, no "None of the above", answer grounded in text, Hindi grammar check.

### Stage 17b: Auto Sections (`agents/17b_auto_sections.py`)
- **Input:** Pipeline content & secondary news pool.
- **Output:** Structured Agriculture Corner cards, Quick Bites (20–40 items), Rapid Revision One-Liners (15–25 items).

### Stage 17c: Static GK Validator (`agents/17c_static_gk_validator.py`)
- **Input:** Content & MCQ Static GK pairs.
- **Output:** Validated static GK against `config/current_facts.json` (verified officeholders, no stale data).

### Stage 18: PDF Design & Rendering (`agents/18_pdf_design.py` & `src/generate_pdf.py`)
- **Input:** Reconciled bilingual content & MCQs.
- **Output:** `output/daily_YYYY-MM-DD.pdf`.
- **Engine:** ReportLab Platypus + Pillow/HarfBuzz Devanagari text shaping + Mukta/Poppins fonts.
- **Mobile Readability:** Minimum 12pt body text, balanced two-column TOC, responsive image cards, orphan prevention.

### Stage 19: PDF QA Gate (`agents/19_pdf_qa.py`)
- **Input:** `output/daily_YYYY-MM-DD.pdf`.
- **Output:** `logs/qa/daily_YYYY-MM-DD_qa.json` (Pass/Fail release verdict).
- **9 Release Gates:** 100% sentence completeness, 0 blank pages, 15 MCQs present, quality score >= 90/100.

### Stage 22: Telegram Publisher (`agents/22_telegram_publisher.py`)
- **Input:** QA-passed PDF file.
- **Output:** Supergroup delivery message ID (`state/published_jobs.json`).
- **Safety:** Strict caption limit <= 1024 UTF-8 chars; fail-closed release gate.

### Stage 23: Telegram Pin Verifier (`agents/23_telegram_pin_verifier.py`)
- **Input:** Message ID from Stage 22.
- **Output:** Pin confirmation in `state/pin_verification.json`.

### Stage 24: Final Health Audit (`agents/24_final_health_audit.py`)
- **Input:** Full pipeline execution state.
- **Output:** Final health audit log, job status marked `success`.

### Stage 25: Autonomous Auto-Healer (`agents/25_auto_healer.py`)
- **Trigger:** Any stage failure in GitHub Actions or unattended runner.
- **Routing:** Story shortfalls route to Stage 12 (reserve backfill); layout issues route to Stage 18; network timeouts retry with exponential backoff.
