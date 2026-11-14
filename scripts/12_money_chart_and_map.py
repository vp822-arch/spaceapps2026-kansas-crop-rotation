"""
Step 12 - Presentation charts.
Written by Claude (Anthropic AI) for Varun Pisharody's Space Apps 2026 team.
  reports/money_chart_ks_central_2024.png  - did the model warn before the drought began?
  reports/kansas_risk_map.png              - latest drought-risk probability per district
Rules followed: one y-axis per panel (no dual axes), thin marks, recessive grid,
direct labels, text in neutral ink.
"""
import os, pandas as pd, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e6e5e1", "#fcfcfb"
BLUE, ORANGE = "#2a78d6", "#eb6834"
plt.rcParams.update({"font.size": 11, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2, "figure.facecolor": SURF,
                     "axes.facecolor": SURF})

# ---------- money chart ----------
R, START, END, WARN = "ks_central", "2024-01-01", "2024-12-31", 0.30
p = pd.read_csv(os.path.join(ROOT, "data/model_predictions.csv"), parse_dates=["week"])
s = p[(p.region == R) & (p.week >= START) & (p.week <= END)].sort_values("week")
dr = s.usdm_now.values >= 50
onsets = [s.week.iloc[i] for i in range(1, len(s)) if dr[i] and not dr[max(0, i-4):i].any()]
fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 6.2), sharex=True, gridspec_kw={"hspace": 0.25})
a1.fill_between(s.week, s.usdm_now, color=ORANGE, alpha=0.25, lw=0)
a1.plot(s.week, s.usdm_now, color=ORANGE, lw=2)
a1.axhline(50, color=INK2, lw=1, ls="--"); a1.text(s.week.iloc[0], 53, "drought line: 50% of area", color=INK2, fontsize=9)
a1.set_ylabel("% of district area\nin drought (USDM D1+)"); a1.set_ylim(0, 105)
a1.set_title("Central Kansas, 2024: the model's ~4-week warning vs. the drought that followed",
             loc="left", color=INK, fontsize=13, pad=12)
s["issued"] = s.week + pd.Timedelta(days=6)   # a forecast exists only once its week of data is complete
a2.plot(s.issued, s.p_logistic, color=BLUE, lw=2)
a2.axhline(WARN, color=INK2, lw=1, ls="--"); a2.text(s.issued.iloc[0] if "issued" in s else s.week.iloc[0], WARN + 0.03, f"warning level ({WARN:.0%})", color=INK2, fontsize=9)
a2.set_ylabel("model: chance of drought\n~4 weeks later\n(plotted on issue date)"); a2.set_ylim(0, 1)
a2.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
for on in onsets:
    # Honest lead time: the warning must START after the previous drought ended,
    # i.e. the unbroken run of weeks with probability >= WARN that leads into the onset,
    # counting only weeks when the district was NOT already in drought.
    before = s[(s.week < on)].iloc[::-1]
    run = []
    for _, row in before.iterrows():
        if row.p_logistic >= WARN and row.usdm_now < 50: run.append(row)
        else: break
    for ax in (a1, a2): ax.axvline(on, color=INK, lw=1)
    a1.text(on, 99, " drought begins", color=INK, fontsize=9, va="top")
    if run:
        first = run[-1]
        issued = first.week + pd.Timedelta(days=6)     # forecast usable only after its week's data ends
        lead = (on - issued).days
        a2.scatter([issued], [first.p_logistic], s=60, color=BLUE, edgecolor=SURF, linewidth=2, zorder=3)
        a2.annotate((f"warning issued\n{lead} days before" if lead >= 7 else f"warning came only\n{lead} day{'s' if lead != 1 else ''} before"), (issued, first.p_logistic),
                    xytext=(-8, -42), textcoords="offset points", ha="right", fontsize=9, color=INK,
                    arrowprops=dict(arrowstyle="-", color=INK2, lw=0.8))
        print(f"onset {on.date()}: warning issued {issued.date()} ({(on - issued).days} days before)")
    else:
        print(f"onset {on.date()}: no warning beforehand")
for ax in (a1, a2):
    ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
    for sp in ("top", "right"): ax.spines[sp].set_visible(False)
fig.text(0.01, 0.005, "Model trained on 2015-2022 only; 2024 is out-of-sample. Inputs: NASA POWER soil wetness, rain, "
         "temperature + current USDM. Drought record: U.S. Drought Monitor.", fontsize=8, color=INK2)
fig.savefig(os.path.join(ROOT, "reports/money_chart_ks_central_2024.png"), dpi=150, bbox_inches="tight")
print("money chart saved; onsets:", [o.date() for o in onsets])

# ---------- map: latest risk per district (county dots coloured by their district's risk) ----------
last = pd.read_csv(os.path.join(ROOT, "data/live_forecast.csv"), parse_dates=["week", "issued", "forecast_for_week"]).set_index("region")
cm = pd.read_csv(os.path.join(ROOT, "data/county_district_map.csv"))
cm["risk"] = cm.district.map(last.p_logistic)
seq = matplotlib.colors.LinearSegmentedColormap.from_list("seq", ["#fbe3d6", "#f2a27e", ORANGE, "#a8401a"])
fig, ax = plt.subplots(figsize=(10, 6.4))
sc = ax.scatter(cm.lon, cm.lat, c=cm.risk, cmap=seq, vmin=0, vmax=1, s=230, marker="s",
                edgecolor=SURF, linewidth=2)
pts = {"ks_northwest": (39.5, -100.9), "ks_west_central": (38.6, -100.9), "ks_southwest": (37.6, -100.9),
       "ks_north_central": (39.5, -98.3), "ks_central": (38.6, -98.3), "ks_south_central": (37.6, -98.3),
       "ks_northeast": (39.5, -95.6), "ks_east_central": (38.6, -95.6), "ks_southeast": (37.5, -95.4)}
for r, (la, lo) in pts.items():
    ax.text(lo, la + 0.32, f"{r.replace('ks_', '').replace('_', ' ')}\n{last.p_logistic[r]:.0%}",
            ha="center", fontsize=9, color=INK, bbox=dict(boxstyle="round,pad=0.2", fc=SURF, ec="none", alpha=0.85))
cb = fig.colorbar(sc, ax=ax, orientation="horizontal", fraction=0.05, pad=0.03, aspect=40); cb.set_label("chance of drought on the forecast date", color=INK2)
cb.ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0)); cb.outline.set_visible(False)
ax.set_title(f"Kansas: chance each district is in drought on {last.forecast_for_week.max().date()}",
             loc="left", color=INK, fontsize=13, pad=22)
ax.text(0, 1.015, f"Forecast issued from data to {last.issued.max().date()}. Each square is a county, coloured by its district's forecast.\n"
        "South central uses the backup model because its root-zone soil data is flagged as suspect.",
        transform=ax.transAxes, fontsize=8.5, color=INK2)
ax.set_aspect(1.25); ax.set_xticks([]); ax.set_yticks([])
for sp in ax.spines.values(): sp.set_visible(False)
fig.savefig(os.path.join(ROOT, "reports/kansas_risk_map.png"), dpi=150, bbox_inches="tight")
print("map saved; data week", last.week.max().date(), "-> forecast for", last.forecast_for_week.max().date())
print(last.p_logistic.round(2).to_string())
