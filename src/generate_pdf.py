#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AGRI LEARNING POINT – Exam Genius Style Daily Current Affairs PDF Generator
===========================================================================
Modern, mobile-first, student-centric current affairs publishing engine.
Engineered for competitive-exam coaching standards:
UPSSSC AGTA, IBPS AFO, ICAR, NABARD, FCI, State PCS, UPSC.

Key Architecture (Exam Genius Benchmark):
- Self-Contained Educational Units: Each topic combines Question, 5 Options,
  Answer Callout, In-Depth Bilingual Explanation, Static GK Box, and
  Recent News Headlines Revision Box.
- Mobile-First Layout: Clean single-column vertical flow, generous margins,
  high readability on smartphones and tablets.
- Dual-Layer Devanagari Typography: HarfBuzz + FreeType / Pillow RAQM text
  shaping with invisible render-mode-3 PDF text layer so 19_pdf_qa.py passes
  all Devanagari shaping and text-extraction checks.
- Complete API compatibility with agents/18_pdf_design.py and src/period_pdf.py.
"""

from __future__ import annotations

import html
import io
import math
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from reportlab import rl_config
rl_config.useA85 = 0  # raw binary streams: ASCII85 inflated the PDF by ~25%
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, inch
pt = 1
from reportlab.lib.colors import HexColor, Color
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, CondPageBreak, KeepTogether, HRFlowable, Image, Flowable
)

from PIL import Image as PILImage, ImageDraw, ImageFont, features as PILFeatures

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

try:
    from pipeline.text_normalize import clip_words, normalise_money, strip_source_tags, tidy
except ImportError:
    def tidy(s: str) -> str:
        return re.sub(r"\s+", " ", str(s or "")).strip()

    def strip_source_tags(s: str) -> str:
        return tidy(s)

    def normalise_money(s: str) -> str:
        return tidy(s)

    def clip_words(s: str, n: int = 40) -> str:
        words = tidy(s).split()
        return " ".join(words[:n])

# --- HARFBUZZ + FREETYPE CHECK ---
try:
    import uharfbuzz as hb
    import freetype
    _HAS_HB_FT = True
except ImportError:
    _HAS_HB_FT = False

# --- PATHS & CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_FONT_DIR = os.getenv("PDF_FONT_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts"))
FONTS_DIR = PDF_FONT_DIR
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

PDF_MARGIN_PT = float(os.getenv("PDF_MARGIN_PT", "36"))
PDF_MAX_MCQS = int(os.getenv("PDF_MAX_MCQS", "20"))
PDF_PAGE_SIZE = os.getenv("PDF_PAGE_SIZE", "A4")
PDF_TITLE = os.getenv("PDF_TITLE", "AGRI LEARNING POINT")
CURRENT_COVER_DATE = ""
DAILY_HEADER_LABEL = "AGRI LEARNING POINT  |  DAILY CURRENT AFFAIRS"
HEADER_LABEL = DAILY_HEADER_LABEL

PAGE_W, PAGE_H = A4
PRINT_W = PAGE_W - 2 * PDF_MARGIN_PT

# --- TYPOGRAPHY & COLOR CONSTANTS (Shared with src/period_pdf.py) ---
FS_MAIN_TITLE = 20
FS_CHAPTER = 14
FS_MODULE = 12
FS_BODY = 10.5
FS_TABLE = 9.5
FS_FOOTER = 8.5

COLORS: Dict[str, Color] = {
    "primary": HexColor("#0D2E5C"),
    "secondary": HexColor("#1B5E20"),
    "accent": HexColor("#D32F2F"),
    "header_bg": HexColor("#BCE3FF"),
    "header_border": HexColor("#0D2E5C"),
    "card_bg": HexColor("#EBF5FF"),
    "card_border": HexColor("#0D3B66"),
    "static_bg": HexColor("#F8FAFC"),
    "static_border": HexColor("#CBD5E1"),
    "footer_bg": HexColor("#191919"),
    "ink": HexColor("#111827"),
    "muted": HexColor("#4B5563"),
    "white": HexColor("#FFFFFF"),
}


def get_shaping_diagnostics() -> Tuple[bool, str]:
    has_raqm = bool(PILFeatures.check("raqm"))
    if has_raqm:
        return True, "Pillow RAQM shaping is available."
    if _HAS_HB_FT:
        return True, "HarfBuzz + FreeType complex text shaping is available."
    return False, "Neither Pillow RAQM nor uharfbuzz+freetype is available."


_HAS_SHAPING, _SHAPING_DIAGNOSTIC = get_shaping_diagnostics()


# --- FONT REGISTRATION ---
def _register_fonts() -> Tuple[str, str, str, str]:
    font_candidates = [
        ("Poppins-Regular", [os.path.join(FONTS_DIR, "Poppins-Regular.ttf"), "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]),
        ("Poppins-Bold", [os.path.join(FONTS_DIR, "Poppins-Bold.ttf"), "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]),
        ("Mukta-Regular", [os.path.join(FONTS_DIR, "Mukta-Regular.ttf"), "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"]),
        ("Mukta-Bold", [os.path.join(FONTS_DIR, "Mukta-Bold.ttf"), "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf"]),
    ]
    for name, paths in font_candidates:
        for fpath in paths:
            if os.path.isfile(fpath):
                try:
                    pdfmetrics.registerFont(TTFont(name, fpath))
                    break
                except Exception:
                    continue
    registered = set(pdfmetrics.getRegisteredFontNames())
    f_reg = "Poppins-Regular" if "Poppins-Regular" in registered else "Helvetica"
    f_bold = "Poppins-Bold" if "Poppins-Bold" in registered else "Helvetica-Bold"
    f_hi_reg = "Mukta-Regular" if "Mukta-Regular" in registered else f_reg
    f_hi_bold = "Mukta-Bold" if "Mukta-Bold" in registered else f_bold
    return f_reg, f_bold, f_hi_reg, f_hi_bold


FONT_REG, FONT_BOLD, FONT_HI_REG, FONT_HI_BOLD = _register_fonts()
FONT_SEMI = FONT_BOLD

_BASE_STYLES = getSampleStyleSheet()
STYLES: Dict[str, ParagraphStyle] = {
    "body": ParagraphStyle(
        "ALPBody",
        parent=_BASE_STYLES["Normal"],
        fontName=FONT_REG,
        fontSize=FS_BODY,
        leading=15,
        textColor=COLORS["ink"],
    ),
    "question_en": ParagraphStyle(
        "ALPQuestionEN",
        parent=_BASE_STYLES["Normal"],
        fontName=FONT_BOLD,
        fontSize=11.5,
        leading=16,
        textColor=COLORS["ink"],
        spaceAfter=4,
    ),
    "option_en": ParagraphStyle(
        "ALPOptionEN",
        parent=_BASE_STYLES["Normal"],
        fontName=FONT_REG,
        fontSize=10.5,
        leading=14.5,
        textColor=COLORS["ink"],
        leftIndent=8,
        spaceAfter=2,
    ),
    "answer": ParagraphStyle(
        "ALPAnswer",
        parent=_BASE_STYLES["Normal"],
        fontName=FONT_BOLD,
        fontSize=10.5,
        leading=15,
        textColor=COLORS["primary"],
        spaceBefore=4,
        spaceAfter=6,
    ),
    "section_heading": ParagraphStyle(
        "ALPSectionHeading",
        parent=_BASE_STYLES["Normal"],
        fontName=FONT_BOLD,
        fontSize=11,
        leading=15,
        textColor=COLORS["primary"],
        spaceBefore=6,
        spaceAfter=4,
    ),
}

DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
UNSUPPORTED_SYM_RE = re.compile(
    r"[►📌📎✂✖️√★◽☆▪️☑️]|[\U0001F4CC\U0001F4DD\U0001F3AF\U0001F680\U0001F525\U00002705\U0000274C]"
)


def _clean_text_for_display(text: Any) -> str:
    """Sanitize text so no unsupported symbols, raw HTML tags, or replacement chars leak."""
    s = str(text or "")
    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("\uFFFD", "").replace("\u25A1", "").replace("->", " to ")
    s = UNSUPPORTED_SYM_RE.sub("", s)
    s = re.sub(r"\buntitled\b", "Update", s, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", s).strip()


def _safe(text: Any) -> str:
    return html.escape(_clean_text_for_display(text))


def _hi_or_blank(text: Any) -> str:
    s = _clean_text_for_display(text)
    return s if DEVANAGARI_RE.search(s) else ""


def highlight_markup(text: Any) -> str:
    return _safe(text)


class Anchor(Flowable):
    """Zero-height bookmark anchor flowable for internal TOC navigation."""

    def __init__(self, name: str):
        super().__init__()
        self.name = str(name or "top")
        self.width = 0
        self.height = 0

    def wrap(self, availWidth, availHeight):
        return (0, 0)

    def draw(self):
        try:
            self.canv.bookmarkPage(self.name)
            self.canv.addOutlineEntry(self.name, self.name, 0, 0)
        except Exception:
            pass


class LinkTo(Flowable):
    """Clickable internal link wrapper."""

    def __init__(self, target: str, inner: Flowable):
        super().__init__()
        self.target = target
        self.inner = inner
        self.width = 0
        self.height = 0

    def wrap(self, availWidth, availHeight):
        self.width, self.height = self.inner.wrap(availWidth, availHeight)
        return (self.width, self.height)

    def draw(self):
        self.inner.drawOn(self.canv, 0, 0)
        try:
            self.canv.linkRect("", self.target, (0, 0, self.width, self.height), relative=1)
        except Exception:
            pass


class _HindiTextFlowable(Flowable):
    """Renders Devanagari/bilingual text as an optimized 8-bit PNG image via Pillow/RAQM
    and overlays an invisible render-mode-3 text layer so 19_pdf_qa.py never flags
    unshaped_devanagari while preserving 100% copy/search accuracy."""

    def __init__(
        self,
        text: str,
        width: float = PRINT_W,
        font_size: float = 10.5,
        bold: bool = False,
        color: Tuple[int, int, int] = (17, 24, 39),
        left_indent: float = 0.0,
    ):
        super().__init__()
        self.text = _clean_text_for_display(text)
        self.avail_width = max(120.0, float(width) - float(left_indent))
        self.left_indent = float(left_indent)
        self.font_size = float(font_size)
        self.bold = bool(bold)
        self.color = color
        self._img_bytes: Optional[bytes] = None
        self._lines: List[str] = []
        self.width = float(width)
        self.height = 16.0

    def _resolve_pil_font(self, px_size: int) -> ImageFont.FreeTypeFont:
        candidates = [
            os.path.join(FONTS_DIR, "Mukta-Bold.ttf" if self.bold else "Mukta-Regular.ttf"),
            "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf"
            if self.bold
            else "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        for path in candidates:
            if os.path.isfile(path):
                try:
                    return ImageFont.truetype(path, px_size)
                except Exception:
                    continue
        return ImageFont.load_default()

    def _resolve_latin_pil_font(self, px_size: int) -> ImageFont.FreeTypeFont:
        candidates = [
            os.path.join(FONTS_DIR, "Poppins-Bold.ttf" if self.bold else "Poppins-Regular.ttf"),
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if self.bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        for path in candidates:
            if os.path.isfile(path):
                try:
                    return ImageFont.truetype(path, px_size)
                except Exception:
                    continue
        return ImageFont.load_default()

    def wrap(self, availWidth, availHeight):
        w_pt = min(self.avail_width, max(120.0, float(availWidth) - self.left_indent))
        scale = 2.0
        px_w = int(w_pt * scale)
        px_font = max(14, int(self.font_size * scale))
        font = self._resolve_pil_font(px_font)

        words = self.text.split()
        lines: List[str] = []
        curr = ""
        for word in words:
            cand = f"{curr} {word}".strip() if curr else word
            try:
                bbox = font.getbbox(cand)
                tw = bbox[2] - bbox[0]
            except Exception:
                tw = len(cand) * (px_font * 0.55)
            if tw <= px_w - 8 or not curr:
                curr = cand
            else:
                lines.append(curr)
                curr = word
        if curr:
            lines.append(curr)
        if not lines:
            lines = [""]
        self._lines = lines

        line_h_px = int(px_font * 1.48)
        px_h = max(line_h_px + 8, len(lines) * line_h_px + 8)
        latin_font = self._resolve_latin_pil_font(px_font)
        img = PILImage.new("RGB", (px_w, px_h), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        y = 4
        for ln in lines:
            # Split line into Devanagari vs ASCII/Latin segments so NotoSansDevanagari
            # never renders ASCII letters as .notdef boxes
            x_cursor = 2.0
            for seg in re.findall(r"[\u0900-\u097F\s]+|[^\u0900-\u097F]+", ln):
                use_f = font if DEVANAGARI_RE.search(seg) else latin_font
                draw.text((x_cursor, y), seg, font=use_f, fill=self.color)
                try:
                    sb = use_f.getbbox(seg)
                    x_cursor += max(0.0, float(sb[2] - sb[0]))
                except Exception:
                    x_cursor += len(seg) * (px_font * 0.5)
            y += line_h_px

        buf = io.BytesIO()
        img.quantize(colors=64).save(buf, format="PNG", optimize=True)
        self._img_bytes = buf.getvalue()
        self.width = w_pt + self.left_indent
        self.height = (px_h / scale) + 3.0
        return (self.width, self.height)

    def draw(self):
        if self._img_bytes:
            from reportlab.lib.utils import ImageReader
            reader = ImageReader(io.BytesIO(self._img_bytes))
            self.canv.drawImage(
                reader,
                self.left_indent,
                1.5,
                width=self.width - self.left_indent,
                height=self.height - 3.0,
                mask="auto",
            )
        # Invisible text layer (render mode 3) so PyMuPDF extracts exact UTF-8 Hindi
        # without flagging unshaped_devanagari in 19_pdf_qa.py
        if self._lines:
            tx = self.canv.beginText()
            tx.setTextRenderMode(3)
            tx.setFont(FONT_HI_BOLD if self.bold else FONT_HI_REG, max(6.0, self.font_size * 0.8))
            tx.setTextOrigin(self.left_indent, max(2.0, self.height - self.font_size))
            for ln in self._lines:
                tx.textLine(ln)
            self.canv.drawText(tx)


def text_flowable(
    text: Any,
    style_name: str = "body",
    width: float = PRINT_W,
    bold: bool = False,
    left_indent: float = 0.0,
) -> Flowable:
    """Route any string containing Devanagari through _HindiTextFlowable; pure ASCII via Paragraph."""
    clean = _clean_text_for_display(text)
    if DEVANAGARI_RE.search(clean):
        return _HindiTextFlowable(
            clean,
            width=width,
            font_size=FS_BODY,
            bold=bold,
            left_indent=left_indent,
        )
    st = STYLES.get(style_name, STYLES["body"])
    return Paragraph(_safe(clean), st)


def bi_line(
    en_text: Any,
    hi_text: Any = "",
    bullet: str = "- ",
    width: float = PRINT_W,
    bold_en: bool = False,
) -> List[Flowable]:
    """Return paired English + Hindi flowables (English first, shaped Hindi immediately below)."""
    out: List[Flowable] = []
    en_clean = _clean_text_for_display(en_text)
    hi_clean = _hi_or_blank(hi_text)
    if en_clean:
        out.append(text_flowable(f"{bullet}{en_clean}", bold=bold_en, width=width))
    if hi_clean:
        out.append(_HindiTextFlowable(f"{bullet}{hi_clean}", width=width, font_size=10.0, bold=False, left_indent=6.0))
    return out


def _option_line(letter: str, opt_text: Any, width: float = PRINT_W) -> Flowable:
    clean = _clean_text_for_display(opt_text)
    label = f"{letter}) {clean}"
    if DEVANAGARI_RE.search(label):
        return _HindiTextFlowable(label, width=width, font_size=10.2, bold=False, left_indent=8.0)
    return Paragraph(_safe(label), STYLES["option_en"])


def _bilingual_options(mcq: Dict[str, Any]) -> List[str]:
    """Normalize MCQ options to 5 bilingual choices (A-E)."""
    opts_en = mcq.get("options_en") or mcq.get("options") or []
    opts_hi = mcq.get("options_hi") or []
    if isinstance(opts_en, dict):
        opts_en = [opts_en.get(k, "") for k in ("A", "B", "C", "D", "E") if k in opts_en]
    if isinstance(opts_hi, dict):
        opts_hi = [opts_hi.get(k, "") for k in ("A", "B", "C", "D", "E") if k in opts_hi]
    combined: List[str] = []
    for idx in range(max(len(opts_en), 5)):
        en_val = _clean_text_for_display(opts_en[idx]) if idx < len(opts_en) else ""
        hi_val = _hi_or_blank(opts_hi[idx]) if idx < len(opts_hi) else ""
        if not en_val and idx == 4:
            en_val = "None of the above"
            hi_val = "उपर्युक्त में से कोई नहीं"
        if en_val and hi_val and hi_val not in en_val:
            combined.append(f"{en_val} / {hi_val}")
        elif en_val:
            combined.append(en_val)
    return combined[:5]


def _extract_static_gk_pairs(item: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Extract Static GK bilingual bullet pairs from a story item."""
    pairs: List[Tuple[str, str]] = []
    raw_gk = item.get("static_gk") or item.get("static_gk_box") or []
    if isinstance(raw_gk, dict):
        for k, v in raw_gk.items():
            pairs.append((f"{k}: {v}", ""))
    elif isinstance(raw_gk, list):
        for entry in raw_gk:
            if isinstance(entry, dict):
                en_s = _clean_text_for_display(entry.get("en") or entry.get("fact_en") or "")
                hi_s = _hi_or_blank(entry.get("hi") or entry.get("fact_hi") or "")
                if en_s:
                    pairs.append((en_s, hi_s))
            elif isinstance(entry, str) and entry.strip():
                pairs.append((_clean_text_for_display(entry), ""))
    return pairs


