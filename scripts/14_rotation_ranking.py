"""
Step 14 - Suggest and rank the top 3 crop ROTATIONS per Kansas district (decision support).
Written by Claude (Anthropic AI) for Varun Pisharody's Space Apps 2026 team.

Candidate rotations come from K-State guidance, by region (cite in References):
  K-State MF2908 "No-Till in Kansas: Rotations and Cultural Practices" (2009):
    West: wheat/corn/sorghum/fallow; ecofallow wheat/sorghum/fallow and wheat/corn/fallow.
    Central: corn/soybeans, sorghum/soybeans, wheat/double-crop soybeans/corn, wheat/sorghum/fallow.
    East: corn/soybean and sorghum/soybean; SE Kansas: double-crop soybeans after wheat do best
      when corn or sorghum preceded the wheat (-> corn/wheat/double-crop soybean).
  K-State Tribune study (Schlegel et al.): W-F, W-S-F, W-C-F, continuous sorghum, W-C-S-F; summer
    crop yields "about twice as great following wheat than following corn or grain sorghum";
    wheat-sorghum-fallow most profitable there.
  Districts are assigned to K-State's west / central / east regions by their names (the NASS
  districts' column of the state).

Crop windows (planting -> start of harvest) from USDA NASS Ag Handbook 628 via K-State eUpdate:
  corn Apr 15-Sep 10, sorghum May 15-Sep 25, soybean May 15-Oct 1, wheat Sep 15-Jun 20.
  Double-crop soybean: Jul 1-Oct 15 (Claude's assumption: planted after wheat harvest).
Crop water need (FAO 1986, midpoints): corn 650, sorghum 550, soybean 575, wheat 550 mm;
  double-crop soybean 450 mm (FAO lower bound; shorter season - Claude's assumption).
Yield response factor Ky (FAO I&D 33): corn 1.25, sorghum 0.9, soybean 0.85, wheat 1.05.
Fallow / off-season storage: 25 % of rain between crops is stored in the soil (K-State: fallow
  stores 20-30 % of precipitation), capped at 230 mm of stored water (Claude's assumption, close
  to the ~9 in. soil water K-State reports at wheat planting after sorghum).
Winter wheat dormancy (Nov 16 - Feb 28): that rain is also counted at 25 % (Claude's assumption).

Method (Claude's design; first version used one candidate list for all districts and a water-only
score, which ranked the same rotations first everywhere and gave only ~1.1x more sorghum after
wheat+fallow vs K-State's measured ~2x - so it was replaced by this hybrid):
  For each district, run every phase of each rotation through the real daily NASA POWER rain,
  2015-2026 (like field plots where every crop of the rotation is grown each year).
  For each crop grown: water = in-season rain + stored water from the gap since the previous
  harvest (25 %, capped). Relative yield index = 1 - Ky * (1 - min(water / need, 1)).
  West only: a summer crop that follows another summer crop gets its index halved (K-State
  Tribune: summer-crop yields about twice as great following wheat).
  Rotation score = average yield index x crops per year  (= water-adjusted crops per year).
  Dry-year score = same with the 25th-percentile yield index of each crop.
  Weights: the top 3 share 100 %, proportional to the score used for ranking.
  Recommend the top 3 by normal score, or by dry-year score where the district's drought
  alert is watch/warning (probability >= 30 %).
  Double-crop moisture gate (K-State MF2908: "Greater soil moisture will allow more double
  cropping of row crops following wheat"; under normal moisture corn/soybean or sorghum/soybean
  may be more profitable): the double-crop rotation is only allowed to rank above the 2-year
  rotations when the district's current NASA root-zone soil wetness is at or above its normal
  (percentile >= 50) AND the drought alert is normal; otherwise it is moved below them.
  NOT included: prices, costs, fertilizer, soils, irrigation, pests, residue effects. The score
  measures water-limited productivity, not profit.
Outputs: data/rotation_ranking.csv, reports/rotation_ranking.md
"""
import os, numpy as np, pandas as pd
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PSE, CAP, WATCH = 0.25, 230.0, 0.30
CROP = {  # name: (plant (m,d), harvest (m,d), harvest year offset, need mm, Ky)
    "wheat":   ((9, 15), (6, 20), 1, 550, 1.05),
    "corn":    ((4, 15), (9, 10), 0, 650, 1.25),
    "sorghum": ((5, 15), (9, 25), 0, 550, 0.90),
    "soybean": ((5, 15), (10, 1), 0, 575, 0.85),
    "dcsoy":   ((7, 1), (10, 15), 0, 450, 0.85),
}
ROT = {  # name: (length in years, [(crop, planting-year offset), ...])
    "W-F (wheat-fallow)":                    (2, [("wheat", 0)]),
    "W-S-F (wheat-sorghum-fallow)":          (3, [("wheat", 0), ("sorghum", 2)]),
    "W-C-F (wheat-corn-fallow)":             (3, [("wheat", 0), ("corn", 2)]),
    "W-C-S-F (wheat-corn-sorghum-fallow)":   (4, [("wheat", 0), ("corn", 2), ("sorghum", 3)]),
    "S-S (continuous sorghum)":              (1, [("sorghum", 0)]),
    "C-Sb (corn-soybean)":                   (2, [("corn", 0), ("soybean", 1)]),
    "S-Sb (sorghum-soybean)":                (2, [("sorghum", 0), ("soybean", 1)]),
    "C-W-dSb (corn/wheat/double-crop soy)":  (2, [("corn", 0), ("wheat", 0), ("dcsoy", 1)]),
}
REGION = {"ks_northwest": "west", "ks_west_central": "west", "ks_southwest": "west",
          "ks_north_central": "central", "ks_central": "central", "ks_south_central": "central",
          "ks_northeast": "east", "ks_east_central": "east", "ks_southeast": "east"}
