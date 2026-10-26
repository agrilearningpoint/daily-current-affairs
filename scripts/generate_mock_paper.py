#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AGRI LEARNING POINT — IBPS AFO Mock Paper Renderer
==================================================
Renders bilingual (Hindi + English) mock question papers for IBPS AFO
(Agriculture Field Officer) from a plain JSON question bank.

Reuses the canonical Devanagari shaping pipeline of src/generate_pdf.py
(HarfBuzz + FreeType) so Hindi text is correctly shaped, searchable and
selectable inside the PDF.

Outputs, for every JSON bank in docs/mock-papers/question-banks/:
    docs/mock-papers/<slug>.pdf   — print-ready bilingual paper + answer key
    docs/mock-papers/<slug>.md    — review-friendly Markdown source

Usage:
    python3 scripts/generate_mock_paper.py
    python3 scripts/generate_mock_paper.py --only set-a
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from src.generate_pdf import COLORS, render_hindi_flowable  # noqa: E402

DATA_DIR = REPO_ROOT / "docs" / "mock-papers" / "question-banks"
OUT_DIR = REPO_ROOT / "docs" / "mock-papers"
LOGO = REPO_ROOT / "assets" / "logo.png"

PAGE_W, PAGE_H = A4
MARGIN = 15 * mm
FRAME_W = PAGE_W - 2 * MARGIN
FRAME_H = PAGE_H - 2 * MARGIN - 12 * mm
COL_W = FRAME_W / 2

NAVY = COLORS["primary"]
GREEN = COLORS["accent_green"]
SLATE = COLORS["body_text"]
MUTED = COLORS["muted_text"]
LIGHT = COLORS["card_bg"]
BORDER = COLORS["border_light"]
GOLD = COLORS["gold_accent"]

BRAND = "AGRI LEARNING POINT"
TAGLINE = "IBPS AFO (Scale-I) — CRP SPL-XVI · Agriculture Professional Knowledge"


# ─────────────────────────────────────────────────────────────────────────────
# STYLES
# ─────────────────────────────────────────────────────────────────────────────
def styles() -> Dict[str, ParagraphStyle]:
    base = dict(fontName="Poppins", textColor=SLATE, leading=13)
    return {
        "title": ParagraphStyle("title", fontName="Poppins-Bold", fontSize=17, leading=21,
                                textColor=NAVY, spaceAfter=2),
        "subtitle": ParagraphStyle("subtitle", fontName="Poppins-SemiBold", fontSize=10.5,
                                   leading=14, textColor=GREEN),
        "meta": ParagraphStyle("meta", fontName="Poppins", fontSize=8.5, leading=11.5,
                               textColor=MUTED),
        "h2": ParagraphStyle("h2", fontName="Poppins-Bold", fontSize=12, leading=15,
                             textColor=NAVY, spaceBefore=6, spaceAfter=4),
        "body": ParagraphStyle("body", **base, fontSize=9.5),
        "small": ParagraphStyle("small", fontName="Poppins", fontSize=8, leading=10.5,
                                textColor=MUTED),
        "tag": ParagraphStyle("tag", fontName="Poppins-SemiBold", fontSize=7.5, leading=9,
                              textColor=GREEN, spaceAfter=1),
        "q": ParagraphStyle("q", fontName="Poppins-SemiBold", fontSize=9.8, leading=13,
                            textColor=SLATE),
        "opt": ParagraphStyle("opt", fontName="Poppins", fontSize=9.2, leading=12,
                              textColor=SLATE),
        "ans": ParagraphStyle("ans", fontName="Poppins-SemiBold", fontSize=9.2, leading=12,
                              textColor=GREEN),
        "cell": ParagraphStyle("cell", fontName="Poppins", fontSize=8.4, leading=11,
                               textColor=SLATE),
        "cell_hi": ParagraphStyle("cell_hi", fontName="Mukta", fontSize=8.6, leading=11,
                                  textColor=SLATE),
        "cover_note": ParagraphStyle("cover_note", fontName="Poppins", fontSize=8.6,
                                     leading=12.5, textColor=SLATE),
    }


S = styles()
OPT_LETTERS = ["a", "b", "c", "d", "e"]


def hi_para(text: str, size: float = 9.2, width: float = FRAME_W, bold: bool = False):
    """Shaped, selectable Devanagari paragraph."""
    return render_hindi_flowable(
        text or "",
        font_size_pt=size,
        width_pt=width,
        is_bold=bold,
        color_rgb=(0x1E, 0x29, 0x3B),
    )


def rule(color=BORDER, thickness=0.6, space_before=3, space_after=4):
    from reportlab.platypus import HRFlowable

    return HRFlowable(width="100%", thickness=thickness, color=color,
                      spaceBefore=space_before, spaceAfter=space_after)


