import copy
import pytest
from es.brief import validate_brief,statistics_sentence,compose_brief

@pytest.fixture
def evidence_fixture():
    complaints={str(i):{"grp":"A|B","month":"2018-08-01","ldate":"2018-08-10","categories":["fire_thermal"]} for i in (11,12,13)}
    evidence={"n":3,"ids":["11","12","13"],"agg":{"fire":1,"smoke":2,"driving":1,"parked":0,"crash":0,"injury":0,"severe":0},"co":[],"years":[["2013",3]]}
    expected={"n":3,"baseline":0.5,"ratio":6.0,"streak":1}
    return complaints,evidence,expected

def checked(text,fixture,**extra):
    complaints,evidence,counts=fixture
    return validate_brief(text,evidence,complaints,grp="A|B",category="fire_thermal",month="2018-08-01",expected_counts=counts,**extra)

VALID=statistics_sentence("A|B","fire_thermal",{"n":3,"baseline":0.5,"ratio":6.0,"streak":1})+" 연기가 언급됐습니다(#11, #12)."

def test_valid_numbers_and_citations(evidence_fixture):
    assert checked(VALID,evidence_fixture)==VALID

@pytest.mark.parametrize("text,reason",[(VALID.replace("#12","#99"),"outside_evidence"),(VALID.replace("신고 3건","신고 4건"),"statistics_template"),(VALID.replace("월 0.5건","월 5건"),"statistics_template"),(VALID+" 사망 7명(#11).","unsupported_narrative_number"),(VALID+" 결함으로 확정됐습니다(#11).","unsupported_conclusion")])
def test_invalid_brief_is_rejected(text,reason,evidence_fixture):
    with pytest.raises(ValueError,match=reason): checked(text,evidence_fixture)

def test_excluded_or_future_complaint_suppresses_whole_brief(evidence_fixture):
    with pytest.raises(ValueError,match="excluded_evidence"):
        checked(VALID,evidence_fixture,excluded=["12"])
    fixture=copy.deepcopy(evidence_fixture)
    fixture[0]["11"]["ldate"]="2018-09-01"
    with pytest.raises(ValueError,match="future_evidence"):
        checked(VALID,fixture)
    fixture=copy.deepcopy(evidence_fixture)
    fixture[1]["n"]=4
    with pytest.raises(ValueError,match="evidence_count"):
        checked(VALID,fixture)


def test_ratio_and_streak_cannot_borrow_another_valid_number(evidence_fixture):
    with pytest.raises(ValueError,match="unsupported_narrative_number"):
        checked(VALID+" 평소 대비 3배(#11).",evidence_fixture)
    with pytest.raises(ValueError,match="unsupported_narrative_number"):
        checked(VALID+" 연속 경보 2개월(#11).",evidence_fixture)


@pytest.mark.parametrize("claim",["부상 1명(#11).","사망 1명(#11).","부상 한 명(#11)."])
def test_counts_cannot_be_borrowed_from_fire_or_other_metrics(claim,evidence_fixture):
    with pytest.raises(ValueError,match="unsupported_narrative_number"):
        checked(VALID+" "+claim,evidence_fixture)

def test_previous_month_date_cannot_hide_behind_current_month_metadata(evidence_fixture):
    fixture=copy.deepcopy(evidence_fixture)
    fixture[0]["11"]["ldate"]="2018-07-31"
    with pytest.raises(ValueError,match="outside_month_evidence"):
        checked(VALID,fixture)
