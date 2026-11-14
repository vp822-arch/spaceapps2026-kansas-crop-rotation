"""
Step 11 - How much does the NASA data add? (ablation) + warning cut-off trade-offs.
Written by Claude (Anthropic AI) for Varun Pisharody's Space Apps 2026 team.
Re-uses the feature table from step 10 (re-builds it the same way).
Appends results to reports/model_report.md.
"""
import os, runpy, io, contextlib, numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import brier_score_loss, roc_auc_score
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with contextlib.redirect_stdout(io.StringIO()):
    ns = runpy.run_path(os.path.join(ROOT, "scripts/10_model_backtest.py"))
train, test = ns["train"], ns["test"]
NASA = ["GWETROOT_pct", "GWETTOP_pct", "rain_30d_pct", "rain_60d_pct", "rain_90d_pct", "T2M_MAX_z", "drying_4w"]
sets = {"all inputs": ns["FEATS"],
        "without NASA data (USDM now + season only)": ["usdm_now", "season_sin", "season_cos"],
        "NASA data only (no USDM now)": NASA + ["season_sin", "season_cos"],
        "without soil wetness (rain/temp kept)": [f for f in ns["FEATS"] if "GWET" not in f and f != "drying_4w"]}
out = ["", "## Ablation: what happens without the NASA data (logistic model, test years)", "",
       "| inputs | Brier all | AUC all | Brier onset | AUC onset |", "|---|---|---|---|---|"]
on = test.in_drought_now == 0
for name, f in sets.items():
    m = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)).fit(train[f], train.target)
    p = m.predict_proba(test[f])[:, 1]
    out.append(f"| {name} | {brier_score_loss(test.target, p):.3f} | {roc_auc_score(test.target, p):.2f} | "
               f"{brier_score_loss(test.target[on], p[on]):.3f} | {roc_auc_score(test.target[on], p[on]):.2f} |")
out += ["", "## Onset warnings at different cut-offs (logistic, all inputs, test years)", "",
        "| warn if probability >= | hit rate | false alarm ratio | warnings issued |", "|---|---|---|---|"]
y, p = test.target[on].values, test.p_logistic[on].values
for c in [0.5, 0.4, 0.3, 0.2, 0.15]:
    wv = p >= c; h = (wv & (y == 1)).sum()
    out.append(f"| {c:.2f} | {h/(y==1).sum():.2f} | {((wv.sum()-h)/wv.sum()) if wv.sum() else float('nan'):.2f} | {wv.sum()} |")
out += ["", "## Known limitations (found while checking the results)", "",
        "- Slow to call the END of a drought: it leans on current USDM coverage, e.g. SE Kansas Sept-Oct 2026 "
        "stayed at 89-94% predicted while the drought ended in October.",
        "- Onset warnings are a trade-off: at a 20-30% warning level it catches about 34-48% of new droughts "
        "about 4 weeks ahead, but most warnings are false alarms (63-67%).",
        "- Lead times are short: in the 2024 central-Kansas example the warning was issued 15 days before the "
        "April onset and only 1 day before the July onset (effectively no warning).",
        "- POWER soil wetness (MERRA-2 model, ~55 km) adds little beyond rainfall; SMAP satellite soil "
        "moisture is pending and is the main hope for improvement.",
        "- 'Districts' = counties nearest each of 9 points (county centres approximated from ZIP codes), "
        "not official NASS district boundaries.",
        "- One root-zone data artifact (south central, from 2026-10-01) is flagged. Possible cause (unconfirmed): "
        "POWER's recent data blends sources (its files list MERRA-2 and GEOS-IT), so a change of source stream "
        "may produce a step; a backup model without "
        "root-zone wetness is used there (its test scores are in the line above this table).",
        "- Timing fixed after a double-check: forecasts are now scored 29 days after the last input day "
        "(earlier version was effectively 22 days, which overstated skill)."]
open(os.path.join(ROOT, "reports/model_report.md"), "a").write("\n".join(out) + "\n")
print("\n".join(out))
