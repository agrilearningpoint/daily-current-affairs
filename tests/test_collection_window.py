from pipeline.collector import collect_window
from datetime import datetime
import pytz
TZ=pytz.timezone("Asia/Kolkata")
def test_daily_window():
    start,end=collect_window("daily","2026-10-05")
    assert start.day == 4 and end.day == 4
    assert start.hour == 0 and end.hour == 23
    assert (end - start).total_seconds() == 86400 - 0.000001
def test_weekly_window_monday():
    start,end=collect_window("weekly","2026-10-05") # Sunday
    assert start.weekday()==0
def test_monthly_window():
    start,end=collect_window("monthly","2026-10-01")
    assert start.day==1 and end.month==9
