"""Chrome/non-news filtering for collected candidates.

Titles in the "dropped" list are taken verbatim from the 2026-10-16 dry run
(38896579675), where 19 of 28 selected items were site chrome. Titles in the
"kept" list are the real news items from the same edition, plus boundary cases
the rules must not swallow.
"""
import sys
from pathlib import Path

import pytest

from pipeline import collector, quality
from pipeline.collector import _extract_listing_items

CHROME = [
    ("POLICY COORDINATION - Department of Agriculture & Farmers Welfare", "Department of Agriculture & Farmers Welfare", "section-label"),
    ("Press Releases - Reserve Bank of India", "Reserve Bank of India", "nav-prefix"),
    ("Press Releases| Official Website of Reserve Bank of India - Reserve Bank of India", "Reserve Bank of India", "nav-prefix"),
    ("Hyperlink Policy - Department of Agriculture & Farmers Welfare", "Department of Agriculture & Farmers Welfare", "document-page"),
    ("Accessibility Help - Department of Agriculture & Farmers Welfare", "Department of Agriculture & Farmers Welfare", "document-page"),
    ("Untitled - ICAR-indian agricultural research institute", "ICAR", "nav-label"),
    ("Untitled - Ministry of Finance, Department of Financial Services", "Ministry of Finance", "nav-label"),
    ("DROUGHT MANAGEMENT - Department of Agriculture & Farmers Welfare", "Department of Agriculture & Farmers Welfare", "section-label"),
    ("CROP INSURANCE DIVISION - Department of Agriculture & Farmers Welfare", "Department of Agriculture & Farmers Welfare", "section-label"),
    ("PLANT PROTECTION - Department of Agriculture & Farmers Welfare", "Department of Agriculture & Farmers Welfare", "section-label"),
    ("HORTICULTURE - Department of Agriculture & Farmers Welfare", "Department of Agriculture & Farmers Welfare", "section-label"),
    ("RAINFED FARMING SYSTEM - Department of Agriculture & Farmers Welfare", "Department of Agriculture & Farmers Welfare", "section-label"),
    ("About Economics and Statistics (Establishment) - Department of Agriculture & Farmers Welfare", "Department of Agriculture & Farmers Welfare", "about-page"),
    ("ECI Candidate Affidavit - Election Commission of India - ECI", "ECI", "document-page"),
    ("F. No. BEDF/2022-23-000051/054 16.10.2026 NOTICE INVITING TENDER The Basmati Export Develo", "APEDA", "document-page"),
    ("Election Commission of India Nirvachan Sadan, Ashoka Road, New Delhi-110001 No.23/2026-ERS", "ECI", "address"),
    ("Competition Commission of India, Government of India - Competition Commission of India", "Competition Commission of India", "self-link"),
    ("International Financial Services Centres Authority - International Financial Services Centres Authority", "International Financial Services Centres Authority", "self-link"),
    ("- Reserve Bank of India", "Reserve Bank of India", "self-link"),
    ("", "PIB", "empty"),
]

NEWS = [
    "Don't bulldoze delimitation Bill again, call all-party meet: Kharge to Modi",
    "South Indian Bank aims 16% loan growth in FY27 amid West Asia war risks",
    "India GDP to grow 7.1-7.3% in FY27 on private investment revival: Deloitte",
    "India wants to push rupee trade to help forex-starved nations: Sitharaman",
    "Trump's US investment tracker: India ranks 6th with $500 billion, UAE leads with $1.4 tril",
    "After SC notice, BJP accuses Rahul Gandhi of ‘spreading lies and confusion’ over Form 6",
    "Dr. Ashok Kumar Mittal leads 'Seva Sankalp', a salute to Prime Minister Modi's 25 years of",
    "Omaxe, Lemon Tree ink pact to manage 10 upcoming hotels worth ₹4,000 cr",
    # boundary cases the rules must not swallow
    "About 300 villages got tap water under the scheme",
    "About time the government raised MSP",
    "Wheat MSP - up Rs 150 per quintal this season",
    "PM MODI LAUNCHES NEW SCHEME FOR FARMERS IN BIHAR TODAY",
    "Horticulture output rises 3.2% as onion prices cool in mandis",
]


@pytest.mark.parametrize(("title", "source_name", "reason"), CHROME)
def test_chrome_titles_are_rejected(title, source_name, reason):
    assert quality.reject_reason(title, source_name) == reason


@pytest.mark.parametrize("title", NEWS)
def test_real_headlines_survive(title):
    assert quality.reject_reason(title, "The Hindu") is None


def test_split_publisher_keeps_dashed_headlines_intact():
    assert quality.split_publisher("Wheat MSP - up Rs 150 per quintal") == (
        "Wheat MSP - up Rs 150 per quintal", "")
    assert quality.split_publisher("Press Releases - Reserve Bank of India") == (
        "Press Releases", "Reserve Bank of India")


def test_kill_switch_disables_the_filter(monkeypatch):
    monkeypatch.setenv(quality.FILTER_ENV, "0")
    assert quality.reject_reason("Hyperlink Policy", "DA&FW") is None
    assert quality.chrome_filter_enabled() is False
    monkeypatch.setenv(quality.FILTER_ENV, "1")
    assert quality.chrome_filter_enabled() is True


