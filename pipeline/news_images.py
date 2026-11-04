# -*- coding: utf-8 -*-
"""
News photos for the daily PDF ("News in Pictures / चित्रों में खबरें").

For the most important final stories this module finds a real news photo
(the feed's media/enclosure image first, then the article page's og:image /
twitter:image), validates it, compresses it and stores it under
``data/images/<job_id>/`` so the PDF renderer can embed it.

Design rules
------------
* Fail soft: every error is logged and skipped.  A missing photo must never
  fail a stage or the edition.
* Validate before use: real ``image/*`` content type, decodes with Pillow,
  at least ``ALP_IMAGE_MIN_WIDTH`` px wide (default 400), sensible aspect
  ratio, URL does not look like a logo / icon / placeholder, download size
  capped (``ALP_IMAGE_MAX_BYTES``, default 6 MB).
* Keep the PDF small: RGB JPEG, max width 1000 px (``ALP_IMAGE_MAX_WIDTH``),
  quality 75 (``ALP_IMAGE_JPEG_QUALITY``), progressive + optimised.
* Sources, in order: the feed image, the source article's og:image /
  twitter:image (Google News redirect links are resolved to the publisher URL
  first), PIB release photos (pib.gov.in ``WriteReadData/userfiles/image``,
  credit "Photo: PIB"), then a Wikimedia Commons search for the story's main
  entity (free licences only; author + licence kept in the credit line).
  Relevance: an image comes from the story's own source page, or its Commons
  file title contains every word of one of the story's entities.  Never an
  unrelated stock image.
* Time-boxed: 8 s per fetch (``ALP_IMAGE_FETCH_TIMEOUT``) and ~90 s for the
  whole photo step (``ALP_IMAGE_TOTAL_BUDGET``); when the budget is spent the
  edition simply carries fewer photos.
* No network in tests / dry runs: ``ALP_DISABLE_NETWORK=1`` or ``DRY_RUN=1``
  disables fetching; callers (and tests) can also inject ``fetch``.
"""
from __future__ import annotations

import hashlib
import io
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple
from urllib.parse import quote, urljoin, urlparse

logger = logging.getLogger(__name__)

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# URLs that are almost always logos, icons, trackers or placeholders.
BAD_URL_RE = re.compile(
    r"logo|icon|favicon|sprite|placeholder|default[-_]?(?:image|img|thumb|og)|no[-_]?image|"
    r"blank|spacer|pixel|1x1|avatar|badge|banner[-_]?ad|/ads?/|doubleclick|gravatar|"
    r"share[-_]?image[-_]?default|fallback|watermark|emblem",
    re.I,
)
# Hosts whose og:image is a generic brand card, never a news photo.
BAD_HOSTS = ("news.google.com", "gstatic.com", "google.com", "googleusercontent.com/proxy",
             "facebook.com", "twitter.com", "x.com")

OG_PATTERNS = [
    re.compile(r'<meta[^>]+(?:property|name)=["\'](?:og:image(?::secure_url)?|twitter:image(?::src)?)["\'][^>]*?content=["\']([^"\']+)["\']', re.I),
    re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*?(?:property|name)=["\'](?:og:image(?::secure_url)?|twitter:image(?::src)?)["\']', re.I),
    re.compile(r'<link[^>]+rel=["\']image_src["\'][^>]*?href=["\']([^"\']+)["\']', re.I),
]


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def network_disabled() -> bool:
    return os.getenv("ALP_DISABLE_NETWORK", "0") == "1" or os.getenv("DRY_RUN", "0") == "1"


def images_enabled() -> bool:
    return os.getenv("ALP_PDF_IMAGES", "1").strip().lower() not in ("0", "off", "false", "no")


def plausible_image_url(url: str) -> bool:
    """Cheap URL-level screen: http(s), not a logo/icon/placeholder, not a brand-card host."""
    if not url or not isinstance(url, str):
        return False
    url = url.strip()
    if not url.lower().startswith(("http://", "https://")):
        return False
    low = url.lower()
    if any(h in low for h in BAD_HOSTS):
        return False
    path = urlparse(low).path
    if path.endswith((".svg", ".gif", ".ico")):
        return False
    return not BAD_URL_RE.search(path + "?" + urlparse(low).query)


