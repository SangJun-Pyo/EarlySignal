"""Synthetic boundary tests; these are not human accuracy measurements."""
import copy
import json
from types import SimpleNamespace
from pathlib import Path
import duckdb
import pandas as pd
import pytest
from es.config import Config
from es.import_llm import validate_complete,read_records,load_complete
from es.label_llm import MODEL,LABEL_SCHEMA,HAZARDS,cache_key,digest,system_prompt
from es.privacy import redact_text


def label(text="Smoke appeared while driving."):
    return {"primary_category":"fire_thermal","secondary_categories":[],"hazards":{h:h in ("smoke","while_driving") for h in HAZARDS},"severity":2,"evidence_quote":text,"summary_ko":"주행 중 연기 발생"}


def record(row,prompt_hash="prompt"):
    text=redact_text(row["text"],1500,denied=row.get("denied",[]))
    return {"odino":str(row["odino"]),"model":MODEL,"prompt_hash":prompt_hash,"input_hash":digest(text),"cache_key":cache_key(str(row["odino"]),text,MODEL,prompt_hash),"status":"ok","run_id":"synthetic","label":label(text)}


def test_complete_current_cache_has_one_label_per_id_and_no_private_text():
    rows=[{"odino":"1","text":"Smoke appeared while driving."},{"odino":"2","text":"Smoke appeared while driving."}]
    frame=validate_complete(rows,[record(row) for row in rows],model=MODEL,prompt_hash="prompt")
    assert len(frame)==2 and frame.odino.is_unique
    assert frame.primary.tolist()==["fire_thermal"]*2
    assert "text" not in frame and "evidence_quote" not in frame and "denied" not in frame
    assert frame.hazard_smoke.all()


@pytest.mark.parametrize("mutation",["missing","failed","model","prompt_hash","input_hash","odino","input_changed"])
def test_incomplete_stale_or_failed_cache_cannot_be_imported(mutation):
    row={"odino":"1","text":"Smoke appeared while driving."}; cached=record(row)
    records=[cached]
    if mutation=="missing": records=[]
    elif mutation=="failed": cached["status"]="failed"
    elif mutation=="input_changed": row["text"]+=" The engine stopped."
    else: cached[mutation]="different"
    with pytest.raises(ValueError,match="Incomplete current LLM coverage"):
        validate_complete([row],records,model=MODEL,prompt_hash="prompt")


def test_public_summary_known_identifiers_are_rejected():
    row={"odino":"1","text":"Smoke appeared while driving.","denied":["Exampleville"]}
    cached=record(row); cached["label"]["summary_ko"]="Exampleville에서 연기 발생"
    with pytest.raises(ValueError,match="Sensitive value"):
        validate_complete([row],[cached],model=MODEL,prompt_hash="prompt")


def test_malformed_trailing_cache_is_not_repaired_during_import(tmp_path):
    path=tmp_path/"cache.jsonl"; original='{"status":"ok"}\n{"odino":'
    path.write_text(original)
    with pytest.raises(ValueError,match="Incomplete or malformed"):
        read_records(path)
    assert path.read_text()==original


def test_partial_export_keeps_existing_public_files_and_database_untouched(tmp_path):
    from es.export import run
    con=duckdb.connect()
    con.execute("CREATE TABLE demo(odino VARCHAR,text VARCHAR)")
    con.execute("INSERT INTO demo VALUES ('1','Smoke appeared while driving.'),('2','Smoke appeared while driving.')")
    con.execute("CREATE TABLE complaints_raw(c02 VARCHAR,c15 VARCHAR,c13 VARCHAR,c41 VARCHAR,c42 VARCHAR,c43 VARCHAR,c51 VARCHAR)")
    (tmp_path/"docs").mkdir(); (tmp_path/"docs/LLM_PROMPTS.md").write_text("### system\n```\nSynthetic test prompt.\n```\n## 2. Brief\n### system\n```\nProvided reports only.\n```\n## 3. Request\n")
    ph=digest(system_prompt(tmp_path)+json.dumps(LABEL_SCHEMA,sort_keys=True))
    path=tmp_path/"data/labels/labels_llm.jsonl"; path.parent.mkdir(parents=True)
    path.write_text(json.dumps(record({"odino":"1","text":"Smoke appeared while driving."},ph))+"\n")
    out=tmp_path/"public";out.mkdir();(out/"console.json").write_text('existing-keyword-output')
    with pytest.raises(ValueError,match="1/2"):
        run(con,Config(root=tmp_path),SimpleNamespace(method="llm",output=out))
    assert (out/"console.json").read_text()=='existing-keyword-output'
    assert set(con.execute("SHOW TABLES").fetchnumpy()["name"])=={"demo","complaints_raw"}


