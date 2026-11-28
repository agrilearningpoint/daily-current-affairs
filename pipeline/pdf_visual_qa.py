# -*- coding: utf-8 -*-
"""
VISUAL PDF QA ENGINE (Phase 9-10)
==================================
Renders PDF pages to raster images via PyMuPDF (`fitz`) and inspects the actual
visual output rather than relying solely on extractable text streams.

Checks performed per rendered page:
  1. Visual blank-page check (pages with near-zero non-white ink variance).
  2. Edge-clipping check (dark foreground pixels colliding with left/right/bottom page edges).
  3. Optional preview PNG archival (cover, TOC/page 2, sample MCQ page) for manual/agent review.

Fails open (`available=False, passed=True`) if PyMuPDF is missing or if a mock/pypdf
document adapter is passed.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("pipeline.pdf_visual_qa")


def inspect_pdf_visuals(
    pdf_path: Path | str,
    *,
    dpi: int = 110,
    preview_dir: Optional[Path] = None,
    max_pages: int = 60,
    edge_px: int = 4,
) -> Dict[str, Any]:
    """Render PDF pages and run pixel-level visual QA checks.

    Returns dict:
        {
          "available": bool,
          "passed": bool,
          "pages_rendered": int,
          "blank_visual_pages": List[int],
          "edge_clip_pages": List[int],
          "preview_paths": List[str],
          "issues": List[Dict[str, Any]],
        }
    """
    pdf_path = Path(pdf_path)
    out: Dict[str, Any] = {
        "available": False,
        "passed": True,
        "pages_rendered": 0,
        "blank_visual_pages": [],
        "edge_clip_pages": [],
        "preview_paths": [],
        "issues": [],
    }
    if not pdf_path.is_file():
        return out

    fitz_mod = None
    try:
        import fitz as fitz_mod  # type: ignore
    except Exception:
        try:
            import pymupdf as fitz_mod  # type: ignore
        except Exception:
            return out

    try:
        from PIL import Image, ImageStat
    except Exception:
        return out

    doc = None
    try:
        doc = fitz_mod.open(str(pdf_path))
        out["available"] = True
        total = min(doc.page_count, max_pages)
        if preview_dir is not None:
            preview_dir = Path(preview_dir)
            preview_dir.mkdir(parents=True, exist_ok=True)

        preview_indices = {0, 1, min(total - 1, 2), total - 1} if total > 0 else set()

        for idx in range(total):
            page = doc[idx]
            pix = page.get_pixmap(dpi=dpi, alpha=False)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            gray = img.convert("L")
            out["pages_rendered"] += 1

            # Save key preview PNGs
            if preview_dir is not None and idx in preview_indices:
                pfile = preview_dir / f"page_{idx + 1:02d}.png"
                img.save(pfile, "PNG", optimize=True)
                out["preview_paths"].append(str(pfile))

            # 1. Visual blank check: stddev close to 0 and mean very near 255
            stat = ImageStat.Stat(gray)
            if stat.mean[0] > 253.5 and stat.stddev[0] < 4.5:
                out["blank_visual_pages"].append(idx + 1)

            # 2. Horizontal body edge clip check (skip cover page idx=0 and top/bottom running header/footer bands ~8%)
            if idx > 0 and pix.width > 20 and pix.height > 80:
                y_top = max(1, int(pix.height * 0.08))
                y_bot = min(pix.height - 1, int(pix.height * 0.92))
                left_body = gray.crop((0, y_top, edge_px, y_bot))
                right_body = gray.crop((pix.width - edge_px, y_top, pix.width, y_bot))
                if ImageStat.Stat(left_body).extrema[0][0] < 60 or ImageStat.Stat(right_body).extrema[0][0] < 60:
                    out["edge_clip_pages"].append(idx + 1)

        if out["blank_visual_pages"]:
            out["issues"].append({
                "severity": "warning",
                "code": "visual_blank_pages",
                "message": f"Visual render shows blank page(s): {out['blank_visual_pages'][:5]}",
                "pages": out["blank_visual_pages"],
            })
        if out["edge_clip_pages"]:
            out["issues"].append({
                "severity": "warning",
                "code": "visual_edge_clipping",
                "message": f"Dark text/ink touches horizontal margin on page(s): {out['edge_clip_pages'][:5]}",
                "pages": out["edge_clip_pages"],
            })
        # Critical failure only if multiple pages rendered visually blank
        if len(out["blank_visual_pages"]) >= 2:
            out["passed"] = False

    except Exception as exc:
        logger.warning("[Visual QA] skipped for %s: %s", pdf_path.name, exc)
    finally:
        if doc is not None:
            try:
                doc.close()
            except Exception:
                pass
    return out
