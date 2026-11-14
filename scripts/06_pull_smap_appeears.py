"""
Step 6 - Pull SMAP soil moisture time series at our Kansas points via NASA AppEEARS.
Written by Claude (Anthropic AI) for Varun Pisharody's Space Apps 2026 team.
Cite in References: NASA AppEEARS; SMAP SPL3SMP_E V006 (DOI 10.5067/M20OXIZHY3RJ - check
on NSIDC page) and SMAP SPL4SMGP V008 (NSIDC), plus this script as AI-generated code.

What it does:
  1. You type your Earthdata username + password HERE, in your own terminal.
     They go straight to NASA's AppEEARS login and are never saved or printed.
  2. Submits ONE "point" task to AppEEARS for:
       - SPL3SMP_E.006  (9 km daily, satellite retrieval, top ~5 cm, AM + PM passes)
       - SPL4SMGP.008   (9 km 3-hourly, model + SMAP, surface AND root zone)
     at every point in data/ks_points.csv (made from TIGER counties) or, if that
     file is missing, at the 9 Kansas crop-district points.
  3. Waits for NASA to process it (can take 10 min to a few hours - leave it running;
     if you close it, just run the script again: it resumes the same task).
  4. Downloads the CSV results into data/raw/smap/.

Run in WSL:  cd /mnt/c/SpaceApps2026 && python3 scripts/06_pull_smap_appeears.py
Standard library only.
"""
import base64, csv, getpass, json, os, re, sys, time, urllib.request, urllib.error
from datetime import date, timedelta

API = "https://appeears.earthdatacloud.nasa.gov/api/"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "raw", "smap")
TASK_FILE = os.path.join(OUT, "appeears_task_id.txt")
os.makedirs(OUT, exist_ok=True)

FALLBACK_POINTS = {   # same as scripts/01_pull_power.py
    "ks_northwest": (39.5, -100.9), "ks_west_central": (38.6, -100.9),
    "ks_southwest": (37.6, -100.9), "ks_north_central": (39.5, -98.3),
    "ks_central": (38.6, -98.3), "ks_south_central": (37.6, -98.3),
    "ks_northeast": (39.5, -95.6), "ks_east_central": (38.6, -95.6),
    "ks_southeast": (37.5, -95.4)}

def call(path, method="GET", token=None, body=None, basic=None, raw=False):
    req = urllib.request.Request(API + path, method=method)
    if token: req.add_header("Authorization", f"Bearer {token}")
    if basic: req.add_header("Authorization", "Basic " + basic)
    data = None
    if body is not None:
        data = json.dumps(body).encode(); req.add_header("Content-Type", "application/json")
    elif method == "POST":
        req.add_header("Content-Length", "0")
    try:
        with urllib.request.urlopen(req, data=data, timeout=300) as r:
            return r.read() if raw else json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        sys.exit(f"AppEEARS error {e.code} on {path}: {e.read()[:500].decode(errors='replace')}")

def load_points():
    p = os.path.join(ROOT, "data", "ks_points.csv")
    if os.path.exists(p):
        rows = list(csv.DictReader(open(p)))
        print(f"Using {len(rows)} points from data/ks_points.csv")
        return [{"id": r["id"], "latitude": float(r["lat"]), "longitude": float(r["lon"]),
                 "category": r.get("category", "ks")} for r in rows]
    print("data/ks_points.csv not found -> using the 9 crop-district points")
    return [{"id": k, "latitude": v[0], "longitude": v[1], "category": "district"}
            for k, v in FALLBACK_POINTS.items()]

def pick_layers(product, wanted):
    info = call(f"product/{product}")          # public endpoint: lists layer names
    names = list(info.keys())
    chosen = [n for n in names if any(re.search(w, n) for w in wanted)]
    if not chosen:
        print(f"No matching layers in {product}. Available layers:\n  " + "\n  ".join(names))
        sys.exit("Send this list to Claude so it can fix the layer names.")
    print(f"{product}: {chosen}")
    return [{"product": product, "layer": n} for n in chosen]

# ---- log in (credentials typed by Varun, never stored) ----
user = input("Earthdata username: ").strip()
pw = getpass.getpass("Earthdata password (hidden): ")
token = call("login", "POST", basic=base64.b64encode(f"{user}:{pw}".encode()).decode())["token"]
del pw
print("Logged in to AppEEARS.")

try:
    if os.path.exists(TASK_FILE):
        task_id = open(TASK_FILE).read().strip()
        print("Resuming existing task", task_id)
    else:
        layers = (pick_layers("SPL3SMP_E.006", [r"_soil_moisture(_pm)?$", r"retrieval_qual_flag(_pm)?$"]) +
                  pick_layers("SPL4SMGP.008", [r"_sm_surface$", r"_sm_rootzone$"]))
        end = (date.today() - timedelta(days=3)).strftime("%m-%d-%Y")
        task = {"task_type": "point", "task_name": "spaceapps2026_kansas_smap",
                "params": {"dates": [{"startDate": "04-01-2015", "endDate": end}],
                           "layers": layers, "coordinates": load_points()}}
        json.dump(task, open(os.path.join(OUT, "appeears_task_request.json"), "w"), indent=1)
        task_id = call("task", "POST", token=token, body=task)["task_id"]
        open(TASK_FILE, "w").write(task_id)
        print("Submitted task", task_id)

    while True:
        st = call(f"task/{task_id}", token=token)
        status = st.get("status")
        print(time.strftime("%H:%M:%S"), "status:", status, st.get("progress", ""))
        if status == "done": break
        if status in ("error", "expired"): sys.exit(f"Task ended with status {status}: {st}")
        time.sleep(60)

    bundle = call(f"bundle/{task_id}", token=token)
    for f in bundle["files"]:
        dest = os.path.join(OUT, f["file_name"].replace("/", "_"))
        if os.path.exists(dest): continue
        open(dest, "wb").write(call(f"bundle/{task_id}/{f['file_id']}", token=token, raw=True))
        print("downloaded", dest)
    print("Done. SMAP files are in", OUT)
finally:
    try: call("logout", "POST", token=token, raw=True)
    except SystemExit: pass