# ─────────────────────────────────────────────────────────────────────────────
# BUILDING BLOCKS
# ─────────────────────────────────────────────────────────────────────────────
def info_box(rows: List[List[str]]) -> Table:
    data = [[Paragraph(k, S["small"]), Paragraph(v, S["cell"])] for k, v in rows]
    t = Table(data, colWidths=[FRAME_W * 0.30, FRAME_W * 0.70])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.7, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _hindi_list(items: List[str], width: float, size: float = 8.6):
    """Shaped Hindi options/lines in ONE flowable (keeps the block tight)."""
    return [hi_para(text, size, width) for text in items]


def options_block(q: Dict[str, Any], hindi: bool) -> Table:
    """Options as a single tight vertical list."""
    opts = q["opts_hi"] if hindi else q["opts_en"]
    letters = OPT_LETTERS[: len(opts)]
    if hindi:
        # one tight running line: (a) ... (b) ... (c) ... — standard Hindi paper style
        joined = "     ".join(f"({l}) {t}" for l, t in zip(letters, opts))
        return [hi_para(joined, 8.8, FRAME_W)]
    rows = [[Paragraph(f"({l})&nbsp;&nbsp;{t}", S["opt"])] for l, t in zip(letters, opts)]
    t = Table(rows, colWidths=[FRAME_W])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))
    return t


def question_block(q: Dict[str, Any], show_subject: bool = True) -> KeepTogether:
    parts: List[Any] = []
    if show_subject:
        parts.append(Paragraph(
            f"Q{q['n']}. <font color='#0D7A42' size=7.5>{q['subject_en'].upper()}</font>",
            S["tag"],
        ))
        parts.append(Paragraph(q["q_en"], S["q"]))
    else:
        parts.append(Paragraph(f"<b>Q{q['n']}.</b> {q['q_en']}", S["q"]))
    parts.append(Spacer(1, 2))
    parts.append(hi_para(q["q_hi"], 9.4, FRAME_W, bold=False))
    parts.append(Spacer(1, 3))
    for block in (options_block(q, hindi=False), options_block(q, hindi=True)):
        if isinstance(block, list):
            parts.extend(block)
        else:
            parts.append(block)
    parts += [Spacer(1, 2), rule(space_before=1, space_after=5)]
    return KeepTogether(parts)


def answer_rows(questions: List[Dict[str, Any]], show_subject: bool = True,
               hindi: bool = True) -> Table:
    head_cells = [Paragraph("<b>Q</b>", S["cell"]), Paragraph("<b>Ans</b>", S["cell"])]
    if show_subject:
        head_cells.append(Paragraph("<b>Topic</b>", S["cell"]))
    head_cells.append(Paragraph("<b>Explanation</b>" + (" / व्याख्या" if hindi else ""), S["cell"]))
    data = [head_cells]
    for q in questions:
        expl: List[Any] = [Paragraph(q["exp_en"], S["cell"])]
        if hindi and q.get("exp_hi"):
            expl += [Spacer(1, 1), hi_para(q["exp_hi"], 8.6, FRAME_W - 140)]
        row = [Paragraph(str(q["n"]), S["cell"]), Paragraph(q["ans"].upper(), S["ans"])]
        if show_subject:
            row.append(Paragraph(q["subject_en"], S["small"]))
        row.append(expl)
        data.append(row)

    if show_subject:
        widths = [28, 26, 72, FRAME_W - 126]
    else:
        widths = [28, 28, FRAME_W - 56]
    t = Table(data, colWidths=widths, repeatRows=1)
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.7, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#FAFCFD")))
    t.setStyle(TableStyle(style))
    return t


