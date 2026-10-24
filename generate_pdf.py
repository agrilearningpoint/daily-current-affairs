#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agri Learning Point - Exam Genius Style Bilingual PDF Generator Engine
======================================================================
Generates publication-quality A4 Bilingual (English + Hindi) Current Affairs PDFs
matching the exact visual architecture of the Exam Genius demo PDF:

  1. Cover Page (Page 1):
     - Curved multi-layered blue wave background
     - 'AGRI LEARNING POINT' -> 'Presents' -> 'AGRI / CURRENT / AFFAIRS'
     - Red 'In Bilingual' + Edition Date ('24 October 2026')
     - Central circular Agri Learning Point badge logo with soft blue ring
     - 5 Exam Pill Badges (UPSC / PCS, IBPS AFO, NABARD, ICAR / JRF, STATE AGRI)
     - Bottom ribbon tagline

  2. Content Pages (Pages 2..N):
     - Top sky-blue curved header arc with dark-blue border ('No. 1 PLATFORM FOR AGRI & GOVT. EXAMS',
       'IBPS AFO | NABARD | ICAR | AGTA | BANKING | SSC', 't.me/agrilearningpoint')
     - Top-right circular Agri Learning Point logo badge overlapping header curve
     - Center faint watermark logo ('AGRI Learning Point')
     - Bottom dark charcoal footer bar featuring the user's 3 official social handles:
         * YouTube: Agri Learning Point
         * Telegram 1: Agri Learning Point
         * Telegram 2: Agri Quiz World
     - Pattern A: MCQ-First Bilingual Flow:
         * Ques: (Bold English)
         * प्रश्न: (Hindi)
         * Options A) to E) (Bilingual EN / HI where applicable)
         * Answer: Option X (Bold)
         * Explanation (व्याख्या): Interleaved English bullet + Hindi bullet pairs
         * Static GK (स्थैतिक सामान्य ज्ञान): Bilingual static facts
     - Pattern B: Rounded Blue Box ('Recent News Headlines Related to ...')
         * Light sky-blue background (#eef6fc) with dark navy rounded border (#0d3b66)
         * Bold centered title + Bilingual bullet pairs
"""

from __future__ import annotations

import base64
import html
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).resolve().parent.parent
import sys
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.branding import BRANDING_CONFIG
from pipeline.content import enrich_item_for_exam_genius_pdf

logger = logging.getLogger("generate_pdf")


def get_shaping_diagnostics() -> tuple[bool, str]:
    """Return Devanagari text shaping diagnostics."""
    try:
        import weasyprint  # noqa: F401
        return True, "WeasyPrint (Pango/HarfBuzz) available for exact Devanagari shaping"
    except ImportError:
        pass
    try:
        import fontTools  # noqa: F401
        return True, "fontTools available for text shaping"
    except ImportError:
        return False, "fontTools not installed"


def _file_to_data_uri(filepath: str | Path) -> str:
    p = Path(filepath)
    if not p.is_file():
        return ""
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{b64}"


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


def _svg_youtube_icon() -> str:
    return (
        '<svg class="social-icon" viewBox="0 0 36 26" xmlns="http://www.w3.org/2000/svg">'
        '<rect x="1" y="1" width="34" height="24" rx="6" fill="#FF0000"/>'
        '<polygon points="14,7 14,19 24,13" fill="#FFFFFF"/>'
        '</svg>'
    )


def _svg_telegram_icon() -> str:
    return (
        '<svg class="social-icon" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">'
        '<circle cx="16" cy="16" r="15" fill="#229ED9"/>'
        '<path d="M7.5 15.6L23.2 9.5C23.9 9.2 24.6 9.7 24.3 10.7L21.6 23.4C21.4 24.3 20.8 24.5 20.1 24.1L15.9 21.0L13.9 22.9C13.7 23.1 13.5 23.3 13.1 23.3L13.4 19.0L21.2 12.0C21.5 11.7 21.1 11.5 20.7 11.8L11.1 17.8L6.9 16.5C6.0 16.2 6.0 15.6 7.5 15.6Z" fill="#FFFFFF"/>'
        '</svg>'
    )


def _svg_badge_icon(kind: str) -> str:
    if kind in ("pillar", "bank"):
        return (
            '<svg class="pill-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">'
            '<path d="M12 2L2 7v2h20V7L12 2zm-7 9v7h3v-7H5zm5.5 0v7h3v-7h-3zM16 11v7h3v-7h-3zM2 20v2h20v-2H2z" fill="#1d4ed8"/>'
            '</svg>'
        )
    if kind == "leaf":
        return (
            '<svg class="pill-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">'
            '<path d="M17 8C8 10 5.9 16.17 3.82 21.34l1.89.66l.95-2.3c.48.17.98.3 1.34.3C19 20 22 3 22 3c-1 2-8 2.25-13 3.25S2 11.5 2 13.5s1.75 3.75 1.75 3.75C7 8 17 8 17 8z" fill="#15803d"/>'
            '</svg>'
        )
    if kind == "user":
        return (
            '<svg class="pill-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">'
            '<circle cx="12" cy="8" r="4" fill="#1d4ed8"/>'
            '<path d="M4 20c0-4 4-6 8-6s8 2 8 6H4z" fill="#1d4ed8"/>'
            '</svg>'
        )
    return (
        '<svg class="pill-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">'
        '<path d="M12 3L1 9l11 6 9-4.91V17h2V9L12 3zm0 13.5L5 12.7v4.3l7 3.8 7-3.8v-4.3l-7 3.8z" fill="#1d4ed8"/>'
        '</svg>'
    )


def _paginate_mcq_blocks(item: Dict[str, Any]) -> List[str]:
    """
    Splits a rich MCQ + Bilingual Explanation + Static GK item into 1 or 2 clean
    page bodies so text never overflows or clips into the footer bar (matching Demo PDF
    where Question + 4-5 Explanation pairs sit on Page N, and remaining Explanation pairs
    + Static GK sit on Page N+1).
    """
    q_en = html.escape(item.get("question_en", ""))
    q_hi = html.escape(item.get("question_hi", ""))
    options = item.get("options") or []
    answer = html.escape(item.get("answer", "Option B"))
    exp_pairs = item.get("explanation_pairs") or []
    static_gk = item.get("static_gk") or []

    # Build Question + Options + Answer HTML
    opts_html_list: List[str] = []
    letters = ["A", "B", "C", "D", "E"]
    for idx, opt_text in enumerate(options[:5]):
        letter = letters[idx]
        opts_html_list.append(f'<div class="mcq-option">{letter}) {html.escape(str(opt_text))}</div>')

    q_header_html = f"""
    <div class="ques-en">Ques: {q_en}</div>
    <div class="ques-hi">प्रश्न: {q_hi}</div>
    <div class="options-block">
      {''.join(opts_html_list)}
    </div>
    <div class="answer-line">Answer: {answer}</div>
    <div class="section-heading">Explanation (व्याख्या):</div>
    """

    # Build each bilingual explanation pair HTML
    exp_blocks: List[str] = []
    for pair in exp_pairs:
        en_t = html.escape(pair.get("en", ""))
        hi_t = html.escape(pair.get("hi", ""))
        b_html = '<div class="exp-pair">'
        if en_t:
            b_html += f'<div class="bullet-en">&bull; {en_t}</div>'
        if hi_t:
            b_html += f'<div class="bullet-hi">&bull; {hi_t}</div>'
        b_html += "</div>"
        exp_blocks.append(b_html)

    # Build Static GK HTML
    gk_html = ""
    if static_gk:
        gk_lines: List[str] = ['<div class="section-heading static-gk-heading">Static GK (स्थैतिक सामान्य ज्ञान):</div>']
        for g in static_gk:
            en_g = html.escape(g.get("en", ""))
            hi_g = html.escape(g.get("hi", ""))
            mode = g.get("mode", "paired")
            if mode == "slash" or not hi_g:
                if ":" in en_g and "/" not in en_g:
                    k, v = en_g.split(":", 1)
                    gk_lines.append(f'<div class="gk-bullet">&bull; <strong>{k}:</strong>{v}</div>')
                else:
                    gk_lines.append(f'<div class="gk-bullet">&bull; {en_g}</div>')
            else:
                if ":" in en_g:
                    k_e, v_e = en_g.split(":", 1)
                    gk_lines.append(f'<div class="gk-bullet">&bull; <strong>{k_e}:</strong>{v_e}</div>')
                else:
                    gk_lines.append(f'<div class="gk-bullet">&bull; {en_g}</div>')
                if ":" in hi_g:
                    k_h, v_h = hi_g.split(":", 1)
                    gk_lines.append(f'<div class="gk-bullet">&bull; <strong>{k_h}:</strong>{v_h}</div>')
                else:
                    gk_lines.append(f'<div class="gk-bullet">&bull; {hi_g}</div>')
        gk_html = '<div class="static-gk-block">' + "".join(gk_lines) + "</div>"

    # Decide whether item fits on 1 page or splits cleanly across 2 pages (like Demo PDF Pages 2-3, 6-7, 8-9)
    total_exp = len(exp_blocks)
    if total_exp <= 3 and len(static_gk) <= 2:
        page1 = q_header_html + "".join(exp_blocks) + gk_html
        return [page1]

    # Split: First 4 explanation pairs on Page 1, remaining explanation pairs + Static GK on Page 2
    first_page_count = 4 if total_exp >= 5 else max(3, total_exp - 1)
    page1_html = q_header_html + "".join(exp_blocks[:first_page_count])
    page2_html = "".join(exp_blocks[first_page_count:]) + gk_html
    if page2_html.strip():
        return [page1_html, page2_html]
    return [page1_html]


def _paginate_recent_headlines_box(box: Dict[str, Any]) -> List[str]:
    """
    Renders 'Recent News Headlines Related to ...' inside the rounded sky-blue box
    (matching Demo PDF Pages 4-5, 11-12, 25-26, 29-30, 39-40).
    """
    title = html.escape(box.get("box_title", "Recent News Headlines :"))
    headlines = box.get("headlines") or []
    if not headlines:
        return []

    # Up to 5 bilingual headline pairs per page inside the rounded blue container
    pages: List[str] = []
    chunk_size = 5
    for i in range(0, len(headlines), chunk_size):
        chunk = headlines[i : i + chunk_size]
        rows: List[str] = []
        if i == 0:
            rows.append(f'<div class="recent-box-title">{title}</div>')
        for h in chunk:
            en_h = html.escape(h.get("en", ""))
            hi_h = html.escape(h.get("hi", ""))
            rows.append(
                '<div class="recent-pair">'
                f'<div class="recent-en">&bull; {en_h}</div>'
                f'<div class="recent-hi">&bull; {hi_h}</div>'
                '</div>'
            )
        box_html = f'<div class="recent-news-box">{"".join(rows)}</div>'
        pages.append(box_html)
    return pages


def build_exam_genius_html(
    items: List[Dict[str, Any]],
    date_str: str | None = None,
    branding: Dict[str, Any] | None = None,
) -> str:
    """Builds the complete standalone HTML document for the Exam-Genius-grade Bilingual PDF."""
    cfg = branding or BRANDING_CONFIG
    display_date = _format_display_date(date_str)

    logo_uri = _file_to_data_uri(cfg.get("logo_path", ROOT_DIR / "assets" / "logo.png"))
    watermark_uri = _file_to_data_uri(cfg.get("watermark_path", ROOT_DIR / "assets" / "watermark_logo.png"))

    # Cover Page Pill Badges
    badges_html_list: List[str] = []
    for b in cfg.get("cover_exam_badges", []):
        icon_svg = _svg_badge_icon(b.get("icon", "pillar"))
        lbl = html.escape(b.get("label", ""))
        badges_html_list.append(
            f'<div class="cover-pill">{icon_svg}<span>{lbl}</span></div>'
        )

    # Bottom Social Bar (3 handles: 1 YouTube + 2 Telegram)
    social_html_list: List[str] = []
    for s in cfg.get("social_handles", []):
        plat = s.get("platform", "telegram").lower()
        icon = _svg_youtube_icon() if plat == "youtube" else _svg_telegram_icon()
        lbl = html.escape(s.get("label", "Agri Learning Point"))
        url = html.escape(s.get("url", "#"))
        social_html_list.append(
            f'<a class="social-item" href="{url}">{icon}<span class="social-label">{lbl}</span></a>'
        )
    social_footer_html = "".join(social_html_list)

    # Top Header HTML + Bottom Footer HTML reused on every content page
    def wrap_content_page(inner_body_html: str) -> str:
        return f"""
        <div class="pdf-page content-page">
          <!-- Top Curved Sky-Blue Header -->
          <div class="top-header-wrap">
            <svg class="header-bg-svg" viewBox="0 0 595.5 92" preserveAspectRatio="none">
              <path d="M0,0 L595.5,0 L595.5,48 Q297.75,92 0,48 Z" fill="#0d2e5c"/>
              <path d="M0,0 L595.5,0 L595.5,44 Q297.75,88 0,44 Z" fill="#5fb4f5"/>
            </svg>
            <div class="header-text-block">
              <div class="hdr-line-1">{html.escape(cfg.get("header_line_1", ""))}</div>
              <div class="hdr-line-2">{html.escape(cfg.get("header_line_2", ""))}</div>
              <div class="hdr-line-3"><a href="{html.escape(cfg.get("header_link_url", "#"))}">{html.escape(cfg.get("header_link_text", ""))}</a></div>
            </div>
            <div class="header-logo-badge">
              <img src="{logo_uri}" alt="Agri Learning Point Logo"/>
            </div>
          </div>

          <!-- Center Page Watermark -->
          <div class="center-watermark">
            <img src="{watermark_uri}" alt=""/>
          </div>

          <!-- Main Content Flow Area -->
          <div class="page-body-content">
            {inner_body_html}
          </div>

          <!-- Bottom Dark Social Bar (YouTube + 2 Telegram Channels) -->
          <div class="bottom-social-bar">
            {social_footer_html}
          </div>
        </div>
        """

    # Build all content pages
    content_pages_html: List[str] = []
    for item in items:
        for p_html in _paginate_mcq_blocks(item):
            content_pages_html.append(wrap_content_page(p_html))
        box = item.get("recent_headlines_box")
        if box and isinstance(box, dict):
            for box_page_html in _paginate_recent_headlines_box(box):
                content_pages_html.append(wrap_content_page(box_page_html))

    hero_lines = cfg.get("cover_hero_lines", ["AGRI", "CURRENT", "AFFAIRS"])
    hero_html = "<br/>".join(html.escape(line) for line in hero_lines)

    cover_page_html = f"""
    <div class="pdf-page cover-page">
      <!-- Multi-layered Curved Wave SVG Background (Identical geometry to Demo PDF Page 1) -->
      <svg class="cover-bg-svg" viewBox="0 0 595.5 842.25" preserveAspectRatio="none">
        <defs>
          <linearGradient id="topSkyGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#bce3ff"/>
            <stop offset="50%" stop-color="#8fd0fc"/>
            <stop offset="100%" stop-color="#5cb6f9"/>
          </linearGradient>
          <linearGradient id="bottomNavyGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#0b4f9c"/>
            <stop offset="55%" stop-color="#083675"/>
            <stop offset="100%" stop-color="#041e4a"/>
          </linearGradient>
        </defs>
        <!-- Base White/Soft Blue -->
        <rect x="0" y="0" width="595.5" height="842.25" fill="#f3f9ff"/>
        <!-- Soft light-blue diagonal wave layer -->
        <path d="M0,180 Q240,410 595.5,380 L595.5,650 L0,650 Z" fill="#e1f2fe"/>
        <!-- Top Sky-Blue Curved Canopy -->
        <path d="M0,0 L595.5,0 L595.5,395 Q330,415 160,305 Q55,235 0,145 Z" fill="url(#topSkyGrad)"/>
        <!-- Bottom Deep Navy Wave Section -->
        <path d="M0,615 Q245,455 595.5,390 L595.5,842.25 L0,842.25 Z" fill="url(#bottomNavyGrad)"/>
      </svg>

      <!-- Cover Top Text Block -->
      <div class="cover-top-content">
        <div class="cover-brand-title">{html.escape(cfg.get("brand_title_upper", "AGRI LEARNING POINT"))}</div>
        <div class="cover-presents">{html.escape(cfg.get("presents_text", "Presents"))}</div>
        <div class="cover-hero-title">{hero_html}</div>
        <div class="cover-bilingual">{html.escape(cfg.get("bilingual_tag", "In Bilingual"))}</div>
        <div class="cover-date">{html.escape(display_date)}</div>
      </div>

      <!-- Center Circular Logo Emblem -->
      <div class="cover-logo-container">
        <div class="cover-logo-ring">
          <img src="{logo_uri}" alt="Agri Learning Point"/>
        </div>
      </div>

      <!-- 5 Exam Pill Badges Row -->
      <div class="cover-pills-row">
        {''.join(badges_html_list)}
      </div>

      <!-- Bottom Ribbon Strip -->
      <div class="cover-bottom-strip">
        {html.escape(cfg.get("bottom_tagline", ""))}
      </div>
    </div>
    """

    full_html = f"""<!DOCTYPE html>
<html lang="hi">
<head>
  <meta charset="utf-8"/>
  <title>Agri Learning Point - Daily Current Affairs ({html.escape(display_date)})</title>
  <style>
    @page {{
      size: 595.5pt 842.25pt;
      margin: 0;
    }}
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}
    html, body {{
      width: 595.5pt;
      margin: 0;
      padding: 0;
      background: #ffffff;
      font-family: 'Poppins', 'DejaVu Sans', 'Noto Sans', 'Noto Sans Devanagari', 'Mukta', sans-serif;
      color: #0f172a;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }}

    /* Fixed Page Container */
    .pdf-page {{
      position: relative;
      width: 595.5pt;
      height: 842.25pt;
      overflow: hidden;
      page-break-after: always;
      break-after: page;
      background: #ffffff;
    }}
    .pdf-page:last-child {{
      page-break-after: auto;
      break-after: auto;
    }}

    /* ================= COVER PAGE (PAGE 1) ================= */
    .cover-bg-svg {{
      position: absolute;
      top: 0;
      left: 0;
      width: 595.5pt;
      height: 842.25pt;
      z-index: 1;
    }}
    .cover-top-content {{
      position: relative;
      z-index: 5;
      text-align: center;
      padding-top: 44pt;
    }}
    .cover-brand-title {{
      font-size: 25pt;
      font-weight: 800;
      color: #072f5f;
      letter-spacing: 0.8pt;
      margin-bottom: 8pt;
    }}
    .cover-presents {{
      font-size: 16.5pt;
      font-weight: 700;
      color: #0f2942;
      margin-bottom: 18pt;
    }}
    .cover-hero-title {{
      font-size: 36pt;
      font-weight: 900;
      font-style: italic;
      line-height: 1.18;
      color: #0d4a8f;
      letter-spacing: 1.2pt;
      text-shadow: 0 1px 2px rgba(255, 255, 255, 0.5);
      margin-bottom: 14pt;
    }}
    .cover-bilingual {{
      font-size: 20pt;
      font-weight: 800;
      color: #d90429;
      margin-bottom: 10pt;
    }}
    .cover-date {{
      font-size: 18pt;
      font-weight: 800;
      color: #072f5f;
    }}
    .cover-logo-container {{
      position: absolute;
      top: 392pt;
      left: 0;
      width: 595.5pt;
      display: flex;
      justify-content: center;
      align-items: center;
      z-index: 6;
    }}
    .cover-logo-ring {{
      width: 176pt;
      height: 176pt;
      border-radius: 50%;
      background: #ffffff;
      padding: 4pt;
      box-shadow: 0 6pt 18pt rgba(4, 30, 74, 0.28);
      display: flex;
      justify-content: center;
      align-items: center;
      margin: 0 auto;
    }}
    .cover-logo-ring img {{
      width: 168pt;
      height: 168pt;
      border-radius: 50%;
      display: block;
    }}
    .cover-pills-row {{
      position: absolute;
      bottom: 166pt;
      left: 24pt;
      right: 24pt;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 7pt;
      z-index: 6;
    }}
    .cover-pill {{
      flex: 1;
      background: #bce3ff;
      border: 2pt solid #ffffff;
      border-radius: 22pt;
      padding: 6pt 8pt;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 4pt;
      font-size: 9.5pt;
      font-weight: 800;
      color: #072f5f;
      white-space: nowrap;
      box-shadow: 0 3pt 8pt rgba(0, 0, 0, 0.22);
    }}
    .pill-icon {{
      width: 13pt;
      height: 13pt;
      flex-shrink: 0;
    }}
    .cover-bottom-strip {{
      position: absolute;
      bottom: 18pt;
      left: 0;
      width: 595.5pt;
      height: 30pt;
      background: #0d5bb5;
      color: #ffffff;
      font-size: 11.2pt;
      font-weight: 700;
      display: flex;
      align-items: center;
      justify-content: center;
      text-align: center;
      z-index: 6;
      letter-spacing: 0.2pt;
    }}

    /* ================= CONTENT PAGES (PAGES 2..N) ================= */
    .top-header-wrap {{
      position: absolute;
      top: 0;
      left: 0;
      width: 595.5pt;
      height: 92pt;
      z-index: 5;
    }}
    .header-bg-svg {{
      position: absolute;
      top: 0;
      left: 0;
      width: 595.5pt;
      height: 82pt;
      z-index: 1;
    }}
    .header-text-block {{
      position: relative;
      z-index: 3;
      text-align: center;
      padding-top: 7pt;
      padding-right: 45pt;
    }}
    .hdr-line-1 {{
      font-size: 11.5pt;
      font-weight: 800;
      color: #072b52;
      line-height: 1.25;
      letter-spacing: 0.3pt;
    }}
    .hdr-line-2 {{
      font-size: 10.5pt;
      font-weight: 800;
      color: #072b52;
      line-height: 1.25;
    }}
    .hdr-line-3 a {{
      font-size: 10.5pt;
      font-weight: 700;
      color: #072b52;
      text-decoration: underline;
    }}
    .header-logo-badge {{
      position: absolute;
      top: 6pt;
      right: 16pt;
      width: 78pt;
      height: 78pt;
      border-radius: 50%;
      background: #ffffff;
      border: 3pt solid #5fb4f5;
      box-shadow: 0 2pt 8pt rgba(13, 46, 92, 0.22);
      z-index: 6;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .header-logo-badge img {{
      width: 72pt;
      height: 72pt;
      border-radius: 50%;
      display: block;
    }}

    /* Center Watermark */
    .center-watermark {{
      position: absolute;
      top: 235pt;
      left: 117.75pt;
      width: 360pt;
      height: 360pt;
      z-index: 1;
      pointer-events: none;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .center-watermark img {{
      width: 350pt;
      height: 350pt;
      display: block;
    }}

    /* Main Content Body */
    .page-body-content {{
      position: relative;
      z-index: 4;
      padding: 90pt 18pt 46pt 18pt;
      font-size: 12pt;
      line-height: 1.44;
      color: #0a0a0a;
    }}

    /* Question & Options Typography */
    .ques-en {{
      font-size: 13pt;
      font-weight: 700;
      color: #000000;
      line-height: 1.38;
      margin-bottom: 4pt;
    }}
    .ques-hi {{
      font-size: 12.6pt;
      font-weight: 500;
      color: #000000;
      line-height: 1.44;
      margin-bottom: 12pt;
    }}
    .options-block {{
      margin-bottom: 12pt;
    }}
    .mcq-option {{
      font-size: 12pt;
      font-weight: 400;
      color: #000000;
      line-height: 1.45;
      margin-bottom: 2pt;
    }}
    .answer-line {{
      font-size: 12.5pt;
      font-weight: 700;
      color: #000000;
      margin-top: 8pt;
      margin-bottom: 12pt;
    }}
    .section-heading {{
      font-size: 12.5pt;
      font-weight: 700;
      color: #000000;
      margin-top: 8pt;
      margin-bottom: 10pt;
    }}
    .static-gk-heading {{
      margin-top: 16pt;
      margin-bottom: 10pt;
    }}
    .exp-pair {{
      margin-bottom: 6pt;
    }}
    .bullet-en {{
      font-size: 11.8pt;
      font-weight: 400;
      color: #0a0a0a;
      line-height: 1.42;
      margin-bottom: 2pt;
    }}
    .bullet-hi {{
      font-size: 11.8pt;
      font-weight: 400;
      color: #0a0a0a;
      line-height: 1.46;
      margin-bottom: 4pt;
    }}
    .static-gk-block {{
      margin-top: 6pt;
    }}
    .gk-bullet {{
      font-size: 11.8pt;
      line-height: 1.46;
      color: #0a0a0a;
      margin-bottom: 3pt;
    }}

    /* Rounded Sky-Blue Box ('Recent News Headlines Related to ...') */
    .recent-news-box {{
      margin-top: 6pt;
      min-height: 675pt;
      background: rgba(235, 245, 255, 0.88);
      border: 2pt solid #0d3b66;
      border-radius: 24pt;
      padding: 20pt 18pt;
    }}
    .recent-box-title {{
      text-align: center;
      font-size: 15.5pt;
      font-weight: 800;
      color: #0f172a;
      margin-bottom: 14pt;
    }}
    .recent-pair {{
      margin-bottom: 12pt;
    }}
    .recent-en {{
      font-size: 11.6pt;
      font-weight: 700;
      color: #0f172a;
      line-height: 1.42;
      margin-bottom: 2pt;
    }}
    .recent-hi {{
      font-size: 11.5pt;
      font-weight: 700;
      color: #0f172a;
      line-height: 1.45;
    }}

    /* Bottom Social Bar (3 Channels: YouTube + 2 Telegram) */
    .bottom-social-bar {{
      position: absolute;
      bottom: 0;
      left: 0;
      width: 595.5pt;
      height: 34pt;
      background: #191919;
      display: flex;
      justify-content: space-around;
      align-items: center;
      padding: 0 18pt;
      z-index: 10;
    }}
    .social-item {{
      display: flex;
      align-items: center;
      gap: 7pt;
      text-decoration: none;
      color: #ffffff;
    }}
    .social-icon {{
      width: 22pt;
      height: 22pt;
      flex-shrink: 0;
    }}
    .social-label {{
      font-size: 9.5pt;
      font-weight: 700;
      color: #ffffff;
      text-decoration: underline;
      white-space: nowrap;
    }}
  </style>
</head>
<body>
  {cover_page_html}
  {''.join(content_pages_html)}
</body>
</html>
"""
    return full_html


def generate_pdf(
    content_data: Dict[str, Any],
    mcq_data: List[Dict[str, Any]] | None = None,
    output_path: str = "output/daily.pdf",
    date_str: str | None = None,
) -> str:
    """
    Renders the Agri Learning Point Bilingual PDF (in the Exam Genius visual layout)
    from `content_data` and `mcq_data`.

    Rendering order of preference:
      1. WeasyPrint (native Pango + HarfBuzz Devanagari shaping)
      2. Headless Chromium (`compile_and_render.py` / Selenium CDP printToPDF)
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    raw_items = content_data.get("items") or []
    mcqs = mcq_data or []
    mcq_by_id = {m.get("id", i + 1): m for i, m in enumerate(mcqs) if isinstance(m, dict)}

    merged_items: List[Dict[str, Any]] = []
    for idx, item in enumerate(raw_items, start=1):
        item_id = item.get("id", idx)
        matched_mcq = mcq_by_id.get(item_id) or (mcqs[idx - 1] if idx - 1 < len(mcqs) else None)
        merged_items.append(enrich_item_for_exam_genius_pdf(item, matched_mcq))

    if not date_str:
        date_str = content_data.get("date") or output_file.stem

    html_str = build_exam_genius_html(merged_items, date_str=date_str)
    html_debug_path = output_file.with_suffix(".html")
    html_debug_path.write_text(html_str, encoding="utf-8")

    # 1. Try WeasyPrint first (fast, exact A4 sizing, Pango/HarfBuzz Hindi shaping)
    try:
        import weasyprint
        weasyprint.HTML(string=html_str, base_url=str(ROOT_DIR)).write_pdf(str(output_file))
        logger.info("Rendered Bilingual PDF via WeasyPrint -> %s", output_file)
        return str(output_file)
    except Exception as exc:
        logger.warning("WeasyPrint render fallback triggered: %s", exc)

    # 2. Fallback to Headless Chromium printToPDF
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=chrome_options)
        try:
            driver.get(html_debug_path.resolve().as_uri())
            pdf_b64 = driver.execute_cdp_cmd(
                "Page.printToPDF",
                {
                    "printBackground": True,
                    "paperWidth": 8.27,
                    "paperHeight": 11.70,
                    "marginTop": 0,
                    "marginBottom": 0,
                    "marginLeft": 0,
                    "marginRight": 0,
                    "preferCSSPageSize": True,
                },
            )["data"]
            output_file.write_bytes(base64.b64decode(pdf_b64))
            logger.info("Rendered Bilingual PDF via Chromium -> %s", output_file)
            return str(output_file)
        finally:
            driver.quit()
    except Exception as exc:
        logger.error("Chromium PDF rendering failed: %s", exc)
        raise
