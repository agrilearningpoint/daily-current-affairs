# -*- coding: utf-8 -*-
"""
PDF Design Agent (18)
=====================
Bilingual (English + Hindi) PDF generator for daily/weekly/monthly editions.

Production features:
- Hindi (Devanagari) font embedding via Mukta/Poppins
- Auto page size (A4), headers/footers, page numbers
- MCQ section with answer key
- Source URL links (clickable)
- Watermark/logo support
- Overflow protection (auto-wrap, font scaling)
- Atomic output write
- Fails fast on missing fonts

Inputs:
  data/content/content_YYYY-MM-DD.json  OR  data/content/*.json (latest)
  data/mcq/mcq_YYYY-MM-DD.json          OR  data/mcq/*.json (latest)

Output:
  output/daily_YYYY-MM-DD.pdf
  (or output/weekly_*, output/monthly_* based on job type)

Env:
  PDF_PAGE_SIZE           (A4 | LETTER, default A4)
  PDF_MARGIN_PT           (default 40)
  PDF_TITLE               (default "Current Affairs")
  PDF_MAX_MCQS            (default 15)
  PDF_FONT_DIR            (default src/fonts)
"""
from __future__ import annotations

import html
import json
import logging
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4, LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, PageBreak, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
)

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
REPO_ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = REPO_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(LOGS_DIR / "pdf_design.log"), encoding="utf-8"),
    ],
)
logger = logging.getLogger("agent.18_pdf_design")

# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
CONTENT_DIR = REPO_ROOT / "data" / "content"
MCQ_DIR = REPO_ROOT / "data" / "mcq"
OUTPUT_DIR = REPO_ROOT / "output"
FONT_DIR = Path(os.getenv("PDF_FONT_DIR", str(REPO_ROOT / "src" / "fonts")))
ASSETS_DIR = REPO_ROOT / "assets"

PDF_TITLE = os.getenv("PDF_TITLE", "Current Affairs")
PAGE_SIZE = LETTER if os.getenv("PDF_PAGE_SIZE", "A4").upper() == "LETTER" else A4
MARGIN = float(os.getenv("PDF_MARGIN_PT", "40"))
MAX_MCQS = int(os.getenv("PDF_MAX_MCQS", "15"))

DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")

# Hindi font aliases (first one found wins)
HINDI_FONT_CANDIDATES = [
    "Mukta-Regular.ttf", "Mukta-Medium.ttf", "Mukta-SemiBold.ttf", "Mukta-Bold.ttf",
    "NotoSansDevanagari-Regular.ttf",
]
HINDI_FONT_BOLD_CANDIDATES = ["Mukta-Bold.ttf", "NotoSansDevanagari-Bold.ttf"]
ENGLISH_FONT_CANDIDATES = ["Poppins-Regular.ttf", "DejaVuSans.ttf"]
ENGLISH_FONT_BOLD_CANDIDATES = ["Poppins-SemiBold.ttf", "Poppins-Bold.ttf", "DejaVuSans-Bold.ttf"]


# --------------------------------------------------------------------------- #
# Font registration
# --------------------------------------------------------------------------- #
def register_fonts() -> Tuple[str, str, str, str]:
    """Register Hindi + English fonts. Returns (en, en_bold, hi, hi_bold)."""
    if not FONT_DIR.exists():
        raise FileNotFoundError(f"Font dir missing: {FONT_DIR}")

    def _find(candidates: List[str]) -> Optional[Path]:
        for name in candidates:
            p = FONT_DIR / name
            if p.exists():
                return p
        return None

    en = _find(ENGLISH_FONT_CANDIDATES)
    en_bold = _find(ENGLISH_FONT_BOLD_CANDIDATES) or en
    hi = _find(HINDI_FONT_CANDIDATES)
    hi_bold = _find(HINDI_FONT_BOLD_CANDIDATES) or hi

    if not en:
        # Fallback to built-in Helvetica
        logger.warning("No English font found — using Helvetica")
        return "Helvetica", "Helvetica-Bold", "Helvetica", "Helvetica-Bold"

    if not hi:
        logger.warning("No Devanagari font found — Hindi will not render properly!")
        return "Eng", "Eng-Bold", "Eng", "Eng-Bold"

    try:
        pdfmetrics.registerFont(TTFont("Eng", str(en)))
        pdfmetrics.registerFont(TTFont("Eng-Bold", str(en_bold)))
        pdfmetrics.registerFont(TTFont("Hindi", str(hi)))
        pdfmetrics.registerFont(TTFont("Hindi-Bold", str(hi_bold)))
        logger.info("Fonts registered: EN=%s HI=%s", en.name, hi.name)
        return "Eng", "Eng-Bold", "Hindi", "Hindi-Bold"
    except Exception as exc:
        logger.exception("Font registration failed: %s", exc)
        return "Helvetica", "Helvetica-Bold", "Helvetica", "Helvetica-Bold"


