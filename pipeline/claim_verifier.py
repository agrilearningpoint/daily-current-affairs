# -*- coding: utf-8 -*-
"""
CLAIM VERIFIER v2 — Claim-Level Fact Verification
Agri Learning Point Pipeline — Production-Ready

Features:
  ✅ Claim-level verification (not just headline match)
  ✅ Structured verification: {claim, verified, evidence, confidence}
  ✅ Numbers, dates, amounts verified separately
  ✅ Primary source required — no verification without evidence
  ✅ Fail-closed: insufficient evidence = UNVERIFIED
  ✅ Jina Reader for page access + AI Router for verification

Usage:
  from pipeline.claim_verifier import verify_claims, verify_news_item
  
  # Verify a single news item
  result = verify_news_item(item)
  
  # Verify multiple items
  results = verify_claims(items)
"""

import os, json, time, logging, re
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLDS = {
    "tier1": 0.70,
    "tier2": 0.85,
    "tier3": 0.90,
}

CLAIM_TYPES = {
    "amount": r'(?:₹|Rs\.?|INR)\s?[\d,]+(?:\.\d+)?(?:\s?(?:crore|lakh|billion|million))?',
    "percentage": r'\d+(?:\.\d+)?\s?%',
    "date": r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
    "organization": r'\b[A-Z]{2,}(?:\s+[A-Z]{2,})*\b',
}


class ClaimExtractor:
    def extract_claims(self, text: str) -> List[Dict]:
        claims = []
        
        for match in re.finditer(CLAIM_TYPES["amount"], text, re.IGNORECASE):
            claims.append({
                "claim_type": "amount",
                "claim_text": match.group(0),
                "claim_value": match.group(0),
            })
        
        for match in re.finditer(CLAIM_TYPES["percentage"], text):
            claims.append({
                "claim_type": "percentage",
                "claim_text": match.group(0),
                "claim_value": match.group(0),
            })
        
        for match in re.finditer(CLAIM_TYPES["date"], text):
            claims.append({
                "claim_type": "date",
                "claim_text": match.group(0),
                "claim_value": match.group(0),
            })
        
        for match in re.finditer(CLAIM_TYPES["organization"], text):
            if len(match.group(0)) > 2:
                claims.append({
                    "claim_type": "organization",
                    "claim_text": match.group(0),
                    "claim_value": match.group(0),
                })
        
        seen = set()
        unique_claims = []
        for claim in claims:
            key = f"{claim['claim_type']}:{claim['claim_value']}"
            if key not in seen:
                seen.add(key)
                unique_claims.append(claim)
        
        return unique_claims


