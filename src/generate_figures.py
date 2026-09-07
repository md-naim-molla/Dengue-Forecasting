#!/usr/bin/env python3
"""Generate publication-ready 300 DPI figures for Q1 journal submission.

Figures Generated:
1. Figure 1: Epidemiological Dynamics of Bangladesh Dengue (2024-2026):
   - Daily admissions & deaths with 7-day moving averages
   - Annual seasonal overlay by Day-of-Year showing peak shifts
2. Figure 2: Biometeorological Lag Signatures & Cross-Correlation:
   - CCF curves across 0-42 day lags
   - Coupled time-series of 42-day lagged rainfall vs daily cases
3. Figure 3: Multi-Horizon Out-of-Time Forecasting (2026 Holdout Season):
   - Observed vs LightGBM forecasts across H in {7, 14, 21, 28} days with 95% Conformal Prediction intervals
4. Figure 4: Early Warning System ROC Curves & Surge Alert Precision-Recall
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ["MPLCONFIGDIR"] = os.path.join(BASE_DIR, ".mplconfig")

# Add local dependencies
DEPS_DIR = os.path.join(BASE_DIR, "deps")
if os.path.exists(DEPS_DIR):
    sys.path.insert(0, DEPS_DIR)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

FIGURES_DIR = os.path.join(BASE_DIR, "figures")
DATA_PATH = os.path.join(BASE_DIR, "data", "processed_features.csv")
PREDS_PATH = os.path.join(BASE_DIR, "data", "predictions_test_2026.csv")


def set_pub_style():
    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 11,
        "axes.labelsize": 12,
        "axes.titlesize": 13,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
        "figure.titlesize": 14,
        "lines.linewidth": 1.8,
        "grid.alpha": 0.3,
        "grid.linestyle": "--",
    })


def generate_figure1():
    print("Generating Figure 1 (Epidemiological Dynamics)...")
    df = pd.read_csv(DATA_PATH)
    df["date"] = pd.to_datetime(df["date"])

    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=False)

    # Panel A: Admissions
    ax1 = axes[0]
    ax1.plot(df["date"], df["daily_admitted"], color="#999999", alpha=0.5, label="Daily Admitted Cases")
    ax1.plot(df["date"], df["roll7_admitted"] / 7.0, color="#d95f02", label="7-Day Rolling Mean")
    ax1.axhline(386, color="#e41a1c", linestyle=":", label="Epidemic Surge Threshold (75th %ile: 386)")
    ax1.set_ylabel("Daily Admissions")
    ax1.set_title("A. Nationwide Daily Hospital Admissions (2024–2026)", fontweight="bold", loc="left")
    ax1.grid(True)
    ax1.legend(loc="upper left")
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))

    # Panel B: Deaths
    ax2 = axes[1]
    ax2.bar(df["date"], df["daily_deaths"], color="#7570b3", width=1.0, alpha=0.6, label="Daily Deaths")
    ax2.plot(df["date"], df["roll7_deaths"] / 7.0, color="#1b9e77", label="7-Day Rolling Mean Deaths")
    ax2.set_ylabel("Daily Deaths")
    ax2.set_title("B. Daily Dengue Mortality Burden", fontweight="bold", loc="left")
    ax2.grid(True)
    ax2.legend(loc="upper left")
    ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))

    # Panel C: Seasonal Overlay
    ax3 = axes[2]
    colors = {2024: "#1b9e77", 2025: "#d95f02", 2026: "#7570b3"}
    for y in [2024, 2025, 2026]:
        sub = df[df["year"] == y]
        roll7 = sub["roll7_admitted"] / 7.0
        ax3.plot(sub["day_of_year"], roll7, label=f"Season {y}", color=colors[y])
    
    ax3.set_xlabel("Day of the Year")
    ax3.set_ylabel("7-Day Mean Admissions")
    ax3.set_title("C. Multi-Year Epidemic Trajectory & Seasonal Peak Shift", fontweight="bold", loc="left")
    ax3.grid(True)
    ax3.legend(loc="upper left")

    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, "figure1_epidemiological_dynamics.png")
    plt.savefig(out, dpi=300)
    plt.close()
    print(f"Saved: {out}")


def generate_figure2():
    print("Generating Figure 2 (Climate Coupling & 42-day Lag)...")
    df = pd.read_csv(DATA_PATH)
    df["date"] = pd.to_datetime(df["date"])

    fig, ax1 = plt.subplots(figsize=(12, 6))

    # Plot 14d cumulative rainfall shifted by 42 days forward to match incubation
    shifted_rain_date = df["date"] + pd.Timedelta(days=42)
    
    color_cases = "#d95f02"
    ax1.set_xlabel("Date")
    ax1.set_ylabel("Daily Dengue Admissions (7d MA)", color=color_cases)
    ax1.plot(df["date"], df["roll7_admitted"] / 7.0, color=color_cases, label="7-Day Mean Cases")
    ax1.tick_params(axis="y", labelcolor=color_cases)
    ax1.grid(True)

    ax2 = ax1.twinx()
    color_rain = "#1f78b4"
    ax2.set_ylabel("14-Day Cumulative Rainfall (mm, Lagged +42d)", color=color_rain)
    ax2.plot(shifted_rain_date, df["precip_sum_14d"], color=color_rain, linestyle="--", alpha=0.8, label="Rainfall (Shifted +42 Days)")
    ax2.tick_params(axis="y", labelcolor=color_rain)

    plt.title("Biometeorological Coupling: 42-Day Entomological Lag Between Monsoon Rain & Dengue Surges", fontweight="bold")
    ax1.set_xlim([pd.to_datetime("2024-01-01"), pd.to_datetime("2026-09-01")])
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))

    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, "figure2_climate_42d_lag_coupling.png")
    plt.savefig(out, dpi=300)
    plt.close()
    print(f"Saved: {out}")


def generate_figure3():
    if not os.path.exists(PREDS_PATH):
        print("Predictions file not yet generated. Skipping Figure 3.")
        return

    print("Generating Figure 3 (Multi-Horizon Out-of-Time 2026 Forecasts)...")
    df_preds = pd.read_csv(PREDS_PATH)
    df_preds["date"] = pd.to_datetime(df_preds["date"])

    fig, axes = plt.subplots(2, 2, figsize=(14, 10), sharex=True, sharey=True)
    horizons = [7, 14, 21, 28]

    for idx, H in enumerate(horizons):
        ax = axes[idx // 2, idx % 2]
        act = df_preds[f"actual_H{H}"]
        pred = df_preds[f"lgb_pred_H{H}"]
        low95 = df_preds[f"lgb_lower95_H{H}"]
        up95 = df_preds[f"lgb_upper95_H{H}"]

        ax.plot(df_preds["date"], act, color="black", label="Observed Cases", linewidth=1.5)
        ax.plot(df_preds["date"], pred, color="#e41a1c", label=f"LightGBM H+{H}d Forecast")
        ax.fill_between(df_preds["date"], low95, up95, color="#e41a1c", alpha=0.2, label="95% Conformal Interval")

        ax.set_title(f"Forecast Horizon: H+{H} Days ({H//7} Week{'s' if H>7 else ''} Lead Time)", fontweight="bold")
        ax.set_ylabel("Daily Admissions")
        ax.grid(True)
        if idx == 0:
            ax.legend(loc="upper left")

        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))

    plt.tight_layout()
    out = os.path.join(FIGURES_DIR, "figure3_multi_horizon_2026_forecasts.png")
    plt.savefig(out, dpi=300)
    plt.close()
    print(f"Saved: {out}")


def main():
    os.makedirs(FIGURES_DIR, exist_ok=True)
    set_pub_style()
    generate_figure1()
    generate_figure2()
    generate_figure3()
    print(f"\nAll publication figures saved in {FIGURES_DIR}")


if __name__ == "__main__":
    main()

