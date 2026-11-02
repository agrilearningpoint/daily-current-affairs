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


# --- KEY-FACT HIGHLIGHTING (numbers, amounts, dates) for quick mobile revision ---
PDF_HIGHLIGHT = os.getenv("ALP_PDF_HIGHLIGHT", "1") != "0"
HIGHLIGHT_HEX = os.getenv("ALP_PDF_HIGHLIGHT_COLOR", "#B42318")
_MONTHS_EN = "January|February|March|April|May|June|July|August|September|October|November|December"
_MONTHS_HI = "जनवरी|फरवरी|मार्च|अप्रैल|मई|जून|जुलाई|अगस्त|सितंबर|अक्टूबर|नवंबर|दिसंबर"
_UNITS = (r"st|nd|rd|th|%|per cent|lakh crore|crore|lakh tonnes|lakh metric tonnes|lakh|million tonnes|million|billion|trillion|"
          r"LMT|tonnes|km|kg|MW|GW|"
          r"लाख करोड़|लाख मीट्रिक टन|लाख टन|करोड़|लाख|प्रतिशत|मिलियन टन|मिलियन|अरब|टन|किलो")
KEYFACT_RE = re.compile(
    r"(?<![A-Za-z0-9\-/\u0900-\u097F])(?:₹\s?|\$\s?|Rs\.?\s?)?\d[\d,]*(?:\.\d+)?"
    r"(?:\s?(?:" + _UNITS + r")(?![A-Za-z\u0900-\u097F]))?"
    r"(?:\s(?:" + _MONTHS_EN + "|" + _MONTHS_HI + r")(?![A-Za-z\u0900-\u097F])(?:,?\s\d{4})?)?"
    r"(?![A-Za-z0-9\-])"
)


def highlight_segments(text: str) -> List[Tuple[str, bool]]:
    """Split text into (chunk, is_key_fact) runs."""
    out: List[Tuple[str, bool]] = []
    pos = 0
    for m in KEYFACT_RE.finditer(text):
        if m.start() == 0 and text[m.end():m.end() + 1] == ".":
            continue  # list numbering such as "12." is not a key fact
        if m.start() > pos:
            out.append((text[pos:m.start()], False))
        out.append((m.group(0), True))
        pos = m.end()
    if pos < len(text):
        out.append((text[pos:], False))
    return out or [(text, False)]


def highlight_markup(text: str) -> str:
    """ReportLab markup for Latin text with key facts bold + accent colour (input is plain text)."""
    if not PDF_HIGHLIGHT:
        return _safe(text)
    parts = []
    for chunk, hl in highlight_segments(text):
        if hl:
            parts.append(f'<font name="{FONT_BOLD}" color="{HIGHLIGHT_HEX}">{_safe(chunk)}</font>')
        else:
            parts.append(_safe(chunk))
    return "".join(parts)


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
            # Invisible vector text for QA & search; squeeze it to the image width
            # (unshaped Devanagari measures wider than the shaped line).
            avail = w_pt - (tx - x) - 2
            t = canvas_obj.beginText(tx, ty)
            t.setTextRenderMode(3)
            t.setFont(L["font_name"], size)
            if lw > avail > 0:
                t.setHorizScale(100.0 * avail / lw)
            t.textOut(clean_l)
            canvas_obj.drawText(t)
        canvas_obj.restoreState()

    def draw(self):
        self.drawOn(self.canv, 0, 0)


HINDI_DPI = int(os.getenv("ALP_PDF_HINDI_DPI", "200"))
HINDI_OPAQUE = os.getenv("ALP_PDF_HINDI_OPAQUE", "1") != "0"
_HB_CACHE: Dict[Tuple[str, float, int], Tuple[Any, Any]] = {}


