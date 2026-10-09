"""Static export with explicit label provenance and conservative public fragments."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import pandas as pd
from .config import CATEGORIES, DEMO_GROUPS
from .privacy import public_text, sensitive_values

CONTRACT="earlysignal-data-v1"
MONTHS=[x.strftime("%Y-%m-%d") for x in pd.date_range("2018-03-01","2018-10-01",freq="MS")]
DISPLAY_CATEGORIES=("fire_thermal","engine_failure","engine_stall","loss_of_power","electrical_failure","lighting","airbag","steering","brakes")
FLAGS=("fire","smoke","driving","parked","crash","injury","severe")
FLAG_SOURCES={"fire":"NHTSA FIRE", "crash":"NHTSA CRASH", "injury":"NHTSA INJURED", "smoke":"keyword", "driving":"keyword", "parked":"keyword", "severe":"unmeasured"}
FLAG_PATTERNS={"smoke":re.compile(r"\bsmok(?:e|ing|ed)\b",re.I),"driving":re.compile(r"\b(?:driving|drove|while\s+(?:traveling|travelling)|highway|interstate)\b",re.I),"parked":re.compile(r"\b(?:parked|parking|charging)\b",re.I)}

def clean_float(value):
    return float(value) if value is not None and math.isfinite(float(value)) else None

def date_string(value):
    return pd.Timestamp(value).strftime("%Y-%m-%d")

def key(grp,category,month):
    return f"{grp}:{category}:{month}"

def flags_for(row,labeler="keyword"):
    flags=[]
    if row.fire: flags.append("fire")
    if row.crash: flags.append("crash")
    if row.injured>0: flags.append("injury")
    if labeler=="llm":
        mapping={"fire":"fire","smoke":"smoke","crash":"crash","injury":"injury","driving":"while_driving","parked":"while_parked_or_charging"}
        flags.extend(flag for flag,hazard in mapping.items() if getattr(row,f"hazard_{hazard}"))
        if row.severity>=3: flags.append("severe")
    else:
        flags.extend(flag for flag,pattern in FLAG_PATTERNS.items() if pattern.search(row.text or ""))
    return [flag for flag in FLAGS if flag in flags]

def series_for(detections, groups, categories, start, end):
    result={}
    for grp in groups:
        selected=detections.loc[(detections.grp==grp)&(detections.month>=pd.Timestamp(start))&(detections.month<=pd.Timestamp(end))]
        months=sorted(selected.month.unique())
        if not months:
            result[grp]={"months":[],"total":[],"categories":{cat:{"n":[],"baseline":[],"alert":[]} for cat in categories}}
            continue
        lookup=selected.set_index(["category","month"])
        totals=selected.drop_duplicates("month").set_index("month").total
        result[grp]={"months":[date_string(m) for m in months],"total":[int(totals[m]) for m in months],"categories":{cat:{"n":[int(lookup.loc[(cat,m),"n"]) for m in months],"baseline":[clean_float(lookup.loc[(cat,m),"baseline"]) for m in months],"alert":[bool(lookup.loc[(cat,m),"alert"]) for m in months]} for cat in categories}}
    return result

def build_evidence(complaints):
    buckets=defaultdict(list)
    for odino,item in complaints.items():
        for category in item["categories"]:
            buckets[key(item["grp"],category,item["month"])].append(odino)
    result={}
    for cell,ids in sorted(buckets.items()):
        if len(ids)<3: continue
        category=cell.rsplit(":",2)[1]
        ids=sorted(ids,key=lambda odino:(-int("fire" in complaints[odino]["flags"]),-int("injury" in complaints[odino]["flags"]),-int("crash" in complaints[odino]["flags"]),-(complaints[odino]["severity"] or 0),odino))
        agg={flag:sum(flag in complaints[odino]["flags"] for odino in ids) for flag in FLAGS}
        co=Counter(cat for odino in ids for cat in complaints[odino]["categories"] if cat!=category)
        years=Counter(complaints[odino]["year"] for odino in ids)
        result[cell]={"n":len(ids),"agg":agg,"co":[[cat,n] for cat,n in sorted(co.items(),key=lambda x:(-x[1],x[0]))[:3]],"years":[[year,n] for year,n in sorted(years.items(),key=lambda x:(-x[1],x[0]))],"ids":ids}
    return result

def build_console(con,detections,source,labeler="keyword"):
    selected=source.loc[source.grp.isin(DEMO_GROUPS)&(source.month>=pd.Timestamp(MONTHS[0]))&(source.month<=pd.Timestamp(MONTHS[-1]))]
    denied=sensitive_values(con,selected.odino.astype(str).to_list())
    complaints={}
    for row in selected.sort_values(["ldate","odino"]).itertuples(index=False):
        odino=str(row.odino)
        complaints[odino]={"grp":row.grp,"month":date_string(row.month),"ldate":date_string(row.ldate),"year":str(row.year or ""),"flags":flags_for(row,labeler),"categories":list(dict.fromkeys([row.primary,*list(row.secondary)])),"severity":int(row.severity) if labeler=="llm" else None,"injured":int(row.injured),"summary_ko":row.summary_ko if labeler=="llm" else None,"text":public_text(row.text,520,denied=denied[odino]),"label_source":labeler}
    pile={month:[odino for odino,item in complaints.items() if item["month"]==month] for month in MONTHS}
    evidence=build_evidence(complaints)
    monitor=detections.loc[detections.grp.isin(DEMO_GROUPS)&detections.category.isin(DISPLAY_CATEGORIES)]
    snapshots={}
    for month in MONTHS:
        timestamp=pd.Timestamp(month)
        current=monitor.loc[monitor.month==timestamp]
        alerted=current.loc[current.alert]
        alerts=[]
        for row in alerted.itertuples(index=False):
            alerts.append({"grp":row.grp,"category":row.category,"n":int(row.n),"baseline":float(row.baseline),"ratio":float(row.n/row.baseline),"p_value":float(row.p_value),"streak":int(row.streak),"is_new":int(row.streak)==1,"comove":sorted(set(alerted.loc[(alerted.category==row.category)&(alerted.grp!=row.grp),"grp"]))})
        alerts.sort(key=lambda a:(-a["ratio"],a["grp"],a["category"]))
        previous=timestamp-pd.DateOffset(months=1)
        prev=monitor.loc[monitor.month==previous]
        current_totals=current.drop_duplicates("grp").total.sum()
        previous_totals=prev.drop_duplicates("grp").total.sum()
        snapshots[month]={"kpi":{"complaints":int(current_totals),"complaints_prev":int(previous_totals),"alerts":len(alerts),"alerts_prev":int(prev.alert.sum()),"fire_alert_models":int(alerted.loc[alerted.category=="fire_thermal","grp"].nunique())},"alerts":alerts}
    note="현재 화면은 키워드 분류 기준선입니다. LLM 라벨·한국어 요약·심각도 판정은 적용하지 않았습니다." if labeler=="keyword" else "전체 demo 신고의 LLM 라벨을 사용합니다. 한국어 요약은 원문과 대조해 검토해야 합니다. 38사례 주 검증은 키워드 기준선입니다."
    flag_sources=FLAG_SOURCES if labeler=="keyword" else {"fire":"NHTSA FIRE or LLM", "crash":"NHTSA CRASH or LLM", "injury":"NHTSA INJURED or LLM", "smoke":"LLM", "driving":"LLM", "parked":"LLM", "severe":"LLM severity >= 3"}
    return {"contract":CONTRACT,"labeler":labeler,"labeling_note":note,"flag_sources":flag_sources,"asof_months":MONTHS,"default_asof":"2018-08-01","demo_signal":{"grp":"HYUNDAI|SONATA","category":"fire_thermal","month":"2018-08-01"},"groups":list(DEMO_GROUPS),"categories":list(DISPLAY_CATEGORIES),"series":series_for(detections,DEMO_GROUPS,DISPLAY_CATEGORIES,"2017-03-01",MONTHS[-1]),"snapshots":snapshots,"complaints":complaints,"pile":pile,"evidence":evidence,"briefs":{},"reveal":{"cases":[],"series_after":series_for(detections,DEMO_GROUPS,DISPLAY_CATEGORIES,"2018-11-01","2019-06-01")},"sources":[{"name":"NHTSA 소비자 신고","status":"connected","count":con.execute("SELECT count(*) FROM complaints").fetchone()[0]},{"name":"AS·보증 수리","status":"not_connected"},{"name":"MES 생산 이력","status":"not_connected"},{"name":"부품 LOT·공급사","status":"not_connected"}],"assumptions":[]}

def schema_validate(data,name):
    import jsonschema
    schema=json.loads((Path(__file__).parent/"contracts"/f"{name}.schema.json").read_text())
    jsonschema.Draft202012Validator(schema).validate(data)

def write_json(path,data,schema_name):
    schema_validate(data,schema_name)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")

def run_keyword(con,config,args=None):
    method=getattr(args,"method","kw")
    output=getattr(args,"output",None) or config.root/"web/public/data"
    output=Path(output)
    detections=con.execute("SELECT * FROM detections_kw").fetchdf()
    source=con.execute('SELECT c.*,l."primary" AS primary,l.secondary FROM scoped c JOIN labels_kw l USING(odino)').fetchdf()
    expected_count=con.execute("SELECT count(*) FROM scoped").fetchone()[0]
    if len(source)!=expected_count or source.odino.duplicated().any():
        raise ValueError("Export requires complete one-label-per-complaint coverage")
    measured=json.loads((config.root/"data/backtest_kw.json").read_text())
    console=build_console(con,detections,source)
    entries=[]
    for item in measured["cases"]:
        first=item["first_alert"]
        entries.append({"case_id":item["case_id"],"split":item["split"],"investigation":item["investigation"],"note":item["title"],"groups":item["groups"],"target_categories":item["target_categories"],"odate":item["odate"],"result":item["result"],"lead_days":item["lead_days"],"first_alert_month":first["month"] if first else None,"first_alert_group":first["grp"] if first else None,"first_alert_category":first["category"] if first else None,"has_llm":False})
        if item["case_id"] in {"PE19003","PE19004","PE20016"}:
            console["reveal"]["cases"].append({"case_id":item["case_id"],"make":item["groups"][0].split("|")[0],"title":item["title"],"odate":item["odate"],"first_alert_month":first["month"] if first else None,"first_alert_grp":first["grp"] if first else None,"first_alert_category":first["category"] if first else None,"available":first["available"] if first else None,"lead_days":item["lead_days"],"groups":item["groups"]})
    cases={"contract":CONTRACT,"cases":entries,"controls":[{"group":x["group"],"ref_date":x["odate"],"matched_to":x["matched_to"]} for x in measured["controls"]]}
    validation={split:{name:{"hits":measured["summary"][split][plural]["hits"],"n":measured["summary"][split][plural]["total"]} for name,plural in (("case","cases"),("control","controls"))} for split in ("dev","holdout")}
    burden={}
    for label,plural in (("case","cases"),("control","controls")):
        alerts=sum(measured["summary"][split][plural]["alerts"] for split in ("dev","holdout"))
        denominator=sum(measured["summary"][split][plural]["group_months"] for split in ("dev","holdout"))
        burden[f"{label}_alerts_per_group_month"]=alerts/denominator if denominator else None
    source_manifest_path=config.root/"data/results/source_manifest.json"
    downloaded_at=json.loads(source_manifest_path.read_text())["observed_local_date"] if source_manifest_path.exists() else datetime.now().astimezone().date().isoformat()
    meta={"contract":CONTRACT,"generated_at":datetime.now(timezone.utc).isoformat(),"data_source":{"name":"NHTSA ODI complaints & investigations","downloaded_at":None,"observed_local_date":downloaded_at,"license":"public domain"},"params":{"rule":"poisson","alpha":config.alpha,"min_count":config.minimum_count,"baseline_months":config.baseline_months,"min_history":config.minimum_history,"lambda_floor":config.baseline_floor,"pre_window_months":12,"evaluation_window_basis":"alert_month"},"validation":validation,"burden":burden,"labels":{"llm_model":None,"llm_labeled":0,"sample_agreement":{"agree":0,"n":0},"human_check":{"n":0,"kw_correct":None,"llm_correct":None},"cost_per_1k_usd":None},"validation_notes":["접수일 기준 회고적 분석이며 당시 파일 공개·수정 이력은 복원하지 않았습니다.","사전 dev 8/19와 현재 9/19는 다릅니다. 기존 키워드 코드가 제공되지 않아 완전 동일성은 미확인입니다.","holdout 결과를 보고 탐지 임계값이나 키워드를 바꾸지 않았습니다.","볼트 EV는 현재 키워드 기준 놓친 사례입니다. 사전 시제품의 late 결과와 다릅니다.","검토 업무량은 등록 평가창의 그룹월을 합산한 관측치이며 현업 업무량은 미검증입니다.","LLM·사람 라벨 검수·라벨 비용은 이 키워드 화면에 미반영입니다."]}
    write_json(output/"console.json",console,"console")
    write_json(output/"meta.json",meta,"meta")
    write_json(output/"cases.json",cases,"cases")
    written=["console.json","meta.json","cases.json"]
    # Case views are evaluation-only. Bound each registered case to complete months.
    for item in measured["cases"]:
        date=pd.Timestamp(item["odate"])
        start=date-pd.DateOffset(months=48);end=date+pd.DateOffset(months=6)
        case_detection=detections.loc[detections.grp.isin(item["groups"])&(detections.month>=start)&((detections.month+pd.offsets.MonthBegin(1))<=end)]
        case_alerts=[]
        candidates=case_detection.loc[case_detection.alert]
        evidence_rows={}
        for row in candidates.itertuples(index=False):
            matching=source.loc[(source.grp==row.grp)&(source.month==row.month)]
            matching=matching.loc[matching.apply(lambda x:row.category in [x['primary'],*list(x.secondary)],axis=1)]
            selected=matching.sort_values(["fire","injured","crash","odino"],ascending=[False,False,False,True]).head(10)
            evidence_rows[(row.grp,row.category,date_string(row.month))]=selected
        all_ids=[str(x) for frame in evidence_rows.values() for x in frame.odino]
        denied=sensitive_values(con,all_ids)
        for row in candidates.itertuples(index=False):
            month=date_string(row.month)
            selected=evidence_rows[(row.grp,row.category,month)]
            evidence=[{"odino":str(x.odino),"ldate":date_string(x.ldate),"fire":bool(x.fire),"crash":bool(x.crash),"injured":int(x.injured),"summary_ko":None,"snippet":public_text(x.text,300,denied=denied[str(x.odino)])} for x in selected.itertuples(index=False)]
            case_alerts.append({"id":key(row.grp,row.category,month),"grp":row.grp,"category":row.category,"month":month,"observed":int(row.n),"baseline":float(row.baseline),"p_value":float(row.p_value),"is_target":row.category in item["target_categories"],"available":date_string(row.month+pd.offsets.MonthBegin(1)),"brief":None,"evidence":evidence})
        data={"contract":CONTRACT,"case_id":item["case_id"],"labeler":"keyword","odate":item["odate"],"target_categories":item["target_categories"],"groups":series_for(case_detection,item["groups"],CATEGORIES,start,end),"alerts":case_alerts}
        filename=f"cases/{item['case_id']}.json"
        write_json(output/filename,data,"case")
        written.append(filename)
    manifest={"contract":CONTRACT,"labeler":"keyword","status":"complete","files":written,"console_months":len(MONTHS),"console_groups":len(DEMO_GROUPS),"complaints":len(console["complaints"]),"evidence_cells":len(console["evidence"]),"briefs":0,"cases":len(entries),"file_sha256":{name:hashlib.sha256((output/name).read_bytes()).hexdigest() for name in written}}
    previous_manifest=output/"completion.json"
    if previous_manifest.exists():
        previous=json.loads(previous_manifest.read_text())
        for old in set(previous.get("files",[]))-set(written):
            relative=Path(old)
            if len(relative.parts)==2 and relative.parts[0]=="cases_llm" and relative.suffix==".json":
                (output/relative).unlink(missing_ok=True)
    write_json(output/"completion.json",manifest,"completion")
    return {"output":str(output),"files":len(written)+1,"console_complaints":len(console["complaints"]),"evidence_cells":len(console["evidence"]),"labeler":"keyword","briefs":0}


def run(con,config,args=None):
    if getattr(args,"method","kw")=="llm":
        from .export_llm import run as run_llm
        return run_llm(con,config,args)
    return run_keyword(con,config,args)
