#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AGRI LEARNING POINT - Premium Daily Current Affairs PDF Generator
Bilingual Edition - 04 October 2026 Sample
Design: Premium colourful magazine, mobile-friendly, exam-oriented
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, HRFlowable, Image, Frame, PageTemplate, NextPageTemplate
)
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, Circle, String as ShapeString, Rect
from reportlab.graphics.charts.textlabels import Label
import textwrap
from PIL import Image as PILImage, ImageDraw, ImageFont
import hashlib

# --- HINDI RENDERING HELPER (Perfect Devanagari via Pillow + HarfBuzz) ---
def hindi_to_image(text, width_mm=170, font_size_pt=8.5, bold=False, color="#212121", bg="white", line_spacing=1.35, align="left", left_padding_mm=0):
    HINDI_FONT_PATH = os.path.join(FONTS_DIR, "Mukta-Regular.ttf")
    HINDI_FONT_BOLD_PATH = os.path.join(FONTS_DIR, "Mukta-Bold.ttf")
    try:
        dpi = 300
        width_px = int(width_mm * dpi / 25.4)
        font_size_px = int(font_size_pt * dpi / 72 * 1.1)
        font_path = HINDI_FONT_BOLD_PATH if bold else HINDI_FONT_PATH
        if not os.path.exists(font_path):
            font_path = HINDI_FONT_PATH
        font = ImageFont.truetype(font_path, font_size_px)
        import re
        # Strip HTML tags like <b>, </b>, <font>, etc. for image rendering
        text = re.sub(r'<[^>]+>', '', text)
        text = text.replace("&nbsp;", " ").strip()
        def hex_to_rgb(h):
            if h.lower() == "white":
                return (255, 255, 255)
            if h.lower() == "transparent":
                return (255, 255, 255)
            h = h.lstrip("#")
            if len(h) == 3:
                h = "".join([c*2 for c in h])
            # Handle named colors fallback
            try:
                return tuple(int(h[i:i+2], 16) for i in (0,2,4))
            except:
                return (255,255,255)
        text_color = hex_to_rgb(color)
        bg_color = hex_to_rgb(bg)
        dummy = PILImage.new("RGB", (width_px, 100), bg_color)
        draw_dummy = ImageDraw.Draw(dummy)
        words = text.split()
        lines = []
        current = ""
        for word in words:
            test = current + " " + word if current else word
            try:
                w = draw_dummy.textlength(test, font=font, language="hi", features=["liga", "kern"])
            except:
                w = font.getlength(test)
            if w <= (width_px - left_padding_mm * dpi/25.4 - 4):
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
        line_height_px = int(font_size_px * line_spacing)
        height_px = line_height_px * len(lines) + 8
        img = PILImage.new("RGB", (width_px, height_px), bg_color)
        draw = ImageDraw.Draw(img)
        y = 4
        for line in lines:
            try:
                line_w = draw.textlength(line, font=font, language="hi", features=["liga"])
            except:
                line_w = font.getlength(line)
            if align == "center":
                x = (width_px - line_w) // 2
            elif align == "right":
                x = width_px - line_w - 6
            else:
                x = int(left_padding_mm * dpi/25.4) + 2
            try:
                draw.text((x, y), line, font=font, fill=text_color, language="hi", features=["liga", "kern"])
            except:
                draw.text((x, y), line, font=font, fill=text_color)
            y += line_height_px
        h = hashlib.md5(text.encode()).hexdigest()[:8]
        tmp_path = f"/tmp/hindi_{h}_{int(width_mm)}_{int(font_size_pt)}_{bold}.png"
        img.save(tmp_path, dpi=(dpi, dpi))
        from reportlab.platypus import Image as RLImage
        pdf_width = width_mm * mm
        pdf_height = (height_px / width_px) * pdf_width
        return RLImage(tmp_path, width=pdf_width, height=pdf_height)
    except Exception as e:
        print(f"Hindi image fallback for '{text[:20]}': {e}")
        return Paragraph(f'<font name="{FONT_HINDI}">{text}</font>', ParagraphStyle("fallback", parent=STYLES["body_hi"], fontName=FONT_HINDI, fontSize=font_size_pt, leading=font_size_pt*1.4, textColor=HexColor(color)))


# --- PATHS ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# FIX: fonts are in src/fonts (previous BASE_DIR/"fonts" path broke font registration -> Helvetica fallback)
FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- COLORS (Premium Palette) ---
COLORS = {
    "primary_green": HexColor("#1B5E20"),      # Deep Agri Green
    "light_green": HexColor("#E8F5E9"),
    "agri_accent": HexColor("#2E7D32"),
    "banking_blue": HexColor("#0D47A1"),
    "banking_light": HexColor("#E3F2FD"),
    "national_orange": HexColor("#E65100"),
    "national_light": HexColor("#FFF3E0"),
    "international_purple": HexColor("#4A148C"),
    "international_light": HexColor("#F3E5F5"),
    "economy_teal": HexColor("#006064"),
    "economy_light": HexColor("#E0F7FA"),
    "science_cyan": HexColor("#01579B"),
    "science_light": HexColor("#E1F5FE"),
    "environment_green": HexColor("#33691E"),
    "environment_light": HexColor("#F1F8E9"),
    "sports_red": HexColor("#B71C1C"),
    "sports_light": HexColor("#FFEBEE"),
    "awards_gold": HexColor("#F57F17"),
    "awards_light": HexColor("#FFF8E1"),
    "exam_yellow": HexColor("#FFF9C4"),
    "exam_yellow_border": HexColor("#FBC02D"),
    "mcq_green": HexColor("#2E7D32"),
    "dark_text": HexColor("#212121"),
    "medium_text": HexColor("#424242"),
    "light_text": HexColor("#757575"),
    "border_grey": HexColor("#E0E0E0"),
    "cover_bg": HexColor("#FAFAFA"),
    "header_bg": HexColor("#1B5E20"),
}

