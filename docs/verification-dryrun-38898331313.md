# Dry-run evidence — run 38898331313

- run URL: https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/38898331313
- edition: 2026-10-16 (DRY_RUN=1)

## Article counts

| stage | count |
|---|---|
| raw | 538 |
| verified | 538 |
| dedup | 432 |
| scored | 24 |
| selected | 24 |
| content | 24 |
| mcq | 15 |

## Category distribution per stage (raw keys here = normalisation missing)

- raw: ```{"agriculture": 1, "national": 60, "agriculture_core": 5, "banking_finance": 8, "economy_data": 6, "food_safety": 11, "govt_national": 73, "science": 1, "defence_science": 51, "discovery": 192, "aggregator": 130}```

## Selected items

- [30/55] Agriculture: AGRICULTURE TRADE POLICY, PROMOTION AND LOGISTICS DEVELOPMENT DIVISION - Department of Agr
- [22/47] Banking & Finance: - Reserve Bank of India
- [30/38] National: Don't bulldoze delimitation Bill again, call all-party meet: Kharge to Modi
- [22/47] Agriculture: Photos - Department of Agriculture & Farmers Welfare
- [20/45] Banking & Finance: International Financial Services Centres Authority - International Financial Services Cent
- [28/36] National: South Indian Bank aims 16% loan growth in FY27 amid West Asia war risks
- [22/47] Agriculture: प्रभाि-आधाररत पूिाानुमान और चेतािननयााँ/Impact Based Fore - IMD
- [28/36] National: India GDP to grow 7.1-7.3% in FY27 on private investment revival: Deloitte
- [22/47] Agriculture: Synoptic observations Significant Weather Rainfall(cm) Maximum Temperature No Large Change
- [27/35] National: India wants to push rupee trade to help forex-starved nations: Sitharaman
- [22/47] Agriculture: STATE FORECAST DETAILED FORECAST AND WARNINGS: - IMD
- [26/34] National: Trump's US investment tracker: India ranks 6th with $500 billion, UAE leads with $1.4 tril
- [20/45] Agriculture: estic
- [25/33] National: After SC notice, BJP accuses Rahul Gandhi of ‘spreading lies and confusion’ over Form 6
- [24/32] National: Dr. Ashok Kumar Mittal leads 'Seva Sankalp', a salute to Prime Minister Modi's 25 years of
- [23/31] National: Don't try to bulldoze Bill again, call all-party meet to discuss delimitation proposals: K
- [23/31] National: Omaxe, Lemon Tree ink pact to manage 10 upcoming hotels worth ₹4,000 cr
- [23/31] National: FIFA chief Infantino apologises for World Cup row, fails to appease critics
- [22/30] National: NGT takes suo motu cognisance of gaps in govt. action over chromium contamination of U.P. 
- [22/30] National: INS Samarthak, first indigenous multi-purpose vessel, commissioned
- [22/30] National: BUCHAREST UNIVERSITY OF ECONOMIC STUDIES CONFERS HONORARY DOCTORATE ON THE PRESIDENT - www
- [22/30] National: PNGRB clears IGX platform to book unused LNG regasification capacity
- [22/30] National: IDBI Bank sale likely to close by fiscal end after RBI nod: Dipam secy
- [22/30] National: Rupee rises 20 paise to 94.79 against US dollar during early trade

## PDF qa report

