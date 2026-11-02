# -*- coding: utf-8 -*-
"""PDF v5: magazine cover, type-size contract, mobile-safe internal links,
auto sections rendering and the page-cap trimming order."""
import io
import random
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

fitz = pytest.importorskip("fitz")


def _shaping_available() -> bool:
    try:
        import freetype  # noqa: F401
        import uharfbuzz  # noqa: F401
        return True
    except ImportError:
        from PIL import features
        return bool(features.check("raqm"))


needs_shaping = pytest.mark.skipif(not _shaping_available(), reason="no Devanagari shaping backend")


def _photo(path: Path, seed: int, w=960, h=600):
    from PIL import Image
    rnd = random.Random(seed)
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(0, h, 8):
        for x in range(0, w, 8):
            c = (rnd.randrange(256), rnd.randrange(256), rnd.randrange(256))
            for dy in range(8):
                for dx in range(8):
                    if x + dx < w and y + dy < h:
                        px[x + dx, y + dy] = c
    img.save(path, "JPEG")


def _sections():
    cats = [("National & States", "राष्ट्रीय एवं राज्य"), ("Economy & Finance", "अर्थव्यवस्था एवं वित्त"),
            ("Defence & Awards", "रक्षा एवं पुरस्कार")]
    bites = []
    for i in range(30):
        cen, chi = cats[i % 3]
        bites.append({"category_en": cen, "category_hi": chi,
                      "en": f"Quick bite number {i + 1}: the Centre approved a Rs {100 + i} crore plan for district {i + 1}.",
                      "hi": f"क्विक बाइट संख्या {i + 1}: केंद्र ने जिला {i + 1} के लिए ₹{100 + i} करोड़ की योजना को मंजूरी दी।"})
    bites.sort(key=lambda b: [c for c, _h in cats].index(b["category_en"]))
    agri = {"items": [{"en": "UP began paddy procurement at MSP of Rs 2,441 per quintal through 4,500 centres.",
                       "hi": "उत्तर प्रदेश ने 4,500 केंद्रों के माध्यम से ₹2,441 प्रति क्विंटल MSP पर धान खरीद शुरू की।"}],
            "static_gk": [{"en": "NABARD was established on 12 July 1982.",
                           "hi": "NABARD की स्थापना 12 जुलाई 1982 को हुई थी।"}]}
    return bites, agri


@pytest.fixture(scope="module")
def v5(tmp_path_factory):
    from src.generate_pdf import generate_pdf
    from tests.fixtures.bilingual_sample import build_sample_content, build_sample_mcqs
    tmp = tmp_path_factory.mktemp("v5")
    content = build_sample_content()
    for n, it in enumerate(content["items"][:4]):
        p = tmp / f"p{n}.jpg"
        _photo(p, n + 3)
        it["image_path"] = str(p)
        it["image_credit"] = "Test Wire"
    content["quick_bites"], content["agri_corner"] = _sections()
    out = tmp / "v5.pdf"
    generate_pdf(content, build_sample_mcqs(), output_path=str(out))
    return out, content


# --------------------------------------------------------------------------- #
# 2. type sizes
# --------------------------------------------------------------------------- #
def test_style_sizes_are_in_the_agreed_ranges():
    import src.generate_pdf as gp
    assert gp.PDF_FONT_SCALE == 1.0
    ranges = gp.TYPE_RANGES
    assert ranges == {"main_title": (24.0, 28.0), "module": (17.0, 19.0), "chapter": (14.0, 15.0),
                      "body": (11.0, 11.5), "table": (9.5, 10.5), "footer": (8.0, 9.0)}
    for name, role in gp.STYLE_ROLES.items():
        lo, hi = ranges[role]
        assert lo <= gp.STYLES[name].fontSize <= hi, (name, role, gp.STYLES[name].fontSize)
    assert set(gp.STYLE_ROLES) == set(gp.STYLES)          # every style has a role
    for const, role in ((gp.FS_MAIN_TITLE, "main_title"), (gp.FS_MODULE, "module"), (gp.FS_CHAPTER, "chapter"),
                        (gp.FS_QUESTION, "chapter"), (gp.FS_BODY, "body"), (gp.FS_TABLE, "table"),
                        (gp.FS_QUICK_BITE, "table"), (gp.FS_FOOTER, "footer")):
        lo, hi = ranges[role]
        assert lo <= const <= hi, (const, role)


