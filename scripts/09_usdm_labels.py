"""
Step 9 - Turn US Drought Monitor county data into weekly drought labels per district.
Written by Claude (Anthropic AI) for Varun Pisharody's Space Apps 2026 team.

Input : data/raw/usdm/county_pct_t1_*.csv  (statisticsType 1 = cumulative:
        "D1" = % of county area in D1 or worse)
Output: data/county_district_map.csv  (each Kansas county -> nearest district point)
        data/usdm_district_weekly.csv (per district per week: mean % area in D1+, D2+, D3+)

County locations: average lat/lon of each county's ZIP codes, from the offline
`zipcodes` Python package (an approximation of the county centre, good enough to
pick the nearest of our 9 district points). Districts here = "counties closest to
each point", NOT the official NASS district boundaries - stated as a limitation.
"""
import glob, math, os, collections
import pandas as pd, zipcodes

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POINTS = {"ks_northwest": (39.5, -100.9), "ks_west_central": (38.6, -100.9),
          "ks_southwest": (37.6, -100.9), "ks_north_central": (39.5, -98.3),
          "ks_central": (38.6, -98.3), "ks_south_central": (37.6, -98.3),
          "ks_northeast": (39.5, -95.6), "ks_east_central": (38.6, -95.6),
          "ks_southeast": (37.5, -95.4)}

usdm = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(os.path.join(ROOT, "data/raw/usdm/county_pct_t1_*.csv")))])
usdm = usdm.drop_duplicates(["MapDate", "FIPS"])
usdm["week"] = pd.to_datetime(usdm.ValidStart)

# county centres from ZIP codes
pts = collections.defaultdict(list)
for z in zipcodes.filter_by(state="KS"):
    if z.get("lat"):
        pts[z["county"].strip().lower()].append((float(z["lat"]), float(z["long"])))
cent = {k: (sum(p[0] for p in v)/len(v), sum(p[1] for p in v)/len(v)) for k, v in pts.items()}

def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = math.sin((la2-la1)/2)**2 + math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
    return 6371 * 2 * math.asin(math.sqrt(h))

rows, missing = [], []
for fips, name in usdm[["FIPS", "County"]].drop_duplicates().itertuples(index=False):
    c = cent.get(name.strip().lower())
    if c is None:
        missing.append(name); continue
    d = min(POINTS, key=lambda r: km(c, POINTS[r]))
    rows.append({"fips": fips, "county": name, "lat": round(c[0], 3), "lon": round(c[1], 3),
                 "district": d, "km_to_point": round(km(c, POINTS[d]), 1)})
cmap = pd.DataFrame(rows)
cmap.to_csv(os.path.join(ROOT, "data", "county_district_map.csv"), index=False)
print(f"counties in USDM: {usdm.FIPS.nunique()}, located: {len(cmap)}, unmatched: {missing}")
print(cmap.groupby("district").county.count().to_string())

m = usdm.merge(cmap[["fips", "district"]], left_on="FIPS", right_on="fips")
weekly = (m.groupby(["district", "week"])[["D0", "D1", "D2", "D3", "D4"]].mean()
            .rename(columns=lambda c: f"pct_{c}_or_worse").reset_index())
weekly.to_csv(os.path.join(ROOT, "data", "usdm_district_weekly.csv"), index=False)
print(f"\nweekly rows: {len(weekly):,}  weeks: {weekly.week.min().date()} to {weekly.week.max().date()}")