def _hb_font_pair(font_path: str, font_size_pt: float, dpi: int) -> Tuple[Any, Any]:
    key = (font_path, round(font_size_pt, 3), dpi)
    if key not in _HB_CACHE:
        face = freetype.Face(font_path)
        face.set_char_size(int(font_size_pt * 64), 0, dpi, dpi)
        with open(font_path, "rb") as f:
            font_data = f.read()
        hb_font = hb.Font(hb.Face(hb.Blob(font_data)))
        hb_font.scale = (face.size.x_ppem * 64, face.size.y_ppem * 64)
        _HB_CACHE[key] = (face, hb_font)
    return _HB_CACHE[key]


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
    highlight_rgb: Optional[Tuple[int, int, int]] = None,
    highlight_font_path: Optional[str] = None,
) -> Tuple[PILImage.Image, List[str], int, int]:
    base = _hb_font_pair(font_path, font_size_pt, dpi)
    hl_font = _hb_font_pair(highlight_font_path or font_path, font_size_pt, dpi) if highlight_rgb else base

    def shape_runs(txt: str, pair) -> Tuple[List[Any], List[Any]]:
        _face, hb_font = pair
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

    def segments(txt: str) -> List[Tuple[str, bool]]:
        return highlight_segments(txt) if highlight_rgb else [(txt, False)]

    def measure_text(txt: str) -> int:
        w = 0
        for chunk, hl in segments(txt):
            _, positions = shape_runs(chunk, hl_font if hl else base)
            w += sum(pos.x_advance for pos in positions) // 64
        return w

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

    for i, line in enumerate(lines):
        line_w = measure_text(line)
        if align == "center":
            pen_x = (width_px - line_w) // 2
        elif align == "right":
            pen_x = width_px - line_w - int(left_padding_mm * dpi / 25.4)
        else:
            pen_x = int(left_padding_mm * dpi / 25.4)
        base_y = i * line_h + ascender

        for chunk, hl in segments(line):
            pair = hl_font if hl else base
            face = pair[0]
            rgb = highlight_rgb if hl else color_rgb
            infos, positions = shape_runs(chunk, pair)
            for info, pos in zip(infos, positions):
                gid = info.codepoint
                face.load_glyph(gid, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_NORMAL)
                bm = face.glyph.bitmap
                if bm.width > 0 and bm.rows > 0:
                    gm = PILImage.frombytes("L", (bm.width, bm.rows), bytes(bm.buffer))
                    tint = PILImage.new("RGBA", (bm.width, bm.rows), (*rgb, 255))
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
    highlight: bool = False,
) -> Flowable:
    """Return a Flowable containing shaped Hindi with underlying selectable text."""
    clean = _strip_html(text)
    if not clean:
        return Spacer(width_pt, 2 * pt)

    fname = "Mukta-Bold.ttf" if is_bold else "Mukta-Regular.ttf"
    fpath = os.path.join(FONTS_DIR, fname)
    dpi = HINDI_DPI
    scale = dpi / 72.0
    w_px = int(width_pt * scale)
    pad_px = int(left_padding_mm * mm * scale)
    avail_w = w_px - pad_px * 2

    img, lines, iw, ih = _render_hindi_hb_ft(
        clean, fpath, font_size_pt, w_px, avail_w,
        left_padding_mm, color_rgb, bg_rgb, 1.35, align, dpi,
        highlight_rgb=_rgb(HexColor(HIGHLIGHT_HEX)) if (highlight and PDF_HIGHLIGHT) else None,
        highlight_font_path=os.path.join(FONTS_DIR, "Mukta-Bold.ttf"),
    )

    buf = io.BytesIO()
    if HINDI_OPAQUE:
        # Flatten onto the known background: no alpha SMask in the PDF, which
        # roughly halves file size (faster Telegram downloads on mobile).
        flat = PILImage.new("RGB", img.size, bg_rgb)
        flat.paste(img, mask=img.split()[3])
        flat.save(buf, format="PNG", optimize=True)
    else:
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
    _footer_link_seq = 0
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states: List[Dict[str, Any]] = []
        self._page_marks: List[Tuple[str, str, int, float]] = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._page_marks = []
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            if self._pageNumber == 1:
                self.draw_cover_decorations()
            else:
                self.draw_page_decorations(num_pages)
            # Destinations/outline must be registered on the real page (two-pass canvas).
            for key, title, level, y in state.get("_page_marks") or []:
                self.bookmarkHorizontal(key, 0, y + 14)
                if title:
                    self.addOutlineEntry(title, key, level=level, closed=level == 0 and False)
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
        # Clickable channel pills on the cover.
        pills = (("YouTube: Agri Learning Point", LINK_YOUTUBE), ("Telegram: @agrilearningpoint", LINK_TELEGRAM),
                 ("Daily Quiz: @agriquizworld", LINK_TELEGRAM_QUIZ))
        self.setFont(FONT_BOLD, 10.5)
        widths = [self.stringWidth(l, FONT_BOLD, 10.5) + 24 for l, _ in pills]
        gap = 10
        x = (w - (sum(widths) + gap * (len(widths) - 1))) / 2
        for (label, url), pw in zip(pills, widths):
            self.setFillColor(COLORS["white"]); self.roundRect(x, 80, pw, 26, 13, stroke=0, fill=1)
            self.setFillColor(HexColor("#0B57D0")); self.drawCentredString(x + pw / 2, 89, label)
            ExamGeniusCanvas._footer_link_seq += 1
            self._annotationCount = 100000 + ExamGeniusCanvas._footer_link_seq
            self.linkURL(url, (x, 80, x + pw, 106), relative=0)
            x += pw + gap
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
        self.setFont(FONT_BOLD, 10)
        self.setFillColor(HexColor("#103F7B"))
        self.drawString(left_m, header_y, "AGRI LEARNING POINT  |  DAILY CURRENT AFFAIRS")

        self.setFont(FONT_SEMI, 9)
        self.setFillColor(HexColor("#103F7B"))
        if PDF_SHOW_TOC and getattr(self, "_has_contents", False):
            pill_txt = "INDEX"
            pw = self.stringWidth(pill_txt, FONT_BOLD, 8.5) + 14
            px, py = right_m - pw, header_y - 4
            self.setFillColor(HexColor("#103F7B"))
            self.roundRect(px, py, pw, 15, 7, stroke=0, fill=1)
            self.setFillColor(COLORS["white"])
            self.setFont(FONT_BOLD, 8.5)
            self.drawCentredString(px + pw / 2, py + 4.2, pill_txt)
            ExamGeniusCanvas._footer_link_seq += 1
            self._annotationCount = 100000 + ExamGeniusCanvas._footer_link_seq
            self.linkRect("", "contents", (px, py, px + pw, py + 15), relative=0, thickness=0)
            self.setFont(FONT_SEMI, 9)
            self.setFillColor(HexColor("#103F7B"))
            self.drawRightString(px - 8, header_y, "AGTA • IBPS AFO • ICAR • NABARD")
        else:
            self.drawRightString(right_m, header_y, "AGTA • IBPS AFO • ICAR • NABARD • PCS")

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

        footer_h = 34 * pt
        footer_y = 13 * pt
        self.setFillColor(HexColor("#111111"))
        self.rect(0, 0, w, footer_h, stroke=0, fill=1)

        fs = 9.5
        link_col = HexColor("#7CC4FF")
        items = [("YouTube", LINK_YOUTUBE), ("@agrilearningpoint", LINK_TELEGRAM), ("@agriquizworld", LINK_TELEGRAM_QUIZ)]
        x = left_m
        self.setFont(FONT_SEMI, fs)
        for i, (label, url) in enumerate(items):
            prefix = "▶ " if i == 0 else ("Telegram: " if i == 1 else "  |  ")
            self.setFillColor(COLORS["white"])
            self.drawString(x, footer_y, prefix)
            x += self.stringWidth(prefix, FONT_SEMI, fs)
            self.setFillColor(link_col)
            self.drawString(x, footer_y, label)
            lw = self.stringWidth(label, FONT_SEMI, fs)
            self.setStrokeColor(link_col); self.setLineWidth(0.5)
            self.line(x, footer_y - 1.5, x + lw, footer_y - 1.5)
            # Page states are replayed in save(), which rewinds reportlab's
            # annotation counter; use a private, monotonic range for footer links.
            ExamGeniusCanvas._footer_link_seq += 1
            self._annotationCount = 100000 + ExamGeniusCanvas._footer_link_seq
            self.linkURL(url, (x - 2, footer_y - 5, x + lw + 2, footer_y + fs + 2), relative=0)
            x += lw + (14 if i == 0 else 0)

        page_str = f"Page {self._pageNumber} of {total_pages}"
        self.setFont(FONT_SEMI, fs)
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

        "section_tag": ParagraphStyle("SectionTag", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=9, leading=11.5, textColor=COLORS["badge_text"], alignment=TA_LEFT),
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


