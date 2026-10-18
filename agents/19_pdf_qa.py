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
  PDF_QA_MIN_PAGES       (default 2)
  PDF_QA_MAX_PAGES       (default 200)
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

MIN_PAGES = int(os.getenv("PDF_QA_MIN_PAGES", "2"))
MAX_PAGES = int(os.getenv("PDF_QA_MAX_PAGES", "200"))
MIN_HINDI_PCT = float(os.getenv("PDF_QA_MIN_HINDI_PCT", "5.0"))
MIN_MCQ_COUNT = int(os.getenv("PDF_QA_MIN_MCQ_COUNT", "10"))
STRICT = os.getenv("PDF_QA_STRICT", "0") == "1"
RENDER_CHECK = os.getenv("PDF_QA_RENDER_CHECK", "1") == "1"

DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
URL_RE = re.compile(r"https?://[^\s\)\]\"']+")
MCQ_Q_RE = re.compile(
    r"(?:प्रश्न|Q(?:uestion)?)\s*[\.\:\-–]?\s*(\d+)",
    re.IGNORECASE,
)
ANSWER_RE = re.compile(
    r"(?:उत्तर|Answer|Correct\s*Answer|Ans)\s*[\.\:\-–]?\s*[\(\[]?([A-E])[\)\]]?",
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
        report.add("warning", "too_many_pages",
                   f"PDF has {report.page_count} pages (max {MAX_PAGES})",
                   pages=report.page_count)

    blanks = detect_blank_pages(doc)
    report.blank_pages = blanks
    if blanks:
        report.add("warning", "blank_pages",
                   f"{len(blanks)} suspicious blank page(s): {blanks[:5]}",
                   blank_pages=blanks)


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


def check_html_leakage(report: QAReport, text: str) -> None:
    """Detect raw HTML tags leaking into the PDF text layer."""
    leaks = HTML_TAG_RE.findall(text)
    if leaks:
        report.add("error", "html_leakage",
                   f"Raw HTML markup leaked into PDF text layer: {leaks[:5]}",
                   samples=leaks[:5])


def check_urls(report: QAReport, text: str) -> None:
    urls = URL_RE.findall(text)
    report.urls_found = len(urls)
    if len(urls) < 3:
        report.add("warning", "few_source_urls",
                   f"Only {len(urls)} source URLs found — attribution may be missing",
                   count=len(urls))


def check_images(report: QAReport, doc: "fitz.Document") -> None:
    count = count_images(doc)
    report.image_xobjects = count
    if count == 0:
        report.add("warning", "no_images",
                   "No embedded images found — logo/watermark may be missing")


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
def run_qa(pdf_path: Path, min_mcq_count: int = MIN_MCQ_COUNT) -> QAReport:
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
        check_glyph_integrity(report, text)
        check_html_leakage(report, text)
        check_mcqs(report, text, min_mcq_count)
        check_urls(report, text)
        check_visual_overflow(report, doc)
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

    min_mcq_count = minimum_mcq_count(len(selected_items))
    logger.info("QA requires at least %d MCQs for %d selected stories",
                min_mcq_count, len(selected_items))
    report = run_qa(pdf, min_mcq_count=min_mcq_count)

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
