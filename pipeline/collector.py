# -*- coding: utf-8 -*-
"""
NEWS COLLECTOR LIBRARY — real fetch/parse/normalize for the Collector Agent.
Adapters: RSS-first (feedparser), HTML link-fallback (BeautifulSoup) for PIB/gov sites.
Every item gets: event_id, headline_en, pub_time_ist, source_name, source_url,
source_tier, category, raw_facts, image_url, needs_primary_verification.
Respects timeout 10s, retry 2x, never invents facts (only extracts what page says).
"""
import hashlib, logging, os, re, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

import feedparser
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dtparser
import pytz

from config.sources import TIER_1_SOURCES, TIER_2_DISCOVERY

TZ = pytz.timezone("Asia/Kolkata")
# ADOPTED from india-policy-intelligence/app/http.py — fixes 403 (Akamai blocks datacenter UAs)
import ssl
try:
    import certifi
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
    SSL_FALLBACK = ssl.create_default_context()
except ImportError:
    import ssl as _ssl
    SSL_CTX = _ssl.create_default_context()
    SSL_FALLBACK = SSL_CTX
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/rss+xml,application/atom+xml;q=0.8,*/*;q=0.7",
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept-Encoding": "gzip",
}
UA = HEADERS  # keep old name for compat
# GitHub Actions budget: whole pipeline must finish well inside runner limits.
# Collector is the heaviest network stage -> tight timeouts + parallel fetching.
TIMEOUT = 6
RETRY = 1            # 1 retry only (was 2) — dead sources shouldn't eat the budget
COLLECT_DEADLINE_S = int(os.getenv("COLLECT_DEADLINE_S", "300"))   # hard cap for collect_all
MAX_WORKERS = 8      # parallel source fetches

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


def fetch(url, timeout=TIMEOUT):
    # ADOPTED from india-policy HttpClient.get + safe_url + certifi fallback
    try:
        if not url.startswith(("http://", "https://")):
            return None, None
        from urllib.parse import quote as _q
        url = _q(url.strip(), safe=":/?&=#%+@;,[]!$'()*")
        # try with HEADERS (browser UA) — fixes PIB/RBI 403
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout, verify=True)
        except requests.exceptions.SSLError as e:
            if "CERTIFICATE_VERIFY_FAILED" in str(e):
                r = requests.get(url, headers=HEADERS, timeout=timeout, verify=False)
            else:
                raise
        if r.status_code == 200:
            ctype = r.headers.get("Content-Type","")
            body = r.content
            if "gzip" in r.headers.get("Content-Encoding","").lower():
                import gzip
                try: body = gzip.decompress(body)
                except: pass
            # limit 12MB like india-policy
            if len(body) > 12_000_000:
                body = body[:12_000_000]
            return 200, body
        return r.status_code, None
    except requests.RequestException:
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
    """Time windows (production-correct):
      daily   -> PREVIOUS calendar day in IST (run on 04 Oct 06:00 => 03 Oct 00:00 → 04 Oct 06:00)
                 Never includes the future part of the edition date.
      weekly  -> Monday 00:00 → run time (Sunday morning best-of-week)
      monthly -> runs on the 1st: the PREVIOUS COMPLETE calendar month
                 (01 Oct run => 01 Sep 00:00 → 30 Sep 23:59). Mid-month runs => current month-to-date.
    """
    day = datetime.strptime(job_date, "%Y-%m-%d").replace(tzinfo=TZ)
    now = datetime.now(TZ)
    if job_type == "daily":
        start = (day - timedelta(days=1)).replace(hour=0, minute=0, second=0)
        end = min(day.replace(hour=6, minute=0, second=0), now) if day.date() == now.date() \
              else day.replace(hour=23, minute=59, second=59)
    elif job_type == "weekly":
        # walk back to Monday of the week containing job_date
        monday = day - timedelta(days=day.weekday())
        start = monday.replace(hour=0, minute=0, second=0)
        end = day.replace(hour=23, minute=59, second=59)
    else:  # monthly — previous complete month when running on the 1st
        if day.day == 1:
            last_day = day - timedelta(days=1)          # e.g. 30 Sep for 01 Oct
            start = last_day.replace(day=1, hour=0, minute=0, second=0)
            end = last_day.replace(hour=23, minute=59, second=59)
        else:
            start = day.replace(day=1, hour=0, minute=0, second=0)
            end = day.replace(hour=23, minute=59, second=59)
    return start, end


def in_window(item, start, end):
    if not item.get("pub_time_ist"):
        return True  # keep undated items; verifier/dedup handle freshness
    try:
        d = datetime.fromisoformat(item["pub_time_ist"])
    except ValueError:
        return True
    return start <= d <= end



# ── ADOPTED: GK-Parchi GNews 6 categories + scrape Google News RSS search (Tier-3 fallback) ──
# Only used if primary 65 return <8 fresh items — never trusted alone (tier3 confidence 0.6)
GNEWS_CATEGORIES = ["general","nation","world","business","sports","science"]
def fetch_gnews_items(api_key, max_items=60):
    out=[]
    if not api_key: return out
    for cat in GNEWS_CATEGORIES:
        try:
            url = f"https://gnews.io/api/v4/top-headlines?category={cat}&lang=en&country=in&max=10&apikey={api_key}"
            import requests as _rq
            r = _rq.get(url, timeout=15, headers=HEADERS)
            if r.status_code==200:
                for art in r.json().get("articles",[]):
                    title=(art.get("title") or "").strip()
                    link=(art.get("url") or "").strip()
                    if len(title)<15: continue
                    out.append(make_item(title, link, "GNews-"+cat, "tier3", None, (art.get("description") or "")[:500], "", role="aggregator"))
        except: pass
    return out[:max_items]

def fetch_google_news_rss_search(max_items=30):
    # scrape pattern: news.google.com/rss/search?q=site:pib.gov.in+OR+site:rbi.org.in...&hl=en-IN&gl=IN&ceid=IN:en
    # Bypasses direct PIB 403 by discovering official URLs via Google News index
    try:
        query = "site:pib.gov.in OR site:rbi.org.in OR site:nabard.org OR site:icar.org.in OR site:sebi.gov.in"
        from urllib.parse import quote_plus as _qp
        url = f"https://news.google.com/rss/search?q={_qp(query)}&hl=en-IN&gl=IN&ceid=IN:en"
        status, body = fetch(url)
        if status != 200 or not body: return []
        import feedparser as _fp
        feed = _fp.parse(body)
        out=[]
        for e in feed.entries[:max_items]:
            title=(e.get("title") or "").strip()
            link=(e.get("link") or "").strip()
            if len(title)<15: continue
            out.append(make_item(title, link, "GoogleNews-RSS", "tier2", None, (e.get("summary") or "")[:500], "", role="discovery"))
        return out
    except: return []


def collect_all(max_items=140):
    """Collect from Tier-1 (all groups) then Tier-2 discovery. Returns list of raw items.

    GitHub-Actions-safe design:
      * sources fetched in PARALLEL (ThreadPoolExecutor, MAX_WORKERS)
      * hard wall-clock deadline COLLECT_DEADLINE_S — on expiry we keep what we have
      * if fewer than MIN_ITEMS survive, raise so the pipeline FAILS LOUD
        instead of silently continuing with an empty edition.
    """
    t0 = time.monotonic()

    def _collect_one(group, src):
        url = src.get("url", "")
        if not url.startswith("http"):
            return group, src, [], ""
        got = rss_items(src, url, "tier1")
        if not got:
            got = html_items(src, url, "tier1")
        for it in got:
            it["group"] = group
        err = "" if got else f"{src['name']}: no items fetched from {url}"
        return group, src, got, err

    tasks = []
    for group, sources in TIER_1_SOURCES.items():
        for src in sources:
            tasks.append((group, src))

    items, errors = [], []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = {ex.submit(_collect_one, g, s): (g, s) for g, s in tasks}
        try:
            for fut in as_completed(futs, timeout=max(30, COLLECT_DEADLINE_S - (time.monotonic() - t0))):
                _, _, got, err = fut.result()
                items.extend(got)
                if err:
                    errors.append(err)
        except TimeoutError:
            logging.warning("[collector] deadline reached during Tier-1; keeping partial results")
        for fut in futs:
            if not fut.done():
                fut.cancel()

    # Tier-2 discovery (Google News site-search RSS) — also parallel, only if budget left
    if time.monotonic() - t0 < COLLECT_DEADLINE_S * 0.6:
        def _discover(src):
            host = src["url"].replace("https://www.", "").replace("https://", "")
            q = requests.utils.quote(f"site:{host} current affairs")
            got = rss_items(src, f"https://news.google.com/rss/search?q={q}", "tier2", role="discovery")
            return got[:15]
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futs = [ex.submit(_discover, src) for src in TIER_2_DISCOVERY]
            try:
                for fut in as_completed(futs, timeout=max(20, COLLECT_DEADLINE_S - (time.monotonic() - t0))):
                    try:
                        items.extend(fut.result())
                    except Exception:
                        pass
            except TimeoutError:
                logging.warning("[collector] deadline reached during Tier-2 discovery")
            for fut in futs:
                if not fut.done():
                    fut.cancel()

    # de-duplicate identical URLs, cap
    uniq, seen = [], set()
    for it in items:
        if it["source_url"] in seen:
            continue
        seen.add(it["source_url"])
        uniq.append(it)

    elapsed = time.monotonic() - t0
    logging.info(f"[collector] finished in {elapsed:.1f}s: {len(uniq)} unique items from {len(tasks)} tier-1 sources ({len(errors)} dead)")

    MIN_ITEMS = int(os.getenv("COLLECT_MIN_ITEMS", "10"))
    if len(uniq) < MIN_ITEMS:
        raise RuntimeError(
            f"COLLECTION FAILED: only {len(uniq)} items collected (<{MIN_ITEMS}). "
            f"Pipeline refuses to continue with an empty edition. Dead sources: {errors[:10]}"
        )
    return uniq[:max_items], errors
