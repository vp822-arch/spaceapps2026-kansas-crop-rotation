# Top 3 crop rotations by Kansas district (decision support, not a guarantee)

Score = weather-adjusted crops per year: average season score x crops per year, simulated through real 2015-2026 NASA POWER weather. Season score = water factor (FAO Ky method; water = in-season rain + 25% of rain stored between crops; need scaled by that season's NASA POWER reference evapotranspiration) x heat factor (hot days in the flowering window) x freeze factor; how much each counts was fitted to USDA yields (reports/factor_calibration.md). Not a profit ranking.

| district | alert now | root-zone soil now (pct) | basis | 1st (weight) | 2nd (weight) | 3rd (weight) |
|---|---|---|---|---|---|---|
| central | normal (6%) | 88 | normal year | C-W-dSb 39% | S-Sb 33% | C-Sb 28% |
| east_central | normal (7%) | 62 | normal year | C-W-dSb 41% | S-Sb 30% | C-Sb 29% |
| north_central | normal (2%) | 100 | normal year | C-W-dSb 39% | S-Sb 33% | C-Sb 28% |
| northeast | normal (3%) | 80 | normal year | C-W-dSb 40% | S-Sb 31% | C-Sb 29% |
| northwest | normal (4%) | 100 | normal year | W-S-F 38% | W-C-F 31% | W-F 31% |
| south_central | warning (61%) | flagged | dry year | S-Sb 35% | C-W-dSb 35%* | C-Sb 30% |
| southeast | watch (30%) | 51 | dry year | S-Sb 34% | C-W-dSb 34%* | C-Sb 32% |
| southwest | normal (7%) | 89 | normal year | W-S-F 38% | W-F 31% | W-C-F 31% |
| west_central | normal (3%) | 99 | normal year | W-S-F 38% | W-F 31% | W-C-F 31% |

Weights: the 3 suggested rotations share 100%, in proportion to their water-adjusted score (normal-year score, or dry-year score when the district is on watch/warning).
* Double-crop rotation moved below the 2-year rotations because soil is not above normal or a drought alert is on (K-State MF2908 moisture guidance); its weight uses the reduced score.

Candidates per K-State region: west: W-F, W-S-F, W-C-F, W-C-S-F, S-S | central: C-Sb, S-Sb, C-W-dSb, W-S-F | east: C-Sb, S-Sb, C-W-dSb

Caveats: weather only (rain, water demand, heat; no prices, costs, soils, irrigation, pests or residue benefits); FAO generic crop values; storage efficiency and soil-water cap are simplified; ~55 km rain data. K-State's Tribune study found wheat-sorghum-fallow the most profitable dryland system in far-western Kansas - profit can rank rotations differently from this water score. MF2908 names double-cropping for central and southeast Kansas but does not specifically recommend it for the rest of eastern Kansas; it is included there as a candidate (still subject to the moisture gate). Check with K-State Research and Extension.

Sensitivity (checked 2026-11-14): the top rotation in every district and the set of 3 suggestions did not change with fallow storage 20-30% or soil-water cap 180-280 mm, or with the soil-moisture threshold at 40 or 60 instead of 50. The western result depends on K-State's measured rotation effect: unchanged if the effect is 1.7x instead of 2x, but at 1.4x three western districts change, and with no effect continuous sorghum would wrongly rank first.
