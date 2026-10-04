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
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
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
        print(f"Font registration fallback: {e}")
        # Fallback to Helvetica
        return False

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

# --- BUILD PDF ---

def build_pdf():
    output_path = os.path.join(OUTPUT_DIR, "Agri Learning Point 04 October 2026 Current Affairs Mobile Bilingual FINAL.pdf")
    
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=13*mm,
        rightMargin=13*mm,
        topMargin=24*mm,
        bottomMargin=13*mm,
        title="Agri Learning Point - Daily Current Affairs 03 Oct 2026 Bilingual",
        author="Agri Learning Point by Satyam Sir"
    )
    
    story = []
    
    # ===== COVER PAGE (Custom drawing via flowables) =====
    # We'll create cover as first page with large elements, then trigger page break and normal header/footer
    # Cover content
    # Logo large
    cover_style_title = STYLES['cover_title']
    cover_style_sub = STYLES['cover_sub']
    
    # Top badge
    story.append(Spacer(1, 8*mm))
    badge_data = [[Paragraph('<b><font color="white" size="7">  TRUSTED BY 50,000+ AGRI ASPIRANTS  •  AGTA | AFO | NABARD | FCI | ICAR</font></b>', ParagraphStyle('badge', parent=STYLES['footer'], alignment=TA_CENTER, textColor=white, fontSize=6.5, leading=7))]]
    badge_table = Table(badge_data, colWidths=[PAGE_W - 26*mm])
    badge_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLORS["primary_green"]),
        ('ROUNDEDCORNERS', [12,12,12,12]),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(badge_table)
    story.append(Spacer(1, 6*mm))
    
    # Big Logo Circle Simulation using Table
    logo_circle_data = [[Paragraph('<font color="white" size="22"><b>A</b></font><br/><font color="white" size="6">ALP</font>', ParagraphStyle('logo', parent=STYLES['cover_title'], textColor=white, alignment=TA_CENTER, leading=14, fontSize=22))]]
    logo_table = Table(logo_circle_data, colWidths=[22*mm])
    logo_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLORS["primary_green"]),
        ('ROUNDEDCORNERS', [20,20,20,20]),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('BOX', (0,0), (-1,-1), 2, HexColor("#A5D6A7")),
    ]))
    # Center logo
    centered_logo = Table([[logo_table]], colWidths=[PAGE_W - 20*mm])
    centered_logo.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
    story.append(centered_logo)
    story.append(Spacer(1, 4*mm))
    
    story.append(Paragraph('<b>AGRI LEARNING POINT</b>', ParagraphStyle('alp', parent=cover_style_title, fontSize=34, leading=36, textColor=COLORS["primary_green"], alignment=TA_CENTER, spaceAfter=2)))
    story.append(Paragraph('<b>BY SATYAM SIR</b>', ParagraphStyle('by', parent=cover_style_sub, fontSize=14, leading=16, textColor=COLORS["banking_blue"], alignment=TA_CENTER, spaceAfter=4)))
    story.append(HRFlowable(width="30%", thickness=1.2, color=COLORS["awards_gold"], spaceAfter=4, spaceBefore=2, hAlign='CENTER'))
    
    story.append(Paragraph('DAILY CURRENT AFFAIRS', ParagraphStyle('dca', parent=cover_style_title, fontSize=28, leading=30, textColor=HexColor("#212121"), alignment=TA_CENTER, spaceAfter=6)))
    story.append(Spacer(1, 4*mm))
    
    # Date Box Premium
    date_data = [[Paragraph('<b><font color="white" size="13">04 OCTOBER 2026</font></b><br/><font color="white" size="7">Saturday</font>', STYLES['cover_date'])]]
    date_table = Table(date_data, colWidths=[70*mm])
    date_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLORS["national_orange"]),
        ('ROUNDEDCORNERS', [6,6,6,6]),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('BOX', (0,0), (-1,-1), 1, HexColor("#FFCC80")),
    ]))
    centered_date = Table([[date_table]], colWidths=[PAGE_W - 20*mm])
    centered_date.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
    story.append(centered_date)
    story.append(Spacer(1, 6*mm))
    
    # Bilingual Edition Badge
    story.append(Paragraph('<b><font color="#1B5E20" size="11">━━━━━━━━  BILINGUAL EDITION  ━━━━━━━━</font></b>', ParagraphStyle('bilingual', parent=STYLES['cover_tag'], alignment=TA_CENTER, textColor=COLORS["primary_green"], fontSize=11, leading=13)))
    story.append(Spacer(1, 1.5*mm))
    story.append(Paragraph('Agriculture  •  Banking  •  National  •  International  •  Economy  •  Science  •  Environment', ParagraphStyle('cats', parent=STYLES['cover_tag'], fontSize=8, leading=10, textColor=COLORS["medium_text"], alignment=TA_CENTER)))
    story.append(Spacer(1, 6*mm))
    # Highlights box to fill page - human editorial touch
    highlights = [
        [Paragraph('<b><font color="#1B5E20" size="7">TODAY\'S HIGHLIGHTS</font></b>', ParagraphStyle('hl_head', parent=STYLES['cover_tag'], alignment=TA_CENTER, textColor=COLORS["primary_green"], fontSize=7, leading=8))],
        [Paragraph('<font color="#424242" size="6">• GOBARdhan Rs 23,731 Cr  •  Women Farmers Conference  •  RBI ED Appointment  •  Hockey Gold  •  Budget Rs 1.32 Lakh Cr</font>', ParagraphStyle('hl_text', parent=STYLES['cover_tag'], alignment=TA_CENTER, textColor=COLORS["medium_text"], fontSize=6, leading=7))],
    ]
    hl_table = Table(highlights, colWidths=[PAGE_W - 30*mm])
    hl_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), HexColor("#E8F5E9")),
        ('BACKGROUND', (0,1), (-1,1), white),
        ('BOX', (0,0), (-1,-1), 0.6, HexColor("#A5D6A7")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('ROUNDEDCORNERS', [4,4,4,4]),
    ]))
    story.append(hl_table)
    story.append(Spacer(1, 6*mm))
    
    # Cover visual - large green banner with icons
    visual_data = [
        [Paragraph('<font color="white" size="28"></font>', ParagraphStyle('v', parent=STYLES['cover_title'], alignment=TA_CENTER, textColor=white, fontSize=28)),
         Paragraph('<font color="white" size="28"></font>', ParagraphStyle('v2', parent=STYLES['cover_title'], alignment=TA_CENTER, textColor=white, fontSize=28)),
         Paragraph('<font color="white" size="28"></font>', ParagraphStyle('v3', parent=STYLES['cover_title'], alignment=TA_CENTER, textColor=white, fontSize=28)),
         Paragraph('<font color="white" size="28"></font>', ParagraphStyle('v4', parent=STYLES['cover_title'], alignment=TA_CENTER, textColor=white, fontSize=28)),
        ],
        [Paragraph('<font color="white" size="6"><b>AGRICULTURE</b></font>', ParagraphStyle('vl', parent=STYLES['footer'], alignment=TA_CENTER, textColor=white, fontSize=6)),
         Paragraph('<font color="white" size="6"><b>BANKING</b></font>', ParagraphStyle('vl2', parent=STYLES['footer'], alignment=TA_CENTER, textColor=white, fontSize=6)),
         Paragraph('<font color="white" size="6"><b>NATIONAL</b></font>', ParagraphStyle('vl3', parent=STYLES['footer'], alignment=TA_CENTER, textColor=white, fontSize=6)),
         Paragraph('<font color="white" size="6"><b>SCIENCE</b></font>', ParagraphStyle('vl4', parent=STYLES['footer'], alignment=TA_CENTER, textColor=white, fontSize=6)),
        ]
    ]
    visual_table = Table(visual_data, colWidths=[22*mm, 22*mm, 22*mm, 22*mm])
    visual_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLORS["primary_green"]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('ROUNDEDCORNERS', [6,6,6,6]),
        ('LINEBELOW', (0,0), (-1,0), 0.6, HexColor("#A5D6A7")),
    ]))
    centered_visual = Table([[visual_table]], colWidths=[PAGE_W - 20*mm])
    centered_visual.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
    story.append(centered_visual)
    story.append(Spacer(1, 8*mm))
    
    # Bottom cover info
    story.append(Paragraph('<b><font color="#212121" size="7">*  PREMIUM • COLOURFUL • EXAM-ORIENTED • RESEARCH-BASED  *</font></b>', ParagraphStyle('premium', parent=STYLES['cover_tag'], alignment=TA_CENTER, fontSize=7, leading=9, textColor=COLORS["dark_text"])))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph('<font color="#757575" size="6">Verified & Exam-Ready  •  Trusted by Aspirants</font>', ParagraphStyle('sources', parent=STYLES['cover_tag'], alignment=TA_CENTER, fontSize=6, leading=7, textColor=COLORS["light_text"])))
    story.append(Spacer(1, 6*mm))
    story.append(Paragraph('<font color="#B71C1C" size="6"><b>!  For AGTA • AFO • NABARD • FCI • ICAR • Banking & Govt Exams</b></font>', ParagraphStyle('exams', parent=STYLES['cover_tag'], alignment=TA_CENTER, textColor=COLORS["sports_red"], fontSize=6, leading=7)))
    
    # Cover footer small
    story.append(Spacer(1, 10*mm))
    story.append(Paragraph('<font color="#9E9E9E" size="5">Agri Learning Point  •  Daily Current Affairs  •  04 October 2026   •  Telegram: @agrilearningpoint</font>', ParagraphStyle('coverfoot', parent=STYLES['footer'], alignment=TA_CENTER, textColor=COLORS["light_text"], fontSize=5, leading=6)))
    story.append(Spacer(1, 3*mm))
    # Telegram and YouTube links - clickable, professional - First page only
    story.append(Paragraph('<font color="#0D47A1" size="7"><b>Join Us:</b></font>  <link href="https://web.telegram.org/k/#@agrilearningpoint" color="#0D47A1"><b>Telegram: @agrilearningpoint</b></link>  •  <link href="https://web.telegram.org/k/#@agriquizworld" color="#0D47A1"><b>@agriquizworld</b></link>', ParagraphStyle('links1', parent=STYLES['cover_tag'], alignment=TA_CENTER, textColor=COLORS["banking_blue"], fontSize=7, leading=9)))
    story.append(Spacer(1, 1*mm))
    story.append(Paragraph('<link href="https://youtube.com/@agrilearningpoint?si=-qubOyurUBMQk5ct" color="#B71C1C"><b>▶  YouTube: @agrilearningpoint</b></link>', ParagraphStyle('links2', parent=STYLES['cover_tag'], alignment=TA_CENTER, textColor=COLORS["sports_red"], fontSize=7, leading=9)))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph('<font color="#757575" size="5"><i>Scan QR or click links to join - Daily PDF, Quizzes & Updates</i></font>', ParagraphStyle('links3', parent=STYLES['cover_tag'], alignment=TA_CENTER, textColor=COLORS["light_text"], fontSize=5, leading=6)))
    story.append(Spacer(1, 6*mm))
    # Bottom fill bar - green strip to make page look full (professional footer)
    footer_bar = Table([[Paragraph('<font color="white" size="6"><b>DAILY FREE PDF  •  TELEGRAM  •  YOUTUBE  •  JOIN @agrilearningpoint  •  TRUSTED BY 50,000+ ASPIRANTS</b></font>', ParagraphStyle('footbar', parent=STYLES['cover_tag'], alignment=TA_CENTER, textColor=HexColor("#FFFFFF"), fontSize=6, leading=7))]], colWidths=[PAGE_W - 10*mm])
    footer_bar.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLORS["primary_green"]),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 2),
        ('RIGHTPADDING', (0,0), (-1,-1), 2),
        ('ROUNDEDCORNERS', [4,4,4,4]),
    ]))
    story.append(footer_bar)
    
    story.append(PageBreak())
    
    # ===== TABLE OF CONTENTS QUICK =====
    # We'll add a TOC box
    toc_title = Paragraph('<b><font color="#1B5E20" size="11">INSIDE THIS ISSUE</font></b>', ParagraphStyle('toc', parent=STYLES['headline_en'], alignment=TA_LEFT, textColor=COLORS["primary_green"], fontSize=11, leading=14, spaceAfter=4))
    story.append(toc_title)
    toc_data = [
        [Paragraph('<b>01</b>', ParagraphStyle('n', parent=STYLES['static_text'], alignment=TA_CENTER, textColor=white)), Paragraph('  Today\'s Most Important — 20 One-Liners', STYLES['static_text']), Paragraph('02', STYLES['static_text'])],
        [Paragraph('<b>02</b>', ParagraphStyle('n2', parent=STYLES['static_text'], alignment=TA_CENTER, textColor=white)), Paragraph('  Agriculture & Allied — 02 News', STYLES['static_text']), Paragraph('03', STYLES['static_text'])],
        [Paragraph('<b>03</b>', ParagraphStyle('n3', parent=STYLES['static_text'], alignment=TA_CENTER, textColor=white)), Paragraph('  Banking & Finance — 02 News', STYLES['static_text']), Paragraph('04', STYLES['static_text'])],
        [Paragraph('<b>04</b>', ParagraphStyle('n4', parent=STYLES['static_text'], alignment=TA_CENTER, textColor=white)), Paragraph('  National Affairs — Gandhi & Swachhata', STYLES['static_text']), Paragraph('06', STYLES['static_text'])],
        [Paragraph('<b>05</b>', ParagraphStyle('n5', parent=STYLES['static_text'], alignment=TA_CENTER, textColor=white)), Paragraph('  +  Economy +  Environment', STYLES['static_text']), Paragraph('07', STYLES['static_text'])],
        [Paragraph('<b>06</b>', ParagraphStyle('n6', parent=STYLES['static_text'], alignment=TA_CENTER, textColor=white)), Paragraph('  Sports — Asian Games Gold', STYLES['static_text']), Paragraph('08', STYLES['static_text'])],
        [Paragraph('<b>07</b>', ParagraphStyle('n7', parent=STYLES['static_text'], alignment=TA_CENTER, textColor=white)), Paragraph('  Top 15 MCQs Based on Today\'s News', STYLES['static_text']), Paragraph('09', STYLES['static_text'])],
        [Paragraph('<b>08</b>', ParagraphStyle('n8', parent=STYLES['static_text'], alignment=TA_CENTER, textColor=white)), Paragraph('  One-Liner Revision +  Most Important Facts', STYLES['static_text']), Paragraph('12', STYLES['static_text'])],
    ]
    toc_table = Table(toc_data, colWidths=[10*mm, PAGE_W - 50*mm, 12*mm])
    toc_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), COLORS["primary_green"]),
        ('BACKGROUND', (1,0), (1,-1), HexColor("#F9FBE7")),
        ('BACKGROUND', (2,0), (2,-1), HexColor("#FFF3E0")),
        ('GRID', (0,0), (-1,-1), 0.4, white),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(toc_table)
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph('<font color="#757575" size="6"><i>>> Tip: This PDF is mobile-friendly. Read on phone, tablet, or print on A4. All news verified from official sources (PIB, RBI, ICAR).</i></font>', ParagraphStyle('tip', parent=STYLES['static_text'], alignment=TA_CENTER, textColor=COLORS["light_text"], fontSize=6, leading=7)))
    story.append(Spacer(1, 6*mm))
    
    # ===== TODAY'S MOST IMPORTANT =====
    story.append(Paragraph('<b><font color="white">TODAY\'S MOST IMPORTANT CURRENT AFFAIRS</font></b>', ParagraphStyle('most_head', parent=STYLES['section_banner'], alignment=TA_CENTER, textColor=white, fontSize=10, leading=12)))
    # Wrap in colored banner
    most_banner = Table([[Paragraph('<b><font color="white">TODAY\'S MOST IMPORTANT CURRENT AFFAIRS</font></b>', ParagraphStyle('mb', parent=STYLES['section_banner'], alignment=TA_CENTER, textColor=white, fontSize=9, leading=11))]], colWidths=[PAGE_W - 20*mm])
    most_banner.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), HexColor("#B71C1C")),
        ('ROUNDEDCORNERS', [4,4,4,4]),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(most_banner)
    story.append(Spacer(1, 1.5*mm))
    story.append(Paragraph('<font color="#B71C1C" size="6"><b>  20 One-Liners for Quick Revision — 2 minutes me pura din cover karo!</b></font>', ParagraphStyle('most_sub', parent=STYLES['static_text'], alignment=TA_CENTER, textColor=COLORS["sports_red"], fontSize=6, leading=7)))
    story.append(Spacer(1, 2*mm))
    
    one_liners_top = [
        " <b>GOBARdhan Scheme</b> launched — Rs 23,731 Cr for Compressed Biogas (CBG) over 10 years (FY27-36)",
        "👩‍ <b>First Female Farmer Worker Conference</b> held in New Delhi — UN International Year of Woman Farmer 2026",
        " <b>RBI appoints Sudhakar Malli</b> as Executive Director (w.e.f. 1 Oct 2026) — to oversee Supervision",
        " <b>India's forex reserves fall $18.3 bn</b> — biggest weekly decline on record (3rd straight week)",
        " <b>RBI MPC to meet 5-7 Oct 2026</b> — economists expect 25 bps repo hike to 5.50% (inflation pressure)",
        " <b>RBI new bulk deposit rules</b> from 1 Oct 2026 — rates to be disclosed on website by 10:10 AM daily",
        " <b>Gandhi Jayanti & Shastri Jayanti</b> observed 02 Oct 2026 — PM tributes, Swachhata Hi Seva 2026 continues",
        "🏑 <b>India Women’s Hockey wins Asian Games Gold</b> after 44 years — beat China 1-0, qualify for Olympics 2028",
        " <b>Asian Games 2026:</b> Lovlina Borgohain (Boxing 75kg) & Sujeet (Wrestling 65kg) win Gold for India",
        " <b>Nomura projects repo to hit 5.75%</b> by Dec 2026 — two 25 bps hikes expected (Oct + Dec)",
        " <b>ICAR & FCI sign MoU</b> for alternative fumigation methods for foodgrain storage (Swachhata Hi Seva)",
        " <b>Agri Budget 2026-27 at Rs 1.32 lakh Cr</b> — Rural Dev + Agri combined crosses Rs 4.35 lakh Cr",
        " <b>Bharat-VISTAAR AI tool</b> proposed in Budget 2026-27 — multilingual AI for farmers via AgriStack + ICAR",
        " <b>RBI eases bank share acquisition norms</b> — funds/insurers can acquire up to 10% with one-time approval",
        " <b>Ladakh: 28 places given standard names</b> by Survey of India — MHA notification 02 Oct 2026",
        " <b>INS Sahyadri & Kulish</b> conclude AIME 2026 participation — defence diplomacy",
        " <b>GOBARdhan to save Rs 40,000 Cr forex</b> via LNG import cut + create 5 lakh jobs + organic manure",
        "👨‍ <b>Female farmers = 33% of agri workforce</b> — Conference highlights their role in food security",
        " <b>FCNR(B) effect:</b> RBI net short forward book swells to record $200 bn — liquidity management",
        " <b>8th PM Mementos Auction</b> highlights Haryana sports achievements — Ministry of Culture",
    ]
    for idx, line in enumerate(one_liners_top, 1):
        bg = HexColor("#FFF3E0") if idx % 2 == 0 else white
        p = Paragraph(f'<b><font color="#B71C1C">{idx:02d}.</font></b>  {line}', ParagraphStyle(f'ol{idx}', parent=STYLES['one_liner'], fontSize=11.5, leading=16, spaceAfter=4))
        # Each in a row table for bg
        t = Table([[p]], colWidths=[PAGE_W - 28*mm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), bg),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('ROUNDEDCORNERS', [2,2,2,2]),
            ('BOX', (0,0), (-1,-1), 0.3, HexColor("#FFE0B2") if idx%2==0 else white),
        ]))
        story.append(t)
    
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph('<font color="#2E7D32" size="6"><i>[OK]  All facts verified from PIB, RBI, ICAR, Ministry sources | Date: 03-04 Oct 2026 window (Asia/Kolkata)</i></font>', ParagraphStyle('verify', parent=STYLES['static_text'], alignment=TA_CENTER, textColor=COLORS["agri_accent"], fontSize=6, leading=7)))
    story.append(Spacer(1, 6*mm))
    
    # ===== MAIN NEWS SECTIONS =====
    
    # Agriculture 01
    # Ensure Agriculture starts at top of new page - add page break if needed to avoid blank at bottom
    story.append(Spacer(1, 3*mm))
    # Teaser box to fill page 2 and preview next sections - makes page look full (no blank)
    teaser = Table([
        [Paragraph('<b><font color="white" size="6">NEXT  •  AGRICULTURE & ALLIED  •  BANKING  •  NATIONAL</font></b>', ParagraphStyle('teasH', parent=STYLES['static_text'], alignment=TA_CENTER, textColor=HexColor("#FFFFFF"), fontSize=6, leading=7))],
        [Paragraph('<font color="#212121" size="5">• <b>GOBARdhan Rs 23,731 Cr Scheme</b> &nbsp;|&nbsp; • <b>Women Farmers Conference 2026</b> &nbsp;|&nbsp; • <b>RBI New ED Appointment</b> &nbsp;|&nbsp; • <b>Gandhi & Swachhata + Budget Rs 1.32 Lakh Cr</b> — Detailed bilingual coverage with Key Points, Static Facts & Exam Fact on next pages →</font>', ParagraphStyle('teasB', parent=STYLES['static_text'], alignment=TA_CENTER, textColor=COLORS["dark_text"], fontSize=5, leading=6))],
    ], colWidths=[PAGE_W - 20*mm])
    teaser.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), COLORS["primary_green"]),
        ('BACKGROUND', (0,1), (-1,1), HexColor("#E8F5E9")),
        ('TOPPADDING', (0,0), (-1,0), 4),
        ('BOTTOMPADDING', (0,0), (-1,0), 4),
        ('TOPPADDING', (0,1), (-1,1), 5),
        ('BOTTOMPADDING', (0,1), (-1,1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('ROUNDEDCORNERS', [4,4,4,4]),
        ('BOX', (0,0), (-1,-1), 0.4, COLORS["border_grey"]),
        ('LINEBELOW', (0,0), (-1,0), 0.4, HexColor("#A5D6A7")),
    ]))
    story.append(teaser)
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph('<font color="#9E9E9E" size="4"><i>Detailed news coverage starts on next page  →</i></font>', ParagraphStyle('nextpage', parent=STYLES['static_text'], alignment=TA_CENTER, textColor=COLORS["light_text"], fontSize=4, leading=5)))
    story.append(PageBreak())
    story.append(section_banner("agriculture", "01"))
    story.append(Spacer(1, 1.5*mm))
    story.extend(news_card(
        headline_en=">> First-Ever Female Farmer Worker Conference Held in New Delhi",
        headline_hi="पहला महिला किसान श्रमिक सम्मेलन नई दिल्ली में आयोजित",
        category_key="agriculture",
        key_points_en=[
            "Organized in New Delhi to recognise women's contribution to agriculture & rural livelihoods — coincides with <b>UN International Year of the Woman Farmer 2026</b>.",
            "Ministry of Agriculture & Farmers Welfare highlighted that <b>women constitute ~33% of agricultural workforce</b> and are key to food security.",
            "Conference discussed: access to credit, land rights, AgriStack, FPOs, natural farming, and PM-KISAN/PMFBY benefits for women farmers.",
        ],
        key_points_hi=[
            "नई दिल्ली में आयोजित — कृषि और ग्रामीण आजीविका में महिलाओं के योगदान को सम्मान देने के लिए — <b>संयुक्त राष्ट्र अंतरराष्ट्रीय महिला किसान वर्ष 2026</b> के साथ संयोग।",
            "कृषि मंत्रालय ने बताया कि <b>महिलाएँ कृषि कार्यबल का लगभग 33% हैं</b> और खाद्य सुरक्षा में महत्वपूर्ण हैं।",
            "सम्मेलन में चर्चा: ऋण तक पहुँच, भूमि अधिकार, एग्रीस्टैक, FPOs, प्राकृतिक खेती और महिला किसानों के लिए PM-KISAN/PMFBY लाभ।",
        ],
        static_facts={
            "Ministry": "Ministry of Agriculture & Farmers Welfare (MoA&FW)",
            "Minister": "Shivraj Singh Chouhan (as of 2026)",
            "UN Year 2026": "International Year of the Woman Farmer (declared by UNGA)",
            "Related Schemes": "PM-KISAN, PMFBY, AgriStack, NRLM, 2,195 FFPOs formed",
            "ICAR Role": "Research on gender-friendly farm tools & extension via KVKs"
        },
        exam_fact_en="UN declared 2026 as International Year of the Woman Farmer — India’s first Female Farmer Worker Conference marks it.",
        exam_fact_hi="संयुक्त राष्ट्र ने 2026 को अंतरराष्ट्रीय महिला किसान वर्ष घोषित किया — भारत का पहला महिला किसान श्रमिक सम्मेलन इसी उपलक्ष्य में।",
        source="PIB / Ministry of Agriculture & Farmers Welfare (02 Oct 2026)",
        image_path="/home/user/image-search/india-women-farmers-conference-new-delhi-1.jpg",
        image_caption="All India Women Farmers' Conference, Vigyan Bhawan, New Delhi - Sep 30, 2026"
    ))
    
    # Agriculture 02 - GOBARdhan
    story.extend(news_card(
        headline_en=">> Government Launches GOBARdhan Scheme with Rs 23,731 Cr Outlay for Compressed Biogas (CBG)",
        headline_hi="सरकार ने GOBARdhan योजना शुरू की — 23,731 करोड़ रुपये का प्रावधान, संपीड़ित बायोगैस (CBG) के लिए",
        category_key="environment",
        key_points_en=[
            "Launched by <b>Union Minister of Petroleum & Natural Gas</b> as <b>Central Sector Scheme</b> — outlay <b>Rs 23,731 crore for 10 years (FY 2026-27 to FY 2035-36)</b>.",
            "Aims to accelerate <b>Compressed Biogas (CBG)</b> sector — reduce <b>LNG imports, save > Rs 40,000 Cr forex</b>, cut CO₂ emissions.",
            "Expected to create <b>~5 lakh jobs</b>, produce <b>organic manure</b> — improves soil health & farmer income (circular economy).",
            "Links to: <b>Swachh Bharat, SATAT, Waste to Wealth, Natural Farming</b> — uses cattle dung, agri waste, kitchen waste."
        ],
        key_points_hi=[
            "<b>केंद्रीय पेट्रोलियम एवं प्राकृतिक गैस मंत्री</b> द्वारा लॉन्च — <b>केंद्रीय क्षेत्र की योजना</b> — <b>10 वर्षों (FY 2026-27 से 2035-36) के लिए 23,731 करोड़ रुपये</b>।",
            "लक्ष्य: <b>संपीड़ित बायोगैस (CBG)</b> क्षेत्र को गति देना — <b>LNG आयात कम करना, 40,000 करोड़ रुपये से अधिक विदेशी मुद्रा बचाना</b>, CO₂ उत्सर्जन घटाना।",
            "अनुमान: <b>~5 लाख रोजगार</b> सृजन, <b>जैविक खाद</b> उत्पादन — मिट्टी की उर्वरता और किसान आय में वृद्धि।",
            "जुड़ाव: <b>स्वच्छ भारत, SATAT, वेस्ट टू वेल्थ, प्राकृतिक खेती</b> — गोबर, कृषि अपशिष्ट, रसोई कचरे का उपयोग।"
        ],
        static_facts={
            "Full Form": "GOBARdhan = Galvanizing Organic Bio-Agro Resources Dhan",
            "Nodal Ministry": "Ministry of Petroleum & Natural Gas + Dept. of Drinking Water & Sanitation",
            "SATAT": "Sustainable Alternative Towards Affordable Transportation (2018)",
            "CBG": "Compressed Biogas — purified biogas ~95% methane, similar to CNG",
            "Outlay Period": "10 years: FY 2026-27 to FY 2035-36"
        },
        exam_fact_en="GOBARdhan: Rs 23,731 Cr | 10 years (FY27-36) | Central Sector | Saving Rs 40k Cr forex | 5 lakh jobs | CBG.",
        exam_fact_hi="GOBARdhan: 23,731 करोड़ | 10 वर्ष | केंद्रीय क्षेत्र | 40 हजार करोड़ बचत | 5 लाख नौकरियाँ | CBG।",
        source="PIB / Insights on India UPSC (02 Oct 2026)",
        image_path="/home/user/image-search/india-gobardhan-compressed-biogas-plant--2.jpg",
        image_caption="GOBARdhan Compressed Biogas (CBG) Plant - Waste to Wealth Initiative"
    ))
    
    # Banking 01
    story.append(section_banner("banking", "02"))
    story.append(Spacer(1, 1.5*mm))
    story.extend(news_card(
        headline_en=">> RBI Appoints Sudhakar Malli as Executive Director (w.e.f. 1 October 2026)",
        headline_hi="RBI ने सुधाकर मल्ली को कार्यकारी निदेशक नियुक्त किया (01 अक्टूबर 2026 से प्रभावी)",
        category_key="banking",
        key_points_en=[
            "<b>RBI appointed Sudhakar Malli as Executive Director</b> — previously <b>Chief General Manager-in-Charge, Department of Supervision</b>.",
            "He will oversee <b>Supervisory Assessment function</b> — supervision of banks, NBFCs & cooperative banks.",
            "Career central banker with <b>~3 decades experience</b>, including <b>2.5+ decades in supervision</b> — domestic & overseas expertise.",
            "Announcement date: <b>02 Oct 2026</b> — Business Standard, Economic Times & RBI press release."
        ],
        key_points_hi=[
            "<b>RBI ने सुधाकर मल्ली को कार्यकारी निदेशक नियुक्त किया</b> — पहले <b>पर्यवेक्षण विभाग के मुख्य महाप्रबंधक प्रभारी</b> थे।",
            "वे <b>पर्यवेक्षी मूल्यांकन कार्य</b> देखेंगे — बैंकों, NBFCs और सहकारी बैंकों का पर्यवेक्षण।",
            "<b>लगभग 3 दशकों का अनुभव</b>, जिनमें <b>ढाई दशक से अधिक पर्यवेक्षण में</b> — देश-विदेश का अनुभव।",
            "घोषणा तिथि: <b>02 अक्टूबर 2026</b>"
        ],
        static_facts={
            "RBI Established": "1 April 1935; Nationalised 1 Jan 1949",
            "Headquarters": "Mumbai, Maharashtra",
            "Governor (2026)": "Sanjay Malhotra (mentioned in reports)",
            "RBI ED Role": "Executive Directors head key departments — Supervision, Monetary Policy etc.",
            "Regulates": "Banks, NBFCs, Cooperative Banks, Payment Systems"
        },
        exam_fact_en="Sudhakar Malli = New RBI Executive Director (01 Oct 2026) | Dept. of Supervision | 30 years experience.",
        exam_fact_hi="सुधाकर मल्ली = नए RBI कार्यकारी निदेशक (01 अक्टूबर 2026) | पर्यवेक्षण विभाग | 30 वर्ष अनुभव।",
        source="RBI / Business Standard / Economic Times (02 Oct 2026)",
        image_path="/home/user/image-search/sudhakar-malli-rbi-executive-director-of-1.jpg",
        image_caption="Shri Sudhakar Malli, New Executive Director, RBI (w.e.f. 01 Oct 2026)"
    ))
    
    story.extend(news_card(
        headline_en=">> RBI MPC Meeting 5-7 Oct 2026: Repo Rate Hike Expected + Forex Reserves Fall $18.3 Bn",
        headline_hi="RBI MPC बैठक 05-07 अक्टूबर 2026: रेपो रेट बढ़ोतरी की उम्मीद + विदेशी मुद्रा भंडार में 18.3 बिलियन डॉलर की गिरावट",
        category_key="banking",
        key_points_en=[
            "<b>RBI Monetary Policy Committee (MPC) to meet 05-07 Oct 2026</b> — decision on <b>07 Oct</b>. Polls expect <b>25 bps hike to 5.50%</b> due to crude-led inflation.",
            "<b>India's forex reserves fell $18.3 bn</b> in week ending late Sep — <b>biggest weekly decline on record</b> (3rd straight week, total ~$38.2 bn fall).",
            "<b>New bulk deposit rules from 01 Oct 2026:</b> Banks must disclose bulk deposit rates on website by <b>10:10 AM daily</b> — uniform application.",
            "<b>Nomura projects terminal repo 5.75% by Dec 2026</b> — expects two hikes (Oct + Dec) before pause; RBI net short forward book at <b>record $200 bn</b> (FCNR(B) effect)."
        ],
        key_points_hi=[
            "<b>RBI मौद्रिक नीति समिति (MPC) की बैठक 05-07 अक्टूबर 2026</b> — निर्णय <b>07 अक्टूबर</b> को। चुनाव में <b>25 bps बढ़ोतरी से 5.50%</b> की उम्मीद (कच्चे तेल से मुद्रास्फीति)।",
            "<b>भारत का विदेशी मुद्रा भंडार 18.3 बिलियन डॉलर घटा</b> — <b>रिकॉर्ड सबसे बड़ी साप्ताहिक गिरावट</b> (लगातार तीसरा सप्ताह, कुल ~38.2 बिलियन गिरावट)।",
            "<b>01 अक्टूबर 2026 से नए बल्क डिपॉजिट नियम:</b> बैंकों को वेबसाइट पर <b>रोज़ सुबह 10:10 बजे तक</b> दरें घोषित करनी होंगी।",
            "<b>नोमुरा अनुमान: टर्मिनल रेपो 5.75% दिसंबर 2026 तक</b> — दो बढ़ोतरी (अक्टूबर + दिसंबर); RBI का नेट शॉर्ट फॉरवर्ड बुक <b>रिकॉर्ड 200 बिलियन डॉलर</b>।"
        ],
        static_facts={
            "RBI MPC": "6 members (3 RBI + 3 Govt. nominees); meets bi-monthly; decides repo rate",
            "Current Repo (Sep 2026)": "5.25% (before Oct meet)",
            "Forex Reserves": "Managed by RBI; includes foreign currency assets, gold, SDRs, reserve position",
            "Bulk Deposit": "Single rupee term deposit of Rs 3 Crore and above (revised definition)",
            "FCNR(B)": "Foreign Currency Non-Resident (Banks) deposits — affects forward book"
        },
        exam_fact_en="RBI MPC: 05-07 Oct 2026 | Repo expected 5.50% (+25 bps) | Forex fall $18.3 bn (record) | Bulk deposit disclosure by 10:10 AM.",
        exam_fact_hi="RBI MPC: 05-07 अक्टूबर 2026 | रेपो अनुमान 5.50% (+25 bps) | विदेशी मुद्रा गिरावट 18.3 बिलियन (रिकॉर्ड) | बल्क डिपॉजिट 10:10 AM।",
        source="Business Standard / MoneyControl / Economic Times (01-02 Oct 2026)",
        image_path="/home/user/image-search/rbi-reserve-bank-india-mumbai-headquarte-2.jpg",
        image_caption="RBI Headquarters, Mumbai - MPC Meeting 5-7 Oct 2026"
    ))
    
    # National Affairs
    story.append(section_banner("national", "03"))
    story.append(Spacer(1, 1.5*mm))
    story.extend(news_card(
        headline_en=">> Nation Observes Gandhi Jayanti & Lal Bahadur Shastri Jayanti (02 October 2026) — Swachhata Hi Seva 2026",
        headline_hi="देश ने गांधी जयंती और लाल बहादुर शास्त्री जयंती मनाई (02 अक्टूबर 2026) — स्वच्छता ही सेवा 2026",
        category_key="national",
        key_points_en=[
            "<b>02 Oct 2026: 157th Gandhi Jayanti & 122nd Shastri Jayanti</b> observed — PM, President paid tributes at Rajghat & Vijay Ghat.",
            "<b>Swachhata Hi Seva 2026 (17 Sep - 02 Oct)</b> concludes — theme <b>'Swabhav Swachhata, Sanskar Swachhata'</b>; ICAR & DARE organized nationwide cleanliness drives & felicitated Safai Mitras (Campaign 6.0 from 02-31 Oct).",
            "<b>Gandhiji's Satyagraha</b> remembered for exam: Champaran (1917), Kheda & Ahmedabad Mill Strike (1918).",
            "<b>Shastri ji remembered</b> for <b>'Jai Jawan, Jai Kisan'</b> (1965) & push for Green Revolution & self-reliance."
        ],
        key_points_hi=[
            "<b>02 अक्टूबर 2026: 157वीं गांधी जयंती और 122वीं शास्त्री जयंती</b> — PM, राष्ट्रपति ने राजघाट और विजय घाट पर श्रद्धांजलि दी।",
            "<b>स्वच्छता ही सेवा 2026 (17 सितंबर - 02 अक्टूबर)</b> संपन्न — थीम <b>'स्वभाव स्वच्छता, संस्कार स्वच्छता'</b>; ICAR और DARE ने देशभर में स्वच्छता अभियान चलाए (02-31 अक्टूबर से विशेष अभियान 6.0)।",
            "<b>गांधीजी का सत्याग्रह</b>: चंपारण (1917), खेड़ा और अहमदाबाद मिल हड़ताल (1918) — परीक्षा उपयोगी।",
            "<b>शास्त्री जी को याद किया गया</b> — <b>'जय जवान, जय किसान' (1965)</b> और हरित क्रांति व आत्मनिर्भरता को बढ़ावा।"
        ],
        static_facts={
            "Gandhi Born": "02 Oct 1869, Porbandar (Gujarat)",
            "UN Day": "02 Oct = International Day of Non-Violence (UNGA 2007)",
            "Shastri Born": "02 Oct 1904, Varanasi (UP); PM 1964-66",
            "Swachh Bharat": "Launched 02 Oct 2014",
            "ICAR & DARE": "DARE/ICAR under MoA&FW — organized SHS 2026"
        },
        exam_fact_en="02 Oct: Gandhi Jayanti = International Day of Non-Violence (UN); Shastri Jayanti; Swachhata Hi Seva theme 2026: Swabhav Swachhata, Sanskar Swachhata.",
        exam_fact_hi="02 अक्टूबर: गांधी जयंती = अंतरराष्ट्रीय अहिंसा दिवस (UN); शास्त्री जयंती; स्वच्छता ही सेवा 2026 थीम: स्वभाव स्वच्छता, संस्कार स्वच्छता।",
        source="PIB / Ministry of Culture / ICAR (02 Oct 2026)",
        image_path="/home/user/image-search/mahatma-gandhi-rajghat-new-delhi-tribute-1.jpg",
        image_caption="Tribute at Rajghat on Gandhi Jayanti, 02 Oct 2026 - New Delhi"
    ))
    
    # Economy + International combined
    story.append(section_banner("economy", "04"))
    story.append(Spacer(1, 1.5*mm))
    story.extend(news_card(
        headline_en=">> Agri Budget 2026-27 at Rs 1.32 Lakh Crore — Combined Agri + Rural Development Crosses Rs 4.35 Lakh Crore",
        headline_hi="कृषि बजट 2026-27: 1.32 लाख करोड़ रुपये — कृषि + ग्रामीण विकास मिलाकर 4.35 लाख करोड़ के पार",
        category_key="economy",
        key_points_en=[
            "Union Agriculture Minister <b>Shivraj Singh Chouhan</b> highlighted <b>Union Budget 2026-27: Agriculture Dept allocation Rs 1,32,561 crore</b> (vs Rs 27,663 Cr in 2013-14).",
            "<b>Combined Rural Development + Agriculture = Rs 4,35,779 crore</b> — 21% hike in Rural Development Budget; reflects focus on villages & farmers.",
            "<b>ICAR allocation Rs 9,967 Cr</b> for agri education & research; <b>fertilizer subsidy Rs 1,70,944 Cr</b> to keep inputs affordable.",
            "Focus on: <b>coconut, cocoa, cashew, sandalwood</b>, rejuvenation of old coconut plantations; <b>Millets, pulses, oilseeds procurement up 76% (2014-26 vs 2004-14)</b>."
        ],
        key_points_hi=[
            "केंद्रीय कृषि मंत्री <b>शिवराज सिंह चौहान</b> ने बताया — <b>केंद्रीय बजट 2026-27: कृषि विभाग आवंटन 1,32,561 करोड़ रुपये</b> (2013-14 में 27,663 करोड़)।",
            "<b>ग्रामीण विकास + कृषि मिलाकर = 4,35,779 करोड़ रुपये</b> — ग्रामीण विकास बजट में 21% वृद्धि; गाँवों और किसानों पर फोकस।",
            "<b>ICAR के लिए 9,967 करोड़</b> कृषि शिक्षा व अनुसंधान हेतु; <b>उर्वरक सब्सिडी 1,70,944 करोड़</b> ताकि इनपुट सस्ते रहें।",
            "फोकस: <b>नारियल, कोको, काजू, चंदन</b>, पुराने नारियल बागानों का पुनरुद्धार; <b>2014-26 में खरीद 76% बढ़ी</b>।"
        ],
        static_facts={
            "Budget Presented": "01 Feb 2026 (Union Budget 2026-27)",
            "Fertilizer Subsidy": "Rs 1,70,944 Cr (2026-27)",
            "ICAR": "Indian Council of Agricultural Research — Est. 16 July 1929; HQ New Delhi",
            "MSP Growth": "Ragi 236%, Nigerseed 179%, Jowar Hybrid 163%, Jute 147% (since 2014-15)",
            "High-Value Crops": "Coconut, cocoa, cashew, sandalwood — new provisions"
        },
        exam_fact_en="Budget 2026-27: Agri Dept Rs 1,32,561 Cr | Agri+Rural = Rs 4,35,779 Cr | ICAR Rs 9,967 Cr | Fertilizer subsidy Rs 1,70,944 Cr.",
        exam_fact_hi="बजट 2026-27: कृषि विभाग 1,32,561 करोड़ | कृषि+ग्रामीण = 4,35,779 करोड़ | ICAR 9,967 करोड़ | उर्वरक सब्सिडी 1,70,944 करोड़।",
        source="PIB (01 Feb 2026, reiterated 02 Oct 2026)",
        image_path="/home/user/image-search/union-budget-india-2026-finance-minister-1.jpg",
        image_caption="Union Budget 2026-27 - Finance Minister presents Agriculture allocation Rs 1.32 lakh crore"
    ))
    
    # Sports
    story.append(section_banner("sports", "05"))
    story.append(Spacer(1, 1.5*mm))
    story.extend(news_card(
        headline_en=">> Asian Games 2026: India Women’s Hockey Wins Gold After 44 Years, Qualifies for Olympics 2028",
        headline_hi="एशियाई खेल 2026: भारतीय महिला हॉकी ने 44 साल बाद स्वर्ण जीता, ओलंपिक 2028 के लिए क्वालीफाई",
        category_key="sports",
        key_points_en=[
            "India Women’s Hockey team beat <b>defending champions China 1-0</b> in final on <b>02 Oct 2026</b> — <b>first Asian Games Gold after 44 years (last: 1982 New Delhi)</b>.",
            "Victory ensures <b>direct qualification for Paris Olympics 2028? Wait — next: Los Angeles Olympics 2028</b> (Hockey qualification).",
            "Simultaneous wins: <b>Lovlina Borgohain (Women’s 75kg Boxing Gold)</b> & <b>Sujeet (Men’s 65kg Freestyle Wrestling Gold)</b> on same day — PMO congratulated.",
            "Other medals: <b>Women’s Recurve Archery Team? & Nethra Kumanan (Sailing Bronze)</b> — India’s tally surges on Gandhi Jayanti."
        ],
        key_points_hi=[
            "भारतीय महिला हॉकी टीम ने <b>02 अक्टूबर 2026 को फाइनल में गत चैंपियन चीन को 1-0 से हराया</b> — <b>44 साल बाद पहला एशियाई खेल स्वर्ण (अंतिम: 1982 नई दिल्ली)</b>।",
            "जीत से <b>ओलंपिक 2028 (लॉस एंजिल्स) के लिए सीधा क्वालीफिकेशन</b> सुनिश्चित।",
            "उसी दिन जीत: <b>लवलीना बोर्गोहेन (महिला 75kg बॉक्सिंग स्वर्ण)</b> और <b>सुजीत (पुरुष 65kg फ्रीस्टाइल कुश्ती स्वर्ण)</b> — PMO ने बधाई दी।",
            "अन्य पदक: <b>नेत्रा कुमानन (सेलिंग कांस्य)</b> सहित पदक तालिका में उछाल।"
        ],
        static_facts={
            "Asian Games 2026": "Held in Japan (Aichi-Nagoya 2026) — 20 Sep to 05 Oct 2026",
            "Women's Hockey Last Gold": "1982 New Delhi Asian Games",
            "Olympics 2028": "Los Angeles, USA — 14-30 July 2028",
            "Hockey India": "Est. 2009; HQ New Delhi; governs field hockey",
            "PM Mementos": "8th Edition auction highlights Haryana sports achievements (Ministry of Culture)"
        },
        exam_fact_en="Women’s Hockey Gold: India 1-0 China | 02 Oct 2026 | After 44 years (1982→2026) | Qualify for Olympics 2028 (LA).",
        exam_fact_hi="महिला हॉकी स्वर्ण: भारत 1-0 चीन | 02 अक्टूबर 2026 | 44 साल बाद (1982→2026) | ओलंपिक 2028 (LA) क्वालीफाई।",
        source="The Hindu / PIB PMO Releases (02 Oct 2026)",
        image_path="/home/user/image-search/indian-women-hockey-team-celebration-gol-1.jpg",
        image_caption="Indian Women's Hockey Team celebrates Asian Games Gold (1-0 vs China) - 02 Oct 2026, Japan"
    ))
    
    # Important Days banner extra compact
    story.append(section_banner("important_days", "06"))
    story.append(Spacer(1, 1.5*mm))
    story.extend(news_card(
        headline_en=">> ICAR Institutes Celebrate Swachhata Hi Seva & Sign Key MoU for Foodgrain Storage",
        headline_hi="ICAR संस्थानों ने स्वच्छता ही सेवा मनाई और खाद्यान्न भंडारण के लिए महत्वपूर्ण MoU पर हस्ताक्षर किए",
        category_key="agriculture",
        key_points_en=[
            "<b>ICAR-KVKs across India</b> organized Swachhata Hi Seva 2026 drives — human chains, cleanliness drives, felicitation of Safai Mitras (01-02 Oct).",
            "<b>ICAR & FCI signed MoU</b> to develop <b>alternative fumigation methods for foodgrain storage</b> — reduces chemical residues, improves food safety (FSSAI link).",
            "<b>Success stories (01 Oct):</b> Bindia Khasia (Integrated Farming), Saimona Begum Sekh (Fish Seed Enterprise), Sita Herbal Farm (Women-led) — showcased on ICAR website.",
            "<b>GI Tag boost:</b> Kalaburagi Tur Dal gets processing & export push via GI tagging — example of value addition for pulses."
        ],
        key_points_hi=[
            "<b>देशभर के ICAR-KVKs</b> ने स्वच्छता ही सेवा 2026 अभियान चलाए — मानव श्रृंखला, स्वच्छता अभियान, सफाई मित्रों का सम्मान (01-02 अक्टूबर)।",
            "<b>ICAR और FCI ने MoU पर हस्ताक्षर किए</b> — <b>खाद्यान्न भंडारण के लिए वैकल्पिक धूमन विधियाँ</b> विकसित करने हेतु — रासायनिक अवशेष कम, खाद्य सुरक्षा बेहतर।",
            "<b>सफलता की कहानियाँ (01 अक्टूबर):</b> बिंदिया खासिया (एकीकृत खेती), साइमोना बेगम शेख (मत्स्य बीज उद्यम), सीता हर्बल फार्म — ICAR वेबसाइट पर।",
            "<b>GI टैग बढ़ावा:</b> कलबुरगी तूर दाल को GI टैगिंग से प्रोसेसिंग और निर्यात में बढ़ावा।"
        ],
        static_facts={
            "ICAR HQ": "New Delhi; DG: (as of 2026) — under DARE, MoA&FW",
            "FCI": "Food Corporation of India — Est. 14 Jan 1965; HQ New Delhi; handles procurement & distribution",
            "KVK": "Krishi Vigyan Kendra — 731 KVKs in India (ICAR network)",
            "GI Tag": "Geographical Indication — Darjeeling Tea was first Indian GI (2004)",
            "Kalaburagi": "Karnataka — known for Tur (Pigeon Pea) dal"
        },
        exam_fact_en="ICAR-FCI MoU: Alternative fumigation for foodgrain storage | KVKs = 731 | Kalaburagi Tur Dal = GI Tag example.",
        exam_fact_hi="ICAR-FCI MoU: खाद्यान्न भंडारण के लिए वैकल्पिक धूमन | KVKs = 731 | कलबुरगी तूर दाल = GI टैग उदाहरण।",
        source="ICAR Official Website / PIB (01-02 Oct 2026)",
        image_path="/home/user/image-search/icar-indian-council-agricultural-researc-1.jpg",
        image_caption="ICAR Headquarters, New Delhi - Agricultural Research & Extension"
    ))
    
    # ===== MCQ SECTION =====
    # Title banner premium
    story.append(Spacer(1, 4*mm))
    mcq_title_banner = Table([[Paragraph('<b><font color="white" size="11">TOP MCQs BASED ON TODAY\'S NEWS</font></b>', ParagraphStyle('mcq_title', parent=STYLES['section_banner'], alignment=TA_CENTER, textColor=white, fontSize=10, leading=12))]], colWidths=[PAGE_W - 20*mm])
    mcq_title_banner.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLORS["primary_green"]),
        ('ROUNDEDCORNERS', [4,4,4,4]),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('BOX', (0,0), (-1,-1), 1, HexColor("#A5D6A7")),
    ]))
    story.append(mcq_title_banner)
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph('<font color="#757575" size="6"><b>Instructions:</b> 15 Qs | 5 Options (A-E) | Based ONLY on 03-04 Oct 2026 news | Exam Level: AGTA/AFO/NABARD/Banking</font>', ParagraphStyle('mcq_instr', parent=STYLES['static_text'], alignment=TA_CENTER, textColor=COLORS["light_text"], fontSize=6, leading=7)))
    story.append(Spacer(1, 4*mm))
    
    mcqs = [
        {
            "q_en": "The GOBARdhan Scheme launched in Oct 2026 has an outlay of Rs 23,731 crore for how many years?",
            "q_hi": "अक्टूबर 2026 में शुरू की गई GOBARdhan योजना का 23,731 करोड़ रुपये का प्रावधान कितने वर्षों के लिए है?",
            "opts": ["5 years (FY27-31)", "7 years (FY27-33)", "10 years (FY27-36)", "15 years (FY27-41)", "None of these"],
            "correct": "C",
            "exp_en": "Central Sector Scheme Rs 23,731 Cr for 10 years FY 2026-27 to 2035-36 to boost Compressed Biogas (CBG).",
            "exp_hi": "केंद्रीय क्षेत्र योजना 23,731 करोड़, 10 वर्ष (FY 2026-27 से 2035-36) संपीड़ित बायोगैस को बढ़ावा देने हेतु।",
            "point": "GOBARdhan = 10 years | FY27-36 | CBG | Rs 23,731 Cr"
        },
        {
            "q_en": "Who has been appointed as Executive Director of RBI w.e.f. 1 October 2026?",
            "q_hi": "01 अक्टूबर 2026 से RBI के कार्यकारी निदेशक के रूप में किसे नियुक्त किया गया है?",
            "opts": ["Sanjay Malhotra", "Sudhakar Malli", "Anup Bagchi", "Gaura Sengupta", "None of these"],
            "correct": "B",
            "exp_en": "Sudhakar Malli, ex-CGM-in-Charge Dept. of Supervision, will oversee Supervisory Assessment; ~30 years experience.",
            "exp_hi": "सुधाकर मल्ली, पूर्व मुख्य महाप्रबंधक प्रभारी, पर्यवेक्षण विभाग, पर्यवेक्षी मूल्यांकन देखेंगे; ~30 वर्ष अनुभव।",
            "point": "RBI ED 01 Oct 2026 = Sudhakar Malli (Supervision)"
        },
        {
            "q_en": "India’s first Female Farmer Worker Conference was held in Oct 2026 coinciding with which UN observance?",
            "q_hi": "अक्टूबर 2026 में भारत का पहला महिला किसान श्रमिक सम्मेलन किस संयुक्त राष्ट्र उपलक्ष्य के साथ आयोजित हुआ?",
            "opts": ["International Year of Millets 2026", "International Year of Woman Farmer 2026", "Decade of Family Farming 2026", "World Food Day 2026", "None of these"],
            "correct": "B",
            "exp_en": "UN declared 2026 as International Year of the Woman Farmer; conference in New Delhi recognized women’s 33% share in agri workforce.",
            "exp_hi": "संयुक्त राष्ट्र ने 2026 को अंतरराष्ट्रीय महिला किसान वर्ष घोषित किया; नई दिल्ली सम्मेलन में महिलाओं की 33% हिस्सेदारी को मान्यता।",
            "point": "2026 = International Year of Woman Farmer (UN)"
        },
        {
            "q_en": "RBI MPC is scheduled to meet on which dates in October 2026 to decide repo rate?",
            "q_hi": "अक्टूबर 2026 में RBI MPC की बैठक रेपो रेट तय करने के लिए किन तारीखों पर निर्धारित है?",
            "opts": ["01-03 Oct", "05-07 Oct", "10-12 Oct", "15-17 Oct", "None of these"],
            "correct": "B",
            "exp_en": "MPC meet 05-07 Oct 2026, decision 07 Oct; poll expects 25 bps hike to 5.50% due to inflation.",
            "exp_hi": "MPC बैठक 05-07 अक्टूबर 2026, निर्णय 07 अक्टूबर; मुद्रास्फीति से 25 bps बढ़ोतरी कर 5.50% की उम्मीद।",
            "point": "RBI MPC Oct 2026 = 05-07 Oct | Decision 07 Oct"
        },
        {
            "q_en": "India’s forex reserves fell by $18.3 billion in the week reported on 02 Oct 2026 — what is special about this fall?",
            "q_hi": "02 अक्टूबर 2026 को रिपोर्ट सप्ताह में भारत का विदेशी मुद्रा भंडार 18.3 बिलियन डॉलर घटा — इस गिरावट में क्या विशेष है?",
            "opts": ["Smallest fall in 2026", "Biggest weekly decline on record", "First fall after 6 months", "Only gold reserves fell", "None of these"],
            "correct": "B",
            "exp_en": "Biggest weekly decline on record; 3rd straight week fall (~$38.2 bn total) as RBI defends rupee amid crude rise.",
            "exp_hi": "रिकॉर्ड सबसे बड़ी साप्ताहिक गिरावट; लगातार तीसरा सप्ताह (~38.2 बिलियन कुल) — RBI रुपये को संभाल रहा है।",
            "point": "Forex fall 02 Oct 2026 = Biggest weekly fall ($18.3 bn)"
        },
        {
            "q_en": "RBI’s new bulk deposit rules from 01 Oct 2026 require banks to disclose rates by what time daily?",
            "q_hi": "01 अक्टूबर 2026 से RBI के नए बल्क डिपॉजिट नियमों में बैंकों को रोज़ किस समय तक दरें घोषित करनी होंगी?",
            "opts": ["09:00 AM", "10:10 AM", "11:00 AM", "04:00 PM", "None of these"],
            "correct": "B",
            "exp_en": "Rates to be disclosed on website by 10 AM with 10-min grace → 10:10 AM latest, uniform across branches.",
            "exp_hi": "वेबसाइट पर सुबह 10 बजे, 10 मिनट की छूट के साथ → अधिकतम 10:10 AM तक, सभी शाखाओं में समान।",
            "point": "Bulk deposit disclosure = by 10:10 AM daily"
        },
        {
            "q_en": "India Women’s Hockey Team won Asian Games Gold on 02 Oct 2026 after how many years, beating whom 1-0?",
            "q_hi": "भारतीय महिला हॉकी टीम ने 02 अक्टूबर 2026 को कितने साल बाद स्वर्ण जीता, किसे 1-0 से हराया?",
            "opts": ["22 years, Japan", "30 years, Korea", "44 years, China", "50 years, Australia", "None of these"],
            "correct": "C",
            "exp_en": "Beat defending champion China 1-0; first Gold after 44 years (last 1982); qualifies for LA Olympics 2028.",
            "exp_hi": "गत चैंपियन चीन को 1-0 से हराया; 44 साल बाद पहला स्वर्ण (अंतिम 1982); LA ओलंपिक 2028 क्वालीफाई।",
            "point": "Women Hockey Gold: After 44 yrs (1982→2026) vs China"
        },
        {
            "q_en": "Combined budget of Rural Development + Agriculture Ministries in 2026-27 is?",
            "q_hi": "2026-27 में ग्रामीण विकास + कृषि मंत्रालयों का संयुक्त बजट कितना है?",
            "opts": ["Rs 2.35 lakh Cr", "Rs 3.15 lakh Cr", "Rs 4.35 lakh Cr", "Rs 5.35 lakh Cr", "None of these"],
            "correct": "C",
            "exp_en": "Agri Dept Rs 1,32,561 Cr + Rural Dev (21% hike) = Rs 4,35,779 Cr combined.",
            "exp_hi": "कृषि विभाग 1,32,561 करोड़ + ग्रामीण विकास (21% वृद्धि) = 4,35,779 करोड़ संयुक्त।",
            "point": "Agri+Rural 2026-27 = Rs 4,35,779 Cr"
        },
        {
            "q_en": "GOBARdhan scheme is expected to save how much forex by reducing LNG imports and create how many jobs?",
            "q_hi": "GOBARdhan योजना से LNG आयात कम कर कितनी विदेशी मुद्रा बचने और कितने रोजगार सृजन की उम्मीद है?",
            "opts": ["Rs 10,000 Cr, 1 lakh jobs", "Rs 40,000 Cr, 5 lakh jobs", "Rs 60,000 Cr, 10 lakh jobs", "Rs 20,000 Cr, 2 lakh jobs", "None of these"],
            "correct": "B",
            "exp_en": "Save > Rs 40,000 Cr forex + 5 lakh jobs + organic manure for soil health.",
            "exp_hi": "40,000 करोड़ से अधिक विदेशी मुद्रा बचत + 5 लाख रोजगार + मिट्टी के लिए जैविक खाद।",
            "point": "GOBARdhan: Rs 40k Cr saving + 5 lakh jobs"
        },
        {
            "q_en": "02 October is observed as International Day of Non-Violence by UN — why?",
            "q_hi": "02 अक्टूबर को संयुक्त राष्ट्र अंतरराष्ट्रीय अहिंसा दिवस के रूप में मनाता है — क्यों?",
            "opts": ["UN Foundation Day", "Gandhi Jayanti", "Shastri Jayanti", "World Peace Day", "None of these"],
            "correct": "B",
            "exp_en": "UNGA declared 02 Oct as International Day of Non-Violence in 2007 to mark Gandhi’s birth anniversary (02 Oct 1869).",
            "exp_hi": "UNGA ने 2007 में गांधी जयंती (02 अक्टूबर 1869) के उपलक्ष्य में 02 अक्टूबर को अंतरराष्ट्रीय अहिंसा दिवस घोषित किया।",
            "point": "02 Oct = Gandhi Jayanti = UN Non-Violence Day (2007)"
        },
        {
            "q_en": "ICAR & FCI signed MoU on 01-02 Oct 2026 for what purpose?",
            "q_hi": "01-02 अक्टूबर 2026 को ICAR और FCI ने किस उद्देश्य से MoU पर हस्ताक्षर किए?",
            "opts": ["MSP procurement", "Alternative fumigation for foodgrain storage", "Seed village scheme", "Crop insurance", "None of these"],
            "correct": "B",
            "exp_en": "To develop alternative fumigation methods for foodgrain storage — safer, low-residue.",
            "exp_hi": "खाद्यान्न भंडारण के लिए वैकल्पिक धूमन विधियाँ विकसित करने हेतु — सुरक्षित, कम अवशेष।",
            "point": "ICAR-FCI MoU = Alternative fumigation"
        },
        {
            "q_en": "Kalaburagi Tur Dal, recently in news for GI tagging, belongs to which state?",
            "q_hi": "हाल में GI टैगिंग के लिए चर्चा में रही कलबुरगी तूर दाल किस राज्य से है?",
            "opts": ["Maharashtra", "Karnataka", "Telangana", "Andhra Pradesh", "None of these"],
            "correct": "B",
            "exp_en": "Kalaburagi (Gulbarga), Karnataka — Tur dal GI push for value addition & export.",
            "exp_hi": "कलबुरगी (गुलबर्गा), कर्नाटक — तूर दाल GI से मूल्यवर्धन और निर्यात को बढ़ावा।",
            "point": "Kalaburagi Tur Dal = Karnataka (GI)"
        },
        {
            "q_en": "Nomura projects RBI repo rate to reach what terminal rate by Dec 2026?",
            "q_hi": "नोमुरा का अनुमान है कि RBI रेपो रेट दिसंबर 2026 तक किस टर्मिनल रेट तक पहुँचेगा?",
            "opts": ["5.25%", "5.50%", "5.75%", "6.00%", "None of these"],
            "correct": "C",
            "exp_en": "Two hikes of 25 bps each in Oct & Dec → 5.75% terminal.",
            "exp_hi": "अक्टूबर और दिसंबर में दो बार 25 bps बढ़ोतरी → 5.75% टर्मिनल।",
            "point": "Repo terminal Dec 2026 = 5.75% (Nomura)"
        },
        {
            "q_en": "Asian Games 2026 are being held in which country?",
            "q_hi": "एशियाई खेल 2026 किस देश में आयोजित हो रहे हैं?",
            "opts": ["China", "South Korea", "Japan", "Qatar", "None of these"],
            "correct": "C",
            "exp_en": "Aichi-Nagoya, Japan — 20 Sep to 05 Oct 2026; India hockey gold there.",
            "exp_hi": "आइची-नागोया, जापान — 20 सितंबर से 05 अक्टूबर 2026; वहीं भारतीय हॉकी स्वर्ण।",
            "point": "Asian Games 2026 = Japan (Aichi-Nagoya)"
        },
        {
            "q_en": "Fertilizer subsidy provision in Union Budget 2026-27 is?",
            "q_hi": "केंद्रीय बजट 2026-27 में उर्वरक सब्सिडी का प्रावधान कितना है?",
            "opts": ["Rs 70,944 Cr", "Rs 1,20,944 Cr", "Rs 1,70,944 Cr", "Rs 2,70,944 Cr", "None of these"],
            "correct": "C",
            "exp_en": "Rs 1,70,944 Cr to keep fertilizers affordable for farmers.",
            "exp_hi": "किसानों के लिए उर्वरक सस्ते रखने हेतु 1,70,944 करोड़ रुपये।",
            "point": "Fertilizer subsidy 2026-27 = Rs 1,70,944 Cr"
        },
    ]
    
    for idx, mq in enumerate(mcqs, 1):
        story.extend(mcq_block(idx, mq["q_en"], mq["q_hi"], mq["opts"], mq["correct"], mq["exp_en"], mq["exp_hi"], mq["point"]))
    
    # ===== ONE-LINER REVISION =====
    one_liner_banner = Table([[Paragraph('<b><font color="white">ONE-LINER CURRENT AFFAIRS</font></b>', ParagraphStyle('olb', parent=STYLES['section_banner'], alignment=TA_CENTER, textColor=white, fontSize=9, leading=11))]], colWidths=[PAGE_W - 20*mm])
    one_liner_banner.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLORS["economy_teal"]),
        ('ROUNDEDCORNERS', [4,4,4,4]),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(one_liner_banner)
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph('<font color="#006064" size="6"><b>  30 One-Liners — Exam से पहले 5 मिनट में रिवीज़न!</b></font>', ParagraphStyle('ol_sub', parent=STYLES['static_text'], alignment=TA_CENTER, textColor=COLORS["economy_teal"], fontSize=6, leading=7)))
    story.append(Spacer(1, 2*mm))
    
    one_liners_all = [
        "GOBARdhan Scheme — <b>Rs 23,731 Cr</b> | <b>10 years (FY27-36)</b> | <b>CBG</b> | Central Sector | MoPNG",
        "Female Farmer Conference — <b>New Delhi</b> | <b>UN Year of Woman Farmer 2026</b> | Women = <b>33% agri workforce</b>",
        "RBI ED — <b>Sudhakar Malli</b> (from 01 Oct 2026) | Supervision Dept | <b>30 years experience</b>",
        "RBI MPC — <b>05-07 Oct 2026</b> | Decision <b>07 Oct</b> | Expected <b>+25 bps → 5.50%</b>",
        "Forex Reserves — <b>-$18.3 bn weekly</b> | <b>Record fall</b> | 3rd week | Total <b>-$38.2 bn</b>",
        "Bulk Deposit Rule — From <b>01 Oct 2026</b> | Disclose by <b>10:10 AM</b> daily on website",
        "Gandhi Jayanti — <b>02 Oct</b> | <b>157th</b> (1869) | UN <b>Non-Violence Day</b> | Shastri Jayanti <b>122nd</b> (1904)",
        "Swachhata Hi Seva — <b>17 Sep-02 Oct 2026</b> | Theme: <b>Swabhav Swachhata, Sanskar Swachhata</b>",
        "Women Hockey — <b>Gold 02 Oct 2026</b> | Beat <b>China 1-0</b> | After <b>44 yrs (1982)</b> | <b>LA Olympics 2028 qualify</b>",
        "Boxing Gold — <b>Lovlina Borgohain</b> (75kg) | Wrestling Gold — <b>Sujeet</b> (65kg) | <b>02 Oct 2026</b>",
        "Budget 2026-27 — Agri <b>Rs 1,32,561 Cr</b> | Agri+Rural <b>Rs 4,35,779 Cr</b> | ICAR <b>Rs 9,967 Cr</b>",
        "Fertilizer Subsidy — <b>Rs 1,70,944 Cr</b> (2026-27) | Affordable inputs for farmers",
        "Bharat-VISTAAR — <b>AI tool</b> for farmers | <b>AgriStack + ICAR</b> | Budget 2026-27 proposal | Multilingual",
        "Nomura Forecast — Repo <b>5.75% by Dec 2026</b> | Two hikes Oct+Dec | Inflation pressure",
        "Bank Share Norms — RBI eases | Funds/insurers can acquire <b>up to 10%</b> with one-time approval",
        "ICAR-FCI MoU — <b>Alternative fumigation</b> for grain storage | Food safety | Low residue",
        "KVKs — <b>731</b> Krishi Vigyan Kendras pan-India under ICAR",
        "Kalaburagi Tur Dal — <b>Karnataka</b> | <b>GI Tag</b> push | Value addition & export",
        "RBI Forward Book — <b>$200 bn</b> net short | Record | FCNR(B) effect",
        "Asian Games 2026 — <b>Japan (Aichi-Nagoya)</b> | <b>20 Sep-05 Oct</b>",
        "MSP Growth since 2014-15 — Ragi <b>236%</b>, Nigerseed <b>179%</b>, Jowar Hybrid <b>163%</b>, Jute <b>147%</b>",
        "FSSAI Link — Food safety in storage innovations; MoU improves grain quality",
        "Special Campaign 6.0 — <b>02-31 Oct 2026</b> | Institutionalizing Swachhata & minimizing pendency",
        "Jai Jawan Jai Kisan — Given by <b>Lal Bahadur Shastri (1965)</b> during Indo-Pak war | Green Revolution push",
        "Sail Bronze — <b>Nethra Kumanan</b> (Sailing) | Asian Games 2026 | 02 Oct 2026",
        "High-Value Crops — Budget focus: <b>Coconut, Cocoa, Cashew, Sandalwood</b> | Rejuvenation of old plantations",
        "FCNR(B) — Foreign Currency Non-Resident (Banks) deposits | Related to RBI swap window closure",
        "PM Mementos — <b>8th Edition</b> auction | Haryana sports achievements highlighted | Ministry of Culture",
        "INS Sahyadri & Kulish — Concluded participation in <b>AIME 2026</b> | Defence news",
        "GOBARdhan Jobs — <b>5 lakh jobs</b> + <b>Rs 40,000 Cr forex saving</b> + <b>Organic manure</b> for soil",
    ]
    for idx, line in enumerate(one_liners_all, 1):
        bg = HexColor("#E0F7FA") if idx % 2 == 0 else white
        p = Paragraph(f'<b><font color="#006064">{idx:02d}.</font></b>  {line}', ParagraphStyle(f'oll{idx}', parent=STYLES['one_liner'], fontSize=11.5, leading=16, spaceAfter=4))
        t = Table([[p]], colWidths=[PAGE_W - 22*mm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), bg),
            ('LEFTPADDING', (0,0), (-1,-1), 3),
            ('RIGHTPADDING', (0,0), (-1,-1), 3),
            ('TOPPADDING', (0,0), (-1,-1), 1.5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 1.5),
            ('ROUNDEDCORNERS', [2,2,2,2]),
            ('BOX', (0,0), (-1,-1), 0.3, HexColor("#B2EBF2") if idx%2==0 else white),
        ]))
        story.append(t)
    
    story.append(Spacer(1, 6*mm))
    
    # Most Important Facts
    most_banner2 = Table([[Paragraph('<b><font color="white">MOST IMPORTANT FACTS</font></b>', ParagraphStyle('mib', parent=STYLES['section_banner'], alignment=TA_CENTER, textColor=white, fontSize=9, leading=11))]], colWidths=[PAGE_W - 20*mm])
    most_banner2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLORS["awards_gold"]),
        ('ROUNDEDCORNERS', [4,4,4,4]),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(most_banner2)
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph('<font color="#F57F17" size="6"><b>*  15 Facts jo exam me direct poochhe ja sakte hain!</b></font>', ParagraphStyle('mi_sub', parent=STYLES['static_text'], alignment=TA_CENTER, textColor=COLORS["awards_gold"], fontSize=6, leading=7)))
    story.append(Spacer(1, 2*mm))
    
    most_facts = [
        "GOBARdhan: <b>Rs 23,731 Cr / 10 years / CBG / LNG save Rs 40k Cr / 5 lakh jobs</b> — Remember: 23,731 & 10 yrs",
        "Female Farmer Conf: <b>UN Year 2026 = Woman Farmer</b> + India 1st conf in <b>New Delhi 02 Oct 2026</b> + 33% workforce",
        "RBI ED: <b>Sudhakar Malli</b> = Supervision (01 Oct 2026) — 30 yrs exp — Don't confuse with Governor Sanjay Malhotra",
        "RBI MPC: <b>05-07 Oct 2026</b> is <b>6-member</b> committee; repo <b>5.25% → 5.50% expected</b> (+25 bps)",
        "Forex: <b>-$18.3 bn = Record weekly fall</b> (02 Oct news) — 3 weeks -$38.2 bn — reason: RBI defends rupee vs crude",
        "Bulk Deposit: <b>Rs 3 Cr+ = bulk</b> | From 01 Oct 2026 disclose <b>10:10 AM</b> — uniform rates",
        "Agri Budget: <b>1,32,561 Cr (2026-27)</b> vs <b>27,663 Cr (2013-14)</b> — 4x increase — Agri+Rural = <b>4,35,779 Cr</b>",
        "Hockey Gold: <b>Women after 44 yrs</b> — <b>1982 New Delhi → 2026 Japan</b> — beat <b>China 1-0</b> — qualify <b>LA 2028</b>",
        "Boxing/Wrestling Gold 02 Oct 2026: <b>Lovlina (75kg)</b> & <b>Sujeet (65kg)</b> — PMO praised — remember weight categories",
        "02 Oct: <b>Gandhi (1869 Porbandar) + Shastri (1904 Varanasi)</b> — UN Non-Violence Day (2007) — Swachh Bharat started 2014",
        "ICAR: <b>Est 16 July 1929, New Delhi, under DARE</b> — Budget <b>Rs 9,967 Cr</b> — <b>731 KVKs</b> pan-India",
        "FCI: <b>14 Jan 1965</b> — procurement & distribution — MoU with ICAR for <b>alternative fumigation</b>",
        "GI Tag: <b>Kalaburagi Tur Dal = Karnataka</b> — first Indian GI was <b>Darjeeling Tea (2004)</b>",
        "Repo Terminal: <b>5.75% by Dec 2026</b> (Nomura) — 2 hikes Oct & Dec — hawkish shift in MPC minutes",
        "Fertilizer Subsidy: <b>Rs 1,70,944 Cr</b> — keep Urea/DAP affordable — related to <b>soil health & natural farming</b>",
    ]
    for idx, fact in enumerate(most_facts, 1):
        p = Paragraph(f'<b><font color="#F57F17">{idx}.</font></b>  {fact}', ParagraphStyle(f'mf{idx}', parent=STYLES['one_liner'], fontSize=7.5, leading=10, spaceAfter=1.5, borderPadding=(2,2,2)))
        # Each fact in card
        t = Table([[Paragraph(f'<b><font color="white">{idx}</font></b>', ParagraphStyle('num_mf', parent=STYLES['one_liner'], alignment=TA_CENTER, textColor=white, fontSize=8, leading=9, fontName=FONT_BOLD)), p]], colWidths=[7*mm, PAGE_W - 29*mm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (0,0), COLORS["awards_gold"]),
            ('BACKGROUND', (1,0), (1,0), COLORS["awards_light"]),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 3),
            ('RIGHTPADDING', (0,0), (-1,-1), 4),
            ('TOPPADDING', (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('ROUNDEDCORNERS', [3,3,3,3]),
            ('BOX', (0,0), (-1,-1), 0.4, HexColor("#FFE082")),
        ]))
        story.append(t)
        story.append(Spacer(1, 1.5*mm))
    
    story.append(Spacer(1, 6*mm))
    
    # Back cover / Thank you
    thank_data = [[Paragraph('<b><font color="white" size="10">THANK YOU</font></b><br/><font color="white" size="6">Thank you for reading Daily Current Affairs! See you tomorrow with new updates.</font>', ParagraphStyle('thank', parent=STYLES['cover_title'], alignment=TA_CENTER, textColor=white, fontSize=10, leading=12))]]
    thank_table = Table(thank_data, colWidths=[PAGE_W - 30*mm])
    thank_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLORS["primary_green"]),
        ('ROUNDEDCORNERS', [6,6,6,6]),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    centered_thank = Table([[thank_table]], colWidths=[PAGE_W - 20*mm])
    centered_thank.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
    story.append(centered_thank)
    story.append(Spacer(1, 1.5*mm))
    story.append(Paragraph('<font color="#212121" size="7"><b>AGRI LEARNING POINT  |  BY SATYAM SIR</b></font><br/><font color="#757575" size="6">AGTA  •  AFO  •  NABARD  •  FCI  •  ICAR  •  Banking & Govt Exams<br/>Telegram: @agrilearningpoint</font>', ParagraphStyle('back', parent=STYLES['cover_tag'], alignment=TA_CENTER, textColor=COLORS["medium_text"], fontSize=7, leading=9)))
    story.append(Spacer(1, 1.5*mm))
    story.append(Paragraph('<font color="#B71C1C" size="6"><b>  Share this PDF with friends — Help them prepare better!</b></font>', ParagraphStyle('share', parent=STYLES['cover_tag'], alignment=TA_CENTER, textColor=COLORS["sports_red"], fontSize=6, leading=7)))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph('<font color="#9E9E9E" size="5">© 2026 Agri Learning Point. All Rights Reserved. | Verified: 02-03 Oct 2026 | For educational purpose only.</font>', ParagraphStyle('copy', parent=STYLES['footer'], alignment=TA_CENTER, textColor=COLORS["light_text"], fontSize=5, leading=6)))
    
    # Build with different page funcs - we need to handle cover vs inner
    # We use a custom onFirstPage for cover, then header_footer for rest
    # Simplest: build with header_footer for all, but cover will have extra header anyway - looks okay
    # Instead we will build story and use onFirstPage=cover_header_footer, onLaterPages=header_footer
    doc.build(story, onFirstPage=cover_header_footer, onLaterPages=header_footer)
    print(f"[OK] PDF generated: {output_path}")
    return output_path

if __name__ == "__main__":
    build_pdf()
