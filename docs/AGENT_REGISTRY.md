# Agent Registry & Dependency Matrix

Every executable stage registered in [`config/workflow.py`](../config/workflow.py) and orchestrated by [`main.py`](../main.py):

| Stage ID | Module | Responsibility | Primary Input | Primary Output | Failure Policy |
|---|---|---|---|---|---|
| `00_model_orchestrator` | `agents/00_model_orchestrator.py` | Zero-token provider health check, pool discovery & observability refresh | Env key pools | `state/model_status.json`, `state/metrics/` | Non-fatal warning if fallback exists |
| `01_source_fetch` | `pipeline/01_source_fetch.py` | Batched thread-safe RSS + GNews collection within IST window | `config/sources.yaml` / registry | `data/raw/<job_id>.json` | Critical (exit 2 on 0 articles) |
| `04_fact_verification` | `agents/04_fact_verification.py` | Cross-source corroboration (wire-collapse aware), origin recovery, heuristics, Serper | `data/raw/<job_id>.json` | `data/verified/<job_id>.json` | Critical (`MIN_VERIFIED_COUNT`) |
| `05_deduplication` | `agents/05_deduplication.py` | 3-stage URL, fingerprint (photo-preserving), and contrastive similarity clustering | `data/verified/<job_id>.json` | `data/dedup/<job_id>.json` | Critical |
| `06_importance_scoring` | `agents/06_importance_scoring.py` | Multi-factor scoring with word-boundary keywords & stub-source penalty | `data/dedup/<job_id>.json` | `data/scored/<job_id>.json` | Critical |
| `07_student_domain_relevance` | `agents/07_student_domain_relevance.py` | Competitive-exam boost/demotion + `agri_focus` / `banking_focus` tagging | `data/scored/<job_id>.json` | `data/scored/<job_id>.json` | Critical |
| `10_final_news_selection` | `agents/10_final_news_selection.py` | Freshness drop, repeat suppression, diverse round-robin + reserves | `data/scored/<job_id>.json` | `data/selected/<job_id>.json` | Critical |
| `11_importance_memory` | `agents/11_importance_memory.py` | Cross-day trend tracking (`NEW/RISING/FALLING`) preserving reserves | `data/selected/<job_id>.json` | `data/memory/`, `state/importance_memory.json` | Fail-closed store check |
| `12_content_editor` | `agents/12_content_editor.py` | Evidence sanitization, EN polish, strict AI HI translation & Hindi editor | `data/selected/<job_id>.json` | `data/content/<job_id>.json` | Fail-closed if Hindi missing in live mode |
| `16_mcq_generator` | `agents/16_mcq_generator.py` | LLM schema MCQs + blind self-verify + bilingual template fallback + reserve backfill | `data/content/<job_id>.json` | `data/mcq/<job_id>.json` | Fail-closed below floor |
| `17_mcq_validator` | `agents/17_mcq_validator.py` | Schema/quality validator + independent adversarial `mcq_examiner` gate | `data/mcq/<job_id>.json` | `data/mcq/<job_id>.json` | Critical |
| `17b_auto_sections` | `agents/17b_auto_sections.py` | Bilingual Agriculture Corner + Quick Bites builder (non-overlapping with main news) | `data/content/<job_id>.json` | `data/content/<job_id>.json` | Critical |
| `17c_static_gk_validator` | `agents/static_gk_validator.py` | Officeholder & organisation verification against `config/current_facts.json` | `data/content/` + `data/mcq/` | Verified content & MCQs | Non-fatal line repair |
| `18_pdf_design` | `agents/18_pdf_design.py` | Photo/graphic attachment + ReportLab/HarfBuzz Exam-Genius PDF generation | `data/content/` + `data/mcq/` | `output/<job_id>.pdf` | Critical |
| `19_pdf_qa` | `agents/19_pdf_qa.py` | Text, Devanagari shaping, editorial, MCQ variety, visual PNG inspection & signed release | `output/<job_id>.pdf` | `logs/qa/<job_id>_qa.json`, `_release.json` | Critical release gate |
| `20_weekly_editor` | `agents/20_weekly_editor.py` | Weekly compilation from published Mon–Sun daily artifacts | `data/period_sources/` | Weekly `content` + `mcq` | Critical for weekly jobs |
| `21_monthly_editor` | `agents/21_monthly_editor.py` | Monthly compilation + topic quick tables from published daily/weekly sources | `data/period_sources/` | Monthly `content` + `mcq` | Critical for monthly jobs |
| `22_telegram_publisher` | `agents/22_telegram_publisher.py` | Idempotent publish enforcing QA hash, release signature & content provenance | `output/<job_id>.pdf` | `state/published_events.json` | Critical |
| `23_telegram_pin_verifier` | `agents/23_telegram_pin_verifier.py` | Verifies & pins published Telegram message | `state/published_events.json` | `state/pin_verification.json` | Critical in live mode |
| `24_final_health_audit` | `agents/24_final_health_audit.py` | End-to-end artifact hash check + edition report + learning cycle | All stage artifacts | `logs/qa/<job_id>_health.json`, `reports/` | Critical |
| `25_auto_healer` | `agents/25_auto_healer.py` | Reads failed stage logs cleanly without corrupting valid `state/jobs.json` | Logs + `state/jobs.json` | Remediation notes | Bounded diagnostics |
| `26_master_supervisor` | `agents/26_master_supervisor.py` | Supervisory audit wrapper over `pipeline.supervisor` | Pipeline artifacts | `logs/<job_id>_supervisor_audit.json` | Bounded repair & audit |
