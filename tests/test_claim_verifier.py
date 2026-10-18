"""Regression tests for pipeline.claim_verifier.

These lock in the fix for the P0 defect where claim_verifier imported a
non-existent ``get_router`` and called non-existent ``read_url``/``generate``,
so every item silently came back UNVERIFIED. All cases are offline: URL
retrieval and AI adjudication are injected / monkeypatched.
"""
import pytest

import pipeline.ai_router as ai_router
import pipeline.claim_verifier as cv


ITEM = {
    "event_id": "evt-1",
    "headline_en": "rbi raised the repo rate to 6.5%",
    "source_url": "https://example.invalid/news",
    "source_tier": "tier3",
}


def _verifier(content):
    return cv.ClaimVerifier(fetcher=lambda url: content)


@pytest.fixture(autouse=True)
def _no_jina(monkeypatch):
    monkeypatch.setattr(cv, "ENABLE_JINA", False)
    # AI is unconfigured unless a test opts in.
    monkeypatch.setattr(ai_router, "is_configured", lambda: False)


def test_missing_url_returns_error_not_verified():
    result = _verifier(None).verify_news_item(ITEM)
    assert result["verification_status"] == cv.ERROR
    assert result["verified"] is False
    assert result["overall_confidence"] == 0.0
    assert "Could not access source URL" in result["reason"]


def test_unreachable_source_never_reports_verified():
    # fetcher simulates an HTTP failure / timeout by returning None
    item = dict(ITEM, event_id="evt-2")
    result = cv.ClaimVerifier(fetcher=lambda url: None).verify_news_item(item)
    assert result["verified"] is False
    assert result["verification_status"] == cv.ERROR


def test_matched_numeric_claim_is_verified():
    page = "The central bank announced a hike to 6.5% effective immediately."
    result = _verifier(page).verify_news_item(ITEM)
    assert result["verified"] is True
    assert result["verification_status"] == cv.VERIFIED
    assert result["claims_verified"] == 1


def test_unsupported_numeric_claim_is_unverified_not_contradicted():
    page = "The central bank left the rate unchanged this cycle."
    result = _verifier(page).verify_news_item(ITEM)
    assert result["verified"] is False
    assert result["verification_status"] == cv.UNVERIFIED
    assert result["claims_verified"] == 0


def test_ai_unavailable_without_claims_is_unverified():
    item = dict(ITEM, event_id="evt-3", headline_en="farmers receive support under the welfare plan")
    result = _verifier("A long article body that does not matter here at all.").verify_news_item(item)
    assert result["verification_status"] == cv.UNVERIFIED
    assert result["verified"] is False


def test_ai_support_can_verify_claimless_headline(monkeypatch):
    monkeypatch.setattr(ai_router, "is_configured", lambda: True)
    monkeypatch.setattr(ai_router, "route", lambda *a, **k: '{"supported": true, "confidence": 0.95}')
    item = dict(ITEM, event_id="evt-4", headline_en="farmers receive support under the welfare plan")
    result = _verifier("A sufficiently long page body for verification here.").verify_news_item(item)
    assert result["verification_status"] == cv.VERIFIED
    assert result["verified"] is True


def test_ai_contradiction_is_reported_as_contradicted(monkeypatch):
    monkeypatch.setattr(ai_router, "is_configured", lambda: True)
    monkeypatch.setattr(ai_router, "route",
                        lambda *a, **k: '{"supported": false, "contradicted": true, "confidence": 0.9}')
    item = dict(ITEM, event_id="evt-5", headline_en="farmers receive support under the welfare plan")
    result = _verifier("The page explicitly denies the claim.").verify_news_item(item)
    assert result["verification_status"] == cv.CONTRADICTED
    assert result["verified"] is False


def test_malformed_ai_response_never_verifies(monkeypatch):
    monkeypatch.setattr(ai_router, "is_configured", lambda: True)
    monkeypatch.setattr(ai_router, "route", lambda *a, **k: "not json at all")
    item = dict(ITEM, event_id="evt-6", headline_en="farmers receive support under the welfare plan")
    result = _verifier("A sufficiently long page body for verification here.").verify_news_item(item)
    assert result["verified"] is False
    assert result["verification_status"] == cv.UNVERIFIED


def test_provider_failure_never_verifies(monkeypatch):
    monkeypatch.setattr(ai_router, "is_configured", lambda: True)
    monkeypatch.setattr(ai_router, "route", lambda *a, **k: None)
    item = dict(ITEM, event_id="evt-7", headline_en="farmers receive support under the welfare plan")
    result = _verifier("A sufficiently long page body for verification here.").verify_news_item(item)
    assert result["verified"] is False
    assert result["verification_status"] == cv.UNVERIFIED


def test_router_has_no_legacy_get_router_api():
    """The broken integration must not be reintroduced."""
    assert not hasattr(ai_router, "get_router")
    assert hasattr(ai_router, "route")


def test_fetch_page_rejects_non_http_schemes():
    assert cv.fetch_page("file:///etc/passwd") is None
    assert cv.fetch_page("") is None
    assert cv.fetch_page("ftp://example.invalid/x") is None


def test_extractor_deduplicates_claims():
    claims = cv.ClaimExtractor().extract_claims("RBI raised 6.5% and again 6.5%")
    values = [c["claim_value"] for c in claims if c["claim_type"] == "percentage"]
    assert values == ["6.5%"]
