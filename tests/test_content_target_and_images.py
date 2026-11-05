# -*- coding: utf-8 -*-
"""Content target (selection reserves, one MCQ per story, backfill) and news photos.

All network access is mocked: photo downloads go through an injected ``fetch``
and feed fetching through a monkeypatched ``requests.get``.
"""
import importlib.util
import io
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_agent(number):
    return _load(next((ROOT / "agents").glob(f"{number}_*.py")), f"test_ctai_agent_{number}")


def _photo_bytes(w=900, h=560, seed=1, fmt="JPEG"):
    from PIL import Image
    rnd = random.Random(seed)
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(0, h, 4):
        for x in range(0, w, 4):
            c = (rnd.randrange(256), rnd.randrange(256), rnd.randrange(256))
            for dy in range(4):
                for dx in range(4):
                    if x + dx < w and y + dy < h:
                        px[x + dx, y + dy] = c
    buf = io.BytesIO()
    img.save(buf, fmt)
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# 01 source fetch: feed images, og:image, undated official entries
# --------------------------------------------------------------------------- #
def _fetch_module():
    return _load(ROOT / "pipeline" / "01_source_fetch.py", "test_ctai_source_fetch")


def test_entry_image_prefers_largest_media_and_skips_logos():
    sf = _fetch_module()
    entry = {
        "media_content": [{"url": "https://cdn.example.com/site-logo.png", "medium": "image", "width": "1200"},
                          {"url": "https://cdn.example.com/photos/cyclone-small.jpg", "medium": "image", "width": "300"},
                          {"url": "https://cdn.example.com/photos/cyclone.jpg", "medium": "image", "width": "1024"}],
    }
    assert sf.extract_entry_image(entry) == "https://cdn.example.com/photos/cyclone.jpg"
    html_entry = {"summary": '<p><img src="//img.example.org/news/budget.jpg" width="800"></p>'}
    assert sf.extract_entry_image(html_entry) == "https://img.example.org/news/budget.jpg"
    assert sf.extract_entry_image({"summary": "no image here"}) == ""


def _rss(items, channel_date=None):
    chan = f"<lastBuildDate>{channel_date}</lastBuildDate>" if channel_date else ""
    body = "".join(
        f"<item><title>{t}</title><link>{l}</link>{f'<pubDate>{d}</pubDate>' if d else ''}"
        f"<description>{t} — detailed official release text for this item with enough words to be useful.</description></item>"
        for t, l, d in items)
    return f'<?xml version="1.0"?><rss version="2.0"><channel><title>x</title>{chan}{body}</channel></rss>'.encode()


class _Resp:
    def __init__(self, content, status=200):
        self.content = content
        self.status_code = status
        self.text = content.decode("utf-8", "replace")

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


@pytest.mark.parametrize("official,expected", [(True, 1), (False, 0)])
def test_undated_items_only_accepted_for_official_feed_dated_in_window(monkeypatch, official, expected):
    from email.utils import format_datetime
    from pipeline.source_registry import SourceSpec
    sf = _fetch_module()
    now = datetime.now(timezone.utc)
    feed = _rss([("Cabinet approves new scheme for dairy cooperatives in five states",
                  "https://www.pib.gov.in/PressReleasePage.aspx?PRID=1", None)],
                channel_date=format_datetime(now - timedelta(hours=2)))
    monkeypatch.setenv("ALP_DISABLE_NETWORK", "1")
    monkeypatch.setattr(sf.requests, "get", lambda *a, **k: _Resp(feed))
    spec = SourceSpec(source_id="pib", name="PIB", rss_url="https://www.pib.gov.in/rss", tier=1,
                      category="govt_national", official=official, language="en", enabled=True,
                      verification_policy="corroborate", extra={})
    arts, total, malformed, err = sf.fetch_spec(spec, now - timedelta(hours=24), now)
    assert err is None and total == 1
    assert len(arts) == expected
    if expected:
        assert arts[0]["date_source"] == "feed"
        assert sf.SKIP_REASONS["pib"]["feed_dated"] == 1
    else:
        assert malformed == 1 and sf.SKIP_REASONS["pib"]["no_date"] == 1


