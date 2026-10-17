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

- https://github.com/agrilearningpoint/daily-current-affairs/releases/tag/untagged-d504c28480e1c3e8fb6a (draft release asset; no Telegram publication was made)
