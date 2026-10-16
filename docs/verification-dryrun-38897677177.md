# Dry-run evidence — run 38897677177

- run URL: https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/38897677177
- edition: 2026-10-16 (DRY_RUN=1)

## Article counts

| stage | count |
|---|---|
| raw | 574 |
| verified | 574 |
| dedup | 458 |
| scored | 42 |
| selected | 28 |
| content | 28 |
| mcq | 14 |

## Category distribution per stage (raw keys here = normalisation missing)

- raw: ```{"agriculture": 2, "national": 60, "agriculture_core": 19, "banking_finance": 14, "economy_data": 7, "food_safety": 12, "environment": 2, "govt_national": 77, "science": 5, "defence_science": 53, "discovery": 190, "aggregator": 133}```

## Selected items

- [33/58] Agriculture: POLICY COORDINATION - Department of Agriculture & Farmers Welfare
- [22/47] Banking & Finance: Press Releases - Reserve Bank of India
- [15/30] Economy: Competition Commission of India, Government of India - Competition Commission of India
- [30/38] National: Don't bulldoze delimitation Bill again, call all-party meet: Kharge to Modi
- [27/52] Agriculture: Assistance to NCDC Programmes for Development of Co-operatives under the Central Sector In
- [22/47] Banking & Finance: Press Releases| Official Website of Reserve Bank of India - Reserve Bank of India
- [28/36] National: South Indian Bank aims 16% loan growth in FY27 amid West Asia war risks
- [26/51] Agriculture: Copyright Policy - Department of Agriculture & Farmers Welfare
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
- [22/47] Agriculture: PLANT PROTECTION - Department of Agriculture & Farmers Welfare
- [23/31] National: Don't try to bulldoze Bill again, call all-party meet to discuss delimitation proposals: K
- [22/47] Agriculture: HORTICULTURE - Department of Agriculture & Farmers Welfare
- [23/31] National: Election Commission of India Nirvachan Sadan, Ashoka Road, New Delhi-110001 No.23/2026-ERS
- [22/47] Agriculture: Related Links - Department of Agriculture & Farmers Welfare
- [23/31] National: ECI Candidate Affidavit - Election Commission of India - ECI
- [22/47] Agriculture: PRICE SUPPORT - Department of Agriculture & Farmers Welfare
- [23/31] National: Omaxe, Lemon Tree ink pact to manage 10 upcoming hotels worth ₹4,000 cr

## PDF qa report

```json
{
  "pdf_path": "/home/runner/work/daily-current-affairs/daily-current-affairs/output/daily_2026-10-16.pdf",
  "checked_at": "2026-10-16T12:04:06.516790+00:00",
  "passed": true,
  "page_count": 34,
  "file_size_bytes": 9019271,
  "devanagari_chars": 3787,
  "total_chars": 57998,
  "hindi_pct": 6.53,
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
      "message": "Hindi coverage 6.5% is low",
      "details": {
        "hindi_pct": 6.53
      }
    },
    {
      "severity": "warning",
      "code": "text_overflow",
      "message": "Text may overflow page bounds on pages: [7, 9]",
      "details": {
        "pages": [
          7,
          9
        ]
      }
    }
  ],
  "job_id": "daily_2026-10-16",
  "file_sha256": "22965fee1f2f6f5db5bd1920e2aa37406df2e432858fa0715d65caaa2ca478f6"
}
```

## PDF health report

```json
{
  "job_id": "daily_2026-10-16",
  "passed": true,
  "dry_run": true,
  "issues": [],
  "checked_at": "2026-10-16T12:04:06.870232+00:00"
}
```

## Stage log inventory