CATEGORY_STYLE = {
    "agriculture": {"color": COLORS["agri_accent"], "light": COLORS["light_green"], "icon": "", "label": "AGRICULTURE & ALLIED"},
    "banking": {"color": COLORS["banking_blue"], "light": COLORS["banking_light"], "icon": "", "label": "BANKING & FINANCE"},
    "national": {"color": COLORS["national_orange"], "light": COLORS["national_light"], "icon": "", "label": "NATIONAL AFFAIRS"},
    "international": {"color": COLORS["international_purple"], "light": COLORS["international_light"], "icon": "", "label": "INTERNATIONAL AFFAIRS"},
    "economy": {"color": COLORS["economy_teal"], "light": COLORS["economy_light"], "icon": "", "label": "ECONOMY"},
    "science": {"color": COLORS["science_cyan"], "light": COLORS["science_light"], "icon": "", "label": "SCIENCE & TECHNOLOGY"},
    "environment": {"color": COLORS["environment_green"], "light": COLORS["environment_light"], "icon": "", "label": "ENVIRONMENT & CLIMATE"},
    "sports": {"color": COLORS["sports_red"], "light": COLORS["sports_light"], "icon": "", "label": "SPORTS"},
    "important_days": {"color": HexColor("#6A1B9A"), "light": HexColor("#F3E5F5"), "icon": "", "label": "IMPORTANT DAYS"},
}

# --- FONTS ---
def register_fonts():
    try:
        pdfmetrics.registerFont(TTFont('Poppins', os.path.join(FONTS_DIR, 'Poppins-Regular.ttf')))
        pdfmetrics.registerFont(TTFont('Poppins-SemiBold', os.path.join(FONTS_DIR, 'Poppins-SemiBold.ttf')))
        pdfmetrics.registerFont(TTFont('Poppins-Bold', os.path.join(FONTS_DIR, 'Poppins-Bold.ttf')))
        pdfmetrics.registerFont(TTFont('Mukta', os.path.join(FONTS_DIR, 'Mukta-Regular.ttf')))
        pdfmetrics.registerFont(TTFont('Mukta-Bold', os.path.join(FONTS_DIR, 'Mukta-Bold.ttf')))
        print("✓ Fonts registered: Poppins + Mukta")
        return True
    except Exception as e:
        raise RuntimeError(f"FATAL: required fonts (Poppins+Mukta) could not be registered from {FONTS_DIR}: {e}. "
                           f"Production PDF must never silently fall back to Helvetica (breaks Hindi).")

FONTS_OK = register_fonts()

# Helper to get font names
FONT_REGULAR = 'Poppins' if FONTS_OK else 'Helvetica'
FONT_BOLD = 'Poppins-Bold' if FONTS_OK else 'Helvetica-Bold'
FONT_SEMI = 'Poppins-SemiBold' if FONTS_OK else 'Helvetica-Bold'
FONT_HINDI = 'Mukta' if FONTS_OK else 'Helvetica'
FONT_HINDI_BOLD = 'Mukta-Bold' if FONTS_OK else 'Helvetica-Bold'

PAGE_W, PAGE_H = A4

