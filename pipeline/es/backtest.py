"""Evaluate fixed registration pool. Outcome dates are used only here."""
import json
import pandas as pd
from .scope import load_pool,case_groups

WINDOW_BASIS="alert_month"

def evaluate_one(detections,groups,targets,odate,window_basis="alert_month"):
    date=pd.Timestamp(odate)
    lower=date-pd.DateOffset(months=12)
    upper=date+pd.DateOffset(months=6)
    main_upper=date-pd.DateOffset(months=1)
    matching=detections.loc[detections.grp.isin(groups)&detections.category.isin(targets)&detections.alert].copy()
    matching["available"]=pd.to_datetime(matching.month)+pd.offsets.MonthBegin(1)
    basis=matching.available if window_basis=="available_date" else pd.to_datetime(matching.month)
    main=matching.loc[(basis>=lower)&(basis<main_upper)]
    candidates=matching.loc[(basis>=lower)&(basis<=upper)&(matching.available<=upper)].sort_values(["available","grp","category"])
    if candidates.empty:
        return {"result":"missed","lead_days":None,"first_alert":None,"primary_hit":not main.empty}
    first=candidates.iloc[0]
    lead=int((date-first.available).days)
    return {"result":"early" if lead>0 else "late","lead_days":lead,
            "first_alert":{"grp":first.grp,"category":first.category,"month":pd.Timestamp(first.month).strftime("%Y-%m-%d"),"available":first.available.strftime("%Y-%m-%d"),"n":int(first.n),"baseline":float(first.baseline),"p_value":float(first.p_value)},"primary_hit":not main.empty}

def workload(detections,groups,odate,window_basis="alert_month"):
    date=pd.Timestamp(odate)
    basis=pd.to_datetime(detections.month)
    if window_basis=="available_date":
        basis=basis+pd.offsets.MonthBegin(1)
    window=detections.loc[detections.grp.isin(groups)&(basis>=date-pd.DateOffset(months=12))&(basis<date-pd.DateOffset(months=1))]
    denominator=len(window[["grp","month"]].drop_duplicates())
    return {"alerts":int(window.alert.sum()),"group_months":denominator}

def evaluate(detections,pool,window_basis="alert_month"):
    cases=[]; controls=[]
    registry={case["case_id"]:case for case in pool["cases"]}
    for case in pool["cases"]:
        groups=case_groups(case)
        cases.append({"case_id":case["case_id"],"investigation":case["investigation"],"title":case["note"],"groups":groups,"target_categories":case["target_categories"],"odate":case["odate"],"split":case["split"],**evaluate_one(detections,groups,case["target_categories"],case["odate"],window_basis),"workload":workload(detections,groups,case["odate"],window_basis)})
    for i,control in enumerate(pool["controls"]):
        matched=registry[control["matched_to"]]
        controls.append({"control_id":f"control-{i+1:02d}","group":control["group"],"matched_to":control["matched_to"],"odate":control["ref_date"],"split":matched["split"],"target_categories":matched["target_categories"],**evaluate_one(detections,[control["group"]],matched["target_categories"],control["ref_date"],window_basis),"workload":workload(detections,[control["group"]],control["ref_date"],window_basis)})
    summary={}
    for split in ("dev","holdout"):
        summary[split]={}
        for name,items in (("cases",cases),("controls",controls)):
            subset=[x for x in items if x["split"]==split]
            alerts=sum(x["workload"]["alerts"] for x in subset)
            denominator=sum(x["workload"]["group_months"] for x in subset)
            summary[split][name]={"hits":sum(x["primary_hit"] for x in subset),"total":len(subset),"alerts":alerts,"group_months":denominator,"alerts_per_group_month":alerts/denominator if denominator else None}
    return {"evaluation_window_basis":window_basis,"primary_window":f"{window_basis} >= odate-12 calendar months AND {window_basis} < odate-1 calendar month","first_signal_window":f"{window_basis} >= odate-12 calendar months AND {window_basis} <= odate+6 calendar months","completed_month_constraint":"available <= odate+6 calendar months (scope receipt end)","summary":summary,"cases":cases,"controls":controls}

def verify_lookahead(con,config,method="kw"):
    """Recompute the full monitoring universe at every registered case cutoff."""
    from .aggregate import aggregate_frame
    from .detect import detect_frame
    import time
    started=time.monotonic()
    source="scoped" if method=="kw" else "demo"
    complaints=con.execute(f"SELECT odino,grp,ldate FROM {source}").fetchdf()
    labels=con.execute(f"SELECT * FROM labels_{method}").fetchdf()
    full=con.execute(f"SELECT * FROM detections_{method}").fetchdf()
    results=[]
    for case in load_pool(config)["cases"]:
        cutoff=pd.Timestamp(case["odate"]).to_period("M").start_time-pd.Timedelta(days=1)
        actual=detect_frame(aggregate_frame(complaints,labels,as_of=cutoff),config)
        expected=full.loc[pd.to_datetime(full.month)<=cutoff].reset_index(drop=True)
        pd.testing.assert_frame_equal(actual,expected,check_exact=True)
        results.append({"case_id":case["case_id"],"cutoff":str(cutoff.date()),"cells":len(actual),"equal":True})
    result={"method":method,"complete_month_cutoffs":len(results),"exact_match":True,"elapsed_s":round(time.monotonic()-started,2),"results":results}
    path=config.root/"data"/"results"/f"lookahead_{method}.json"
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    return {"complete_month_cutoffs":len(results),"exact_match":True}

def run(con,config,args=None):
    method=getattr(args,"method","kw")
    detections=con.execute(f"SELECT * FROM detections_{method}").fetchdf()
    pool=load_pool(config)
    result=evaluate(detections,pool)
    sensitivity=evaluate(detections,pool,"available_date")
    result["available_date_sensitivity"]={"evaluation_window_basis":"available_date","primary_window":sensitivity["primary_window"],"summary":sensitivity["summary"]}
    single_cases=[case for case in pool["cases"] if len(case_groups(case))==1]
    single_ids={case["case_id"] for case in single_cases}
    single_pool={"cases":single_cases,"controls":[control for control in pool["controls"] if control["matched_to"] in single_ids]}
    single=evaluate(detections,single_pool)
    sensitivity_path=config.root/"data"/"results"/f"sensitivity_single_group_{method}.json"
    sensitivity_path.parent.mkdir(parents=True,exist_ok=True)
    sensitivity_path.write_text(json.dumps(single,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    result["single_group_sensitivity"]={"evaluation_window_basis":"alert_month","cases":{"hits":sum(x["primary_hit"] for x in single["cases"]),"total":len(single["cases"])},"controls":{"hits":sum(x["primary_hit"] for x in single["controls"]),"total":len(single["controls"])}}
    result["method"]=method
    result["rule"]={"baseline_months":config.baseline_months,"minimum_history":config.minimum_history,"baseline_floor":config.baseline_floor,"alpha":config.alpha,"minimum_count":config.minimum_count}
    path=config.root/"data"/f"backtest_{method}.json"
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    verification=verify_lookahead(con,config,method) if getattr(args,"verify_lookahead",False) else None
    return {"lookahead":verification,"method":method,"summary":result["summary"],"representatives":[x for x in result["cases"] if x["case_id"] in ("PE19003","PE19004","PE20016")],"output":str(path.relative_to(config.root))}
