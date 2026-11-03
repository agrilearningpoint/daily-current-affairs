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


DEFAULT_DAILY_CUTOFF = "06:00"
# A previous edition's recorded end is trusted as the next start only when it
# is at most this many hours before the nominal start (prevents a stale or
# missing edition from producing a multi-day window).
_MAX_CARRYOVER_HOURS = 12


def daily_cutoff() -> dt_time:
    """Edition cutoff (IST wall clock) from ALP_DAILY_CUTOFF, default 06:00."""
    import os
    raw = (os.getenv("ALP_DAILY_CUTOFF") or DEFAULT_DAILY_CUTOFF).strip()
    try:
        hh, mm = raw.split(":", 1)
        return dt_time(int(hh), int(mm))
    except (ValueError, TypeError):
        return dt_time(6, 0)


def daily_edition_window(edition_day: date, *, previous_end: datetime | None = None,
                         now: datetime | None = None) -> tuple[datetime, datetime]:
    """Fixed news window for daily edition ``edition_day``.

    Nominal window: (edition_day-1) CUTOFF IST -> edition_day CUTOFF IST
    (CUTOFF = ALP_DAILY_CUTOFF, default 06:00). It depends on the edition date,
    never on when the run happens, so a late cron, a retry or a --reset cannot
    shift it or make it overlap the previous edition.

    * A run before the cutoff (the 02:00-04:00 IST generation crons) cannot see
      the future, so the end is clipped to the run time.
    * When the previous edition recorded its actual end (``previous_end``), the
      window starts there instead, so consecutive editions are contiguous with
      no overlap and no gap (e.g. a 02:00 generation run yesterday -> today's
      window starts at yesterday 02:00).
    """
    cutoff = daily_cutoff()
    nominal_end = datetime.combine(edition_day, cutoff, tzinfo=IST)
    nominal_start = nominal_end - timedelta(hours=24)
    now = (now or datetime.now(IST)).astimezone(IST)
    end = now if nominal_start < now < nominal_end else nominal_end
    start = nominal_start
    if previous_end is not None:
        if previous_end.tzinfo is None:
            previous_end = previous_end.replace(tzinfo=IST)
        previous_end = previous_end.astimezone(IST)
        if nominal_start - timedelta(hours=_MAX_CARRYOVER_HOURS) <= previous_end < end:
            start = previous_end
    return start, end


def collect_window(job_type: str, job_date: str, *, previous_end: datetime | None = None,
                   now: datetime | None = None) -> tuple[datetime, datetime]:
    """Return inclusive IST collection window for a daily/weekly/monthly edition.

    Daily: fixed edition window, see ``daily_edition_window`` (previous day
    06:00 IST -> edition day 06:00 IST by default, contiguous with the previous
    edition's recorded end when one is given).
    Weekly: Monday through the end of job_date.
    Monthly: previous complete month when job_date is the first; otherwise MTD.
    """
    if job_type not in {"daily", "weekly", "monthly"}:
        raise ValueError(f"Unsupported job_type: {job_type!r}")
    try:
        edition_day = date.fromisoformat(job_date)
    except ValueError as exc:
        raise ValueError(f"job_date must be YYYY-MM-DD, got {job_date!r}") from exc

    if job_type == "daily":
        start, end = daily_edition_window(edition_day, previous_end=previous_end, now=now)
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
