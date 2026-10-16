"""Canonical production collection stage (Task 01).

Single source-fetch path for daily jobs. Loads the canonical registry from
pipeline.source_registry, fetches RSS feeds with feedparser, normalizes and
validates every article at this boundary, and writes one edition JSON file.

Contract:
- Output path: data/raw/<job_id>.json   (job_id = ALP_JOB_ID or daily_<date>)
- Date policy : requested ALP_JOB_DATE is authoritative for naming; the
                collection uses the shared IST edition window (previous day
                for historical daily editions). Backfill never becomes "today".
- Failure    : zero usable articles after a full run -> exit 2 (loud fail).
               A single failed feed does NOT discard other feeds' results.
- No live network access happens at import time.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    import feedparser  # declared in requirements.txt
    import requests
except ImportError as exc:  # pragma: no cover - environment issue
    raise SystemExit(
        "feedparser is required for source fetching. "
        "Install project dependencies (pip install -r requirements.txt). "
        f"Original error: {exc}"
    ) from exc

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.quality import is_landing_link, reject_reason
from pipeline.source_registry import SourceSpec, SourceConfigError, load_sources

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"


# --------------------------------------------------------------------------
# Job context (date/backfill correctness)
# --------------------------------------------------------------------------

def job_context() -> Tuple[str, str, datetime]:
    """Return (job_id, job_date_iso, window_end_utc).

    ALP_JOB_DATE is authoritative. Never substitutes wall-clock today when an
    explicit date was requested. Window boundaries come from pipeline.windows
    so all collection paths share one edition policy.
    """
    now = datetime.now(timezone.utc)
    date_env = os.environ.get("ALP_JOB_DATE", "").strip()
    if date_env:
        try:
            base = datetime.strptime(date_env, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            print(f"[01_source_fetch] invalid ALP_JOB_DATE={date_env!r}; "
                  f"expected YYYY-MM-DD", file=sys.stderr)
            raise SystemExit(2)
    else:
        base = now
    job_date = base.strftime("%Y-%m-%d")
    job_id = os.environ.get("ALP_JOB_ID", "").strip() or f"daily_{job_date}"
    from pipeline.windows import collect_window
    _, window_end = collect_window(os.getenv("ALP_JOB_TYPE", "daily"), job_date)
    if os.getenv("ALP_WINDOW_END"):
        window_end = datetime.fromisoformat(os.environ["ALP_WINDOW_END"])
    window_end = window_end.astimezone(timezone.utc)
    return job_id, job_date, window_end


def _parse_entry_time(entry: Any) -> datetime | None:
    """Timezone-aware publication datetime from a feedparser entry, or None."""
    for key in ("published_parsed", "updated_parsed"):
        t = getattr(entry, key, None)
        if t:
            try:
                return datetime.fromtimestamp(calendar_time_to_epoch(t), tz=timezone.utc)
            except Exception:
                continue
    return None


def calendar_time_to_epoch(t) -> float:
    import calendar
    return calendar.timegm(t)


def content_hash(title: str, link: str) -> str:
    """Stable dedup key: normalized title + normalized link."""
    norm_title = " ".join((title or "").lower().split())
    norm_link = (link or "").strip().lower()
    return hashlib.sha256(f"{norm_title}|{norm_link}".encode("utf-8")).hexdigest()[:16]


# --------------------------------------------------------------------------
# Fetch + normalize
# --------------------------------------------------------------------------

def fetch_spec(spec: SourceSpec, window_start: datetime, window_end: datetime,
               seen_hashes: set) -> Tuple[List[Dict[str, Any]], int, int, str | None, int]:
    """Fetch one feed.

    Returns ``(articles, total_entries, skipped_malformed, error, chrome_skipped)``.
    Errors are reported per feed; they never discard results from other feeds.

    ``chrome_skipped`` counts discovery entries that are site chrome rather than
    news (see pipeline.quality) - the 2026-10-16 dry run showed those pages
    otherwise reach selection and crowd out real news.
    """
    collected: List[Dict[str, Any]] = []
    malformed = 0
    chrome_skipped = 0
    try:
        response = requests.get(spec.rss_url, headers={"User-Agent": "alp-collector/1.0"},
                                timeout=int(os.getenv("ALP_FEED_TIMEOUT", "20")))
        response.raise_for_status()
        parsed = feedparser.parse(response.content)
    except Exception as exc:  # network/disk level failure
        return [], 0, 0, f"{type(exc).__name__}: {exc}", 0

    status = getattr(parsed, "status", None)
    if parsed.bozo and not parsed.entries:
        err = getattr(parsed, "bozo_exception", "unparseable feed")
        if status == 404:
            return [], 0, 0, f"HTTP 404 (feed moved/deleted): {spec.rss_url}", 0
        return [], 0, 0, f"feed parse error ({err})", 0

    entries = list(getattr(parsed, "entries", []) or [])
    for entry in entries:
        title = (getattr(entry, "title", "") or "").strip()
        link = (getattr(entry, "link", "") or "").strip()
        if not title or not link.lower().startswith(("http://", "https://")):
            malformed += 1
            continue  # validated at collection boundary; logged via counter
        if reject_reason(title, spec.name) or is_landing_link(link):
            chrome_skipped += 1
            continue  # site chrome, not a news item

        published = _parse_entry_time(entry)
        if published is None:
            # Missing timestamps are NOT treated as current news.
            malformed += 1
            continue
        if not (window_start <= published <= window_end):
            continue  # outside the requested job window
        h = content_hash(title, link)
        if h in seen_hashes:
            continue
        seen_hashes.add(h)
        summary = getattr(entry, "summary", "") or ""
        collected.append({
            "title": title,
            "link": link,
            "summary": summary[:2000],
            "published": published.isoformat(),
            "source_feed": spec.rss_url,
            "source_name": spec.name,
            "source_id": spec.source_id,
            "source_tier": spec.tier,
            "publisher_url": spec.extra.get("url", spec.rss_url),
            **({"source_level": spec.extra["level"]} if "level" in spec.extra else {}),
            "official": spec.official,
            "category": spec.category,
            "language": spec.language,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "content_hash": h,
        })
    return collected, len(entries), malformed, None, chrome_skipped


def main() -> int:
    job_id, job_date, window_end = job_context()
    from pipeline.windows import collect_window
    window_start, _ = collect_window(os.getenv("ALP_JOB_TYPE", "daily"), job_date)
    if os.getenv("ALP_WINDOW_START"):
        window_start = datetime.fromisoformat(os.environ["ALP_WINDOW_START"])
    window_start = window_start.astimezone(timezone.utc)

    try:
        specs = load_sources()
    except SourceConfigError as exc:
        print(f"[01_source_fetch] FATAL source config error:\n{exc}", file=sys.stderr)
        return 2

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RAW_DIR / f"{job_id}.json"

    all_articles: List[Dict[str, Any]] = []
    seen_hashes: set = set()
    feed_failures: List[Dict[str, str]] = []
    ok_feeds = 0

    chrome_rejected = 0
    for spec in specs:
        arts, total, malformed, error, chrome_skipped = fetch_spec(
            spec, window_start, window_end, seen_hashes)
        chrome_rejected += chrome_skipped
        if error:
            feed_failures.append({"source_id": spec.source_id,
                                  "url": spec.rss_url, "error": error})
            print(f"[01_source_fetch] WARN feed failed: {spec.name} -> {error}",
                  file=sys.stderr)
            continue
        ok_feeds += 1
        all_articles.extend(arts)
        print(f"[01_source_fetch] {spec.name}: {len(arts)} in-window "
              f"(of {total} entries, {malformed} malformed skipped, "
              f"{chrome_skipped} chrome skipped)")

    edition = {
        "schema_version": "1.0",
        "job_id": job_id,
        "job_date": job_date,
        "collected_window": {
            "start": window_start.isoformat(),
            "end": window_end.isoformat(),
        },
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "sources_enabled": len(specs),
        "sources_fetched_ok": ok_feeds,
        "sources_failed": len(feed_failures),
        "feed_failures": feed_failures,
        "article_count": len(all_articles),
        "chrome_rejected_count": chrome_rejected,
        "articles": all_articles,
    }

    tmp_path = out_path.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(edition, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    os.replace(tmp_path, out_path)  # atomic write

    if not all_articles:
        print(f"[01_source_fetch] FATAL: zero usable articles collected into "
              f"{out_path} ({len(feed_failures)} feed failures). Refusing to "
              f"produce an empty edition.", file=sys.stderr)
        return 2

    print(f"[01_source_fetch] wrote {out_path} "
          f"({len(all_articles)} articles, {ok_feeds}/{len(specs)} feeds ok, "
          f"{chrome_rejected} chrome skipped)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
