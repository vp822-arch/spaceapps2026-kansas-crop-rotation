# Kansas Crop Rotation Advice: code and data (NASA Space Apps 2026)

Prepared 2026-11-14 for the team. Data analysis by Varun Pisharody; all scripts were
written by Claude (Anthropic AI), and each file is labelled. List both in the submission's References.

**No passwords, tokens or keys are in this package.** Get your own where noted below.

## Team access

- **Algorithm and data:** this repo. Keep it **private** and add teammates as collaborators.
- **Live data:** the GitHub Action `Weekly refresh` (`.github/workflows/weekly_refresh.yml`) runs every
  Monday on GitHub's servers. It downloads new NASA POWER and Drought Monitor data, re-ranks the
  rotations, runs the safety checks, publishes the app JSON to Cloudflare R2, and commits the updated
  `data/` and `reports/` here. To refresh now: Actions tab, then Weekly refresh, then Run workflow.
- **App data (no login needed):** the app fetches one public file,
  `https://pub-fe3948f31a9c462890b089ed5356c336.r2.dev/app_rotation_advice.json`, from Cloudflare R2. The upload keys
  live only in the repo secrets `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` and
  `R2_BUCKET`, or in a local `.r2.env` file that is never committed. (Tiger Cloud was used until
  2026-11-14 and is no longer updated.)

## The current-crop feature

The farmer can say which crop is in the field now: corn, sorghum, soybean or wheat. The app then shows only
rotations that **include** that crop (double-crop soybean counts as soybean), in the same order and with the same
rules as the overall ranking, with weights that total 100% among those shown. Some areas have fewer than 3
such rotations (for example, no K-State dryland rotation for western Kansas includes soybeans); the JSON
then gives fewer rotations plus a `message` explaining why. Data: `data/rotation_by_current_crop.csv`;
report: `reports/rotation_by_current_crop.md`; JSON: each county's `by_current_crop`.

## What's inside

| folder | what it holds |
|---|---|
| `scripts/` | the full pipeline, steps 01 to 19 (07 and 18 are the old Tiger Cloud loader and its login test, kept for reference), plus `run_weekly.sh` / `run_weekly.py` (one command for everything) |
| `data/` | every input and output; the app needs only `app_rotation_advice.json` |
| `data/raw/` | original downloads: NASA POWER (JSON), U.S. Drought Monitor (CSV), USDA NASS yields (CSV), SMAP task request (fresh refresh downloads go to `data/raw/power_latest/`, which is not committed) |
| `reports/` | readable results: rotation ranking, yield validation (+ chart), model report, data quality, references, run log |

## The algorithm in one paragraph

NASA POWER daily rain, temperature and soil wetness for 9 Kansas districts (2015 to now) are cleaned
(02) and compared with each district's normal (03). A drought model (09 to 11) predicts drought 4 weeks
ahead. In the app it is a hidden input that switches a district to "dry-year" rankings. For each
district, K-State's candidate rotations (west / central / east) are simulated through the real rain
record using FAO crop water needs and yield-response factors, with 25% of off-season rain stored
(14). Each simulated season is scored water x heat x freeze from NASA POWER weather: the water need is scaled by
that season's evapotranspiration (FAO-56), and hot days in each crop's flowering window cut the score; how much each
factor counts was fitted to real USDA yields and kept only if it predicted held-out years better (21,
`reports/factor_calibration.md`). Score = weather-adjusted crops per year. The top 3 get weights that total 100%. A double-crop
rotation is moved down when soil is dry or a drought alert is on. The water scores were checked against real
USDA county yields 2015-2025 (16, `reports/yield_validation.md`). 14 also makes the current-crop lists, 17 exports the app JSON,
and 19 publishes it to Cloudflare R2.
Full details and caveats are in `reports/rotation_ranking.md`.

## Quick start

Needs: Linux, macOS or WSL, plus [uv](https://docs.astral.sh/uv/). `run_weekly.sh` installs Python 3.12 and
the exact library versions (pandas 2.3.3, NumPy 2.2.6, scikit-learn 1.7.2, SciPy 1.15.3,
Matplotlib 3.10.9, zipcodes 3.0.1, psycopg 3).

1. Re-run all the analysis on the included data, with no internet and no database:
   `bash scripts/run_weekly.sh --skip-download --no-load`
2. Also download fresh NASA POWER and Drought Monitor data (public, no login), without touching the database:
   `bash scripts/run_weekly.sh --no-load`
3. Full refresh, including publishing to Cloudflare R2: needs the four R2 settings as environment
   variables or in `.r2.env` (never commit them). Then run `bash scripts/run_weekly.sh`.

The run stops at the first failed step, and it skips the database upload if any safety check fails
(data age, 9 districts, 3 rotations each, weights total 100, current-crop table complete). Every run is logged in `reports/run_log.md`.

## Steps that need your own credentials (not needed for the weekly refresh)

- `06_pull_smap_appeears.py` (SMAP): an Earthdata Login account. It asks for your username and password
  at run time and never saves them. It resumes the task id in `data/raw/smap/`, which belongs to Varun's account;
  delete that id file to submit your own task.
- `15_pull_nass_yields.py` (validation only): a free USDA NASS Quick Stats API key, saved as `.nass_key`.

## For the app

Fetch `app_rotation_advice.json` from the public R2 link (or read `data/app_rotation_advice.json` in this repo). Field list, display rules and code examples are in the
"App Developer Handoff" guide Varun is sharing.

## Data credits (required)

NASA POWER, the U.S. Drought Monitor (official credit line in `reports/REFERENCES.md`) and USDA NASS Quick
Stats. FAO and K-State sources are listed in `reports/REFERENCES.md`.
