# Dry-run evidence — run 38896579675

- run URL: https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/38896579675
- edition: 2026-10-16 (DRY_RUN=1)

## Article counts

| stage | count |
|---|---|
| raw | 562 |
| verified | 562 |
| dedup | 446 |
| scored | 41 |
| selected | 28 |
| content | 28 |
| mcq | 14 |

## Category distribution per stage (raw keys here = normalisation missing)

- raw: ```{"agriculture": 2, "national": 60, "agriculture_core": 18, "banking_finance": 14, "economy_data": 8, "food_safety": 11, "environment": 2, "govt_national": 74, "science": 2, "defence_science": 54, "discovery": 187, "aggregator": 130}```

## Selected items

- [33/58] Agriculture: POLICY COORDINATION - Department of Agriculture & Farmers Welfare
- [22/47] Banking & Finance: Press Releases - Reserve Bank of India
- [15/30] Economy: Competition Commission of India, Government of India - Competition Commission of India
- [30/38] National: Don't bulldoze delimitation Bill again, call all-party meet: Kharge to Modi
- [26/51] Agriculture: About Economics and Statistics (Establishment) - Department of Agriculture & Farmers Welfa
- [22/47] Banking & Finance: Press Releases| Official Website of Reserve Bank of India - Reserve Bank of India
- [28/36] National: South Indian Bank aims 16% loan growth in FY27 amid West Asia war risks
- [26/51] Agriculture: Hyperlink Policy - Department of Agriculture & Farmers Welfare
- [22/47] Banking & Finance: - Reserve Bank of India
- [28/36] National: India GDP to grow 7.1-7.3% in FY27 on private investment revival: Deloitte
- [26/51] Agriculture: F. No. BEDF/2022-23-000051/054 16.10.2026 NOTICE INVITING TENDER The Basmati Export Develo
- [20/45] Banking & Finance: International Financial Services Centres Authority - International Financial Services Cent
- [27/35] National: India wants to push rupee trade to help forex-starved nations: Sitharaman
- [26/51] Agriculture: Untitled - ICAR-indian agricultural research institute
- [18/43] Banking & Finance: Untitled - Ministry of Finance, Department of Financial Services
- [26/34] National: Trump's US investment tracker: India ranks 6th with $500 billion, UAE leads with $1.4 tril
- [24/49] Agriculture: Accessibility Help - Department of Agriculture & Farmers Welfare
- [25/33] National: After SC notice, BJP accuses Rahul Gandhi of ‘spreading lies and confusion’ over Form 6
- [24/49] Agriculture: DROUGHT MANAGEMENT - Department of Agriculture & Farmers Welfare
- [24/32] National: Dr. Ashok Kumar Mittal leads 'Seva Sankalp', a salute to Prime Minister Modi's 25 years of
- [24/49] Agriculture: CROP INSURANCE DIVISION - Department of Agriculture & Farmers Welfare
- [23/31] National: Don't try to bulldoze Bill again, call all-party meet to discuss delimitation proposals: K
- [22/47] Agriculture: PLANT PROTECTION - Department of Agriculture & Farmers Welfare
- [23/31] National: Election Commission of India Nirvachan Sadan, Ashoka Road, New Delhi-110001 No.23/2026-ERS
- [22/47] Agriculture: HORTICULTURE - Department of Agriculture & Farmers Welfare
- [23/31] National: ECI Candidate Affidavit - Election Commission of India - ECI
- [22/47] Agriculture: RAINFED FARMING SYSTEM - Department of Agriculture & Farmers Welfare
- [23/31] National: Omaxe, Lemon Tree ink pact to manage 10 upcoming hotels worth ₹4,000 cr

## PDF qa report

