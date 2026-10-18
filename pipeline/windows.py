"""Shared edition windows, independent of source configuration and network I/O."""

from datetime import date, datetime, time as dt_time, timedelta
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


def collect_window(job_type: str, job_date: str) -> tuple[datetime, datetime]:
    """Return inclusive IST collection window for a daily/weekly/monthly edition.

    Daily current-date run: trailing 24 hours ending at run time.
    Daily historical-date run: previous calendar day (edition dated job_date).
    Weekly: Monday through the end of job_date.
    Monthly: previous complete month when job_date is the first; otherwise MTD.
    """
    if job_type not in {"daily", "weekly", "monthly"}:
        raise ValueError(f"Unsupported job_type: {job_type!r}")
    try:
        edition_day = date.fromisoformat(job_date)
    except ValueError as exc:
        raise ValueError(f"job_date must be YYYY-MM-DD, got {job_date!r}") from exc

    now = datetime.now(IST)
    if job_type == "daily":
        if edition_day == now.date():
            end = now
            # Include from start of yesterday (00:00:00 IST) up to now (24-36 hrs),
            # ensuring early-morning releases and UTC midnight items from yesterday
            # are captured for complete 24-hour current affairs coverage.
            start = datetime.combine(edition_day - timedelta(days=1), dt_time.min, tzinfo=IST)
        else:
            end_day = edition_day - timedelta(days=1)
            start = datetime.combine(end_day, dt_time.min, tzinfo=IST)
            end = datetime.combine(edition_day, dt_time.min, tzinfo=IST) - timedelta(microseconds=1)
    elif job_type == "weekly":
        start_day = edition_day - timedelta(days=edition_day.weekday())
        start = datetime.combine(start_day, dt_time.min, tzinfo=IST)
        end = datetime.combine(edition_day, dt_time.max, tzinfo=IST)
    else:
        if edition_day.day == 1:
            end_day = edition_day - timedelta(days=1)
            start_day = end_day.replace(day=1)
            start = datetime.combine(start_day, dt_time.min, tzinfo=IST)
            end = datetime.combine(end_day, dt_time.max, tzinfo=IST)
        else:
            start_day = edition_day.replace(day=1)
            start = datetime.combine(start_day, dt_time.min, tzinfo=IST)
            end = datetime.combine(edition_day, dt_time.max, tzinfo=IST)
    return start, end
