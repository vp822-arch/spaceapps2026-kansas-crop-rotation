# Drought-warning model: backtest report

Target: district in drought (>= 50% area in USDM D1+) **29 days after the last day of input data** (about 4 weeks; target map = 5 weeks after the input week's Tuesday).
Train: 2015-06-23 to 2022-12-27 (3537 district-weeks).
Test: 2023-01-03 to 2026-09-29 (1763 district-weeks, never seen in training).

## All test weeks

| method | hit rate | false alarm ratio | Brier (lower better) | AUC | droughts |
|---|---|---|---|---|---|
| persistence | 0.79 | 0.25 | 0.182 | 0.81 | 681 / 1763 |
| climatology | 0.03 | 0.78 | 0.279 | 0.54 | 681 / 1763 |
| logistic | 0.75 | 0.20 | 0.127 | 0.89 | 681 / 1763 |
| gradient_boosting | 0.69 | 0.23 | 0.145 | 0.87 | 681 / 1763 |

## Onset only (not in drought now)

| method | hit rate | false alarm ratio | Brier (lower better) | AUC | droughts |
|---|---|---|---|---|---|
| persistence | 0.00 | nan | 0.138 | 0.50 | 145 / 1051 |
| climatology | 0.03 | 0.94 | 0.151 | 0.59 | 145 / 1051 |
| logistic | 0.17 | 0.47 | 0.106 | 0.77 | 145 / 1051 |
| gradient_boosting | 0.13 | 0.66 | 0.116 | 0.76 | 145 / 1051 |

## What drives the logistic model (standardized coefficients; negative = wetter lowers risk)

- usdm_now: +1.78
- GWETTOP_pct: -1.09
- season_cos: +0.57
- rain_30d_pct: -0.49
- GWETROOT_pct: +0.39
- season_sin: -0.32
- rain_60d_pct: -0.20
- drying_4w: +0.08
- rain_90d_pct: -0.06
- T2M_MAX_z: +0.03

Notes: hit rate and false alarm ratio use a 50 % probability cut-off. Persistence cannot warn of onsets by definition (it scores 0 there). POWER soil wetness is MERRA-2 model output at ~55 km; SMAP will be added when the AppEEARS download finishes.
Backup model without root-zone wetness (used when it is flagged suspect): test Brier 0.127, AUC 0.89

## Ablation: what happens without the NASA data (logistic model, test years)

| inputs | Brier all | AUC all | Brier onset | AUC onset |
|---|---|---|---|---|
| all inputs | 0.127 | 0.89 | 0.106 | 0.77 |
| without NASA data (USDM now + season only) | 0.142 | 0.85 | 0.127 | 0.58 |
| NASA data only (no USDM now) | 0.168 | 0.82 | 0.103 | 0.83 |
| without soil wetness (rain/temp kept) | 0.130 | 0.89 | 0.108 | 0.76 |

## Onset warnings at different cut-offs (logistic, all inputs, test years)

| warn if probability >= | hit rate | false alarm ratio | warnings issued |
|---|---|---|---|
| 0.50 | 0.17 | 0.47 | 45 |
| 0.40 | 0.26 | 0.56 | 87 |
| 0.30 | 0.34 | 0.63 | 133 |
| 0.20 | 0.48 | 0.67 | 208 |
| 0.15 | 0.55 | 0.71 | 274 |

## Known limitations (found while checking the results)

- Slow to call the END of a drought: it leans on current USDM coverage, e.g. SE Kansas Sept-Oct 2026 stayed at 89-94% predicted while the drought ended in October.
- Onset warnings are a trade-off: at a 20-30% warning level it catches about 34-48% of new droughts about 4 weeks ahead, but most warnings are false alarms (63-67%).
- Lead times are short: in the 2024 central-Kansas example the warning was issued 15 days before the April onset and only 1 day before the July onset (effectively no warning).
- POWER soil wetness (MERRA-2 model, ~55 km) adds little beyond rainfall; SMAP satellite soil moisture is pending and is the main hope for improvement.
- 'Districts' = counties nearest each of 9 points (county centres approximated from ZIP codes), not official NASS district boundaries.
- One root-zone data artifact (south central, from 2026-10-01) is flagged. Possible cause (unconfirmed): POWER's recent data blends sources (its files list MERRA-2 and GEOS-IT), so a change of source stream may produce a step; a backup model without root-zone wetness is used there (its test scores are in the line above this table).
- Timing fixed after a double-check: forecasts are now scored 29 days after the last input day (earlier version was effectively 22 days, which overstated skill).
