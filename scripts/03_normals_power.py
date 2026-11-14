"""
Step 3 - Compute each district's "normal" (climatology) and how unusual each day is.
Written by Claude (Anthropic AI) for Varun Pisharody's Space Apps 2026 team.

Input : data/power_daily_clean.csv  (from step 2)
Output: data/power_normals.csv      one row per district x day-of-year x variable
        data/power_anomalies.csv    the daily data plus z-score and percentile columns

Idea: "Is today dry?" only makes sense compared with what is normal for THIS
place at THIS time of year. 1 mm of rain in a week is normal in a dry January
in western Kansas but alarming in June in eastern Kansas.

How:
  * Rain on one day is too noisy, so we use running totals: rain over the
    last 30, 60 and 90 days (rain_30d, rain_60d, rain_90d).
  * For each district and each day of the year (1-365), collect every value
    within +/-15 days of that date in the BASELINE years -> about 8 years x
    31 days = ~250 values. Their mean, spread (std) and percentiles = the normal.
  * BASELINE = 2015-04-01 .. 2022-12-31 only (our planned training years), so
    the 2023-2026 test years never leak into the normal.
  * Then for every day: z = (value - normal mean) / normal std, and
    percentile = % of baseline values (same district, same window) below it.
    Percentile 10 = drier than 90 % of normal days.
"""
import os
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WINDOW = 15
BASE_END = "2022-12-31"

df = pd.read_csv(os.path.join(ROOT, "data", "power_daily_clean.csv"), parse_dates=["date"])
df = df.sort_values(["region", "date"])
g = df.groupby("region")["PRECTOTCORR"]
for n in (30, 60, 90):
    df[f"rain_{n}d"] = g.transform(lambda s: s.rolling(n, min_periods=n).sum())

VARS = ["GWETROOT", "GWETTOP", "rain_30d", "rain_60d", "rain_90d", "T2M_MAX", "T2M"]

# day of year 1..365, with Feb 29 folded into Feb 28
doy = df.date.dt.dayofyear
leap_after_feb = df.date.dt.is_leap_year & (doy >= 60)
df["doy"] = np.where(leap_after_feb, doy - 1, doy)

base = df[df.date <= BASE_END]
norm_rows, anom = [], df.copy()
for v in VARS:
    anom[f"{v}_z"] = np.nan
    anom[f"{v}_pct"] = np.nan

for region, b in base.groupby("region"):
    idx_r = anom.region == region
    for d in range(1, 366):
        dist = np.abs(b.doy - d)
        dist = np.minimum(dist, 365 - dist)          # wrap around New Year
        win = b[dist <= WINDOW]
        sel = idx_r & (anom.doy == d)
        for v in VARS:
            vals = np.sort(win[v].dropna().to_numpy())
            if len(vals) < 50:
                continue
            m, s = vals.mean(), vals.std(ddof=1)
            norm_rows.append({"region": region, "doy": d, "variable": v, "n": len(vals),
                              "mean": m, "std": s, "p10": np.percentile(vals, 10),
                              "p50": np.percentile(vals, 50), "p90": np.percentile(vals, 90)})
            x = anom.loc[sel, v].to_numpy()
            anom.loc[sel, f"{v}_z"] = (x - m) / s if s > 0 else np.nan
            # mid-rank percentile: ties count half, so rounded values (POWER gives
            # 2 decimals) do not push percentiles upward
            lo_ = np.searchsorted(vals, x, side="left"); hi_ = np.searchsorted(vals, x, side="right")
            pct = 100 * (lo_ + hi_) / 2 / len(vals)
            anom.loc[sel, f"{v}_pct"] = np.where(np.isnan(x), np.nan, pct)

normals = pd.DataFrame(norm_rows)
normals.to_csv(os.path.join(ROOT, "data", "power_normals.csv"), index=False)
anom.to_csv(os.path.join(ROOT, "data", "power_anomalies.csv"), index=False)
print(f"normals rows: {len(normals):,}  (expected {df.region.nunique()*365*len(VARS):,})")
print(f"anomaly rows: {len(anom):,}")
print("baseline values per window (n): min", normals.n.min(), "median", int(normals.n.median()))
