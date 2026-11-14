"""
run_weekly.py - refresh the whole crop rotation advice pipeline in one go.
Written by Claude (Anthropic AI) for Varun Pisharody's Space Apps 2026 team.

What it does, in order (stops at the first step that fails, so the app keeps
showing the last good advice):
  1. 01_pull_power.py      new NASA POWER days (full record re-downloaded into data/raw/power_latest)
  2. 08_pull_usdm.py       new U.S. Drought Monitor weeks for the current year
  3. 02_clean_power.py     cleaning + quality flags
  4. 03_normals_power.py   compare each day with normal
  5. 09_usdm_labels.py     drought labels per district
  6. 11_ablation_thresholds.py  runs the drought model (script 10) -> data/live_forecast.csv
  7. 13_crop_ranking.py    single-crop scores
  8. 14_rotation_ranking.py     top-3 rotations with weights
     17_export_app_json.py     same advice as data/app_rotation_advice.json for the app
  9. checks                sanity checks on the new advice (below)
 10. 19_upload_cloudflare_r2.py publish the app JSON to Cloudflare R2 (skipped with --no-load)
     (Tiger Cloud, 07_load_tiger_cloud.py, is no longer used: the team moved to Cloudflare 2026-11-14)

Usage (WSL, from C:\\SpaceApps2026):   bash scripts/run_weekly.sh
Options: --no-load       do everything except the Cloudflare upload
         --skip-download reuse the data already on disk (for testing)
A short log of every run is appended to reports/run_log.md.
"""
import os, subprocess, sys, time
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = lambda f: os.path.join(ROOT, "scripts", f)
args = set(sys.argv[1:])
STEPS = ([] if "--skip-download" in args else ["01_pull_power.py", "08_pull_usdm.py"]) + [
    "02_clean_power.py", "03_normals_power.py", "09_usdm_labels.py",
    "11_ablation_thresholds.py", "13_crop_ranking.py", "14_rotation_ranking.py",
    "17_export_app_json.py"]
LOG = os.path.join(ROOT, "reports", "run_log.md")
log_lines = [f"\n## Run {datetime.now():%Y-%m-%d %H:%M}  (options: {' '.join(sorted(args)) or 'none'})"]

def finish(ok, msg):
    log_lines.append(f"- RESULT: {'OK' if ok else 'STOPPED'} - {msg}")
    with open(LOG, "a") as f:
        f.write("\n".join(log_lines) + "\n")
    print(("\nDONE: " if ok else "\nSTOPPED: ") + msg)
    sys.exit(0 if ok else 1)

env = dict(os.environ, REFRESH="1", MPLBACKEND="Agg")
for step in STEPS:
    t0 = time.time()
    print(f"\n=== {step} ===", flush=True)
    r = subprocess.run([sys.executable, S(step)], cwd=ROOT, env=env)
    log_lines.append(f"- {step}: {'ok' if r.returncode == 0 else 'FAILED'} ({time.time()-t0:.0f} s)")
    if r.returncode != 0:
        finish(False, f"{step} failed; database NOT updated, app still shows the previous advice.")

# ---- sanity checks before anything reaches the app ----
import pandas as pd
print("\n=== checks ===")
problems = []
pw = pd.read_csv(os.path.join(ROOT, "data", "power_daily_clean.csv"), parse_dates=["date"])
last_day = pw.date.max()
age = (pd.Timestamp.today().normalize() - last_day).days
if age > 14:
    problems.append(f"newest NASA POWER day is {last_day:%Y-%m-%d} ({age} days old)")
if pw.groupby("region").date.max().nunique() != 1:
    problems.append("districts do not all end on the same day")
lf = pd.read_csv(os.path.join(ROOT, "data", "live_forecast.csv"))
# (a blank root-zone value is expected where the backup model is used, e.g. south_central)
if lf.region.nunique() != 9 or lf.p_logistic.isna().any():
    problems.append("live forecast does not have 9 complete districts")
rr = pd.read_csv(os.path.join(ROOT, "data", "rotation_ranking.csv"))
top = rr[rr.recommended_rank <= 3]
if top.groupby("region").size().ne(3).any() or top.region.nunique() != 9:
    problems.append("not exactly 3 recommended rotations in each of the 9 districts")
import json as _json
try:
    _fc = _json.load(open(os.path.join(ROOT, "data", "factor_coefficients.json")))["crops"]
    if set(_fc) != {"corn", "sorghum", "soybean", "wheat"}:
        problems.append("factor_coefficients.json does not cover the 4 crops")
except Exception as e:
    problems.append(f"factor_coefficients.json missing or unreadable ({e})")
cc = pd.read_csv(os.path.join(ROOT, "data", "rotation_by_current_crop.csv"))
if cc.groupby(["region", "current_crop"]).ngroups != 36:
    problems.append("current-crop table does not cover 9 districts x 4 crops")
ccs = cc.dropna(subset=["rank"]).groupby(["region", "current_crop"]).weight_pct.sum()
if (ccs != 100).any():
    problems.append("current-crop weights do not total 100 somewhere")
sums = top.groupby("region").weight_pct.sum()
if (sums != 100).any():
    problems.append(f"weights do not total 100 in: {', '.join(sums[sums != 100].index)}")
summary = "; ".join(
    f"{reg.replace('ks_', '')}: " + ", ".join(f"{g.rotation} {int(g.weight_pct)}%" for g in
                                              grp.sort_values('recommended_rank').itertuples())
    for reg, grp in top.groupby("region"))
log_lines.append(f"- data through {last_day:%Y-%m-%d}; top-3: {summary}")
print(f"data through {last_day:%Y-%m-%d}")
if problems:
    for p in problems:
        print("  PROBLEM:", p)
    finish(False, "checks failed (" + "; ".join(problems) + "); database NOT updated.")
print("all checks passed")

if "--no-load" in args:
    finish(True, "pipeline refreshed; Cloudflare upload skipped (--no-load).")
print("\n=== 19_upload_cloudflare_r2.py ===", flush=True)
r = subprocess.run([sys.executable, S("19_upload_cloudflare_r2.py")], cwd=ROOT, env=env)
if r.returncode != 0:
    finish(False, "Cloudflare upload failed; the app keeps showing the previous advice.")
finish(True, f"advice refreshed with data through {last_day:%Y-%m-%d} and published to Cloudflare R2.")
