# -*- coding: utf-8 -*-
"""
CLAIM VERIFIER v3 — Claim-Level Fact Verification
Agri Learning Point Pipeline — Production-Ready

What changed vs v2 (production audit):
- v2 imported ``get_router`` / called ``router.read_url`` / ``router.generate`` —
  none of those exist in pipeline/ai_router.py, so verification silently failed
  closed for every item. The integration now uses the real router API
  (``pipeline.ai_router.route``) and a dedicated, injectable page fetcher.
- Page retrieval and AI adjudication are now separate responsibilities
  (``fetch_page`` vs ``_ai_verify``), so each can be tested with a fake.
- A failed fetch or a failed AI call never fabricates a result: those become
  ``ERROR`` (or stay ``UNVERIFIED``), never ``VERIFIED``.
- Contract (per README shape) is unchanged for downstream readers:
  ``{event_id, headline_en, source_url, verified, overall_confidence,
     claims_verified, claims_total, claim_details, verification_status, reason}``

Status vocabulary:
    VERIFIED      — supported by the source with enough confidence
    PARTIAL       — some claims matched; not enough for the tier threshold
    UNVERIFIED    — could not be confirmed (insufficient / unsupported evidence)
    CONTRADICTED  — the source explicitly contradicts the headline claim
    ERROR         — the source could not be retrieved or adjudicated

Policy:
- An unsupported claim is UNVERIFIED, never automatically false.
- CONTRADICTED is only used when the AI explicitly reports a contradiction.

Usage:
    from pipeline.claim_verifier import verify_claims, verify_news_item
    result = verify_news_item(item)
    results = verify_claims(items)

Env:
    ALP_CLAIM_FETCH_TIMEOUT  (default 20)  — per-request timeout, seconds
    ALP_CLAIM_MAX_BYTES      (default 2000000) — response size cap
    ALP_CLAIM_ENABLE_JINA    (1 = try Jina Reader fallback when direct fetch fails)
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLDS = {
    "tier1": 0.70,
    "tier2": 0.85,
    "tier3": 0.90,
}

CLAIM_TYPES = {
    "amount": r"(?:₹|Rs\.?|INR)\s?[\d,]+(?:\.\d+)?(?:\s?(?:crore|lakh|billion|million))?",
    "percentage": r"\d+(?:\.\d+)?\s?%",
    "date": r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
    "organization": r"\b[A-Z]{2,}(?:\s+[A-Z]{2,})*\b",
}

FETCH_TIMEOUT = int(os.getenv("ALP_CLAIM_FETCH_TIMEOUT", "20"))
MAX_PAGE_BYTES = int(os.getenv("ALP_CLAIM_MAX_BYTES", "2000000"))
ENABLE_JINA = os.getenv("ALP_CLAIM_ENABLE_JINA", "1") == "1"

VERIFIED = "VERIFIED"
PARTIAL = "PARTIAL"
UNVERIFIED = "UNVERIFIED"
CONTRADICTED = "CONTRADICTED"
ERROR = "ERROR"


# --------------------------------------------------------------------------- #
# Page retrieval (separate, testable responsibility)
# --------------------------------------------------------------------------- #
def _valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url or "")
    except ValueError:
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def fetch_page(url: str) -> Optional[str]:
    """Fetch readable page text for a source URL.

    Returns the page text, or None when the URL is unusable or the fetch fails.
    Never raises and never invents content.
    """
    if not _valid_url(url):
        return None
    try:
        import requests
    except ImportError:  # pragma: no cover - environment issue
        return None

    try:
        with requests.get(
            url,
            timeout=FETCH_TIMEOUT,
            headers={"User-Agent": "alp-claim-verifier/1.0", "Accept-Language": "en-IN,en;q=0.9"},
            stream=True,
        ) as response:
            if response.status_code != 200:
                logger.warning("[Claim Verifier] fetch HTTP %s for %s", response.status_code, url)
                return None
            chunks: List[bytes] = []
            total = 0
            for chunk in response.iter_content(chunk_size=65536):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_PAGE_BYTES:
                    break
                chunks.append(chunk)
        text = b"".join(chunks).decode(response.encoding or "utf-8", errors="replace")
    except Exception as exc:  # network/timeout/ssl/decode
        logger.warning("[Claim Verifier] direct fetch failed for %s: %s", url, exc)
        text = ""

    if len(text) > 100:
        return text

    if ENABLE_JINA:
        try:
            from pipeline.llm_helper import call_jina_reader
            jina = call_jina_reader(url)
            if jina and len(jina) > 100:
                return jina
        except Exception as exc:  # pragma: no cover - optional fallback
            logger.debug("[Claim Verifier] jina fallback failed: %s", exc)
    return None


class ClaimExtractor:
    def extract_claims(self, text: str) -> List[Dict]:
        claims: List[Dict] = []

        for match in re.finditer(CLAIM_TYPES["amount"], text or "", re.IGNORECASE):
            claims.append({"claim_type": "amount", "claim_text": match.group(0),
                           "claim_value": match.group(0)})

        for match in re.finditer(CLAIM_TYPES["percentage"], text or ""):
            claims.append({"claim_type": "percentage", "claim_text": match.group(0),
                           "claim_value": match.group(0)})

        for match in re.finditer(CLAIM_TYPES["date"], text or ""):
            claims.append({"claim_type": "date", "claim_text": match.group(0),
                           "claim_value": match.group(0)})

        for match in re.finditer(CLAIM_TYPES["organization"], text or ""):
            if len(match.group(0)) > 2:
                claims.append({"claim_type": "organization", "claim_text": match.group(0),
                               "claim_value": match.group(0)})

        seen = set()
        unique_claims: List[Dict] = []
        for claim in claims:
            key = f"{claim['claim_type']}:{claim['claim_value']}"
            if key not in seen:
                seen.add(key)
                unique_claims.append(claim)
        return unique_claims


def _normalize(value: str) -> str:
    return value.replace(",", "").replace(" ", "").lower()


def _result(item: Dict, *, status: str, verified: bool, confidence: float,
            claims: Optional[List[Dict]] = None, reason: str = "") -> Dict:
    """Build the canonical result record (item fields first, verdict last)."""
    claim_details = claims or []
    verified_count = sum(1 for c in claim_details if c.get("verified"))
    return {
        **item,
        "event_id": item.get("event_id", ""),
        "headline_en": item.get("headline_en") or item.get("title", ""),
        "source_url": item.get("source_url") or item.get("link", ""),
        "verified": verified,
        "overall_confidence": round(confidence, 4),
        "claims_verified": verified_count,
        "claims_total": len(claim_details),
        "claim_details": claim_details,
        "verification_status": status,
        "reason": reason,
    }


class ClaimVerifier:
    def __init__(self, fetcher: Optional[Callable[[str], Optional[str]]] = None) -> None:
        self._fetcher = fetcher or fetch_page
        self._extractor = ClaimExtractor()
        logger.info("[Claim Verifier] Initialized")

    # -- AI adjudication (uses the real router API; injectable for tests) --- #
    def _ai_verify(self, headline: str, page_content: str,
                   tier: str) -> Optional[Tuple[str, float, str]]:
        """Return (status, confidence, reason) or None when AI is unavailable."""
        try:
            from pipeline.ai_router import is_configured, route
        except ImportError:  # pragma: no cover - environment issue
            return None
        if not is_configured():
            return None

        prompt = (
            "Decide whether the HEADLINE is supported by the ARTICLE below.\n"
            'Respond with JSON only: {"supported": true/false, "contradicted": true/false, '
            '"confidence": 0.0-1.0, "evidence": "short quote or empty"}\n\n'
            f"HEADLINE: {headline}\n\n"
            f"ARTICLE (first 2000 chars):\n{page_content[:2000]}"
        )
        response = route(
            prompt,
            task="verification",
            response_format={"type": "json_object"},
            system_prompt=(
                "You are a careful fact-checking assistant. Only mark a claim "
                "contradicted when the article explicitly disagrees with it. "
                "Missing evidence means unsupported, not false. Return JSON only."
            ),
        )
        if not response:
            return None
        match = re.search(r"\{.*\}", response, re.DOTALL)
        if not match:
            logger.warning("[Claim Verifier] AI response was not JSON")
            return None
        try:
            data = json.loads(match.group())
        except (ValueError, TypeError):
            logger.warning("[Claim Verifier] AI JSON parse failed")
            return None
        if not isinstance(data, dict):
            return None

        try:
            confidence = max(0.0, min(1.0, float(data.get("confidence", 0.5))))
        except (TypeError, ValueError):
            confidence = 0.5
        threshold = CONFIDENCE_THRESHOLDS.get(tier, 0.90)
        if data.get("contradicted") is True:
            return CONTRADICTED, confidence, "source contradicts the headline"
        if data.get("supported") is True and confidence >= threshold:
            return VERIFIED, confidence, "AI confirms headline is supported"
        return UNVERIFIED, confidence, "AI could not confirm headline support"

    # -- Public API -------------------------------------------------------- #
    def verify_news_item(self, item: Dict) -> Dict:
        headline = item.get("headline_en") or item.get("title", "") or ""
        url = item.get("source_url") or item.get("link", "") or ""
        tier = item.get("source_tier", "tier3")

        logger.info("[Claim Verifier] Verifying: %s", headline[:60])

        page_content = self._fetcher(url)
        if not page_content:
            # Fail closed — never claim verification without evidence.
            return _result(item, status=ERROR, verified=False, confidence=0.0,
                           reason="Could not access source URL")

        claims = self._extractor.extract_claims(headline)
        if not claims:
            ai = self._ai_verify(headline, page_content, tier)
            if ai is None:
                return _result(item, status=UNVERIFIED, verified=False,
                               confidence=0.0,
                               reason="No verifiable claim and AI unavailable")
            status, confidence, reason = ai
            return _result(item, status=status,
                           verified=(status == VERIFIED),
                           confidence=confidence, reason=reason)

        normalized_page = _normalize(page_content)
        claim_results: List[Dict] = []
        for claim in claims:
            kind = claim["claim_type"]
            if kind in {"amount", "percentage", "date"}:
                if _normalize(claim["claim_value"]) in normalized_page:
                    claim_results.append({
                        **claim, "verified": True, "confidence": 0.9,
                        "evidence": f"Found in article: {claim['claim_value']}",
                        "reason": "Exact match found in source",
                    })
                else:
                    claim_results.append({
                        **claim, "verified": False, "confidence": 0.2, "evidence": "",
                        "reason": f"Not found in source: {claim['claim_value']}",
                    })

        checkable = [c for c in claim_results if c["claim_type"] in {"amount", "percentage", "date"}]
        if not checkable:
            ai = self._ai_verify(headline, page_content, tier)
            if ai is None:
                return _result(item, status=UNVERIFIED, verified=False, confidence=0.0,
                               claims=claim_results,
                               reason="No checkable numeric claim and AI unavailable")
            status, confidence, reason = ai
            return _result(item, status=status, verified=(status == VERIFIED),
                           confidence=confidence, claims=claim_results, reason=reason)

        verified_count = sum(1 for c in checkable if c["verified"])
        verification_ratio = verified_count / len(checkable)
        if verified_count:
            overall_confidence = 0.5 * (sum(c["confidence"] for c in checkable) / len(checkable)) \
                + 0.5 * verification_ratio
        else:
            overall_confidence = 0.2 * verification_ratio

        threshold = CONFIDENCE_THRESHOLDS.get(tier, 0.90)
        if verified_count == 0:
            # No numeric claim found — unsupported, not proven false.
            status = UNVERIFIED
        elif overall_confidence >= threshold:
            status = VERIFIED
        else:
            status = PARTIAL

        reason = f"{verified_count}/{len(checkable)} numeric claims matched in source"
        logger.info("[Claim Verifier] %s: %s", status, reason)
        return _result(item, status=status, verified=(status == VERIFIED),
                       confidence=overall_confidence, claims=claim_results, reason=reason)


_verifier_instance: Optional[ClaimVerifier] = None


def get_verifier() -> ClaimVerifier:
    global _verifier_instance
    if _verifier_instance is None:
        _verifier_instance = ClaimVerifier()
    return _verifier_instance


def verify_news_item(item: Dict) -> Dict:
    return get_verifier().verify_news_item(item)


def verify_claims(items: List[Dict], chunk_size: int = 5, delay: int = 3) -> List[Dict]:
    verifier = get_verifier()
    results: List[Dict] = []
    for i in range(0, len(items), chunk_size):
        chunk = items[i:i + chunk_size]
        for item in chunk:
            results.append(verifier.verify_news_item(item))
        if i + chunk_size < len(items) and delay:
            time.sleep(delay)
    return results
