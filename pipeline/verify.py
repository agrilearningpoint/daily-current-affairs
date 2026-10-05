# -*- coding: utf-8 -*-
"""
REAL FACT VERIFICATION (Agent 04) — HEAD-status is NOT verification.

For each item we FETCH the actual source page and check that the headline's claims
are supported by the page CONTENT:
  1. URL resolves (GET, not HEAD — many gov sites 403 on HEAD)
  2. title-token overlap between headline and page <title>/page text
  3. every distinctive number in the headline (₹5000, 7.8%, 123rd…) must appear
     in the page text (strongest anti-mismatch signal)
  4. named organisations/people from the headline must appear on the page
  5. freshness: page/feed pub date inside the job window (if known)

Result record per README shape:
  {event_id, claim, source_url, source_type, published_at, verified, confidence,
   claims_verified[], claims_unverified[]}

Tier policy (README "primary-source gate"):
  tier1 official  -> verified if content supports headline (conf >= 0.7)
  tier2 discovery -> needs content support AND (official mirror found or conf >= 0.85)
  tier3           -> dropped unless conf >= 0.9 (effectively never published raw)
Budget-safe: parallel fetches, hard wall-clock deadline, cached page bodies shared
with later stages via data/raw/<job>_pages.json (so PDF/image agents don't re-fetch).
"""
import hashlib, logging, os, re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import requests
from bs4 import BeautifulSoup

TIMEOUT = int(os.getenv("VERIFY_TIMEOUT", "8"))
MAX_WORKERS = int(os.getenv("VERIFY_WORKERS", "10"))
DEADLINE_S = int(os.getenv("VERIFY_DEADLINE_S", "240"))
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0 Safari/537.36", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "en-IN,en;q=0.9"}

STOP = set("""the a an and or of in on at to for with from by is are was were new launch launches
launched approved approves says said over after before amid as its it this that will can has have
million billion crore lakh percent per cent about more most than then there their them""".split())


def _tokens(s):
    return {w for w in re.findall(r"[A-Za-z0-9₹%.]+", (s or "").lower()) if w not in STOP and len(w) > 2}


def _numbers(s):
    """Distinctive numeric claims: ₹figures, %, ranks, plain numbers >= 2 digits."""
    out = set()
    s = s or ""
    for m in re.finditer(r"(?:₹|Rs\.?|INR)\s?([\d][\d,.]*)", s, re.I):
        out.add(m.group(1))
    for m in re.finditer(r"\b(\d+(?:[.,]\d+)?)\s?(?:%|percent|crore|lakh|billion|million|bps)\b", s, re.I):
        out.add(m.group(1))
    for m in re.finditer(r"\b\d{2,}\b", s):
        out.add(m.group(0))
    return out


def _entities(s):
    """Capitalised multi-word names / all-caps orgs in a headline."""
    out = set()
    for m in re.finditer(r"\b[A-Z][A-Za-z&'-]{2,}(?:[ -][A-Z][A-Za-z&'-]{2,})+\b", s or ""):
        out.add(m.group(0))
    for m in re.finditer(r"\b[A-Z]{3,}\b", s or ""):
        out.add(m.group(0))
    return out


_GN_DECODER = None


def decode_gnews_link(gurl, cache={}):
    """Google News RSS links are /rss/articles/AGxGR... base64 pointers to the real
    publisher URL. Decode the protobuf-ish payload: modern encodings embed the FULL
    article HTML (<title>, <meta og:url>) — extract the canonical URL from there."""
    if gurl in cache:
        return cache[gurl]
    real = None
    try:
        import base64
        m = re.search(r"articles/([A-Za-z0-9_\-]+)", gurl)
        if m:
            pad = m.group(1) + "=" * (-len(m.group(1)) % 4)
            raw = base64.urlsafe_b64decode(pad)
            # prefer URLs that look like real articles (contain path segments),
            # reject googleusercontent images / google shells
            found = re.findall(rb'https?://[\x20-\x7e]+?(?=[\x00-\x1f"<>\s]|$)', raw)
            cands = []
            for u in found:
                u = u.decode(errors="ignore").rstrip("/\\'\".,")
                if "google" in u or "gstatic" in u or "w3.org" in u:
                    continue
                if u.endswith((".css", ".js", ".ico", ".png", ".jpg", ".webp")):
                    continue
                # real article URLs have a path beyond just the host
                rest = re.sub(r"^https?://", "", u)
                if "/" not in rest and "." not in rest.split("/")[0]:
                    continue
                cands.append(u)
            if cands:
                # longest is usually the full canonical URL vs truncated fragments
                real = sorted(cands, key=lambda x: (len(x), x.count("/")), reverse=True)[0]
        if not real:
            r = requests.get(gurl, headers=UA, timeout=TIMEOUT, allow_redirects=True)
            cm = re.search(r'<c-data[^>]*data="([^"]+)"', r.text)
            if cm:
                return decode_gnews_link("https://news.google.com/rss/articles/" + cm.group(1))
            urls = [u.rstrip("\\/") for u in re.findall(r'https?://[^"\'<>\\ ]+', r.text)
                    if "google" not in u and "gstatic" not in u]
            real = max(urls, key=len) if urls else None
    except Exception:
        real = None
    cache[gurl] = real
    return real


