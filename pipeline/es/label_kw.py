"""Deterministic comparison baseline; narrative only, no component fields."""
import re
import pandas as pd
from .config import CATEGORIES

PATTERNS = {
"fire_thermal": r"\bfires?\b|\bflames?\b|\bsmok(?:e|ing|ed)\b|\bburn(?:ing|t|ed)?\s+(?:smell|odor)|\b(?:melt\w*|overheat\w*)\b",
"electrical_failure": r"\b(?:electrical|electric\s+system|battery|batteries|alternator|wiring|short\s+circuit|power\s+surge)\b",
"loss_of_power": r"\blos[st]\s+(?:all\s+)?(?:motive\s+)?power\b|\bloss\s+of\s+(?:motive\s+)?power\b|\bno\s+(?:engine\s+)?power\b|\b(?:unable|fail\w*)\s+to\s+accelerate\b|\bpower\s+loss\b",
"engine_stall": r"\bstall\w*\b|\b(?:engine|vehicle)\s+(?:shut\w*|cut\w*)\s+(?:off|out|down)\b|\bengine\s+died\b",
"engine_failure": r"\bengine\s+(?:fail\w*|seiz\w*|knock\w*|blown|damage\w*|replac\w*)|\b(?:rod\s+bearing|connecting\s+rod|engine\s+block)\b",
"airbag": r"\bair\s*bags?\b|\btakata\b",
"brakes": r"\bbrak\w*\b|\babs\b",
"steering": r"\bsteer\w*\b|\bpower\s+assist\b",
"seat_belt": r"\bseat\s*belts?\b|\brestrain\w*\b|\bpretension\w*\b",
"fuel_leak": r"\bfuel\s+(?:leak\w*|pump|odor)|\bgas(?:oline)?\s+(?:leak\w*|smell)|\bfuel\s+tank\b",
"transmission": r"\btransmission\b|\bgear\w*\b|\bshift\w*\b|\bclutch\b",
"lighting": r"\b(?:head\s*lights?|tail\s*lights?|brake\s*lights?|turn\s+signals?|lamp\w*)\b",
"suspension": r"\b(?:suspension|struts?|shocks?|ball\s+joints?|control\s+arms?|axles?)\b",
"structure_body": r"\b(?:doors?|latch\w*|hood|trunk|tailgate|rust\w*|corrosion|roof|windshield|frame)\b",
"tires_wheels": r"\b(?:tires?|tyres?|wheels?|rims?)\b",
}
COMPILED = [(category,re.compile(PATTERNS[category],re.I)) for category in CATEGORIES if category in PATTERNS]

def label_text(text):
    hits = [category for category,pattern in COMPILED if pattern.search(text or "")]
    return {"primary":hits[0] if hits else "other", "secondary":hits[1:3]}

def run(con, config, args=None):
    source = con.execute("SELECT odino,text FROM scoped UNION SELECT odino,text FROM demo ORDER BY odino").fetchdf()
    records = [{"odino":str(row.odino),**label_text(row.text)} for row in source.itertuples(index=False)]
    frame = pd.DataFrame(records,columns=["odino","primary","secondary"])
    con.register("kw_labels",frame)
    con.execute('CREATE OR REPLACE TABLE labels_kw AS SELECT odino, "primary", secondary::VARCHAR[] AS secondary FROM kw_labels')
    con.unregister("kw_labels")
    return {"labelled":len(frame),"primary_counts":frame["primary"].value_counts().to_dict()}
