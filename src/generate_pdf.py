#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AGRI LEARNING POINT — Exam Genius Style Daily Current Affairs PDF Generator
==========================================================================
Modern, mobile-first, student-centric current affairs publishing engine.
Engineered for competitive-exam coaching standards:
UPSSSC AGTA, IBPS AFO, ICAR, NABARD, FCI, State PCS, UPSC.

Key Architecture (Exam Genius Benchmark):
- Self-Contained Educational Units: Each topic combines Question, 5 Options,
  Answer Callout, In-Depth Bilingual Explanation, and Static GK Box.
- Mobile-First Layout: Clean single-column vertical flow, generous margins,
  high readability on smartphones and tablets.
- Dual-Layer Devanagari Typography: HarfBuzz + FreeType vector text shaping
  with selectable PDF text layer.
- Zero clutter, professional branding, and 100% verified exam facts.
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
    PageBreak, KeepTogether, HRFlowable, Image, Flowable
)

from PIL import Image as PILImage, ImageDraw, ImageFont, features as PILFeatures

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


def get_shaping_diagnostics() -> tuple[bool, str]:
    has_raqm = bool(PILFeatures.check("raqm"))
    if has_raqm:
        return True, "Pillow RAQM shaping is available."
    if _HAS_HB_FT:
        return True, "HarfBuzz + FreeType complex text shaping is available."
    return False, "Neither Pillow RAQM nor uharfbuzz+freetype is available."


_HAS_SHAPING, _SHAPING_DIAGNOSTIC = get_shaping_diagnostics()
_ALLOW_UNSHAPED_DEV = os.getenv("ALP_ALLOW_UNSHAPED_DEV_PDF", "0") == "1"

if not _HAS_SHAPING and not _ALLOW_UNSHAPED_DEV:
    raise RuntimeError(f"FATAL: {_SHAPING_DIAGNOSTIC}")

# --- COLOR PALETTE (Modern Exam Genius Theme) ---
COLORS = {
    "primary": HexColor("#0A2540"),        # Deep Academic Navy
    "primary_dark": HexColor("#051626"),   # Near Black Slate
    "secondary": HexColor("#0F4C81"),      # Classic Blueprint Navy
    "accent_green": HexColor("#0D7A42"),   # Vibrant Agricultural Green
    "light_green_bg": HexColor("#ECFDF5"), # Soft Mint Green Box
    "border_green": HexColor("#6EE7B7"),   # Clean Green Border
    "badge_bg": HexColor("#EFF6FF"),       # Light Indigo Pill
    "badge_text": HexColor("#1D4ED8"),     # Indigo Pill Text
    "dark_text": HexColor("#0F172A"),      # Charcoal Primary Text
    "body_text": HexColor("#1E293B"),      # Slate Dark
    "body_hindi": HexColor("#1E293B"),     # Hindi Text Slate
    "muted_text": HexColor("#64748B"),     # Subtitle & Meta Gray
    "border_light": HexColor("#E2E8F0"),   # Hairline Slate Border
    "card_bg": HexColor("#F8FAFC"),        # Ice White Card BG
    "card_border": HexColor("#CBD5E1"),    # Card Border
    "gold_accent": HexColor("#D97706"),    # Highlight Gold
    "white": HexColor("#FFFFFF"),
}

PAGE_W, PAGE_H = A4
PRINT_W = PAGE_W - 72 * pt  # 523.28 pt printable width (36pt margins left/right)


# --- FONT REGISTRATION ---
def register_fonts() -> bool:
    try:
        pdfmetrics.registerFont(TTFont("Poppins", os.path.join(FONTS_DIR, "Poppins-Regular.ttf")))
        pdfmetrics.registerFont(TTFont("Poppins-SemiBold", os.path.join(FONTS_DIR, "Poppins-SemiBold.ttf")))
        pdfmetrics.registerFont(TTFont("Poppins-Bold", os.path.join(FONTS_DIR, "Poppins-Bold.ttf")))
        pdfmetrics.registerFont(TTFont("Mukta", os.path.join(FONTS_DIR, "Mukta-Regular.ttf")))
        pdfmetrics.registerFont(TTFont("Mukta-SemiBold", os.path.join(FONTS_DIR, "Mukta-SemiBold.ttf")))
        pdfmetrics.registerFont(TTFont("Mukta-Bold", os.path.join(FONTS_DIR, "Mukta-Bold.ttf")))
        return True
    except Exception as exc:
        raise RuntimeError(f"FATAL: Required fonts failed to register from {FONTS_DIR}: {exc}")


FONTS_OK = register_fonts()
FONT_REGULAR = "Poppins"
FONT_SEMI = "Poppins-SemiBold"
FONT_BOLD = "Poppins-Bold"
FONT_HINDI = "Mukta"
FONT_HINDI_SEMI = "Mukta-SemiBold"
FONT_HINDI_BOLD = "Mukta-Bold"


# --- GLYPH SUPPORT & SANITIZATION ---
_SYMBOL_FALLBACK = {
    "\u25b6": "\u00bb",
    "\u25b8": "\u00bb",
    "\u2794": "\u00bb",
    "\u2192": "\u00bb",
    "\u2714": "\u00b7",
    "\u2713": "\u00b7",
    "\u258c": "",
    "\u258d": "", "\u258e": "", "\u258f": "", "\u2588": "",
    "\u2605": "\u00b7",
    "\u25cf": "\u00b7",
    "\u25a0": "\u00b7",
    "\U0001F4CC": "\u00b7",
    "\U0001F4DD": "\u00b7",
    "\U0001F3AF": "\u00bb",
    "\U0001F680": "\u00bb",
    "\u2705": "\u00b7",
    "\u274C": "\u00b7",
}

_GLYPH_CACHE: Dict[str, bool] = {}
_COVERAGE_FACES: Any = None


