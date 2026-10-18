# PDF Design — bilingual daily current-affairs

Production PDF engine: **`src/generate_pdf.py`** (single canonical implementation).
Stage wrapper: `agents/18_pdf_design.py`. QA gate: `agents/19_pdf_qa.py`.
Preview tool: `scripts/pdf_preview.py`.

Everything below was verified against a real generated PDF on 2026-10-18 using the
deterministic fixture in `tests/fixtures/bilingual_sample.py`. Nothing in this
document is aspirational — each claim has a measurement or a test behind it.

---

## 1. Format and layout

| Property | Value |
| --- | --- |
| Page size | A4 portrait (`A4`, 210 × 297 mm) |
| Columns | Single column |
| Background | Near-white page, white content cards |
| Margins | left/right 14 mm, top 22 mm, bottom 14 mm |
| Content width | 182 mm |
| Grid | Single column, mobile-readable line lengths |

---

## 2. Palette (spec-aligned)

Tokens live in `COLORS` in `src/generate_pdf.py`. Existing token **names** were
preserved (so no call site broke); their values were retargeted to the spec.

| Role | Token | Hex |
| --- | --- | --- |
| Major headings, header/footer bands, cover masthead | `primary_navy` / `header_bg` / `footer_bg` | `#123B5D` |
| Category labels, accents, secondary headings | `brand_teal` / `economy_teal` | `#087E8B` |
| Subtle teal panel | `teal_light` | `#E7F4F5` |
| Restrained highlight | `brand_gold` | `#E7B44A` |
| Light gold panel | `gold_light` / `alert_light` | `#FBF3DF` |
| Warning/exam-pointer text | `alert_gold` | `#B45309` |
| Body copy | `body_text` | `#222B36` |
| Strong dark text | `dark_text` | `#1B2634` |
| Metadata / captions | `muted_text` | `#5B6673` |
| Card background | `card_bg` | `#F7F9FA` |
| Hairline borders | `border_light` | `#E2E8F0` |

**Restrained category colour.** All categories render teal-on-teal-light. Category
identity comes from the label text, not from a rainbow of colours — this is a
deliberate, documented change from the previous multi-colour scheme
(`CATEGORY_STYLE`).

---

## 3. Typography

| Element | Style | Size (pt) | Leading | Colours |
| --- | --- | --- | --- | --- |
| Cover masthead | `cover_masthead` | 28 | 32 | navy |
| Cover sub-title | `cover_sub` | 13 | 17 | ALP green |
| Section banner | `section_banner` | 16 | 20 | white on navy |
| News headline (EN) | `headline_en` | 15 | 19.5 | navy |
| News headline (HI, raster) | `headline_hi` | 15 | — | navy |
| Body (EN) | `body_en` | 12 | 17 | dark slate |
| Body (HI) | `body_hi` | 12 | 17.5 | body |
| Static-GK label | `static_label` | 10 | 13 | navy |
| Static-GK text | `static_text` | 10 | 14 | dark slate |
| Exam pointer | `exam_fact` | 10 | 14 | `#B45309` |
| MCQ question | `mcq_q` | 11.5 | 15.5 | dark slate |
| MCQ option | `mcq_opt` | 10.5 | 14.5 | dark slate |
| MCQ answer chip | `mcq_ans` | 10.5 | 14.5 | white on navy |
| MCQ explanation | `mcq_exp` | 10 | 14 | body |
| Category one-liner | `one_liner` | 11 | 15.5 | dark slate |
| Header / footer | `header` / `footer` | 9 | 11 | white |
| Source line / caption | inline | 9 | 12 | muted |

Line spacing sits within the requested ~1.35–1.5× band for body copy
(12 pt text on 17 pt leading ≈ 1.42×).

Fonts: **Poppins** (Regular / SemiBold / Bold) for English, **Mukta**
(Regular / Bold) for Hindi, both bundled in `src/fonts/` and registered at import
time inside a `try/except` in `register_fonts()`. Failure to register raises a
fatal `RuntimeError` — the pipeline must not silently produce an English-only PDF.

---

## 4. Devanagari rendering pipeline

Two backends, in order, gated by `_HAS_SHAPING`:

1. **`_render_hindi_hb_ft`** — `uharfbuzz` shaping + `freetype` rasterisation
   (primary; no Pillow RAQM needed).
