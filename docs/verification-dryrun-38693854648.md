# Dry-run evidence — run 38693854648

- run URL: https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/38693854648
- edition: 2026-10-15 (DRY_RUN=1)

## Article counts

| stage | count |
|---|---|
| raw | 553 |
| verified | 553 |
| dedup | 426 |
| scored | 32 |
| selected | 28 |

## Selected categories

```
{
 "Agriculture": 7,
 "Banking & Finance": 7,
 "Economy": 3,
 "National": 11
}
```

## Stage log inventory

| log | lines | first | last |
|---|---|---|---|
| content_editor.log | 2508 | 2026-10-15 06:41:15 | 2026-10-15 07:26:29 |

## Log excerpts (retries / skips / QA)

```
content_editor.log: 2026-10-15 06:41:15 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:41:18 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:41:18 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:41:20 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:41:20 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:41:22 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:41:22 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:41:24 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:41:24 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['mistral: no response'])
content_editor.log: 2026-10-15 06:41:25 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:41:27 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:41:27 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:41:29 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:41:29 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:41:31 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:41:31 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:41:33 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:41:33 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['mistral: no response'])
content_editor.log: 2026-10-15 06:41:34 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:41:36 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:41:36 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:41:38 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:41:38 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:41:40 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:41:40 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:41:43 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:41:43 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['mistral: no response'])
content_editor.log: 2026-10-15 06:41:43 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:41:45 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:41:45 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:41:47 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:41:47 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:41:49 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:41:49 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:41:51 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:41:51 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['mistral: no response'])
content_editor.log: 2026-10-15 06:41:52 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:41:54 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:41:54 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:41:56 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:41:56 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:41:58 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:41:58 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:42:01 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:42:01 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['mistral: no response'])
content_editor.log: 2026-10-15 06:42:01 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:42:03 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:42:03 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:42:05 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:42:05 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:42:07 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:42:07 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:42:10 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:42:10 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['mistral: no response'])
content_editor.log: 2026-10-15 06:42:10 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:42:12 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:42:12 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:42:14 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:42:14 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:42:16 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:42:16 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:42:19 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:42:19 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['mistral: no response'])
content_editor.log: 2026-10-15 06:42:19 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:42:21 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:42:21 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:42:23 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:42:23 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:42:25 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:42:25 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:42:28 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:42:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['mistral: no response'])
content_editor.log: 2026-10-15 06:42:28 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:42:30 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:42:30 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:42:32 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:42:32 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:42:34 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:42:34 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:42:37 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:42:37 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['mistral: no response'])
content_editor.log: 2026-10-15 06:42:37 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:42:39 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:42:39 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:42:41 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:42:41 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:42:43 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:42:43 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:42:45 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:42:45 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['mistral: no response'])
content_editor.log: 2026-10-15 06:42:46 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:42:48 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:42:48 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:42:50 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:42:50 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:42:52 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:42:52 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:42:55 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:42:55 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['mistral: no response'])
content_editor.log: 2026-10-15 06:42:55 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:42:57 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:42:57 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:42:59 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:42:59 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:43:01 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:43:01 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:43:04 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:43:04 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['mistral: no response'])
content_editor.log: 2026-10-15 06:43:04 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:43:06 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:43:06 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:43:08 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:43:08 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:43:10 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:43:10 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:43:12 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:43:12 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['mistral: no response'])
content_editor.log: 2026-10-15 06:43:13 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:43:15 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:43:15 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:43:17 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:43:17 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:43:19 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:43:19 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:43:21 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:43:21 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['mistral: no response'])
content_editor.log: 2026-10-15 06:43:22 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:43:24 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:43:24 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:43:26 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:43:26 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:43:28 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:43:28 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:43:30 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:43:30 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['mistral: no response'])
content_editor.log: 2026-10-15 06:43:30 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:43:33 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:43:33 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:43:35 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:43:35 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:43:37 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:43:37 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:43:39 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:43:39 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['mistral: no response'])
content_editor.log: 2026-10-15 06:43:40 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:43:42 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:43:42 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:43:44 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:43:44 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:43:46 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:43:46 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:43:48 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:43:48 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['mistral: no response'])
content_editor.log: 2026-10-15 06:43:49 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:43:51 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:43:51 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:43:53 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:43:53 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:43:55 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:43:55 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:43:57 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:43:57 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['mistral: no response'])
content_editor.log: 2026-10-15 06:43:57 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:44:00 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:44:00 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:44:02 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:44:02 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:44:04 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:44:04 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:44:06 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:44:06 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['mistral: no response'])
content_editor.log: 2026-10-15 06:44:06 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:44:08 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:44:09 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:44:11 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:44:11 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:44:13 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:44:13 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:44:16 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:44:16 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['mistral: no response'])
content_editor.log: 2026-10-15 06:44:16 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:44:18 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:44:18 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:44:20 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:44:20 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:44:22 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:44:22 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:44:25 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:44:25 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['mistral: no response'])
content_editor.log: 2026-10-15 06:44:25 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:44:27 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:44:27 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:44:29 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:44:29 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:44:31 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:44:31 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:44:34 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:44:34 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['mistral: no response'])
content_editor.log: 2026-10-15 06:44:34 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:44:36 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:44:36 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:44:38 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:44:38 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:44:40 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:44:40 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:44:42 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:44:42 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['mistral: no response'])
content_editor.log: 2026-10-15 06:44:43 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:44:45 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:44:45 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:44:47 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:44:47 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:44:49 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:44:49 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:44:51 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:44:51 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['mistral: no response'])
content_editor.log: 2026-10-15 06:44:52 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:44:54 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:44:54 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:44:56 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:44:56 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:44:58 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:44:58 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:45:00 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:45:00 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['mistral: no response'])
content_editor.log: 2026-10-15 06:45:00 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:45:03 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:45:03 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:45:05 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:45:05 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:45:07 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:45:07 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:45:10 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:45:10 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['mistral: no response'])
content_editor.log: 2026-10-15 06:45:10 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:45:12 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:45:12 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:45:14 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:45:14 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:45:16 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:45:16 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:45:19 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:45:19 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['mistral: no response'])
content_editor.log: 2026-10-15 06:45:19 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:45:21 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:45:21 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:45:23 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:45:23 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:45:25 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:45:25 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:45:28 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:45:28 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['mistral: no response'])
content_editor.log: 2026-10-15 06:45:28 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:45:30 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:45:30 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:45:32 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:45:32 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:45:34 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:45:34 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:45:37 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:45:37 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['mistral: no response'])
content_editor.log: 2026-10-15 06:45:37 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:45:39 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:45:39 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:45:41 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:45:41 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:45:43 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:45:43 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:45:45 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:45:45 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['mistral: no response'])
content_editor.log: 2026-10-15 06:45:46 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:45:48 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:45:48 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:45:50 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:45:50 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:45:52 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:45:52 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:45:54 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:45:54 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['mistral: no response'])
content_editor.log: 2026-10-15 06:45:55 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:45:57 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:45:57 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:45:59 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:45:59 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:46:01 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:46:01 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:46:03 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:46:03 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['mistral: no response'])
content_editor.log: 2026-10-15 06:46:03 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:46:06 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:46:06 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:46:08 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
content_editor.log: 2026-10-15 06:46:08 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:46:10 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
content_editor.log: 2026-10-15 06:46:10 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:46:12 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-15 06:46:12 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['mistral: no response'])
content_editor.log: 2026-10-15 06:46:12 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:46:15 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-15 06:46:15 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
```

