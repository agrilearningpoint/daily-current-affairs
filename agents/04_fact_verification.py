# -*- coding: utf-8 -*-
"""FACT VERIFICATION AGENT v2 — Jina Reader + AI Router — FIXES Stage 04 failure"""
import re, json, logging

COMMAND = "Verify every news item against its primary source."
MASTER_RULE = "Student Value First. Accuracy Before Speed. Quality Before Quantity."

class Agent:
    def __init__(self, job_id, job_type, context):
        self.job_id = job_id
        self.job_type = job_type
        self.context = context
        self.name = "FACT VERIFICATION AGENT v2"

    def run(self):
        from pipeline.state import RAW_DIR, VERIFIED_DIR, data_path, read_json, write_json_atomic
        raw = read_json(data_path(RAW_DIR, self.job_id), {"items": []})["items"]
        items = sorted(raw, key=lambda x: (x.get("source_tier") != "tier1",
                     -(len(x.get("headline_en") or ""))))[:120]
        logging.info(f"[{self.name}] Processing {len(items)} items...")
        try:
            from pipeline.ai_router import get_router, chunked
            router = get_router()
            def verify_chunk(chunk):
                return [self._verify_ai(router, item) for item in chunk]
            all_results = chunked(items, verify_chunk, chunk_size=5, delay=3)
        except Exception as e:
            logging.warning(f"[{self.name}] AI Router unavailable ({e}), fallback to HTTP")
            all_results = [self._verify_http(item) for item in items]
        verified = [v for v in all_results if v and v.get("verified")]
        dropped = [v for v in all_results if v and not v.get("verified")]
        logging.info(f"[{self.name}] verified={len(verified)} dropped={len(dropped)}")
        min_verified = 5 if self.job_type == "daily" else (8 if self.job_type == "weekly" else 10)
        if len(verified) < min_verified:
            self.context["stage_failed"] = f"only {len(verified)} verified (min {min_verified})"
            raise RuntimeError(self.context["stage_failed"])
        write_json_atomic(data_path(VERIFIED_DIR, self.job_id), {"items": verified, "dropped": len(dropped)})
        return self.context

    def _verify_ai(self, router, item):
        url = item.get("source_url", "")
        headline = item.get("headline_en", "")
        tier = item.get("source_tier", "tier3")
        page_content = ""
        try:
            page_content = router.read_url(url)
        except Exception as e:
            logging.warning(f"Jina failed for {url}: {e}")
            page_content = self._fetch_direct(url)
        if not page_content or len(page_content) < 100:
            return {**item, "verified": False, "confidence": 0.2,
                    "claims_unverified": ["URL not accessible"]}
        prompt = f"""Verify if this headline is supported by the article.

HEADLINE: {headline}

ARTICLE (first 3000 chars):
{page_content[:3000]}

Respond ONLY in JSON: {{"verified": true/false, "confidence": 0.0-1.0, "claims_verified": [], "claims_unverified": [], "reason": "brief"}}"""
        try:
            response = router.generate(prompt, task="verification")
            json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = {"verified": False, "confidence": 0.5, "claims_verified": [], "claims_unverified": ["Parse failed"]}
        except Exception as e:
            result = {"verified": False, "confidence": 0.4, "claims_unverified": [str(e)[:100]]}
        threshold = {"tier1": 0.70, "tier2": 0.85, "tier3": 0.90}.get(tier, 0.90)
        return {
            **item, "verified": result.get("confidence", 0) >= threshold,
            "confidence": result.get("confidence", 0),
            "claims_verified": result.get("claims_verified", []),
            "claims_unverified": result.get("claims_unverified", []),
            "source_url": url, "source_type": tier,
            "published_at": item.get("pub_time_ist"), "claim": headline,
        }

    def _verify_http(self, item):
        import requests
        url = item.get("source_url", "")
        tier = item.get("source_tier", "tier3")
        try:
            r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=True)
            if r.status_code != 200:
                return {**item, "verified": False, "confidence": 0.2}
            from pipeline.verify import score_item
            title_match = re.search(r'<title[^>]*>([^<]+)</title>', r.text[:5000], re.I)
            title = title_match.group(1) if title_match else ""
            conf, cv, cu = score_item(item, title, r.text[:200000])
            threshold = {"tier1": 0.70, "tier2": 0.85, "tier3": 0.90}.get(tier, 0.90)
            return {**item, "verified": conf >= threshold, "confidence": conf,
                    "claims_verified": cv, "claims_unverified": cu,
                    "source_url": url, "source_type": tier,
                    "published_at": item.get("pub_time_ist"), "claim": item.get("headline_en", "")}
        except Exception as e:
            return {**item, "verified": False, "confidence": 0.1, "claims_unverified": [str(e)[:100]]}

    def _fetch_direct(self, url):
        import requests
        try:
            r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=True)
            if r.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(r.text[:400000], "lxml")
                for tag in soup(["script", "style", "noscript"]):
                    tag.decompose()
                return soup.get_text(" ", strip=True)[:50000]
        except Exception:
            pass
        return ""

    def verify(self):
        return not self.context.get("stage_failed")
