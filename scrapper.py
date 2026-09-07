#!/usr/bin/env python3
"""Scrape dengue data from the DGHS HEOC dengue dashboard.

Source: https://dashboard.dghs.gov.bd/pages/heoc_dengue_v1.php
Output: CSV files in the `data` directory next to this script.
"""

import csv
import os
import re
import sys
from datetime import datetime

import requests
from bs4 import BeautifulSoup

URL = "https://dashboard.dghs.gov.bd/pages/heoc_dengue_v1.php"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def fetch_html():
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text


def write_csv(filename, rows):
    if not rows:
        return
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, filename)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    print(f"  {filename}: {len(rows) - 1} rows")


def extract_chart_block(html, chart_var):
    i = html.find("Highcharts.chart('" + chart_var + "'")
    if i == -1:
        i = html.find('Highcharts.chart("' + chart_var + '"')
    if i == -1:
        return "", -1
    start = html.index("{", i) + 1
    brace_count = 1
    pos = start
    while pos < len(html) and brace_count > 0:
        c = html[pos]
        if c == "{":
            brace_count += 1
        elif c == "}":
            brace_count -= 1
        pos += 1
    return html[start : pos - 1], i


def parse_js_array(text):
    text = re.sub(r"\s+", " ", text.strip())
    if not (text.startswith("[") and text.endswith("]")):
        return []
    inner = text[1:-1].strip()
    if not inner:
        return []
    items, depth, buf = [], 0, ""
    for ch in inner:
        if ch in "[({":
            depth += 1
        elif ch in "])}":
            depth -= 1
        if ch == "," and depth == 0:
            items.append(buf.strip())
            buf = ""
        else:
            buf += ch
    if buf.strip():
        items.append(buf.strip())

    parsed = []
    for item in items:
        item = item.strip().strip('"').strip("'")
        try:
            parsed.append(int(item))
        except ValueError:
            try:
                parsed.append(float(item))
            except ValueError:
                parsed.append(item)
    return parsed


def extract_categories(html, chart_pos, block):
    m = re.search(r"categories\s*:\s*(\[[^\]]*\])", block)
    if m:
        return parse_js_array(m.group(1))
    window = html[max(0, chart_pos - 3000) : chart_pos]
    matches = list(re.finditer(r"var categories\s*=\s*(\[[^\]]*\])", window))
    if matches:
        return parse_js_array(matches[-1].group(1))
    return []


def extract_series(block):
    series = []
    for sm in re.finditer(
        r"\{\s*[^}]*?name\s*:\s*['\"]([^'\"]*)['\"][^}]*?data\s*:\s*(\[[^\]]*\])\s*\}",
        block,
    ):
        name = sm.group(1)
        data = parse_js_array(sm.group(2))
        series.append((name, data))
    return series


def extract_pie_data(block):
    """Extract name:value pairs from a pie chart's data: [{...}] array."""
    m = re.search(r"data\s*:\s*(\[[^\]]*\])", block)
    if not m:
        return []
    data = parse_js_array(m.group(1))
    items = []
    for entry in data:
        nm = re.search(r"name\s*:\s*['\"]([^'\"]*)['\"]", entry)
        y = re.search(r"y\s*:\s*([\d.]+)", entry)
        if nm and y:
            items.append((nm.group(1), float(y.group(1))))
    return items


def clean_num(text):
    text = re.sub(r"[,\s]", "", text)
    try:
        return int(text)
    except ValueError:
        return text


def parse_tables(soup):
    tables = {}
    for tbl in soup.find_all("table"):
        h3 = tbl.find_previous("h3", class_="box-title")
        title = h3.get_text(strip=True) if h3 else "untitled"
        rows = []
        for tr in tbl.find_all("tr"):
            cells = [
                td.get_text(strip=True).replace("\u00a0", "")
                for td in tr.find_all(["td", "th"])
            ]
            cells = [c for c in cells if c]
            if cells:
                rows.append(cells)
        safe = re.sub(r"[^a-zA-Z0-9_]+", "_", title.lower()).strip("_")
        tables.setdefault(safe, []).extend(rows)
    return tables


