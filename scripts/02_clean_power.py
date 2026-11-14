"""
Step 2 - Clean the NASA POWER daily data.
Written by Claude (Anthropic AI) for Varun Pisharody's Space Apps 2026 team.

Input : data/power_daily_raw.csv   (from step 1)
Output: data/power_daily_clean.csv
        reports/power_quality_report.md

What "cleaning" means here:
  1. -999 is POWER's "no data" code  -> turn into a real blank (NaN).
  2. Duplicate rows (same district + date) -> keep one.
  3. Missing calendar days -> add them back as blank rows, so gaps are visible.
  4. Impossible values (negative rain, humidity > 100 %, Tmin > Tmax, ...)
     -> blank them and count them.
  5. The newest few days are often not filled in yet -> trim each district's
     record to the last day where every variable is present.
  6. Short gaps (<= 3 days) in smooth variables (temperature, humidity, sun,
     wind, soil wetness) are filled by straight-line interpolation; rain is
     NEVER interpolated (a gap in rain is not "average rain").
Every change is counted in the report.
"""
import os
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
raw = pd.read_csv(os.path.join(ROOT, "data", "power_daily_raw.csv"), parse_dates=["date"])
VARS = [c for c in raw.columns if c not in ("region", "point", "lat", "lon", "date")]
SMOOTH = [v for v in VARS if v != "PRECTOTCORR"]

# physical limits: (min, max)
LIMITS = {"PRECTOTCORR": (0, 400), "T2M": (-45, 50), "T2M_MAX": (-45, 55),
          "T2M_MIN": (-50, 45), "RH2M": (0, 100), "ALLSKY_SFC_SW_DWN": (0, 45),
          "WS2M": (0, 40), "GWETTOP": (0, 1), "GWETROOT": (0, 1)}

log = ["# NASA POWER data-quality report", "",
       f"Input rows: {len(raw):,}  |  districts: {raw.region.nunique()}  |  "
       f"dates {raw.date.min().date()} to {raw.date.max().date()}", ""]

df = raw.copy()
df[VARS] = df[VARS].replace(-999, np.nan)
log.append(f"- `-999` codes turned into blanks: {int(raw[VARS].eq(-999).sum().sum()):,}")

before = len(df)
df = df.drop_duplicates(["region", "date"])
log.append(f"- Duplicate rows removed: {before - len(df)}")

out, added_days, trimmed, bad_total, filled_total, flag_notes = [], 0, 0, {}, {}, []
for region, g in df.groupby("region"):
    g = g.set_index("date").sort_index()
    full = pd.date_range(g.index.min(), g.index.max(), freq="D")
    added_days += len(full) - len(g)
    g = g.reindex(full)
    for c in ("region", "point", "lat", "lon"):
        g[c] = g[c].ffill().bfill()

    for v, (lo, hi) in LIMITS.items():
        if v in g:
            bad = (g[v] < lo) | (g[v] > hi)
            bad_total[v] = bad_total.get(v, 0) + int(bad.sum())
            g.loc[bad, v] = np.nan
    if {"T2M_MIN", "T2M_MAX"} <= set(g):
        bad = g.T2M_MIN > g.T2M_MAX
        bad_total["Tmin>Tmax"] = bad_total.get("Tmin>Tmax", 0) + int(bad.sum())
        g.loc[bad, ["T2M_MIN", "T2M_MAX"]] = np.nan

    complete = g[VARS].notna().all(axis=1)
    last_ok = complete[complete].index.max()
    trimmed += int((g.index > last_ok).sum())
    g = g.loc[:last_ok]

    for v in SMOOTH:
        n0 = g[v].isna().sum()
        g[v] = g[v].interpolate(limit=3, limit_area="inside")
        filled_total[v] = filled_total.get(v, 0) + int(n0 - g[v].isna().sum())

    # 7. Physical-consistency check (added after finding a bad step in Oct 2026):
    #    root-zone wetness (top ~1 m) cannot drop > 0.05 in one day while it rains > 5 mm.
    #    Flag that day and every later day for this district as "suspect" (the level
    #    stays shifted afterwards), so the app does not report a false drought.
    d = g["GWETROOT"].diff()
    breaks = g.index[(d < -0.05) & (g["PRECTOTCORR"] > 5)]
    g["gwetroot_flag"] = 0
    if len(breaks):
        g.loc[g.index >= breaks.min(), "gwetroot_flag"] = 1
        flag_notes.append(f"{region}: root-zone wetness fell {d.loc[breaks.min()]:.2f} in one day on "
                          f"{breaks.min().date()} during {g.loc[breaks.min(),'PRECTOTCORR']:.1f} mm of rain "
                          f"-> {int(g.gwetroot_flag.sum())} days from then on flagged suspect")
    g.index.name = "date"
    out.append(g.reset_index())

clean = pd.concat(out, ignore_index=True)[["region", "point", "lat", "lon", "date"] + VARS + ["gwetroot_flag"]]
clean["point"] = clean["point"].astype(int)

log += [f"- Missing calendar days added back as blank rows: {added_days}",
        f"- Newest not-yet-filled days trimmed off: {trimmed} "
        f"(clean record ends {clean.date.max().date()})",
        "- Impossible values blanked: " + (", ".join(f"{k} {v}" for k, v in bad_total.items() if v) or "none"),
        "- Short gaps (<= 3 days) filled by interpolation: " + (", ".join(f"{k} {v}" for k, v in filled_total.items() if v) or "none"),
        "- Physical-consistency flags (gwetroot_flag = 1 means root-zone value is suspect): "
        + ("; ".join(flag_notes) or "none"),
        "", "## Remaining blanks after cleaning (per variable)", "",
        "| variable | blanks | % |", "|---|---|---|"]
for v in VARS:
    n = int(clean[v].isna().sum())
    log.append(f"| {v} | {n} | {100*n/len(clean):.2f} |")

log += ["", "## Per-district summary", "",
        "| district | first day | last day | days | mean rain mm/day | mean T2M C | mean root-zone wetness |",
        "|---|---|---|---|---|---|---|"]
for r, g in clean.groupby("region"):
    log.append(f"| {r} | {g.date.min().date()} | {g.date.max().date()} | {len(g)} | "
               f"{g.PRECTOTCORR.mean():.2f} | {g.T2M.mean():.1f} | {g.GWETROOT.mean():.2f} |")

clean.to_csv(os.path.join(ROOT, "data", "power_daily_clean.csv"), index=False)
open(os.path.join(ROOT, "reports", "power_quality_report.md"), "w").write("\n".join(log) + "\n")
print("\n".join(log))