# ─────────────────────────────────────────────────────────────────────────────
# PAGE DECORATION
# ─────────────────────────────────────────────────────────────────────────────
class PaperDoc(BaseDocTemplate):
    def __init__(self, filename: str, title: str, set_label: str, **kw):
        super().__init__(filename, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                         topMargin=MARGIN, bottomMargin=MARGIN, title=title,
                         author=BRAND, subject=TAGLINE, **kw)
        self.paper_title = title
        self.set_label = set_label
        frame = Frame(MARGIN, MARGIN, FRAME_W, FRAME_H + 6 * mm, id="body",
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([PageTemplate(id="main", frames=[frame],
                                            onPage=self._decorate)])

    def _decorate(self, canv, doc):
        canv.saveState()
        # top band
        canv.setFillColor(NAVY)
        canv.rect(0, PAGE_H - 11 * mm, PAGE_W, 11 * mm, stroke=0, fill=1)
        canv.setFillColor(colors.white)
        canv.setFont("Poppins-Bold", 8.2)
        canv.drawString(MARGIN, PAGE_H - 7.2 * mm, BRAND)
        canv.setFont("Poppins", 7.4)
        canv.setFillColor(colors.HexColor("#A7F3D0"))
        canv.drawRightString(PAGE_W - MARGIN, PAGE_H - 7.2 * mm,
                             f"{self.set_label} · Agriculture Professional Knowledge")
        # footer
        canv.setStrokeColor(BORDER)
        canv.setLineWidth(0.6)
        canv.line(MARGIN, 11 * mm, PAGE_W - MARGIN, 11 * mm)
        canv.setFillColor(MUTED)
        canv.setFont("Poppins", 7.2)
        canv.drawString(MARGIN, 7 * mm, "Free practice material · agrilearningpoint")
        canv.drawRightString(PAGE_W - MARGIN, 7 * mm, f"Page {doc.page}")
        canv.restoreState()


# ─────────────────────────────────────────────────────────────────────────────
# PDF
# ─────────────────────────────────────────────────────────────────────────────
def build_pdf(bank: Dict[str, Any], out_path: Path) -> Path:
    qs = bank["questions"]
    show_subject = bank.get("show_subject", True)
    hindi_key = bank.get("answer_key_language", "both") != "en"
    marks_per_q = 2  # professional knowledge carries 2 marks per question
    total_marks = len(qs) * marks_per_q
    label = f"SET {bank['set']}"

    doc = PaperDoc(str(out_path), title=bank["title_en"], set_label=label)
    flow: List[Any] = []

    # ── cover / instructions ──────────────────────────────────────────────
    if LOGO.exists():
        logo = Image(str(LOGO), width=26 * mm, height=26 * mm)
        logo.hAlign = "LEFT"
        flow.append(logo)
        flow.append(Spacer(1, 2))
    flow.append(Paragraph(BRAND, S["meta"]))
    flow.append(Paragraph(bank["title_en"], S["title"]))
    flow.append(hi_para(bank["title_hi"], 12.5, FRAME_W, bold=True))
    flow.append(Spacer(1, 3))
    flow.append(Paragraph(f"{bank['exam']} · {bank['stage']} · {label}", S["subtitle"]))
    flow.append(Spacer(1, 8))
    flow.append(info_box([
        ("Pattern / पैटर्न", bank["pattern_en"]),
        ("कुल / Total", f"{len(qs)} प्रश्न · {total_marks} अंक · अंत में व्याख्या सहित उत्तर कुंजी"),
        ("Merit note / मेरिट", "Mains merit is built on the Professional Knowledge score only "
                                "(80% mains : 20% interview). | मेरिट केवल व्यावसायिक ज्ञान अंक "
                                "से बनती है (80:20)।"),
    ]))
    flow.append(Spacer(1, 10))
    flow.append(Paragraph("Instructions / निर्देश", S["h2"]))
    instructions = [
        ("1", "Sectional timing applies in the real exam — attempt this set in one sitting with a timer.",
         "वास्तविक परीक्षा में अनुभागीय समय होता है — इस सेट को घड़ी लगाकर एक ही बैठक में हल करें।"),
        ("2", "Negative marking is 1/4th of the marks assigned to the question; skip blind guesses.",
         "नेगेटिव मार्किंग प्रश्न के निर्धारित अंकों का 1/4 भाग है; अनुमान से उत्तर न दें।"),
        ("3", "Questions are bilingual — English first, Hindi immediately below.",
         "प्रश्न द्विभाषी हैं — पहले अंग्रेज़ी, उसके तुरंत नीचे हिन्दी।"),
        ("4", "Mark one option per question; use the answer key only after the full attempt.",
         "प्रति प्रश्न एक विकल्प चुनें; उत्तर कुंजी पूरा प्रयास करने के बाद ही देखें।"),
    ]
    rows = [[Paragraph("<b>#</b>", S["cell"]), Paragraph("<b>Instruction</b>", S["cell"])]]
    for n, en, hi in instructions:
        rows.append([Paragraph(n, S["cell"]), [Paragraph(en, S["cover_note"]), hi_para(hi, 8.6, FRAME_W - 60)]])
    t = Table(rows, colWidths=[16, FRAME_W - 16])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.7, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    flow.append(t)
    flow.append(PageBreak())

    # ── questions ─────────────────────────────────────────────────────────
    flow.append(Paragraph(f"{label} — Questions / प्रश्न", S["h2"]))
    flow.append(Paragraph(f"{len(qs)} questions · {total_marks} marks · bilingual", S["small"]))
    flow.append(rule(thickness=1.1, color=GREEN, space_after=8))
    for q in qs:
        flow.append(question_block(q, show_subject))
    flow.append(PageBreak())

    # ── answer key ────────────────────────────────────────────────────────
    key_title = "Answer Key with Explanations" + (" / उत्तर कुंजी एवं व्याख्या" if hindi_key else "")
    flow.append(Paragraph(key_title, S["h2"]))
    flow.append(Paragraph("Tick your score: +2 for a correct answer, −0.5 for a wrong one "
                          "(professional knowledge carries double marks).", S["small"]))
    flow.append(rule(thickness=1.1, color=GOLD, space_after=8))
    flow.append(answer_rows(qs, show_subject, hindi_key))

    doc.build(flow)
    return out_path


# ─────────────────────────────────────────────────────────────────────────────
# MARKDOWN
# ─────────────────────────────────────────────────────────────────────────────
def build_markdown(bank: Dict[str, Any]) -> str:
    qs = bank["questions"]
    show_subject = bank.get("show_subject", True)
    hindi_key = bank.get("answer_key_language", "both") != "en"
    lines = [
        f"# {bank['title_en']} — Set {bank['set']}",
        "",
        f"**{bank['title_hi']}**",
        "",
        f"- **Exam:** {bank['exam']}",
        f"- **Stage:** {bank['stage']}",
        f"- **Pattern:** {bank['pattern_en']}",
        f"- **पैटर्न:** {bank['pattern_hi']}",
        "",
        "---",
        "",
    ]
    for q in qs:
        head = f"### Q{q['n']}."
        if show_subject:
            head += f" [{q['subject_en']} / {q['subject_hi']}]"
        lines.append(head)
        lines.append("")
        lines.append(q["q_en"])
        lines.append("")
        lines.append(q["q_hi"])
        lines.append("")
        for i, (en, hi) in enumerate(zip(q["opts_en"], q["opts_hi"])):
            letter = OPT_LETTERS[i]
            lines.append(f"- **({letter})** {en} / {hi}")
        lines.append("")
    lines += ["---", "", "## Answer Key" + (" / उत्तर कुंजी" if hindi_key else "")]
    if show_subject:
        lines += ["", "| Q | Ans | Topic | Explanation" + (" | व्याख्या |" if hindi_key else " |"),
                  "|---|---|---|---|" + ("---|" if hindi_key else "")]
    else:
        lines += ["", "| Q | Ans | Explanation" + (" | व्याख्या |" if hindi_key else " |"),
                  "|---|---|---|" + ("---|" if hindi_key else "")]
    for q in qs:
        cells = [str(q["n"]), f"**{q['ans'].upper()}**"]
        if show_subject:
            cells.append(q["subject_en"])
        cells.append(q["exp_en"].replace("|", "/"))
        if hindi_key:
            cells.append((q.get("exp_hi") or "").replace("|", "/"))
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    return "\n".join(lines)


def validate(bank: Dict[str, Any], path: Path) -> None:
    """Fail loudly on a malformed question bank (wrong answer letter, missing fields)."""
    problems = []
    hindi_key = bank.get("answer_key_language", "both") != "en"
    for q in bank["questions"]:
        n = q.get("n")
        if q.get("ans") not in OPT_LETTERS[: len(q.get("opts_en", []))]:
            problems.append(f"Q{n}: invalid answer key {q.get('ans')!r}")
        for lang in ("en", "hi"):
            if len(q.get(f"opts_{lang}", [])) != len(q.get("opts_en", [])):
                problems.append(f"Q{n}: option count mismatch in {lang}")
            for field in (f"q_{lang}", f"opts_{lang}"):
                if not q.get(field):
                    problems.append(f"Q{n}: missing {field}")
            if not q.get("exp_en"):
                problems.append(f"Q{n}: missing exp_en")
            if hindi_key and lang == "hi" and not q.get("exp_hi"):
                problems.append(f"Q{n}: missing exp_hi")
    if problems:
        raise SystemExit(f"{path.name}: " + "; ".join(problems))


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def main() -> int:
    ap = argparse.ArgumentParser(description="Render IBPS AFO mock papers")
    ap.add_argument("--only", help="Render only banks whose filename contains this text")
    args = ap.parse_args()

    banks = sorted(DATA_DIR.glob("*.json"))
    if not banks:
        print(f"No question banks found in {DATA_DIR}")
        return 1

    for path in banks:
        if args.only and args.only not in path.name:
            continue
        bank = json.loads(path.read_text(encoding="utf-8"))
        validate(bank, path)
        slug = slugify(path.stem.replace("ibps-afo-2026-", "afo-2026-"))
        md_path = OUT_DIR / f"{slug}.md"
        pdf_path = OUT_DIR / f"{slug}.pdf"
        md_path.write_text(build_markdown(bank), encoding="utf-8")
        build_pdf(bank, pdf_path)
        print(f"✔ {bank['set']} → {pdf_path.relative_to(REPO_ROOT)} "
              f"({len(bank['questions'])} Q) + {md_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
