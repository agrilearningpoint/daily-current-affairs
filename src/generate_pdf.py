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
    PageBreak, KeepTogether, HRFlowable, Image
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


# --- COLOR TOKENS (Premium Coaching Palette) ---
COLORS = {
    "primary_navy": HexColor("#0A2540"),       # Executive Deep Navy
    "secondary_navy": HexColor("#1E3A8A"),     # Royal Navy
    "primary_green": HexColor("#1B5E20"),      # Deep Forest Agriculture Green
    "light_green": HexColor("#E8F5E9"),        # Subtle Mint Tint
    "agri_accent": HexColor("#2E7D32"),        # Vibrant Leaf Green
    "banking_blue": HexColor("#0D47A1"),       # Deep Banking Blue
    "banking_light": HexColor("#E3F2FD"),      # Banking Light
    "national_orange": HexColor("#C2410C"),     # Rust Orange
    "national_light": HexColor("#FFF7ED"),
    "economy_teal": HexColor("#0F766E"),       # Deep Teal
    "economy_light": HexColor("#F0FDFA"),
    "science_cyan": HexColor("#0369A1"),       # Science Sky
    "science_light": HexColor("#F0F9FF"),
    "environment_green": HexColor("#15803D"),
    "environment_light": HexColor("#F0FDF4"),
    "sports_red": HexColor("#B91C1C"),
    "sports_light": HexColor("#FEF2F2"),
    "alert_gold": HexColor("#D97706"),         # Amber Alert
    "alert_light": HexColor("#FEF3C7"),        # Light Amber Box
    "dark_text": HexColor("#0F172A"),          # High Contrast Slate Dark
    "body_text": HexColor("#334155"),          # Softer Dark Slate
    "muted_text": HexColor("#64748B"),         # Cool Gray
    "border_light": HexColor("#E2E8F0"),       # Clean Thin Border
    "card_bg": HexColor("#F8FAFC"),            # Soft Card Background
    "header_bg": HexColor("#0A2540"),          # Header Dark Navy
    "footer_bg": HexColor("#0A2540"),          # Footer Dark Navy
}

CATEGORY_STYLE = {
    "agriculture": {"color": COLORS["primary_green"], "light": COLORS["light_green"], "label": "AGRICULTURE & ALLIED"},
    "banking": {"color": COLORS["banking_blue"], "light": COLORS["banking_light"], "label": "BANKING & FINANCE"},
    "national": {"color": COLORS["national_orange"], "light": COLORS["national_light"], "label": "NATIONAL AFFAIRS"},
    "international": {"color": HexColor("#6D28D9"), "light": HexColor("#F5F3FF"), "label": "INTERNATIONAL AFFAIRS"},
    "economy": {"color": COLORS["economy_teal"], "light": COLORS["economy_light"], "label": "ECONOMY & SCHEMES"},
    "science": {"color": COLORS["science_cyan"], "light": COLORS["science_light"], "label": "SCIENCE & TECHNOLOGY"},
    "environment": {"color": COLORS["environment_green"], "light": COLORS["environment_light"], "label": "ENVIRONMENT & CLIMATE"},
    "sports": {"color": COLORS["sports_red"], "light": COLORS["sports_light"], "label": "SPORTS"},
    "important_days": {"color": HexColor("#7C3AED"), "light": HexColor("#F5F3FF"), "label": "IMPORTANT DAYS"},
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
        "section_banner": ParagraphStyle("SectionBanner", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=13, leading=16, textColor=white, alignment=TA_LEFT),
        "headline_en": ParagraphStyle("HeadlineEN", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=14, leading=18, textColor=COLORS["dark_text"], alignment=TA_LEFT, spaceAfter=2),
        "headline_hi": ParagraphStyle("HeadlineHI", parent=styles["Normal"], fontName=FONT_HINDI_BOLD, fontSize=13.5, leading=17.5, textColor=COLORS["body_text"], alignment=TA_LEFT, spaceAfter=4),
        "body_en": ParagraphStyle("BodyEN", parent=styles["Normal"], fontName=FONT_REGULAR, fontSize=10, leading=14.5, textColor=COLORS["dark_text"], alignment=TA_LEFT, spaceAfter=2),
        "body_hi": ParagraphStyle("BodyHI", parent=styles["Normal"], fontName=FONT_HINDI, fontSize=10.5, leading=15, textColor=COLORS["body_text"], alignment=TA_LEFT, spaceAfter=2),
        "static_label": ParagraphStyle("StaticLabel", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=8.5, leading=11, textColor=COLORS["primary_navy"], alignment=TA_LEFT),
        "static_text": ParagraphStyle("StaticText", parent=styles["Normal"], fontName=FONT_REGULAR, fontSize=9.5, leading=13, textColor=COLORS["dark_text"], alignment=TA_LEFT),
        "exam_fact": ParagraphStyle("ExamFact", parent=styles["Normal"], fontName=FONT_SEMI, fontSize=9.5, leading=13.5, textColor=HexColor("#92400E"), alignment=TA_LEFT),
        "mcq_q": ParagraphStyle("MCQQ", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=10.5, leading=14.5, textColor=COLORS["dark_text"], alignment=TA_LEFT, spaceAfter=3),
        "mcq_opt": ParagraphStyle("MCQOpt", parent=styles["Normal"], fontName=FONT_REGULAR, fontSize=9.5, leading=13.5, textColor=COLORS["dark_text"], alignment=TA_LEFT, leftIndent=12, spaceAfter=2),
        "mcq_ans": ParagraphStyle("MCQAns", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=9.5, leading=13.5, textColor=white, alignment=TA_LEFT),
        "mcq_exp": ParagraphStyle("MCQExp", parent=styles["Normal"], fontName=FONT_REGULAR, fontSize=9, leading=13, textColor=COLORS["body_text"], alignment=TA_LEFT, spaceAfter=2),
        "one_liner": ParagraphStyle("OneLiner", parent=styles["Normal"], fontName=FONT_REGULAR, fontSize=10, leading=14.5, textColor=COLORS["dark_text"], alignment=TA_LEFT, leftIndent=10, spaceAfter=3),
        "footer": ParagraphStyle("Footer", parent=styles["Normal"], fontName=FONT_REGULAR, fontSize=8, leading=10, textColor=white, alignment=TA_CENTER),
        "header": ParagraphStyle("Header", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=8.5, leading=11, textColor=white, alignment=TA_CENTER),
    }


