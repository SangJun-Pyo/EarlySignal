"""Fixed causal monthly Poisson detector; no raw narratives or investigations."""
import numpy as np
import pandas as pd
from scipy.stats import poisson, binom
from .config import Config

def detect_frame(counts, config=None):
    config=config or Config()
    data=counts[["grp","category","month","n","total"]].copy()
    data["month"]=pd.to_datetime(data["month"])
    if data[["grp","category","month"]].duplicated().any():
        raise ValueError("Duplicate monthly observation")
    if data["month"].isna().any() or not data["month"].dt.is_month_start.all():
        raise ValueError("Months must be valid calendar month starts")
    if ((data.n<0)|(data.total<0)|(data.n>data.total)).any():
        raise ValueError("Complaint counts must satisfy 0 <= n <= total")
    pieces=[]
    for _,group in data.groupby(["grp","category"],sort=True):
        group=group.sort_values("month").copy()
        if not group.month.to_list() == pd.date_range(group.month.min(), group.month.max(), freq="MS").to_list():
            raise ValueError("Missing calendar months; fill zero months before detection")
        n=group.n.astype(float)
        baseline=n.shift(1).rolling(config.baseline_months,min_periods=config.minimum_history).mean().clip(lower=config.baseline_floor)
        group["baseline"]=baseline
        group["p_value"]=poisson.sf(n-1,baseline)
        group["alert"]=(group.p_value<config.alpha)&(group.n>=config.minimum_count)
        streak=[]; current=0
        for alert in group.alert:
            current=current+1 if alert else 0
            streak.append(current)
        group["streak"]=streak
        historical_total=group.total.shift(1).rolling(config.baseline_months,min_periods=config.minimum_history).sum()
        historical_n=n.shift(1).rolling(config.baseline_months,min_periods=config.minimum_history).sum()
        rate=(historical_n/historical_total).clip(0,1)
        group["binomial_p_value"]=binom.sf(n-1,group.total,rate)
        group["binomial_alert"]=(group.binomial_p_value<config.alpha)&(group.n>=config.minimum_count)
        pieces.append(group)
    if not pieces:
        return data.assign(baseline=np.nan,p_value=np.nan,alert=False,streak=0,binomial_p_value=np.nan,binomial_alert=False)
    return pd.concat(pieces,ignore_index=True)

def run(con, config, args=None):
    method=getattr(args,"method","kw")
    frame=detect_frame(con.execute(f"SELECT * FROM aggregated_{method}").fetchdf(),config)
    con.register("detection_frame",frame)
    con.execute(f"CREATE OR REPLACE TABLE detections_{method} AS SELECT * FROM detection_frame")
    con.unregister("detection_frame")
    return {"method":method,"cells":len(frame),"alert_cells":int(frame.alert.sum()),"rule":{"baseline_months":config.baseline_months,"minimum_history":config.minimum_history,"baseline_floor":config.baseline_floor,"alpha":config.alpha,"minimum_count":config.minimum_count}}
