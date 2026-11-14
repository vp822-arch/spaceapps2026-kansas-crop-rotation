"""
21_calibrate_factors.py - decide how much heat and freeze count, using REAL Kansas yields.
Written by Claude (Anthropic AI) for Varun Pisharody's Space Apps 2026 team.

For each crop (corn, sorghum, soybeans, winter wheat), every district and harvest year 2015-2025:
  - weather features from NASA POWER (factors.py): season water, ET0 ratio, heat days, freeze metric
  - USDA NASS county yields -> % above/below each county's own average, averaged per district-year
Then, adding one factor at a time (forward selection):
  1. water only (fixed FAO need)                      - the current model
  2. + ET0 scaling of the water need                  - kept only if it improves the test below
  3. + heat (fit b_heat)                              - kept only if it improves the test below
  4. + freeze (fit b_freeze)                          - kept only if it improves the test below
Test = leave-one-year-out: the coefficients are fitted WITHOUT a year, used to score that year, for
every year in turn; the out-of-fold scores are then compared with real yields (within-district
Spearman r, the same headline measure as the yield validation). A factor must raise this
out-of-sample r by at least 0.01, so it is kept only if it predicts years it never saw.
Output: data/factor_coefficients.json (used by 14 and 16), reports/factor_calibration.md
Run manually when the method changes (not part of the weekly refresh): python3 scripts/21_calibrate_factors.py
"""
import json, os, sys
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import factors as F

PSE, CAP = 0.25, 230.0
NASS = {"corn": ("corn", "CORN, GRAIN - YIELD"), "sorghum": ("sorghum", "SORGHUM, GRAIN - YIELD"),
        "soybean": ("soybeans", "SOYBEANS - YIELD"), "wheat": ("wheat", "WHEAT, WINTER - YIELD")}
B_GRID = np.round(np.arange(0, 0.0601, 0.0025), 4)
MIN_GAIN = 0.01

weather = F.load_weather(ROOT)
et0_mean = F.et0_season_means(weather)
cmap = pd.read_csv(os.path.join(ROOT, "data/county_district_map.csv"))


def season_inputs(region, crop, harvest_year):
    """Water (mm) and weather features for one crop season, as in the yield validation (16)."""
    wx = weather[region]; rain = wx.PRECTOTCORR
    (pm, pd_), (hm, hd), hoff = F.CROP[crop][0], F.CROP[crop][1], F.CROP[crop][2]
    plant = pd.Timestamp(harvest_year - hoff, pm, pd_); harv = pd.Timestamp(harvest_year, hm, hd)
    prev_harv = pd.Timestamp(plant.year, 6, 20) if crop == "wheat" else pd.Timestamp(plant.year - 1, hm, hd)
    if prev_harv < rain.index.min() or harv > rain.index.max():
        return None
    stored = min(PSE * rain.loc[prev_harv + pd.Timedelta(days=1):plant - pd.Timedelta(days=1)].sum(), CAP)
    season = rain.loc[plant:harv]
    if crop == "wheat":
        dorm = season[((season.index.month == 11) & (season.index.day >= 16)) | season.index.month.isin([12, 1, 2])]
        water = season.sum() - dorm.sum() + PSE * dorm.sum() + stored
    else:
        water = season.sum() + stored
    feats = F.season_features(wx, crop, plant, harv, et0_mean[(region, crop)])
    return {"water": float(water), **feats}


rows = []
for crop, (fname, sd) in NASS.items():
    y = pd.read_csv(os.path.join(ROOT, f"data/raw/nass/ks_county_yield_{fname}.csv"))
    y = y[(y.short_desc == f"{sd}, MEASURED IN BU / ACRE") & ~y.county_name.str.contains("OTHER")].copy()
    y["Value"] = pd.to_numeric(y.Value.astype(str).str.replace(",", ""), errors="coerce")
    y["fips"] = (y.state_fips_code * 1000 + y.county_code).astype(int)
    y = y.dropna(subset=["Value"]).merge(cmap[["fips", "district"]], on="fips")
    m = y.groupby("fips").Value.transform("mean")
    y["pct_anom"] = 100 * (y.Value - m) / m
    d = y.groupby(["district", "year"]).pct_anom.mean()
    for (district, year), anom in d.items():
        s = season_inputs(district, crop, int(year))
        if s:
            rows.append({"crop": crop, "district": district, "year": int(year), "yield_pct_anom": anom, **s})