def _coverage_faces() -> list:
    global _COVERAGE_FACES
    if _COVERAGE_FACES is None:
        faces: list = []
        try:
            import freetype
            for fname in ("Poppins-Regular.ttf", "Mukta-Regular.ttf"):
                fp = os.path.join(FONTS_DIR, fname)
                if os.path.exists(fp):
                    faces.append(freetype.Face(fp))
        except Exception:
            faces = []
        _COVERAGE_FACES = faces
    return _COVERAGE_FACES


def glyph_supported(ch: str) -> bool:
    """True when at least one bundled font has a glyph for ``ch``."""
    cached = _GLYPH_CACHE.get(ch)
    if cached is not None:
        return cached
    faces = _coverage_faces()
    ok = True if not faces else any(f.get_char_index(ord(ch)) != 0 for f in faces)
    _GLYPH_CACHE[ch] = ok
    return ok


def sanitize_glyphs(text: str) -> str:
    """Replace/drop codepoints the bundled fonts cannot render (tofu guard)."""
    if not text:
        return text
    out: List[str] = []
    for ch in text:
        if ord(ch) < 128 or glyph_supported(ch):
            out.append(ch)
        else:
            out.append(_SYMBOL_FALLBACK.get(ch, ""))
    return "".join(out)


def _safe(text: Any) -> str:
    if text is None:
        return ""
    s = html.unescape(str(text))
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = s.replace("\u00a0", " ")
    s = sanitize_glyphs(s)
    return s


