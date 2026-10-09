import pandas as pd
from es.backtest import evaluate_one

def signal(month):
    return pd.DataFrame({"grp":["A|B"],"category":["fire_thermal"],"month":[pd.Timestamp(month)],"n":[5],"baseline":[0.5],"p_value":[0.0001],"alert":[True]})

def test_next_month_availability_and_last_month_exclusion():
    result=evaluate_one(signal("2020-02-01"),["A|B"],["fire_thermal"],"2020-03-15",window_basis="available_date")
    assert result["result"]=="early" and result["lead_days"]==14
    assert result["primary_hit"] is False
    assert evaluate_one(signal("2020-01-01"),["A|B"],["fire_thermal"],"2020-03-15",window_basis="available_date")["primary_hit"] is True
    result=evaluate_one(signal("2020-02-01"),["A|B"],["fire_thermal"],"2020-03-01",window_basis="available_date")
    assert result["result"]=="late" and result["lead_days"]==0

def test_available_lower_boundary_is_inclusive_main_upper_exclusive():
    assert evaluate_one(signal("2019-02-01"),["A|B"],["fire_thermal"],"2020-03-01",window_basis="available_date")["primary_hit"] is True
    assert evaluate_one(signal("2020-01-01"),["A|B"],["fire_thermal"],"2020-03-01",window_basis="available_date")["primary_hit"] is False


def test_registered_month_window_preserved_and_lead_uses_availability():
    result=evaluate_one(signal("2020-02-01"),["A|B"],["fire_thermal"],"2020-03-15")
    assert result["primary_hit"] is True
    assert result["result"]=="early" and result["lead_days"]==14
    result=evaluate_one(signal("2020-03-01"),["A|B"],["fire_thermal"],"2020-03-15")
    assert result["primary_hit"] is False
    assert result["result"]=="late" and result["lead_days"]==-17


def test_incomplete_last_scope_month_is_excluded():
    result=evaluate_one(signal("2020-09-01"),["A|B"],["fire_thermal"],"2020-03-15")
    assert result["result"]=="missed"