# --- STYLES ---
def get_styles():
    styles = getSampleStyleSheet()
    
    s_cover_title = ParagraphStyle('CoverTitle', parent=styles['Normal'], fontName=FONT_BOLD, fontSize=34, leading=38, textColor=COLORS["primary_green"], alignment=TA_CENTER, spaceAfter=4)
    s_cover_sub = ParagraphStyle('CoverSub', parent=styles['Normal'], fontName=FONT_SEMI, fontSize=14, leading=18, textColor=COLORS["medium_text"], alignment=TA_CENTER, spaceAfter=2)
    s_cover_date = ParagraphStyle('CoverDate', parent=styles['Normal'], fontName=FONT_BOLD, fontSize=13, leading=16, textColor=white, alignment=TA_CENTER)
    s_section_banner = ParagraphStyle('SectionBanner', parent=styles['Normal'], fontName=FONT_BOLD, fontSize=16, leading=19, textColor=white, alignment=TA_LEFT)
    s_headline_en = ParagraphStyle('HeadlineEN', parent=styles['Normal'], fontName=FONT_BOLD, fontSize=18, leading=23, textColor=COLORS["dark_text"], alignment=TA_LEFT, spaceAfter=3, spaceBefore=8)
    s_headline_hi = ParagraphStyle('HeadlineHI', parent=styles['Normal'], fontName=FONT_HINDI_BOLD, fontSize=17, leading=22, textColor=COLORS["medium_text"], alignment=TA_LEFT, spaceAfter=6)
    s_body_en = ParagraphStyle('BodyEN', parent=styles['Normal'], fontName=FONT_REGULAR, fontSize=12, leading=16, textColor=COLORS["dark_text"], alignment=TA_LEFT, spaceAfter=3, bulletIndent=10, leftIndent=14)
    s_body_hi = ParagraphStyle('BodyHI', parent=styles['Normal'], fontName=FONT_HINDI, fontSize=12.5, leading=16.5, textColor=HexColor("#333333"), alignment=TA_LEFT, spaceAfter=3, bulletIndent=10, leftIndent=14)
    s_static_label = ParagraphStyle('StaticLabel', parent=styles['Normal'], fontName=FONT_BOLD, fontSize=9, leading=11, textColor=white, alignment=TA_CENTER)
    s_static_text = ParagraphStyle('StaticText', parent=styles['Normal'], fontName=FONT_REGULAR, fontSize=11.5, leading=15, textColor=COLORS["dark_text"], alignment=TA_LEFT)
    s_exam_fact = ParagraphStyle('ExamFact', parent=styles['Normal'], fontName=FONT_SEMI, fontSize=12.5, leading=16, textColor=HexColor("#5D4037"), alignment=TA_LEFT)
    s_mcq_q = ParagraphStyle('MCQQ', parent=styles['Normal'], fontName=FONT_BOLD, fontSize=12.5, leading=16, textColor=COLORS["dark_text"], alignment=TA_LEFT, spaceAfter=5)
    s_mcq_opt = ParagraphStyle('MCQOpt', parent=styles['Normal'], fontName=FONT_REGULAR, fontSize=11.5, leading=15, textColor=COLORS["dark_text"], alignment=TA_LEFT, leftIndent=14, spaceAfter=2)
    s_mcq_ans = ParagraphStyle('MCQAns', parent=styles['Normal'], fontName=FONT_BOLD, fontSize=11.5, leading=15, textColor=white, alignment=TA_LEFT)
    s_mcq_exp = ParagraphStyle('MCQExp', parent=styles['Normal'], fontName=FONT_REGULAR, fontSize=11, leading=14.5, textColor=COLORS["medium_text"], alignment=TA_LEFT, spaceAfter=3)
    s_one_liner = ParagraphStyle('OneLiner', parent=styles['Normal'], fontName=FONT_REGULAR, fontSize=11.5, leading=15, textColor=COLORS["dark_text"], alignment=TA_LEFT, leftIndent=12, spaceAfter=3, bulletIndent=6)
    s_footer = ParagraphStyle('Footer', parent=styles['Normal'], fontName=FONT_REGULAR, fontSize=9, leading=11, textColor=white, alignment=TA_CENTER)
    s_header = ParagraphStyle('Header', parent=styles['Normal'], fontName=FONT_BOLD, fontSize=9, leading=11, textColor=white, alignment=TA_CENTER)
    s_cover_tag = ParagraphStyle('CoverTag', parent=styles['Normal'], fontName=FONT_SEMI, fontSize=7, leading=9, textColor=COLORS["primary_green"], alignment=TA_CENTER)
    return {
        'cover_title': s_cover_title,
        'cover_sub': s_cover_sub,
        'cover_date': s_cover_date,
        'section_banner': s_section_banner,
        'headline_en': s_headline_en,
        'headline_hi': s_headline_hi,
        'body_en': s_body_en,
        'body_hi': s_body_hi,
        'static_label': s_static_label,
        'static_text': s_static_text,
        'exam_fact': s_exam_fact,
        'mcq_q': s_mcq_q,
        'mcq_opt': s_mcq_opt,
        'mcq_ans': s_mcq_ans,
        'mcq_exp': s_mcq_exp,
        'one_liner': s_one_liner,
        'footer': s_footer,
        'header': s_header,
        'cover_tag': s_cover_tag,
    }

STYLES = get_styles()

