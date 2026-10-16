# Dry-run evidence — run 38879882929

- run URL: https://github.com/agrilearningpoint/daily-current-affairs/actions/runs/38879882929
- edition: 2026-10-15 (DRY_RUN=1)

## Article counts

| stage | count |
|---|---|
| raw | 551 |
| verified | 3 |
| dedup | 2 |
| scored | 2 |
| selected | 2 |
| content | 2 |

## Category distribution per stage (raw keys here = normalisation missing)

- raw: ```{"agriculture": 1, "national": 60, "banking_finance": 21, "economy_data": 11, "agriculture_core": 7, "govt_national": 73, "cooperation": 2, "science": 19, "defence_science": 52, "environment": 3, "discovery": 169, "aggregator": 133}```

## Selected items

- [20/45] Agriculture: banner M Kisan
- [12/12] economy_data: Data Centre Evaluation Framework to Help States Plan for Sustainable Growth

## Stage log inventory

| log | lines | first | last |
|---|---|---|---|
| content_editor.log | 152 | 2026-10-16 09:21:55 | 2026-10-16 09:23:02 |
| 10_final_news_selection.log | 6 | --- attempt 1; exit | 2026-10-16 09:21:55 |
| 11_importance_memory.log | 2 | --- attempt 1; exit | INFO:root:[IMPORTAN |
| 12_content_editor.log | 161 | --- attempt 1; exit |   warnings.warn( |

## Log excerpts (retries / skips / QA)

```
content_editor.log: 2026-10-16 09:22:21 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-16 09:22:22 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ['unusual length ratio 0.06']
content_editor.log: 2026-10-16 09:22:23 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-16 09:22:23 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['gemini: rate limited', 'groq: validation failed', 'openrouter: HTTP 402', 'mistral: rate limited'
content_editor.log: 2026-10-16 09:22:24 | WARNING  | pipeline.ai_router | [Router] gemini HTTP 429 (rate_limit): {
content_editor.log: 2026-10-16 09:22:24 | WARNING  | pipeline.ai_router | [Router] Provider gemini disabled for 120s: rate limited
content_editor.log: 2026-10-16 09:22:26 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ['unusual length ratio 0.35']
content_editor.log: 2026-10-16 09:22:27 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['groq: validation failed', 'openrouter: HTTP 402'])
content_editor.log: 2026-10-16 09:22:29 | WARNING  | pipeline.content | [Content Builder] 2 translations need review (AI did not pass)
content_editor.log: 2026-10-16 09:22:29 | ERROR    | __main__ | Translation validation failed; refusing to publish unreviewed content
content_editor.log: 2026-10-16 09:22:35 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-16 09:22:36 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ['unusual length ratio 0.06']
content_editor.log: 2026-10-16 09:22:36 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-16 09:22:36 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['groq: validation failed', 'openrouter: HTTP 402', 'mistral: rate limited'])
content_editor.log: 2026-10-16 09:22:37 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ["missing acronyms: ['GK']"]
content_editor.log: 2026-10-16 09:22:37 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['groq: validation failed', 'openrouter: HTTP 402'])
content_editor.log: 2026-10-16 09:22:37 | WARNING  | pipeline.ai_router | [Router] gemini HTTP 429 (rate_limit): {
content_editor.log: 2026-10-16 09:22:37 | WARNING  | pipeline.ai_router | [Router] Provider gemini disabled for 120s: rate limited
content_editor.log: 2026-10-16 09:22:41 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ['unusual length ratio 0.38']
content_editor.log: 2026-10-16 09:22:41 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['groq: validation failed', 'openrouter: HTTP 402'])
content_editor.log: 2026-10-16 09:22:44 | WARNING  | pipeline.content | [Content Builder] 3 translations need review (AI did not pass)
content_editor.log: 2026-10-16 09:22:44 | ERROR    | __main__ | Translation validation failed; refusing to publish unreviewed content
content_editor.log: 2026-10-16 09:22:55 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
content_editor.log: 2026-10-16 09:22:56 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ['unusual length ratio 0.06']
content_editor.log: 2026-10-16 09:22:57 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
content_editor.log: 2026-10-16 09:22:57 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['groq: validation failed', 'openrouter: HTTP 402', 'mistral: rate limited'])
content_editor.log: 2026-10-16 09:22:57 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ["missing acronyms: ['GK']"]
content_editor.log: 2026-10-16 09:22:57 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['groq: validation failed', 'openrouter: HTTP 402'])
content_editor.log: 2026-10-16 09:22:58 | WARNING  | pipeline.ai_router | [Router] gemini HTTP 429 (rate_limit): {
content_editor.log: 2026-10-16 09:22:58 | WARNING  | pipeline.ai_router | [Router] Provider gemini disabled for 120s: rate limited
content_editor.log: 2026-10-16 09:23:01 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ['unusual length ratio 0.35']
content_editor.log: 2026-10-16 09:23:01 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['groq: validation failed', 'openrouter: HTTP 402'])
content_editor.log: 2026-10-16 09:23:01 | WARNING  | pipeline.ai_translator | [Translator] groq rate-limited (429)
content_editor.log: 2026-10-16 09:23:01 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['groq: rate limited', 'openrouter: HTTP 402'])
content_editor.log: 2026-10-16 09:23:01 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['openrouter: HTTP 402'])
content_editor.log: 2026-10-16 09:23:02 | WARNING  | pipeline.ai_router | [Router] groq HTTP 429 (rate_limit): {"error":{"message":"Rate limit reached for model `openai/gpt-oss-120b` in organization `org_01m4n8hsfce0q8z1yndppr2nmv` service 
content_editor.log: 2026-10-16 09:23:02 | WARNING  | pipeline.ai_router | [Router] Provider groq disabled for 120s: rate limited
content_editor.log: 2026-10-16 09:23:02 | WARNING  | pipeline.ai_router | [Router] openrouter HTTP 402 (auth_error): {"error":{"message":"This request requires more credits, or fewer max_tokens. You requested up to 16384 tokens, but can onl
content_editor.log: 2026-10-16 09:23:02 | WARNING  | pipeline.ai_router | [Router] Provider openrouter disabled for 3600s: auth error
content_editor.log: 2026-10-16 09:23:02 | WARNING  | pipeline.ai_router | [Router] mistral HTTP 429 (rate_limit): {"object":"error","message":"Rate limit exceeded","type":"rate_limited","param":null,"code":"1300","raw_status_code":429}
content_editor.log: 2026-10-16 09:23:02 | WARNING  | pipeline.ai_router | [Router] Provider mistral disabled for 120s: rate limited
content_editor.log: 2026-10-16 09:23:02 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: mistral: rate_limit
content_editor.log: 2026-10-16 09:23:02 | WARNING  | pipeline.content | [Content Builder] 5 translations need review (AI did not pass)
content_editor.log: 2026-10-16 09:23:02 | ERROR    | __main__ | Translation validation failed; refusing to publish unreviewed content
10_final_news_selection.log: 2026-10-16 09:21:55,428 | INFO     | root | [FINAL NEWS SELECTION AGENT v2] selected 2 items (target=28)
12_content_editor.log: 2026-10-16 09:22:21 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
12_content_editor.log: 2026-10-16 09:22:22 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ['unusual length ratio 0.06']
12_content_editor.log: 2026-10-16 09:22:23 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
12_content_editor.log: 2026-10-16 09:22:23 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['gemini: rate limited', 'groq: validation failed', 'openrouter: HTTP 402', 'mistral: rate limited'
12_content_editor.log: 2026-10-16 09:22:24 | WARNING  | pipeline.ai_router | [Router] gemini HTTP 429 (rate_limit): {
12_content_editor.log: 2026-10-16 09:22:24 | WARNING  | pipeline.ai_router | [Router] Provider gemini disabled for 120s: rate limited
12_content_editor.log: 2026-10-16 09:22:26 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ['unusual length ratio 0.35']
12_content_editor.log: 2026-10-16 09:22:27 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['groq: validation failed', 'openrouter: HTTP 402'])
12_content_editor.log: 2026-10-16 09:22:29 | WARNING  | pipeline.content | [Content Builder] 2 translations need review (AI did not pass)
12_content_editor.log: 2026-10-16 09:22:29 | ERROR    | __main__ | Translation validation failed; refusing to publish unreviewed content
12_content_editor.log: 2026-10-16 09:22:35 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
12_content_editor.log: 2026-10-16 09:22:36 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ['unusual length ratio 0.06']
12_content_editor.log: 2026-10-16 09:22:36 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
12_content_editor.log: 2026-10-16 09:22:36 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['groq: validation failed', 'openrouter: HTTP 402', 'mistral: rate limited'])
12_content_editor.log: 2026-10-16 09:22:37 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ["missing acronyms: ['GK']"]
12_content_editor.log: 2026-10-16 09:22:37 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['groq: validation failed', 'openrouter: HTTP 402'])
12_content_editor.log: 2026-10-16 09:22:37 | WARNING  | pipeline.ai_router | [Router] gemini HTTP 429 (rate_limit): {
12_content_editor.log: 2026-10-16 09:22:37 | WARNING  | pipeline.ai_router | [Router] Provider gemini disabled for 120s: rate limited
12_content_editor.log: 2026-10-16 09:22:41 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ['unusual length ratio 0.38']
12_content_editor.log: 2026-10-16 09:22:41 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['groq: validation failed', 'openrouter: HTTP 402'])
12_content_editor.log: 2026-10-16 09:22:44 | WARNING  | pipeline.content | [Content Builder] 3 translations need review (AI did not pass)
12_content_editor.log: 2026-10-16 09:22:44 | ERROR    | __main__ | Translation validation failed; refusing to publish unreviewed content
12_content_editor.log: 2026-10-16 09:22:55 | WARNING  | pipeline.ai_translator | [Translator] gemini rate-limited (429)
12_content_editor.log: 2026-10-16 09:22:56 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ['unusual length ratio 0.06']
12_content_editor.log: 2026-10-16 09:22:57 | WARNING  | pipeline.ai_translator | [Translator] mistral rate-limited (429)
12_content_editor.log: 2026-10-16 09:22:57 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['groq: validation failed', 'openrouter: HTTP 402', 'mistral: rate limited'])
12_content_editor.log: 2026-10-16 09:22:57 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ["missing acronyms: ['GK']"]
12_content_editor.log: 2026-10-16 09:22:57 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['groq: validation failed', 'openrouter: HTTP 402'])
12_content_editor.log: 2026-10-16 09:22:58 | WARNING  | pipeline.ai_router | [Router] gemini HTTP 429 (rate_limit): {
12_content_editor.log: 2026-10-16 09:22:58 | WARNING  | pipeline.ai_router | [Router] Provider gemini disabled for 120s: rate limited
12_content_editor.log: 2026-10-16 09:23:01 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ['unusual length ratio 0.35']
12_content_editor.log: 2026-10-16 09:23:01 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['groq: validation failed', 'openrouter: HTTP 402'])
12_content_editor.log: 2026-10-16 09:23:01 | WARNING  | pipeline.ai_translator | [Translator] groq rate-limited (429)
12_content_editor.log: 2026-10-16 09:23:01 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['groq: rate limited', 'openrouter: HTTP 402'])
12_content_editor.log: 2026-10-16 09:23:01 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['openrouter: HTTP 402'])
12_content_editor.log: 2026-10-16 09:23:02 | WARNING  | pipeline.ai_router | [Router] groq HTTP 429 (rate_limit): {"error":{"message":"Rate limit reached for model `openai/gpt-oss-120b` in organization `org_01m4n8hsfce0q8z1yndppr2nmv` service 
12_content_editor.log: 2026-10-16 09:23:02 | WARNING  | pipeline.ai_router | [Router] Provider groq disabled for 120s: rate limited
12_content_editor.log: 2026-10-16 09:23:02 | WARNING  | pipeline.ai_router | [Router] openrouter HTTP 402 (auth_error): {"error":{"message":"This request requires more credits, or fewer max_tokens. You requested up to 16384 tokens, but can onl
12_content_editor.log: 2026-10-16 09:23:02 | WARNING  | pipeline.ai_router | [Router] Provider openrouter disabled for 3600s: auth error
12_content_editor.log: 2026-10-16 09:23:02 | WARNING  | pipeline.ai_router | [Router] mistral HTTP 429 (rate_limit): {"object":"error","message":"Rate limit exceeded","type":"rate_limited","param":null,"code":"1300","raw_status_code":429}
12_content_editor.log: 2026-10-16 09:23:02 | WARNING  | pipeline.ai_router | [Router] Provider mistral disabled for 120s: rate limited
12_content_editor.log: 2026-10-16 09:23:02 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: mistral: rate_limit
12_content_editor.log: 2026-10-16 09:23:02 | WARNING  | pipeline.content | [Content Builder] 5 translations need review (AI did not pass)
12_content_editor.log: 2026-10-16 09:23:02 | ERROR    | __main__ | Translation validation failed; refusing to publish unreviewed content
```

## Stage log tails

### content_editor.log

```
2026-10-16 09:22:58 | WARNING  | pipeline.ai_router | [Router] gemini HTTP 429 (rate_limit): {
  "error": {
    "code": 429,
    "message": "You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-a
2026-10-16 09:22:58 | WARNING  | pipeline.ai_router | [Router] Provider gemini disabled for 120s: rate limited
2026-10-16 09:22:58 | INFO     | pipeline.ai_router | [Router] ✔ groq responded (task=polish, 14 chars)
2026-10-16 09:22:59 | INFO     | pipeline.ai_router | [Router] ✔ groq responded (task=polish, 232 chars)
2026-10-16 09:22:59 | INFO     | pipeline.ai_translator | [Translator] skipping gemini after an earlier rate limit
2026-10-16 09:22:59 | INFO     | pipeline.ai_translator | [Translator] trying provider groq
2026-10-16 09:23:00 | INFO     | pipeline.ai_translator | [Translator] skipping gemini after an earlier rate limit
2026-10-16 09:23:00 | INFO     | pipeline.ai_translator | [Translator] trying provider groq
2026-10-16 09:23:01 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ['unusual length ratio 0.35']
2026-10-16 09:23:01 | INFO     | pipeline.ai_translator | [Translator] trying provider openrouter
2026-10-16 09:23:01 | INFO     | pipeline.ai_translator | [Translator] skipping mistral after an earlier rate limit
2026-10-16 09:23:01 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['groq: validation failed', 'openrouter: HTTP 402'])
2026-10-16 09:23:01 | INFO     | pipeline.ai_translator | [Translator] skipping gemini after an earlier rate limit
2026-10-16 09:23:01 | INFO     | pipeline.ai_translator | [Translator] trying provider groq
2026-10-16 09:23:01 | WARNING  | pipeline.ai_translator | [Translator] groq rate-limited (429)
2026-10-16 09:23:01 | INFO     | pipeline.ai_translator | [Translator] moving to the next configured provider
2026-10-16 09:23:01 | INFO     | pipeline.ai_translator | [Translator] trying provider openrouter
2026-10-16 09:23:01 | INFO     | pipeline.ai_translator | [Translator] skipping mistral after an earlier rate limit
2026-10-16 09:23:01 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['groq: rate limited', 'openrouter: HTTP 402'])
2026-10-16 09:23:01 | INFO     | pipeline.ai_translator | [Translator] skipping gemini after an earlier rate limit
2026-10-16 09:23:01 | INFO     | pipeline.ai_translator | [Translator] skipping groq after an earlier rate limit
2026-10-16 09:23:01 | INFO     | pipeline.ai_translator | [Translator] trying provider openrouter
2026-10-16 09:23:01 | INFO     | pipeline.ai_translator | [Translator] skipping mistral after an earlier rate limit
2026-10-16 09:23:01 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['openrouter: HTTP 402'])
2026-10-16 09:23:02 | INFO     | pipeline.ai_router | [Router] ✔ groq responded (task=polish, 80 chars)
2026-10-16 09:23:02 | INFO     | pipeline.content | [Polish] rejected - fact check failed
2026-10-16 09:23:02 | WARNING  | pipeline.ai_router | [Router] groq HTTP 429 (rate_limit): {"error":{"message":"Rate limit reached for model `openai/gpt-oss-120b` in organization `org_01m4n8hsfce0q8z1yndppr2nmv` service 
2026-10-16 09:23:02 | WARNING  | pipeline.ai_router | [Router] Provider groq disabled for 120s: rate limited
2026-10-16 09:23:02 | WARNING  | pipeline.ai_router | [Router] openrouter HTTP 402 (auth_error): {"error":{"message":"This request requires more credits, or fewer max_tokens. You requested up to 16384 tokens, but can onl
2026-10-16 09:23:02 | WARNING  | pipeline.ai_router | [Router] Provider openrouter disabled for 3600s: auth error
2026-10-16 09:23:02 | WARNING  | pipeline.ai_router | [Router] mistral HTTP 429 (rate_limit): {"object":"error","message":"Rate limit exceeded","type":"rate_limited","param":null,"code":"1300","raw_status_code":429}
2026-10-16 09:23:02 | WARNING  | pipeline.ai_router | [Router] Provider mistral disabled for 120s: rate limited
2026-10-16 09:23:02 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: mistral: rate_limit
2026-10-16 09:23:02 | INFO     | pipeline.content | [Polish] rejected - fact check failed
2026-10-16 09:23:02 | INFO     | pipeline.content | [Content Builder] Translation stats: ai=2 fallback=0 untranslated=5 (AI success 28.6%)
2026-10-16 09:23:02 | WARNING  | pipeline.content | [Content Builder] 5 translations need review (AI did not pass)
2026-10-16 09:23:02 | ERROR    | __main__ | Translation validation failed; refusing to publish unreviewed content
```

### 10_final_news_selection.log

```
--- attempt 1; exit 0 ---
[10_final_news_selection] job=daily_2026-10-15 type=daily date=2026-10-15
[10] OK — selected_count=2
2026-10-16 09:21:55,428 | INFO     | root | [FINAL NEWS SELECTION AGENT v2] selected 2 items (target=28)
2026-10-16 09:21:55,428 | INFO     | root |   Agriculture: 1
2026-10-16 09:21:55,428 | INFO     | root |   economy_data: 1
```

### 11_importance_memory.log

```
--- attempt 1; exit 0 ---
INFO:root:[IMPORTANCE MEMORY AGENT] memory updated for 2 events (local + persistent)
```

### 12_content_editor.log

```
    "code": 429,
    "message": "You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-a
2026-10-16 09:22:58 | WARNING  | pipeline.ai_router | [Router] Provider gemini disabled for 120s: rate limited
2026-10-16 09:22:58 | INFO     | pipeline.ai_router | [Router] ✔ groq responded (task=polish, 14 chars)
2026-10-16 09:22:59 | INFO     | pipeline.ai_router | [Router] ✔ groq responded (task=polish, 232 chars)
2026-10-16 09:22:59 | INFO     | pipeline.ai_translator | [Translator] skipping gemini after an earlier rate limit
2026-10-16 09:22:59 | INFO     | pipeline.ai_translator | [Translator] trying provider groq
2026-10-16 09:23:00 | INFO     | pipeline.ai_translator | [Translator] skipping gemini after an earlier rate limit
2026-10-16 09:23:00 | INFO     | pipeline.ai_translator | [Translator] trying provider groq
2026-10-16 09:23:01 | WARNING  | pipeline.ai_translator | [Translator] groq validation failed: ['unusual length ratio 0.35']
2026-10-16 09:23:01 | INFO     | pipeline.ai_translator | [Translator] trying provider openrouter
2026-10-16 09:23:01 | INFO     | pipeline.ai_translator | [Translator] skipping mistral after an earlier rate limit
2026-10-16 09:23:01 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['groq: validation failed', 'openrouter: HTTP 402'])
2026-10-16 09:23:01 | INFO     | pipeline.ai_translator | [Translator] skipping gemini after an earlier rate limit
2026-10-16 09:23:01 | INFO     | pipeline.ai_translator | [Translator] trying provider groq
2026-10-16 09:23:01 | WARNING  | pipeline.ai_translator | [Translator] groq rate-limited (429)
2026-10-16 09:23:01 | INFO     | pipeline.ai_translator | [Translator] moving to the next configured provider
2026-10-16 09:23:01 | INFO     | pipeline.ai_translator | [Translator] trying provider openrouter
2026-10-16 09:23:01 | INFO     | pipeline.ai_translator | [Translator] skipping mistral after an earlier rate limit
2026-10-16 09:23:01 | WARNING  | pipeline.content | [Translation] AI unavailable for task=key_points (validation failed: ['groq: rate limited', 'openrouter: HTTP 402'])
2026-10-16 09:23:01 | INFO     | pipeline.ai_translator | [Translator] skipping gemini after an earlier rate limit
2026-10-16 09:23:01 | INFO     | pipeline.ai_translator | [Translator] skipping groq after an earlier rate limit
2026-10-16 09:23:01 | INFO     | pipeline.ai_translator | [Translator] trying provider openrouter
2026-10-16 09:23:01 | INFO     | pipeline.ai_translator | [Translator] skipping mistral after an earlier rate limit
2026-10-16 09:23:01 | WARNING  | pipeline.content | [Translation] AI unavailable for task=general (validation failed: ['openrouter: HTTP 402'])
2026-10-16 09:23:02 | INFO     | pipeline.ai_router | [Router] ✔ groq responded (task=polish, 80 chars)
2026-10-16 09:23:02 | INFO     | pipeline.content | [Polish] rejected - fact check failed
2026-10-16 09:23:02 | WARNING  | pipeline.ai_router | [Router] groq HTTP 429 (rate_limit): {"error":{"message":"Rate limit reached for model `openai/gpt-oss-120b` in organization `org_01m4n8hsfce0q8z1yndppr2nmv` service 
2026-10-16 09:23:02 | WARNING  | pipeline.ai_router | [Router] Provider groq disabled for 120s: rate limited
2026-10-16 09:23:02 | WARNING  | pipeline.ai_router | [Router] openrouter HTTP 402 (auth_error): {"error":{"message":"This request requires more credits, or fewer max_tokens. You requested up to 16384 tokens, but can onl
2026-10-16 09:23:02 | WARNING  | pipeline.ai_router | [Router] Provider openrouter disabled for 3600s: auth error
2026-10-16 09:23:02 | WARNING  | pipeline.ai_router | [Router] mistral HTTP 429 (rate_limit): {"object":"error","message":"Rate limit exceeded","type":"rate_limited","param":null,"code":"1300","raw_status_code":429}
2026-10-16 09:23:02 | WARNING  | pipeline.ai_router | [Router] Provider mistral disabled for 120s: rate limited
2026-10-16 09:23:02 | ERROR    | pipeline.ai_router | [Router] All providers failed. Last error: mistral: rate_limit
2026-10-16 09:23:02 | INFO     | pipeline.content | [Polish] rejected - fact check failed
2026-10-16 09:23:02 | INFO     | pipeline.content | [Content Builder] Translation stats: ai=2 fallback=0 untranslated=5 (AI success 28.6%)
2026-10-16 09:23:02 | WARNING  | pipeline.content | [Content Builder] 5 translations need review (AI did not pass)
2026-10-16 09:23:02 | ERROR    | __main__ | Translation validation failed; refusing to publish unreviewed content
/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/site-packages/requests/__init__.py:113: RequestsDependencyWarning: urllib3 (2.2.3) or chardet (7.6.0)/charset_normalizer (3.4.0) doesn't match a supported version!
  warnings.warn(
```

## Committed state on this branch at collection time

```json
{
 "status": "failed",
 "dry_run": false,
 "last_success_stage": "07_student_domain_relevance",
 "failed_stage": "10_final_news_selection",
 "checkpoint_run_id": "38694723499",
 "last_error": "10_final_news_selection: failed after 3 attempt(s): [10_final_news_selection] job=daily_2026-10-15 type=daily date=2026-10-15\n\n2026-10-15 07:27:23,464 | INFO     | root | [FINAL NEWS SELECTION AGENT v2] selected 2 items (target=28)\n2026-10-15 07:27:23,464 | INFO     | root |   Agriculture: 1\n2026-10-15 07:27:23,464 | INFO     | root |   economy_data: 1\n[10] FAILED: only 2 selected (min 5)"
}
```
