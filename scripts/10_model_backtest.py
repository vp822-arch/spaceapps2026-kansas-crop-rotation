"""
Step 10 - Features, drought-warning model, and an honest backtest.
Written by Claude (Anthropic AI) for Varun Pisharody's Space Apps 2026 team.

Question the model answers, every week, for every district:
   "Will this district be in drought about 4 weeks (29 days) after our latest data?"
   drought = at least 50 % of the district's county area in USDM category D1 or worse.

Inputs (all known at prediction time - nothing from the future):
   - NASA POWER root-zone and surface soil wetness percentiles (vs that district's normal)
   - 30/60/90-day rain percentiles, max-temperature z-score
   - 4-week change in root-zone percentile (how fast it is drying)
   - time of year (sin/cos of week)
   - current USDM drought coverage (published weekly, so known in real time)
Train: 2015-2022.  Test: 2023 onward (never seen in training or in the normals).

Compared against two simple baselines judges expect:
   - persistence: "in 4 weeks it will be the same as now"
   - climatology: "the usual drought rate for this district and month"
Scores: hit rate (share of real droughts we warned about), false alarm ratio
(share of warnings that were wrong), Brier score (lower = better probabilities).
The fairest test is ONSET: weeks where the district is NOT in drought now - can we
warn before it starts? Persistence can never warn of an onset.
Outputs: reports/model_report.md, data/model_predictions.csv
"""
import os, numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import brier_score_loss, roc_auc_score

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Timing (fixed after a double-check): a week's inputs run from its Tuesday (USDM map date)
# to the following Monday (day 6). The forecast is "issued" at the end of day 6. The target
# is the USDM map LEAD weeks after the week's Tuesday, so with LEAD = 5 the target is
# 35 - 6 = 29 days after the last day of input data, i.e. truly about 4 weeks ahead.
LEAD, THRESH, TEST_START = 5, 50.0, "2023-01-01"
DAYS_AHEAD = LEAD * 7 - 6

a = pd.read_csv(os.path.join(ROOT, "data/power_anomalies.csv"), parse_dates=["date"])
u = pd.read_csv(os.path.join(ROOT, "data/usdm_district_weekly.csv"), parse_dates=["week"])
a["week"] = a.date - pd.to_timedelta((a.date.dt.dayofweek - 1) % 7, unit="D")   # USDM weeks start Tuesday
a.loc[a.gwetroot_flag == 1, "GWETROOT_pct"] = np.nan   # suspect root-zone values only (see step 2)
cols = ["GWETROOT_pct", "GWETTOP_pct", "rain_30d_pct", "rain_60d_pct", "rain_90d_pct", "T2M_MAX_z"]
w = a.groupby(["region", "week"])[cols].mean().reset_index()
nroot = a.groupby(["region", "week"]).GWETROOT_pct.count().values
w.loc[nroot < 7, "GWETROOT_pct"] = np.nan     # partial weeks of root-zone data -> treat as missing
d = w.merge(u, left_on=["region", "week"], right_on=["district", "week"]).sort_values(["region", "week"])
g = d.groupby("region")
d["drying_4w"] = d.GWETROOT_pct - g.GWETROOT_pct.shift(4)
d["usdm_now"] = d.pct_D1_or_worse
d["in_drought_now"] = (d.usdm_now >= THRESH).astype(int)
d["target"] = (g.pct_D1_or_worse.shift(-LEAD) >= THRESH).astype(float)
d.loc[g.pct_D1_or_worse.shift(-LEAD).isna(), "target"] = np.nan
woy = d.week.dt.isocalendar().week.astype(float)
d["season_sin"], d["season_cos"] = np.sin(2*np.pi*woy/52.18), np.cos(2*np.pi*woy/52.18)
d["month"] = d.week.dt.month
FEATS = cols + ["drying_4w", "usdm_now", "season_sin", "season_cos"]
d_all = d.copy()                               # every week, incl. the newest (no outcome yet)
d = d.dropna(subset=FEATS + ["target"])
train, test = d[d.week < TEST_START].copy(), d[d.week >= TEST_START].copy()

clim = train.groupby(["region", "month"]).target.mean()
for df in (train, test):
    df["p_climatology"] = [clim.get((r, m), train.target.mean()) for r, m in zip(df.region, df.month)]
    df["p_persistence"] = df.in_drought_now.astype(float)

models = {"logistic": make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)),
          "gradient_boosting": HistGradientBoostingClassifier(max_depth=3, learning_rate=0.05,
                                                              max_iter=300, random_state=0)}
for name, m in models.items():
    m.fit(train[FEATS], train.target)
    test[f"p_{name}"] = m.predict_proba(test[FEATS])[:, 1]

