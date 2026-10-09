import pandas as pd
import pytest
from es.aggregate import aggregate_frame
from es.detect import detect_frame

@pytest.mark.parametrize("cutoff",["2017-07-31","2017-12-31","2018-03-15","2018-08-31"])
def test_receipt_cutoff_equals_full_detection_for_completed_months(cutoff):
    rows=[]
    for i,month in enumerate(pd.date_range("2017-01-01",periods=24,freq="MS")):
        for j in range(1 if i<6 else 6):
            rows.append((f"{i}-{j}","A|B",month+pd.Timedelta(days=j+1)))
    complaints=pd.DataFrame(rows,columns=["odino","grp","ldate"])
    # Trap: event dates, component classes and retrospective fields cannot matter.
    complaints["faildate"]="2000-01-01"
    complaints["compdesc_list"]="RETROSPECTIVE"
    labels=pd.DataFrame({"odino":complaints.odino,"primary":"fire_thermal","secondary":[[] for _ in rows]})
    full=detect_frame(aggregate_frame(complaints,labels))
    bounded=detect_frame(aggregate_frame(complaints,labels,as_of=cutoff))
    cutoff_date=pd.Timestamp(cutoff)
    completed_end=(cutoff_date+pd.offsets.MonthEnd(0))
    if cutoff_date != completed_end:
        completed_end=cutoff_date.to_period("M").start_time-pd.Timedelta(days=1)
    expected=full.loc[full.month<=completed_end].reset_index(drop=True)
    actual=bounded.loc[bounded.month<=completed_end].reset_index(drop=True)
    pd.testing.assert_frame_equal(actual,expected,check_exact=True)

def test_midmonth_does_not_count_later_receipts():
    c=pd.DataFrame({"odino":["a","b"],"grp":["A|B"]*2,"ldate":["2018-03-10","2018-03-25"]})
    labels=pd.DataFrame({"odino":["a","b"],"primary":["fire_thermal"]*2,"secondary":[[],[]]})
    bounded=aggregate_frame(c,labels,as_of="2018-03-15")
    assert bounded.loc[bounded.category=="fire_thermal","n"].tolist()==[1]
