import pandas as pd
import numpy as np
from scipy.stats import poisson
from es.detect import detect_frame
from es.aggregate import aggregate_frame

def test_causal_baseline_floor_and_streak():
    data=pd.DataFrame({"grp":"A|B","category":"fire_thermal","month":pd.date_range("2017-01-01",periods=10,freq="MS"),"n":[0]*6+[5,8,0,3],"total":10})
    result=detect_frame(data)
    assert result.baseline.iloc[:6].isna().all()
    assert result.baseline.iloc[6] == 0.5
    assert result.p_value.iloc[6] == poisson.sf(4,0.5)
    assert result.streak.iloc[6:9].tolist() == [1,2,0]
    assert result.baseline.iloc[7] == 5/7

def test_unique_ids_multilabel_and_zero_month():
    complaints=pd.DataFrame({"odino":["1","1","2"],"grp":["A|B"]*3,"ldate":["2018-01-03","2018-01-03","2018-03-04"]})
    labels=pd.DataFrame({"odino":["1","2"],"primary":["fire_thermal","other"],"secondary":[["fire_thermal","brakes"],[]]})
    counts=aggregate_frame(complaints,labels)
    assert counts.loc[counts.category=="fire_thermal","n"].tolist() == [1,0,0]
    assert counts.loc[counts.category=="brakes","n"].tolist() == [1,0,0]
    assert counts.loc[counts.category=="fire_thermal","total"].tolist() == [1,0,1]


def test_incomplete_label_coverage_fails_instead_of_counting_zero():
    import pytest
    complaints=pd.DataFrame({"odino":["1","2"],"grp":["A|B"]*2,"ldate":["2018-01-01"]*2})
    labels=pd.DataFrame({"odino":["1"],"primary":["other"],"secondary":[[]]})
    with pytest.raises(ValueError,match="Incomplete label coverage: 1"):
        aggregate_frame(complaints,labels)
    with pytest.raises(ValueError,match="Incomplete label coverage: 2"):
        aggregate_frame(complaints,labels.iloc[:0])


def test_detector_rejects_duplicate_or_missing_calendar_months():
    import pytest
    counts=pd.DataFrame({"grp":["A|B"]*2,"category":["other"]*2,"month":pd.to_datetime(["2018-01-01","2018-03-01"]),"n":[0,0],"total":[0,0]})
    with pytest.raises(ValueError,match="Missing calendar months"):
        detect_frame(counts)
    counts.loc[1,"month"]=counts.loc[0,"month"]
    with pytest.raises(ValueError,match="Duplicate monthly observation"):
        detect_frame(counts)
