"""Stage 01 — Canonical RSS source fetch for the daily pipeline.

Task 01 rewrite. This module is the single production collection path wired
into main.py's DAILY_STAGES. It reads the canonical source registry from
pipeline.source_registry (config.feeds.VERIFIED_RSS + config.sources.ALL_SOURCES)
and writes one raw-edition JSON file per job.

Contract:
- Input:  enabled SourceSpec list (validated at startup; fail-loud).
- Output: data/raw/<job_id>.json   (falls back to daily_YYYY-MM-DD.json form)
- Schema: {"job_id", "job_date", "collected_at", "window_start", "window_end",
           "sources_total", "sources_failed", "articles": [Article...]}
- Article keys are a superset of what downstream stages consume:
  title, link, summary, published, source_feed, collected_at, content_hash,
  plus provenance fields source_name/source_id/source_tier/category/language.
- Never uses local wall-clock as the job date when ALP_JOB_DATE is provided.
- Empty successful parse result => hard failure (exit 2); no silent empty run.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse

# --- optional third-party deps with clear actionable errors ---------------
try:
    import feedparser  # type: ignore
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "ERROR: 'feedparser' is required by stage 01 but not installed. "
        "Run: pip install -r requirements.txt"
    ) from exc

try:
    import requests  # type: ignore
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "ERROR: 'requests' is required by stage 01 but not installed. "
        "Run: pip install -r requirements.txt"
    ) from exc

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.source_registry import SourceConfigError, SourceSpec, load_sources

ROOT = Path(os.environ.get("ALP_ROOT", Path(__file__).resolve().parent.parent))
RAW_DIR = ROOT / "data" / "raw"

HTTP_TIMEOUT = int(os.environ.get("FETCH_TIMEOUT", "20"))
MAX_RETRIES = int(os.environ.get("FETCH_RETRIES", "2"))
USER_AGENT = os.environ.get(
    "FETCH_USER_AGENT",
    "AgriLearningPointBot/1.0 (+https://github.com/agrilearningpoint)",
)


# --------------------------------------------------------------------------
# Job context helpers
# --------------------------------------------------------------------------
def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_job_context() -> Tuple[str, str]:
    """Return (job_id, job_date) honouring explicit orchestrator env vars.

    Backfill safety rule: if ALP_JOB_DATE is set, it wins over wall clock.
    We never silently replace an explicitly requested date with today.
    """
    job_date = os.environ.get("ALP_JOB_DATE", "").strip()
    job_id = os.environ.get("ALP_JOB_ID", "").strip()
    if not job_date:
        job_date = _utcnow().strftime("%Y-%m-%d")
    if not job_id:
        job_type = os.environ.get("ALP_JOB_TYPE", "daily").strip() or "daily"
        job_id = f"{job_type}_{job_date}"
    return job_id, job_date


def resolve_window(job_date: str) -> Tuple[datetime, datetime]:
    """Compute the collection window using the project's existing policy.

    Existing documented behaviour (collect_window in the previous collector):
    - scheduled/manual runs for *today*: last 24 hours ending now.
    - backfill runs for an explicit past date: that calendar day 00:00–24:00 UTC.
    We preserve that policy rather than inventing a new one.
    """
    try:
        target = datetime.strptime(job_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        # Malformed explicit date must not fall back to wall clock silently.
        raise SystemExit(f"ERROR: invalid ALP_JOB_DATE {job_date!r} (want YYYY-MM-DD)")
    today = _utcnow().date()
    if target.date() == today:
        end = _utcnow()
        start = end - timedelta(hours=24)
    else:
        start = target
        end = target + timedelta(days=1)
    return start, end


# --------------------------------------------------------------------------
# Parsing / normalisation helpers
# --------------------------------------------------------------------------
def parse_entry_time(entry) -> Optional[datetime]:
    """Extract a timezone-aware publication datetime from a feed entry."""
    for key in ("published_parsed", "updated_parsed"):
        st = getattr(entry, key, None)
        if st:
            try:
                return datetime.fromtimestamp(time.mktime(st), tz=timezone.utc)
            except (ValueError, OverflowError, OSError):
                continue
    for key in ("published", "updated"):
        raw = getattr(entry, key, None)
        if isinstance(raw, str):
            try:
                dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except ValueError:
                continue
    return None


def normalize_url(url: str) -> str:
    """Normalize scheme/host case and strip fragment; keep query params intact."""
    if not url:
        return ""
    try:
        p = urlparse(url.strip())
        scheme = p.scheme.lower() or "https"
        netloc = p.netloc.lower()
        path = p.path or "/"
        query = f"?{p.query}" if p.query else ""
        return f"{scheme}://{netloc}{path.rstrip('/')}{query}"
    except ValueError:
        return url.strip()


def content_hash(title: str, summary: str, link: str) -> str:
    """Stable dedup fingerprint: normalized title+summary+link."""
    norm = re.sub(r"\s+", " ", f"{title}|{summary[:300]}|{normalize_url(link)}")
    return hashlib.sha256(norm.encode("utf-8", "ignore")).hexdigest()[:16]


def clean_text(s: Optional[str]) -> str:
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", " ", s)          # strip HTML tags
    s = re.sub(r"&[a-z]+;|&#\d+;", " ", s, flags=re.I)  # crude entity cleanup
    return re.sub(r"\s+", " ", s).strip()


# --------------------------------------------------------------------------
# Fetching
# --------------------------------------------------------------------------
def fetch_feed(spec: SourceSpec) -> Tuple[Optional[bytes], Optional[str]]:
    """Fetch one feed with retries. Returns (payload_bytes, error_message)."""
    last_err: Optional[str] = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.get(
                spec.rss_url,
                timeout=HTTP_TIMEOUT,
                headers={"User-Agent": USER_AGENT},
            )
            if resp.status_code == 200 and resp.content:
                return resp.content, None
            last_err = f"HTTP {resp.status_code}"
        except requests.RequestException as exc:
            last_err = f"{type(exc).__name__}: {exc}"
        if attempt < MAX_RETRIES:
            time.sleep(min(2 ** attempt, 4))
    return None, last_err


def collect(spec: SourceSpec, win_start: datetime, win_end: datetime,
            logs: list) -> Tuple[list, Optional[str]]:
    """Fetch + parse one source. Returns (articles, fatal_error_or_None).

    Malformed individual entries are skipped and logged; they never abort the
    whole feed. A failed feed returns fatal_error so other feeds still count.
    """
    payload, err = fetch_feed(spec)
    if payload is None:
        return [], f"{spec.name}: fetch failed ({err})"

    parsed = feedparser.parse(payload)
    if getattr(parsed, "bozo", 0) and not parsed.entries:
        return [], f"{spec.name}: unparseable feed body (bozo={parsed.bozo})"

    articles = []
    now_iso = _utcnow().isoformat()
    for i, entry in enumerate(parsed.entries):
        try:
            title = clean_text(getattr(entry, "title", ""))
            link = str(getattr(entry, "link", "") or "").strip()
            if not title or not link.lower().startswith(("http://", "https://")):
                logs.append(f"{spec.name} entry[{i}]: skipped (missing title/link)")
                continue
            pub_dt = parse_entry_time(entry)
            if pub_dt is None:
                logs.append(f"{spec.name} entry[{i}]: no publication date; excluded")
                continue  # do NOT treat undated items as current news
            if not (win_start <= pub_dt < win_end):
                continue  # outside the job window
            summary = clean_text(
                getattr(entry, "summary", "")
                or getattr(entry, "description", "")
            )
            articles.append({
                "title": title,
                "link": normalize_url(link),
                "summary": summary,
                "published": pub_dt.isoformat(),
                "source_feed": spec.rss_url,
                "source_id": spec.source_id,
                "source_name": spec.name,
                "source_tier": spec.tier,
                "category": spec.category,
                "language": spec.language,
                "official": spec.official,
                "collected_at": now_iso,
                "content_hash": content_hash(title, summary, link),
            })
        except Exception as exc:  # defensive: one bad entry must not kill feed
            logs.append(f"{spec.name} entry[{i}]: malformed ({type(exc).__name__}); skipped")
    return articles, None


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main() -> int:
    try:
        specs = load_sources()
    except SourceConfigError as exc:
        print(f"FATAL SOURCE CONFIG ERROR:\n{exc}", file=sys.stderr)
        return 2

    job_id, job_date = get_job_context()
    win_start, win_end = resolve_window(job_date)

    all_articles: list = []
    seen_hashes: set = set()
    failed_sources = 0
    logs: list = []

    for spec in specs:
        arts, fatal = collect(spec, win_start, win_end, logs)
        if fatal:
            failed_sources += 1
            print(f"WARN [{spec.name}] {fatal}", file=sys.stderr)
            continue
        added = 0
        for art in arts:
            if art["content_hash"] in seen_hashes:
                continue
            seen_hashes.add(art["content_hash"])
            all_articles.append(art)
            added += 1
        print(f"[{spec.name}] kept {added} articles")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RAW_DIR / f"{job_id}.json"
    edition = {
        "job_id": job_id,
        "job_date": job_date,
        "collected_at": _utcnow().isoformat(),
        "window_start": win_start.isoformat(),
        "window_end": win_end.isoformat(),
        "sources_total": len(specs),
        "sources_failed": failed_sources,
        "skip_log": logs[-200:],  # bounded diagnostics, not full spam
        "articles": all_articles,
    }
    tmp = out_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(edition, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, out_path)  # atomic publish

    print(f"Wrote {len(all_articles)} articles -> {out_path}")

    if not all_articles:
        # Loud failure: an empty edition must never flow downstream silently.
        print(
            "FATAL: zero articles collected within the job window "
            f"({win_start:%Y-%m-%d %H:%M} → {win_end:%Y-%m-%d %H:%M} UTC); "
            f"{failed_sources}/{len(specs)} sources failed.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