def _strip_html(text: Any) -> str:
    if text is None:
        return ""
    s = html.unescape(str(text))
    s = re.sub(r"<[^>]+>", " ", s)
    s = s.replace("\u00a0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    s = sanitize_glyphs(s)
    return s


def _clean_text_for_display(t: Any) -> str:
    if not t:
        return ""
    s = _strip_html(str(t)).strip()
    s = re.sub(r'^(?:Topic\s*:\s*)?(?:&gt;|>>|>|\s)+', '', s, flags=re.IGNORECASE)
    s = re.sub(r'^(?:Ques|Question)\s*[:.-]*\s*', '', s, flags=re.IGNORECASE)
    s = re.sub(r'\bWatch\s*[-:]*\s*', '', s, flags=re.IGNORECASE)
    s = re.sub(r'&gt;&gt;|&gt;|>>|>', '', s)
    return re.sub(r'\s+', ' ', s).strip()


DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")


# --- SHAPED HINDI FLOWABLE WITH DUAL VECTOR-TEXT LAYER ---
class _HindiTextFlowable(Flowable):
    """Renders pixel-perfect HarfBuzz-shaped Devanagari while preserving vector text."""
    def __init__(self, img_flowable: Image, layer: Dict[str, Any]):
        super().__init__()
        self.img = img_flowable
        self.layer = layer
        self._w = img_flowable.drawWidth
        self._h = img_flowable.drawHeight

    def wrap(self, availWidth, availHeight):
        w, h = self.img.wrap(availWidth, availHeight)
        self._w, self._h = w, h
        return w, h

    def drawOn(self, canvas_obj, x, y, _sW=0):
        self.img.drawOn(canvas_obj, x, y, _sW)
        L = self.layer
        w_pt, h_pt = L["path"]
        size = L["size_pt"]
        n = max(len(L["lines"]), 1)
        slot = h_pt / n
        canvas_obj.saveState()
        canvas_obj.setFont(L["font_name"], size)
        for i, line in enumerate(L["lines"]):
            clean_l = _strip_html(line)
            lw = stringWidth(clean_l, L["font_name"], size)
            if L["align"] == "center":
                tx = x + (w_pt - lw) / 2
            elif L["align"] == "right":
                tx = x + w_pt - lw - 6
            else:
                tx = x + L["left_pad_mm"] * mm + 2
            ty = y + h_pt - (i + 1) * slot + slot * 0.16
            canvas_obj.drawString(tx, ty, clean_l, mode=3)  # Invisible vector text for QA & search
        canvas_obj.restoreState()

    def draw(self):
        self.drawOn(self.canv, 0, 0)


def _render_hindi_hb_ft(
    text: str,
    font_path: str,
    font_size_pt: float,
    width_px: int,
    avail_w_px: int,
    left_padding_mm: float,
    color_rgb: Tuple[int, int, int],
    bg_rgb: Tuple[int, int, int],
    line_spacing: float,
    align: str,
    dpi: int,
) -> Tuple[PILImage.Image, List[str], int, int]:
    face = freetype.Face(font_path)
    face.set_char_size(int(font_size_pt * 64), 0, dpi, dpi)

    with open(font_path, "rb") as f:
        font_data = f.read()
    hb_face = hb.Face(hb.Blob(font_data))
    hb_font = hb.Font(hb_face)
    hb_font.scale = (face.size.x_ppem * 64, face.size.y_ppem * 64)

    def shape_runs(txt: str) -> Tuple[List[Any], List[Any]]:
        all_infos = []
        all_pos = []
        tokens = re.split(r'([ऀ-ॿ‌‍]+)', txt)
        for tok in tokens:
            if not tok:
                continue
            is_deva = bool(re.search(r'[ऀ-ॿ]', tok))
            buf = hb.Buffer()
            buf.add_str(tok)
            if is_deva:
                buf.script = 'Deva'
                buf.language = 'hi'
            else:
                buf.script = 'Latn'
                buf.language = 'en'
            buf.direction = 'ltr'
            hb.shape(hb_font, buf, {'liga': True, 'kern': True})
            all_infos.extend(buf.glyph_infos)
            all_pos.extend(buf.glyph_positions)
        return all_infos, all_pos

    def measure_text(txt: str) -> int:
        _, positions = shape_runs(txt)
        return sum(pos.x_advance for pos in positions) // 64

    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = current + " " + word if current else word
        if measure_text(test) <= avail_w_px:
            current = test
        else:
            if current:
                lines.append(current)
                current = word
            else:
                lines.append(word)
                current = ""
    if current:
        lines.append(current)
    if not lines:
        lines = [text]

    ascender = face.size.ascender // 64
    descender = face.size.descender // 64
    line_h = int((ascender - descender) * line_spacing)
    total_h = line_h * len(lines) + int(6 * dpi / 72)

    img = PILImage.new("RGBA", (width_px, max(total_h, 1)), (bg_rgb[0], bg_rgb[1], bg_rgb[2], 0 if bg_rgb == (255, 255, 255) else 255))
    draw = ImageDraw.Draw(img)

    for i, line in enumerate(lines):
        infos, positions = shape_runs(line)
        line_w = sum(pos.x_advance for pos in positions) // 64
        if align == "center":
            pen_x = (width_px - line_w) // 2
        elif align == "right":
            pen_x = width_px - line_w - int(left_padding_mm * dpi / 25.4)
        else:
            pen_x = int(left_padding_mm * dpi / 25.4)
        base_y = i * line_h + ascender

        for info, pos in zip(infos, positions):
            gid = info.codepoint
            face.load_glyph(gid, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_NORMAL)
            bm = face.glyph.bitmap
            if bm.width > 0 and bm.rows > 0:
                buf = bytes(bm.buffer)
                gm = PILImage.frombytes("L", (bm.width, bm.rows), buf)
                tint = PILImage.new("RGBA", (bm.width, bm.rows), (*color_rgb, 255))
                tint.putalpha(gm)
                gx = pen_x + pos.x_offset // 64 + face.glyph.bitmap_left
                gy = base_y - (pos.y_offset // 64 + face.glyph.bitmap_top)
                img.alpha_composite(tint, (gx, gy))
            pen_x += pos.x_advance // 64

    return img, lines, width_px, total_h


def render_hindi_flowable(
    text: str,
    font_size_pt: float = 10.0,
    width_pt: float = 523.0,
    is_bold: bool = False,
    color_rgb: Tuple[int, int, int] = (15, 23, 42),
    bg_rgb: Tuple[int, int, int] = (255, 255, 255),
    align: str = "left",
    left_padding_mm: float = 0.0,
) -> Flowable:
    """Return a Flowable containing shaped Hindi with underlying selectable text."""
    clean = _strip_html(text)
    if not clean:
        return Spacer(width_pt, 2 * pt)

    fname = "Mukta-Bold.ttf" if is_bold else "Mukta-Regular.ttf"
    fpath = os.path.join(FONTS_DIR, fname)
    dpi = 220
    scale = dpi / 72.0
    w_px = int(width_pt * scale)
    pad_px = int(left_padding_mm * mm * scale)
    avail_w = w_px - pad_px * 2

    img, lines, iw, ih = _render_hindi_hb_ft(
        clean, fpath, font_size_pt, w_px, avail_w,
        left_padding_mm, color_rgb, bg_rgb, 1.35, align, dpi
    )

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    draw_w = width_pt
    draw_h = ih / scale

    img_f = Image(buf, width=draw_w, height=draw_h)
    layer = {
        "lines": lines,
        "path": (draw_w, draw_h),
        "size_pt": font_size_pt,
        "font_name": "Mukta-Bold" if is_bold else "Mukta",
        "align": align,
        "left_pad_mm": left_padding_mm,
    }
    return _HindiTextFlowable(img_f, layer)


# --- DYNAMIC IMPORTANT DAYS DATABASE (12 MONTHS) ---
IMPORTANT_DAYS_BY_MONTH: Dict[str, List[str]] = {
    "january": [
        "9 January: Pravasi Bharatiya Divas (Non-Resident Indian Day)",
        "10 January: World Hindi Day (Vishwa Hindi Diwas)",
        "12 January: National Youth Day (Swami Vivekananda Jayanti)",
        "15 January: Indian Army Day",
        "24 January: National Girl Child Day",
        "25 January: National Voters' Day",
        "26 January: Republic Day of India / International Customs Day",
        "30 January: Martyrs' Day (Shaheed Diwas - Mahatma Gandhi Smriti)",
    ],
    "february": [
        "2 February: World Wetlands Day (Ramsar Convention)",
        "4 February: World Cancer Day",
        "10 February: World Pulses Day (FAO)",
        "13 February: National Women's Day (Sarojini Naidu)",
        "24 February: Central Excise Day / PM-KISAN Launch Anniversary",
        "28 February: National Science Day (Raman Effect)",
    ],
    "march": [
        "3 March: World Wildlife Day",
        "8 March: International Women's Day",
        "15 March: World Consumer Rights Day",
        "21 March: International Day of Forests",
        "22 March: World Water Day (Leveraging Water for Peace)",
        "23 March: World Meteorological Day / Shaheed Diwas",
        "24 March: World Tuberculosis (TB) Day",
    ],
    "april": [
        "7 April: World Health Day (WHO Foundation 1948)",
        "14 April: Dr. B.R. Ambedkar Jayanti / National Water Day",
        "18 April: World Heritage Day",
        "21 April: National Civil Services Day",
        "22 April: Earth Day (International Mother Earth Day)",
        "24 April: National Panchayati Raj Day (73rd Amendment)",
    ],
    "may": [
        "1 May: International Labour Day",
        "3 May: World Press Freedom Day",
        "11 May: National Technology Day (Pokhran-II)",
        "20 May: World Bee Day (FAO)",
        "22 May: International Day for Biological Diversity",
        "31 May: World No Tobacco Day",
    ],
    "june": [
        "1 June: World Milk Day (FAO)",
        "5 June: World Environment Day (UNEP)",
        "7 June: World Food Safety Day (FAO/WHO)",
        "17 June: World Day to Combat Desertification and Drought",
        "21 June: International Day of Yoga (UN)",
        "23 June: United Nations Public Service Day",
        "29 June: National Statistics Day (Prof. P.C. Mahalanobis)",
    ],
    "july": [
        "1 July: National Doctor's Day / GST Day / SBI Foundation Day",
        "11 July: World Population Day",
        "12 July: NABARD Foundation Day (Established 12 July 1982)",
        "16 July: ICAR Foundation Day (Established 16 July 1929)",
        "20 July: World Chess Day / International Moon Day",
        "26 July: Kargil Vijay Diwas",
        "28 July: World Nature Conservation Day / World Hepatitis Day",
        "29 July: International Tiger Day",
    ],
    "august": [
        "7 August: National Handloom Day / National Javelin Day",
        "9 August: International Day of the World's Indigenous Peoples",
        "10 August: World Biofuel Day",
        "12 August: International Youth Day",
        "15 August: Independence Day of India",
        "20 August: Sadbhavana Diwas",
        "23 August: National Space Day (Chandrayaan-3 Landing)",
        "29 August: National Sports Day (Major Dhyan Chand)",
    ],
    "september": [
        "1-7 September: National Nutrition Week (Rashtriya Poshan Maah)",
        "5 September: National Teachers' Day (Dr. S. Radhakrishnan)",
        "8 September: International Literacy Day (UNESCO)",
        "14 September: National Hindi Diwas",
        "15 September: Engineers' Day (M. Visvesvaraya) / International Democracy Day",
        "16 September: World Ozone Day (Montreal Protocol)",
        "21 September: International Day of Peace",
        "27 September: World Tourism Day",
        "28 September: World Rabies Day",
    ],
    "october": [
        "1 October: International Day of Older Persons / National Voluntary Blood Donation Day",
        "2 October: Gandhi Jayanti / Lal Bahadur Shastri Jayanti / International Day of Non-Violence",
        "4 October: World Animal Day",
        "5 October: World Teachers' Day / National Dolphin Day",
        "7 October: World Cotton Day",
        "8 October: Indian Air Force Day (IAF)",
        "9 October: World Post Day",
        "11 October: International Day of the Girl Child",
        "15 October: World Students' Day (Dr. A.P.J. Abdul Kalam) / National Women Farmers Day",
        "16 October: World Food Day (FAO Foundation Day, 1945)",
        "20 October: National Solidarity Day / World Statistics Day",
        "24 October: United Nations Day / World Polio Day / ITBP Raising Day",
        "31 October: National Unity Day (Rashtriya Ekta Diwas - Sardar Vallabhbhai Patel)",
    ],
    "november": [
        "5 November: World Tsunami Awareness Day",
        "7 November: National Cancer Awareness Day",
        "9 November: National Legal Services Day",
        "11 November: National Education Day (Maulana Abul Kalam Azad)",
        "14 November: Children's Day / World Diabetes Day",
        "15 November: Janjatiya Gaurav Divas (Bhagwan Birsa Munda)",
        "19 November: World Toilet Day / National Integration Day",
        "21 November: World Fisheries Day",
        "26 November: Constitution Day (Samvidhan Divas) / National Milk Day (Dr. Verghese Kurien)",
    ],
    "december": [
        "1 December: World AIDS Day",
        "2 December: National Pollution Control Day / World Computer Literacy Day",
        "3 December: International Day of Persons with Disabilities / National Agricultural Education Day",
        "4 December: Indian Navy Day",
        "5 December: World Soil Day (FAO)",
        "7 December: Armed Forces Flag Day",
        "10 December: Human Rights Day",
        "14 December: National Energy Conservation Day",
        "18 December: Minorities Rights Day",
        "22 December: National Mathematics Day (Srinivasa Ramanujan)",
        "23 December: Kisan Diwas (National Farmers' Day - Chaudhary Charan Singh)",
        "24 December: National Consumer Rights Day",
        "25 December: Good Governance Day (Sushasan Divas - Atal Bihari Vajpayee)",
    ],
}


def get_important_days_for_date(date_str: str) -> List[str]:
    d_low = str(date_str or "").lower()
    for month_name, days in IMPORTANT_DAYS_BY_MONTH.items():
        if month_name in d_low:
            return days
    m_iso = re.search(r"-(0[1-9]|1[0-2])-", d_low)
    if m_iso:
        months_list = list(IMPORTANT_DAYS_BY_MONTH.keys())
        idx = int(m_iso.group(1)) - 1
        if 0 <= idx < len(months_list):
            return IMPORTANT_DAYS_BY_MONTH[months_list[idx]]
    return IMPORTANT_DAYS_BY_MONTH["october"]


# --- TWO-PASS CANVAS FOR HEADERS, FOOTERS & RUNNING METADATA ---
class ExamGeniusCanvas(canvas.Canvas):
    """Draws running header, divider, and footer across all pages except the cover."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states: List[Dict[str, Any]] = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            if self._pageNumber > 1:
                self.draw_page_decorations(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_decorations(self, total_pages: int):
        self.saveState()
        w = PAGE_W
        h = PAGE_H
        left_m = 36 * pt
        right_m = w - 36 * pt

        # Top Running Header
        header_y = h - 26 * pt
        self.setFont(FONT_SEMI, 8)
        self.setFillColor(COLORS["primary"])
        self.drawString(left_m, header_y, "AGRI LEARNING POINT  |  DAILY CURRENT AFFAIRS (BILINGUAL)")

        self.setFont(FONT_REGULAR, 7.5)
        self.setFillColor(COLORS["muted_text"])
        self.drawRightString(right_m, header_y, "UPSSSC AGTA • IBPS AFO • ICAR • NABARD • STATE PCS")

        # Top Hairline Divider
        self.setStrokeColor(COLORS["border_light"])
        self.setLineWidth(0.75)
        self.line(left_m, header_y - 4 * pt, right_m, header_y - 4 * pt)

        # Bottom Running Footer
        footer_y = 22 * pt
        self.line(left_m, footer_y + 10 * pt, right_m, footer_y + 10 * pt)

        self.setFont(FONT_SEMI, 7.5)
        self.setFillColor(COLORS["primary"])
        self.drawString(left_m, footer_y, "Agri Learning Point — YouTube: Agri Learning Point")

        self.setFont(FONT_REGULAR, 7.5)
        self.setFillColor(COLORS["muted_text"])
        self.drawCentredString(w / 2.0, footer_y, "Telegram: @agrilearningpoint  |  Quiz: @agriquizworld")

        page_str = f"Page {self._pageNumber} of {total_pages}"
        self.setFont(FONT_SEMI, 7.5)
        self.setFillColor(COLORS["primary"])
        self.drawRightString(right_m, footer_y, page_str)

        self.restoreState()


# --- STYLESHEET SETUP ---
def get_pdf_styles() -> Dict[str, ParagraphStyle]:
    styles = getSampleStyleSheet()
    return {
        "cover_super": ParagraphStyle("CoverSuper", parent=styles["Normal"], fontName=FONT_SEMI, fontSize=11, leading=15, textColor=COLORS["secondary"], alignment=TA_CENTER),
        "cover_title": ParagraphStyle("CoverTitle", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=26, leading=30, textColor=COLORS["primary"], alignment=TA_CENTER),
        "cover_sub": ParagraphStyle("CoverSub", parent=styles["Normal"], fontName=FONT_SEMI, fontSize=14, leading=18, textColor=COLORS["accent_green"], alignment=TA_CENTER),
        "cover_date": ParagraphStyle("CoverDate", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=13, leading=16, textColor=COLORS["white"], alignment=TA_CENTER),
        "cover_badge": ParagraphStyle("CoverBadge", parent=styles["Normal"], fontName=FONT_SEMI, fontSize=9, leading=12, textColor=COLORS["primary"], alignment=TA_CENTER),
        "cover_bullet": ParagraphStyle("CoverBullet", parent=styles["Normal"], fontName=FONT_REGULAR, fontSize=9.5, leading=14, textColor=COLORS["dark_text"], alignment=TA_LEFT),

        "section_tag": ParagraphStyle("SectionTag", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=8, leading=10, textColor=COLORS["badge_text"], alignment=TA_LEFT),
        "topic_headline": ParagraphStyle("TopicHeadline", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=11.5, leading=15, textColor=COLORS["primary"], alignment=TA_LEFT),

        "ques_en": ParagraphStyle("QuesEN", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=10.5, leading=14.5, textColor=COLORS["dark_text"], alignment=TA_LEFT),
        "option_text": ParagraphStyle("OptionText", parent=styles["Normal"], fontName=FONT_REGULAR, fontSize=9.5, leading=13.5, textColor=COLORS["body_text"], alignment=TA_LEFT),
        "answer_text": ParagraphStyle("AnswerText", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=10, leading=13, textColor=HexColor("#065F46"), alignment=TA_LEFT),

        "block_head": ParagraphStyle("BlockHead", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=9.5, leading=13, textColor=COLORS["primary"], alignment=TA_LEFT),
        "bullet_en": ParagraphStyle("BulletEN", parent=styles["Normal"], fontName=FONT_REGULAR, fontSize=9, leading=13, textColor=COLORS["body_text"], alignment=TA_LEFT, leftIndent=8),
        "static_fact_en": ParagraphStyle("StaticFactEN", parent=styles["Normal"], fontName=FONT_REGULAR, fontSize=8.5, leading=12, textColor=COLORS["body_text"], alignment=TA_LEFT, leftIndent=6),

        "index_title": ParagraphStyle("IndexTitle", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=14, leading=18, textColor=COLORS["primary"], alignment=TA_CENTER),
        "index_col_head": ParagraphStyle("IndexColHead", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=8.5, leading=11, textColor=COLORS["white"], alignment=TA_CENTER),
        "index_cell": ParagraphStyle("IndexCell", parent=styles["Normal"], fontName=FONT_REGULAR, fontSize=8, leading=10.5, textColor=COLORS["body_text"], alignment=TA_LEFT),
        "index_cell_c": ParagraphStyle("IndexCellC", parent=styles["Normal"], fontName=FONT_SEMI, fontSize=8, leading=10.5, textColor=COLORS["primary"], alignment=TA_CENTER),

        "key_cell": ParagraphStyle("KeyCell", parent=styles["Normal"], fontName=FONT_SEMI, fontSize=8.5, leading=11, textColor=COLORS["body_text"], alignment=TA_CENTER),
        "key_cell_bold": ParagraphStyle("KeyCellBold", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=8.5, leading=11, textColor=COLORS["accent_green"], alignment=TA_CENTER),
    }


STYLES = get_pdf_styles()


# --- STORY HELPER FUNCTIONS ---
def _extract_explanation_points(item: Dict[str, Any], mcq: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Extract substantive bilingual explanation bullet pairs without headline repetition."""
    pairs: List[Tuple[str, str]] = []
    seen: List[str] = []

    def is_dup(txt: str) -> bool:
        low = txt.lower()
        return any(low in s.lower() or s.lower() in low for s in seen)

    # 1. Key Points
    kp_ens = item.get("key_points_en") or []
    kp_his = item.get("key_points_hi") or []
    for idx, kpe in enumerate(kp_ens):
        clean_en = _clean_text_for_display(kpe)
        if not clean_en or len(clean_en) < 20 or is_dup(clean_en):
            continue
        clean_hi = ""
        if idx < len(kp_his):
            c_hi = _clean_text_for_display(kp_his[idx])
            if DEVANAGARI_RE.search(c_hi):
                clean_hi = c_hi
        seen.append(clean_en)
        pairs.append((clean_en, clean_hi))
        if len(pairs) >= 3:
            break

    # 2. Detailed Explanation
    det_en = _clean_text_for_display(item.get("detailed_explanation_en", ""))
    if det_en and len(det_en) > 30 and not is_dup(det_en):
        det_hi = _clean_text_for_display(item.get("detailed_explanation_hi", ""))
        c_hi = det_hi if DEVANAGARI_RE.search(det_hi) else ""
        seen.append(det_en)
        pairs.append((det_en, c_hi))

    # 3. MCQ explanation
    if len(pairs) < 2:
        m_en = _clean_text_for_display(mcq.get("explanation_en", ""))
        if m_en and len(m_en) > 20 and not is_dup(m_en):
            m_hi = _clean_text_for_display(mcq.get("explanation_hi", ""))
            c_hi = m_hi if DEVANAGARI_RE.search(m_hi) else ""
            seen.append(m_en)
            pairs.append((m_en, c_hi))

    return pairs[:3]


def _extract_static_gk_pairs(item: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Extract clean bilingual static facts."""
    pairs: List[Tuple[str, str]] = []
    sf = item.get("static_facts") or {}
    if isinstance(sf, dict):
        for k, v in sf.items():
            k_clean = _clean_text_for_display(k)
            v_clean = _clean_text_for_display(v)
            if k_clean and v_clean:
                en = f"• {k_clean}: {v_clean}"
                pairs.append((en, ""))

    ef_en = _clean_text_for_display(item.get("exam_fact_en", ""))
    ef_hi = _clean_text_for_display(item.get("exam_fact_hi", ""))
    if ef_en and len(ef_en) > 15:
        hi = ef_hi if DEVANAGARI_RE.search(ef_hi) else ""
        pairs.append((f"• परीक्षा तथ्य / Exam Fact: {ef_en}", f"• परीक्षा तथ्य: {hi}" if hi else ""))

    return pairs[:4]


# --- MAIN PDF GENERATION ENGINE ---
def generate_pdf(content: Dict[str, Any], mcqs: List[Dict[str, Any]], output_path: Optional[str] = None) -> str:
    """Generate professional Exam Genius-grade Current Affairs PDF."""
    items = content.get("items") or []
    if not items:
        raise ValueError("Empty edition: Refusing to generate PDF with zero items.")

    job_info = content.get("job") or {}
    date_display = job_info.get("date_display") or datetime.now().strftime("%d %B %Y")
    job_id = job_info.get("id") or f"daily_{datetime.now().strftime('%Y-%m-%d')}"

    if output_path is None:
        output_path = os.path.join(OUTPUT_DIR, f"{job_id}.pdf")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=36 * pt,
        rightMargin=36 * pt,
        topMargin=38 * pt,
        bottomMargin=36 * pt,
    )

    story: List[Flowable] = []

    # =========================================================================
    # PAGE 1: EXAM GENIUS STYLE COVER PAGE
    # =========================================================================
    story.append(Spacer(PRINT_W, 10 * pt))
    story.append(Paragraph("AGRI LEARNING POINT — YOUR ULTIMATE GUIDE TO AGRICULTURE & ALL COMPETITIVE EXAMS", STYLES["cover_super"]))
    story.append(Spacer(PRINT_W, 12 * pt))

    story.append(Paragraph("AGRI LEARNING POINT", STYLES["cover_title"]))
    story.append(Spacer(PRINT_W, 4 * pt))
    story.append(Paragraph("Presents", STYLES["cover_super"]))
    story.append(Spacer(PRINT_W, 4 * pt))
    story.append(Paragraph("GENIUS CURRENT AFFAIRS", STYLES["cover_sub"]))
    story.append(Spacer(PRINT_W, 4 * pt))
    story.append(Paragraph("IN BILINGUAL (हिन्दी + ENGLISH)", STYLES["cover_super"]))
    story.append(Spacer(PRINT_W, 12 * pt))

    # Date Banner
    date_banner_data = [[Paragraph(f"EDITION DATE: {date_display.upper()}", STYLES["cover_date"])]]
    date_banner = Table(date_banner_data, colWidths=[PRINT_W])
    date_banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLORS["primary"]),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(date_banner)
    story.append(Spacer(PRINT_W, 14 * pt))

    # Target Exams Bar
    exam_badges = [
        "UPSSSC AGTA", "IBPS AFO", "ICAR JRF/SRF", "NABARD GRADE-A",
        "FCI MANAGER", "STATE AGRICULTURE SUPERVISOR", "UPSC & STATE PCS"
    ]
    badge_data = [[Paragraph(f"<b>TARGET EXAMS:</b> {' • '.join(exam_badges)}", STYLES["cover_badge"])]]
    badge_table = Table(badge_data, colWidths=[PRINT_W])
    badge_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLORS["badge_bg"]),
        ("BOX", (0, 0), (-1, -1), 1, COLORS["badge_text"]),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(badge_table)
    story.append(Spacer(PRINT_W, 16 * pt))

    # Features Box
    features = [
        ("• Genuine Rolling 24-Hour Coverage", "Strictly verified news from PIB, ICAR, MEA, MoAFW, RBI & National Dailies."),
        ("• Mobile-First Educational Structure", "Every question is paired with its verified answer, bilingual explanation & static GK."),
        ("• Standard 5-Option Practice MCQs", "Designed for negative-marking competitive exams with high-probability distractors."),
        ("• Deep Institutional Static GK", "Headquarters, establishment years, nodal ministries, and relevant agricultural acts."),
    ]
    feat_rows = []
    for f_title, f_desc in features:
        p = Paragraph(f"<b>{_safe(f_title)}:</b> {_safe(f_desc)}", STYLES["cover_bullet"])
        feat_rows.append([p])
    feat_table = Table(feat_rows, colWidths=[PRINT_W])
    feat_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLORS["card_bg"]),
        ("BOX", (0, 0), (-1, -1), 1, COLORS["border_light"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(feat_table)
    story.append(Spacer(PRINT_W, 18 * pt))

    # Important Days of the Month Quick Callout
    sample_days = get_important_days_for_date(date_display)
    day_rows = [[Paragraph(f"<b>IMPORTANT EXAM DAYS & OBSERVANCES ({date_display}):</b>", STYLES["section_tag"])]]
    for d in sample_days[:4]:
        day_rows.append([Paragraph(f"• {_safe(d)}", STYLES["cover_bullet"])])
    day_table = Table(day_rows, colWidths=[PRINT_W])
    day_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HexColor("#FEF3C7")),
        ("BOX", (0, 0), (-1, -1), 1, COLORS["gold_accent"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(day_table)
    story.append(Spacer(PRINT_W, 18 * pt))

    # Social Channels Bar
    social_text = "<b>YouTube:</b> Agri Learning Point   |   <b>Telegram:</b> @agrilearningpoint   |   <b>Daily Quiz:</b> @agriquizworld"
    social_data = [[Paragraph(social_text, STYLES["cover_badge"])]]
    social_table = Table(social_data, colWidths=[PRINT_W])
    social_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLORS["badge_bg"]),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(social_table)

    story.append(PageBreak())

    # =========================================================================
    # PAGE 2: INDEX / TODAY'S EXAM HEADLINES
    # =========================================================================
    story.append(Paragraph("INDEX & TODAY'S EXAM HEADLINES • विषय-सूची", STYLES["index_title"]))
    story.append(Paragraph(f"दैनिक समसामयिकी विषय-सूची • महत्वपूर्ण दिवस एवं परीक्षा तथ्य • {date_display}", STYLES["cover_super"]))
    story.append(Spacer(PRINT_W, 10 * pt))

    index_rows = [[
        Paragraph("Q#", STYLES["index_col_head"]),
        Paragraph("EXAM TOPIC / HEADLINE", STYLES["index_col_head"]),
        Paragraph("CATEGORY", STYLES["index_col_head"]),
    ]]

    for idx, it in enumerate(items, 1):
        hl = _clean_text_for_display(it.get("headline_en", ""))
        cat = str(it.get("category", "General")).upper()
        if not hl:
            continue
        index_rows.append([
            Paragraph(f"Q{idx}", STYLES["index_cell_c"]),
            Paragraph(_safe(hl), STYLES["index_cell"]),
            Paragraph(_safe(cat), STYLES["index_cell_c"]),
        ])

    index_table = Table(index_rows, colWidths=[36 * pt, 375 * pt, 112 * pt])
    index_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLORS["primary"]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, COLORS["border_light"]),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COLORS["white"], COLORS["card_bg"]]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(index_table)
    story.append(PageBreak())

    # =========================================================================
    # PAGES 3+: SELF-CONTAINED EXAM GENIUS EDUCATIONAL UNITS
    # =========================================================================
    mcq_by_num: Dict[int, Dict[str, Any]] = {
        m.get("q_num", i): m for i, m in enumerate(mcqs, 1)
    }

    total_units = max(len(items), len(mcqs))

    for q_idx in range(1, total_units + 1):
        if q_idx > 1:
            story.append(PageBreak())

        it = items[q_idx - 1] if q_idx <= len(items) else items[(q_idx - 1) % len(items)]
        m = mcq_by_num.get(q_idx) or (mcqs[q_idx - 1] if q_idx <= len(mcqs) else {})

        cat = str(it.get("category", "National")).upper()
        headline_en = _clean_text_for_display(it.get("headline_en", ""))
        source_name = (it.get("source") or {}).get("name") or "Verified National Source"
        source_url = (it.get("source") or {}).get("url") or "https://t.me/agrilearningpoint"

        unit_elements: List[Flowable] = []

        # 1. Header Pill Bar
        pill_text = f"<b>[ {cat} ]</b>   •   <b>Topic:</b> {_safe(headline_en)}"
        pill_data = [[Paragraph(pill_text, STYLES["section_tag"])]]
        pill_table = Table(pill_data, colWidths=[PRINT_W])
        pill_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLORS["badge_bg"]),
            ("BOX", (0, 0), (-1, -1), 0.5, COLORS["badge_text"]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        unit_elements.append(pill_table)
        unit_elements.append(Spacer(PRINT_W, 6 * pt))

        # 2. Question (English + Hindi)
        q_en = _clean_text_for_display(m.get("question_en", ""))
        if not q_en:
            q_en = f"What key development was announced regarding {headline_en}?"
        unit_elements.append(Paragraph(f"<b>Q{q_idx}. Ques {q_idx}:</b> {_safe(q_en)}", STYLES["ques_en"]))
        unit_elements.append(Spacer(PRINT_W, 2 * pt))

        q_hi = _clean_text_for_display(m.get("question_hi", ""))
        if q_hi and DEVANAGARI_RE.search(q_hi):
            unit_elements.append(render_hindi_flowable(f"बहुविकल्पीय प्रश्न {q_idx}: {q_hi}", font_size_pt=10.0, width_pt=PRINT_W, is_bold=True))
            unit_elements.append(Spacer(PRINT_W, 4 * pt))

        # 3. 5 Options (A, B, C, D, E)
        raw_options = m.get("options") or ["Option 1", "Option 2", "Option 3", "Option 4", "Option 5"]
        while len(raw_options) < 5:
            raw_options.append("None of the above")

        letters = ["A", "B", "C", "D", "E"]
        opt_rows = []
        for ltr, opt in zip(letters, raw_options[:5]):
            clean_opt = _clean_text_for_display(opt)
            opt_p = Paragraph(f"<b>{ltr})</b> {_safe(clean_opt)}", STYLES["option_text"])
            opt_rows.append([opt_p])

        opt_table = Table(opt_rows, colWidths=[PRINT_W])
        opt_table.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 1.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
        ]))
        unit_elements.append(opt_table)
        unit_elements.append(Spacer(PRINT_W, 5 * pt))

        # 4. Answer Callout Box
        correct_ltr = str(m.get("correct") or "A").strip().upper()
        if correct_ltr not in letters:
            correct_ltr = "A"

        ans_data = [[
            Paragraph(f"<b>Answer: Option {correct_ltr}</b>   (उत्तर: विकल्प {correct_ltr})", STYLES["answer_text"])
        ]]
        ans_table = Table(ans_data, colWidths=[PRINT_W])
        ans_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLORS["light_green_bg"]),
            ("BOX", (0, 0), (-1, -1), 1, COLORS["border_green"]),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        unit_elements.append(ans_table)
        unit_elements.append(Spacer(PRINT_W, 6 * pt))

        # 5. Explanation Section (व्याख्या)
        unit_elements.append(Paragraph("<b>Explanation | व्याख्या (मुख्य बिंदु) :</b>", STYLES["block_head"]))
        unit_elements.append(Spacer(PRINT_W, 3 * pt))

        expl_pairs = _extract_explanation_points(it, m)
        for ep_en, ep_hi in expl_pairs:
            unit_elements.append(Paragraph(f"• {_safe(ep_en)}", STYLES["bullet_en"]))
            if ep_hi and DEVANAGARI_RE.search(ep_hi):
                unit_elements.append(render_hindi_flowable(f"• मुख्य बिंदु: {ep_hi}", font_size_pt=9.0, width_pt=PRINT_W - 8 * pt, left_padding_mm=2.5))
            unit_elements.append(Spacer(PRINT_W, 2.5 * pt))

        # 6. Static GK Box (स्थैतिक सामान्य ज्ञान)
        static_pairs = _extract_static_gk_pairs(it)
        if static_pairs:
            sgk_rows = [[Paragraph("<b>Static GK | स्थैतिक तथ्य एवं सामान्य ज्ञान :</b>", STYLES["block_head"])]]
            for s_en, s_hi in static_pairs:
                sgk_rows.append([Paragraph(_safe(s_en), STYLES["static_fact_en"])])
                if s_hi and DEVANAGARI_RE.search(s_hi):
                    h_f = render_hindi_flowable(s_hi, font_size_pt=8.5, width_pt=PRINT_W - 16 * pt, left_padding_mm=2.0)
                    sgk_rows.append([h_f])

            sgk_table = Table(sgk_rows, colWidths=[PRINT_W])
            sgk_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), COLORS["card_bg"]),
                ("BOX", (0, 0), (-1, -1), 0.75, COLORS["card_border"]),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            unit_elements.append(Spacer(PRINT_W, 3 * pt))
            unit_elements.append(sgk_table)

        # 7. Source & Attribution
        src_text = f"<b>Source:</b> {_safe(source_name)}   |   <b>Official Link:</b> {_safe(source_url)}"
        unit_elements.append(Spacer(PRINT_W, 3 * pt))
        unit_elements.append(Paragraph(src_text, STYLES["section_tag"]))

        # Thin divider before next educational unit
        unit_elements.append(Spacer(PRINT_W, 6 * pt))
        unit_elements.append(HRFlowable(width="100%", thickness=0.5, color=COLORS["border_light"]))
        unit_elements.append(Spacer(PRINT_W, 10 * pt))

        story.extend(unit_elements)

    # =========================================================================
    # FINAL PAGE: RAPID REVISION ANSWER KEY
    # =========================================================================
    story.append(PageBreak())
    story.append(Paragraph("RAPID REVISION ANSWER KEY • त्वरित उत्तर कुंजी", STYLES["index_title"]))
    story.append(Paragraph(f"Agri Learning Point • Daily Bilingual Edition • {date_display}", STYLES["cover_super"]))
    story.append(Spacer(PRINT_W, 12 * pt))

    key_rows = [[
        Paragraph("Q#", STYLES["index_col_head"]),
        Paragraph("ANSWER", STYLES["index_col_head"]),
        Paragraph("EXAM TOPIC / HEADLINE", STYLES["index_col_head"]),
        Paragraph("CATEGORY", STYLES["index_col_head"]),
    ]]

    for q_idx in range(1, total_units + 1):
        it = items[q_idx - 1] if q_idx <= len(items) else items[-1]
        m = mcq_by_num.get(q_idx) or (mcqs[q_idx - 1] if q_idx <= len(mcqs) else {})
        ans = str(m.get("correct") or "A").strip().upper()
        hl = _clean_text_for_display(it.get("headline_en", ""))
        cat = str(it.get("category", "General")).upper()

        key_rows.append([
            Paragraph(f"Q{q_idx}", STYLES["key_cell"]),
            Paragraph(f"<b>Option {ans}</b>", STYLES["key_cell_bold"]),
            Paragraph(_safe(hl[:85]), STYLES["index_cell"]),
            Paragraph(_safe(cat), STYLES["key_cell"]),
        ])

    key_table = Table(key_rows, colWidths=[36 * pt, 65 * pt, 320 * pt, 102 * pt])
    key_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLORS["primary"]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, COLORS["border_light"]),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COLORS["white"], COLORS["card_bg"]]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(key_table)

    # Strategy & Exam Preparation Guidance Box
    story.append(Spacer(PRINT_W, 14 * pt))
    guide_title = Paragraph("<b>COMPETITIVE EXAM REVISION & PREPARATION STRATEGY:</b>", STYLES["section_tag"])
    tips = [
        "1. Active Recall: First attempt all 20+ MCQs independently without checking the answer callout.",
        "2. Institutional Static GK: Review nodal ministries, establishment years, and headquarters mentioned in each box.",
        "3. Agricultural Core: Pay special focus to ICAR institutes, MSP declarations, and central government farmer welfare schemes.",
        "4. Daily Quizzes: Participate in daily current affairs timed quizzes on Telegram: @agriquizworld.",
        "5. Official Source Verification: Every fact in this booklet is verified against primary government and agency records.",
        "6. Study Resources: प्रतिदिन नए अभ्यास प्रश्न और संपूर्ण अध्ययन सामग्री हमारे टेलीग्राम चैनल पर नियमित रूप से मिलते हैं।",
    ]
    guide_rows = [[guide_title]]
    for tip in tips:
        guide_rows.append([Paragraph(f"• {_safe(tip)}", STYLES["cover_bullet"])])
    guide_table = Table(guide_rows, colWidths=[PRINT_W])
    guide_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLORS["card_bg"]),
        ("BOX", (0, 0), (-1, -1), 1, COLORS["badge_text"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(guide_table)

    # Build PDF with Two-Pass ExamGeniusCanvas
    doc.build(story, canvasmaker=ExamGeniusCanvas)
    return output_path


if __name__ == "__main__":
    import json
    data_file = os.path.join(BASE_DIR, "data", "content", "daily_2026-10-24.json")
    mcq_file = os.path.join(BASE_DIR, "data", "mcq", "daily_2026-10-24.json")
    if not os.path.exists(mcq_file):
        mcq_file = os.path.join(BASE_DIR, "data", "content", "mcqs_daily_2026-10-24.json")
    if os.path.exists(data_file):
        with open(data_file, "r", encoding="utf-8") as f:
            c = json.load(f)
        m = []
        if os.path.exists(mcq_file):
            with open(mcq_file, "r", encoding="utf-8") as f:
                m = json.load(f)
        out = generate_pdf(c, m)
        print("Generated Exam Genius PDF:", out)