# Mobile-first reading: PDFs are mostly read fit-to-width on phones, so body,
# question and heading text is scaled up (cover styles keep their design size).
PDF_FONT_SCALE = float(os.getenv("ALP_PDF_FONT_SCALE", "1.28"))
_UNSCALED_STYLES = {"cover_super", "cover_title", "cover_sub", "cover_date", "cover_badge", "cover_bullet",
                    "index_col_head", "index_cell", "index_cell_c", "key_cell", "key_cell_bold"}


def _scale_styles(styles: Dict[str, ParagraphStyle], scale: float) -> Dict[str, ParagraphStyle]:
    if abs(scale - 1.0) < 1e-6:
        return styles
    for name, st in styles.items():
        if name in _UNSCALED_STYLES:
            continue
        st.fontSize = round(st.fontSize * scale, 2)
        st.leading = round(st.leading * scale, 2)
    return styles


STYLES = _scale_styles(get_pdf_styles(), PDF_FONT_SCALE)

# Clickable channel links (footer on every page, cover, closing page).
LINK_YOUTUBE = os.getenv("ALP_LINK_YOUTUBE", "https://www.youtube.com/@agrilearningpoint")
LINK_TELEGRAM = os.getenv("ALP_LINK_TELEGRAM", "https://t.me/agrilearningpoint")
LINK_TELEGRAM_QUIZ = os.getenv("ALP_LINK_TELEGRAM_QUIZ", "https://t.me/agriquizworld")


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
                  markup: Optional[str] = None, highlight: bool = False) -> Flowable:
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
            left_padding_mm=left_pad_mm, highlight=highlight,
        )
    if markup is None:
        markup = highlight_markup(clean) if highlight else _safe(clean)
    return Paragraph(markup, style)


def bi_line(en: str, hi: str, style_en: ParagraphStyle, style_hi: Optional[ParagraphStyle] = None,
            width: float = PRINT_W, bg: Color = COLORS["white"], bullet: str = "• ",
            hi_pad_mm: float = 2.5, highlight: bool = False) -> List[Flowable]:
    """One bilingual fact: the English line, then its Hindi line underneath."""
    out: List[Flowable] = []
    en_c = _clean_text_for_display(en)
    if en_c:
        out.append(text_flowable(bullet + en_c, style_en, width=width, bg=bg,
                                 markup=f"{_safe(bullet)}{highlight_markup(en_c) if highlight else _safe(en_c)}"))
    hi_c = _hi_or_blank(hi)
    if hi_c:
        out.append(text_flowable(hi_c, style_hi or style_en, width=width, bg=bg, left_pad_mm=hi_pad_mm,
                                 highlight=highlight))
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



# =========================================================================
# NEWS PHOTOS ("News in Pictures | चित्रों में खबरें" + one photo per story unit)
# =========================================================================
PDF_INLINE_PHOTOS = os.getenv("ALP_PDF_INLINE_PHOTOS", "1") != "0"
PDF_PHOTO_GALLERY = os.getenv("ALP_PDF_GALLERY", "1") != "0"
PDF_GALLERY_MIN = int(os.getenv("ALP_PDF_GALLERY_MIN", "3"))
PHOTO_RADIUS = 7 * pt
PHOTO_BORDER = HexColor("#CBD5E1")


def _photo_path(it: Dict[str, Any]) -> str:
    """Local, readable photo for a story ('' when none). Never raises."""
    p = str((it or {}).get("image_path") or "").strip()
    if not p:
        return ""
    cand = p if os.path.isabs(p) else os.path.join(BASE_DIR, p)
    try:
        if os.path.isfile(cand) and os.path.getsize(cand) > 0:
            with PILImage.open(cand) as im:
                im.verify()
            return cand
    except Exception:
        return ""
    return ""


class NewsPhoto(Flowable):
    """A news photo scaled to fit (width x max_h), clipped to a rounded frame with a hairline border."""

    def __init__(self, path: str, width: float, max_h: float, align: str = "center", box_w: Optional[float] = None):
        super().__init__()
        self.path = path
        with PILImage.open(path) as im:
            iw, ih = im.size
        scale = min(width / float(iw), max_h / float(ih))
        self.img_w, self.img_h = iw * scale, ih * scale
        self.box_w = box_w if box_w is not None else width
        self.align = align

    def wrap(self, availWidth, availHeight):
        self.box_w = min(self.box_w, availWidth)
        return self.box_w, self.img_h

    def draw(self):
        c = self.canv
        x = {"left": 0, "right": self.box_w - self.img_w}.get(self.align, (self.box_w - self.img_w) / 2.0)
        c.saveState()
        path = c.beginPath()
        path.roundRect(x, 0, self.img_w, self.img_h, PHOTO_RADIUS)
        c.clipPath(path, stroke=0, fill=0)
        c.drawImage(self.path, x, 0, width=self.img_w, height=self.img_h, preserveAspectRatio=False, mask=None)
        c.restoreState()
        c.saveState()
        c.setStrokeColor(PHOTO_BORDER)
        c.setLineWidth(0.8)
        c.roundRect(x, 0, self.img_w, self.img_h, PHOTO_RADIUS, stroke=1, fill=0)
        c.restoreState()