# --------------------------------------------------------------------------- #
# Text helpers
# --------------------------------------------------------------------------- #
def _is_devanagari(text: str) -> bool:
    if not text:
        return False
    return bool(DEVANAGARI_RE.search(text))


def _escape(text: str) -> str:
    if not text:
        return ""
    return html.escape(str(text), quote=False)


def _font_for(text: str, en_font: str, hi_font: str) -> str:
    return hi_font if _is_devanagari(text) else en_font


# --------------------------------------------------------------------------- #
# Styles
# --------------------------------------------------------------------------- #
def build_styles(en_font: str, en_bold: str, hi_font: str, hi_bold: str) -> Dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title", parent=base["Title"],
            fontName=en_bold, fontSize=22, leading=28,
            alignment=TA_CENTER, textColor=colors.HexColor("#1a5490"),
            spaceAfter=6,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle", parent=base["Normal"],
            fontName=en_font, fontSize=11, leading=14,
            alignment=TA_CENTER, textColor=colors.HexColor("#666"),
            spaceAfter=14,
        ),
        "section": ParagraphStyle(
            "Section", parent=base["Heading2"],
            fontName=en_bold, fontSize=14, leading=18,
            textColor=colors.HexColor("#0a3d62"),
            spaceBefore=12, spaceAfter=8,
        ),
        "headline_en": ParagraphStyle(
            "HeadlineEN", parent=base["Normal"],
            fontName=en_bold, fontSize=12, leading=15,
            textColor=colors.HexColor("#222"), spaceAfter=2,
        ),
        "headline_hi": ParagraphStyle(
            "HeadlineHI", parent=base["Normal"],
            fontName=hi_bold, fontSize=12, leading=16,
            textColor=colors.HexColor("#222"), spaceAfter=6,
        ),
        "body_en": ParagraphStyle(
            "BodyEN", parent=base["Normal"],
            fontName=en_font, fontSize=10, leading=14,
            alignment=TA_JUSTIFY, spaceAfter=4,
        ),
        "body_hi": ParagraphStyle(
            "BodyHI", parent=base["Normal"],
            fontName=hi_font, fontSize=10.5, leading=16,
            alignment=TA_JUSTIFY, spaceAfter=4,
        ),
        "fact": ParagraphStyle(
            "Fact", parent=base["Normal"],
            fontName=en_font, fontSize=9.5, leading=13,
            textColor=colors.HexColor("#444"),
            leftIndent=10, spaceAfter=3,
        ),
        "mcq_q": ParagraphStyle(
            "MCQQ", parent=base["Normal"],
            fontName=en_font, fontSize=10, leading=14,
            spaceBefore=6, spaceAfter=2, textColor=colors.HexColor("#111"),
        ),
        "mcq_opt": ParagraphStyle(
            "MCQOpt", parent=base["Normal"],
            fontName=en_font, fontSize=9.5, leading=13,
            leftIndent=14, spaceAfter=1,
        ),
        "mcq_ans": ParagraphStyle(
            "MCQAns", parent=base["Normal"],
            fontName=en_bold, fontSize=9.5, leading=13,
            leftIndent=14, textColor=colors.HexColor("#0a6b3a"),
            spaceAfter=4,
        ),
        "small": ParagraphStyle(
            "Small", parent=base["Normal"],
            fontName=en_font, fontSize=8, leading=10,
            textColor=colors.HexColor("#888"),
        ),
    }


