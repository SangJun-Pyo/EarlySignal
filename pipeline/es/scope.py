import pandas as pd
import yaml
from .config import DEMO_GROUPS

def load_pool(config):
    return yaml.safe_load(config.cases.read_text(encoding="utf-8"))

def case_groups(case):
    return sorted({"|".join(v.split("|")[:2]) for v in case["vehicles"]})

def build_windows(pool):
    records=[]
    for case in pool["cases"]:
        date = pd.Timestamp(case["odate"])
        for grp in case_groups(case):
            records.append((grp, (date-pd.DateOffset(months=48)).date(), (date+pd.DateOffset(months=6)).date()))
    for control in pool["controls"]:
        date = pd.Timestamp(control["ref_date"])
        records.append((control["group"],(date-pd.DateOffset(months=48)).date(),(date+pd.DateOffset(months=6)).date()))
    return pd.DataFrame(records,columns=["grp","start_date","end_date"])

def run(con, config, args=None):
    windows = build_windows(load_pool(config))
    con.register("scope_windows",windows)
    con.execute("""CREATE OR REPLACE TABLE scoped AS SELECT c.* FROM complaints c
        WHERE EXISTS(SELECT 1 FROM scope_windows w WHERE c.grp=w.grp
        AND c.ldate >= w.start_date AND c.ldate < w.end_date)""")
    placeholders = ",".join("?" for _ in DEMO_GROUPS)
    con.execute(f"""CREATE OR REPLACE TABLE demo AS SELECT * FROM complaints WHERE
        (grp IN ({placeholders}) AND ldate >= DATE '2017-03-01' AND ldate < DATE '2019-07-01')
        OR (grp='CHEVROLET|BOLT EV' AND ldate >= DATE '2018-10-01' AND ldate < DATE '2021-02-01')""", list(DEMO_GROUPS))
    con.unregister("scope_windows")
    return {"scoped": con.execute("SELECT count(*) FROM scoped").fetchone()[0],
            "demo": con.execute("SELECT count(*) FROM demo").fetchone()[0],
            "demo_groups":con.execute("SELECT grp,count(*) FROM demo GROUP BY grp ORDER BY grp").fetchall()}