def test_hindi_sizes_are_visually_matched_within_allowance():
    import src.generate_pdf as gp
    for role, (lo, hi) in gp.TYPE_RANGES.items():
        for en in (lo, (lo + hi) / 2, hi):
            h = gp.hindi_font_size(en)
            assert lo <= h <= hi + gp.HINDI_VISUAL_ALLOWANCE_PT, (role, en, h)
    assert gp.hindi_font_size(gp.FS_BODY) > gp.FS_BODY   # Mukta set a little larger than Poppins


@needs_shaping
def test_rendered_latin_sizes_stay_in_ranges(v5):
    import src.generate_pdf as gp
    path, _content = v5
    sizes = Counter()
    with fitz.open(str(path)) as doc:
        for page in doc:
            for b in page.get_text("dict")["blocks"]:
                for line in b.get("lines", []):
                    for sp in line["spans"]:
                        if "Poppins" in sp["font"] and sp["text"].strip():
                            sizes[round(sp["size"], 2)] += len(sp["text"])
    allowed = list(gp.TYPE_RANGES.values())
    bad = {s: n for s, n in sizes.items() if not any(lo - 0.01 <= s <= hi + 0.01 for lo, hi in allowed)}
    assert not bad, bad
    body_lo, body_hi = gp.TYPE_RANGES["body"]
    assert body_lo <= sizes.most_common(1)[0][0] <= body_hi   # most text is body text


# --------------------------------------------------------------------------- #
# 1. magazine cover
# --------------------------------------------------------------------------- #
@needs_shaping
def test_magazine_cover(v5):
    path, content = v5
    with fitz.open(str(path)) as doc:
        cover = doc[0].get_text()
        assert "CURRENT AFFAIRS" in cover and "TOP STORY" in cover and "ALSO IN THIS EDITION" in cover
        assert "INSIDE" in cover and "Quick Bites (30)" in cover and "Agriculture Corner" in cover
        assert "News in Pictures" in cover and "18 October 2026" in cover
        assert "@agrilearningpoint" in cover
        assert [im for im in doc[0].get_images() if im[5] != 'Indexed']  # hero photo
        teasers = [l for l in doc[0].get_links() if l["kind"] == fitz.LINK_GOTO]
        assert len(teasers) >= 3 + 3                             # hero + >=2 cover lines + inside pills


@needs_shaping
def test_cover_without_photos_is_typographic(tmp_path):
    from src.generate_pdf import generate_pdf
    from tests.fixtures.bilingual_sample import build_sample_content, build_sample_mcqs
    out = tmp_path / "nophoto.pdf"
    generate_pdf(build_sample_content(), build_sample_mcqs(), output_path=str(out))
    with fitz.open(str(out)) as doc:
        txt = doc[0].get_text()
        assert "TOP STORY" in txt and "ALSO IN THIS EDITION" in txt
        # Hindi lines are shaped into small indexed rasters; a hero photo is RGB/JPEG.
        assert not [im for im in doc[0].get_images() if im[5] != 'Indexed']


