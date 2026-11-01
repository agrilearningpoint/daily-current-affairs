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
CURRENT_COVER_DATE = ""


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

    # Mukta's hhea ascender/descender span ~1.7 em, which made every Hindi line
    # about twice as tall as its English partner.  Use em-based metrics instead:
    # upper matras/reph reach ~1.0 em above the baseline, lower matras ~0.4 em below.
    em_px = font_size_pt * dpi / 72.0
    ascender = int(round(em_px * 1.05))
    line_h = int(round(em_px * max(line_spacing, 1.0) * 1.12))
    total_h = line_h * (len(lines) - 1) + ascender + int(round(em_px * 0.45)) + int(2 * dpi / 72)

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
            if self._pageNumber == 1:
                self.draw_cover_decorations()
            else:
                self.draw_page_decorations(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_cover_decorations(self):
        """Draw the full-bleed branded cover used by the supplied reference."""
        self.saveState()
        w, h = PAGE_W, PAGE_H
        self.setFillColor(HexColor("#E7F4FC"))
        self.rect(0, 0, w, h, stroke=0, fill=1)
        self.setFillColor(HexColor("#74BDF0"))
        p = self.beginPath()
        p.moveTo(0, h); p.lineTo(w, h); p.lineTo(w, h * .54)
        p.curveTo(w * .70, h * .49, w * .27, h * .49, 0, h * .82); p.close()
        self.drawPath(p, stroke=0, fill=1)
        self.setFillColor(HexColor("#083B82"))
        p = self.beginPath()
        p.moveTo(0, 0); p.lineTo(w, 0); p.lineTo(w, h * .54)
        p.curveTo(w * .69, h * .48, w * .32, h * .39, 0, h * .22); p.close()
        self.drawPath(p, stroke=0, fill=1)
        self.setFillColor(HexColor("#103F7B")); self.setFont(FONT_BOLD, 22)
        self.drawCentredString(w / 2, h - 68, "AGRI LEARNING POINT")
        self.setFont(FONT_SEMI, 14); self.drawCentredString(w / 2, h - 98, "Presents")
        self.setFillColor(HexColor("#0953A2")); self.setFont(FONT_BOLD, 31)
        for y, line in ((h - 154, "AGRI"), (h - 198, "CURRENT"), (h - 242, "AFFAIRS")):
            self.drawCentredString(w / 2, y, line)
        self.setFillColor(HexColor("#E51D3E")); self.setFont(FONT_BOLD, 18)
        self.drawCentredString(w / 2, h - 282, "In Bilingual")
        self.setFillColor(HexColor("#103F7B")); self.setFont(FONT_BOLD, 14)
        self.drawCentredString(w / 2, h - 310, CURRENT_COVER_DATE)
        logo = os.path.join(BASE_DIR, "assets", "logo.png")
        if os.path.isfile(logo):
            try:
                self.setFillColor(COLORS["white"]); self.circle(w / 2, h * .43, 68, stroke=0, fill=1)
                self.drawImage(logo, w / 2 - 54, h * .43 - 54, 108, 108,
                               preserveAspectRatio=True, mask="auto")
            except Exception:
                pass
        badges = ("UPSC / PCS", "IBPS AFO", "NABARD", "ICAR / JRF", "STATE AGRI")
        x = 27
        for label in badges:
            self.setFillColor(HexColor("#D5ECFF")); self.roundRect(x, 135, 102, 26, 13, stroke=0, fill=1)
            self.setStrokeColor(COLORS["white"]); self.setLineWidth(1.5)
            self.roundRect(x, 135, 102, 26, 13, stroke=1, fill=0)
            self.setFillColor(HexColor("#103F7B")); self.setFont(FONT_SEMI, 7.6)
            self.drawCentredString(x + 51, 145, label); x += 108
        self.setFillColor(HexColor("#1262B9")); self.rect(0, 0, w, 30, stroke=0, fill=1)
        self.setFillColor(COLORS["white"]); self.setFont(FONT_SEMI, 9)
        self.drawCentredString(w / 2, 11, "Achieve Success with Agri Learning Point - Your Ultimate Guide to Agriculture & Govt. Exams")
        self.restoreState()

    def draw_page_decorations(self, total_pages: int):
        self.saveState()
        w = PAGE_W
        h = PAGE_H
        left_m = 36 * pt
        right_m = w - 36 * pt

        # Reference-style blue running header.
        self.setFillColor(HexColor("#65B4EB"))
        self.rect(0, h - 50 * pt, w, 50 * pt, stroke=0, fill=1)
        self.setStrokeColor(HexColor("#103F7B"))
        self.setLineWidth(1.25)
        self.line(0, h - 43 * pt, w, h - 43 * pt)
        header_y = h - 28 * pt
        self.setFont(FONT_SEMI, 8)
        self.setFillColor(HexColor("#103F7B"))
        self.drawString(left_m, header_y, "AGRI LEARNING POINT  |  DAILY CURRENT AFFAIRS (BILINGUAL)")

        self.setFont(FONT_REGULAR, 7.5)
        self.setFillColor(HexColor("#103F7B"))
        self.drawRightString(right_m, header_y, "UPSSSC AGTA • IBPS AFO • ICAR • NABARD • STATE PCS")

        # Top hairline divider.
        self.setStrokeColor(HexColor("#B6DDF7"))
        self.setLineWidth(0.75)
        self.line(left_m, header_y - 4 * pt, right_m, header_y - 4 * pt)

        # Discreet watermark plus the reference's black social footer.
        watermark = os.path.join(BASE_DIR, "assets", "watermark_logo.png")
        if os.path.isfile(watermark):
            try:
                self.setFillAlpha(0.08)
                self.drawImage(watermark, w / 2 - 105, h / 2 - 105, 210, 210,
                               preserveAspectRatio=True, mask="auto")
                self.setFillAlpha(1)
            except Exception:
                pass

        footer_y = 12 * pt
        self.setFillColor(HexColor("#111111"))
        self.rect(0, 0, w, 31 * pt, stroke=0, fill=1)

        self.setFont(FONT_SEMI, 7.5)
        self.setFillColor(COLORS["white"])
        self.drawString(left_m, footer_y, "YouTube: @agrilearningpoint")

        self.setFont(FONT_REGULAR, 7.5)
        self.setFillColor(COLORS["white"])
        self.drawCentredString(w / 2.0, footer_y, "Telegram: @agrilearningpoint")

        page_str = f"Page {self._pageNumber} of {total_pages}"
        self.setFont(FONT_SEMI, 7.5)
        self.setFillColor(COLORS["white"])
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

        "ques_en": ParagraphStyle("QuesEN", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=12, leading=16.5, textColor=COLORS["dark_text"], alignment=TA_LEFT),
        "option_text": ParagraphStyle("OptionText", parent=styles["Normal"], fontName=FONT_REGULAR, fontSize=10.5, leading=15, textColor=COLORS["body_text"], alignment=TA_LEFT),
        "answer_text": ParagraphStyle("AnswerText", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=11, leading=14, textColor=HexColor("#065F46"), alignment=TA_LEFT),

        "block_head": ParagraphStyle("BlockHead", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=11, leading=15, textColor=COLORS["primary"], alignment=TA_LEFT),
        "bullet_en": ParagraphStyle("BulletEN", parent=styles["Normal"], fontName=FONT_REGULAR, fontSize=10.5, leading=15, textColor=COLORS["body_text"], alignment=TA_LEFT),
        "static_fact_en": ParagraphStyle("StaticFactEN", parent=styles["Normal"], fontName=FONT_REGULAR, fontSize=10, leading=14, textColor=COLORS["body_text"], alignment=TA_LEFT, leftIndent=6),

        "index_title": ParagraphStyle("IndexTitle", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=14, leading=18, textColor=COLORS["primary"], alignment=TA_CENTER),
        "index_col_head": ParagraphStyle("IndexColHead", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=8.5, leading=11, textColor=COLORS["white"], alignment=TA_CENTER),
        "index_cell": ParagraphStyle("IndexCell", parent=styles["Normal"], fontName=FONT_REGULAR, fontSize=8, leading=10.5, textColor=COLORS["body_text"], alignment=TA_LEFT),
        "index_cell_c": ParagraphStyle("IndexCellC", parent=styles["Normal"], fontName=FONT_SEMI, fontSize=8, leading=10.5, textColor=COLORS["primary"], alignment=TA_CENTER),

        "box_title": ParagraphStyle("BoxTitle", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=11.5, leading=15.5, textColor=HexColor("#0B3D7A"), alignment=TA_LEFT),
        "box_text": ParagraphStyle("BoxText", parent=styles["Normal"], fontName=FONT_REGULAR, fontSize=10, leading=14, textColor=COLORS["body_text"], alignment=TA_LEFT),
        "ques_hi": ParagraphStyle("QuesHI", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=12, leading=16.5, textColor=COLORS["dark_text"], alignment=TA_LEFT),
        "hi_body": ParagraphStyle("HiBody", parent=styles["Normal"], fontName=FONT_REGULAR, fontSize=10.5, leading=15, textColor=COLORS["body_hindi"], alignment=TA_LEFT),
        "oneliner_title": ParagraphStyle("OneLinerTitle", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=15, leading=20, textColor=HexColor("#0B3D7A"), alignment=TA_CENTER),
        "oneliner": ParagraphStyle("OneLiner", parent=styles["Normal"], fontName=FONT_REGULAR, fontSize=11, leading=15.5, textColor=COLORS["body_text"], alignment=TA_LEFT),
        "key_cell": ParagraphStyle("KeyCell", parent=styles["Normal"], fontName=FONT_SEMI, fontSize=8.5, leading=11, textColor=COLORS["body_text"], alignment=TA_CENTER),
        "key_cell_bold": ParagraphStyle("KeyCellBold", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=8.5, leading=11, textColor=COLORS["accent_green"], alignment=TA_CENTER),
    }


