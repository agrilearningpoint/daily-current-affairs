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
try:
    from config.feeds import VERIFIED_RSS, GOOGLE_NEWS_SITES, gnews_url
except Exception:
    VERIFIED_RSS, GOOGLE_NEWS_SITES = [], {}
    def gnews_url(d): return ""

TZ = pytz.timezone("Asia/Kolkata")
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
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
    out = []
    # try declared feed first, then common paths
    candidates = []
    if url.rstrip("/").endswith(".xml") or "/rss" in url or "/feed" in url or "news.google.com" in url:
        candidates = [url]
    else:
        base = url.rstrip("/")
        candidates = [base + "/rss", base + "/feed", base + "/en/rss", base + "/rss.xml", base + "/feed.xml"]
    status, body = None, None
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


def _discover_one(src, tier):
    """Google News site-search RSS discovery for one source dict."""
    host = re.sub(r"^https?://(www\.)?", "", src.get("url", "")).split("/")[0]
    got = rss_items(src, gnews_url(host), tier, role="discovery")
    return got[:15]


def _parallel(items_iter, fn, deadline_left, cap_each=None):
    """Run fn(x) for each x in items_iter in parallel until deadline. Returns list of results."""
    results, tasks = [], list(items_iter)
    if not tasks:
        return results
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(tasks))) as ex:
        futs = {ex.submit(fn, t): t for t in tasks}
        try:
            for fut in as_completed(futs, timeout=max(15, deadline_left)):
                try:
                    r = fut.result()
                    results.extend(r if isinstance(r, list) else [r])
                except Exception:
                    pass
        except TimeoutError:
            logging.warning("[collector] deadline reached; keeping partial results")
        for fut in futs:
            if not fut.done():
                fut.cancel()
    return results


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


def collect_all(max_items=140):
    """Collect from Tier-1 (all groups) then Tier-2 discovery. Returns list of raw items.

    GitHub-Actions-safe design:
      * sources fetched in PARALLEL (ThreadPoolExecutor, MAX_WORKERS)
      * hard wall-clock deadline COLLECT_DEADLINE_S — on expiry we keep what we have
      * if fewer than MIN_ITEMS survive, raise so the pipeline FAILS LOUD
        instead of silently continuing with an empty edition.
    """
    t0 = time.monotonic()
    return _collect_all_inner(t0, max_items)


def _gnews_source(src, tier, cap=25):
    """Google News site-search RSS for a domain — verified working route for
    bot-blocked / SSL-broken gov sites (PIB, RBI, FAO, IMF, DARE, CACP ...)."""
    host = re.sub(r"^https?://(www\.)?", "", src.get("url", "")).split("/")[0]
    got = rss_items(src, gnews_url(host), tier, role="primary-via-gnews")
    return got[:cap]


def _collect_all_inner(t0, max_items):
    def _collect_one(group, src):
        url = src.get("url", "")
        if not url.startswith("http"):
            return group, src, [], ""
        host = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
        got = []
        # 1) declared verified feed (config/sources.py "rss" key) — live-tested route
        if src.get("rss"):
            got = rss_items(src, src["rss"], "tier1")
        # 2) native RSS discovery on the official site
        if not got:
            got = rss_items(src, url, "tier1")
        # 3) HTML listing scrape of the official site
        if not got:
            got = html_items(src, url, "tier1")
        # 4) Google News site-search fallback for known-blocked domains
        if not got and GOOGLE_NEWS_SITES and host in GOOGLE_NEWS_SITES and GOOGLE_NEWS_SITES[host] == "tier1":
            got = _gnews_source(src, "tier1")
        for it in got:
            it["group"] = group
        err = "" if got else f"{src['name']}: no items fetched from {url}"
        return group, src, got, err

    tasks = []
    for group, sources in TIER_1_SOURCES.items():
        for src in sources:
            tasks.append((group, src))
    tasks.sort(key=lambda t: -t[1].get("priority", 0))  # priority-100 sources first

    items, errors = [], []
    # STAGE 0: verified native RSS feeds first (fastest, most reliable) — parallel
    def _vf(x):
        name, furl, ftier, fcat = x
        got = rss_items({"name": name}, furl, ftier)
        for it in got:
            it["group"] = "verified_feed"
        return got
    items.extend(_parallel(VERIFIED_RSS, _vf, COLLECT_DEADLINE_S * 0.35))

    # STAGE 1: Tier-1 official sites (declared feed / native RSS / HTML / gnews fallback)
    # — ONE shared pool so slow sources can never block fast ones (8 workers).
    results = _parallel(tasks, lambda g_s: _collect_one(*g_s),
                        COLLECT_DEADLINE_S - (time.monotonic() - t0) - 45)
    done_tasks = len(results)
    for res in results:
        try:
            _, _, got, err = res
            items.extend(got)
            if err:
                errors.append(err)
        except Exception:
            pass
    if done_tasks < len(tasks):
        logging.warning(f"[collector] {len(tasks)-done_tasks} tier-1 tasks unfinished at deadline")

    # STAGE 2: Tier-2 discovery via Google News site-search RSS — parallel, only if budget left
    if time.monotonic() - t0 < COLLECT_DEADLINE_S * 0.75:
        disc = _parallel(TIER_2_DISCOVERY, lambda s: _discover_one(s, "tier2"),
                         COLLECT_DEADLINE_S - (time.monotonic() - t0) - 20)
        items.extend(disc)

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
