"""Feed-level resilience tests for pipeline/01_source_fetch.py.

Two measured production defects are covered here:

1. PIB served XML with a bare ``&`` and SEBI served an undeclared ``&nbsp;``;
   feedparser rejected both feeds outright, so a tier-1 source disappeared from
   the edition without any article-level symptom. ``repair_feed_xml`` fixes the
   three documented defects and nothing else.
2. Indian Express and the Ministry of External Affairs answered HTTP 403 to the
   collector's user agent, so those feeds never contributed either.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from pipeline.source_registry import SourceSpec


def _load_collector(name: str):
    module_path = Path(__file__).resolve().parents[1] / "pipeline" / "01_source_fetch.py"
    spec = importlib.util.spec_from_file_location(name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


collector = _load_collector("alp_source_fetch_repair")

TRAILING_AMP_FEED = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    "<rss version=\"2.0\"><channel><title>PIB</title>"
    "<item><title>Cabinet approves MSP for rabi crops</title>"
    "<link>https://www.pib.gov.in/PressReleasePage.aspx?PRID=1</link>"
    "<description>Food & Agriculture Ministry</description>"
    "<pubDate>Thu, 15 Oct 2026 06:00:00 GMT</pubDate></item>"
    "</channel></rss>"
)

UNDECLARED_ENTITY_FEED = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    "<rss version=\"2.0\"><channel><title>SEBI</title>"
    "<item><title>SEBI revises disclosure norms&nbsp;for listed firms</title>"
    "<link>https://www.sebi.gov.in/media/1.html</link>"
    "<pubDate>Thu, 15 Oct 2026 07:00:00 GMT</pubDate></item>"
    "</channel></rss>"
)

HEALTHY_FEED = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    "<rss version=\"2.0\"><channel><title>RBI</title>"
    "<item><title>RBI keeps repo rate unchanged</title>"
    "<link>https://www.rbi.org.in/pressrelease/1.aspx</link>"
    "<description>Policy &amp; stance</description>"
    "<pubDate>Thu, 15 Oct 2026 08:00:00 GMT</pubDate></item>"
    "</channel></rss>"
)

SPEC = SourceSpec(source_id="feed-00-pib", name="PIB", rss_url="https://pib.gov.in/rss.xml",
                  tier=1, category="national", official=True)


def test_repair_fixes_bare_ampersand():
    repaired = collector.repair_feed_xml(TRAILING_AMP_FEED.encode("utf-8"))
    assert b"Food &amp; Agriculture" in repaired
    assert b"Food & Agriculture" not in repaired


def test_repair_fixes_undeclared_entity():
    repaired = collector.repair_feed_xml(UNDECLARED_ENTITY_FEED.encode("utf-8"))
    assert b"&nbsp;" not in repaired
    assert b"&#160;" in repaired


def test_repair_leaves_valid_entities_alone():
    payload = b"<rss><item><title>A &amp; B &#8212; C</title></item></rss>"
    assert collector.repair_feed_xml(payload) == payload


def test_repair_strips_bom_and_control_bytes():
    payload = "\ufeff<rss><item><title>Clean\x00 title</title></item></rss>".encode("utf-8")
    repaired = collector.repair_feed_xml(payload)
    assert not repaired.startswith(b"\xef\xbb\xbf")
    assert b"\x00" not in repaired


def test_malformed_feed_recovered_without_error():
    parsed, error = collector.parse_feed(TRAILING_AMP_FEED.encode("utf-8"))
    assert error is None
    assert [entry.title for entry in parsed.entries] == ["Cabinet approves MSP for rabi crops"]


def test_undeclared_entity_feed_recovered():
    parsed, error = collector.parse_feed(UNDECLARED_ENTITY_FEED.encode("utf-8"))
    assert error is None
    assert "SEBI revises disclosure norms" in parsed.entries[0].title


def test_healthy_feed_is_untouched():
    parsed, error = collector.parse_feed(HEALTHY_FEED.encode("utf-8"))
    assert error is None
    assert len(parsed.entries) == 1


def test_html_block_page_is_reported_as_such():
    html = b"<!DOCTYPE html><html><head><title>Access denied</title></head></html>"
    parsed, error = collector.parse_feed(html)
    assert error is not None
    assert "HTML page" in error
    assert parsed.entries == []


class _Response:
    def __init__(self, status_code: int, payload: bytes = HEALTHY_FEED.encode("utf-8")):
        self.status_code = status_code
        self.content = payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_fetch_retries_with_browser_ua_on_403(monkeypatch):
    seen: list[str] = []

    def fake_get(url, headers=None, timeout=None):
        seen.append(headers["User-Agent"])
        return _Response(403) if len(seen) == 1 else _Response(200)

    monkeypatch.setattr(collector.requests, "get", fake_get)
    payload, error = collector.fetch_feed_bytes(SPEC)
    assert error is None
    assert payload is not None
    assert seen == [collector.UA_DEFAULT, collector.UA_BROWSER]


def test_fetch_reports_error_when_still_blocked(monkeypatch):
    monkeypatch.setattr(collector.requests, "get",
                        lambda url, headers=None, timeout=None: _Response(403))
    payload, error = collector.fetch_feed_bytes(SPEC)
    assert payload is None
    assert error is not None and "403" in error


def test_fetch_reports_network_failure(monkeypatch):
    def boom(url, headers=None, timeout=None):
        raise TimeoutError("read timed out")

    monkeypatch.setattr(collector.requests, "get", boom)
    payload, error = collector.fetch_feed_bytes(SPEC)
    assert payload is None
    assert error is not None and "TimeoutError" in error


def test_fetch_spec_reports_repaired_feed_articles(monkeypatch):
    from datetime import datetime, timezone

    def fake_get(url, headers=None, timeout=None):
        return _Response(200, TRAILING_AMP_FEED.encode("utf-8"))

    monkeypatch.setattr(collector.requests, "get", fake_get)
    start = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 10, 16, 0, 0, tzinfo=timezone.utc)
    articles, total, malformed, error, chrome = collector.fetch_spec(SPEC, start, end, set())
    assert error is None
    assert [a["title"] for a in articles] == ["Cabinet approves MSP for rabi crops"]
    assert total == 1 and malformed == 0 and chrome == 0


def test_fetch_spec_still_rejects_chrome_after_repair(monkeypatch):
    from datetime import datetime, timezone

    feed = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<rss version=\"2.0\"><channel><title>Discovery</title>"
        "<item><title>- Reserve Bank of India</title><link>https://www.rbi.org.in/</link>"
        "<pubDate>Thu, 15 Oct 2026 06:00:00 GMT</pubDate></item>"
        "</channel></rss>"
    )
    monkeypatch.setattr(collector.requests, "get",
                        lambda url, headers=None, timeout=None: _Response(200, feed.encode("utf-8")))
    start = datetime(2026, 10, 15, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 10, 16, 0, 0, tzinfo=timezone.utc)
    articles, _total, _malformed, error, chrome = collector.fetch_spec(SPEC, start, end, set())
    assert error is None
    assert articles == []
    assert chrome == 1


@pytest.mark.parametrize("title", [
    "Notice inviting tender for supply of laptops",
    "Applications are invited for the post of Assistant Manager",
])
def test_notices_are_rejected_whatever_the_code(title):
    from pipeline.quality import reject_reason

    assert reject_reason(title) is not None


@pytest.mark.parametrize("title,reason", [
    ("Engagement of Pharmacist in the Bank on contract basis with fixed hourly remuneration, Mumbai",
     "notice"),
    ("https://mausam.imd.gov.in/bhubaneswar/ Agromet Advisory Service Bulletin for the State of Odisha",
     "routine-bulletin"),
    ("Weekly rainfall report for the week ending 14 October", "routine-bulletin"),
    ("io'> - dof.gov.in", "markup-leak"),
])
def test_non_editorial_official_pages_are_rejected(title, reason):
    """The 2026-10-15 edition carried these; they must not reach selection."""
    from pipeline.quality import reject_reason

    assert reject_reason(title) == reason


@pytest.mark.parametrize("title", [
    "Cabinet approves Productivity Linked Bonus for 78 days to Railway Employees",
    "Instructions given to expedite the computerization of PACS",
    "Data Centre Evaluation Framework to Help States Plan for Sustainable Growth",
    "IMD warns of heavy rainfall over Odisha coast as cyclone intensifies",
    "Government notifies new rules for wheat procurement",
])
def test_real_news_survives_the_new_rules(title):
    from pipeline.quality import reject_reason

    assert reject_reason(title, "PIB") is None
