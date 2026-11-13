# -*- coding: utf-8 -*-
"""
Strict Previous-24-Hour IST News Research Window Engine
=======================================================
Enforces an explicit India Standard Time (Asia/Kolkata) research window:
For edition date D (default cutoff 06:00 IST):
  window_start = (D - 1 day) at 06:00:00+05:30
  window_end   = D at 06:00:00+05:30

Rules enforced (Master Spec Section 5):
1. Every news item must have a verified publication timestamp.
2. All timestamps are converted into Asia/Kolkata (+05:30).
3. News published before window_start or after window_end is strictly excluded.
4. Article modification/update dates are never used to disguise an old original_published_at.
5. Old-event coverage (e.g. "in 2023", "last year") inside a newly published article is flagged.
6. Missing timestamps are quarantined, never assumed to be today's news.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")

STALE_EVENT_YEAR_RE = re.compile(r"\b(201\d|202[0-4])\b")
OLD_EVENT_PHRASE_RE = re.compile(
    r"\b(?:two\s+years\s+ago|three\s+years\s+ago|back\s+in\s+202[0-4]|archive\s+report)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ResearchWindow:
    edition_date: str
    start_ist: datetime
    end_ist: datetime

    @property
    def label(self) -> str:
        return (
            f"{self.start_ist.strftime('%d %B %Y, %H:%M IST')} to "
            f"{self.end_ist.strftime('%d %B %Y, %H:%M IST')}"
        )

    def contains(self, dt: datetime) -> bool:
        dt_ist = to_ist(dt)
        return self.start_ist <= dt_ist <= self.end_ist


def to_ist(dt: datetime) -> datetime:
    """Convert any aware or naive datetime to Asia/Kolkata (naive assumed UTC)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST)


def compute_edition_window(
    edition_date_str: Optional[str] = None,
    cutoff_hhmm: Optional[str] = None,
    hours: int = 24,
) -> ResearchWindow:
    """Compute the strict 24-hour IST research window for an edition date."""
    if not edition_date_str:
        edition_date_str = os.getenv("ALP_JOB_DATE") or datetime.now(IST).strftime("%Y-%m-%d")
    cutoff = (cutoff_hhmm or os.getenv("ALP_DAILY_CUTOFF", "06:00")).strip()
    hh, mm = (int(x) for x in cutoff.split(":", 1))
    d = date.fromisoformat(edition_date_str)
    end_ist = datetime.combine(d, time(hh, mm, 0), tzinfo=IST)
    start_ist = end_ist - timedelta(hours=hours)
    return ResearchWindow(edition_date=edition_date_str, start_ist=start_ist, end_ist=end_ist)


def parse_timestamp_to_ist(raw_value: Any) -> Optional[datetime]:
    """Parse ISO-8601, RFC-2822 (RSS pubDate), or epoch into an IST-aware datetime."""
    if raw_value is None:
        return None
    if isinstance(raw_value, datetime):
        return to_ist(raw_value)
    if isinstance(raw_value, (int, float)):
        try:
            return datetime.fromtimestamp(float(raw_value), tz=timezone.utc).astimezone(IST)
        except Exception:
            return None
    s = str(raw_value).strip()
    if not s:
        return None
    # Try ISO-8601
    try:
        iso_s = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso_s)
        return to_ist(dt)
    except Exception:
        pass
    # Try RFC-2822 (RSS pubDate)
    try:
        dt = parsedate_to_datetime(s)
        if dt is not None:
            return to_ist(dt)
    except Exception:
        pass
    # Try common Indian date patterns "2026-11-13 14:30:00"
    for fmt in ("%Y-%m-%d %H:%M:%S", "%d-%m-%Y %H:%M", "%Y/%m/%d %H:%M:%S"):
        try:
            dt = datetime.strptime(s, fmt).replace(tzinfo=IST)
            return dt
        except Exception:
            continue
    return None


def is_old_event_coverage(item: Dict[str, Any], edition_year: int) -> Tuple[bool, str]:
    """Detect when a newly published article is actually retrospective coverage of an old event."""
    headline = str(item.get("headline_en") or item.get("title") or "")
    summary = str(item.get("summary_en") or item.get("summary") or "")
    combined = f"{headline} {summary}"
    if OLD_EVENT_PHRASE_RE.search(combined):
        return True, "retrospective_old_event_phrase"
    # If the headline explicitly centers on an older year without current edition year
    years = [int(y) for y in re.findall(r"\b(20\d{2})\b", headline)]
    if years and max(years) < edition_year - 1:
        return True, f"headline_references_old_year_{max(years)}"
    return False, ""


def filter_articles_by_window(
    items: List[Dict[str, Any]],
    window: ResearchWindow,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Filter articles strictly against `window`.
    Returns (accepted_items, rejected_outside_window, quarantined_missing_timestamp).
    """
    accepted: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    quarantined: List[Dict[str, Any]] = []
    edition_year = int(window.edition_date.split("-")[0])

    for item in items:
        working = dict(item)
        # Rule 4: Do not confuse updated_at with original_published_at
        orig_raw = (
            working.get("original_published_at")
            or working.get("published_at")
            or working.get("pubDate")
            or working.get("published")
        )
        # If only updated_at is present without published_at, quarantine
        if not orig_raw:
            working["quarantine_reason"] = "missing_original_publication_timestamp"
            quarantined.append(working)
            continue

        pub_ist = parse_timestamp_to_ist(orig_raw)
        if pub_ist is None:
            working["quarantine_reason"] = f"unparseable_timestamp:{orig_raw}"
            quarantined.append(working)
            continue

        working["published_at_ist"] = pub_ist.isoformat()

        if not window.contains(pub_ist):
            working["rejection_reason"] = (
                f"outside_window ({pub_ist.isoformat()} not in "
                f"[{window.start_ist.isoformat()}, {window.end_ist.isoformat()}])"
            )
            rejected.append(working)
            continue

        old_ev, reason = is_old_event_coverage(working, edition_year)
        if old_ev:
            working["rejection_reason"] = f"old_event_coverage:{reason}"
            rejected.append(working)
            continue

        accepted.append(working)

    return accepted, rejected, quarantined