class ClaimVerifier:
    def __init__(self):
        self._router = None
        self._extractor = ClaimExtractor()
        logger.info("[Claim Verifier] Initialized")
    
    def _get_router(self):
        if self._router is None:
            try:
                from pipeline.ai_router import get_router
                self._router = get_router()
            except ImportError:
                return None
        return self._router
    
    def _fetch_page_content(self, url: str) -> Optional[str]:
        router = self._get_router()
        if router is None:
            return None
        
        try:
            content = router.read_url(url)
            if content and len(content) > 100:
                return content
        except Exception as e:
            logger.warning(f"[Claim Verifier] Failed to fetch {url}: {e}")
        
        return None
    
    def verify_news_item(self, item: Dict) -> Dict:
        headline = item.get("headline_en", "")
        url = item.get("source_url", "")
        tier = item.get("source_tier", "tier3")
        event_id = item.get("event_id", "")
        
        logger.info(f"[Claim Verifier] Verifying: {headline[:60]}")
        
        page_content = self._fetch_page_content(url)
        if not page_content:
            return {
                "event_id": event_id,
                "headline_en": headline,
                "source_url": url,
                "verified": False,
                "overall_confidence": 0.0,
                "claims_verified": 0,
                "claims_total": 0,
                "claim_details": [],
                "verification_status": "UNVERIFIED",
                "reason": "Could not access source URL",
            }
        
        claims = self._extractor.extract_claims(headline)
        
        if not claims:
            return self._general_verification(item, page_content)
        
        claim_results = []
        for claim in claims:
            if claim["claim_type"] in ["amount", "percentage", "date"]:
                claim_normalized = claim["claim_value"].replace(",", "").replace(" ", "").lower()
                page_normalized = page_content.replace(",", "").replace(" ", "").lower()
                
                if claim_normalized in page_normalized:
                    claim_results.append({
                        "claim_type": claim["claim_type"],
                        "claim_text": claim["claim_text"],
                        "verified": True,
                        "confidence": 0.9,
                        "evidence": f"Found in article: {claim['claim_value']}",
                        "reason": "Exact match found in source",
                    })
                else:
                    claim_results.append({
                        "claim_type": claim["claim_type"],
                        "claim_text": claim["claim_text"],
                        "verified": False,
                        "confidence": 0.2,
                        "evidence": "",
                        "reason": f"Not found in source: {claim['claim_value']}",
                    })
        
        verified_count = sum(1 for c in claim_results if c["verified"])
        total_claims = len(claim_results)
        
        if total_claims == 0:
            overall_confidence = 0.5
        else:
            avg_confidence = sum(c["confidence"] for c in claim_results) / total_claims
            verification_ratio = verified_count / total_claims
            overall_confidence = (avg_confidence + verification_ratio) / 2
        
        threshold = CONFIDENCE_THRESHOLDS.get(tier, 0.90)
        is_verified = overall_confidence >= threshold
        
        status = "VERIFIED" if is_verified else ("PARTIAL" if verified_count > 0 else "UNVERIFIED")
        
        result = {
            "event_id": event_id,
            "headline_en": headline,
            "source_url": url,
            "verified": is_verified,
            "overall_confidence": round(overall_confidence, 2),
            "claims_verified": verified_count,
            "claims_total": total_claims,
            "claim_details": claim_results,
            "verification_status": status,
            **item,
        }
        
        logger.info(f"[Claim Verifier] {status}: {verified_count}/{total_claims} claims verified")
        
        return result
    
    def _general_verification(self, item: Dict, page_content: str) -> Dict:
        router = self._get_router()
        headline = item.get("headline_en", "")
        tier = item.get("source_tier", "tier3")
        
        if router is None:
            return {
                **item,
                "verified": False,
                "overall_confidence": 0.0,
                "verification_status": "UNVERIFIED",
            }
        
        prompt = f"""Verify if this headline is supported by the article.

HEADLINE: {headline}

ARTICLE (first 2000 chars):
{page_content[:2000]}

Respond in JSON: {{"verified": true/false, "confidence": 0.0-1.0}}"""
        
        try:
            response = router.generate(prompt, task="verification")
            json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                confidence = result.get("confidence", 0.5)
                threshold = CONFIDENCE_THRESHOLDS.get(tier, 0.90)
                is_verified = confidence >= threshold
                
                return {
                    **item,
                    "verified": is_verified,
                    "overall_confidence": confidence,
                    "verification_status": "VERIFIED" if is_verified else "UNVERIFIED",
                }
        except Exception as e:
            logger.error(f"[Claim Verifier] General verification failed: {e}")
        
        return {
            **item,
            "verified": False,
            "overall_confidence": 0.0,
            "verification_status": "UNVERIFIED",
        }


_verifier_instance = None

def get_verifier() -> ClaimVerifier:
    global _verifier_instance
    if _verifier_instance is None:
        _verifier_instance = ClaimVerifier()
    return _verifier_instance

def verify_news_item(item: Dict) -> Dict:
    return get_verifier().verify_news_item(item)

def verify_claims(items: List[Dict], chunk_size: int = 5, delay: int = 3) -> List[Dict]:
    verifier = get_verifier()
    results = []
    
    for i in range(0, len(items), chunk_size):
        chunk = items[i:i + chunk_size]
        
        for item in chunk:
            result = verifier.verify_news_item(item)
            results.append(result)
        
        if i + chunk_size < len(items):
            time.sleep(delay)
    
    return results
