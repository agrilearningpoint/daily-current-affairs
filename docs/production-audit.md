# Production Architecture & Pipeline Audit — daily-current-affairs

**Audit Date:** 2026-11-17  
**Auditor:** Principal Python Architect / SRE / QA Lead  
**Baseline Artifact:** `daily_2026-11-17.pdf` (34 pages, SHA-256: `ed544c065b7ae8797b4243aea03a81b98b8f404b2b547a9ae68a4d38f2890f12`)  
**Target Audience:** UPSSSC AGTA, IBPS AFO, ICAR T-3/T-4, ICAR JRF, NABARD, FCI, and State Agriculture Examinations  
**Brand:** Agri Learning Point • BY SATYAM SIR & TEAM  

---

## 1. Pipeline Dependency Mapping & Stage Contracts

The production pipeline executes 18 registered stages sequentially, coordinated by `main.py` through `DAILY_STAGES`:

```
00_model_orchestrator
       │
01_source_fetch ─────────────► data/raw/daily_YYYY-MM-DD.json
       │
04_fact_verification ───────► data/verified/daily_YYYY-MM-DD.json
       │
05_deduplication ────────────► data/dedup/daily_YYYY-MM-DD.json
       │
06_news_importance ──────────► data/scored/daily_YYYY-MM-DD.json
       │
07_student_domain_relevance ─► [Annotates domain exam relevance]
       │
10_final_news_selection ─────► data/selected/daily_YYYY-MM-DD.json (15 items)
       │
11_importance_memory ────────► state/importance_memory.json
       │
12_content_editor ───────────► data/content/daily_YYYY-MM-DD.json
       │
16_mcq_generator ────────────► data/mcq/daily_YYYY-MM-DD.json
       │
17_mcq_validator ────────────► [Validates 5 options, answer key, Devanagari]
       │
17b_auto_sections ───────────► [Quick Bites & Agriculture Corner in content]
       │
17c_static_gk_validator ─────► [Validates officeholders & static facts]
       │
18_pdf_design ───────────────► output/daily_YYYY-MM-DD.pdf
       │
19_pdf_qa ───────────────────► logs/qa/daily_YYYY-MM-DD_qa.json
       │
22_telegram_publisher ───────► [Sends PDF to Telegram supergroup]
       │
23_telegram_pin_verifier ────► state/pin_verification.json
       │
24_final_health_audit ───────► logs/qa/daily_YYYY-MM-DD_health.json
```

### Detailed Stage Contracts

| Stage | Module | Critical? | Inputs | Outputs | Failure Mode & Recovery |
|---|---|---|---|---|---|
| **00** | `agents/00_model_orchestrator.py` | Yes | Environment / Providers | Router status | Fails fast if no valid LLM provider or fallback exists |
| **01** | `pipeline/01_source_fetch.py` | Yes | RSS/GNews feeds, PIB | `data/raw/*.json` | Network retries, tier-1/tier-2 official source registry |
| **04** | `agents/04_fact_verification.py` | Yes | `data/raw/*.json` | `data/verified/*.json` | Verifies claims, drops unverified headlines |
| **05** | `agents/05_deduplication.py` | Yes | `data/verified/*.json` | `data/dedup/*.json` | Semantic & lexical fingerprint deduplication |
| **06** | `agents/06_news_importance.py` | Yes | `data/dedup/*.json` | `data/scored/*.json` | Scores 0-100 based on exam & policy significance |
| **07** | `agents/07_student_domain_relevance.py` | Yes | `data/scored/*.json` | Annotated scored items | Boosts agriculture, rural development, finance, schemes |
| **10** | `agents/10_final_news_selection.py` | Yes | `data/scored/*.json` | `data/selected/*.json` | Selects exactly 15 top stories (min 4 agriculture) |
| **11** | `agents/11_importance_memory.py` | Yes | `data/selected/*.json` | `state/importance_memory.json` | Cross-edition deduplication & event history |
| **12** | `agents/12_content_editor.py` | Yes | `data/selected/*.json` | `data/content/*.json` | Bilingual editorial generation (EN+HI), exam takeaways |
| **16** | `agents/16_mcq_generator.py` | Yes | `data/content/*.json` | `data/mcq/*.json` | LLM schema generation with deterministic template fallback |
| **17** | `agents/17_mcq_validator.py` | Yes | `data/mcq/*.json` | Validated MCQs | Fail-closed gate: 5 options, source text grounding |
| **17b** | `agents/17b_auto_sections.py` | No (Daily) | `data/content/*.json` | Enriched content | Quick Bites & Agriculture Corner generation (fail-soft) |
| **17c** | `agents/17c_static_gk_validator.py` | No | `data/content/*.json`, `data/mcq/*.json` | Atomically updated JSON | Strict officeholder check against `config/current_facts.json` |
| **18** | `agents/18_pdf_design.py` | Yes | Content & MCQ JSON | `output/*.pdf` | ReportLab + HarfBuzz Devanagari 2-pass compilation |
| **19** | `agents/19_pdf_qa.py` | Yes | Generated PDF | QA JSON report | 8-layer release gate: structural, density, character thresholds |
| **22** | `agents/22_telegram_publisher.py` | Yes | Generated PDF | Sent Telegram msg | Uploads document to group, records message ID |
| **23** | `agents/23_telegram_pin_verifier.py` | Yes | Telegram msg ID | Pinned confirmation | Pins message in supergroup, logs status |
| **24** | `agents/24_final_health_audit.py` | Yes | All stage logs | Audit summary | Validates entire run integrity before job completion |

