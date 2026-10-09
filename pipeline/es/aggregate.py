"""Count unique complaint IDs by received month and every assigned label."""
import pandas as pd
from .config import CATEGORIES

OUTPUT_COLUMNS = ["grp","category","month","n","total"]

def aggregate_frame(complaints, labels, as_of=None):
    # Explicit allowlist prevents component/investigation fields entering calculation.
    data = complaints[["odino","grp","ldate"]].copy()
    data["odino"] = data["odino"].astype(str)
    data["ldate"] = pd.to_datetime(data["ldate"])
    if as_of is not None:
        data = data.loc[data.ldate <= pd.Timestamp(as_of)]
    data = data.dropna(subset=["ldate"]).drop_duplicates("odino")
    if data.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)
    data["month"] = data.ldate.dt.to_period("M").dt.to_timestamp()
    assigned = labels[["odino","primary","secondary"]].copy()
    assigned["odino"] = assigned["odino"].astype(str)
    if assigned.odino.duplicated().any():
        raise ValueError("Labels must contain exactly one record per ODINO")
    missing = set(data.odino) - set(assigned.odino)
    if missing:
        raise ValueError(f"Incomplete label coverage: {len(missing)} complaint IDs are unlabelled")
    assigned["category"] = assigned.apply(lambda row:list(dict.fromkeys([row["primary"],*list(row["secondary"])])),axis=1)
    assigned=assigned[["odino","category"]].explode("category")
    if not assigned.category.isin(CATEGORIES).all():
        raise ValueError("Unknown label category")
    merged = data.merge(assigned,on="odino",how="inner").drop_duplicates(["odino","category"])
    totals = data.groupby(["grp","month"]).odino.nunique()
    counts = merged.groupby(["grp","category","month"]).odino.nunique()
    records=[]
    for grp, group in data.groupby("grp",sort=True):
        months = pd.date_range(group.month.min(),data.month.max(),freq="MS")
        if as_of is not None:
            months = pd.date_range(group.month.min(),pd.Timestamp(as_of).to_period("M").to_timestamp(),freq="MS")
        for category in CATEGORIES:
            for month in months:
                records.append((grp,category,month,int(counts.get((grp,category,month),0)),int(totals.get((grp,month),0))))
    return pd.DataFrame(records,columns=OUTPUT_COLUMNS)

def run(con, config, args=None):
    method=getattr(args,"method","kw")
    source = "scoped" if method == "kw" else "demo"
    complaints=con.execute(f"SELECT odino,grp,ldate FROM {source}").fetchdf()
    labels=con.execute(f'SELECT odino,"primary",secondary FROM labels_{method}').fetchdf()
    frame=aggregate_frame(complaints,labels,getattr(args,"as_of",None))
    con.register("count_frame",frame)
    con.execute(f"CREATE OR REPLACE TABLE aggregated_{method} AS SELECT * FROM count_frame")
    con.unregister("count_frame")
    return {"method":method,"cells":len(frame),"groups":frame.grp.nunique(),"as_of":getattr(args,"as_of",None)}