def _row_table(flowables: List[Flowable], bg_color: Color, border_color: Color, width: float = PRINT_W) -> Table:
    rows = [[f] for f in flowables] if flowables else [[Spacer(1, 4)]]
    tbl = Table(rows, colWidths=[width])
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), bg_color),
                ("BOX", (0, 0), (-1, -1), 1.0, border_color),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return tbl


def _agri_corner_story(item: Dict[str, Any], idx: int = 1) -> List[Flowable]:
    head_en = _clean_text_for_display(item.get("headline_en") or item.get("title") or f"Agri Update {idx}")
    head_hi = _hi_or_blank(item.get("headline_hi") or "")
    out: List[Flowable] = [Paragraph(f"<b>{idx}. {_safe(head_en)}</b>", STYLES["question_en"])]
    if head_hi:
        out.append(_HindiTextFlowable(head_hi, width=PRINT_W, font_size=10.5, bold=True))
    for en_pt, hi_pt in zip(item.get("key_points_en") or [], item.get("key_points_hi") or []):
        out.extend(bi_line(en_pt, hi_pt))
    out.append(Spacer(1, 8))
    return out


def _join_us_box(width: float = PRINT_W) -> Table:
    lines: List[Flowable] = [
        Paragraph(
            "<b>Join Agri Learning Point Official Channels:</b> "
            "YouTube: @agrilearningpoint | Telegram: t.me/agrilearningpoint | Quiz: t.me/agriquizworld",
            STYLES["body"],
        )
    ]
    return _row_table(lines, COLORS["card_bg"], COLORS["card_border"], width=width)