---

## 2. Root Cause Analysis of 17 November 2026 Baseline Defects

Inspection of `output/daily_2026-11-17.pdf` (34 pages) revealed the following concrete root causes:

### 1. Factual Acronym Collision (Q13 / Page 21-22) — P0 Critical
- **Defect:** Story 13 reports CCPA penalising ExportersIndia.com for listing hazardous chemicals (ammonium nitrate, PETN, picric acid). The MCQ explanation and Static GK expand CCPA as "Chief Controller of Explosives", assign its parent ministry as "Ministry of Home Affairs", and governing Act as "Explosives Act, 1884".
- **Root Cause:** CCPA in government releases is the **Central Consumer Protection Authority** (established under the Consumer Protection Act, 2019, under the Ministry of Consumer Affairs, Food & Public Distribution). The LLM associated "explosives" in the headline with "explosives controller", hallucinating the wrong expansion. Neither `agents/17_mcq_validator.py` nor `agents/17c_static_gk_validator.py` had an entity acronym verification layer to trap acronym collisions.
- **Remediation:** Implement an authoritative entity/acronym registry in `pipeline/static_gk_db.py` and strict acronym collision validation in `agents/static_gk_validator.py` and `agents/19_pdf_qa.py`.

### 2. Broken Question Syntax & Dangling Prepositions (Q1 / Page 4) — P1 Major
- **Defect:** `Q1. Which State / Union Territory is associated with the following development: "IEPFA and SEBI to Organize ‘Niveshak Shivir’ in to Empower Investors and Simplify Grievance Redressal and…"?`
- **Root Cause:** Deterministic headline substitution in `pipeline/mcq_builder.py` truncated `"in New Delhi to Empower"` into `"in to Empower"`, producing a grammatically broken, dangling preposition question.
- **Remediation:** Enhance question grammar and semantic cleaning in `pipeline/mcq_builder.py` and `pipeline/content.py` to prevent broken token splits and validate natural phrasing.

### 3. Numerical Conflation in Crop Insurance Question (Q3 / Page 6-7) — P1 Major
- **Defect:** Q3 asks: `What is the key figure / financial outlay associated with: "El Nino impact drives record surge in crop insurance registrations across"?` Options: 180%, 135%, 21 per cent, 45%. But the story text describes 37.5 lakh farmers in Kharif 2026 vs 20.91 lakh in Kharif 2025.
- **Root Cause:** A generic numerical regex picked percentages from unrelated sentences, testing numbers that conflicted with the actual core metric of the article (farmer registrations).
- **Remediation:** Anchor numerical MCQs to the specific metric tested (registrations vs outlays vs growth rates) and prohibit cross-context number insertion.

