#!/usr/bin/env python3
"""Multi-Horizon Forecasting & Outbreak Surge Early Warning Engine.

Implements:
1. Data Splitting:
   - Train: 2024 season (Jan 1, 2024 to Dec 31, 2024)
   - Calibration/Val: 2025 season (Jan 1, 2025 to Dec 31, 2025)
   - Test (Out-of-Time): 2026 season (Jan 1, 2026 to Sep 1, 2026)
2. Models:
   - Persistence (Naive)
   - Seasonal Naive (7-day periodic)
   - Ridge Regression (L2 regularized linear model)
   - Random Forest Regressor
   - LightGBM Regressor (with early stopping)
3. Multi-Horizon Forecasting:
   - H in {7, 14, 21, 28} days ahead
4. Evaluation:
   - MAE, RMSE, MASE, Pearson r
   - Surge Classification (Threshold >= 386 cases/day): Accuracy, Sensitivity, Specificity, F1, ROC-AUC
5. Conformal Prediction:
   - Calibrated 80% and 95% prediction intervals with empirical coverage assessment
6. Output:
   - tables/table3_forecasting_benchmark.csv
   - tables/table4_surge_early_warning_metrics.csv
   - tables/table5_conformal_coverage.csv
   - data/predictions_test_2026.csv (for plotting Figure 2 & Figure 3)
"""

import csv
import math
import os
import sys

# Add local dependencies directory to sys.path
DEPS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "deps")
if os.path.exists(DEPS_DIR):
    sys.path.insert(0, DEPS_DIR)

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.metrics import mean_absolute_error, mean_squared_error, roc_auc_score, f1_score, recall_score, precision_score
import lightgbm as lgb

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "processed_features.csv")
TABLES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tables")
OUT_PREDS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "predictions_test_2026.csv")


def compute_mase(y_true, y_pred, y_train_naive_diff):
    mae = mean_absolute_error(y_true, y_pred)
    return mae / y_train_naive_diff if y_train_naive_diff > 0 else np.nan


def compute_pearson(y_true, y_pred):
    if len(y_true) < 3 or np.std(y_pred) == 0 or np.std(y_true) == 0:
        return 0.0
    return np.corrcoef(y_true, y_pred)[0, 1]


