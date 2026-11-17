# Advanced MCQ Quality Engine — Agri Learning Point

**Purpose:** Comprehensive specification for high-yield, error-free, diverse examination assessment generation.  
**Audience:** UPSSSC AGTA, IBPS AFO, ICAR, NABARD, FCI, and State Agriculture Examinations.  

---

## 1. Supported 18 Question Types

MCQs must vary naturally across the 15 daily stories, selected dynamically based on available story evidence:

1. **Direct Factual Question:** Clear single-fact query supported by the news.
2. **Conceptual Understanding:** Tests the underlying principle or mechanism of a development.
3. **Institution & Organisation:** Probes apex bodies, regulatory powers, or institutional mandates.
4. **Scheme Objective & Implementation:** Explores beneficiary criteria, nodal agencies, or delivery mechanisms.
5. **Ministry & Department:** Identifies the responsible administrative authority.
6. **Numerical & Data Interpretation:** Evaluates financial outlays, growth rates, production targets, or survey statistics.
7. **Chronology & Important Dates:** Examines implementation timelines, founding dates, or phased milestones.
8. **Location & Headquarters:** Probes administrative headquarters, research stations, or summit venues.
9. **Statement-Based Questions:** Presents statements (I and II) to determine validity.
10. **Correct/Incorrect Combinations:** Evaluates multiple assertions (e.g. "Only 1 and 2 are correct").
11. **Match the Following:** Pairs schemes with ministries or institutes with headquarters.
12. **Assertion and Reasoning:** Tests causal relationships between two facts.
13. **Application-Based Question:** Tests practical implications of a policy or technological advancement.
14. **Agriculture-Specific Technical Question:** Focuses on agronomy, soil health, crop varieties, pests, or ICAR research.
15. **Scientific Significance & Research:** Focuses on biotechnology, space research, or environmental science.
16. **Regulatory & Policy Question:** Tests governing Acts, statutory orders, or legal penalties (e.g. Consumer Protection Act, 2019).
17. **Reports, Indices & Rankings:** Evaluates publishing agencies, key indicators, or India's rank.
18. **Awards, Appointments & Important Events:** Validates national honours, apex appointments, or summits.

---

## 2. Option & Distractor Design Rules

- **Option Count:** Exactly five options (A, B, C, D, E) for every question.
- **Homogeneity:** All 5 options must belong to the exact same category (all ministries, all states, all percentage ranges, all apex authorities).
- **Plausibility:** Distractors must be genuine, established entities or dimensionally sound numbers. Never invent fictional agency names or impossible percentages (>100% for shares).
- **No Second Correct Answer:** Distractors must not overlap or be partially true.
- **Prohibited Phrases:** Strict ban on:
  - "None of the above" / "All of the above"
  - "उपर्युक्त में से कोई नहीं" / "इनमें से सभी"
- **Grammatical Independence:** The option text must not give away the correct answer through atypical length or leading grammar.

---

## 3. Explanation Standards

Every MCQ must provide a substantive bilingual explanation structured as follows:
1. **Core Affirmation:** Direct confirmation of why the correct option is valid.
2. **Supporting News Fact:** The specific data point, outlay, or statement from the primary source.
3. **Institutional / Policy Context:** Background on the implementing ministry, scheme framework, or regulatory mandate.
4. **Examination Takeaway:** An additional contextual fact useful for revision.

### Strict Explanation Filters
- Prohibit copying news agency datelines (`Updated - November 17, 2026 12:59 am IST...`).
- Prohibit generic circular endings (`Therefore, Option B is the correct answer`).
- Prohibit copying raw URLs (`http://...`, `https://...`).
- Prohibit repetitive empty filler (`This highlights the importance of the sector...`).

---

## 4. Semantic Validation & Quality Gates

Deterministic checks implemented in `pipeline/mcq_schema.py` and `agents/17_mcq_validator.py`:

| Check | Failure Condition | Action |
|---|---|---|
| **Agency Question Filter** | Stem asks "Which news agency reported..." or "Which channel..." | **REJECT** — Regenerate with policy/outlay angle |
| **Headline Copying** | Question merely repeats the full headline verbatim | **REJECT** — Test underlying concept |
| **Dangling Syntax** | Malformed phrases like "in to", dangling prepositions, cut-off strings | **REJECT** — Clean syntax or regenerate |
| **Option Distinctiveness** | Duplicate options or case-insensitive collisions | **REJECT** |
| **Source Grounding** | Correct answer cannot be corroborated in source text or verified database | **REJECT** |
| **Acronym Collision** | Acronym mapped to conflicting entity (e.g. CCPA -> Chief Controller of Explosives) | **CRITICAL FAIL** — Block publication |
