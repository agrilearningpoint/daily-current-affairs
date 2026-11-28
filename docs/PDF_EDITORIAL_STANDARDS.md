# PDF Design & Editorial Standards

> Governed by [`config/branding.py`](../config/branding.py), [`src/generate_pdf.py`](../src/generate_pdf.py), [`src/period_pdf.py`](../src/period_pdf.py), and [`agents/19_pdf_qa.py`](../agents/19_pdf_qa.py).

---

## 1. Visual Identity & Unified Branding

- **Brand Title:** `AGRI LEARNING POINT — BY SATYAM SIR & TEAM`
- **Unified Color Palette (`BRAND_PALETTE` in `config/branding.py`):**
  - Primary Navy `#0A2540`, Secondary `#0F4C81`, Agricultural Green `#0D7A42`, Gold Accent `#D97706`, Ice Card `#F8FAFC`, Charcoal Ink `#0F172A`.
- **Official Social Channels (Footer & Join-Us Block):**
  - YouTube: `@agrilearningpoint`
  - Telegram Channel: `@agrilearningpoint`
  - Daily Quiz Channel: `@agriquizworld`

---

## 2. Typography & Bilingual Shaping

- **English Font Family:** `Poppins` (`Regular`, `SemiBold`, `Bold`)
- **Hindi Font Family:** `Mukta` (`Regular`, `SemiBold`, `Bold`) shaped exclusively through **HarfBuzz + FreeType** (`_HindiTextFlowable`) paired with an invisible selectable PDF text layer (`TextRenderMode(3)`).
- Unshaped ReportLab Devanagari text is treated as a **critical QA error** (`unshaped_devanagari` / `broken_devanagari_matras`).
- Numeral consistency: Hindi prose normalizes Devanagari digits to Arabic numerals (`0-9`) with standardized Indian currency notation (`₹X करोड़`, `₹X लाख`).

---

## 3. Competitive-Exam Editorial Structure

1. **Cover Page:** Edition type badge, exam target pills (`UPSSSC AGTA`, `IBPS AFO`, `NABARD`, `ICAR / JRF`, `STATE PCS / FCI`), date, and quick navigation.
2. **Clickable Table of Contents:** Anchor-linked entries for every story unit, Agriculture Corner, Quick Bites, One-Liners, and Answer Key.
3. **Self-Contained Bilingual MCQ Units:**
   - Category pill + Headline (cleaned, zero trailing outlet tags or URLs).
   - High-resolution validated news image (400px+ wide where available, full credit / Wikimedia license attribution including `GODL` / `CC-BY`) or distinct non-photographic category banner graphic.
   - 5-option bilingual MCQ (`A`–`E`), no meta-options (`None/All of the above`), balanced answer-key distribution.
   - Highlighted Answer box + paired Bilingual Explanation (4–5 sentences, zero raw URLs or news datelines).
   - Curated Bilingual Static GK Box (verified against `config/current_facts.json` and domain databases; zero generic `Currency: Indian Rupee` or meaningless `Fact 1` dumps).
4. **Rapid Revision Sections:** Agriculture Corner, Quick Bites, English & Hindi One-Liners (distilled summaries, never blind headline copies), and Rapid Revision Answer Key.

---

## 4. Hard QA Thresholds

- **Daily Page Bounds:** `15` to `45` pages (`PDF_QA_MIN_PAGES`..`PDF_QA_MAX_PAGES`).
- **Minimum Hindi Coverage:** `>= 3.0%` Devanagari codepoints (typical editions achieve `18%–35%`).
- **Visual Pixel Inspection (`pipeline/pdf_visual_qa.py`):** No multi-page blank white renders and edge-clipping monitoring on rendered PNG pages.