STYLES = get_styles()


# --- SANITIZATION ---
def _strip_html(text: Any) -> str:
    """Completely strip HTML markup and unescape entities."""
    if not text:
        return ""
    # Strip well-formed tags
    cleaned = re.sub(r"<[^>]+>", " ", str(text))
    # Strip unclosed or broken tags
    cleaned = re.sub(r"<[^>]*", " ", cleaned)
    cleaned = html.unescape(cleaned)
    return " ".join(cleaned.split()).strip()


def _safe(s: Any) -> str:
    """Clean HTML markup and safely escape XML entities for ReportLab paragraphs."""
    cleaned = _strip_html(s)
    return cleaned.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# --- NUMBERED CANVAS (Dynamic "Page X of Y") ---
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
                self.setFont(FONT_REGULAR, 7.5)
                self.setFillColor(white)
                self.drawRightString(PAGE_W - 14*mm, 3.8*mm, f"Page {self._pageNumber} of {num_pages}")
                self.restoreState()
            super().showPage()
        super().save()


# --- HINDI / DEVANAGARI RENDERING ENGINE ---
DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")


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
    """Pure cross-platform OpenType shaping and rasterization via HarfBuzz + FreeType."""
    face = freetype.Face(font_path)
    face.set_char_size(int(font_size_pt * 64), 0, dpi, dpi)

    with open(font_path, "rb") as f:
        font_data = f.read()
    hb_face = hb.Face(hb.Blob(font_data))
    hb_font = hb.Font(hb_face)
    hb_font.scale = (face.size.x_ppem * 64, face.size.y_ppem * 64)

    def shape_runs(txt: str) -> Tuple[List[Any], List[Any]]:
        """Shape mixed text by segmenting into Unicode script runs so Devanagari is always shaped with Deva script."""
        all_infos = []
        all_pos = []
        tokens = re.split(r'([\u0900-\u097F\u200C\u200D]+)', txt)
        for tok in tokens:
            if not tok:
                continue
            is_deva = bool(re.search(r'[\u0900-\u097F]', tok))
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

    line_h_px = int(face.size.height / 64 * line_spacing) if face.size.height else int(font_size_pt * dpi / 72 * line_spacing)
    ascent_px = int(face.size.ascender / 64) if face.size.ascender else int(font_size_pt * dpi / 72)
    height_px = line_h_px * len(lines) + int(6 * dpi / 72)

    img = PILImage.new("RGB", (width_px, height_px), bg_rgb)
    pen_y = ascent_px + int(3 * dpi / 72)

    for line in lines:
        glyph_infos, glyph_positions = shape_runs(line)
        line_w = sum(pos.x_advance for pos in glyph_positions) // 64

        if align == "center":
            pen_x = (width_px - line_w) // 2
        elif align == "right":
            pen_x = width_px - line_w - 6
        else:
            pen_x = int(left_padding_mm * dpi / 25.4) + 2

        for info, pos in zip(glyph_infos, glyph_positions):
            face.load_glyph(info.codepoint, freetype.FT_LOAD_RENDER)
            bitmap = face.glyph.bitmap
            top = face.glyph.bitmap_top
            left = face.glyph.bitmap_left

            bx = pen_x + (pos.x_offset // 64) + left
            by = pen_y - (pos.y_offset // 64) - top

            if bitmap.width > 0 and bitmap.rows > 0:
                glyph_mask = PILImage.frombytes("L", (bitmap.width, bitmap.rows), bytes(bitmap.buffer))
                color_patch = PILImage.new("RGB", (bitmap.width, bitmap.rows), color_rgb)
                img.paste(color_patch, (bx, by), glyph_mask)

            pen_x += pos.x_advance // 64
        pen_y += line_h_px

    return img, lines, width_px, height_px


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
    """Render using Pillow RAQM layout engine when available in environment."""
    font_size_px = int(font_size_pt * dpi / 72 * 1.05)
    font = ImageFont.truetype(font_path, font_size_px, layout_engine=ImageFont.Layout.RAQM)

    dummy = PILImage.new("RGB", (width_px, 100), bg_rgb)
    draw_dummy = ImageDraw.Draw(dummy)

    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = current + " " + word if current else word
        w = draw_dummy.textlength(test, font=font, language="hi", features=["liga", "kern"])
        if w <= avail_w_px:
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

    line_h_px = int(font_size_px * line_spacing)
    height_px = line_h_px * len(lines) + 8
    img = PILImage.new("RGB", (width_px, height_px), bg_rgb)
    draw = ImageDraw.Draw(img)
    y = 4

    for line in lines:
        line_w = draw.textlength(line, font=font, language="hi", features=["liga"])
        if align == "center":
            x = (width_px - line_w) // 2
        elif align == "right":
            x = width_px - line_w - 6
        else:
            x = int(left_padding_mm * dpi / 25.4) + 2
        draw.text((x, y), line, font=font, fill=color_rgb, language="hi", features=["liga", "kern"])
        y += line_h_px

    return img, lines, width_px, height_px


def hindi_to_image(
    text: str,
    width_mm: float = 182,
    font_size_pt: float = 10,
    bold: bool = False,
    color: str = "#0F172A",
    bg: str = "white",
    line_spacing: float = 1.35,
    align: str = "left",
    left_padding_mm: float = 0,
) -> _HindiTextFlowable:
    """Render Hindi text with flawless OpenType Devanagari shaping."""
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

    # Prioritize HarfBuzz + FreeType with script-run tokenization for perfect Devanagari shaping
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
        # Fallback for dev only
        font = ImageFont.truetype(font_path, int(font_size_pt * dpi / 72))
        img = PILImage.new("RGB", (width_px, int(font_size_pt * 2 * dpi / 72)), bg_rgb)
        lines = [clean_text]
        w_px, h_px = img.size

    h_hash = hashlib.md5((clean_text + f"{font_size_pt}_{bold}_{color_rgb}_{bg_rgb}_{width_mm}").encode("utf-8")).hexdigest()[:10]
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
    """Route text containing Devanagari glyphs through the shaping engine."""
    clean_text = _strip_html(text)
    st = ParagraphStyle(style_name, parent=base_style, **kw)
    if DEVANAGARI_RE.search(clean_text):
        bold = ("Bold" in st.fontName or "SemiBold" in st.fontName or "Bold" in base_style.fontName)
        width_mm = kw.pop("width_mm", None)
        bg = kw.pop("bg", "white")
        if width_mm is None:
            width_mm = 182
        color_hex = "#0F172A"
        tc = getattr(st, "textColor", None)
        if tc is not None:
            if hasattr(tc, "red") and hasattr(tc, "green") and hasattr(tc, "blue"):
                r = int(round(tc.red * 255))
                g = int(round(tc.green * 255))
                b = int(round(tc.blue * 255))
                color_hex = f"#{r:02x}{g:02x}{b:02x}"
            elif hasattr(tc, "hexval"):
                hv = tc.hexval()
                if isinstance(hv, int):
                    color_hex = f"#{hv:06x}"[-7:]
                else:
                    s = str(hv).lower()
                    if s.startswith("0x"):
                        color_hex = "#" + s[2:]
                    elif not s.startswith("#"):
                        color_hex = "#" + s
                    else:
                        color_hex = s
        align = {TA_CENTER: "center", TA_RIGHT: "right"}.get(st.alignment, "left")
        return hindi_to_image(
            clean_text,
            width_mm=width_mm,
            font_size_pt=st.fontSize,
            bold=bold,
            color=color_hex,
            bg=bg,
            align=align,
        )
    return Paragraph(_safe(clean_text), st)


# --- HEADER / FOOTER CANVAS DECORATOR ---
def header_footer(canvas_obj: canvas.Canvas, doc: Any) -> None:
    canvas_obj.saveState()
    page_num = canvas_obj.getPageNumber()

    # --- TOP HEADER BAR ---
    canvas_obj.setFillColor(COLORS["header_bg"])
    canvas_obj.rect(0, PAGE_H - 17*mm, PAGE_W, 17*mm, fill=1, stroke=0)

    # Accent thin strip below header
    canvas_obj.setFillColor(COLORS["primary_green"])
    canvas_obj.rect(0, PAGE_H - 18.2*mm, PAGE_W, 1.2*mm, fill=1, stroke=0)

    # Top Brand + Exam Text
    canvas_obj.setFillColor(white)
    canvas_obj.setFont(FONT_BOLD, 8.5)
    canvas_obj.drawString(14*mm, PAGE_H - 8*mm, "AGRI LEARNING POINT")
    canvas_obj.drawCentredString(PAGE_W / 2, PAGE_H - 8*mm, "DAILY CURRENT AFFAIRS  |  BY SATYAM SIR")
    canvas_obj.drawRightString(PAGE_W - 14*mm, PAGE_H - 8*mm, "BILINGUAL STUDY MATERIAL")

    canvas_obj.setFont(FONT_REGULAR, 6.5)
    canvas_obj.setFillColor(HexColor("#94A3B8"))
    canvas_obj.drawString(14*mm, PAGE_H - 13*mm, "Target: AGTA • AFO • ICAR • NABARD • FCI • IBPS • State Agriculture Exams")
    canvas_obj.drawRightString(PAGE_W - 14*mm, PAGE_H - 13*mm, "Daily • Weekly • Monthly Series")

    # --- BOTTOM FOOTER BAR ---
    canvas_obj.setFillColor(COLORS["footer_bg"])
    canvas_obj.rect(0, 0, PAGE_W, 9.5*mm, fill=1, stroke=0)

    # Accent thin strip above footer
    canvas_obj.setFillColor(COLORS["alert_gold"])
    canvas_obj.rect(0, 9.5*mm, PAGE_W, 0.8*mm, fill=1, stroke=0)

    # Left Brand string
    canvas_obj.setFillColor(white)
    canvas_obj.setFont(FONT_REGULAR, 7)
    canvas_obj.drawString(14*mm, 3.8*mm, "Agri Learning Point  |  By Satyam Sir")

    # Center Telegram links (Red Plane + Bright Cyan Clickable Channels)
    ch1_name = "@agrilearningpoint"
    ch2_name = "@agriquizworld"
    ch1_url = "https://web.telegram.org/k/#@agrilearningpoint"
    ch2_url = "https://web.telegram.org/k/#@agriquizworld"
    RED_ICON = HexColor("#EF4444")
    CYAN_TG = HexColor("#7DD3FC")
    icon_sz = 3.0*mm
    link_y = 2.6*mm

    w1 = stringWidth(ch1_name, FONT_REGULAR, 7)
    w2 = stringWidth(ch2_name, FONT_REGULAR, 7)
    gap = 6*mm
    total_w = (icon_sz + 1*mm + w1) + gap + (icon_sz + 1*mm + w2)
    cx = PAGE_W / 2
    x_start = cx - total_w / 2

    x1_icon = x_start
    x1_text = x1_icon + icon_sz + 1*mm
    x2_icon = x1_text + w1 + gap
    x2_text = x2_icon + icon_sz + 1*mm

    def draw_tg_icon(x: float, y: float):
        canvas_obj.saveState()
        canvas_obj.setFillColor(RED_ICON)
        canvas_obj.circle(x + icon_sz / 2, y + icon_sz / 2 + 0.2*mm, icon_sz / 2, stroke=0, fill=1)
        canvas_obj.setFillColor(white)
        p = canvas_obj.beginPath()
        p.moveTo(x + 0.7*mm, y + 0.85*mm)
        p.lineTo(x + 2.4*mm, y + 1.55*mm)
        p.lineTo(x + 0.7*mm, y + 2.35*mm)
        p.lineTo(x + 1.1*mm, y + 1.55*mm)
        p.close()
        canvas_obj.drawPath(p, stroke=0, fill=1)
        canvas_obj.restoreState()

    draw_tg_icon(x1_icon, link_y)
    draw_tg_icon(x2_icon, link_y)

    canvas_obj.setFillColor(CYAN_TG)
    canvas_obj.setFont(FONT_REGULAR, 7)
    canvas_obj.drawString(x1_text, link_y + 0.6*mm, ch1_name)
    canvas_obj.drawString(x2_text, link_y + 0.6*mm, ch2_name)

    canvas_obj.linkURL(ch1_url, (x1_icon - 0.5*mm, link_y - 0.5*mm, x1_text + w1 + 0.5*mm, link_y + 4*mm), relative=0)
    canvas_obj.linkURL(ch2_url, (x2_icon - 0.5*mm, link_y - 0.5*mm, x2_text + w2 + 0.5*mm, link_y + 4*mm), relative=0)

    # --- WATERMARK (Subtle Faded Center Logo) ---
    try:
        watermark_path = os.path.join(BASE_DIR, "assets", "watermark_logo.png")
        if not os.path.exists(watermark_path):
            watermark_path = os.path.join(BASE_DIR, "assets", "logo.png")
        if os.path.exists(watermark_path):
            canvas_obj.saveState()
            canvas_obj.setFillAlpha(0.04)
            wm_size = 90*mm
            wm_x = (PAGE_W - wm_size) / 2
            wm_y = (PAGE_H - wm_size) / 2
            canvas_obj.drawImage(watermark_path, wm_x, wm_y, width=wm_size, height=wm_size, preserveAspectRatio=True, mask="auto")
            canvas_obj.restoreState()
    except Exception:
        pass

    canvas_obj.restoreState()


def cover_header_footer(canvas_obj: canvas.Canvas, doc: Any) -> None:
    """Clean cover background with subtle watermark."""
    canvas_obj.saveState()
    try:
        watermark_path = os.path.join(BASE_DIR, "assets", "watermark_logo.png")
        if not os.path.exists(watermark_path):
            watermark_path = os.path.join(BASE_DIR, "assets", "logo.png")
        if os.path.exists(watermark_path):
            canvas_obj.saveState()
            canvas_obj.setFillAlpha(0.04)
            wm_size = 110*mm
            wm_x = (PAGE_W - wm_size) / 2
            wm_y = (PAGE_H - wm_size) / 2
            canvas_obj.drawImage(watermark_path, wm_x, wm_y, width=wm_size, height=wm_size, preserveAspectRatio=True, mask="auto")
            canvas_obj.restoreState()
    except Exception:
        pass
    canvas_obj.restoreState()


# --- REUSABLE EDITORIAL COMPONENTS ---
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
    content.append(mixed_para("▶ EXAM POINTER • परीक्षा तथ्य", "efh", STYLES["exam_fact"], fontSize=9, leading=12, textColor=HexColor("#B45309"), bg="#FEF3C7", width_mm=174))
    if text_en:
        content.append(mixed_para(text_en, "ef_en", STYLES["exam_fact"], bg="#FEF3C7", width_mm=174))
    if text_hi:
        content.append(mixed_para(text_hi, "ef_hi", STYLES["exam_fact"], bg="#FEF3C7", width_mm=174))

    inner = Table([[content]], colWidths=[PAGE_W - 32*mm])
    inner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLORS["alert_light"]),
        ("BOX", (0, 0), (-1, -1), 0.6, COLORS["alert_gold"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROUNDEDCORNERS", [3, 3, 3, 3]),
    ]))
    return inner


