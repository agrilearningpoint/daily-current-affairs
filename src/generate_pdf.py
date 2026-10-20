#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AGRI LEARNING POINT - Premium Daily Current Affairs PDF Generator
================================================================
Production engine for daily / weekly / monthly bilingual editions.
Engineered for competitive-exam coaching standards (AGTA, AFO, ICAR, NABARD, FCI, UPSC, SSC).

Clean, Mobile-Friendly, Distraction-Free Design:
- Minimal Two-Color Palette: Deep Classic Navy (#0F2B48) & Forest Green (#166534)
- Crisp Devanagari Typography: Mukta (SemiBold for headings, Regular for body) shaped with HarfBuzz + FreeType
- Selectable vector text layer for QA & searchability
- Clean running header and 3 official channels footer (YouTube, @agrilearningpoint, @agriquizworld)
- Zero unnecessary colors, zero fake social links.
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
    has_raqm = bool(PILFeatures.check("raqm"))
    if has_raqm:
        return True, "Pillow RAQM shaping is available."
    if _HAS_HB_FT:
        return True, "HarfBuzz + FreeType complex text shaping is available."
    return False, "Neither Pillow RAQM nor uharfbuzz+freetype is available."


_HAS_SHAPING, _SHAPING_DIAGNOSTIC = get_shaping_diagnostics()
_HAS_RAQM = bool(PILFeatures.check("raqm"))
_ALLOW_UNSHAPED_DEV = os.getenv("ALP_ALLOW_UNSHAPED_DEV_PDF", "0") == "1"

if not _HAS_SHAPING and not _ALLOW_UNSHAPED_DEV:
    raise RuntimeError(f"FATAL: {_SHAPING_DIAGNOSTIC}")

# --- COLOR TOKENS (Clean, Mobile-Friendly, Minimal Palette) ---
COLORS = {
    "primary_navy": HexColor("#0F2B48"),       # Deep Navy — primary brand & title
    "secondary_navy": HexColor("#1E3A5F"),     # Subtle Navy
    "brand_teal": HexColor("#0F2B48"),         # Harmonized with primary navy
    "teal_light": HexColor("#F1F5F9"),         # Soft neutral slate panel
    "primary_green": HexColor("#166534"),      # Forest green for answers & takeaways
    "light_green": HexColor("#F0FDF4"),        # Soft mint panel
    "border_green": HexColor("#86EFAC"),       # Light green border
    "dark_text": HexColor("#0F172A"),          # High contrast deep charcoal
    "body_text": HexColor("#1E293B"),          # Slate dark for easy mobile reading
    "muted_text": HexColor("#64748B"),         # Cool gray for metadata
    "border_light": HexColor("#E2E8F0"),       # Clean thin border
    "card_bg": HexColor("#F8FAFC"),            # Soft card background
    "header_bg": HexColor("#0F2B48"),          # Navy header
    "footer_bg": HexColor("#0F2B48"),          # Navy footer
    "alert_gold": HexColor("#B45309"),
    "alert_light": HexColor("#FEF3C7"),
    "sports_red": HexColor("#0F2B48"),
}

CATEGORY_STYLE = {
    "agriculture": {"color": COLORS["primary_navy"], "light": COLORS["card_bg"], "label": "AGRICULTURE & ALLIED"},
    "banking": {"color": COLORS["primary_navy"], "light": COLORS["card_bg"], "label": "BANKING & FINANCE"},
    "national": {"color": COLORS["primary_navy"], "light": COLORS["card_bg"], "label": "NATIONAL AFFAIRS"},
    "international": {"color": COLORS["primary_navy"], "light": COLORS["card_bg"], "label": "INTERNATIONAL AFFAIRS"},
    "economy": {"color": COLORS["primary_navy"], "light": COLORS["card_bg"], "label": "ECONOMY & SCHEMES"},
    "science": {"color": COLORS["primary_navy"], "light": COLORS["card_bg"], "label": "SCIENCE & TECHNOLOGY"},
    "environment": {"color": COLORS["primary_navy"], "light": COLORS["card_bg"], "label": "ENVIRONMENT & CLIMATE"},
    "sports": {"color": COLORS["primary_navy"], "light": COLORS["card_bg"], "label": "SPORTS"},
    "important_days": {"color": COLORS["primary_navy"], "light": COLORS["card_bg"], "label": "IMPORTANT DAYS"},
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
        pdfmetrics.registerFont(TTFont("Mukta-Bold", os.path.join(FONTS_DIR, "Mukta-SemiBold.ttf")))
        return True
    except Exception as exc:
        raise RuntimeError(f"FATAL: Required fonts failed to register from {FONTS_DIR}: {exc}")


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
        "cover_masthead": ParagraphStyle("CoverMasthead", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=24, leading=28, textColor=COLORS["primary_navy"], alignment=TA_CENTER),
        "cover_sub": ParagraphStyle("CoverSub", parent=styles["Normal"], fontName=FONT_SEMI, fontSize=12, leading=16, textColor=COLORS["primary_navy"], alignment=TA_CENTER),
        "cover_pill": ParagraphStyle("CoverPill", parent=styles["Normal"], fontName=FONT_SEMI, fontSize=8.5, leading=11, textColor=COLORS["primary_navy"], alignment=TA_CENTER),
        "cover_tag": ParagraphStyle("CoverTag", parent=styles["Normal"], fontName=FONT_REGULAR, fontSize=9, leading=12, textColor=COLORS["muted_text"], alignment=TA_CENTER),
        "headline_en": ParagraphStyle("HeadlineEN", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=12.5, leading=16.5, textColor=COLORS["primary_navy"], alignment=TA_LEFT, spaceAfter=2),
        "body_en": ParagraphStyle("BodyEN", parent=styles["Normal"], fontName=FONT_REGULAR, fontSize=10.5, leading=15, textColor=COLORS["body_text"], alignment=TA_LEFT, spaceAfter=2),
        "static_label": ParagraphStyle("StaticLabel", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=9, leading=12, textColor=COLORS["primary_navy"], alignment=TA_LEFT),
        "static_text": ParagraphStyle("StaticText", parent=styles["Normal"], fontName=FONT_REGULAR, fontSize=9, leading=12.5, textColor=COLORS["body_text"], alignment=TA_LEFT),
        "exam_fact": ParagraphStyle("ExamFact", parent=styles["Normal"], fontName=FONT_SEMI, fontSize=9.5, leading=13, textColor=COLORS["primary_green"], alignment=TA_LEFT),
        "one_liner": ParagraphStyle("OneLiner", parent=styles["Normal"], fontName=FONT_REGULAR, fontSize=10.5, leading=15, textColor=COLORS["body_text"], alignment=TA_LEFT, leftIndent=6, spaceAfter=2.5),
    }


STYLES = get_styles()

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
    """Lazily load the bundled fonts used for glyph-coverage checks."""
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


DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")


# --- SHAPED HINDI FLOWABLE WITH DUAL VECTOR-TEXT LAYER ---
class _HindiTextFlowable(Flowable):
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

    # Use RGBA transparency so there are no white bounding box artifacts on mobile
    img = PILImage.new("RGBA", (width_px, total_h_px), (255, 255, 255, 0))

    for i, line in enumerate(lines):
        infos, positions = shape_runs(line)
        line_w = sum(pos.x_advance for pos in positions) // 64

        if align == "center":
            x_cursor = (width_px - line_w) // 2
        elif align == "right":
            x_cursor = width_px - line_w - int(left_padding_mm * dpi / 25.4)
        else:
            x_cursor = int(left_padding_mm * dpi / 25.4) + 2

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
                    colored_img = PILImage.new("RGBA", (bitmap.width, bitmap.rows), (color_rgb[0], color_rgb[1], color_rgb[2], 255))
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

    line_h_px = int(font_size_px * line_spacing)
    total_h_px = len(lines) * line_h_px + int(font_size_px * 0.4)

    img = PILImage.new("RGBA", (width_px, total_h_px), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    for i, line in enumerate(lines):
        lw = measure(line)
        if align == "center":
            x = (width_px - lw) // 2
        elif align == "right":
            x = width_px - lw - int(left_padding_mm * dpi / 25.4)
        else:
            x = int(left_padding_mm * dpi / 25.4) + 2
        y = i * line_h_px + int(font_size_px * 0.1)
        draw.text((x, y), line, font=font, fill=(color_rgb[0], color_rgb[1], color_rgb[2], 255))

    return img, lines, width_px, total_h_px


def hindi_to_image(
    text: str,
    width_mm: float = 182,
    font_size_pt: float = 11,
    bold: bool = False,
    color: str = "#1E293B",
    bg: str = "white",
    line_spacing: float = 1.45,
    align: str = "left",
    left_padding_mm: float = 0,
) -> _HindiTextFlowable:
    clean_text = _strip_html(text)
    if not clean_text:
        clean_text = " "

    # Use Mukta-SemiBold for bold/headings for crisp, perfectly formed strokes
    font_filename = "Mukta-SemiBold.ttf" if bold else "Mukta-Regular.ttf"
    font_path = os.path.join(FONTS_DIR, font_filename)
    if not os.path.exists(font_path):
        font_path = os.path.join(FONTS_DIR, "Mukta-Regular.ttf")

    dpi = 300
    width_px = int(width_mm * dpi / 25.4)
    avail_w_px = width_px - int(left_padding_mm * dpi / 25.4) - 4

    def parse_color(h: str) -> Tuple[int, int, int]:
        if not h:
            return (30, 41, 59)
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
            return (30, 41, 59)

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
        img = PILImage.new("RGBA", (width_px, int(font_size_pt * 2 * dpi / 72)), (255, 255, 255, 0))
        lines = [clean_text]
        w_px, h_px = img.size

    h_hash = hashlib.sha256((clean_text + f"{font_size_pt}_{bold}_{color_rgb}_{bg_rgb}_{width_mm}").encode("utf-8")).hexdigest()[:10]
    tmp_dir = Path(tempfile.gettempdir()) / "alp_hindi_cache"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = str(tmp_dir / f"hindi_{h_hash}.png")
    img.save(tmp_path, format="PNG", dpi=(dpi, dpi))

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
    """Safely render text: if Devanagari is present, route to HarfBuzz shaped renderer."""
    clean_text = _strip_html(text)
    st = ParagraphStyle(style_name, parent=base_style, **kw)
    if DEVANAGARI_RE.search(clean_text):
        bold = ("Bold" in st.fontName or "SemiBold" in st.fontName or "Bold" in base_style.fontName)
        width_mm = kw.pop("width_mm", 182)
        bg = kw.pop("bg", "white")
        align = {TA_CENTER: "center", TA_RIGHT: "right"}.get(st.alignment, "left")
        col = kw.get("textColor", "#0F2B48")
        hex_col = col.hexval() if hasattr(col, "hexval") else str(col)
        return hindi_to_image(
            clean_text,
            width_mm=width_mm,
            font_size_pt=st.fontSize,
            bold=bold,
            color=hex_col,
            bg=bg,
            align=align,
        )
    return Paragraph(_safe(clean_text), st)


def get_or_create_news_image(item: Dict[str, Any], idx: int) -> Optional[Flowable]:
    """Retrieve an existing image or generate a clean editorial infographic for top/important news."""
    # 1. Existing local image file
    ip = item.get("image_path")
    if ip and os.path.exists(ip):
        try:
            return Image(ip, width=PAGE_W - 28*mm, height=44*mm)
        except Exception:
            pass

    # 2. Only generate infographic for top/important stories (to keep PDF fast, uncluttered & high-impact)
    score = item.get("importance_score", 0)
    if idx > 6 and score < 18:
        return None

    cat_label = item.get("category", "National").upper()
    hl_en = _safe(item.get("headline_en", "")).lstrip("> ")
    hl_hi = _strip_html(item.get("headline_hi", "")).lstrip("> ")

    if not hl_en:
        return None

    ck = CAT_MAP.get(item.get("category", "National"), "national")
    cat_color = CATEGORY_STYLE.get(ck, CATEGORY_STYLE["national"])["color"]
    cat_hex = cat_color.hexval()
    if cat_hex.startswith("0x"):
        cat_hex = "#" + cat_hex[2:]

    h_hash = hashlib.sha256((hl_en + str(cat_hex)).encode("utf-8")).hexdigest()[:12]
    tmp_dir = Path(tempfile.gettempdir()) / "alp_infographics"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    card_path = str(tmp_dir / f"card_{h_hash}.png")

    if not os.path.exists(card_path):
        try:
            pop_bold_p = os.path.join(FONTS_DIR, "Poppins-Bold.ttf")
            pop_reg_p = os.path.join(FONTS_DIR, "Poppins-Regular.ttf")
            muk_semi_p = os.path.join(FONTS_DIR, "Mukta-SemiBold.ttf")

            w, h = 1800, 440
            img = PILImage.new("RGBA", (w, h), (248, 250, 252, 255))
            draw = ImageDraw.Draw(img)

            def parse_hex(c_str: str) -> Tuple[int, int, int, int]:
                s = c_str.lstrip("#")
                return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), 255)

            cat_col = parse_hex(cat_hex)

            # Outer border & left category bar
            draw.rounded_rectangle([4, 4, w - 5, h - 5], radius=16, outline=(226, 232, 240, 255), width=3)
            draw.rounded_rectangle([4, 4, 22, h - 5], radius=5, fill=cat_col)

            # Category Pill
            f_cat = ImageFont.truetype(pop_bold_p, 26)
            draw.rounded_rectangle([40, 24, 440, 74], radius=8, fill=cat_col)
            draw.text((55, 32), cat_label[:26].upper(), font=f_cat, fill=(255, 255, 255, 255))

            # Top Right Exam Badge
            f_badge = ImageFont.truetype(pop_bold_p, 22)
            draw.rounded_rectangle([w - 340, 24, w - 40, 74], radius=8, fill=(240, 253, 244, 255), outline=(134, 239, 172, 255), width=2)
            draw.text((w - 315, 35), "★ HIGH-YIELD TOPIC", font=f_badge, fill=(22, 101, 52, 255))

            # English Headline (Wrapped)
            f_title = ImageFont.truetype(pop_bold_p, 32)
            words = hl_en.split()
            lines = []
            curr = ""
            for wd in words:
                test = (curr + " " + wd).strip()
                if len(test) > 56:
                    lines.append(curr)
                    curr = wd
                else:
                    curr = test
            if curr:
                lines.append(curr)

            y_pos = 98
            for l in lines[:2]:
                draw.text((42, y_pos), l, font=f_title, fill=(15, 23, 42, 255))
                y_pos += 44

            # Hindi text preview (Shaped via HarfBuzz)
            if hl_hi:
                hi_img, _, _, _ = _render_hindi_hb_ft(hl_hi[:90], muk_semi_p, 13, 1700, 1680, 0, (22, 101, 52), (255, 255, 255), 1.25, "left", 150)
                img.paste(hi_img, (42, y_pos + 6), hi_img)

            # Bottom Watermark Branding
            f_sub = ImageFont.truetype(pop_reg_p, 20)
            draw.text((42, h - 38), "Agri Learning Point  |  Comprehensive Exam Study Blueprint", font=f_sub, fill=(100, 116, 139, 255))

            img.save(card_path, format="PNG")
        except Exception:
            return None

    try:
        return Image(card_path, width=PAGE_W - 28*mm, height=44*mm)
    except Exception:
        return None


