"""Offline, fail-closed import of complete, current LLM labels. No API calls."""
import json
import os
from pathlib import Path
import pandas as pd
from .label_llm import MODEL, LABEL_SCHEMA, HAZARDS, cache_key, digest, system_prompt, validate_label
from .privacy import redact_text, privacy_matches, sensitive_values


def read_records(path):
    if not path.exists():
        return []
    # Never repair or truncate a file that another labeling process may be writing.
    records=[]
    for number,line in enumerate(path.read_text(encoding="utf-8").splitlines(),1):
        if line.strip():
            try:
                item=json.loads(line)
            except json.JSONDecodeError:
                raise ValueError(f"Incomplete or malformed LLM cache line {number}") from None
            if not isinstance(item,dict):
                raise ValueError(f"Invalid LLM cache record {number}")
            records.append(item)
    return records


def validate_complete(rows, records, *, model, prompt_hash):
    """Check all current IDs/inputs before producing any importable table."""
    expected={str(row["odino"]):row for row in rows}
    if not expected or len(expected)!=len(rows):
        raise ValueError("Demo must contain unique, nonempty complaint IDs")
    by_key={record.get("cache_key"):record for record in records if record.get("status")=="ok"}
    accepted=[]; missing=[]
    for odino,row in sorted(expected.items()):
        source=redact_text(row["text"],1500,denied=row.get("denied",[]))
        current_key=cache_key(odino,source,model,prompt_hash)
        record=by_key.get(current_key)
        if not record or any(record.get(name)!=value for name,value in (("odino",odino),("model",model),("prompt_hash",prompt_hash),("input_hash",digest(source)))):
            missing.append(odino)
            continue
        label=validate_label(record.get("label"),source)
        if privacy_matches(label["summary_ko"],row.get("denied",[])) or privacy_matches(label["evidence_quote"],row.get("denied",[])):
            raise ValueError("Sensitive value in LLM label output")
        accepted.append({"odino":odino,"primary":label["primary_category"],"secondary":label["secondary_categories"],"severity":label["severity"],"summary_ko":label["summary_ko"],**{f"hazard_{h}":label["hazards"][h] for h in HAZARDS},"model":model,"prompt_hash":prompt_hash,"input_hash":digest(source),"cache_key":current_key})
    if missing:
        raise ValueError(f"Incomplete current LLM coverage: {len(accepted)}/{len(expected)}; {len(missing)} missing or stale. Keyword data is unchanged.")
    return pd.DataFrame(accepted)


def load_complete(con, config, model=None):
    model=model or os.getenv("ES_LLM_MODEL") or MODEL
    prompt_hash=digest(system_prompt(config.root)+json.dumps(LABEL_SCHEMA,sort_keys=True))
    rows=con.execute("SELECT odino,text FROM demo ORDER BY odino").fetchdf().to_dict("records")
    denied=sensitive_values(con,[str(row["odino"]) for row in rows])
    for row in rows:
        row["denied"]=denied.get(str(row["odino"]),[])
    records=read_records(config.root/"data/labels/labels_llm.jsonl")
    frame=validate_complete(rows,records,model=model,prompt_hash=prompt_hash)
    return frame,{"model":model,"prompt_hash":prompt_hash,"population":len(rows),"labeled":len(frame),"status":"complete","cache_fingerprint":digest("\n".join(sorted(frame.cache_key)))}


def install(con,frame):
    con.register("complete_llm_labels",frame)
    try:
        con.execute("CREATE OR REPLACE TABLE labels_llm AS SELECT * FROM complete_llm_labels")
    finally:
        con.unregister("complete_llm_labels")


def run(con,config,args=None):
    frame,report=load_complete(con,config,getattr(args,"model",None))
    install(con,frame)
    path=config.root/"data/results/llm_import.json"
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return report
