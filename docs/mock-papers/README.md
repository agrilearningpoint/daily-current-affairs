# IBPS AFO 2026 — Agriculture (Professional Knowledge) Mock Papers

Bilingual (English + Hindi) practice papers for the **Agriculture Field Officer (Scale-I)**
post under **IBPS CRP SPL-XVI (2026 cycle)**.

> ⚠️ Pattern note: the old AFO mains paper (60 questions / 60 marks / 45 minutes,
> agriculture only) **is no longer the current pattern**. It was replaced in the
> CRP SPL-XVI notification (1 July 2026).

---

## Current pattern (CRP SPL-XVI, 2026)

### Prelims — 100 questions, 125 marks, 80 minutes (qualifying)
| Section | Qs | Marks | Time |
|---|---|---|---|
| English Language | 25 | 25 | 20 min |
| Reasoning | 25 | 25 | 20 min |
| Quantitative Aptitude | 25 | 25 | 20 min |
| **Professional Knowledge (Agriculture)** | **25** | **50 (2 marks/question)** | **20 min** |

### Mains — 152 questions, 225 marks, 155 minutes
| Section | Qs | Marks | Time |
|---|---|---|---|
| English Language | 30 | 30 | 25 min |
| Reasoning | 40 | 40 | 35 min |
| Quantitative Aptitude | 30 | 30 | 25 min |
| **Professional Knowledge (Agriculture) — Objective** | **50** | **100 (2 marks/question)** | **40 min** |
| Descriptive Paper (English) | 2 | 25 | 30 min |

- Negative marking: **1/4th of the marks assigned** to the question (so −0.5 in PK).
- Final merit: **Mains 80 : Interview 20**, and only the **Professional Knowledge**
  score counts for merit — English / Reasoning / Quant are qualifying.

---

## Papers in this folder

| Set | File | Pattern simulated | Questions / Marks |
|---|---|---|---|
| **FINAL** | `afo-2026-final-hard.pdf` | **Mains PK — hard, PYQ-calibrated, 5 options (A–E), English-only answer key** | **50 Q / 100 marks / 40 min** |
| A | `afo-2026-set-a-mains-pk.pdf` | Mains Professional Knowledge (bilingual key) | 50 Q / 100 marks / 40 min |
| B | `afo-2026-set-b-prelims-pk.pdf` | Prelims Professional Knowledge | 25 Q / 50 marks / 20 min |

> The FINAL paper has **no subject headings inside the question paper** (pure exam
> look) and an **English-only answer key**; subject labels are kept only in the
> question-bank JSON for internal review.

Each PDF contains: cover + instructions → bilingual questions (English first,
Hindi below, same option layout) → **answer key with bilingual explanations**.

Markdown versions (`*.md`) are generated alongside for quick review/diffing.

### FINAL paper subject distribution (PYQ-calibrated)
Agronomy 11 · Soil Science 8 · Horticulture 6 · Plant Pathology 7 · Entomology 6 ·
Genetics & Breeding 4 · Agri Economics 3 · Schemes/Finance 3 · Irrigation 3

### Set A subject distribution (mirrors recent AFO papers)
| Subject | Qs |
|---|---|
| Agronomy | 11 |
| Soil Science | 8 |
| Horticulture | 6 |
| Plant Pathology | 7 |
| Entomology | 6 |
| Genetics & Plant Breeding | 4 |
| Agricultural Economics | 3 |
| Agricultural Finance / Schemes | 3 |
| Irrigation & Water Management | 3 |

---

## Regenerating

Question banks live in [`question-banks/`](question-banks/) as plain JSON. Edit/add a bank, then:

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # reportlab, uharfbuzz, freetype-py, Pillow

python scripts/generate_mock_paper.py            # render all banks
python scripts/generate_mock_paper.py --only set-b   # render one bank
```

Output PDFs are written here; `*.pdf` is git-ignored by repo convention, so
regenerate after cloning. The script validates every bank first (answer letter,
option counts, missing fields) and fails loudly on a malformed question.

The renderer reuses the repo's canonical Devanagari engine
(`src/generate_pdf.py` → HarfBuzz + FreeType), so Hindi is correctly shaped and
the text stays selectable.

---

## Fact-checking of the current-affairs questions

The scheme/budget facts used in Sets A and B are from: Union Budget 2025-26
(PM-DDKY, Mission for Aatmanirbharta in Pulses, Mission for Cotton Productivity,
KCC limit ₹3 lakh → ₹5 lakh), Cabinet approval of PM-DDKY (16 July 2025),
Digital Agriculture Mission (₹2,817 crore, 2 September 2024), PM-KISAN,
e-NAM (2016) and NABARD (1982). Re-verify against the latest PIB/IBPS releases
before printing a new edition.
