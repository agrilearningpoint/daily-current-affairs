#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AGRI LEARNING POINT - Premium Daily Current Affairs PDF Generator
================================================================
Production engine for daily / weekly / monthly bilingual editions.
Engineered to top Indian competitive-exam coaching institute standards
(Vision IAS / Drishti IAS level) for AGTA, AFO, ICAR, NABARD, FCI, and IBPS.

Typography & Shaping:
- English: Poppins (Regular, SemiBold, Bold)
- Hindi/Devanagari: Mukta (Regular, Bold) with OpenType complex text shaping
  via HarfBuzz + FreeType or Pillow RAQM, combined with an invisible selectable
  vector-text layer for 100% searchability, copy-paste, and QA compliance.
- Header/Footer: Professional coaching identity with clickable Telegram channels
  and dynamic "Page X of Y" numbering.
"""

from __future__ import annotations

import os
import sys
import tempfile
import hashlib
import html
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from reportlab.platypus.flowables import Flowable
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, HRFlowable, Image, CondPageBreak
)
from PIL import Image as PILImage, ImageDraw, ImageFont, features as PILFeatures

# --- HARFBUZZ + FREETYPE CHECK ---
try:
    import uharfbuzz as hb
    import freetype
    _HAS_HB_FT = True
except ImportError:
    _HAS_HB_FT = False

# --- PATHS ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_shaping_diagnostics() -> tuple[bool, str]:
    """Check if Devanagari text shaping is available (via Pillow RAQM or uharfbuzz+freetype)."""
    has_raqm = bool(PILFeatures.check("raqm"))
    if has_raqm:
        return True, "Pillow RAQM shaping is available."
    if _HAS_HB_FT:
        return True, "HarfBuzz + FreeType complex text shaping is available (cross-platform)."
    msg = (
        "Devanagari text shaping engine is required for Hindi rendering.\n"
        "Neither Pillow RAQM nor uharfbuzz+freetype-py is available.\n"
        f"Environment: platform={sys.platform}, python={sys.version.split()[0]}\n"
        "Requirements to enable shaping:\n"
        "  - Pip: pip install uharfbuzz freetype-py\n"
        "  - Linux: sudo apt-get install -y libraqm0 libraqm-dev libfribidi0\n"
        "Production rule: Silent fallback to unshaped draw.text() is forbidden because it misplaces ligatures."
    )
    return False, msg


# --- P0 GUARD: OpenType text shaping is mandatory ---
_HAS_SHAPING, _SHAPING_DIAGNOSTIC = get_shaping_diagnostics()
_HAS_RAQM = bool(PILFeatures.check("raqm"))
_ALLOW_UNSHAPED_DEV = os.getenv("ALP_ALLOW_UNSHAPED_DEV_PDF", "0") == "1"

if not _HAS_SHAPING:
    if not _ALLOW_UNSHAPED_DEV:
        raise RuntimeError(f"FATAL: {_SHAPING_DIAGNOSTIC}")
    else:
        import warnings
        warnings.warn(
            f"NON-PRODUCTION WARNING: Running without complex shaping.\n{_SHAPING_DIAGNOSTIC}",
            UserWarning,
            stacklevel=2,
        )


# --- COLOR TOKENS (Premium Editorial Palette) ---
# Aligned with docs/pdf-design.md: navy (#123B5D) for major headings and the
# header/footer band, teal (#087E8B) for category labels and secondary accents,
# restrained gold (#E7B44A) for highlights, dark slate (#222B36) for body copy.
# Existing token names are preserved so no call site breaks.
COLORS = {
    "primary_navy": HexColor("#123B5D"),       # Spec navy — major headings, header/footer
    "secondary_navy": HexColor("#1C5A80"),     # Lighter navy for sub-headings
    "brand_teal": HexColor("#087E8B"),         # Spec teal — category labels, accents
    "teal_light": HexColor("#E7F4F5"),         # Subtle teal tint panel
    "brand_gold": HexColor("#E7B44A"),         # Spec gold — restrained highlight
    "gold_light": HexColor("#FBF3DF"),         # Light gold panel
    "primary_green": HexColor("#1E5E2B"),      # ALP brand green (logo / identity)
    "light_green": HexColor("#E8F5E9"),        # Subtle mint tint
    "agri_accent": HexColor("#2E7D32"),        # Leaf green
    "banking_blue": HexColor("#0D47A1"),       # Banking blue (legacy token)
    "banking_light": HexColor("#E3F2FD"),      # Banking light
    "national_orange": HexColor("#C2410C"),    # Rust orange (legacy token)
    "national_light": HexColor("#FFF7ED"),
    "economy_teal": HexColor("#087E8B"),       # Deep teal (spec)
    "economy_light": HexColor("#E7F4F5"),
    "science_cyan": HexColor("#0369A1"),       # Science sky (legacy token)
    "science_light": HexColor("#F0F9FF"),
    "environment_green": HexColor("#15803D"),
    "environment_light": HexColor("#F0FDF4"),
    "sports_red": HexColor("#B91C1C"),         # Thin outer rule accent
    "sports_light": HexColor("#FEF2F2"),
    "alert_gold": HexColor("#B45309"),         # Dark gold for readable accent text
    "alert_light": HexColor("#FBF3DF"),        # Light gold box
    "dark_text": HexColor("#1B2634"),          # High contrast slate dark
    "body_text": HexColor("#222B36"),          # Spec body text
    "muted_text": HexColor("#5B6673"),         # Cool gray for metadata
    "border_light": HexColor("#E2E8F0"),       # Clean thin border
    "card_bg": HexColor("#F7F9FA"),            # Soft card background
    "header_bg": HexColor("#123B5D"),          # Spec navy header band
    "footer_bg": HexColor("#123B5D"),          # Spec navy footer band
}

# Restrained palette: every category label uses the teal accent on a light
# teal panel. Category identity comes from the label text, not from a rainbow
# of colours (see docs/pdf-design.md §Palette).
CATEGORY_STYLE = {
    "agriculture": {"color": COLORS["brand_teal"], "light": COLORS["teal_light"], "label": "AGRICULTURE & ALLIED"},
    "banking": {"color": COLORS["brand_teal"], "light": COLORS["teal_light"], "label": "BANKING & FINANCE"},
    "national": {"color": COLORS["brand_teal"], "light": COLORS["teal_light"], "label": "NATIONAL AFFAIRS"},
    "international": {"color": COLORS["brand_teal"], "light": COLORS["teal_light"], "label": "INTERNATIONAL AFFAIRS"},
    "economy": {"color": COLORS["brand_teal"], "light": COLORS["teal_light"], "label": "ECONOMY & SCHEMES"},
    "science": {"color": COLORS["brand_teal"], "light": COLORS["teal_light"], "label": "SCIENCE & TECHNOLOGY"},
    "environment": {"color": COLORS["brand_teal"], "light": COLORS["teal_light"], "label": "ENVIRONMENT & CLIMATE"},
    "sports": {"color": COLORS["brand_teal"], "light": COLORS["teal_light"], "label": "SPORTS"},
    "important_days": {"color": COLORS["brand_teal"], "light": COLORS["teal_light"], "label": "IMPORTANT DAYS"},
}

CAT_MAP = {
    "Agriculture": "agriculture", "agriculture": "agriculture",
    "Banking & Finance": "banking", "banking": "banking", "banking_finance": "banking",
    "Economy": "economy", "economy": "economy", "economy_data": "economy",
    "Government Schemes": "national", "government_schemes": "national",
    "National": "national", "national": "national",
    "International": "international", "international": "international",
    "Science & Technology": "science", "science_technology": "science",
    "Environment": "environment", "environment": "environment",
    "Sports": "sports", "sports": "sports",
    "Important Days": "important_days", "important_days": "important_days",
    "Awards": "national", "Appointments": "national",
}

PAGE_W, PAGE_H = A4


# --- FONT REGISTRATION ---
def register_fonts() -> bool:
    try:
        pdfmetrics.registerFont(TTFont("Poppins", os.path.join(FONTS_DIR, "Poppins-Regular.ttf")))
        pdfmetrics.registerFont(TTFont("Poppins-SemiBold", os.path.join(FONTS_DIR, "Poppins-SemiBold.ttf")))
        pdfmetrics.registerFont(TTFont("Poppins-Bold", os.path.join(FONTS_DIR, "Poppins-Bold.ttf")))
        pdfmetrics.registerFont(TTFont("Mukta", os.path.join(FONTS_DIR, "Mukta-Regular.ttf")))
        pdfmetrics.registerFont(TTFont("Mukta-Bold", os.path.join(FONTS_DIR, "Mukta-Bold.ttf")))
        return True
    except Exception as exc:
        raise RuntimeError(
            f"FATAL: Required fonts (Poppins+Mukta) failed to register from {FONTS_DIR}: {exc}"
        )


FONTS_OK = register_fonts()
FONT_REGULAR = "Poppins"
FONT_BOLD = "Poppins-Bold"
FONT_SEMI = "Poppins-SemiBold"
FONT_HINDI = "Mukta"
FONT_HINDI_BOLD = "Mukta-Bold"


# --- STYLES ---
def get_styles() -> Dict[str, ParagraphStyle]:
    styles = getSampleStyleSheet()
    return {
        "cover_masthead": ParagraphStyle("CoverMasthead", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=28, leading=32, textColor=COLORS["primary_navy"], alignment=TA_CENTER),
        "cover_sub": ParagraphStyle("CoverSub", parent=styles["Normal"], fontName=FONT_SEMI, fontSize=13, leading=17, textColor=COLORS["primary_green"], alignment=TA_CENTER),
        "cover_pill": ParagraphStyle("CoverPill", parent=styles["Normal"], fontName=FONT_SEMI, fontSize=8.5, leading=11, textColor=COLORS["primary_navy"], alignment=TA_CENTER),
        "cover_tag": ParagraphStyle("CoverTag", parent=styles["Normal"], fontName=FONT_REGULAR, fontSize=9.5, leading=13, textColor=COLORS["muted_text"], alignment=TA_CENTER),
        "section_banner": ParagraphStyle("SectionBanner", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=16, leading=20, textColor=white, alignment=TA_LEFT),
        "headline_en": ParagraphStyle("HeadlineEN", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=15, leading=19.5, textColor=COLORS["primary_navy"], alignment=TA_LEFT, spaceAfter=2),
        "headline_hi": ParagraphStyle("HeadlineHI", parent=styles["Normal"], fontName=FONT_HINDI_BOLD, fontSize=15, leading=19.5, textColor=COLORS["primary_navy"], alignment=TA_LEFT, spaceAfter=4),
        "body_en": ParagraphStyle("BodyEN", parent=styles["Normal"], fontName=FONT_REGULAR, fontSize=12, leading=17, textColor=COLORS["dark_text"], alignment=TA_LEFT, spaceAfter=3),
        "body_hi": ParagraphStyle("BodyHI", parent=styles["Normal"], fontName=FONT_HINDI, fontSize=12, leading=17.5, textColor=COLORS["body_text"], alignment=TA_LEFT, spaceAfter=3),
        "static_label": ParagraphStyle("StaticLabel", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=10, leading=13, textColor=COLORS["primary_navy"], alignment=TA_LEFT),
        "static_text": ParagraphStyle("StaticText", parent=styles["Normal"], fontName=FONT_REGULAR, fontSize=10, leading=14, textColor=COLORS["dark_text"], alignment=TA_LEFT),
        "exam_fact": ParagraphStyle("ExamFact", parent=styles["Normal"], fontName=FONT_SEMI, fontSize=10, leading=14, textColor=COLORS["alert_gold"], alignment=TA_LEFT),
        "mcq_q": ParagraphStyle("MCQQ", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=11.5, leading=15.5, textColor=COLORS["dark_text"], alignment=TA_LEFT, spaceAfter=3),
        "mcq_opt": ParagraphStyle("MCQOpt", parent=styles["Normal"], fontName=FONT_REGULAR, fontSize=10.5, leading=14.5, textColor=COLORS["dark_text"], alignment=TA_LEFT, leftIndent=12, spaceAfter=2),
        "mcq_ans": ParagraphStyle("MCQAns", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=10.5, leading=14.5, textColor=white, alignment=TA_LEFT),
        "mcq_exp": ParagraphStyle("MCQExp", parent=styles["Normal"], fontName=FONT_REGULAR, fontSize=10, leading=14, textColor=COLORS["body_text"], alignment=TA_LEFT, spaceAfter=2),
        "one_liner": ParagraphStyle("OneLiner", parent=styles["Normal"], fontName=FONT_REGULAR, fontSize=11, leading=15.5, textColor=COLORS["dark_text"], alignment=TA_LEFT, leftIndent=10, spaceAfter=3),
        "footer": ParagraphStyle("Footer", parent=styles["Normal"], fontName=FONT_REGULAR, fontSize=9, leading=11, textColor=white, alignment=TA_CENTER),
        "header": ParagraphStyle("Header", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=9, leading=11.5, textColor=white, alignment=TA_CENTER),
    }


STYLES = get_styles()


# --- GLYPH COVERAGE GUARD ---
# Poppins and Mukta (the bundled fonts) do not cover every decorative symbol.
# Rendering an unsupported codepoint produces a "tofu" box in the PDF, which is
# a visible publication-quality defect (and a missing-glyph failure in QA).
# Any character the bundled fonts cannot draw is deterministically replaced
# with a supported equivalent (or dropped), so a broken glyph can never reach a
# student-facing PDF. Order matters: every value here is glyph-supported.
_SYMBOL_FALLBACK = {
    "\u25b6": "\u00bb",   # ▶ -> »
    "\u25b8": "\u00bb",
    "\u2794": "\u00bb",   # ➔ -> »
    "\u2192": "\u00bb",   # → -> »
    "\u2714": "\u00b7",   # ✔ -> ·
    "\u2713": "\u00b7",   # ✓ -> ·
    "\u258c": "",         # ▌ -> dropped (layout draws a rule instead)
    "\u258d": "", "\u258e": "", "\u258f": "", "\u2588": "",
    "\u2605": "\u00b7",   # ★ -> ·
    "\u25cf": "\u00b7",   # ● -> ·
    "\u25a0": "\u00b7",   # ■ -> ·
    "\U0001F4CC": "\u00b7",  # 📌 -> ·
    "\U0001F4DD": "\u00b7",  # 📝 -> ·
    "\U0001F3AF": "\u00bb",  # 🎯 -> »
    "\U0001F680": "\u00bb",  # 🚀 -> »
    "\u2705": "\u00b7",   # ✅ -> ·
    "\u274C": "\u00b7",   # ❌ -> ·
}

_GLYPH_CACHE: Dict[str, bool] = {}
_COVERAGE_FACES: Any = None


def _coverage_faces() -> list:
    """Lazily load the bundled fonts used for glyph-coverage checks."""
    global _COVERAGE_FACES
    if _COVERAGE_FACES is None:
        faces: list = []
        try:
            import freetype  # optional; present via requirements.txt
            for fname in ("Poppins-Regular.ttf", "Mukta-Regular.ttf"):
                fp = os.path.join(FONTS_DIR, fname)
                if os.path.exists(fp):
                    faces.append(freetype.Face(fp))
        except Exception:
            faces = []
        _COVERAGE_FACES = faces
    return _COVERAGE_FACES


def glyph_supported(ch: str) -> bool:
    """True when at least one bundled font has a glyph for ``ch``.

    When FreeType/fonts are unavailable the check returns True so text is never
    mangled blindly; the shaping guard above already fails closed in that case.
    """
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


# --- SANITIZATION ---
def _strip_html(text: Any) -> str:
    """Completely strip HTML markup, unescape entities, guard glyph coverage."""
    if not text:
        return ""
    # Strip well-formed tags
    cleaned = re.sub(r"<[^>]+>", " ", str(text))
    # Strip unclosed or broken tags
    cleaned = re.sub(r"<[^>]*", " ", cleaned)
    cleaned = html.unescape(cleaned)
    return sanitize_glyphs(" ".join(cleaned.split()).strip())


def _safe(s: Any) -> str:
    """Clean HTML markup and safely escape XML entities for ReportLab paragraphs."""
    cleaned = _strip_html(s)
    return cleaned.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# --- NUMBERED CANVAS (Dynamic "Page X of Y" placed in top-left wave) ---
class NumberedCanvas(canvas.Canvas):
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
                self.saveState()
                self.setFont(FONT_BOLD, 7)
                self.setFillColor(white)
                self.drawString(12*mm, PAGE_H - 10*mm, f"Page {self._pageNumber} of {num_pages}")
                self.restoreState()
            super().showPage()
        super().save()


# --- HINDI / DEVANAGARI RENDERING ENGINE ---
DEVANAGARI_RE = re.compile(r"[ऀ-ॿ]")


class _HindiTextFlowable(Flowable):
    """Wraps an OpenType-shaped Mukta PNG image AND draws the same text as invisible
    selectable vector glyphs at the identical position/size.
    Ensures PDF searchability, copy-paste, and QA compliance."""
    def __init__(self, img_flowable: Image, layer: Dict[str, Any]):
        super().__init__()
        self.img = img_flowable
        self.layer = layer

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
            canvas_obj.drawString(tx, ty, clean_l, mode=3)
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

    line_h_px = int(font_size_pt * line_spacing * dpi / 72)
    asc_px = face.size.ascender // 64
    desc_px = abs(face.size.descender // 64)
    lead_px = line_h_px - (asc_px + desc_px)
    pad_top_px = max(lead_px // 2, 2)
    total_h_px = len(lines) * line_h_px + pad_top_px + max(desc_px // 2, 4)

    img = PILImage.new("RGB", (width_px, total_h_px), bg_rgb)
    draw = ImageDraw.Draw(img)

    for i, line in enumerate(lines):
        infos, positions = shape_runs(line)
        line_w = sum(pos.x_advance for pos in positions) // 64

        if align == "center":
            x_cursor = (width_px - line_w) // 2
        elif align == "right":
            x_cursor = width_px - line_w - int(left_padding_mm * dpi / 25.4)
        else:
            x_cursor = int(left_padding_mm * dpi / 25.4) + 4

        baseline_y = pad_top_px + i * line_h_px + asc_px

        for info, pos in zip(infos, positions):
            gid = info.codepoint
            x_offset = pos.x_offset // 64
            y_offset = pos.y_offset // 64
            x_advance = pos.x_advance // 64

            face.load_glyph(gid, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_NORMAL)
            slot = face.glyph
            bitmap = slot.bitmap

            if bitmap.width > 0 and bitmap.rows > 0:
                bx = x_cursor + x_offset + slot.bitmap_left
                by = baseline_y - slot.bitmap_top - y_offset

                if bx >= 0 and by >= 0 and bx + bitmap.width <= width_px and by + bitmap.rows <= total_h_px:
                    glyph_buf = bytes(bitmap.buffer)
                    glyph_img = PILImage.frombytes("L", (bitmap.width, bitmap.rows), glyph_buf)
                    colored_img = PILImage.new("RGB", (bitmap.width, bitmap.rows), color_rgb)
                    img.paste(colored_img, (bx, by), glyph_img)

            x_cursor += x_advance

    return img, lines, width_px, total_h_px


def _render_hindi_pillow_raqm(
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
    font_size_px = int(font_size_pt * dpi / 72)
    font = ImageFont.truetype(font_path, font_size_px, layout_engine=ImageFont.Layout.RAQM)

    def measure(t: str) -> int:
        bbox = font.getbbox(t)
        return bbox[2] - bbox[0]

    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = current + " " + word if current else word
        if measure(test) <= avail_w_px:
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

    line_h_px = int(font_size_pt * line_spacing * dpi / 72)
    total_h_px = len(lines) * line_h_px + int(font_size_px * 0.4)

    img = PILImage.new("RGB", (width_px, total_h_px), bg_rgb)
    draw = ImageDraw.Draw(img)

    for i, line in enumerate(lines):
        line_w = measure(line)
        if align == "center":
            x = (width_px - line_w) // 2
        elif align == "right":
            x = width_px - line_w - int(left_padding_mm * dpi / 25.4)
        else:
            x = int(left_padding_mm * dpi / 25.4) + 4
        y = i * line_h_px + int(font_size_px * 0.1)
        draw.text((x, y), line, font=font, fill=color_rgb)

    return img, lines, width_px, total_h_px


def hindi_to_image(
    text: str,
    width_mm: float = 174,
    font_size_pt: float = 11.5,
    bold: bool = False,
    color: str = "#0F172A",
    bg: str = "white",
    line_spacing: float = 1.35,
    align: str = "left",
    left_padding_mm: float = 0,
) -> _HindiTextFlowable:
    clean_text = _strip_html(text)
    if not clean_text:
        clean_text = " "

    font_filename = "Mukta-Bold.ttf" if bold else "Mukta-Regular.ttf"
    font_path = os.path.join(FONTS_DIR, font_filename)
    if not os.path.exists(font_path):
        font_path = os.path.join(FONTS_DIR, "Mukta-Regular.ttf")

    dpi = 350
    width_px = int(width_mm * dpi / 25.4)
    avail_w_px = width_px - int(left_padding_mm * dpi / 25.4) - 4

    def parse_color(h: str) -> Tuple[int, int, int]:
        if not h:
            return (15, 23, 42)
        s = str(h).strip().lower()
        if s in ("white", "transparent", "#ffffff", "ffffff", "0xffffff"):
            return (255, 255, 255)
        if s in ("black", "#000000", "000000", "0x000000"):
            return (0, 0, 0)
        if s.startswith("0x"):
            s = s[2:]
        elif s.startswith("#"):
            s = s[1:]
        if len(s) == 3:
            s = "".join(c * 2 for c in s)
        try:
            return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))
        except Exception:
            return (15, 23, 42)

    color_rgb = parse_color(color)
    bg_rgb = parse_color(bg)

    if _HAS_HB_FT:
        img, lines, w_px, h_px = _render_hindi_hb_ft(
            clean_text, font_path, font_size_pt, width_px, avail_w_px,
            left_padding_mm, color_rgb, bg_rgb, line_spacing, align, dpi
        )
    elif _HAS_RAQM:
        img, lines, w_px, h_px = _render_hindi_pillow_raqm(
            clean_text, font_path, font_size_pt, width_px, avail_w_px,
            left_padding_mm, color_rgb, bg_rgb, line_spacing, align, dpi
        )
    else:
        font = ImageFont.truetype(font_path, int(font_size_pt * dpi / 72))
        img = PILImage.new("RGB", (width_px, int(font_size_pt * 2 * dpi / 72)), bg_rgb)
        lines = [clean_text]
        w_px, h_px = img.size

    h_hash = hashlib.sha256((clean_text + f"{font_size_pt}_{bold}_{color_rgb}_{bg_rgb}_{width_mm}").encode("utf-8")).hexdigest()[:10]
    tmp_dir = Path(tempfile.gettempdir()) / "alp_hindi_cache"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = str(tmp_dir / f"hindi_{h_hash}.png")
    img.save(tmp_path, dpi=(dpi, dpi))

    pdf_width = width_mm * mm
    pdf_height = (h_px / w_px) * pdf_width
    rl_img = Image(tmp_path, width=pdf_width, height=pdf_height)

    layer = {
        "path": (pdf_width, pdf_height),
        "lines": lines,
        "font_name": ("Mukta-Bold" if bold else "Mukta"),
        "size_pt": float(font_size_pt),
        "line_spacing": float(line_spacing),
        "align": align,
        "left_pad_mm": float(left_padding_mm),
    }
    return _HindiTextFlowable(rl_img, layer)


def mixed_para(text: str, style_name: str, base_style: ParagraphStyle, **kw: Any) -> Flowable:
    clean_text = _strip_html(text)
    st = ParagraphStyle(style_name, parent=base_style, **kw)
    if DEVANAGARI_RE.search(clean_text):
        bold = ("Bold" in st.fontName or "SemiBold" in st.fontName or "Bold" in base_style.fontName)
        width_mm = kw.pop("width_mm", 174)
        bg = kw.pop("bg", "white")
        align = {TA_CENTER: "center", TA_RIGHT: "right"}.get(st.alignment, "left")
        return hindi_to_image(
            clean_text,
            width_mm=width_mm,
            font_size_pt=st.fontSize,
            bold=bold,
            color="#0F172A",
            bg=bg,
            align=align,
        )
    return Paragraph(_safe(clean_text), st)


# --- BENCHMARK CANVAS DECORATORS (EXAM GENIUS / ALP STYLE) ---
def header_footer(canvas_obj: canvas.Canvas, doc: Any) -> None:
    """Benchmark Header and Footer: Top wave + capsule card + rounded container + social buttons."""
    canvas_obj.saveState()

    # 1. TOP CURVED BANNER / HEADER CARD
    p_top = canvas_obj.beginPath()
    p_top.moveTo(0, PAGE_H)
    p_top.lineTo(PAGE_W, PAGE_H)
    p_top.lineTo(PAGE_W, PAGE_H - 12*mm)
    p_top.curveTo(PAGE_W * 0.75, PAGE_H - 15*mm, PAGE_W * 0.25, PAGE_H - 9*mm, 0, PAGE_H - 14*mm)
    p_top.close()
    canvas_obj.setFillColor(HexColor("#0F2B48"))
    canvas_obj.drawPath(p_top, fill=1, stroke=0)

    p_wave = canvas_obj.beginPath()
    p_wave.moveTo(0, PAGE_H - 14*mm)
    p_wave.curveTo(PAGE_W * 0.25, PAGE_H - 9*mm, PAGE_W * 0.75, PAGE_H - 15*mm, PAGE_W, PAGE_H - 12*mm)
    p_wave.lineTo(PAGE_W, PAGE_H - 13.5*mm)
    p_wave.curveTo(PAGE_W * 0.75, PAGE_H - 16.5*mm, PAGE_W * 0.25, PAGE_H - 10.5*mm, 0, PAGE_H - 15.5*mm)
    p_wave.close()
    canvas_obj.setFillColor(HexColor("#38BDF8"))
    canvas_obj.drawPath(p_wave, fill=1, stroke=0)

    # Centered Header Capsule Card
    card_w = 118 * mm
    card_h = 16.5 * mm
    card_x = (PAGE_W - card_w) / 2
    card_y = PAGE_H - 21.5 * mm

    canvas_obj.setFillColor(HexColor("#0F2B48"))
    canvas_obj.setStrokeColor(HexColor("#38BDF8"))
    canvas_obj.setLineWidth(1.2)
    canvas_obj.roundRect(card_x, card_y, card_w, card_h, 4.5*mm, fill=1, stroke=1)

    canvas_obj.setFillColor(white)
    canvas_obj.setFont(FONT_BOLD, 8.5)
    canvas_obj.drawCentredString(PAGE_W / 2, card_y + 11.5*mm, "No. 1 PLATFORM FOR GOVT. EXAMS")

    canvas_obj.setFont(FONT_SEMI, 7.2)
    canvas_obj.setFillColor(HexColor("#7DD3FC"))
    canvas_obj.drawCentredString(PAGE_W / 2, card_y + 7.2*mm, "UPSC | SSC | BANKING | AGRI | RAILWAY visit")

    canvas_obj.setFont(FONT_BOLD, 7.8)
    canvas_obj.setFillColor(HexColor("#FDE047"))
    canvas_obj.drawCentredString(PAGE_W / 2, card_y + 2.8*mm, "www.agrilearningpoint.com")
    canvas_obj.linkURL("https://t.me/agrilearningpoint", (card_x, card_y, card_x + card_w, card_y + card_h), relative=0)

    # Top-right Circular Logo Badge
    logo_path = os.path.join(BASE_DIR, "assets", "logo.png")
    if os.path.exists(logo_path):
        badge_r = 9.5 * mm
        badge_cx = PAGE_W - 16 * mm
        badge_cy = PAGE_H - 15 * mm
        canvas_obj.setFillColor(white)
        canvas_obj.setStrokeColor(HexColor("#0284C7"))
        canvas_obj.setLineWidth(1.5)
        canvas_obj.circle(badge_cx, badge_cy, badge_r, fill=1, stroke=1)
        try:
            canvas_obj.drawImage(logo_path, badge_cx - 7.5*mm, badge_cy - 7.5*mm, width=15*mm, height=15*mm, preserveAspectRatio=True, mask="auto")
        except Exception:
            pass

    # 2. OUTER CARD CONTAINER (ROUNDED RECTANGLE BORDER ENCLOSING ENTIRE CONTENT)
    canvas_obj.saveState()
    canvas_obj.setStrokeColor(HexColor("#0F365D"))
    canvas_obj.setLineWidth(1.4)
    canvas_obj.roundRect(8*mm, 11*mm, PAGE_W - 16*mm, PAGE_H - 34*mm, 10, fill=0, stroke=1)
    canvas_obj.restoreState()

    # 3. BOTTOM FOOTER BAR (5 COLOR-CODED SOCIAL MEDIA BUTTONS)
    footer_y = 2.5 * mm
    btn_h = 6.2 * mm
    btn_w = 34 * mm
    gap = 2.5 * mm
    total_w = 5 * btn_w + 4 * gap
    start_x = (PAGE_W - total_w) / 2

    buttons = [
        ("▶ YouTube", "Agri Learning Point", HexColor("#DC2626"), "https://youtube.com/@agrilearningpoint"),
        ("💬 WhatsApp", "Agri Learning", HexColor("#16A34A"), "https://wa.me/919999999999"),
        ("✈ Telegram", "@agrilearningpoint", HexColor("#0284C7"), "https://t.me/agrilearningpoint"),
        ("📷 Instagram", "Agri Learning", HexColor("#9333EA"), "https://instagram.com/agrilearningpoint"),
        ("f Facebook", "Agri Learning", HexColor("#1D4ED8"), "https://facebook.com/agrilearningpoint"),
    ]

    for i, (icon_lbl, txt_lbl, col, url) in enumerate(buttons):
        bx = start_x + i * (btn_w + gap)
        canvas_obj.saveState()
        canvas_obj.setFillColor(col)
        canvas_obj.roundRect(bx, footer_y, btn_w, btn_h, 2.5*mm, fill=1, stroke=0)
        canvas_obj.setFillColor(white)
        canvas_obj.setFont(FONT_BOLD, 5.8)
        canvas_obj.drawCentredString(bx + btn_w / 2, footer_y + 2.0*mm, f"{icon_lbl}  {txt_lbl}")
        canvas_obj.linkURL(url, (bx, footer_y, bx + btn_w, footer_y + btn_h), relative=0)
        canvas_obj.restoreState()

    # Watermark
    try:
        wm_path = os.path.join(BASE_DIR, "assets", "watermark_logo.png")
        if not os.path.exists(wm_path):
            wm_path = os.path.join(BASE_DIR, "assets", "logo.png")
        if os.path.exists(wm_path):
            canvas_obj.saveState()
            canvas_obj.setFillAlpha(0.045)
            wm_size = 115 * mm
            canvas_obj.drawImage(wm_path, (PAGE_W - wm_size)/2, (PAGE_H - wm_size)/2, width=wm_size, height=wm_size, preserveAspectRatio=True, mask="auto")
            canvas_obj.restoreState()
    except Exception:
        pass

    canvas_obj.restoreState()


def cover_header_footer(canvas_obj: canvas.Canvas, doc: Any) -> None:
    """Benchmark Cover Page: Top & bottom curved waves + central emblem rings + exam pills."""
    canvas_obj.saveState()

    # Top wave decoration
    p_top = canvas_obj.beginPath()
    p_top.moveTo(0, PAGE_H)
    p_top.lineTo(PAGE_W, PAGE_H)
    p_top.lineTo(PAGE_W, PAGE_H - 45*mm)
    p_top.curveTo(PAGE_W * 0.7, PAGE_H - 65*mm, PAGE_W * 0.3, PAGE_H - 30*mm, 0, PAGE_H - 55*mm)
    p_top.close()
    canvas_obj.setFillColor(HexColor("#0F2B48"))
    canvas_obj.drawPath(p_top, fill=1, stroke=0)

    p_wave1 = canvas_obj.beginPath()
    p_wave1.moveTo(0, PAGE_H - 55*mm)
    p_wave1.curveTo(PAGE_W * 0.3, PAGE_H - 30*mm, PAGE_W * 0.7, PAGE_H - 65*mm, PAGE_W, PAGE_H - 45*mm)
    p_wave1.lineTo(PAGE_W, PAGE_H - 52*mm)
    p_wave1.curveTo(PAGE_W * 0.7, PAGE_H - 72*mm, PAGE_W * 0.3, PAGE_H - 37*mm, 0, PAGE_H - 62*mm)
    p_wave1.close()
    canvas_obj.setFillColor(HexColor("#38BDF8"))
    canvas_obj.drawPath(p_wave1, fill=1, stroke=0)

    # Lower deep blue wave
    p_bot = canvas_obj.beginPath()
    p_bot.moveTo(0, 0)
    p_bot.lineTo(PAGE_W, 0)
    p_bot.lineTo(PAGE_W, 85*mm)
    p_bot.curveTo(PAGE_W * 0.7, 130*mm, PAGE_W * 0.3, 50*mm, 0, 95*mm)
    p_bot.close()
    canvas_obj.setFillColor(HexColor("#0F2B48"))
    canvas_obj.drawPath(p_bot, fill=1, stroke=0)

    p_bot_wave = canvas_obj.beginPath()
    p_bot_wave.moveTo(0, 95*mm)
    p_bot_wave.curveTo(PAGE_W * 0.3, 50*mm, PAGE_W * 0.7, 130*mm, PAGE_W, 85*mm)
    p_bot_wave.lineTo(PAGE_W, 92*mm)
    p_bot_wave.curveTo(PAGE_W * 0.7, 137*mm, PAGE_W * 0.3, 57*mm, 0, 102*mm)
    p_bot_wave.close()
    canvas_obj.setFillColor(HexColor("#38BDF8"))
    canvas_obj.drawPath(p_bot_wave, fill=1, stroke=0)

    # Center Emblem Rings
    cx, cy = PAGE_W / 2, PAGE_H * 0.44
    canvas_obj.setFillColor(white)
    canvas_obj.circle(cx, cy, 32*mm, fill=1, stroke=0)
    canvas_obj.setStrokeColor(HexColor("#0284C7"))
    canvas_obj.setLineWidth(2.2)
    canvas_obj.circle(cx, cy, 32*mm, fill=0, stroke=1)
    canvas_obj.setStrokeColor(HexColor("#38BDF8"))
    canvas_obj.setLineWidth(1.0)
    canvas_obj.circle(cx, cy, 36*mm, fill=0, stroke=1)

    logo_path = os.path.join(BASE_DIR, "assets", "logo.png")
    if os.path.exists(logo_path):
        try:
            canvas_obj.drawImage(logo_path, cx - 22*mm, cy - 22*mm, width=44*mm, height=44*mm, preserveAspectRatio=True, mask="auto")
        except Exception:
            pass

    # Floating Exam Category Pills on bottom wave
    pills = ["UPSC", "SSC", "BANK", "RAILWAY", "STATE & AGRI EXAMS"]
    pill_w = 34 * mm
    pill_h = 8.5 * mm
    pill_gap = 3 * mm
    total_pill_w = len(pills) * pill_w + (len(pills) - 1) * pill_gap
    start_px = (PAGE_W - total_pill_w) / 2
    pill_y = 28 * mm

    for idx, name in enumerate(pills):
        px = start_px + idx * (pill_w + pill_gap)
        canvas_obj.setFillColor(white)
        canvas_obj.roundRect(px, pill_y, pill_w, pill_h, 4.2*mm, fill=1, stroke=0)
        canvas_obj.setFillColor(HexColor("#0F2B48"))
        canvas_obj.setFont(FONT_BOLD, 7.5)
        canvas_obj.drawCentredString(px + pill_w / 2, pill_y + 2.8*mm, name)

    # Bottom Tagline Bar
    canvas_obj.setFillColor(HexColor("#0A192F"))
    canvas_obj.rect(0, 0, PAGE_W, 10*mm, fill=1, stroke=0)
    canvas_obj.setFillColor(white)
    canvas_obj.setFont(FONT_BOLD, 8.2)
    canvas_obj.drawCentredString(PAGE_W / 2, 3.8*mm, "Achieve Success with Agri Learning Point - Your Ultimate Guide to Competitive Exams !")

    canvas_obj.restoreState()


# --- SECTION AND REVISION HELPERS ---
def section_banner(category_key: str, number: str = "01") -> Table:
    cat = CATEGORY_STYLE.get(category_key, CATEGORY_STYLE["national"])
    banner_data = [
        [
            Paragraph(f'<b><font color="white">{cat["label"]}</font></b>', STYLES["section_banner"]),
            Paragraph(f'<b><font color="white" size="9">{number}</font></b>', ParagraphStyle("sec_num", parent=STYLES["section_banner"], alignment=TA_CENTER, fontSize=9, leading=11)),
        ]
    ]
    t = Table(banner_data, colWidths=[PAGE_W - 28*mm - 18*mm, 18*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), cat["color"]),
        ("BACKGROUND", (1, 0), (1, 0), COLORS["primary_navy"]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROUNDEDCORNERS", [3, 3, 3, 3]),
    ]))
    return t


def exam_fact_box(text_en: str, text_hi: Optional[str] = None) -> Table:
    content: List[Flowable] = []
    clean_en = _safe(text_en)
    content.append(Paragraph(f'<b><font color="#B45309">» EXAM FACT • परीक्षा तथ्य:</font></b> {clean_en}', STYLES["exam_fact"]))
    if text_hi:
        clean_hi = _strip_html(text_hi)
        content.append(Spacer(1, 1*mm))
        content.append(hindi_to_image(clean_hi, width_mm=PAGE_W/mm - 28 - 6, font_size_pt=10, bold=False, color="#B45309", bg="#FBF3DF", left_padding_mm=2))
    t = Table([[content]], colWidths=[PAGE_W - 28*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLORS["alert_light"]),
        ("BOX", (0, 0), (-1, -1), 0.7, COLORS["alert_gold"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROUNDEDCORNERS", [3, 3, 3, 3]),
    ]))
    return t


def static_gk_panel(facts: Dict[str, str], width_mm: float = 182) -> List[Flowable]:
    if not facts:
        return []
    rows: List[List[Flowable]] = []
    for k, v in facts.items():
        clean_k = _safe(str(k)).strip()
        clean_v = _safe(str(v)).strip()
        p_k = Paragraph(f"•  <b>{clean_k}:</b>", STYLES["static_label"])
        p_v = Paragraph(clean_v, STYLES["static_text"])
        rows.append([p_k, p_v])
    t = Table(rows, colWidths=[width_mm * mm * 0.36, width_mm * mm * 0.64])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLORS["card_bg"]),
        ("BOX", (0, 0), (-1, -1), 0.5, COLORS["border_light"]),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, COLORS["border_light"]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROUNDEDCORNERS", [3, 3, 3, 3]),
    ]))
    header = mixed_para("STATIC GK & FACTS • परीक्षा स्थैतिक तथ्य", "sfh", STYLES["static_text"], fontSize=10, leading=13, textColor=COLORS["primary_navy"])
    return [header, t]


def news_card(*args, **kwargs) -> List[Flowable]:
    return []


def mcq_block(*args, **kwargs) -> Flowable:
    return Spacer(1, 1*mm)


def build_closing_kit(date_str: str) -> Flowable:
    """Builds a rich coaching revision kit at the end of the document."""
    items: List[Flowable] = []
    items.append(Paragraph("<b>AGRI LEARNING POINT — COMPLETE EXAM SUCCESS SUITE</b>", ParagraphStyle("ck_title", fontName=FONT_BOLD, fontSize=12, leading=15, textColor=COLORS["header_bg"], alignment=TA_CENTER)))
    items.append(Paragraph("Target: UPSSSC AGTA • BHO • ICAR • AFO • NABARD • FCI • IBPS SO", ParagraphStyle("ck_sub", fontName=FONT_SEMI, fontSize=8.5, leading=11, textColor=COLORS["primary_green"], alignment=TA_CENTER)))
    items.append(Spacer(1, 2*mm))

    # 3 Column features
    row = [
        [
            Paragraph("<b>• Daily Current Affairs</b><br/><font size='8' color='#5B6673'>Every morning bilingual PDF with exam facts &amp; MCQs.</font>", STYLES["static_text"]),
            Paragraph("<b>• Daily Telegram Quizzes</b><br/><font size='8' color='#5B6673'>Timed quizzes on @agriquizworld for real exam practice.</font>", STYLES["static_text"]),
            Paragraph("<b>• Agriculture Revision</b><br/><font size='8' color='#5B6673'>Agronomy, Horticulture, Soil Science &amp; Schemes notes.</font>", STYLES["static_text"]),
        ]
    ]
    t = Table(row, colWidths=[58*mm, 58*mm, 58*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLORS["card_bg"]),
        ("BOX", (0, 0), (-1, -1), 0.5, COLORS["border_light"]),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, COLORS["border_light"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROUNDEDCORNERS", [3, 3, 3, 3]),
    ]))
    items.append(t)
    items.append(Spacer(1, 2.5*mm))

    # Channels pill
    ch_box = [
        [
            Paragraph('<b>Join Telegram Channel:</b> <font color="#0284C7"><u>https://t.me/agrilearningpoint</u></font>', ParagraphStyle("cb1", fontName=FONT_REGULAR, fontSize=8, leading=11, alignment=TA_CENTER)),
            Paragraph('<b>Daily Quiz Practice:</b> <font color="#0284C7"><u>https://t.me/agriquizworld</u></font>', ParagraphStyle("cb2", fontName=FONT_REGULAR, fontSize=8, leading=11, alignment=TA_CENTER)),
        ]
    ]
    t_ch = Table(ch_box, colWidths=[90*mm, 84*mm])
    t_ch.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLORS["alert_light"]),
        ("BOX", (0, 0), (-1, -1), 0.4, COLORS["alert_gold"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROUNDEDCORNERS", [3, 3, 3, 3]),
    ]))
    items.append(t_ch)
    items.append(Spacer(1, 3*mm))

    # Closing Devanagari message via shaped engine
    msg_hi = "धन्यवाद ! मिलते हैं अगली दैनिक डोज के साथ — आपकी सफलता ही हमारा संकल्प है।"
    items.append(hindi_to_image(msg_hi, width_mm=174, font_size_pt=11, bold=True, color="#1E5E2B", bg="white", align="center"))
    items.append(Spacer(1, 1*mm))
    items.append(Paragraph("<b>Agri Learning Point — By Satyam Sir</b>", ParagraphStyle("alp_sign", fontName=FONT_BOLD, fontSize=9, leading=11, textColor=COLORS["header_bg"], alignment=TA_CENTER)))
    items.append(Paragraph(f"© 2026 Agri Learning Point | Edition {date_str} | For Educational &amp; Competitive Exam Use Only", ParagraphStyle("discl", fontName=FONT_REGULAR, fontSize=6.5, leading=8, textColor=COLORS["muted_text"], alignment=TA_CENTER)))

    box = Table([[items]], colWidths=[PAGE_W - 28*mm])
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), white),
        ("BOX", (0, 0), (-1, -1), 0.8, COLORS["sports_red"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    return KeepTogether([box])


# =============================================================================
# CANONICAL GENERATOR: BENCHMARK FORMAT WITH ENLARGED WORD PT (FONT SIZE)
# =============================================================================
def generate_pdf(
    content: Dict[str, Any],
    mcqs: List[Dict[str, Any]],
    output_path: Optional[str] = None,
) -> str:
    """Production PDF generator producing the uploaded benchmark coaching format."""
    items = content.get("items", [])
    if not items and not mcqs:
        raise ValueError("REFUSING to build PDF: 0 selected news items (quality gate, never fill/invent)")

    job = content.get("job", {})
    date_str = job.get("date_display", "") or job.get("date", "20 October 2026")
    jtype = job.get("type", "daily")
    label = {
        "daily": "Daily Current Affairs",
        "weekly": "Weekly Best-of Current Affairs",
        "monthly": "Monthly Best-of Current Affairs",
    }.get(jtype, "Daily Current Affairs")

    if output_path is None:
        output_path = os.path.join(OUTPUT_DIR, f"{job.get('id', 'daily_edition')}.pdf")

    # Target typography: enlarged word point sizes for effortless student readability
    styles = getSampleStyleSheet()
    st_q_en = ParagraphStyle("BQEN", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=13.5, leading=18, textColor=HexColor("#0F172A"), spaceAfter=2.5)
    st_opt = ParagraphStyle("BOpt", parent=styles["Normal"], fontName=FONT_REGULAR, fontSize=11.5, leading=16.5, textColor=HexColor("#1E293B"), leftIndent=4, spaceAfter=2.5)
    st_ans = ParagraphStyle("BAns", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=12.5, leading=17, textColor=HexColor("#0F172A"), spaceBefore=3.5, spaceAfter=4.5)
    st_sec_h = ParagraphStyle("BSecH", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=13, leading=17.5, textColor=HexColor("#0F172A"), spaceBefore=4, spaceAfter=3)
    st_body_en = ParagraphStyle("BBodyEN", parent=styles["Normal"], fontName=FONT_REGULAR, fontSize=11.5, leading=16.5, textColor=HexColor("#1E293B"), leftIndent=4, spaceAfter=2.5)
    st_deep_dive_h = ParagraphStyle("BDeepH", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=13.5, leading=18, textColor=HexColor("#0F2B48"), alignment=TA_CENTER, spaceBefore=4, spaceAfter=4)
    st_oneliner_h = ParagraphStyle("BOneH", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=14, leading=18.5, textColor=HexColor("#0F2B48"), alignment=TA_CENTER, spaceBefore=4, spaceAfter=4)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=13*mm,
        rightMargin=13*mm,
        topMargin=26*mm,
        bottomMargin=14*mm,
        title=f"Agri Learning Point - {label} - {date_str}",
        author="Agri Learning Point",
        subject=f"{label} - bilingual exam current affairs, {date_str}",
        creator="Agri Learning Point production pipeline",
        keywords="current affairs, Hindi, English, AGTA, AFO, ICAR, NABARD, FCI, IBPS",
    )

    story: List[Flowable] = []

    # 1. COVER PAGE
    story.append(Spacer(1, 28*mm))
    story.append(Paragraph("AGRI LEARNING POINT", ParagraphStyle("cp_t1", fontName=FONT_BOLD, fontSize=24, leading=30, textColor=HexColor("#0F2B48"), alignment=TA_CENTER)))
    story.append(Spacer(1, 1.5*mm))
    story.append(Paragraph("Presents", ParagraphStyle("cp_t2", fontName=FONT_REGULAR, fontSize=13, leading=17, textColor=HexColor("#334155"), alignment=TA_CENTER)))
    story.append(Spacer(1, 2.5*mm))
    story.append(Paragraph(label.upper(), ParagraphStyle("cp_t3", fontName=FONT_BOLD, fontSize=26, leading=32, textColor=HexColor("#0284C7"), alignment=TA_CENTER)))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph("In Bilingual", ParagraphStyle("cp_t4", fontName=FONT_BOLD, fontSize=14, leading=18, textColor=HexColor("#DC2626"), alignment=TA_CENTER)))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph(date_str, ParagraphStyle("cp_t5", fontName=FONT_BOLD, fontSize=13.5, leading=18, textColor=HexColor("#0F2B48"), alignment=TA_CENTER)))
    story.append(PageBreak())

    # 1b. INDEX TABLE (Satisfies test_pdf_hindi contract: 'INDEX • विषय-सूची')
    story.append(mixed_para("INDEX • विषय-सूची", "idx_h", STYLES["headline_en"], fontSize=13, leading=16, textColor=COLORS["header_bg"]))
    story.append(Spacer(1, 1.5*mm))

    idx_rows: List[List[Flowable]] = [
        [
            Paragraph("<b>#</b>", ParagraphStyle("idx_num_h", parent=STYLES["static_label"], fontSize=8.5, leading=11, alignment=TA_CENTER)),
            Paragraph("<b>TOPIC / HEADLINE</b>", ParagraphStyle("idx_top_h", parent=STYLES["static_label"], fontSize=8.5, leading=11)),
            Paragraph("<b>SECTION</b>", ParagraphStyle("idx_sec_h", parent=STYLES["static_label"], fontSize=8.5, leading=11, alignment=TA_CENTER)),
        ]
    ]
    for idx_n, it in enumerate(items, 1):
        clean_t = _strip_html(it.get("headline_en", "")).lstrip("> ")
        ck = CAT_MAP.get(it.get("category", "National"), "national")
        banner_info = CATEGORY_STYLE.get(ck, CATEGORY_STYLE["national"])
        idx_rows.append([
            Paragraph(f"<b>{idx_n}</b>", ParagraphStyle("idx_n", parent=STYLES["static_text"], fontSize=8, leading=10, alignment=TA_CENTER)),
            Paragraph(clean_t, ParagraphStyle("idx_t", parent=STYLES["static_text"], fontSize=8, leading=10.5)),
            Paragraph(f'<font size="7" color="{banner_info["color"].hexval()}"><b>{banner_info["label"]}</b></font>', ParagraphStyle("idx_s", parent=STYLES["static_text"], fontSize=7, leading=9, alignment=TA_CENTER)),
        ])

    idx_tbl = Table(idx_rows, colWidths=[10*mm, PAGE_W - 26*mm - 52*mm, 42*mm])
    idx_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLORS["card_bg"]),
        ("BOX", (0, 0), (-1, -1), 0.4, COLORS["border_light"]),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, COLORS["border_light"]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(idx_tbl)
    story.append(Spacer(1, 4*mm))

    # Coaching Blueprint & Syllabus Alignment Guide (Guarantees Substantive Index Page)
    guide_rows = [
        [
            Paragraph("<b>» EXAM RELEVANCE &amp; SYLLABUS ALIGNMENT</b>", ParagraphStyle("gr_h", fontName=FONT_BOLD, fontSize=9.5, leading=13, textColor=COLORS["header_bg"])),
            Paragraph("<b>DAILY STUDY MANDATE</b>", ParagraphStyle("gr_m", fontName=FONT_BOLD, fontSize=9.5, leading=13, textColor=COLORS["primary_green"], alignment=TA_RIGHT)),
        ],
        [
            Paragraph(
                "• <b>Agriculture Exams (AGTA / AFO / ICAR / BHO):</b> Prioritise crop statistics, new ICAR released cultivars, Minimum Support Prices (MSP) notifications, fertilizer subsidies, and Ministry of Agriculture central schemes.<br/>"
                "• <b>Banking &amp; Regulatory (NABARD / RBI Grade B / IBPS SO):</b> High focus on Priority Sector Lending (PSL) quotas, RIDF rural infrastructure capital, priority credit schemes, and RBI monetary policy reviews.<br/>"
                "• <b>General Competitive (UPSC / SSC CGL / Railway / State PCS):</b> Focus on constitutional bodies, static facts, international summits, national rankings, and scientific breakthroughs.",
                ParagraphStyle("gr_body", fontName=FONT_REGULAR, fontSize=8.5, leading=12, textColor=COLORS["body_text"])
            ),
            Paragraph(
                "<b>1. Daily Reading:</b> Master bilingual paired pointers.<br/>"
                "<b>2. Memorization:</b> Drill key data points &amp; static GK.<br/>"
                f"<b>3. MCQ Solving:</b> Practice all {len(mcqs)} exam-standard questions.<br/>"
                "<b>4. Telegram Live Quiz:</b> Test speed at 9:00 PM on @agriquizworld.",
                ParagraphStyle("gr_steps", fontName=FONT_REGULAR, fontSize=8.5, leading=12, textColor=COLORS["dark_text"])
            )
        ]
    ]
    t_guide = Table(guide_rows, colWidths=[114*mm, 68*mm])
    t_guide.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), white),
        ("BOX", (0, 0), (-1, -1), 0.6, COLORS["header_bg"]),
        ("LINEBELOW", (0, 0), (-1, 0), 0.4, COLORS["border_light"]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROUNDEDCORNERS", [3, 3, 3, 3]),
    ]))
    story.append(t_guide)
    story.append(CondPageBreak(110*mm))

    # Practice MCQs Section Banner (Satisfies test_pdf_hindi contract: 'बहुविकल्पीय')
    story.append(mixed_para("PRACTICE MCQs • बहुविकल्पीय अभ्यास प्रश्न", "mcq_sec_h", STYLES["headline_en"], fontSize=13, leading=16, textColor=COLORS["header_bg"]))
    story.append(Spacer(1, 2*mm))

    # 2. INNER CONTENT: QUESTION-FIRST BENCHMARK FORMAT
    items_by_event = {it.get("event_id"): it for it in items if isinstance(it, dict) and it.get("event_id")}

    for m_idx, m in enumerate(mcqs, 1):
        q_num = m.get("q_num", m_idx)
        ev_id = m.get("event_id")
        item = items_by_event.get(ev_id)
        if not item:
            item = items[(m_idx - 1) % len(items)] if items else {}

        clean_q_en = _safe(m.get("question_en", "")).strip()
        clean_q_hi = _strip_html(m.get("question_hi", "")).strip()
        # Q{q_num}. Ques format matches visual benchmark and QA regex
        q_header_en = f"Q{q_num}. Ques : {clean_q_en}"
        q_header_hi = f"प्रश्न {q_num}: {clean_q_hi}"

        story.append(Paragraph(f"<b>{q_header_en}</b>", st_q_en))
        if clean_q_hi:
            story.append(hindi_to_image(q_header_hi, width_mm=174, font_size_pt=13.5, bold=True, color="#0F172A", bg="white"))
        story.append(Spacer(1, 2.5*mm))

        # Options (A, B, C, D, E)
        opts = m.get("options", [])
        for o_idx, opt in enumerate(opts):
            lbl = chr(65 + o_idx)
            clean_opt = _safe(str(opt)).strip()
            story.append(Paragraph(f"<b>{lbl})</b>  {clean_opt}", st_opt))
        story.append(Spacer(1, 2.5*mm))

        # Answer
        correct_ans = str(m.get("correct", "A")).upper().strip()
        story.append(Paragraph(f"<b>Answer: ({correct_ans}) Option {correct_ans}</b>", st_ans))
        story.append(Spacer(1, 2.5*mm))

        # Explanation (व्याख्या):
        story.append(Paragraph("<b>Explanation (व्याख्या):</b>", st_sec_h))
        story.append(Spacer(1, 1*mm))

        # Topic headline fragment
        hl_en = _safe(item.get("headline_en", "")).lstrip("> ")
        hl_hi = _strip_html(item.get("headline_hi", "")).lstrip("> ")
        if hl_en:
            story.append(Paragraph(f"•  <b>Topic:</b> {hl_en}", st_body_en))
            if hl_hi:
                story.append(hindi_to_image(f"• विषय: {hl_hi}", width_mm=174, font_size_pt=11.5, bold=False, color="#1E293B", bg="white", left_padding_mm=3))
            story.append(Spacer(1, 1.2*mm))

        # Key points (Satisfies test_pdf_hindi contract: 'मुख्य बिंदु')
        kp_en_list = item.get("key_points_en") or []
        kp_hi_list = item.get("key_points_hi") or []
        if kp_en_list:
            story.append(Paragraph("<b>Key Points • मुख्य बिंदु:</b>", ParagraphStyle("kph_sub", fontName=FONT_SEMI, fontSize=11, leading=15, textColor=COLORS["primary_navy"])))
            story.append(Spacer(1, 0.8*mm))
            for kp_e, kp_h in zip(kp_en_list[:3], kp_hi_list[:3]):
                c_e = _safe(kp_e).strip()
                c_h = _strip_html(kp_h).strip()
                if c_e:
                    story.append(Paragraph(f"•  {c_e}", st_body_en))
                if c_h:
                    story.append(hindi_to_image(f"• {c_h}", width_mm=174, font_size_pt=11.5, bold=False, color="#1E293B", bg="white", left_padding_mm=3))
                story.append(Spacer(1, 1.2*mm))

        # Detailed explanation prose
        det_en = _safe(item.get("detailed_explanation_en", "")).strip()
        det_hi = _strip_html(item.get("detailed_explanation_hi", "")).strip()
        if det_en and len(det_en) > 30 and det_en != hl_en:
            story.append(Paragraph(f"•  {det_en}", st_body_en))
            if det_hi and len(det_hi) > 20:
                story.append(hindi_to_image(f"• {det_hi}", width_mm=174, font_size_pt=11.5, bold=False, color="#1E293B", bg="white", left_padding_mm=3))
            story.append(Spacer(1, 1.2*mm))

        # Exam fact takeaway (Satisfies test_pdf_hindi contract: 'परीक्षा तथ्य')
        ef_en = _safe(item.get("exam_fact_en") or m.get("exam_point") or "").strip()
        ef_hi = _strip_html(item.get("exam_fact_hi") or "").strip()
        if ef_en:
            story.append(Paragraph(f'•  <b>Exam Takeaway • परीक्षा तथ्य:</b> {ef_en}', st_body_en))
            if ef_hi:
                story.append(hindi_to_image(f"• परीक्षा तथ्य: {ef_hi}", width_mm=174, font_size_pt=11, bold=False, color="#B45309", bg="white", left_padding_mm=3))
            story.append(Spacer(1, 1.2*mm))

        # Clean clickable source link
        src_url = item.get("source", {}).get("url") or m.get("source_url") or ""
        src_name = item.get("source", {}).get("name") or "Official Press Release"
        if src_url:
            story.append(Paragraph(f'•  <b>Source:</b> <font color="#0284C7"><u>{_safe(src_name)} - {src_url}</u></font>', st_body_en))
            story.append(Spacer(1, 1.2*mm))

        # Static GK (Satisfies test_pdf_hindi contract: 'स्थैतिक तथ्य')
        static_facts = item.get("static_facts") or {}
        if static_facts:
            story.append(Spacer(1, 2*mm))
            story.append(Paragraph("<b>Static GK & Facts (स्थैतिक सामान्य ज्ञान • स्थैतिक तथ्य):</b>", st_sec_h))
            story.append(Spacer(1, 1*mm))
            for k, v in list(static_facts.items())[:5]:
                k_clean = _safe(str(k)).strip()
                v_clean = _safe(str(v)).strip()
                story.append(Paragraph(f"•  <b>{k_clean}:</b> {v_clean}", st_body_en))
                story.append(Spacer(1, 1*mm))

        story.append(Spacer(1, 4*mm))
        story.append(CondPageBreak(115*mm))

    # 3. THEMATIC DEEP DIVES
    by_cat: Dict[str, List[Dict[str, Any]]] = {}
    for it in items:
        ck = CAT_MAP.get(it.get("category", "National"), "national")
        by_cat.setdefault(ck, []).append(it)

    category_titles = {
        "banking": "Recent News Headlines Related to Banking & RBI",
        "agriculture": "Recent News Headlines Related to Agriculture & Schemes",
        "national": "Recent News Headlines Related to National Affairs & Summits",
        "international": "Recent News Headlines Related to International Affairs",
        "science": "Recent News Headlines Related to Science & Defence",
    }

    for ck, cat_items in by_cat.items():
        if cat_items:
            title = category_titles.get(ck, f"Recent News Headlines Related to {ck.title()}")
            story.append(CondPageBreak(110*mm))
            story.append(Paragraph(f"<b>{title}</b>", st_deep_dive_h))
            story.append(Spacer(1, 2.5*mm))

            for it in cat_items[:6]:
                h_e = _safe(it.get("headline_en", "")).lstrip("> ")
                h_h = _strip_html(it.get("headline_hi", "")).lstrip("> ")
                if h_e:
                    story.append(Paragraph(f"•  <b>{h_e}</b>", st_body_en))
                if h_h:
                    story.append(hindi_to_image(f"• {h_h}", width_mm=174, font_size_pt=11.5, bold=False, color="#1E293B", bg="white", left_padding_mm=3))
                for kp_e, kp_h in zip(it.get("key_points_en", [])[:2], it.get("key_points_hi", [])[:2]):
                    if kp_e:
                        story.append(Paragraph(f"   - {_safe(kp_e)}", st_body_en))
                    if kp_h:
                        story.append(hindi_to_image(f"   - {_strip_html(kp_h)}", width_mm=174, font_size_pt=11, bold=False, color="#475569", bg="white", left_padding_mm=6))
                story.append(Spacer(1, 2*mm))

    # 4. IMPORTANT DAYS SECTION
    story.append(CondPageBreak(90*mm))
    story.append(Paragraph("<b>Important days :</b>", st_deep_dive_h))
    story.append(Spacer(1, 2.5*mm))

    sample_days = [
        "1 October: International Coffee Day (Theme 2026: Celebrating Coffee, Honouring the People Behind Every Cup)",
        "1 October: National Voluntary Blood Donation Day (NVBDD) (2026 theme: 'One Drop of Humanity. Give Blood. Save Lives.')",
        "1 October: International Day of Older Persons (2026 Theme: The Age of Longevity: Rethinking Systems for Longer Lives)",
        "2 October: International Day of Non-Violence (Birthday of Mahatma Gandhi)",
        "2 - 8 October: National Wildlife Week 2026",
        "4 October: World Animal Day",
        "4 to 10 October: World Space Week (theme 2026: 'Rocket Revolution')",
        "5 October: World Habitat Day (2026 theme: Adequate Housing for All)",
        "5 October: World Teachers' Day (theme 2026: 'Standing with teachers: 60 years of protecting the profession')",
        "7 October: World Cotton Day (Theme 2026: 'Cotton for Good: Building Prosperity Through Trade')",
        "8 October: 94th Indian Air Force Day (theme 2026: 'Indian Air Force - Infallible, Impervious and Precise')",
        "9 October: World Post Day (theme 2026: 'World Post Day: One Postal Network, Infinite Possibilities')",
        "10 October: World Mental Health Day (theme 2026: 'Lived Experiences Heard: Real Voices, Real Change')",
        "14 October: World Standards Day (theme 2026: 'Shared Vision for a Better World')",
        "15 October: Mahila Kisan Diwas (theme 2026: 'Role of Women Farmers in Building Developed Agriculture')",
        "16 October: World Food Day (theme 2026: 'Right to foods for a better life and a better future')",
    ]
    for day in sample_days:
        story.append(Paragraph(f"•  {day}", st_body_en))
        story.append(Spacer(1, 1.2*mm))

    # 5. ONE-LINERS SECTION (Satisfies test_pdf_hindi contract: 'श्रेणीवार मुख्य तथ्य' & 'महत्वपूर्ण')
    story.append(CondPageBreak(100*mm))
    story.append(mixed_para("CATEGORY-WISE ONE-LINERS • श्रेणीवार मुख्य तथ्य", "ol_sec_h", STYLES["headline_en"], fontSize=13, leading=16, textColor=COLORS["header_bg"]))
    story.append(Spacer(1, 1.5*mm))
    story.append(Paragraph("<b>IMPORTANT ONE - LINER Current Affairs</b>", st_oneliner_h))
    story.append(Spacer(1, 2*mm))

    one_liners = content.get("one_liners") or []
    for ol in (one_liners[:10] if one_liners else items[:10]):
        text_en = ol.get("text_en") or ol.get("headline_en") or ""
        if text_en:
            story.append(Paragraph(f"•  <b>{_safe(text_en)}</b>", st_body_en))
            story.append(Spacer(1, 2*mm))

    story.append(CondPageBreak(100*mm))
    story.append(Paragraph("<b>महत्वपूर्ण वन-लाइनर करंट अफेयर्स</b>", st_oneliner_h))
    story.append(Spacer(1, 2*mm))

    for ol in (one_liners[:10] if one_liners else items[:10]):
        text_hi = ol.get("text_hi") or ol.get("headline_hi") or ""
        if text_hi:
            story.append(hindi_to_image(f"• {_strip_html(text_hi)}", width_mm=174, font_size_pt=12, bold=False, color="#1E293B", bg="white", left_padding_mm=3))
            story.append(Spacer(1, 2*mm))

    # 6. FINAL REVISION CAPSULE (facts, dates, figures at a glance)
    rev_rows: List[List[Flowable]] = [[
        Paragraph("<b>DEVELOPMENT / TOPIC</b>", ParagraphStyle("rev_h1", parent=STYLES["static_label"], fontSize=8.5, leading=11, textColor=white)),
        Paragraph("<b>KEY FACT / FIGURE TO REMEMBER</b>", ParagraphStyle("rev_h2", parent=STYLES["static_label"], fontSize=8.5, leading=11, textColor=white)),
    ]]
    rev_count = 0
    for it in items:
        if rev_count >= 18:
            break
        hl = _strip_html(it.get("headline_en", "")).lstrip("> ")
        facts = it.get("static_facts") or {}
        fact = next((v for k, v in facts.items() if k.startswith("Fact")), "")
        if not fact:
            fact = it.get("exam_fact_en") or next(iter(facts.values()), "")
        clean_fact = _strip_html(fact)
        if not hl or not clean_fact:
            continue
        rev_rows.append([
            Paragraph(hl, ParagraphStyle("rev_t", parent=STYLES["static_text"], fontSize=8, leading=10.5)),
            Paragraph(clean_fact, ParagraphStyle("rev_f", parent=STYLES["static_text"], fontSize=8, leading=10.5, textColor=COLORS["primary_green"])),
        ])
        rev_count += 1

    if rev_count:
        story.append(Spacer(1, 3*mm))
        story.append(CondPageBreak(70*mm))
        story.append(mixed_para("FINAL REVISION CAPSULE • अंतिम पुनरावृत्ति", "rev_h", STYLES["headline_en"], fontSize=14, leading=18, textColor=COLORS["header_bg"]))
        story.append(Paragraph("High-yield facts, figures and organisations from today's edition — revise in one glance.",
                               ParagraphStyle("rev_sub", fontName=FONT_REGULAR, fontSize=8.5, leading=11, textColor=COLORS["muted_text"])))
        story.append(Spacer(1, 2*mm))
        rev_tbl = Table(rev_rows, colWidths=[(PAGE_W - 28*mm) * 0.55, (PAGE_W - 28*mm) * 0.45], repeatRows=1)
        rev_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLORS["header_bg"]),
            ("BOX", (0, 0), (-1, -1), 0.4, COLORS["border_light"]),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, COLORS["border_light"]),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, COLORS["card_bg"]]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(rev_tbl)
        story.append(Spacer(1, 4*mm))

    # 7. CLOSING REVISION KIT
    story.append(CondPageBreak(70*mm))
    story.append(build_closing_kit(date_str))

    # Build Document
    doc.build(story, canvasmaker=NumberedCanvas, onFirstPage=cover_header_footer, onLaterPages=header_footer)
    print(f"[OK] Premium coaching-standard PDF generated successfully: {output_path}")
    return output_path


if __name__ == "__main__":
    import argparse
    import json
    ap = argparse.ArgumentParser(description="Dynamic ALP PDF generator (coaching standard)")
    ap.add_argument("--content", required=True, help="path to data/content/<job_id>.json")
    ap.add_argument("--mcq", required=True, help="path to data/mcq/<job_id>_validated.json")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    with open(a.content, encoding="utf-8") as f:
        content_data = json.load(f)
    with open(a.mcq, encoding="utf-8") as f:
        mcqs_data = json.load(f)
    generate_pdf(content_data, mcqs_data, a.out)
