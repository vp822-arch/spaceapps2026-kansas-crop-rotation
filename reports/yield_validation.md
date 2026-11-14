# Does the model's weather score track REAL Kansas yields? (USDA NASS, 2015-2025)

Each point = one crop, one district, one year. Yield = average of the district's counties, each as % above/below that county's own 2015-2025 average. Model = the season score used by the rotation advice (water factor with NASA POWER evapotranspiration-scaled need x heat factor x freeze factor), also taken relative to its district's own average so both sides are compared like for like.

| crop | district-years | r, within-district (headline) | p | r, out-of-sample (calibration test) | r, water-only score (before) | r without 2022-23 drought years | r range leaving out any one year |
|---|---|---|---|---|---|---|---|
| corn | 89 | 0.57 | < 0.001 | 0.53 | 0.46 | 0.41 | 0.47 to 0.63 |
| sorghum | 84 | 0.69 | < 0.001 | 0.68 | 0.56 | 0.51 | 0.62 to 0.73 |
| soybeans | 78 | 0.72 | < 0.001 | 0.72 | 0.65 | 0.67 | 0.67 to 0.75 |
| wheat | 81 | 0.51 | < 0.001 | 0.51 | 0.47 | 0.43 | 0.43 to 0.55 |

How to read it: r = 0 means no link, 1 = perfect. p = chance of a link this strong if the model were unrelated to yields (permutation test, years shuffled within each district, 5,000 times). The heat coefficients were fitted on these same years, so the headline r is slightly optimistic; the out-of-sample column (each year scored by coefficients fitted without it) is the fairer measure.

Honest findings:
- All four crops show a positive, statistically significant link between the model's weather score and real yields (within-district r 0.51-0.72).
- Adding NASA POWER evapotranspiration (water demand) improved every crop; heat stress at flowering improved corn and sorghum; freeze risk did not improve any crop in 2015-2025 and is set to zero (reports/factor_calibration.md).
- Much of the link comes from the 2022-23 drought: without those years it is weaker. The model is best at flagging seriously stressed seasons - the years that matter most for choosing a rotation.
- 'ALL PRODUCTION PRACTICES' yields include irrigated fields (especially western corn), which weakens the link to weather. Fewer counties reported in later years; no wheat county data for 2024. The model uses one NASA POWER point per district (~55 km grid).
- This tests the weather scores that drive the rotation ranking; it cannot test economics (prices, costs), which the model does not include.
