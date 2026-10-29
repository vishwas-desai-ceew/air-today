"""Open-Meteo forecast for central Delhi -> data/meteo_api_hourly.csv

One plain JSON request (no API key, CC-BY 4.0). Replaces meteo_api.py's
openmeteo_requests/requests_cache/retry_requests stack and its
"variable order must match" FlatBuffers parsing, and adds the extra fields the
weather cards need (humidity, wind direction, apparent temperature, cloud,
visibility).

`fetch_live()` is called by the dashboard (cached 5 min, auto-refreshed): it
takes OBSERVED values from the METAR reports of Safdarjung (VIDD, IMD's
reference station for Delhi; IGI airport VIDP as fallback) via NOAA's
aviationweather.gov API (no key, refreshed every 30 min), and fills the gaps
METAR doesn't report (feels-like, mixing height, daily high/low) from the
Open-Meteo model.

Usage (cron, daily ~17:30 IST):  python ingestion/weather.py
"""
import sys
import math
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

PARENT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PARENT_DIR))
from config.settings import DELHI_LAT, DELHI_LON, HTTP_HEADERS, IST, METEO_HOURLY_CSV, OPEN_METEO_FORECAST_URL
from config.logging_config import get_logger

logger = get_logger(__name__)

HOURLY_VARS = [
    "temperature_2m", "boundary_layer_height", "wind_speed_10m", "rain",
    "relative_humidity_2m", "wind_direction_10m", "precipitation_probability",
]
CURRENT_VARS = [
    "temperature_2m", "apparent_temperature", "relative_humidity_2m", "wind_speed_10m",
    "wind_direction_10m", "surface_pressure", "cloud_cover", "precipitation", "visibility",
    "is_day", "weather_code",
]
DAILY_VARS = ["temperature_2m_max", "temperature_2m_min", "sunrise", "sunset", "uv_index_max"]


def _request(params, attempts=3):
    base = {
        "latitude": DELHI_LAT,
        "longitude": DELHI_LON,
        "timezone": "Asia/Kolkata",
        "wind_speed_unit": "ms",
        "models": "best_match",
    }
    last_error = None
    for attempt in range(attempts):
        try:
            r = requests.get(OPEN_METEO_FORECAST_URL, params={**base, **params}, headers=HTTP_HEADERS, timeout=20)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            last_error = e
            time.sleep(2 ** attempt)
    raise last_error


def fetch_hourly(forecast_days=3) -> pd.DataFrame:
    data = _request({"hourly": ",".join(HOURLY_VARS), "forecast_days": forecast_days})
    df = pd.DataFrame(data["hourly"]).rename(columns={"time": "date"})
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize("Asia/Kolkata")
    return df


def fetch_current() -> dict:
    """Current conditions + today's min/max and the hourly BLH for this hour."""
    data = _request({
        "current": ",".join(CURRENT_VARS),
        "daily": ",".join(DAILY_VARS),
        "hourly": "boundary_layer_height",
        "past_days": 1,
        "forecast_days": 2,
    })
    current = dict(data["current"])
    # Open-Meteo's "today" can lag around midnight IST, so match on the date explicitly
    today = current["time"][:10]
    day_idx = data["daily"]["time"].index(today) if today in data["daily"]["time"] else -1
    current.update({k: v[day_idx] for k, v in data["daily"].items() if k != "time"})
    hour = current["time"][:13]
    for t, blh in zip(data["hourly"]["time"], data["hourly"]["boundary_layer_height"]):
        if t.startswith(hour):
            current["boundary_layer_height"] = blh
            break
    current["source"] = "Open-Meteo"
    return current


METAR_URL = "https://aviationweather.gov/api/data/metar"
METAR_STATIONS = {"VIDD": "Safdarjung", "VIDP": "IGI Airport"}
METAR_WEATHER = {  # present-weather codes most relevant to Delhi
    "TS": "Thunderstorm", "RA": "Rain", "DZ": "Drizzle", "SH": "Showers", "FG": "Fog",
    "BR": "Mist", "HZ": "Haze", "FU": "Smoke", "DU": "Dust", "SA": "Sand",
}
METAR_CLOUDS = {"SKC": "Clear sky", "CLR": "Clear sky", "NSC": "Clear sky", "CAVOK": "Clear sky",
                "FEW": "Mostly clear", "SCT": "Partly cloudy", "BKN": "Mostly cloudy", "OVC": "Overcast"}


def _relative_humidity(temp_c, dewpoint_c):
    """Magnus formula - METAR reports dew point, not humidity."""
    a, b = 17.625, 243.04
    return round(100 * math.exp(a * dewpoint_c / (b + dewpoint_c) - a * temp_c / (b + temp_c)))


def describe_metar(obs) -> str:
    wx = (obs.get("wxString") or "").strip()
    if wx:
        intensity = "Light " if wx.startswith("-") else "Heavy " if wx.startswith("+") else ""
        words = [label for code, label in METAR_WEATHER.items() if code in wx]
        if words:
            return (intensity + " and ".join(words[:2])).strip().capitalize()
    return METAR_CLOUDS.get(obs.get("cover") or "", "")


def fetch_metar() -> dict:
    """Latest observation from Safdarjung, else IGI. Units converted to the
    dashboard's (m/s, metres, %)."""
    r = requests.get(METAR_URL, params={"ids": ",".join(METAR_STATIONS), "format": "json"},
                     headers=HTTP_HEADERS, timeout=15)
    r.raise_for_status()
    by_station = {m["icaoId"]: m for m in r.json()}
    for icao, name in METAR_STATIONS.items():
        obs = by_station.get(icao)
        if not obs or obs.get("temp") is None:
            continue
        observed = datetime.fromtimestamp(obs["obsTime"], IST)
        out = {
            "temperature_2m": float(obs["temp"]),
            "observed_at": observed.isoformat(timespec="minutes"),
            "station": f"{name} ({icao})",
            "condition": describe_metar(obs),
        }
        if obs.get("dewp") is not None:
            out["relative_humidity_2m"] = _relative_humidity(obs["temp"], obs["dewp"])
        if obs.get("wspd") is not None:
            out["wind_speed_10m"] = round(obs["wspd"] * 0.514444, 1)   # knots -> m/s
        if isinstance(obs.get("wdir"), (int, float)):                    # "VRB" for variable
            out["wind_direction_10m"] = obs["wdir"]
        visib = obs.get("visib")
        if isinstance(visib, (int, float)):
            out["visibility"] = round(visib * 1609.344, -2)              # statute miles -> m
        if obs.get("altim") is not None:
            out["surface_pressure"] = obs["altim"]
        return out
    raise ValueError("No usable METAR for Delhi stations")


def fetch_live() -> dict:
    """Open-Meteo model fields, overwritten by observed METAR values where available."""
    current = fetch_current()
    current["source"] = "Open-Meteo model"
    current["observed_at"] = None
    try:
        obs = fetch_metar()
        current.update(obs)
        current["source"] = f"Observed at {obs['station']} (METAR) · gaps from Open-Meteo"
    except Exception as e:
        logger.warning("METAR unavailable, using Open-Meteo only: %s", e)
    return current


def run() -> dict:
    df = fetch_hourly()
    tmp = METEO_HOURLY_CSV.with_suffix(".csv.tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(METEO_HOURLY_CSV)
    logger.info("Open-Meteo hourly forecast written (%d rows)", len(df))
    return {"rows": len(df), "from": str(df["date"].min()), "to": str(df["date"].max())}


if __name__ == "__main__":
    print(run())
