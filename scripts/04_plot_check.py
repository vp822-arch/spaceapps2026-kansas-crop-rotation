"""
Quick visual check: one district's root-zone soil wetness vs its normal range.
Written by Claude (Anthropic AI) for Varun Pisharody's Space Apps 2026 team.
Output: reports/ks_central_rootzone_vs_normal.png
"""
import os, pandas as pd, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = "ks_central"
a = pd.read_csv(os.path.join(ROOT, "data", "power_anomalies.csv"), parse_dates=["date"])
n = pd.read_csv(os.path.join(ROOT, "data", "power_normals.csv"))
a = a[a.region == R]; n = n[(n.region == R) & (n.variable == "GWETROOT")].set_index("doy")
fig, ax = plt.subplots(figsize=(12, 4.5))
ax.fill_between(a.date, n.loc[a.doy, "p10"].values, n.loc[a.doy, "p90"].values,
                color="#9bb7d4", alpha=.5, label="normal range (10th-90th percentile, 2015-2022)")
ax.plot(a.date, n.loc[a.doy, "p50"].values, color="#4a6f96", lw=1, label="normal (median)")
ax.plot(a.date, a.GWETROOT, color="#b5462f", lw=1.2, label="actual")
ax.axvline(pd.Timestamp("2023-01-01"), color="grey", ls="--", lw=1)
ax.text(pd.Timestamp("2023-02-01"), ax.get_ylim()[1]*0.97, "test years ->", va="top", color="grey")
ax.set_title(f"Root-zone soil wetness, {R} (NASA POWER / MERRA-2), vs its normal for that time of year")
ax.set_ylabel("wetness (0 = dry, 1 = saturated)"); ax.legend(loc="lower left", fontsize=8, frameon=False)
for s in ("top", "right"): ax.spines[s].set_visible(False)
plt.tight_layout(); plt.savefig(os.path.join(ROOT, "reports", f"{R}_rootzone_vs_normal.png"), dpi=130)
print("saved")