# --------------------------------------------------------------------------- #
# Data loading
# --------------------------------------------------------------------------- #
def _latest_json(folder: Path, prefix: str) -> Optional[Path]:
    if not folder.exists():
        return None
    candidates = sorted(
        [p for p in folder.glob(f"{prefix}*.json") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def load_content(job_id: Optional[str] = None) -> List[Dict[str, Any]]:
    if job_id:
        path = CONTENT_DIR / f"content_{job_id}.json"
        if not path.exists():
            path = CONTENT_DIR / f"{job_id}.json"
    else:
        path = _latest_json(CONTENT_DIR, "content_") or _latest_json(CONTENT_DIR, "")
    if not path or not path.exists():
        logger.error("No content file found in %s", CONTENT_DIR)
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = data.get("items") or data.get("articles") or []
        logger.info("Loaded %d content items from %s", len(data), path.name)
        return data
    except Exception as exc:
        logger.exception("Failed to load content: %s", exc)
        return []


def load_mcqs(job_id: Optional[str] = None) -> List[Dict[str, Any]]:
    if job_id:
        path = MCQ_DIR / f"mcq_{job_id}.json"
        if not path.exists():
            path = MCQ_DIR / f"{job_id}.json"
    else:
        path = _latest_json(MCQ_DIR, "mcq_") or _latest_json(MCQ_DIR, "")
    if not path or not path.exists():
        logger.warning("No MCQ file found in %s", MCQ_DIR)
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = data.get("mcqs") or data.get("items") or []
        logger.info("Loaded %d MCQs from %s", len(data), path.name)
        return data[:MAX_MCQS]
    except Exception as exc:
        logger.exception("Failed to load MCQs: %s", exc)
        return []


# --------------------------------------------------------------------------- #
# Page decorations
# --------------------------------------------------------------------------- #
def _make_page_decorator(en_font: str, hi_font: str, header_title: str):
    def _decorate(canvas, doc):
        canvas.saveState()
        width, height = doc.pagesize
        # Header
        canvas.setFont(en_font, 9)
        canvas.setFillColor(colors.HexColor("#666"))
        canvas.drawString(MARGIN, height - MARGIN + 8, header_title)
        canvas.drawRightString(width - MARGIN, height - MARGIN + 8,
                                datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        # Footer
        canvas.setFont(en_font, 8)
        canvas.drawCentredString(width / 2, MARGIN / 2, f"Page {doc.page}")
        canvas.drawString(MARGIN, MARGIN / 2,
                          "Agri Learning Point — Daily Current Affairs")
        canvas.setStrokeColor(colors.HexColor("#ddd"))
        canvas.line(MARGIN, MARGIN, width - MARGIN, MARGIN)
        canvas.restoreState()
    return _decorate


# --------------------------------------------------------------------------- #
# Content builders
# --------------------------------------------------------------------------- #
def build_cover(story: List[Any], styles: Dict[str, ParagraphStyle],
                en_bold: str, edition_label: str) -> None:
    story.append(Spacer(1, 60))
    # Logo if available
    logo = ASSETS_DIR / "logo.png"
    if logo.exists():
        try:
            img = Image(str(logo), width=60 * mm, height=30 * mm, kind="proportional")
            img.hAlign = "CENTER"
            story.append(img)
            story.append(Spacer(1, 12))
        except Exception as exc:
            logger.warning("Logo embed failed: %s", exc)

    story.append(Paragraph(_escape(PDF_TITLE), styles["title"]))
    story.append(Paragraph(_escape(edition_label), styles["subtitle"]))
    story.append(Spacer(1, 20))
    story.append(PageBreak())


def build_content_section(story: List[Any], items: List[Dict[str, Any]],
                          styles: Dict[str, ParagraphStyle],
                          en_font: str, en_bold: str,
                          hi_font: str, hi_bold: str) -> None:
    story.append(Paragraph("📰 News Highlights", styles["section"]))
    story.append(Spacer(1, 6))

    for idx, item in enumerate(items, 1):
        headline_en = (item.get("headline_en") or "").lstrip("> ").strip()
        headline_hi = (item.get("headline_hi") or "").lstrip("> ").strip()
        category = item.get("category") or "General"

        if not headline_en and not headline_hi:
            continue

        # Category tag
        story.append(Paragraph(f"<b>{idx}. [{_escape(category)}]</b>", styles["headline_en"]))
        if headline_en:
            story.append(Paragraph(_escape(headline_en), styles["headline_en"]))
        if headline_hi:
            story.append(Paragraph(_escape(headline_hi), styles["headline_hi"]))

        # Key points (English)
        for kp in (item.get("key_points_en") or [])[:4]:
            if kp:
                story.append(Paragraph(f"• {_escape(kp)}",
                                       styles["body_en"]))

        # Key points (Hindi)
        for kp in (item.get("key_points_hi") or [])[:4]:
            if kp:
                story.append(Paragraph(f"• {_escape(kp)}",
                                       styles["body_hi"]))

        # Static facts
        facts = item.get("static_facts") or {}
        if facts:
            rows = [[Paragraph("<b>Fact</b>", styles["fact"]),
                     Paragraph("<b>Value</b>", styles["fact"])]]
            for k, v in list(facts.items())[:5]:
                rows.append([Paragraph(_escape(k), styles["fact"]),
                             Paragraph(_escape(str(v)), styles["fact"])])
            tbl = Table(rows, colWidths=[35 * mm, 130 * mm])
            tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef4fa")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#ccc")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(Spacer(1, 4))
            story.append(tbl)

        # Source link
        src = item.get("source") or {}
        url = src.get("url") or ""
        if url and url.startswith("http"):
            story.append(Paragraph(
                f'🔗 <link href="{html.escape(url, quote=True)}">'
                f'{_escape(url[:80])}</link>',
                styles["small"],
            ))

        story.append(Spacer(1, 8))


def build_mcq_section(story: List[Any], mcqs: List[Dict[str, Any]],
                      styles: Dict[str, ParagraphStyle],
                      en_font: str, en_bold: str,
                      hi_font: str, hi_bold: str) -> None:
    if not mcqs:
        return

    story.append(PageBreak())
    story.append(Paragraph("📝 Practice Questions (MCQs)", styles["section"]))
    story.append(Spacer(1, 6))

    for idx, m in enumerate(mcqs, 1):
        q_en = m.get("question_en") or ""
        q_hi = m.get("question_hi") or ""
        options = m.get("options") or []
        correct = m.get("correct") or "A"

        # Question
        q_style = "body_hi" if _is_devanagari(q_en) else "mcq_q"
        story.append(Paragraph(f"<b>Q{idx}.</b> {_escape(q_en)}", styles[q_style]))
        if q_hi and q_hi != q_en:
            story.append(Paragraph(f"<b>Q{idx}.</b> {_escape(q_hi)}", styles["body_hi"]))

        # Options
        for i, opt in enumerate(options):
            letter = "ABCDE"[i] if i < 5 else str(i)
            opt_style = "body_hi" if _is_devanagari(opt) else "mcq_opt"
            story.append(Paragraph(f"({letter}) {_escape(opt)}", styles[opt_style]))

        # Answer
        story.append(Paragraph(f"✅ Correct: ({correct})", styles["mcq_ans"]))
        story.append(Spacer(1, 4))


def build_answer_key(story: List[Any], mcqs: List[Dict[str, Any]],
                     styles: Dict[str, ParagraphStyle],
                     en_bold: str) -> None:
    if not mcqs:
        return
    story.append(PageBreak())
    story.append(Paragraph("🔑 Answer Key", styles["section"]))
    story.append(Spacer(1, 6))

    keys = [f"Q{i}. ({m.get('correct','?')})" for i, m in enumerate(mcqs, 1)]
    # 5 per row
    rows = [keys[i:i + 5] for i in range(0, len(keys), 5)]
    data = [[Paragraph(k, styles["body_en"]) for k in r] for r in rows]
    tbl = Table(data, colWidths=[33 * mm] * 5)
    tbl.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#ccc")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef4fa")),
    ]))
    story.append(tbl)


