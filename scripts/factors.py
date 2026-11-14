"""
factors.py - the weather factors behind each simulated crop season, all from NASA POWER daily data.
Written by Claude (Anthropic AI) for Varun Pisharody's Space Apps 2026 team.
Shared by 14_rotation_ranking.py, 16_validate_with_yields.py and 21_calibrate_factors.py so the
ranking, the validation and the calibration always use exactly the same calculations.

Each crop season gets a score from 0 to 1:   water factor x heat factor x freeze factor
  water  : FAO I&D 33 yield response  1 - Ky x (1 - water / need). The FAO seasonal need is scaled by
           that season's reference evapotranspiration (ET0, FAO-56 Penman-Monteith from POWER
           temperature, humidity, sunlight and wind) relative to the district's average for the same
           window, so a hot, dry, windy season needs more water.          [if "et0_scaling" is on]
  heat   : 1 - b_heat x (days with max temperature >= the crop's threshold in its flowering window)
  freeze : 1 - b_freeze x freeze metric (wheat: days <= 28 F while heading; summer crops: days of the
           season lost to a fall freeze <= 28 F before the normal harvest date)
b_heat and b_freeze are fitted to real USDA county yields by 21_calibrate_factors.py
(data/factor_coefficients.json); a factor that does not improve out-of-sample prediction gets 0.

Thresholds and windows (sources in reports/REFERENCES.md):
  corn    : heat >= 35.0 C (95 F) Jul 5 - Jul 31, silking/pollination (K-State)
  sorghum : heat >= 37.8 C (100 F) Jul 25 - Aug 25, bloom (K-State: sorghum heat units capped at 100 F)
  soybean : heat >= 35.0 C Jul 10 - Aug 20, flowering/pod set (team assumption, same as corn)
  dcsoy   : heat >= 35.0 C Aug 10 - Sep 10 (double-crop soybean flowers later)
  wheat   : heat >= 27.8 C (82 F) May 1 - May 25, just before/at flowering (K-State);
            freeze <= -2.2 C (28 F) Apr 15 - May 20, boot/heading (K-State)
  summer crops: fall freeze <= -2.2 C (28 F) between Sep 1 and the normal harvest date
"""
import json, math, os
import numpy as np
import pandas as pd

FREEZE_C = -2.2                     # 28 F
CROP = {  # plant (m,d), harvest (m,d), harvest year offset, FAO need mm, FAO Ky   (same as before)
    "wheat":   ((9, 15), (6, 20), 1, 550, 1.05),
    "corn":    ((4, 15), (9, 10), 0, 650, 1.25),
    "sorghum": ((5, 15), (9, 25), 0, 550, 0.90),
    "soybean": ((5, 15), (10, 1), 0, 575, 0.85),
    "dcsoy":   ((7, 1), (10, 15), 0, 450, 0.85),
}
HEAT = {  # crop: (threshold C, window start (m,d), window end (m,d)) - window in the harvest year
    "corn":    (35.0, (7, 5), (7, 31)),
    "sorghum": (37.8, (7, 25), (8, 25)),
    "soybean": (35.0, (7, 10), (8, 20)),
    "dcsoy":   (35.0, (8, 10), (9, 10)),
    "wheat":   (27.8, (5, 1), (5, 25)),
}
WHEAT_FREEZE_WINDOW = ((4, 15), (5, 20))
COEF_CROP = {"dcsoy": "soybean"}   # double-crop soybean uses the soybean coefficients


