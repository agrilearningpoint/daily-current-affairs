# -*- coding: utf-8 -*-
"""Story freshness: keep months-old news out of a daily edition.

Audit of daily_2026-11-04 found a Jun 2023 PIB release, the Kharif MSP approval
of 13 May 2026, the Jal Jeevan extension of 10 Mar 2026, a February state Budget
and "National Teachers Awards today" (a 5 Sep event) printed as the day's news:
DD News topic pages and feed-level dates (PIB) re-stamp old articles.

``stale_reason(item, job_date)`` returns why an item is old ("" when it is not).
It only drops on positive evidence, in this order:

* the item's own publish date (unless it is only the feed's channel date);
* a date in the URL (``/2026/05/13/``, ``2026-05-13``, ``20260513``);
* a PIB ``PRID`` (sequential; estimated from two dated anchors, wide margin);
* a full event date named in the headline / opening text that is months old;
* "<annual day> ... today" headlines (Teachers' Day on 5 Sep) far from the job date;
* "Budget 2026-27" presentation news long after that Budget.

Items with no date evidence at all are kept, so the reserve pool stays deep.
Env: ``ALP_FRESHNESS_FILTER=0`` disables; ``ALP_MAX_STORY_AGE_HOURS`` (72);
``ALP_STALE_EVENT_DAYS`` (60) for dates named in the text.
"""
from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

_MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september",
     "october", "november", "december"], 1)}
_MONTHS.update({k[:3]: v for k, v in list(_MONTHS.items())})
_MONTHS["sept"] = 9
_MON = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
_DMY_RE = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+" + _MON + r"\.?,?\s+(20\d{2})\b", re.I)
_MDY_RE = re.compile(r"\b" + _MON + r"\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(20\d{2})\b", re.I)
_URL_DATE_RES = (
    re.compile(r"/(20\d{2})/(\d{1,2})/(\d{1,2})(?:/|$)"),
    re.compile(r"(?<!\d)(20\d{2})-(\d{2})-(\d{2})(?!\d)"),
    re.compile(r"[/_-](20\d{2})(\d{2})(\d{2})(?=[/_.-]|$)"),
)
_PRID_RE = re.compile(r"[?&]PRID=(\d{6,8})", re.I)
# Two dated PIB releases (audit of 2026-11-04): PRID 2237548 = 10 Mar 2026,
# PRID 2260618 = 13 May 2026 -> ~360 releases a day.
_PRID_ANCHOR = (2260618, date(2026, 5, 13))
_PRID_PER_DAY = (2260618 - 2237548) / (date(2026, 5, 13) - date(2026, 3, 10)).days
_PRID_MARGIN_DAYS = 30

# Annual days that make "... today" headlines datable (month, day).
_ANNUAL_DAYS = [
    (re.compile(r"teachers['’]?\s*(?:day|awards?)", re.I), (9, 5)),
    (re.compile(r"independence\s+day", re.I), (8, 15)),
    (re.compile(r"republic\s+day", re.I), (1, 26)),
    (re.compile(r"hindi\s+diwas", re.I), (9, 14)),
    (re.compile(r"gandhi\s+jayanti", re.I), (10, 2)),
    (re.compile(r"constitution\s+day|samvidhan\s+diwas", re.I), (11, 26)),
    (re.compile(r"world\s+food\s+day", re.I), (10, 16)),
    (re.compile(r"(?:national\s+farmers['’]?\s+day|kisan\s+diwas)", re.I), (12, 23)),
    (re.compile(r"international\s+yoga\s+day|yoga\s+day", re.I), (6, 21)),
    (re.compile(r"national\s+sports\s+day", re.I), (8, 29)),
    (re.compile(r"engineers['’]?\s+day", re.I), (9, 15)),
]
_BUDGET_RE = re.compile(r"\bbudget\s*(?:for\s+)?(20\d{2})\s*[-–/]\s*(?:20)?(\d{2})\b", re.I)
_BUDGET_LATER_RE = re.compile(r"\b(?:review|revised|supplementary|mid-?year|utili[sz]\w*|spent|spending|"
                              r"allocation\s+(?:used|released)|outcome|implementation)\b", re.I)


def _enabled() -> bool:
    return os.getenv("ALP_FRESHNESS_FILTER", "1") != "0"


def max_age_hours() -> float:
    try:
        return float(os.getenv("ALP_MAX_STORY_AGE_HOURS", "72"))
    except ValueError:
        return 72.0


def _event_days() -> int:
    try:
        return int(os.getenv("ALP_STALE_EVENT_DAYS", "60"))
    except ValueError:
        return 60


def job_date(value: Any = None) -> date:
    raw = str(value or os.getenv("ALP_JOB_DATE") or "").strip()
    try:
        return datetime.strptime(raw[:10], "%Y-%m-%d").date()
    except ValueError:
        return datetime.now(timezone.utc).date()