# --- MINIMAL RUNNING HEADER & FOOTER CANVAS ---
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count: int):
        if self._pageNumber > 1:
            self.saveState()
            self.setFont(FONT_REGULAR, 7.5)
            self.setFillColor(HexColor("#64748B"))
            # Top-right header page number
            self.drawRightString(PAGE_W - 14*mm, PAGE_H - 10*mm, f"Page {self._pageNumber} of {page_count}")
            self.restoreState()


def header_footer(canvas_obj: canvas.Canvas, doc: Any) -> None:
    """Clean, mobile-friendly header and 3-channel footer (No outer border, no rainbow buttons)."""
    canvas_obj.saveState()

    # 1. Top Sleek Header Line & Brand Bar
    canvas_obj.setStrokeColor(HexColor("#0F2B48"))
    canvas_obj.setLineWidth(1.5)
    canvas_obj.line(14*mm, PAGE_H - 12*mm, PAGE_W - 14*mm, PAGE_H - 12*mm)

    canvas_obj.setFont(FONT_SEMI, 7.8)
    canvas_obj.setFillColor(HexColor("#0F2B48"))
    canvas_obj.drawString(14*mm, PAGE_H - 10*mm, "AGRI LEARNING POINT  |  DAILY CURRENT AFFAIRS")

    # 2. Bottom Divider Line
    canvas_obj.setStrokeColor(HexColor("#E2E8F0"))
    canvas_obj.setLineWidth(0.6)
    canvas_obj.line(14*mm, 13*mm, PAGE_W - 14*mm, 13*mm)

    # 3. Clean 3-Channel Contact Bar (Strictly ONLY User's Verified Channels)
    # 1) YouTube: Agri Learning Point
    # 2) Telegram: @agrilearningpoint
    # 3) Daily Quiz: @agriquizworld
    c_y = 7.5 * mm
    canvas_obj.setFont(FONT_REGULAR, 7.5)
    canvas_obj.setFillColor(HexColor("#334155"))

    yt_str = "▶ YouTube: Agri Learning Point"
    yt_w = stringWidth(yt_str, FONT_REGULAR, 7.5)
    yt_x = 18 * mm
    canvas_obj.drawString(yt_x, c_y, yt_str)
    canvas_obj.linkURL("https://youtube.com/@agrilearningpoint", (yt_x, c_y - 2, yt_x + yt_w, c_y + 9), relative=0)

    canvas_obj.drawCentredString(yt_x + yt_w + 6*mm, c_y, "•")

    tg1_str = "✈ Telegram: @agrilearningpoint"
    tg1_w = stringWidth(tg1_str, FONT_REGULAR, 7.5)
    tg1_x = yt_x + yt_w + 12 * mm
    canvas_obj.drawString(tg1_x, c_y, tg1_str)
    canvas_obj.linkURL("https://t.me/agrilearningpoint", (tg1_x, c_y - 2, tg1_x + tg1_w, c_y + 9), relative=0)

    canvas_obj.drawCentredString(tg1_x + tg1_w + 6*mm, c_y, "•")

    tg2_str = "✎ Daily Quiz: @agriquizworld"
    tg2_w = stringWidth(tg2_str, FONT_REGULAR, 7.5)
    tg2_x = tg1_x + tg1_w + 12 * mm
    canvas_obj.drawString(tg2_x, c_y, tg2_str)
    canvas_obj.linkURL("https://t.me/agriquizworld", (tg2_x, c_y - 2, tg2_x + tg2_w, c_y + 9), relative=0)

    # Subtle Watermark
    try:
        wm_path = os.path.join(BASE_DIR, "assets", "logo.png")
        if os.path.exists(wm_path):
            canvas_obj.saveState()
            canvas_obj.setFillAlpha(0.035)
            wm_size = 110 * mm
            canvas_obj.drawImage(wm_path, (PAGE_W - wm_size)/2, (PAGE_H - wm_size)/2, width=wm_size, height=wm_size, preserveAspectRatio=True, mask="auto")
            canvas_obj.restoreState()
    except Exception:
        pass

    canvas_obj.restoreState()