2. **`_render_hindi_pillow_raqm`** — Pillow with `raqm` feature (fallback).

`_HindiTextFlowable` draws the rasterised image **and** an invisible, selectable
text layer at the same coordinates. This is why the PDF has both:
* visually correct conjuncts/matras (shape correctness comes from HarfBuzz), and
* extractable Unicode Devanagari (so QA, search and copy-paste work).

If no shaping backend is available, generation **fails closed** unless the
developer override `ALP_ALLOW_UNSHAPED_DEV_PDF=1` is set. Never set that override
in production or CI publishing jobs.

Verified extraction forms (asserted by `tests/test_pdf_hindi.py`):
`विषय-सूची`, `मुख्य बिंदु`, `स्थैतिक तथ्य` must be present, and broken orders
(`वषिय`, `मलिते`, `महत्वपूरण`) must be absent.

---

## 5. Glyph-coverage guard (missing-glyph / tofu prevention)

**Problem.** Poppins and Mukta do not contain several decorative symbols that the
template used. Rendering them produced visible tofu boxes.

Measured (FreeType, 2026-10-18) — **missing in all bundled faces**:
`U+25B6 (▶)`, `U+2714 (✔)`, `U+258C (▌)`, `U+2192 (→)`, `U+2713 (✓)`,
`U+25CF (●)`, `U+25A0 (■)`, `U+2605 (★)`, `U+2794 (➔)`, plus emoji.
**Supported**: `U+2022 (•)`, `U+00BB (»)`, `U+00B7 (·)`, `U+20B9 (₹)`,
`U+2013 (–)`, `U+2014 (—)`, curly quotes.

**Three-layer fix:**

1. Template literals use supported glyphs (`▶ → »`, `✔ → ·`, `→ → »`,
   emoji → `·`/`»`).
2. The category accent bar `▌` was replaced by a **filled table cell**
   (`BACKGROUND` = category colour). It is drawn by the layout engine, not a
   font, so it can never regress to tofu.
3. `sanitize_glyphs()` runs inside `_strip_html()` — the single chokepoint for
   every string that reaches a Paragraph or a Hindi image. Any codepoint the
   bundled fonts cannot draw is replaced by a supported equivalent or dropped.
   **Input data therefore cannot introduce tofu**, regardless of what a feed
   contains.

`agents/19_pdf_qa.py::check_glyph_integrity` fails the gate on U+FFFD / U+25A1
and on the known-unsupported symbol set. `tests/test_pdf_sample_qa.py` asserts
both the guard's behaviour and that the fonts really do lack those symbols (so the
guard is not silently dead code).

---

## 6. Document structure

1. **Cover** — masthead, date, edition label, headline strip, edition stats.
2. **Table of contents / index** — categories with story counts.
3. **Category-wise one-liners** — grouped bilingual revision pointers, one
   section heading per category that actually has news (no empty headings).
4. **Category sections** — teal section banner, then per story:
   * bilingual headline (EN paragraph + HI raster),
   * **Detailed Analysis** panel (bilingual factual prose) — rendered only when
     it adds content beyond the key points, so a fact is not printed twice,
   * key points (EN + HI),
   * optional image with centred caption,
   * **Static GK & Facts** panel,
   * **Exam Pointer** gold panel,
   * **clickable source line** (link + printed URL).
5. **Practice MCQs** — section banner; per question: EN + HI prompt, up to five
   options `(A)–(E)`, highlighted correct-answer chip, EN + HI detailed
   explanation, exam takeaway. Each MCQ is wrapped in `KeepTogether`.
6. **Final Revision Capsule** — a dense two-column table of the day's
   high-yield facts, figures and organisations (headline → key fact).
7. **Closing revision kit** — channel/offer summary with supported bullets.
8. **Header/footer on every page** — navy band with logo, brand string, and
   `Page X of Y` (dynamic via `NumberedCanvas`); thin outer rule.

### Clickable source references

Each story's source line emits `<link href="URL">Source name</link>` **and**
prints the URL as text. The link works for readers; the printed text keeps the
URL findable in extracted text (QA regex) and in copy-paste.

### PDF metadata

`title`, `author`, plus `subject`, `creator`, and `keywords` are set on the
`SimpleDocTemplate`.

---

## 7. QA gate (`agents/19_pdf_qa.py`)

Runs on the **real PDF bytes**, exit `0` pass / `1` fail.

