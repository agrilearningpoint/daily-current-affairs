# Dry-run evidence — run 38904929697

- run URL: https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/38904929697
- edition: 2026-10-15 (DRY_RUN=1)

## Article counts

| stage | count |
|---|---|
| raw | 46 |
| verified | 46 |
| dedup | 41 |
| scored | 8 |
| selected | 8 |
| content | 8 |
| mcq | 15 |

## Category distribution per stage (raw keys here = normalisation missing)

- raw: ```{"banking_finance": 1, "economy_data": 4, "agriculture_core": 2, "food_safety": 1, "govt_national": 26, "cooperation": 1, "science": 5, "defence_science": 4, "education": 1, "aggregator": 1}```

## Selected items

- [23/48] Agriculture: io'> - dof.gov.in | https://news.google.com/rss/articles/CBMihAFBVV95cUxQSkFOR2JfdnU3ZTNXZ2FEem1DaWZlMFVtVHJjNGZNQWFyUUtOTzBmT2hkc1FRWWlGTWl
- [23/48] Banking & Finance: Engagement of Pharmacist in the Bank on contract basis with fixed hourly remuneration, Mum | https://news.google.com/rss/articles/CBMiZ0FVX3lxTE54bVZjM3dQaTRyRGpzVi1hZS1iLUM0dVVnUmF5RHV1YU41SWpMYTZ3T2U5SXZNNXZBNDh
- [17/32] Economy: Data Centre Evaluation Framework to Help States Plan for Sustainable Growth | http://www.niti.gov.in/node/2443
- [24/32] National: Cabinet approves Productivity Linked Bonus (PLB) for 78 days to Railway Employees - PM Ind | https://news.google.com/rss/articles/CBMiwAFBVV95cUxQYURXV3A0dnFKU0dQM3RfS0hmRzE4Sk5IZGhfdHJoMDVQZU9ZOVE1OFU2SkllLWdaY3V
- [22/47] Agriculture: https://mausam.imd.gov.in/bhubaneswar/ Agromet Advisory Service Bulletin for the State of  | https://news.google.com/rss/articles/CBMiakFVX3lxTE41VlJtNVdDTEFWc3kwbWZLbW9KN2loa05vMWxSaWZLbWU0R2JXdkRucVoxaTFwaGY0REt
- [15/30] Economy: General Statement The Competition Commission of India (Settlement) Regulations, 2024 1. Th | https://news.google.com/rss/articles/CBMivwFBVV95cUxOUnJGUFNGT2VrT3FKMWZBR0U5Q3pkV1lVNHZ0YS0xRDg0d19aaTFReXFkdTB1cEo1RHd
- [23/31] National: Cabinet approves continuation of the National Social Assistance Programme for five years f | https://news.google.com/rss/articles/CBMi7AFBVV95cUxPM1ZqODh6RTFZSnY1eWV3Tjd6bDJGU3p3cjJlZ25LWDBzZ0hyZzFmYVZ2VTEyc2pfQW8
- [20/45] Agriculture: Instructions given to expedite the computerization of PACS - Ministry of Cooperation | https://news.google.com/rss/articles/CBMiowFBVV95cUxQSjZYWHNsS1BnM3pSVkhERXktbDluNW5sRzlHbmZYWjdVQU52c3p3dHlzUnJ2WEVtVlF

## PDF qa report

```json
{
  "pdf_path": "/home/runner/work/daily-current-affairs/daily-current-affairs/output/daily_2026-10-15.pdf",
  "checked_at": "2026-10-16T13:04:35.020234+00:00",
  "passed": true,
  "page_count": 19,
  "file_size_bytes": 4903641,
  "devanagari_chars": 1767,
  "total_chars": 32373,
  "hindi_pct": 5.46,
  "font_names": [
    "AAAAAA+Mukta-Bold",
    "AAAAAA+Mukta-Regular",
    "AAAAAA+Poppins-Bold",
    "AAAAAA+Poppins-Regular",
    "AAAAAA+Poppins-SemiBold",
    "Helvetica"
  ],
  "mcq_count": 17,
  "answers_found": 15,
  "duplicate_questions": 0,
  "urls_found": 58,
  "blank_pages": [],
  "image_xobjects": 111,
  "issues": [
    {
      "severity": "warning",
      "code": "low_hindi",
      "message": "Hindi coverage 5.5% is low",
      "details": {
        "hindi_pct": 5.46
      }
    },
    {
      "severity": "warning",
      "code": "text_overflow",
      "message": "Text may overflow page bounds on pages: [6, 18]",
      "details": {
        "pages": [
          6,
          18
        ]
      }
    }
  ],
  "job_id": "daily_2026-10-15",
  "file_sha256": "7c0d127dd24a144956bd6132edf467b7bfce33ff0915e4de0092342de9eaca0e"
}
```

## PDF health report

```json
{
  "job_id": "daily_2026-10-15",
  "passed": true,
  "dry_run": true,
  "issues": [],
  "checked_at": "2026-10-16T13:04:35.502798+00:00"
}
```

## Stage log inventory

