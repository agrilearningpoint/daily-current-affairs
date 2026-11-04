# -*- coding: utf-8 -*-
"""Weekly and monthly edition layouts (built from the published daily editions).

``src.generate_pdf.generate_pdf`` hands any content whose ``job.type`` is
``weekly`` or ``monthly`` to :func:`generate_period_pdf`.  The daily layout is
untouched.  Every Devanagari string (table cells included) goes through
``text_flowable`` / ``bi_line`` so it is HarfBuzz-shaped, and every section is
reachable from the clickable index (``Anchor`` / ``LinkTo``).

Weekly: cover → index → top stories by section (EN/HI headline, 3-line
bilingual summary, 2-3 Static GK pairs) → 50-MCQ practice set → answer key →
one-liners (EN, HI) → Agriculture Corner → Join Us.
Monthly: cover → index → compact stories by section → quick tables
(appointments, awards, days, MoUs, schemes, reports, sports, obituaries; empty
tables skipped) → 100 MCQs → answer key → one-liners → Agriculture Corner.
"""
from __future__ import annotations

import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (CondPageBreak, Flowable, HRFlowable, KeepTogether, PageBreak,
                                Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle)
from reportlab.lib.pagesizes import A4

import src.generate_pdf as G
from src.generate_pdf import (COLORS, FONT_BOLD, FONT_SEMI, FS_BODY, FS_CHAPTER, FS_FOOTER, FS_MAIN_TITLE,
                              FS_MODULE, FS_TABLE, PAGE_H, PAGE_W, PRINT_W, STYLES, Anchor, LinkTo,
                              _agri_corner_story, _bilingual_options, _clean_text_for_display,
                              _extract_static_gk_pairs, _hi_or_blank, _join_us_box, _option_line,
                              _row_table, _safe, bi_line, highlight_markup, text_flowable, pt)

SECTION_ORDER = ["National", "International", "Economy", "Defence & Science", "Agriculture",
                 "Appointments & Awards", "Sports", "Important Days"]
SECTION_HI = {
    "National": "राष्ट्रीय", "International": "अंतरराष्ट्रीय", "Economy": "अर्थव्यवस्था",
    "Defence & Science": "रक्षा एवं विज्ञान", "Agriculture": "कृषि",
    "Appointments & Awards": "नियुक्तियाँ एवं पुरस्कार", "Sports": "खेल",
    "Important Days": "महत्वपूर्ण दिवस",
}
BAND = HexColor("#0B3D7A")
BAND_SUB = HexColor("#103F7B")
ROW_ALT = HexColor("#F3F7FC")
CARD_BG = COLORS["card_bg"]
COVER_NAVY = HexColor("#0A2540")
COVER_RED = HexColor("#C8102E")
COVER_MUTED = HexColor("#475569")
_UNTITLED_RE = re.compile(r"\buntitled\b", re.IGNORECASE)
_LETTERS = ["A", "B", "C", "D", "E"]

CHANNELS = [
    ("Telegram", "@agrilearningpoint", G.LINK_TELEGRAM),
    ("Daily Quiz", "@agriquizworld", G.LINK_TELEGRAM_QUIZ),
    ("YouTube", "@agrilearningpoint", G.LINK_YOUTUBE),
]


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def _good_headline(text: Any) -> bool:
    t = _clean_text_for_display(text)
    return bool(t) and not _UNTITLED_RE.search(t)


def _section_of(it: Dict[str, Any]) -> str:
    s = it.get("section")
    return s if s in SECTION_HI else "National"