# --- HEADER / FOOTER / WATERMARK ---
def header_footer(canvas, doc):
    canvas.saveState()
    page_num = canvas.getPageNumber()
    
    # Header bar
    canvas.setFillColor(COLORS["header_bg"])
    canvas.rect(0, PAGE_H - 22*mm, PAGE_W, 10*mm, fill=1, stroke=0)
    
    # Header text
    canvas.setFillColor(white)
    canvas.setFont(FONT_BOLD, 8)
    canvas.drawCentredString(PAGE_W/2, PAGE_H - 15*mm, "AGRI LEARNING POINT  |  DAILY CURRENT AFFAIRS  |  BY SATYAM SIR")
    canvas.setFont(FONT_REGULAR, 6)
    canvas.drawCentredString(PAGE_W/2, PAGE_H - 18*mm, "AGTA  •  AFO  •  NABARD  •  FCI  •  ICAR  •  Agriculture & Banking Aspirants")
    
    # Logo placeholder circle on header
    canvas.setFillColor(HexColor("#2E7D32"))
    canvas.circle(18*mm, PAGE_H - 15*mm, 5*mm, fill=1, stroke=0)
    canvas.setFillColor(white)
    canvas.setFont(FONT_BOLD, 7)
    canvas.drawCentredString(18*mm, PAGE_H - 14*mm, "A")
    canvas.setFont(FONT_REGULAR, 3.5)
    canvas.drawCentredString(18*mm, PAGE_H - 16.2*mm, "ALP")
    
    # Footer bar
    canvas.setFillColor(COLORS["header_bg"])
    canvas.rect(0, 0, PAGE_W, 9*mm, fill=1, stroke=0)
    canvas.setFillColor(white)
    canvas.setFont(FONT_REGULAR, 6)
    canvas.setFont(FONT_REGULAR, 7)
    canvas.drawCentredString(PAGE_W/2 - 20*mm, 5*mm, "Agri Learning Point  |  BY SATYAM SIR")
    canvas.setFont(FONT_REGULAR, 6)
    canvas.drawCentredString(PAGE_W/2 - 20*mm, 2.8*mm, "Telegram: @agrilearningpoint")
    canvas.setFont(FONT_BOLD, 6)
    canvas.setFont(FONT_REGULAR, 9)
    canvas.drawRightString(PAGE_W - 12*mm, 4*mm, f"Page {page_num}")
    
    # Watermark PNG - AGRI LEARNING POINT Logo (user logo - centred, faded)
    try:
        watermark_path = os.path.join(BASE_DIR, "assets", "watermark_logo.png")
        if os.path.exists(watermark_path):
            canvas.saveState()
            canvas.setFillAlpha(0.09)
            # Draw logo centred, large but faded (single logo, not tiled)
            # Centre of page
            wm_size = 90*mm
            wm_x = (PAGE_W - wm_size)/2
            wm_y = (PAGE_H - wm_size)/2 + 5*mm
            canvas.drawImage(watermark_path, wm_x, wm_y, width=wm_size, height=wm_size, preserveAspectRatio=True, mask='auto')
            canvas.restoreState()
    except Exception as e:
        # Fallback to text watermark
        canvas.setFillColor(HexColor("#E8F5E9"))
        canvas.setFont(FONT_BOLD, 60)
        canvas.saveState()
        canvas.setFillAlpha(0.09)
        canvas.rotate(30)
        canvas.drawString(40*mm, -10*mm, "AGRI LEARNING POINT")
        canvas.restoreState()
    
    # Double border - Red outer + Green inner (professional double line)
    canvas.setStrokeColor(HexColor("#B71C1C"))  # Red outer
    canvas.setLineWidth(1.2)
    canvas.rect(5*mm, 10*mm, PAGE_W - 10*mm, PAGE_H - 32*mm, fill=0, stroke=1)
    canvas.setStrokeColor(HexColor("#1B5E20"))  # Green inner
    canvas.setLineWidth(0.8)
    canvas.rect(6.5*mm, 11.5*mm, PAGE_W - 13*mm, PAGE_H - 35*mm, fill=0, stroke=1)
    
    canvas.restoreState()

def cover_header_footer(canvas, doc):
    # No header/footer on cover - clean
    canvas.saveState()
    # Watermark PNG on cover too - same logo, slightly lighter
    try:
        watermark_path = os.path.join(BASE_DIR, "assets", "watermark_logo.png")
        if os.path.exists(watermark_path):
            canvas.saveState()
            canvas.setFillAlpha(0.09)
            wm_size = 100*mm
            wm_x = (PAGE_W - wm_size)/2
            wm_y = (PAGE_H - wm_size)/2
            canvas.drawImage(watermark_path, wm_x, wm_y, width=wm_size, height=wm_size, preserveAspectRatio=True, mask='auto')
            canvas.restoreState()
    except:
        canvas.setFillColor(HexColor("#E8F5E9"))
        canvas.setFont(FONT_BOLD, 70)
        canvas.setFillAlpha(0.06)
        canvas.saveState()
        canvas.rotate(30)
        canvas.drawString(30*mm, 10*mm, "AGRI LEARNING POINT")
        canvas.restoreState()
    canvas.restoreState()

# --- HELPER COMPONENTS ---

def section_banner(category_key, number="01"):
    cat = CATEGORY_STYLE[category_key]
    # Create a table as banner
    banner_data = [
        [Paragraph(f'<font color="white"><b>{cat["icon"]}  {cat["label"]}</b></font>', STYLES['section_banner']),
         Paragraph(f'<font color="white" size="9"><b>{number}</b></font>', ParagraphStyle('num', parent=STYLES['section_banner'], alignment=TA_CENTER, fontSize=9, leading=11))]
    ]
    t = Table(banner_data, colWidths=[PAGE_W - 34*mm, 18*mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), cat["color"]),
        ('BACKGROUND', (1,0), (1,0), HexColor("#212121")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('ROUNDEDCORNERS', [3,3,3,3]),
    ]))
    return t

