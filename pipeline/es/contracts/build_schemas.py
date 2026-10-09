"""Generate schemas for the documented v1 Python/TypeScript boundary."""
import json
from pathlib import Path
from es.config import CATEGORIES

S={"type":"string"}; N={"type":"number"}; I={"type":"integer","minimum":0}; B={"type":"boolean"}
NS={"type":["string","null"]}; NN={"type":["number","null"]}
MONTH={"type":"string","pattern":r"^\d{4}-\d{2}-01$"}
DATE={"type":"string","pattern":r"^\d{4}-\d{2}-\d{2}$"}
CAT={"type":"string","enum":list(CATEGORIES)}
FLAGS=("fire","smoke","driving","parked","crash","injury","severe")

def arr(items,**kwargs): return {"type":"array","items":items,**kwargs}
def obj(properties,required=None,extra=False): return {"type":"object","properties":properties,"required":list(properties) if required is None else required,"additionalProperties":extra}
def mapping(value): return {"type":"object","additionalProperties":value}
def tup(a,b): return {"type":"array","prefixItems":[a,b],"items":False,"minItems":2,"maxItems":2}
def root(properties): return {"$schema":"https://json-schema.org/draft/2020-12/schema",**obj({"contract":{"const":"earlysignal-data-v1"},**properties})}

catseries=obj({"n":arr(I),"baseline":arr(NN),"alert":arr(B)})
series=obj({"months":arr(MONTH),"total":arr(I),"categories":{"type":"object","propertyNames":CAT,"additionalProperties":catseries}})
complaint=obj({"grp":S,"month":MONTH,"ldate":DATE,"year":S,"flags":arr({"enum":list(FLAGS)},uniqueItems=True),"categories":arr(CAT,uniqueItems=True,minItems=1,maxItems=3),"severity":{"type":["integer","null"],"minimum":1,"maximum":3},"injured":I,"summary_ko":NS,"text":{"type":"string","maxLength":520},"label_source":{"enum":["keyword","llm"]}})
alert=obj({"grp":S,"category":CAT,"n":I,"baseline":N,"ratio":N,"p_value":{"type":"number","minimum":0,"maximum":1},"streak":I,"is_new":B,"comove":arr(S,uniqueItems=True)})
evidence=obj({"n":I,"agg":obj({flag:I for flag in FLAGS}),"co":arr(tup(CAT,I),maxItems=3),"years":arr(tup(S,I)),"ids":arr(S,uniqueItems=True,minItems=3)})
revealcase=obj({"case_id":S,"make":S,"title":S,"odate":DATE,"first_alert_month":NS,"first_alert_grp":NS,"first_alert_category":{"anyOf":[CAT,{"type":"null"}]},"available":NS,"lead_days":{"type":["integer","null"]},"groups":arr(S)})
console=root({"labeler":{"enum":["keyword","llm"]},"labeling_note":S,"flag_sources":obj({flag:S for flag in FLAGS}),"asof_months":arr(MONTH,minItems=8,maxItems=8,uniqueItems=True),"default_asof":MONTH,"demo_signal":obj({"grp":S,"category":CAT,"month":MONTH}),"groups":arr(S,minItems=9,maxItems=9,uniqueItems=True),"categories":arr(CAT,uniqueItems=True),"series":mapping(series),"snapshots":mapping(obj({"kpi":obj({x:I for x in ("complaints","complaints_prev","alerts","alerts_prev","fire_alert_models")}),"alerts":arr(alert)})),"complaints":mapping(complaint),"pile":mapping(arr(S,uniqueItems=True)),"evidence":mapping(evidence),"briefs":mapping(S),"reveal":obj({"cases":arr(revealcase),"series_after":mapping(series)}),"sources":arr(obj({"name":S,"status":{"enum":["connected","not_connected"]},"count":I},required=["name","status"])),"assumptions":arr(S)})
metric=obj({"hits":I,"n":I})
meta=root({"generated_at":S,"data_source":obj({"name":S,"downloaded_at":{"anyOf":[DATE,{"type":"null"}]},"observed_local_date":DATE,"license":S}),"params":mapping({"type":["number","string"]}),"validation":obj({split:obj({"case":metric,"control":metric}) for split in ("dev","holdout")}),"burden":obj({"case_alerts_per_group_month":NN,"control_alerts_per_group_month":NN}),"labels":obj({"llm_model":NS,"llm_labeled":I,"sample_agreement":obj({"agree":I,"n":I}),"human_check":obj({"n":I,"kw_correct":{"type":["integer","null"]},"llm_correct":{"type":["integer","null"]}}),"cost_per_1k_usd":NN}),"validation_notes":arr(S)})
caseresult=obj({"case_id":S,"split":{"enum":["dev","holdout"]},"investigation":S,"note":S,"groups":arr(S),"target_categories":arr(CAT),"odate":DATE,"result":{"enum":["early","late","missed"]},"lead_days":{"type":["integer","null"]},"first_alert_month":NS,"first_alert_group":NS,"first_alert_category":{"anyOf":[CAT,{"type":"null"}]},"has_llm":B})
cases=root({"cases":arr(caseresult),"controls":arr(obj({"group":S,"ref_date":DATE,"matched_to":S}))})
caseevidence=obj({"odino":S,"ldate":DATE,"fire":B,"crash":B,"injured":I,"summary_ko":NS,"snippet":{"type":"string","maxLength":300}})
casealert=obj({"id":S,"grp":S,"category":CAT,"month":MONTH,"observed":I,"baseline":N,"p_value":N,"is_target":B,"available":DATE,"brief":NS,"evidence":arr(caseevidence,maxItems=10)})
case=root({"case_id":S,"labeler":{"enum":["keyword","llm"]},"odate":DATE,"target_categories":arr(CAT),"groups":mapping(series),"alerts":arr(casealert)})
case["properties"]["coverage"]=obj({"source":{"const":"demo"},"start":DATE,"end_exclusive":DATE,"registered_window_complete":B})
completion=root({"labeler":{"enum":["keyword","llm"]},"status":{"const":"complete"},"files":arr(S),"console_months":I,"console_groups":I,"complaints":I,"evidence_cells":I,"briefs":I,"cases":I,"file_sha256":mapping({"type":"string","pattern":"^[a-f0-9]{64}$"})})
for name,schema in {"console":console,"meta":meta,"cases":cases,"case":case,"completion":completion}.items():
    (Path(__file__).parent/f"{name}.schema.json").write_text(json.dumps(schema,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
