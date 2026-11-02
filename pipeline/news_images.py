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
* No network in tests / dry runs: ``ALP_DISABLE_NETWORK=1`` or ``DRY_RUN=1``
  disables fetching; callers (and tests) can also inject ``fetch``.
"""
from __future__ import annotations

import hashlib
import io
import logging
import os
import re
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# URLs that are almost always logos, icons, trackers or placeholders.
BAD_URL_RE = re.compile(
    r"logo|icon|favicon|sprite|placeholder|default[-_]?(?:image|img|thumb|og)|no[-_]?image|"
    r"blank|spacer|pixel|1x1|avatar|badge|banner[-_]?ad|/ads?/|doubleclick|gravatar|"
    r"share[-_]?image[-_]?default|fallback|watermark",
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


def candidate_urls(item: Dict[str, Any], fetch: Callable[..., Tuple[int, str, bytes]],
                   timeout: float = 8.0) -> List[str]:
    """Feed image first, then og:image of the article page."""
    out: List[str] = []
    feed_img = str(item.get("image_url") or "").strip()
    if plausible_image_url(feed_img):
        out.append(feed_img)
    page = _item_page_url(item)
    if page and "news.google.com" not in page:
        try:
            status, ctype, body = fetch(page, timeout, 1_500_000)
            if status == 200 and body and ("html" in ctype or not ctype):
                og = extract_og_image(body.decode("utf-8", "replace"), page)
                if og and og not in out:
                    out.append(og)
        except Exception as exc:
            logger.info("[images] page fetch failed for %s: %s", page, exc)
    return out


def attach_images(items: List[Dict[str, Any]], job_id: str, out_root: Path, *,
                  limit: Optional[int] = None,
                  fetch: Optional[Callable[..., Tuple[int, str, bytes]]] = None,
                  timeout: float = 8.0) -> Dict[str, Any]:
    """Give up to ``limit`` of the most important items a validated local photo.

    Mutates items in place: sets ``image_path`` (absolute path), ``image_credit``
    (source name) and ``image_url_used``.  Items that already carry an existing
    ``image_path`` file are kept and count toward the limit.  Never raises.
    """
    stats = {"attempted": 0, "attached": 0, "rejected": 0, "skipped_reason": ""}
    try:
        if not images_enabled():
            stats["skipped_reason"] = "disabled"
            return stats
        limit = limit if limit is not None else _env_int("ALP_PDF_MAX_IMAGES", 8)
        max_bytes = _env_int("ALP_IMAGE_MAX_BYTES", 6_000_000)
        if fetch is None:
            if network_disabled():
                stats["skipped_reason"] = "network disabled"
                # Still count photos that already exist locally.
            fetch = None if network_disabled() else _default_fetch
        out_dir = Path(out_root) / re.sub(r"[^\w.-]+", "_", job_id or "edition")
        order = sorted(range(len(items)), key=lambda i: -float(items[i].get("importance_score") or 0))
        seen_hashes: set = set()
        for idx in order:
            if stats["attached"] >= limit:
                break
            it = items[idx]
            if not isinstance(it, dict):
                continue
            existing = it.get("image_path")
            if existing and not Path(existing).is_absolute():
                existing = str(Path(out_root).resolve().parent.parent / existing)
            if existing and Path(existing).is_file():
                it["image_path"] = existing
                stats["attached"] += 1
                it.setdefault("image_credit", _source_name(it))
                continue
            it["image_path"] = ""
            if fetch is None:
                continue
            stats["attempted"] += 1
            try:
                cands = candidate_urls(it, fetch, timeout)
            except Exception as exc:
                logger.info("[images] candidates failed: %s", exc)
                cands = []
            for url in cands:
                try:
                    status, ctype, body = fetch(url, timeout, max_bytes)
                except Exception as exc:
                    logger.info("[images] download failed %s: %s", url, exc)
                    continue
                if status != 200 or not body or not ctype.startswith("image/") or "svg" in ctype:
                    stats["rejected"] += 1
                    continue
                eid = str(it.get("event_id") or idx)
                dest = out_dir / (re.sub(r"[^\w-]+", "_", eid)[:40] + ".jpg")
                try:
                    info = process_image_bytes(body, dest)
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
                it["image_credit"] = _source_name(it)
                it["image_url_used"] = url
                stats["attached"] += 1
                break
    except Exception as exc:  # absolute fail-soft guarantee
        logger.warning("[images] image step aborted (edition continues without more photos): %s", exc)
        stats["skipped_reason"] = f"error: {exc}"
    logger.info("[images] %d photo(s) attached (%d attempted, %d rejected)",
                stats["attached"], stats["attempted"], stats["rejected"])
    return stats