# --------------------------------------------------------------------------- #
# Cover
# --------------------------------------------------------------------------- #
class PeriodCover(Flowable):
    """Full-page cover drawn in page coordinates (suppresses the classic cover)."""

    def __init__(self, kind: str, title: str, date_display: str, stats: List[str],
                 highlights: List[Tuple[str, str]]):
        super().__init__()
        self.kind, self.title, self.date_display = kind, title, date_display
        self.stats, self.highlights = stats, highlights

    def wrap(self, availWidth, availHeight):
        self.width, self.height = availWidth, availHeight
        return availWidth, availHeight

    def draw(self):
        c = self.canv
        x0, y0 = c.absolutePosition(0, 0)
        c.saveState()
        c.translate(-x0, -y0)
        try:
            self._draw(c)
            c._magazine_cover = True
        except Exception as exc:  # fail-soft: classic cover is painted instead
            sys.stderr.write(f"[period_pdf] cover failed, using classic cover: {exc}\n")
        finally:
            c.restoreState()

    def _block(self, c, f: Flowable, x: float, y_top: float, w: float) -> float:
        _w, h = f.wrapOn(c, w, PAGE_H)
        f.drawOn(c, x, y_top - h)
        return h

    def _draw(self, c):
        W, H, M = PAGE_W, PAGE_H, 30 * pt
        iw = W - 2 * M
        c.setFillColor(COLORS["white"]); c.rect(0, 0, W, H, stroke=0, fill=1)
        c.setFillColor(COVER_RED); c.rect(0, H - 8, W, 8, stroke=0, fill=1)
        c.setFillColor(COVER_RED); c.setFont(FONT_BOLD, FS_TABLE)
        c.drawString(M, H - 32, "AGRI LEARNING POINT")
        c.setFillColor(COVER_MUTED); c.setFont(FONT_SEMI, FS_FOOTER)
        c.drawRightString(W - M, H - 32, f"{self.kind.upper()} EDITION  •  BILINGUAL (HINDI + ENGLISH)")

        # Navy title band
        band_top, band_h = H - 46, 178
        c.setFillColor(COVER_NAVY); c.rect(0, band_top - band_h, W, band_h, stroke=0, fill=1)
        c.setFillColor(COLORS["white"]); c.setFont(FONT_BOLD, 40)
        c.drawString(M, band_top - 52, self.kind.upper())
        c.setFont(FONT_BOLD, FS_MAIN_TITLE + 3)
        c.drawString(M, band_top - 88, "CURRENT AFFAIRS")
        hi_kind = "साप्ताहिक करंट अफेयर्स" if self.kind == "weekly" else "मासिक करंट अफेयर्स"
        hi_st = ParagraphStyle("CovHI", parent=STYLES["cover_sub"], textColor=COLORS["white"], alignment=0)
        self._block(c, text_flowable(hi_kind, hi_st, width=iw, bg=COVER_NAVY), M, band_top - 98, iw)
        c.setFillColor(HexColor("#FFD166")); c.setFont(FONT_BOLD, FS_CHAPTER + 2)
        c.drawString(M, band_top - band_h + 18, self.date_display)

        # Exact edition title line
        y = band_top - band_h - 30
        t_st = ParagraphStyle("CovTitle", parent=STYLES["topic_headline"], fontSize=FS_CHAPTER + 1,
                              leading=(FS_CHAPTER + 1) * 1.3, textColor=COVER_NAVY)
        y -= self._block(c, Paragraph(f"<b>{_safe(self.title)}</b>", t_st), M, y, iw) + 8

        # Stats chips
        chip_w = (iw - 8 * (len(self.stats) - 1)) / max(1, len(self.stats))
        for i, s in enumerate(self.stats):
            x = M + i * (chip_w + 8)
            c.setFillColor(HexColor("#EEF5FF")); c.setStrokeColor(HexColor("#9CC3EE"))
            c.roundRect(x, y - 34, chip_w, 34, 8, stroke=1, fill=1)
            c.setFillColor(COVER_NAVY); c.setFont(FONT_BOLD, FS_TABLE)
            c.drawCentredString(x + chip_w / 2, y - 21, s)
        y -= 52

        # Highlights (each one taps through to its story)
        c.setFillColor(COVER_RED); c.setFont(FONT_BOLD, FS_BODY)
        c.drawString(M, y, "TOP STORIES")
        y -= 10
        hl_st = ParagraphStyle("CovHL", parent=STYLES["bullet_en"], fontName=FONT_SEMI)
        for head, key in self.highlights:
            if y < 190:
                break
            p = Paragraph(f'<font color="#C8102E">▸</font> {_safe(head)}' if G.glyph_supported("▸")
                          else f"• {_safe(head)}", hl_st)
            h = self._block(c, p, M, y, iw)
            G.goto_link(c, key, M, y - h, M + iw, y)
            y -= h + 5

        # Channel links
        box_h = 118
        c.setFillColor(HexColor("#FFF7E0")); c.setStrokeColor(COLORS["gold_accent"])
        c.roundRect(M, 44, iw, box_h, 10, stroke=1, fill=1)
        c.setFillColor(COVER_NAVY); c.setFont(FONT_BOLD, FS_BODY + 1)
        c.drawString(M + 14, 44 + box_h - 24, "Join us for daily current affairs & quizzes")
        yy = 44 + box_h - 50
        for label, handle, url in CHANNELS:
            c.setFillColor(COVER_MUTED); c.setFont(FONT_SEMI, FS_BODY)
            c.drawString(M + 14, yy, f"{label}:")
            c.setFillColor(HexColor("#0B57D0")); c.setFont(FONT_BOLD, FS_BODY + 1)
            c.drawString(M + 110, yy, handle)
            tw = c.stringWidth(handle, FONT_BOLD, FS_BODY + 1)
            c.setStrokeColor(HexColor("#0B57D0")); c.setLineWidth(0.6)
            c.line(M + 110, yy - 2, M + 110 + tw, yy - 2)
            c.linkURL(url, (M + 8, yy - 9, M + iw - 8, yy + 17), relative=0)
            yy -= 26


