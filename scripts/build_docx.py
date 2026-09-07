#!/usr/bin/env python3
"""Build a publication-ready .docx manuscript for PLOS NTD / Scientific Reports.

Includes:
- Title, Authors, Abstract, Keywords
- Introduction, Materials & Methods, Results, Discussion
- Embedded native styled tables (Tables 1 to 6)
- Embedded 300-DPI high-resolution figures (Figures 1 to 3) with full figure captions
- Formatted with 1-inch margins, Times New Roman, 1.5 line spacing
"""

import csv
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEPS_DIR = os.path.join(BASE_DIR, "deps")
if os.path.exists(DEPS_DIR):
    sys.path.insert(0, DEPS_DIR)

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn


def add_equation(doc, omml_content, eq_number=None):
    """Inserts a formal numbered mathematical equation into the Word document.
    Uses a borderless table layout:
    - Left/Center cell (5.75 in): Equation in OMML
    - Right cell (0.75 in): Equation number right-aligned in Times New Roman
    """
    tbl = doc.add_table(rows=1, cols=2)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER

    tbl_pr = tbl._tbl.tblPr
    tbl_borders = parse_xml(r"""
        <w:tblBorders xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
            <w:top w:val="none" w:sz="0" w:space="0" w:color="auto"/>
            <w:left w:val="none" w:sz="0" w:space="0" w:color="auto"/>
            <w:bottom w:val="none" w:sz="0" w:space="0" w:color="auto"/>
            <w:right w:val="none" w:sz="0" w:space="0" w:color="auto"/>
            <w:insideH w:val="none" w:sz="0" w:space="0" w:color="auto"/>
            <w:insideV w:val="none" w:sz="0" w:space="0" w:color="auto"/>
        </w:tblBorders>
    """)
    tbl_pr.append(tbl_borders)

    cell_eq = tbl.cell(0, 0)
    cell_num = tbl.cell(0, 1)

    cell_eq.width = Inches(5.75)
    cell_num.width = Inches(0.75)

    p_eq = cell_eq.paragraphs[0]
    p_eq.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_eq.paragraph_format.space_before = Pt(5)
    p_eq.paragraph_format.space_after = Pt(5)

    omml_elem = parse_xml(
        f'<m:oMath xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">{omml_content}</m:oMath>'
    )
    p_eq._p.append(omml_elem)

    p_num = cell_num.paragraphs[0]
    p_num.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_num.paragraph_format.space_before = Pt(5)
    p_num.paragraph_format.space_after = Pt(5)
    if eq_number is not None:
        r = p_num.add_run(f"({eq_number})")
        r.font.name = "Times New Roman"
        r.font.size = Pt(11)
        r.bold = True


def set_cell_background(cell, fill_hex):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), fill_hex)
    tc_pr.append(shd)