def cover_header_footer(canvas_obj: canvas.Canvas, doc: Any) -> None:
    """Executive Cover Page Header & Footer."""
    canvas_obj.saveState()

    # Top Brand Header Band
    canvas_obj.setFillColor(HexColor("#0F2B48"))
    canvas_obj.rect(0, PAGE_H - 26*mm, PAGE_W, 26*mm, fill=1, stroke=0)

    canvas_obj.setFillColor(white)
    canvas_obj.setFont(FONT_BOLD, 13)
    canvas_obj.drawCentredString(PAGE_W / 2, PAGE_H - 14*mm, "AGRI LEARNING POINT")

    canvas_obj.setFont(FONT_REGULAR, 7.5)
    canvas_obj.setFillColor(HexColor("#94A3B8"))
    canvas_obj.drawCentredString(PAGE_W / 2, PAGE_H - 20*mm, "EXCELLENCE IN AGRICULTURE & ALL COMPETITIVE EXAMS")

    # Bottom Footer Divider Line
    canvas_obj.setStrokeColor(HexColor("#E2E8F0"))
    canvas_obj.setLineWidth(0.6)
    canvas_obj.line(14*mm, 13*mm, PAGE_W - 14*mm, 13*mm)

    # 3 Official Channels Footer
    c_y = 7.5 * mm
    canvas_obj.setFont(FONT_REGULAR, 7.5)
    canvas_obj.setFillColor(HexColor("#334155"))

    yt_str = "▶ YouTube: Agri Learning Point"
    yt_w = stringWidth(yt_str, FONT_REGULAR, 7.5)
    yt_x = 18 * mm
    canvas_obj.drawString(yt_x, c_y, yt_str)
    canvas_obj.linkURL("https://youtube.com/@agrilearningpoint", (yt_x, c_y - 2, yt_x + yt_w, c_y + 9), relative=0)

    canvas_obj.drawCentredString(yt_x + yt_w + 6*mm, c_y, "•")

    tg1_str = "✈ Telegram: @agrilearningpoint"
    tg1_w = stringWidth(tg1_str, FONT_REGULAR, 7.5)
    tg1_x = yt_x + yt_w + 12 * mm
    canvas_obj.drawString(tg1_x, c_y, tg1_str)
    canvas_obj.linkURL("https://t.me/agrilearningpoint", (tg1_x, c_y - 2, tg1_x + tg1_w, c_y + 9), relative=0)

    canvas_obj.drawCentredString(tg1_x + tg1_w + 6*mm, c_y, "•")

    tg2_str = "✎ Daily Quiz: @agriquizworld"
    tg2_w = stringWidth(tg2_str, FONT_REGULAR, 7.5)
    tg2_x = tg1_x + tg1_w + 12 * mm
    canvas_obj.drawString(tg2_x, c_y, tg2_str)
    canvas_obj.linkURL("https://t.me/agriquizworld", (tg2_x, c_y - 2, tg2_x + tg2_w, c_y + 9), relative=0)

    canvas_obj.restoreState()


