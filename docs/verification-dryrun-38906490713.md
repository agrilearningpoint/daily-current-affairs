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

> Full stage-log excerpts and tails are not kept in the repository; they are
> attached to the run as the `daily-logs-<run id>` artifact and can be
> regenerated with `COLLECT_RUN_ID=<run id> FULL_EVIDENCE=1` on the
> dry-run dispatcher.

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