LISTING_HTML = """
<html><body>
  <header><a href="/site/about">Hyperlink Policy - Department of Agriculture &amp; Farmers Welfare</a></header>
  <nav><a href="/site/help">Accessibility Help - Department of Agriculture &amp; Farmers Welfare</a></nav>
  <main>
    <a href="/news/2026/msp-hike">Cabinet clears wheat MSP hike of Rs 150 per quintal for rabi season</a>
    <a href="/news/2026/drought-package">Government releases drought relief package for 12 states</a>
  </main>
  <footer><a href="/site/policy">CROP INSURANCE DIVISION - Department of Agriculture &amp; Farmers Welfare</a></footer>
</body></html>
"""


def test_listing_extraction_skips_nav_chrome(monkeypatch):
    source = {
        "name": "Department of Agriculture & Farmers Welfare",
        "url": "https://agriwelfare.gov.in/",
        "level": 1,
        "category": "agriculture",
    }
    items = _extract_listing_items(
        source, "https://agriwelfare.gov.in/index.aspx", LISTING_HTML, "official_html", 20)

    titles = [item["headline_en"] for item in items]
    assert titles == [
        "Cabinet clears wheat MSP hike of Rs 150 per quintal for rabi season",
        "Government releases drought relief package for 12 states",
    ], "nav/header/footer chrome must not become candidates"


def test_off_host_links_are_still_rejected():
    """The chrome filter must not change which hosts are accepted."""
    source = {"name": "PIB", "url": "https://pib.gov.in/", "level": 1}
    items = _extract_listing_items(
        source, "https://pib.gov.in/index.aspx",
        "<html><body><main><a href='https://example.com/x'>Some off-host link with a long title</a></main></body></html>",
        "official_html", 20)
    assert items == []


IN_CONTENT_CHROME_HTML = """
<html><body><main>
  <a href="/site/policy">Hyperlink Policy - Department of Agriculture &amp; Farmers Welfare</a>
  <a href="/site/label">CROP INSURANCE DIVISION - Department of Agriculture &amp; Farmers Welfare</a>
  <a href="/news/2026/msp-hike">Cabinet clears wheat MSP hike of Rs 150 per quintal for rabi season</a>
</main></body></html>
"""


def test_chrome_rejections_are_counted_for_the_collection_report():
    """Chrome that sits in the content area is dropped by rule and counted."""
    collector.CHROME_REJECTED = 0
    source = {"name": "Department of Agriculture & Farmers Welfare",
              "url": "https://agriwelfare.gov.in/", "level": 1}
    items = _extract_listing_items(
        source, "https://agriwelfare.gov.in/index.aspx", IN_CONTENT_CHROME_HTML,
        "official_html", 20)

    assert [item["headline_en"] for item in items] == [
        "Cabinet clears wheat MSP hike of Rs 150 per quintal for rabi season"]
    assert collector.CHROME_REJECTED == 2, "the report must show how much chrome was dropped"
    assert "chrome_rejected_count" in collector.CollectionReport("daily", "2026-10-16", "").__dict__


# --------------------------------------------------------------------------- #
# Production collection path: pipeline/01_source_fetch.py
# --------------------------------------------------------------------------- #
import importlib.util  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

from pipeline.source_registry import SourceSpec  # noqa: E402

GOOGLE_NEWS_STYLE_FEED = """<?xml version="1.0"?>
<rss version="2.0"><channel>
  <item>
    <title>Hyperlink Policy - Department of Agriculture &amp; Farmers Welfare</title>
    <link>https://agriwelfare.gov.in/hyperlink-policy</link>
    <pubDate>Thu, 16 Oct 2026 06:00:00 GMT</pubDate>
    <description>Hyperlink Policy</description>
  </item>
  <item>
    <title>CROP INSURANCE DIVISION - Department of Agriculture &amp; Farmers Welfare</title>
    <link>https://agriwelfare.gov.in/crop-insurance</link>
    <pubDate>Thu, 16 Oct 2026 06:05:00 GMT</pubDate>
    <description>CROP INSURANCE DIVISION</description>
  </item>
  <item>
    <title>Cabinet clears wheat MSP hike of Rs 150 per quintal for rabi season</title>
    <link>https://example.gov.in/news/msp-hike</link>
    <pubDate>Thu, 16 Oct 2026 06:10:00 GMT</pubDate>
    <description>Wheat support price increased.</description>
  </item>
</channel></rss>
"""


def test_source_fetch_drops_chrome_entries(monkeypatch):
    """The Chrome that shipped in run 38897677177 came through this stage."""
    module_path = Path(__file__).resolve().parents[1] / "pipeline" / "01_source_fetch.py"
    spec = importlib.util.spec_from_file_location("alp_source_fetch_quality", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    class _Response:
        content = GOOGLE_NEWS_STYLE_FEED.encode("utf-8")

        def raise_for_status(self):
            return None

    monkeypatch.setattr(module.requests, "get", lambda *a, **k: _Response())
    feed_spec = SourceSpec(
        source_id="agriwelfare", name="Department of Agriculture & Farmers Welfare",
        rss_url="https://agriwelfare.gov.in/rss.xml", category="agriculture",
        tier="tier1", language="en", official=True, extra={},
    )
    window_start = datetime(2026, 10, 15, tzinfo=timezone.utc)
    window_end = datetime(2026, 10, 17, tzinfo=timezone.utc)

    articles, total, malformed, error, chrome_skipped = module.fetch_spec(
        feed_spec, window_start, window_end, set())

    assert error is None and total == 3 and malformed == 0
    assert chrome_skipped == 2, "chrome entries must be counted so runs stay auditable"
    assert [a["title"] for a in articles] == [
        "Cabinet clears wheat MSP hike of Rs 150 per quintal for rabi season"]