def main():
    print("Loading engineered features...")
    df = pd.read_csv(DATA_PATH)
    df["date"] = pd.to_datetime(df["date"])
    print(f"Total dataset shape: {df.shape}")

    # Feature columns: exclude target columns and metadata identifiers
    exclude_cols = ["date", "year", "month", "day", "day_of_year", "week_of_year"] + [
        c for c in df.columns if c.startswith("target_")
    ]
    feature_cols = [c for c in df.columns if c not in exclude_cols]
    print(f"Number of predictor features: {len(feature_cols)}")

    # Fill any potential small initial NaNs in rolling features with column medians
    df[feature_cols] = df[feature_cols].fillna(df[feature_cols].median())

    # Temporal split
    train_mask = (df["year"] == 2024)
    val_mask = (df["year"] == 2025)
    test_mask = (df["year"] == 2026)

    train_df = df[train_mask].copy()
    val_df = df[val_mask].copy()
    test_df = df[test_mask].copy()

    # Calculate naive difference for MASE normalization from training set
    train_naive_diff = np.mean(np.abs(np.diff(train_df["daily_admitted"].values)))
    print(f"In-sample naive 1-day MAE: {train_naive_diff:.2f}")

    surge_threshold = 386  # 75th percentile

    horizons = [7, 14, 21, 28]
    models = ["Persistence", "Seasonal_Naive", "Ridge", "RandomForest", "LightGBM"]

    benchmark_rows = []
    surge_rows = []
    conformal_rows = []
    importance_rows = []
    predictions_dict = {"date": test_df["date"].values}

    for H in horizons:
        target_col = f"target_admitted_H{H}"
        
        # Filter valid rows where target is not null
        train_valid = train_df.dropna(subset=[target_col])
        val_valid = val_df.dropna(subset=[target_col])
        test_valid = test_df.dropna(subset=[target_col])

        X_train, y_train = train_valid[feature_cols].values, train_valid[target_col].values
        X_val, y_val = val_valid[feature_cols].values, val_valid[target_col].values
        X_test, y_test = test_valid[feature_cols].values, test_valid[target_col].values

        predictions_dict[f"actual_H{H}"] = y_test

        # Expanding window training: combine 2024 (train) and 2025 (val) to test on 2026
        X_train_full = np.vstack([X_train, X_val])
        y_train_full = np.concatenate([y_train, y_val])

        # Train & Evaluate each model on test set
        horizon_preds = {}

        # 1. Persistence baseline: predict current day's admissions
        horizon_preds["Persistence"] = test_valid["daily_admitted"].values

        # 2. Seasonal Naive baseline: predict admissions from 7 days ago
        horizon_preds["Seasonal_Naive"] = test_valid["lag7_admitted"].values

        # 3. Ridge Regression
        ridge = Ridge(alpha=10.0)
        ridge.fit(X_train_full, y_train_full)
        ridge_pred = np.clip(ridge.predict(X_test), 0, None)
        horizon_preds["Ridge"] = ridge_pred

        # 4. Random Forest Regressor
        rf = RandomForestRegressor(n_estimators=150, max_depth=10, random_state=42, n_jobs=-1)
        rf.fit(X_train_full, y_train_full)
        rf_pred = np.clip(rf.predict(X_test), 0, None)
        horizon_preds["RandomForest"] = rf_pred

        # 5. LightGBM Regressor
        # Train on 2024 to generate out-of-sample calibration residuals on 2025
        lgb_cal = lgb.LGBMRegressor(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=6,
            num_leaves=31,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            verbose=-1,
        )
        lgb_cal.fit(X_train, y_train)

        # Refit on expanding window (2024 + 2025) with optimal hyperparameters for out-of-time test (2026)
        lgb_model = lgb.LGBMRegressor(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=6,
            num_leaves=31,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            verbose=-1,
        )
        lgb_model.fit(X_train_full, y_train_full)
        lgb_pred = np.clip(lgb_model.predict(X_test), 0, None)
        horizon_preds["LightGBM"] = lgb_pred

        # Conformal Prediction on LightGBM:
        # Non-conformity scores on validation set (2025)
        val_lgb_pred = np.clip(lgb_cal.predict(X_val), 0, None)
        val_residuals = np.abs(y_val - val_lgb_pred)
        
        q80 = np.percentile(val_residuals, 80)
        q95 = np.percentile(val_residuals, 95)
        
        lgb_lower_80 = np.clip(lgb_pred - q80, 0, None)
        lgb_upper_80 = lgb_pred + q80
        lgb_lower_95 = np.clip(lgb_pred - q95, 0, None)
        lgb_upper_95 = lgb_pred + q95

        predictions_dict[f"lgb_pred_H{H}"] = lgb_pred
        predictions_dict[f"lgb_lower80_H{H}"] = lgb_lower_80
        predictions_dict[f"lgb_upper80_H{H}"] = lgb_upper_80
        predictions_dict[f"lgb_lower95_H{H}"] = lgb_lower_95
        predictions_dict[f"lgb_upper95_H{H}"] = lgb_upper_95

        # Feature importances
        for feat_name, imp in zip(feature_cols, lgb_model.feature_importances_):
            importance_rows.append({
                "horizon_days": H,
                "feature": feat_name,
                "importance_split": int(imp),
            })

        # Empirical coverage on test set (2026)
        cov_80 = np.mean((y_test >= lgb_lower_80) & (y_test <= lgb_upper_80)) * 100
        cov_95 = np.mean((y_test >= lgb_lower_95) & (y_test <= lgb_upper_95)) * 100
        conformal_rows.append({
            "horizon_days": H,
            "nominal_80_target": 80.0,
            "empirical_coverage_80_pct": round(cov_80, 2),
            "margin_80_cases": round(q80, 1),
            "nominal_95_target": 95.0,
            "empirical_coverage_95_pct": round(cov_95, 2),
            "margin_95_cases": round(q95, 1),
        })

        # Calculate metrics for all models
        for m_name in models:
            preds = horizon_preds[m_name]
            mae = mean_absolute_error(y_test, preds)
            rmse = np.sqrt(mean_squared_error(y_test, preds))
            mase = compute_mase(y_test, preds, train_naive_diff)
            pearson = compute_pearson(y_test, preds)

            benchmark_rows.append({
                "horizon_days": H,
                "model": m_name,
                "mae": round(mae, 2),
                "rmse": round(rmse, 2),
                "mase": round(mase, 3),
                "pearson_r": round(pearson, 3),
            })

            # Surge Early Warning Classification metrics
            y_test_surge = (y_test >= surge_threshold).astype(int)
            preds_surge = (preds >= surge_threshold).astype(int)
            
            acc = np.mean(y_test_surge == preds_surge)
            rec = recall_score(y_test_surge, preds_surge, zero_division=0)
            spec = np.mean(preds_surge[y_test_surge == 0] == 0) if np.sum(y_test_surge == 0) > 0 else np.nan
            prec = precision_score(y_test_surge, preds_surge, zero_division=0)
            f1 = f1_score(y_test_surge, preds_surge, zero_division=0)
            try:
                auc = roc_auc_score(y_test_surge, preds)
            except ValueError:
                auc = np.nan

            surge_rows.append({
                "horizon_days": H,
                "model": m_name,
                "accuracy": round(acc, 3),
                "sensitivity_recall": round(rec, 3),
                "specificity": round(spec, 3),
                "precision": round(prec, 3),
                "f1_score": round(f1, 3),
                "roc_auc": round(auc, 3),
            })

    # Save Tables
    os.makedirs(TABLES_DIR, exist_ok=True)
    pd.DataFrame(benchmark_rows).to_csv(os.path.join(TABLES_DIR, "table3_forecasting_benchmark.csv"), index=False)
    pd.DataFrame(surge_rows).to_csv(os.path.join(TABLES_DIR, "table4_surge_early_warning_metrics.csv"), index=False)
    pd.DataFrame(conformal_rows).to_csv(os.path.join(TABLES_DIR, "table5_conformal_coverage.csv"), index=False)
    pd.DataFrame(importance_rows).to_csv(os.path.join(TABLES_DIR, "table6_feature_importances.csv"), index=False)
    
    # Save predictions dataframe for plotting
    pred_len = len(conformal_rows)
    # Save predictions where all horizons match length of test_valid for H28
    min_len = min(len(v) for k, v in predictions_dict.items() if k != "date")
    trimmed_preds = {"date": test_df["date"].values[:min_len]}
    for k, v in predictions_dict.items():
        if k != "date":
            trimmed_preds[k] = v[:min_len]
    pd.DataFrame(trimmed_preds).to_csv(OUT_PREDS_PATH, index=False)

    print("\n--- Summary: Table 3 Multi-Horizon Benchmark (Out-of-Time 2026 Season) ---")
    b_df = pd.DataFrame(benchmark_rows)
    for H in horizons:
        print(f"\nHorizon: H+{H} Days:")
        sub = b_df[b_df["horizon_days"] == H]
        for _, r in sub.iterrows():
            print(f"  {r['model']:<15} MAE: {r['mae']:<8} RMSE: {r['rmse']:<8} MASE: {r['mase']:<8} Pearson r: {r['pearson_r']}")

    print("\n--- Summary: Table 4 Surge Early Warning Utility (Threshold >= 386 cases/day) ---")
    s_df = pd.DataFrame(surge_rows)
    for H in [14, 28]:
        print(f"\nHorizon: H+{H} Days:")
        sub = s_df[s_df["horizon_days"] == H]
        for _, r in sub.iterrows():
            print(f"  {r['model']:<15} ROC-AUC: {r['roc_auc']:<8} Sensitivity: {r['sensitivity_recall']:<8} F1: {r['f1_score']}")

    print("\n--- Summary: Table 5 Conformal Prediction Coverage (Out-of-Time 2026) ---")
    c_df = pd.DataFrame(conformal_rows)
    print(c_df.to_string(index=False))


if __name__ == "__main__":
    main()

