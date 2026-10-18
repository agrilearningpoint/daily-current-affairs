"""PDF preview + QA tool for the canonical bilingual generator.

Generates the real production PDF from the synthetic fixture in
tests/fixtures/bilingual_sample.py, runs the real PDF QA gate
(agents/19_pdf_qa.run_qa) against it and renders representative pages to PNG
for visual inspection.

This tool never publishes anything and never calls Telegram.

Usage
-----
    python scripts/pdf_preview.py
    python scripts/pdf_preview.py --out output/sample_preview.pdf \
        --png-dir output/preview --dpi 110

Exit codes
----------
    0 — PDF generated and QA passed
    1 — PDF generated but QA failed (inspect the report / PNGs)
    2 — could not generate the PDF
"""
from __future__ import annotations

import argparse
import contextlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

for _stream in (sys.stdout, sys.stderr):
    if _stream and hasattr(_stream, "reconfigure"):
        with contextlib.suppress(Exception):
            _stream.reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default=str(REPO_ROOT / "output" / "sample_preview.pdf"))
    parser.add_argument("--png-dir", default=str(REPO_ROOT / "output" / "preview"))
    parser.add_argument("--dpi", type=int, default=110)
    parser.add_argument("--no-png", action="store_true", help="skip PNG rendering")
    args = parser.parse_args(argv)

    from tests.fixtures.bilingual_sample import build_sample_content, build_sample_mcqs

    content = build_sample_content()
    mcqs = build_sample_mcqs()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        from src.generate_pdf import generate_pdf
        pdf_path = generate_pdf(content, mcqs, output_path=str(out_path))
    except Exception as exc:  # generation failure is a blocking error
        print(f"[X] PDF generation failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    print(f"[OK] Generated PDF: {pdf_path}")

    # --- Real QA gate -------------------------------------------------------
    import importlib.util

    qa_spec = importlib.util.spec_from_file_location(
        "alp_pdf_qa", str(REPO_ROOT / "agents" / "19_pdf_qa.py")
    )
    qa_mod = importlib.util.module_from_spec(qa_spec)
    sys.modules[qa_spec.name] = qa_mod  # dataclasses needs the module registered
    qa_spec.loader.exec_module(qa_mod)  # type: ignore[union-attr]

    report = qa_mod.run_qa(Path(pdf_path), min_mcq_count=len(mcqs))
    qa_mod.print_summary(report)
    print(f"QA verdict: {'PASSED' if report.passed else 'FAILED'}")

    # --- PNG rendering for visual inspection --------------------------------
    if not args.no_png:
        png_dir = Path(args.png_dir)
        png_dir.mkdir(parents=True, exist_ok=True)
        try:
            import pymupdf

            doc = pymupdf.open(pdf_path)
            n = doc.page_count
            # Representative pages: cover, first story page, a middle page,
            # the MCQ start, and the final page.
            wanted = sorted({1, 2, 3, max(1, n // 2), max(1, n - 2), n})
            for pno in wanted:
                page = doc[pno - 1]
                pix = page.get_pixmap(dpi=args.dpi)
                dest = png_dir / f"page_{pno:02d}.png"
                pix.save(str(dest))
                print(f"[PNG] page {pno}/{n} -> {dest}")
            doc.close()
        except Exception as exc:
            print(f"[!] PNG rendering skipped: {type(exc).__name__}: {exc}", file=sys.stderr)

    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