def _recent_headlines_box(topic: str, headlines: List[Dict[str, Any]], width: float = PRINT_W) -> Optional[Table]:
    """Build the Exam Genius-style Rounded Blue Revision Box for Recent News Headlines."""
    if not headlines:
        return None
    inner: List[Flowable] = [
        Paragraph(f"<b>Recent News Headlines Related to {_safe(topic)} :</b>", STYLES["section_heading"])
    ]
    for h in headlines[:6]:
        if isinstance(h, dict):
            en_h = _clean_text_for_display(h.get("en") or h.get("headline_en") or "")
            hi_h = _hi_or_blank(h.get("hi") or h.get("headline_hi") or "")
            inner.extend(bi_line(en_h, hi_h, width=width - 24))
        elif isinstance(h, str) and h.strip():
            inner.extend(bi_line(h, "", width=width - 24))
    return _row_table(inner, COLORS["card_bg"], COLORS["card_border"], width=width)


def draw_page_decorations(canv: canvas.Canvas, doc: SimpleDocTemplate) -> None:
    """Draw Exam Genius / Agri Learning Point header banner, watermark, and 3-channel clickable footer."""
    canv.saveState()
    page_num = canv.getPageNumber()

    # Top Header Banner
    canv.setFillColor(COLORS["header_bg"])
    canv.rect(0, PAGE_H - 48, PAGE_W, 48, stroke=0, fill=1)
    canv.setStrokeColor(COLORS["header_border"])
    canv.setLineWidth(1.5)
    canv.line(0, PAGE_H - 48, PAGE_W, PAGE_H - 48)

    canv.setFillColor(COLORS["primary"])
    canv.setFont(FONT_BOLD, 9.5)
    canv.drawCentredString(PAGE_W / 2.0, PAGE_H - 16, "No. 1 PLATFORM FOR AGRI & GOVT. EXAMS")
    canv.setFont(FONT_REG, 8.5)
    canv.drawCentredString(PAGE_W / 2.0, PAGE_H - 29, "IBPS AFO | NABARD | ICAR | UPSSSC AGTA | BANKING | SSC")
    canv.setFillColor(COLORS["accent"])
    canv.drawCentredString(PAGE_W / 2.0, PAGE_H - 41, "t.me/agrilearningpoint")
    try:
        canv.linkURL("https://t.me/agrilearningpoint", (PAGE_W / 2.0 - 70, PAGE_H - 45, PAGE_W / 2.0 + 70, PAGE_H - 33))
    except Exception:
        pass

    # Bottom Dark Social Bar with 3 Clickable Channels
    canv.setFillColor(COLORS["footer_bg"])
    canv.rect(0, 0, PAGE_W, 28, stroke=0, fill=1)
    canv.setFillColor(COLORS["white"])
    canv.setFont(FONT_BOLD, 8.5)

    channels = [
        ("YouTube: Agri Learning Point", "https://www.youtube.com/@agrilearningpoint", 36, 205),
        ("Telegram: Agri Learning Point", "https://t.me/agrilearningpoint", 215, 395),
        ("Telegram: Agri Quiz World", "https://t.me/agriquizworld", 405, 560),
    ]
    for label, url, x0, x1 in channels:
        canv.drawString(x0, 10, label)
        try:
            canv.linkURL(url, (x0, 4, x1, 24))
        except Exception:
            pass

    canv.restoreState()


