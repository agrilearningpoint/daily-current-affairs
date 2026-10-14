# -*- coding: utf-8 -*-
"""
Regression tests for Unicode safety.
Audit P0 fix: original bug was re.sub(r"[^\\x20-\\x7E]", "", text)
which destroyed Devanagari characters.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load(path: str):
    full = REPO_ROOT / path
    spec = importlib.util.spec_from_file_location(Path(path).stem, str(full))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def collector():
    return _load("agents/03_news_collection.py")


class TestUnicodePreservation:
    def test_hindi_preserved(self, collector):
        text = "कैबिनेट ने 5% MSP वृद्धि को मंजूरी दी"
        out = collector.clean_text(text)
        assert "कैबिनेट" in out
        assert "वृद्धि" in out
        assert "मंजूरी" in out

    def test_english_preserved(self, collector):
        out = collector.clean_text("Cabinet approves MSP hike")
        assert "Cabinet" in out
        assert "approves" in out

    def test_mixed_content_preserved(self, collector):
        text = "RBI ने दरें बढ़ाईं — Repo rate 6.5%"
        out = collector.clean_text(text)
        assert "RBI" in out
        assert "दरें" in out
        assert "6.5%" in out

    def test_tamil_preserved(self, collector):
        out = collector.clean_text("தமிழ் செய்தி")
        assert "தமிழ்" in out

    def test_bengali_preserved(self, collector):
        out = collector.clean_text("বাংলা খবর")
        assert "বাংলা" in out


class TestHtmlCleaning:
    def test_html_tags_stripped(self, collector):
        assert "<p>" not in collector.clean_text("<p>Hello</p>")

    def test_html_entities_unescaped(self, collector):
        out = collector.clean_text("A &amp; B &lt; C")
        assert "&amp;" not in out
        assert "&" in out

    def test_nbsp_handled(self, collector):
        out = collector.clean_text("Hello&nbsp;World")
        assert "Hello" in out and "World" in out


class TestControlChars:
    def test_null_byte_removed(self, collector):
        assert "\x00" not in collector.clean_text("abc\x00def")

    def test_newlines_collapsed(self, collector):
        out = collector.clean_text("line1\n\n\nline2")
        assert "\n" not in out

    def test_tabs_collapsed(self, collector):
        out = collector.clean_text("a\t\tb")
        assert "a b" == out


class TestNormalization:
    def test_nfc_normalization_applied(self, collector):
        import unicodedata
        decomposed = unicodedata.normalize("NFD", "कि")
        out = collector.clean_text(decomposed)
        assert out == unicodedata.normalize("NFC", "कि")

    def test_empty_input(self, collector):
        assert collector.clean_text("") == ""
        assert collector.clean_text(None) == ""

    def test_max_len_respected(self, collector):
        text = "x" * 10000
        out = collector.clean_text(text, max_len=100)
        assert len(out) <= 100