def main():
    print("Fetching page...")
    html = fetch_html()
    soup = BeautifulSoup(html, "html5lib")

    print("Parsing page...")

    # -------- Last updated --------
    last_updated = ""
    m = re.search(r"Last Updated[:\s<>/span]*>?([\d]+-[A-Za-z]+-[\d]+)", html, re.I)
    if m:
        last_updated = m.group(1)

    # -------- Headline numbers from item_one divs --------
    items = []
    for div in soup.select(".item_one"):
        txt = div.get_text(" ", strip=True)
        items.append(txt)
    # items = ['W35: 3,584', '12', '37,170', '102']
    w35_admitted = clean_num(re.sub(r"W\d+[:\s]*", "", items[0])) if len(items) >= 1 else None
    w35_deaths = clean_num(items[1]) if len(items) >= 2 else None
    cum_admitted = clean_num(items[2]) if len(items) >= 3 else None
    cum_deaths = clean_num(items[3]) if len(items) >= 4 else None

    # -------- 24h & cumulative stats from pie charts --------
    def extract_gender(html, chart_var):
        block, _ = extract_chart_block(html, chart_var)
        if not block:
            return {}
        return dict(extract_pie_data(block))

    g24 = extract_gender(html, "dengue_affected_by_gender_24")
    affected_male_24h = int(g24.get("Male", 0)) if g24.get("Male") else None
    affected_female_24h = int(g24.get("Female", 0)) if g24.get("Female") else None

    gc = extract_gender(html, "dengue_affected_by_gender")
    affected_male_cum = int(gc.get("Male", 0)) if gc.get("Male") else None
    affected_female_cum = int(gc.get("Female", 0)) if gc.get("Female") else None

    gd = extract_gender(html, "dengue_death_by_gender")
    death_male_cum = int(gd.get("Male", 0)) if gd.get("Male") else None
    death_female_cum = int(gd.get("Female", 0)) if gd.get("Female") else None

    # discharged from the column chart
    block, _ = extract_chart_block(html, "dengue_discharged_total_and_24_hours")
    discharged_24h = None
    discharged_cum = None
    if block:
        series = extract_series(block)
        for name, data in series:
            if "last 24 hours" in name.lower() and data:
                discharged_24h = data[0]
            elif "till date" in name.lower() and data:
                discharged_cum = data[0]

    # 24h death gender from the age group death table grand total
    death_male_24h = None
    death_female_24h = None
    for tbl in soup.find_all("table"):
        h3 = tbl.find_previous("h3", class_="box-title")
        title = h3.get_text(strip=True).lower() if h3 else ""
        if "death" in title and "24" in title:
            for tr in tbl.find_all("tr"):
                tds = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if tds and tds[0] == "Grand Total":
                    if len(tds) >= 3:
                        death_male_24h = clean_num(tds[1])
                        death_female_24h = clean_num(tds[2])
                    break
            break

    # -------- Tables --------
    tables = parse_tables(soup)
    table_map = {
        "age_group_distribution_of_affected_cases_of_last_24_hours": "age_group_affected_24h.csv",
        "age_group_distribution_of_deaths_of_last_24_hours": "age_group_deaths_24h.csv",
        "age_group_distribution_of_affected_cases_from_1_january_to_till_date_in_2026": "age_group_affected_till_date.csv",
        "age_group_distribution_of_deaths_from_1_january_to_till_date_in_2026": "age_group_deaths_till_date.csv",
        "affected_cases_within_city_corporation_from_01_january_to_till_date": "affected_within_cc_till_date.csv",
        "affected_cases_outside_of_city_corporation_from_01_january_to_till_date": "affected_outside_cc_till_date.csv",
        "deaths_within_city_corporation_from_01_january_to_till_date": "deaths_within_cc_till_date.csv",
        "deaths_outside_of_city_corporation_from_01_january_to_till_date": "deaths_outside_cc_till_date.csv",
    }
    for key, fname in table_map.items():
        rows = tables.get(key)
        if rows:
            write_csv(fname, rows)

    # -------- Highcharts chart blocks --------
    chart_configs = [
        ("affected_case_last_24_hour", "24h_cases_single.csv", ["category", "admitted"]),
        ("death_case_last_24_hour", "24h_deaths_single.csv", ["category", "deaths"]),
        ("div_city_cor_case_last_24_hour", "division_cc_cases_24h.csv", ["division", "admitted"]),
        ("div_city_cor_death_last_24_hour", "division_cc_deaths_24h.csv", ["division", "deaths"]),
        ("div_city_cor_case_in_year", "division_cc_cases_till_date.csv", ["division", "admitted"]),
        ("div_city_cor_death_in_year", "division_cc_deaths_till_date.csv", ["division", "deaths"]),
        ("monthly_case_and_death_in_year", "monthly_cases_till_date.csv", ["month", "admitted"]),
        ("monthly_case_and_death_only_in_year", "monthly_deaths_till_date.csv", ["month", "deaths"]),
        ("division_case", "division_cases_till_date.csv", ["division", "admitted"]),
        ("division_death", "division_deaths_till_date.csv", ["division", "deaths"]),
        ("year_case", "cases_by_year.csv", ["year", "admitted"]),
        ("confirmed_case", "daily_cases_year.csv", ["date", "admitted"]),
        ("death_case", "deaths_by_date_year.csv", ["date", "deaths"]),
        ("dengue_affected_by_age_group", "age_group_affected_chart.csv", ["age_group", "gender", "count"]),
        ("dengue_death_by_age_group", "age_group_deaths_chart.csv", ["age_group", "gender", "count"]),
    ]

    for chart_var, fname, cols in chart_configs:
        block, chart_pos = extract_chart_block(html, chart_var)
        if not block:
            continue
        categories = extract_categories(html, chart_pos, block)
        series = extract_series(block)
        rows = [cols]
        if len(cols) == 2:
            for name, data in series:
                for i, val in enumerate(data):
                    label = categories[i] if i < len(categories) else i + 1
                    rows.append([label, val])
        else:
            for name, data in series:
                for i, val in enumerate(data):
                    label = categories[i] if i < len(categories) else i + 1
                    val = abs(val) if isinstance(val, (int, float)) else val
                    rows.append([label, name, val])
        write_csv(fname, rows)

    # -------- Multi-year weekly cases --------
    block, chart_pos = extract_chart_block(html, "by_week_case")
    if block:
        categories = extract_categories(html, chart_pos, block)
        series = extract_series(block)
        rows = [["week", "year", "admitted"]]
        for name, data in series:
            year = re.search(r"(\d{4})", name)
            year = year.group(1) if year else name
            for i, val in enumerate(data):
                label = categories[i] if i < len(categories) else i + 1
                rows.append([label, year, val])
        write_csv("cases_by_week.csv", rows)

    # -------- Multi-year monthly cases --------
    block, chart_pos = extract_chart_block(html, "by_month_case")
    if block:
        categories = extract_categories(html, chart_pos, block)
        series = extract_series(block)
        rows = [["month_num", "year", "admitted"]]
        for name, data in series:
            year = re.search(r"(\d{4})", name)
            year = year.group(1) if year else name
            for i, val in enumerate(data):
                label = categories[i] if i < len(categories) else i + 1
                rows.append([label, year, val])
        write_csv("cases_by_month.csv", rows)

    # -------- Death rate by week --------
    block, chart_pos = extract_chart_block(html, "death_case_ration_by_week")
    if block:
        categories = extract_categories(html, chart_pos, block)
        series = extract_series(block)
        rows = [["week", "admitted", "deaths", "death_rate"]]
        for i, cat in enumerate(categories):
            vals = [s[1][i] if i < len(s[1]) else "" for s in series]
            rows.append([cat] + vals)
        write_csv("death_rate_by_week.csv", rows)

    # -------- Division cases by week --------
    block, chart_pos = extract_chart_block(html, "affected_in_division_by_week")
    if block:
        categories = extract_categories(html, chart_pos, block)
        series = extract_series(block)
        rows = [["week", "division", "admitted"]]
        for name, data in series:
            for i, val in enumerate(data):
                label = categories[i] if i < len(categories) else i + 1
                rows.append([label, name, val])
        write_csv("division_cases_by_week.csv", rows)

    # -------- Summary meta --------
    meta = [
        ["field", "value"],
        ["source", URL],
        ["scraped_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        ["last_updated", last_updated],
        ["week_admitted", w35_admitted],
        ["week_deaths", w35_deaths],
        ["cumulative_admitted", cum_admitted],
        ["cumulative_deaths", cum_deaths],
        ["discharged_24h", discharged_24h],
        ["discharged_cumulative", discharged_cum],
        ["affected_male_24h", affected_male_24h],
        ["affected_female_24h", affected_female_24h],
        ["affected_male_cumulative", affected_male_cum],
        ["affected_female_cumulative", affected_female_cum],
        ["death_male_24h", death_male_24h],
        ["death_female_24h", death_female_24h],
        ["death_male_cumulative", death_male_cum],
        ["death_female_cumulative", death_female_cum],
    ]

    try:
        with open(os.path.join(OUT_DIR, "division_cc_cases_24h.csv")) as f:
            c24 = sum(int(r[1]) for r in list(csv.reader(f))[1:])
        with open(os.path.join(OUT_DIR, "division_cc_deaths_24h.csv")) as f:
            d24 = sum(int(r[1]) for r in list(csv.reader(f))[1:])
        meta.append(["24h_admitted_total", c24])
        meta.append(["24h_deaths_total", d24])
    except (OSError, ValueError, IndexError):
        pass

    write_csv("summary.csv", meta)

    print(f"\nDone. Output written to {OUT_DIR}")


if __name__ == "__main__":
    sys.exit(main())