def _photo_credit(it: Dict[str, Any]) -> str:
    src = it.get("source") if isinstance(it.get("source"), dict) else {}
    name = _clean_text_for_display(it.get("image_credit") or src.get("name") or it.get("source_name") or "")
    name = re.sub(r"https?://\S+", "", name).strip(" -|")
    return name


def _caption_style(align=TA_RIGHT) -> ParagraphStyle:
    return ParagraphStyle("PhotoCaption", parent=STYLES["bullet_en"], fontName=FONT_REGULAR,
                          fontSize=7.5 * PDF_FONT_SCALE, leading=9.5 * PDF_FONT_SCALE,
                          textColor=COLORS["muted_text"], alignment=align)


def _unit_photo_block(it: Dict[str, Any]) -> List[Flowable]:
    """Framed story photo + small 'Image: <source>' credit, or [] when the story has no photo."""
    if not PDF_INLINE_PHOTOS:
        return []
    path = _photo_path(it)
    if not path:
        return []
    try:
        w = PRINT_W * 0.6
        photo = NewsPhoto(path, w, 165 * pt, align="center", box_w=PRINT_W)
        out: List[Flowable] = [photo]
        credit = _photo_credit(it)
        if credit:
            pad = (PRINT_W - photo.img_w) / 2.0
            cap = Paragraph(f"<i>Image: {_safe(credit)}</i>", _caption_style(TA_RIGHT))
            cap_t = Table([[cap]], colWidths=[PRINT_W])
            cap_t.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), pad), ("RIGHTPADDING", (0, 0), (-1, -1), pad),
                                       ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
            out.append(cap_t)
        out.append(Spacer(PRINT_W, 6 * pt))
        return out
    except Exception:
        return []  # a bad photo must never break the edition


def _news_in_pictures_story(units) -> List[Flowable]:
    """'News in Pictures | चित्रों में खबरें': three-column photo cards, each linked to its story unit."""
    if not PDF_PHOTO_GALLERY:
        return []
    cards_src = [(i, it) for i, (it, _ms) in enumerate(units, 1) if _photo_path(it)]
    if len(cards_src) < PDF_GALLERY_MIN:
        return []
    ncol = 3
    gap = 8 * pt
    col_w = (PRINT_W - gap * (ncol - 1)) / float(ncol)
    inner = col_w - 10 * pt
    head_st = ParagraphStyle("GalleryHead", parent=STYLES["bullet_en"], fontName=FONT_SEMI,
                             textColor=COLORS["primary"], fontSize=STYLES["bullet_en"].fontSize * 0.74,
                             leading=STYLES["bullet_en"].leading * 0.72)
    hi_st = ParagraphStyle("GalleryHI", parent=STYLES["hi_body"], fontSize=STYLES["hi_body"].fontSize * 0.68,
                           leading=STYLES["hi_body"].leading * 0.68)
    tag_st = ParagraphStyle("GalleryTag", parent=STYLES["section_tag"], fontSize=STYLES["section_tag"].fontSize * 0.78,
                            leading=STYLES["section_tag"].leading * 0.8)
    cap_st = _caption_style(TA_LEFT)

    def _short(t: str, n: int) -> str:
        return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "…"

    cards = []
    for n, it in cards_src:
        try:
            en = _short(_clean_text_for_display(it.get("headline_en", "")), 88)
            hi = _short(_hi_or_blank(it.get("headline_hi", "")), 80)
            cell: List[Flowable] = [NewsPhoto(_photo_path(it), inner, 92 * pt, align="center", box_w=inner),
                                    Spacer(inner, 3 * pt),
                                    Paragraph(f"{_safe(str(it.get('category', 'National')).upper())}  •  Story {n}", tag_st),
                                    LinkTo(Paragraph(_safe(en), head_st), f"u{n}")]
            if hi:
                cell.append(LinkTo(text_flowable(hi, hi_st, width=inner), f"u{n}"))
            credit = _photo_credit(it)
            if credit:
                cell.append(Paragraph(f"<i>Image: {_safe(credit)}</i>", cap_st))
            cards.append(cell)
        except Exception:
            continue
    if len(cards) < PDF_GALLERY_MIN:
        return []
    real = len(cards)
    while len(cards) % ncol:
        cards.append([Spacer(inner, 1)])
    rows = []
    for i in range(0, len(cards), ncol):
        row: List[Any] = []
        for j in range(ncol):
            row.append(cards[i + j])
            if j < ncol - 1:
                row.append("")
        rows.append(row)
    widths: List[float] = []
    for j in range(ncol):
        widths.append(col_w)
        if j < ncol - 1:
            widths.append(gap)
    grid = Table(rows, colWidths=widths)
    styles_ = [("VALIGN", (0, 0), (-1, -1), "TOP"),
               ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
               ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
               ("LEFTPADDING", (1, 0), (1, -1), 0), ("RIGHTPADDING", (1, 0), (1, -1), 0),
               ("LEFTPADDING", (3, 0), (3, -1), 0), ("RIGHTPADDING", (3, 0), (3, -1), 0)]
    for k in range(real):
        r, c = divmod(k, ncol)
        styles_.append(("BOX", (c * 2, r), (c * 2, r), 0.6, COLORS["card_border"]))
    grid.setStyle(TableStyle(styles_))
    return [Anchor("pics", "News in Pictures | चित्रों में खबरें", 0),
            Paragraph("<b>NEWS IN PICTURES</b>", STYLES["oneliner_title"]),
            text_flowable("चित्रों में खबरें  •  पूरी खबर के लिए शीर्षक पर टैप करें", STYLES["cover_super"]),
            Spacer(PRINT_W, 8 * pt), grid, PageBreak()]


