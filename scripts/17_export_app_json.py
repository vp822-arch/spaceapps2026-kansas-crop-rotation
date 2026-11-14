"""
17_export_app_json.py - export the crop rotation advice as one JSON file for the app.
Written by Claude (Anthropic AI) for Varun Pisharody's Space Apps 2026 team.

Same rows as the database view app_rotation_advice (top 3 rotations per county),
grouped by county, so the app can be built and demoed without database access.

Output: data/app_rotation_advice.json
{
  "data_through": "2026-11-09", "generated": "...", "disclaimer": "...",
  "rotation_glossary": {"W-S-F": "wheat - sorghum - fallow", ...},
  "counties": [ {fips, county, district, k_state_region, lat, lon, alert,
                 drought_probability_now, rootzone_pct_now, basis,
                 rotations: [ {rank, code, name, weight_pct, crops_per_year,
                               score_normal, score_dry_year, note}, x3 ],
                 by_current_crop: { "corn"|"sorghum"|"soybean"|"wheat":
                     {message, rotations: [ {rank, code, name, weight_pct, note}, 0-3 ]} } }, x105 ]
}
by_current_crop = only rotations that include the crop already in the field (from
data/rotation_by_current_crop.csv); "rotations" (no crop given) is unchanged.
"""
import json, os, re
from datetime import datetime, timezone
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda f: os.path.join(ROOT, "data", f)

cmap = pd.read_csv(D("county_district_map.csv"))
rot = pd.read_csv(D("rotation_ranking.csv"))
live = pd.read_csv(D("live_forecast.csv"))
rot = rot[rot.recommended_rank <= 3]                      # same filter as the view
bycc = pd.read_csv(D("rotation_by_current_crop.csv"))
data_through = str(live.issued.max())

def split(name):                                          # "W-S-F (wheat-sorghum-fallow)"
    m = re.match(r"^(\S+)\s*\((.*)\)$", name)
    return (m.group(1), m.group(2)) if m else (name, name)

def _factors():
    """Which weather factors the ranking uses, from data/factor_coefficients.json (fitted to USDA yields)."""
    c = json.load(open(D("factor_coefficients.json")))["crops"]
    return {"description": "Each simulated season is scored water x heat x freeze from NASA POWER weather; "
                           "how much heat and freeze count was fitted to USDA yields (0 = not used).",
            "crops": {k: {"water_need_scaled_by_evapotranspiration": v["et0_scaling"],
                          "heat_loss_per_hot_day": v["b_heat"], "freeze_loss_per_day": v["b_freeze"]}
                      for k, v in c.items()}}

def num(x, nd=3):
    return None if pd.isna(x) else round(float(x), nd)

glossary, counties = {}, []
for c in cmap.sort_values("county").itertuples():
    g = rot[rot.region == c.district].sort_values("recommended_rank")
    if len(g) != 3:
        raise SystemExit(f"{c.county}: expected 3 rotations, found {len(g)}")
    first = g.iloc[0]
    rows = []
    for r in g.itertuples():
        code, name = split(r.rotation)
        glossary[code] = name
        rows.append({"rank": int(r.recommended_rank), "code": code, "name": name,
                     "weight_pct": int(r.weight_pct), "crops_per_year": num(r.crops_per_year, 2),
                     "score_normal": num(r.score_normal), "score_dry_year": num(r.score_dry_year),
                     "note": r.note if isinstance(r.note, str) and r.note else None})
    if sum(x["weight_pct"] for x in rows) != 100:
        raise SystemExit(f"{c.county}: weights do not total 100")
    cc_out = {}
    for crop, gg in bycc[bycc.region == c.district].groupby("current_crop"):
        shown = gg.dropna(subset=["rank"]).sort_values("rank")
        lst = []
        for x in shown.itertuples():
            code, name = split(x.rotation)
            glossary[code] = name
            lst.append({"rank": int(x.rank), "code": code, "name": name, "weight_pct": int(x.weight_pct),
                        "note": x.note if isinstance(x.note, str) and x.note else None})
        if lst and sum(y["weight_pct"] for y in lst) != 100:
            raise SystemExit(f"{c.county} {crop}: weights do not total 100")
        msg = gg.message.iloc[0]
        cc_out[crop] = {"message": msg if isinstance(msg, str) and msg else None, "rotations": lst}
    if sorted(cc_out) != ["corn", "sorghum", "soybean", "wheat"]:
        raise SystemExit(f"{c.county}: missing current-crop entries")
    counties.append({"fips": str(c.fips), "county": c.county, "district": c.district,
                     "k_state_region": first.k_state_region, "lat": c.lat, "lon": c.lon,
                     "alert": first.alert, "drought_probability_now": num(first.drought_probability_now),
                     "rootzone_pct_now": num(first.rootzone_pct_now, 0), "basis": first.basis,
                     "rotations": rows, "by_current_crop": cc_out})

out = {"data_through": data_through,
       "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
       "disclaimer": ("Decision support from NASA POWER weather data (rain, water demand and heat stress; freeze "
                      "risk was tested and not needed) and FAO crop methods, not a guarantee. Weather only "
                      "(no prices, costs, soils or irrigation). "
                      "Check with K-State Research and Extension before acting."),
       "rotation_glossary": dict(sorted(glossary.items())),
       "current_crop_options": ["corn", "sorghum", "soybean", "wheat"],
       "score_factors": _factors(),
       "counties": counties}
with open(D("app_rotation_advice.json"), "w") as f:
    json.dump(out, f, indent=1)
print(f"wrote data/app_rotation_advice.json: {len(counties)} counties x 3 rotations, data through {data_through}")
