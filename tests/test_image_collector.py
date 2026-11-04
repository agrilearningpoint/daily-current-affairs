# -*- coding: utf-8 -*-
"""Image collector (pipeline/news_images.py): PIB + Wikimedia Commons sources,
relevance, dedupe, time cap, category graphics, fail-open. All HTTP is mocked."""
from __future__ import annotations

import io
import json
import time
from pathlib import Path

import pytest

from pipeline import news_images as ni


def _photo_bytes(seed: int, size=(800, 500)) -> bytes:
    from PIL import Image
    import random
    rnd = random.Random(seed)
    img = Image.new("RGB", size)
    px = img.load()
    for x in range(0, size[0], 4):
        for y in range(0, size[1], 4):
            c = (rnd.randrange(256), rnd.randrange(256), rnd.randrange(256))
            for dx in range(4):
                for dy in range(4):
                    if x + dx < size[0] and y + dy < size[1]:
                        px[x + dx, y + dy] = c
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    return buf.getvalue()


def _commons_json(pages):
    return json.dumps({"query": {"pages": {str(i): {
        "index": i, "title": t,
        "imageinfo": [{"thumburl": u, "url": u, "mime": "image/jpeg",
                       "extmetadata": {"LicenseShortName": {"value": lic},
                                       "Artist": {"value": "<a href='x'>Jane Doe</a>"}}}]}
        for i, (t, u, lic) in enumerate(pages)}}}).encode()


def test_pib_release_photos_are_used_with_pib_credit(tmp_path):
    page = "https://pib.gov.in/PressReleasePage.aspx?PRID=1"
    html = (b'<meta property="og:image" content="https://pib.gov.in/images/indian-emblem.png">'
            b'<img src="https://static.pib.gov.in/WriteReadData/userfiles/image/2026/nov/image001_a.jpg">')
    blobs = {"https://static.pib.gov.in/WriteReadData/userfiles/image/2026/nov/image001_a.jpg":
             _photo_bytes(1, (300, 220))}

    def fetch(url, timeout, max_bytes):
        if url == page:
            return 200, "text/html", html
        if url in blobs:
            return 200, "image/jpeg", blobs[url]
        raise OSError("offline")

    items = [{"event_id": "p1", "importance_score": 9, "source": {"name": "PIB", "url": page}}]
    stats = ni.attach_images(items, "j", tmp_path, fetch=fetch)
    assert stats["attached"] == 1 and items[0]["image_credit"] == "Photo: PIB"
    assert items[0]["image_source_kind"] == "pib"
    assert "emblem" not in items[0]["image_url_used"]


def test_commons_relevance_licence_and_credit():
    good = ("File:Reserve Bank of India headquarters.jpg", "https://upload.wikimedia.org/a.jpg", "CC BY-SA 4.0")
    unrelated = ("File:Langur monkey, Orchha, Madhya Pradesh, India.jpg", "https://upload.wikimedia.org/b.jpg",
                 "CC BY-SA 4.0")
    nonfree = ("File:Reserve Bank of India building.jpg", "https://upload.wikimedia.org/c.jpg", "Fair use")

    def fetch(url, timeout, max_bytes):
        return 200, "application/json", _commons_json([good, unrelated, nonfree])

    got = ni.commons_candidates("Reserve Bank of India", fetch)
    assert [u for u, _ in got] == ["https://upload.wikimedia.org/a.jpg"]
    assert got[0][1] == "Photo: Jane Doe / Wikimedia Commons, CC BY-SA 4.0"
    assert not ni.commons_title_matches(unrelated[0], "Madhya Pradesh")
    assert not ni.commons_title_matches("File:ISRO logo.png", "NABARD")


def test_story_entities_skip_source_orgs_and_generic_words():
    it = {"organizations": ["PIB", "Government of India", "NABARD", "RBI"],
          "headline_en": ">> Soreng, Sikkim: first organic fisheries cluster"}
    ents = ni.story_entities(it, limit=3)
    assert ents[0] == "NABARD" and "PIB" not in ents and "Government of India" not in ents
    assert "RBI" not in ents  # single 3-letter token is too ambiguous for a Commons search


