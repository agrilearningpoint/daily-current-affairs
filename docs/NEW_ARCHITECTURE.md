# Enterprise Multi-Agent Architecture — Agri Learning Point

## End-to-End Stage Pipeline
1. **Stage 01 (`pipeline/01_source_fetch.py`)**: Concurrent RSS/Atom-first collection across 22 official & editorial sources (`config/news_sources.json`) with ETag/Last-Modified caching and 24-hour dead-feed quarantine (`state/feed_health.json`).
2. **Stage 02 (`pipeline/windows.py`)**: Strict 24-hour India Standard Time (`Asia/Kolkata`) research window enforcement (`prev_day 06:00 IST` to `edition_day 06:00 IST`), rejecting stale items and quarantining missing timestamps.
3. **Stage 04 (`agents/04_fact_verification.py`)**: Zero-hallucination 5W1H + numerical/institutional extractor, cross-source contradiction detector, and permanent `state/fact_ledger.json`.
4. **Stage 05 (`pipeline/store.py`)**: 4-Layer News & Event Deduplication (Canonical URL, Normalized Headline, Semantic Similarity, Event Identity Signature) persisted in `state/news_history.json`.
5. **Stage 10 (`agents/10_final_news_selection.py`)**: Category-diverse round-robin selector with official-source floor (`PIB`, `RBI`, `ICAR`, `NABARD`, `ISRO`) and 15-story reserve pool.
6. **Stage 12 (`agents/12_content_editor.py`) & `pipeline/ai_router.py`**: Task-aware multi-provider LLM router with per-key cooldown (`GEMINI_API_KEY_1..7`, `GROQ_API_KEY_1..2`, `MISTRAL`, `OPENROUTER`) and deterministic fallback.
7. **Stage 16 & 17 (`agents/16_mcq_generator.py`, `agents/17_mcq_validator.py`)**: 16-format exam MCQ generator with 8-layer historical deduplication (`state/mcq_history.json`) and independent answer/source validator.
8. **Stage 18 & 19 (`src/generate_pdf.py`, `agents/19_pdf_qa.py`)**: Dual-layer Devanagari PDF engine (`Mukta` + `Poppins` + invisible render-mode-3 text layer) and hard-gate PDF QA verifier.
9. **Stage 22 & 23 (`agents/22_telegram_publisher.py`, `agents/23_telegram_pin_verifier.py`)**: SHA-256 idempotent Telegram publisher with timeout reconciliation and pin verification.
10. **Stage 24 & 25 (`agents/24_final_health_audit.py`, `agents/25_auto_healer.py`)**: Pre-publication content/PDF audit (`reports/daily_quality_report.json`) and autonomous self-healing recovery agent.