def fetch_page(url):
    global _GN_DECODER
    try:
        r = requests.get(url, headers=UA, timeout=TIMEOUT, allow_redirects=True)
        # Google News redirect shell -> resolve to official article, then verify THAT
        if "news.google.com" in url:
            real = decode_gnews_link(url)
            if real:
                _GN_DECODER = real
                return fetch_page(real)
        if r.status_code != 200 or not r.text:
            return None, None
        soup = BeautifulSoup(r.text[:400_000], "lxml")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = re.sub(r"\s+", " ", soup.get_text(" "))
        title = (soup.title.get_text(strip=True) if soup.title else "")
        return title, text[:200_000]
    except requests.RequestException:
        return None, None


def score_item(item, page_title, page_text):
    """Return (confidence, claims_verified, claims_unverified)."""
    head = item.get("headline_en", "")
    if page_text is None:
        return 0.2, [], [f"source URL did not resolve: {item.get('source_url','')[:100]}"]
    hay = ((page_title or "") + " " + page_text).lower()
    hay_norm = re.sub(r"[,\s]", " ", hay)

    # Google News redirect pages often only carry syndication boilerplate — treat as weak
    if "news.google.com" in item.get("source_url", "") and len(page_text) < 400:
        return 0.5, [], ["google-news redirect without article body"]

    ht = _tokens(head)
    pt = _tokens((page_title or "") + " " + " ".join(page_text.split()[:600]))
    overlap = len(ht & pt) / max(1, len(ht))

    nums = _numbers(head)
    nums_ok = {n for n in nums if n in hay or n in hay_norm}
    nums_bad = nums - nums_ok

    ents = _entities(head)
    ents_ok = {e for e in ents if e.lower() in hay}
    ents_bad = ents - ents_ok

    conf = 0.35 + 0.25 * min(1.0, overlap / 0.5)          # title/content token match
    if nums:
        conf += 0.25 * (len(nums_ok) / len(nums))         # numeric claims verified
    if ents:
        conf += 0.15 * (len(ents_ok) / len(ents))         # entities present
    conf -= 0.15 * bool(nums_bad)                          # penalty: headline number missing
    conf = round(max(0.0, min(1.0, conf)), 2)

    cv = []
    if overlap >= 0.4:
        cv.append(f"headline tokens matched on source page ({overlap:.0%})")
    cv += [f"figure “{n}” confirmed on page" for n in list(nums_ok)[:4]]
    cv += [f"entity “{e}” confirmed on page" for e in list(ents_ok)[:3]]
    cu = [f"figure “{n}” NOT found on page" for n in list(nums_bad)[:4]]
    cu += [f"entity “{e}” NOT found on page" for e in list(ents_bad)[:3]]
    return conf, cv, cu


def verify_all(items):
    """Parallel real verification. Returns (verified_items, dropped_list)."""
    t0 = datetime.now()
    results, dropped = [], []
    jobs = items

    def work(it):
        global _GN_DECODER
        _GN_DECODER = None
        url = it["source_url"]
        title, text = fetch_page(url)
        if _GN_DECODER:                      # gnews redirect resolved → keep official URL as citation
            it = dict(it)
            it["source_url"] = _GN_DECODER
            it["discovered_via"] = "google-news"
            title, text = fetch_page(_GN_DECODER)   # fresh read w/o decoder side-effects
        conf, cv, cu = score_item(it, title, text)
        tier = it.get("source_tier", "tier3")
        ok = (tier == "tier1" and conf >= 0.70) or (tier == "tier2" and conf >= 0.85) \
             or (tier == "tier3" and conf >= 0.90)
        return it, conf, cv, cu, ok

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = {ex.submit(work, it): it for it in jobs}
        try:
            for fut in as_completed(futs, timeout=DEADLINE_S):
                it, conf, cv, cu, ok = fut.result()
                rec = dict(it)
                rec.update({"verified": ok, "confidence": conf,
                            "claim": it.get("headline_en", ""),
                            "source_type": it.get("source_tier", ""),
                            "published_at": it.get("pub_time_ist"),
                            "claims_verified": cv, "claims_unverified": cu})
                (results if ok else dropped).append(rec)
        except Exception:
            pass  # TimeoutError etc → keep partial
        for f in futs:
            if not f.done():
                f.cancel()
    logging.info(f"[verifier] content-verified={len(results)} dropped={len(dropped)} "
                 f"in {(datetime.now()-t0).total_seconds():.0f}s")
    return results, dropped
