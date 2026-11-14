# How much each weather factor counts (calibrated on real Kansas yields)

Test = leave-one-year-out: coefficients fitted without a year, then used to score that year. r = within-district Spearman correlation of those out-of-sample scores with real USDA yields (same measure as the yield validation). A factor is kept only if it raises r by at least 0.01.

| crop | district-years | water only | + ET0-scaled need | + heat | + freeze | kept | b_heat (per day) | b_freeze (per day) |
|---|---|---|---|---|---|---|---|---|
| corn | 89 | 0.46 | 0.51 | 0.53 | 0.53 | et0_scaling, heat | 0.0250 | 0.0000 |
| sorghum | 84 | 0.56 | 0.59 | 0.68 | 0.68 | et0_scaling, heat | 0.0175 | 0.0000 |
| soybean | 78 | 0.65 | 0.72 | 0.28 | 0.72 | et0_scaling | 0.0000 | 0.0000 |
| wheat | 81 | 0.47 | 0.51 | 0.43 | 0.48 | et0_scaling | 0.0000 | 0.0000 |

Each '+' column adds that factor to the best model so far (whether or not the previous one was kept is shown in 'kept'). Double-crop soybean uses the soybean coefficients. Heat = days at or above the crop's threshold in its flowering window; freeze = wheat: days at or below 28 F while heading; summer crops: days of season lost to a 28 F fall freeze. Source thresholds: see factors.py and REFERENCES.md.
