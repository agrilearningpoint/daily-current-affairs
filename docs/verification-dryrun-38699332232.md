# Dry-run evidence — run 38699332232

- run URL: https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/38699332232
- edition: 2026-10-15 (DRY_RUN=1)

## Article counts

| stage | count |
|---|---|
| raw | 553 |
| verified | 553 |
| dedup | 426 |
| scored | 32 |
| selected | 28 |
| content | 28 |
| mcq | 15 |

## Selected categories

```
{
 "Agriculture": 7,
 "Banking & Finance": 7,
 "Economy": 3,
 "National": 11
}
```

## PDF qa report

```json
{
  "pdf_path": "/home/runner/work/daily-current-affairs/daily-current-affairs/output/daily_2026-10-15.pdf",
  "checked_at": "2026-10-15T07:32:16.212846+00:00",
  "passed": true,
  "page_count": 32,
  "file_size_bytes": 8470667,
  "devanagari_chars": 4046,
  "total_chars": 53745,
  "hindi_pct": 7.53,
  "font_names": [
    "AAAAAA+Mukta-Bold",
    "AAAAAA+Mukta-Regular",
    "AAAAAA+Poppins-Bold",
    "AAAAAA+Poppins-Regular",
    "AAAAAA+Poppins-SemiBold",
    "Helvetica"
  ],
  "mcq_count": 16,
  "answers_found": 15,
  "duplicate_questions": 0,
  "urls_found": 34,
  "blank_pages": [],
  "image_xobjects": 250,
  "issues": [
    {
      "severity": "warning",
      "code": "low_hindi",
      "message": "Hindi coverage 7.5% is low",
      "details": {
        "hindi_pct": 7.53
      }
    },
    {
      "severity": "warning",
      "code": "text_overflow",
      "message": "Text may overflow page bounds on pages: [10]",
      "details": {
        "pages": [
          10
        ]
      }
    }
  ],
  "job_id": "daily_2026-10-15",
  "file_sha256": "78b89245baae03126a72071ef724ecaea3da885f526f9828536ab2c493a0caf8"
}
```

## PDF health report

```json
{
  "job_id": "daily_2026-10-15",
  "passed": true,
  "dry_run": true,
  "issues": [],
  "checked_at": "2026-10-15T07:32:16.939657+00:00"
}
```

## Stage log inventory

