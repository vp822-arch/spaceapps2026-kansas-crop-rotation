"""
Step 15 - Download real Kansas crop yields (USDA NASS Quick Stats) to TEST the rotation advice.
Written by Claude (Anthropic AI) for Varun Pisharody's Space Apps 2026 team.
Cite in References: USDA National Agricultural Statistics Service, Quick Stats API
(https://quickstats.nass.usda.gov/api).

What it downloads: yearly yield (bushels/acre) for corn (grain), sorghum (grain), soybeans and
winter wheat, for each Kansas agricultural (crop reporting) district, 2015 onward, all production
practices including NON-IRRIGATED where published (rain-fed yields are the fair test for a
rainfall-based model).

SETUP (Varun, once): request a free key at https://quickstats.nass.usda.gov/api , then save it as
the only line of C:\\SpaceApps2026\\.nass_key (Notepad, Save as type "All files"). The key is read
here and never printed.
Run in WSL:  cd /mnt/c/SpaceApps2026 && python3 scripts/15_pull_nass_yields.py
Standard library only.
"""
import os, sys, time, urllib.parse, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "raw", "nass"); os.makedirs(OUT, exist_ok=True)
kp = os.path.join(ROOT, ".nass_key")
if not os.path.exists(kp):
    sys.exit("No key file: save your NASS Quick Stats key as C:\\SpaceApps2026\\.nass_key")
KEY = open(kp, encoding="utf-8-sig").read().strip()
BASE = "https://quickstats.nass.usda.gov/api/api_GET/"
# District-level yields stop after 2019 (seen in the first download), so also fetch COUNTY level,
# which Claude aggregates to our districts with data/county_district_map.csv.
for level, tag in [("AGRICULTURAL DISTRICT", "district"), ("COUNTY", "county")]:
    for commodity in ["CORN", "SORGHUM", "SOYBEANS", "WHEAT"]:
        dest = os.path.join(OUT, f"ks_{tag}_yield_{commodity.lower()}.csv")
        if os.path.exists(dest) and os.path.getsize(dest) > 200:
            print("already have", os.path.basename(dest)); continue
        q = {"key": KEY, "source_desc": "SURVEY", "sector_desc": "CROPS", "commodity_desc": commodity,
             "statisticcat_desc": "YIELD", "agg_level_desc": level,
             "state_alpha": "KS", "year__GE": "2015", "format": "CSV"}
        url = BASE + "?" + urllib.parse.urlencode(q)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "SpaceApps2026"}), timeout=180) as r:
                body = r.read()
        except urllib.error.HTTPError as e:
            msg = e.read()[:300].decode(errors="replace")
            print(f"{tag} {commodity}: HTTP {e.code} - {msg}"); continue   # message never contains the key
        open(dest, "wb").write(body)
        n = body.count(b"\n")
        print(f"ok {tag} {commodity}: {n} lines -> {os.path.basename(dest)}")
        time.sleep(1)
print("Done. Files are in", OUT)