def test_feed_dated_fallback_can_be_disabled(monkeypatch):
    from email.utils import format_datetime
    from pipeline.source_registry import SourceSpec
    sf = _fetch_module()
    now = datetime.now(timezone.utc)
    feed = _rss([("Cabinet approves new scheme for dairy cooperatives in five states",
                  "https://www.pib.gov.in/PressReleasePage.aspx?PRID=1", None)],
                channel_date=format_datetime(now - timedelta(hours=2)))
    monkeypatch.setenv("ALP_DISABLE_NETWORK", "1")
    monkeypatch.setenv("ALP_ACCEPT_FEED_DATED_OFFICIAL", "0")
    monkeypatch.setattr(sf.requests, "get", lambda *a, **k: _Resp(feed))
    spec = SourceSpec(source_id="pib", name="PIB", rss_url="https://www.pib.gov.in/rss", tier=1,
                      category="govt_national", official=True, language="en", enabled=True,
                      verification_policy="corroborate", extra={})
    arts, _total, malformed, _err = sf.fetch_spec(spec, now - timedelta(hours=24), now)
    assert arts == [] and malformed == 1


# --------------------------------------------------------------------------- #
# News photos
# --------------------------------------------------------------------------- #
def test_og_image_extraction_and_url_screen():
    from pipeline.news_images import extract_og_image, plausible_image_url
    page = ('<html><head><meta property="og:image" content="/assets/default-og-image.png">'
            '<meta content="https://img.example.com/2026/11/flood.jpg" property="og:image:secure_url">'
            '</head></html>')
    assert extract_og_image(page, "https://example.com/news/1") == "https://img.example.com/2026/11/flood.jpg"
    assert not plausible_image_url("https://example.com/static/logo.png")
    assert not plausible_image_url("https://news.google.com/x.jpg")
    assert not plausible_image_url("https://example.com/a.svg")
    assert plausible_image_url("https://example.com/photo/rbi-governor.jpg")


def test_process_image_resizes_compresses_and_rejects_bad(tmp_path):
    from PIL import Image
    from pipeline.news_images import process_image_bytes
    info = process_image_bytes(_photo_bytes(1600, 900), tmp_path / "a.jpg")
    assert info and info["width"] == 1000 and info["bytes"] < 400_000
    with Image.open(tmp_path / "a.jpg") as im:
        assert im.format == "JPEG" and im.mode == "RGB"
    assert process_image_bytes(_photo_bytes(300, 200), tmp_path / "small.jpg") is None  # too small
    assert process_image_bytes(_photo_bytes(1600, 200), tmp_path / "strip.jpg") is None  # banner strip
    flat = io.BytesIO()
    Image.new("RGB", (900, 600), (240, 240, 240)).save(flat, "PNG")
    assert process_image_bytes(flat.getvalue(), tmp_path / "flat.jpg") is None  # placeholder
    assert process_image_bytes(b"<html>not an image</html>", tmp_path / "x.jpg") is None


def test_attach_images_uses_feed_then_og_image_dedupes_and_limits(tmp_path):
    from pipeline.news_images import attach_images
    photo1, photo2, photo3 = _photo_bytes(seed=1), _photo_bytes(seed=2), _photo_bytes(seed=3)
    pages = {
        "https://pub.example/a": b'<meta property="og:image" content="https://img.example/a.jpg">',
        "https://pub.example/b": b'<meta property="og:image" content="https://img.example/b.jpg">',
        "https://pub.example/c": b'<meta property="og:image" content="https://img.example/logo.png">',
        "https://pub.example/d": b'<meta property="og:image" content="https://img.example/a-copy.jpg">',
    }
    blobs = {"https://img.example/feed.jpg": photo3, "https://img.example/a.jpg": photo1,
             "https://img.example/b.jpg": photo2, "https://img.example/a-copy.jpg": photo1}
    calls = []

    def fetch(url, timeout, max_bytes):
        calls.append(url)
        if url in pages:
            return 200, "text/html", pages[url]
        if url in blobs:
            return 200, "image/jpeg", blobs[url]
        raise OSError("offline")

    items = [
        {"event_id": "e0", "importance_score": 50, "image_url": "https://img.example/feed.jpg",
         "source": {"name": "Feed Pub", "url": "https://pub.example/zz"}},
        {"event_id": "e1", "importance_score": 90, "source": {"name": "The Hindu", "url": "https://pub.example/a"}},
        {"event_id": "e2", "importance_score": 80, "source": {"name": "Mint", "url": "https://pub.example/b"}},
        {"event_id": "e3", "importance_score": 70, "source": {"name": "X", "url": "https://pub.example/c"}},
        {"event_id": "e4", "importance_score": 60, "source": {"name": "Y", "url": "https://pub.example/d"}},
        {"event_id": "e5", "importance_score": 40, "source": {"name": "Z", "url": "https://pub.example/missing"}},
    ]
    stats = attach_images(items, "daily_2026-11-02", tmp_path, limit=3, fetch=fetch)
    got = {it["event_id"]: it.get("image_path") for it in items}
    assert stats["attached"] == 3
    assert got["e1"] and got["e2"] and got["e0"]           # top-importance first, feed image used for e0
    assert not got["e3"] and not got["e4"]                 # logo rejected, duplicate photo rejected
    assert items[1]["image_credit"] == "The Hindu"
    assert all(Path(p).parent == tmp_path / "daily_2026-11-02" for p in got.values() if p)
    assert "https://img.example/logo.png" not in calls


