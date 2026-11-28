# Master Architecture — Agri Learning Point Newsroom Platform

> **Brand:** Agri Learning Point (By Satyam Sir & Team)
> **Scope:** Daily, Weekly, and Monthly Bilingual (English + Hindi) Current Affairs & MCQ Magazine Publishing Engine

---

## 1. Architectural Overview

Agri Learning Point operates as a **Master-Supervised Autonomous Editorial & Publishing Pipeline** orchestrated by [`main.py`](../main.py) and [`pipeline/supervisor.py`](../pipeline/supervisor.py). Every edition progresses through a deterministic checkpoint graph recorded atomically in `state/jobs.json`.

### Control Loop (`MasterSupervisor`)

Each pipeline stage executes inside a bounded self-repairing cycle defined in [`config/supervisor_policy.json`](../config/supervisor_policy.json):

```text
PLAN -> EXECUTE -> OBSERVE -> CRITIQUE -> (bounded REPAIR + downstream hash invalidation + RETEST) -> APPROVE / REJECT
```

Key architectural guarantees:
1. **Atomic State & Checkpoint Integrity:** Every JSON write flows through `pipeline.persistence.write_json_atomic` (`*.tmp` flush + `fsync` + `os.replace`) with cross-stage SHA-256 verification via `pipeline.checkpoints`.
2. **Stale Downstream Invalidation:** When a stage repairs or re-runs, `MasterSupervisor` automatically invalidates downstream checkpoint hashes so later stages never consume stale artifacts.
3. **Fail-Closed Verification & Publication:** Unverified claims, unreviewed Hindi translations, invalid MCQs, failed PDF QA reports, or unapproved release signatures halt publication before Telegram dispatch.

---

## 2. Pipeline Stage Topology

| Edition | Stage Sequence | Primary Output |
|---|---|---|
| **Daily** | `00` Health -> `01` Fetch -> `04` Verify -> `05` Dedup -> `06` Score -> `07` Relevance -> `10` Select -> `11` Memory -> `12` Content -> `16` MCQ -> `17` MCQ Validate & Examine -> `17b` Auto Sections -> `17c` Static GK Validate -> `18` PDF Design -> `19` PDF & Visual QA -> `22` Telegram Publish -> `23` Pin Verify -> `24` Health Audit & Report | `output/daily_<YYYY-MM-DD>.pdf` |
| **Weekly** | Fetch Daily Artifacts -> `20_weekly_editor` (`period_builder`) -> `17c` Static GK Validate -> `18` PDF Design -> `19` PDF QA -> `22` Publish -> `23` Pin Verify -> `24` Audit & Report | `output/weekly_<YYYY-MM-DD>.pdf` |
| **Monthly** | Fetch Daily/Weekly Artifacts -> `21_monthly_editor` (`period_builder`) -> `17c` Static GK Validate -> `18` PDF Design -> `19` PDF QA -> `22` Publish -> `23` Pin Verify -> `24` Audit & Report | `output/monthly_<YYYY-MM-DD>.pdf` |

---

## 3. Core Subsystems

- **Source Collection & Windows:** [`pipeline/01_source_fetch.py`](../pipeline/01_source_fetch.py), [`pipeline/windows.py`](../pipeline/windows.py), [`pipeline/freshness.py`](../pipeline/freshness.py).
- **Multi-Key AI Routing & Observability:** [`pipeline/ai_router.py`](../pipeline/ai_router.py), [`pipeline/ai_usage.py`](../pipeline/ai_usage.py).
- **Fact Verification & Scoring:** [`agents/04_fact_verification.py`](../agents/04_fact_verification.py), [`pipeline/claim_verifier.py`](../pipeline/claim_verifier.py), [`pipeline/scoring.py`](../pipeline/scoring.py).
- **Hindi Editorial Stack:** [`pipeline/ai_translator.py`](../pipeline/ai_translator.py), [`pipeline/hindi_postfix.py`](../pipeline/hindi_postfix.py), [`pipeline/hindi_editor.py`](../pipeline/hindi_editor.py), [`pipeline/content_sanitizer.py`](../pipeline/content_sanitizer.py), [`pipeline/text_normalize.py`](../pipeline/text_normalize.py).
- **Static GK & MCQ Exam Board:** [`pipeline/static_gk_db.py`](../pipeline/static_gk_db.py), [`config/current_facts.json`](../config/current_facts.json), [`agents/static_gk_validator.py`](../agents/static_gk_validator.py), [`pipeline/mcq_builder.py`](../pipeline/mcq_builder.py), [`pipeline/mcq_quality.py`](../pipeline/mcq_quality.py), [`pipeline/mcq_examiner.py`](../pipeline/mcq_examiner.py).
- **PDF Shaping, Visual QA & Branding:** [`config/branding.py`](../config/branding.py), [`src/generate_pdf.py`](../src/generate_pdf.py), [`src/period_pdf.py`](../src/period_pdf.py), [`pipeline/pdf_visual_qa.py`](../pipeline/pdf_visual_qa.py), [`agents/19_pdf_qa.py`](../agents/19_pdf_qa.py).
- **Publication, Audit & Bounded Learning:** [`agents/22_telegram_publisher.py`](../agents/22_telegram_publisher.py), [`agents/23_telegram_pin_verifier.py`](../agents/23_telegram_pin_verifier.py), [`pipeline/edition_report.py`](../pipeline/edition_report.py), [`pipeline/self_improvement.py`](../pipeline/self_improvement.py), [`agents/25_auto_healer.py`](../agents/25_auto_healer.py).
