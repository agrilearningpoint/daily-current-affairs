# Dry-run evidence — run 38906490713

- run URL: https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/38906490713
- edition: 2026-10-15 (DRY_RUN=1)

## Article counts

| stage | count |
|---|---|
| raw | 38 |
| verified | 38 |
| dedup | 36 |
| scored | 6 |
| selected | 6 |
| content | 6 |
| mcq | 15 |

## Category distribution per stage (raw keys here = normalisation missing)

- raw: ```{"economy_data": 2, "agriculture_core": 1, "food_safety": 2, "govt_national": 24, "cooperation": 1, "science": 5, "defence_science": 1, "education": 1, "aggregator": 1}```

## Selected items

- [22/47] Agriculture: Significant Weather Observations Stations Rainfall (in mm) - IMD | https://news.google.com/rss/articles/CBMia0FVX3lxTE93QnV1QWRHZnEzSXdRQjB1NXl2S0hpSTAxaF9reGlCZVcwaktLUkFKLWM0SzJsS1pZMDl
- [15/30] Economy: General Statement The Competition Commission of India (Settlement) Regulations, 2024 1. Th | https://news.google.com/rss/articles/CBMivwFBVV95cUxOUnJGUFNGT2VrT3FKMWZBR0U5Q3pkV1lVNHZ0YS0xRDg0d19aaTFReXFkdTB1cEo1RHd
- [24/32] National: Cabinet approves Productivity Linked Bonus (PLB) for 78 days to Railway Employees - PM Ind | https://news.google.com/rss/articles/CBMiwAFBVV95cUxQYURXV3A0dnFKU0dQM3RfS0hmRzE4Sk5IZGhfdHJoMDVQZU9ZOVE1OFU2SkllLWdaY3V
- [20/45] Agriculture: Instructions given to expedite the computerization of PACS - Ministry of Cooperation | https://news.google.com/rss/articles/CBMiowFBVV95cUxQSjZYWHNsS1BnM3pSVkhERXktbDluNW5sRzlHbmZYWjdVQU52c3p3dHlzUnJ2WEVtVlF
- [23/31] National: Cabinet approves continuation of the National Social Assistance Programme for five years f | https://news.google.com/rss/articles/CBMi7AFBVV95cUxPM1ZqODh6RTFZSnY1eWV3Tjd6bDJGU3p3cjJlZ25LWDBzZ0hyZzFmYVZ2VTEyc2pfQW8
- [19/27] National: View DetailsAmul DairyView Details - Government of India - India.gov.in | https://news.google.com/rss/articles/CBMimAFBVV95cUxPM0xqSjlKTUxKeTdDZUh6aHR1VUpYUGEyV3Jkc3JrdDlodGlvUTlMR2IzcUxlOE9FMy1

## PDF qa report

```json
{
  "pdf_path": "/home/runner/work/daily-current-affairs/daily-current-affairs/output/daily_2026-10-15.pdf",
  "checked_at": "2026-10-16T13:16:58.730030+00:00",
  "passed": true,
  "page_count": 17,
  "file_size_bytes": 4383171,
  "devanagari_chars": 1673,
  "total_chars": 29744,
  "hindi_pct": 5.62,
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
  "urls_found": 59,
  "blank_pages": [],
  "image_xobjects": 93,
  "issues": [
    {
      "severity": "warning",
      "code": "low_hindi",
      "message": "Hindi coverage 5.6% is low",
      "details": {
        "hindi_pct": 5.62
      }
    },
    {
      "severity": "warning",
      "code": "text_overflow",
      "message": "Text may overflow page bounds on pages: [14]",
      "details": {
        "pages": [
          14
        ]
      }
    }
  ],
  "job_id": "daily_2026-10-15",
  "file_sha256": "a9d8bb7add57dcc7e5329ee028068d520ec003ce402ed1b45431bcd0d7deb47e"
}
```

## PDF health report

```json
{
  "job_id": "daily_2026-10-15",
  "passed": true,
  "dry_run": true,
  "issues": [],
  "checked_at": "2026-10-16T13:16:59.181949+00:00"
}
```

## Stage log inventory