def _join_us_box() -> Flowable:
    """Clickable YouTube / Telegram links that close the edition."""
    st = ParagraphStyle("JoinLink", parent=STYLES["box_text"], fontName=FONT_SEMI,
                        fontSize=STYLES["box_text"].fontSize * 1.05, leading=STYLES["box_text"].leading * 1.25)
    rows = [
        ("YouTube:", LINK_YOUTUBE, "Agri Learning Point"),
        ("Telegram:", LINK_TELEGRAM, "@agrilearningpoint"),
        ("Daily Quiz:", LINK_TELEGRAM_QUIZ, "@agriquizworld"),
    ]
    kids: List[Flowable] = [Paragraph("<b>Join Us for Daily Current Affairs &amp; Quizzes</b>", STYLES["box_title"])]
    for lbl, url, txt in rows:
        kids.append(Paragraph(f'<b>{_safe(lbl)}</b> <a href="{url}" color="#0B57D0"><u>{_safe(txt)}</u></a>', st))
    return RoundedBox(kids)


QUICK_BITE_BAND = HexColor("#0B3D7A")

PDF_SHOW_TOC = os.getenv("ALP_PDF_TOC", "1") != "0"
AGRI_GREEN = HexColor("#1B5E20")
AGRI_BG = HexColor("#EAF6EA")
AGRI_BORDER = HexColor("#8BC58F")


class Anchor(Flowable):
    """Zero-size flowable: a named destination (and optional outline entry) at this spot."""

    def __init__(self, key: str, title: str = "", level: int = 0):
        super().__init__()
        self.key, self.title, self.level = key, title, level
        self.width = self.height = 0

    def wrap(self, availWidth, availHeight):
        return 0, 0

    def draw(self):
        _x, y = self.canv.absolutePosition(0, 0)
        marks = getattr(self.canv, "_page_marks", None)
        if marks is not None:
            marks.append((self.key, self.title, self.level, y))
        else:  # plain canvas
            self.canv.bookmarkHorizontal(self.key, 0, y + 14)
            if self.title:
                self.canv.addOutlineEntry(self.title, self.key, level=self.level)
        if self.key == "contents":
            self.canv._has_contents = True


class LinkTo(Flowable):
    """Makes any flowable (incl. shaped-Hindi images) a tap target that jumps to a destination."""

    def __init__(self, child: Flowable, key: str):
        super().__init__()
        self.child, self.key = child, key

    def wrap(self, availWidth, availHeight):
        self.width, self.height = self.child.wrap(availWidth, availHeight)
        return self.width, self.height

    def draw(self):
        self.child.drawOn(self.canv, 0, 0)
        self.canv.linkRect("", self.key, (0, 0, self.width, self.height), relative=1, thickness=0)


TOC_LINK_KEYS: set = set()


