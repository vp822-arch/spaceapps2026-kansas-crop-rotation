"""
Step 8 - Download US Drought Monitor (USDM) history for Kansas: the "answer key"
of when drought actually happened. No login needed.
Written by Claude (Anthropic AI) for Varun Pisharody's Space Apps 2026 team.
Cite in References: U.S. Drought Monitor, National Drought Mitigation Center at the
University of Nebraska-Lincoln, USDA and NOAA (droughtmonitor.unl.edu).

USDM publishes a weekly map with categories D0 (abnormally dry) to D4 (exceptional
drought). These services give, for each week, the % of an area in each category.

Downloads (one request per year, 2015-2026, to stay within any range limits):
  - every Kansas county,  percent of area, statisticsType 1 and 2
  - Kansas statewide (FIPS 20), percent of area, statisticsType 1
  - Kansas statewide Drought Severity and Coverage Index (DSCI, 0-500)
Saved as CSV in data/raw/usdm/. Claude processes them afterwards.

Run in WSL:  cd /mnt/c/SpaceApps2026 && python3 scripts/08_pull_usdm.py
"""
import os, time, urllib.request, urllib.error
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "raw", "usdm")
os.makedirs(OUT, exist_ok=True)
BASE = "https://usdmdataservices.unl.edu/api"

JOBS = [  # (file prefix, area, statistic, aoi, statisticsType)
    ("county_pct_t1", "CountyStatistics", "GetDroughtSeverityStatisticsByAreaPercent", "KS", 1),
    ("county_pct_t2", "CountyStatistics", "GetDroughtSeverityStatisticsByAreaPercent", "KS", 2),
    ("state_pct_t1",  "StateStatistics",  "GetDroughtSeverityStatisticsByAreaPercent", "20", 1),
    ("state_dsci",    "StateStatistics",  "GetDSCI",                                   "20", 1),
]

for prefix, area, stat, aoi, stype in JOBS:
    for year in range(2015, date.today().year + 1):
        dest = os.path.join(OUT, f"{prefix}_{year}.csv")
        if os.path.exists(dest) and os.path.getsize(dest) > 100:
            # Weekly refresh (REFRESH=1): get the current year again as a new, dated file.
            # Step 09 drops duplicate weeks, so old and new files can sit side by side.
            if os.environ.get("REFRESH") == "1" and year == date.today().year:
                dest = os.path.join(OUT, f"{prefix}_{year}_upd{date.today():%Y%m%d}.csv")
                if os.path.exists(dest) and os.path.getsize(dest) > 100:
                    continue
            else:
                continue
        end = f"12/31/{year}" if year < date.today().year else date.today().strftime("%-m/%-d/%Y")
        url = (f"{BASE}/{area}/{stat}?aoi={aoi}&startdate=1/1/{year}&enddate={end}"
               f"&statisticsType={stype}")
        req = urllib.request.Request(url, headers={"Accept": "text/csv",
                                                   "User-Agent": "SpaceApps2026-student-project"})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    body = r.read()
                break
            except Exception as e:
                print(f"  retry {attempt+1} {prefix} {year}: {e}"); time.sleep(5)
        else:
            print(f"FAILED {prefix} {year}"); continue
        open(dest, "wb").write(body)
        n_lines = body.count(b"\n")
        print(f"ok {prefix} {year}: {n_lines} lines")
        time.sleep(0.5)
print("Done. Files are in", OUT)