def scores(df, p, cut=0.5):
    y, pr = df.target.values, df[p].values
    warn = pr >= cut
    hits = (warn & (y == 1)).sum(); events = (y == 1).sum(); warns = warn.sum()
    return {"hit_rate": hits/events if events else np.nan,
            "false_alarm_ratio": (warns-hits)/warns if warns else np.nan,
            "brier": brier_score_loss(y, pr),
            "auc": roc_auc_score(y, pr) if len(set(y)) > 1 else np.nan,
            "n": len(df), "events": int(events)}

lines = ["# Drought-warning model: backtest report", "",
         f"Target: district in drought (>= {THRESH:.0f}% area in USDM D1+) **{DAYS_AHEAD} days after the last day of input data** "
         f"(about 4 weeks; target map = {LEAD} weeks after the input week's Tuesday).",
         f"Train: {train.week.min().date()} to {train.week.max().date()} ({len(train)} district-weeks).",
         f"Test: {test.week.min().date()} to {test.week.max().date()} ({len(test)} district-weeks, never seen in training).", ""]
for title, sub in [("All test weeks", test), ("Onset only (not in drought now)", test[test.in_drought_now == 0])]:
    lines += [f"## {title}", "", "| method | hit rate | false alarm ratio | Brier (lower better) | AUC | droughts |",
              "|---|---|---|---|---|---|"]
    for p in ["p_persistence", "p_climatology", "p_logistic", "p_gradient_boosting"]:
        s = scores(sub, p)
        lines.append(f"| {p[2:]} | {s['hit_rate']:.2f} | {s['false_alarm_ratio']:.2f} | {s['brier']:.3f} | "
                     f"{s['auc']:.2f} | {s['events']} / {s['n']} |")
    lines.append("")

# which inputs matter (logistic coefficients on standardized inputs)
coef = models["logistic"][-1].coef_[0]
lines += ["## What drives the logistic model (standardized coefficients; negative = wetter lowers risk)", ""]
lines += [f"- {f}: {c:+.2f}" for f, c in sorted(zip(FEATS, coef), key=lambda t: -abs(t[1]))]
lines += ["", "Notes: hit rate and false alarm ratio use a 50 % probability cut-off. Persistence cannot warn of "
          "onsets by definition (it scores 0 there). POWER soil wetness is MERRA-2 model output at ~55 km; "
          "SMAP will be added when the AppEEARS download finishes."]
open(os.path.join(ROOT, "reports/model_report.md"), "w").write("\n".join(lines) + "\n")
# LIVE forecast: newest week per district (its outcome is still in the future)
FEATS_NOROOT = [f for f in FEATS if f not in ("GWETROOT_pct", "drying_4w")]
backup = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)).fit(train[FEATS_NOROOT], train.target)
nb = backup.predict_proba(test[FEATS_NOROOT])[:, 1]
lines += [f"Backup model without root-zone wetness (used when it is flagged suspect): test Brier "
          f"{brier_score_loss(test.target, nb):.3f}, AUC {roc_auc_score(test.target, nb):.2f}"]
open(os.path.join(ROOT, "reports/model_report.md"), "w").write("\n".join(lines) + "\n")
live = d_all.dropna(subset=FEATS_NOROOT).sort_values("week").groupby("region").tail(1).copy()
live["model_used"] = np.where(live[FEATS].notna().all(axis=1), "main", "backup (root zone suspect)")
main_ok = live.model_used == "main"
live["p_logistic"] = backup.predict_proba(live[FEATS_NOROOT])[:, 1]
live["p_gradient_boosting"] = np.nan
if main_ok.any():
    live.loc[main_ok, "p_logistic"] = models["logistic"].predict_proba(live.loc[main_ok, FEATS])[:, 1]
    live.loc[main_ok, "p_gradient_boosting"] = models["gradient_boosting"].predict_proba(live.loc[main_ok, FEATS])[:, 1]
live["issued"] = live.week + pd.Timedelta(days=6)
live["forecast_for_week"] = live.week + pd.Timedelta(weeks=LEAD)
live[["region", "week", "issued", "forecast_for_week", "usdm_now", "GWETROOT_pct", "rain_90d_pct",
      "p_logistic", "p_gradient_boosting", "model_used"]].to_csv(os.path.join(ROOT, "data/live_forecast.csv"), index=False)
keep = ["region", "week", "usdm_now", "target", "p_persistence", "p_climatology", "p_logistic", "p_gradient_boosting"]
test[keep].to_csv(os.path.join(ROOT, "data/model_predictions.csv"), index=False)
print("\n".join(lines))
