#!/usr/bin/env python3
"""Fetch daily historical meteorological data for Bangladesh (Dhaka) from Open-Meteo.

Timeline: 2023-11-01 to 2026-09-01
(Includes late 2023 to compute up to 42-day rolling/lag features without missing values).

Variables:
- temperature_2m_max, min, mean (°C)
- precipitation_sum (mm)
- relative_humidity_2m_mean (%)
- wind_speed_10m_max (km/h)
- shortwave_radiation_sum (MJ/m²)
"""

import csv
import json
import os
import sys
import urllib.request
import urllib.parse

OUT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "meteorological_data.csv")

# Dhaka coordinates (epicenter and national reference)
LAT = 23.8103
LON = 90.4125
START_DATE = "2023-11-01"
END_DATE = "2026-09-01"

PARAMS = {
    "latitude": LAT,
    "longitude": LON,
    "start_date": START_DATE,
    "end_date": END_DATE,
    "daily": "temperature_2m_max,temperature_2m_min,temperature_2m_mean,precipitation_sum,relative_humidity_2m_mean,wind_speed_10m_max,shortwave_radiation_sum",
    "timezone": "Asia/Dhaka",
}

BASE_URL = "https://archive-api.open-meteo.com/v1/archive"


def fetch_weather():
    url = BASE_URL + "?" + urllib.parse.urlencode(PARAMS)
    print(f"Fetching meteorological data from:\n{url}\n")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Research/Academic Dengue Modeling)"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    
    daily = data.get("daily", {})
    dates = daily.get("time", [])
    if not dates:
        raise ValueError("No daily data received from Open-Meteo API.")
    
    fields = [
        "date",
        "temp_max",
        "temp_min",
        "temp_mean",
        "precipitation",
        "humidity_mean",
        "wind_speed_max",
        "solar_radiation",
        "diurnal_temp_range",
    ]
    
    rows = []
    t_max = daily.get("temperature_2m_max", [])
    t_min = daily.get("temperature_2m_min", [])
    t_mean = daily.get("temperature_2m_mean", [])
    precip = daily.get("precipitation_sum", [])
    humidity = daily.get("relative_humidity_2m_mean", [])
    wind = daily.get("wind_speed_10m_max", [])
    solar = daily.get("shortwave_radiation_sum", [])
    
    for i, d in enumerate(dates):
        mx = t_max[i] if i < len(t_max) else None
        mn = t_min[i] if i < len(t_min) else None
        dtr = round(mx - mn, 2) if (mx is not None and mn is not None) else None
        
        rows.append({
            "date": d,
            "temp_max": mx,
            "temp_min": mn,
            "temp_mean": t_mean[i] if i < len(t_mean) else None,
            "precipitation": precip[i] if i < len(precip) else None,
            "humidity_mean": humidity[i] if i < len(humidity) else None,
            "wind_speed_max": wind[i] if i < len(wind) else None,
            "solar_radiation": solar[i] if i < len(solar) else None,
            "diurnal_temp_range": dtr,
        })
    
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Successfully saved {len(rows)} daily meteorological records to:")
    print(f"  {OUT_PATH}")
    print(f"Date range: {rows[0]['date']} to {rows[-1]['date']}")


if __name__ == "__main__":
    fetch_weather()