def test_llm_cannot_replace_registered_keyword_backtest():
    from es.backtest import run
    with pytest.raises(ValueError,match="38-case main backtest"):
        run(None,Config(),SimpleNamespace(method="llm"))


def test_complete_synthetic_cache_reaches_console_without_replacing_main_validation(tmp_path):
    from es.aggregate import aggregate_frame
    from es.detect import detect_frame
    from es.export import run,schema_validate
    from es.backtest import evaluate
    from es.config import DEMO_GROUPS
    rows=[];number=1000
    for grp in DEMO_GROUPS:
        for month in pd.date_range("2017-03-01","2018-10-01",freq="MS"):
            for _ in range(8 if grp=="HYUNDAI|SONATA" and month==pd.Timestamp("2018-08-01") else 1):
                number+=1
                rows.append({"odino":str(number),"grp":grp,"ldate":month+pd.Timedelta(days=9),"month":month,"year":"2013","fire":False,"crash":False,"injured":0,"text":"Smoke appeared while driving."})
    number+=1
    rows.append({**rows[-1],"odino":str(number),"grp":"CHEVROLET|BOLT EV","month":pd.Timestamp("2018-10-01"),"ldate":pd.Timestamp("2018-10-10")})
    source=pd.DataFrame(rows)
    keyword=pd.DataFrame([{"odino":row["odino"],"primary":"fire_thermal","secondary":[]} for row in rows])
    config=Config(root=tmp_path)
    con=duckdb.connect()
    con.register("synthetic_complaints",source)
    for table in ("complaints","scoped","demo"):
        con.execute(f"CREATE TABLE {table} AS SELECT * FROM synthetic_complaints")
    con.register("synthetic_labels",keyword);con.execute("CREATE TABLE labels_kw AS SELECT * FROM synthetic_labels")
    detected=detect_frame(aggregate_frame(source,keyword),config)
    con.register("synthetic_detected",detected);con.execute("CREATE TABLE detections_kw AS SELECT * FROM synthetic_detected")
    con.execute("CREATE TABLE complaints_raw(c02 VARCHAR,c15 VARCHAR,c13 VARCHAR,c41 VARCHAR,c42 VARCHAR,c43 VARCHAR,c51 VARCHAR)")
    (tmp_path/"docs").mkdir();(tmp_path/"docs/LLM_PROMPTS.md").write_text("### system\n```\nSynthetic test prompt.\n```\n## 2. Brief\n### system\n```\nProvided reports only.\n```\n## 3. Request\n")
    ph=digest(system_prompt(tmp_path)+json.dumps(LABEL_SCHEMA,sort_keys=True))
    caches=[record(row,ph) for row in rows]
    for cached in caches:
        cached["label"]["primary_category"]="electrical_failure"
    path=tmp_path/"data/labels/labels_llm.jsonl";path.parent.mkdir(parents=True)
    path.write_text("\n".join(json.dumps(row) for row in caches)+"\n")
    cases=[]
    for case_id,grp,split in (("PE19003","HYUNDAI|SONATA","dev"),("PE19004","KIA|SORENTO","dev"),("PE20016","CHEVROLET|BOLT EV","holdout")):
        cases.append({"case_id":case_id,"investigation":case_id,"note":"Synthetic test only","vehicles":[grp],"target_categories":["fire_thermal"],"odate":"2019-03-29","split":split})
    measured=evaluate(detected,{"cases":cases,"controls":[]})
    (tmp_path/"data/backtest_kw.json").write_text(json.dumps(measured))
    output=tmp_path/"public"
    report=run(con,config,SimpleNamespace(method="llm",output=output))
    assert report["labeled"]==len(rows) and report["main_validation_labeler"]=="keyword"
    console=json.loads((output/"console.json").read_text())
    assert console["labeler"]=="llm"
    assert all(item["categories"]==["electrical_failure"] and item["summary_ko"]=="주행 중 연기 발생" for item in console["complaints"].values())
    assert all(item["label_source"]=="llm" and item["severity"]==2 for item in console["complaints"].values())
    assert console["briefs"]=={}
    meta=json.loads((output/"meta.json").read_text())
    assert meta["validation"]["dev"]["case"]["hits"]==measured["summary"]["dev"]["cases"]["hits"]
    assert meta["labels"]["human_check"]["n"]==0 and meta["labels"]["cost_per_1k_usd"] is None
    assert json.loads((output/"cases/PE19003.json").read_text())["labeler"]=="keyword"
    detail=json.loads((output/"cases_llm/PE19003.json").read_text())
    assert detail["coverage"]["registered_window_complete"] is False
    assert any(a["category"]=="electrical_failure" for a in detail["alerts"])
    comparison=json.loads((tmp_path/"data/results/llm_demo_comparison.json").read_text())
    assert comparison["primary_agreement"]=={"agree":0,"n":len(rows)}
    manifest=json.loads((output/"completion.json").read_text())
    assert set(manifest["files"])=={str(path.relative_to(output)) for path in output.rglob("*.json") if path.name!="completion.json"}
    for name in manifest["files"]:
        schema_validate(json.loads((output/name).read_text()),"case" if name.startswith(("cases/","cases_llm/")) else Path(name).stem)
    # A real offline generated and input-bound cache reaches the next export.
    import asyncio
    from es.brief import generate_briefs, load_public_console
    calls=[]
    async def create(**kwargs):
        calls.append(kwargs)
        supplied=json.loads(kwargs["messages"][1]["content"])["evidence"]
        content=json.dumps({"narrative":f"주행 중 연기가 발생했다는 신고입니다(#{supplied[0]['odino']})."})
        return SimpleNamespace(usage=None,choices=[SimpleNamespace(finish_reason="stop",message=SimpleNamespace(content=content,refusal=None))])
    client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    generated=asyncio.run(generate_briefs(console,root=tmp_path,client=client,limit=1))
    assert generated["completed"]==1 and len(calls)==1
    report=run(con,config,SimpleNamespace(method="llm",output=output))
    complete_console=load_public_console(output/"console.json")
    assert report["briefs"]==1 and len(complete_console["briefs"])==1
    assert json.loads((output/"completion.json").read_text())["briefs"]==1



def test_cost_includes_paid_failure_from_previous_run_and_rejects_unlinked_usage(tmp_path):
    from es.export_llm import estimated_cost_per_1k
    labels=pd.DataFrame([{"odino":"1","model":MODEL,"cache_key":"current"}])
    path=tmp_path/"data/labels/llm_usage.jsonl";path.parent.mkdir(parents=True)
    usages=[{"odino":"1","model":MODEL,"cache_key":"current","run_id":"failed-before","estimated_usd":0.01},{"odino":"1","model":MODEL,"cache_key":"current","run_id":"success-now","estimated_usd":0.02}]
    path.write_text("\n".join(json.dumps(u) for u in usages)+"\n")
    assert estimated_cost_per_1k(Config(root=tmp_path),labels)==pytest.approx(30)
    usages[0].pop("cache_key")
    path.write_text("\n".join(json.dumps(u) for u in usages)+"\n")
    assert estimated_cost_per_1k(Config(root=tmp_path),labels) is None
