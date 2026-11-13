# Multi-Provider AI Router & Zero-API Failover Guide

1. **Per-Key Rotation (`pipeline/ai_router.py`)**: Tracks individual key slots (`GEMINI_API_KEY_1..7`, `GROQ_API_KEY_1..2`, `MISTRAL_API_KEY`, `OPENROUTER_API_KEY`) in `state/api_health.json`.
2. **Error Classification & Backoff**:
   - `429`: Exponential backoff + random jitter (or `Retry-After` header) on the single affected key; immediate failover to the next healthy key.
   - `401 / 403`: Marks the specific key slot `permanently_invalid` for 24 hours and triggers secret monitor alerting.
   - `500 / 502 / 503 / 504 / Timeout`: Short cooldown and instant provider switch.
3. **Zero-API Deterministic Fallback**: Date filtering, URL canonicalization, 4-layer deduplication, 5W1H fact extraction, rule-based content editing, and 16-format MCQ construction operate deterministically when all external LLM providers are unreachable.
