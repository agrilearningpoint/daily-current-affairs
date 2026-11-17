# Static GK Standards & Knowledge Base — Agri Learning Point

**Purpose:** Comprehensive standards for authoritative, contextual, and examination-relevant Static GK.  
**Audience:** Aspirants preparing for UPSSSC AGTA, IBPS AFO, ICAR, NABARD, FCI, and State PSCs.  

---

## 1. Contextual Relevance Mandate

Static GK must provide high-yield institutional, legal, and operational context directly related to the entities named in the news story.

### Permitted Institutional Categories:
- **Establishment & History:** Precise founding date and historical milestones (e.g. ICAR: 16 July 1929).
- **Headquarters & Regional Centers:** City and state location of apex offices.
- **Parent Ministry & Administrative Department:** The exact nodal ministry (e.g. APEDA under Ministry of Commerce and Industry; CCPA under Ministry of Consumer Affairs).
- **Constitutional / Statutory Status:** Governing Act (e.g. Consumer Protection Act, 2019; NABARD Act, 1981; RBI Act, 1934).
- **Core Objectives & Regulatory Mandate:** Procurement, price support, export inspection, monetary policy, consumer safety.
- **Apex Committees & Reports:** Key advisory bodies and annual flagship publications.

---

## 2. Strict Prohibition of Generic National Boilerplate

Static GK boxes must never contain generic trivia that adds zero value to competitive exam aspirants:
- ❌ `Country – India` / `देश – भारत`
- ❌ `Capital – New Delhi` / `राजधानी – नई दिल्ली`
- ❌ `Official language – Hindi` / `आधिकारिक भाषा – हिन्दी`
- ❌ `Year of independence – 1947` / `स्वतंत्रता वर्ष – 1947`
- ❌ Copying the news headline as an "Exam Fact".
- ❌ Unrelated historical trivia unconnected to the story entity.

If no genuine institutional Static GK can be verified for a story, the box must be omitted cleanly rather than filled with generic national filler.

---

## 3. Entity & Acronym Resolution Architecture

To eliminate catastrophic acronym collisions (such as expanding `CCPA` as `Chief Controller of Explosives`), the system maintains a verified master registry in `pipeline/static_gk_db.py`:

```
Entity Name ──► [Master Registry in pipeline/static_gk_db.py]
                      │
                      ├── Verified Full Name (EN + HI)
                      ├── Parent Ministry (EN + HI)
                      ├── Governing Act (EN + HI)
                      ├── Headquarters (EN + HI)
                      └── Core Statutory Functions (EN + HI)
```

### Critical Disambiguation Matrix:
| Acronym | Authoritative Expansion | Governing Act / Parent Ministry | Banned Collision |
|---|---|---|---|
| **CCPA** | Central Consumer Protection Authority | Consumer Protection Act, 2019 / Ministry of Consumer Affairs, Food & Public Distribution | Chief Controller of Explosives (CCE / PESO) |
| **CCE / PESO** | Petroleum and Explosives Safety Organization / Chief Controller of Explosives | Explosives Act, 1884 / DPIIT, Ministry of Commerce and Industry | Central Consumer Protection Authority |
| **CTI** | Chamber of Trade and Industry | Apex Trade Body, New Delhi / Non-governmental industry advocacy | Central Training Institute |
| **ICAR** | Indian Council of Agricultural Research | DARE, Ministry of Agriculture and Farmers Welfare (Est. 1929) | International Centre for Agricultural Research |
| **APEDA** | Agricultural and Processed Food Products Export Development Authority | APEDA Act, 1985 / Ministry of Commerce and Industry | Agricultural Produce Market Committee |
| **FCI** | Food Corporation of India | Food Corporations Act, 1964 / Ministry of Consumer Affairs | Fertiliser Corporation of India |
| **SEBI** | Securities and Exchange Board of India | SEBI Act, 1992 / Ministry of Finance | State Electricity Board |
| **IEPFA** | Investor Education and Protection Fund Authority | Companies Act, 2013 / Ministry of Corporate Affairs | Indian Environmental Protection Fund |
