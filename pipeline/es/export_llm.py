"""Complete demo LLM export; the registered keyword backtest stays independent."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import pandas as pd
from .aggregate import aggregate_frame
from .backtest import evaluate_one
from .config import CATEGORIES
from .detect import detect_frame
from .export import CONTRACT, FLAGS, MONTHS, build_console, date_string, flags_for, key, series_for, write_json, run_keyword
from .import_llm import load_complete, read_records
from .label_llm import digest
from .privacy import public_text, sensitive_values
from .brief import load_validated_briefs

REPRESENTATIVES={"PE19003","PE19004","PE20016"}


def bounded_demo(detections):
    bolt=detections.grp=="CHEVROLET|BOLT EV"
    return detections.loc[(bolt&(detections.month>=pd.Timestamp("2018-10-01"))&(detections.month<pd.Timestamp("2021-02-01")))|(~bolt&(detections.month>=pd.Timestamp("2017-03-01"))&(detections.month<pd.Timestamp("2019-07-01")))].reset_index(drop=True)


def case_detail(con,source,detections,item):
    bolt=item["case_id"]=="PE20016"
    start="2018-10-01" if bolt else "2017-03-01"
    end="2021-02-01" if bolt else "2019-07-01"
    complete_end=min(pd.Timestamp(end),pd.Timestamp(item["odate"])+pd.DateOffset(months=6))
    selected=detections.loc[detections.grp.isin(item["groups"])&(detections.month>=pd.Timestamp(start))&((detections.month+pd.offsets.MonthBegin(1))<=complete_end)]
    alerts=[]
    for row in selected.loc[selected.alert].itertuples(index=False):
        matching=source.loc[(source.grp==row.grp)&(source.month==row.month)]
        matching=matching.loc[matching.apply(lambda x:row.category in [x['primary'],*list(x.secondary)],axis=1)].copy()
        matching["review_flags"]=matching.apply(lambda x:flags_for(x,"llm"),axis=1)
        matching["review_order"]=matching.apply(lambda x:(-int("fire" in x.review_flags),-int("injury" in x.review_flags),-int("crash" in x.review_flags),-int(x.severity),str(x.odino)),axis=1)
        matching=matching.sort_values("review_order").head(10)
        denied=sensitive_values(con,matching.odino.astype(str).tolist())
        evidence=[{"odino":str(x.odino),"ldate":date_string(x.ldate),"fire":"fire" in x.review_flags,"crash":"crash" in x.review_flags,"injured":int(x.injured),"summary_ko":x.summary_ko,"snippet":public_text(x.text,300,denied=denied[str(x.odino)])} for x in matching.itertuples(index=False)]
        month=date_string(row.month)
        alerts.append({"id":key(row.grp,row.category,month),"grp":row.grp,"category":row.category,"month":month,"observed":int(row.n),"baseline":float(row.baseline),"p_value":float(row.p_value),"is_target":row.category in item["target_categories"],"available":date_string(row.month+pd.offsets.MonthBegin(1)),"brief":None,"evidence":evidence})
    detail={"contract":CONTRACT,"case_id":item["case_id"],"labeler":"llm","odate":item["odate"],"target_categories":item["target_categories"],"groups":series_for(selected,item["groups"],CATEGORIES,start,end),"alerts":alerts,"coverage":{"source":"demo","start":start,"end_exclusive":end,"registered_window_complete":False}}
    return detail,evaluate_one(selected,item["groups"],item["target_categories"],item["odate"])


def estimated_cost_per_1k(config,labels):
    # Count all attempts across runs for the current cache/input keys, including
    # paid validation failures preceding a later success. Old unlinked ledgers
    # cannot safely establish this total and therefore remain unknown.
    keys=set(labels.cache_key)
    odinos=set(labels.odino)
    models=set(labels.model)
    relevant=[u for u in read_records(config.root/"data/labels/llm_usage.jsonl") if u.get("odino") in odinos and u.get("model") in models]
    if any(not u.get("cache_key") for u in relevant):
        return None
    usages=[u for u in relevant if u["cache_key"] in keys]
    if {u["cache_key"] for u in usages}!=keys or any(u.get("estimated_usd") is None for u in usages):
        return None
    return sum(u["estimated_usd"] for u in usages)/len(labels)*1000


def prepare(con,config):
    labels,provenance=load_complete(con,config)
    complaints=con.execute("SELECT * FROM demo").fetchdf()
    complaints["odino"]=complaints.odino.astype(str)
    source=complaints.merge(labels,on="odino",how="inner",validate="one_to_one")
    detections=bounded_demo(detect_frame(aggregate_frame(complaints,labels),config))
    keyword=con.execute('SELECT odino,"primary",secondary FROM labels_kw').fetchdf()
    keyword["odino"]=keyword.odino.astype(str)
    keyword=keyword.loc[keyword.odino.isin(labels.odino)]
    # Identical complaint population and observation history for this comparison.
    keyword_detections=bounded_demo(detect_frame(aggregate_frame(complaints,keyword),config))
    merged=labels[["odino","primary"]].merge(keyword[["odino","primary"]],on="odino",suffixes=("_llm","_kw"),validate="one_to_one")
    if len(merged)!=len(labels):
        raise ValueError("Incomplete keyword comparison coverage")
    sample_ids=sorted(merged.odino,key=lambda value:digest("seed42:"+value))[:60]
    sample=merged.set_index("odino").loc[sample_ids]
    comparison={"scope":"same demo complaints; not the registered 38-case backtest","population":len(labels),"model":provenance["model"],"prompt_hash":provenance["prompt_hash"],"primary_agreement":{"agree":int((merged.primary_llm==merged.primary_kw).sum()),"n":len(merged)},"sample_agreement":{"agree":int((sample.primary_llm==sample.primary_kw).sum()),"n":len(sample)},"detector_cells":{"keyword":len(keyword_detections),"llm":len(detections)},"alert_cells":{"keyword":int(keyword_detections.alert.sum()),"llm":int(detections.alert.sum())},"cases":[],"human_check":{"n":0,"kw_correct":None,"llm_correct":None}}
    return source,labels,detections,keyword_detections,provenance,comparison


def run(con,config,args=None):
    # Completion/privacy/provenance guards run before any output mutation.
    source,labels,detections,keyword_detections,provenance,comparison=prepare(con,config)
    output=Path(getattr(args,"output",None) or config.root/"web/public/data")
    output.parent.mkdir(parents=True,exist_ok=True)
    measured=json.loads((config.root/"data/backtest_kw.json").read_text())
    console=build_console(con,detections,source,"llm")
    console["briefs"]=load_validated_briefs(console,root=config.root,
        denied_by_id=sensitive_values(con,console["complaints"]))
    details={}
    for item in measured["cases"]:
        if item["case_id"] not in REPRESENTATIVES:
            continue
        detail,result=case_detail(con,source,detections,item)
        details[item["case_id"]]=detail
        start=detail["coverage"]["start"]; end=detail["coverage"]["end_exclusive"]
        kw_selected=keyword_detections.loc[(keyword_detections.month>=pd.Timestamp(start))&((keyword_detections.month+pd.offsets.MonthBegin(1))<=pd.Timestamp(end))]
        kw_result=evaluate_one(kw_selected,item["groups"],item["target_categories"],item["odate"])
        comparison["cases"].append({"case_id":item["case_id"],"coverage":detail["coverage"],"keyword":kw_result,"llm":result})
        first=result["first_alert"]
        console["reveal"]["cases"].append({"case_id":item["case_id"],"make":item["groups"][0].split("|")[0],"title":item["title"],"odate":item["odate"],"first_alert_month":first["month"] if first else None,"first_alert_grp":first["grp"] if first else None,"first_alert_category":first["category"] if first else None,"available":first["available"] if first else None,"lead_days":result["lead_days"],"groups":item["groups"]})
    console["assumptions"].append("LLM 사후 비교는 demo 관측 기간에 한정됩니다. 38사례 주 검증은 키워드 기준선입니다.")
    with tempfile.TemporaryDirectory(prefix="earlysignal-export-",dir=output.parent) as temporary:
        stage=Path(temporary)
        run_keyword(con,config,SimpleNamespace(method="kw",output=stage))
        meta=json.loads((stage/"meta.json").read_text())
        meta["labels"].update({"llm_model":provenance["model"],"llm_labeled":len(labels),"sample_agreement":comparison["sample_agreement"],"cost_per_1k_usd":estimated_cost_per_1k(config,labels)})
        meta["validation_notes"][-1]="38사례·36대조 주 검증과 검토 업무량은 키워드 기준선입니다. 콘솔의 LLM은 전체 demo를 사용하며, 사람 정답 검수는 미완료입니다."
        cases=json.loads((stage/"cases.json").read_text())
        for item in cases["cases"]:
            item["has_llm"]=item["case_id"] in details
        write_json(stage/"console.json",console,"console")
        write_json(stage/"meta.json",meta,"meta")
        write_json(stage/"cases.json",cases,"cases")
        for case_id,detail in details.items():
            write_json(stage/f"cases_llm/{case_id}.json",detail,"case")
        manifest=json.loads((stage/"completion.json").read_text())
        manifest.update({"labeler":"llm","complaints":len(console["complaints"]),"evidence_cells":len(console["evidence"]),"briefs":len(console["briefs"])})
        manifest["files"]=sorted([str(path.relative_to(stage)) for path in stage.rglob("*.json") if path.name!="completion.json"])
        manifest["file_sha256"]={name:hashlib.sha256((stage/name).read_bytes()).hexdigest() for name in manifest["files"]}
        write_json(stage/"completion.json",manifest,"completion")
        output.mkdir(parents=True,exist_ok=True)
        # Manifest goes last so an interrupted publish never claims completion.
        for name in [*manifest["files"],"completion.json"]:
            target=output/name; target.parent.mkdir(parents=True,exist_ok=True)
            os.replace(stage/name,target)
    report=config.root/"data/results/llm_demo_comparison.json"
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(comparison,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    comparison_labels=source[["odino","grp","month","ldate","summary_ko"]].merge(con.execute('SELECT odino,"primary" AS kw_primary FROM labels_kw').fetchdf().astype({"odino":str}),on="odino",validate="one_to_one").merge(labels[["odino","primary"]].rename(columns={"primary":"llm_primary"}),on="odino",validate="one_to_one")
    sample_ids=sorted(labels.odino,key=lambda value:digest("seed42:"+value))[:60]
    comparison_labels=comparison_labels.set_index("odino").loc[sample_ids].reset_index()
    denied=sensitive_values(con,sample_ids)
    source_by_id=source.set_index("odino")
    comparison_labels["snippet"]=[public_text(source_by_id.loc[odino,"text"],520,denied=denied[odino]) for odino in sample_ids]
    comparison_labels["human_gold"]=""
    comparison_labels["human_notes"]=""
    comparison_labels.to_csv(config.root/"data/labels/sample60_compare.csv",index=False)
    return {"output":str(output),"files":len(manifest["files"])+1,"console_complaints":len(console["complaints"]),"evidence_cells":len(console["evidence"]),"labeler":"llm","labeled":len(labels),"briefs":len(console["briefs"]),"main_validation_labeler":"keyword","comparison":str(report)}