# --------------------------------------------------------------------------- #
# Building blocks
# --------------------------------------------------------------------------- #
def _band(title_en: str, title_hi: str, key: str, color=BAND) -> List[Flowable]:
    head = ParagraphStyle("PBand", parent=STYLES["oneliner_title"], textColor=COLORS["white"])
    sub = ParagraphStyle("PBandHI", parent=STYLES["cover_super"], textColor=COLORS["white"])
    rows: List[List[Any]] = [[text_flowable(title_en, head, width=PRINT_W - 12, bg=color,
                                            markup=f"<b>{_safe(title_en)}</b>")]]
    if title_hi:
        rows.append([text_flowable(title_hi, sub, width=PRINT_W - 12, bg=color)])
    t = Table(rows, colWidths=[PRINT_W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), color),
                           ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    return [Anchor(key, f"{title_en}", 0), t, Spacer(PRINT_W, 8 * pt)]


def _static_gk_box(pairs: List[Tuple[str, str]]) -> Optional[Flowable]:
    if not pairs:
        return None
    inner = PRINT_W - 16 * pt
    rows = [[text_flowable("Static GK | स्थैतिक सामान्य ज्ञान", STYLES["block_head"], width=inner, bg=CARD_BG)]]
    for en, hi in pairs:
        for f in bi_line(en, hi, STYLES["static_fact_en"], STYLES["hi_body"], width=inner, bg=CARD_BG):
            rows.append([f])
    t = Table(rows, colWidths=[PRINT_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CARD_BG), ("BOX", (0, 0), (-1, -1), 0.75, COLORS["card_border"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


_WHOLE_RE = re.compile(r"[.!?।][\"”’')\]]*$")


def _summary(it: Dict[str, Any], n: int) -> List[Tuple[str, str]]:
    """The builder's whole-sentence bullets.  When the builder has decided them
    (``summary_pairs`` present, possibly empty) the raw daily key points are never
    used: they are cut at a character limit and would print half sentences."""
    out: List[Tuple[str, str]] = []
    if "summary_pairs" in it:
        for p in it.get("summary_pairs") or []:
            en = _clean_text_for_display(p.get("en")) if isinstance(p, dict) else ""
            if en and _WHOLE_RE.search(en):
                out.append((en, _hi_or_blank(p.get("hi"))))
        return out[:n]
    en = [_clean_text_for_display(x) for x in it.get("key_points_en") or []]
    hi = list(it.get("key_points_hi") or [])
    out = [(e, _hi_or_blank(hi[i]) if i < len(hi) else "") for i, e in enumerate(en) if e]
    return out[:n]


def _date_tag(it: Dict[str, Any]) -> str:
    d = str(it.get("edition_date") or "")
    try:
        from datetime import date as _d
        x = _d.fromisoformat(d)
        return f"{x.day} {x.strftime('%b')}"
    except ValueError:
        return ""


def _story_block(it: Dict[str, Any], num: int, total: int, compact: bool) -> List[Flowable]:
    sec = _section_of(it)
    en = _clean_text_for_display(it.get("headline_en"))
    hi = _hi_or_blank(it.get("headline_hi"))
    tag = f"<b>{_safe(sec.upper())}</b>   •   STORY {num} OF {total}"
    if _date_tag(it):
        tag += f"   •   {_safe(_date_tag(it))}"
    head_rows: List[List[Any]] = [[Paragraph(tag, STYLES["section_tag"])],
                                  [Paragraph(f"<b>{_safe(en)}</b>", STYLES["topic_headline"])]]
    hi_st = ParagraphStyle("PHeadHI", parent=STYLES["topic_headline"], fontSize=FS_CHAPTER - (1.5 if compact else 0.5))
    if hi:
        head_rows.append([text_flowable(hi, hi_st, width=PRINT_W - 15, bg=COLORS["badge_bg"])])
    head = Table(head_rows, colWidths=[PRINT_W])
    head.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLORS["badge_bg"]),
        ("LINEBEFORE", (0, 0), (0, -1), 3, COLORS["badge_text"]),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    first: List[Flowable] = [Anchor(f"s{num}", f"{num}. {en[:70]}", 1), head, Spacer(PRINT_W, 5 * pt)]
    if not compact:
        first += G._unit_photo_block(it) if G._real_photo_path(it) else []
    lines = _summary(it, 2 if compact else 3)
    rest: List[Flowable] = []
    for i, (e, h) in enumerate(lines):
        f = bi_line(e, h, STYLES["bullet_en"], STYLES["hi_body"], highlight=True)
        (first if i == 0 else rest).extend(f + [Spacer(PRINT_W, 2.5 * pt)])
    out: List[Flowable] = [KeepTogether(first)] + rest
    gk = _static_gk_box(_extract_static_gk_pairs(it, None)[: (2 if compact else 3)])
    if gk is not None:
        out += [Spacer(PRINT_W, 3 * pt), KeepTogether([gk])]
    out += [Spacer(PRINT_W, 7 * pt), HRFlowable(width="100%", thickness=0.5, color=COLORS["border_light"]),
            Spacer(PRINT_W, 8 * pt)]
    return out


def _mcq_block(m: Dict[str, Any], n: int) -> Optional[Flowable]:
    q_en = _clean_text_for_display(m.get("question_en"))
    if not q_en or _UNTITLED_RE.search(q_en):
        return None
    opts = _bilingual_options(m)
    if len(opts) < 4:
        return None
    block: List[Flowable] = [text_flowable(f"Q{n}. {q_en}", STYLES["ques_en"], markup=f"<b>Q{n}.</b> {_safe(q_en)}")]
    q_hi = _hi_or_blank(m.get("question_hi"))
    if q_hi:
        block += [Spacer(PRINT_W, 2 * pt), text_flowable(f"प्रश्न {n}: {q_hi}", STYLES["ques_hi"])]
    block.append(Spacer(PRINT_W, 4 * pt))
    for ltr, (o_en, o_hi) in zip(_LETTERS, opts):
        block += [_option_line(ltr, o_en, o_hi), Spacer(PRINT_W, 1.5 * pt)]
    block.append(Spacer(PRINT_W, 9 * pt))
    return KeepTogether(block)


def _answer_key(rows: List[Tuple[int, str]]) -> List[Flowable]:
    ncol = 5
    cell_st = ParagraphStyle("PKey", parent=STYLES["key_cell"], fontSize=FS_BODY, leading=FS_BODY * 1.35)
    cells = [Paragraph(f"<b>{n}.</b> Ans: <b>{_safe(ltr)}</b>", cell_st) for n, ltr in rows]
    while len(cells) % ncol:
        cells.append(Paragraph("", cell_st))
    grid = [cells[i:i + ncol] for i in range(0, len(cells), ncol)]
    t = Table(grid, colWidths=[PRINT_W / ncol] * ncol, repeatRows=0)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, COLORS["border_light"]),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [COLORS["white"], ROW_ALT]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return [t]


def _quick_table(tbl: Dict[str, Any], key: str) -> List[Flowable]:
    rows_in = [r for r in tbl.get("rows") or [] if isinstance(r, dict) and _good_headline(r.get("en"))]
    if not rows_in:
        return []
    date_w = 62 * pt
    ev_w = PRINT_W - date_w
    inner = ev_w - 14
    head_st = STYLES["index_col_head"]
    data: List[List[Any]] = [[Paragraph("DATE", head_st),
                              Paragraph("EVENT", head_st)]]
    for i, r in enumerate(rows_in):
        bg = COLORS["white"] if i % 2 == 0 else ROW_ALT
        cell: List[Flowable] = [Paragraph(_safe(_clean_text_for_display(r.get("en"))), STYLES["index_cell"])]
        hi = _hi_or_blank(r.get("hi"))
        if hi:
            cell.append(text_flowable(hi, STYLES["toc_hi"], width=inner, bg=bg))
        data.append([Paragraph(_safe(_date_tag({"edition_date": r.get("date")})), STYLES["key_cell"]), cell])
    t = Table(data, colWidths=[date_w, ev_w], repeatRows=1)
    style = [("BACKGROUND", (0, 0), (-1, 0), COLORS["primary"]),
             ("GRID", (0, 0), (-1, -1), 0.5, COLORS["border_light"]),
             ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
             ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
             ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6)]
    for i in range(len(rows_in)):
        style.append(("BACKGROUND", (0, i + 1), (-1, i + 1), COLORS["white"] if i % 2 == 0 else ROW_ALT))
    t.setStyle(TableStyle(style))
    title_en = str(tbl.get("title_en") or "Quick Table")
    sub = ParagraphStyle("QTHead", parent=STYLES["box_title"], fontSize=FS_MODULE - 2, leading=(FS_MODULE - 2) * 1.3)
    head = [Anchor(key, title_en, 1), Paragraph(f"<b>{_safe(title_en)}</b>", sub)]
    if _hi_or_blank(tbl.get("title_hi")):
        head.append(text_flowable(_hi_or_blank(tbl.get("title_hi")), STYLES["hi_body"]))
    return [CondPageBreak(PAGE_H * 0.22), KeepTogether(head + [Spacer(PRINT_W, 4 * pt)]), t, Spacer(PRINT_W, 12 * pt)]


