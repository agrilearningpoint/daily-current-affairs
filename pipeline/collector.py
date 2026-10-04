# -*- coding: utf-8 -*-
"""
NEWS COLLECTOR LIBRARY — real fetch/parse/normalize for the Collector Agent.
Adapters: RSS-first (feedparser), HTML link-fallback (BeautifulSoup) for PIB/gov sites.
Every item gets: event_id, headline_en, pub_time_ist, source_name, source_url,
source_tier, category, raw_facts, image_url, needs_primary_verification.
Respects timeout 10s, retry 2x, never invents facts (only extracts what page says).
"""
import hashlib, logging, os, re, time
from datetime import datetime, timedelta

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dtparser
import pytz

from config.sources import TIER_1_SOURCES, TIER_2_DISCOVERY

TZ = pytz.timezone("Asia/Kolkata")
UA = {"User-Agent": "AgriLearningPointBot/1.0 (educational current-affairs collector; contact: agrilearningpoint)"}
TIMEOUT = 10
RETRY = 2

CATEGORY_KEYWORDS = {
    "Agriculture": ["agriculture", "farm", "kisan", "crop", "msp", "icar", "iari", "horticulture",
                    "apeda", "nhb", "fisheries", "dairy", "livestock", "monsoon", "soil", "seed",
                    "irrigation", "agri", "farmer", "shrimp", "cattle", "buffalo", "food processing"],
    "Banking & Finance": ["rbi", "bank", "nabard", "sebi", "upi", "npci", "loan", "credit", "repo",
                          "monetary", "insurance", "irdai", "pfrda", "ifsc", "deposit", "nbfc", "currency"],
    "Economy": ["gdp", "inflation", "budget", "economic", "mospi", "trade", "export", "import",
                "gst", "finance", "survey", "forex", "deficit", "growth", "industry", "ppi", "cad"],
    "Government Schemes": ["scheme", "yojana", "mission", "initiative", "cabinet", "policy", "mou",
                           "launched", "approved", "gazette", "notification", "programme", "program"],
    "National": ["india", "delhi", "president", "pm ", "prime minister", "parliament", "supreme court",
                 "election", "eci", "defence", "isro", "drdo", "appointment", "award", "padma",
                 "republic", "independence", "bihar", "state"],
    "International": ["un ", "united nations", "fao", "world bank", "imf", "wto", "who", "unesco",
                      "unep", "undp", "ilo", "climate", "global", "international", "summit", "bilateral",
                      "mea", "china", "pakistan", "us ", "russia", "asian games", "olympic"],
    "Science & Technology": ["scient", "research", "technology", "space", "satellite", "ai ",
                             "quantum", "vaccine", "drug", "medical", "health", "hospital", "dst",
                             "innovation", "startup", "digital"],
    "Environment": ["environment", "forest", "climate change", "pollution", "wildlife", "carbon",
                    "renewable", "solar", "wind", "biodiversity", "moefcc", "cpcb", "emission"],
    "Sports": ["sports", "cricket", "hockey", "khel", "match", "tournament", "medal", "gold",
               "olympics", "asian games", "federation"],
}


def _hash(*parts):
    return hashlib.sha1("||".join(parts).encode("utf-8", "ignore")).hexdigest()[:16]


def infer_category(text):
    t = " " + (text or "").lower() + " "
    scores = {}
    for cat, kws in CATEGORY_KEYWORDS.items():
        s = sum(1 for k in kws if k in t)
        if s:
            scores[cat] = s
    if not scores:
        return "National"
    return max(scores, key=scores.get)