| log | lines | first | last |
|---|---|---|---|
| content_editor.log | 174 | 2026-10-16 13:16:51 | 2026-10-16 13:16:53 |
| deduplication.log | 5 | 2026-10-16 13:16:50 | 2026-10-16 13:16:50 |
| fact_verification.log | 56 | 2026-10-16 13:16:38 | 2026-10-16 13:16:50 |
| orchestrator_00.log | 10 | 2026-10-16 13:16:06 | 2026-10-16 13:16:13 |
| pdf_qa.log | 4 | 2026-10-16 13:16:58 | 2026-10-16 13:16:58 |
| pin_verifier.log | 1 | 2026-10-16 13:16:59 | 2026-10-16 13:16:59 |
| 00_model_orchestrator.log | 13 | --- attempt 1; exit |   warnings.warn( |
| 01_source_fetch.log | 61 | --- attempt 1; exit | [01_source_fetch] W |
| 04_fact_verification.log | 59 | --- attempt 1; exit |   warnings.warn( |
| 05_deduplication.log | 6 | --- attempt 1; exit | 2026-10-16 13:16:50 |
| 06_news_importance.log | 4 | --- attempt 1; exit | 2026-10-16 13:16:50 |
| 07_student_domain_relevance.log | 3 | --- attempt 1; exit | INFO:root:[STUDENT  |
| 10_final_news_selection.log | 7 | --- attempt 1; exit | 2026-10-16 13:16:51 |
| 11_importance_memory.log | 2 | --- attempt 1; exit | INFO:root:[IMPORTAN |
| 12_content_editor.log | 177 | --- attempt 1; exit |   warnings.warn( |
| 16_mcq_generator.log | 7 | --- attempt 1; exit | INFO:root:[MCQ GENE |
| 17_mcq_validator.log | 6 | --- attempt 1; exit | INFO:root:[MCQ VALI |
| 18_pdf_design.log | 3 | --- attempt 1; exit | [OK] PDF generated: |
| 19_pdf_qa.log | 24 | --- attempt 1; exit | 2026-10-16 13:16:58 |
| 22_telegram_publisher.log | 10 | --- attempt 1; exit |   warnings.warn( |
| 23_telegram_pin_verifier.log | 4 | --- attempt 1; exit |   warnings.warn( |
| 24_final_health_audit.log | 2 | --- attempt 1; exit | {"job_id": "daily_2 |
| telegram_publisher.log | 7 | 2026-10-16 13:16:58 | 2026-10-16 13:16:58 |

## Log excerpts (retries / skips / QA)

```
content_editor.log: 2026-10-16 13:16:51 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-16 13:16:51 | WARNING  | pipeline.ai_translator | [Translator] groq rate-limited (429)
content_editor.log: 2026-10-16 13:16:51 | WARNING  | pipeline.ai_translator | [Translator] openrouter parked for 900s (HTTP 402)
content_editor.log: 2026-10-16 13:16:52 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-16 13:16:52 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['gemini: rate limited', 'groq: rate limited', 'openrouter: HTTP 402', 'mistral: rate limited'])
content_editor.log: 2026-10-16 13:16:52 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:16:52 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:16:52 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:16:52 | WARNING  | pipeline.ai_router | [Router] gemini HTTP 429 (rate_limit): {
content_editor.log: 2026-10-16 13:16:52 | WARNING  | pipeline.ai_router | [Router] Provider gemini disabled for 120s: rate limited
content_editor.log: 2026-10-16 13:16:52 | WARNING  | pipeline.ai_router | [Router] groq HTTP 429 (rate_limit): {"error":{"message":"Rate limit reached for model `openai/gpt-oss-120b` in organization `org_01m4n8hsfce0q8z1yndppr2nmv` service 
content_editor.log: 2026-10-16 13:16:52 | WARNING  | pipeline.ai_router | [Router] Provider groq disabled for 120s: rate limited
content_editor.log: 2026-10-16 13:16:52 | WARNING  | pipeline.ai_router | [Router] openrouter HTTP 402 (auth_error): {"error":{"message":"This request requires more credits, or fewer max_tokens. You requested up to 16384 tokens, but can onl
content_editor.log: 2026-10-16 13:16:52 | WARNING  | pipeline.ai_router | [Router] Provider openrouter disabled for 3600s: auth error
content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.ai_router | [Router] mistral HTTP 429 (rate_limit): {"object":"error","message":"Rate limit exceeded","type":"rate_limited","param":null,"code":"1300","raw_status_code":429}
content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.ai_router | [Router] Provider mistral disabled for 120s: rate limited
content_editor.log: 2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: mistral: rate_limit
content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
content_editor.log: 2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Content Builder] 26 translations need review (AI did not pass)
fact_verification.log: 2026-10-16 13:16:38 | WARNING  | pipeline.ai_router | [Router] gemini HTTP 429 (rate_limit): {
fact_verification.log: 2026-10-16 13:16:38 | WARNING  | pipeline.ai_router | [Router] Provider gemini disabled for 120s: rate limited
fact_verification.log: 2026-10-16 13:16:50 | WARNING  | pipeline.ai_router | [Router] groq HTTP 429 (rate_limit): {"error":{"message":"Rate limit reached for model `openai/gpt-oss-120b` in organization `org_01m4n8hsfce0q8z1yndppr2nmv` service 
fact_verification.log: 2026-10-16 13:16:50 | WARNING  | pipeline.ai_router | [Router] Provider groq disabled for 120s: rate limited
fact_verification.log: 2026-10-16 13:16:50 | WARNING  | pipeline.ai_router | [Router] openrouter HTTP 402 (auth_error): {"error":{"message":"This request requires more credits, or fewer max_tokens. You requested up to 16384 tokens, but can onl
fact_verification.log: 2026-10-16 13:16:50 | WARNING  | pipeline.ai_router | [Router] Provider openrouter disabled for 3600s: auth error
fact_verification.log: 2026-10-16 13:16:50 | WARNING  | pipeline.ai_router | [Router] mistral HTTP 429 (rate_limit): {"object":"error","message":"Rate limit exceeded","type":"rate_limited","param":null,"code":"1300","raw_status_code":429}
fact_verification.log: 2026-10-16 13:16:50 | WARNING  | pipeline.ai_router | [Router] Provider mistral disabled for 120s: rate limited
fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: mistral: rate_limit
fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
pdf_qa.log: 2026-10-16 13:16:58 | INFO     | agent.19_pdf_qa | QA requires at least 10 MCQs for 6 selected stories
pdf_qa.log: 2026-10-16 13:16:58 | INFO     | agent.19_pdf_qa | ✔ PDF QA passed — safe to publish
pin_verifier.log: 2026-10-16 13:16:59 | INFO     | agent.23_telegram_pin_verifier | [DRY-RUN] No live publication receipt to pin.
01_source_fetch.log: [01_source_fetch] ICAR: 0 in-window (of 10 entries, 0 malformed skipped, 4 chrome skipped)
01_source_fetch.log: [01_source_fetch] WHO News: 0 in-window (of 198 entries, 0 malformed skipped, 0 chrome skipped)
01_source_fetch.log: [01_source_fetch] The Hindu National: 0 in-window (of 60 entries, 0 malformed skipped, 0 chrome skipped)
01_source_fetch.log: [01_source_fetch] Ministry of Agriculture & Farmers Welfare: 0 in-window (of 15 entries, 0 malformed skipped, 12 chrome skipped)
01_source_fetch.log: [01_source_fetch] RBI: 0 in-window (of 57 entries, 0 malformed skipped, 53 chrome skipped)
01_source_fetch.log: [01_source_fetch] NABARD: 0 in-window (of 0 entries, 0 malformed skipped, 0 chrome skipped)
01_source_fetch.log: [01_source_fetch] Ministry of Statistics and Programme Implementation: 1 in-window (of 15 entries, 0 malformed skipped, 9 chrome skipped)
01_source_fetch.log: [01_source_fetch] India Meteorological Department: 1 in-window (of 100 entries, 0 malformed skipped, 26 chrome skipped)
01_source_fetch.log: [01_source_fetch] Department of Animal Husbandry and Dairying: 0 in-window (of 6 entries, 0 malformed skipped, 4 chrome skipped)
01_source_fetch.log: [01_source_fetch] Department of Fisheries: 0 in-window (of 1 entries, 0 malformed skipped, 1 chrome skipped)
01_source_fetch.log: [01_source_fetch] APEDA: 0 in-window (of 7 entries, 0 malformed skipped, 3 chrome skipped)
01_source_fetch.log: [01_source_fetch] Department of Agriculture Research and Education: 0 in-window (of 0 entries, 0 malformed skipped, 0 chrome skipped)
01_source_fetch.log: [01_source_fetch] Indian Agricultural Research Institute: 0 in-window (of 15 entries, 0 malformed skipped, 6 chrome skipped)
01_source_fetch.log: [01_source_fetch] National Horticulture Board: 0 in-window (of 1 entries, 0 malformed skipped, 1 chrome skipped)
01_source_fetch.log: [01_source_fetch] FSSAI: 2 in-window (of 100 entries, 0 malformed skipped, 91 chrome skipped)
01_source_fetch.log: [01_source_fetch] ICFRE: 0 in-window (of 28 entries, 0 malformed skipped, 16 chrome skipped)
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
01_source_fetch.log: [01_source_fetch] Competition Commission of India: 1 in-window (of 77 entries, 0 malformed skipped, 55 chrome skipped)
01_source_fetch.log: [01_source_fetch] RBI Bulletin: 0 in-window (of 0 entries, 0 malformed skipped, 0 chrome skipped)
01_source_fetch.log: [01_source_fetch] India.gov.in: 8 in-window (of 100 entries, 0 malformed skipped, 29 chrome skipped)
01_source_fetch.log: [01_source_fetch] Prime Minister of India: 9 in-window (of 25 entries, 0 malformed skipped, 0 chrome skipped)
01_source_fetch.log: [01_source_fetch] Cabinet Secretariat: 0 in-window (of 1 entries, 0 malformed skipped, 1 chrome skipped)
01_source_fetch.log: [01_source_fetch] MyGov India: 7 in-window (of 100 entries, 0 malformed skipped, 62 chrome skipped)
01_source_fetch.log: [01_source_fetch] Ministry of Rural Development: 0 in-window (of 0 entries, 0 malformed skipped, 0 chrome skipped)
01_source_fetch.log: [01_source_fetch] Ministry of Cooperation: 1 in-window (of 9 entries, 0 malformed skipped, 2 chrome skipped)
01_source_fetch.log: [01_source_fetch] Department of Science and Technology: 5 in-window (of 100 entries, 0 malformed skipped, 62 chrome skipped)
01_source_fetch.log: [01_source_fetch] Department of Biotechnology: 0 in-window (of 0 entries, 0 malformed skipped, 0 chrome skipped)
01_source_fetch.log: [01_source_fetch] DRDO: 1 in-window (of 99 entries, 0 malformed skipped, 88 chrome skipped)
01_source_fetch.log: [01_source_fetch] Central Pollution Control Board: 0 in-window (of 7 entries, 0 malformed skipped, 5 chrome skipped)
01_source_fetch.log: [01_source_fetch] Ministry of Education: 1 in-window (of 25 entries, 0 malformed skipped, 9 chrome skipped)
01_source_fetch.log: [01_source_fetch] UGC: 0 in-window (of 1 entries, 0 malformed skipped, 1 chrome skipped)
01_source_fetch.log: [01_source_fetch] National Testing Agency: 0 in-window (of 0 entries, 0 malformed skipped, 0 chrome skipped)
01_source_fetch.log: [01_source_fetch] Ministry of Defence: 0 in-window (of 13 entries, 0 malformed skipped, 6 chrome skipped)
01_source_fetch.log: [01_source_fetch] President of India: 0 in-window (of 21 entries, 0 malformed skipped, 3 chrome skipped)
01_source_fetch.log: [01_source_fetch] Election Commission of India: 0 in-window (of 10 entries, 0 malformed skipped, 9 chrome skipped)
01_source_fetch.log: [01_source_fetch] UPSC: 0 in-window (of 4 entries, 0 malformed skipped, 0 chrome skipped)
01_source_fetch.log: [01_source_fetch] The Hindu: 0 in-window (of 60 entries, 0 malformed skipped, 0 chrome skipped)
01_source_fetch.log: [01_source_fetch] Mint: 0 in-window (of 35 entries, 0 malformed skipped, 0 chrome skipped)
01_source_fetch.log: [01_source_fetch] Economic Times: 0 in-window (of 53 entries, 0 malformed skipped, 1 chrome skipped)
01_source_fetch.log: [01_source_fetch] Google News India: 1 in-window (of 38 entries, 0 malformed skipped, 0 chrome skipped)
01_source_fetch.log: [01_source_fetch] Google News Search: 0 in-window (of 100 entries, 0 malformed skipped, 41 chrome skipped)
01_source_fetch.log: [01_source_fetch] wrote /home/runner/work/daily-current-affairs/daily-current-affairs/data/raw/daily_2026-10-15.json (38 articles, 50/57 feeds ok, 728 chrome skipped)
04_fact_verification.log: 2026-10-16 13:16:38 | WARNING  | pipeline.ai_router | [Router] gemini HTTP 429 (rate_limit): {
04_fact_verification.log: 2026-10-16 13:16:38 | WARNING  | pipeline.ai_router | [Router] Provider gemini disabled for 120s: rate limited
04_fact_verification.log: 2026-10-16 13:16:50 | WARNING  | pipeline.ai_router | [Router] groq HTTP 429 (rate_limit): {"error":{"message":"Rate limit reached for model `openai/gpt-oss-120b` in organization `org_01m4n8hsfce0q8z1yndppr2nmv` service 
04_fact_verification.log: 2026-10-16 13:16:50 | WARNING  | pipeline.ai_router | [Router] Provider groq disabled for 120s: rate limited
04_fact_verification.log: 2026-10-16 13:16:50 | WARNING  | pipeline.ai_router | [Router] openrouter HTTP 402 (auth_error): {"error":{"message":"This request requires more credits, or fewer max_tokens. You requested up to 16384 tokens, but can onl
04_fact_verification.log: 2026-10-16 13:16:50 | WARNING  | pipeline.ai_router | [Router] Provider openrouter disabled for 3600s: auth error
04_fact_verification.log: 2026-10-16 13:16:50 | WARNING  | pipeline.ai_router | [Router] mistral HTTP 429 (rate_limit): {"object":"error","message":"Rate limit exceeded","type":"rate_limited","param":null,"code":"1300","raw_status_code":429}
04_fact_verification.log: 2026-10-16 13:16:50 | WARNING  | pipeline.ai_router | [Router] Provider mistral disabled for 120s: rate limited
04_fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: mistral: rate_limit
04_fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
04_fact_verification.log: 2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
07_student_domain_relevance.log: WARNING:root:[STUDENT & DOMAIN RELEVANCE AGENT] sparse daily top-up: keep=6 (filled from next-best verified)
07_student_domain_relevance.log: INFO:root:[STUDENT & DOMAIN RELEVANCE AGENT] relevant=6/36 agri=2 banking=0
10_final_news_selection.log: 2026-10-16 13:16:51,050 | INFO     | root | [FINAL NEWS SELECTION AGENT v2] selected 6 items (target=28)
12_content_editor.log: 2026-10-16 13:16:51 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
12_content_editor.log: 2026-10-16 13:16:51 | WARNING  | pipeline.ai_translator | [Translator] groq rate-limited (429)
12_content_editor.log: 2026-10-16 13:16:51 | WARNING  | pipeline.ai_translator | [Translator] openrouter parked for 900s (HTTP 402)
12_content_editor.log: 2026-10-16 13:16:52 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
12_content_editor.log: 2026-10-16 13:16:52 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['gemini: rate limited', 'groq: rate limited', 'openrouter: HTTP 402', 'mistral: rate limited'])
12_content_editor.log: 2026-10-16 13:16:52 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:16:52 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:16:52 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:16:52 | WARNING  | pipeline.ai_router | [Router] gemini HTTP 429 (rate_limit): {
12_content_editor.log: 2026-10-16 13:16:52 | WARNING  | pipeline.ai_router | [Router] Provider gemini disabled for 120s: rate limited
12_content_editor.log: 2026-10-16 13:16:52 | WARNING  | pipeline.ai_router | [Router] groq HTTP 429 (rate_limit): {"error":{"message":"Rate limit reached for model `openai/gpt-oss-120b` in organization `org_01m4n8hsfce0q8z1yndppr2nmv` service 
12_content_editor.log: 2026-10-16 13:16:52 | WARNING  | pipeline.ai_router | [Router] Provider groq disabled for 120s: rate limited
12_content_editor.log: 2026-10-16 13:16:52 | WARNING  | pipeline.ai_router | [Router] openrouter HTTP 402 (auth_error): {"error":{"message":"This request requires more credits, or fewer max_tokens. You requested up to 16384 tokens, but can onl
12_content_editor.log: 2026-10-16 13:16:52 | WARNING  | pipeline.ai_router | [Router] Provider openrouter disabled for 3600s: auth error
12_content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.ai_router | [Router] mistral HTTP 429 (rate_limit): {"object":"error","message":"Rate limit exceeded","type":"rate_limited","param":null,"code":"1300","raw_status_code":429}
12_content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.ai_router | [Router] Provider mistral disabled for 120s: rate limited
12_content_editor.log: 2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: mistral: rate_limit
12_content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
12_content_editor.log: 2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
12_content_editor.log: 2026-10-16 13:16:53 | WARNING  | pipeline.content | [Content Builder] 26 translations need review (AI did not pass)
19_pdf_qa.log: 2026-10-16 13:16:58 | INFO     | agent.19_pdf_qa | QA requires at least 10 MCQs for 6 selected stories
19_pdf_qa.log: PDF QA REPORT — ✅ PASSED
19_pdf_qa.log: 2026-10-16 13:16:58 | INFO     | agent.19_pdf_qa | ✔ PDF QA passed — safe to publish
22_telegram_publisher.log: 2026-10-16 13:16:58 | WARNING  | agent.22_telegram_publisher | Adopted 10 unverifiable legacy publication row(s) as history
22_telegram_publisher.log: 2026-10-16 13:16:58 | INFO     | agent.22_telegram_publisher | [DRY-RUN] Would publish daily_2026-10-15.pdf (4383171 bytes) with caption:
23_telegram_pin_verifier.log: 2026-10-16 13:16:59 | INFO     | agent.23_telegram_pin_verifier | [DRY-RUN] No live publication receipt to pin.
telegram_publisher.log: 2026-10-16 13:16:58 | WARNING  | agent.22_telegram_publisher | Adopted 10 unverifiable legacy publication row(s) as history
telegram_publisher.log: 2026-10-16 13:16:58 | INFO     | agent.22_telegram_publisher | [DRY-RUN] Would publish daily_2026-10-15.pdf (4383171 bytes) with caption:
```

## Stage log tails

### content_editor.log

```
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:53 | INFO     | pipeline.content | [Content Builder] Translation stats: ai=0 fallback=26 untranslated=0 (AI success 0.0%)
2026-10-16 13:16:53 | WARNING  | pipeline.content | [Content Builder] 26 translations need review (AI did not pass)
```

### deduplication.log

```
2026-10-16 13:16:50 | INFO     | agent.05_deduplication | Input: 38 articles from daily_2026-10-15.json
2026-10-16 13:16:50 | INFO     | agent.05_deduplication | After URL dedup: 38
2026-10-16 13:16:50 | INFO     | agent.05_deduplication | After fingerprint dedup: 38
2026-10-16 13:16:50 | INFO     | agent.05_deduplication | After similarity clustering: 36
2026-10-16 13:16:50 | INFO     | agent.05_deduplication | ✔ Dedup complete: 38 → 36 (5.3% reduction)
```

### fact_verification.log

```
2026-10-16 13:16:47 | INFO     | pipeline.ai_router | [Router] ✔ groq responded (task=fact_verification, 66 chars)
2026-10-16 13:16:47 | INFO     | pipeline.ai_router | [Router] ✔ groq responded (task=fact_verification, 30 chars)
2026-10-16 13:16:48 | INFO     | pipeline.ai_router | [Router] ✔ groq responded (task=fact_verification, 141 chars)
2026-10-16 13:16:49 | INFO     | pipeline.ai_router | [Router] ✔ groq responded (task=fact_verification, 29 chars)
2026-10-16 13:16:50 | INFO     | pipeline.ai_router | [Router] ✔ groq responded (task=fact_verification, 76 chars)
2026-10-16 13:16:50 | WARNING  | pipeline.ai_router | [Router] groq HTTP 429 (rate_limit): {"error":{"message":"Rate limit reached for model `openai/gpt-oss-120b` in organization `org_01m4n8hsfce0q8z1yndppr2nmv` service 
2026-10-16 13:16:50 | WARNING  | pipeline.ai_router | [Router] Provider groq disabled for 120s: rate limited
2026-10-16 13:16:50 | WARNING  | pipeline.ai_router | [Router] openrouter HTTP 402 (auth_error): {"error":{"message":"This request requires more credits, or fewer max_tokens. You requested up to 16384 tokens, but can onl
2026-10-16 13:16:50 | WARNING  | pipeline.ai_router | [Router] Provider openrouter disabled for 3600s: auth error
2026-10-16 13:16:50 | WARNING  | pipeline.ai_router | [Router] mistral HTTP 429 (rate_limit): {"object":"error","message":"Rate limit exceeded","type":"rate_limited","param":null,"code":"1300","raw_status_code":429}
2026-10-16 13:16:50 | WARNING  | pipeline.ai_router | [Router] Provider mistral disabled for 120s: rate limited
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: mistral: rate_limit
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | INFO     | agent.04_fact_verification | Verification complete in 11.9s | 38 total | 38 passed | 0 rejected | 0 crashed
2026-10-16 13:16:50 | INFO     | agent.04_fact_verification | Avg confidence: 0.569
2026-10-16 13:16:50 | INFO     | agent.04_fact_verification | Methods: {'combined': 13, 'heuristic+cross_source': 25}
2026-10-16 13:16:50 | INFO     | agent.04_fact_verification | ✔ Fact verification completed: 38 items → /home/runner/work/daily-current-affairs/daily-current-affairs/data/verified/daily_2026-10-15.json
```

### orchestrator_00.log

```
2026-10-16 13:16:06 | INFO     | agent.00_model_orchestrator | Model orchestrator starting
2026-10-16 13:16:07 | INFO     | agent.00_model_orchestrator | Checking gemini (model=gemini-flash-latest)
2026-10-16 13:16:07 | INFO     | agent.00_model_orchestrator |   ❌ gemini → rate_limit
2026-10-16 13:16:07 | INFO     | agent.00_model_orchestrator | Checking groq (model=openai/gpt-oss-120b)
2026-10-16 13:16:07 | INFO     | agent.00_model_orchestrator |   ❌ groq → malformed
2026-10-16 13:16:07 | INFO     | agent.00_model_orchestrator | Checking openrouter (model=openai/gpt-4o-mini)
2026-10-16 13:16:12 | INFO     | agent.00_model_orchestrator |   ✅ openrouter → ok
2026-10-16 13:16:12 | INFO     | agent.00_model_orchestrator | Checking mistral (model=mistral-small-latest)
2026-10-16 13:16:13 | INFO     | agent.00_model_orchestrator |   ❌ mistral → rate_limit
2026-10-16 13:16:13 | INFO     | agent.00_model_orchestrator | Model status: 1/4 healthy → /home/runner/work/daily-current-affairs/daily-current-affairs/state/model_status.json
```

### pdf_design.log

```
```

### pdf_qa.log

```
2026-10-16 13:16:58 | INFO     | agent.19_pdf_qa | QA check: daily_2026-10-15.pdf
2026-10-16 13:16:58 | INFO     | agent.19_pdf_qa | QA requires at least 10 MCQs for 6 selected stories
2026-10-16 13:16:58 | INFO     | agent.19_pdf_qa | Report: /home/runner/work/daily-current-affairs/daily-current-affairs/logs/qa/daily_2026-10-15_qa.json
2026-10-16 13:16:58 | INFO     | agent.19_pdf_qa | ✔ PDF QA passed — safe to publish
```

### pin_verifier.log

```
2026-10-16 13:16:59 | INFO     | agent.23_telegram_pin_verifier | [DRY-RUN] No live publication receipt to pin.
```

### 00_model_orchestrator.log

```
--- attempt 1; exit 0 ---
2026-10-16 13:16:06 | INFO     | agent.00_model_orchestrator | Model orchestrator starting
2026-10-16 13:16:07 | INFO     | agent.00_model_orchestrator | Checking gemini (model=gemini-flash-latest)
2026-10-16 13:16:07 | INFO     | agent.00_model_orchestrator |   ❌ gemini → rate_limit
2026-10-16 13:16:07 | INFO     | agent.00_model_orchestrator | Checking groq (model=openai/gpt-oss-120b)
2026-10-16 13:16:07 | INFO     | agent.00_model_orchestrator |   ❌ groq → malformed
2026-10-16 13:16:07 | INFO     | agent.00_model_orchestrator | Checking openrouter (model=openai/gpt-4o-mini)
2026-10-16 13:16:12 | INFO     | agent.00_model_orchestrator |   ✅ openrouter → ok
2026-10-16 13:16:12 | INFO     | agent.00_model_orchestrator | Checking mistral (model=mistral-small-latest)
2026-10-16 13:16:13 | INFO     | agent.00_model_orchestrator |   ❌ mistral → rate_limit
2026-10-16 13:16:13 | INFO     | agent.00_model_orchestrator | Model status: 1/4 healthy → /home/runner/work/daily-current-affairs/daily-current-affairs/state/model_status.json
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/requests/__init__.py:113: RequestsDependencyWarning: urllib3 (2.2.3) or chardet (7.6.0)/charset_normalizer (3.4.0) doesn't match a supported version!
  warnings.warn(
```

### 01_source_fetch.log

```
[01_source_fetch] PFRDA: 0 in-window (of 12 entries, 0 malformed skipped, 2 chrome skipped)
[01_source_fetch] IRDAI: 0 in-window (of 0 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] IFSCA: 0 in-window (of 85 entries, 0 malformed skipped, 81 chrome skipped)
[01_source_fetch] Department of Financial Services: 0 in-window (of 20 entries, 0 malformed skipped, 14 chrome skipped)
[01_source_fetch] Union Budget of India: 0 in-window (of 2 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] GST Council: 0 in-window (of 27 entries, 0 malformed skipped, 26 chrome skipped)
[01_source_fetch] Competition Commission of India: 1 in-window (of 77 entries, 0 malformed skipped, 55 chrome skipped)
[01_source_fetch] RBI Bulletin: 0 in-window (of 0 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] India.gov.in: 8 in-window (of 100 entries, 0 malformed skipped, 29 chrome skipped)
[01_source_fetch] Prime Minister of India: 9 in-window (of 25 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] Cabinet Secretariat: 0 in-window (of 1 entries, 0 malformed skipped, 1 chrome skipped)
[01_source_fetch] MyGov India: 7 in-window (of 100 entries, 0 malformed skipped, 62 chrome skipped)
[01_source_fetch] Ministry of Rural Development: 0 in-window (of 0 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] Ministry of Cooperation: 1 in-window (of 9 entries, 0 malformed skipped, 2 chrome skipped)
[01_source_fetch] Department of Science and Technology: 5 in-window (of 100 entries, 0 malformed skipped, 62 chrome skipped)
[01_source_fetch] Department of Biotechnology: 0 in-window (of 0 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] DRDO: 1 in-window (of 99 entries, 0 malformed skipped, 88 chrome skipped)
[01_source_fetch] Central Pollution Control Board: 0 in-window (of 7 entries, 0 malformed skipped, 5 chrome skipped)
[01_source_fetch] Ministry of Education: 1 in-window (of 25 entries, 0 malformed skipped, 9 chrome skipped)
[01_source_fetch] UGC: 0 in-window (of 1 entries, 0 malformed skipped, 1 chrome skipped)
[01_source_fetch] National Testing Agency: 0 in-window (of 0 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] Ministry of Defence: 0 in-window (of 13 entries, 0 malformed skipped, 6 chrome skipped)
[01_source_fetch] President of India: 0 in-window (of 21 entries, 0 malformed skipped, 3 chrome skipped)
[01_source_fetch] Election Commission of India: 0 in-window (of 10 entries, 0 malformed skipped, 9 chrome skipped)
[01_source_fetch] UPSC: 0 in-window (of 4 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] The Hindu: 0 in-window (of 60 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] Mint: 0 in-window (of 35 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] Economic Times: 0 in-window (of 53 entries, 0 malformed skipped, 1 chrome skipped)
[01_source_fetch] Google News India: 1 in-window (of 38 entries, 0 malformed skipped, 0 chrome skipped)
[01_source_fetch] Google News Search: 0 in-window (of 100 entries, 0 malformed skipped, 41 chrome skipped)
[01_source_fetch] wrote /home/runner/work/daily-current-affairs/daily-current-affairs/data/raw/daily_2026-10-15.json (38 articles, 50/57 feeds ok, 728 chrome skipped)
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/requests/__init__.py:113: RequestsDependencyWarning: urllib3 (2.2.3) or chardet (7.6.0)/charset_normalizer (3.4.0) doesn't match a supported version!
  warnings.warn(
[01_source_fetch] WARN feed failed: Indian Express -> HTTP 403 to the default user agent; HTTPError: 403 Client Error: Forbidden for url: https://indianexpress.com/feed/
[01_source_fetch] WARN feed failed: PIB — Press Information Bureau -> HTTP 403 to the default user agent; HTTPError: 403 Client Error: Forbidden for url: https://www.pib.gov.in/ViewRss.aspx?lang=1&reg=1
[01_source_fetch] WARN feed failed: SEBI -> feed returned an HTML page (blocked or moved)
[01_source_fetch] WARN feed failed: NITI Aayog -> HTTP 403 to the default user agent; HTTPError: 403 Client Error: Forbidden for url: https://www.niti.gov.in/rss.xml
[01_source_fetch] WARN feed failed: Ministry of External Affairs -> HTTP 403 to the default user agent; HTTPError: 403 Client Error: Forbidden for url: https://www.mea.gov.in/rss-feeds.htm
[01_source_fetch] WARN feed failed: Reuters -> HTTPError: 404 Client Error: Not Found for url: https://reutersagency.com/feed/?best-topics=tech&post_type=best; HTTPError: 404 Client Error: Not Found for url: https://reut
[01_source_fetch] WARN feed failed: Business Standard -> HTTP 403 to the default user agent; HTTPError: 403 Client Error: Forbidden for url: https://www.business-standard.com/rss/latest.rss
```

### 04_fact_verification.log

```
2026-10-16 13:16:48 | INFO     | pipeline.ai_router | [Router] ✔ groq responded (task=fact_verification, 141 chars)
2026-10-16 13:16:49 | INFO     | pipeline.ai_router | [Router] ✔ groq responded (task=fact_verification, 29 chars)
2026-10-16 13:16:50 | INFO     | pipeline.ai_router | [Router] ✔ groq responded (task=fact_verification, 76 chars)
2026-10-16 13:16:50 | WARNING  | pipeline.ai_router | [Router] groq HTTP 429 (rate_limit): {"error":{"message":"Rate limit reached for model `openai/gpt-oss-120b` in organization `org_01m4n8hsfce0q8z1yndppr2nmv` service 
2026-10-16 13:16:50 | WARNING  | pipeline.ai_router | [Router] Provider groq disabled for 120s: rate limited
2026-10-16 13:16:50 | WARNING  | pipeline.ai_router | [Router] openrouter HTTP 402 (auth_error): {"error":{"message":"This request requires more credits, or fewer max_tokens. You requested up to 16384 tokens, but can onl
2026-10-16 13:16:50 | WARNING  | pipeline.ai_router | [Router] Provider openrouter disabled for 3600s: auth error
2026-10-16 13:16:50 | WARNING  | pipeline.ai_router | [Router] mistral HTTP 429 (rate_limit): {"object":"error","message":"Rate limit exceeded","type":"rate_limited","param":null,"code":"1300","raw_status_code":429}
2026-10-16 13:16:50 | WARNING  | pipeline.ai_router | [Router] Provider mistral disabled for 120s: rate limited
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: mistral: rate_limit
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:50 | INFO     | agent.04_fact_verification | Verification complete in 11.9s | 38 total | 38 passed | 0 rejected | 0 crashed
2026-10-16 13:16:50 | INFO     | agent.04_fact_verification | Avg confidence: 0.569
2026-10-16 13:16:50 | INFO     | agent.04_fact_verification | Methods: {'combined': 13, 'heuristic+cross_source': 25}
2026-10-16 13:16:50 | INFO     | agent.04_fact_verification | ✔ Fact verification completed: 38 items → /home/runner/work/daily-current-affairs/daily-current-affairs/data/verified/daily_2026-10-15.json
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/requests/__init__.py:113: RequestsDependencyWarning: urllib3 (2.2.3) or chardet (7.6.0)/charset_normalizer (3.4.0) doesn't match a supported version!
  warnings.warn(
```

### 05_deduplication.log

```
--- attempt 1; exit 0 ---
2026-10-16 13:16:50 | INFO     | agent.05_deduplication | Input: 38 articles from daily_2026-10-15.json
2026-10-16 13:16:50 | INFO     | agent.05_deduplication | After URL dedup: 38
2026-10-16 13:16:50 | INFO     | agent.05_deduplication | After fingerprint dedup: 38
2026-10-16 13:16:50 | INFO     | agent.05_deduplication | After similarity clustering: 36
2026-10-16 13:16:50 | INFO     | agent.05_deduplication | ✔ Dedup complete: 38 → 36 (5.3% reduction)
```

### 06_news_importance.log

```
--- attempt 1; exit 0 ---
[06_news_importance] job=daily_2026-10-15 type=daily date=2026-10-15
[06] OK — scored=36
2026-10-16 13:16:50,929 | INFO     | root | [NEWS IMPORTANCE AGENT] scored 36 events, top=24
```

### 07_student_domain_relevance.log

```
--- attempt 1; exit 0 ---
WARNING:root:[STUDENT & DOMAIN RELEVANCE AGENT] sparse daily top-up: keep=6 (filled from next-best verified)
INFO:root:[STUDENT & DOMAIN RELEVANCE AGENT] relevant=6/36 agri=2 banking=0
```

### 10_final_news_selection.log

```
--- attempt 1; exit 0 ---
[10_final_news_selection] job=daily_2026-10-15 type=daily date=2026-10-15
[10] OK — selected_count=6
2026-10-16 13:16:51,050 | INFO     | root | [FINAL NEWS SELECTION AGENT v2] selected 6 items (target=28)
2026-10-16 13:16:51,050 | INFO     | root |   National: 3
2026-10-16 13:16:51,051 | INFO     | root |   Agriculture: 2
2026-10-16 13:16:51,051 | INFO     | root |   Economy: 1
```

### 11_importance_memory.log

```
--- attempt 1; exit 0 ---
INFO:root:[IMPORTANCE MEMORY AGENT] memory updated for 6 events (local + persistent)
```

### 12_content_editor.log

```
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['no usable providers available'])
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['no usable providers available'])
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping gemini (rate limited or parked earlier)
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping groq (rate limited or parked earlier)
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping openrouter (rate limited or parked earlier)
2026-10-16 13:16:53 | INFO     | pipeline.ai_translator | [Translator] skipping mistral (rate limited or parked earlier)
2026-10-16 13:16:53 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['no usable providers available'])
2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:53 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: None
2026-10-16 13:16:53 | INFO     | pipeline.content | [Content Builder] Translation stats: ai=0 fallback=26 untranslated=0 (AI success 0.0%)
2026-10-16 13:16:53 | WARNING  | pipeline.content | [Content Builder] 26 translations need review (AI did not pass)
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/requests/__init__.py:113: RequestsDependencyWarning: urllib3 (2.2.3) or chardet (7.6.0)/charset_normalizer (3.4.0) doesn't match a supported version!
  warnings.warn(
```

### 16_mcq_generator.log

```
--- attempt 1; exit 0 ---
INFO:root:[MCQ GENERATOR AGENT v4 (FAIL-CLOSED)] Generating MCQs for 6 items...
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
2026-10-16 13:16:58 | INFO     | agent.19_pdf_qa | QA check: daily_2026-10-15.pdf
2026-10-16 13:16:58 | INFO     | agent.19_pdf_qa | QA requires at least 10 MCQs for 6 selected stories
2026-10-16 13:16:58 | INFO     | agent.19_pdf_qa | Report: /home/runner/work/daily-current-affairs/daily-current-affairs/logs/qa/daily_2026-10-15_qa.json
========================================================================
PDF QA REPORT — ✅ PASSED
========================================================================
File:            /home/runner/work/daily-current-affairs/daily-current-affairs/output/daily_2026-10-15.pdf
Size:            4280 KB
Pages:           17
Chars:           29744
Devanagari:      1673 (5.6%)
Fonts:           6 (AAAAAA+Mukta-Bold, AAAAAA+Mukta-Regular, AAAAAA+Poppins-Bold...)
MCQs:            17
Answer markers:  15
Duplicate Qs:    0
URLs:            59
Images:          93
Blank pages:     none
--- Issues ---
  ⚠️  [low_hindi] Hindi coverage 5.6% is low
  ⚠️  [text_overflow] Text may overflow page bounds on pages: [14]
========================================================================
2026-10-16 13:16:58 | INFO     | agent.19_pdf_qa | ✔ PDF QA passed — safe to publish
```

### 22_telegram_publisher.log

```
--- attempt 1; exit 0 ---
2026-10-16 13:16:58 | INFO     | agent.22_telegram_publisher | Found 1 candidate PDF(s) (max 5 per run)
2026-10-16 13:16:58 | WARNING  | agent.22_telegram_publisher | Adopted 10 unverifiable legacy publication row(s) as history
2026-10-16 13:16:58 | INFO     | agent.22_telegram_publisher | [1/1] daily_2026-10-15.pdf
2026-10-16 13:16:58 | INFO     | agent.22_telegram_publisher | [DRY-RUN] Would publish daily_2026-10-15.pdf (4383171 bytes) with caption:
<b>&gt;&gt; Significant Weather Observations Stations Rainfall (in mm) - IMD</b>
&lt;a href="https://news.google.com/rss/articles/CBMia0FVX3lxTE93QnV1QWRHZnEzSXdRQjB1NXl2S0hpSTAxaF9reGlCZVcwaktLUkFKL
2026-10-16 13:16:58 | INFO     | agent.22_telegram_publisher | Publishing complete: success=1 failed=0 skipped=0 total=1
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/requests/__init__.py:113: RequestsDependencyWarning: urllib3 (2.2.3) or chardet (7.6.0)/charset_normalizer (3.4.0) doesn't match a supported version!
  warnings.warn(
```

### 23_telegram_pin_verifier.log

```
--- attempt 1; exit 0 ---
2026-10-16 13:16:59 | INFO     | agent.23_telegram_pin_verifier | [DRY-RUN] No live publication receipt to pin.
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/requests/__init__.py:113: RequestsDependencyWarning: urllib3 (2.2.3) or chardet (7.6.0)/charset_normalizer (3.4.0) doesn't match a supported version!
  warnings.warn(
```

### 24_final_health_audit.log

```
--- attempt 1; exit 0 ---
{"job_id": "daily_2026-10-15", "passed": true, "dry_run": true, "issues": [], "checked_at": "2026-10-16T13:16:59.181949+00:00"}
```

### telegram_publisher.log

```
2026-10-16 13:16:58 | INFO     | agent.22_telegram_publisher | Found 1 candidate PDF(s) (max 5 per run)
2026-10-16 13:16:58 | WARNING  | agent.22_telegram_publisher | Adopted 10 unverifiable legacy publication row(s) as history
2026-10-16 13:16:58 | INFO     | agent.22_telegram_publisher | [1/1] daily_2026-10-15.pdf
2026-10-16 13:16:58 | INFO     | agent.22_telegram_publisher | [DRY-RUN] Would publish daily_2026-10-15.pdf (4383171 bytes) with caption:
<b>&gt;&gt; Significant Weather Observations Stations Rainfall (in mm) - IMD</b>
&lt;a href="https://news.google.com/rss/articles/CBMia0FVX3lxTE93QnV1QWRHZnEzSXdRQjB1NXl2S0hpSTAxaF9reGlCZVcwaktLUkFKL
2026-10-16 13:16:58 | INFO     | agent.22_telegram_publisher | Publishing complete: success=1 failed=0 skipped=0 total=1
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

- https://github.com/agrilearningpoint/daily-current-affairs/releases/tag/untagged-c0ad05548b0f13159d27 (draft release asset; no Telegram publication was made)