| log | lines | first | last |
|---|---|---|---|
| content_editor.log | 738 | 2026-10-16 12:03:44 | 2026-10-16 12:03:58 |
| deduplication.log | 5 | 2026-10-16 12:03:31 | 2026-10-16 12:03:43 |
| fact_verification.log | 592 | 2026-10-16 12:02:38 | 2026-10-16 12:03:31 |
| orchestrator_00.log | 10 | 2026-10-16 12:02:07 | 2026-10-16 12:02:10 |
| pdf_qa.log | 4 | 2026-10-16 12:04:06 | 2026-10-16 12:04:06 |
| pin_verifier.log | 1 | 2026-10-16 12:04:06 | 2026-10-16 12:04:06 |
| 00_model_orchestrator.log | 13 | --- attempt 1; exit |   warnings.warn( |
| 01_source_fetch.log | 61 | --- attempt 1; exit | [01_source_fetch] W |
| 04_fact_verification.log | 595 | --- attempt 1; exit |   warnings.warn( |
| 05_deduplication.log | 6 | --- attempt 1; exit | 2026-10-16 12:03:43 |
| 06_news_importance.log | 4 | --- attempt 1; exit | 2026-10-16 12:03:44 |
| 07_student_domain_relevance.log | 2 | --- attempt 1; exit | INFO:root:[STUDENT  |
| 10_final_news_selection.log | 8 | --- attempt 1; exit | 2026-10-16 12:03:44 |
| 11_importance_memory.log | 2 | --- attempt 1; exit | INFO:root:[IMPORTAN |
| 12_content_editor.log | 741 | --- attempt 1; exit |   warnings.warn( |
| 16_mcq_generator.log | 7 | --- attempt 1; exit | INFO:root:[MCQ GENE |
| 17_mcq_validator.log | 6 | --- attempt 1; exit | INFO:root:[MCQ VALI |
| 18_pdf_design.log | 3 | --- attempt 1; exit | [OK] PDF generated: |
| 19_pdf_qa.log | 24 | --- attempt 1; exit | 2026-10-16 12:04:06 |
| 22_telegram_publisher.log | 10 | --- attempt 1; exit |   warnings.warn( |
| 23_telegram_pin_verifier.log | 4 | --- attempt 1; exit |   warnings.warn( |
| 24_final_health_audit.log | 2 | --- attempt 1; exit | {"job_id": "daily_2 |
| telegram_publisher.log | 7 | 2026-10-16 12:04:06 | 2026-10-16 12:04:06 |

## Log excerpts (retries / skips / QA)

```
content_editor.log: 2026-10-16 12:03:44 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-16 12:03:45 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ["missing acronyms: ['POLICY']"]
content_editor.log: 2026-10-16 12:03:45 | WARNING  | pipeline.ai_translator | [Translator] openrouter parked for 900s (HTTP 402)
content_editor.log: 2026-10-16 12:03:45 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-16 12:03:45 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['gemini: rate limited', 'groq: validation failed', 'openrouter: HTTP 402', 'mistral: rate limited'])
content_editor.log: 2026-10-16 12:03:46 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ["missing acronyms: ['POLICY']", 'unusual length ratio 0.02']
content_editor.log: 2026-10-16 12:03:46 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['groq: validation failed'])
content_editor.log: 2026-10-16 12:03:47 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ["missing acronyms: ['POLICY']"]
content_editor.log: 2026-10-16 12:03:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['groq: validation failed'])
content_editor.log: 2026-10-16 12:03:47 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ["missing acronyms: ['GK']"]
content_editor.log: 2026-10-16 12:03:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['groq: validation failed'])
content_editor.log: 2026-10-16 12:03:48 | WARNING  | pipeline.ai_router | [Router] gemini HTTP 429 (rate_limit): {
content_editor.log: 2026-10-16 12:03:48 | WARNING  | pipeline.ai_router | [Router] Provider gemini disabled for 120s: rate limited
content_editor.log: 2026-10-16 12:03:51 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ['unusual length ratio 0.40']
content_editor.log: 2026-10-16 12:03:51 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['groq: validation failed'])
content_editor.log: 2026-10-16 12:03:55 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ['no Devanagari characters']
content_editor.log: 2026-10-16 12:03:55 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['groq: validation failed'])
content_editor.log: 2026-10-16 12:03:56 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ['unusual length ratio 0.05']
content_editor.log: 2026-10-16 12:03:56 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['groq: validation failed'])
content_editor.log: 2026-10-16 12:03:57 | WARNING  | pipeline.ai_translator | [Translator] groq rate-limited (429)
content_editor.log: 2026-10-16 12:03:57 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['groq: rate limited'])
content_editor.log: 2026-10-16 12:03:57 | WARNING  | pipeline.ai_router | [Router] groq HTTP 429 (rate_limit): {"error":{"message":"Rate limit reached for model `openai/gpt-oss-120b` in organization `org_01m4n8hsfce0q8z1yndppr2nmv` service 
content_editor.log: 2026-10-16 12:03:57 | WARNING  | pipeline.ai_router | [Router] Provider groq disabled for 120s: rate limited
content_editor.log: 2026-10-16 12:03:57 | WARNING  | pipeline.ai_router | [Router] openrouter HTTP 402 (auth_error): {"error":{"message":"This request requires more credits, or fewer max_tokens. You requested up to 16384 tokens, but can onl
content_editor.log: 2026-10-16 12:03:57 | WARNING  | pipeline.ai_router | [Router] Provider openrouter disabled for 3600s: auth error
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.ai_router | [Router] mistral HTTP 429 (rate_limit): {"object":"error","message":"Rate limit exceeded","type":"rate_limited","param":null,"code":"1300","raw_status_code":429}
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.ai_router | [Router] Provider mistral disabled for 120s: rate limited
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: mistral: rate_limit
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:03:58 | WARNING  | pipeline.content | [Content Builder] 121 translations need review (AI did not pass)
fact_verification.log: 2026-10-16 12:02:46 | WARNING  | pipeline.ai_router | [Router] gemini HTTP 429 (rate_limit): {
fact_verification.log: 2026-10-16 12:02:46 | WARNING  | pipeline.ai_router | [Router] Provider gemini disabled for 120s: rate limited
fact_verification.log: 2026-10-16 12:03:05 | WARNING  | pipeline.ai_router | [Router] groq HTTP 429 (rate_limit): {"error":{"message":"Rate limit reached for model `openai/gpt-oss-120b` in organization `org_01m4n8hsfce0q8z1yndppr2nmv` service 
fact_verification.log: 2026-10-16 12:03:05 | WARNING  | pipeline.ai_router | [Router] Provider groq disabled for 120s: rate limited
fact_verification.log: 2026-10-16 12:03:05 | WARNING  | pipeline.ai_router | [Router] openrouter HTTP 402 (auth_error): {"error":{"message":"This request requires more credits, or fewer max_tokens. You requested up to 16384 tokens, but can onl
fact_verification.log: 2026-10-16 12:03:05 | WARNING  | pipeline.ai_router | [Router] Provider openrouter disabled for 3600s: auth error
fact_verification.log: 2026-10-16 12:03:05 | WARNING  | pipeline.ai_router | [Router] mistral HTTP 429 (rate_limit): {"object":"error","message":"Rate limit exceeded","type":"rate_limited","param":null,"code":"1300","raw_status_code":429}
fact_verification.log: 2026-10-16 12:03:05 | WARNING  | pipeline.ai_router | [Router] Provider mistral disabled for 120s: rate limited
fact_verification.log: 2026-10-16 12:03:05 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: mistral: rate_limit
fact_verification.log: 2026-10-16 12:03:05 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:05 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:05 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:05 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:05 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:05 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:05 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:06 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:06 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:06 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:06 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:06 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:06 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:06 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:06 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:06 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:06 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:06 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:06 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:06 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:06 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:06 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:06 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:07 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:07 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:07 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:07 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:07 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:07 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:07 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:07 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:07 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:07 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:07 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:07 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:07 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:07 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:07 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:07 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:08 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:08 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:08 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:08 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:08 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:08 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:08 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:08 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:08 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:08 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:08 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:08 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:08 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:08 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:08 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:08 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:08 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:08 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:08 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:03:08 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
```

## Stage log tails

### content_editor.log

```
2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 12:03:58 | INFO     | pipeline.content | [Content Builder] Translation stats: ai=4 fallback=121 untranslated=0 (AI success 3.2%)
2026-10-16 12:03:58 | WARNING  | pipeline.content | [Content Builder] 121 translations need review (AI did not pass)
```

### deduplication.log

```
2026-10-16 12:03:31 | INFO     | agent.05_deduplication | Input: 574 articles from daily_2026-10-16.json
2026-10-16 12:03:31 | INFO     | agent.05_deduplication | After URL dedup: 574
2026-10-16 12:03:31 | INFO     | agent.05_deduplication | After fingerprint dedup: 481
2026-10-16 12:03:43 | INFO     | agent.05_deduplication | After similarity clustering: 458
2026-10-16 12:03:43 | INFO     | agent.05_deduplication | ✔ Dedup complete: 574 → 458 (20.2% reduction)
```

### fact_verification.log

```
2026-10-16 12:03:29 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:29 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:29 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:29 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:29 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:29 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:29 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:29 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:31 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:31 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:31 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:31 | INFO     | agent.04_fact_verification | Verification complete in 53.1s | 574 total | 574 passed | 0 rejected | 0 crashed
2026-10-16 12:03:31 | INFO     | agent.04_fact_verification | Avg confidence: 0.545
2026-10-16 12:03:31 | INFO     | agent.04_fact_verification | Methods: {'heuristic+cross_source': 558, 'combined': 16}
2026-10-16 12:03:31 | INFO     | agent.04_fact_verification | ✔ Fact verification completed: 574 items → /home/runner/work/daily-current-affairs/daily-current-affairs/data/verified/daily_2026-10-16.json
```

### orchestrator_00.log

```
2026-10-16 12:02:07 | INFO     | agent.00_model_orchestrator | Model orchestrator starting
2026-10-16 12:02:07 | INFO     | agent.00_model_orchestrator | Checking gemini (model=gemini-flash-latest)
2026-10-16 12:02:07 | INFO     | agent.00_model_orchestrator |   ❌ gemini → http_error
2026-10-16 12:02:07 | INFO     | agent.00_model_orchestrator | Checking groq (model=openai/gpt-oss-120b)
2026-10-16 12:02:08 | INFO     | agent.00_model_orchestrator |   ❌ groq → malformed
2026-10-16 12:02:08 | INFO     | agent.00_model_orchestrator | Checking openrouter (model=openai/gpt-4o-mini)
2026-10-16 12:02:09 | INFO     | agent.00_model_orchestrator |   ✅ openrouter → ok
2026-10-16 12:02:09 | INFO     | agent.00_model_orchestrator | Checking mistral (model=mistral-small-latest)
2026-10-16 12:02:10 | INFO     | agent.00_model_orchestrator |   ❌ mistral → rate_limit
2026-10-16 12:02:10 | INFO     | agent.00_model_orchestrator | Model status: 1/4 healthy → /home/runner/work/daily-current-affairs/daily-current-affairs/state/model_status.json
```

### pdf_design.log

```
```

### pdf_qa.log

```
2026-10-16 12:04:06 | INFO     | agent.19_pdf_qa | QA check: daily_2026-10-16.pdf
2026-10-16 12:04:06 | INFO     | agent.19_pdf_qa | QA requires at least 10 MCQs for 28 selected stories
2026-10-16 12:04:06 | INFO     | agent.19_pdf_qa | Report: /home/runner/work/daily-current-affairs/daily-current-affairs/logs/qa/daily_2026-10-16_qa.json
2026-10-16 12:04:06 | INFO     | agent.19_pdf_qa | ✔ PDF QA passed — safe to publish
```

### pin_verifier.log

```
2026-10-16 12:04:06 | INFO     | agent.23_telegram_pin_verifier | [DRY-RUN] No live publication receipt to pin.
```

### 00_model_orchestrator.log

```
--- attempt 1; exit 0 ---
2026-10-16 12:02:07 | INFO     | agent.00_model_orchestrator | Model orchestrator starting
2026-10-16 12:02:07 | INFO     | agent.00_model_orchestrator | Checking gemini (model=gemini-flash-latest)
2026-10-16 12:02:07 | INFO     | agent.00_model_orchestrator |   ❌ gemini → http_error
2026-10-16 12:02:07 | INFO     | agent.00_model_orchestrator | Checking groq (model=openai/gpt-oss-120b)
2026-10-16 12:02:08 | INFO     | agent.00_model_orchestrator |   ❌ groq → malformed
2026-10-16 12:02:08 | INFO     | agent.00_model_orchestrator | Checking openrouter (model=openai/gpt-4o-mini)
2026-10-16 12:02:09 | INFO     | agent.00_model_orchestrator |   ✅ openrouter → ok
2026-10-16 12:02:09 | INFO     | agent.00_model_orchestrator | Checking mistral (model=mistral-small-latest)
2026-10-16 12:02:10 | INFO     | agent.00_model_orchestrator |   ❌ mistral → rate_limit
2026-10-16 12:02:10 | INFO     | agent.00_model_orchestrator | Model status: 1/4 healthy → /home/runner/work/daily-current-affairs/daily-current-affairs/state/model_status.json
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/requests/__init__.py:113: RequestsDependencyWarning: urllib3 (2.2.3) or chardet (7.6.0)/charset_normalizer (3.4.0) doesn't match a supported version!
  warnings.warn(
```

### 01_source_fetch.log

```
[01_source_fetch] NPCI: 0 in-window (of 2 entries, 0 malformed skipped)
[01_source_fetch] PFRDA: 0 in-window (of 12 entries, 0 malformed skipped)
[01_source_fetch] IRDAI: 0 in-window (of 0 entries, 0 malformed skipped)
[01_source_fetch] IFSCA: 1 in-window (of 84 entries, 0 malformed skipped)
[01_source_fetch] Department of Financial Services: 1 in-window (of 21 entries, 0 malformed skipped)
[01_source_fetch] Union Budget of India: 0 in-window (of 2 entries, 0 malformed skipped)
[01_source_fetch] GST Council: 0 in-window (of 27 entries, 0 malformed skipped)
[01_source_fetch] Competition Commission of India: 1 in-window (of 73 entries, 0 malformed skipped)
[01_source_fetch] RBI Bulletin: 0 in-window (of 0 entries, 0 malformed skipped)
[01_source_fetch] India.gov.in: 18 in-window (of 96 entries, 0 malformed skipped)
[01_source_fetch] Prime Minister of India: 5 in-window (of 25 entries, 0 malformed skipped)
[01_source_fetch] Cabinet Secretariat: 0 in-window (of 1 entries, 0 malformed skipped)
[01_source_fetch] MyGov India: 47 in-window (of 100 entries, 0 malformed skipped)
[01_source_fetch] Ministry of Rural Development: 0 in-window (of 0 entries, 0 malformed skipped)
[01_source_fetch] Ministry of Cooperation: 0 in-window (of 9 entries, 0 malformed skipped)
[01_source_fetch] Department of Science and Technology: 5 in-window (of 100 entries, 0 malformed skipped)
[01_source_fetch] Department of Biotechnology: 0 in-window (of 0 entries, 0 malformed skipped)
[01_source_fetch] DRDO: 53 in-window (of 100 entries, 0 malformed skipped)
[01_source_fetch] Central Pollution Control Board: 0 in-window (of 7 entries, 0 malformed skipped)
[01_source_fetch] Ministry of Education: 0 in-window (of 24 entries, 0 malformed skipped)
[01_source_fetch] UGC: 0 in-window (of 1 entries, 0 malformed skipped)
[01_source_fetch] National Testing Agency: 0 in-window (of 0 entries, 0 malformed skipped)
[01_source_fetch] Ministry of Defence: 0 in-window (of 13 entries, 0 malformed skipped)
[01_source_fetch] President of India: 5 in-window (of 21 entries, 0 malformed skipped)
[01_source_fetch] Election Commission of India: 2 in-window (of 10 entries, 0 malformed skipped)
[01_source_fetch] UPSC: 0 in-window (of 4 entries, 0 malformed skipped)
[01_source_fetch] The Hindu: 24 in-window (of 60 entries, 0 malformed skipped)
[01_source_fetch] Business Standard: 125 in-window (of 125 entries, 0 malformed skipped)
[01_source_fetch] Mint: 35 in-window (of 35 entries, 0 malformed skipped)
[01_source_fetch] Economic Times: 6 in-window (of 76 entries, 0 malformed skipped)
[01_source_fetch] Google News India: 36 in-window (of 38 entries, 0 malformed skipped)
[01_source_fetch] Google News Search: 97 in-window (of 100 entries, 0 malformed skipped)
[01_source_fetch] wrote /home/runner/work/daily-current-affairs/daily-current-affairs/data/raw/daily_2026-10-16.json (574 articles, 52/57 feeds ok)
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
2026-10-16 12:03:29 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:29 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:29 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:29 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:29 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:29 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:30 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:31 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:31 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:31 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:03:31 | INFO     | agent.04_fact_verification | Verification complete in 53.1s | 574 total | 574 passed | 0 rejected | 0 crashed
2026-10-16 12:03:31 | INFO     | agent.04_fact_verification | Avg confidence: 0.545
2026-10-16 12:03:31 | INFO     | agent.04_fact_verification | Methods: {'heuristic+cross_source': 558, 'combined': 16}
2026-10-16 12:03:31 | INFO     | agent.04_fact_verification | ✔ Fact verification completed: 574 items → /home/runner/work/daily-current-affairs/daily-current-affairs/data/verified/daily_2026-10-16.json
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/requests/__init__.py:113: RequestsDependencyWarning: urllib3 (2.2.3) or chardet (7.6.0)/charset_normalizer (3.4.0) doesn't match a supported version!
  warnings.warn(
```

### 05_deduplication.log

```
--- attempt 1; exit 0 ---
2026-10-16 12:03:31 | INFO     | agent.05_deduplication | Input: 574 articles from daily_2026-10-16.json
2026-10-16 12:03:31 | INFO     | agent.05_deduplication | After URL dedup: 574
2026-10-16 12:03:31 | INFO     | agent.05_deduplication | After fingerprint dedup: 481
2026-10-16 12:03:43 | INFO     | agent.05_deduplication | After similarity clustering: 458
2026-10-16 12:03:43 | INFO     | agent.05_deduplication | ✔ Dedup complete: 574 → 458 (20.2% reduction)
```

### 06_news_importance.log

```
--- attempt 1; exit 0 ---
[06_news_importance] job=daily_2026-10-16 type=daily date=2026-10-16
[06] OK — scored=458
2026-10-16 12:03:44,049 | INFO     | root | [NEWS IMPORTANCE AGENT] scored 458 events, top=33
```

### 07_student_domain_relevance.log

```
--- attempt 1; exit 0 ---
INFO:root:[STUDENT & DOMAIN RELEVANCE AGENT] relevant=42/458 agri=18 banking=5
```

### 10_final_news_selection.log

```
--- attempt 1; exit 0 ---
[10_final_news_selection] job=daily_2026-10-16 type=daily date=2026-10-16
[10] OK — selected_count=28
2026-10-16 12:03:44,173 | INFO     | root | [FINAL NEWS SELECTION AGENT v2] selected 28 items (target=28)
2026-10-16 12:03:44,173 | INFO     | root |   Agriculture: 11
2026-10-16 12:03:44,173 | INFO     | root |   National: 11
2026-10-16 12:03:44,173 | INFO     | root |   Banking & Finance: 5
2026-10-16 12:03:44,173 | INFO     | root |   Economy: 1
```

### 11_importance_memory.log

```
--- attempt 1; exit 0 ---
INFO:root:[IMPORTANCE MEMORY AGENT] memory updated for 28 events (local + persistent)
```

### 12_content_editor.log

```
2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 12:03:58 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 12:03:58 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 12:03:58 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 12:03:58 | INFO     | pipeline.content | [Content Builder] Translation stats: ai=4 fallback=121 untranslated=0 (AI success 3.2%)
2026-10-16 12:03:58 | WARNING  | pipeline.content | [Content Builder] 121 translations need review (AI did not pass)
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
2026-10-16 12:04:06 | INFO     | agent.19_pdf_qa | QA check: daily_2026-10-16.pdf
2026-10-16 12:04:06 | INFO     | agent.19_pdf_qa | QA requires at least 10 MCQs for 28 selected stories
2026-10-16 12:04:06 | INFO     | agent.19_pdf_qa | Report: /home/runner/work/daily-current-affairs/daily-current-affairs/logs/qa/daily_2026-10-16_qa.json
========================================================================
PDF QA REPORT — ✅ PASSED
========================================================================
File:            /home/runner/work/daily-current-affairs/daily-current-affairs/output/daily_2026-10-16.pdf
Size:            8807 KB
Pages:           34
Chars:           57998
Devanagari:      3787 (6.5%)
Fonts:           6 (AAAAAA+Mukta-Bold, AAAAAA+Mukta-Regular, AAAAAA+Poppins-Bold...)
MCQs:            15
Answer markers:  14
Duplicate Qs:    0
URLs:            28
Images:          257
Blank pages:     none
--- Issues ---
  ⚠️  [low_hindi] Hindi coverage 6.5% is low
  ⚠️  [text_overflow] Text may overflow page bounds on pages: [7, 9]
========================================================================
2026-10-16 12:04:06 | INFO     | agent.19_pdf_qa | ✔ PDF QA passed — safe to publish
```

### 22_telegram_publisher.log

```
--- attempt 1; exit 0 ---
2026-10-16 12:04:06 | INFO     | agent.22_telegram_publisher | Found 1 candidate PDF(s) (max 5 per run)
2026-10-16 12:04:06 | WARNING  | agent.22_telegram_publisher | Adopted 10 unverifiable legacy publication row(s) as history
2026-10-16 12:04:06 | INFO     | agent.22_telegram_publisher | [1/1] daily_2026-10-16.pdf
2026-10-16 12:04:06 | INFO     | agent.22_telegram_publisher | [DRY-RUN] Would publish daily_2026-10-16.pdf (9019271 bytes) with caption:
<b>&gt;&gt; Policy Coordination – Department of Agriculture and Farmers’ Welfare</b>
&lt;a href="https://news.google.com/rss/articles/CBMiZkFVX3lxTE00NXJ3UmNMdHhNNzdVenZYRjliMFpDVnZWcHhTbHRZT092a1dxU
2026-10-16 12:04:06 | INFO     | agent.22_telegram_publisher | Publishing complete: success=1 failed=0 skipped=0 total=1
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/requests/__init__.py:113: RequestsDependencyWarning: urllib3 (2.2.3) or chardet (7.6.0)/charset_normalizer (3.4.0) doesn't match a supported version!
  warnings.warn(
```

### 23_telegram_pin_verifier.log

```
--- attempt 1; exit 0 ---
2026-10-16 12:04:06 | INFO     | agent.23_telegram_pin_verifier | [DRY-RUN] No live publication receipt to pin.
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/requests/__init__.py:113: RequestsDependencyWarning: urllib3 (2.2.3) or chardet (7.6.0)/charset_normalizer (3.4.0) doesn't match a supported version!
  warnings.warn(
```

### 24_final_health_audit.log

```
--- attempt 1; exit 0 ---
{"job_id": "daily_2026-10-16", "passed": true, "dry_run": true, "issues": [], "checked_at": "2026-10-16T12:04:06.870232+00:00"}
```

### telegram_publisher.log

```
2026-10-16 12:04:06 | INFO     | agent.22_telegram_publisher | Found 1 candidate PDF(s) (max 5 per run)
2026-10-16 12:04:06 | WARNING  | agent.22_telegram_publisher | Adopted 10 unverifiable legacy publication row(s) as history
2026-10-16 12:04:06 | INFO     | agent.22_telegram_publisher | [1/1] daily_2026-10-16.pdf
2026-10-16 12:04:06 | INFO     | agent.22_telegram_publisher | [DRY-RUN] Would publish daily_2026-10-16.pdf (9019271 bytes) with caption:
<b>&gt;&gt; Policy Coordination – Department of Agriculture and Farmers’ Welfare</b>
&lt;a href="https://news.google.com/rss/articles/CBMiZkFVX3lxTE00NXJ3UmNMdHhNNzdVenZYRjliMFpDVnZWcHhTbHRZT092a1dxU
2026-10-16 12:04:06 | INFO     | agent.22_telegram_publisher | Publishing complete: success=1 failed=0 skipped=0 total=1
```

## Committed state on this branch at collection time

```json
{
 "status": "success",
 "dry_run": true,
 "last_success_stage": "24_final_health_audit",
 "failed_stage": null,
 "checkpoint_run_id": "38896579675",
 "last_error": null
}
```
