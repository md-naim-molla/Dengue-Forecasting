#!/usr/bin/env python3
"""Exploratory epidemiological synthesis and statistical characterization.

Produces:
1. Annual epidemic wave metrics (2024, 2025, 2026):
   - Total admissions, total deaths, crude CFR (Case Fatality Rate %)
   - Epidemic peak magnitude, peak date, duration of high-transmission window
2. Cross-correlation analysis (CCF) between climatic drivers and dengue admissions:
   - Identifies optimal lag (days) for temperature, precipitation, and relative humidity.
3. Summary tables formatted for manuscript submission (CSV / LaTeX ready).
"""

import csv
import math
import os
from collections import defaultdict
from datetime import datetime

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "processed_features.csv")
TABLES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tables")


def mean(vals):
    v = [x for x in vals if x is not None]
    return sum(v) / len(v) if v else 0.0


def std(vals):
    v = [x for x in vals if x is not None]
    if len(v) < 2:
        return 0.0
    m = mean(v)
    return math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1))


def pearson_r(x, y):
    pairs = [(a, b) for a, b in zip(x, y) if a is not None and b is not None]
    if len(pairs) < 3:
        return 0.0
    x_vals = [p[0] for p in pairs]
    y_vals = [p[1] for p in pairs]
    mx, my = mean(x_vals), mean(y_vals)
    sx, sy = std(x_vals), std(y_vals)
    if sx == 0 or sy == 0:
        return 0.0
    cov = sum((a - mx) * (b - my) for a, b in zip(x_vals, y_vals)) / (len(pairs) - 1)
    return cov / (sx * sy)


def main():
    os.makedirs(TABLES_DIR, exist_ok=True)
    rows = []
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            parsed = {}
            for k, v in r.items():
                if v == "" or v is None:
                    parsed[k] = None
                elif k in ["date"]:
                    parsed[k] = v
                elif k in ["year", "month", "day", "day_of_year", "week_of_year", "daily_admitted", "daily_deaths", "target_surge_H7", "target_surge_H14", "target_surge_H21", "target_surge_H28"]:
                    parsed[k] = int(v) if v is not None else None
                else:
                    try:
                        parsed[k] = float(v)
                    except ValueError:
                        parsed[k] = v
            rows.append(parsed)

    print(f"Loaded {len(rows)} records for epidemiological analysis.")

    # 1. Annual Characterization
    by_year = defaultdict(list)
    for r in rows:
        by_year[r["year"]].append(r)

    annual_summary = []
    for y in sorted(by_year.keys()):
        yr_rows = by_year[y]
        total_cases = sum(r["daily_admitted"] for r in yr_rows)
        total_deaths = sum(r["daily_deaths"] for r in yr_rows)
        cfr = (total_deaths / total_cases * 100) if total_cases > 0 else 0.0
        
        peak_case_row = max(yr_rows, key=lambda x: x["daily_admitted"])
        peak_death_row = max(yr_rows, key=lambda x: x["daily_deaths"])
        
        # High transmission days (e.g. daily admitted > 300)
        high_trans_days = sum(1 for r in yr_rows if r["daily_admitted"] >= 300)
        
        # Mean climate during the year
        avg_temp = mean([r["temp_mean_t0"] for r in yr_rows])
        total_precip = sum(r["precipitation_t0"] for r in yr_rows if r["precipitation_t0"] is not None)
        avg_rh = mean([r["humidity_t0"] for r in yr_rows])

        annual_summary.append({
            "year": y,
            "observation_days": len(yr_rows),
            "date_range": f"{yr_rows[0]['date']} to {yr_rows[-1]['date']}",
            "total_admitted": total_cases,
            "total_deaths": total_deaths,
            "case_fatality_rate_pct": round(cfr, 3),
            "peak_daily_admitted": peak_case_row["daily_admitted"],
            "peak_admitted_date": peak_case_row["date"],
            "peak_daily_deaths": peak_death_row["daily_deaths"],
            "peak_death_date": peak_death_row["date"],
            "days_admitted_ge_300": high_trans_days,
            "mean_temp_c": round(avg_temp, 1),
            "total_precip_mm": round(total_precip, 1),
            "mean_humidity_pct": round(avg_rh, 1),
        })

    # Save Table 1: Annual Epidemiological Dynamics
    t1_path = os.path.join(TABLES_DIR, "table1_epidemiological_summary.csv")
    with open(t1_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(annual_summary[0].keys()))
        writer.writeheader()
        writer.writerows(annual_summary)

    print("\n--- Table 1: Annual Epidemiological Summary (2024-2026) ---")
    for s in annual_summary:
        print(f"Year {s['year']}: Cases={s['total_admitted']:,}, Deaths={s['total_deaths']}, CFR={s['case_fatality_rate_pct']}%, Peak={s['peak_daily_admitted']} on {s['peak_admitted_date']}, High-Surge Days={s['days_admitted_ge_300']}")

    # 2. Climate-Dengue Cross-Correlation Analysis
    # Evaluate lags from 0 to 42 days for Mean Temp, Cumulative Precip (14d), and Humidity
    admitted_all = [r["daily_admitted"] for r in rows]
    
    climate_vars = {
        "Mean Temperature": [r["temp_mean_t0"] for r in rows],
        "Diurnal Temp Range (DTR)": [r["dtr_t0"] for r in rows],
        "Relative Humidity": [r["humidity_t0"] for r in rows],
        "14-Day Cumulative Precip": [r["precip_sum_14d"] for r in rows],
        "Breeding Suitability Index": [r["breeding_suitability_idx"] for r in rows],
    }

    ccf_results = []
    for var_name, var_vals in climate_vars.items():
        correlations = {}
        for lag in range(0, 43, 7):
            # lag = k means weather at day (t - lag) compared to cases at day t
            if lag == 0:
                r_val = pearson_r(var_vals, admitted_all)
            else:
                x_sub = var_vals[:-lag]
                y_sub = admitted_all[lag:]
                r_val = pearson_r(x_sub, y_sub)
            correlations[f"lag_{lag}d"] = round(r_val, 3)

        # find best lag
        best_lag = max(correlations.items(), key=lambda x: abs(x[1]))
        entry = {"variable": var_name, "optimal_lag": best_lag[0], "max_correlation_r": best_lag[1]}
        entry.update(correlations)
        ccf_results.append(entry)

    t2_path = os.path.join(TABLES_DIR, "table2_climate_cross_correlations.csv")
    with open(t2_path, "w", newline="", encoding="utf-8") as f:
        fields = ["variable", "optimal_lag", "max_correlation_r"] + [f"lag_{k}d" for k in range(0, 43, 7)]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(ccf_results)

    print("\n--- Table 2: Climate-Dengue Cross-Correlation Across Lags ---")
    for c in ccf_results:
        print(f"{c['variable']}: Peak r={c['max_correlation_r']} at {c['optimal_lag']}")


if __name__ == "__main__":
    main()