def test_attach_images_is_fail_soft(tmp_path, monkeypatch):
    from pipeline.news_images import attach_images

    def boom(*a, **k):
        raise RuntimeError("network down")

    items = [{"event_id": "e1", "importance_score": 1, "image_url": "https://img.example/x.jpg",
              "source": {"url": "https://pub.example/a"}}]
    stats = attach_images(items, "j", tmp_path, fetch=boom)
    assert stats["attached"] == 0 and items[0]["image_path"] == ""
    monkeypatch.setenv("ALP_DISABLE_NETWORK", "1")
    stats = attach_images([{"event_id": "e2", "image_url": "https://img.example/y.jpg"}], "j", tmp_path)
    assert stats["attached"] == 0 and stats["skipped_reason"] == "network disabled"


# --------------------------------------------------------------------------- #
# MCQs: one valid bilingual MCQ per story
# --------------------------------------------------------------------------- #
def _story(eid, en, hi, kps_en, kps_hi, score=50, src="The Hindu"):
    return {"event_id": eid, "category": "National", "importance_score": score,
            "headline_en": ">> " + en, "headline_hi": ">> " + hi,
            "key_points_en": kps_en, "key_points_hi": kps_hi,
            "summary_en": kps_en[0], "detailed_explanation_en": " ".join(kps_en),
            "static_facts": {}, "exam_fact_en": kps_en[0],
            "source": {"name": src, "url": f"https://example.com/{eid}"}}


CYCLONE = _story("cyc", "Cyclone Murasu: Red alert in two Telangana districts, orange in three more",
                 "चक्रवात मुरासु: तेलंगाना के दो जिलों में रेड अलर्ट, तीन और में ऑरेंज अलर्ट",
                 ["The India Meteorological Department issued a red alert for two districts of Telangana as Cyclone Murasu approached."],
                 ["चक्रवात मुरासु के निकट आने पर भारत मौसम विज्ञान विभाग ने तेलंगाना के दो जिलों के लिए रेड अलर्ट जारी किया।"])
UAE = _story("uae", "Foreign Secretary holds talks in UAE on trade and energy cooperation",
             "विदेश सचिव ने व्यापार और ऊर्जा सहयोग पर संयुक्त अरब अमीरात में वार्ता की",
             ["The Foreign Secretary visited the UAE for talks on trade and energy cooperation."],
             ["विदेश सचिव ने व्यापार और ऊर्जा सहयोग पर वार्ता के लिए संयुक्त अरब अमीरात का दौरा किया।"])
VAGUE = _story("vague", "What the week ahead may bring for readers and viewers alike",
               "आने वाला सप्ताह पाठकों और दर्शकों के लिए क्या ला सकता है",
               ["A look at what the week ahead may bring."], ["आने वाले सप्ताह पर एक नज़र।"])


def test_state_and_country_templates_are_bilingual_and_validate():
    from pipeline.content import _evidence_text, validate_mcqs
    from pipeline.mcq_builder import country_mcq, state_mcq
    m = state_mcq(CYCLONE, _evidence_text(CYCLONE))
    assert m and m["type"] == "place-state"
    ok, rej = validate_mcqs([m], [CYCLONE])
    assert ok and not rej
    correct = m["options"]["ABCDE".index(m["correct"])]
    assert correct == "Telangana / तेलंगाना"
    assert all(" / " in o for o in m["options"]) and len(m["options"]) == 5
    assert "Telangana" not in m["question_en"] and "तेलंगाना" not in m["question_hi"]
    c = country_mcq(UAE, _evidence_text(UAE))
    assert c and c["options"]["ABCDE".index(c["correct"])].startswith("UAE / ")
    assert validate_mcqs([c], [UAE])[0]


