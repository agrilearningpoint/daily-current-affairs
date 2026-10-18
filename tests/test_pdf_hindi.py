import sys
import pytest

def has_shaping_backend() -> bool:
    try:
        import uharfbuzz, freetype  # type: ignore
        return True
    except ImportError:
        from PIL import features
        return bool(features.check("raqm"))


def test_raqm_guard():
    assert has_shaping_backend(), "Either uharfbuzz+freetype or Pillow RAQM required for Hindi shaping"


def test_mixed_para_hindi_shaping():
    """Regression test for mixed_para Devanagari shaping via HarfBuzz/FreeType or RAQM image path.
    Previously mixed_para used ReportLab direct TTF → ि-matra/reph misplace:
    मिलते → मलिते, विषय-सूची → वषिय-सूची, महत्वपूर्ण → महत्वपूरण.
    Now mixed_para routes Devanagari through hindi_to_image (HarfBuzz)."""
    import os, sys, re, tempfile, pathlib
    if not has_shaping_backend() and os.environ.get("ALP_ALLOW_UNSHAPED_DEV_PDF") != "1":
        pytest.skip(
            "Neither uharfbuzz+freetype nor Pillow RAQM available in this environment."
        )
    # Ensure repo root on path (tests/ -> ..)
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from src.generate_pdf import generate_pdf
    content = {
        "job": {"id":"test_hindi_regression","type":"daily","date":"2026-10-06","date_display":"06 October 2026"},
        "items": [{
            "event_id":"t1",
            "category":"Agriculture",
            "headline_en":">> Test",
            "headline_hi":">> टेस्ट",
            "key_points_en":["P1"], "key_points_hi":["मुख्य बिंदु टेस्ट"],
            "static_facts":{"K":"V"},
            "exam_fact_en":"E","exam_fact_hi":"परीक्षा तथ्य",
            "source":{"name":"PIB","url":"https://pib.gov.in"},
            "importance_score":80, "image_path":""
        }]
    }
    mcqs=[{"q_num":1,"question_en":"Q?","question_hi":"प्रश्न?","options":["A","B","C","D"],"correct":"A","explanation_en":"Exp","explanation_hi":"व्याख्या","exam_point":""}]
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "hindi_test.pdf")
        pdf = generate_pdf(content, mcqs, output_path=out)
        full = ""
        try:
            import pymupdf as fitz
            with fitz.open(pdf) as doc:
                full = "\n".join(p.get_text() for p in doc)
        except Exception:
            import pypdf
            reader = pypdf.PdfReader(pdf)
            full = "\n".join(p.extract_text() or "" for p in reader.pages)
        # Must contain correct forms via hidden text layer
        assert "विषय-सूची" in full, "INDEX Hindi broken: expected विषय-सूची"
        assert ("श्रेणीवार मुख्य तथ्य" in full or "महत्वपूर्ण" in full), "One-liners heading Hindi broken"
        assert "मुख्य बिंदु" in full, "Key Points Hindi broken"
        assert "स्थैतिक तथ्य" in full, "Static Facts Hindi broken"
        assert "परीक्षा तथ्य" in full, "Exam Fact Hindi broken"
        assert "बहुविकल्पीय" in full, "MCQ Hindi broken"
        assert "मिलते" in full, "Back cover मिलते broken"
        # Must NOT contain broken glyph orders
        assert "वषिय" not in full, "Broken glyph वषिय found (विषय→वषिय)"
        assert "मलिते" not in full, "Broken glyph मलिते found (मिलते→मलिते)"
        assert "महत्वपूरण" not in full, "Broken glyph महत्वपूरण found"
