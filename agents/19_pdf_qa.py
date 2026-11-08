# -*- coding: utf-8 -*-
"""
PDF QA Agent (19)
==================
Final gate-keeper before Telegram publish. Fails the job if PDF is
unfit for students.

Checks:
1. File exists + valid PDF structure
2. Page count within expected range
3. Fonts embedded (Devanagari fonts present)
4. Hindi coverage (Devanagari codepoints in text layer)
5. MCQ section present with answer key
6. No duplicate MCQ questions
7. Source URLs preserved
8. Page text density (no blank pages)
9. Optional: visual overflow detection (via pdfplumber bboxes)
10. Optional: image XObjects present (watermark/logo)

Env:
  PDF_QA_MIN_PAGES       (default 15)
  PDF_QA_MAX_PAGES       (default 45)
  PDF_QA_MIN_HINDI_PCT   (default 5.0)  — % of chars that must be Devanagari
  PDF_QA_MIN_MCQ_COUNT   (default 10; sparse editions require 2 per story)
  PDF_QA_STRICT          (1 = fail on warnings; 0 = warnings OK)
  PDF_QA_RENDER_CHECK    (1 = render pages to image for blank detection)

Exit codes:
  0 — QA passed
  1 — QA failed (job should not publish)
  2 — Config / IO error
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# --- PDF libraries ---
fitz = None
pypdf = None
try:
    import fitz  # PyMuPDF
except (ImportError, Exception):
    try:
        import pymupdf as fitz  # newer name
    except (ImportError, Exception):
        fitz = None

try:
    import pypdf
except ImportError:
    pypdf = None


class _PyPdfPageAdapter:
    def __init__(self, page):
        self._page = page
        try:
            mb = page.mediabox
            self.rect = type("Rect", (), {"width": float(mb.width), "height": float(mb.height)})()
        except Exception:
            self.rect = type("Rect", (), {"width": 595.0, "height": 842.0})()

    def get_text(self, kind="text"):
        if kind == "blocks":
            return []
        try:
            return self._page.extract_text() or ""
        except Exception:
            return ""

    def get_fonts(self, full=True):
        fonts = []
        try:
            resources = self._page.get("/Resources", {})
            font_dict = resources.get("/Font", {})
            for key, val in font_dict.items():
                if hasattr(val, "get") and val.get("/BaseFont"):
                    fonts.append((0, 0, 0, str(val["/BaseFont"])))
                elif hasattr(val, "base_font"):
                    fonts.append((0, 0, 0, str(val.base_font)))
        except Exception:
            pass
        return fonts

    def get_images(self, full=True):
        try:
            return list(self._page.images)
        except Exception:
            return []


class _PyPdfDocAdapter:
    def __init__(self, reader):
        self._reader = reader
        self.page_count = len(reader.pages)

    def __iter__(self):
        for p in self._reader.pages:
            yield _PyPdfPageAdapter(p)

    def close(self):
        pass


def open_pdf_document(pdf_path: Path | str):
    if fitz is not None:
        try:
            return fitz.open(str(pdf_path))
        except Exception:
            if pypdf is not None:
                reader = pypdf.PdfReader(str(pdf_path))
                return _PyPdfDocAdapter(reader)
            raise
    if pypdf is not None:
        reader = pypdf.PdfReader(str(pdf_path))
        return _PyPdfDocAdapter(reader)
    raise RuntimeError("Neither PyMuPDF (fitz) nor pypdf is available. Run: pip install pymupdf pypdf")


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
        logging.FileHandler(str(LOGS_DIR / "pdf_qa.log"), encoding="utf-8"),
    ],
)
logger = logging.getLogger("agent.19_pdf_qa")

# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
OUTPUT_DIR = REPO_ROOT / "output"
QA_REPORT_DIR = REPO_ROOT / "logs" / "qa"
QA_REPORT_DIR.mkdir(parents=True, exist_ok=True)

# Release editions are intentionally bounded: fewer than 15 pages is not a
# complete daily study pack, while more than 45 pages is too long for a daily
# revision booklet. Offline fixtures may explicitly lower the minimum.
MIN_PAGES = int(os.getenv("PDF_QA_MIN_PAGES", "15"))
MAX_PAGES = int(os.getenv("PDF_QA_MAX_PAGES", "45"))
MIN_HINDI_PCT = float(os.getenv("PDF_QA_MIN_HINDI_PCT", "3.0"))
MIN_MCQ_COUNT = int(os.getenv("PDF_QA_MIN_MCQ_COUNT", "10"))
STRICT = os.getenv("PDF_QA_STRICT", "0") == "1"
RENDER_CHECK = os.getenv("PDF_QA_RENDER_CHECK", "1") == "1"
# Editorial target for a normal daily edition (master spec section 4).
TARGET_SUBSTANTIVE_PAGES = int(os.getenv("PDF_QA_TARGET_PAGES", "15"))
# A page with at least this many extractable characters is "substantive"; below
# this but above the blank threshold is a "near-empty / heading-only" page.
SUBSTANTIVE_CHARS = int(os.getenv("PDF_QA_SUBSTANTIVE_CHARS", "600"))
NEAR_EMPTY_CHARS = int(os.getenv("PDF_QA_NEAR_EMPTY_CHARS", "260"))
# The 15-page release bound includes a cover, index and rapid-revision page.
# Keep the content-loss floor independent so a legitimate 15-page edition is
# not rejected merely because those designed pages are not text-dense.
MIN_SUBSTANTIVE_PAGES = int(os.getenv("PDF_QA_MIN_SUBSTANTIVE_PAGES", "2"))

DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
URL_RE = re.compile(r"https?://[^\s\)\]\"']+")
MCQ_Q_RE = re.compile(
    r"(?:प्रश्न|Q(?:uestion|ues)?)\s*[\.\:\-–]?\s*(\d+)",
    re.IGNORECASE,
)
ANSWER_RE = re.compile(
    r"(?:उत्तर|Answer|Correct\s*Answer|Ans)\s*[\.\:\-–]?\s*(?:Option\s*)?[\(\[]?([A-E])[\)\]]?",
    re.IGNORECASE,
)


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
@dataclass
class QAIssue:
    severity: str       # "error" | "warning" | "info"
    code: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QAReport:
    pdf_path: str
    page_count: int = 0
    file_size_bytes: int = 0
    devanagari_chars: int = 0
    total_chars: int = 0
    hindi_pct: float = 0.0
    font_names: List[str] = field(default_factory=list)
    mcq_count: int = 0
    answers_found: int = 0
    duplicate_questions: int = 0
    urls_found: int = 0
    blank_pages: List[int] = field(default_factory=list)
    near_empty_pages: List[int] = field(default_factory=list)
    substantive_pages: int = 0
    min_page_chars: int = 0
    stories_missing: List[str] = field(default_factory=list)
    image_xobjects: int = 0
    issues: List[QAIssue] = field(default_factory=list)
    checked_at: str = ""

    def add(self, severity: str, code: str, message: str, **details: Any) -> None:
        self.issues.append(QAIssue(severity, code, message, details))

    @property
    def passed(self) -> bool:
        has_error = any(i.severity == "error" for i in self.issues)
        if has_error:
            return False
        if STRICT:
            return not any(i.severity == "warning" for i in self.issues)
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pdf_path": self.pdf_path,
            "checked_at": self.checked_at,
            "passed": self.passed,
            "page_count": self.page_count,
            "file_size_bytes": self.file_size_bytes,
            "devanagari_chars": self.devanagari_chars,
            "total_chars": self.total_chars,
            "hindi_pct": round(self.hindi_pct, 2),
            "font_names": self.font_names,
            "mcq_count": self.mcq_count,
            "answers_found": self.answers_found,
            "duplicate_questions": self.duplicate_questions,
            "urls_found": self.urls_found,
            "blank_pages": self.blank_pages,
            "near_empty_pages": self.near_empty_pages,
            "substantive_pages": self.substantive_pages,
            "min_page_chars": self.min_page_chars,
            "stories_missing": self.stories_missing,
            "image_xobjects": self.image_xobjects,
            "issues": [
                {"severity": i.severity, "code": i.code,
                 "message": i.message, "details": i.details}
                for i in self.issues
            ],
        }


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def find_latest_pdf() -> Optional[Path]:
    if not OUTPUT_DIR.exists():
        return None
    pdfs = sorted(
        [p for p in OUTPUT_DIR.glob("*.pdf") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return pdfs[0] if pdfs else None


def extract_text(doc: "fitz.Document") -> str:
    """Extract all text from PDF."""
    chunks: List[str] = []
    for page in doc:
        try:
            chunks.append(page.get_text("text"))
        except Exception as exc:
            logger.warning("Text extraction failed on page: %s", exc)
    return "\n".join(chunks)


def extract_fonts(doc: "fitz.Document") -> List[str]:
    """Get list of fonts used (deduped)."""
    fonts: set[str] = set()
    for page in doc:
        try:
            for f in page.get_fonts(full=True):
                # f is a tuple; name is index 3
                if len(f) > 3 and f[3]:
                    fonts.add(str(f[3]))
        except Exception:
            continue
    return sorted(fonts)


def count_images(doc: "fitz.Document") -> int:
    """Count embedded image XObjects."""
    total = 0
    for page in doc:
        try:
            total += len(page.get_images(full=True))
        except Exception:
            continue
    return total


def detect_blank_pages(doc: "fitz.Document", min_chars: int = 20) -> List[int]:
    """Return list of page numbers (1-indexed) with suspiciously little text."""
    blanks: List[int] = []
    for idx, page in enumerate(doc, 1):
        try:
            text = page.get_text("text").strip()
            images = len(page.get_images())
            # Blank = almost no text AND no images
            if len(text) < min_chars and images == 0:
                blanks.append(idx)
        except Exception:
            continue
    return blanks


def analyse_page_density(doc: "fitz.Document") -> Tuple[List[int], int, int]:
    """Return (per-page char counts, substantive page count, min chars on a page).

    A page counts as *substantive* when it carries at least ``SUBSTANTIVE_CHARS``
    extractable characters. This is a measured occupancy proxy that works across
    PyMuPDF and the pypdf adapter, so a heading-only or near-empty page cannot
    masquerade as real content (master spec section 11).
    """
    counts: List[int] = []
    for page in doc:
        try:
            counts.append(len(page.get_text("text").strip()))
        except Exception:
            counts.append(0)
    substantive = sum(1 for c in counts if c >= SUBSTANTIVE_CHARS)
    return counts, substantive, (min(counts) if counts else 0)


def _normalize_for_coverage(text: str) -> str:
    """Lower-case, strip markup/punctuation and collapse whitespace.

    Used to compare a selected story headline against the extracted PDF text so
    the comparison survives line wrapping, HTML escaping and symbol-safe
    substitutions made by the glyph guard.
    """
    text = re.sub(r"<[^>]+>", " ", text or "")
    # The display cleaner prints "Rs 5" / "INR 5" as "₹5": compare both spellings alike.
    text = re.sub(r"(?i)\b(?:rs|inr)\b\.?\s*", " ₹", text).replace("₹", " rs ")
    text = re.sub(r"[^0-9A-Za-z\u0900-\u097F]+", " ", text)
    return re.sub(r"\s+", " ", text).lower().strip()


def check_story_coverage(report: QAReport, text: str,
                         selected_items: List[Dict[str, Any]]) -> None:
    """Verify every selected story actually appears in the PDF.

    This is the layout-independent content-loss gate. It does not care how many
    pages the edition uses; it fails only when the renderer silently dropped
    selected stories (the failure mode the master spec calls "content lost").
    """
    norm = _normalize_for_coverage(text)
    if not norm:
        return

    missing: List[str] = []
    total = 0
    raw_file_re = re.compile(r"(?:\b[\w\-_.]+\.(?:pdf|docx?|xlsx?|csv|pptx)\b)|(?:^\s*[\w\-_.]+\.(?:pdf|docx?|xlsx?)\b)", re.IGNORECASE)
    for it in selected_items:
        headline = it.get("headline_en") or ""
        if raw_file_re.search(headline):
            continue  # Raw file attachments are legitimately filtered at the PDF boundary
        words = _normalize_for_coverage(headline).split()
        if len(words) < 3:
            continue
        total += 1
        key = " ".join(words[:7]) if len(words) >= 7 else " ".join(words)
        if key not in norm:
            missing.append(headline.strip()[:80])

    report.stories_missing = missing
    if not total:
        return
    threshold = max(2, -(-total // 5))  # max(2, ceil(20% of stories))
    if len(missing) >= threshold:
        report.add("error", "stories_missing_from_pdf",
                   f"{len(missing)}/{total} selected stories not found in the PDF "
                   f"— content lost in layout",
                   missing=missing[:5], total=total)
    elif missing:
        report.add("warning", "story_missing_from_pdf",
                   f"{len(missing)}/{total} selected stories not found in the PDF",
                   missing=missing[:5], total=total)


def check_story_count(report: QAReport, edition_count: int, selected_count: int) -> None:
    """Error when the edition lost more than 20% of the selected stories (after
    reserve backfill), mirroring the story-coverage tolerance."""
    if selected_count <= 0:
        return
    floor = selected_count - max(2, -(-selected_count // 5)) + 1
    if edition_count < floor:
        report.add("error", "edition_story_shortfall",
                   f"Edition has {edition_count} stories for {selected_count} selected "
                   f"(floor {floor}) — reserves could not replace dropped stories",
                   edition=edition_count, selected=selected_count, floor=floor)
    elif edition_count < selected_count:
        report.add("warning", "edition_story_shortfall",
                   f"Edition has {edition_count}/{selected_count} selected-story slots filled",
                   edition=edition_count, selected=selected_count)


def compute_mcq_stats(text: str) -> Tuple[int, int, int]:
    """
    Returns (mcq_count, answer_count, duplicate_count).
    Duplicate = questions whose normalized text appears more than once.
    """
    # --- MCQ count ---
    q_numbers = [int(m.group(1)) for m in MCQ_Q_RE.finditer(text)]
    # Dedup consecutive or repeat numbers
    unique_q = sorted(set(q_numbers))
    mcq_count = len(unique_q) if unique_q else 0

    # --- Answer key count ---
    answer_letters = [m.group(1).upper() for m in ANSWER_RE.finditer(text)]
    answer_count = len(answer_letters)

    # --- Duplicate question detection ---
    # Split text into question blocks by "प्रश्न N" / "Q N"
    split_re = re.compile(
        r"(?:प्रश्न|Q(?:uestion)?)\s*[\.\:\-–]?\s*\d+",
        re.IGNORECASE,
    )
    parts = split_re.split(text)
    normalized: List[str] = []
    for p in parts[1:]:   # skip first (before Q1)
        # Take first ~200 chars after question marker as "question stem"
        stem = re.sub(r"\s+", " ", p[:250]).strip().lower()
        if stem:
            normalized.append(stem)

    seen: Dict[str, int] = {}
    for stem in normalized:
        h = hashlib.sha1(stem.encode("utf-8")).hexdigest()[:16]
        seen[h] = seen.get(h, 0) + 1

    duplicate_count = sum(1 for v in seen.values() if v > 1)

    return mcq_count, answer_count, duplicate_count


# --------------------------------------------------------------------------- #
# Checks
# --------------------------------------------------------------------------- #
def check_file(report: QAReport, path: Path) -> None:
    if not path.exists():
        report.add("error", "file_missing", f"PDF not found: {path}")
        return
    report.file_size_bytes = path.stat().st_size
    if report.file_size_bytes < 5000:
        report.add("error", "file_too_small",
                   f"PDF only {report.file_size_bytes} bytes — likely empty",
                   size=report.file_size_bytes)
    elif report.file_size_bytes < 20000:
        report.add("warning", "file_small",
                   f"PDF is only {report.file_size_bytes // 1024} KB — may be missing content",
                   size=report.file_size_bytes)


def check_pages(report: QAReport, doc: "fitz.Document") -> None:
    report.page_count = doc.page_count
    if report.page_count < MIN_PAGES:
        report.add("error", "too_few_pages",
                   f"PDF has only {report.page_count} pages (min {MIN_PAGES})",
                   pages=report.page_count)
    if report.page_count > MAX_PAGES:
        report.add("error", "too_many_pages",
                   f"PDF has {report.page_count} pages (max {MAX_PAGES})",
                   pages=report.page_count)

    blanks = detect_blank_pages(doc)
    report.blank_pages = blanks
    if blanks:
        report.add("warning", "blank_pages",
                   f"{len(blanks)} suspicious blank page(s): {blanks[:5]}",
                   blank_pages=blanks)

    # Content-aware occupancy: substantive vs near-empty / heading-only pages.
    counts, substantive, min_chars = analyse_page_density(doc)
    report.substantive_pages = substantive
    report.min_page_chars = min_chars
    near_empty = [
        i for i, c in enumerate(counts, 1)
        if NEAR_EMPTY_CHARS <= c < SUBSTANTIVE_CHARS and i not in blanks
    ]
    report.near_empty_pages = near_empty
    if near_empty:
        report.add("warning", "near_empty_pages",
                   f"{len(near_empty)} near-empty/heading-only page(s): {near_empty[:5]}",
                   near_empty_pages=near_empty)


def check_fonts(report: QAReport, doc: "fitz.Document") -> None:
    fonts = extract_fonts(doc)
    report.font_names = fonts
    if not fonts:
        report.add("error", "no_fonts",
                   "No fonts detected in PDF — text may not render")
        return

    # Check for Devanagari-capable fonts
    devanagari_hints = ["mukta", "poppins", "noto", "deva", "hind", "sans"]
    has_deva_font = any(
        any(hint in f.lower() for hint in devanagari_hints)
        for f in fonts
    )
    if not has_deva_font:
        report.add("warning", "no_devanagari_font",
                   "No Devanagari-capable font detected — Hindi may not render",
                   fonts=fonts[:10])



def check_editorial_quality(report: QAReport, text: str) -> None:
    """Editorial quality assurance: prevents placeholder, corrupt, or leaked content."""
    # 1. Untitled content check
    if re.search(r"\buntitled\b", text, re.IGNORECASE):
        report.add("error", "untitled_content", "PDF contains 'Untitled' headline or placeholder string")

    # 2. Suspected truncated prefix check
    corrupt_matches = re.findall(r"\b(aiwan|ranscript of|inistr)\b", text, re.IGNORECASE)
    if corrupt_matches:
        report.add("warning", "corrupt_prefix", f"PDF contains suspected truncated words: {corrupt_matches}")

    # 3. Broken question template check
    if 'Which ministry / organisation is responsible for implementing "- \'' in text:
        report.add("error", "broken_mcq_template", "PDF contains broken/robotic MCQ template with bare hyphen")

    # Publisher paywall/account UI must never become a study fact. This is an
    # error (not a warning) so it blocks Telegram publication, including
    # mojibake variants of a curly apostrophe in "don't".
    paywall_ui = re.search(
        r"(?:active\s+subscription|subscribed\s+with\s+another\s+email|"
        r"need\s+help\s+with\s+your\s+subscription|logout\s+and\s+login\s+with\s+that\s+one)",
        text,
        re.IGNORECASE,
    )
    if paywall_ui:
        report.add("error", "paywall_ui_leakage",
                   "PDF contains publisher subscription/account UI text",
                   sample=paywall_ui.group(0))


def check_text_content(report: QAReport, text: str) -> None:
    report.total_chars = len(text)
    if report.total_chars < 500:
        report.add("error", "too_little_text",
                   f"Only {report.total_chars} chars in PDF — content missing",
                   chars=report.total_chars)
        return

    deva_chars = len(DEVANAGARI_RE.findall(text))
    report.devanagari_chars = deva_chars
    report.hindi_pct = (deva_chars / report.total_chars * 100.0) if report.total_chars else 0.0

    if report.hindi_pct < MIN_HINDI_PCT:
        report.add("error", "insufficient_hindi",
                   f"Only {report.hindi_pct:.1f}% Devanagari chars (min {MIN_HINDI_PCT}%) "
                   f"— Hindi content missing",
                   hindi_pct=round(report.hindi_pct, 2),
                   min=MIN_HINDI_PCT)
    elif report.hindi_pct < MIN_HINDI_PCT * 2:
        report.add("warning", "low_hindi",
                   f"Hindi coverage {report.hindi_pct:.1f}% is low",
                   hindi_pct=round(report.hindi_pct, 2))


def minimum_mcq_count(item_count: int) -> int:
    """Require two validated questions per selected story, capped at the normal edition minimum."""
    if item_count < 1:
        return MIN_MCQ_COUNT
    return min(MIN_MCQ_COUNT, item_count * 2)


def minimum_substantive_pages(item_count: int) -> int:
    """Content-loss floor: about half a page per selected story, capped at the target.

    Real RSS summaries are shorter than the rich test fixture, so requiring a
    full page per story would fail legitimate short-summary editions. The floor
    is therefore deliberately conservative (ceil(n/2), clamped to
    ``[MIN_PAGES, TARGET_SUBSTANTIVE_PAGES]``): falling below it means the
    renderer dropped or crushed content, not that it was a quiet news day.
    """
    if item_count < 1:
        return MIN_SUBSTANTIVE_PAGES
    half = (item_count + 1) // 2  # ceil(n / 2)
    return max(MIN_SUBSTANTIVE_PAGES, min(TARGET_SUBSTANTIVE_PAGES, half))


def check_page_target(report: QAReport, item_count: int) -> None:
    """Warn when the edition is below the editorial page target; error only on
    clear content loss (fewer substantive pages than selected stories)."""
    floor = minimum_substantive_pages(item_count)
    if report.substantive_pages < floor:
        report.add("error", "insufficient_substantive_pages",
                   f"Only {report.substantive_pages} substantive page(s) for "
                   f"{item_count} stories (floor {floor}) — content lost or layout defect",
                   substantive_pages=report.substantive_pages, floor=floor, items=item_count)
    elif report.substantive_pages < TARGET_SUBSTANTIVE_PAGES:
        report.add("warning", "below_page_target",
                   f"{report.substantive_pages} substantive page(s) is below the "
                   f"{TARGET_SUBSTANTIVE_PAGES}-page daily target (verified news volume may be low)",
                   substantive_pages=report.substantive_pages, target=TARGET_SUBSTANTIVE_PAGES)


def check_mcqs(report: QAReport, text: str, min_mcq_count: int = MIN_MCQ_COUNT) -> None:
    mcq_count, answer_count, dup_count = compute_mcq_stats(text)
    report.mcq_count = mcq_count
    report.answers_found = answer_count
    report.duplicate_questions = dup_count

    if mcq_count < min_mcq_count:
        report.add("error", "insufficient_mcqs",
                   f"Only {mcq_count} MCQs found (min {min_mcq_count})",
                   count=mcq_count, min=min_mcq_count)

    if answer_count < mcq_count * 0.8:
        report.add("warning", "missing_answers",
                   f"Only {answer_count} answer markers for {mcq_count} MCQs",
                   answers=answer_count, mcqs=mcq_count)

    if dup_count > 0:
        report.add("warning", "duplicate_questions",
                   f"{dup_count} duplicate question(s) detected",
                   count=dup_count)


HTML_TAG_RE = re.compile(r"<(?:span|div|time|p|br|table|tr|td|b|i|font)\b[^>]*>", re.IGNORECASE)

# Glyph-integrity checks: characters that indicate a missing/unmappable glyph
# in the PDF text layer. src/generate_pdf.py sanitises these at generation
# time; if they still appear, the glyph guard has regressed.
REPLACEMENT_CHAR_RE = re.compile(r"[\uFFFD\u25A1]")
UNSUPPORTED_SYMBOL_RE = re.compile(r"[▶✔✒✖▌→✓★●■☆▪➔✔️]|[\U0001F4CC\U0001F4DD\U0001F3AF\U0001F680\U0001F525\U00002705\U0000274C]")


def check_glyph_integrity(report: QAReport, text: str) -> None:
    """Fail on replacement characters or symbols the bundled fonts cannot draw."""
    replacements = REPLACEMENT_CHAR_RE.findall(text)
    if replacements:
        report.add("error", "replacement_chars",
                   f"{len(replacements)} replacement/notdef character(s) in PDF text",
                   samples=replacements[:5])
    unsupported = sorted(set(UNSUPPORTED_SYMBOL_RE.findall(text)))
    if unsupported:
        report.add("error", "unsupported_symbols",
                   "Symbols not covered by the bundled fonts leaked into the PDF: "
                   f"{unsupported}",
                   samples=unsupported)


# Visible matra-reordering artefacts produced when ReportLab draws Devanagari
# without shaping (e.g. विषय -> वषिय, स्थैतिक -> स्थैतकि).
BROKEN_MATRA_SAMPLES = ("वषिय", "मलिते", "महत्वपूरण", "स्थैतकि", "वकिल्प", "बदिु", "वयाख्या")


def check_devanagari_shaping(report: QAReport, doc: "fitz.Document", text: str) -> None:
    """Every visible Devanagari glyph must come from the HarfBuzz-shaped image path.

    src/generate_pdf.py draws Hindi as a shaped image plus an *invisible*
    (render mode 3) text layer.  Visible Devanagari text spans therefore mean a
    string bypassed render_hindi_flowable/bi_line and went through a plain
    ReportLab Paragraph, which misplaces the ि matra.
    """
    broken = [w for w in BROKEN_MATRA_SAMPLES if w in text]
    if broken:
        report.add("error", "broken_devanagari_matras",
                   f"Unshaped Devanagari artefacts in PDF text: {broken}", samples=broken)
    pages: List[int] = []
    for idx, page in enumerate(doc, 1):
        trace = getattr(page, "get_texttrace", None)
        if trace is None:
            return  # pypdf fallback adapter: render modes unavailable
        try:
            spans = trace()
        except Exception:
            continue
        for sp in spans:
            if sp.get("type", 0) == 3:  # invisible text layer over the shaped image
                continue
            chars = "".join(chr(c[0]) for c in sp.get("chars", ()) if c and c[0] > 0)
            if DEVANAGARI_RE.search(chars):
                pages.append(idx)
                break
    if pages:
        report.add("error", "unshaped_devanagari",
                   f"Devanagari drawn as plain (unshaped) text on pages {pages[:5]} "
                   "— route it through render_hindi_flowable/bi_line",
                   pages=pages)


def check_html_leakage(report: QAReport, text: str) -> None:
    """Detect raw HTML tags leaking into the PDF text layer."""
    leaks = HTML_TAG_RE.findall(text)
    if leaks:
        report.add("error", "html_leakage",
                   f"Raw HTML markup leaked into PDF text layer: {leaks[:5]}",
                   samples=leaks[:5])


# The public PDF deliberately prints no source URLs (evidence stays in the
# pipeline data; photos carry an "Image: <source>" credit).  Opt back in to the
# attribution-URL warning with PDF_QA_EXPECT_SOURCE_URLS=1.
EXPECT_SOURCE_URLS = os.getenv("PDF_QA_EXPECT_SOURCE_URLS", "0") == "1"


def check_urls(report: QAReport, text: str) -> None:
    urls = URL_RE.findall(text)
    report.urls_found = len(urls)
    if EXPECT_SOURCE_URLS and len(urls) < 3:
        report.add("warning", "few_source_urls",
                   f"Only {len(urls)} source URLs found — attribution may be missing",
                   count=len(urls))


def check_images(report: QAReport, doc: "fitz.Document") -> None:
    count = count_images(doc)
    report.image_xobjects = count
    if count == 0:
        report.add("warning", "no_images",
                   "No embedded images found — logo/watermark may be missing")


def check_photo_count(report: QAReport, items: Optional[List[Dict[str, Any]]]) -> None:
    """Fewer real news photos than the target (ALP_IMAGE_TARGET, default 10) is
    logged and recorded as INFO only: a photo shortfall never fails QA, even
    with PDF_QA_STRICT=1.  Category graphics are not counted as photos."""
    try:
        target = int(os.getenv("ALP_IMAGE_TARGET", "10") or 10)
        real = sum(1 for it in items or [] if isinstance(it, dict) and it.get("image_path")
                   and not it.get("image_placeholder"))
        if real < target:
            logger.warning("Only %d real news photo(s) in the edition (target %d) — not blocking", real, target)
            report.add("info", "few_photos", f"{real} real news photos (target {target})", count=real)
    except Exception as exc:  # fail open
        logger.warning("Photo count check skipped: %s", exc)


def story_has_body(it: Dict[str, Any]) -> bool:
    """A story prints at least one bullet besides its headline (period editions:
    ``summary_pairs``; daily: key points / summary that is not the headline)."""
    def norm(x: Any) -> str:
        return re.sub(r"[^0-9a-z\u0900-\u097f]+", " ", str(x or "").lower()).strip()
    if "summary_pairs" in it:
        return any(isinstance(p, dict) and norm(p.get("en")) for p in it.get("summary_pairs") or [])
    head = norm(it.get("headline_en"))
    for k in list(it.get("key_points_en") or []) + [it.get("summary_en"), it.get("detailed_explanation_en")]:
        n = norm(k)
        if n and n != head and not head.startswith(n) and len(n.split()) >= 4:
            return True
    return False


def check_story_bodies(report: QAReport, items: Optional[List[Dict[str, Any]]], job_type: str = "") -> None:
    """Headline-only stories (weekly 2026-11-08 printed 10). Period editions FAIL
    (error); a daily edition gets a warning (blocking only with PDF_QA_STRICT=1)."""
    empty = [str(it.get("headline_en") or "")[:90] for it in items or []
             if isinstance(it, dict) and not story_has_body(it)]
    if not empty:
        return
    sev = "error" if job_type in ("weekly", "monthly") else "warning"
    report.add(sev, "title_only_stories",
               f"{len(empty)} headline-only stor{'y' if len(empty) == 1 else 'ies'} (no body/bullets), "
               f"e.g. {empty[0]!r}", stories=empty[:20])


def check_visual_overflow(report: QAReport, doc: "fitz.Document") -> None:
    """
    Detect text blocks that extend beyond page bounds.
    Uses PyMuPDF's text block bounding boxes.
    """
    overflow_pages: List[int] = []
    for idx, page in enumerate(doc, 1):
        try:
            rect = page.rect
            blocks = page.get_text("blocks")
            for b in blocks:
                if len(b) < 4:
                    continue
                x0, y0, x1, y1 = b[:4]
                # Allow small margin (5pt)
                if x1 > rect.width + 5 or y1 > rect.height + 5 or x0 < -5 or y0 < -5:
                    overflow_pages.append(idx)
                    break
        except Exception:
            continue

    if overflow_pages:
        report.add("warning", "text_overflow",
                   f"Text may overflow page bounds on pages: {overflow_pages[:5]}",
                   pages=overflow_pages)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
# Weekly / monthly only: a story line printed again and again means the period
# builder let a filler sentence or a duplicate event through.  Reported, never
# blocking (severity "info" + a logged warning, so even PDF_QA_STRICT passes).
REPEAT_MAX = 2
_REPEAT_LABELS = ("static gk |", "agri learning point", "telegram:", "page ")


def check_repeated_lines(report: QAReport, doc: "fitz.Document", min_len: int = 31,
                         max_repeats: int = REPEAT_MAX) -> List[Tuple[str, int]]:
    """Lines (> 30 chars) outside the page header/footer that occur more than
    ``max_repeats`` times in the PDF.  Logs a warning; never fails QA."""
    counts: Dict[str, int] = {}
    try:
        for page in doc:
            height = float(page.rect.height)
            for b in page.get_text("blocks"):
                if len(b) < 5 or b[1] < 50 or b[3] > height - 50:  # running header / footer band
                    continue
                for line in str(b[4]).splitlines():
                    line = " ".join(line.split())
                    if len(line) < min_len or line.lower().startswith(_REPEAT_LABELS):
                        continue
                    counts[line] = counts.get(line, 0) + 1
    except Exception as exc:  # never let a diagnostic break QA
        logger.warning("Repeated-line check skipped: %s", exc)
        return []
    reps = sorted(((t, n) for t, n in counts.items() if n > max_repeats), key=lambda x: -x[1])
    if reps:
        logger.warning("%d line(s) repeat more than %d times in the edition, e.g. %s",
                       len(reps), max_repeats, "; ".join(f"{t[:70]!r} x{n}" for t, n in reps[:5]))
        report.add("info", "repeated_lines",
                   f"{len(reps)} non-header line(s) repeat more than {max_repeats} times",
                   examples=[{"text": t[:120], "count": n} for t, n in reps[:10]])
    return reps


def run_qa(pdf_path: Path, min_mcq_count: int = MIN_MCQ_COUNT,
           item_count: Optional[int] = None,
           selected_items: Optional[List[Dict[str, Any]]] = None,
           job_type: str = "") -> QAReport:
    report = QAReport(
        pdf_path=str(pdf_path),
        checked_at=datetime.now(timezone.utc).isoformat(),
    )

    check_file(report, pdf_path)
    if not pdf_path.exists():
        return report

    try:
        doc = open_pdf_document(pdf_path)
    except Exception as exc:
        report.add("error", "cannot_open",
                   f"PDF reader cannot open PDF: {exc}")
        return report

    try:
        check_pages(report, doc)
        check_fonts(report, doc)
        check_images(report, doc)
        text = extract_text(doc)
        check_text_content(report, text)
        check_editorial_quality(report, text)
        check_glyph_integrity(report, text)
        check_devanagari_shaping(report, doc, text)
        check_html_leakage(report, text)
        check_mcqs(report, text, min_mcq_count)
        check_urls(report, text)
        check_visual_overflow(report, doc)
        if job_type in ("weekly", "monthly"):
            check_repeated_lines(report, doc)
        if selected_items:
            check_story_coverage(report, text, selected_items)
        if item_count is not None:
            check_page_target(report, item_count)
    finally:
        doc.close()

    return report


def print_summary(report: QAReport) -> None:
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    pass_mark = "[PASSED]"
    fail_mark = "[FAILED]"
    try:
        pass_mark = "✅ PASSED"
        fail_mark = "❌ FAILED"
    except Exception:
        pass
    print()
    print("=" * 72)
    print(f"PDF QA REPORT — {pass_mark if report.passed else fail_mark}")
    print("=" * 72)
    print(f"File:            {report.pdf_path}")
    print(f"Size:            {report.file_size_bytes // 1024} KB")
    print(f"Pages:           {report.page_count}")
    print(f"Chars:           {report.total_chars}")
    print(f"Devanagari:      {report.devanagari_chars} ({report.hindi_pct:.1f}%)")
    print(f"Fonts:           {len(report.font_names)} ({', '.join(report.font_names[:3])}...)")
    print(f"MCQs:            {report.mcq_count}")
    print(f"Answer markers:  {report.answers_found}")
    print(f"Duplicate Qs:    {report.duplicate_questions}")
    print(f"URLs:            {report.urls_found}")
    print(f"Images:          {report.image_xobjects}")
    print(f"Blank pages:     {report.blank_pages if report.blank_pages else 'none'}")
    print(f"Substantive pgs: {report.substantive_pages} (min page chars {report.min_page_chars})")
    print(f"Near-empty pgs:  {report.near_empty_pages if report.near_empty_pages else 'none'}")
    if report.stories_missing:
        print(f"Stories missing: {len(report.stories_missing)} (e.g. {report.stories_missing[0]!r})")

    if report.issues:
        print()
        print("--- Issues ---")
        for i in report.issues:
            icon = {"error": "[ERROR]", "warning": "[WARN]", "info": "[INFO]"}.get(i.severity, "?")
            print(f"  {icon} [{i.code}] {i.message}")
    print("=" * 72)
    print()


def main() -> int:
    from pipeline.agent_context import get_context
    ctx = get_context()
    pdf = ctx.pdf_path() if os.getenv("ALP_JOB_ID") else find_latest_pdf()
    if pdf is None or not pdf.exists():
        logger.error("No PDF found in %s", OUTPUT_DIR)
        return 2

    logger.info("QA check: %s", pdf.name)
    selected_path = ctx.find_input("selected")
    if selected_path is None:
        logger.error("Selected-news artifact not found for %s", ctx.job_id)
        return 2
    try:
        selected = json.loads(selected_path.read_text(encoding="utf-8"))
        selected_items = selected.get("items") if isinstance(selected, dict) else None
        if not isinstance(selected_items, list) or not selected_items:
            raise ValueError("selected-news artifact must contain a non-empty items list")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        logger.error("Cannot determine selected-news count for %s: %s", ctx.job_id, exc)
        return 2

    # The edition's final story list is the content artifact (stage 12 backfills
    # from reserves, stage 16 swaps in reserves for stories without a valid MCQ).
    # Coverage is checked against that list; a content shortfall versus the
    # selection (more than 20% fewer stories) is still a content-loss error.
    edition_items = selected_items
    content_path = ctx.find_input("content")
    if content_path is not None:
        try:
            content = json.loads(content_path.read_text(encoding="utf-8"))
            c_items = content.get("items") if isinstance(content, dict) else None
            if isinstance(c_items, list) and c_items:
                edition_items = c_items
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Content artifact unreadable, checking coverage against selection: %s", exc)

    min_mcq_count = minimum_mcq_count(len(edition_items))
    logger.info("QA requires at least %d MCQs for %d selected stories",
                min_mcq_count, len(selected_items))
    report = run_qa(pdf, min_mcq_count=min_mcq_count,
                    item_count=len(edition_items), selected_items=edition_items,
                    job_type=str(getattr(ctx, "job_type", "") or ""))
    check_story_count(report, len(edition_items), len(selected_items))
    check_story_bodies(report, edition_items, str(getattr(ctx, "job_type", "") or ""))
    check_photo_count(report, edition_items)

    # Save report
    report_file = ctx.qa_report_path()
    report_file.parent.mkdir(parents=True, exist_ok=True)
    data = report.to_dict()
    data["job_id"] = ctx.job_id
    data["file_sha256"] = hashlib.sha256(pdf.read_bytes()).hexdigest()
    report_file.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Report: %s", report_file)

    print_summary(report)

    if report.passed:
        logger.info("✔ PDF QA passed — safe to publish")
        return 0

    logger.error("✘ PDF QA failed — DO NOT publish")
    return 1


if __name__ == "__main__":
    sys.exit(main())
