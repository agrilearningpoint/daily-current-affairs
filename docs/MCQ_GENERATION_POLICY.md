# MCQ Generation, Variety & Anti-Repetition Policy

1. **Permanent Historical Database (`state/mcq_history.json`)**: Every generated question is stored permanently with its `mcq_id`, English & Hindi stems, 5 options, answer key, source `event_id`, `fact_key`, and order-invariant `semantic_fingerprint`.
2. **8-Layer Deduplication**: Before accepting any question, `is_duplicate_mcq()` compares exact text, normalized invariant tokens, EN/HI semantic similarity, `fact_key`, and option sets—catching passive/active rewrites (`"Which organization launched Scheme X?"` vs `"Scheme X was introduced by which organization?"`) and reordered options.
3. **16 Question Formats & Difficulty Balance**: Questions rotate across Statement-Based, Assertion-Reason, Numerical/Statistical, Location-Based, Pair-Based, and Direct Institutional formats with a 25% Easy / 50% Moderate / 25% Difficult distribution.
4. **Independent Answer Validation (`agents/17_mcq_validator.py`)**: Independently verifies 5 unique options (`A`–`E`), valid answer key mapping, Devanagari presence, and source evidence alignment.