```json
{
  "pdf_path": "/home/runner/work/daily-current-affairs/daily-current-affairs/output/daily_2026-10-16.pdf",
  "checked_at": "2026-10-16T12:10:02.742860+00:00",
  "passed": true,
  "page_count": 34,
  "file_size_bytes": 9237625,
  "devanagari_chars": 4226,
  "total_chars": 58774,
  "hindi_pct": 7.19,
  "font_names": [
    "AAAAAA+Mukta-Bold",
    "AAAAAA+Mukta-Regular",
    "AAAAAA+Poppins-Bold",
    "AAAAAA+Poppins-Regular",
    "AAAAAA+Poppins-SemiBold",
    "Helvetica"
  ],
  "mcq_count": 16,
  "answers_found": 20,
  "duplicate_questions": 0,
  "urls_found": 14,
  "blank_pages": [],
  "image_xobjects": 245,
  "issues": [
    {
      "severity": "warning",
      "code": "low_hindi",
      "message": "Hindi coverage 7.2% is low",
      "details": {
        "hindi_pct": 7.19
      }
    }
  ],
  "job_id": "daily_2026-10-16",
  "file_sha256": "0d9f3d5523c9178faad95d1dd73314e6190488ebedd9d8828244e8a563e3a2ca"
}
```

## PDF health report

```json
{
  "job_id": "daily_2026-10-16",
  "passed": true,
  "dry_run": true,
  "issues": [],
  "checked_at": "2026-10-16T12:10:03.325463+00:00"
}
```

## Stage log inventory

