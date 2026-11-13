# Premium Bilingual PDF Design & Typography Guidelines

1. **Branding & Header/Footer**: Uses official **AGRI LEARNING POINT | By Satyam Sir & Team** branding, top curved sky-blue exam banner (`IBPS AFO | NABARD | ICAR | UPSSSC AGTA | BANKING | SSC`), and bottom dark bar with clickable links for YouTube (`Agri Learning Point`), Telegram (`Agri Learning Point`), and Telegram Quiz (`Agri Quiz World`).
2. **Dual-Layer Devanagari Shaping**: All Hindi text is shaped via `_HindiTextFlowable` (`Mukta` / `Noto Sans Devanagari`) into optimized 8-bit PNGs paired with an invisible render-mode-3 UTF-8 text layer so `19_pdf_qa.py` verifies zero unshaped matras while preserving text search/copy.
3. **Pagination & Density**: Uses `CondPageBreak(160)` and wraps only `Question + 5 Options + Answer` in `KeepTogether`, allowing Bilingual Explanations, Static GK, and Recent News Headlines Blue Revision Boxes to flow without creating near-empty pages.
