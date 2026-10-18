"""Sample-PDF generation + real QA gate, driven by the synthetic fixture.

These tests exercise the *canonical* generator (src/generate_pdf.py) and the
*canonical* QA gate (agents/19_pdf_qa.py) on a deterministic bilingual fixture.
They assert:

* the PDF is generated at all;
* the real QA gate passes (no errors);
* Hindi is present and shaped (Mukta embedded, Devanagari in the text layer);
* no replacement/noto-def characters or font-unsupported symbols leak in;
* every selected story and every MCQ appears in the PDF.

Skipped only when no Devanagari shaping backend is available.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _shaping_available() -> bool:
    try:
        import freetype
        import uharfbuzz
        return True
    except ImportError:
        from PIL import features
        return bool(features.check("raqm"))


def _load_pdf_qa():
    spec = importlib.util.spec_from_file_location(
        "alp_pdf_qa_test", str(REPO_ROOT / "agents" / "19_pdf_qa.py")
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod  # dataclasses requires the module registered
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


pytestmark = pytest.mark.skipif(
    not _shaping_available(),
    reason="No Devanagari shaping backend (uharfbuzz+freetype or Pillow RAQM).",
)


@pytest.fixture(scope="module")
def sample_pdf(tmp_path_factory):
    from src.generate_pdf import generate_pdf
    from tests.fixtures.bilingual_sample import build_sample_content, build_sample_mcqs

    content = build_sample_content()
    mcqs = build_sample_mcqs()
    out = tmp_path_factory.mktemp("sample_pdf") / "sample.pdf"
    path = generate_pdf(content, mcqs, output_path=str(out))
    return Path(path), content, mcqs


def test_sample_pdf_passes_real_qa_gate(sample_pdf):
    pdf_path, content, mcqs = sample_pdf
    qa = _load_pdf_qa()
    report = qa.run_qa(pdf_path, min_mcq_count=len(mcqs),
                       item_count=len(content["items"]), selected_items=content["items"])
    errors = [i for i in report.issues if i.severity == "error"]
    assert report.passed, f"QA failed: {[ (i.code, i.message) for i in errors ]}"
    assert report.page_count >= 3
    assert report.hindi_pct >= 5.0
    assert report.mcq_count >= len(mcqs)
    assert not report.blank_pages
    assert not report.stories_missing


def test_sample_pdf_meets_daily_page_and_qa_targets(sample_pdf):
    """The deterministic sample must clear the 15-page daily target with a clean gate."""
    pdf_path, content, mcqs = sample_pdf
    qa = _load_pdf_qa()
    report = qa.run_qa(pdf_path, min_mcq_count=len(mcqs),
                       item_count=len(content["items"]), selected_items=content["items"])
    errors = [i for i in report.issues if i.severity == "error"]
    assert report.passed, f"QA failed: {[ (i.code, i.message) for i in errors ]}"
    assert report.substantive_pages >= 15, (
        f"Only {report.substantive_pages} substantive pages (target 15)"
    )
    assert not report.blank_pages
    assert not report.near_empty_pages
    assert not report.stories_missing


def test_sample_pdf_contains_all_stories_and_mcqs(sample_pdf):
    pdf_path, content, mcqs = sample_pdf
    import pymupdf

    with pymupdf.open(pdf_path) as doc:
        text = "\n".join(page.get_text() for page in doc)
    flat = " ".join(text.split())
    for item in content["items"]:
        # Each English headline (trimmed to a stable fragment) must appear.
        fragment = " ".join(item["headline_en"].split())[:45]
        assert fragment in flat, f"story missing from PDF: {fragment!r}"
    for m in mcqs:
        assert f"Q{m['q_num']}." in flat, f"MCQ {m['q_num']} missing"


def test_sample_pdf_has_no_broken_glyphs(sample_pdf):
    pdf_path, _content, _mcqs = sample_pdf
    import pymupdf

    with pymupdf.open(pdf_path) as doc:
        text = "\n".join(page.get_text() for page in doc)
    assert "\ufffd" not in text, "replacement character in PDF text"
    for bad in ("\u25b6", "\u2714", "\u258c", "\u2192", "\u2713", "\u2605"):
        assert bad not in text, f"font-unsupported symbol leaked into PDF: {bad!r}"


def test_bundled_fonts_do_not_cover_decorative_symbols_so_guard_is_required():
    """Documents *why* the glyph guard exists: these symbols are NOT in the fonts.

    If a future font upgrade adds them, the guard simply becomes a no-op; this
    test then fails and can be updated deliberately.
    """
    from src.generate_pdf import glyph_supported

    for ch in ("\u25b6", "\u2714", "\u258c", "\u2192"):
        assert glyph_supported(ch) is False, (
            f"Unexpected: {ch!r} now supported by bundled fonts — update "
            f"_SYMBOL_FALLBACK and this test."
        )
    # Symbols that MUST remain untouched.
    for ch in ("\u2022", "\u00bb", "\u20b9", "\u2013", "\u2014"):
        assert glyph_supported(ch) is True


def test_sanitize_glyphs_maps_unsupported_and_preserves_supported():
    from src.generate_pdf import sanitize_glyphs

    assert sanitize_glyphs("▶ Exam • परीक्षा तथ्य") == "» Exam • परीक्षा तथ्य"
    assert sanitize_glyphs("✔ done") == "· done"
    assert sanitize_glyphs("₹1,250 — 60:40") == "₹1,250 — 60:40"
    assert sanitize_glyphs("मुख्य बिंदु") == "मुख्य बिंदु"