| log | lines | first | last |
|---|---|---|---|
| content_editor.log | 663 | 2026-10-16 12:09:28 | 2026-10-16 12:09:47 |
| deduplication.log | 5 | 2026-10-16 12:09:06 | 2026-10-16 12:09:28 |
| fact_verification.log | 556 | 2026-10-16 12:08:04 | 2026-10-16 12:09:06 |
| orchestrator_00.log | 10 | 2026-10-16 12:07:41 | 2026-10-16 12:07:44 |
| pdf_qa.log | 4 | 2026-10-16 12:10:02 | 2026-10-16 12:10:02 |
| pin_verifier.log | 1 | 2026-10-16 12:10:03 | 2026-10-16 12:10:03 |
| 00_model_orchestrator.log | 13 | --- attempt 1; exit |   warnings.warn( |
| 01_source_fetch.log | 61 | --- attempt 1; exit | [01_source_fetch] W |
| 04_fact_verification.log | 559 | --- attempt 1; exit |   warnings.warn( |
| 05_deduplication.log | 6 | --- attempt 1; exit | 2026-10-16 12:09:28 |
| 06_news_importance.log | 4 | --- attempt 1; exit | 2026-10-16 12:09:28 |
| 07_student_domain_relevance.log | 2 | --- attempt 1; exit | INFO:root:[STUDENT  |
| 10_final_news_selection.log | 7 | --- attempt 1; exit | 2026-10-16 12:09:28 |
| 11_importance_memory.log | 2 | --- attempt 1; exit | INFO:root:[IMPORTAN |
| 12_content_editor.log | 666 | --- attempt 1; exit |   warnings.warn( |
| 16_mcq_generator.log | 7 | --- attempt 1; exit | INFO:root:[MCQ GENE |
| 17_mcq_validator.log | 6 | --- attempt 1; exit | INFO:root:[MCQ VALI |
| 18_pdf_design.log | 3 | --- attempt 1; exit | [OK] PDF generated: |
| 19_pdf_qa.log | 23 | --- attempt 1; exit | 2026-10-16 12:10:02 |
| 22_telegram_publisher.log | 10 | --- attempt 1; exit |   warnings.warn( |
| 23_telegram_pin_verifier.log | 4 | --- attempt 1; exit |   warnings.warn( |
| 24_final_health_audit.log | 2 | --- attempt 1; exit | {"job_id": "daily_2 |
| telegram_publisher.log | 7 | 2026-10-16 12:10:03 | 2026-10-16 12:10:03 |

## Log excerpts (retries / skips / QA)

```
content_editor.log: 2026-10-16 12:09:28 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-16 12:09:29 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ["missing acronyms: ['DIVISION', 'AND', 'POLICY']"]
content_editor.log: 2026-10-16 12:09:30 | WARNING  | pipeline.ai_translator | [Translator] openrouter parked for 900s (HTTP 402)
content_editor.log: 2026-10-16 12:09:30 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-16 12:09:30 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['gemini: rate limited', 'groq: validation failed', 'openrouter: HTTP 402', 'mistral: rate limited'])
content_editor.log: 2026-10-16 12:09:31 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ['unusual length ratio 0.40']
content_editor.log: 2026-10-16 12:09:31 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['groq: validation failed'])
content_editor.log: 2026-10-16 12:09:32 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ["missing acronyms: ['DIVISION', 'AND', 'POLICY']"]
content_editor.log: 2026-10-16 12:09:32 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['groq: validation failed'])
content_editor.log: 2026-10-16 12:09:33 | WARNING  | pipeline.ai_router | [Router] gemini HTTP 429 (rate_limit): {
content_editor.log: 2026-10-16 12:09:33 | WARNING  | pipeline.ai_router | [Router] Provider gemini disabled for 120s: rate limited
content_editor.log: 2026-10-16 12:09:42 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ["missing numbers: ['64 days']"]
content_editor.log: 2026-10-16 12:09:42 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['groq: validation failed'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.ai_router | [Router] groq HTTP 429 (rate_limit): {"error":{"message":"Rate limit reached for model `openai/gpt-oss-120b` in organization `org_01m4n8hsfce0q8z1yndppr2nmv` service 
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.ai_router | [Router] Provider groq disabled for 120s: rate limited
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.ai_router | [Router] openrouter HTTP 402 (auth_error): {"error":{"message":"This request requires more credits, or fewer max_tokens. You requested up to 16384 tokens, but can onl
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.ai_router | [Router] Provider openrouter disabled for 3600s: auth error
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.ai_router | [Router] mistral HTTP 429 (rate_limit): {"object":"error","message":"Rate limit exceeded","type":"rate_limited","param":null,"code":"1300","raw_status_code":429}
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.ai_router | [Router] Provider mistral disabled for 120s: rate limited
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: mistral: rate_limit
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.ai_translator | [Translator] groq rate-limited (429)
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['groq: rate limited'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 12:09:47 | WARNING  | pipeline.content | [Content Builder] 105 translations need review (AI did not pass)
fact_verification.log: 2026-10-16 12:08:04 | WARNING  | pipeline.ai_router | [Router] gemini HTTP 429 (rate_limit): {
fact_verification.log: 2026-10-16 12:08:04 | WARNING  | pipeline.ai_router | [Router] Provider gemini disabled for 120s: rate limited
fact_verification.log: 2026-10-16 12:08:23 | WARNING  | pipeline.ai_router | [Router] groq HTTP 429 (rate_limit): {"error":{"message":"Rate limit reached for model `openai/gpt-oss-120b` in organization `org_01m4n8hsfce0q8z1yndppr2nmv` service 
fact_verification.log: 2026-10-16 12:08:23 | WARNING  | pipeline.ai_router | [Router] Provider groq disabled for 120s: rate limited
fact_verification.log: 2026-10-16 12:08:23 | WARNING  | pipeline.ai_router | [Router] openrouter HTTP 402 (auth_error): {"error":{"message":"This request requires more credits, or fewer max_tokens. You requested up to 16384 tokens, but can onl
fact_verification.log: 2026-10-16 12:08:23 | WARNING  | pipeline.ai_router | [Router] Provider openrouter disabled for 3600s: auth error
fact_verification.log: 2026-10-16 12:08:23 | WARNING  | pipeline.ai_router | [Router] mistral HTTP 429 (rate_limit): {"object":"error","message":"Rate limit exceeded","type":"rate_limited","param":null,"code":"1300","raw_status_code":429}
fact_verification.log: 2026-10-16 12:08:23 | WARNING  | pipeline.ai_router | [Router] Provider mistral disabled for 120s: rate limited
fact_verification.log: 2026-10-16 12:08:23 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: mistral: rate_limit
fact_verification.log: 2026-10-16 12:08:23 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:24 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:24 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:24 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:24 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:24 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:24 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:24 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:24 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:24 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:26 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:26 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:26 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:26 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:26 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:26 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:26 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:26 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:26 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:27 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:27 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:27 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:27 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:27 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:27 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:27 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:27 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:27 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:27 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:28 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:30 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:30 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:30 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:30 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:30 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:30 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:30 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:30 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:30 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:30 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:30 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:30 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:30 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:30 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:31 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:31 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:31 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:31 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:31 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:31 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 12:08:31 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
```

## Stage log tails

### content_editor.log

```
2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 12:09:47 | INFO     | pipeline.content | [Content Builder] Translation stats: ai=10 fallback=105 untranslated=0 (AI success 8.7%)
2026-10-16 12:09:47 | WARNING  | pipeline.content | [Content Builder] 105 translations need review (AI did not pass)
```

### deduplication.log

```
2026-10-16 12:09:06 | INFO     | agent.05_deduplication | Input: 538 articles from daily_2026-10-16.json
2026-10-16 12:09:06 | INFO     | agent.05_deduplication | After URL dedup: 538
2026-10-16 12:09:06 | INFO     | agent.05_deduplication | After fingerprint dedup: 447
2026-10-16 12:09:28 | INFO     | agent.05_deduplication | After similarity clustering: 432
2026-10-16 12:09:28 | INFO     | agent.05_deduplication | ✔ Dedup complete: 538 → 432 (19.7% reduction)
```

### fact_verification.log

```
2026-10-16 12:09:03 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:04 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:04 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:04 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:04 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:04 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:04 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:04 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:04 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:04 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:04 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:04 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:04 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:04 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:04 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:05 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:05 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:05 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:05 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:05 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:05 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:05 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:05 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:05 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:05 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:05 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:05 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:05 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:06 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:06 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:06 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:06 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:06 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:06 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:06 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:06 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:06 | INFO     | agent.04_fact_verification | Verification complete in 62.2s | 538 total | 538 passed | 0 rejected | 0 crashed
2026-10-16 12:09:06 | INFO     | agent.04_fact_verification | Avg confidence: 0.546
2026-10-16 12:09:06 | INFO     | agent.04_fact_verification | Methods: {'combined': 17, 'heuristic+cross_source': 521}
2026-10-16 12:09:06 | INFO     | agent.04_fact_verification | ✔ Fact verification completed: 538 items → /home/runner/work/daily-current-affairs/daily-current-affairs/data/verified/daily_2026-10-16.json
```

### orchestrator_00.log

```
2026-10-16 12:07:41 | INFO     | agent.00_model_orchestrator | Model orchestrator starting
2026-10-16 12:07:41 | INFO     | agent.00_model_orchestrator | Checking gemini (model=gemini-flash-latest)
2026-10-16 12:07:42 | INFO     | agent.00_model_orchestrator |   ❌ gemini → http_error
2026-10-16 12:07:42 | INFO     | agent.00_model_orchestrator | Checking groq (model=openai/gpt-oss-120b)
2026-10-16 12:07:42 | INFO     | agent.00_model_orchestrator |   ❌ groq → malformed
2026-10-16 12:07:42 | INFO     | agent.00_model_orchestrator | Checking openrouter (model=openai/gpt-4o-mini)
2026-10-16 12:07:44 | INFO     | agent.00_model_orchestrator |   ✅ openrouter → ok
2026-10-16 12:07:44 | INFO     | agent.00_model_orchestrator | Checking mistral (model=mistral-small-latest)
2026-10-16 12:07:44 | INFO     | agent.00_model_orchestrator |   ❌ mistral → rate_limit
2026-10-16 12:07:44 | INFO     | agent.00_model_orchestrator | Model status: 1/4 healthy → /home/runner/work/daily-current-affairs/daily-current-affairs/state/model_status.json
```

### pdf_design.log

```
```

### pdf_qa.log

```
2026-10-16 12:10:02 | INFO     | agent.19_pdf_qa | QA check: daily_2026-10-16.pdf
2026-10-16 12:10:02 | INFO     | agent.19_pdf_qa | QA requires at least 10 MCQs for 24 selected stories
2026-10-16 12:10:02 | INFO     | agent.19_pdf_qa | Report: /home/runner/work/daily-current-affairs/daily-current-affairs/logs/qa/daily_2026-10-16_qa.json
2026-10-16 12:10:02 | INFO     | agent.19_pdf_qa | ✔ PDF QA passed — safe to publish
```

### pin_verifier.log

```
2026-10-16 12:10:03 | INFO     | agent.23_telegram_pin_verifier | [DRY-RUN] No live publication receipt to pin.
```

### 00_model_orchestrator.log

```
--- attempt 1; exit 0 ---
2026-10-16 12:07:41 | INFO     | agent.00_model_orchestrator | Model orchestrator starting
2026-10-16 12:07:41 | INFO     | agent.00_model_orchestrator | Checking gemini (model=gemini-flash-latest)
2026-10-16 12:07:42 | INFO     | agent.00_model_orchestrator |   ❌ gemini → http_error
2026-10-16 12:07:42 | INFO     | agent.00_model_orchestrator | Checking groq (model=openai/gpt-oss-120b)
2026-10-16 12:07:42 | INFO     | agent.00_model_orchestrator |   ❌ groq → malformed
2026-10-16 12:07:42 | INFO     | agent.00_model_orchestrator | Checking openrouter (model=openai/gpt-4o-mini)
2026-10-16 12:07:44 | INFO     | agent.00_model_orchestrator |   ✅ openrouter → ok
2026-10-16 12:07:44 | INFO     | agent.00_model_orchestrator | Checking mistral (model=mistral-small-latest)
2026-10-16 12:07:44 | INFO     | agent.00_model_orchestrator |   ❌ mistral → rate_limit
2026-10-16 12:07:44 | INFO     | agent.00_model_orchestrator | Model status: 1/4 healthy → /home/runner/work/daily-current-affairs/daily-current-affairs/state/model_status.json
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/requests/__init__.py:113: RequestsDependencyWarning: urllib3 (2.2.3) or chardet (7.6.0)/charset_normalizer (3.4.0) doesn't match a supported version!
  warnings.warn(
```

### 01_source_fetch.log

```
[01_source_fetch] NPCI: 0 in-window (of 2 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] PFRDA: 0 in-window (of 12 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] IRDAI: 0 in-window (of 0 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] IFSCA: 1 in-window (of 82 entries, 0 malformed skipped, 1 chrome skipped)
[01_source_fetch] Department of Financial Services: 0 in-window (of 20 entries, 0 malformed skipped, 13 chrome skipped)
[01_source_fetch] Union Budget of India: 0 in-window (of 2 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] GST Council: 0 in-window (of 27 entries, 0 malformed skipped, 2 chrome skipped)
[01_source_fetch] Competition Commission of India: 0 in-window (of 77 entries, 0 malformed skipped, 53 chrome skipped)
[01_source_fetch] RBI Bulletin: 0 in-window (of 0 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] India.gov.in: 19 in-window (of 99 entries, 0 malformed skipped, 3 chrome skipped)
[01_source_fetch] Prime Minister of India: 5 in-window (of 25 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] Cabinet Secretariat: 0 in-window (of 1 entries, 0 malformed skipped, 1 chrome skipped)
[01_source_fetch] MyGov India: 46 in-window (of 100 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] Ministry of Rural Development: 0 in-window (of 0 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] Ministry of Cooperation: 0 in-window (of 9 entries, 0 malformed skipped, 1 chrome skipped)
[01_source_fetch] Department of Science and Technology: 1 in-window (of 100 entries, 0 malformed skipped, 20 chrome skipped)
[01_source_fetch] Department of Biotechnology: 0 in-window (of 0 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] DRDO: 51 in-window (of 100 entries, 0 malformed skipped, 2 chrome skipped)
[01_source_fetch] Central Pollution Control Board: 0 in-window (of 7 entries, 0 malformed skipped, 3 chrome skipped)
[01_source_fetch] Ministry of Education: 0 in-window (of 24 entries, 0 malformed skipped, 1 chrome skipped)
[01_source_fetch] UGC: 0 in-window (of 1 entries, 0 malformed skipped, 1 chrome skipped)
[01_source_fetch] National Testing Agency: 0 in-window (of 0 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] Ministry of Defence: 0 in-window (of 13 entries, 0 malformed skipped, 3 chrome skipped)
[01_source_fetch] President of India: 3 in-window (of 21 entries, 0 malformed skipped, 3 chrome skipped)
[01_source_fetch] Election Commission of India: 0 in-window (of 10 entries, 0 malformed skipped, 9 chrome skipped)
[01_source_fetch] UPSC: 0 in-window (of 4 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] The Hindu: 26 in-window (of 60 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] Business Standard: 125 in-window (of 125 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] Mint: 35 in-window (of 35 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] Economic Times: 6 in-window (of 76 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] Google News India: 35 in-window (of 38 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] Google News Search: 95 in-window (of 100 entries, 0 malformed skipped, 3 chrome skipped)
[01_source_fetch] wrote /home/runner/work/daily-current-affairs/daily-current-affairs/data/raw/daily_2026-10-16.json (538 articles, 52/57 feeds ok, 170 chrome skipped)
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
2026-10-16 12:09:04 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:04 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:04 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:04 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:04 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:04 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:04 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:04 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:04 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:04 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:04 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:04 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:04 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:05 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:05 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:05 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:05 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:05 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:05 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:05 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:05 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:05 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:05 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:05 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:05 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:05 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:06 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:06 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:06 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:06 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:06 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:06 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:06 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:06 | ERROR    | pipeline.ai_router | [Router] Hourly budget exceeded (500 calls)
2026-10-16 12:09:06 | INFO     | agent.04_fact_verification | Verification complete in 62.2s | 538 total | 538 passed | 0 rejected | 0 crashed
2026-10-16 12:09:06 | INFO     | agent.04_fact_verification | Avg confidence: 0.546
2026-10-16 12:09:06 | INFO     | agent.04_fact_verification | Methods: {'combined': 17, 'heuristic+cross_source': 521}
2026-10-16 12:09:06 | INFO     | agent.04_fact_verification | ✔ Fact verification completed: 538 items → /home/runner/work/daily-current-affairs/daily-current-affairs/data/verified/daily_2026-10-16.json
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/requests/__init__.py:113: RequestsDependencyWarning: urllib3 (2.2.3) or chardet (7.6.0)/charset_normalizer (3.4.0) doesn't match a supported version!
  warnings.warn(
```

### 05_deduplication.log

```
--- attempt 1; exit 0 ---
2026-10-16 12:09:06 | INFO     | agent.05_deduplication | Input: 538 articles from daily_2026-10-16.json
2026-10-16 12:09:06 | INFO     | agent.05_deduplication | After URL dedup: 538
2026-10-16 12:09:06 | INFO     | agent.05_deduplication | After fingerprint dedup: 447
2026-10-16 12:09:28 | INFO     | agent.05_deduplication | After similarity clustering: 432
2026-10-16 12:09:28 | INFO     | agent.05_deduplication | ✔ Dedup complete: 538 → 432 (19.7% reduction)
```

### 06_news_importance.log

```
--- attempt 1; exit 0 ---
[06_news_importance] job=daily_2026-10-16 type=daily date=2026-10-16
[06] OK — scored=432
2026-10-16 12:09:28,227 | INFO     | root | [NEWS IMPORTANCE AGENT] scored 432 events, top=30
```

### 07_student_domain_relevance.log

```
--- attempt 1; exit 0 ---
INFO:root:[STUDENT & DOMAIN RELEVANCE AGENT] relevant=24/432 agri=6 banking=2
```

### 10_final_news_selection.log

```
--- attempt 1; exit 0 ---
[10_final_news_selection] job=daily_2026-10-16 type=daily date=2026-10-16
[10] OK — selected_count=24
2026-10-16 12:09:28,417 | INFO     | root | [FINAL NEWS SELECTION AGENT v2] selected 24 items (target=28)
2026-10-16 12:09:28,417 | INFO     | root |   National: 16
2026-10-16 12:09:28,417 | INFO     | root |   Agriculture: 6
2026-10-16 12:09:28,417 | INFO     | root |   Banking & Finance: 2
```

### 11_importance_memory.log

```
--- attempt 1; exit 0 ---
INFO:root:[IMPORTANCE MEMORY AGENT] memory updated for 24 events (local + persistent)
```

### 12_content_editor.log

```
2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 12:09:47 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 12:09:47 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 12:09:47 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 12:09:47 | INFO     | pipeline.content | [Content Builder] Translation stats: ai=10 fallback=105 untranslated=0 (AI success 8.7%)
2026-10-16 12:09:47 | WARNING  | pipeline.content | [Content Builder] 105 translations need review (AI did not pass)
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/requests/__init__.py:113: RequestsDependencyWarning: urllib3 (2.2.3) or chardet (7.6.0)/charset_normalizer (3.4.0) doesn't match a supported version!
  warnings.warn(
```

### 16_mcq_generator.log

```
--- attempt 1; exit 0 ---
INFO:root:[MCQ GENERATOR AGENT v4 (FAIL-CLOSED)] Generating MCQs for 24 items...
INFO:root:[MCQ GENERATOR AGENT v4 (FAIL-CLOSED)] Generated 15 raw MCQs
INFO:root:[MCQ GENERATOR AGENT v4 (FAIL-CLOSED)] Running mcq_validator (FAIL-CLOSED)...
INFO:pipeline.content:[MCQ Validation] 15/15 MCQs passed (0 rejected)
INFO:root:[MCQ GENERATOR AGENT v4 (FAIL-CLOSED)] Validation: 15/15 passed (0 rejected)
INFO:root:[MCQ GENERATOR AGENT v4 (FAIL-CLOSED)] ✓ Final: 15 VALIDATED MCQs using mcq_validator_v2
```

### 17_mcq_validator.log

```
--- attempt 1; exit 0 ---
INFO:root:[MCQ VALIDATOR AGENT v4 (FAIL-CLOSED)] Validating 15 MCQs from Agent 16...
INFO:root:[MCQ VALIDATOR AGENT v4 (FAIL-CLOSED)] Running mcq_validator (FAIL-CLOSED)...
INFO:pipeline.content:[MCQ Validation] 15/15 MCQs passed (0 rejected)
INFO:root:[MCQ VALIDATOR AGENT v4 (FAIL-CLOSED)] Validation: 15/15 passed (0 rejected)
INFO:root:[MCQ VALIDATOR AGENT v4 (FAIL-CLOSED)] ✓ Final: 15 VALIDATED MCQs using mcq_validator_v2
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
2026-10-16 12:10:02 | INFO     | agent.19_pdf_qa | QA check: daily_2026-10-16.pdf
2026-10-16 12:10:02 | INFO     | agent.19_pdf_qa | QA requires at least 10 MCQs for 24 selected stories
2026-10-16 12:10:02 | INFO     | agent.19_pdf_qa | Report: /home/runner/work/daily-current-affairs/daily-current-affairs/logs/qa/daily_2026-10-16_qa.json
========================================================================
PDF QA REPORT — ✅ PASSED
========================================================================
File:            /home/runner/work/daily-current-affairs/daily-current-affairs/output/daily_2026-10-16.pdf
Size:            9021 KB
Pages:           34
Chars:           58774
Devanagari:      4226 (7.2%)
Fonts:           6 (AAAAAA+Mukta-Bold, AAAAAA+Mukta-Regular, AAAAAA+Poppins-Bold...)
MCQs:            16
Answer markers:  20
Duplicate Qs:    0
URLs:            14
Images:          245
Blank pages:     none
--- Issues ---
  ⚠️  [low_hindi] Hindi coverage 7.2% is low
========================================================================
2026-10-16 12:10:02 | INFO     | agent.19_pdf_qa | ✔ PDF QA passed — safe to publish
```

### 22_telegram_publisher.log

```
--- attempt 1; exit 0 ---
2026-10-16 12:10:03 | INFO     | agent.22_telegram_publisher | Found 1 candidate PDF(s) (max 5 per run)
2026-10-16 12:10:03 | WARNING  | agent.22_telegram_publisher | Adopted 10 unverifiable legacy publication row(s) as history
2026-10-16 12:10:03 | INFO     | agent.22_telegram_publisher | [1/1] daily_2026-10-16.pdf
2026-10-16 12:10:03 | INFO     | agent.22_telegram_publisher | [DRY-RUN] Would publish daily_2026-10-16.pdf (9237625 bytes) with caption:
<b>&gt;&gt; Agriculture Trade Policy, Promotion, and Logistics Development Division – Department of Agriculture and Farmers’ Welfare</b>
&lt;a href="https://news.google.com/rss/articles/CBMia0FVX3lxT
2026-10-16 12:10:03 | INFO     | agent.22_telegram_publisher | Publishing complete: success=1 failed=0 skipped=0 total=1
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/requests/__init__.py:113: RequestsDependencyWarning: urllib3 (2.2.3) or chardet (7.6.0)/charset_normalizer (3.4.0) doesn't match a supported version!
  warnings.warn(
```

### 23_telegram_pin_verifier.log

```
--- attempt 1; exit 0 ---
2026-10-16 12:10:03 | INFO     | agent.23_telegram_pin_verifier | [DRY-RUN] No live publication receipt to pin.
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/requests/__init__.py:113: RequestsDependencyWarning: urllib3 (2.2.3) or chardet (7.6.0)/charset_normalizer (3.4.0) doesn't match a supported version!
  warnings.warn(
```

### 24_final_health_audit.log

```
--- attempt 1; exit 0 ---
{"job_id": "daily_2026-10-16", "passed": true, "dry_run": true, "issues": [], "checked_at": "2026-10-16T12:10:03.325463+00:00"}
```

### telegram_publisher.log

```
2026-10-16 12:10:03 | INFO     | agent.22_telegram_publisher | Found 1 candidate PDF(s) (max 5 per run)
2026-10-16 12:10:03 | WARNING  | agent.22_telegram_publisher | Adopted 10 unverifiable legacy publication row(s) as history
2026-10-16 12:10:03 | INFO     | agent.22_telegram_publisher | [1/1] daily_2026-10-16.pdf
2026-10-16 12:10:03 | INFO     | agent.22_telegram_publisher | [DRY-RUN] Would publish daily_2026-10-16.pdf (9237625 bytes) with caption:
<b>&gt;&gt; Agriculture Trade Policy, Promotion, and Logistics Development Division – Department of Agriculture and Farmers’ Welfare</b>
&lt;a href="https://news.google.com/rss/articles/CBMia0FVX3lxT
2026-10-16 12:10:03 | INFO     | agent.22_telegram_publisher | Publishing complete: success=1 failed=0 skipped=0 total=1
```

## Committed state on this branch at collection time

```json
{
 "status": "success",
 "dry_run": true,
 "last_success_stage": "24_final_health_audit",
 "failed_stage": null,
 "checkpoint_run_id": "38897677177",
 "last_error": null
}
```