def test_llm_mcq_rejection_is_retried_with_feedback():
    from pipeline.mcq_schema import generate_llm_mcqs
    prompts = []
    bad = {"mcq": {"question": {"en": "Which state?", "hi": "कौन सा राज्य?"},
                   "options": [{"en": x, "hi": "क"} for x in ["Telangana", "Kerala", "Bihar", "Goa", "Assam"]],
                   "correct": "A"}, "explanation": [{"en": "Telangana.", "hi": "तेलंगाना।"}]}
    good = dict(bad, explanation=[{"en": f"Telangana fact {i}.", "hi": f"तेलंगाना तथ्य {i}।"} for i in range(4)],
                static_gk=[{"label_en": "a", "value_en": "b", "label_hi": "क", "value_hi": "ख"}])  # 1 GK row -> dropped, not fatal

    def route(prompt, **kw):
        prompts.append(prompt)
        return json.dumps(bad if len(prompts) == 1 else good)

    out = generate_llm_mcqs([CYCLONE], lambda it: "Telangana cyclone", route=route, attempts=3)
    assert "cyc" in out and out["cyc"]["static_gk"] == []
    gen = [p for p in prompts if "MCQ SELF-CHECK" not in p]  # self-verify calls are separate
    assert len(gen) == 2 and "previous answer was rejected" in gen[1]


def _write_content(state, tmp_path, monkeypatch, items, reserves):
    monkeypatch.setattr(state, "CONTENT_DIR", tmp_path / "content")
    monkeypatch.setattr(state, "MCQ_DIR", tmp_path / "mcq")
    monkeypatch.setenv("ALP_MCQ_MODE", "deterministic")
    job_id = "daily_2026-11-02"
    state.write_json_atomic(state.data_path(state.CONTENT_DIR, job_id),
                            {"job": {"id": job_id}, "items": items, "reserve_items": reserves})
    return job_id


def test_stage16_gives_every_story_an_mcq_and_backfills_from_reserves(tmp_path, monkeypatch):
    from pipeline import state
    job_id = _write_content(state, tmp_path, monkeypatch, [CYCLONE, VAGUE], [UAE])
    ctx = {}
    load_agent("16").Agent(job_id, "daily", ctx).run()
    content = json.loads(state.data_path(state.CONTENT_DIR, job_id).read_text())
    mcqs = json.loads(state.data_path(state.MCQ_DIR, job_id).read_text())
    ids = [i["event_id"] for i in content["items"]]
    assert ids == ["cyc", "uae"]                     # vague story replaced by the reserve
    assert {m["event_id"] for m in mcqs} == set(ids)  # every printed story has its MCQ unit
    assert content["mcq_reconciliation"]["promoted_reserves"] == 1
    assert content["mcq_reconciliation"]["dropped_no_mcq"][0]["event_id"] == "vague"
    assert [m["q_num"] for m in mcqs] == list(range(1, len(mcqs) + 1))
    # stage 17 re-validates the same set without losing anything
    load_agent("17").Agent(job_id, "daily", {}).run()
    assert len(json.loads(state.data_path(state.MCQ_DIR, job_id).read_text())) == len(mcqs)