def extract_og_image(html_text: str, base_url: str = "") -> str:
    """First og:image / twitter:image / image_src URL in an HTML document ('' if none)."""
    if not html_text:
        return ""
    head = html_text[:400_000]
    for pat in OG_PATTERNS:
        for m in pat.finditer(head):
            cand = (m.group(1) or "").strip().replace("&amp;", "&")
            if not cand:
                continue
            if cand.startswith("//"):
                cand = "https:" + cand
            elif base_url and not cand.lower().startswith("http"):
                cand = urljoin(base_url, cand)
            if plausible_image_url(cand):
                return cand
    return ""


def _default_fetch(url: str, timeout: float, max_bytes: int) -> Tuple[int, str, bytes]:
    """GET with a byte cap. Returns (status, content_type, body)."""
    import requests
    with requests.get(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
                      timeout=timeout, stream=True, allow_redirects=True) as resp:
        ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        declared = resp.headers.get("Content-Length")
        if declared and declared.isdigit() and int(declared) > max_bytes:
            return resp.status_code, ctype, b""
        buf = bytearray()
        for chunk in resp.iter_content(64 * 1024):
            buf.extend(chunk)
            if len(buf) > max_bytes:
                return resp.status_code, ctype, b""
        return resp.status_code, ctype, bytes(buf)