CANDIDATES = {
    "west":    ["W-F (wheat-fallow)", "W-S-F (wheat-sorghum-fallow)", "W-C-F (wheat-corn-fallow)",
                "W-C-S-F (wheat-corn-sorghum-fallow)", "S-S (continuous sorghum)"],
    "central": ["C-Sb (corn-soybean)", "S-Sb (sorghum-soybean)", "C-W-dSb (corn/wheat/double-crop soy)",
                "W-S-F (wheat-sorghum-fallow)"],
    "east":    ["C-Sb (corn-soybean)", "S-Sb (sorghum-soybean)", "C-W-dSb (corn/wheat/double-crop soy)"],
}
SUMMER = {"corn", "sorghum", "soybean"}
w = pd.read_csv(os.path.join(ROOT, "data/power_daily_clean.csv"), parse_dates=["date"])
live = pd.read_csv(os.path.join(ROOT, "data/live_forecast.csv")).set_index("region")

def events(L, crops, phase, y0=2014, y1=2027):
    out = []
    for cyc in range(y0 - L, y1 + 1, L):
        for crop, off in crops:
            pm, hm, hoff = CROP[crop][0], CROP[crop][1], CROP[crop][2]
            py = cyc + phase + off
            out.append((crop, pd.Timestamp(py, *pm), pd.Timestamp(py + hoff, *hm)))
    return sorted(out, key=lambda e: e[1])