def test_selection_filters_non_news_caps_a_source_and_keeps_reserves(tmp_path, monkeypatch):
    from pipeline import state
    monkeypatch.setattr(state, "SCORED_DIR", tmp_path / "scored")
    monkeypatch.setattr(state, "SELECTED_DIR", tmp_path / "selected")
    monkeypatch.setenv("ALP_TARGET_NEWS_COUNT", "5")
    monkeypatch.setenv("ALP_SELECTION_RESERVES", "4")
    job_id = "daily_2026-11-02"
    items = [{"event_id": f"h{i}", "headline_en": f"Hindu national story number {i} about policy",
              "source_name": "The Hindu", "category": "National", "importance_score": 100 - i} for i in range(8)]
    items += [{"event_id": f"o{i}", "headline_en": f"Official release {i} on agriculture credit scheme",
               "source_name": f"Ministry {i}", "category": "Agriculture", "importance_score": 40 - i} for i in range(4)]
    items += [{"event_id": "bid", "headline_en": "Bid opening meeting link for Procurement of Laboratory Equipment",
               "source_name": "IARI", "category": "Agriculture", "importance_score": 99},
              {"event_id": "ed", "headline_en": "Why ISRO's success matters | The Hindu Editorial",
               "source_name": "The Hindu", "category": "National", "importance_score": 98}]
    state.write_json_atomic(state.data_path(state.SCORED_DIR, job_id), {"items": items})
    ctx = {}
    load_agent("10").Agent(job_id, "daily", ctx).run()
    sel = json.loads(state.data_path(state.SELECTED_DIR, job_id).read_text())
    ids = [x["event_id"] for x in sel["items"]]
    assert len(ids) == 5 and "bid" not in ids and "ed" not in ids
    assert sum(1 for x in sel["items"] if x["source_name"] == "The Hindu") <= 3
    assert len(sel["reserves"]) == 4 and not set(ids) & {x["event_id"] for x in sel["reserves"]}
    assert ctx["reserve_count"] == 4


def test_qa_story_count_floor():
    qa = load_agent("19")
    r = qa.QAReport(pdf_path="x", checked_at="now")
    qa.check_story_count(r, 13, 15)
    assert r.passed
    r = qa.QAReport(pdf_path="x", checked_at="now")
    qa.check_story_count(r, 12, 15)
    assert not r.passed and r.issues[0].code == "edition_story_shortfall"


# --------------------------------------------------------------------------- #
# PDF: photos rendered in units + News in Pictures, kept as JPEG, small file
# --------------------------------------------------------------------------- #
def test_pdf_renders_news_photos_and_gallery(tmp_path, monkeypatch):
    fitz = pytest.importorskip("fitz")
    sys.path.insert(0, str(ROOT))
    from tests.fixtures.bilingual_sample import build_sample_content, build_sample_mcqs
    from src.generate_pdf import generate_pdf
    content = build_sample_content()
    for n, it in enumerate(content["items"][:5]):
        p = tmp_path / f"p{n}.jpg"
        p.write_bytes(_photo_bytes(1000, 620, seed=n + 10))
        it["image_path"] = str(p)
        it["image_credit"] = "Test Wire"
    content["items"][5]["image_path"] = str(tmp_path / "missing.jpg")  # missing file is ignored
    out = tmp_path / "out.pdf"
    generate_pdf(content, build_sample_mcqs(), output_path=str(out))
    doc = fitz.open(str(out))
    text = "".join(page.get_text() for page in doc)
    assert "NEWS IN PICTURES" in text and "Image: Test Wire" in text
    jpeg_xrefs = set()
    for page in doc:
        for img in page.get_images(full=True):
            if img[8] == "DCTDecode" if len(img) > 8 else False:
                jpeg_xrefs.add(img[0])
    # each story photo embedded once (gallery + unit share the XObject) + the cropped cover hero
    assert len(jpeg_xrefs) == 6
    assert out.stat().st_size < 4_000_000


def test_photos_are_dropped_before_the_page_ceiling_is_exceeded(tmp_path, monkeypatch):
    fitz = pytest.importorskip("fitz")
    sys.path.insert(0, str(ROOT))
    from tests.fixtures.bilingual_sample import build_sample_content, build_sample_mcqs
    from src.generate_pdf import generate_pdf
    import src.generate_pdf as gp
    content = build_sample_content()
    for n, it in enumerate(content["items"][:4]):
        p = tmp_path / f"p{n}.jpg"
        p.write_bytes(_photo_bytes(1000, 620, seed=n + 30))
        it["image_path"] = str(p)
    monkeypatch.setenv("PDF_QA_MAX_PAGES", "1")  # impossible ceiling -> photos removed, text kept
    out = tmp_path / "out.pdf"
    generate_pdf(content, build_sample_mcqs(), output_path=str(out))
    doc = fitz.open(str(out))
    assert not any(x[8] == "DCTDecode" for page in doc for x in page.get_images(full=True))
    assert gp.PDF_INLINE_PHOTOS and gp.PDF_PHOTO_GALLERY  # module settings restored