def exam_fact_box(text_en, text_hi=None):
    # Yellow highlight box
    content = []
    content.append(Paragraph('<b><font color="#F57F17">  ▶ EXAM FACT • परीक्षा तथ्य</font></b>', ParagraphStyle('ef_head', parent=STYLES['exam_fact'], textColor=COLORS["awards_gold"], fontSize=11, leading=13, spaceAfter=4)))
    content.append(Paragraph(text_en, STYLES['exam_fact']))
    if text_hi:
        try:
            ef_img = hindi_to_image(text_hi, width_mm=(PAGE_W/mm - 32), font_size_pt=12.5, bold=False, color="#4E342E", bg="#FFF9C4")
            content.append(ef_img)
        except Exception as e:
            content.append(Paragraph(f'<font name="{FONT_HINDI}" size="12.5">{text_hi}</font>', ParagraphStyle('ef_hi', parent=STYLES['exam_fact'], fontName=FONT_HINDI, fontSize=12.5, leading=16, textColor=HexColor("#4E342E"))))
    
    inner = Table([[content]], colWidths=[PAGE_W - 30*mm])
    inner.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLORS["exam_yellow"]),
        ('BOX', (0,0), (-1,-1), 0.6, COLORS["exam_yellow_border"]),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('ROUNDEDCORNERS', [3,3,3,3]),
    ]))
    # Left accent
    outer = Table([[Paragraph('<font color="#FBC02D">▐</font>', ParagraphStyle('accent', parent=STYLES['exam_fact'], textColor=COLORS["exam_yellow_border"], fontSize=18, leading=18)), inner]], colWidths=[4*mm, PAGE_W - 30*mm])
    outer.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    return outer

def static_facts_table(facts_dict):
    # facts_dict: {label: value}
    rows = []
    for k,v in facts_dict.items():
        rows.append([
            Paragraph(f'<b><font color="white">{k}</font></b>', STYLES['static_label']),
            Paragraph(v, STYLES['static_text'])
        ])
    # Build table with 2 rows per line? For compact, use 2 column pairs if many
    # Single column table for simplicity
    t = Table(rows, colWidths=[28*mm, PAGE_W - 58*mm])
    style = [
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('GRID', (0,0), (-1,-1), 0.4, white),
        ('BACKGROUND', (0,0), (0,-1), COLORS["agri_accent"]),
        ('BACKGROUND', (1,0), (1,-1), HexColor("#F9FBE7")),
        ('ROUNDEDCORNERS', [2,2,2,2]),
    ]
    t.setStyle(TableStyle(style))
    # Wrap with header
    header = Paragraph('<b><font color="#1B5E20" size="10">STATIC FACTS • स्थैतिक तथ्य</font></b>', ParagraphStyle('sf_head', parent=STYLES['static_text'], alignment=TA_LEFT, spaceAfter=5, textColor=COLORS["primary_green"], fontSize=10, leading=13))
    return [header, t]

