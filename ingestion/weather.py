"""Open-Meteo forecast for central Delhi -> data/meteo_api_hourly.csv

One plain JSON request (no API key, CC-BY 4.0). Replaces meteo_api.py's
openmeteo_requests/requests_cache/retry_requests stack and its
"variable order must match" FlatBuffers parsing, and adds the extra fields the
weather cards need (humidity, wind direction, apparent temperature, cloud,
visibility).

`fetch_current()` is also called live by the dashboard (cached 15 min), so the
weather cards show conditions now rather than at the last cron run.

Usage (cron, daily ~17:30 IST):  python ingestion/weather.py
"""
import sys
import time
from pathlib import Path

import pandas as pd
import requests

PARENT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PARENT_DIR))
from config.settings import DELHI_LAT, DELHI_LON, HTTP_HEADERS, METEO_HOURLY_CSV, OPEN_METEO_FORECAST_URL
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


def run() -> dict:
    df = fetch_hourly()
    tmp = METEO_HOURLY_CSV.with_suffix(".csv.tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(METEO_HOURLY_CSV)
    logger.info("Open-Meteo hourly forecast written (%d rows)", len(df))
    return {"rows": len(df), "from": str(df["date"].min()), "to": str(df["date"].max())}


if __name__ == "__main__":
    print(run())