rows = []
for region, g in w.groupby("region"):
    rain = g.set_index("date").PRECTOTCORR
    first, last = rain.index.min(), rain.index.max()
    reg = REGION[region]
    for rname in CANDIDATES[reg]:
        L, crops = ROT[rname]
        idx = {c: [] for c, _ in crops}
        for phase in range(L):
            ev = events(L, crops, phase)
            for k in range(1, len(ev)):
                crop, plant, harv = ev[k]; prev_harv = ev[k - 1][2]; prev_crop = ev[k - 1][0]
                if prev_harv < first or harv > last or prev_harv >= plant:
                    continue                                   # need full weather record, no overlap
                stored = min(PSE * rain.loc[prev_harv + pd.Timedelta(days=1):plant - pd.Timedelta(days=1)].sum(), CAP)
                season = rain.loc[plant:harv]
                if crop == "wheat":                            # winter dormancy counted at PSE
                    dorm = season[((season.index.month == 11) & (season.index.day >= 16)) | season.index.month.isin([12, 1, 2])]
                    water = season.sum() - dorm.sum() + PSE * dorm.sum() + stored
                else:
                    water = season.sum() + stored
                need, ky = CROP[crop][3], CROP[crop][4]
                yi = max(0.0, 1 - ky * (1 - min(water / need, 1.0)))
                if reg == "west" and crop in SUMMER and prev_crop in SUMMER and (plant - prev_harv).days < 330:
                    yi *= 0.5      # K-State Tribune: summer crops ~2x better after wheat/fallow
                idx[crop].append(yi)
        n_crops = len(crops)
        mean_idx = np.mean([np.mean(v) for v in idx.values()])
        dry_idx = np.mean([np.percentile(v, 25) for v in idx.values()])
        p = float(live.loc[region, "p_logistic"])
        rows.append({"region": region, "k_state_region": reg, "rotation": rname, "crops_per_year": round(n_crops / L, 2),
                     "mean_crop_index": round(mean_idx, 2), "dry_crop_index": round(dry_idx, 2),
                     "score_normal": round(mean_idx * n_crops / L, 3), "score_dry_year": round(dry_idx * n_crops / L, 3),
                     "crop_events_simulated": sum(len(v) for v in idx.values()),
                     "drought_probability_now": round(p, 2),
                     "alert": "warning" if p >= 0.5 else ("watch" if p >= WATCH else "normal")})
r = pd.DataFrame(rows)
rz = live["GWETROOT_pct"] if "GWETROOT_pct" in live else pd.Series(dtype=float)
r["rootzone_pct_now"] = r.region.map(rz).round(0)
r["double_crop_ok"] = (r.alert == "normal") & (r.rootzone_pct_now >= 50)
DC = "C-W-dSb (corn/wheat/double-crop soy)"
gate = (r.rotation == DC) & ~r.double_crop_ok
for col in ("score_normal", "score_dry_year"):        # gated: ranks just below the best 2-year rotation
    best2 = r[r.rotation.isin(["C-Sb (corn-soybean)", "S-Sb (sorghum-soybean)"])].groupby("region")[col].max()
    r[col + "_for_rank"] = np.where(gate, np.minimum(r[col], r.region.map(best2) - 0.001), r[col])
r["rank_normal"] = r.groupby("region").score_normal_for_rank.rank(ascending=False, method="min").astype(int)
r["rank_dry_year"] = r.groupby("region").score_dry_year_for_rank.rank(ascending=False, method="min").astype(int)
r["note"] = np.where(gate, "double-crop moved down: soil not above normal or drought alert on (K-State MF2908)", "")
# Score actually used for ranking (normal or dry-year, after the double-crop gate)
r["score_used"] = np.where(r.alert == "normal", r.score_normal_for_rank, r.score_dry_year_for_rank).round(3)
r = r.drop(columns=["score_normal_for_rank", "score_dry_year_for_rank"])
r["recommended_rank"] = np.where(r.alert == "normal", r.rank_normal, r.rank_dry_year)
r["basis"] = np.where(r.alert == "normal", "normal-year water", "dry-year water (district on watch/warning)")
r = r.sort_values(["region", "recommended_rank"])
r["note"] = r["note"].fillna("")
# WEIGHTS: the top 3 rotations per district share 100 %, in proportion to their score_used
top3 = r.recommended_rank <= 3
r["weight_pct"] = np.nan
def whole_pct(scores):        # largest-remainder rounding so the 3 weights always total exactly 100
    raw = 100 * scores / scores.sum(); base = np.floor(raw); left = int(100 - base.sum())
    order = np.argsort(-(raw - base).values)
    base.iloc[order[:left]] += 1
    return base