def news_card(headline_en, headline_hi, category_key, key_points_en, key_points_hi, static_facts, exam_fact_en, exam_fact_hi, source, image_path=None, image_caption=None, image_note=None):
    # Returns list of flowables for one news item
    cat = CATEGORY_STYLE.get(category_key, CATEGORY_STYLE["national"])
    story = []
    
    # Headline with left color border
    hl_en = Paragraph(f'<b>{headline_en}</b>', STYLES['headline_en'])
    try:
        hl_hi = hindi_to_image(headline_hi, width_mm=(PAGE_W/mm - 30), font_size_pt=17, bold=True, color="#424242", bg="white")
    except Exception as e:
        hl_hi = Paragraph(f'<font name="{FONT_HINDI}">{headline_hi}</font>', STYLES['headline_hi'])
    
    # Headline block with left accent
    hl_table = Table([
        [Paragraph(f'<font color="{cat["color"].hexval()}">█</font>', ParagraphStyle('accent', parent=STYLES['headline_en'], textColor=cat["color"], fontSize=20, leading=20)), 
         [hl_en, hl_hi]]
    ], colWidths=[4*mm, PAGE_W - 30*mm])
    hl_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 1),
        ('RIGHTPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 1),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
    ]))
    story.append(hl_table)
    story.append(Spacer(1, 2*mm))
    
    # Real image - editorial style, full width with subtle caption
    if image_path and os.path.exists(image_path):
        try:
            from PIL import Image as PILImg
            pil = PILImg.open(image_path)
            iw, ih = pil.size
            aspect = ih / iw if iw else 0.6
            max_h_mm = 62  # mobile-friendly larger image
            w_mm = PAGE_W/mm - 26
            h_mm = w_mm * aspect
            if h_mm > max_h_mm:
                h_mm = max_h_mm
                w_mm = h_mm / aspect if aspect else w_mm
            rl_img = Image(image_path, width=w_mm*mm, height=h_mm*mm)
            img_table = Table([[rl_img]], colWidths=[PAGE_W - 26*mm])
            img_table.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
                ('RIGHTPADDING', (0,0), (-1,-1), 0),
                ('TOPPADDING', (0,0), (-1,-1), 0),
                ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                ('BOX', (0,0), (-1,-1), 0.4, HexColor("#E0E0E0")),
            ]))
            story.append(img_table)
            if image_caption:
                cap = Paragraph(f'<font color="#757575" size="9"><i>{image_caption}</i></font>', ParagraphStyle('cap', parent=STYLES['static_text'], alignment=TA_CENTER, textColor=COLORS["light_text"], fontSize=9, leading=11, spaceBefore=2))
                story.append(cap)
            story.append(Spacer(1, 2*mm))
        except Exception as e:
            print(f"Image embed failed {image_path}: {e}")
            if image_note:
                story.append(Paragraph(f'<font color="#757575" size="5"><i>{image_note}</i></font>', ParagraphStyle('img_fallback', parent=STYLES['static_text'], alignment=TA_CENTER, textColor=COLORS["light_text"])))
                story.append(Spacer(1, 2*mm))
    elif image_note:
        story.append(Paragraph(f'<font color="#757575" size="5"><i>{image_note}</i></font>', ParagraphStyle('img_fallback2', parent=STYLES['static_text'], alignment=TA_CENTER, textColor=COLORS["light_text"])))
        story.append(Spacer(1, 2*mm))

    story.append(Paragraph('<b><font color="#1B5E20">Key Points  •  मुख्य बिंदु</font></b>', ParagraphStyle('kp_head', parent=STYLES['body_en'], fontName=FONT_BOLD, fontSize=13, leading=17, textColor=COLORS["primary_green"], spaceAfter=4, spaceBefore=4)))
    
    # Bilingual paired (English + Hindi below, no labels) - human editorial style
    for en, hi in zip(key_points_en, key_points_hi):
      # English bullet - clean, professional
      story.append(Paragraph(f'•  {en}', STYLES['body_en']))
      # Hindi translation directly below, slightly indented, softer color, perfect Devanagari via image
      try:
          hi_clean = re.sub(r'<[^>]+>', '', hi).strip()
          hi_img = hindi_to_image(hi_clean, width_mm=(PAGE_W/mm - 28), font_size_pt=12.5, bold=False, color="#616161", bg="white", left_padding_mm=4)
          story.append(hi_img)
      except Exception as e:
          story.append(Paragraph(f'<font name="{FONT_HINDI}" size="12.5">{hi}</font>', ParagraphStyle('hi_fallback', parent=STYLES['body_hi'], fontSize=12.5, leading=16.5, textColor=HexColor("#616161"), leftIndent=10)))
      story.append(Spacer(1, 1.2*mm))    
    story.append(Spacer(1, 2*mm))
    
    # Static Facts
    if static_facts:
        for item in static_facts_table(static_facts):
            story.append(item)
        story.append(Spacer(1, 2*mm))
    
    # Exam Fact
    story.append(exam_fact_box(exam_fact_en, exam_fact_hi))
    story.append(Spacer(1, 2*mm))
    
    # Source
    story.append(HRFlowable(width="100%", thickness=0.3, color=COLORS["border_grey"], spaceAfter=4, spaceBefore=4))
    
    # MOBILE: Don't wrap entire news in outer Table (too tall ~778pt > 725pt frame with 12pt fonts) - allow natural page split
    # Instead add a subtle top accent line and return story directly for smart splitting
    # Add a light separator at start to indicate card boundary
    # Insert a thin top border via HR at start of story (already have headline accent)
    # Return flowables directly - reportlab will split naturally across pages, avoiding orphan via KeepTogether on heading block only
    story.append(Spacer(1, 1*mm))
    story.append(HRFlowable(width="100%", thickness=0.6, color=cat["light"], spaceAfter=4*mm, spaceBefore=2*mm))
    # Keep headline+image+first key point together to avoid orphan (wrap that small part in KeepTogether)
    # But for now return as is - the headline table + image + first 2 points will naturally stay together if space, else will move
    return story

def mcq_block(q_num, question_en, question_hi, options_en, correct, explanation_en, explanation_hi, exam_point):
    story = []
    q_title = Paragraph(f'<b>Q{q_num}.  {question_en}</b>', STYLES['mcq_q'])
    try:
        q_title_hi = hindi_to_image(question_hi, width_mm=(PAGE_W/mm - 26), font_size_pt=12.5, bold=False, color="#424242", bg="white")
    except Exception as e:
        q_title_hi = Paragraph(f'<font name="{FONT_HINDI}">{question_hi}</font>', ParagraphStyle('q_hi', parent=STYLES['mcq_q'], fontName=FONT_HINDI, fontSize=12.5, leading=16, textColor=COLORS["medium_text"]))
    story.append(q_title)
    story.append(q_title_hi)
    story.append(Spacer(1, 1.5*mm))
    for idx, opt in enumerate(options_en):
        label = chr(65+idx)
        is_correct = label == correct
        # Highlight correct differently? But show all normally, answer below
        story.append(Paragraph(f'<b>{label})</b>  {opt}', STYLES['mcq_opt']))
    story.append(Spacer(1, 2*mm))
    # Answer box
    ans_data = [[Paragraph(f'<b>[OK]  Correct Answer: {correct}) {options_en[ord(correct)-65]}</b>', STYLES['mcq_ans'])]]
    ans_table = Table(ans_data, colWidths=[PAGE_W - 30*mm])
    ans_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLORS["mcq_green"]),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('ROUNDEDCORNERS', [3,3,3,3]),
    ]))
    story.append(ans_table)
    story.append(Spacer(1, 1.5*mm))
    story.append(Paragraph(f'<b><font color="#0D47A1" size="11">▶ Explanation:</font></b>', ParagraphStyle('exp_head', parent=STYLES['mcq_exp'], fontSize=11, leading=14, textColor=COLORS["banking_blue"])))
    story.append(Paragraph(explanation_en, STYLES['mcq_exp']))
    try:
        exp_hi_img = hindi_to_image(explanation_hi, width_mm=(PAGE_W/mm - 26), font_size_pt=11, bold=False, color="#424242", bg="white")
        story.append(exp_hi_img)
    except Exception as e:
        story.append(Paragraph(f'<font name="{FONT_HINDI}">{explanation_hi}</font>', ParagraphStyle('exp_hi', parent=STYLES['mcq_exp'], fontName=FONT_HINDI, fontSize=11, leading=14.5)))
    story.append(Spacer(1, 1*mm))
    story.append(Paragraph(f'<b><font color="#F57F17" size="11">  ▶ Exam Point:</font></b> <font size="11">{exam_point}</font>', ParagraphStyle('ep', parent=STYLES['mcq_exp'], fontSize=11, leading=14.5)))
    story.append(HRFlowable(width="100%", thickness=0.3, color=COLORS["border_grey"], spaceAfter=3, spaceBefore=3))
    return story

