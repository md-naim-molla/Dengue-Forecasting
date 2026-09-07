# Structural Transition of Dengue Transmission and Multi-Horizon Outbreak Forecasting in Bangladesh (2024–2026)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Manuscript: PLOS NTD](https://img.shields.io/badge/Target-PLOS%20NTD-green.svg)](https://journals.plos.org/plosntds/)

A biometeorological machine learning surveillance study investigating the post-2023 epidemiological regime shift of dengue in Bangladesh and delivering an operational multi-horizon early warning system ($H \in \{7, 14, 21, 28\}$ days ahead) with distribution-free conformal uncertainty bounds.

---

## 🔬 Key Epidemiological & Methodological Findings

1. **The Post-2023 Seasonal Shift:**
   * Analysis of 975 consecutive days of official DGHS national surveillance data (2024–2026; 241,236 admissions, 1,090 deaths) proves that dengue transmission has structurally transitioned: peak hospitalizations in 2024 and 2025 occurred in **mid-November** (Nov 17, 2024: 1,389 cases/day; Nov 9, 2025: 1,195 cases/day), contrasting sharply with historical pre-2023 August/September peaks.
2. **The 42-Day (6-Week) Climate Lag Synchronization:**
   * Cross-correlation function (CCF) analysis against ERA5 meteorological reanalysis revealed an exact 42-day synchronization between cumulative 14-day rainfall ($r = +0.634$), relative humidity ($r = +0.544$), reduced diurnal temperature range ($r = -0.606$), and nationwide hospitalization surges, directly mirroring the multi-stage arboviral transmission cycle.
3. **Multi-Horizon Early Warning Engine ($H \in \{7, 14, 21, 28\}$ Days):**
   * LightGBM gradient-boosted decision trees achieved superior forecasting accuracy across all operational horizons ($\text{MASE} < 1.0$; MAE: 35.86–76.99 cases/day; Pearson $r: 0.952\text{--}0.971$), outperforming Random Forest and Persistence baselines.
4. **Zero False-Alarm Epidemic Crest Detection:**
   * At 3- and 4-week lead times, early warning classification for epidemic surges ($\ge 386$ cases/day) delivered **100.0% specificity and 100.0% precision (zero false alarms, $\text{FP} = 0$)**, detecting over 51% of major surge crests well in advance of peak hospital saturation.
5. **Calibrated Inductive Conformal Prediction:**
   * Distribution-free finite-sample conformal prediction bounds provide calibrated 80% (85.2%–93.3% empirical coverage) and 95% (91.7%–99.2% empirical coverage) uncertainty envelopes across all horizons on unseen 2026 test data.

---

## 📁 Repository Structure

```
.
├── Dengue_Manuscript_PLOS_NTD.tex     # Full LaTeX manuscript (PLOS NTD format)
├── Dengue_Manuscript_PLOS_NTD.docx    # Full Word manuscript with native OMML equations
├── manuscript_latex.pdf               # Compiled publication-ready PDF
├── references.bib                     # 25 BibTeX citations
├── Dengue_LaTeX_Overleaf_Package.zip  # Drag-and-drop Overleaf bundle
├── requirements.txt                   # Python package dependencies
├── .gitignore                         # Git exclusion rules
│
├── data/                              # Surveillance and meteorological datasets
│   ├── dengue_ml_dataset.csv          # DGHS daily surveillance (Jan 2024 – Sep 2026)
│   ├── meteorological_data.csv        # Open-Meteo ERA5 reanalysis (Nov 2023 – Sep 2026)
│   ├── processed_features.csv         # Engineered biometeorological feature matrix
│   └── predictions_test_2026.csv      # Out-of-time multi-horizon test predictions
│
├── figures/                           # Publication figures (300 DPI)
│   ├── figure1_epidemiological_dynamics.png
│   ├── figure2_climate_42d_lag_coupling.png
│   └── figure3_multi_horizon_2026_forecasts.png
│
├── tables/                            # Benchmark evaluation tables (Tables 1–6)
│   ├── table1_epidemiological_summary.csv
│   ├── table2_climate_cross_correlations.csv
│   ├── table3_forecasting_benchmark.csv
│   ├── table4_surge_early_warning_metrics.csv
│   ├── table5_conformal_coverage.csv
│   └── table6_feature_importances.csv
│
├── src/                               # Modeling and analysis codebase
│   ├── eda.py                         # Exploratory data analysis & lag CCF
│   ├── feature_engineering.py         # Biometeorological lag pipeline
│   ├── generate_figures.py            # High-resolution figure generator
│   └── models/
│       └── train_and_evaluate.py      # Multi-horizon benchmarking & conformal calibration
│
├── scripts/                           # Auxiliary data & document builders
│   ├── build_docx.py                  # Generates Dengue_Manuscript_PLOS_NTD.docx
│   ├── build_tex.py                   # Generates Dengue_Manuscript_PLOS_NTD.tex
│   └── fetch_weather.py               # Ingests Open-Meteo ERA5 reanalysis
│
├── build_dataset.py                   # DGHS HEOC dashboard automated scraper
└── scrapper.py                        # Diagnostic scraper for dashboard tables
```

---

## 🚀 Quick Start

### 1. Installation
Clone the repository and install the dependencies:
```bash
git clone https://github.com/your-username/dengue-bangladesh-early-warning.git
cd dengue-bangladesh-early-warning
pip install -r requirements.txt
```

### 2. Run the Feature Engineering Pipeline
```bash
python3 src/feature_engineering.py
```

### 3. Train & Evaluate Multi-Horizon Models
```bash
python3 src/models/train_and_evaluate.py
```

### 4. Regenerate Figures and Tables
```bash
python3 src/generate_figures.py
```

### 5. Rebuild Manuscripts
* **Generate Word Manuscript:**
  ```bash
  python3 scripts/build_docx.py
  ```
* **Generate LaTeX Manuscript:**
  ```bash
  python3 scripts/build_tex.py
  ```

---

## 📄 Manuscript & Overleaf

* **Overleaf Submission:** Upload `Dengue_LaTeX_Overleaf_Package.zip` directly to [Overleaf](https://www.overleaf.com) via **New Project $\rightarrow$ Upload Project** and click **Recompile**.
* **Pre-compiled PDF:** View [`manuscript_latex.pdf`](manuscript_latex.pdf) directly in the repository.

---

## 📜 License & Citation

This project is licensed under the MIT License. If you use this dataset or code in your research, please cite:

```bibtex
@article{rahman2026dengue,
  title={Structural Transition of Dengue Transmission and Multi-Horizon Outbreak Forecasting in Bangladesh (2024--2026): A Biometeorological Machine Learning Surveillance Study},
  author={Rahman, Md. Naimur and others},
  journal={PLOS Neglected Tropical Diseases},
  year={2026}
}
```