def et0_fao56(df, lat_deg, elev_m):
    """Daily reference ET (mm/day), FAO-56 Penman-Monteith (eqs. 6-8, 11-13, 19, 21-39), G = 0."""
    tmax, tmin = df.T2M_MAX.values, df.T2M_MIN.values
    tmean = (tmax + tmin) / 2
    rs = df.ALLSKY_SFC_SW_DWN.values                      # MJ m-2 day-1
    u2 = df.WS2M.values                                   # m/s at 2 m
    rh = df.RH2M.values                                   # % (daily mean)
    P = 101.3 * ((293 - 0.0065 * elev_m) / 293) ** 5.26   # kPa
    gamma = 0.000665 * P
    es_f = lambda t: 0.6108 * np.exp(17.27 * t / (t + 237.3))
    es = (es_f(tmax) + es_f(tmin)) / 2
    ea = rh / 100 * es                                    # eq. 19 (RH mean)
    delta = 4098 * es_f(tmean) / (tmean + 237.3) ** 2
    J = pd.DatetimeIndex(df.index).dayofyear.values
    phi = math.radians(lat_deg)
    dr = 1 + 0.033 * np.cos(2 * np.pi / 365 * J)
    dec = 0.409 * np.sin(2 * np.pi / 365 * J - 1.39)
    ws = np.arccos(-np.tan(phi) * np.tan(dec))
    ra = 24 * 60 / np.pi * 0.0820 * dr * (ws * np.sin(phi) * np.sin(dec) + np.cos(phi) * np.cos(dec) * np.sin(ws))
    rso = (0.75 + 2e-5 * elev_m) * ra
    rns = (1 - 0.23) * rs
    sigma = 4.903e-9
    ratio = np.clip(rs / np.where(rso > 0, rso, np.nan), 0.25, 1.0)
    rnl = sigma * ((tmax + 273.16) ** 4 + (tmin + 273.16) ** 4) / 2 * (0.34 - 0.14 * np.sqrt(np.maximum(ea, 0))) * (1.35 * ratio - 0.35)
    rn = rns - rnl
    et0 = (0.408 * delta * rn + gamma * 900 / (tmean + 273) * u2 * (es - ea)) / (delta + gamma * (1 + 0.34 * u2))
    return np.maximum(et0, 0)


def load_weather(root):
    """region -> DataFrame (daily, indexed by date) with rain, temperatures and ET0."""
    w = pd.read_csv(os.path.join(root, "data/power_daily_clean.csv"), parse_dates=["date"])
    out = {}
    for region, g in w.groupby("region"):
        g = g.set_index("date").sort_index()
        meta = json.load(open(os.path.join(root, "data/raw/power", f"{region}_0.json")))["geometry"]["coordinates"]
        lon, lat, elev = meta
        g = g.copy()
        g["ET0"] = et0_fao56(g, lat, elev)
        out[region] = g
    return out


def _d(y, md):
    return pd.Timestamp(y, *md)


def season_features(wx, crop, plant, harv, et0_mean=None):
    """Weather features for one crop season. et0_mean: the district's average season ET0 for this crop."""
    season = wx.loc[plant:harv]
    y = harv.year
    thr, ws, we = HEAT[crop]
    if crop == "wheat":
        win = wx.loc[_d(y, ws):_d(y, we)]
    else:
        win = wx.loc[_d(plant.year, ws):_d(plant.year, we)]
    heat_days = int((win.T2M_MAX >= thr).sum())
    if crop == "wheat":
        fz = wx.loc[_d(y, WHEAT_FREEZE_WINDOW[0]):_d(y, WHEAT_FREEZE_WINDOW[1])]
        freeze = int((fz.T2M_MIN <= FREEZE_C).sum())
    else:
        fall = wx.loc[_d(plant.year, (9, 1)):harv]
        hit = fall.index[fall.T2M_MIN <= FREEZE_C]
        freeze = int((harv - hit[0]).days) if len(hit) else 0
    et0 = float(season.ET0.sum())
    return {"heat_days": heat_days, "freeze": freeze, "et0": et0,
            "et0_ratio": (et0 / et0_mean) if et0_mean else 1.0}


def et0_season_means(weather, crops=("wheat", "corn", "sorghum", "soybean", "dcsoy")):
    """Average season ET0 per (region, crop) over every complete season in the record."""
    out = {}
    for region, wx in weather.items():
        first, last = wx.index.min(), wx.index.max()
        for crop in crops:
            (pm, hm, hoff) = CROP[crop][0], CROP[crop][1], CROP[crop][2]
            vals = []
            for y in range(first.year - 1, last.year + 1):
                p, h = _d(y, pm), _d(y + hoff, hm)
                if p >= first and h <= last:
                    vals.append(float(wx.loc[p:h].ET0.sum()))
            out[(region, crop)] = float(np.mean(vals))
    return out


def load_coefficients(root):
    p = os.path.join(root, "data/factor_coefficients.json")
    return json.load(open(p))


def season_score(crop, water, feats, coef):
    """0-1 score for one crop season = water factor x heat factor x freeze factor."""
    need, ky = CROP[crop][3], CROP[crop][4]
    c = coef["crops"][COEF_CROP.get(crop, crop)]
    if c.get("et0_scaling", coef.get("et0_scaling")):
        need = need * feats["et0_ratio"]
    water_f = max(0.0, 1 - ky * (1 - min(water / need, 1.0)))
    heat_f = max(0.0, 1 - c["b_heat"] * feats["heat_days"])
    freeze_f = max(0.0, 1 - c["b_freeze"] * feats["freeze"])
    return water_f * heat_f * freeze_f, (water_f, heat_f, freeze_f)