def _toc_story(units, content: Dict[str, Any], date_display: str) -> List[Flowable]:
    """Clickable contents page: every MCQ topic (EN + HI) and every section."""
    TOC_LINK_KEYS.clear()
    out: List[Flowable] = [Anchor("contents", "Contents | विषय-सूची", 0)]
    out.append(Paragraph("<b>TODAY'S CONTENTS</b>", STYLES["oneliner_title"]))
    out.append(text_flowable("आज की विषय-सूची  •  किसी भी विषय पर टैप करें", STYLES["cover_super"]))
    out.append(Spacer(PRINT_W, 8 * pt))
    num_w = 40 * pt
    txt_w = PRINT_W - num_w - 16 * pt
    rows = []
    st_en = ParagraphStyle("TocEN", parent=STYLES["bullet_en"], fontName=FONT_SEMI, textColor=COLORS["primary"],
                           fontSize=STYLES["bullet_en"].fontSize * 0.86, leading=STYLES["bullet_en"].leading * 0.84)
    st_hi = ParagraphStyle("TocHI", parent=STYLES["hi_body"], fontSize=STYLES["hi_body"].fontSize * 0.8)
    st_num = ParagraphStyle("TocNum", parent=STYLES["bullet_en"], fontName=FONT_BOLD, textColor=COLORS["white"],
                            fontSize=STYLES["bullet_en"].fontSize * 0.9, alignment=TA_CENTER)
    for i, (it, _ms) in enumerate(units, 1):
        en = _clean_text_for_display(it.get("headline_en", ""))
        hi = _hi_or_blank(it.get("headline_hi", ""))
        key = f"u{i}"
        cell = [LinkTo(Paragraph(_safe(en), st_en), key)]
        if hi:
            cell.append(LinkTo(text_flowable(hi, st_hi, width=txt_w), key))
        rows.append([LinkTo(Paragraph(f"Q{i}", st_num), key), cell])
    t = Table(rows, colWidths=[num_w, PRINT_W - num_w])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), COLORS["primary"]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, COLORS["border_light"]),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (0, -1), 2), ("LEFTPADDING", (1, 0), (1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    out.append(t)
    out.append(Spacer(PRINT_W, 10 * pt))
    # Section chips
    chips: List[Tuple[str, str, str]] = []
    if PDF_PHOTO_GALLERY and sum(1 for it, _m in units if _photo_path(it)) >= PDF_GALLERY_MIN:
        chips.append(("News in Pictures", "चित्रों में खबरें", "pics"))
    if (content.get("agri_corner") or {}).get("items"):
        chips.append(("Agriculture Corner", "कृषि कॉर्नर", "agri"))
    cats = _quick_bite_categories(content)
    for j, (cen, chi) in enumerate(cats):
        chips.append((f"Quick Bites: {cen}", f"क्विक बाइट्स: {chi}" if chi else "", f"qb{j}"))
    chips.append(("One-Liners (English)", "वन-लाइनर (अंग्रेज़ी)", "ol_en"))
    chips.append(("One-Liners (Hindi)", "वन-लाइनर (हिन्दी)", "ol_hi"))
    chip_st = ParagraphStyle("TocChip", parent=STYLES["bullet_en"], fontName=FONT_SEMI, textColor=HexColor("#0B57D0"),
                             fontSize=STYLES["bullet_en"].fontSize * 0.92, leading=STYLES["bullet_en"].leading * 0.92)
    col_w = PRINT_W / 2
    cells = [LinkTo(Paragraph(f"<u>{_safe(e)}</u>", chip_st), k) for e, _h, k in chips]
    TOC_LINK_KEYS.update(k for _e, _h, k in chips)
    TOC_LINK_KEYS.update(f"u{i}" for i in range(1, len(units) + 1))
    if len(cells) % 2:
        cells.append(Spacer(1, 1))
    grid = Table([cells[i:i + 2] for i in range(0, len(cells), 2)], colWidths=[col_w, col_w])
    grid.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HexColor("#EEF5FF")),
        ("BOX", (0, 0), (-1, -1), 0.6, HEADLINE_BOX_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, HEADLINE_BOX_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    out.append(text_flowable("More Sections | अन्य खंड", STYLES["block_head"]))
    out.append(Spacer(PRINT_W, 4 * pt))
    out.append(grid)
    out.append(PageBreak())
    return out


def _quick_bite_categories(content: Dict[str, Any]) -> List[Tuple[str, str]]:
    seen: List[Tuple[str, str]] = []
    for b in content.get("quick_bites") or []:
        if not isinstance(b, dict) or not _clean_text_for_display(b.get("en")):
            continue
        k = str(b.get("category_en") or "General")
        if k not in [x[0] for x in seen]:
            seen.append((k, _hi_or_blank(b.get("category_hi"))))
    return seen


def _agri_corner_story(content: Dict[str, Any]) -> List[Flowable]:
    """'Agriculture Corner': farm-sector news for AGTA / IBPS AFO / ICAR / NABARD aspirants."""
    ac = content.get("agri_corner") or {}
    items = [x for x in (ac.get("items") or []) if isinstance(x, dict) and _clean_text_for_display(x.get("en"))]
    if not items:
        return []
    inner = PRINT_W - 24 * pt
    head_st = ParagraphStyle("AgriHead", parent=STYLES["oneliner_title"], textColor=COLORS["white"])
    band = Table([[Paragraph("<b>AGRICULTURE CORNER</b>", head_st)],
                  [text_flowable("कृषि कॉर्नर  •  AGTA | IBPS AFO | ICAR | NABARD", ParagraphStyle(
                      "AgriSub", parent=STYLES["cover_super"], textColor=COLORS["white"]), width=PRINT_W - 12, bg=AGRI_GREEN)]],
                 colWidths=[PRINT_W])
    band.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), AGRI_GREEN),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    out: List[Flowable] = [PageBreak(), Anchor("agri", "Agriculture Corner | कृषि कॉर्नर", 0), band,
                           Spacer(PRINT_W, 8 * pt)]
    num_st = ParagraphStyle("AgriEN", parent=STYLES["bullet_en"])
    for n, x in enumerate(items, 1):
        en = _clean_text_for_display(x.get("en"))
        kids: List[Flowable] = [Paragraph(f'<font name="{FONT_BOLD}" color="#1B5E20">{n}.</font> {highlight_markup(en)}', num_st)]
        hi = _hi_or_blank(x.get("hi"))
        if hi:
            kids.append(text_flowable(hi, STYLES["hi_body"], width=inner, bg=AGRI_BG, left_pad_mm=2.5, highlight=True))
        out.append(RoundedBox(kids, bg=AGRI_BG, border=AGRI_BORDER, radius=10 * pt, pad=10 * pt, gap=2 * pt))
        out.append(Spacer(PRINT_W, 6 * pt))
    gk = [g for g in (ac.get("static_gk") or []) if isinstance(g, dict) and _clean_text_for_display(g.get("en"))]
    if gk:
        kids = [text_flowable("Agri Static GK | कृषि स्थैतिक सामान्य ज्ञान", STYLES["box_title"], width=inner, bg=HexColor("#FFF7E0"))]
        for g in gk:
            kids.extend(bi_line(g.get("en"), g.get("hi"), STYLES["static_fact_en"], STYLES["hi_body"],
                                width=inner, bg=HexColor("#FFF7E0")))
        out.append(Spacer(PRINT_W, 4 * pt))
        out.append(KeepTogether([RoundedBox(kids, bg=HexColor("#FFF7E0"), border=COLORS["gold_accent"], radius=10 * pt)]))
    return out



def _quick_bites_story(content: Dict[str, Any]) -> List[Flowable]:
    """'Quick Bites' section: short bilingual news grouped by category (content['quick_bites'])."""
    bites = [b for b in (content.get("quick_bites") or []) if isinstance(b, dict) and _clean_text_for_display(b.get("en"))]
    if not bites:
        return []
    out: List[Flowable] = [PageBreak(), Anchor("qb", "Quick Bites | क्विक बाइट्स", 0),
                           Paragraph("<b>QUICK BITES: Other Important News</b>", STYLES["oneliner_title"]),
                           text_flowable("क्विक बाइट्स: अन्य महत्वपूर्ण समाचार", STYLES["oneliner_title"]),
                           Spacer(PRINT_W, 8 * pt)]
    head_en = ParagraphStyle("QBHeadEN", parent=STYLES["block_head"], textColor=COLORS["white"])
    num = 0
    order: List[str] = []
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for b in bites:
        k = str(b.get("category_en") or "General")
        if k not in groups:
            order.append(k)
        groups.setdefault(k, []).append(b)
    inner = PRINT_W - 16 * pt
    for ci, k in enumerate(order):
        rows = groups[k]
        cat_hi = _hi_or_blank(rows[0].get("category_hi"))
        band_txt = f"{k}  |  {cat_hi}" if cat_hi else k
        band = Table([[text_flowable(band_txt, head_en, width=inner, bg=QUICK_BITE_BAND, markup=f"<b>{_safe(k)}</b>")]],
                     colWidths=[PRINT_W])
        band.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), QUICK_BITE_BAND),
            ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        first = True
        for b in rows:
            num += 1
            en = _clean_text_for_display(b.get("en"))
            fl: List[Flowable] = [Paragraph(f"<b>{num}.</b> {highlight_markup(en)}", STYLES["bullet_en"])]
            hi = _hi_or_blank(b.get("hi"))
            if hi:
                fl.append(text_flowable(hi, STYLES["hi_body"], left_pad_mm=2.5, highlight=True))
            fl.append(Spacer(PRINT_W, 6 * pt))
            if first:
                out.append(Spacer(PRINT_W, 6 * pt))
                out.append(KeepTogether([Anchor(f"qb{ci}", k, 1), band, Spacer(PRINT_W, 5 * pt)] + fl))
                first = False
            else:
                out.append(KeepTogether(fl))
    return out


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



