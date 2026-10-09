"""Verify exported numbers and dates against the public evidence ledger."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import duckdb
import pandas as pd
from es.config import Config
from es.export import FLAGS, MONTHS, schema_validate
from es.privacy import privacy_matches, sensitive_values

ROOT=Config().root
OUT=ROOT/"web/public/data"
FORBIDDEN={"vin","city","state","dealer_name","dealer_tel","dealer_city","dealer_state","dealer_zip","vehicle_operator"}

def load(name):
    return json.loads((OUT/name).read_text())

def scan_fields(value):
    if isinstance(value,dict):
        assert not (set(k.lower() for k in value)&FORBIDDEN)
        for child in value.values(): scan_fields(child)
    elif isinstance(value,list):
        for child in value: scan_fields(child)

def test_all_export_files_schemas_and_completion_checksums():
    completion=load("completion.json")
    schema_validate(completion,"completion")
    assert len(completion["files"])==(44 if completion["labeler"]=="llm" else 41)
    actual_files={str(path.relative_to(OUT)) for path in OUT.rglob("*.json") if path.name!="completion.json"}
    assert actual_files==set(completion["files"])
    for name in completion["files"]:
        item=load(name)
        schema_validate(item,"case" if name.startswith(("cases/","cases_llm/")) else Path(name).stem)
        scan_fields(item)
        assert hashlib.sha256((OUT/name).read_bytes()).hexdigest()==completion["file_sha256"][name]
    assert completion["cases"]==38

def test_console_evidence_joins_counts_flags_and_months():
    console=load("console.json")
    assert console["asof_months"]==MONTHS
    assert console["default_asof"] in MONTHS
    assert len(console["groups"])==9
    assert set(console["snapshots"])==set(MONTHS)
    complaints=console["complaints"]
    for month,ids in console["pile"].items():
        assert len(ids)==len(set(ids))
        assert set(ids)=={odino for odino,x in complaints.items() if x["month"]==month}
    for cell,evidence in console["evidence"].items():
        grp,category,month=cell.rsplit(":",2)
        expected={odino for odino,x in complaints.items() if x["grp"]==grp and x["month"]==month and category in x["categories"]}
        assert set(evidence["ids"])==expected
        assert evidence["n"]==len(expected)>=3
        assert evidence["agg"]=={flag:sum(flag in complaints[odino]["flags"] for odino in expected) for flag in FLAGS}
        years=Counter(complaints[odino]["year"] for odino in expected)
        assert evidence["years"]==[[year,n] for year,n in sorted(years.items(),key=lambda x:(-x[1],x[0]))]
        co=Counter(cat for odino in expected for cat in complaints[odino]["categories"] if cat!=category)
        assert evidence["co"]==[[cat,n] for cat,n in sorted(co.items(),key=lambda x:(-x[1],x[0]))[:3]]
    for month,snapshot in console["snapshots"].items():
        assert snapshot["kpi"]["complaints"]==len(console["pile"][month])
        assert snapshot["kpi"]["alerts"]==len(snapshot["alerts"])
        assert snapshot["alerts"]==sorted(snapshot["alerts"],key=lambda x:(-x["ratio"],x["grp"],x["category"]))
        for alert in snapshot["alerts"]:
            evidence=console["evidence"][f"{alert['grp']}:{alert['category']}:{month}"]
            assert alert["n"]==evidence["n"]
            assert alert["ratio"]==alert["n"]/alert["baseline"]
            series=console["series"][alert["grp"]]
            index=series["months"].index(month)
            category=series["categories"][alert["category"]]
            assert category["n"][index]==alert["n"]
            assert category["baseline"][index]==alert["baseline"]
            assert category["alert"][index] is True
            assert set(alert["comove"])=={other["grp"] for other in snapshot["alerts"] if other["category"]==alert["category"] and other["grp"]!=alert["grp"]}

def test_no_future_actual_values_in_operational_series_and_no_fake_llm():
    console=load("console.json")
    for item in console["series"].values():
        assert all(month<=MONTHS[-1] for month in item["months"])
        assert len(item["total"])==len(item["months"])
        for values in item["categories"].values():
            assert all(len(values[name])==len(item["months"]) for name in ("n","baseline","alert"))
    for item in console["reveal"]["series_after"].values():
        assert all(month>MONTHS[-1] for month in item["months"])
    for item in console["complaints"].values():
        assert item["month"] in MONTHS
        assert item["ldate"][:7]==item["month"][:7]
        assert item["grp"] in console["groups"]
        assert item["label_source"]==console["labeler"]
        if console["labeler"]=="keyword":
            assert item["summary_ko"] is None and item["severity"] is None
    if console["labeler"]=="keyword":
        assert console["briefs"]=={}
        labels=load("meta.json")["labels"]
        assert labels["llm_model"] is None and labels["llm_labeled"]==0
        assert labels["human_check"]["n"]==0
        assert labels["human_check"]["kw_correct"] is None
        assert labels["cost_per_1k_usd"] is None

def test_public_fragments_hide_known_identifiers_and_sensitive_patterns():
    console=load("console.json")
    all_items=[(odino,text) for odino,x in console["complaints"].items() for text in (x["text"],x["summary_ko"] or "")]
    for item in load("completion.json")["files"]:
        if item.startswith(("cases/","cases_llm/")):
            all_items.extend((e["odino"],text) for a in load(item)["alerts"] for e in a["evidence"] for text in (e["snippet"],e["summary_ko"] or ""))
    known={}
    if Config().database.exists():
        with duckdb.connect(str(Config().database),read_only=True) as con:
            known=sensitive_values(con,[odino for odino,_ in all_items])
    for odino,text in all_items:
        assert not privacy_matches(text,known.get(odino,[]))

def test_case_result_leads_are_from_next_month_and_all_failures_remain():
    cases=load("cases.json")["cases"]
    assert len(cases)==38
    assert sum(case["split"]=="dev" for case in cases)==19
    assert sum(case["split"]=="holdout" for case in cases)==19
    for case in cases:
        if case["first_alert_month"] is None:
            assert case["result"]=="missed" and case["lead_days"] is None
        else:
            available=pd.Timestamp(case["first_alert_month"])+pd.offsets.MonthBegin(1)
            lead=(pd.Timestamp(case["odate"])-available).days
            assert case["lead_days"]==lead
            assert case["result"]==("early" if lead>0 else "late")
        detail=load(f"cases/{case['case_id']}.json")
        scope_end=pd.Timestamp(case["odate"])+pd.DateOffset(months=6)
        assert all(pd.Timestamp(a["available"])<=scope_end for a in detail["alerts"])
