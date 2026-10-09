"""Offline tests for leakage, exact input and preserving real annotations."""
import csv
import json
from pathlib import Path
import pandas as pd
import pytest
from es.config import Config, CATEGORIES
from es.human_review import (prepare_review, selected_ids, run, BLIND_FIELDS, MAPPING_FIELDS,
                             REVIEW_SEED, digest)
from es.privacy import redact_text
from es.export_llm import write_development_comparison


@pytest.fixture
def root(tmp_path):
    (tmp_path/"docs/Development").mkdir(parents=True)
    (tmp_path/"docs/LLM_PROMPTS.md").write_text("### system\n```\nSynthetic label prompt.\n```\n")
    (tmp_path/"docs/Development/HUMAN_REVIEW.md").write_text("Synthetic frozen rubric.")
    return tmp_path


def rows():
    return [{"odino":str(10000+i),"text":"  HYUNDAI SONATA\n Smoke while driving. Exampleville contact a@example.com. "+"Long source text. "*120,
             "denied":["Exampleville"], "llm_primary":"brakes", "summary_ko":"MODEL SECRET"} for i in range(120)]


def csv_rows(path):
    with Path(path).open(encoding="utf-8",newline="") as handle:return list(csv.DictReader(handle))


def test_new_seed_excludes_development_and_blind_input_matches_actual_send(root,monkeypatch):
    monkeypatch.setattr("dotenv.load_dotenv",lambda *a,**k: (_ for _ in ()).throw(AssertionError("No .env access")))
    values=rows();chosen,excluded=selected_ids(values)
    assert len(chosen)==30 and len(excluded)==50 and not set(chosen)&excluded
    result=prepare_review(list(reversed(values)),root=root)
    out=Path(result["output"]);blind=csv_rows(out/"blind.csv");mapping=csv_rows(out/"mapping.csv")
    assert len(blind)==30 and list(blind[0])==BLIND_FIELDS and list(mapping[0])==MAPPING_FIELDS
    by_id={r["odino"]:r for r in values}
    assert {m["odino"] for m in mapping}==set(chosen)
    for b,m in zip(blind,mapping):
        source=by_id[m["odino"]];sent=redact_text(source["text"],1500,denied=source["denied"])
        assert b["text"]==sent and len(sent)==1500 and m["input_hash"]==digest(sent)
        assert "HYUNDAI SONATA" in b["text"] and "Exampleville" not in b["text"] and "a@example.com" not in b["text"]
        assert all(b[f]=="" for f in BLIND_FIELDS[2:])
    assert "MODEL SECRET" not in (out/"blind.csv").read_text()
    assert result["accuracy"] is None and result["api_calls"]==0 and result["filled_gold_rows"]==0
    assert all(p.stat().st_mode&0o777==0o600 for p in out.iterdir()) and out.stat().st_mode&0o777==0o700
    manifest=json.loads((out/"manifest.json").read_text())
    assert manifest["sampling_rule"]["review_seed"]==REVIEW_SEED and manifest["sampling_rule"]["prediction_conditioning"] is False
    assert manifest["model"] and manifest["label_prompt_schema_hash"] and manifest["quote_policy"] and manifest["rubric_hash"]


def test_resuming_preserves_gold_notes_and_all_files_byte_for_byte(root):
    values=rows();out=Path(prepare_review(values,root=root)["output"])
    reviewed=csv_rows(out/"blind.csv");reviewed[0].update(gold_primary="fire_thermal",review_status="clear",gold_evidence="Smoke while driving.",human_notes="Actual human note, preserve")
    with (out/"blind.csv").open("w",encoding="utf-8",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=BLIND_FIELDS);writer.writeheader();writer.writerows(list(reversed(reviewed)))
    before={p.name:p.read_bytes() for p in out.iterdir()}
    result=prepare_review(values,root=root)
    assert result["created"] is False and result["filled_gold_rows"]==1 and result["accuracy"] is None
    assert before=={p.name:p.read_bytes() for p in out.iterdir()}


@pytest.mark.parametrize("change",["source","model","prompt","policy","rubric","population","mapping","deleted_row","gold_enum"])
def test_changed_locked_inputs_or_damaged_review_refuses_without_overwriting(root,change):
    values=rows();out=Path(prepare_review(values,root=root)["output"]);kwargs={}
    if change=="source":
        selected,_=selected_ids(values)
        next(v for v in values if v["odino"]==selected[0])["text"]+="changed"
        # Put the change within the sent 1500-character boundary.
        next(v for v in values if v["odino"]==selected[0])["text"]="changed prefix "+values[0]["text"]
    elif change=="model":kwargs["model"]="other-model"
    elif change=="prompt":(root/"docs/LLM_PROMPTS.md").write_text("### system\n```\nChanged prompt.\n```\n")
    elif change=="policy":kwargs["quote_policy"]="verbatim-only"
    elif change=="rubric":(root/"docs/Development/HUMAN_REVIEW.md").write_text("Changed rubric.")
    elif change=="population":values.append({"odino":"99999","text":"Smoke."})
    elif change=="mapping":(out/"mapping.csv").write_text("altered")
    else:
        reviewed=csv_rows(out/"blind.csv")
        if change=="deleted_row":reviewed.pop()
        else:reviewed[0]["gold_primary"]="invented_category"
        with (out/"blind.csv").open("w",newline="") as handle:
            writer=csv.DictWriter(handle,fieldnames=BLIND_FIELDS);writer.writeheader();writer.writerows(reviewed)
    before={p.name:p.read_bytes() for p in out.iterdir()}
    with pytest.raises(ValueError):prepare_review(values,root=root,**kwargs)
    assert before=={p.name:p.read_bytes() for p in out.iterdir()}


def test_development_comparison_is_marked_and_never_overwrites_gold(root):
    frame=pd.DataFrame([{"odino":"1","llm_primary":"fire_thermal","human_gold":"","human_notes":""}])
    write_development_comparison(frame,root)
    path=root/"data/labels/sample60_compare.csv"
    path.write_text("odino,human_gold,human_notes\n1,brakes,Do not erase actual review\n")
    before=path.read_bytes();write_development_comparison(frame,root)
    assert path.read_bytes()==before
    note=json.loads(path.with_suffix(".purpose.json").read_text())
    assert note["independent_evaluation"] is False and note["accuracy"] is None


def test_actual_source_query_is_read_only_and_credentials_are_never_loaded(root,monkeypatch):
    import duckdb
    from es.human_review import main
    db=root/"working.duckdb"
    with duckdb.connect(str(db)) as con:
        frame=pd.DataFrame([{k:v for k,v in row.items() if k in ("odino","text")} for row in rows()]);con.register("input",frame)
        con.execute("CREATE TABLE demo AS SELECT * FROM input")
        con.execute("CREATE TABLE complaints_raw(c02 VARCHAR,c15 VARCHAR,c13 VARCHAR,c41 VARCHAR,c42 VARCHAR,c43 VARCHAR,c51 VARCHAR)")
    monkeypatch.setattr("dotenv.load_dotenv",lambda *a,**k: (_ for _ in ()).throw(AssertionError("No .env")))
    monkeypatch.setattr("es.human_review.label_llm.AsyncOpenAI",lambda *a,**k: (_ for _ in ()).throw(AssertionError("No API client")))
    result=run(Config(root=root,db_path=db))
    assert result["independent_rows"]==30 and result["api_calls"]==0