STYLES = get_pdf_styles()


# --- STORY HELPER FUNCTIONS ---
# --- EXPLANATION / STATIC GK EXTRACTION ---
MAX_EXPLANATION_POINTS = 5
MAX_STATIC_GK_POINTS = 6
_HI_SENT_SPLIT_RE = re.compile(r"(?<=[।!?])\s+|(?<=\.)\s+(?=[\u0900-\u097F])")
_EN_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9₹\"'(])")


def _split_en(text: str) -> List[str]:
    return [s.strip() for s in _EN_SENT_SPLIT_RE.split(text or "") if s.strip()]


def _split_hi(text: str) -> List[str]:
    return [s.strip() for s in _HI_SENT_SPLIT_RE.split(text or "") if s.strip()]


def _hi_or_blank(text: Any) -> str:
    c = _clean_text_for_display(text)
    return c if DEVANAGARI_RE.search(c) else ""


def _extract_explanation_points(item: Dict[str, Any], mcq: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Up to 5 bilingual explanation sentences (EN line + its HI line).

    Prefers the MCQ's own ``explanation_pairs`` (LLM schema, already validated in
    stage 17); otherwise builds them from the item's key points, the detailed
    explanation (sentence-aligned when EN/HI sentence counts match) and finally
    the MCQ's one-line explanation.  No more 2-point cap and no 'मुख्य बिंदु' prefix.
    """
    pairs: List[Tuple[str, str]] = []
    seen: List[str] = []

    def _toks(txt: str) -> set:
        return set(re.findall(r"[a-z0-9₹]+", txt.lower())) - {"the", "a", "an", "of", "for", "and", "in", "to", "is", "at", "on", "by", "will", "be"}

    def is_dup(txt: str) -> bool:
        low = txt.lower()
        t = _toks(low)
        for s in seen:
            if low in s or s in low:
                return True
            st = _toks(s)
            if t and st and len(t & st) / min(len(t), len(st)) >= 0.6:
                return True
        return False

    def add(en: Any, hi: Any, min_len: int = 20) -> None:
        en_c = _clean_text_for_display(en)
        if not en_c or len(en_c) < min_len or is_dup(en_c) or len(pairs) >= MAX_EXPLANATION_POINTS:
            return
        seen.append(en_c.lower())
        pairs.append((en_c, _hi_or_blank(hi)))

    # The MCQ's own pairs were validated in stage 17: keep them as written
    # (only exact repeats dropped), no similarity de-duplication.
    for p in (mcq or {}).get("explanation_pairs") or []:
        if isinstance(p, dict):
            en_c = _clean_text_for_display(p.get("en", ""))
            if en_c and en_c.lower() not in seen and len(pairs) < MAX_EXPLANATION_POINTS:
                seen.append(en_c.lower())
                pairs.append((en_c, _hi_or_blank(p.get("hi", ""))))
    if pairs:
        return pairs

    kp_ens = item.get("key_points_en") or []
    kp_his = item.get("key_points_hi") or []
    for idx, kpe in enumerate(kp_ens):
        add(kpe, kp_his[idx] if idx < len(kp_his) else "")

    det_en = _clean_text_for_display(item.get("detailed_explanation_en", ""))
    det_hi = _clean_text_for_display(item.get("detailed_explanation_hi", ""))
    en_s, hi_s = _split_en(det_en), _split_hi(det_hi)
    if en_s and len(en_s) == len(hi_s):
        for e, h in zip(en_s, hi_s):
            add(e, h)
    elif det_en and len(pairs) < MAX_EXPLANATION_POINTS:
        add(det_en, det_hi, min_len=30)

    if mcq:
        add(mcq.get("explanation_en", ""), mcq.get("explanation_hi", ""))
    return pairs[:MAX_EXPLANATION_POINTS]


def _extract_static_gk_pairs(item: Dict[str, Any], mcq: Optional[Dict[str, Any]] = None) -> List[Tuple[str, str]]:
    """Up to 6 Static GK pairs as ('Label – Value', 'लेबल – मान').

    Source order: the MCQ's ``static_gk`` (LLM schema: label/value in EN+HI),
    ``item['static_gk_pairs']`` (verified pairs from pipeline.static_gk_db), and
    only as a fallback the ``static_facts`` dict.  Private keys (``_static_gk_pairs``
    and anything starting with ``_``) are never printed.
    """
    pairs: List[Tuple[str, str]] = []
    seen: set = set()

    def _add(en: Any, hi: Any) -> None:
        en_c = _clean_text_for_display(en)
        if not en_c or en_c.lower() in seen or len(pairs) >= MAX_STATIC_GK_POINTS:
            return
        if en_c.startswith("[") or en_c.startswith("("):  # stringified list/tuple
            return
        seen.add(en_c.lower())
        pairs.append((en_c, _hi_or_blank(hi)))

    for g in (mcq or {}).get("static_gk") or []:
        if isinstance(g, dict) and g.get("label_en") and g.get("value_en"):
            hi = ""
            if g.get("label_hi") and g.get("value_hi"):
                hi = f"{g['label_hi']} – {g['value_hi']}"
            _add(f"{g['label_en']} – {g['value_en']}", hi)

    for p in item.get("static_gk_pairs") or []:
        if isinstance(p, dict):
            _add(p.get("en", ""), p.get("hi", ""))
        elif isinstance(p, (list, tuple)) and p:
            _add(p[0], p[1] if len(p) > 1 else "")
        elif isinstance(p, str):
            _add(p, "")

    if not pairs:
        sf = item.get("static_facts") or {}
        if isinstance(sf, dict):
            for k, v in sf.items():
                if not isinstance(k, str) or k.startswith("_") or not isinstance(v, (str, int, float)):
                    continue
                k_clean = _clean_text_for_display(k)
                v_clean = _clean_text_for_display(v)
                if k_clean and v_clean:
                    _add(f"{k_clean} – {v_clean}", "")

    if len(pairs) < 4:
        ef_en = _clean_text_for_display(item.get("exam_fact_en", ""))
        if ef_en and len(ef_en) > 15:
            hi = _hi_or_blank(item.get("exam_fact_hi", ""))
            _add(f"Exam Fact – {ef_en}", f"परीक्षा तथ्य – {hi}" if hi else "")

    return pairs[:MAX_STATIC_GK_POINTS]


# --- BILINGUAL RENDERING HELPERS ---
# ReportLab's Paragraph cannot shape Devanagari (the ि matra lands after the
# consonant: विषय -> वषिय).  Every string containing Devanagari therefore goes
# through render_hindi_flowable (HarfBuzz) via text_flowable()/bi_line().
PDF_SHOW_INDEX = os.getenv("ALP_PDF_INDEX", "0").strip().lower() in ("1", "true", "yes", "on")
PDF_SHOW_ANSWER_KEY = os.getenv("ALP_PDF_ANSWER_KEY", "0").strip().lower() in ("1", "true", "yes", "on")
PDF_STATIC_HEADLINE_BOXES = os.getenv("ALP_PDF_STATIC_HEADLINE_BOXES", "0").strip().lower() in ("1", "true", "yes", "on")

HINDI_SIZE_SCALE = float(os.getenv("ALP_PDF_HINDI_SCALE", "1.12"))
HEADLINE_BOX_BG = HexColor("#DCEBFB")
HEADLINE_BOX_BORDER = HexColor("#9CC3EE")
HEADLINE_BOX_RADIUS = 14 * pt
_LETTERS = ["A", "B", "C", "D", "E"]
_NONE_OF_ABOVE_RE = re.compile(r"none of (the )?(above|these)|उपर्युक्त में से कोई नहीं", re.IGNORECASE)


def _rgb(color: Color) -> Tuple[int, int, int]:
    return (int(round(color.red * 255)), int(round(color.green * 255)), int(round(color.blue * 255)))


def text_flowable(text: str, style: ParagraphStyle, width: float = PRINT_W,
                  bg: Color = COLORS["white"], left_pad_mm: float = 0.0,
                  markup: Optional[str] = None) -> Flowable:
    """Paragraph for Latin-only text, HarfBuzz-shaped image+text layer for anything with Devanagari.

    ``markup`` is optional ReportLab markup used only on the Latin path (e.g. <b>).
    """
    clean = _clean_text_for_display(text)
    if DEVANAGARI_RE.search(clean):
        align = {TA_CENTER: "center", TA_RIGHT: "right"}.get(style.alignment, "left")
        # Mukta's x-height is ~12% smaller than Poppins', so scale Hindi up to
        # look the same size as its English partner line (as in the reference).
        return render_hindi_flowable(
            clean, font_size_pt=round(style.fontSize * HINDI_SIZE_SCALE, 2), width_pt=width,
            is_bold=style.fontName == FONT_BOLD or (markup or "").startswith("<b>"),
            color_rgb=_rgb(style.textColor), bg_rgb=_rgb(bg), align=align,
            left_padding_mm=left_pad_mm,
        )
    return Paragraph(markup if markup is not None else _safe(clean), style)


def bi_line(en: str, hi: str, style_en: ParagraphStyle, style_hi: Optional[ParagraphStyle] = None,
            width: float = PRINT_W, bg: Color = COLORS["white"], bullet: str = "• ",
            hi_pad_mm: float = 2.5) -> List[Flowable]:
    """One bilingual fact: the English line, then its Hindi line underneath."""
    out: List[Flowable] = []
    en_c = _clean_text_for_display(en)
    if en_c:
        out.append(text_flowable(bullet + en_c, style_en, width=width, bg=bg,
                                 markup=f"{_safe(bullet)}{_safe(en_c)}"))
    hi_c = _hi_or_blank(hi)
    if hi_c:
        out.append(text_flowable(hi_c, style_hi or style_en, width=width, bg=bg, left_pad_mm=hi_pad_mm))
    return out


class RoundedBox(Flowable):
    """Light-blue rounded panel ('Recent News Headlines Related to ...'), splittable across pages."""

    def __init__(self, children: List[Flowable], width: float = PRINT_W, bg: Color = HEADLINE_BOX_BG,
                 border: Color = HEADLINE_BOX_BORDER, radius: float = HEADLINE_BOX_RADIUS,
                 pad: float = 12 * pt, gap: float = 3 * pt):
        super().__init__()
        self.children = children
        self.width = width
        self.bg, self.border, self.radius, self.pad, self.gap = bg, border, radius, pad, gap
        self._sizes: List[Tuple[float, float]] = []

    def _inner_w(self) -> float:
        return self.width - 2 * self.pad

    def wrap(self, availWidth, availHeight):
        self._sizes = [c.wrap(self._inner_w(), availHeight) for c in self.children]
        h = sum(s[1] for s in self._sizes) + self.gap * max(len(self.children) - 1, 0) + 2 * self.pad
        self.height = h
        return self.width, h

    def split(self, availWidth, availHeight):
        if not self._sizes:
            self.wrap(availWidth, availHeight)
        if self.height <= availHeight or len(self.children) < 2:
            return []
        used, cut = 2 * self.pad, 0
        for i, (_, ch) in enumerate(self._sizes):
            if used + ch > availHeight:
                break
            used += ch + self.gap
            cut = i + 1
        if cut == 0 or cut >= len(self.children):
            return []
        mk = lambda kids: RoundedBox(kids, self.width, self.bg, self.border, self.radius, self.pad, self.gap)
        return [mk(self.children[:cut]), mk(self.children[cut:])]

    def draw(self):
        c = self.canv
        c.saveState()
        c.setFillColor(self.bg)
        c.setStrokeColor(self.border)
        c.setLineWidth(0.8)
        c.roundRect(0, 0, self.width, self.height, self.radius, stroke=1, fill=1)
        c.restoreState()
        y = self.height - self.pad
        for child, (_, ch) in zip(self.children, self._sizes):
            y -= ch
            child.drawOn(c, self.pad, y)
            y -= self.gap


def _headline_box(title: str, rows: List[Tuple[str, str]]) -> Optional[RoundedBox]:
    rows = [(e, h) for e, h in rows if _clean_text_for_display(e)]
    if not rows:
        return None
    inner = PRINT_W - 24 * pt
    kids: List[Flowable] = [text_flowable(title, STYLES["box_title"], width=inner, bg=HEADLINE_BOX_BG,
                                          markup=f"<b>{_safe(title)}</b>")]
    for en, hi in rows:
        kids.extend(bi_line(en, hi, STYLES["box_text"], width=inner, bg=HEADLINE_BOX_BG))
    return RoundedBox(kids)


def _unit_theme(item: Dict[str, Any], mcq: Dict[str, Any]) -> str:
    theme = _clean_text_for_display((mcq or {}).get("theme") or item.get("theme") or item.get("category") or "")
    return theme or "National"


def _one_liner_for(item: Dict[str, Any], mcq: Dict[str, Any], content: Dict[str, Any]) -> Tuple[str, str]:
    ol = (mcq or {}).get("one_liner") or {}
    if isinstance(ol, dict) and ol.get("en"):
        return _clean_text_for_display(ol.get("en")), _hi_or_blank(ol.get("hi"))
    for row in content.get("one_liners") or []:
        if isinstance(row, dict) and row.get("event_id") and row.get("event_id") == item.get("event_id"):
            return _clean_text_for_display(row.get("text_en")), _hi_or_blank(row.get("text_hi"))
    return (_clean_text_for_display(re.sub(r"^\s*>>\s*", "", str(item.get("headline_en", "")))),
            _hi_or_blank(re.sub(r"^\s*>>\s*", "", str(item.get("headline_hi", "")))))


def _plan_headline_boxes(units, content) -> Dict[int, RoundedBox]:
    """Group today's units by theme; after the last unit of a theme with 2+ stories, place its box.

    Built from the edition's own verified stories.  The curated (dated) entries in
    pipeline.static_gk_db.RECENT_HEADLINES_BILINGUAL_DB are only used when
    ALP_PDF_STATIC_HEADLINE_BOXES=1, because they are not tied to this edition's window.
    """
    groups: Dict[str, List[int]] = {}
    for idx, (it, ms) in enumerate(units):
        groups.setdefault(_unit_theme(it, ms[0]).lower(), []).append(idx)
    boxes: Dict[int, RoundedBox] = {}
    for key, idxs in groups.items():
        theme = _unit_theme(units[idxs[0]][0], units[idxs[0]][1][0])
        box = None
        if len(idxs) >= 2:
            rows = [_one_liner_for(units[i][0], units[i][1][0], content) for i in idxs]
            box = _headline_box(f"Recent News Headlines Related to {theme} :", rows)
        elif PDF_STATIC_HEADLINE_BOXES:
            try:
                from pipeline.static_gk_db import lookup_recent_headlines_box
                it = units[idxs[0]][0]
                db = lookup_recent_headlines_box(str(it.get("headline_en", "")), str(it.get("category", "")))
                if db:
                    box = _headline_box(db.get("box_title", ""), [(h.get("en", ""), h.get("hi", "")) for h in db.get("headlines", [])])
            except Exception:
                box = None
        if box is not None:
            boxes[idxs[-1]] = box
    return boxes


def _bilingual_options(m: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Five (en, hi) options.  Never pads with 'None of the above'."""
    out: List[Tuple[str, str]] = []
    raw = m.get("options_bi")
    if isinstance(raw, list) and raw and isinstance(raw[0], dict):
        out = [(_clean_text_for_display(o.get("en")), _hi_or_blank(o.get("hi"))) for o in raw]
    else:
        opts = m.get("options") or []
        his = m.get("options_hi") or []
        for i, o in enumerate(opts):
            if isinstance(o, dict):
                out.append((_clean_text_for_display(o.get("en")), _hi_or_blank(o.get("hi"))))
                continue
            en, hi = _clean_text_for_display(o), (his[i] if i < len(his) else "")
            if not hi and " / " in en:
                left, right = en.split(" / ", 1)
                if DEVANAGARI_RE.search(right):
                    en, hi = left.strip(), right
            out.append((en, _hi_or_blank(hi)))
    return [(e, h) for e, h in out if e and not _NONE_OF_ABOVE_RE.search(e)][:5]


