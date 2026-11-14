"""
Step 1 - Pull each location's history from NASA POWER (daily, no login needed).

Written by Claude (Anthropic AI) for Varun Pisharody's NASA Space Apps 2026 team.
List this script and NASA POWER in the submission's References.
NASA POWER's official reference (power.larc.nasa.gov/docs/referencing/): "The data was
obtained from National Aeronautics and Space Administration (NASA) Langley Research
Center's Prediction Of Worldwide Energy Resources (POWER) project funded through the NASA
Earth Science Division." Plus a data reference with API version and access date.

What "pull a location's history" means here:
  for each point (lat, lon), ask POWER for every day from 2015-04-01 (SMAP era)
  to a few days ago, for ~10 weather variables -> one row per day per point.

Run from the C:\\SpaceApps2026 folder:
  Windows:  python scripts\\01_pull_power.py
  WSL:      cd /mnt/c/SpaceApps2026 && python3 scripts/01_pull_power.py
Uses only the Python standard library (no pip installs).
"""
import csv, json, os, sys, time, urllib.request, urllib.error
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, "data", "raw", "power")
# Weekly refresh (REFRESH=1, set by run_weekly.py): download the full record again up to
# today-5 into a separate folder, one file per run date. The original downloads are never touched.
REFRESH = os.environ.get("REFRESH") == "1"
if REFRESH:
    RAW_DIR = os.path.join(ROOT, "data", "raw", "power_latest")
OUT_CSV = os.path.join(ROOT, "data", "power_daily_raw.csv")
os.makedirs(RAW_DIR, exist_ok=True)

# Kansas first (team decision 13:51, Nov 14; replaces Illinois).
# One point per USDA NASS Kansas crop reporting district, so results can be
# compared with NASS district yields later. Coordinates are approximate
# district centres chosen by Claude (not official centroids) - edit freely.
REGIONS = {
    "ks_northwest":     (39.5, -100.9),
    "ks_west_central":  (38.6, -100.9),
    "ks_southwest":     (37.6, -100.9),
    "ks_north_central": (39.5,  -98.3),
    "ks_central":       (38.6,  -98.3),
    "ks_south_central": (37.6,  -98.3),
    "ks_northeast":     (39.5,  -95.6),
    "ks_east_central":  (38.6,  -95.6),
    "ks_southeast":     (37.5,  -95.4),
}
OFFSETS = [(0, 0)]   # one point per district; add neighbours later if needed

CORE = ["PRECTOTCORR", "T2M", "T2M_MAX", "T2M_MIN", "RH2M",
        "ALLSKY_SFC_SW_DWN", "WS2M"]
EXTRA = ["GWETTOP", "GWETROOT"]   # model soil wetness; dropped if POWER rejects them

START = "20150401"
END = (date.today() - timedelta(days=5)).strftime("%Y%m%d")
BASE = "https://power.larc.nasa.gov/api/temporal/daily/point"

def fetch(lat, lon, params):
    url = (f"{BASE}?parameters={','.join(params)}&community=AG"
           f"&latitude={lat}&longitude={lon}&start={START}&end={END}&format=JSON")
    with urllib.request.urlopen(url, timeout=120) as r:
        return json.load(r)

rows, used_params = [], None
for region, (clat, clon) in REGIONS.items():
    for i, (dlat, dlon) in enumerate(OFFSETS):
        lat, lon = round(clat + dlat, 3), round(clon + dlon, 3)
        cache = os.path.join(RAW_DIR, f"{region}_{i}_{END}.json" if REFRESH else f"{region}_{i}.json")
        if os.path.exists(cache):                      # don't re-download
            data = json.load(open(cache))
        else:
            params = CORE + EXTRA
            for attempt in range(3):
                try:
                    data = fetch(lat, lon, params); break
                except urllib.error.HTTPError as e:
                    if e.code in (400, 422) and params != CORE:
                        print(f"  POWER rejected {EXTRA}; retrying with core only")
                        params = CORE; continue
                    print(f"  HTTP {e.code} for {region}_{i}, retry {attempt+1}")
                    time.sleep(5)
                except Exception as e:
                    print(f"  error {e} for {region}_{i}, retry {attempt+1}")
                    time.sleep(5)
            else:
                print(f"FAILED {region}_{i}; skipping"); continue
            json.dump(data, open(cache, "w"))
            time.sleep(1)                              # be polite to the API
        p = data["properties"]["parameter"]
        names = sorted(p)
        used_params = used_params or names
        for d in sorted(p[names[0]]):
            rows.append({"region": region, "point": i, "lat": lat, "lon": lon,
                         "date": f"{d[:4]}-{d[4:6]}-{d[6:]}",
                         **{n: p[n].get(d) for n in names}})
        print(f"ok {region}_{i}  ({lat}, {lon})  {len(p[names[0]])} days")

with open(OUT_CSV, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)
print(f"\nWrote {len(rows)} rows to {OUT_CSV}")
print("Variables:", used_params)
print("Note: -999 means 'no data' in POWER; step 2 (cleaning) handles it.")