r.loc[top3, "weight_pct"] = r.loc[top3].groupby("region", group_keys=False).score_used.apply(whole_pct)
r.to_csv(os.path.join(ROOT, "data/rotation_ranking.csv"), index=False)

# CURRENT-CROP FEATURE (added 2026-11-14 at the team's request): the farmer says what crop is in the
# field now; only rotations that INCLUDE that crop are suggested (double-crop soybean counts as soybean).
# Same order as the overall ranking (same basis and double-crop rule); up to 3 shown; weights share 100 %
# among the ones shown. If fewer than 3 K-State candidates in the region contain the crop, fewer are shown.
CURRENT_CROPS = ["corn", "sorghum", "soybean", "wheat"]
CROP_NAME = {"corn": "corn", "sorghum": "grain sorghum", "soybean": "soybeans", "wheat": "winter wheat"}
AREA = {"west": "western", "central": "central", "east": "eastern"}
def crops_in(rname):
    return {"soybean" if c == "dcsoy" else c for c, _ in ROT[rname][1]}
cc_rows = []
for region, g in r.groupby("region"):
    for cc in CURRENT_CROPS:
        sub = g[g.rotation.map(lambda n: cc in crops_in(n))].copy()
        # Re-apply the double-crop rule inside the filtered list: a moved-down (gated) rotation may not
        # come first while another option exists, so its score is capped just below the best other one.
        gated = sub.note.astype(bool)
        if gated.any() and (~gated).any():
            best_other = sub.loc[~gated, "score_used"].max()
            sub.loc[gated, "score_used"] = np.minimum(sub.loc[gated, "score_used"], best_other - 0.001).round(3)
        sub = sub.sort_values(["score_used", "recommended_rank"], ascending=[False, True]).head(3)
        n_cand = int(g.rotation.map(lambda n: cc in crops_in(n)).sum())
        if len(sub) == 0:
            cc_rows.append({"region": region, "current_crop": cc, "k_state_region": g.k_state_region.iloc[0],
                            "rank": None, "rotation": None, "weight_pct": None, "score_used": None,
                            "basis": g.basis.iloc[0], "note": "", "n_shown": 0,
                            "message": f"No K-State dryland rotation for {AREA[g.k_state_region.iloc[0]]} Kansas includes {CROP_NAME[cc]}."})
            continue
        sub["weight_pct"] = whole_pct(sub.score_used).values
        msg = ("" if len(sub) == 3 else
               f"Only {len(sub)} of the K-State rotations for {AREA[sub.k_state_region.iloc[0]]} Kansas include{'s' if len(sub) == 1 else ''} {CROP_NAME[cc]}.")
        for k, row in enumerate(sub.itertuples(), 1):
            cc_rows.append({"region": region, "current_crop": cc, "k_state_region": row.k_state_region,
                            "rank": k, "rotation": row.rotation, "weight_pct": row.weight_pct,
                            "score_used": row.score_used, "basis": row.basis, "note": row.note,
                            "n_shown": len(sub), "message": msg})
cc = pd.DataFrame(cc_rows)
cc.to_csv(os.path.join(ROOT, "data/rotation_by_current_crop.csv"), index=False)
_md = ["# Rotations that include the crop already in the field (decision support, not a guarantee)", "",
       "Only rotations containing the farmer's current crop are shown (double-crop soybean counts as soybean); "
       "same order and rules as the overall ranking; weights share 100% among those shown.", "",
       "| district | current crop | suggestions (weight) |", "|---|---|---|"]
