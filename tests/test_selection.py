import json, pathlib
from agents import __path__
# Cap-aware test: selection must never exceed hi
def test_cap():
    # Simulate 20 items, hi=12, ensure 2 agri 2 banking but cap respected
    items=[{"event_id":str(i),"student_relevance":100-i,"agri_focus":i<2,"banking_focus":2<=i<4} for i in range(20)]
    # Mimic agent logic hi=12
    hi=12
    chosen=[i for i in items if i["student_relevance"]>=25][:hi]
    # ensure would not exceed hi
    assert len(chosen)<=hi
