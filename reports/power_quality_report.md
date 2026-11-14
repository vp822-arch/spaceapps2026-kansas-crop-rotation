# NASA POWER data-quality report

Input rows: 38,169  |  districts: 9  |  dates 2015-04-01 to 2026-11-09

- `-999` codes turned into blanks: 9
- Duplicate rows removed: 0
- Missing calendar days added back as blank rows: 0
- Newest not-yet-filled days trimmed off: 0 (clean record ends 2026-11-09)
- Impossible values blanked: none
- Short gaps (<= 3 days) filled by interpolation: ALLSKY_SFC_SW_DWN 9
- Physical-consistency flags (gwetroot_flag = 1 means root-zone value is suspect): ks_south_central: root-zone wetness fell -0.07 in one day on 2026-10-01 during 16.0 mm of rain -> 40 days from then on flagged suspect

## Remaining blanks after cleaning (per variable)

| variable | blanks | % |
|---|---|---|
| ALLSKY_SFC_SW_DWN | 0 | 0.00 |
| GWETROOT | 0 | 0.00 |
| GWETTOP | 0 | 0.00 |
| PRECTOTCORR | 0 | 0.00 |
| RH2M | 0 | 0.00 |
| T2M | 0 | 0.00 |
| T2M_MAX | 0 | 0.00 |
| T2M_MIN | 0 | 0.00 |
| WS2M | 0 | 0.00 |

## Per-district summary

| district | first day | last day | days | mean rain mm/day | mean T2M C | mean root-zone wetness |
|---|---|---|---|---|---|---|
| ks_central | 2015-04-01 | 2026-11-09 | 4241 | 2.18 | 14.2 | 0.44 |
| ks_east_central | 2015-04-01 | 2026-11-09 | 4241 | 2.86 | 14.0 | 0.62 |
| ks_north_central | 2015-04-01 | 2026-11-09 | 4241 | 2.12 | 13.5 | 0.43 |
| ks_northeast | 2015-04-01 | 2026-11-09 | 4241 | 2.67 | 13.1 | 0.61 |
| ks_northwest | 2015-04-01 | 2026-11-09 | 4241 | 1.52 | 13.2 | 0.39 |
| ks_south_central | 2015-04-01 | 2026-11-09 | 4241 | 2.45 | 14.9 | 0.47 |
| ks_southeast | 2015-04-01 | 2026-11-09 | 4241 | 3.04 | 15.0 | 0.63 |
| ks_southwest | 2015-04-01 | 2026-11-09 | 4241 | 1.61 | 14.9 | 0.36 |
| ks_west_central | 2015-04-01 | 2026-11-09 | 4241 | 1.61 | 14.1 | 0.39 |