def _png_indexed_parts(img, colors: int):
    """Quantize to a small palette and return (PLTE rgb bytes, IDAT zlib stream, bit depth)."""
    import struct
    q = img.convert("RGB").quantize(colors=colors, method=PILImage.Quantize.MEDIANCUT, dither=PILImage.Dither.NONE)
    bits = 4 if colors <= 16 else 8
    b = io.BytesIO()
    q.save(b, format="PNG", optimize=True, bits=bits)
    data = b.getvalue()
    pos, plte, idat, depth = 8, b"", b"", 8
    while pos < len(data):
        ln = struct.unpack(">I", data[pos:pos + 4])[0]
        typ = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            depth = body[8]
        elif typ == b"PLTE":
            plte = body
        elif typ == b"IDAT":
            idat += body
        pos += 12 + ln
    if not plte or not idat:
        return None
    return plte, idat, depth


def compact_pdf_images(path: str, colors: int = 16):
    """Re-encode the shaped-Hindi raster images as small indexed-colour PNG streams.

    Text images hold 1-2 ink colours on one background, so a 16-colour palette is
    visually lossless while cutting the file size several-fold (mobile/Telegram).
    """
    import fitz  # PyMuPDF
    before = os.path.getsize(path)
    doc = fitz.open(path)
    for xref in range(1, doc.xref_length()):
        try:
            if doc.xref_get_key(xref, "Subtype")[1] != "/Image":
                continue
            if doc.xref_get_key(xref, "SMask")[0] != "null":
                continue  # keep alpha images (logos) untouched
            if doc.xref_get_key(xref, "ColorSpace")[1] != "/DeviceRGB":
                continue
            if "DCTDecode" in doc.xref_get_key(xref, "Filter")[1]:
                continue  # JPEG news photos: already compressed, must keep full colour
            pix = fitz.Pixmap(doc, xref)
            if pix.n != 3 or pix.width < 50:
                continue
            img = PILImage.frombytes("RGB", (pix.width, pix.height), pix.samples)
            parts = _png_indexed_parts(img, colors)
            if not parts:
                continue
            plte, idat, depth = parts
            if len(idat) >= len(doc.xref_stream_raw(xref) or b""):
                continue
            ncol = len(plte) // 3
            doc.update_stream(xref, idat, compress=False)
            doc.xref_set_key(xref, "Filter", "/FlateDecode")
            doc.xref_set_key(xref, "BitsPerComponent", str(depth))
            doc.xref_set_key(xref, "ColorSpace", f"[/Indexed /DeviceRGB {ncol - 1} <{plte.hex()}>]")
            doc.xref_set_key(xref, "DecodeParms",
                             f"<</Predictor 15 /Colors 1 /BitsPerComponent {depth} /Columns {pix.width}>>")
        except Exception as exc:  # pragma: no cover - optimisation only
            print("compact skip", xref, exc)
            continue
    tmp = path + ".tmp"
    doc.save(tmp, garbage=3, deflate=True)
    doc.close()
    os.replace(tmp, path)
    return before, os.path.getsize(path)


def _pdf_page_count(path: str) -> int:
    try:
        import fitz  # PyMuPDF
        with fitz.open(path) as d:
            return d.page_count
    except Exception:
        try:
            from pypdf import PdfReader
            return len(PdfReader(path).pages)
        except Exception:
            return 0


# --- MAIN PDF GENERATION ENGINE ---
def generate_pdf(
    content: Dict[str, Any],
    mcqs: List[Dict[str, Any]],
    output_path: Optional[str] = None,
    date_str: Optional[str] = None,
    **kwargs: Any,
) -> str:
    """Generate the PDF; photos never push it past the QA page ceiling.

    When the edition with photos exceeds PDF_QA_MAX_PAGES, it is rebuilt with the
    gallery only, then without photos (the text content is never cut)."""
    global PDF_INLINE_PHOTOS, PDF_PHOTO_GALLERY
    path = _generate_pdf_once(content, mcqs, output_path, date_str, **kwargs)
    has_photos = any(_photo_path(it) for it in (content.get("items") or []) if isinstance(it, dict))
    try:
        max_pages = int(os.getenv("PDF_QA_MAX_PAGES", "45"))
    except ValueError:
        max_pages = 45
    if not has_photos or _pdf_page_count(path) <= max_pages:
        return path
    saved = (PDF_INLINE_PHOTOS, PDF_PHOTO_GALLERY)
    try:
        for inline, gallery in ((False, saved[1]), (False, False)):
            if (inline, gallery) == saved:
                continue
            PDF_INLINE_PHOTOS, PDF_PHOTO_GALLERY = inline, gallery
            path = _generate_pdf_once(content, mcqs, output_path, date_str, **kwargs)
            if _pdf_page_count(path) <= max_pages:
                break
    finally:
        PDF_INLINE_PHOTOS, PDF_PHOTO_GALLERY = saved
    return path