## Stage log tails

### content_editor.log

```
2026-10-15 07:25:51 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['mistral: no response'])
2026-10-15 07:25:51 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
2026-10-15 07:25:53 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
2026-10-15 07:25:53 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
2026-10-15 07:25:55 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
2026-10-15 07:25:55 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
2026-10-15 07:25:57 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
2026-10-15 07:25:57 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
2026-10-15 07:26:00 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
2026-10-15 07:26:00 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['mistral: no response'])
2026-10-15 07:26:00 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
2026-10-15 07:26:02 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
2026-10-15 07:26:02 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
2026-10-15 07:26:04 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
2026-10-15 07:26:04 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
2026-10-15 07:26:06 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
2026-10-15 07:26:06 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
2026-10-15 07:26:09 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
2026-10-15 07:26:09 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['mistral: no response'])
2026-10-15 07:26:09 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
2026-10-15 07:26:11 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
2026-10-15 07:26:11 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
2026-10-15 07:26:13 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
2026-10-15 07:26:13 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
2026-10-15 07:26:15 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
2026-10-15 07:26:15 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
2026-10-15 07:26:18 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
2026-10-15 07:26:18 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['mistral: no response'])
2026-10-15 07:26:18 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
2026-10-15 07:26:20 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
2026-10-15 07:26:20 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
2026-10-15 07:26:22 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
2026-10-15 07:26:22 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
2026-10-15 07:26:24 | WARNING  | pipeline.ai_translator | [Translator] openrouter failed: 402 Client Error: Payment Required for url: https://openrouter.ai/api/v1/chat/completions
2026-10-15 07:26:24 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
2026-10-15 07:26:26 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
2026-10-15 07:26:26 | WARNING  | pipeline.content | [Translation] AI unavailable for task=headline (validation failed: ['mistral: no response'])
2026-10-15 07:26:27 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
2026-10-15 07:26:29 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
2026-10-15 07:26:29 | WARNING  | pipeline.ai_translator | [Translator] groq failed: 404 Client Error: Not Found for url: https://api.groq.com/openai/v1/chat/completions
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