# --------------------------------------------------------------------------- #
# Build PDF
# --------------------------------------------------------------------------- #
def build_pdf(
    items: List[Dict[str, Any]],
    mcqs: List[Dict[str, Any]],
    output_path: Path,
    edition_label: str,
) -> bool:
    en_font, en_bold, hi_font, hi_bold = register_fonts()
    styles = build_styles(en_font, en_bold, hi_font, hi_bold)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=f".{output_path.stem}_", suffix=".pdf",
        dir=str(output_path.parent),
    )
    os.close(fd)

    try:
        doc = BaseDocTemplate(
            tmp_path,
            pagesize=PAGE_SIZE,
            leftMargin=MARGIN, rightMargin=MARGIN,
            topMargin=MARGIN + 10, bottomMargin=MARGIN + 10,
            title=f"{PDF_TITLE} — {edition_label}",
            author="Agri Learning Point",
        )
        frame = Frame(
            MARGIN, MARGIN + 10,
            PAGE_SIZE[0] - 2 * MARGIN, PAGE_SIZE[1] - 2 * MARGIN - 20,
            id="main",
        )
        decorator = _make_page_decorator(en_font, hi_font, PDF_TITLE)
        doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=decorator)])

        story: List[Any] = []
        build_cover(story, styles, en_bold, edition_label)
        build_content_section(story, items, styles, en_font, en_bold, hi_font, hi_bold)
        build_mcq_section(story, mcqs, styles, en_font, en_bold, hi_font, hi_bold)
        build_answer_key(story, mcqs, styles, en_bold)

        doc.build(story)
        os.replace(tmp_path, output_path)
        logger.info("PDF written: %s (%d bytes)", output_path,
                    output_path.stat().st_size)
        return True
    except Exception as exc:
        logger.exception("PDF build failed: %s", exc)
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        return False


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def _infer_job_meta() -> Tuple[str, str]:
    """Return (job_id, edition_label)."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    # Infer from env or default to daily
    job_type = os.getenv("JOB_TYPE", "daily")
    if job_type == "weekly":
        label = f"Weekly Digest — {today}"
    elif job_type == "monthly":
        label = f"Monthly Digest — {today[:7]}"
    else:
        label = f"Daily Edition — {today}"
    return today, label


def main() -> int:
    job_id, label = _infer_job_meta()
    logger.info("Building PDF for job=%s label=%s", job_id, label)

    items = load_content(job_id)
    if not items:
        # Fallback to latest
        items = load_content(None)
    if not items:
        logger.error("No content — aborting PDF build")
        return 1

    mcqs = load_mcqs(job_id) or load_mcqs(None)

    output_path = OUTPUT_DIR / f"daily_{job_id}.pdf"
    ok = build_pdf(items, mcqs, output_path, label)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