def _option_line(letter: str, en: str, hi: str) -> Flowable:
    if hi and _canon_cmp(hi) != _canon_cmp(en):
        return text_flowable(f"{letter}) {en} / {hi}", STYLES["option_text"], left_pad_mm=1.5)
    return text_flowable(f"{letter}) {en}", STYLES["option_text"], markup=f"<b>{letter})</b> {_safe(en)}")


def _canon_cmp(s: str) -> str:
    return re.sub(r"\s+", "", str(s or "")).lower()


def _pair_units(items: List[Dict[str, Any]], mcqs: List[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], List[Dict[str, Any]]]]:
    """One unit per news item, carrying that item's own MCQs.

    MCQs are matched to items by ``event_id``; when MCQs carry no event ids
    they are paired one-to-one by position.  Items are never recycled (no
    modulo wrap-around), so a headline can never appear under another story's
    question, and an item with no MCQ is skipped.
    """
    items = [i for i in (items or []) if isinstance(i, dict)]
    mcqs = [m for m in (mcqs or []) if isinstance(m, dict) and m]
    by_event: Dict[str, List[Dict[str, Any]]] = {}
    for m in mcqs:
        ev = str(m.get("event_id") or "")
        if ev:
            by_event.setdefault(ev, []).append(m)
    units: List[Tuple[Dict[str, Any], List[Dict[str, Any]]]] = []
    if by_event:
        for it in items:
            ms = by_event.get(str(it.get("event_id") or ""))
            if ms:
                units.append((it, ms))
    else:
        for it, m in zip(items, mcqs):
            units.append((it, [m]))
    return units


