# PDF Design & Publishing Quality Standards — Agri Learning Point

**Brand Identity:** Agri Learning Point • BY SATYAM SIR & TEAM  
**Primary Delivery Platform:** Telegram Mobile PDF  
**Layout Engine:** ReportLab with HarfBuzz Devanagari font shaping  
**Primary Typography:** Mukta (Hindi), Poppins (English)  

---

## 1. Visual Hierarchy & Typography Targets

| Section / Element | Font Family & Weight | Size Target | Color Theme |
|---|---|---|---|
| **Cover Title** | Poppins Bold | 28–36 pt | Primary Dark Blue (`#0F2C59`) |
| **Section Headings** | Poppins Bold | 20–24 pt | Navy Blue (`#1A365D`) |
| **Story Headline (EN)**| Poppins SemiBold | 16–18 pt | Dark Neutral (`#1E293B`) |
| **Story Headline (HI)**| Mukta Bold | 16–18 pt | Primary Blue (`#0F2C59`) |
| **MCQ Question (EN/HI)**| Poppins / Mukta Medium | 13–14 pt | Black (`#111827`) |
| **MCQ Options** | Poppins / Mukta Regular| 12–13 pt | Dark Gray (`#374151`) |
| **Answer Callout** | Poppins Bold | 12–13 pt | Agriculture Accent Green (`#15803D`) |
| **Explanation Text** | Mukta / Poppins Regular| 11.5–12.5 pt | Neutral Slate (`#334155`) |
| **Static GK Labels** | Poppins Bold / Mukta | 11.5–12.5 pt | Dark Blue / Teal (`#0369A1`) |
| **Footer & Page Info** | Poppins Regular | 9–10 pt | Muted Gray (`#64748B`) |

---

## 2. Page Balance & Layout Rules

1. **Table of Contents (Single-Page Fit):**
   - The 15-story index must fit cleanly on Page 2 in a compact two-column layout. It must never spill an orphan row onto Page 3.
2. **News in Pictures (Gap-Free Balanced Grid):**
   - Number of cards determines the column and row structure.
   - For 4 cards: 2x2 grid.
   - For 5 cards: 4 cards selected or balanced layout without awkward orphan slots.
   - For 6 cards: 3x2 grid.
   - For 7-8 cards: Balanced 2-page grid (4 cards per page).
3. **No Broken MCQ Units:**
   - A question, its 5 options, and its answer callout must remain intact on the same page using ReportLab `KeepTogether` blocks.
4. **Clean Section Transitions:**
   - Quick Bites, One-Liners, and Agriculture Corner must have clear section banners and no orphan headers at page bottoms.

---

## 3. Multi-Layer Quality Assurance (QA) Release Gates

The PDF generation pipeline enforces eight release validation layers before Telegram publishing:

1. **Layer 1: Structural QA**
   - Valid PDF syntax, correct page count (15–45 pages), valid cover date, embedded fonts, and valid file checksum.
2. **Layer 2: Completeness QA**
   - Exactly 15 stories, 15 MCQs with 5 options each, answer key present, no truncated sentences.
3. **Layer 3: Factual & Entity QA**
   - Zero acronym collisions (e.g. CCPA verified as Central Consumer Protection Authority).
   - Zero conflicting ministry or statutory Act attributions.
4. **Layer 4: MCQ Quality QA**
   - Zero phrase-recognition stems (`Which phrase appeared...`).
   - Zero news-agency stems (`Which news agency reported...`).
   - Zero headline verbatim repetition.
5. **Layer 5: Static GK QA**
   - Zero generic country boilerplate (`Country – India`, `Capital – New Delhi`, `Year of independence – 1947`).
   - Strict verification of officeholders and dates.
6. **Layer 6: Editorial & Language QA**
   - Grammatically sound English (no dangling "in to").
   - Natural Hindi Devanagari text without broken transliteration.
7. **Layer 7: Visual QA**
   - Rendered PNG contact sheet review.
   - Zero blank or near-empty pages (<260 characters).
8. **Layer 8: Production Release Score**
   - Overall composite QA score must meet or exceed 90/100. Zero unresolved critical factual errors.
