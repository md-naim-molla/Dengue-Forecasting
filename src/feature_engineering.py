#!/usr/bin/env python3
"""Feature engineering pipeline for Q1 Dengue Multi-Horizon Early Warning System.

Merges:
  - data/dengue_ml_dataset.csv (daily surveillance: admissions & deaths, 2024-2026)
  - data/meteorological_data.csv (daily weather reanalysis: 2023-11-01 to 2026-09-01)

Features Engineered:
1. Entomological & Biometeorological Lags:
   - Temperature (mean, max, min, DTR) at lags: 7, 14, 21, 28, 35, 42 days.
   - Cumulative precipitation over windows: 7d, 14d, 21d, 28d.
   - Relative humidity (mean) at lags: 7, 14, 21, 28 days.
   - Non-linear breeding index: Cumulative 14d rain * mean temp (thermal-moisture suitability).
2. Epidemiological Dynamics:
   - Autoregressive lags: admissions & deaths at lags 1, 2, 3, 7, 14, 21 days.
   - Rolling totals & momentum: roll7, roll14, 7-day momentum ratio ((roll7 - prev_roll7) / prev_roll7).
   - Case fatality indicator: deaths_roll7 / (admitted_roll7 + 1).
3. Solar & Cyclical Seasonality:
   - Fourier harmonic terms: sin(2*pi*doy/365.25), cos(2*pi*doy/365.25), sin(4*pi*doy/365.25), cos(4*pi*doy/365.25).
4. Multi-Horizon Forecasting Targets:
   - Target horizons: H7 (t+7), H14 (t+14), H21 (t+21), H28 (t+28).
   - Surge alert target: binary classification indicator for epidemic threshold exceedance.
"""

import csv
import math
import os
import sys
from datetime import date, datetime, timedelta

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DENGUE_PATH = os.path.join(DATA_DIR, "dengue_ml_dataset.csv")
WEATHER_PATH = os.path.join(DATA_DIR, "meteorological_data.csv")
OUT_PATH = os.path.join(DATA_DIR, "processed_features.csv")


def load_weather(path):
    weather_by_date = {}
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            d = datetime.strptime(row["date"], "%Y-%m-%d").date()
            weather_by_date[d] = {
                "temp_max": float(row["temp_max"]) if row["temp_max"] else None,
                "temp_min": float(row["temp_min"]) if row["temp_min"] else None,
                "temp_mean": float(row["temp_mean"]) if row["temp_mean"] else None,
                "precipitation": float(row["precipitation"]) if row["precipitation"] else 0.0,
                "humidity_mean": float(row["humidity_mean"]) if row["humidity_mean"] else None,
                "wind_speed_max": float(row["wind_speed_max"]) if row["wind_speed_max"] else None,
                "solar_radiation": float(row["solar_radiation"]) if row["solar_radiation"] else None,
                "diurnal_temp_range": float(row["diurnal_temp_range"]) if row["diurnal_temp_range"] else None,
            }
    return weather_by_date


def load_dengue(path):
    dengue_by_date = {}
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            d = datetime.strptime(row["date"], "%Y-%m-%d").date()
            dengue_by_date[d] = {
                "daily_admitted": int(row["daily_admitted"]),
                "daily_deaths": int(row["daily_deaths"]),
            }
    return dengue_by_date


