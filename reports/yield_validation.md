# Does the model's water score track REAL Kansas yields? (USDA NASS, 2015-2025)

Each point = one crop, one district, one year. Yield = average of the district's counties, each as % above/below that county's own 2015-2025 average. Model = water-based relative yield index from NASA POWER rain (same method as the rotation advice), also taken relative to its district's own average so both sides are compared like for like.

| crop | district-years | r, within-district (headline) | p | r, raw score | r without 2022-23 drought years | r range leaving out any one year |
|---|---|---|---|---|---|---|
| corn | 89 | 0.46 | < 0.001 | 0.36 | 0.33 | 0.39 to 0.53 |
| sorghum | 84 | 0.56 | < 0.001 | 0.34 | 0.50 | 0.49 to 0.62 |
| soybeans | 78 | 0.65 | < 0.001 | 0.62 | 0.57 | 0.60 to 0.68 |
| wheat | 81 | 0.47 | < 0.001 | 0.29 | 0.39 | 0.42 to 0.55 |

How to read it: r = 0 means no link, 1 = perfect. p = chance of a link this strong if the model were unrelated to yields (permutation test, years shuffled within each district, 5,000 times).

Honest findings:
- All four crops show a positive, statistically significant link between the model's water score and real yields (within-district r 0.46-0.65).
- Much of the link for corn, sorghum and wheat comes from the 2022-23 drought: without those years it is weaker. The model is best at flagging seriously water-short seasons - the years that matter most for choosing a rotation - and less able to explain small year-to-year differences. Soybeans keep a strong link even without the drought years.
- 'ALL PRODUCTION PRACTICES' yields include irrigated fields (especially western corn), which weakens the link to rainfall. Fewer counties reported in later years; no wheat county data for 2024. The model uses one NASA POWER point per district (~55 km grid).
- This tests the water scores that drive the rotation ranking; it cannot test the ranking's economics (prices, costs), which the model does not include.