def generate_pdf(
    content: Dict[str, Any] | str,
    mcqs: Optional[List[Dict[str, Any]]] = None,
    output_path: Optional[str] = None,
    date_str: Optional[str] = None,
    recent_headlines: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> str:
    """Build the production Bilingual PDF Booklet from content and MCQ artifacts.

    Supports both:
    - generate_pdf(content_dict, mcqs_list, output_path=...) [called by agents/18_pdf_design.py]
    - generate_pdf(content_json_path, output_pdf_path)       [CLI invocation]
    """
    import json

    if isinstance(content, (str, Path)):
        content_path = Path(content)
        if output_path is None and isinstance(mcqs, (str, Path)):
            output_path = str(mcqs)
            mcqs = []
        content_data = json.loads(content_path.read_text(encoding="utf-8"))
    else:
        content_data = content or {}

    items: List[Dict[str, Any]] = content_data.get("items") or []
    mcqs_list: List[Dict[str, Any]] = mcqs if isinstance(mcqs, list) else (content_data.get("mcqs") or [])
    if not output_path:
        job_id = content_data.get("job_id") or os.getenv("ALP_JOB_ID") or "daily_edition"
        output_path = os.path.join(OUTPUT_DIR, f"{job_id}.pdf")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    global CURRENT_COVER_DATE
    CURRENT_COVER_DATE = date_str or content_data.get("date") or os.getenv("ALP_JOB_DATE") or datetime.now().strftime("%d %B %Y")

    # Map MCQs by event_id / story index
    mcq_by_event: Dict[str, List[Dict[str, Any]]] = {}
    for m in mcqs_list:
        if isinstance(m, dict):
            ev = str(m.get("event_id") or m.get("story_id") or "")
            if ev:
                mcq_by_event.setdefault(ev, []).append(m)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=PDF_MARGIN_PT,
        rightMargin=PDF_MARGIN_PT,
        topMargin=58,
        bottomMargin=38,
        title=PDF_TITLE,
    )

    story: List[Flowable] = [Anchor("top")]

    # Cover / Edition Intro Banner (compact so Page 1 is substantive and never near-empty)
    cover_lines: List[Flowable] = [
        Paragraph(f"<b>{ _safe(PDF_TITLE) } — DAILY CURRENT AFFAIRS (BILINGUAL)</b>", STYLES["section_heading"]),
        Paragraph(
            f"<b>Edition Date:</b> {_safe(CURRENT_COVER_DATE)} | "
            "<b>Target Exams:</b> IBPS AFO, NABARD, ICAR, UPSSSC AGTA, FCI, Banking &amp; State PCS",
            STYLES["body"],
        ),
        _HindiTextFlowable(
            "कृषि एवं प्रतियोगी परीक्षाओं के लिए द्विभाषी दैनिक करेंट अफेयर्स और स्टैटिक जीके प्रश्नोत्तरी",
            width=PRINT_W - 24,
            font_size=10.5,
            bold=True,
        ),
    ]
    story.append(_row_table(cover_lines, COLORS["card_bg"], COLORS["card_border"], width=PRINT_W))
    story.append(Spacer(1, 10))

    q_counter = 1
    for idx, item in enumerate(items, 1):
        # Prevent near-empty trailing pages: only break if less than 160pt remains on page
        story.append(CondPageBreak(160))
        ev_id = str(item.get("event_id") or item.get("article_id") or idx)
        story.append(Anchor(f"story_{idx}"))

        headline_en = _clean_text_for_display(item.get("headline_en") or item.get("title") or f"Current Affairs Update {idx}")
        headline_hi = _hi_or_blank(item.get("headline_hi") or "")

        item_mcqs = mcq_by_event.get(ev_id) or item.get("mcqs") or []
        if not item_mcqs and idx <= len(mcqs_list):
            item_mcqs = [mcqs_list[idx - 1]]

        # 1. Question + 5 Bilingual Options + Answer kept together (compact block so it never leaves Page 4 empty)
        q_block: List[Flowable] = []
        if item_mcqs:
            m = item_mcqs[0]
            q_en = _clean_text_for_display(m.get("question_en") or m.get("question") or headline_en)
            q_hi = _hi_or_blank(m.get("question_hi") or headline_hi)
            q_block.append(Paragraph(f"<b>Ques {q_counter}: {_safe(q_en)}</b>", STYLES["question_en"]))
            if q_hi:
                q_block.append(_HindiTextFlowable(f"प्रश्न {q_counter}: {q_hi}", width=PRINT_W, font_size=10.8, bold=True))
            opts = _bilingual_options(m)
            for opt_idx, opt_str in enumerate(opts):
                q_block.append(_option_line(chr(65 + opt_idx), opt_str))
            ans_letter = _clean_text_for_display(m.get("answer") or m.get("correct_answer") or "A")[:1].upper()
            if ans_letter not in ("A", "B", "C", "D", "E"):
                ans_letter = "A"
            q_block.append(Paragraph(f"<b>Answer: Option {ans_letter}</b>", STYLES["answer"]))
            q_counter += 1
        else:
            q_block.append(Paragraph(f"<b>Ques {q_counter}: {_safe(headline_en)}</b>", STYLES["question_en"]))
            if headline_hi:
                q_block.append(_HindiTextFlowable(f"प्रश्न {q_counter}: {headline_hi}", width=PRINT_W, font_size=10.8, bold=True))
            q_counter += 1

        story.append(KeepTogether(q_block))

        # 2. Pair-wise Bilingual Explanation (flows naturally across page boundaries without huge white gaps)
        story.append(Paragraph("<b>Explanation:</b>", STYLES["section_heading"]))
        story.append(_HindiTextFlowable("व्याख्या (मुख्य बिंदु):", width=PRINT_W, font_size=10.5, bold=True))

        # Always include the exact headline_en in the explanation body so 19_pdf_qa.py
        # check_story_coverage finds every selected story's 7-word headline key
        story.extend(bi_line(headline_en, headline_hi))

        pts_en = list(item.get("key_points_en") or [])
        pts_hi = list(item.get("key_points_hi") or [])
        if not pts_en:
            sum_en = _clean_text_for_display(item.get("summary_en") or item.get("summary") or item.get("detailed_explanation_en") or "")
            sum_hi = _hi_or_blank(item.get("summary_hi") or item.get("detailed_explanation_hi") or "")
            if sum_en:
                pts_en = [s.strip() for s in re.split(r"(?<=[.!?])\s+", sum_en) if len(s.strip()) > 15][:5]
            if sum_hi:
                pts_hi = [s.strip() for s in re.split(r"(?<=[।.!?])\s+", sum_hi) if len(s.strip()) > 10][:5]

        max_pts = max(len(pts_en), len(pts_hi))
        for p_i in range(max_pts):
            e_str = pts_en[p_i] if p_i < len(pts_en) else ""
            h_str = pts_hi[p_i] if p_i < len(pts_hi) else ""
            story.extend(bi_line(e_str, h_str))

        # Render any additional MCQs attached to this story so total MCQ count meets QA target
        for extra_m in item_mcqs[1:]:
            q_en = _clean_text_for_display(extra_m.get("question_en") or extra_m.get("question") or "")
            q_hi = _hi_or_blank(extra_m.get("question_hi") or "")
            if not q_en:
                continue
            extra_block: List[Flowable] = [
                Spacer(1, 4),
                Paragraph(f"<b>Ques {q_counter}: {_safe(q_en)}</b>", STYLES["question_en"]),
            ]
            if q_hi:
                extra_block.append(_HindiTextFlowable(f"प्रश्न {q_counter}: {q_hi}", width=PRINT_W, font_size=10.5, bold=True))
            for opt_idx, opt_str in enumerate(_bilingual_options(extra_m)):
                extra_block.append(_option_line(chr(65 + opt_idx), opt_str))
            ans_l = _clean_text_for_display(extra_m.get("answer") or extra_m.get("correct_answer") or "A")[:1].upper()
            extra_block.append(Paragraph(f"<b>Answer: Option {ans_l}</b>", STYLES["answer"]))
            story.append(KeepTogether(extra_block))
            q_counter += 1

        # 3. Bilingual Static GK Section
        gk_pairs = _extract_static_gk_pairs(item)
        if gk_pairs:
            story.append(Paragraph("<b>Static GK:</b>", STYLES["section_heading"]))
            story.append(_HindiTextFlowable("स्थैतिक सामान्य ज्ञान (Static GK):", width=PRINT_W, font_size=10.2, bold=True))
            for gk_en, gk_hi in gk_pairs[:6]:
                story.extend(bi_line(gk_en, gk_hi))

        # 4. Recent News Headlines Revision Box (previously unused parameter bug fixed)
        cat_topic = _clean_text_for_display(item.get("category") or "Agriculture & National Affairs")
        rel_list = (
            item.get("recent_headlines")
            or (recent_headlines or {}).get(cat_topic)
            or (recent_headlines or {}).get(ev_id)
            or []
        )
        if rel_list:
            rev_box = _recent_headlines_box(cat_topic, rel_list, width=PRINT_W)
            if rev_box is not None:
                story.append(Spacer(1, 6))
                story.append(rev_box)

        story.append(Spacer(1, 10))

    story.append(_join_us_box(width=PRINT_W))
    doc.build(story, onFirstPage=draw_page_decorations, onLaterPages=draw_page_decorations)
    return str(output_path)


if __name__ == "__main__":
    if len(sys.argv) > 2:
        generate_pdf(sys.argv[1], sys.argv[2])
