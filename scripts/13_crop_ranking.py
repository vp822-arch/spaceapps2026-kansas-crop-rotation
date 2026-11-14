"""
Step 13 - Rank Kansas spring/summer crops per district (decision support, not a guarantee).
Written by Claude (Anthropic AI) for Varun Pisharody's Space Apps 2026 team.

Sourced inputs (cite in References):
  Planting/harvest windows: USDA NASS (2010) Agricultural Handbook 628 "most active" Kansas dates,
    as tabulated by K-State Agronomy eUpdate: corn plant from Apr 15 / harvest from Sep 10;
    grain sorghum May 15 / Sep 25; soybeans May 15 / Oct 1; winter wheat Sep 15 / Jun 20.
  Seasonal crop water need (mm per growing period): FAO (1986), tabulated by SSWM:
    maize 500-800, sorghum 450-650, soybean 450-700, wheat 450-650.
  Seasonal yield response factor Ky (FAO Irrigation & Drainage Paper 33, Table 1 in FAO I&D
    Paper 66): maize 1.25, sorghum 0.9, soybean 0.85, winter wheat 1.05.
    FAO water production function: 1 - Ya/Ym = Ky * (1 - ETa/ETm).
Our data: NASA POWER daily rain per district; live drought alert per district.

Method (Claude's design; first version was revised after review because it ranked winter
wheat against summer crops and ignored drought sensitivity):
  1. Water-use season per crop = start of planting window -> start of harvest window.
  2. Season rain per district for each complete season 2015-2025 (11 seasons);
     normal = median, dry year = 25th percentile.
  3. Supply ratio r = season rain / crop water need (FAO midpoint), capped at 1.
  4. Relative yield index = 1 - Ky * (1 - r)   (FAO I&D 33 water production function).
     Rain is not all usable and stored soil water also counts, so this is a RELATIVE index
     for comparing crops in the same place, not a yield forecast.
  5. Rank corn / sorghum / soybeans by the normal-year index and by the dry-year index.
     Recommended order = dry-year order if the district's current alert is watch/warning
     (probability >= 30%), else normal-year order.
  Winter wheat (already planted for 2026-27) is reported separately, not ranked.
Outputs: data/crop_ranking.csv, reports/crop_ranking.md
"""
import os, pandas as pd, numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CROPS = {  # crop: (season start, season end, FAO need low, high, Ky)
    "corn":          ((4, 15), (9, 10), 500, 800, 1.25),
    "grain sorghum": ((5, 15), (9, 25), 450, 650, 0.90),
    "soybeans":      ((5, 15), (10, 1), 450, 700, 0.85),
    "winter wheat":  ((9, 15), (6, 20), 450, 650, 1.05),   # crosses New Year; reported, not ranked
}
WATCH = 0.30
w = pd.read_csv(os.path.join(ROOT, "data/power_daily_clean.csv"), parse_dates=["date"])
live = pd.read_csv(os.path.join(ROOT, "data/live_forecast.csv")).set_index("region")

def yindex(rain, need, ky):
    r = min(rain / need, 1.0)
    return max(0.0, 1 - ky * (1 - r))

rows = []
for crop, (s, e, lo, hi, ky) in CROPS.items():
    need = (lo + hi) / 2
    for region, g in w.groupby("region"):
        g = g.set_index("date").PRECTOTCORR
        totals = []
        for yr in range(2015, 2026):
            start, end = pd.Timestamp(yr, *s), pd.Timestamp(yr + (1 if e < s else 0), *e)
            if start >= g.index.min() and end <= g.index.max():
                totals.append(g.loc[start:end].sum())
        totals = np.array(totals); normal, dry = np.median(totals), np.percentile(totals, 25)
        rows.append({"region": region, "crop": crop, "ky": ky, "fao_need_mm": f"{lo}-{hi}",
                     "seasons_used": len(totals), "season_rain_normal_mm": round(normal),
                     "season_rain_dry_year_mm": round(dry),
                     "yield_index_normal": round(yindex(normal, need, ky), 2),
                     "yield_index_dry_year": round(yindex(dry, need, ky), 2)})
r = pd.DataFrame(rows)
r["drought_probability_now"] = r.region.map(live.p_logistic).round(2)
r["alert"] = np.where(r.drought_probability_now >= 0.5, "warning",
                      np.where(r.drought_probability_now >= WATCH, "watch", "normal"))
summer = r.crop != "winter wheat"
for col, tag in [("yield_index_normal", "rank_normal"), ("yield_index_dry_year", "rank_dry_year")]:
    r.loc[summer, tag] = r[summer].groupby("region")[col].rank(ascending=False, method="min")
r["recommended_rank"] = np.where(r.alert == "normal", r.rank_normal, r.rank_dry_year)
r["basis"] = np.where(r.alert == "normal", "normal-year water", "dry-year water (district on watch/warning)")
r = r.sort_values(["region", "recommended_rank"])
r.to_csv(os.path.join(ROOT, "data/crop_ranking.csv"), index=False)

lines = ["# Kansas spring/summer crop ranking by district (decision support, not a guarantee)", "",
         "Relative yield index = 1 - Ky x (1 - season rain / FAO crop water need), capped at 0-1 "
         "(FAO I&D Paper 33). Higher = less yield lost to water shortage. Compares crops in the same "
         "place; it is not a yield forecast.", "",
         "| district | alert now | order used | 1st | 2nd | 3rd |", "|---|---|---|---|---|---|"]
for region, g in r.loc[r.crop != "winter wheat"].groupby("region"):
    col = "yield_index_normal" if g.alert.iloc[0] == "normal" else "yield_index_dry_year"
    cells = [f"{c} ({x:.2f})" for c, x in zip(g.crop, g[col])]
    lines.append(f"| {region.replace('ks_', '')} | {g.alert.iloc[0]} ({g.drought_probability_now.iloc[0]:.0%}) | "
                 f"{'dry year' if col.endswith('dry_year') else 'normal year'} | " + " | ".join(cells) + " |")
ww = r.loc[r.crop == "winter wheat"].set_index("region")
lines += ["", "Winter wheat (already planted for 2026-27; for next fall's decision) relative yield index, "
          "normal / dry year: " + "; ".join(f"{k.replace('ks_', '')} {v.yield_index_normal:.2f}/{v.yield_index_dry_year:.2f}"
                                            for k, v in ww.iterrows()),
          "", "Caveats: rain only - no irrigation, groundwater, stored soil water, soil type, prices, seed "
          "access or local practice. Ky and water needs are FAO generic values, not Kansas-calibrated. "
          "11 seasons of NASA POWER rain at 0.5 deg (~55 km). The current drought alert is a 4-week "
          "forecast, used only to choose the cautious (dry-year) order. Check with K-State Research and "
          "Extension before acting."]
open(os.path.join(ROOT, "reports/crop_ranking.md"), "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
