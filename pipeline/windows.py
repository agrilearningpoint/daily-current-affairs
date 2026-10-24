"""Shared edition windows, independent of source configuration and network I/O."""

from datetime import date, datetime, time as dt_time, timedelta, timezone
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


def rolling_24h_utc_window(run_started_at_utc: datetime | None = None) -> tuple[datetime, datetime]:
    """Return strictly reproducible 24-hour UTC window: [run_started_at_utc - 24 hours, run_started_at_utc].
    
    Timestamps are converted to Asia/Kolkata for display and metadata logging.
    """
    if run_started_at_utc is None:
        run_started_at_utc = datetime.now(timezone.utc)
    elif run_started_at_utc.tzinfo is None:
        run_started_at_utc = run_started_at_utc.replace(tzinfo=timezone.utc)
    else:
        run_started_at_utc = run_started_at_utc.astimezone(timezone.utc)
    window_end = run_started_at_utc
    window_start = window_end - timedelta(hours=24)
    return window_start, window_end


def collect_window(job_type: str, job_date: str) -> tuple[datetime, datetime]:
    """Return inclusive IST collection window for a daily/weekly/monthly edition.

    Daily current-date run: genuine trailing 24 hours ending at run time.
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
            # Strict rolling 24 hours: ending at current execution time
            start = end - timedelta(hours=24)
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