def _generate_pdf_once(
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
        bottomMargin=44 * pt,  # clears the 34pt footer band
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
    social_text = (f'<b>YouTube:</b> <a href="{LINK_YOUTUBE}" color="#0B57D0"><u>Agri Learning Point</u></a>   |   '
                   f'<b>Telegram:</b> <a href="{LINK_TELEGRAM}" color="#0B57D0"><u>@agrilearningpoint</u></a>   |   '
                   f'<b>Daily Quiz:</b> <a href="{LINK_TELEGRAM_QUIZ}" color="#0B57D0"><u>@agriquizworld</u></a>')
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
    # CLICKABLE CONTENTS (replaces the old static index table; ALP_PDF_TOC=0 disables)
    # =========================================================================
    units = _pair_units(items, mcqs)
    if PDF_SHOW_TOC:
        story.extend(_toc_story(units, content, date_display))
        story.append(Anchor("mcq", "MCQ Topics | MCQ विषय", 0))
    try:
        story.extend(_news_in_pictures_story(units))
    except Exception:
        pass  # photos are optional; never fail the edition on them

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
        story.append(Anchor(f"u{u_idx + 1}", f"Q{u_idx + 1}. {headline_en[:70]}", 1 if PDF_SHOW_TOC else 0))

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
                block += _unit_photo_block(it)
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
                first_pair = bi_line(*expl[0], STYLES["bullet_en"], STYLES["hi_body"], highlight=True)
                story.append(KeepTogether([head, Spacer(PRINT_W, 3 * pt)] + first_pair))
                story.append(Spacer(PRINT_W, 2.5 * pt))
                for ep_en, ep_hi in expl[1:]:
                    story.extend(bi_line(ep_en, ep_hi, STYLES["bullet_en"], STYLES["hi_body"], highlight=True))
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
            story.append(KeepTogether([sgk_table]))

        # Evidence remains in pipeline data; public PDFs intentionally have no source URLs.
        story.append(Spacer(PRINT_W, 8 * pt))
        if u_idx in boxes:
            story.append(boxes[u_idx])
            story.append(Spacer(PRINT_W, 8 * pt))
        story.append(HRFlowable(width="100%", thickness=0.5, color=COLORS["border_light"]))
        story.append(Spacer(PRINT_W, 10 * pt))

    story.extend(_agri_corner_story(content))
    qb_story = _quick_bites_story(content)
    story.extend(qb_story)
    if qb_story:
        story.append(Spacer(PRINT_W, 10 * pt))
        story.append(_join_us_box())

    # =========================================================================
    # IMPORTANT ONE-LINER PAGES (English, then Hindi) — as in the reference
    # =========================================================================
    one_liners = [_one_liner_for(it, ms[0], content) for it, ms in units]
    one_liners = [(e, h) for e, h in one_liners if e]
    if one_liners:
        # Start on the same page when at least ~45% of it is free (avoids a near-empty page).
        from reportlab.platypus import CondPageBreak
        story.append(CondPageBreak(PAGE_H * 0.45))
        story.append(Spacer(PRINT_W, 6 * pt))
        story.append(Anchor("ol_en", "One-Liners (English)", 0))
        story.append(Paragraph("<b>IMPORTANT ONE - LINER Current Affairs</b>", STYLES["oneliner_title"]))
        story.append(Spacer(PRINT_W, 10 * pt))
        for n, (en, _hi) in enumerate(one_liners, 1):
            story.append(text_flowable(f"{n}. {en}", STYLES["oneliner"], markup=f"<b>{n}.</b> {highlight_markup(en)}"))
            story.append(Spacer(PRINT_W, 4 * pt))
        if any(h for _e, h in one_liners):
            story.append(CondPageBreak(PAGE_H * 0.45))
            story.append(Spacer(PRINT_W, 10 * pt))
            story.append(Anchor("ol_hi", "One-Liners (Hindi) | वन-लाइनर", 0))
            story.append(text_flowable("महत्वपूर्ण वन-लाइनर करंट अफेयर्स", STYLES["oneliner_title"]))
            story.append(Spacer(PRINT_W, 10 * pt))
            ol_hi = ParagraphStyle("OneLinerHI", parent=STYLES["oneliner"],
                                   fontSize=round(STYLES["oneliner"].fontSize * 0.93, 2))
            for n, (_en, hi) in enumerate(one_liners, 1):
                if hi:
                    story.append(text_flowable(f"{n}. {hi}", ol_hi, highlight=True))
                    story.append(Spacer(PRINT_W, 3 * pt))

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

    # Closing call-to-action with clickable channel links (placed after Quick Bites when present).
    if not qb_story:
        story.append(Spacer(PRINT_W, 14 * pt))
        story.append(_join_us_box())

    # Build PDF with Two-Pass ExamGeniusCanvas
    global CURRENT_COVER_DATE
    CURRENT_COVER_DATE = date_display.upper()
    # Every contents link must resolve: add a fallback destination for any section
    # that ended up empty (e.g. no Hindi one-liners), so reportlab never fails the build.
    defined = {f.key for f in story if isinstance(f, Anchor)}
    for kt in story:
        if isinstance(kt, KeepTogether):
            defined |= {f.key for f in kt._content if isinstance(f, Anchor)}
    for key in TOC_LINK_KEYS - defined:
        story.append(Anchor(key))
    doc.build(story, canvasmaker=ExamGeniusCanvas)
    if os.getenv("ALP_PDF_COMPACT", "1") != "0":
        try:
            compact_pdf_images(output_path, int(os.getenv("ALP_PDF_COMPACT_COLORS", "16")))
        except Exception:
            pass  # compaction is an optimisation only; never fail the edition on it
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