# --- DYNAMIC PDF BUILDER (data-driven; no hardcoded content) ---
CAT_MAP = {
    "Agriculture": "agriculture", "Banking & Finance": "banking", "Economy": "economy",
    "Government Schemes": "national", "National": "national", "International": "international",
    "Science & Technology": "science", "Environment": "environment", "Sports": "sports",
    "Important Days": "important_days", "Awards": "awards_gold" , "Appointments": "national",
}

def _safe(s):
    """Escape XML-unsafe chars for ReportLab paragraphs."""
    return (str(s) or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def generate_pdf(content, mcqs, output_path=None):
    """Build the premium bilingual edition from pipeline JSON data.
    content = {"job": {...}, "items": [news entries]} ; mcqs = validated MCQ list.
    Refuses empty editions (never publish an empty/filler PDF — MASTER_RULE)."""
    items = content.get("items", [])
    if not items:
        raise ValueError("REFUSING to build PDF: 0 selected news items (quality gate, never fill/invent)")
    job = content.get("job", {})
    date_str = job.get("date_display", "")
    jtype = job.get("type", "daily")
    label = {"daily": "Daily Current Affairs", "weekly": "Weekly Best-of Current Affairs",
             "monthly": "Monthly Best-of Current Affairs"}[jtype]
    if output_path is None:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_path = os.path.join(OUTPUT_DIR, f"Agri Learning Point {date_str} {label} Mobile Bilingual FINAL.pdf")

    doc = SimpleDocTemplate(output_path, pagesize=A4, leftMargin=13*mm, rightMargin=13*mm,
                            topMargin=24*mm, bottomMargin=20*mm, title=f"ALP {date_str} {label}",
                            author="Agri Learning Point")
    story = []

    # ---------- COVER ----------
    logo = os.path.join(BASE_DIR, "assets", "logo.png")
    if os.path.exists(logo):
        story.append(Image(logo, width=38*mm, height=38*mm))
    story.append(Spacer(1, 6*mm))
    story.append(Paragraph("AGRI LEARNING POINT", STYLES["cover_title"]))
    story.append(Paragraph(_safe(f"{label} — {date_str}"), STYLES["cover_sub"]))
    story.append(Paragraph("बilingual • Mobile Friendly • Exam Oriented", STYLES["cover_sub"]))
    story.append(Paragraph("AGTA • AFO • NABARD • FCI • ICAR • IBPS PO/SO • RBI Assistant", STYLES["cover_tag"]))
    story.append(Spacer(1, 8*mm))
    top_items = sorted(items, key=lambda x: -x.get("importance_score", 0))
    hl_rows = [[Paragraph('<font color="white"><b>TODAY\u2019S HIGHLIGHTS</b></font>', ParagraphStyle("hlh", parent=STYLES["static_label"], fontSize=12, leading=15))]]
    for it in top_items[:8]:
        hl_rows.append([Paragraph(_safe(it["headline_en"].lstrip("> ")[:110]), ParagraphStyle("hl", parent=STYLES["static_text"], fontSize=11, leading=14))])
    t = Table(hl_rows, colWidths=[PAGE_W - 26*mm])
    t.setStyle(TableStyle([("BACKGROUND", (0,0), (0,0), COLORS["primary_green"]),
                           ("BOX", (0,0), (-1,-1), 1, COLORS["primary_green"]),
                           ("INNERGRID", (0,1), (-1,-1), 0.3, COLORS["border_grey"]),
                           ("LEFTPADDING", (0,0), (-1,-1), 8), ("RIGHTPADDING", (0,0), (-1,-1), 8),
                           ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5)]))
    story.append(t)
    story.append(Spacer(1, 10*mm))
    story.append(Paragraph("Telegram: @Agrikrishna  |  YouTube: Agri Learning Point", STYLES["cover_sub"]))
    story.append(PageBreak())

    # ---------- INDEX ----------
    story.append(Paragraph('<font color="#1B5E20"><b>INDEX • विषय-सूची</b></font>', ParagraphStyle("idx", parent=STYLES["headline_en"], fontSize=16)))
    by_cat = {}
    for it in items:
        by_cat.setdefault(CAT_MAP.get(it.get("category", "National"), "national"), []).append(it)
    n = 0
    idx_rows = []
    for ck, group in by_cat.items():
        banner = CATEGORY_STYLE.get(ck, CATEGORY_STYLE["national"])
        for g in group:
            n += 1
            idx_rows.append([str(n), _safe(g["headline_en"].lstrip("> ")[:95]), banner["label"]])
    idx_tbl = Table([[Paragraph(f'<b>{r[0]}</b>', STYLES["static_text"]), Paragraph(r[1], STYLES["static_text"]),
                      Paragraph(f'<font size="8" color="#757575">{r[2]}</font>', STYLES["static_text"])] for r in idx_rows],
                    colWidths=[10*mm, PAGE_W - 80*mm, 55*mm])
    idx_tbl.setStyle(TableStyle([("LINEBELOW", (0,0), (-1,-1), 0.25, COLORS["border_grey"]),
                                 ("TOPPADDING", (0,0), (-1,-1), 3), ("BOTTOMPADDING", (0,0), (-1,-1), 3)]))
    story.append(idx_tbl)
    story.append(PageBreak())

    # ---------- MOST IMPORTANT ONE-LINERS ----------
    story.append(Paragraph('<font color="#E65100"><b>MOST IMPORTANT TODAY • सबसे महत्वपूर्ण</b></font>',
                           ParagraphStyle("mi", parent=STYLES["headline_en"], fontSize=15)))
    for it in top_items[:12]:
        fact = next(iter(it.get("static_facts", {}).values()), "")
        line = it["headline_en"].lstrip("> ") + (f"  →  {_safe(fact)}" if fact else "")
        story.append(Paragraph(f"<bullet>•</bullet> {line}", STYLES["one_liner"]))
    story.append(PageBreak())

    # ---------- NEWS SECTIONS ----------
    sec_no = 0
    for ck, group in by_cat.items():
        sec_no += 1
        story.append(section_banner(ck, f"{sec_no:02d}"))
        story.append(Spacer(1, 3*mm))
        for it in group:
            blocks = news_card(
                headline_en=_safe(it["headline_en"]),
                headline_hi=it["headline_hi"],
                category_key=ck,
                key_points_en=[_safe(p) for p in it.get("key_points_en", [])],
                key_points_hi=it.get("key_points_hi", []),
                static_facts={_safe(k): _safe(v) for k, v in it.get("static_facts", {}).items()},
                exam_fact_en=_safe(it.get("exam_fact_en", "")),
                exam_fact_hi=it.get("exam_fact_hi", ""),
                source=_safe(it.get("source", {}).get("name", "")),
                image_path=it.get("image_path") or None,
                image_caption=_safe(it.get("image_caption", "")) or None,
            )
            story.extend(blocks)
            story.append(HRFlowable(width="100%", thickness=0.4, color=CATEGORY_STYLE.get(ck, CATEGORY_STYLE["national"])["color"], spaceAfter=6))
    story.append(PageBreak())

    # ---------- MCQs ----------
    story.append(Paragraph('<font color="#2E7D32"><b>MCQ PRACTICE • बहुविकल्पीय प्रश्न</b></font>',
                           ParagraphStyle("mcqh", parent=STYLES["headline_en"], fontSize=15)))
    story.append(Spacer(1, 3*mm))
    for m in mcqs:
        story.extend(mcq_block(m["q_num"], _safe(m["question_en"]), m["question_hi"],
                               [_safe(o) for o in m["options"]], m["correct"],
                               _safe(m["explanation_en"]), m["explanation_hi"], _safe(m.get("exam_point", ""))))
    story.append(PageBreak())

    # ---------- BACK COVER ----------
    story.append(Spacer(1, 40*mm))
    story.append(Paragraph("धन्यवाद ! मिलते हैं अगली डोज के साथ 🙏", ParagraphStyle("tc", parent=STYLES["cover_title"], fontSize=20)))
    story.append(Paragraph("Agri Learning Point — BY Satyam Sir", STYLES["cover_sub"]))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(f'© 2026 Agri Learning Point | Edition {date_str} | For educational purpose only.',
                           ParagraphStyle("copy", parent=STYLES["footer"], alignment=TA_CENTER, textColor=COLORS["light_text"], fontSize=5, leading=6)))

    doc.build(story, onFirstPage=cover_header_footer, onLaterPages=header_footer)
    print(f"[OK] PDF generated: {output_path}")
    return output_path


if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser(description="Dynamic ALP PDF generator (data-driven)")
    ap.add_argument("--content", required=True, help="path to data/content/<job_id>.json")
    ap.add_argument("--mcq", required=True, help="path to data/mcq/<job_id>_validated.json")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    with open(a.content, encoding="utf-8") as f:
        content = json.load(f)
    with open(a.mcq, encoding="utf-8") as f:
        mcqs = json.load(f)
    generate_pdf(content, mcqs, a.out)