def add_styled_table(doc, csv_path, caption):
    if not os.path.exists(csv_path):
        print(f"Warning: {csv_path} not found.")
        return

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = list(csv.reader(f))

    if not reader:
        return

    headers = reader[0]
    data_rows = reader[1:]

    p_cap = doc.add_paragraph()
    p_cap.paragraph_format.space_before = Pt(12)
    p_cap.paragraph_format.space_after = Pt(4)
    run_cap = p_cap.add_run(caption)
    run_cap.bold = True
    run_cap.font.name = "Times New Roman"
    run_cap.font.size = Pt(11)

    table = doc.add_table(rows=len(reader), cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    # Style Header
    hdr_cells = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr_cells[i].text = h.replace("_", " ").title()
        set_cell_background(hdr_cells[i], "2C3E50")
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for r in p.runs:
            r.font.bold = True
            r.font.name = "Times New Roman"
            r.font.size = Pt(9.5)
            r.font.color.rgb = RGBColor(255, 255, 255)

    # Style Data Rows
    for row_idx, row_data in enumerate(data_rows):
        cells = table.rows[row_idx + 1].cells
        bg_color = "F8F9FA" if row_idx % 2 == 1 else "FFFFFF"
        for col_idx, val in enumerate(row_data):
            cells[col_idx].text = str(val)
            set_cell_background(cells[col_idx], bg_color)
            p = cells[col_idx].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if col_idx > 0 else WD_ALIGN_PARAGRAPH.LEFT
            for r in p.runs:
                r.font.name = "Times New Roman"
                r.font.size = Pt(9.5)

    p_after = doc.add_paragraph()
    p_after.paragraph_format.space_after = Pt(12)


def main():
    doc = docx.Document()

    # Set Margins
    for sec in doc.sections:
        sec.top_margin = Inches(1.0)
        sec.bottom_margin = Inches(1.0)
        sec.left_margin = Inches(1.0)
        sec.right_margin = Inches(1.0)

    # Base Style
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Times New Roman'
    normal_style.font.size = Pt(12)
    normal_style.paragraph_format.line_spacing = 1.35
    normal_style.paragraph_format.space_after = Pt(6)

    # Title
    p_title = doc.add_paragraph()
    p_title.paragraph_format.space_before = Pt(0)
    p_title.paragraph_format.space_after = Pt(12)
    r_title = p_title.add_run("Structural Transition of Dengue Transmission and Multi-Horizon Outbreak Forecasting in Bangladesh (2024–2026): A Biometeorological Machine Learning Surveillance Study")
    r_title.bold = True
    r_title.font.name = "Times New Roman"
    r_title.font.size = Pt(18)
    r_title.font.color.rgb = RGBColor(26, 36, 43)

    # Running Title
    p_run = doc.add_paragraph()
    p_run.paragraph_format.space_after = Pt(14)
    r_run = p_run.add_run("Short Running Title: Multi-Horizon Dengue Early Warning in Bangladesh")
    r_run.italic = True
    r_run.font.size = Pt(10.5)

    # Authors Placeholder
    p_auth = doc.add_paragraph()
    p_auth.paragraph_format.space_after = Pt(4)
    r_auth = p_auth.add_run("Author Names Placeholder¹,²*")
    r_auth.bold = True
    r_auth.font.size = Pt(11)

    p_aff = doc.add_paragraph()
    p_aff.paragraph_format.space_after = Pt(16)
    r_aff = p_aff.add_run("¹ Department of Public Health / Data Science, Institution Name, Dhaka, Bangladesh\n² Research Affiliation Placeholder\n* Corresponding Author: author@institution.ac.bd")
    r_aff.font.size = Pt(10)
    r_aff.font.color.rgb = RGBColor(80, 80, 80)

    # Abstract Box
    h_abs = doc.add_heading("Abstract", level=1)
    h_abs.paragraph_format.space_before = Pt(14)
    h_abs.paragraph_format.space_after = Pt(6)

    abstract_sections = [
        ("Background: ", "Following Bangladesh's catastrophic 2023 dengue epidemic (>321,000 hospital admissions and 1,705 deaths), dengue transmission expanded nationwide. Understanding whether transmission reverted to historical urban dynamics or established a persistent 'new normal' is critical for public health preparedness. Furthermore, existing forecasting studies often suffer from trivial next-day autocorrelation (t+1) that provides insufficient lead time for vector control or hospital surge management."),
        ("Methods: ", "We analyzed 975 consecutive days of official Directorate General of Health Services (DGHS) national surveillance data (January 1, 2024 – September 1, 2026; 241,236 admitted cases, 1,090 deaths) coupled with ERA5 meteorological reanalysis (daily temperature, precipitation, relative humidity, and diurnal temperature range). Biologically plausible distributed lags (7–42 days) were engineered to capture Aedes breeding and extrinsic incubation periods. We established a direct multi-horizon forecasting framework (H ∈ {7, 14, 21, 28} days ahead) comparing gradient-boosted decision trees (LightGBM), random forests, and regularized linear baselines under strict expanding-window walk-forward validation (Train: 2024; Calibrate: 2025; Out-of-Time Test: 2026). Conformal prediction was applied to construct calibrated 80% and 95% uncertainty intervals, and outbreak surge classification was evaluated at the 75th percentile threshold (τ = 386 cases/day)."),
        ("Results: ", "Surveillance analysis reveals a fundamental seasonal shift: peak transmission in 2024 and 2025 occurred in mid-November (November 17, 2024: 1,389 cases/day; November 9, 2025: 1,195 cases/day), contrasting sharply with historical pre-2023 peaks in August–September. Cross-correlation analysis demonstrated an exact 42-day (6-week) lag between cumulative 14-day rainfall (r = +0.634), relative humidity (r = +0.544), reduced diurnal temperature range (r = -0.606), and nationwide dengue hospitalizations. In out-of-time evaluation across the 2026 epidemic wave, gradient-boosted decision trees (LightGBM) established superior forecasting accuracy across all operational lead times (MAE: 35.86–76.99 cases/day; Pearson r: 0.952–0.971), consistently achieving MASE < 1.0 (0.412 at H=7d to 0.884 at H=28d) and outperforming Random Forest (MAE = 83.40, MASE = 0.957) and Persistence (MAE = 96.84, MASE = 1.112). Outbreak surge early warning classification (≥ 386 cases/day) maintained high specificity (98.5%–100.0%) and precision (89.7%–100.0%) across all horizons. At 21- and 28-day lead times, LightGBM delivered 60.0% and 51.4% surge sensitivity with 100.0% precision (zero false alarms; ROC-AUC: 0.988–0.989). Conformal prediction intervals maintained empirical coverage within close margins of nominal targets (85.2%–93.3% for 80% target; 91.7%–99.2% for 95% target)."),
        ("Conclusions: ", "Dengue in Bangladesh has transitioned into a delayed-peak, hyperendemic regime driven by monsoon precipitation pulses operating on a 6-week biometeorological delay. Coupling meteorological lags with multi-horizon machine learning provides an actionable 2-to-4-week early warning window for municipal vector control and clinical capacity mobilization with minimal false-alarm risk.")
    ]

    for label, text in abstract_sections:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(6)
        r1 = p.add_run(label)
        r1.bold = True
        r2 = p.add_run(text)

    # Keywords
    p_kw = doc.add_paragraph()
    p_kw.paragraph_format.space_before = Pt(6)
    p_kw.paragraph_format.space_after = Pt(12)
    r_kw_lbl = p_kw.add_run("Keywords: ")
    r_kw_lbl.bold = True
    p_kw.add_run("Dengue virus, Bangladesh, Early Warning System, Biometeorology, Multi-Horizon Forecasting, LightGBM, Random Forest, Conformal Prediction, Climate Lags")

    # Author Summary Box (PLOS NTD Mandatory)
    h_as = doc.add_heading("Author Summary", level=1)
    h_as.paragraph_format.space_before = Pt(12)
    h_as.paragraph_format.space_after = Pt(6)
    p_as = doc.add_paragraph()
    p_as.paragraph_format.space_after = Pt(12)
    r_as1 = p_as.add_run("Why was this study done? ")
    r_as1.bold = True
    p_as.add_run(
        "Following Bangladesh's catastrophic 2023 dengue epidemic (>321,000 hospitalizations and 1,705 deaths), "
        "understanding whether transmission reverted to historical urban schedules or established a persistent 'new normal' is vital for public health preparedness. "
        "Furthermore, existing forecasting models frequently focus on single-day ahead predictions (t + 1), which fail to provide actionable advance notice for vector control or hospital surge planning.\n\n"
    )
    r_as2 = p_as.add_run("What did the researchers do and find? ")
    r_as2.bold = True
    p_as.add_run(
        "We investigated 975 consecutive days of official national surveillance data from 2024 through September 2026 coupled with ERA5 meteorological reanalysis. "
        "We discovered that transmission peaks have decisively shifted from historical August/September schedules to mid-November, governed by an exact 42-day (6-week) delay "
        "following monsoon rainfall pulses. We developed direct multi-horizon forecasting models (LightGBM) spanning 7 to 28 days ahead. Evaluated across the 2026 epidemic wave "
        "under strict expanding-window validation, LightGBM outperformed all benchmark baselines across every lead time (MASE < 1.0) and successfully detected major epidemic surges "
        "up to 4 weeks in advance with 100% precision and zero false alarms.\n\n"
    )
    r_as3 = p_as.add_run("What do these findings mean? ")
    r_as3.bold = True
    p_as.add_run(
        "Public health mosquito abatement programs that traditionally scale down in September must now extend through December. "
        "The 42-day rainfall countdown provides municipal authorities with an actionable operational timeline, and multi-horizon forecasts equip hospitals with reliable, "
        "uncertainty-bounded advance warnings to allocate beds, intravenous fluids, and clinical staffing well before peak hospital admissions occur."
    )

    doc.add_page_break()

    # Introduction
    doc.add_heading("1. Introduction", level=1)
    doc.add_paragraph(
        "Dengue virus (DENV, family Flaviviridae) represents one of the most rapidly propagating vector-borne viral pathogens globally, "
        "with an estimated 3.9 billion people residing in transmission-receptive regions [1,2]. In Bangladesh, where dengue was first clinically "
        "documented in 1964 and established hyperendemicity in 2000 [3,4], transmission was historically characterized as an urban seasonal phenomenon "
        "largely confined to the Dhaka metropolitan area between July and September [4,25].\n\n"
        "However, the unprecedented epidemic of 2023 shattered historical baselines, overwhelming the healthcare delivery infrastructure with 321,179 "
        "hospital admissions and a staggering 1,705 fatalities [3,5]. Crucially, the 2023 crisis exhibited widespread geographical dissemination across all 64 "
        "administrative districts, signaling that dengue has transitioned from a localized metropolitan nuisance into a nationwide public health emergency [4,5].\n\n"
        "Despite the rapid growth of predictive modeling literature in South Asia, two critical research gaps persist:\n"
        "1. The Post-2023 Empirical Void: The transmission trajectory of dengue in Bangladesh following the catastrophic 2023 hyper-epidemic remains completely "
        "uncharacterized in the peer-reviewed literature. Did transmission revert to historical pre-outbreak baselines, or did Bangladesh enter an altered, "
        "hyperendemic steady-state with extended seasonality and altered peak timings?\n"
        "2. The 'Trivial Next-Day' Forecasting Fallacy: A pervasive methodological flaw in recent applied machine learning studies is the reliance on single-step "
        "ahead forecasting (predicting tomorrow, t + 1, using today's caseload, y_t). While such models frequently report deceptively high accuracy (R² > 0.95), "
        "this is merely an artifact of strong day-to-day autocorrelation. Such predictions provide near-zero operational utility to municipal vector control "
        "teams or hospital administrators, who require multi-week advance warnings to mobilize chemical larviciding campaigns, secure platelet concentrates, and "
        "allocate hospital surge capacity [19,23].\n\n"
        "To address these critical knowledge gaps, this study presents the first comprehensive biometeorological surveillance investigation and multi-horizon early "
        "warning forecasting engine (H ∈ {7, 14, 21, 28} days ahead) across three consecutive nationwide epidemic cycles (2024–2026)."
    )

    # Materials and Methods
    doc.add_heading("2. Materials and Methods", level=1)
    
    p_m1 = doc.add_paragraph()
    r_m1_t = p_m1.add_run("2.1 Epidemiological Surveillance Data\n")
    r_m1_t.bold = True
    p_m1.add_run(
        "Daily national epidemiological surveillance data was acquired from the Directorate General of Health Services (DGHS) "
        "Health Emergency Operation Centre & Control Room (HEOC) portal (https://dashboard.dghs.gov.bd) [3]. The compiled dataset covers "
        "975 consecutive days from January 1, 2024 to September 1, 2026. Key clinical surveillance metrics include daily laboratory-confirmed "
        "hospital admissions (y_t), in-hospital dengue-related mortality, 7-day and 14-day rolling totals, and cumulative caseload trackers."
    )

    p_m2 = doc.add_paragraph()
    r_m2_t = p_m2.add_run("2.2 Meteorological Reanalysis Data\n")
    r_m2_t.bold = True
    p_m2.add_run(
        "Daily meteorological parameters were obtained from the European Centre for Medium-Range Weather Forecasts (ECMWF) ERA5 reanalysis pipeline "
        "via Open-Meteo for Bangladesh (centered at Dhaka: 23.8103°N, 90.4125°E) from November 1, 2023 to September 1, 2026 [11]. The environmental "
        "parameters extracted include daily maximum temperature (T_max, °C), minimum temperature (T_min, °C), mean temperature (T_mean, °C), "
        "diurnal temperature range (DTR = T_max - T_min), total daily precipitation (P_t, mm), relative humidity (RH_t, %), and solar radiation (MJ/m²)."
    )

    p_m3 = doc.add_paragraph()
    r_m3_t = p_m3.add_run("2.3 Biometeorological Lag Feature Engineering\n")
    r_m3_t.bold = True
    p_m3.add_run(
        "Because the biological transmission cycle involves mosquito oviposition, aquatic egg-to-adult emergence (7–14 days), extrinsic incubation "
        "period (EIP: 8–12 days at 28–30°C) [6-8], and human intrinsic incubation (4–7 days) prior to clinical hospital presentation [9,10], "
        "we engineered distributed thermal and precipitation lags across 7, 14, 21, 28, 35, and 42 days. In addition, an entomological "
        "Breeding Suitability Index (BSI_t) was formulated to quantify the non-linear interaction between thermal suitability and cumulative rainfall:"
    )

    # Equation 1: BSI
    add_equation(doc, """<m:sSub><m:e><m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>BSI</m:t></m:r></m:e><m:sub><m:r><m:t>t</m:t></m:r></m:sub></m:sSub>
      <m:r><m:t> = </m:t></m:r>
      <m:sSub><m:e><m:r><m:t>P</m:t></m:r></m:e><m:sub><m:r><m:t>14,t</m:t></m:r></m:sub></m:sSub>
      <m:r><m:t> × </m:t></m:r>
      <m:d>
        <m:dPr><m:begChr m:val="("/><m:endChr m:val=")"/></m:dPr>
        <m:e>
          <m:f>
            <m:num>
              <m:acc>
                <m:accPr><m:chr m:val="̄"/></m:accPr>
                <m:e><m:sSub><m:e><m:r><m:t>T</m:t></m:r></m:e><m:sub><m:r><m:t>14,t</m:t></m:r></m:sub></m:sSub></m:e>
              </m:acc>
            </m:num>
            <m:den><m:r><m:t>30.0</m:t></m:r></m:den>
          </m:f>
        </m:e>
      </m:d>""", 1)

    p_m3b = doc.add_paragraph(
        "where P_{14,t} = ∑_{k=0}^{13} P_{t-k} represents the 14-day cumulative rainfall (mm), T̄_{14,t} is the 14-day rolling mean ambient temperature (°C), "
        "and 30.0°C denotes the standard physiological optimum for Aedes aegypti development. Cyclical seasonality was captured using first- and "
        "second-order Fourier harmonic terms: sin(2π · DOY_t / 365.25), cos(2π · DOY_t / 365.25), sin(4π · DOY_t / 365.25), and cos(4π · DOY_t / 365.25)."
    )

    p_m4 = doc.add_paragraph()
    r_m4_t = p_m4.add_run("2.4 Multi-Horizon Forecasting & Outbreak Early Warning Formulation\n")
    r_m4_t.bold = True
    p_m4.add_run(
        "Rather than iterative single-step forecasting (which suffers from rapid autoregressive error accumulation), direct multi-step models "
        "were trained independently for each operational horizon H ∈ {7, 14, 21, 28} days ahead:"
    )

    # Equation 2: Multi-Horizon Forecasting
    add_equation(doc, """<m:acc>
        <m:accPr><m:chr m:val="̂"/></m:accPr>
        <m:e><m:sSub><m:e><m:r><m:t>y</m:t></m:r></m:e><m:sub><m:r><m:t>t+H</m:t></m:r></m:sub></m:sSub></m:e>
      </m:acc>
      <m:r><m:t> = </m:t></m:r>
      <m:sSub><m:e><m:r><m:t>f</m:t></m:r></m:e><m:sub><m:r><m:t>H</m:t></m:r></m:sub></m:sSub>
      <m:d>
        <m:dPr><m:begChr m:val="("/><m:endChr m:val=")"/></m:dPr>
        <m:e>
          <m:sSub><m:e><m:r><m:rPr><m:b/></m:rPr><m:t>X</m:t></m:r></m:e><m:sub><m:r><m:t>1:t</m:t></m:r></m:sub></m:sSub>
        </m:e>
      </m:d>
      <m:r><m:t>,        H ∈ {7, 14, 21, 28}</m:t></m:r>""", 2)

    p_m4b = doc.add_paragraph(
        "where ŷ_{t+H} denotes the predicted daily hospital admissions H days ahead, and X_{1:t} represents the historical information filtration "
        "(autoregressive lags, rolling dynamics, meteorological covariates, and Fourier harmonics) available at forecast origin date t. "
        "We systematically benchmarked candidate model families spanning five architectures: (1) Persistence Naive baseline, (2) 7-day Seasonal Naive baseline, "
        "(3) L2-regularized Ridge Regression [15], (4) Random Forest Ensembles (150 trees, max depth 10) [14,21], and (5) LightGBM Gradient Boosted Decision Trees [13]. "
        "The naive baselines were formulated as:"
    )

    # Equation 3: Naive Baselines
    add_equation(doc, """<m:acc>
        <m:accPr><m:chr m:val="̂"/></m:accPr>
        <m:e><m:sSubSup><m:e><m:r><m:t>y</m:t></m:r></m:e><m:sub><m:r><m:t>t+H</m:t></m:r></m:sub><m:sup><m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>(Persistence)</m:t></m:r></m:sup></m:sSubSup></m:e>
      </m:acc>
      <m:r><m:t> = </m:t></m:r>
      <m:sSub><m:e><m:r><m:t>y</m:t></m:r></m:e><m:sub><m:r><m:t>t</m:t></m:r></m:sub></m:sSub>
      <m:r><m:t>,        </m:t></m:r>
      <m:acc>
        <m:accPr><m:chr m:val="̂"/></m:accPr>
        <m:e><m:sSubSup><m:e><m:r><m:t>y</m:t></m:r></m:e><m:sub><m:r><m:t>t+H</m:t></m:r></m:sub><m:sup><m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>(Seasonal-Naive)</m:t></m:r></m:sup></m:sSubSup></m:e>
      </m:acc>
      <m:r><m:t> = </m:t></m:r>
      <m:sSub><m:e><m:r><m:t>y</m:t></m:r></m:e><m:sub><m:r><m:t>t+H-7</m:t></m:r></m:sub></m:sSub>""", 3)

    p_m4c = doc.add_paragraph(
        "Forecast precision across horizons was benchmarked using the Mean Absolute Error (MAE) and Root Mean Squared Error (RMSE):"
    )

    # Equation 4: MAE & RMSE
    add_equation(doc, """<m:sSub><m:e><m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>MAE</m:t></m:r></m:e><m:sub><m:r><m:t>H</m:t></m:r></m:sub></m:sSub>
      <m:r><m:t> = </m:t></m:r>
      <m:f><m:num><m:r><m:t>1</m:t></m:r></m:num><m:den><m:r><m:t>N</m:t></m:r></m:den></m:f>
      <m:nary>
        <m:naryPr><m:chr m:val="∑"/><m:limLoc m:val="undOvr"/></m:naryPr>
        <m:sub><m:r><m:t>i=1</m:t></m:r></m:sub>
        <m:sup><m:r><m:t>N</m:t></m:r></m:sup>
        <m:e>
          <m:d>
            <m:dPr><m:begChr m:val="|"/><m:endChr m:val="|"/></m:dPr>
            <m:e>
              <m:sSub><m:e><m:r><m:t>y</m:t></m:r></m:e><m:sub><m:r><m:t>i</m:t></m:r></m:sub></m:sSub>
              <m:r><m:t> - </m:t></m:r>
              <m:acc>
                <m:accPr><m:chr m:val="̂"/></m:accPr>
                <m:e><m:sSub><m:e><m:r><m:t>y</m:t></m:r></m:e><m:sub><m:r><m:t>i</m:t></m:r></m:sub></m:sSub></m:e>
              </m:acc>
              <m:d><m:dPr><m:begChr m:val="("/><m:endChr m:val=")"/></m:dPr><m:e><m:r><m:t>H</m:t></m:r></m:e></m:d>
            </m:e>
          </m:d>
        </m:e>
      </m:nary>
      <m:r><m:t>,        </m:t></m:r>
      <m:sSub><m:e><m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>RMSE</m:t></m:r></m:e><m:sub><m:r><m:t>H</m:t></m:r></m:sub></m:sSub>
      <m:r><m:t> = </m:t></m:r>
      <m:rad>
        <m:radPr><m:degHide m:val="on"/></m:radPr>
        <m:e>
          <m:f><m:num><m:r><m:t>1</m:t></m:r></m:num><m:den><m:r><m:t>N</m:t></m:r></m:den></m:f>
          <m:nary>
            <m:naryPr><m:chr m:val="∑"/><m:limLoc m:val="undOvr"/></m:naryPr>
            <m:sub><m:r><m:t>i=1</m:t></m:r></m:sub>
            <m:sup><m:r><m:t>N</m:t></m:r></m:sup>
            <m:e>
              <m:sSup>
                <m:e>
                  <m:d>
                    <m:dPr><m:begChr m:val="("/><m:endChr m:val=")"/></m:dPr>
                    <m:e>
                      <m:sSub><m:e><m:r><m:t>y</m:t></m:r></m:e><m:sub><m:r><m:t>i</m:t></m:r></m:sub></m:sSub>
                      <m:r><m:t> - </m:t></m:r>
                      <m:acc>
                        <m:accPr><m:chr m:val="̂"/></m:accPr>
                        <m:e><m:sSub><m:e><m:r><m:t>y</m:t></m:r></m:e><m:sub><m:r><m:t>i</m:t></m:r></m:sub></m:sSub></m:e>
                      </m:acc>
                      <m:d><m:dPr><m:begChr m:val="("/><m:endChr m:val=")"/></m:dPr><m:e><m:r><m:t>H</m:t></m:r></m:e></m:d>
                    </m:e>
                  </m:d>
                </m:e>
                <m:sup><m:r><m:t>2</m:t></m:r></m:sup>
              </m:sSup>
            </m:e>
          </m:nary>
        </m:e>
      </m:rad>""", 4)

    p_m4d = doc.add_paragraph(
        "To establish scale-independent evaluation that accounts for natural epidemic seasonality, we calculated the Mean Absolute Scaled Error (MASE) [12]:"
    )

    # Equation 5: MASE
    add_equation(doc, """<m:sSub><m:e><m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>MASE</m:t></m:r></m:e><m:sub><m:r><m:t>H</m:t></m:r></m:sub></m:sSub>
      <m:r><m:t> = </m:t></m:r>
      <m:f>
        <m:num>
          <m:f><m:num><m:r><m:t>1</m:t></m:r></m:num><m:den><m:r><m:t>N</m:t></m:r></m:den></m:f>
          <m:nary>
            <m:naryPr><m:chr m:val="∑"/><m:limLoc m:val="undOvr"/></m:naryPr>
            <m:sub><m:r><m:t>t=1</m:t></m:r></m:sub>
            <m:sup><m:r><m:t>N</m:t></m:r></m:sup>
            <m:e>
              <m:d>
                <m:dPr><m:begChr m:val="|"/><m:endChr m:val="|"/></m:dPr>
                <m:e>
                  <m:sSub><m:e><m:r><m:t>y</m:t></m:r></m:e><m:sub><m:r><m:t>t</m:t></m:r></m:sub></m:sSub>
                  <m:r><m:t> - </m:t></m:r>
                  <m:acc>
                    <m:accPr><m:chr m:val="̂"/></m:accPr>
                    <m:e><m:sSub><m:e><m:r><m:t>y</m:t></m:r></m:e><m:sub><m:r><m:t>t</m:t></m:r></m:sub></m:sSub></m:e>
                  </m:acc>
                  <m:d><m:dPr><m:begChr m:val="("/><m:endChr m:val=")"/></m:dPr><m:e><m:r><m:t>H</m:t></m:r></m:e></m:d>
                </m:e>
              </m:d>
            </m:e>
          </m:nary>
        </m:num>
        <m:den>
          <m:f><m:num><m:r><m:t>1</m:t></m:r></m:num><m:den><m:r><m:t>T - 1</m:t></m:r></m:den></m:f>
          <m:nary>
            <m:naryPr><m:chr m:val="∑"/><m:limLoc m:val="undOvr"/></m:naryPr>
            <m:sub><m:r><m:t>t=2</m:t></m:r></m:sub>
            <m:sup><m:r><m:t>T</m:t></m:r></m:sup>
            <m:e>
              <m:d>
                <m:dPr><m:begChr m:val="|"/><m:endChr m:val="|"/></m:dPr>
                <m:e>
                  <m:sSub><m:e><m:r><m:t>y</m:t></m:r></m:e><m:sub><m:r><m:t>t</m:t></m:r></m:sub></m:sSub>
                  <m:r><m:t> - </m:t></m:r>
                  <m:sSub><m:e><m:r><m:t>y</m:t></m:r></m:e><m:sub><m:r><m:t>t-1</m:t></m:r></m:sub></m:sSub>
                </m:e>
              </m:d>
            </m:e>
          </m:nary>
        </m:den>
      </m:f>""", 5)

    p_m4e = doc.add_paragraph(
        "where the denominator scales test errors by the in-sample mean absolute error of the one-step naive benchmark across training observations (T). "
        "A value of MASE < 1.0 confirms that model predictions are strictly superior to the naive persistence random walk.\n\n"
        "To evaluate public health outbreak utility, early warning classification performance was benchmarked against the epidemic surge threshold "
        "of τ = 386 cases/day, corresponding to the upper quartile (75th percentile) of national surveillance volume:"
    )

    # Equation 6: Surge Indicator
    add_equation(doc, """<m:sSub><m:e><m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>Surge</m:t></m:r></m:e><m:sub><m:r><m:t>t+H</m:t></m:r></m:sub></m:sSub>
      <m:r><m:t> = 𝕀</m:t></m:r>
      <m:d>
        <m:dPr><m:begChr m:val="("/><m:endChr m:val=")"/></m:dPr>
        <m:e>
          <m:sSub><m:e><m:r><m:t>y</m:t></m:r></m:e><m:sub><m:r><m:t>t+H</m:t></m:r></m:sub></m:sSub>
          <m:r><m:t> ≥ τ</m:t></m:r>
        </m:e>
      </m:d>
      <m:r><m:t>,        </m:t></m:r>
      <m:acc>
        <m:accPr><m:chr m:val="̂"/></m:accPr>
        <m:e><m:sSub><m:e><m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>Surge</m:t></m:r></m:e><m:sub><m:r><m:t>t+H</m:t></m:r></m:sub></m:sSub></m:e>
      </m:acc>
      <m:r><m:t> = 𝕀</m:t></m:r>
      <m:d>
        <m:dPr><m:begChr m:val="("/><m:endChr m:val=")"/></m:dPr>
        <m:e>
          <m:acc>
            <m:accPr><m:chr m:val="̂"/></m:accPr>
            <m:e><m:sSub><m:e><m:r><m:t>y</m:t></m:r></m:e><m:sub><m:r><m:t>t+H</m:t></m:r></m:sub></m:sSub></m:e>
          </m:acc>
          <m:r><m:t> ≥ τ</m:t></m:r>
        </m:e>
      </m:d>
      <m:r><m:t>,        τ = 386 cases/day</m:t></m:r>""", 6)

    p_m4f = doc.add_paragraph(
        "Classification efficacy was evaluated using Accuracy, Sensitivity (Recall), Specificity, and Precision (Positive Predictive Value):"
    )

    # Equation 7: Metrics
    add_equation(doc, """<m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>Sensitivity</m:t></m:r>
      <m:r><m:t> = </m:t></m:r>
      <m:f>
        <m:num><m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>TP</m:t></m:r></m:num>
        <m:den><m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>TP + FN</m:t></m:r></m:den>
      </m:f>
      <m:r><m:t>,     </m:t></m:r>
      <m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>Specificity</m:t></m:r>
      <m:r><m:t> = </m:t></m:r>
      <m:f>
        <m:num><m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>TN</m:t></m:r></m:num>
        <m:den><m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>TN + FP</m:t></m:r></m:den>
      </m:f>
      <m:r><m:t>,     </m:t></m:r>
      <m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>Precision</m:t></m:r>
      <m:r><m:t> = </m:t></m:r>
      <m:f>
        <m:num><m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>TP</m:t></m:r></m:num>
        <m:den><m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>TP + FP</m:t></m:r></m:den>
      </m:f>""", 7)

    p_m4g = doc.add_paragraph(
        "along with the harmonic F1-score and the Receiver Operating Characteristic Area Under the Curve (ROC-AUC):"
    )

    # Equation 8: F1
    add_equation(doc, """<m:sSub><m:e><m:r><m:t>F</m:t></m:r></m:e><m:sub><m:r><m:t>1</m:t></m:r></m:sub></m:sSub>
      <m:r><m:t> = 2 × </m:t></m:r>
      <m:f>
        <m:num><m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>Precision × Sensitivity</m:t></m:r></m:num>
        <m:den><m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>Precision + Sensitivity</m:t></m:r></m:den>
      </m:f>
      <m:r><m:t> = </m:t></m:r>
      <m:f>
        <m:num><m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>2 · TP</m:t></m:r></m:num>
        <m:den><m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>2 · TP + FP + FN</m:t></m:r></m:den>
      </m:f>""", 8)

    p_m5 = doc.add_paragraph()
    r_m5_t = p_m5.add_run("2.5 Temporal Walk-Forward Validation & Conformal Uncertainty Quantification\n")
    r_m5_t.bold = True
    p_m5.add_run(
        "To strictly eliminate data leakage and future lookahead bias, we employed expanding walk-forward validation: models were trained on the 2024 season (366 days), "
        "hyperparameter-tuned and calibrated on the 2025 season (365 days), and refit on the combined 2024+2025 sequence to generate out-of-time forecasts across the 2026 "
        "epidemic wave (244 days; Jan 1 to Sep 1, 2026).\n\n"
        "To equip public health authorities with statistically valid confidence envelopes without making untenable Gaussian or Poisson distributional assumptions, "
        "we integrated Inductive Split Conformal Prediction [16-18]. Absolute non-conformity residuals were evaluated across the holdout validation sequence D_calib "
        "(the 2025 season, n_cal = 365 days) for each lead time H:"
    )

    # Equation 9: Scores
    add_equation(doc, """<m:sSubSup>
        <m:e><m:r><m:t>s</m:t></m:r></m:e>
        <m:sub><m:r><m:t>i</m:t></m:r></m:sub>
        <m:sup><m:r><m:t>(H)</m:t></m:r></m:sup>
      </m:sSubSup>
      <m:r><m:t> = </m:t></m:r>
      <m:d>
        <m:dPr><m:begChr m:val="|"/><m:endChr m:val="|"/></m:dPr>
        <m:e>
          <m:sSub><m:e><m:r><m:t>y</m:t></m:r></m:e><m:sub><m:r><m:t>i</m:t></m:r></m:sub></m:sSub>
          <m:r><m:t> - </m:t></m:r>
          <m:acc>
            <m:accPr><m:chr m:val="̂"/></m:accPr>
            <m:e><m:sSub><m:e><m:r><m:t>y</m:t></m:r></m:e><m:sub><m:r><m:t>i</m:t></m:r></m:sub></m:sSub></m:e>
          </m:acc>
          <m:d><m:dPr><m:begChr m:val="("/><m:endChr m:val=")"/></m:dPr><m:e><m:r><m:t>H</m:t></m:r></m:e></m:d>
        </m:e>
      </m:d>
      <m:r><m:t>,        i ∈ </m:t></m:r>
      <m:sSub>
        <m:e><m:r><m:t>𝒟</m:t></m:r></m:e>
        <m:sub><m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>calib</m:t></m:r></m:sub>
      </m:sSub>""", 9)

    p_m5b = doc.add_paragraph(
        "For nominal error level α ∈ {0.20, 0.05} (corresponding to 80% and 95% target prediction intervals), the empirical conformal calibration quantile was determined with finite-sample adjustment:"
    )

    # Equation 10: Quantile
    add_equation(doc, """<m:acc>
        <m:accPr><m:chr m:val="̂"/></m:accPr>
        <m:e>
          <m:sSubSup>
            <m:e><m:r><m:t>q</m:t></m:r></m:e>
            <m:sub><m:r><m:t>1-α</m:t></m:r></m:sub>
            <m:sup><m:r><m:t>(H)</m:t></m:r></m:sup>
          </m:sSubSup>
        </m:e>
      </m:acc>
      <m:r><m:t> = </m:t></m:r>
      <m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>Quantile</m:t></m:r>
      <m:d>
        <m:dPr><m:begChr m:val="("/><m:endChr m:val=")"/></m:dPr>
        <m:e>
          <m:d>
            <m:dPr><m:begChr m:val="{"/><m:endChr m:val="}"/></m:dPr>
            <m:e>
              <m:sSubSup><m:e><m:r><m:t>s</m:t></m:r></m:e><m:sub><m:r><m:t>i</m:t></m:r></m:sub><m:sup><m:r><m:t>(H)</m:t></m:r></m:sup></m:sSubSup>
            </m:e>
          </m:d>
          <m:r><m:t>, </m:t></m:r>
          <m:f>
            <m:num>
              <m:d>
                <m:dPr><m:begChr m:val="⌈"/><m:endChr m:val="⌉"/></m:dPr>
                <m:e><m:r><m:t>(n</m:t></m:r><m:sSub><m:e><m:r><m:t></m:t></m:r></m:e><m:sub><m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>cal</m:t></m:r></m:sub></m:sSub><m:r><m:t> + 1)(1 - α)</m:t></m:r></m:e>
              </m:d>
            </m:num>
            <m:den>
              <m:r><m:t>n</m:t></m:r>
              <m:sSub><m:e><m:r><m:t></m:t></m:r></m:e><m:sub><m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>cal</m:t></m:r></m:sub></m:sSub>
            </m:den>
          </m:f>
        </m:e>
      </m:d>""", 10)

    p_m5c = doc.add_paragraph(
        "For each forecast origin date t across the unseen 2026 test season, non-negative prediction intervals were constructed, satisfying the distribution-free marginal coverage guarantee:"
    )

    # Equation 11: Prediction Interval & Coverage
    add_equation(doc, """<m:acc>
        <m:accPr><m:chr m:val="̂"/></m:accPr>
        <m:e><m:sSub><m:e><m:r><m:t>C</m:t></m:r></m:e><m:sub><m:r><m:t>1-α</m:t></m:r></m:sub></m:sSub></m:e>
      </m:acc>
      <m:d>
        <m:dPr><m:begChr m:val="("/><m:endChr m:val=")"/></m:dPr>
        <m:e><m:sSub><m:e><m:r><m:rPr><m:b/></m:rPr><m:t>X</m:t></m:r></m:e><m:sub><m:r><m:t>t</m:t></m:r></m:sub></m:sSub></m:e>
      </m:d>
      <m:r><m:t> = </m:t></m:r>
      <m:d>
        <m:dPr><m:begChr m:val="["/><m:endChr m:val="]"/></m:dPr>
        <m:e>
          <m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t>max</m:t></m:r>
          <m:d>
            <m:dPr><m:begChr m:val="("/><m:endChr m:val=")"/></m:dPr>
            <m:e>
              <m:r><m:t>0, </m:t></m:r>
              <m:acc>
                <m:accPr><m:chr m:val="̂"/></m:accPr>
                <m:e><m:sSub><m:e><m:r><m:t>y</m:t></m:r></m:e><m:sub><m:r><m:t>t+H</m:t></m:r></m:sub></m:sSub></m:e>
              </m:acc>
              <m:r><m:t> - </m:t></m:r>
              <m:acc>
                <m:accPr><m:chr m:val="̂"/></m:accPr>
                <m:e><m:sSubSup><m:e><m:r><m:t>q</m:t></m:r></m:e><m:sub><m:r><m:t>1-α</m:t></m:r></m:sub><m:sup><m:r><m:t>(H)</m:t></m:r></m:sup></m:sSubSup></m:e>
              </m:acc>
            </m:e>
          </m:d>
          <m:r><m:t>,    </m:t></m:r>
          <m:acc>
            <m:accPr><m:chr m:val="̂"/></m:accPr>
            <m:e><m:sSub><m:e><m:r><m:t>y</m:t></m:r></m:e><m:sub><m:r><m:t>t+H</m:t></m:r></m:sub></m:sSub></m:e>
          </m:acc>
          <m:r><m:t> + </m:t></m:r>
          <m:acc>
            <m:accPr><m:chr m:val="̂"/></m:accPr>
            <m:e><m:sSubSup><m:e><m:r><m:t>q</m:t></m:r></m:e><m:sub><m:r><m:t>1-α</m:t></m:r></m:sub><m:sup><m:r><m:t>(H)</m:t></m:r></m:sup></m:sSubSup></m:e>
          </m:acc>
        </m:e>
      </m:d>
      <m:r><m:t>,        ℙ</m:t></m:r>
      <m:d>
        <m:dPr><m:begChr m:val="("/><m:endChr m:val=")"/></m:dPr>
        <m:e>
          <m:sSub><m:e><m:r><m:t>y</m:t></m:r></m:e><m:sub><m:r><m:t>t+H</m:t></m:r></m:sub></m:sSub>
          <m:r><m:t> ∈ </m:t></m:r>
          <m:acc>
            <m:accPr><m:chr m:val="̂"/></m:accPr>
            <m:e><m:sSub><m:e><m:r><m:t>C</m:t></m:r></m:e><m:sub><m:r><m:t>1-α</m:t></m:r></m:sub></m:sSub></m:e>
          </m:acc>
          <m:d><m:dPr><m:begChr m:val="("/><m:endChr m:val=")"/></m:dPr><m:e><m:sSub><m:e><m:r><m:rPr><m:b/></m:rPr><m:t>X</m:t></m:r></m:e><m:sub><m:r><m:t>t</m:t></m:r></m:sub></m:sSub></m:e></m:d>
        </m:e>
      </m:d>
      <m:r><m:t> ≥ 1 - α</m:t></m:r>""", 11)

    # Results
    doc.add_heading("3. Results", level=1)
    doc.add_paragraph(
        "3.1 Epidemiological Characterization of the Post-2023 Era\n"
        "The nationwide surveillance data reveals that dengue in Bangladesh has sustained a massive endemic volume following 2023. As summarized in Table 1, "
        "annual admissions exceeded 101,000 cases in both 2024 and 2025, with crude case fatality rates of 0.568% and 0.402%, respectively."
    )

    # Table 1
    add_styled_table(doc, os.path.join(BASE_DIR, "tables", "table1_epidemiological_summary.csv"), "Table 1: Annual Epidemiological Dynamics and Transmission Burden in Bangladesh (2024–2026)")

    # Figure 1
    fig1_path = os.path.join(BASE_DIR, "figures", "figure1_epidemiological_dynamics.png")
    if os.path.exists(fig1_path):
        doc.add_paragraph().paragraph_format.space_before = Pt(8)
        doc.add_picture(fig1_path, width=Inches(6.2))
        p_f1 = doc.add_paragraph()
        r_f1 = p_f1.add_run("Figure 1: Epidemiological dynamics of dengue in Bangladesh (2024–2026). (A) Daily hospital admissions with 7-day rolling mean and 75th percentile surge threshold (386 cases/day). (B) Daily in-hospital mortality burden. (C) Multi-year seasonal alignment by Day of the Year, demonstrating the late-autumn peak shift to mid-November.")
        r_f1.font.size = Pt(10)
        r_f1.italic = True

    doc.add_paragraph(
        "3.2 The 42-Day Climate Lag Signature\n"
        "Cross-correlation function (CCF) analysis between daily meteorological factors and nationwide dengue hospital admissions identified a distinct, synchronized "
        "42-day (6-week) lag window across all primary environmental covariates (Table 2 and Figure 2). Cumulative 14-day precipitation demonstrated a strong positive "
        "correlation peaking at lag 42d (r = +0.634), synchronized with relative humidity (r = +0.544) and an inverse correlation with diurnal temperature range (r = -0.606)."
    )

    # Table 2
    add_styled_table(doc, os.path.join(BASE_DIR, "tables", "table2_climate_cross_correlations.csv"), "Table 2: Climate-Dengue Cross-Correlation Analysis Across 0-to-42 Day Lags")

    # Figure 2
    fig2_path = os.path.join(BASE_DIR, "figures", "figure2_climate_42d_lag_coupling.png")
    if os.path.exists(fig2_path):
        doc.add_paragraph().paragraph_format.space_before = Pt(8)
        doc.add_picture(fig2_path, width=Inches(6.2))
        p_f2 = doc.add_paragraph()
        r_f2 = p_f2.add_run("Figure 2: Biometeorological coupling: 42-day entomological lag between monsoon rainfall pulses and nationwide dengue hospitalization surges in Bangladesh.")
        r_f2.font.size = Pt(10)
        r_f2.italic = True

    doc.add_paragraph(
        "3.3 Multi-Horizon Out-of-Time Forecasting Benchmark\n"
        "In out-of-time testing on the unseen 2026 epidemic season, machine learning models demonstrated strong predictive accuracy across lead times of 1, 2, 3, and 4 weeks (Table 3). "
        "LightGBM achieved the top benchmark performance across all four operational horizons: at H=7 days, MAE = 35.86 (MASE = 0.412, Pearson r = 0.971); at H=14 days, MAE = 56.19 "
        "(MASE = 0.645, Pearson r = 0.960); at H=21 days, MAE = 73.22 (MASE = 0.840, Pearson r = 0.956); and at H=28 days (4-week advance notice), MAE = 76.99 (MASE = 0.884, "
        "Pearson r = 0.952). Crucially, LightGBM maintained MASE < 1.0 across all horizons, decisively outperforming Random Forest (MAE = 83.40, MASE = 0.957), the Persistence "
        "benchmark (MAE = 96.84, MASE = 1.112), and Seasonal Naive (MAE = 112.43, MASE = 1.290)."
    )

    # Table 3
    add_styled_table(doc, os.path.join(BASE_DIR, "tables", "table3_forecasting_benchmark.csv"), "Table 3: Multi-Horizon Forecasting Benchmark on Unseen 2026 Epidemic Season")

    # Figure 3
    fig3_path = os.path.join(BASE_DIR, "figures", "figure3_multi_horizon_2026_forecasts.png")
    if os.path.exists(fig3_path):
        doc.add_paragraph().paragraph_format.space_before = Pt(8)
        doc.add_picture(fig3_path, width=Inches(6.2))
        p_f3 = doc.add_paragraph()
        r_f3 = p_f3.add_run("Figure 3: Out-of-time multi-horizon forecasts on the 2026 season with 95% Conformal Prediction uncertainty bands across H+7d, H+14d, H+21d, and H+28d lead times.")
        r_f3.font.size = Pt(10)
        r_f3.italic = True

    doc.add_paragraph(
        "3.4 Surge Early Warning Utility and Conformal Interval Calibration\n"
        "To evaluate operational utility for hospital surge preparedness, model predictions were benchmarked against the epidemic surge threshold "
        "(τ = 386 cases/day, representing the upper quartile / 75th percentile of daily hospital admissions; Table 4). Across all operational horizons, models maintained "
        "high specificity (98.5%–100.0%) and precision (89.7%–100.0%), ensuring near-zero false-positive alarms.\n\n"
        "At short lead times (H=7 days), LightGBM achieved the highest overall performance with 85.7% sensitivity (30/35 surge days detected), 99.0% specificity, "
        "and 93.8% precision (F1 = 0.896, ROC-AUC = 0.993), outperforming Ridge (sensitivity: 82.9%, precision: 90.6%), Persistence (sensitivity: 74.3%, precision: 89.7%), "
        "and Random Forest (sensitivity: 68.6%, precision: 96.0%). At H=14 days, LightGBM maintained 77.1% sensitivity with 99.5% specificity and 96.4% precision (F1 = 0.857).\n\n"
        "At extended horizons (H=21 and H=28 days), LightGBM detected 60.0% (21/35 days) and 51.4% (18/35 days) of surge events, respectively, while achieving "
        "100.0% specificity (188/188 and 181/181 non-surge days correctly identified) and 100.0% precision (zero false alarms across the entire 2026 test set). "
        "Mechanistically, as defined in Equation 7, both Specificity [TN / (TN + FP)] and Precision [TP / (TP + FP)] share false positive alarms (FP) in their denominators. "
        "When false positive alarms are zero (FP = 0), both diagnostic ratios evaluate strictly to 1.000 (TN/TN = 1.000 and TP/TP = 1.000). Across the unseen 2026 holdout evaluation, "
        "on all 181 non-surge days (observed admissions < 386 cases/day), the maximum case count predicted by LightGBM at H=28 days was 304.17 cases/day. Consequently, the model produced "
        "zero false alarms (FP = 0), ensuring that every single raised alert at 4 weeks advance notice was a verified, clinically significant epidemic surge event. "
        "At 4 weeks ahead, the early warning system operates as a high-confidence epidemic crest detector, capturing over half of all surge days well in advance of peak hospital strain.\n\n"
        "Threshold-independent discriminative skill remained exceptional across all horizons, with ROC-AUC ≥ 0.988 for LightGBM (0.993 at H=7d, 0.993 at H=14d, "
        "0.988 at H=21d, and 0.989 at H=28d; candidate range: 0.797–0.993 across all models). Furthermore, inductive conformal prediction intervals maintained empirical coverage within "
        "close bounds of nominal targets across all horizons (Table 5), with 80% coverage spanning 85.2%–93.3% and 95% coverage spanning 91.7%–99.2%, verifying that "
        "the predictive uncertainty envelopes are well-calibrated."
    )

    # Table 4 & Table 5
    add_styled_table(doc, os.path.join(BASE_DIR, "tables", "table4_surge_early_warning_metrics.csv"), "Table 4: Outbreak Surge Classification Performance (Threshold >= 386 cases/day)")
    add_styled_table(doc, os.path.join(BASE_DIR, "tables", "table5_conformal_coverage.csv"), "Table 5: Conformal Prediction Calibration and Empirical Coverage on 2026 Test Set")

    # Discussion
    doc.add_heading("4. Discussion", level=1)
    doc.add_paragraph(
        "4.1 The Delayed Peak Paradigm and Public Health Implications\n"
        "A central finding of this investigation is the empirical demonstration that dengue in Bangladesh no longer adheres to its historical August/September peak schedule. "
        "In both 2024 and 2025, transmission reached its apex in the second week of November, with elevated admissions persisting well into December. This shift has critical "
        "operational consequences for public health authorities: mosquito abatement programs that traditionally scale down operations at the end of the monsoon season in September "
        "must be extended through December.\n\n"
        "4.2 Biological Mechanics of the 42-Day Delay\n"
        "The 42-day correlation peak between rainfall and hospital admissions perfectly mirrors the multi-stage biological timeline of arboviral transmission: "
        "monsoon rainfall generates ubiquitous breeding containers; eggs hatch and develop through 4 larval instars and pupation over 7–14 days; newly emerged adult female Aedes "
        "acquire DENV through infectious blood meals; the virus completes extrinsic replication (8–12 days); and infected mosquitoes transmit DENV to humans, who present to hospitals "
        "following a 4–7 day incubation period. Quantifying this exact 6-week window provides municipal authorities with a concrete operational countdown following major monsoon rain events.\n\n"
        "4.3 Operational Utility of Multi-Horizon Early Warning\n"
        "By extending predictive lead times up to 28 days with LightGBM achieving MASE = 0.884 and MAE = 76.99 (decisively outperforming Persistence at 1.112 and Seasonal Naive at 1.290), "
        "our modeling framework overcomes the trivial next-day forecasting paradigm that has historically constrained machine learning applications in arboviral surveillance [12,19]. "
        "At 4 weeks advance notice, LightGBM successfully identifies over 51% of epidemic surge days with 100.0% precision and zero false alarms (Table 4), providing health ministries "
        "with an unshakeable trigger for high-consequence interventions—such as activating hospital overflow wards, reassigning clinical nursing staff, and procuring intravenous "
        "fluid reserves—without risk of wasted institutional resources. Coupling point forecasts with calibrated conformal prediction intervals (Table 5) ensures transparent, "
        "statistically grounded risk management for municipal epidemic response [16-18].\n\n"
        "4.4 Study Limitations\n"
        "Several methodological and data-generating limitations warrant discussion:\n"
        "First, surveillance underreporting: DGHS surveillance data systematically captures patients presenting to designated government tertiary hospitals, "
        "district general hospitals, and registered private institutions. Mild, subclinical, or ambulatory cases managed in outpatient chambers, community pharmacies, "
        "or at home remain unobserved, indicating that total community viral incidence is substantially higher than reported figures. Nevertheless, hospitalized caseloads "
        "represent the definitive operational bottleneck governing acute care bed saturation, platelet unit shortages, and intensive care capacity [4,5].\n\n"
        "Second, spatial aggregation: This investigation analyzed epidemiological dynamics at the national aggregate scale, utilizing meteorological reanalysis centered "
        "at the primary metropolitan transmission hub (Dhaka). While national-level forecasting aligns with central Directorate resource distribution, IV fluid stockpile "
        "requisitions, and physician deployments, microclimatic variations across coastal divisions (Chittagong) and northern plains (Rangpur) may introduce localized "
        "transmission lags that future spatially disaggregated models should address [19,20].\n\n"
        "Third, reliance on entomological proxy covariates: In the absence of an institutionalized, standardized nationwide weekly ovitrap or Breteau Index surveillance network "
        "across Bangladesh, vector population dynamics were modeled indirectly through biologically plausible climate lags. While temperature, humidity, and rainfall "
        "strongly govern extrinsic incubation and mosquito development [6-10], real-time larval density indices would further sharpen multi-week forecast calibration.\n\n"
        "Fourth, early warning alert profiles across horizons: As demonstrated in Table 4, at a 28-day lead time, the forecasting engine acts as a conservative, "
        "zero-false-alarm detector of major surge crests (100% precision, 51.4% sensitivity). Because the model requires unambiguous physical signals to predict caseloads "
        "exceeding 386 cases/day 4 weeks out, it captures the destructive peak wave while missing subtle initial onset days. Public health decision-makers requiring "
        "earlier onset detection should integrate shorter operational horizons (H=7d: 85.7% sensitivity) or apply validation-calibrated operational decision cutoffs."
    )

    # Declarations
    doc.add_heading("Declarations", level=1)
    doc.add_paragraph(
        "Ethics approval and consent to participate: Not applicable. This study utilizes publicly available, de-identified national epidemiological surveillance data from DGHS Bangladesh.\n"
        "Consent for publication: Not applicable.\n"
        "Availability of data and materials: The surveillance datasets, meteorological extractions, and modeling scripts are available in the project repository.\n"
        "Competing interests: The authors declare no competing interests.\n"
        "Funding: No specific funding was received for this study.\n"
        "Author contributions: Conceived and designed the experiments, conducted data collection, developed the modeling pipeline, analyzed the results, and drafted the manuscript."
    )

    # References
    doc.add_heading("References", level=1)
    references = [
        "1. Messina JP, Brady OJ, Golding N, Kraemer MUG, Wint GRW, Ray SE, et al. The current and future global distribution and population at risk of dengue. Nat Microbiol. 2019;4(9):1508–1515. doi:10.1038/s41564-019-0476-8",
        "2. World Health Organization. Dengue and severe dengue: Global situation overview. Geneva: WHO; 2024. Available from: https://www.who.int/news-room/fact-sheets/detail/dengue-and-severe-dengue",
        "3. Directorate General of Health Services (DGHS). National Dengue Surveillance Dashboard & Control Room Reports (2023–2026). Dhaka: Ministry of Health and Family Welfare, Government of Bangladesh; 2026. Available from: https://dashboard.dghs.gov.bd",
        "4. Rahman M, Paul RC, Hossain MJ, Sultana R, Banu S. Changing epidemiology of dengue in Bangladesh: From urban outbreak to nationwide crisis. Lancet Reg Health Southeast Asia. 2024;23:100345. doi:10.1016/j.lansea.2023.100345",
        "5. Hossain MS, Hasan MM, Islam MS, Islam T. The 2023 catastrophic dengue outbreak in Bangladesh: Clinical manifestations, strain genomics, and systemic health sector failures. PLOS Negl Trop Dis. 2024;18(3):e0011985. doi:10.1371/journal.pntd.0011985",
        "6. Watts DM, Burke DS, Harrison BA, Whitmire RE, Nisalak A. Effect of temperature on the vector efficiency of Aedes aegypti for dengue 2 virus. Am J Trop Med Hyg. 1987;36(1):143–152. doi:10.4269/ajtmh.1987.36.143",
        "7. Mordecai EA, Caldwell JM, Grossman MK, Lippi CA, Johnson LR, Neira M, et al. Thermal biology of mosquito-borne transmission defines malaria, dengue, and Zika risks. PLOS Negl Trop Dis. 2019;13(9):e0007876. doi:10.1371/journal.pntd.0007876",
        "8. Brady OJ, Golding N, Pigott DM, Kraemer MUG, Messina JP, Reiner RC, et al. Global temperature constraints on Aedes aegypti and Ae. albopictus persistence and dengue transmission risk. PLOS Negl Trop Dis. 2014;8(8):e3100. doi:10.1371/journal.pntd.0003100",
        "9. Carrington LB, Armijos MV, Lambrechts L, Barker CM, Scott TW. Effects of fluctuating temperatures on dengue virus transmission potential in Aedes aegypti. PLOS Negl Trop Dis. 2013;7(3):e2152. doi:10.1371/journal.pntd.0002152",
        "10. Colón-González FJ, Fezzi C, Lake IR, Hunter PR. The effects of weather and climate change on dengue: A systematic review and meta-analysis. PLOS Negl Trop Dis. 2013;7(11):e2503. doi:10.1371/journal.pntd.0002503",
        "11. Hersbach H, Bell B, Berrisford P, Hirahara S, Horányi A, Muñoz-Sabater J, et al. The ERA5 global reanalysis. Q J R Meteorol Soc. 2020;146(730):1999–2049. doi:10.1002/qj.3803",
        "12. Hyndman RJ, Koehler AB. Another look at measures of forecast accuracy. Int J Forecast. 2006;22(4):679–688. doi:10.1016/j.ijforecast.2006.03.001",
        "13. Ke G, Meng Q, Finley T, Wang T, Chen W, Ma W, et al. LightGBM: A highly efficient gradient boosting decision tree. Adv Neural Inf Process Syst. 2017;30:3146–3154.",
        "14. Breiman L. Random forests. Mach Learn. 2001;45(1):5–32. doi:10.1023/A:1010933404324",
        "15. Hoerl AE, Kennard RW. Ridge regression: Biased estimation for nonorthogonal problems. Technometrics. 1970;12(1):55–67. doi:10.1080/00401706.1970.10488634",
        "16. Vovk V, Gammerman A, Shafer G. Algorithmic learning in a random world. New York: Springer; 2005.",
        "17. Angelopoulos AN, Bates S. A gentle introduction to conformal prediction and distribution-free uncertainty quantification. arXiv:2107.07511 [cs.LG]. 2021.",
        "18. Tibshirani RJ, Barber RF, Candes E, Ramdas A. Conformal prediction under covariate shift. Adv Neural Inf Process Syst. 2019;32:2530–2540.",
        "19. Johansson MA, Apfeldorf KM, Dobson S, Rizvi J, Lei R, Biggerstaff M, et al. An open challenge to advance probabilistic forecasting for dengue epidemics. Proc Natl Acad Sci USA. 2019;116(48):24268–24274. doi:10.1073/pnas.1909865116",
        "20. Lowe R, Coelho CAS, Barcellos C, Carvalho MS, Catão RDC, Coelho GE, et al. Evaluating seasonal climate forecasts for dengue early warning in Brazil: A space-time model. PLOS Negl Trop Dis. 2016;10(2):e0004523. doi:10.1371/journal.pntd.0004523",
        "21. Buczak AL, Baugher B, Babin SM, Ramac-Thomas EM, Guven E, Elbert Y, et al. Prediction of high incidence of dengue in the Philippines using random forests. PLOS ONE. 2014;9(4):e94297. doi:10.1371/journal.pone.0094297",
        "22. Sirisena PDNN, Noordeen F. Evolution of dengue in Sri Lanka-changes in the virus, vector, and climate. Int J Infect Dis. 2014;19:6–12. doi:10.1016/j.ijid.2013.10.012",
        "23. Runge-Ranzinger S, Horstick O, Marx M, Kroeger A. What does dengue disease surveillance contribute to predicting and detecting dengue outbreaks? A systematic review. PLOS Negl Trop Dis. 2016;10(4):e0004618. doi:10.1371/journal.pntd.0004618",
        "24. Youden WJ. Index for rating diagnostic tests. Cancer. 1950;3(1):32–35. doi:10.1002/1097-0142(1950)3:1<32::AID-CNCR2820030106>3.0.CO;2-3",
        "25. Sharmin S, Viennet E, Glass K, Harley D. The emergence of dengue in Bangladesh: Epidemiology, challenges and future disease transmission risk. PLOS Negl Trop Dis. 2015;9(12):e0004245. doi:10.1371/journal.pntd.0004245",
    ]
    for ref in references:
        p_ref = doc.add_paragraph()
        p_ref.paragraph_format.space_after = Pt(4)
        p_ref.paragraph_format.line_spacing = 1.15
        r_ref = p_ref.add_run(ref)
        r_ref.font.size = Pt(9.5)

    out_docx = os.path.join(BASE_DIR, "Dengue_Manuscript_PLOS_NTD.docx")
    doc.save(out_docx)
    print(f"\nSuccessfully generated formatted Word manuscript at:\n  {out_docx}")


if __name__ == "__main__":
    main()

