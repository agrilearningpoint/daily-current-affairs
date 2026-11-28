# API Routing, Key Pools & Quota Policy

Centralized in [`pipeline/ai_router.py`](../pipeline/ai_router.py), [`pipeline/ai_usage.py`](../pipeline/ai_usage.py), [`scripts/verify_keys.py`](../scripts/verify_keys.py), and [`agents/00_model_orchestrator.py`](../agents/00_model_orchestrator.py).

---

## 1. Active Supported Providers & Key Pools

All provider keys stay strictly inside GitHub Actions Secrets or untracked local `.env` files. Never print or commit keys.

| Provider | Pool Environment Variables | Scheduling Policy | Notes |
|---|---|---|---|
| **Gemini** | `GEMINI_API_KEY`, `GEMINI_API_KEY_1` .. `GEMINI_API_KEY_7` | `least_used` / `round_robin` (`ALP_KEY_SCHEDULING`) | Model rotation (`models`) and shared-project quota detection (`gemini_shared_project`) |
| **Groq** | `GROQ_API_KEY`, `GROQ_API_KEY_1`, `GROQ_API_KEY_2` | Pool rotation on 401/402/403/429 | Fast inference for verification and fallback |
| **OpenAI** | `OPENAI_API_KEY`, `OPENAI_API_KEY_1` | Key-shape validation + zero-token `GET /models` health check | Explicit primary/secondary support |
| **Mistral** | `MISTRAL_API_KEY` | Auto free/configured model discovery | Strong multilingual & reasoning support |
| **OpenRouter** | `OPENROUTER_API_KEY` | Free-model rotation | Optional overflow provider |
| **NVIDIA** | `NVIDIA_API_KEY` | Auto model discovery | Optional overflow provider |
| **News / Discovery** | `GNEWS_API_KEY`, `NEWSDATA_API_KEY`, `SERPER_API_KEY`, `JINA_API_KEY` | Budgeted per-run (`ALP_SERPER_MAX_CALLS`, `ALP_JINA_MAX_CALLS`, staggered GNews waves) | Discovery & corroboration only |

---

## 2. Task-Aware Provider Routing

`pipeline.ai_router.providers_for_task(task, needs_hindi=...)` dynamically prioritizes providers suited for each cognitive role:

- `bilingual`, `bilingual_headline_batch`, `bilingual_body_batch`, `translation`: Hindi-capable models prioritized (`gemini` -> `mistral` -> `openai` -> `groq`).
- `mcq`, `mcq_verification`: Reasoning & schema adherence prioritized (`gemini` -> `mistral` -> `openai` -> `groq`).
- `verification`, `fact_verification`, `polish`, `edit`: Fast structured JSON extraction prioritized.

### Fail-Safe Pool Rotation & Cooldown Rules

1. **Pool Discovery:** Numbered keys (`_1`, `_2`, ...) are discovered even if the base unnumbered variable is absent.
2. **Slot Isolation:** Each key slot (`provider:ENV_VAR`) tracks independent call counts, errors, latency, and rate-limit cooldown timestamps.
3. **429 / Quota Handling:** Single-slot 429 switches to the next healthy key slot or model within the same provider before falling back across providers. Shared-project quota exhaustion pauses all keys sharing that quota cleanly instead of spamming failing requests.
4. **Zero-Token Health Checks:** `scripts/verify_keys.py` and `00_model_orchestrator.py` validate OpenAI and Gemini/Groq/Mistral keys using zero-token metadata endpoints (`GET /models`) whenever available.

---

## 3. Telemetry & Observability

Every AI call appends a sanitized record via `pipeline.ai_usage.record_ai_usage()` to `logs/ai_usage.jsonl` / `state/metrics/ai_usage.jsonl` containing:
`timestamp`, `provider`, `key_slot`, `model`, `task`, `latency_ms`, `tokens_in`, `tokens_out`, `estimated_cost_usd`, `success`, and `error_type`.

`update_provider_observability()` aggregates per-provider and per-slot summaries into `state/metrics/provider_observability.json` for `scripts/run_summary.py` and `pipeline/self_improvement.py`.
