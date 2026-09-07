#!/usr/bin/env python3
"""Build a single ML-ready dengue dataset (2024-2026) from the DGHS dashboard.

Source: https://dashboard.dghs.gov.bd/pages/heoc_dengue_v1.php
The dashboard embeds per-year data server-side; POSTing `filter_year`
returns each year's daily admitted cases and death events.

Output: dengue_ml_dataset.csv (one row per day)
"""

import csv
import os
import re
import sys
from datetime import date, datetime, timedelta

import requests

URL = "https://dashboard.dghs.gov.bd/pages/heoc_dengue_v1.php"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
OUT_FILE = os.path.join(OUT_DIR, "dengue_ml_dataset.csv")

YEARS = [2024, 2025, 2026]


def fetch_year(year):
    resp = requests.post(
        URL,
        headers=HEADERS,
        data={"filter_year": str(year), "search_filter": "Search"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.text


def extract_chart_block(html, chart_name):
    i = html.find("Highcharts.chart('" + chart_name + "'")
    if i == -1:
        i = html.find('Highcharts.chart("' + chart_name + '"')
    if i == -1:
        return None
    start = html.index("{", i) + 1
    depth, pos = 1, start
    while pos < len(html) and depth > 0:
        if html[pos] == "{":
            depth += 1
        elif html[pos] == "}":
            depth -= 1
        pos += 1
    return html[start : pos - 1]


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


def extract_categories_and_series(block):
    cats = []
    m = re.search(r"categories\s*:\s*(\[[^\]]*\])", block)
    if m:
        cats = parse_js_array(m.group(1))
    series = []
    for sm in re.finditer(
        r"\{\s*[^}]*?name\s*:\s*['\"]([^'\"]*)['\"][^}]*?data\s*:\s*(\[[^\]]*\])\s*\}",
        block,
    ):
        series.append((sm.group(1), parse_js_array(sm.group(2))))
    return cats, series


def parse_date(s):
    try:
        return datetime.strptime(s, "%d-%b-%y").date()
    except ValueError:
        return None


def get_daily_cases(html):
    block = extract_chart_block(html, "confirmed_case")
    if not block:
        return {}
    cats, series = extract_categories_and_series(block)
    if not series:
        return {}
    data = series[0][1]
    out = {}
    for c, v in zip(cats, data):
        d = parse_date(str(c))
        if d and isinstance(v, (int, float)):
            out[d] = int(v)
    return out


def get_death_events(html):
    block = extract_chart_block(html, "death_case")
    if not block:
        return {}
    cats, series = extract_categories_and_series(block)
    if not series:
        return {}
    data = series[0][1]
    out = {}
    for c, v in zip(cats, data):
        d = parse_date(str(c))
        if d and isinstance(v, (int, float)):
            out[d] = int(v)
    return out


def build_year_dataset(year):
    html = fetch_year(year)
    cases = get_daily_cases(html)
    deaths = get_death_events(html)

    if not cases:
        print(f"  {year}: no daily data found")
        return []

    start = date(year, 1, 1)
    end = max(cases.keys())
    end = max(end, date(year, 12, 31) if year < 2026 else end)

    rows = []
    d = start
    while d <= end:
        admitted = cases.get(d, 0)
        rows.append(
            {
                "date": d,
                "year": d.year,
                "month": d.month,
                "day": d.day,
                "day_of_year": d.timetuple().tm_yday,
                "week_of_year": d.isocalendar()[1],
                "daily_admitted": admitted,
                "daily_deaths": deaths.get(d, 0),
            }
        )
        d += timedelta(days=1)
    return rows


def add_features(rows):
    admitted = [r["daily_admitted"] for r in rows]
    deaths = [r["daily_deaths"] for r in rows]
    n = len(rows)

    for i, r in enumerate(rows):
        r["cumulative_admitted"] = sum(admitted[: i + 1])
        r["cumulative_deaths"] = sum(deaths[: i + 1])
        r["roll7_admitted"] = sum(admitted[max(0, i - 6) : i + 1])
        r["roll14_admitted"] = sum(admitted[max(0, i - 13) : i + 1])
        r["roll7_deaths"] = sum(deaths[max(0, i - 6) : i + 1])
        r["lag1_admitted"] = admitted[i - 1] if i >= 1 else 0
        r["lag2_admitted"] = admitted[i - 2] if i >= 2 else 0
        r["lag3_admitted"] = admitted[i - 3] if i >= 3 else 0
        r["lag7_admitted"] = admitted[i - 7] if i >= 7 else 0
        r["lag1_deaths"] = deaths[i - 1] if i >= 1 else 0
        r["lag7_deaths"] = deaths[i - 7] if i >= 7 else 0
    return rows


def main():
    print("Fetching year data...")
    all_rows = []
    for year in YEARS:
        rows = build_year_dataset(year)
        print(f"  {year}: {len(rows)} daily rows")
        all_rows.extend(rows)

    all_rows = add_features(all_rows)

    fields = [
        "date", "year", "month", "day", "day_of_year", "week_of_year",
        "daily_admitted", "daily_deaths",
        "cumulative_admitted", "cumulative_deaths",
        "roll7_admitted", "roll14_admitted", "roll7_deaths",
        "lag1_admitted", "lag2_admitted", "lag3_admitted", "lag7_admitted",
        "lag1_deaths", "lag7_deaths",
    ]

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(all_rows)

    total = len(all_rows)
    admitted_sum = sum(r["daily_admitted"] for r in all_rows)
    deaths_sum = sum(r["daily_deaths"] for r in all_rows)
    print(f"\nWrote {OUT_FILE}")
    print(f"  rows: {total}  ({YEARS[0]}-{YEARS[-1]})")
    print(f"  total admitted: {admitted_sum}")
    print(f"  total deaths:   {deaths_sum}")


if __name__ == "__main__":
    sys.exit(main())