def _format_display_date(date_str: str | None) -> str:
    if not date_str:
        return datetime.now().strftime("%d %B %Y")
    clean = str(date_str).replace("daily_", "").replace("weekly_", "").replace("monthly_", "").strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d %B %Y"):
        try:
            dt = datetime.strptime(clean, fmt)
            return dt.strftime("%d %B %Y").lstrip("0")
        except ValueError:
            continue
    return clean


# --- MAIN PDF GENERATION ENGINE ---
def generate_pdf(
    content: Dict[str, Any],
    mcqs: List[Dict[str, Any]],
    output_path: Optional[str] = None,
    date_str: Optional[str] = None,
    **kwargs: Any,
) -> str:
    """Generate professional Exam Genius-grade Current Affairs PDF."""
    items = content.get("items") or []
    if not items:
        raise ValueError("Empty edition: Refusing to generate PDF with zero items.")

    job_info = content.get("job") or {}
    if date_str:
        date_display = _format_display_date(date_str)
    else:
        date_display = job_info.get("date_display") or datetime.now().strftime("%d %B %Y")
    job_id = job_info.get("id") or f"daily_{datetime.now().strftime('%Y-%m-%d')}"

    if output_path is None:
        output_path = os.path.join(OUTPUT_DIR, f"{job_id}.pdf")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        # The platypus Frame adds 6pt padding on each side; 30pt margins give a
        # usable width of exactly PRINT_W at x=36pt, so Paragraphs, tables and
        # shaped-Hindi images all start on the same left edge.
        leftMargin=30 * pt,
        rightMargin=30 * pt,
        topMargin=62 * pt,     # clears the 50pt running-header band (index title was clipped)
        bottomMargin=42 * pt,  # clears the 31pt footer band
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
    story.append(text_flowable("IN BILINGUAL (हिन्दी + ENGLISH)", STYLES["cover_super"]))
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
    # OPTIONAL INDEX (reference PDF has none; enable with ALP_PDF_INDEX=1)
    # =========================================================================
    units = _pair_units(items, mcqs)
    if PDF_SHOW_INDEX:
        story.append(text_flowable("INDEX & TODAY'S EXAM HEADLINES • विषय-सूची", STYLES["index_title"]))
        story.append(text_flowable(f"दैनिक समसामयिकी विषय-सूची • महत्वपूर्ण दिवस एवं परीक्षा तथ्य • {date_display}", STYLES["cover_super"]))
        story.append(Spacer(PRINT_W, 10 * pt))
        index_rows = [[
            Paragraph("Q#", STYLES["index_col_head"]),
            Paragraph("EXAM TOPIC / HEADLINE", STYLES["index_col_head"]),
            Paragraph("CATEGORY", STYLES["index_col_head"]),
        ]]
        for idx, (it, _m) in enumerate(units, 1):
            hl = _clean_text_for_display(it.get("headline_en", ""))
            if not hl:
                continue
            index_rows.append([
                Paragraph(f"Q{idx}", STYLES["index_cell_c"]),
                Paragraph(_safe(hl), STYLES["index_cell"]),
                Paragraph(_safe(str(it.get("category", "General")).upper()), STYLES["index_cell_c"]),
            ])
        index_table = Table(index_rows, colWidths=[36 * pt, 375 * pt, 112 * pt], repeatRows=1)
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
    # MCQ UNITS: Ques / प्रश्न, 5 bilingual options, answer, explanation, Static GK
    # =========================================================================
    q_counter = 0
    answer_key: List[Tuple[int, str, Dict[str, Any]]] = []
    boxes = _plan_headline_boxes(units, content)
    card_bg = COLORS["card_bg"]

    for u_idx, (it, unit_mcqs) in enumerate(units):
        cat = str(it.get("category", "National")).upper()
        headline_en = _clean_text_for_display(it.get("headline_en", ""))
        static_pairs = _extract_static_gk_pairs(it, unit_mcqs[0])

        pill = Table([[Paragraph(f"<b>[ {_safe(cat)} ]</b>   •   <b>Topic:</b> {_safe(headline_en)}", STYLES["section_tag"])]],
                     colWidths=[PRINT_W])
        pill.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLORS["badge_bg"]),
            ("BOX", (0, 0), (-1, -1), 0.5, COLORS["badge_text"]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        first_in_unit = True

        for m in unit_mcqs:
            q_en = _clean_text_for_display(m.get("question_en", ""))
            if not q_en:
                continue  # never invent a question stem for an MCQ without one
            q_counter += 1
            q_idx = q_counter

            block: List[Flowable] = []
            if not first_in_unit:
                block.append(Spacer(PRINT_W, 8 * pt))
            if first_in_unit:
                block += [pill, Spacer(PRINT_W, 6 * pt)]
            block.append(text_flowable(f"Q{q_idx}. {q_en}", STYLES["ques_en"], markup=f"<b>Q{q_idx}.</b> {_safe(q_en)}"))
            q_hi = _hi_or_blank(m.get("question_hi", ""))
            if q_hi:
                block.append(Spacer(PRINT_W, 2 * pt))
                block.append(text_flowable(f"प्रश्न {q_idx}: {q_hi}", STYLES["ques_hi"]))
            block.append(Spacer(PRINT_W, 4 * pt))

            options = _bilingual_options(m)
            for ltr, (o_en, o_hi) in zip(_LETTERS, options):
                block.append(_option_line(ltr, o_en, o_hi))
                block.append(Spacer(PRINT_W, 1.5 * pt))
            block.append(Spacer(PRINT_W, 4 * pt))

            correct_ltr = str(m.get("correct") or "").strip().upper()
            if correct_ltr not in _LETTERS[:len(options)]:
                correct_ltr = "A"
            ans = Table([[Paragraph(f"<b>Answer: Option {correct_ltr}</b>", STYLES["answer_text"])]], colWidths=[PRINT_W])
            ans.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), COLORS["light_green_bg"]),
                ("BOX", (0, 0), (-1, -1), 1, COLORS["border_green"]),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            block.append(ans)
            # Question + options + answer never split across pages.
            story.append(KeepTogether(block))
            story.append(Spacer(PRINT_W, 6 * pt))
            answer_key.append((q_idx, correct_ltr, it))

            expl = _extract_explanation_points(it, m if (m.get("explanation_pairs") or first_in_unit) else {})
            if not first_in_unit and not m.get("explanation_pairs"):
                expl = [(e, h) for e, h in [(_clean_text_for_display(m.get("explanation_en")), m.get("explanation_hi", ""))] if e]
            if expl:
                head = text_flowable("Explanation | व्याख्या:", STYLES["block_head"])
                first_pair = bi_line(*expl[0], STYLES["bullet_en"], STYLES["hi_body"])
                story.append(KeepTogether([head, Spacer(PRINT_W, 3 * pt)] + first_pair))
                story.append(Spacer(PRINT_W, 2.5 * pt))
                for ep_en, ep_hi in expl[1:]:
                    story.extend(bi_line(ep_en, ep_hi, STYLES["bullet_en"], STYLES["hi_body"]))
                    story.append(Spacer(PRINT_W, 2.5 * pt))
            first_in_unit = False

        if static_pairs:
            inner = PRINT_W - 16 * pt
            sgk_rows = [[text_flowable("Static GK (स्थैतिक सामान्य ज्ञान):", STYLES["block_head"], width=inner, bg=card_bg)]]
            for s_en, s_hi in static_pairs:
                for f in bi_line(s_en, s_hi, STYLES["static_fact_en"], STYLES["hi_body"], width=inner, bg=card_bg):
                    sgk_rows.append([f])
            sgk_table = Table(sgk_rows, colWidths=[PRINT_W])
            sgk_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), card_bg),
                ("BOX", (0, 0), (-1, -1), 0.75, COLORS["card_border"]),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]))
            story.append(Spacer(PRINT_W, 3 * pt))
            story.append(sgk_table)

        # Evidence remains in pipeline data; public PDFs intentionally have no source URLs.
        story.append(Spacer(PRINT_W, 8 * pt))
        if u_idx in boxes:
            story.append(boxes[u_idx])
            story.append(Spacer(PRINT_W, 8 * pt))
        story.append(HRFlowable(width="100%", thickness=0.5, color=COLORS["border_light"]))
        story.append(Spacer(PRINT_W, 10 * pt))

    # =========================================================================
    # IMPORTANT ONE-LINER PAGES (English, then Hindi) — as in the reference
    # =========================================================================
    one_liners = [_one_liner_for(it, ms[0], content) for it, ms in units]
    one_liners = [(e, h) for e, h in one_liners if e]
    if one_liners:
        story.append(PageBreak())
        story.append(Paragraph("<b>IMPORTANT ONE - LINER Current Affairs</b>", STYLES["oneliner_title"]))
        story.append(Spacer(PRINT_W, 10 * pt))
        for n, (en, _hi) in enumerate(one_liners, 1):
            story.append(text_flowable(f"{n}. {en}", STYLES["oneliner"], markup=f"<b>{n}.</b> {_safe(en)}"))
            story.append(Spacer(PRINT_W, 6 * pt))
        if any(h for _e, h in one_liners):
            story.append(PageBreak())
            story.append(text_flowable("महत्वपूर्ण वन-लाइनर करंट अफेयर्स", STYLES["oneliner_title"]))
            story.append(Spacer(PRINT_W, 10 * pt))
            for n, (_en, hi) in enumerate(one_liners, 1):
                if hi:
                    story.append(text_flowable(f"{n}. {hi}", STYLES["oneliner"]))
                    story.append(Spacer(PRINT_W, 6 * pt))

    # =========================================================================
    # OPTIONAL ANSWER KEY (enable with ALP_PDF_ANSWER_KEY=1)
    # =========================================================================
    if PDF_SHOW_ANSWER_KEY and answer_key:
        story.append(PageBreak())
        story.append(text_flowable("RAPID REVISION ANSWER KEY • त्वरित उत्तर कुंजी", STYLES["index_title"]))
        story.append(Paragraph(f"Agri Learning Point • Daily Bilingual Edition • {_safe(date_display)}", STYLES["cover_super"]))
        story.append(Spacer(PRINT_W, 12 * pt))
        key_rows = [[
            Paragraph("Q#", STYLES["index_col_head"]),
            Paragraph("ANSWER", STYLES["index_col_head"]),
            Paragraph("EXAM TOPIC / HEADLINE", STYLES["index_col_head"]),
            Paragraph("CATEGORY", STYLES["index_col_head"]),
        ]]
        for q_idx, ans_l, it in answer_key:
            key_rows.append([
                Paragraph(f"Q{q_idx}", STYLES["key_cell"]),
                Paragraph(f"<b>Option {ans_l}</b>", STYLES["key_cell_bold"]),
                Paragraph(_safe(_clean_text_for_display(it.get("headline_en", ""))[:85]), STYLES["index_cell"]),
                Paragraph(_safe(str(it.get("category", "General")).upper()), STYLES["key_cell"]),
            ])
        key_table = Table(key_rows, colWidths=[36 * pt, 65 * pt, 320 * pt, 102 * pt], repeatRows=1)
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

        story.append(Spacer(PRINT_W, 14 * pt))
        tips = [
            f"1. Active Recall: First attempt all {q_counter} MCQs independently without checking the answer callout.",
            "2. Institutional Static GK: Review nodal ministries, establishment years, and headquarters mentioned in each box.",
            "3. Agricultural Core: Pay special focus to ICAR institutes, MSP declarations, and central government farmer welfare schemes.",
            "4. Daily Quizzes: Participate in daily current affairs timed quizzes on Telegram: @agriquizworld.",
            "5. Study Resources: प्रतिदिन नए अभ्यास प्रश्न और संपूर्ण अध्ययन सामग्री हमारे टेलीग्राम चैनल पर नियमित रूप से मिलते हैं।",
        ]
        inner = PRINT_W - 20 * pt
        guide_rows = [[Paragraph("<b>COMPETITIVE EXAM REVISION & PREPARATION STRATEGY:</b>", STYLES["section_tag"])]]
        for tip in tips:
            guide_rows.append([text_flowable(f"• {tip}", STYLES["cover_bullet"], width=inner, bg=card_bg)])
        guide_table = Table(guide_rows, colWidths=[PRINT_W])
        guide_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), card_bg),
            ("BOX", (0, 0), (-1, -1), 1, COLORS["badge_text"]),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(guide_table)

    # Build PDF with Two-Pass ExamGeniusCanvas
    global CURRENT_COVER_DATE
    CURRENT_COVER_DATE = date_display.upper()
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