def static_facts_table(facts_dict: Dict[str, str]) -> List[Flowable]:
    rows: List[List[Flowable]] = []
    for k, v in facts_dict.items():
        clean_k = _strip_html(k)
        clean_v = _strip_html(v)
        rows.append([
            mixed_para(clean_k, "sf_k", STYLES["static_label"], width_mm=30),
            mixed_para(clean_v, "sf_v", STYLES["static_text"], width_mm=(PAGE_W/mm - 28 - 32)),
        ])
    t = Table(rows, colWidths=[32*mm, PAGE_W - 28*mm - 32*mm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("GRID", (0, 0), (-1, -1), 0.3, COLORS["border_light"]),
        ("BACKGROUND", (0, 0), (0, -1), COLORS["card_bg"]),
        ("BACKGROUND", (1, 0), (1, -1), white),
    ]))
    header = mixed_para("STATIC GK & FACTS • परीक्षा स्थैतिक तथ्य", "sfh", STYLES["static_text"], fontSize=8.5, leading=11, textColor=COLORS["primary_navy"])
    return [header, t]


def news_card(
    headline_en: str,
    headline_hi: str,
    category_key: str,
    key_points_en: List[str],
    key_points_hi: List[str],
    static_facts: Dict[str, str],
    exam_fact_en: str,
    exam_fact_hi: str,
    source_name: str,
    image_path: Optional[str] = None,
    image_caption: Optional[str] = None,
) -> List[Flowable]:
    cat = CATEGORY_STYLE.get(category_key, CATEGORY_STYLE["national"])
    story: List[Flowable] = []

    # Headline block: Category tag + English + Hindi
    clean_en = _safe(headline_en).lstrip("> ")
    clean_hi = _strip_html(headline_hi).lstrip("> ")

    hl_en = Paragraph(f"<b>{clean_en}</b>", STYLES["headline_en"])
    hl_hi = hindi_to_image(clean_hi, width_mm=174, font_size_pt=13.5, bold=True, color="#334155", bg="white")

    header_block = Table([
        [Paragraph(f'<font color="{cat["color"].hexval()}">▌</font>', ParagraphStyle("bar", parent=STYLES["headline_en"], fontSize=18, leading=18, textColor=cat["color"])),
         [hl_en, hl_hi]]
    ], colWidths=[3.5*mm, PAGE_W - 28*mm - 3.5*mm])
    header_block.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 1),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))

    story.append(header_block)
    story.append(Spacer(1, 1.5*mm))

    # Real editorial image if available
    if image_path and os.path.exists(image_path):
        try:
            pil = PILImage.open(image_path)
            iw, ih = pil.size
            aspect = ih / iw if iw else 0.55
            max_h_mm = 50
            w_mm = PAGE_W / mm - 28
            h_mm = w_mm * aspect
            if h_mm > max_h_mm:
                h_mm = max_h_mm
                w_mm = h_mm / aspect if aspect else w_mm
            rl_img = Image(image_path, width=w_mm*mm, height=h_mm*mm)
            img_table = Table([[rl_img]], colWidths=[PAGE_W - 28*mm])
            img_table.setStyle(TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOX", (0, 0), (-1, -1), 0.3, COLORS["border_light"]),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]))
            story.append(img_table)
            if image_caption:
                story.append(Paragraph(f'<font color="#64748B" size="7.5"><i>{_safe(image_caption)}</i></font>', ParagraphStyle("cap", parent=STYLES["static_text"], alignment=TA_CENTER, fontSize=7.5, leading=10, spaceBefore=1)))
            story.append(Spacer(1, 1.5*mm))
        except Exception:
            pass

    # Key Points Header
    story.append(mixed_para(
        "Key Points  •  मुख्य बिंदु",
        "kph",
        STYLES["body_en"],
        fontSize=10.5,
        leading=14,
        textColor=COLORS["primary_navy"],
        fontName="Helvetica-Bold",
        width_mm=178,
    ))
    story.append(Spacer(1, 1*mm))

    # Paired Key Points
    for en, hi in zip(key_points_en, key_points_hi):
        c_en = _safe(en)
        c_hi = _strip_html(hi)
        if not c_en:
            continue
        story.append(Paragraph(f"•  {c_en}", STYLES["body_en"]))
        if c_hi:
            story.append(hindi_to_image(c_hi, width_mm=178, font_size_pt=10, bold=False, color="#475569", bg="white", left_padding_mm=3.5))
        story.append(Spacer(1, 0.8*mm))

    story.append(Spacer(1, 1.5*mm))

    # Static Facts
    if static_facts:
        for item in static_facts_table(static_facts):
            story.append(item)
        story.append(Spacer(1, 1.5*mm))

    # Exam Fact Box
    if exam_fact_en:
        story.append(exam_fact_box(exam_fact_en, exam_fact_hi))
        story.append(Spacer(1, 1.5*mm))

    # Source line
    if source_name:
        story.append(Paragraph(f'<font color="#64748B" size="7.5">Source: <b>{_safe(source_name)}</b> | Verified for Competitive Exams</font>', ParagraphStyle("src", parent=STYLES["static_text"], fontSize=7.5, leading=10, alignment=TA_RIGHT)))

    story.append(Spacer(1, 2*mm))
    story.append(HRFlowable(width="100%", thickness=0.4, color=COLORS["border_light"], spaceAfter=3*mm, spaceBefore=1*mm))
    return story


def mcq_block(
    q_num: int,
    question_en: str,
    question_hi: str,
    options_en: List[str],
    correct: str,
    explanation_en: str,
    explanation_hi: str,
    exam_point: str,
) -> Flowable:
    """Pack an entire MCQ into a KeepTogether block so it NEVER orphans across page boundaries."""
    story: List[Flowable] = []

    clean_q_en = _safe(question_en)
    clean_q_hi = _strip_html(question_hi)

    q_title_en = Paragraph(f"<b>Q{q_num}.  {clean_q_en}</b>", STYLES["mcq_q"])
    story.append(q_title_en)
    if clean_q_hi:
        story.append(hindi_to_image(clean_q_hi, width_mm=182, font_size_pt=10.5, bold=False, color="#334155", bg="white"))
    story.append(Spacer(1, 1.2*mm))

    for idx, opt in enumerate(options_en):
        clean_opt = _safe(opt)
        label = chr(65 + idx)
        story.append(Paragraph(f"<b>({label})</b>  {clean_opt}", STYLES["mcq_opt"]))
    story.append(Spacer(1, 1.5*mm))

    # Correct Answer Box
    correct_idx = ord(correct.upper()) - 65 if correct else 0
    correct_text = _safe(options_en[correct_idx]) if 0 <= correct_idx < len(options_en) else ""
    ans_text = f"✔  Correct Answer: ({correct}) {correct_text}"
    ans_data = [[Paragraph(f"<b>{ans_text}</b>", STYLES["mcq_ans"])]]
    ans_table = Table(ans_data, colWidths=[PAGE_W - 28*mm])
    ans_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLORS["primary_green"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROUNDEDCORNERS", [3, 3, 3, 3]),
    ]))
    story.append(ans_table)
    story.append(Spacer(1, 1.2*mm))

    # Explanation
    clean_exp_en = _safe(explanation_en)
    clean_exp_hi = _strip_html(explanation_hi)
    story.append(Paragraph('<b><font color="#0A2540" size="8.5">▶ Detailed Explanation:</font></b>', ParagraphStyle("exph", parent=STYLES["mcq_exp"], fontSize=8.5, leading=11, textColor=COLORS["primary_navy"])))
    if clean_exp_en:
        story.append(Paragraph(clean_exp_en, STYLES["mcq_exp"]))
    if clean_exp_hi:
        story.append(hindi_to_image(clean_exp_hi, width_mm=182, font_size_pt=9.5, bold=False, color="#475569", bg="white"))

    if exam_point:
        clean_ep = _safe(exam_point)
        story.append(Paragraph(f'<b><font color="#D97706" size="8.5">▶ Exam Takeaway:</font></b> <font size="8.5">{clean_ep}</font>', ParagraphStyle("ep", parent=STYLES["mcq_exp"], fontSize=8.5, leading=11)))

    story.append(Spacer(1, 1.5*mm))
    story.append(HRFlowable(width="100%", thickness=0.3, color=COLORS["border_light"], spaceAfter=2*mm, spaceBefore=1*mm))

    return KeepTogether(story)