data = pd.DataFrame(rows)


def score(g, et0_scaling, b_heat, b_freeze):
    coef = {"crops": {c: {"b_heat": b_heat, "b_freeze": b_freeze, "et0_scaling": et0_scaling} for c in NASS}}
    return np.array([F.season_score(r.crop, r.water, {"heat_days": r.heat_days, "freeze": r.freeze,
                                                      "et0_ratio": r.et0_ratio}, coef)[0] for r in g.itertuples()])


def within_r(g, s):
    x = pd.Series(s, index=g.index)
    x = x - x.groupby(g.district).transform("mean")
    return spearmanr(x, g.yield_pct_anom)[0]


def fit(g, et0_scaling, use_heat, use_freeze):
    best = (-9, 0.0, 0.0)
    for bh in (B_GRID if use_heat else [0.0]):
        for bf in (B_GRID if use_freeze else [0.0]):
            r = within_r(g, score(g, et0_scaling, bh, bf))
            if r > best[0] + 1e-9:
                best = (r, bh, bf)
    return best


def out_of_fold_r(g, et0_scaling, use_heat, use_freeze):
    oof = pd.Series(np.nan, index=g.index)
    for yr in sorted(g.year.unique()):
        tr, te = g[g.year != yr], g[g.year == yr]
        _, bh, bf = fit(tr, et0_scaling, use_heat, use_freeze)
        oof[te.index] = score(te, et0_scaling, bh, bf)
    return within_r(g, oof.values)


out = {"method": "water x heat x freeze; coefficients fitted to USDA NASS county yields 2015-2025; "
                 "factor kept only if leave-one-year-out within-district Spearman r improves by >= 0.01",
       "crops": {}}
lines = ["# How much each weather factor counts (calibrated on real Kansas yields)", "",
         "Test = leave-one-year-out: coefficients fitted without a year, then used to score that year. "
         "r = within-district Spearman correlation of those out-of-sample scores with real USDA yields "
         "(same measure as the yield validation). A factor is kept only if it raises r by at least 0.01.", "",
         "| crop | district-years | water only | + ET0-scaled need | + heat | + freeze | kept | b_heat (per day) | b_freeze (per day) |",
         "|---|---|---|---|---|---|---|---|---|"]
for crop in NASS:
    g = data[data.crop == crop].reset_index(drop=True)
    steps = []
    cur = {"et0_scaling": False, "heat": False, "freeze": False}
    base = out_of_fold_r(g, False, False, False); steps.append(base); best_r = base
    for name in ("et0_scaling", "heat", "freeze"):
        trial = dict(cur, **{name: True})
        r = out_of_fold_r(g, trial["et0_scaling"], trial["heat"], trial["freeze"])
        steps.append(r)
        if r >= best_r + MIN_GAIN:
            cur, best_r = trial, r
    r_all, bh, bf = fit(g, cur["et0_scaling"], cur["heat"], cur["freeze"])
    out["crops"][crop] = {"et0_scaling": cur["et0_scaling"], "b_heat": float(bh), "b_freeze": float(bf),
                          "oof_r_water_only": round(base, 3), "oof_r_final": round(best_r, 3),
                          "n": int(len(g))}
    kept = ", ".join(k for k, v in cur.items() if v) or "water only"
    lines.append(f"| {crop} | {len(g)} | {steps[0]:.2f} | {steps[1]:.2f} | {steps[2]:.2f} | {steps[3]:.2f} | "
                 f"{kept} | {bh:.4f} | {bf:.4f} |")
lines += ["", "Each '+' column adds that factor to the best model so far (whether or not the previous one was kept "
          "is shown in 'kept'). Double-crop soybean uses the soybean coefficients. Heat = days at or above the "
          "crop's threshold in its flowering window; freeze = wheat: days at or below 28 F while heading; "
          "summer crops: days of season lost to a 28 F fall freeze. Source thresholds: see factors.py and REFERENCES.md."]
json.dump(out, open(os.path.join(ROOT, "data/factor_coefficients.json"), "w"), indent=1)
open(os.path.join(ROOT, "reports/factor_calibration.md"), "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
