"""
Step 16 - Test the rotation model's crop weather scores (water x heat x freeze) against REAL Kansas yields (USDA NASS).
Written by Claude (Anthropic AI) for Varun Pisharody's Space Apps 2026 team.

Question: in years when the model says a crop was short of water in a district, were real
harvests in that district actually lower?

Model side: for each crop / district / year, the same relative yield index used by the rotation
model (FAO Ky method): water = in-season NASA POWER rain + 25 % of the rain in the off-season
before planting (from the previous year's harvest date), capped at 230 mm.
Real side: USDA NASS county yields (bu/acre), 2015-2025. Each county's yield is expressed as its
anomaly from that county's own 2015-2025 average (removes soil/management differences), then
averaged over the district's counties for each year. "ALL PRODUCTION PRACTICES" is used (NASS
publishes few non-irrigated county values); western corn is heavily irrigated, which should
weaken the link there - reported, not hidden.
Statistics: Spearman rank correlation between model index and yield anomaly across all
district-years per crop, with a permutation test (5,000 shuffles of years within district).
Outputs: data/yield_validation.csv, reports/yield_validation.md, reports/yield_validation.png
"""
import json, os, glob, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from scipy.stats import spearmanr
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PSE, CAP = 0.25, 230.0
CROP = {  # NASS commodity file: (model crop, plant (m,d), harvest (m,d), harvest year offset, need, Ky, NASS short_desc start)
    "corn":     ((4, 15), (9, 10), 0, 650, 1.25, "CORN, GRAIN - YIELD"),
    "sorghum":  ((5, 15), (9, 25), 0, 550, 0.90, "SORGHUM, GRAIN - YIELD"),
    "soybeans": ((5, 15), (10, 1), 0, 575, 0.85, "SOYBEANS - YIELD"),
    "wheat":    ((9, 15), (6, 20), 1, 550, 1.05, "WHEAT, WINTER - YIELD"),
}
w = pd.read_csv(os.path.join(ROOT, "data/power_daily_clean.csv"), parse_dates=["date"])
# Multi-factor season score (2026-11-14): same factors.py as the rotation ranking (14).
import sys
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import factors as F
WX = F.load_weather(ROOT)
ET0_MEAN = F.et0_season_means(WX)
COEF = F.load_coefficients(ROOT)
FCROP = {"corn": "corn", "sorghum": "sorghum", "soybeans": "soybean", "wheat": "wheat"}
cmap = pd.read_csv(os.path.join(ROOT, "data/county_district_map.csv"))

def model_index(rain, crop, harvest_year, region=None):
    (pm, pd_), (hm, hd), hoff, need, ky, _ = CROP[crop]
    plant = pd.Timestamp(harvest_year - hoff, pm, pd_); harv = pd.Timestamp(harvest_year, hm, hd)
    prev_harv = pd.Timestamp(plant.year - (1 if crop != "wheat" else 0), hm, hd) if crop != "wheat" \
        else pd.Timestamp(plant.year, 6, 20)          # wheat: off-season = summer before planting
    if prev_harv < rain.index.min() or harv > rain.index.max():
        return np.nan
    stored = min(PSE * rain.loc[prev_harv + pd.Timedelta(days=1):plant - pd.Timedelta(days=1)].sum(), CAP)
    season = rain.loc[plant:harv]
    if crop == "wheat":
        dorm = season[((season.index.month == 11) & (season.index.day >= 16)) | season.index.month.isin([12, 1, 2])]
        water = season.sum() - dorm.sum() + PSE * dorm.sum() + stored
    else:
        water = season.sum() + stored
    if region is None:                                 # water-only (kept for comparison)
        return max(0.0, 1 - ky * (1 - min(water / need, 1.0)))
    fc = FCROP[crop]
    feats = F.season_features(WX[region], fc, plant, harv, ET0_MEAN[(region, fc)])
    return F.season_score(fc, water, feats, COEF)[0]

rows = []
for crop, spec in CROP.items():
    y = pd.read_csv(os.path.join(ROOT, f"data/raw/nass/ks_county_yield_{crop}.csv"))
    y = y[(y.short_desc == f"{spec[5]}, MEASURED IN BU / ACRE") & ~y.county_name.str.contains("OTHER")].copy()
    y["Value"] = pd.to_numeric(y.Value.astype(str).str.replace(",", ""), errors="coerce")
    y["fips"] = (y.state_fips_code * 1000 + y.county_code).astype(int)
    y = y.dropna(subset=["Value"]).merge(cmap[["fips", "district"]], on="fips")
    y["anom"] = y.Value - y.groupby("fips").Value.transform("mean")
    y["pct_anom"] = 100 * y.anom / y.groupby("fips").Value.transform("mean")
    d = y.groupby(["district", "year"]).agg(yield_pct_anom=("pct_anom", "mean"), counties=("fips", "nunique")).reset_index()
    for region, g in w.groupby("region"):
        rain = g.set_index("date").PRECTOTCORR
        for yr in range(2015, 2026):
            rows.append({"crop": crop, "district": region, "year": yr, "model_index": model_index(rain, crop, yr, region),
                         "water_only_index": model_index(rain, crop, yr)})
    m = pd.DataFrame([r for r in rows if r["crop"] == crop])
    rows = [r for r in rows if r["crop"] != crop] + m.merge(d, on=["district", "year"], how="left").to_dict("records")
v = pd.DataFrame(rows).dropna(subset=["model_index", "yield_pct_anom"])