def test_collector_is_fail_open_on_any_error(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("network down")

    items = [{"event_id": "e1", "importance_score": 1, "organizations": ["NABARD"],
              "source": {"url": "https://pub.example/a"}, "image_url": "https://img.example/x.jpg"}]
    stats = ni.attach_images(items, "j", tmp_path, fetch=boom, post=boom)
    assert stats["attached"] == 0 and items[0]["image_path"] == ""
    # Even a broken candidate builder never escapes.
    monkeypatch.setattr(ni, "candidate_sources", boom)
    stats = ni.attach_images(items, "j", tmp_path, fetch=boom)
    assert stats["attached"] == 0


def test_dedupe_by_url_and_by_content(tmp_path):
    same = _photo_bytes(7)

    def fetch(url, timeout, max_bytes):
        return 200, "image/jpeg", same

    items = [{"event_id": f"e{i}", "importance_score": 10 - i,
              "image_url": u, "source": {"name": "S"}}
             for i, u in enumerate(["https://img.example/a.jpg", "https://img.example/a.jpg",
                                    "https://img.example/b.jpg"])]
    stats = ni.attach_images(items, "j", tmp_path, fetch=fetch)
    assert stats["attached"] == 1
    assert [bool(it["image_path"]) for it in items] == [True, False, False]


def test_limit_and_total_time_cap(tmp_path):
    calls = []

    def slow_fetch(url, timeout, max_bytes):
        calls.append(url)
        assert timeout <= 8.0
        time.sleep(0.4)
        return 200, "image/jpeg", _photo_bytes(len(calls))

    items = [{"event_id": f"e{i}", "importance_score": 50 - i,
              "image_url": f"https://img.example/{i}.jpg"} for i in range(20)]
    t0 = time.monotonic()
    stats = ni.attach_images(items, "j", tmp_path, fetch=slow_fetch, total_budget=1.5)
    assert time.monotonic() - t0 < 4.0
    assert stats["budget_exhausted"] and stats["attached"] < 20
    calls.clear()
    stats = ni.attach_images([dict(it, image_path="") for it in items], "j2", tmp_path,
                             fetch=lambda u, t, m: (200, "image/jpeg", _photo_bytes(hash(u) % 999)), limit=4)
    assert stats["attached"] == 4


def test_category_graphics_top_up_and_are_not_real_photos(tmp_path):
    items = [{"event_id": f"e{i}", "importance_score": i, "category": "Economy", "image_path": ""}
             for i in range(5)]
    items[0]["image_path"] = str(tmp_path / "real.jpg")
    added = ni.fill_category_graphics(items, "j", tmp_path, real_count=1, target=3)
    assert added == 2
    ph = [it for it in items if it.get("image_placeholder")]
    assert len(ph) == 2 and all(it["image_credit"].startswith("Graphic:") for it in ph)
    assert all(Path(it["image_path"]).is_file() for it in ph)
    assert ni.real_photo_count(items) == 1


def test_category_graphics_fail_open(tmp_path, monkeypatch):
    monkeypatch.setattr(ni, "make_category_graphic", lambda *a, **k: (_ for _ in ()).throw(OSError("disk")))
    items = [{"event_id": "e", "category": "Sports", "image_path": ""}]
    assert ni.fill_category_graphics(items, "j", tmp_path, real_count=0, target=10) == 0
    assert items[0]["image_path"] == ""


def test_google_news_link_is_resolved_before_og_lookup(tmp_path):
    gn = "https://news.google.com/rss/articles/CBMiABC?oc=5"
    real = "https://pub.example/story"
    pages = {"https://news.google.com/rss/articles/CBMiABC": b'<div data-n-a-sg="SIG" data-n-a-ts="123"></div>',
             real: b'<meta property="og:image" content="https://img.example/story.jpg">'}

    def fetch(url, timeout, max_bytes):
        if url in pages:
            return 200, "text/html", pages[url]
        if url == "https://img.example/story.jpg":
            return 200, "image/jpeg", _photo_bytes(3)
        raise OSError("offline")

    def post(url, data, timeout):
        inner = json.dumps(["garturl", real])
        return 200, ")]}'\n\n" + json.dumps([["wrb.fr", "Fbv4je", inner]])

    items = [{"event_id": "g", "importance_score": 1, "source": {"name": "The Hindu", "url": gn}}]
    stats = ni.attach_images(items, "j", tmp_path, fetch=fetch, post=post)
    assert stats["attached"] == 1 and items[0]["image_credit"] == "The Hindu"


def test_qa_photo_shortfall_is_info_only(monkeypatch):
    import importlib.util
    root = Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location("t_qa19_img", str(root / "agents" / "19_pdf_qa.py"))
    qa = importlib.util.module_from_spec(spec)
    import sys
    monkeypatch.setitem(sys.modules, "t_qa19_img", qa)
    spec.loader.exec_module(qa)
    monkeypatch.setattr(qa, "STRICT", True)
    rep = qa.QAReport(pdf_path="x", checked_at="now")
    qa.check_photo_count(rep, [{"image_path": "a.jpg"}, {"image_path": "g.jpg", "image_placeholder": True}])
    assert [i.code for i in rep.issues] == ["few_photos"] and rep.issues[0].severity == "info"
    assert rep.passed


def test_home_pages_never_vouch_for_photos(tmp_path):
    pages = {"https://www.pib.gov.in/": b'<img src="https://static.pib.gov.in/WriteReadData/userfiles/image/x1.jpg">',
             "https://www.nobelprize.org/": b'<meta property="og:image" content="https://img.example/brand.jpg">'}
    calls = []

    def fetch(url, timeout, max_bytes):
        calls.append(url)
        if url in pages:
            return 200, "text/html", pages[url]
        return 200, "image/jpeg", _photo_bytes(9)

    items = [{"event_id": "h1", "importance_score": 2, "source": {"name": "PIB", "url": "https://www.pib.gov.in/"}},
             {"event_id": "h2", "importance_score": 1, "source": {"name": "Nobel", "url": "https://www.nobelprize.org/"}}]
    stats = ni.attach_images(items, "j", tmp_path, fetch=fetch)
    assert stats["attached"] == 0
    assert not any("x1.jpg" in c or "brand.jpg" in c for c in calls)