# --- CLOSING PREPARATION KIT (Replaces Empty Blank Last Page) ---
def build_closing_kit(date_str: str) -> Flowable:
    """Builds a rich coaching revision kit at the end of the document."""
    items: List[Flowable] = []
    items.append(Paragraph("<b>AGRI LEARNING POINT — COMPLETE EXAM SUCCESS SUITE</b>", ParagraphStyle("ck_title", fontName=FONT_BOLD, fontSize=12, leading=15, textColor=COLORS["primary_navy"], alignment=TA_CENTER)))
    items.append(Paragraph("Target: AGTA • AFO • ICAR JRF/SRF • NABARD Grade A • FCI • IBPS SO", ParagraphStyle("ck_sub", fontName=FONT_SEMI, fontSize=8.5, leading=11, textColor=COLORS["primary_green"], alignment=TA_CENTER)))
    items.append(Spacer(1, 2*mm))

    # 3 Column features
    row = [
        [
            Paragraph("<b>📌 Daily Current Affairs</b><br/><font size='7' color='#475569'>Every morning bilingual PDF with exam facts &amp; MCQs.</font>", STYLES["static_text"]),
            Paragraph("<b>📝 Daily Telegram Quizzes</b><br/><font size='7' color='#475569'>Timed quizzes on @agriquizworld for real exam practice.</font>", STYLES["static_text"]),
            Paragraph("<b>🎯 Agriculture Revision</b><br/><font size='7' color='#475569'>Agronomy, Horticulture, Soil Science &amp; Schemes notes.</font>", STYLES["static_text"]),
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
    items.append(hindi_to_image(msg_hi, width_mm=174, font_size_pt=11, bold=True, color="#0A2540", bg="white", align="center"))
    items.append(Paragraph(f"© 2026 Agri Learning Point | Edition {date_str} | For Educational &amp; Competitive Exam Use Only", ParagraphStyle("discl", fontName=FONT_REGULAR, fontSize=6.5, leading=8, textColor=COLORS["muted_text"], alignment=TA_CENTER)))

    box = Table([[items]], colWidths=[PAGE_W - 28*mm])
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), white),
        ("BOX", (0, 0), (-1, -1), 0.8, COLORS["primary_navy"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    return KeepTogether([box])


# --- MAIN PDF GENERATION ENGINE ---
def generate_pdf(content: Dict[str, Any], mcqs: List[Dict[str, Any]], output_path: Optional[str] = None) -> str:
    """Build the premium bilingual edition from pipeline JSON data.
    Enforces publication quality gates, zero orphan questions, and clean page flow."""
    raw_items = content.get("items", [])
    # Filter out empty or broken headlines
    items = [
        it for it in raw_items
        if len(_strip_html(it.get("headline_en", "")).lstrip("> ")) >= 15
        and len(_strip_html(it.get("headline_en", "")).lstrip("> ").split()) >= 3
    ]
    if not items:
        # If strict filtering dropped everything, check if original items exist
        items = raw_items
    if not items:
        raise ValueError("REFUSING to build PDF: 0 selected news items (quality gate, never fill/invent)")

    job = content.get("job", {})
    date_str = job.get("date_display", "") or job.get("date", "")
    jtype = job.get("type", "daily")
    label = {
        "daily": "Daily Current Affairs",
        "weekly": "Weekly Best-of Current Affairs",
        "monthly": "Monthly Best-of Current Affairs",
    }.get(jtype, "Current Affairs")

    if output_path is None:
        output_path = os.path.join(OUTPUT_DIR, f"Agri Learning Point {date_str} {label} Mobile Bilingual FINAL.pdf")

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=14*mm,
        rightMargin=14*mm,
        topMargin=22*mm,
        bottomMargin=14*mm,
        title=f"Agri Learning Point - {label} - {date_str}",
        author="Agri Learning Point (Satyam Sir)",
    )

    story: List[Flowable] = []

    # =========================================================================
    # 1. COVER PAGE (Page 1 - Compact, balanced, executive coaching standard)
    # =========================================================================
    logo_path = os.path.join(BASE_DIR, "assets", "logo.png")
    if os.path.exists(logo_path):
        try:
            story.append(Image(logo_path, width=28*mm, height=28*mm))
        except Exception:
            pass
    story.append(Spacer(1, 2*mm))

    story.append(Paragraph("AGRI LEARNING POINT", STYLES["cover_masthead"]))
    story.append(Paragraph(f"{label}  •  {date_str}", STYLES["cover_sub"]))
    story.append(Spacer(1, 1.5*mm))

    # Target exam pills
    pill_text = "TARGET EXAMS:  AGTA  •  AFO  •  ICAR JRF/SRF  •  NABARD  •  FCI  •  IBPS SO  •  STATE EXAMS"
    t_pill = Table([[Paragraph(f"<b>{pill_text}</b>", STYLES["cover_pill"])]], colWidths=[PAGE_W - 28*mm])
    t_pill.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLORS["light_green"]),
        ("BOX", (0, 0), (-1, -1), 0.5, COLORS["primary_green"]),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROUNDEDCORNERS", [3, 3, 3, 3]),
    ]))
    story.append(t_pill)
    story.append(Spacer(1, 1.5*mm))

    story.append(Paragraph("Bilingual (Hindi + English)  |  100% Verified Sources  |  Exam-Oriented Static GK  |  By Satyam Sir", STYLES["cover_tag"]))
    story.append(Spacer(1, 3.5*mm))

    # Today's Highlights Box (Well-proportioned, clean headlines without mid-word cuts)
    top_items = sorted(items, key=lambda x: -x.get("importance_score", 0))
    hl_rows: List[List[Flowable]] = [
        [
            mixed_para("TODAY’S EXAM HEADLINES • आज के प्रमुख समाचार", "hl_top", STYLES["static_label"], fontSize=9.5, leading=12, textColor=white, bg="#0A2540", width_mm=(PAGE_W/mm - 28 - 38)),
            Paragraph('<b><font color="white" size="8.5">CATEGORY</font></b>', ParagraphStyle("hl_cat_h", parent=STYLES["static_label"], fontSize=8.5, leading=11, alignment=TA_CENTER)),
        ]
    ]

    for it in top_items[:7]:
        clean_hl = _strip_html(it.get("headline_en", "")).lstrip("> ")
        cat_key = CAT_MAP.get(it.get("category", "National"), "national")
        cat_info = CATEGORY_STYLE.get(cat_key, CATEGORY_STYLE["national"])
        hl_rows.append([
            Paragraph(f"•  <b>{clean_hl}</b>", ParagraphStyle("hl_item", parent=STYLES["static_text"], fontSize=8.5, leading=11.5)),
            Paragraph(f'<font size="7" color="{cat_info["color"].hexval()}"><b>{cat_info["label"]}</b></font>', ParagraphStyle("hl_cat", parent=STYLES["static_text"], fontSize=7, leading=9, alignment=TA_CENTER)),
        ])

    t_hl = Table(hl_rows, colWidths=[PAGE_W - 28*mm - 38*mm, 38*mm])
    t_hl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLORS["primary_navy"]),
        ("BOX", (0, 0), (-1, -1), 0.8, COLORS["primary_navy"]),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, COLORS["border_light"]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t_hl)
    story.append(Spacer(1, 3*mm))

    # Quick Stats & Community Bar
    stats_data = [
        [
            Paragraph(f"<b>📌 Selected Stories:</b> {len(items)}", STYLES["static_text"]),
            Paragraph(f"<b>📝 Practice MCQs:</b> {len(mcqs)}", STYLES["static_text"]),
            Paragraph("<b>⚡ Static GK:</b> Included", STYLES["static_text"]),
            Paragraph("<b>✈ Telegram:</b> @agrilearningpoint", STYLES["static_text"]),
        ]
    ]
    t_stats = Table(stats_data, colWidths=[42*mm, 42*mm, 40*mm, 50*mm])
    t_stats.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLORS["card_bg"]),
        ("BOX", (0, 0), (-1, -1), 0.4, COLORS["border_light"]),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROUNDEDCORNERS", [3, 3, 3, 3]),
    ]))
    story.append(t_stats)
    story.append(Spacer(1, 3*mm))

    # Coaching Institute Exam Guide Box (Fills lower cover page with real exam value)
    guide_rows = [
        [
            Paragraph("<b>🎯 EXAM RELEVANCE &amp; SYLLABUS ALIGNMENT</b>", ParagraphStyle("gr_h", fontName=FONT_BOLD, fontSize=8.5, leading=11, textColor=COLORS["primary_navy"])),
            Paragraph("<b>DAILY STUDY MANDATE</b>", ParagraphStyle("gr_m", fontName=FONT_BOLD, fontSize=8.5, leading=11, textColor=COLORS["primary_green"], alignment=TA_RIGHT)),
        ],
        [
            Paragraph(
                "• <b>Agriculture Exams (AGTA / AFO / ICAR):</b> Focus on crop yield estimates, new ICAR varieties, MSP notifications, fertilizer subsidies, and Ministry of Agriculture initiatives.<br/>"
                "• <b>Banking &amp; Regulatory (NABARD / RBI / IBPS):</b> Special emphasis on PSL targets, rural infrastructure funding (RIDF), priority credit schemes, and quarterly monetary policies.<br/>"
                "• <b>General Competitive (FCI / UPSC / State PCS):</b> Static facts, organizational headquarters, national policies, bilateral agreements, and indices.",
                ParagraphStyle("gr_body", fontName=FONT_REGULAR, fontSize=7, leading=9.5, textColor=COLORS["body_text"])
            ),
            Paragraph(
                "<b>1. Read Daily:</b> Go through paired English-Hindi pointers.<br/>"
                "<b>2. Memorize:</b> Revise static facts and numbers.<br/>"
                "<b>3. Solve MCQs:</b> Attempt the 15 exam-standard practice questions.<br/>"
                "<b>4. Telegram Quiz:</b> Join 9:00 PM live quiz on @agriquizworld.",
                ParagraphStyle("gr_steps", fontName=FONT_REGULAR, fontSize=7, leading=9.5, textColor=COLORS["dark_text"])
            )
        ]
    ]
    t_guide = Table(guide_rows, colWidths=[114*mm, 68*mm])
    t_guide.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), white),
        ("BOX", (0, 0), (-1, -1), 0.6, COLORS["primary_navy"]),
        ("LINEBELOW", (0, 0), (-1, 0), 0.4, COLORS["border_light"]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROUNDEDCORNERS", [3, 3, 3, 3]),
    ]))
    story.append(t_guide)
    story.append(Spacer(1, 2*mm))

    story.append(Paragraph("Study Material Prepared for Daily Revision  |  Agri Learning Point by Satyam Sir", ParagraphStyle("cover_foot", fontName=FONT_REGULAR, fontSize=7, leading=9, textColor=COLORS["muted_text"], alignment=TA_CENTER)))

    # End of cover page
    story.append(PageBreak())

    # =========================================================================
    # 2. FLOWING BODY CONTENT (Index + One-Liners + News)
    # =========================================================================
    # Group news items by category
    by_cat: Dict[str, List[Dict[str, Any]]] = {}
    for it in items:
        ck = CAT_MAP.get(it.get("category", "National"), "national")
        by_cat.setdefault(ck, []).append(it)

    # --- INDEX TABLE ---
    story.append(mixed_para("INDEX • विषय-सूची", "idx_h", STYLES["headline_en"], fontSize=13, leading=16, textColor=COLORS["primary_navy"]))
    story.append(Spacer(1, 1*mm))

    idx_rows: List[List[Flowable]] = [
        [
            Paragraph("<b>#</b>", ParagraphStyle("idx_num_h", parent=STYLES["static_label"], fontSize=8, leading=10, alignment=TA_CENTER)),
            Paragraph("<b>TOPIC / HEADLINE</b>", ParagraphStyle("idx_top_h", parent=STYLES["static_label"], fontSize=8, leading=10)),
            Paragraph("<b>SECTION</b>", ParagraphStyle("idx_sec_h", parent=STYLES["static_label"], fontSize=8, leading=10, alignment=TA_CENTER)),
        ]
    ]
    item_n = 0
    for ck, group in by_cat.items():
        banner_info = CATEGORY_STYLE.get(ck, CATEGORY_STYLE["national"])
        for g in group:
            item_n += 1
            clean_t = _strip_html(g.get("headline_en", "")).lstrip("> ")
            idx_rows.append([
                Paragraph(f"<b>{item_n}</b>", ParagraphStyle("idx_n", parent=STYLES["static_text"], fontSize=8, leading=10, alignment=TA_CENTER)),
                Paragraph(clean_t, ParagraphStyle("idx_t", parent=STYLES["static_text"], fontSize=8, leading=10.5)),
                Paragraph(f'<font size="6.5" color="{banner_info["color"].hexval()}"><b>{banner_info["label"]}</b></font>', ParagraphStyle("idx_s", parent=STYLES["static_text"], fontSize=6.5, leading=8.5, alignment=TA_CENTER)),
            ])

    idx_tbl = Table(idx_rows, colWidths=[8*mm, PAGE_W - 28*mm - 48*mm, 40*mm])
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
    story.append(Spacer(1, 3.5*mm))

    # --- MOST IMPORTANT ONE-LINERS (Directly following index, no blank page!) ---
    story.append(mixed_para("MOST IMPORTANT EXAM POINTERS • मुख्य परीक्षा तथ्य", "mi_h", STYLES["headline_en"], fontSize=13, leading=16, textColor=COLORS["primary_navy"]))
    story.append(Spacer(1, 1*mm))

    for it in top_items[:8]:
        fact = next(iter(it.get("static_facts", {}).values()), "")
        clean_hl = _strip_html(it.get("headline_en", "")).lstrip("> ")
        clean_fact = _strip_html(fact)
        line = f"<b>{clean_hl}</b>" + (f'  →  <font color="#1B5E20">{clean_fact}</font>' if clean_fact else "")
        story.append(Paragraph(f"•  {line}", STYLES["one_liner"]))

    story.append(Spacer(1, 3.5*mm))
    story.append(HRFlowable(width="100%", thickness=0.8, color=COLORS["primary_navy"], spaceAfter=3*mm, spaceBefore=2*mm))

    # --- NEWS SECTIONS ---
    sec_no = 0
    for ck, group in by_cat.items():
        sec_no += 1
        story.append(section_banner(ck, f"{sec_no:02d}"))
        story.append(Spacer(1, 2*mm))

        for it in group:
            blocks = news_card(
                headline_en=it.get("headline_en", ""),
                headline_hi=it.get("headline_hi", ""),
                category_key=ck,
                key_points_en=it.get("key_points_en", []),
                key_points_hi=it.get("key_points_hi", []),
                static_facts=it.get("static_facts", {}),
                exam_fact_en=it.get("exam_fact_en", ""),
                exam_fact_hi=it.get("exam_fact_hi", ""),
                source_name=it.get("source", {}).get("name", ""),
                image_path=it.get("image_path") or None,
                image_caption=it.get("image_caption") or None,
            )
            story.extend(blocks)

    # Clean break before MCQs
    story.append(PageBreak())

    # =========================================================================
    # 3. MCQ PRACTICE SECTION (All blocks KeepTogether to prevent orphans)
    # =========================================================================
    story.append(mixed_para("PRACTICE MCQs • बहुविकल्पीय अभ्यास प्रश्न", "mcq_sec", STYLES["headline_en"], fontSize=14, leading=18, textColor=COLORS["primary_navy"]))
    story.append(Paragraph("Designed for AGTA, AFO, ICAR, NABARD, FCI &amp; IBPS Exam Patterns", ParagraphStyle("mcq_sub", fontName=FONT_REGULAR, fontSize=8, leading=10.5, textColor=COLORS["muted_text"])))
    story.append(Spacer(1, 2*mm))

    for m in mcqs:
        block = mcq_block(
            q_num=m.get("q_num", 1),
            question_en=m.get("question_en", ""),
            question_hi=m.get("question_hi", ""),
            options_en=m.get("options", []),
            correct=m.get("correct", "A"),
            explanation_en=m.get("explanation_en", ""),
            explanation_hi=m.get("explanation_hi", ""),
            exam_point=m.get("exam_point", ""),
        )
        story.append(block)

    # =========================================================================
    # 4. CLOSING REVISION KIT (Replaces 90% Blank Final Page)
    # =========================================================================
    story.append(Spacer(1, 4*mm))
    story.append(build_closing_kit(date_str))

    # Build document with dynamic page numbering
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