def _index(kind: str, stories: List[Dict[str, Any]], sections: List[Tuple[str, str, str]],
           chips: List[Tuple[str, str]]) -> List[Flowable]:
    out: List[Flowable] = [Anchor("contents", "Contents | विषय-सूची", 0),
                           Paragraph("<b>CONTENTS</b>", STYLES["oneliner_title"]),
                           text_flowable("विषय-सूची  •  किसी भी विषय पर टैप करें", STYLES["cover_super"]),
                           Spacer(PRINT_W, 8 * pt)]
    # Section chips (tap targets)
    chip_st = ParagraphStyle("PChip", parent=STYLES["toc_en"], textColor=HexColor("#0B57D0"))
    ncol = 3
    col_w = (PRINT_W - 3 * (ncol - 1) * pt) / ncol
    cells = []
    for label, key in chips:
        chip = _row_table([Paragraph(f"<u>{_safe(label)}</u>", chip_st)], [col_w], [
            ("BACKGROUND", (0, 0), (-1, -1), HexColor("#EEF5FF")),
            ("BOX", (0, 0), (-1, -1), 0.6, HexColor("#9CC3EE")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)])
        cells.append(LinkTo(chip, key))
    while len(cells) % ncol:
        cells.append(Spacer(1, 1))
    grid = Table([cells[i:i + ncol] for i in range(0, len(cells), ncol)],
                 colWidths=[col_w + 3] * (ncol - 1) + [col_w])
    grid.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                              ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    out += [grid, Spacer(PRINT_W, 8 * pt)]

    num_w = 34 * pt
    st_num = STYLES["toc_num"]
    st_en = STYLES["toc_en"]
    sec_st = ParagraphStyle("PIdxSec", parent=STYLES["block_head"], textColor=BAND)
    n = 0
    for sec_en, sec_hi, key in sections:
        members = [s for s in stories if _section_of(s) == sec_en]
        if not members:
            continue
        out.append(LinkTo(Paragraph(f"<b>{_safe(sec_en.upper())}</b>  ({len(members)})", sec_st), key, min_h=24))
        for s in members:
            n = stories.index(s) + 1
            bg = COLORS["white"] if n % 2 else ROW_ALT
            row = _row_table([Paragraph(f"{n}", st_num),
                              Paragraph(_safe(_clean_text_for_display(s.get("headline_en"))), st_en)],
                             [num_w, PRINT_W - num_w], [
                ("BACKGROUND", (0, 0), (0, 0), COLORS["primary"]), ("BACKGROUND", (1, 0), (1, 0), bg),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LINEBELOW", (0, 0), (-1, -1), 0.5, COLORS["border_light"]),
                ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING", (0, 0), (0, 0), 2), ("LEFTPADDING", (1, 0), (1, 0), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6)], min_h=G.MIN_TAP_PT - 4)
            out.append(LinkTo(row, f"s{n}", full_width=True))
        out.append(Spacer(PRINT_W, 4 * pt))
    out.append(PageBreak())
    return out


# --------------------------------------------------------------------------- #
# Main entry
# --------------------------------------------------------------------------- #
def _story_order(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    good = [it for it in items if isinstance(it, dict) and _good_headline(it.get("headline_en"))]
    rank = {s: i for i, s in enumerate(SECTION_ORDER)}
    return sorted(good, key=lambda it: rank.get(_section_of(it), 99))  # stable within section


def _build_once(content: Dict[str, Any], mcqs: List[Dict[str, Any]], output_path: str,
                compact: bool, one_liner_cap: Optional[int]) -> str:
    job = content.get("job") or {}
    kind = str(job.get("type") or "weekly").lower()
    stories = _story_order(content.get("items") or [])
    if not stories:
        raise ValueError("Empty edition: no titled stories for the period PDF.")
    date_display = str(job.get("date_display") or "")
    title = str(content.get("edition_title") or f"{kind.title()} Current Affairs {date_display}")

    mcq_blocks: List[Tuple[int, str, Flowable]] = []
    for m in mcqs or []:
        if not isinstance(m, dict):
            continue
        n = len(mcq_blocks) + 1
        blk = _mcq_block(m, n)
        if blk is None:
            continue
        opts = _bilingual_options(m)
        ltr = str(m.get("correct") or "").strip().upper()
        mcq_blocks.append((n, ltr if ltr in _LETTERS[:len(opts)] else "A", blk))

    ols = [o for o in content.get("one_liners") or [] if isinstance(o, dict)
           and _good_headline(o.get("text_en"))]
    if one_liner_cap is not None:
        ols = ols[:one_liner_cap]
    tables = [t for t in (content.get("quick_tables") or []) if isinstance(t, dict)
              and any(isinstance(r, dict) and _good_headline(r.get("en")) for r in t.get("rows") or [])]
    has_agri = bool([x for x in ((content.get("agri_corner") or {}).get("items") or [])
                     if isinstance(x, dict) and _clean_text_for_display(x.get("en"))])

    sections = [(s, SECTION_HI[s], f"sec_{_slug(s)}") for s in SECTION_ORDER]
    chips: List[Tuple[str, str]] = []
    if kind == "monthly" and tables:
        chips.append(("Quick Tables", "qt"))
    if mcq_blocks:
        chips += [(f"MCQs ({len(mcq_blocks)})", "mcq"), ("Answer Key", "key")]
    if ols:
        chips += [("One-Liners (EN)", "ol_en"), ("One-Liners (HI)", "ol_hi")]
    if has_agri:
        chips.append(("Agriculture Corner", "agri"))
    chips.append(("Join Us", "join"))

    stats = [f"{len(stories)} TOP STORIES", f"{len(mcq_blocks)} MCQs", f"{len(ols)} ONE-LINERS"]
    highlights = [(_clean_text_for_display(s.get("headline_en")), f"s{i}")
                  for i, s in enumerate(stories, 1)]
    highlights.sort(key=lambda h: -float((stories[int(h[1][1:]) - 1].get("importance_score") or 0)))

    story: List[Flowable] = [PeriodCover(kind, title, date_display, stats, highlights[:10]), PageBreak()]
    story += _index(kind, stories, sections, chips)

    # Stories by section
    for sec_en, sec_hi, key in sections:
        members = [s for s in stories if _section_of(s) == sec_en]
        if not members:
            continue
        story.append(CondPageBreak(PAGE_H * 0.35))
        story += _band(sec_en.upper(), sec_hi, key)
        for s in members:
            story += _story_block(s, stories.index(s) + 1, len(stories), compact)

    # Monthly quick tables
    if kind == "monthly" and tables:
        story.append(PageBreak())
        story += _band("QUICK REVISION TABLES", "त्वरित पुनरावृत्ति तालिकाएँ", "qt", BAND_SUB)
        for i, t in enumerate(tables):
            story += _quick_table(t, f"qt{i}")

    # MCQ practice set + answer key
    if mcq_blocks:
        story.append(PageBreak())
        story += _band(f"PRACTICE SET  •  {len(mcq_blocks)} MCQs", f"अभ्यास प्रश्न  •  {len(mcq_blocks)} बहुविकल्पीय प्रश्न", "mcq")
        for _n, _l, blk in mcq_blocks:
            story.append(blk)
        key_rows = -(-len(mcq_blocks) // 5)
        story.append(CondPageBreak(min(PAGE_H * 0.8, key_rows * 27 * pt + 90 * pt)))
        story += _band("ANSWER KEY", "उत्तर कुंजी", "key", HexColor("#065F46"))
        story += _answer_key([(n, ltr) for n, ltr, _b in mcq_blocks])

    # One-liners
    if ols:
        story.append(PageBreak())
        story += _band("IMPORTANT ONE-LINERS", "", "ol_en")
        for n, o in enumerate(ols, 1):
            en = _clean_text_for_display(o.get("text_en"))
            story += [text_flowable(f"{n}. {en}", STYLES["oneliner"], markup=f"<b>{n}.</b> {highlight_markup(en)}"),
                      Spacer(PRINT_W, 4 * pt)]
        story.append(CondPageBreak(PAGE_H * 0.4))
        story.append(Spacer(PRINT_W, 8 * pt))
        story += _band("महत्वपूर्ण वन-लाइनर", "", "ol_hi")
        for n, o in enumerate(ols, 1):
            hi = _hi_or_blank(o.get("text_hi"))
            if hi:
                story += [text_flowable(f"{n}. {hi}", STYLES["oneliner"], highlight=True), Spacer(PRINT_W, 3 * pt)]

    story += _agri_corner_story(content)
    story += [Spacer(PRINT_W, 14 * pt), Anchor("join"), KeepTogether([_join_us_box()])]

    # Every index link must resolve even if a section ended up empty.
    defined = set()
    for f in story:
        if isinstance(f, Anchor):
            defined.add(f.key)
        elif isinstance(f, KeepTogether):
            defined |= {x.key for x in f._content if isinstance(x, Anchor)}
    wanted = {k for _l, k in chips} | {k for _a, _b, k in sections} | {"contents"} | \
             {f"s{i}" for i in range(1, len(stories) + 1)}
    for key in sorted(wanted - defined):
        story.append(Anchor(key))

    doc = SimpleDocTemplate(output_path, pagesize=A4, leftMargin=30 * pt, rightMargin=30 * pt,
                            topMargin=62 * pt, bottomMargin=44 * pt,
                            title=title, author="Agri Learning Point")
    saved_label, saved_date = G.HEADER_LABEL, G.CURRENT_COVER_DATE
    G.HEADER_LABEL = f"AGRI LEARNING POINT  |  {kind.upper()} CURRENT AFFAIRS"
    G.CURRENT_COVER_DATE = date_display.upper()
    try:
        doc.build(story, canvasmaker=G.ExamGeniusCanvas)
    finally:
        G.HEADER_LABEL, G.CURRENT_COVER_DATE = saved_label, saved_date
    if os.getenv("ALP_PDF_COMPACT", "1") != "0":
        try:
            G.compact_pdf_images(output_path, int(os.getenv("ALP_PDF_COMPACT_COLORS", "16")))
        except Exception:
            pass
    return output_path


def generate_period_pdf(content: Dict[str, Any], mcqs: List[Dict[str, Any]],
                        output_path: Optional[str] = None, date_str: Optional[str] = None) -> str:
    """Render a weekly/monthly edition; stays within PDF_QA_MAX_PAGES by compacting."""
    job = content.get("job") or {}
    kind = str(job.get("type") or "weekly").lower()
    if output_path is None:
        output_path = os.path.join(G.OUTPUT_DIR, f"{job.get('id') or kind}.pdf")
    try:
        max_pages = int(os.getenv("PDF_QA_MAX_PAGES", "45"))
    except ValueError:
        max_pages = 45
    n_ol = len(content.get("one_liners") or [])
    tiers = [(kind == "monthly", None), (True, None), (True, max(10, n_ol // 2))]
    path = output_path
    for compact, cap in tiers:
        path = _build_once(content, mcqs, output_path, compact, cap)
        if G._pdf_page_count(path) <= max_pages:
            break
    return path