| Check | Severity |
| --- | --- |
| File exists, not truncated (`file_missing`, `file_too_small`) | error |
| Page count sane (`too_few_pages` error, `too_many_pages` warn) | error / warning |
| Blank pages | warning |
| **Substantive page count** (`insufficient_substantive_pages`, floor scales with story count) | error |
| **Below 15-page daily target** (`below_page_target`) | warning |
| **Near-empty / heading-only pages** (`near_empty_pages`) | warning |
| Fonts embedded; Devanagari font present | error / warning |
| Sufficient text (`too_little_text`) | error |
| Hindi present (`insufficient_hindi` error, `low_hindi` warn) | error / warning |
| MCQ count, answer markers, duplicate questions | error / warning |
| **Glyph integrity** (`replacement_chars`, `unsupported_symbols`) | error |
| HTML/entity leakage | error |
| Source URLs present | warning |
| Images present; text overflow beyond page box | warning |
| `file_sha256` recorded for the publication ledger | info |

### Substantive page gate (content-aware)

`analyse_page_density()` measures the extractable character count of every
page. A page is **substantive** when it carries at least
`PDF_QA_SUBSTANTIVE_CHARS` (default 600) characters; a page between
`PDF_QA_NEAR_EMPTY_CHARS` (default 260) and that threshold is a
**near-empty / heading-only** page.

* The editorial daily target is `PDF_QA_TARGET_PAGES` (default **15**) — falling
  short raises `below_page_target` (warning).
* The hard floor is `minimum_substantive_pages(item_count) = clamp(item_count, 2, 15)`.
  Falling below that raises `insufficient_substantive_pages` (error), which means
  content was lost in layout, not that it was a genuinely quiet news day.

This distinguishes the two failure modes the spec calls out: **content lost**
(fail) versus **genuinely little verified news** (warn + honest QA report).

`scripts/pdf_preview.py` runs the real generator **and** this QA gate, then
renders representative pages (cover, first story, middle, MCQ, last) to PNG.

---

## 8. Evidence — sample edition

Generated 2026-10-18 from `tests/fixtures/bilingual_sample.py` (12 synthetic
stories across 12 categories, 8 five-option MCQs):

```
Pages:             22
Substantive pages: 22  (target >= 15)
Blank pages:       none
Near-empty pages:  none
Chars:             42,654
Devanagari:        9,880 (23.2%)
Fonts:             6 (Mukta-Bold, Mukta-Regular, Poppins-Bold, …)
MCQs:              8
Answer markers:    8
Duplicate Qs:      0
URLs:              15
Image XObjects:    209
QA verdict:        PASSED (0 errors, 0 warnings)
```

Rendered pages were inspected visually: Hindi conjuncts/matras shape correctly,
the `»`/`·` markers render (no tofu), source URLs print and are clickable,
detailed bilingual analysis and the revision capsule are present, and the footer
page numbers advance correctly.

---

## 9. Known cosmetic caveats (honest list)

| Item | Status |
| --- | --- |
| Extra vertical whitespace can appear between a long rasterised Hindi headline and the next block (the raster keeps padding for descenders). | Cosmetic only; not fixed, because changing the raster height computation is riskier than the benefit. |
| `KeepTogether` MCQ blocks can leave whitespace at the bottom of a page when the next MCQ does not fit. | Intentional — an orphaned/split MCQ is worse than whitespace. |
| Repeated page watermark. | Measured peak deviation from white ≤ ~1 RGB unit at 7 % alpha; it does not obscure text, so it was retained as a subtle brand mark. |
| Cover can look sparse for short editions. | Expected for a small daily edition. |
| The **Detailed Analysis** panel is suppressed when its wording is entirely covered by the key points. | Intentional — prevents printing the same fact twice in one card. |
| The **Final Revision Capsule** starts on a fresh page so its table is not split. | Intentional — a split revision table is harder to revise from. |

---

## 10. How to reproduce

```powershell
# Generate a sample edition, run the real QA gate, render pages to PNG
python scripts/pdf_preview.py --out output/sample_preview.pdf --png-dir output/preview

# Offline tests, including the real generate→QA path and the page target
python -m pytest tests/test_pdf_sample_qa.py tests/test_pdf_hindi.py `
                 tests/test_content_completeness.py tests/test_selection.py -q
```
