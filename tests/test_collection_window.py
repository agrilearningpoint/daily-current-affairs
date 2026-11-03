from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from pipeline.collector import collect_window
from pipeline.windows import collect_window as shared_window

IST = ZoneInfo("Asia/Kolkata")


def test_daily_window_is_fixed_to_edition_date():
    # Historical edition: previous day 06:00 IST -> edition day 06:00 IST.
    start, end = collect_window("daily", "2026-10-05")
    assert (start.day, start.hour, end.day, end.hour) == (4, 6, 5, 6)
    assert (end - start) == timedelta(hours=24)


def test_late_run_does_not_shift_the_window(monkeypatch):
    monkeypatch.delenv("ALP_DAILY_CUTOFF", raising=False)
    late = datetime(2026, 11, 3, 9, 10, tzinfo=IST)       # the 2026-11-03 delayed cron
    start, end = shared_window("daily", "2026-11-03", now=late)
    assert start == datetime(2026, 11, 2, 6, 0, tzinfo=IST)
    assert end == datetime(2026, 11, 3, 6, 0, tzinfo=IST)


def test_early_generation_run_clips_end_to_run_time():
    early = datetime(2026, 11, 4, 2, 0, tzinfo=IST)
    start, end = shared_window("daily", "2026-11-04", now=early)
    assert end == early and start == datetime(2026, 11, 3, 6, 0, tzinfo=IST)


def test_window_starts_at_previous_edition_end_no_overlap():
    late = datetime(2026, 11, 3, 9, 10, tzinfo=IST)
    # Yesterday's reset run recorded 20:04 -> today starts there, never earlier.
    prev = datetime(2026, 11, 2, 20, 4, tzinfo=IST)
    start, end = shared_window("daily", "2026-11-03", previous_end=prev, now=late)
    assert start == prev and end == datetime(2026, 11, 3, 6, 0, tzinfo=IST)
    # Yesterday generated at 02:00 -> contiguous window from yesterday 02:00.
    prev = datetime(2026, 11, 2, 2, 0, tzinfo=IST)
    start, _ = shared_window("daily", "2026-11-03", previous_end=prev, now=late)
    assert start == prev


def test_stale_previous_end_is_ignored():
    late = datetime(2026, 11, 3, 9, 10, tzinfo=IST)
    prev = datetime(2026, 10, 30, 6, 0, tzinfo=IST)
    start, _ = shared_window("daily", "2026-11-03", previous_end=prev, now=late)
    assert start == datetime(2026, 11, 2, 6, 0, tzinfo=IST)


def test_cutoff_is_configurable(monkeypatch):
    monkeypatch.setenv("ALP_DAILY_CUTOFF", "05:30")
    start, end = shared_window("daily", "2026-10-05")
    assert (start.hour, start.minute, end.hour, end.minute) == (5, 30, 5, 30)


def test_weekly_window_monday():
    start, end = collect_window("weekly", "2026-10-05")  # Sunday
    assert start.weekday() == 0


def test_monthly_window():
    start, end = collect_window("monthly", "2026-10-01")
    assert start.day == 1 and end.month == 9