def to_ist(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    return dt.astimezone(TZ)


def parse_dt(raw):
    if not raw:
        return None
    try:
        d = dtparser.parse(str(raw))
        return to_ist(d)
    except (ValueError, OverflowError, TypeError):
        return None


def fetch(url):
    """GET with retry 2x and 10s timeout. Returns (status_code, text) or (None, None)."""
    for attempt in range(RETRY + 1):
        try:
            r = requests.get(url, headers=UA, timeout=TIMEOUT)
            if r.status_code == 200 and r.text:
                return 200, r.text
            if r.status_code in (403, 429):
                return r.status_code, None
        except requests.RequestException:
            pass
        time.sleep(1 + attempt)
    return None, None


def rss_items(source, url, tier, role=None):
    out, status, body = [], None, None
    # try declared feed first, then common paths
    candidates = []
    if url.rstrip("/").endswith(".xml") or "/rss" in url or "/feed" in url:
        candidates = [url]
    else:
        base = url.rstrip("/")
        candidates = [base + "/rss", base + "/feed", base + "/en/rss", base + "/rss.xml", base + "/feed.xml"]
    for cand in candidates:
        status, body = fetch(cand)
        if status == 200:
            break
    if status != 200:
        return out
    try:
        feed = feedparser.parse(body)
    except Exception:
        return out
    for e in feed.entries[:40]:
        title = (e.get("title") or "").strip()
        link = (e.get("link") or "").strip()
        if not title or not link:
            continue
        published = parse_dt(e.get("published") or e.get("updated"))
        summary = BeautifulSoup(e.get("summary", ""), "lxml").get_text(" ", strip=True)[:600]
        img = ""
        if e.get("media_thumbnail"):
            img = e["media_thumbnail"][0].get("url", "")
        elif e.get("enclosures"):
            img = next((x.href for x in e.enclosures if "image" in (x.type or "")), "")
        out.append(make_item(title, link, source, tier, published, summary, img, role))
    return out


def html_items(source, url, tier, role=None, link_pattern=r'href=["\']([^"\']*(?:release|news|press|pr-|announcement|update|media|post)[^"\']*)["\']', limit=25):
    """Fallback: scrape announcement/news links from an official listing page."""
    status, body = fetch(url)
    if status != 200:
        return []
    soup = BeautifulSoup(body, "lxml")
    out, seen = [], set()
    for m in re.finditer(link_pattern, str(soup), re.I):
        href = m.group(1)
        if href.startswith("//"):
            href = "https:" + href
        elif href.startswith("/"):
            href = url.rstrip("/") + href
        elif not href.startswith("http"):
            continue
        if href in seen:
            continue
        seen.add(href)
        # anchor text near href
        a = soup.find("a", href=re.escape(m.group(1)))
        title = a.get_text(" ", strip=True) if a else ""
        title = re.sub(r"\s+", " ", title)[:300]
        if len(title) < 25:
            continue
        out.append(make_item(title, href, source, tier, None, "", "", role))
        if len(out) >= limit:
            break
    return out


def make_item(title, link, source, tier, published, summary, img, role=None):
    eid = _hash(re.sub(r"\W+", " ", title.lower()).strip(), source.get("name", ""))
    return {
        "event_id": eid,
        "headline_en": title,
        "pub_time_ist": published.isoformat() if published else None,
        "source_name": source.get("name", ""),
        "source_url": link,
        "source_tier": tier,
        "category": infer_category(title + " " + summary),
        "raw_facts": summary or title,
        "image_url": img,
        "needs_primary_verification": tier != "tier1",
        "discovery_role": role or ("primary" if tier == "tier1" else "discovery"),
        "collected_at": datetime.now(TZ).isoformat(),
    }


def collect_window(job_type, job_date):
    """Time window per README: daily=last 24h, weekly=Mon-Sun, monthly=full month."""
    day = datetime.strptime(job_date, "%Y-%m-%d").replace(tzinfo=TZ)
    end = day.replace(hour=18, minute=0)  # 06:00 IST run covers up to ~18:00 buffer? use 24h window ending at run
    if job_type == "daily":
        start = end - timedelta(hours=24)
    elif job_type == "weekly":
        start = (day - timedelta(days=6)).replace(hour=0)
        end = day.replace(hour=23, minute=59)
    else:  # monthly
        start = day.replace(day=1, hour=0)
        end = day.replace(hour=23, minute=59)
    return start, end


def in_window(item, start, end):
    if not item.get("pub_time_ist"):
        return True  # keep undated items; verifier/dedup handle freshness
    try:
        d = datetime.fromisoformat(item["pub_time_ist"])
    except ValueError:
        return True
    return start <= d <= end


def collect_all(max_items=140):
    """Collect from Tier-1 (all groups) then Tier-2 discovery. Returns list of raw items."""
    items, errors = [], []
    for group, sources in TIER_1_SOURCES.items():
        for src in sources:
            url = src.get("url", "")
            if not url.startswith("http"):
                continue
            got = rss_items(src, url, "tier1")
            if not got:
                got = html_items(src, url, "tier1")
            for it in got:
                it["group"] = group
            items.extend(got)
            if not got:
                errors.append(f"{src['name']}: no items fetched from {url}")
            if len(items) >= max_items * 2:
                break
    for src in TIER_2_DISCOVERY:
        # Google News site-search RSS as discovery proxy (Tier-2 headlines only, must verify via Tier-1)
        q = requests.utils.quote(f'site:{src["url"].replace("https://www.","").replace("https://","")} current affairs')
        got = rss_items(src, f"https://news.google.com/rss/search?q={q}", "tier2", role="discovery")
        items.extend(got[:15])
    # de-duplicate identical URLs, cap
    uniq, seen = [], set()
    for it in items:
        if it["source_url"] in seen:
            continue
        seen.add(it["source_url"])
        uniq.append(it)
    return uniq[:max_items], errors