def _safe_date(y: int, m: int, d: int) -> Optional[date]:
    try:
        return date(int(y), int(m), int(d))
    except (TypeError, ValueError):
        return None


def parse_published(raw: Any) -> Optional[datetime]:
    """ISO / RFC-822 / 'Mon 2026-11-02 10:21 AM IST' -> aware datetime (UTC)."""
    if not raw:
        return None
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    s = str(raw).strip()
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(s)
        if dt is not None:
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        pass
    m = re.search(r"(20\d{2})-(\d{2})-(\d{2})", s)
    if m:
        d = _safe_date(*m.groups())
        if d:
            return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    return None


def url_date(url: str) -> Optional[date]:
    u = str(url or "")
    for rx in _URL_DATE_RES:
        for m in rx.finditer(u):
            d = _safe_date(*m.groups())
            if d and 2000 <= d.year <= 2100:
                return d
    return None


def prid_date(url: str) -> Optional[date]:
    """Rough publication date of a PIB release from its sequential PRID."""
    m = _PRID_RE.search(str(url or ""))
    if not m:
        return None
    prid = int(m.group(1))
    days = (prid - _PRID_ANCHOR[0]) / _PRID_PER_DAY
    try:
        return _PRID_ANCHOR[1] + timedelta(days=round(days))
    except OverflowError:
        return None


def text_dates(text: str) -> List[date]:
    out: List[date] = []
    for m in _DMY_RE.finditer(text or ""):
        d = _safe_date(m.group(3), _MONTHS.get(m.group(2).lower().rstrip("."), 0), m.group(1))
        if d:
            out.append(d)
    for m in _MDY_RE.finditer(text or ""):
        d = _safe_date(m.group(3), _MONTHS.get(m.group(1).lower().rstrip("."), 0), m.group(2))
        if d:
            out.append(d)
    return out


def _urls(item: Dict[str, Any]) -> List[str]:
    return [str(item.get(k) or "") for k in ("link", "source_url", "url", "canonical_url") if item.get(k)]


def stale_reason(item: Dict[str, Any], jdate: Any = None, hours: Optional[float] = None) -> str:
    """Why *item* is too old for the edition of *jdate* ("" = fresh or undatable)."""
    if not isinstance(item, dict):
        return ""
    jd = jdate if isinstance(jdate, date) else job_date(jdate)
    ref = datetime(jd.year, jd.month, jd.day, tzinfo=timezone.utc)
    cutoff = ref - timedelta(hours=max_age_hours() if hours is None else hours)
    # 1. the item's own publish date (feed-level dates are only the channel's build time)
    if str(item.get("date_source") or "entry") != "feed":
        for key in ("published", "published_at", "pubDate", "publish_date", "date"):
            dt = parse_published(item.get(key))
            if dt is not None:
                if dt < cutoff:
                    return f"published {dt.date().isoformat()}"
                break
    # 2. dates carried by the URL
    for u in _urls(item):
        d = url_date(u)
        if d and d < cutoff.date():
            return f"url date {d.isoformat()}"
        p = prid_date(u)
        if p and p < cutoff.date() - timedelta(days=_PRID_MARGIN_DAYS):
            return f"PIB PRID ~{p.isoformat()}"
    head = str(item.get("headline_en") or item.get("title") or "")
    body = str(item.get("raw_facts") or item.get("summary") or "")
    # 3. a full event date in the headline / opening text that is months old
    found = text_dates(f"{head} . {body[:600]}")
    if found:
        newest = max(found)
        if newest < jd - timedelta(days=_event_days()):
            return f"event date {newest.isoformat()}"
    # 4. "<annual day> ... today" far from that day
    if re.search(r"\btoday\b", head, re.I):
        for rx, (mm, dd) in _ANNUAL_DAYS:
            if rx.search(head):
                cands = [_safe_date(jd.year + k, mm, dd) for k in (-1, 0, 1)]
                gap = min(abs((c - jd).days) for c in cands if c)
                if gap > 3:
                    return f"annual day {mm:02d}-{dd:02d} named 'today'"
    # 5. Budget YYYY-YY presentation news long after that Budget
    bm = _BUDGET_RE.search(head)
    if bm and not _BUDGET_LATER_RE.search(head):
        start = int(bm.group(1))
        if jd > date(start, 8, 15):
            return f"Budget {start}-{bm.group(2)} news"
    return ""


def filter_fresh(items: Iterable[Dict[str, Any]], jdate: Any = None,
                 hours: Optional[float] = None) -> Tuple[List[Dict[str, Any]], List[Tuple[Dict[str, Any], str]]]:
    """Split *items* into (fresh, [(stale_item, reason)]). No-op when disabled."""
    items = list(items or [])
    if not _enabled():
        return items, []
    kept, dropped = [], []
    for it in items:
        why = stale_reason(it, jdate, hours)
        if why:
            dropped.append((it, why))
        else:
            kept.append(it)
    return kept, dropped