def process_image_bytes(data: bytes, dest: Path, *, min_width: Optional[int] = None,
                        max_width: Optional[int] = None, quality: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Validate + resize + JPEG-compress image bytes into ``dest`` (atomic). None when rejected."""
    from PIL import Image, ImageOps
    min_width = min_width or _env_int("ALP_IMAGE_MIN_WIDTH", 400)
    max_width = max_width or _env_int("ALP_IMAGE_MAX_WIDTH", 1000)
    quality = quality or _env_int("ALP_IMAGE_JPEG_QUALITY", 75)
    if not data:
        return None
    try:
        with Image.open(io.BytesIO(data)) as probe:
            probe.verify()
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img)
        img.load()
    except Exception as exc:
        logger.info("[images] undecodable image: %s", exc)
        return None
    w, h = img.size
    if w < min_width or h < 160:
        logger.info("[images] too small: %dx%d", w, h)
        return None
    ratio = w / float(h)
    if not (0.6 <= ratio <= 2.6):
        logger.info("[images] odd aspect ratio %.2f (banner/strip?)", ratio)
        return None
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")
    # Near-uniform images are placeholders / blank cards, not photos.
    try:
        from PIL import ImageStat
        stat = ImageStat.Stat(img.resize((64, 64)))
        if max(stat.stddev) < 12:
            logger.info("[images] near-uniform image rejected (placeholder?)")
            return None
    except Exception:
        pass
    if w > max_width:
        img = img.resize((max_width, max(1, round(h * max_width / float(w)))), Image.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    img.save(tmp, "JPEG", quality=quality, optimize=True, progressive=True)
    os.replace(tmp, dest)
    return {"path": str(dest), "width": img.size[0], "height": img.size[1],
            "bytes": dest.stat().st_size,
            "sha1": hashlib.sha1(dest.read_bytes()).hexdigest()}


def _item_page_url(item: Dict[str, Any]) -> str:
    src = item.get("source") if isinstance(item.get("source"), dict) else {}
    for cand in (src.get("url"), item.get("source_url"), item.get("link")):
        if cand and str(cand).lower().startswith(("http://", "https://")):
            return str(cand)
    return ""


def _source_name(item: Dict[str, Any]) -> str:
    src = item.get("source") if isinstance(item.get("source"), dict) else {}
    name = (src.get("name") or item.get("source_name") or "").strip()
    if not name:
        host = urlparse(_item_page_url(item)).hostname or ""
        name = host.removeprefix("www.")
    return name


class _Budget:
    """Wall-clock cap for the whole photo step (fail-open: an exhausted budget only means fewer photos)."""

    def __init__(self, total: float, per_fetch: float):
        self.deadline = time.monotonic() + max(0.0, float(total))
        self.per_fetch = float(per_fetch)

    def remaining(self) -> float:
        return self.deadline - time.monotonic()

    def exhausted(self) -> bool:
        return self.remaining() <= 0.5

    def timeout(self) -> float:
        return max(0.5, min(self.per_fetch, self.remaining()))


PIB_IMG_RE = re.compile(
    r'<img[^>]+src=["\']([^"\']*WriteReadData/userfiles/image/[^"\']+\.(?:jpe?g|png))["\']', re.I)
GNEWS_SG_RE = re.compile(r'data-n-a-sg="([^"]+)"')
GNEWS_TS_RE = re.compile(r'data-n-a-ts="([^"]+)"')
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
COMMONS_UA = ("AgriLearningPointBot/1.0 (https://github.com/agrilearningpoint/daily-current-affairs; "
              "daily current-affairs PDF) python-requests")
FREE_LICENSE_RE = re.compile(r"^\s*(?:cc0|cc[ -]by(?:[ -]sa)?(?:[ -]\d(?:\.\d)?)?|public domain|pd\b|"
                             r"gody|gfdl|attribution)", re.I)
# Words that never identify a story on their own (Commons relevance check).
_ENTITY_STOP = {
    "the", "and", "for", "with", "from", "of", "in", "on", "to", "a", "an", "by", "at", "new",
    "india", "indian", "government", "union", "ministry", "minister", "department", "national",
    "pib", "press", "information", "bureau", "scheme", "mission", "programme", "program", "day",
    "first", "launch", "launched", "news", "report", "state", "states", "centre", "central",
}
_SOURCE_ORGS = {"pib", "press information bureau", "prime minister of india", "ministry of external affairs",
                "government of india", "ani", "pti", "ians"}


def _is_gnews(url: str) -> bool:
    try:
        u = urlparse(url)
    except ValueError:
        return False
    return (u.hostname or "").endswith("news.google.com") and "/articles/" in u.path


def _default_post(url: str, data: str, timeout: float) -> Tuple[int, str]:
    import requests
    resp = requests.post(url, data=data, timeout=timeout, headers={
        "User-Agent": USER_AGENT, "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"})
    return resp.status_code, resp.text


def resolve_google_news(url: str, fetch: Callable[..., Tuple[int, str, bytes]],
                        post: Optional[Callable[..., Tuple[int, str]]], timeout: float = 8.0) -> str:
    """Publisher URL behind a news.google.com/articles/<id> link ('' when it cannot be resolved)."""
    if not post or not _is_gnews(url) or os.getenv("ALP_IMAGE_RESOLVE_GNEWS", "1") == "0":
        return ""
    try:
        import json as _json
        gid = urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]
        status, _ctype, body = fetch(f"https://news.google.com/rss/articles/{gid}", timeout, 1_500_000)
        if status != 200 or not body:
            return ""
        html_text = body.decode("utf-8", "replace")
        sg, ts = GNEWS_SG_RE.search(html_text), GNEWS_TS_RE.search(html_text)
        if not (sg and ts):
            return ""
        inner = _json.dumps(["garturlreq", [["X", "X", ["X", "X"], None, None, 1, 1, "US:en", None, 1, None,
                                            None, None, None, None, 0, 1], "X", "X", 1, [1, 1, 1], 1, 1, None,
                                           0, 0, None, 0], gid, int(ts.group(1)), sg.group(1)])
        freq = _json.dumps([[["Fbv4je", inner, None, "generic"]]])
        pstatus, text = post("https://news.google.com/_/DotsSplashUi/data/batchexecute",
                             "f.req=" + quote(freq), timeout)
        if pstatus != 200 or not text:
            return ""
        payload = _json.loads(text.split("\n\n", 1)[-1])
        real = _json.loads(payload[0][2])[1]
        if isinstance(real, str) and real.lower().startswith(("http://", "https://")) and not _is_gnews(real):
            return real
    except Exception as exc:
        logger.info("[images] google news link not resolved: %s", exc)
    return ""


def extract_pib_images(html_text: str, base_url: str = "") -> List[str]:
    """Photo URLs embedded in a PIB press-release page (userfiles images only, deduped, in page order)."""
    out: List[str] = []
    for m in PIB_IMG_RE.finditer(html_text or ""):
        cand = m.group(1).strip()
        if cand.startswith("//"):
            cand = "https:" + cand
        elif not cand.lower().startswith("http"):
            cand = urljoin(base_url or "https://pib.gov.in/", cand)
        if cand not in out and plausible_image_url(cand):
            out.append(cand)
    return out


def _is_story_page(url: str) -> bool:
    """A site home page / section index never vouches for a story photo (its og:image is a brand card)."""
    try:
        u = urlparse(url)
    except ValueError:
        return False
    path = (u.path or "/").rstrip("/")
    return bool(path) or bool(u.query)


def _is_pib(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower() if url else ""
    return host.endswith("pib.gov.in")


def _entity_tokens(entity: str) -> List[str]:
    return [w for w in re.findall(r"[a-z0-9]+", entity.lower()) if len(w) >= 3 and w not in _ENTITY_STOP]


def story_entities(item: Dict[str, Any], limit: int = 2) -> List[str]:
    """Main named entities of a story (organisations first, then a short place/name prefix of the headline)."""
    out: List[str] = []
    cands: List[str] = [str(o) for o in (item.get("organizations") or []) if isinstance(o, str)]
    head = re.sub(r"^[>\s\-–•]+", "", str(item.get("headline_en") or item.get("title") or ""))
    if ":" in head:
        prefix = head.split(":", 1)[0].strip()
        if 3 <= len(prefix) <= 40:
            cands.append(prefix)
    for c in cands:
        c = re.sub(r"\s+", " ", c).strip()
        if not c or c.lower() in _SOURCE_ORGS:
            continue
        toks = _entity_tokens(c)
        # A single short generic word is not an entity; need >=2 words or one distinctive word (>=4 chars).
        if not toks or (len(toks) == 1 and len(toks[0]) < 4):
            continue
        if c not in out:
            out.append(c)
        if len(out) >= limit:
            break
    return out


_TITLE_NOISE = {"file", "jpg", "jpeg", "png", "tif", "tiff", "version", "img", "dsc", "photo", "image"}


def commons_title_matches(title: str, entity: str) -> bool:
    """Relevance check for a Commons file: every distinctive word of the entity is in the
    file title AND the entity is what the title is mostly about (>= half of its distinctive
    words), so "Langur monkey, Orchha, Madhya Pradesh" never illustrates a Madhya Pradesh MoU."""
    toks = _entity_tokens(entity)
    words = [w for w in re.findall(r"[a-z0-9]+", (title or "").lower())
             if len(w) >= 3 and not w.isdigit() and w not in _ENTITY_STOP and w not in _TITLE_NOISE]
    if not toks or not all(t in words for t in toks):
        return False
    distinct = set(words)
    return len(set(toks)) * 2 >= len(distinct)


def _strip_tags(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text or "")).strip()


def commons_candidates(entity: str, fetch: Callable[..., Tuple[int, str, bytes]],
                       timeout: float = 8.0, limit: int = 6) -> List[Tuple[str, str]]:
    """(image_url, credit) pairs from Wikimedia Commons for an entity: free licence + title relevance only."""
    import json as _json
    if not entity or os.getenv("ALP_IMAGE_COMMONS", "1") == "0":
        return []
    q = (f"{COMMONS_API}?action=query&format=json&generator=search&gsrnamespace=6&gsrlimit={limit}"
         f"&gsrsearch={quote(entity + ' filetype:bitmap')}&prop=imageinfo"
         f"&iiprop=url%7Cmime%7Csize%7Cextmetadata&iiurlwidth=1000")
    try:
        status, _ctype, body = fetch(q, timeout, 2_000_000)
        if status != 200 or not body:
            return []
        data = _json.loads(body.decode("utf-8", "replace"))
    except Exception as exc:
        logger.info("[images] commons search failed for %r: %s", entity, exc)
        return []
    pages = sorted(((data.get("query") or {}).get("pages") or {}).values(), key=lambda p: p.get("index", 99))
    out: List[Tuple[str, str]] = []
    for pg in pages:
        try:
            title = str(pg.get("title") or "")
            if not commons_title_matches(title, entity):
                continue
            info = (pg.get("imageinfo") or [{}])[0]
            if str(info.get("mime") or "") not in ("image/jpeg", "image/png"):
                continue
            meta = info.get("extmetadata") or {}
            lic = _strip_tags(str((meta.get("LicenseShortName") or {}).get("value") or ""))
            if not lic or not FREE_LICENSE_RE.match(lic):
                continue
            artist = _strip_tags(str((meta.get("Artist") or {}).get("value") or ""))[:60] or "unknown author"
            url = str(info.get("thumburl") or info.get("url") or "")
            if not plausible_image_url(url):
                continue
            out.append((url, f"Photo: {artist} / Wikimedia Commons, {lic}"))
        except Exception:
            continue
    return out


def candidate_sources(item: Dict[str, Any], fetch: Callable[..., Tuple[int, str, bytes]],
                      timeout: float = 8.0, *, post: Optional[Callable[..., Tuple[int, str]]] = None,
                      budget: Optional[_Budget] = None) -> List[Tuple[str, str, str]]:
    """Ordered (url, credit, kind) candidates for one story. kind: feed | og | pib | commons. Never raises."""
    out: List[Tuple[str, str, str]] = []
    seen: set = set()

    def add(url: str, credit: str, kind: str) -> None:
        if url and url not in seen and plausible_image_url(url):
            seen.add(url)
            out.append((url, credit, kind))

    def t() -> float:
        return budget.timeout() if budget else timeout

    try:
        name = _source_name(item)
        add(str(item.get("image_url") or "").strip(), name, "feed")
        page = _item_page_url(item)
        if page and _is_gnews(page):
            if budget is None or not budget.exhausted():
                page = resolve_google_news(page, fetch, post, t()) or ""
            else:
                page = ""
        if page and "news.google.com" not in page and (budget is None or not budget.exhausted()):
            try:
                status, ctype, body = fetch(page, t(), 1_500_000)
                if status == 200 and body and ("html" in ctype or not ctype):
                    html_text = body.decode("utf-8", "replace")
                    # Relevance: only a story page (not a site home page) vouches for its photos;
                    # PIB photos only from a press-release page (PRID=...).
                    if _is_pib(page) and re.search(r"[?&]PRID=\d+", page, re.I):
                        for u in extract_pib_images(html_text, page):
                            add(u, "Photo: PIB", "pib")
                    if _is_story_page(page):
                        og = extract_og_image(html_text, page)
                        if og:
                            add(og, "Photo: PIB" if _is_pib(page) else name, "og")
            except Exception as exc:
                logger.info("[images] page fetch failed for %s: %s", page, exc)
        if os.getenv("ALP_IMAGE_COMMONS", "1") != "0":
            for ent in story_entities(item):
                if budget is not None and budget.exhausted():
                    break
                for u, credit in commons_candidates(ent, fetch, t())[:2]:
                    add(u, credit, "commons")
    except Exception as exc:
        logger.info("[images] candidate search failed: %s", exc)
    return out


def candidate_urls(item: Dict[str, Any], fetch: Callable[..., Tuple[int, str, bytes]],
                   timeout: float = 8.0) -> List[str]:
    """Feed image first, then the article page's photos (backward-compatible URL list)."""
    return [u for u, _c, _k in candidate_sources(item, fetch, timeout)]


def attach_images(items: List[Dict[str, Any]], job_id: str, out_root: Path, *,
                  limit: Optional[int] = None,
                  fetch: Optional[Callable[..., Tuple[int, str, bytes]]] = None,
                  timeout: Optional[float] = None,
                  post: Optional[Callable[..., Tuple[int, str]]] = None,
                  total_budget: Optional[float] = None) -> Dict[str, Any]:
    """Give up to ``limit`` of the most important items a validated local photo.

    Mutates items in place: sets ``image_path`` (absolute path), ``image_credit``
    (credit line: source name, "Photo: PIB" or the Commons author + licence),
    ``image_source_kind`` and ``image_url_used``.  Items that already carry an
    existing ``image_path`` file are kept and count toward the limit.  Each fetch
    is capped at ``timeout`` (8 s) and the whole step at ``total_budget`` (~90 s).
    Never raises.
    """
    stats = {"attempted": 0, "attached": 0, "rejected": 0, "skipped_reason": "",
             "by_kind": {}, "budget_exhausted": False}
    try:
        if not images_enabled():
            stats["skipped_reason"] = "disabled"
            return stats
        limit = limit if limit is not None else _env_int("ALP_PDF_MAX_IMAGES", 12)
        timeout = float(timeout if timeout is not None else _env_int("ALP_IMAGE_FETCH_TIMEOUT", 8))
        budget = _Budget(total_budget if total_budget is not None else _env_int("ALP_IMAGE_TOTAL_BUDGET", 90),
                         timeout)
        max_bytes = _env_int("ALP_IMAGE_MAX_BYTES", 6_000_000)
        if fetch is None:
            if network_disabled():
                stats["skipped_reason"] = "network disabled"
                # Still count photos that already exist locally.
            else:
                fetch = _default_fetch
                post = post or _default_post
        out_dir = Path(out_root) / re.sub(r"[^\w.-]+", "_", job_id or "edition")
        order = sorted(range(len(items)), key=lambda i: -float(items[i].get("importance_score") or 0))
        seen_hashes: set = set()
        seen_urls: set = set()
        for idx in order:
            if stats["attached"] >= limit:
                break
            it = items[idx]
            if not isinstance(it, dict):
                continue
            existing = it.get("image_path")
            if existing and not Path(existing).is_absolute():
                existing = str(Path(out_root).resolve().parent.parent / existing)
            if existing and Path(existing).is_file() and not it.get("image_placeholder"):
                it["image_path"] = existing
                stats["attached"] += 1
                it.setdefault("image_credit", _source_name(it))
                continue
            it["image_path"] = ""
            it.pop("image_placeholder", None)
            if fetch is None:
                continue
            if budget.exhausted():
                stats["budget_exhausted"] = True
                continue
            stats["attempted"] += 1
            try:
                cands = candidate_sources(it, fetch, timeout, post=post, budget=budget)
            except Exception as exc:
                logger.info("[images] candidates failed: %s", exc)
                cands = []
            for url, credit, kind in cands:
                if url in seen_urls:
                    continue
                if budget.exhausted():
                    stats["budget_exhausted"] = True
                    break
                seen_urls.add(url)
                try:
                    status, ctype, body = fetch(url, budget.timeout(), max_bytes)
                except Exception as exc:
                    logger.info("[images] download failed %s: %s", url, exc)
                    continue
                if status != 200 or not body or not ctype.startswith("image/") or "svg" in ctype:
                    stats["rejected"] += 1
                    continue
                eid = str(it.get("event_id") or idx)
                dest = out_dir / (re.sub(r"[^\w-]+", "_", eid)[:40] + ".jpg")
                try:
                    # PIB release photos are published small (~300 px); they are official story photos.
                    info = process_image_bytes(body, dest, min_width=280 if kind == "pib" else None)
                except Exception as exc:
                    logger.info("[images] processing failed %s: %s", url, exc)
                    info = None
                if not info:
                    stats["rejected"] += 1
                    continue
                if info["sha1"] in seen_hashes:  # same stock image reused by another story
                    try:
                        dest.unlink()
                    except OSError:
                        pass
                    stats["rejected"] += 1
                    continue
                seen_hashes.add(info["sha1"])
                it["image_path"] = info["path"]
                it["image_credit"] = credit or _source_name(it)
                it["image_source_kind"] = kind
                it["image_url_used"] = url
                stats["attached"] += 1
                stats["by_kind"][kind] = stats["by_kind"].get(kind, 0) + 1
                break
    except Exception as exc:  # absolute fail-soft guarantee
        logger.warning("[images] image step aborted (edition continues without more photos): %s", exc)
        stats["skipped_reason"] = f"error: {exc}"
    logger.info("[images] %d photo(s) attached (%d attempted, %d rejected, by source %s%s)",
                stats["attached"], stats["attempted"], stats["rejected"], stats["by_kind"],
                ", time budget exhausted" if stats["budget_exhausted"] else "")
    return stats


# --------------------------------------------------------------------------- #
# Category graphics (fallback only; never counted as real photos)
# --------------------------------------------------------------------------- #
_CATEGORY_RGB = {
    "agriculture": (22, 101, 52), "economy": (30, 64, 175), "banking": (30, 64, 175),
    "science": (91, 33, 182), "technology": (91, 33, 182), "environment": (21, 128, 61),
    "international": (14, 116, 144), "defence": (55, 65, 81), "sports": (194, 65, 12),
    "polity": (153, 27, 27), "national": (15, 23, 42),
}


def make_category_graphic(category: str, dest: Path) -> Optional[str]:
    """A simple, clearly non-photographic category card (JPEG). None on any error."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        cat = (category or "News").strip() or "News"
        rgb = next((v for k, v in _CATEGORY_RGB.items() if k in cat.lower()), (15, 23, 42))
        w, h = 1200, 240   # slim banner: marks the story without costing a page
        img = Image.new("RGB", (w, h), rgb)
        d = ImageDraw.Draw(img)
        light = tuple(min(255, c + 40) for c in rgb)
        for i in range(-h, w, 60):  # diagonal stripes so it never reads as a photo
            d.line([(i, h), (i + h, 0)], fill=light, width=14)
        font = None
        fdir = Path(__file__).resolve().parent.parent / "src" / "fonts"
        for name in ("Poppins-Bold.ttf", "Mukta-Bold.ttf"):
            try:
                font = ImageFont.truetype(str(fdir / name), 72)
                break
            except Exception:
                continue
        font = font or ImageFont.load_default()
        text = cat.upper()[:22]
        try:
            box = d.textbbox((0, 0), text, font=font)
            tw, th = box[2] - box[0], box[3] - box[1]
        except Exception:
            tw, th = len(text) * 40, 80
        d.rectangle([(w - tw) / 2 - 30, (h - th) / 2 - 30, (w + tw) / 2 + 30, (h + th) / 2 + 40], fill=rgb)
        d.text(((w - tw) / 2, (h - th) / 2 - 10), text, fill=(255, 255, 255), font=font)
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        img.save(tmp, "JPEG", quality=70, optimize=True)
        os.replace(tmp, dest)
        return str(dest)
    except Exception as exc:
        logger.info("[images] category graphic failed: %s", exc)
        return None


def fill_category_graphics(items: List[Dict[str, Any]], job_id: str, out_root: Path,
                           real_count: int, target: Optional[int] = None) -> int:
    """Top up photo-less stories with a category graphic until ``target`` is reached.

    Graphics carry ``image_placeholder=True`` and a "Graphic:" credit so nothing
    counts them as real news photos.  Disabled with ALP_IMAGE_PLACEHOLDERS=0.
    Returns how many graphics were added.  Never raises.
    """
    added = 0
    try:
        if os.getenv("ALP_IMAGE_PLACEHOLDERS", "1") == "0" or not images_enabled():
            return 0
        target = target if target is not None else _env_int("ALP_IMAGE_TARGET", 10)
        need = max(0, target - int(real_count))
        if not need:
            return 0
        out_dir = Path(out_root) / re.sub(r"[^\w.-]+", "_", job_id or "edition")
        order = sorted(range(len(items)), key=lambda i: -float(items[i].get("importance_score") or 0))
        cache: Dict[str, str] = {}
        for idx in order:
            if added >= need:
                break
            it = items[idx]
            if not isinstance(it, dict) or it.get("image_path"):
                continue
            cat = str(it.get("category") or "News")
            path = cache.get(cat)
            if not path:
                slug = re.sub(r"[^\w-]+", "_", cat.lower())[:30] or "news"
                path = make_category_graphic(cat, out_dir / f"_graphic_{slug}.jpg") or ""
                cache[cat] = path
            if not path:
                continue
            it["image_path"] = path
            it["image_placeholder"] = True
            it["image_source_kind"] = "category_graphic"
            it["image_credit"] = f"Graphic: {cat} (illustration, not a news photo)"
            added += 1
    except Exception as exc:
        logger.warning("[images] category graphics skipped: %s", exc)
    return added


def real_photo_count(items: List[Dict[str, Any]]) -> int:
    """Stories carrying a real (non-placeholder) photo."""
    return sum(1 for it in items or [] if isinstance(it, dict) and it.get("image_path")
               and not it.get("image_placeholder"))