```json
{
  "pdf_path": "/home/runner/work/daily-current-affairs/daily-current-affairs/output/daily_2026-10-16.pdf",
  "checked_at": "2026-10-16T11:54:44.185933+00:00",
  "passed": true,
  "page_count": 34,
  "file_size_bytes": 9093499,
  "devanagari_chars": 4246,
  "total_chars": 57806,
  "hindi_pct": 7.35,
  "font_names": [
    "AAAAAA+Mukta-Bold",
    "AAAAAA+Mukta-Regular",
    "AAAAAA+Poppins-Bold",
    "AAAAAA+Poppins-Regular",
    "AAAAAA+Poppins-SemiBold",
    "Helvetica"
  ],
  "mcq_count": 15,
  "answers_found": 14,
  "duplicate_questions": 0,
  "urls_found": 28,
  "blank_pages": [],
  "image_xobjects": 257,
  "issues": [
    {
      "severity": "warning",
      "code": "low_hindi",
      "message": "Hindi coverage 7.3% is low",
      "details": {
        "hindi_pct": 7.35
      }
    },
    {
      "severity": "warning",
      "code": "text_overflow",
      "message": "Text may overflow page bounds on pages: [7, 8]",
      "details": {
        "pages": [
          7,
          8
        ]
      }
    }
  ],
  "job_id": "daily_2026-10-16",
  "file_sha256": "a6697f5c5d5916f534575607f23e513663ca8e9abb6613b594f3fda8d7ce778c"
}
```

## PDF health report

```json
{
  "job_id": "daily_2026-10-16",
  "passed": true,
  "dry_run": true,
  "issues": [],
  "checked_at": "2026-10-16T11:54:44.777565+00:00"
}
```

## Stage log inventory