| log | lines | first | last |
|---|---|---|---|
| content_editor.log | 134 | 2026-10-15 07:31:55 | 2026-10-15 07:32:04 |
| pdf_qa.log | 3 | 2026-10-15 07:32:16 | 2026-10-15 07:32:16 |
| pin_verifier.log | 1 | 2026-10-15 07:32:16 | 2026-10-15 07:32:16 |
| 12_content_editor.log | 137 | --- attempt 1; exit |   warnings.warn( |
| 16_mcq_generator.log | 7 | --- attempt 1; exit | INFO:root:[MCQ GENE |
| 17_mcq_validator.log | 6 | --- attempt 1; exit | INFO:root:[MCQ VALI |
| 18_pdf_design.log | 3 | --- attempt 1; exit | [OK] PDF generated: |
| 19_pdf_qa.log | 23 | --- attempt 1; exit | 2026-10-15 07:32:16 |
| 22_telegram_publisher.log | 10 | --- attempt 1; exit |   warnings.warn( |
| 23_telegram_pin_verifier.log | 4 | --- attempt 1; exit |   warnings.warn( |
| 24_final_health_audit.log | 2 | --- attempt 1; exit | {"job_id": "daily_2 |
| telegram_publisher.log | 7 | 2026-10-15 07:32:16 | 2026-10-15 07:32:16 |

## Log excerpts (retries / skips / QA)

```
content_editor.log: 2026-10-15 07:31:55 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 07:31:55 | WARNING  | pipeline.ai_translator | [Translator] gemini parked for 600s (HTTP 429 rate limit)
content_editor.log: 2026-10-15 07:31:57 | WARNING  | pipeline.ai_translator | [Translator] groq rejected credentials/request (404)
content_editor.log: 2026-10-15 07:31:57 | WARNING  | pipeline.ai_translator | [Translator] groq parked for 3600s (HTTP 404)
content_editor.log: 2026-10-15 07:31:59 | WARNING  | pipeline.ai_translator | [Translator] openrouter rejected credentials/request (402)
content_editor.log: 2026-10-15 07:31:59 | WARNING  | pipeline.ai_translator | [Translator] openrouter parked for 3600s (HTTP 402)
content_editor.log: 2026-10-15 07:32:01 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 07:32:01 | WARNING  | pipeline.ai_translator | [Translator] mistral parked for 600s (HTTP 429 rate limit)
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Content Builder] 121 translations need review (AI did not pass)
pdf_qa.log: 2026-10-15 07:32:16 | INFO     | agent.19_pdf_qa | ✔ PDF QA passed — safe to publish
pin_verifier.log: 2026-10-15 07:32:16 | INFO     | agent.23_telegram_pin_verifier | [DRY-RUN] No live publication receipt to pin.
12_content_editor.log: 2026-10-15 07:31:55 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
12_content_editor.log: 2026-10-15 07:31:55 | WARNING  | pipeline.ai_translator | [Translator] gemini parked for 600s (HTTP 429 rate limit)
12_content_editor.log: 2026-10-15 07:31:57 | WARNING  | pipeline.ai_translator | [Translator] groq rejected credentials/request (404)
12_content_editor.log: 2026-10-15 07:31:57 | WARNING  | pipeline.ai_translator | [Translator] groq parked for 3600s (HTTP 404)
12_content_editor.log: 2026-10-15 07:31:59 | WARNING  | pipeline.ai_translator | [Translator] openrouter rejected credentials/request (402)
12_content_editor.log: 2026-10-15 07:31:59 | WARNING  | pipeline.ai_translator | [Translator] openrouter parked for 3600s (HTTP 402)
12_content_editor.log: 2026-10-15 07:32:01 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
12_content_editor.log: 2026-10-15 07:32:01 | WARNING  | pipeline.ai_translator | [Translator] mistral parked for 600s (HTTP 429 rate limit)
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
12_content_editor.log: 2026-10-15 07:32:04 | WARNING  | pipeline.content | [Content Builder] 121 translations need review (AI did not pass)
19_pdf_qa.log: PDF QA REPORT — ✅ PASSED
19_pdf_qa.log: 2026-10-15 07:32:16 | INFO     | agent.19_pdf_qa | ✔ PDF QA passed — safe to publish
22_telegram_publisher.log: 2026-10-15 07:32:16 | WARNING  | agent.22_telegram_publisher | Publication ledger used the pre-versioned flat schema; adopted 10 legacy entr(ies) as legacy_unknown (live resend of those editions stays blocked until manua
22_telegram_publisher.log: 2026-10-15 07:32:16 | INFO     | agent.22_telegram_publisher | [DRY-RUN] Would publish daily_2026-10-15.pdf (8470667 bytes) with caption:
23_telegram_pin_verifier.log: 2026-10-15 07:32:16 | INFO     | agent.23_telegram_pin_verifier | [DRY-RUN] No live publication receipt to pin.
telegram_publisher.log: 2026-10-15 07:32:16 | WARNING  | agent.22_telegram_publisher | Publication ledger used the pre-versioned flat schema; adopted 10 legacy entr(ies) as legacy_unknown (live resend of those editions stays blocked until manua
telegram_publisher.log: 2026-10-15 07:32:16 | INFO     | agent.22_telegram_publisher | [DRY-RUN] Would publish daily_2026-10-15.pdf (8470667 bytes) with caption:
```

## Stage log tails

### content_editor.log

```
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | INFO     | pipeline.content | [Content Builder] Translation stats: ai=0 fallback=121 untranslated=0 (AI success 0.0%)
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Content Builder] 121 translations need review (AI did not pass)
```

### pdf_design.log

```
```

### pdf_qa.log

```
2026-10-15 07:32:16 | INFO     | agent.19_pdf_qa | QA check: daily_2026-10-15.pdf
2026-10-15 07:32:16 | INFO     | agent.19_pdf_qa | Report: /home/runner/work/daily-current-affairs/daily-current-affairs/logs/qa/daily_2026-10-15_qa.json
2026-10-15 07:32:16 | INFO     | agent.19_pdf_qa | ✔ PDF QA passed — safe to publish
```

### pin_verifier.log

```
2026-10-15 07:32:16 | INFO     | agent.23_telegram_pin_verifier | [DRY-RUN] No live publication receipt to pin.
```

### 12_content_editor.log

```
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['all providers parked after failures'])
2026-10-15 07:32:04 | INFO     | pipeline.content | [Content Builder] Translation stats: ai=0 fallback=121 untranslated=0 (AI success 0.0%)
2026-10-15 07:32:04 | WARNING  | pipeline.content | [Content Builder] 121 translations need review (AI did not pass)
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/requests/__init__.py:113: RequestsDependencyWarning: urllib3 (2.2.3) or chardet (7.6.0)/charset_normalizer (3.4.0) doesn't match a supported version!
  warnings.warn(
```

### 16_mcq_generator.log

```
--- attempt 1; exit 0 ---
INFO:root:[MCQ GENERATOR AGENT v4 (FAIL-CLOSED)] Generating MCQs for 28 items...
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
2026-10-15 07:32:16 | INFO     | agent.19_pdf_qa | QA check: daily_2026-10-15.pdf
2026-10-15 07:32:16 | INFO     | agent.19_pdf_qa | Report: /home/runner/work/daily-current-affairs/daily-current-affairs/logs/qa/daily_2026-10-15_qa.json
========================================================================
PDF QA REPORT — ✅ PASSED
========================================================================
File:            /home/runner/work/daily-current-affairs/daily-current-affairs/output/daily_2026-10-15.pdf
Size:            8272 KB
Pages:           32
Chars:           53745
Devanagari:      4046 (7.5%)
Fonts:           6 (AAAAAA+Mukta-Bold, AAAAAA+Mukta-Regular, AAAAAA+Poppins-Bold...)
MCQs:            16
Answer markers:  15
Duplicate Qs:    0
URLs:            34
Images:          250
Blank pages:     none
--- Issues ---
  ⚠️  [low_hindi] Hindi coverage 7.5% is low
  ⚠️  [text_overflow] Text may overflow page bounds on pages: [10]
========================================================================
2026-10-15 07:32:16 | INFO     | agent.19_pdf_qa | ✔ PDF QA passed — safe to publish
```

### 22_telegram_publisher.log

```
--- attempt 1; exit 0 ---
2026-10-15 07:32:16 | INFO     | agent.22_telegram_publisher | Found 1 candidate PDF(s) (max 5 per run)
2026-10-15 07:32:16 | WARNING  | agent.22_telegram_publisher | Publication ledger used the pre-versioned flat schema; adopted 10 legacy entr(ies) as legacy_unknown (live resend of those editions stays blocked until manua
2026-10-15 07:32:16 | INFO     | agent.22_telegram_publisher | [1/1] daily_2026-10-15.pdf
2026-10-15 07:32:16 | INFO     | agent.22_telegram_publisher | [DRY-RUN] Would publish daily_2026-10-15.pdf (8470667 bytes) with caption:
<b>&gt;&gt; 2026-10-14 Time of Issue: 13:25:00 hours IST (Mid-Day) ALL INDIA WEATHER SUMMARY AND FORECAST BULLETIN Significant Weather Featu - IMD</b>
&lt;a href="https://news.google.com/rss/articles
2026-10-15 07:32:16 | INFO     | agent.22_telegram_publisher | Publishing complete: success=1 failed=0 skipped=0 total=1
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/requests/__init__.py:113: RequestsDependencyWarning: urllib3 (2.2.3) or chardet (7.6.0)/charset_normalizer (3.4.0) doesn't match a supported version!
  warnings.warn(
```

### 23_telegram_pin_verifier.log

```
--- attempt 1; exit 0 ---
2026-10-15 07:32:16 | INFO     | agent.23_telegram_pin_verifier | [DRY-RUN] No live publication receipt to pin.
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/requests/__init__.py:113: RequestsDependencyWarning: urllib3 (2.2.3) or chardet (7.6.0)/charset_normalizer (3.4.0) doesn't match a supported version!
  warnings.warn(
```

### 24_final_health_audit.log

```
--- attempt 1; exit 0 ---
{"job_id": "daily_2026-10-15", "passed": true, "dry_run": true, "issues": [], "checked_at": "2026-10-15T07:32:16.939657+00:00"}
```

### telegram_publisher.log

```
2026-10-15 07:32:16 | INFO     | agent.22_telegram_publisher | Found 1 candidate PDF(s) (max 5 per run)
2026-10-15 07:32:16 | WARNING  | agent.22_telegram_publisher | Publication ledger used the pre-versioned flat schema; adopted 10 legacy entr(ies) as legacy_unknown (live resend of those editions stays blocked until manua
2026-10-15 07:32:16 | INFO     | agent.22_telegram_publisher | [1/1] daily_2026-10-15.pdf
2026-10-15 07:32:16 | INFO     | agent.22_telegram_publisher | [DRY-RUN] Would publish daily_2026-10-15.pdf (8470667 bytes) with caption:
<b>&gt;&gt; 2026-10-14 Time of Issue: 13:25:00 hours IST (Mid-Day) ALL INDIA WEATHER SUMMARY AND FORECAST BULLETIN Significant Weather Featu - IMD</b>
&lt;a href="https://news.google.com/rss/articles
2026-10-15 07:32:16 | INFO     | agent.22_telegram_publisher | Publishing complete: success=1 failed=0 skipped=0 total=1
```

## Committed state at collection time

```json
{
 "status": "failed",
 "dry_run": true,
 "last_success_stage": "11_importance_memory",
 "failed_stage": "12_content_editor",
 "checkpoint_run_id": "38693854648",
 "last_error": "12_content_editor: failed after 3 attempt(s): timeout after 900s"
}
```