def build_features():
    print("Loading raw surveillance and meteorological data...")
    weather = load_weather(WEATHER_PATH)
    dengue = load_dengue(DENGUE_PATH)

    dengue_dates = sorted(dengue.keys())
    print(f"Dengue timeline: {dengue_dates[0]} to {dengue_dates[-1]} ({len(dengue_dates)} days)")
    print(f"Weather timeline: {min(weather.keys())} to {max(weather.keys())} ({len(weather)} days)")

    # Compute 75th percentile of daily admitted to define the epidemic surge threshold
    all_admitted = [dengue[d]["daily_admitted"] for d in dengue_dates]
    sorted_adm = sorted(all_admitted)
    p75_threshold = sorted_adm[int(0.75 * len(sorted_adm))]
    p90_threshold = sorted_adm[int(0.90 * len(sorted_adm))]
    print(f"Epidemic Surge Thresholds: 75th percentile = {p75_threshold} cases/day, 90th percentile = {p90_threshold} cases/day")

    rows = []
    horizons = [7, 14, 21, 28]

    for idx, d in enumerate(dengue_dates):
        row = {
            "date": d.isoformat(),
            "year": d.year,
            "month": d.month,
            "day": d.day,
            "day_of_year": d.timetuple().tm_yday,
            "week_of_year": d.isocalendar()[1],
            "daily_admitted": dengue[d]["daily_admitted"],
            "daily_deaths": dengue[d]["daily_deaths"],
        }

        # 1. Cyclical calendar harmonic features
        doy = d.timetuple().tm_yday
        row["sin_doy"] = round(math.sin(2 * math.pi * doy / 365.25), 5)
        row["cos_doy"] = round(math.cos(2 * math.pi * doy / 365.25), 5)
        row["sin2_doy"] = round(math.sin(4 * math.pi * doy / 365.25), 5)
        row["cos2_doy"] = round(math.cos(4 * math.pi * doy / 365.25), 5)

        # 2. Epidemiological rolling sums & lags
        # rolling 7-day admitted
        past_7d = [dengue[d - timedelta(days=k)]["daily_admitted"] for k in range(7) if (d - timedelta(days=k)) in dengue]
        past_14d = [dengue[d - timedelta(days=k)]["daily_admitted"] for k in range(14) if (d - timedelta(days=k)) in dengue]
        past_7d_deaths = [dengue[d - timedelta(days=k)]["daily_deaths"] for k in range(7) if (d - timedelta(days=k)) in dengue]

        row["roll7_admitted"] = sum(past_7d)
        row["roll14_admitted"] = sum(past_14d)
        row["roll7_deaths"] = sum(past_7d_deaths)

        # 7-day momentum ratio
        prev_7d = [dengue[d - timedelta(days=k)]["daily_admitted"] for k in range(7, 14) if (d - timedelta(days=k)) in dengue]
        prev_sum = sum(prev_7d)
        row["momentum_7d"] = round((row["roll7_admitted"] - prev_sum) / (prev_sum + 1), 4)

        # Case fatality ratio proxy
        row["cfr_roll7"] = round(row["roll7_deaths"] / (row["roll7_admitted"] + 1), 5)

        # Autoregressive lags
        for lag in [1, 2, 3, 7, 14, 21]:
            target_d = d - timedelta(days=lag)
            row[f"lag{lag}_admitted"] = dengue[target_d]["daily_admitted"] if target_d in dengue else 0
            if lag in [1, 7, 14]:
                row[f"lag{lag}_deaths"] = dengue[target_d]["daily_deaths"] if target_d in dengue else 0

        # 3. Biometeorological Lags & Accumulations
        # Weather on day t
        w_t = weather.get(d, {})
        row["temp_mean_t0"] = w_t.get("temp_mean")
        row["temp_max_t0"] = w_t.get("temp_max")
        row["temp_min_t0"] = w_t.get("temp_min")
        row["precipitation_t0"] = w_t.get("precipitation", 0.0)
        row["humidity_t0"] = w_t.get("humidity_mean")
        row["dtr_t0"] = w_t.get("diurnal_temp_range")

        # Weather distributed lags (representing extrinsic incubation and breeding lags)
        for lag in [7, 14, 21, 28, 35, 42]:
            w_lag = weather.get(d - timedelta(days=lag), {})
            row[f"temp_mean_lag{lag}"] = w_lag.get("temp_mean")
            row[f"humidity_lag{lag}"] = w_lag.get("humidity_mean")
            row[f"dtr_lag{lag}"] = w_lag.get("diurnal_temp_range")

        # Cumulative precipitation windows
        for win in [7, 14, 21, 28]:
            precip_win = [weather[d - timedelta(days=k)]["precipitation"] for k in range(win) if (d - timedelta(days=k)) in weather]
            row[f"precip_sum_{win}d"] = round(sum(precip_win), 2)

        # Rolling temperature mean (thermal comfort for mosquito survival: 24-30°C optimal)
        t_win14 = [weather[d - timedelta(days=k)]["temp_mean"] for k in range(14) if (d - timedelta(days=k)) in weather and weather[d - timedelta(days=k)]["temp_mean"] is not None]
        row["temp_mean_roll14"] = round(sum(t_win14) / len(t_win14), 2) if t_win14 else None

        # Breeding suitability interaction term: past 14d rainfall * past 14d temperature
        if row["temp_mean_roll14"] is not None:
            row["breeding_suitability_idx"] = round(row["precip_sum_14d"] * (row["temp_mean_roll14"] / 30.0), 2)
        else:
            row["breeding_suitability_idx"] = 0.0

        # 4. Multi-Horizon Targets (t + H)
        for H in horizons:
            fut_d = d + timedelta(days=H)
            if fut_d in dengue:
                row[f"target_admitted_H{H}"] = dengue[fut_d]["daily_admitted"]
                row[f"target_deaths_H{H}"] = dengue[fut_d]["daily_deaths"]
                # Binary surge indicator
                row[f"target_surge_H{H}"] = 1 if dengue[fut_d]["daily_admitted"] >= p75_threshold else 0
            else:
                row[f"target_admitted_H{H}"] = None
                row[f"target_deaths_H{H}"] = None
                row[f"target_surge_H{H}"] = None

        rows.append(row)

    # Write output
    fieldnames = list(rows[0].keys())
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nFeature engineering complete! Processed matrix written to:\n  {OUT_PATH}")
    print(f"Total observations: {len(rows)}")
    print(f"Total features + targets: {len(fieldnames)}")
    print(f"Surge alert thresholds: 75th percentile = {p75_threshold} cases/day, 90th percentile = {p90_threshold} cases/day")


if __name__ == "__main__":
    build_features()