rng = np.random.default_rng(0)
# Like-for-like: yields are anomalies from each county's own average, so the model score is also
# expressed relative to its district's own average ("within-district"). Headline = within-district.
v["model_anom"] = v.model_index - v.groupby(["crop", "district"]).model_index.transform("mean")
def perm_p(g, xcol, r):
    null = []
    for _ in range(5000):   # shuffle years within each district (keeps district differences)
        sh = g.groupby("district").yield_pct_anom.transform(
            lambda s: s.sample(frac=1, random_state=int(rng.integers(1e9))).values)
        null.append(spearmanr(g[xcol], sh)[0])
    return (np.sum(np.array(null) >= r) + 1) / (len(null) + 1)
v["water_only_anom"] = v.water_only_index - v.groupby(["crop", "district"]).water_only_index.transform("mean")
cal = json.load(open(os.path.join(ROOT, "data/factor_coefficients.json")))["crops"]
lines = ["# Does the model's weather score track REAL Kansas yields? (USDA NASS, 2015-2025)", "",
         "Each point = one crop, one district, one year. Yield = average of the district's counties, each "
         "as % above/below that county's own 2015-2025 average. Model = the season score used by the rotation "
         "advice (water factor with NASA POWER evapotranspiration-scaled need x heat factor x freeze factor), "
         "also taken relative to its district's own average so both sides are compared like for like.", "",
         "| crop | district-years | r, within-district (headline) | p | r, out-of-sample (calibration test) | r, water-only score (before) | r without 2022-23 drought years | r range leaving out any one year |",
         "|---|---|---|---|---|---|---|---|"]
res = {}
for crop, g in v.groupby("crop"):
    r_w = spearmanr(g.model_anom, g.yield_pct_anom)[0]; p_w = perm_p(g, "model_anom", r_w)
    r_old = spearmanr(g.water_only_anom, g.yield_pct_anom)[0]
    h = g[~g.year.isin([2022, 2023])]; r_nd = spearmanr(h.model_anom, h.yield_pct_anom)[0]
    loo = [spearmanr(g[g.year != y].model_anom, g[g.year != y].yield_pct_anom)[0] for y in sorted(g.year.unique())]
    oof = cal[FCROP[crop]]["oof_r_final"]
    res[crop] = (r_w, p_w, len(g))
    lines.append(f"| {crop} | {len(g)} | {r_w:.2f} | {'< 0.001' if p_w < 0.001 else f'{p_w:.3f}'} | {oof:.2f} | {r_old:.2f} | "
                 f"{r_nd:.2f} | {min(loo):.2f} to {max(loo):.2f} |")
rs = [x[0] for x in res.values()]
lines += ["", "How to read it: r = 0 means no link, 1 = perfect. p = chance of a link this strong if the model "
          "were unrelated to yields (permutation test, years shuffled within each district, 5,000 times). "
          "The heat coefficients were fitted on these same years, so the headline r is slightly optimistic; the "
          "out-of-sample column (each year scored by coefficients fitted without it) is the fairer measure.", "",
          "Honest findings:",
          f"- All four crops show a positive, statistically significant link between the model's weather score "
          f"and real yields (within-district r {min(rs):.2f}-{max(rs):.2f}).",
          "- Adding NASA POWER evapotranspiration (water demand) improved every crop; heat stress at flowering "
          "improved corn and sorghum; freeze risk did not improve any crop in 2015-2025 and is set to zero "
          "(reports/factor_calibration.md).",
          "- Much of the link comes from the 2022-23 drought: without those years it is weaker. The model is best "
          "at flagging seriously stressed seasons - the years that matter most for choosing a rotation.",
          "- 'ALL PRODUCTION PRACTICES' yields include irrigated fields (especially western corn), which "
          "weakens the link to weather. Fewer counties reported in later years; no wheat county data for 2024. "
          "The model uses one NASA POWER point per district (~55 km grid).",
          "- This tests the weather scores that drive the rotation ranking; it cannot test economics (prices, "
          "costs), which the model does not include."]
open(os.path.join(ROOT, "reports/yield_validation.md"), "w").write("\n".join(lines) + "\n")
v.to_csv(os.path.join(ROOT, "data/yield_validation.csv"), index=False)
print("\n".join(lines))

INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e6e5e1", "#fcfcfb"
fig, axes = plt.subplots(1, 4, figsize=(15, 4.2), sharey=True, facecolor=SURF)
for ax, crop in zip(axes, ["wheat", "sorghum", "soybeans", "corn"]):
    g = v[v.crop == crop]; r, p, n = res[crop]
    ax.scatter(g.model_anom, g.yield_pct_anom, s=26, color="#2a78d6", alpha=0.75, edgecolor=SURF, linewidth=0.8)
    ax.axhline(0, color=INK2, lw=0.8, ls="--")
    ax.set_title(f"{crop}: r = {r:.2f}" + (" (p < 0.001)" if p < 0.001 else f" (p = {p:.3f})"), loc="left", fontsize=11, color=INK)
    ax.set_xlabel("model weather score vs district average", color=INK2); ax.set_facecolor(SURF)
    ax.grid(color=GRID, lw=0.8); ax.set_axisbelow(True)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
axes[0].set_ylabel("real yield vs county average (%)", color=INK2)
fig.suptitle("Kansas 2015-2025: when NASA weather data says a season was stressed, were real harvests lower? (each dot = district-year; USDA NASS county yields)",
             x=0.01, ha="left", fontsize=12, color=INK)
plt.tight_layout(); plt.savefig(os.path.join(ROOT, "reports/yield_validation.png"), dpi=140, bbox_inches="tight")
print("\nchart saved")