| log | lines | first | last |
|---|---|---|---|
| content_editor.log | 238 | 2026-10-16 13:04:26 | 2026-10-16 13:04:29 |
| deduplication.log | 5 | 2026-10-16 13:04:25 | 2026-10-16 13:04:26 |
| fact_verification.log | 64 | 2026-10-16 13:04:13 | 2026-10-16 13:04:25 |
| orchestrator_00.log | 10 | 2026-10-16 13:03:49 | 2026-10-16 13:03:51 |
| pdf_qa.log | 4 | 2026-10-16 13:04:35 | 2026-10-16 13:04:35 |
| pin_verifier.log | 1 | 2026-10-16 13:04:35 | 2026-10-16 13:04:35 |
| 00_model_orchestrator.log | 13 | --- attempt 1; exit |   warnings.warn( |
| 01_source_fetch.log | 61 | --- attempt 1; exit | [01_source_fetch] W |
| 04_fact_verification.log | 67 | --- attempt 1; exit |   warnings.warn( |
| 05_deduplication.log | 6 | --- attempt 1; exit | 2026-10-16 13:04:26 |
| 06_news_importance.log | 4 | --- attempt 1; exit | 2026-10-16 13:04:26 |
| 07_student_domain_relevance.log | 2 | --- attempt 1; exit | INFO:root:[STUDENT  |
| 10_final_news_selection.log | 8 | --- attempt 1; exit | 2026-10-16 13:04:26 |
| 11_importance_memory.log | 2 | --- attempt 1; exit | INFO:root:[IMPORTAN |
| 12_content_editor.log | 241 | --- attempt 1; exit |   warnings.warn( |
| 16_mcq_generator.log | 7 | --- attempt 1; exit | INFO:root:[MCQ GENE |
| 17_mcq_validator.log | 6 | --- attempt 1; exit | INFO:root:[MCQ VALI |
| 18_pdf_design.log | 3 | --- attempt 1; exit | [OK] PDF generated: |
| 19_pdf_qa.log | 24 | --- attempt 1; exit | 2026-10-16 13:04:35 |
| 22_telegram_publisher.log | 10 | --- attempt 1; exit |   warnings.warn( |
| 23_telegram_pin_verifier.log | 4 | --- attempt 1; exit |   warnings.warn( |
| 24_final_health_audit.log | 2 | --- attempt 1; exit | {"job_id": "daily_2 |
| telegram_publisher.log | 7 | 2026-10-16 13:04:35 | 2026-10-16 13:04:35 |

## Log excerpts (retries / skips / QA)

```
content_editor.log: 2026-10-16 13:04:26 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-16 13:04:27 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ['no Devanagari characters']
content_editor.log: 2026-10-16 13:04:27 | WARNING  | pipeline.ai_translator | [Translator] openrouter parked for 900s (HTTP 402)
content_editor.log: 2026-10-16 13:04:27 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-16 13:04:27 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['gemini: rate limited', 'groq: validation failed', 'openrouter: HTTP 402', 'mistral: rate limited'])
content_editor.log: 2026-10-16 13:04:27 | WARNING  | pipeline.ai_translator | [Translator] groq rate-limited (429)
content_editor.log: 2026-10-16 13:04:27 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['groq: rate limited'])
content_editor.log: 2026-10-16 13:04:27 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:04:27 | WARNING  | pipeline.ai_router | [Router] gemini HTTP 429 (rate_limit): {
content_editor.log: 2026-10-16 13:04:27 | WARNING  | pipeline.ai_router | [Router] Provider gemini disabled for 120s: rate limited
content_editor.log: 2026-10-16 13:04:28 | WARNING  | pipeline.ai_router | [Router] groq HTTP 429 (rate_limit): {"error":{"message":"Rate limit reached for model `openai/gpt-oss-120b` in organization `org_01m4n8hsfce0q8z1yndppr2nmv` service 
content_editor.log: 2026-10-16 13:04:28 | WARNING  | pipeline.ai_router | [Router] Provider groq disabled for 120s: rate limited
content_editor.log: 2026-10-16 13:04:28 | WARNING  | pipeline.ai_router | [Router] openrouter HTTP 402 (auth_error): {"error":{"message":"This request requires more credits, or fewer max_tokens. You requested up to 16384 tokens, but can onl
content_editor.log: 2026-10-16 13:04:28 | WARNING  | pipeline.ai_router | [Router] Provider openrouter disabled for 3600s: auth error
content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.ai_router | [Router] mistral HTTP 429 (rate_limit): {"object":"error","message":"Rate limit exceeded","type":"rate_limited","param":null,"code":"1300","raw_status_code":429}
content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.ai_router | [Router] Provider mistral disabled for 120s: rate limited
content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: mistral: rate_limit
content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Content Builder] 37 translations need review (AI did not pass)
fact_verification.log: 2026-10-16 13:04:14 | WARNING  | pipeline.ai_router | [Router] gemini HTTP 429 (rate_limit): {
fact_verification.log: 2026-10-16 13:04:14 | WARNING  | pipeline.ai_router | [Router] Provider gemini disabled for 120s: rate limited
fact_verification.log: 2026-10-16 13:04:25 | WARNING  | pipeline.ai_router | [Router] groq HTTP 429 (rate_limit): {"error":{"message":"Rate limit reached for model `openai/gpt-oss-120b` in organization `org_01m4n8hsfce0q8z1yndppr2nmv` service 
fact_verification.log: 2026-10-16 13:04:25 | WARNING  | pipeline.ai_router | [Router] Provider groq disabled for 120s: rate limited
fact_verification.log: 2026-10-16 13:04:25 | WARNING  | pipeline.ai_router | [Router] openrouter HTTP 402 (auth_error): {"error":{"message":"This request requires more credits, or fewer max_tokens. You requested up to 16384 tokens, but can onl
fact_verification.log: 2026-10-16 13:04:25 | WARNING  | pipeline.ai_router | [Router] Provider openrouter disabled for 3600s: auth error
fact_verification.log: 2026-10-16 13:04:25 | WARNING  | pipeline.ai_router | [Router] mistral HTTP 429 (rate_limit): {"object":"error","message":"Rate limit exceeded","type":"rate_limited","param":null,"code":"1300","raw_status_code":429}
fact_verification.log: 2026-10-16 13:04:25 | WARNING  | pipeline.ai_router | [Router] Provider mistral disabled for 120s: rate limited
fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: mistral: rate_limit
fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
pdf_qa.log: 2026-10-16 13:04:35 | INFO     | agent.19_pdf_qa | QA requires at least 10 MCQs for 8 selected stories
pdf_qa.log: 2026-10-16 13:04:35 | INFO     | agent.19_pdf_qa | ✔ PDF QA passed — safe to publish
pin_verifier.log: 2026-10-16 13:04:35 | INFO     | agent.23_telegram_pin_verifier | [DRY-RUN] No live publication receipt to pin.
01_source_fetch.log: [01_source_fetch] ICAR: 0 in-window (of 10 entries, 0 malformed skipped, 4 chrome skipped)
01_source_fetch.log: [01_source_fetch] WHO News: 0 in-window (of 204 entries, 0 malformed skipped, 0 chrome skipped)
01_source_fetch.log: [01_source_fetch] The Hindu National: 0 in-window (of 60 entries, 0 malformed skipped, 0 chrome skipped)
01_source_fetch.log: [01_source_fetch] Ministry of Agriculture & Farmers Welfare: 0 in-window (of 16 entries, 0 malformed skipped, 15 chrome skipped)
01_source_fetch.log: [01_source_fetch] RBI: 1 in-window (of 55 entries, 0 malformed skipped, 50 chrome skipped)
01_source_fetch.log: [01_source_fetch] NABARD: 0 in-window (of 0 entries, 0 malformed skipped, 0 chrome skipped)
01_source_fetch.log: [01_source_fetch] NITI Aayog: 2 in-window (of 10 entries, 0 malformed skipped, 0 chrome skipped)
01_source_fetch.log: [01_source_fetch] Ministry of Statistics and Programme Implementation: 1 in-window (of 14 entries, 0 malformed skipped, 8 chrome skipped)
01_source_fetch.log: [01_source_fetch] India Meteorological Department: 1 in-window (of 100 entries, 0 malformed skipped, 23 chrome skipped)
01_source_fetch.log: [01_source_fetch] Department of Animal Husbandry and Dairying: 0 in-window (of 6 entries, 0 malformed skipped, 4 chrome skipped)
01_source_fetch.log: [01_source_fetch] Department of Fisheries: 1 in-window (of 1 entries, 0 malformed skipped, 0 chrome skipped)
01_source_fetch.log: [01_source_fetch] APEDA: 0 in-window (of 6 entries, 0 malformed skipped, 3 chrome skipped)
01_source_fetch.log: [01_source_fetch] Department of Agriculture Research and Education: 0 in-window (of 0 entries, 0 malformed skipped, 0 chrome skipped)
01_source_fetch.log: [01_source_fetch] Indian Agricultural Research Institute: 0 in-window (of 15 entries, 0 malformed skipped, 8 chrome skipped)
01_source_fetch.log: [01_source_fetch] National Horticulture Board: 0 in-window (of 1 entries, 0 malformed skipped, 1 chrome skipped)
01_source_fetch.log: [01_source_fetch] FSSAI: 1 in-window (of 100 entries, 0 malformed skipped, 92 chrome skipped)
01_source_fetch.log: [01_source_fetch] ICFRE: 0 in-window (of 29 entries, 0 malformed skipped, 17 chrome skipped)
01_source_fetch.log: [01_source_fetch] Commission for Agricultural Costs and Prices: 0 in-window (of 1 entries, 0 malformed skipped, 0 chrome skipped)
01_source_fetch.log: [01_source_fetch] Ministry of Food Processing Industries: 0 in-window (of 1 entries, 0 malformed skipped, 0 chrome skipped)
01_source_fetch.log: [01_source_fetch] Ministry of Environment, Forest and Climate Change: 0 in-window (of 10 entries, 0 malformed skipped, 5 chrome skipped)
01_source_fetch.log: [01_source_fetch] NPCI: 0 in-window (of 2 entries, 0 malformed skipped, 0 chrome skipped)
01_source_fetch.log: [01_source_fetch] PFRDA: 0 in-window (of 12 entries, 0 malformed skipped, 2 chrome skipped)
01_source_fetch.log: [01_source_fetch] IRDAI: 0 in-window (of 0 entries, 0 malformed skipped, 0 chrome skipped)
01_source_fetch.log: [01_source_fetch] IFSCA: 0 in-window (of 85 entries, 0 malformed skipped, 81 chrome skipped)
01_source_fetch.log: [01_source_fetch] Department of Financial Services: 0 in-window (of 20 entries, 0 malformed skipped, 14 chrome skipped)
01_source_fetch.log: [01_source_fetch] Union Budget of India: 0 in-window (of 2 entries, 0 malformed skipped, 0 chrome skipped)
01_source_fetch.log: [01_source_fetch] GST Council: 0 in-window (of 27 entries, 0 malformed skipped, 26 chrome skipped)
01_source_fetch.log: [01_source_fetch] Competition Commission of India: 1 in-window (of 73 entries, 0 malformed skipped, 53 chrome skipped)
01_source_fetch.log: [01_source_fetch] RBI Bulletin: 0 in-window (of 0 entries, 0 malformed skipped, 0 chrome skipped)
01_source_fetch.log: [01_source_fetch] India.gov.in: 9 in-window (of 100 entries, 0 malformed skipped, 27 chrome skipped)
01_source_fetch.log: [01_source_fetch] Prime Minister of India: 9 in-window (of 26 entries, 0 malformed skipped, 0 chrome skipped)
01_source_fetch.log: [01_source_fetch] Cabinet Secretariat: 0 in-window (of 1 entries, 0 malformed skipped, 1 chrome skipped)
01_source_fetch.log: [01_source_fetch] MyGov India: 7 in-window (of 100 entries, 0 malformed skipped, 62 chrome skipped)
01_source_fetch.log: [01_source_fetch] Ministry of Rural Development: 0 in-window (of 0 entries, 0 malformed skipped, 0 chrome skipped)
01_source_fetch.log: [01_source_fetch] Ministry of Cooperation: 1 in-window (of 9 entries, 0 malformed skipped, 2 chrome skipped)
01_source_fetch.log: [01_source_fetch] Department of Science and Technology: 5 in-window (of 100 entries, 0 malformed skipped, 60 chrome skipped)
01_source_fetch.log: [01_source_fetch] Department of Biotechnology: 0 in-window (of 0 entries, 0 malformed skipped, 0 chrome skipped)
01_source_fetch.log: [01_source_fetch] DRDO: 4 in-window (of 99 entries, 0 malformed skipped, 82 chrome skipped)
01_source_fetch.log: [01_source_fetch] Central Pollution Control Board: 0 in-window (of 7 entries, 0 malformed skipped, 5 chrome skipped)
01_source_fetch.log: [01_source_fetch] Ministry of Education: 1 in-window (of 24 entries, 0 malformed skipped, 9 chrome skipped)
01_source_fetch.log: [01_source_fetch] UGC: 0 in-window (of 1 entries, 0 malformed skipped, 1 chrome skipped)
01_source_fetch.log: [01_source_fetch] National Testing Agency: 0 in-window (of 0 entries, 0 malformed skipped, 0 chrome skipped)
01_source_fetch.log: [01_source_fetch] Ministry of Defence: 0 in-window (of 13 entries, 0 malformed skipped, 6 chrome skipped)
01_source_fetch.log: [01_source_fetch] President of India: 1 in-window (of 21 entries, 0 malformed skipped, 3 chrome skipped)
01_source_fetch.log: [01_source_fetch] Election Commission of India: 0 in-window (of 10 entries, 0 malformed skipped, 9 chrome skipped)
01_source_fetch.log: [01_source_fetch] UPSC: 0 in-window (of 4 entries, 0 malformed skipped, 0 chrome skipped)
01_source_fetch.log: [01_source_fetch] The Hindu: 0 in-window (of 60 entries, 0 malformed skipped, 0 chrome skipped)
01_source_fetch.log: [01_source_fetch] Business Standard: 0 in-window (of 135 entries, 0 malformed skipped, 1 chrome skipped)
01_source_fetch.log: [01_source_fetch] Mint: 0 in-window (of 35 entries, 0 malformed skipped, 0 chrome skipped)
01_source_fetch.log: [01_source_fetch] Economic Times: 0 in-window (of 76 entries, 0 malformed skipped, 1 chrome skipped)
01_source_fetch.log: [01_source_fetch] Google News India: 1 in-window (of 38 entries, 0 malformed skipped, 0 chrome skipped)
01_source_fetch.log: [01_source_fetch] Google News Search: 0 in-window (of 100 entries, 0 malformed skipped, 42 chrome skipped)
01_source_fetch.log: [01_source_fetch] wrote /home/runner/work/daily-current-affairs/daily-current-affairs/data/raw/daily_2026-10-15.json (46 articles, 52/57 feeds ok, 717 chrome skipped)
04_fact_verification.log: 2026-10-16 13:04:14 | WARNING  | pipeline.ai_router | [Router] gemini HTTP 429 (rate_limit): {
04_fact_verification.log: 2026-10-16 13:04:14 | WARNING  | pipeline.ai_router | [Router] Provider gemini disabled for 120s: rate limited
04_fact_verification.log: 2026-10-16 13:04:25 | WARNING  | pipeline.ai_router | [Router] groq HTTP 429 (rate_limit): {"error":{"message":"Rate limit reached for model `openai/gpt-oss-120b` in organization `org_01m4n8hsfce0q8z1yndppr2nmv` service 
04_fact_verification.log: 2026-10-16 13:04:25 | WARNING  | pipeline.ai_router | [Router] Provider groq disabled for 120s: rate limited
04_fact_verification.log: 2026-10-16 13:04:25 | WARNING  | pipeline.ai_router | [Router] openrouter HTTP 402 (auth_error): {"error":{"message":"This request requires more credits, or fewer max_tokens. You requested up to 16384 tokens, but can onl
04_fact_verification.log: 2026-10-16 13:04:25 | WARNING  | pipeline.ai_router | [Router] Provider openrouter disabled for 3600s: auth error
04_fact_verification.log: 2026-10-16 13:04:25 | WARNING  | pipeline.ai_router | [Router] mistral HTTP 429 (rate_limit): {"object":"error","message":"Rate limit exceeded","type":"rate_limited","param":null,"code":"1300","raw_status_code":429}
04_fact_verification.log: 2026-10-16 13:04:25 | WARNING  | pipeline.ai_router | [Router] Provider mistral disabled for 120s: rate limited
04_fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: mistral: rate_limit
04_fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
07_student_domain_relevance.log: INFO:root:[STUDENT & DOMAIN RELEVANCE AGENT] relevant=8/41 agri=3 banking=1
10_final_news_selection.log: 2026-10-16 13:04:26,213 | INFO     | root | [FINAL NEWS SELECTION AGENT v2] selected 8 items (target=28)
12_content_editor.log: 2026-10-16 13:04:26 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
12_content_editor.log: 2026-10-16 13:04:27 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ['no Devanagari characters']
12_content_editor.log: 2026-10-16 13:04:27 | WARNING  | pipeline.ai_translator | [Translator] openrouter parked for 900s (HTTP 402)
12_content_editor.log: 2026-10-16 13:04:27 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
12_content_editor.log: 2026-10-16 13:04:27 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['gemini: rate limited', 'groq: validation failed', 'openrouter: HTTP 402', 'mistral: rate limited'])
12_content_editor.log: 2026-10-16 13:04:27 | WARNING  | pipeline.ai_translator | [Translator] groq rate-limited (429)
12_content_editor.log: 2026-10-16 13:04:27 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['groq: rate limited'])
12_content_editor.log: 2026-10-16 13:04:27 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:04:27 | WARNING  | pipeline.ai_router | [Router] gemini HTTP 429 (rate_limit): {
12_content_editor.log: 2026-10-16 13:04:27 | WARNING  | pipeline.ai_router | [Router] Provider gemini disabled for 120s: rate limited
12_content_editor.log: 2026-10-16 13:04:28 | WARNING  | pipeline.ai_router | [Router] groq HTTP 429 (rate_limit): {"error":{"message":"Rate limit reached for model `openai/gpt-oss-120b` in organization `org_01m4n8hsfce0q8z1yndppr2nmv` service 
12_content_editor.log: 2026-10-16 13:04:28 | WARNING  | pipeline.ai_router | [Router] Provider groq disabled for 120s: rate limited
12_content_editor.log: 2026-10-16 13:04:28 | WARNING  | pipeline.ai_router | [Router] openrouter HTTP 402 (auth_error): {"error":{"message":"This request requires more credits, or fewer max_tokens. You requested up to 16384 tokens, but can onl
12_content_editor.log: 2026-10-16 13:04:28 | WARNING  | pipeline.ai_router | [Router] Provider openrouter disabled for 3600s: auth error
12_content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.ai_router | [Router] mistral HTTP 429 (rate_limit): {"object":"error","message":"Rate limit exceeded","type":"rate_limited","param":null,"code":"1300","raw_status_code":429}
12_content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.ai_router | [Router] Provider mistral disabled for 120s: rate limited
12_content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: mistral: rate_limit
12_content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:04:29 | WARNING  | pipeline.content | [Content Builder] 37 translations need review (AI did not pass)
19_pdf_qa.log: 2026-10-16 13:04:35 | INFO     | agent.19_pdf_qa | QA requires at least 10 MCQs for 8 selected stories
19_pdf_qa.log: PDF QA REPORT — ✅ PASSED
```

## Stage log tails

### content_editor.log

```
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:29 | INFO     | pipeline.content | [Content Builder] Translation stats: ai=0 fallback=37 untranslated=0 (AI success 0.0%)
2026-10-16 13:04:29 | WARNING  | pipeline.content | [Content Builder] 37 translations need review (AI did not pass)
```

### deduplication.log

```
2026-10-16 13:04:25 | INFO     | agent.05_deduplication | Input: 46 articles from daily_2026-10-15.json
2026-10-16 13:04:25 | INFO     | agent.05_deduplication | After URL dedup: 46
2026-10-16 13:04:25 | INFO     | agent.05_deduplication | After fingerprint dedup: 44
2026-10-16 13:04:26 | INFO     | agent.05_deduplication | After similarity clustering: 41
2026-10-16 13:04:26 | INFO     | agent.05_deduplication | ✔ Dedup complete: 46 → 41 (10.9% reduction)
```

### fact_verification.log

```
2026-10-16 13:04:25 | WARNING  | pipeline.ai_router | [Router] Provider openrouter disabled for 3600s: auth error
2026-10-16 13:04:25 | WARNING  | pipeline.ai_router | [Router] mistral HTTP 429 (rate_limit): {"object":"error","message":"Rate limit exceeded","type":"rate_limited","param":null,"code":"1300","raw_status_code":429}
2026-10-16 13:04:25 | WARNING  | pipeline.ai_router | [Router] Provider mistral disabled for 120s: rate limited
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: mistral: rate_limit
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | INFO     | agent.04_fact_verification | Verification complete in 11.8s | 46 total | 46 passed | 0 rejected | 0 crashed
2026-10-16 13:04:25 | INFO     | agent.04_fact_verification | Avg confidence: 0.562
2026-10-16 13:04:25 | INFO     | agent.04_fact_verification | Methods: {'combined': 13, 'heuristic+cross_source': 33}
2026-10-16 13:04:25 | INFO     | agent.04_fact_verification | ✔ Fact verification completed: 46 items → /home/runner/work/daily-current-affairs/daily-current-affairs/data/verified/daily_2026-10-15.json
```

### orchestrator_00.log

```
2026-10-16 13:03:49 | INFO     | agent.00_model_orchestrator | Model orchestrator starting
2026-10-16 13:03:50 | INFO     | agent.00_model_orchestrator | Checking gemini (model=gemini-flash-latest)
2026-10-16 13:03:50 | INFO     | agent.00_model_orchestrator |   ❌ gemini → rate_limit
2026-10-16 13:03:50 | INFO     | agent.00_model_orchestrator | Checking groq (model=openai/gpt-oss-120b)
2026-10-16 13:03:50 | INFO     | agent.00_model_orchestrator |   ❌ groq → malformed
2026-10-16 13:03:50 | INFO     | agent.00_model_orchestrator | Checking openrouter (model=openai/gpt-4o-mini)
2026-10-16 13:03:51 | INFO     | agent.00_model_orchestrator |   ✅ openrouter → ok
2026-10-16 13:03:51 | INFO     | agent.00_model_orchestrator | Checking mistral (model=mistral-small-latest)
2026-10-16 13:03:51 | INFO     | agent.00_model_orchestrator |   ❌ mistral → rate_limit
2026-10-16 13:03:51 | INFO     | agent.00_model_orchestrator | Model status: 1/4 healthy → /home/runner/work/daily-current-affairs/daily-current-affairs/state/model_status.json
```

### pdf_design.log

```
```

### pdf_qa.log

```
2026-10-16 13:04:35 | INFO     | agent.19_pdf_qa | QA check: daily_2026-10-15.pdf
2026-10-16 13:04:35 | INFO     | agent.19_pdf_qa | QA requires at least 10 MCQs for 8 selected stories
2026-10-16 13:04:35 | INFO     | agent.19_pdf_qa | Report: /home/runner/work/daily-current-affairs/daily-current-affairs/logs/qa/daily_2026-10-15_qa.json
2026-10-16 13:04:35 | INFO     | agent.19_pdf_qa | ✔ PDF QA passed — safe to publish
```

### pin_verifier.log

```
2026-10-16 13:04:35 | INFO     | agent.23_telegram_pin_verifier | [DRY-RUN] No live publication receipt to pin.
```

### 00_model_orchestrator.log

```
--- attempt 1; exit 0 ---
2026-10-16 13:03:49 | INFO     | agent.00_model_orchestrator | Model orchestrator starting
2026-10-16 13:03:50 | INFO     | agent.00_model_orchestrator | Checking gemini (model=gemini-flash-latest)
2026-10-16 13:03:50 | INFO     | agent.00_model_orchestrator |   ❌ gemini → rate_limit
2026-10-16 13:03:50 | INFO     | agent.00_model_orchestrator | Checking groq (model=openai/gpt-oss-120b)
2026-10-16 13:03:50 | INFO     | agent.00_model_orchestrator |   ❌ groq → malformed
2026-10-16 13:03:50 | INFO     | agent.00_model_orchestrator | Checking openrouter (model=openai/gpt-4o-mini)
2026-10-16 13:03:51 | INFO     | agent.00_model_orchestrator |   ✅ openrouter → ok
2026-10-16 13:03:51 | INFO     | agent.00_model_orchestrator | Checking mistral (model=mistral-small-latest)
2026-10-16 13:03:51 | INFO     | agent.00_model_orchestrator |   ❌ mistral → rate_limit
2026-10-16 13:03:51 | INFO     | agent.00_model_orchestrator | Model status: 1/4 healthy → /home/runner/work/daily-current-affairs/daily-current-affairs/state/model_status.json
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/requests/__init__.py:113: RequestsDependencyWarning: urllib3 (2.2.3) or chardet (7.6.0)/charset_normalizer (3.4.0) doesn't match a supported version!
  warnings.warn(
```

### 01_source_fetch.log

```
[01_source_fetch] NPCI: 0 in-window (of 2 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] PFRDA: 0 in-window (of 12 entries, 0 malformed skipped, 2 chrome skipped)
[01_source_fetch] IRDAI: 0 in-window (of 0 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] IFSCA: 0 in-window (of 85 entries, 0 malformed skipped, 81 chrome skipped)
[01_source_fetch] Department of Financial Services: 0 in-window (of 20 entries, 0 malformed skipped, 14 chrome skipped)
[01_source_fetch] Union Budget of India: 0 in-window (of 2 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] GST Council: 0 in-window (of 27 entries, 0 malformed skipped, 26 chrome skipped)
[01_source_fetch] Competition Commission of India: 1 in-window (of 73 entries, 0 malformed skipped, 53 chrome skipped)
[01_source_fetch] RBI Bulletin: 0 in-window (of 0 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] India.gov.in: 9 in-window (of 100 entries, 0 malformed skipped, 27 chrome skipped)
[01_source_fetch] Prime Minister of India: 9 in-window (of 26 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] Cabinet Secretariat: 0 in-window (of 1 entries, 0 malformed skipped, 1 chrome skipped)
[01_source_fetch] MyGov India: 7 in-window (of 100 entries, 0 malformed skipped, 62 chrome skipped)
[01_source_fetch] Ministry of Rural Development: 0 in-window (of 0 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] Ministry of Cooperation: 1 in-window (of 9 entries, 0 malformed skipped, 2 chrome skipped)
[01_source_fetch] Department of Science and Technology: 5 in-window (of 100 entries, 0 malformed skipped, 60 chrome skipped)
[01_source_fetch] Department of Biotechnology: 0 in-window (of 0 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] DRDO: 4 in-window (of 99 entries, 0 malformed skipped, 82 chrome skipped)
[01_source_fetch] Central Pollution Control Board: 0 in-window (of 7 entries, 0 malformed skipped, 5 chrome skipped)
[01_source_fetch] Ministry of Education: 1 in-window (of 24 entries, 0 malformed skipped, 9 chrome skipped)
[01_source_fetch] UGC: 0 in-window (of 1 entries, 0 malformed skipped, 1 chrome skipped)
[01_source_fetch] National Testing Agency: 0 in-window (of 0 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] Ministry of Defence: 0 in-window (of 13 entries, 0 malformed skipped, 6 chrome skipped)
[01_source_fetch] President of India: 1 in-window (of 21 entries, 0 malformed skipped, 3 chrome skipped)
[01_source_fetch] Election Commission of India: 0 in-window (of 10 entries, 0 malformed skipped, 9 chrome skipped)
[01_source_fetch] UPSC: 0 in-window (of 4 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] The Hindu: 0 in-window (of 60 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] Business Standard: 0 in-window (of 135 entries, 0 malformed skipped, 1 chrome skipped)
[01_source_fetch] Mint: 0 in-window (of 35 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] Economic Times: 0 in-window (of 76 entries, 0 malformed skipped, 1 chrome skipped)
[01_source_fetch] Google News India: 1 in-window (of 38 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] Google News Search: 0 in-window (of 100 entries, 0 malformed skipped, 42 chrome skipped)
[01_source_fetch] wrote /home/runner/work/daily-current-affairs/daily-current-affairs/data/raw/daily_2026-10-15.json (46 articles, 52/57 feeds ok, 717 chrome skipped)
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
2026-10-16 13:04:25 | WARNING  | pipeline.ai_router | [Router] Provider mistral disabled for 120s: rate limited
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: mistral: rate_limit
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:25 | INFO     | agent.04_fact_verification | Verification complete in 11.8s | 46 total | 46 passed | 0 rejected | 0 crashed
2026-10-16 13:04:25 | INFO     | agent.04_fact_verification | Avg confidence: 0.562
2026-10-16 13:04:25 | INFO     | agent.04_fact_verification | Methods: {'combined': 13, 'heuristic+cross_source': 33}
2026-10-16 13:04:25 | INFO     | agent.04_fact_verification | ✔ Fact verification completed: 46 items → /home/runner/work/daily-current-affairs/daily-current-affairs/data/verified/daily_2026-10-15.json
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/requests/__init__.py:113: RequestsDependencyWarning: urllib3 (2.2.3) or chardet (7.6.0)/charset_normalizer (3.4.0) doesn't match a supported version!
  warnings.warn(
```

### 05_deduplication.log

```
--- attempt 1; exit 0 ---
2026-10-16 13:04:25 | INFO     | agent.05_deduplication | Input: 46 articles from daily_2026-10-15.json
2026-10-16 13:04:25 | INFO     | agent.05_deduplication | After URL dedup: 46
2026-10-16 13:04:25 | INFO     | agent.05_deduplication | After fingerprint dedup: 44
2026-10-16 13:04:26 | INFO     | agent.05_deduplication | After similarity clustering: 41
2026-10-16 13:04:26 | INFO     | agent.05_deduplication | ✔ Dedup complete: 46 → 41 (10.9% reduction)
```

### 06_news_importance.log

```
--- attempt 1; exit 0 ---
[06_news_importance] job=daily_2026-10-15 type=daily date=2026-10-15
[06] OK — scored=41
2026-10-16 13:04:26,085 | INFO     | root | [NEWS IMPORTANCE AGENT] scored 41 events, top=24
```

### 07_student_domain_relevance.log

```
--- attempt 1; exit 0 ---
INFO:root:[STUDENT & DOMAIN RELEVANCE AGENT] relevant=8/41 agri=3 banking=1
```

### 10_final_news_selection.log

```
--- attempt 1; exit 0 ---
[10_final_news_selection] job=daily_2026-10-15 type=daily date=2026-10-15
[10] OK — selected_count=8
2026-10-16 13:04:26,213 | INFO     | root | [FINAL NEWS SELECTION AGENT v2] selected 8 items (target=28)
2026-10-16 13:04:26,214 | INFO     | root |   Agriculture: 3
2026-10-16 13:04:26,214 | INFO     | root |   Economy: 2
2026-10-16 13:04:26,214 | INFO     | root |   National: 2
2026-10-16 13:04:26,214 | INFO     | root |   Banking & Finance: 1
```

### 11_importance_memory.log

```
--- attempt 1; exit 0 ---
INFO:root:[IMPORTANCE MEMORY AGENT] memory updated for 8 events (local + persistent)
```

### 12_content_editor.log

```
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 13:04:29 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 13:04:29 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:29 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:04:29 | INFO     | pipeline.content | [Content Builder] Translation stats: ai=0 fallback=37 untranslated=0 (AI success 0.0%)
2026-10-16 13:04:29 | WARNING  | pipeline.content | [Content Builder] 37 translations need review (AI did not pass)
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/requests/__init__.py:113: RequestsDependencyWarning: urllib3 (2.2.3) or chardet (7.6.0)/charset_normalizer (3.4.0) doesn't match a supported version!
  warnings.warn(
```

### 16_mcq_generator.log

```
--- attempt 1; exit 0 ---
INFO:root:[MCQ GENERATOR AGENT v4 (FAIL-CLOSED)] Generating MCQs for 8 items...
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
[OK] PDF generated: /home/runner/work/daily-current-affairs/daily-current-affairs/output/daily_2026-10-15.pdf
```

### 19_pdf_qa.log

```
--- attempt 1; exit 0 ---
2026-10-16 13:04:35 | INFO     | agent.19_pdf_qa | QA check: daily_2026-10-15.pdf
2026-10-16 13:04:35 | INFO     | agent.19_pdf_qa | QA requires at least 10 MCQs for 8 selected stories
2026-10-16 13:04:35 | INFO     | agent.19_pdf_qa | Report: /home/runner/work/daily-current-affairs/daily-current-affairs/logs/qa/daily_2026-10-15_qa.json
========================================================================
PDF QA REPORT — ✅ PASSED
========================================================================
File:            /home/runner/work/daily-current-affairs/daily-current-affairs/output/daily_2026-10-15.pdf
Size:            4788 KB
Pages:           19
Chars:           32373
Devanagari:      1767 (5.5%)
Fonts:           6 (AAAAAA+Mukta-Bold, AAAAAA+Mukta-Regular, AAAAAA+Poppins-Bold...)
MCQs:            17
Answer markers:  15
Duplicate Qs:    0
URLs:            58
Images:          111
Blank pages:     none
--- Issues ---
  ⚠️  [low_hindi] Hindi coverage 5.5% is low
  ⚠️  [text_overflow] Text may overflow page bounds on pages: [6, 18]
========================================================================
2026-10-16 13:04:35 | INFO     | agent.19_pdf_qa | ✔ PDF QA passed — safe to publish
```

### 22_telegram_publisher.log

```
--- attempt 1; exit 0 ---
2026-10-16 13:04:35 | INFO     | agent.22_telegram_publisher | Found 1 candidate PDF(s) (max 5 per run)
2026-10-16 13:04:35 | WARNING  | agent.22_telegram_publisher | Adopted 10 unverifiable legacy publication row(s) as history
2026-10-16 13:04:35 | INFO     | agent.22_telegram_publisher | [1/1] daily_2026-10-15.pdf
2026-10-16 13:04:35 | INFO     | agent.22_telegram_publisher | [DRY-RUN] Would publish daily_2026-10-15.pdf (4903641 bytes) with caption:
<b>&gt;&gt; io' &gt; - dof.gov.in</b>
&lt;a href="https://news.google.com/rss/articles/CBMihAFBVV95cUxQSkFOR2JfdnU3ZTNXZ2FEem1DaWZlMFVtVHJjNGZNQWFyUUtOTzBmT2hkc1FRWWlGTWl2U0JmeFJpODcycjhCU3NWaEM0OXRI
2026-10-16 13:04:35 | INFO     | agent.22_telegram_publisher | Publishing complete: success=1 failed=0 skipped=0 total=1
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/requests/__init__.py:113: RequestsDependencyWarning: urllib3 (2.2.3) or chardet (7.6.0)/charset_normalizer (3.4.0) doesn't match a supported version!
  warnings.warn(
```

### 23_telegram_pin_verifier.log

```
--- attempt 1; exit 0 ---
2026-10-16 13:04:35 | INFO     | agent.23_telegram_pin_verifier | [DRY-RUN] No live publication receipt to pin.
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/requests/__init__.py:113: RequestsDependencyWarning: urllib3 (2.2.3) or chardet (7.6.0)/charset_normalizer (3.4.0) doesn't match a supported version!
  warnings.warn(
```

### 24_final_health_audit.log

```
--- attempt 1; exit 0 ---
{"job_id": "daily_2026-10-15", "passed": true, "dry_run": true, "issues": [], "checked_at": "2026-10-16T13:04:35.502798+00:00"}
```

### telegram_publisher.log

```
2026-10-16 13:04:35 | INFO     | agent.22_telegram_publisher | Found 1 candidate PDF(s) (max 5 per run)
2026-10-16 13:04:35 | WARNING  | agent.22_telegram_publisher | Adopted 10 unverifiable legacy publication row(s) as history
2026-10-16 13:04:35 | INFO     | agent.22_telegram_publisher | [1/1] daily_2026-10-15.pdf
2026-10-16 13:04:35 | INFO     | agent.22_telegram_publisher | [DRY-RUN] Would publish daily_2026-10-15.pdf (4903641 bytes) with caption:
<b>&gt;&gt; io' &gt; - dof.gov.in</b>
&lt;a href="https://news.google.com/rss/articles/CBMihAFBVV95cUxQSkFOR2JfdnU3ZTNXZ2FEem1DaWZlMFVtVHJjNGZNQWFyUUtOTzBmT2hkc1FRWWlGTWl2U0JmeFJpODcycjhCU3NWaEM0OXRI
2026-10-16 13:04:35 | INFO     | agent.22_telegram_publisher | Publishing complete: success=1 failed=0 skipped=0 total=1
```

## Committed state on this branch at collection time

```json
{
 "status": "success",
 "dry_run": true,
 "last_success_stage": "24_final_health_audit",
 "failed_stage": null,
 "checkpoint_run_id": "38904929697",
 "last_error": null
}
```

## PDF download

- https://github.com/agrilearningpoint/daily-current-affairs/releases/tag/untagged-d504c28480e1c3e8fb6a (draft release asset; no Telegram publication was made)