for (reg, crop), gg in cc.groupby(["region", "current_crop"], sort=True):
    if gg.n_shown.iloc[0] == 0:
        _md.append(f"| {reg.replace('ks_', '')} | {crop} | none - {gg.message.iloc[0]} |")
    else:
        _md.append(f"| {reg.replace('ks_', '')} | {crop} | " + ", ".join(
            f"{x.rotation.split()[0]} {int(x.weight_pct)}%{'*' if x.note else ''}" for x in gg.itertuples()) + " |")
_md += ["", "* double-crop moved down (soil not above normal or drought alert on; K-State MF2908)."]
open(os.path.join(ROOT, "reports/rotation_by_current_crop.md"), "w").write("\n".join(_md) + "\n")

lines = ["# Top 3 crop rotations by Kansas district (decision support, not a guarantee)", "",
         "Score = water-adjusted crops per year: average FAO relative yield index (Ky method, using "
         "in-season rain + 25% of rain stored between crops) x crops per year, simulated through real "
         "2015-2026 NASA POWER rain. Higher = more water-limited production per year. Not a profit ranking.", "",
         "| district | alert now | root-zone soil now (pct) | basis | 1st (weight) | 2nd (weight) | 3rd (weight) |", "|---|---|---|---|---|---|---|"]
for region, g in r.groupby("region"):
    col = "score_normal" if g.alert.iloc[0] == "normal" else "score_dry_year"
    top = g.sort_values("recommended_rank").head(3)
    cells = [f"{n.split(' (')[0]} {w:.0f}%{'*' if nt else ''}" for n, w, nt in zip(top.rotation, top.weight_pct, top.note)]
    rzv = g.rootzone_pct_now.iloc[0]
    lines.append(f"| {region.replace('ks_', '')} | {g.alert.iloc[0]} ({g.drought_probability_now.iloc[0]:.0%}) | "
                 f"{'flagged' if pd.isna(rzv) else int(rzv)} | "
                 f"{'dry year' if col == 'score_dry_year' else 'normal year'} | " + " | ".join(cells) + " |")
lines += ["", "Weights: the 3 suggested rotations share 100%, in proportion to their water-adjusted score "
          "(normal-year score, or dry-year score when the district is on watch/warning).",
          "* Double-crop rotation moved below the 2-year rotations because soil is not above normal or a "
          "drought alert is on (K-State MF2908 moisture guidance); its weight uses the reduced score.",
          "", "Candidates per K-State region: " + " | ".join(f"{k}: " + ", ".join(n.split(' (')[0] for n in v) for k, v in CANDIDATES.items()), "",
          "Caveats: water only (no prices, costs, soils, irrigation, pests or residue benefits); FAO generic "
          "crop values; storage efficiency and soil-water cap are simplified; ~55 km rain data. K-State's "
          "Tribune study found wheat-sorghum-fallow the most profitable dryland system in far-western Kansas - "
          "profit can rank rotations differently from this water score. MF2908 names double-cropping for central "
          "and southeast Kansas but does not specifically recommend it for the rest of eastern Kansas; it is "
          "included there as a candidate (still subject to the moisture gate). Check with K-State Research and Extension.",
          "", "Sensitivity (checked 2026-11-14): the top rotation in every district and the set of 3 suggestions did "
          "not change with fallow storage 20-30% or soil-water cap 180-280 mm, or with the soil-moisture threshold at "
          "40 or 60 instead of 50. The western result depends on K-State's measured rotation effect: unchanged if the "
          "effect is 1.7x instead of 2x, but at 1.4x three western districts change, and with no effect continuous "
          "sorghum would wrongly rank first."]
open(os.path.join(ROOT, "reports/rotation_ranking.md"), "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
print("\nfull scores, normal year:\n", r.pivot(index="region", columns="rotation", values="score_normal").round(2).fillna("").to_string())
print("\nsimulated crop events per rotation (min across districts):", r.groupby("rotation").crop_events_simulated.min().to_dict())