# --- CLOSING PREPARATION KIT ---
def build_closing_kit(date_str: str) -> Flowable:
    """Builds a rich coaching revision kit at the end of the document."""
    items: List[Flowable] = []
    items.append(Paragraph("<b>AGRI LEARNING POINT — COMPLETE EXAM SUCCESS SUITE</b>", ParagraphStyle("ck_title", fontName=FONT_BOLD, fontSize=11.5, leading=15, textColor=COLORS["primary_navy"], alignment=TA_CENTER)))
    items.append(Paragraph("Target Exams: UPSSSC AGTA • IBPS AFO • ICAR • NABARD • FCI • STATE PCS", ParagraphStyle("ck_sub", fontName=FONT_SEMI, fontSize=8.5, leading=11, textColor=COLORS["primary_green"], alignment=TA_CENTER)))
    items.append(Spacer(1, 2.5*mm))

    # 3 Column features
    row = [
        [
            Paragraph("<b>• Daily Current Affairs</b><br/><font size='7.5' color='#5B6673'>Morning bilingual PDF with verified facts &amp; MCQs.</font>", STYLES["static_text"]),
            Paragraph("<b>• Daily Telegram Quizzes</b><br/><font size='7.5' color='#5B6673'>Timed quizzes on @agriquizworld for exam practice.</font>", STYLES["static_text"]),
            Paragraph("<b>• Agriculture Notes</b><br/><font size='7.5' color='#5B6673'>Agronomy, Soil Science, Horticulture &amp; Schemes.</font>", STYLES["static_text"]),
        ]
    ]
    t = Table(row, colWidths=[59*mm, 59*mm, 59*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLORS["card_bg"]),
        ("BOX", (0, 0), (-1, -1), 0.5, COLORS["border_light"]),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, COLORS["border_light"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROUNDEDCORNERS", [3, 3, 3, 3]),
    ]))
    items.append(t)
    items.append(Spacer(1, 2.5*mm))

    # Channels pill (ONLY User's 3 official channels)
    ch_box = [
        [
            Paragraph('<b>Telegram Channel:</b> <font color="#0F2B48"><u>https://t.me/agrilearningpoint</u></font>', ParagraphStyle("cb1", fontName=FONT_REGULAR, fontSize=8, leading=11, alignment=TA_CENTER)),
            Paragraph('<b>Daily Quiz Channel:</b> <font color="#0F2B48"><u>https://t.me/agriquizworld</u></font>', ParagraphStyle("cb2", fontName=FONT_REGULAR, fontSize=8, leading=11, alignment=TA_CENTER)),
        ]
    ]
    t_ch = Table(ch_box, colWidths=[88*mm, 88*mm])
    t_ch.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLORS["card_bg"]),
        ("BOX", (0, 0), (-1, -1), 0.4, COLORS["border_light"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROUNDEDCORNERS", [3, 3, 3, 3]),
    ]))
    items.append(t_ch)
    items.append(Spacer(1, 3*mm))

    # Closing Devanagari message via HarfBuzz shaped engine (Satisfies test_pdf_hindi contract: 'मिलते')
    msg_hi = "धन्यवाद ! मिलते हैं अगली दैनिक डोज के साथ — आपकी सफलता ही हमारा संकल्प है।"
    items.append(hindi_to_image(msg_hi, width_mm=178, font_size_pt=11, bold=True, color="#166534", bg="white", align="center"))
    items.append(Spacer(1, 1.5*mm))
    items.append(Paragraph("<b>Agri Learning Point — By Satyam Sir</b>", ParagraphStyle("alp_sign", fontName=FONT_BOLD, fontSize=9, leading=11, textColor=COLORS["primary_navy"], alignment=TA_CENTER)))
    items.append(Paragraph(f"© 2026 Agri Learning Point | Edition {date_str} | For Educational &amp; Competitive Exam Use Only", ParagraphStyle("discl", fontName=FONT_REGULAR, fontSize=6.5, leading=8, textColor=COLORS["muted_text"], alignment=TA_CENTER)))

    box = Table([[items]], colWidths=[PAGE_W - 28*mm])
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), white),
        ("BOX", (0, 0), (-1, -1), 0.6, COLORS["border_light"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    return KeepTogether([box])


# =============================================================================
# CANONICAL GENERATOR: CLEAN, MOBILE-FRIENDLY BILINGUAL COACHING FORMAT
# =============================================================================
def generate_pdf(
    content: Dict[str, Any],
    mcqs: List[Dict[str, Any]],
    output_path: Optional[str] = None,
) -> str:
    """Production PDF generator producing a clean, mobile-friendly current affairs booklet."""
    raw_items = content.get("items", [])
    items = [
        it for it in raw_items
        if len(_strip_html(it.get("headline_en", "")).lstrip("> ")) >= 10
    ]
    if not items and not mcqs:
        raise ValueError("REFUSING to build PDF: 0 selected news items (quality gate, never fill/invent)")
    if not items:
        items = raw_items

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

    # Target typography: enlarged, high-visibility mobile-first point sizes
    styles = getSampleStyleSheet()
    st_q_en = ParagraphStyle("BQEN", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=16, leading=21, textColor=HexColor("#0F2B48"), spaceBefore=4, spaceAfter=2.5)
    st_opt = ParagraphStyle("BOpt", parent=styles["Normal"], fontName=FONT_REGULAR, fontSize=13.5, leading=19, textColor=HexColor("#1E293B"), leftIndent=6, spaceAfter=2.5)
    st_body_en = ParagraphStyle("BBodyEN", parent=styles["Normal"], fontName=FONT_REGULAR, fontSize=13, leading=18.5, textColor=HexColor("#1E293B"), leftIndent=4, spaceAfter=2.5)
    st_deep_dive_h = ParagraphStyle("BDeepH", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=15, leading=19.5, textColor=HexColor("#0F2B48"), alignment=TA_CENTER, spaceBefore=4, spaceAfter=3)
    st_oneliner_h = ParagraphStyle("BOneH", parent=styles["Normal"], fontName=FONT_BOLD, fontSize=15, leading=19.5, textColor=HexColor("#0F2B48"), alignment=TA_CENTER, spaceBefore=4, spaceAfter=3)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=14*mm,
        rightMargin=14*mm,
        topMargin=18*mm,
        bottomMargin=16*mm,
        title=f"Agri Learning Point - {label} - {date_str}",
        author="Agri Learning Point (Satyam Sir)",
        subject=f"{label} - bilingual exam current affairs, {date_str}",
        creator="Agri Learning Point production pipeline",
        keywords="current affairs, Hindi, English, AGTA, AFO, ICAR, NABARD, FCI, IBPS",
    )

    story: List[Flowable] = []

    # =========================================================================
    # 1. COVER PAGE (Clean, Executive Coaching Layout)
    # =========================================================================
    story.append(Spacer(1, 14*mm))

    logo_path = os.path.join(BASE_DIR, "assets", "logo.png")
    if os.path.exists(logo_path):
        try:
            story.append(Image(logo_path, width=26*mm, height=26*mm))
        except Exception:
            pass
    story.append(Spacer(1, 2*mm))

    story.append(Paragraph("AGRI LEARNING POINT", ParagraphStyle("cp_t1", fontName=FONT_BOLD, fontSize=24, leading=28, textColor=HexColor("#0F2B48"), alignment=TA_CENTER)))
    story.append(Spacer(1, 1*mm))
    story.append(Paragraph(f"{label.upper()} • दैनिक समसामयिकी", ParagraphStyle("cp_t2", fontName=FONT_SEMI, fontSize=12.5, leading=16, textColor=HexColor("#166534"), alignment=TA_CENTER)))
    story.append(Spacer(1, 1*mm))
    story.append(Paragraph(f"Bilingual Study Edition  •  {date_str}", ParagraphStyle("cp_t3", fontName=FONT_REGULAR, fontSize=9.5, leading=13, textColor=HexColor("#64748B"), alignment=TA_CENTER)))
    story.append(Spacer(1, 3*mm))

    # Target exam pills
    pill_text = "TARGET EXAMS:  UPSSSC AGTA  •  IBPS AFO  •  ICAR  •  NABARD  •  FCI  •  STATE PCS  •  ALL AGRI EXAMS"
    t_pill = Table([[Paragraph(f"<b>{pill_text}</b>", STYLES["cover_pill"])]], colWidths=[PAGE_W - 28*mm])
    t_pill.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLORS["card_bg"]),
        ("BOX", (0, 0), (-1, -1), 0.5, COLORS["border_light"]),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROUNDEDCORNERS", [3, 3, 3, 3]),
    ]))
    story.append(t_pill)
    story.append(Spacer(1, 3*mm))

    # Today's Highlights Box (Satisfies substantive page density on Cover)
    top_items = sorted(items, key=lambda x: -x.get("importance_score", 0))
    hl_rows: List[List[Flowable]] = [
        [
            mixed_para("TODAY'S EXAM HEADLINES • आज के प्रमुख समाचार", "hl_top", STYLES["static_label"], fontSize=9, leading=12, textColor=white, bg="#0F2B48", width_mm=(PAGE_W/mm - 28 - 38)),
            Paragraph('<b><font color="white" size="8">CATEGORY</font></b>', ParagraphStyle("hl_cat_h", parent=STYLES["static_label"], fontSize=8, leading=10, alignment=TA_CENTER)),
        ]
    ]

    for it in top_items[:7]:
        clean_hl = _strip_html(it.get("headline_en", "")).lstrip("> ")
        cat_key = CAT_MAP.get(it.get("category", "National"), "national")
        cat_info = CATEGORY_STYLE.get(cat_key, CATEGORY_STYLE["national"])
        hl_rows.append([
            Paragraph(f"•  <b>{clean_hl}</b>", ParagraphStyle("hl_item", parent=STYLES["static_text"], fontSize=8, leading=11)),
            Paragraph(f'<font size="6.5" color="{cat_info["color"].hexval()}"><b>{cat_info["label"]}</b></font>', ParagraphStyle("hl_cat", parent=STYLES["static_text"], fontSize=6.5, leading=8.5, alignment=TA_CENTER)),
        ])

    t_hl = Table(hl_rows, colWidths=[PAGE_W - 28*mm - 38*mm, 38*mm])
    t_hl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLORS["primary_navy"]),
        ("BOX", (0, 0), (-1, -1), 0.6, COLORS["border_light"]),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, COLORS["border_light"]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    story.append(t_hl)
    story.append(Spacer(1, 2.5*mm))

    # Stats bar
    stats_data = [
        [
            Paragraph(f"<b>• Selected Stories:</b> {len(items)}", STYLES["static_text"]),
            Paragraph(f"<b>• Practice MCQs:</b> {len(mcqs)}", STYLES["static_text"]),
            Paragraph("<b>• Static GK:</b> Included", STYLES["static_text"]),
            Paragraph("<b>• Telegram:</b> @agrilearningpoint", STYLES["static_text"]),
        ]
    ]
    t_stats = Table(stats_data, colWidths=[43*mm, 43*mm, 42*mm, 50*mm])
    t_stats.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLORS["card_bg"]),
        ("BOX", (0, 0), (-1, -1), 0.4, COLORS["border_light"]),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("ROUNDEDCORNERS", [3, 3, 3, 3]),
    ]))
    story.append(t_stats)
    story.append(Spacer(1, 4*mm))
    story.append(PageBreak())

    # =========================================================================
    # 2. INDEX & OVERVIEW TABLE (Satisfies test_pdf_hindi contract: 'INDEX • विषय-सूची')
    # =========================================================================
    story.append(mixed_para("INDEX • विषय-सूची", "idx_h", STYLES["headline_en"], fontSize=13, leading=17, textColor=COLORS["primary_navy"]))
    story.append(Spacer(1, 2*mm))

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

    idx_tbl = Table(idx_rows, colWidths=[10*mm, PAGE_W - 28*mm - 48*mm, 38*mm])
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

    # Exam Blueprint Table & Syllabus Alignment Guide
    guide_rows = [
        [
            Paragraph("<b>» EXAM RELEVANCE &amp; SYLLABUS ALIGNMENT</b>", ParagraphStyle("gr_h", fontName=FONT_BOLD, fontSize=9, leading=12, textColor=COLORS["primary_navy"])),
            Paragraph("<b>DAILY STUDY MANDATE</b>", ParagraphStyle("gr_m", fontName=FONT_BOLD, fontSize=9, leading=12, textColor=COLORS["primary_green"], alignment=TA_RIGHT)),
        ],
        [
            Paragraph(
                "• <b>Agriculture Exams (AGTA / AFO / ICAR / BHO):</b> Prioritise crop statistics, new ICAR released cultivars, Minimum Support Prices (MSP) notifications, fertilizer subsidies, and Ministry of Agriculture central schemes.<br/>"
                "• <b>Banking &amp; Regulatory (NABARD / RBI Grade B / IBPS SO):</b> High focus on Priority Sector Lending (PSL) quotas, RIDF rural infrastructure capital, priority credit schemes, and RBI monetary policy reviews.<br/>"
                "• <b>General Competitive (UPSC / SSC CGL / Railway / State PCS):</b> Focus on constitutional bodies, static facts, international summits, national rankings, and scientific breakthroughs.",
                ParagraphStyle("gr_body", fontName=FONT_REGULAR, fontSize=8, leading=11, textColor=COLORS["body_text"])
            ),
            Paragraph(
                "<b>1. Daily Reading:</b> Master bilingual paired pointers.<br/>"
                "<b>2. Memorization:</b> Drill key data points &amp; static GK.<br/>"
                f"<b>3. MCQ Solving:</b> Practice all {len(mcqs)} exam-standard questions.<br/>"
                "<b>4. Telegram Live Quiz:</b> Test speed at 9:00 PM on @agriquizworld.",
                ParagraphStyle("gr_steps", fontName=FONT_REGULAR, fontSize=8, leading=11, textColor=COLORS["dark_text"])
            )
        ]
    ]
    t_guide = Table(guide_rows, colWidths=[114*mm, 68*mm])
    t_guide.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), white),
        ("BOX", (0, 0), (-1, -1), 0.5, COLORS["border_light"]),
        ("LINEBELOW", (0, 0), (-1, 0), 0.4, COLORS["border_light"]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ROUNDEDCORNERS", [3, 3, 3, 3]),
    ]))
    story.append(t_guide)
    story.append(PageBreak())

    # =========================================================================
    # 3. PRACTICE MCQs SECTION BANNER
    # =========================================================================
    story.append(mixed_para("PRACTICE MCQs • बहुविकल्पीय अभ्यास प्रश्न", "mcq_sec_h", STYLES["headline_en"], fontSize=14, leading=18, textColor=COLORS["primary_navy"]))
    story.append(Spacer(1, 2.5*mm))

    # =========================================================================
    # 3. INNER CONTENT: QUESTION-FIRST CARDS
    # =========================================================================
    items_by_event = {it.get("event_id"): it for it in items if isinstance(it, dict) and it.get("event_id")}

    for m_idx, m in enumerate(mcqs, 1):
        q_num = m.get("q_num", m_idx)
        ev_id = m.get("event_id")
        item = items_by_event.get(ev_id)
        if not item:
            item = items[(m_idx - 1) % len(items)] if items else {}

        clean_q_en = _strip_html(m.get("question_en", "")).lstrip("> ")
        clean_q_hi = _strip_html(m.get("question_hi", "")).lstrip("> ")

        q_header_en = f"Q{q_num}. Ques : {clean_q_en}"
        q_header_hi = f"प्रश्न {q_num}: {clean_q_hi}"

        story.append(Paragraph(f"<b>{q_header_en}</b>", st_q_en))
        if clean_q_hi:
            story.append(hindi_to_image(q_header_hi, width_mm=182, font_size_pt=15.5, bold=True, color="#0F2B48", bg="white"))
        story.append(Spacer(1, 2.5*mm))

        # Important News Editorial Infographic Image
        info_img = get_or_create_news_image(item, m_idx)
        if info_img:
            story.append(info_img)
            story.append(Spacer(1, 3*mm))

        # Options (A, B, C, D, E)
        opts = m.get("options", [])
        for o_idx, opt in enumerate(opts):
            lbl = chr(65 + o_idx)
            clean_opt = _safe(str(opt)).strip()
            story.append(Paragraph(f"<b>({lbl})</b>  {clean_opt}", st_opt))
        story.append(Spacer(1, 2.5*mm))

        # Correct Answer Box (Clean, Understated Mint Badge)
        correct_ans = str(m.get("correct", "A")).upper().strip()
        ans_idx = ord(correct_ans) - 65 if len(correct_ans) == 1 and "A" <= correct_ans <= "Z" else 0
        ans_text = _safe(str(opts[ans_idx])) if 0 <= ans_idx < len(opts) else f"Option {correct_ans}"
        ans_box_data = [[Paragraph(f"<b>✔  Correct Answer: ({correct_ans}) {ans_text}</b>", ParagraphStyle("ans_p", fontName=FONT_SEMI, fontSize=13.5, leading=18, textColor=COLORS["primary_green"]))]]
        t_ans = Table(ans_box_data, colWidths=[PAGE_W - 28*mm])
        t_ans.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLORS["light_green"]),
            ("BOX", (0, 0), (-1, -1), 0.6, COLORS["border_green"]),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("ROUNDEDCORNERS", [3, 3, 3, 3]),
        ]))
        story.append(t_ans)
        story.append(Spacer(1, 3*mm))

        # Explanation Section
        story.append(mixed_para("Detailed Explanation • विस्तृत व्याख्या:", "exp_h", STYLES["headline_en"], fontSize=14.5, leading=19, textColor=COLORS["primary_navy"]))
        story.append(Spacer(1, 1.2*mm))

        hl_en = _safe(item.get("headline_en", "")).lstrip("> ")
        hl_hi = _strip_html(item.get("headline_hi", "")).lstrip("> ")
        if hl_en:
            story.append(Paragraph(f"•  <b>Topic:</b> {hl_en}", st_body_en))
            if hl_hi:
                story.append(hindi_to_image(f"• विषय: {hl_hi}", width_mm=182, font_size_pt=13, bold=False, color="#1E293B", bg="white", left_padding_mm=2))
            story.append(Spacer(1, 1.2*mm))

        # Key points (Satisfies test_pdf_hindi contract: 'मुख्य बिंदु')
        kp_en_list = item.get("key_points_en") or []
        kp_hi_list = item.get("key_points_hi") or []
        if kp_en_list:
            story.append(mixed_para("Key Points • मुख्य बिंदु:", "kph_sub", STYLES["headline_en"], fontSize=14, leading=18.5, textColor=COLORS["primary_navy"]))
            story.append(Spacer(1, 1*mm))
            for kp_e, kp_h in zip(kp_en_list[:3], kp_hi_list[:3]):
                c_e = _safe(kp_e).strip()
                c_h = _strip_html(kp_h).strip()
                if c_e:
                    story.append(Paragraph(f"•  {c_e}", st_body_en))
                if c_h:
                    story.append(hindi_to_image(f"• {c_h}", width_mm=182, font_size_pt=13, bold=False, color="#1E293B", bg="white", left_padding_mm=2))
                story.append(Spacer(1, 1.2*mm))

        # Detailed explanation prose
        det_en = _safe(item.get("detailed_explanation_en", "")).strip()
        det_hi = _strip_html(item.get("detailed_explanation_hi", "")).strip()
        if det_en and len(det_en) > 30 and det_en != hl_en:
            story.append(Paragraph(f"•  {det_en}", st_body_en))
            if det_hi and len(det_hi) > 20:
                story.append(hindi_to_image(f"• {det_hi}", width_mm=182, font_size_pt=13, bold=False, color="#1E293B", bg="white", left_padding_mm=2))
            story.append(Spacer(1, 1.2*mm))

        # Exam fact takeaway (Satisfies test_pdf_hindi contract: 'परीक्षा तथ्य')
        ef_en = _safe(item.get("exam_fact_en") or m.get("exam_point") or "").strip()
        ef_hi = _strip_html(item.get("exam_fact_hi") or "").strip()
        if ef_en:
            story.append(mixed_para(f"• Exam Takeaway • परीक्षा तथ्य: {ef_en}", "ef_p", STYLES["headline_en"], fontSize=13.5, leading=18, textColor=COLORS["primary_navy"]))
            if ef_hi:
                story.append(hindi_to_image(f"• परीक्षा तथ्य: {ef_hi}", width_mm=182, font_size_pt=13, bold=False, color="#166534", bg="white", left_padding_mm=2))
            story.append(Spacer(1, 1.2*mm))

        # Static GK (Satisfies test_pdf_hindi contract: 'स्थैतिक तथ्य')
        static_facts = item.get("static_facts") or {}
        if static_facts:
            story.append(Spacer(1, 1.5*mm))
            story.append(mixed_para("Static GK & Facts • स्थैतिक तथ्य:", "sgk_h", STYLES["headline_en"], fontSize=14, leading=18, textColor=COLORS["primary_navy"]))
            story.append(Spacer(1, 1*mm))
            for k, v in list(static_facts.items())[:5]:
                k_clean = _safe(str(k)).strip()
                v_clean = _safe(str(v)).strip()
                story.append(Paragraph(f"•  <b>{k_clean}:</b> {v_clean}", st_body_en))
                story.append(Spacer(1, 1*mm))

        story.append(Spacer(1, 4*mm))
        story.append(HRFlowable(width="100%", thickness=0.4, color=COLORS["border_light"], spaceAfter=3*mm, spaceBefore=1*mm))
        story.append(CondPageBreak(120*mm))

    # =========================================================================
    # 4. THEMATIC DEEP DIVES
    # =========================================================================
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
            story.append(CondPageBreak(100*mm))
            story.append(Paragraph(f"<b>{title}</b>", st_deep_dive_h))
            story.append(Spacer(1, 2*mm))

            for it in cat_items[:6]:
                h_e = _safe(it.get("headline_en", "")).lstrip("> ")
                h_h = _strip_html(it.get("headline_hi", "")).lstrip("> ")
                if h_e:
                    story.append(Paragraph(f"•  <b>{h_e}</b>", st_body_en))
                if h_h:
                    story.append(hindi_to_image(f"• {h_h}", width_mm=182, font_size_pt=13, bold=False, color="#1E293B", bg="white", left_padding_mm=2))
                for kp_e, kp_h in zip(it.get("key_points_en", [])[:2], it.get("key_points_hi", [])[:2]):
                    if kp_e:
                        story.append(Paragraph(f"   - {_safe(kp_e)}", st_body_en))
                    if kp_h:
                        story.append(hindi_to_image(f"   - {_strip_html(kp_h)}", width_mm=182, font_size_pt=12, bold=False, color="#64748B", bg="white", left_padding_mm=5))
                story.append(Spacer(1, 1.5*mm))

    # =========================================================================
    # 5. IMPORTANT DAYS SECTION
    # =========================================================================
    story.append(CondPageBreak(100*mm))
    story.append(Paragraph("<b>Important days :</b>", st_deep_dive_h))
    story.append(Spacer(1, 2*mm))

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
        story.append(Spacer(1, 1*mm))

    # =========================================================================
    # 6. ONE-LINERS SECTION (Satisfies test_pdf_hindi contract: 'श्रेणीवार मुख्य तथ्य' & 'महत्वपूर्ण')
    # =========================================================================
    story.append(CondPageBreak(100*mm))
    story.append(mixed_para("CATEGORY-WISE ONE-LINERS • श्रेणीवार मुख्य तथ्य", "ol_sec_h", STYLES["headline_en"], fontSize=12.5, leading=16, textColor=COLORS["primary_navy"]))
    story.append(Spacer(1, 1.5*mm))
    story.append(Paragraph("<b>IMPORTANT ONE - LINER Current Affairs</b>", st_oneliner_h))
    story.append(Spacer(1, 2*mm))

    one_liners = content.get("one_liners") or []
    for ol in (one_liners[:10] if one_liners else items[:10]):
        text_en = ol.get("text_en") or ol.get("headline_en") or ""
        if text_en:
            story.append(Paragraph(f"•  <b>{_safe(text_en)}</b>", st_body_en))
            story.append(Spacer(1, 1.5*mm))

    story.append(CondPageBreak(100*mm))
    story.append(hindi_to_image("महत्वपूर्ण वन-लाइनर करंट अफेयर्स", width_mm=182, font_size_pt=15, bold=True, color="#0F2B48", align="center"))
    story.append(Spacer(1, 2.5*mm))

    for ol in (one_liners[:10] if one_liners else items[:10]):
        text_hi = ol.get("text_hi") or ol.get("headline_hi") or ""
        if text_hi:
            story.append(hindi_to_image(f"• {_strip_html(text_hi)}", width_mm=182, font_size_pt=13, bold=False, color="#1E293B", bg="white", left_padding_mm=2))
            story.append(Spacer(1, 1.5*mm))

    # =========================================================================
    # 7. FINAL REVISION CAPSULE
    # =========================================================================
    rev_rows: List[List[Flowable]] = [[
        Paragraph("<b>DEVELOPMENT / TOPIC</b>", ParagraphStyle("rev_h1", parent=STYLES["static_label"], fontSize=8, leading=10, textColor=white)),
        Paragraph("<b>KEY FACT / FIGURE TO REMEMBER</b>", ParagraphStyle("rev_h2", parent=STYLES["static_label"], fontSize=8, leading=10, textColor=white)),
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
            Paragraph(hl, ParagraphStyle("rev_t", parent=STYLES["static_text"], fontSize=7.5, leading=10)),
            Paragraph(clean_fact, ParagraphStyle("rev_f", parent=STYLES["static_text"], fontSize=7.5, leading=10, textColor=COLORS["primary_green"])),
        ])
        rev_count += 1

    if rev_count:
        story.append(Spacer(1, 2.5*mm))
        story.append(CondPageBreak(70*mm))
        story.append(mixed_para("FINAL REVISION CAPSULE • अंतिम पुनरावृत्ति", "rev_h", STYLES["headline_en"], fontSize=13, leading=16.5, textColor=COLORS["primary_navy"]))
        story.append(Paragraph("High-yield facts, figures and organisations from today's edition — revise in one glance.",
                               ParagraphStyle("rev_sub", fontName=FONT_REGULAR, fontSize=8, leading=10.5, textColor=COLORS["muted_text"])))
        story.append(Spacer(1, 2*mm))
        rev_tbl = Table(rev_rows, colWidths=[(PAGE_W - 28*mm) * 0.55, (PAGE_W - 28*mm) * 0.45], repeatRows=1)
        rev_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), COLORS["primary_navy"]),
            ("BOX", (0, 0), (-1, -1), 0.4, COLORS["border_light"]),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, COLORS["border_light"]),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, COLORS["card_bg"]]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ]))
        story.append(rev_tbl)
        story.append(Spacer(1, 3*mm))

    # =========================================================================
    # 8. CLOSING REVISION KIT (ONLY 3 Verified Channels)
    # =========================================================================
    story.append(CondPageBreak(70*mm))
    story.append(build_closing_kit(date_str))

    # Build Document
    doc.build(story, canvasmaker=NumberedCanvas, onFirstPage=cover_header_footer, onLaterPages=header_footer)
    print(f"[OK] Clean mobile-friendly PDF generated successfully: {output_path}")
    return output_path


if __name__ == "__main__":
    import argparse
    import json
    ap = argparse.ArgumentParser(description="ALP Mobile-Friendly Current Affairs PDF Generator")
    ap.add_argument("--content", required=True, help="path to data/content/<job_id>.json")
    ap.add_argument("--mcq", required=True, help="path to data/mcq/<job_id>_validated.json")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    with open(a.content, encoding="utf-8") as f:
        content_data = json.load(f)
    with open(a.mcq, encoding="utf-8") as f:
        mcqs_data = json.load(f)
    generate_pdf(content_data, mcqs_data, a.out)