# --------------------------------------------------------------------------- #
# 3. mobile-safe internal links
# --------------------------------------------------------------------------- #
@needs_shaping
def test_internal_links_are_explicit_goto_full_rows_and_resolve(v5):
    path, content = v5
    n_units = len(content["items"])
    with fitz.open(str(path)) as doc:
        story_page = {}
        for pno in range(doc.page_count):
            txt = doc[pno].get_text()
            for i in range(1, n_units + 1):
                if f"STORY {i} OF " in txt and i not in story_page:
                    story_page[i] = pno
        internal = 0
        for pno in range(doc.page_count):
            seen = set()
            for l in doc[pno].get_links():
                if l["kind"] == fitz.LINK_URI:
                    continue
                internal += 1
                assert l["kind"] == fitz.LINK_GOTO and isinstance(l["page"], int) and l["page"] >= 0, l
                obj = doc.xref_object(l["xref"])
                assert "/S /GoTo" in obj and "/D [" in obj and "/Dest" not in obj, obj
                assert l["from"].height >= 29.9, (pno + 1, l["from"])
                key = (tuple(round(v) for v in l["from"]), l["page"])
                assert key not in seen, ("duplicate link", pno + 1, key)
                seen.add(key)
        assert internal >= n_units * 2  # contents rows + gallery/cover + INDEX pills
        # Contents page: row i -> the page where story i starts.
        toc = next(p for p in range(doc.page_count) if "TODAY'S CONTENTS" in doc[p].get_text())
        rows = sorted((l for l in doc[toc].get_links() if l["kind"] == fitz.LINK_GOTO and l["from"].x0 < 60),
                      key=lambda l: l["from"].y0)
        # Section rows (Agriculture Corner, Quick Bites, ...) also live on the contents page.
        story_pages = set(story_page.values())
        rows = [l for l in rows if l["page"] in story_pages][:n_units]
        assert len(rows) == n_units
        for i, l in enumerate(rows, 1):
            assert l["from"].width > 400                    # the whole row, not just the text
            assert l["page"] == story_page[i], (i, l["page"], story_page[i])
        # News in Pictures: one link per card covering the photo, to that card's story.
        pics = next(p for p in range(doc.page_count) if "NEWS IN PICTURES" in doc[p].get_text())
        cards = [l for l in doc[pics].get_links() if l["kind"] == fitz.LINK_GOTO and l["from"].y0 > 80]
        assert len(cards) == 4
        assert {l["page"] for l in cards} == {story_page[i] for i in range(1, 5)}
        assert all(l["from"].height > 120 for l in cards)
        # INDEX pill on every inner page -> contents page.
        for pno in range(1, doc.page_count):
            assert any(l["kind"] == fitz.LINK_GOTO and l["page"] == toc and l["from"].y0 < 50
                       for l in doc[pno].get_links()), pno + 1


# --------------------------------------------------------------------------- #
# 5. auto sections render + page cap trims Quick Bites first
# --------------------------------------------------------------------------- #
@needs_shaping
def test_quick_bites_and_agri_corner_render(v5):
    path, _content = v5
    with fitz.open(str(path)) as doc:
        text = "\n".join(p.get_text() for p in doc)
    assert "AGRICULTURE CORNER" in text and "QUICK BITES: Other Important News" in text
    assert "Quick bite number 30" in text and "क्विक बाइट संख्या" in text


@needs_shaping
@pytest.mark.timeout(600)
def test_page_cap_trims_quick_bites_before_photos(tmp_path, monkeypatch):
    from src.generate_pdf import generate_pdf, _pdf_page_count
    from tests.fixtures.bilingual_sample import build_sample_content, build_sample_mcqs
    content = build_sample_content()
    p = tmp_path / "p.jpg"
    _photo(p, 9)
    content["items"][0]["image_path"] = str(p)
    bites, agri = _sections()
    content["quick_bites"] = bites * 2                       # 60 bites
    full = tmp_path / "full.pdf"
    generate_pdf(content, build_sample_mcqs(), output_path=str(full))
    n_full = _pdf_page_count(str(full))
    monkeypatch.setenv("PDF_QA_MAX_PAGES", str(n_full - 1))
    capped = tmp_path / "capped.pdf"
    generate_pdf(content, build_sample_mcqs(), output_path=str(capped))
    with fitz.open(str(capped)) as doc:
        assert doc.page_count <= n_full - 1
        text = "\n".join(pg.get_text() for pg in doc)
        assert doc[0].get_images()                             # photos kept: bites were trimmed first
    assert text.count("Quick bite number") < 60
    assert len(content["quick_bites"]) == 60                   # caller's content is not mutated