### 4. Trivial News Agency Recognition Questions (Q6 & Q9 / Pages 11 & 16) — P1 Major
- **Defect:** Q6: `Which news agency reported the launch of the Agri Welfare Portal?` (Answer: DD News). Q9: `Which news agency reported the Cabinet's approval of the Semicon 2.0 scheme?` (Answer: DD News).
- **Root Cause:** The LLM was instructed to test only facts in NEWS; seeing `"Source: DD News"`, it repeatedly fell back to trivial agency-identification questions.
- **Remediation:** Add an explicit prohibition against agency-identification stems (`\bWhich news agency reported\b`, `\bWhich media outlet reported\b`) across prompts and validators. MCQs must test scheme outlays, implementing ministries, objectives, and policy significance.

### 5. News vs Historical GK Disconnect (Q11 / Page 18-19) — P1 Major
- **Defect:** Story 11 is about "Sustainable Natural Resource Management Training", but the MCQ asks `When was the Indian Council of Agricultural Research (ICAR) established?`
- **Root Cause:** When an article lacks clear quantitative data, the generator replaced the entire question with a generic institutional establishment date, completely ignoring the news event.
- **Remediation:** Ensure the MCQ tests the substantive news event (training mandate, target domain, sustainable agriculture) while delegating historical founding dates to the Static GK box.

### 6. Generic Country Boilerplate Static GK (Page 26) — P2 Quality Defect
- **Defect:** Page 26 Static GK: `Country – India`, `Capital – New Delhi`, `Official language – Hindi`, `Year of independence – 1947`.
- **Root Cause:** LLM hallucinated generic national facts when unable to find entity-specific institutional facts, and `_extract_static_gk_pairs` only filtered category blurbs, not national boilerplate.
- **Remediation:** Add strict filter patterns for generic national facts (`Country – India`, `Capital – New Delhi`, `Year of Independence`) across `pipeline/mcq_schema.py`, `pipeline/static_gk_db.py`, and `src/generate_pdf.py`.

### 7. Verbatim Headline Copying in Explanations & One-Liners (Pages 4-26, 33-34) — P2 Quality Defect
- **Defect:** Explanations repeated article timestamps (`Updated - November 17, 2026 12:59 am IST - Bengaluru...`) and copied verbatim headlines into One-Liners.
- **Root Cause:** Missing timestamp scrubbing in `pipeline/content.py` and lack of rapid-revision synthesis in `agents/17b_auto_sections.py`.
- **Remediation:** Implement regex filters for datelines and timestamps, and enforce distinct learning takeaways in One-Liners.

### 8. Whitespace Imbalance in News in Pictures (Page 3) — P2 Visual Defect
- **Defect:** 5 cards in a 3-column grid produced 3 cards on Row 1 and 2 cards on Row 2 with a large blank gap on the bottom right.
- **Root Cause:** Column count calculation `ncol = 2 if n <= 4 else 3` selected 3 columns for 5 cards instead of a balanced grid or selecting the top 4 verified photos.
- **Remediation:** Update layout algorithm in `src/generate_pdf.py` so that 5 cards are balanced or structured without orphan slots.

---

## 3. Corrective Architecture Blueprint

1. **Entity & Acronym Validation Layer:**
   - Central registry in `pipeline/static_gk_db.py` mapping acronyms to authoritative full names, parent ministries, governing Acts, and headquarters.
   - Validation stage in `agents/static_gk_validator.py` and release gate in `agents/19_pdf_qa.py`.
2. **Advanced MCQ Engine:**
   - 18 exam question types supported in `pipeline/mcq_schema.py` and `pipeline/mcq_builder.py`.
   - Strict semantic validation forbidding agency questions, dangling prepositions, and headline verbatim stems.
3. **Smart Contextual Static GK:**
   - Automatic lookup of verified entity facts from `pipeline/static_gk_db.py`.
   - Complete ban on generic country boilerplate (India/New Delhi/1947).
4. **Distinct Rapid-Revision Sections:**
   - Quick Bites = secondary news briefs.
   - One-Liners = distilled high-yield facts (Dates, Outlays, Acts, Ministries).
   - Agriculture Corner = exam-oriented concepts (Agronomy, Schemes, ICAR institutes).
5. **PDF Visual Balance & Multi-Layer QA:**
   - Responsive, gap-free gallery layouts.
   - 8-layer QA gate failing release on critical factual contradictions or broken answer keys.