| log | lines | first | last |
|---|---|---|---|
| content_editor.log | 729 | 2026-10-16 11:54:09 | 2026-10-16 11:54:28 |
| deduplication.log | 5 | 2026-10-16 11:53:46 | 2026-10-16 11:54:09 |
| fact_verification.log | 580 | 2026-10-16 11:52:40 | 2026-10-16 11:53:46 |
| orchestrator_00.log | 10 | 2026-10-16 11:52:13 | 2026-10-16 11:52:15 |
| pdf_qa.log | 4 | 2026-10-16 11:54:44 | 2026-10-16 11:54:44 |
| pin_verifier.log | 1 | 2026-10-16 11:54:44 | 2026-10-16 11:54:44 |
| 00_model_orchestrator.log | 13 | --- attempt 1; exit |   warnings.warn( |
| 01_source_fetch.log | 61 | --- attempt 1; exit | [01_source_fetch] W |
| 04_fact_verification.log | 583 | --- attempt 1; exit |   warnings.warn( |
| 05_deduplication.log | 6 | --- attempt 1; exit | 2026-10-16 11:54:09 |
| 06_news_importance.log | 4 | --- attempt 1; exit | 2026-10-16 11:54:09 |
| 07_student_domain_relevance.log | 2 | --- attempt 1; exit | INFO:root:[STUDENT  |
| 10_final_news_selection.log | 8 | --- attempt 1; exit | 2026-10-16 11:54:09 |
| 11_importance_memory.log | 2 | --- attempt 1; exit | INFO:root:[IMPORTAN |
| 12_content_editor.log | 732 | --- attempt 1; exit |   warnings.warn( |
| 16_mcq_generator.log | 7 | --- attempt 1; exit | INFO:root:[MCQ GENE |
| 17_mcq_validator.log | 6 | --- attempt 1; exit | INFO:root:[MCQ VALI |
| 18_pdf_design.log | 3 | --- attempt 1; exit | [OK] PDF generated: |
| 19_pdf_qa.log | 24 | --- attempt 1; exit | 2026-10-16 11:54:44 |
| 22_telegram_publisher.log | 10 | --- attempt 1; exit |   warnings.warn( |
| 23_telegram_pin_verifier.log | 4 | --- attempt 1; exit |   warnings.warn( |
| 24_final_health_audit.log | 2 | --- attempt 1; exit | {"job_id": "daily_2 |
| telegram_publisher.log | 7 | 2026-10-16 11:54:44 | 2026-10-16 11:54:44 |

## Log excerpts (retries / skips / QA)

```
content_editor.log: 2026-10-16 11:54:09 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-16 11:54:10 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ["missing acronyms: ['POLICY']"]
content_editor.log: 2026-10-16 11:54:10 | WARNING  | pipeline.ai_translator | [Translator] openrouter parked for 900s (HTTP 402)
content_editor.log: 2026-10-16 11:54:11 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-16 11:54:11 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['gemini: rate limited', 'groq: validation failed', 'openrouter: HTTP 402', 'mistral: rate limited'])
content_editor.log: 2026-10-16 11:54:11 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ["missing acronyms: ['POLICY']", 'unusual length ratio 0.02']
content_editor.log: 2026-10-16 11:54:11 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['groq: validation failed'])
content_editor.log: 2026-10-16 11:54:12 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ["missing acronyms: ['POLICY']"]
content_editor.log: 2026-10-16 11:54:12 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['groq: validation failed'])
content_editor.log: 2026-10-16 11:54:13 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ["missing acronyms: ['GK']"]
content_editor.log: 2026-10-16 11:54:13 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['groq: validation failed'])
content_editor.log: 2026-10-16 11:54:13 | WARNING  | pipeline.ai_router | [Router] gemini HTTP 429 (rate_limit): {
content_editor.log: 2026-10-16 11:54:13 | WARNING  | pipeline.ai_router | [Router] Provider gemini disabled for 120s: rate limited
content_editor.log: 2026-10-16 11:54:20 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ['no Devanagari characters']
content_editor.log: 2026-10-16 11:54:20 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['groq: validation failed'])
content_editor.log: 2026-10-16 11:54:21 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ['no Devanagari characters']
content_editor.log: 2026-10-16 11:54:21 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['groq: validation failed'])
content_editor.log: 2026-10-16 11:54:23 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ["missing acronyms: ['CPI', 'GDP']"]
content_editor.log: 2026-10-16 11:54:23 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['groq: validation failed'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ["missing numbers: ['64 days']"]
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['groq: validation failed'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.ai_translator | [Translator] groq rate-limited (429)
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['groq: rate limited'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.ai_router | [Router] groq HTTP 429 (rate_limit): {"error":{"message":"Rate limit reached for model `openai/gpt-oss-120b` in organization `org_01m4n8hsfce0q8z1yndppr2nmv` service 
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.ai_router | [Router] Provider groq disabled for 120s: rate limited
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.ai_router | [Router] openrouter HTTP 402 (auth_error): {"error":{"message":"This request requires more credits, or fewer max_tokens. You requested up to 16384 tokens, but can onl
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.ai_router | [Router] Provider openrouter disabled for 3600s: auth error
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.ai_router | [Router] mistral HTTP 429 (rate_limit): {"object":"error","message":"Rate limit exceeded","type":"rate_limited","param":null,"code":"1300","raw_status_code":429}
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.ai_router | [Router] Provider mistral disabled for 120s: rate limited
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: mistral: rate_limit
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 11:54:28 | WARNING  | pipeline.content | [Content Builder] 118 translations need review (AI did not pass)
fact_verification.log: 2026-10-16 11:52:40 | WARNING  | pipeline.ai_router | [Router] gemini HTTP 429 (rate_limit): {
fact_verification.log: 2026-10-16 11:52:40 | WARNING  | pipeline.ai_router | [Router] Provider gemini disabled for 120s: rate limited
fact_verification.log: 2026-10-16 11:53:02 | WARNING  | pipeline.ai_router | [Router] groq HTTP 429 (rate_limit): {"error":{"message":"Rate limit reached for model `openai/gpt-oss-120b` in organization `org_01m4n8hsfce0q8z1yndppr2nmv` service 
fact_verification.log: 2026-10-16 11:53:02 | WARNING  | pipeline.ai_router | [Router] Provider groq disabled for 120s: rate limited
fact_verification.log: 2026-10-16 11:53:02 | WARNING  | pipeline.ai_router | [Router] openrouter HTTP 402 (auth_error): {"error":{"message":"This request requires more credits, or fewer max_tokens. You requested up to 16384 tokens, but can onl
fact_verification.log: 2026-10-16 11:53:02 | WARNING  | pipeline.ai_router | [Router] Provider openrouter disabled for 3600s: auth error
fact_verification.log: 2026-10-16 11:53:02 | WARNING  | pipeline.ai_router | [Router] mistral HTTP 429 (rate_limit): {"object":"error","message":"Rate limit exceeded","type":"rate_limited","param":null,"code":"1300","raw_status_code":429}
fact_verification.log: 2026-10-16 11:53:02 | WARNING  | pipeline.ai_router | [Router] Provider mistral disabled for 120s: rate limited
fact_verification.log: 2026-10-16 11:53:02 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: mistral: rate_limit
fact_verification.log: 2026-10-16 11:53:02 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:02 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:02 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:02 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:02 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:02 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:03 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:03 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:03 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:03 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:03 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:03 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:03 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:03 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:04 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:04 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:04 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:04 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:04 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:04 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:04 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:04 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:04 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:05 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:05 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:05 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:05 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:05 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:05 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:05 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:05 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:05 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:06 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:06 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:06 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:06 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:06 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:06 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:06 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:06 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:06 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:07 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:07 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:07 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:07 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:07 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:07 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:07 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:07 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:07 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:07 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:07 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:07 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:07 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:07 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:07 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:07 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:08 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:08 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:08 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:08 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:08 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:08 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 11:53:08 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
```

## Stage log tails

### content_editor.log

```
2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 11:54:28 | INFO     | pipeline.content | [Content Builder] Translation stats: ai=7 fallback=118 untranslated=0 (AI success 5.6%)
2026-10-16 11:54:28 | WARNING  | pipeline.content | [Content Builder] 118 translations need review (AI did not pass)
```

### deduplication.log

```
2026-10-16 11:53:46 | INFO     | agent.05_deduplication | Input: 562 articles from daily_2026-10-16.json
2026-10-16 11:53:46 | INFO     | agent.05_deduplication | After URL dedup: 562
2026-10-16 11:53:46 | INFO     | agent.05_deduplication | After fingerprint dedup: 469
2026-10-16 11:54:09 | INFO     | agent.05_deduplication | After similarity clustering: 446
2026-10-16 11:54:09 | INFO     | agent.05_deduplication | ✔ Dedup complete: 562 → 446 (20.6% reduction)
```

### fact_verification.log

```
2026-10-16 11:53:44 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:44 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:44 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:44 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:44 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:44 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:44 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:44 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:44 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:44 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:44 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:44 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:44 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:44 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:45 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:45 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:45 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:45 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:45 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:45 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:45 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:45 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:45 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:45 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:45 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:45 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:45 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:46 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:46 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:46 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:46 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:46 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:46 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:46 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:46 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:46 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:46 | INFO     | agent.04_fact_verification | Verification complete in 66.1s | 562 total | 562 passed | 0 rejected | 0 crashed
2026-10-16 11:53:46 | INFO     | agent.04_fact_verification | Avg confidence: 0.545
2026-10-16 11:53:46 | INFO     | agent.04_fact_verification | Methods: {'combined': 18, 'heuristic+cross_source': 544}
2026-10-16 11:53:46 | INFO     | agent.04_fact_verification | ✔ Fact verification completed: 562 items → /home/runner/work/daily-current-affairs/daily-current-affairs/data/verified/daily_2026-10-16.json
```

### orchestrator_00.log

```
2026-10-16 11:52:13 | INFO     | agent.00_model_orchestrator | Model orchestrator starting
2026-10-16 11:52:13 | INFO     | agent.00_model_orchestrator | Checking gemini (model=gemini-flash-latest)
2026-10-16 11:52:14 | INFO     | agent.00_model_orchestrator |   ❌ gemini → http_error
2026-10-16 11:52:14 | INFO     | agent.00_model_orchestrator | Checking groq (model=openai/gpt-oss-120b)
2026-10-16 11:52:14 | INFO     | agent.00_model_orchestrator |   ❌ groq → malformed
2026-10-16 11:52:14 | INFO     | agent.00_model_orchestrator | Checking openrouter (model=openai/gpt-4o-mini)
2026-10-16 11:52:15 | INFO     | agent.00_model_orchestrator |   ✅ openrouter → ok
2026-10-16 11:52:15 | INFO     | agent.00_model_orchestrator | Checking mistral (model=mistral-small-latest)
2026-10-16 11:52:15 | INFO     | agent.00_model_orchestrator |   ❌ mistral → rate_limit
2026-10-16 11:52:15 | INFO     | agent.00_model_orchestrator | Model status: 1/4 healthy → /home/runner/work/daily-current-affairs/daily-current-affairs/state/model_status.json
```

### pdf_design.log

```
```

### pdf_qa.log

```
2026-10-16 11:54:44 | INFO     | agent.19_pdf_qa | QA check: daily_2026-10-16.pdf
2026-10-16 11:54:44 | INFO     | agent.19_pdf_qa | QA requires at least 10 MCQs for 28 selected stories
2026-10-16 11:54:44 | INFO     | agent.19_pdf_qa | Report: /home/runner/work/daily-current-affairs/daily-current-affairs/logs/qa/daily_2026-10-16_qa.json
2026-10-16 11:54:44 | INFO     | agent.19_pdf_qa | ✔ PDF QA passed — safe to publish
```

### pin_verifier.log

```
2026-10-16 11:54:44 | INFO     | agent.23_telegram_pin_verifier | [DRY-RUN] No live publication receipt to pin.
```

### 00_model_orchestrator.log

```
--- attempt 1; exit 0 ---
2026-10-16 11:52:13 | INFO     | agent.00_model_orchestrator | Model orchestrator starting
2026-10-16 11:52:13 | INFO     | agent.00_model_orchestrator | Checking gemini (model=gemini-flash-latest)
2026-10-16 11:52:14 | INFO     | agent.00_model_orchestrator |   ❌ gemini → http_error
2026-10-16 11:52:14 | INFO     | agent.00_model_orchestrator | Checking groq (model=openai/gpt-oss-120b)
2026-10-16 11:52:14 | INFO     | agent.00_model_orchestrator |   ❌ groq → malformed
2026-10-16 11:52:14 | INFO     | agent.00_model_orchestrator | Checking openrouter (model=openai/gpt-4o-mini)
2026-10-16 11:52:15 | INFO     | agent.00_model_orchestrator |   ✅ openrouter → ok
2026-10-16 11:52:15 | INFO     | agent.00_model_orchestrator | Checking mistral (model=mistral-small-latest)
2026-10-16 11:52:15 | INFO     | agent.00_model_orchestrator |   ❌ mistral → rate_limit
2026-10-16 11:52:15 | INFO     | agent.00_model_orchestrator | Model status: 1/4 healthy → /home/runner/work/daily-current-affairs/daily-current-affairs/state/model_status.json
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/requests/__init__.py:113: RequestsDependencyWarning: urllib3 (2.2.3) or chardet (7.6.0)/charset_normalizer (3.4.0) doesn't match a supported version!
  warnings.warn(
```

### 01_source_fetch.log

```
[01_source_fetch] NPCI: 0 in-window (of 2 entries, 0 malformed skipped)
[01_source_fetch] PFRDA: 0 in-window (of 12 entries, 0 malformed skipped)
[01_source_fetch] IRDAI: 0 in-window (of 0 entries, 0 malformed skipped)
[01_source_fetch] IFSCA: 1 in-window (of 85 entries, 0 malformed skipped)
[01_source_fetch] Department of Financial Services: 1 in-window (of 20 entries, 0 malformed skipped)
[01_source_fetch] Union Budget of India: 0 in-window (of 2 entries, 0 malformed skipped)
[01_source_fetch] GST Council: 0 in-window (of 27 entries, 0 malformed skipped)
[01_source_fetch] Competition Commission of India: 2 in-window (of 73 entries, 0 malformed skipped)
[01_source_fetch] RBI Bulletin: 0 in-window (of 0 entries, 0 malformed skipped)
[01_source_fetch] India.gov.in: 17 in-window (of 97 entries, 0 malformed skipped)
[01_source_fetch] Prime Minister of India: 5 in-window (of 26 entries, 0 malformed skipped)
[01_source_fetch] Cabinet Secretariat: 0 in-window (of 1 entries, 0 malformed skipped)
[01_source_fetch] MyGov India: 46 in-window (of 100 entries, 0 malformed skipped)
[01_source_fetch] Ministry of Rural Development: 0 in-window (of 0 entries, 0 malformed skipped)
[01_source_fetch] Ministry of Cooperation: 0 in-window (of 9 entries, 0 malformed skipped)
[01_source_fetch] Department of Science and Technology: 2 in-window (of 100 entries, 0 malformed skipped)
[01_source_fetch] Department of Biotechnology: 0 in-window (of 0 entries, 0 malformed skipped)
[01_source_fetch] DRDO: 54 in-window (of 100 entries, 0 malformed skipped)
[01_source_fetch] Central Pollution Control Board: 0 in-window (of 7 entries, 0 malformed skipped)
[01_source_fetch] Ministry of Education: 0 in-window (of 24 entries, 0 malformed skipped)
[01_source_fetch] UGC: 0 in-window (of 2 entries, 0 malformed skipped)
[01_source_fetch] National Testing Agency: 0 in-window (of 0 entries, 0 malformed skipped)
[01_source_fetch] Ministry of Defence: 0 in-window (of 13 entries, 0 malformed skipped)
[01_source_fetch] President of India: 4 in-window (of 21 entries, 0 malformed skipped)
[01_source_fetch] Election Commission of India: 2 in-window (of 10 entries, 0 malformed skipped)
[01_source_fetch] UPSC: 0 in-window (of 4 entries, 0 malformed skipped)
[01_source_fetch] The Hindu: 26 in-window (of 60 entries, 0 malformed skipped)
[01_source_fetch] Business Standard: 120 in-window (of 120 entries, 0 malformed skipped)
[01_source_fetch] Mint: 35 in-window (of 35 entries, 0 malformed skipped)
[01_source_fetch] Economic Times: 6 in-window (of 76 entries, 0 malformed skipped)
[01_source_fetch] Google News India: 36 in-window (of 38 entries, 0 malformed skipped)
[01_source_fetch] Google News Search: 94 in-window (of 100 entries, 0 malformed skipped)
[01_source_fetch] wrote /home/runner/work/daily-current-affairs/daily-current-affairs/data/raw/daily_2026-10-16.json (562 articles, 52/57 feeds ok)
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/requests/__init__.py:113: RequestsDependencyWarning: urllib3 (2.2.3) or chardet (7.6.0)/charset_normalizer (3.4.0) doesn't match a supported version!
  warnings.warn(
[01_source_fetch] WARN feed failed: Indian Express -> HTTPError: 403 Client Error: Forbidden for url: https://indianexpress.com/feed/
[01_source_fetch] WARN feed failed: PIB — Press Information Bureau -> feed parse error (<unknown>:15:70: not well-formed (invalid token))
[01_source_fetch] WARN feed failed: SEBI -> feed parse error (<unknown>:65:21: undefined entity)
[01_source_fetch] WARN feed failed: Ministry of External Affairs -> HTTPError: 403 Client Error: Forbidden for url: https://www.mea.gov.in/rss-feeds.htm
[01_source_fetch] WARN feed failed: Reuters -> HTTPError: 404 Client Error: Not Found for url: https://reutersagency.com/feed/?best-topics=tech&post_type=best
```

### 04_fact_verification.log

```
2026-10-16 11:53:44 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:44 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:44 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:44 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:44 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:44 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:44 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:44 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:44 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:44 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:44 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:44 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:45 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:45 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:45 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:45 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:45 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:45 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:45 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:45 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:45 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:45 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:45 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:45 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:45 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:46 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:46 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:46 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:46 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:46 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:46 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:46 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:46 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:46 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 11:53:46 | INFO     | agent.04_fact_verification | Verification complete in 66.1s | 562 total | 562 passed | 0 rejected | 0 crashed
2026-10-16 11:53:46 | INFO     | agent.04_fact_verification | Avg confidence: 0.545
2026-10-16 11:53:46 | INFO     | agent.04_fact_verification | Methods: {'combined': 18, 'heuristic+cross_source': 544}
2026-10-16 11:53:46 | INFO     | agent.04_fact_verification | ✔ Fact verification completed: 562 items → /home/runner/work/daily-current-affairs/daily-current-affairs/data/verified/daily_2026-10-16.json
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/requests/__init__.py:113: RequestsDependencyWarning: urllib3 (2.2.3) or chardet (7.6.0)/charset_normalizer (3.4.0) doesn't match a supported version!
  warnings.warn(
```

### 05_deduplication.log

```
--- attempt 1; exit 0 ---
2026-10-16 11:53:46 | INFO     | agent.05_deduplication | Input: 562 articles from daily_2026-10-16.json
2026-10-16 11:53:46 | INFO     | agent.05_deduplication | After URL dedup: 562
2026-10-16 11:53:46 | INFO     | agent.05_deduplication | After fingerprint dedup: 469
2026-10-16 11:54:09 | INFO     | agent.05_deduplication | After similarity clustering: 446
2026-10-16 11:54:09 | INFO     | agent.05_deduplication | ✔ Dedup complete: 562 → 446 (20.6% reduction)
```

### 06_news_importance.log

```
--- attempt 1; exit 0 ---
[06_news_importance] job=daily_2026-10-16 type=daily date=2026-10-16
[06] OK — scored=446
2026-10-16 11:54:09,228 | INFO     | root | [NEWS IMPORTANCE AGENT] scored 446 events, top=33
```

### 07_student_domain_relevance.log

```
--- attempt 1; exit 0 ---
INFO:root:[STUDENT & DOMAIN RELEVANCE AGENT] relevant=41/446 agri=18 banking=5
```

### 10_final_news_selection.log

```
--- attempt 1; exit 0 ---
[10_final_news_selection] job=daily_2026-10-16 type=daily date=2026-10-16
[10] OK — selected_count=28
2026-10-16 11:54:09,422 | INFO     | root | [FINAL NEWS SELECTION AGENT v2] selected 28 items (target=28)
2026-10-16 11:54:09,422 | INFO     | root |   Agriculture: 11
2026-10-16 11:54:09,422 | INFO     | root |   National: 11
2026-10-16 11:54:09,422 | INFO     | root |   Banking & Finance: 5
2026-10-16 11:54:09,422 | INFO     | root |   Economy: 1
```

### 11_importance_memory.log

```
--- attempt 1; exit 0 ---
INFO:root:[IMPORTANCE MEMORY AGENT] memory updated for 28 events (local + persistent)
```

### 12_content_editor.log

```
2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 11:54:28 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 11:54:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 11:54:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 11:54:28 | INFO     | pipeline.content | [Content Builder] Translation stats: ai=7 fallback=118 untranslated=0 (AI success 5.6%)
2026-10-16 11:54:28 | WARNING  | pipeline.content | [Content Builder] 118 translations need review (AI did not pass)
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/requests/__init__.py:113: RequestsDependencyWarning: urllib3 (2.2.3) or chardet (7.6.0)/charset_normalizer (3.4.0) doesn't match a supported version!
  warnings.warn(
```

### 16_mcq_generator.log

```
--- attempt 1; exit 0 ---
INFO:root:[MCQ GENERATOR AGENT v4 (FAIL-CLOSED)] Generating MCQs for 28 items...
INFO:root:[MCQ GENERATOR AGENT v4 (FAIL-CLOSED)] Generated 15 raw MCQs
INFO:root:[MCQ GENERATOR AGENT v4 (FAIL-CLOSED)] Running mcq_validator (FAIL-CLOSED)...
INFO:pipeline.content:[MCQ Validation] 14/15 MCQs passed (1 rejected)
INFO:root:[MCQ GENERATOR AGENT v4 (FAIL-CLOSED)] Validation: 14/15 passed (1 rejected)
INFO:root:[MCQ GENERATOR AGENT v4 (FAIL-CLOSED)] ✓ Final: 14 VALIDATED MCQs using mcq_validator_v2
```

### 17_mcq_validator.log

```
--- attempt 1; exit 0 ---
INFO:root:[MCQ VALIDATOR AGENT v4 (FAIL-CLOSED)] Validating 14 MCQs from Agent 16...
INFO:root:[MCQ VALIDATOR AGENT v4 (FAIL-CLOSED)] Running mcq_validator (FAIL-CLOSED)...
INFO:pipeline.content:[MCQ Validation] 14/14 MCQs passed (0 rejected)
INFO:root:[MCQ VALIDATOR AGENT v4 (FAIL-CLOSED)] Validation: 14/14 passed (0 rejected)
INFO:root:[MCQ VALIDATOR AGENT v4 (FAIL-CLOSED)] ✓ Final: 14 VALIDATED MCQs using mcq_validator_v2
```

### 18_pdf_design.log

```
--- attempt 1; exit 0 ---
✓ Fonts registered: Poppins + Mukta
[OK] PDF generated: /home/runner/work/daily-current-affairs/daily-current-affairs/output/daily_2026-10-16.pdf
```

### 19_pdf_qa.log

```
--- attempt 1; exit 0 ---
2026-10-16 11:54:44 | INFO     | agent.19_pdf_qa | QA check: daily_2026-10-16.pdf
2026-10-16 11:54:44 | INFO     | agent.19_pdf_qa | QA requires at least 10 MCQs for 28 selected stories
2026-10-16 11:54:44 | INFO     | agent.19_pdf_qa | Report: /home/runner/work/daily-current-affairs/daily-current-affairs/logs/qa/daily_2026-10-16_qa.json
========================================================================
PDF QA REPORT — ✅ PASSED
========================================================================
File:            /home/runner/work/daily-current-affairs/daily-current-affairs/output/daily_2026-10-16.pdf
Size:            8880 KB
Pages:           34
Chars:           57806
Devanagari:      4246 (7.3%)
Fonts:           6 (AAAAAA+Mukta-Bold, AAAAAA+Mukta-Regular, AAAAAA+Poppins-Bold...)
MCQs:            15
Answer markers:  14
Duplicate Qs:    0
URLs:            28
Images:          257
Blank pages:     none
--- Issues ---
  ⚠️  [low_hindi] Hindi coverage 7.3% is low
  ⚠️  [text_overflow] Text may overflow page bounds on pages: [7, 8]
========================================================================
2026-10-16 11:54:44 | INFO     | agent.19_pdf_qa | ✔ PDF QA passed — safe to publish
```

### 22_telegram_publisher.log

```
--- attempt 1; exit 0 ---
2026-10-16 11:54:44 | INFO     | agent.22_telegram_publisher | Found 1 candidate PDF(s) (max 5 per run)
2026-10-16 11:54:44 | WARNING  | agent.22_telegram_publisher | Adopted 10 unverifiable legacy publication row(s) as history
2026-10-16 11:54:44 | INFO     | agent.22_telegram_publisher | [1/1] daily_2026-10-16.pdf
2026-10-16 11:54:44 | INFO     | agent.22_telegram_publisher | [DRY-RUN] Would publish daily_2026-10-16.pdf (9093499 bytes) with caption:
<b>&gt;&gt; Policy Coordination – Department of Agriculture &amp; Farmers' Welfare</b>
POLICY – https://news.google.com/rss/articles/CBMiZkFVX3lxTE00NXJ3UmNMdHhNNzdVenZYRjliMFpDVnZWcHhTbHRZT092a1dxUH
2026-10-16 11:54:44 | INFO     | agent.22_telegram_publisher | Publishing complete: success=1 failed=0 skipped=0 total=1
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/requests/__init__.py:113: RequestsDependencyWarning: urllib3 (2.2.3) or chardet (7.6.0)/charset_normalizer (3.4.0) doesn't match a supported version!
  warnings.warn(
```

### 23_telegram_pin_verifier.log

```
--- attempt 1; exit 0 ---
2026-10-16 11:54:44 | INFO     | agent.23_telegram_pin_verifier | [DRY-RUN] No live publication receipt to pin.
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/requests/__init__.py:113: RequestsDependencyWarning: urllib3 (2.2.3) or chardet (7.6.0)/charset_normalizer (3.4.0) doesn't match a supported version!
  warnings.warn(
```

### 24_final_health_audit.log

```
--- attempt 1; exit 0 ---
{"job_id": "daily_2026-10-16", "passed": true, "dry_run": true, "issues": [], "checked_at": "2026-10-16T11:54:44.777565+00:00"}
```

### telegram_publisher.log

```
2026-10-16 11:54:44 | INFO     | agent.22_telegram_publisher | Found 1 candidate PDF(s) (max 5 per run)
2026-10-16 11:54:44 | WARNING  | agent.22_telegram_publisher | Adopted 10 unverifiable legacy publication row(s) as history
2026-10-16 11:54:44 | INFO     | agent.22_telegram_publisher | [1/1] daily_2026-10-16.pdf
2026-10-16 11:54:44 | INFO     | agent.22_telegram_publisher | [DRY-RUN] Would publish daily_2026-10-16.pdf (9093499 bytes) with caption:
<b>&gt;&gt; Policy Coordination – Department of Agriculture &amp; Farmers' Welfare</b>
POLICY – https://news.google.com/rss/articles/CBMiZkFVX3lxTE00NXJ3UmNMdHhNNzdVenZYRjliMFpDVnZWcHhTbHRZT092a1dxUH
2026-10-16 11:54:44 | INFO     | agent.22_telegram_publisher | Publishing complete: success=1 failed=0 skipped=0 total=1
```

## Committed state on this branch at collection time

```json
{
 "status": "failed",
 "dry_run": false,
 "last_success_stage": "11_importance_memory",
 "failed_stage": "12_content_editor",
 "checkpoint_run_id": "38879885706",
 "last_error": "12_content_editor: failed after 3 attempt(s): -16 09:24:19 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None\n2026-10-16 09:24:19 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None\n2026-10-16 09:24:19 | INFO     | pipeline.content | [Content Builder] Translation stats: ai=0 fallback=0 untranslated=7 (AI success 0.0%)\n2026-10-16 09:24:19 | WARNING  | pipeline.content | [Content Builder] 7 translations need review (AI did not pass)\n2026-10-16 09:24:19 | ERROR    | __main__ | Translation validation failed; refusing to publish unreviewed content\n\n/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/requests/__init__.py:113: RequestsDependencyWarning: urllib3 (2.2.3) or chardet (7.6.0)/charset_normalizer (3.4.0) doesn't match a supported version!\n  warnings.warn("
}
```
