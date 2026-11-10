"""Delhi hourly PM2.5 and PM10 from Earthmetry Signals (`signalsfunc.read_cpcb`),
cached in a temp file so the API is called at most once an hour.

    read_cpcb(['PM25', 'PM10'], start, end,
              city_names_to_filter=['Delhi'], aggregate_to_city=True)

`aggregate_to_city=True` averages all CPCB CAAQMS stations tagged city = Delhi
into one value per hour. The value used is `avg_of_average_value_in_hour`
(the stations' hourly averages, averaged across stations).

The cache (CPCB_HOURLY_CACHE, in the system temp dir) holds the raw long table
read_cpcb returns. `load()` reads it while it is under an hour old; past that
it calls read_cpcb again. If that fails (no `signalsfunc` in this environment,
upstream down) the old cache is used, however old, and the caller is told.

`signalsfunc` is a private package installed only in the server's
`geospatial` env. If the dashboard runs elsewhere, refresh the cache from that
env with cron instead:

    python ingestion/cpcb_hourly.py            # refresh now, print a summary
"""
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.logging_config import get_logger
from config.settings import CPCB_HOURLY_CACHE, IST

logger = get_logger(__name__)

CITY = "Delhi"
PARAMETERS = ["PM25", "PM10"]
VALUE_COL = "avg_of_average_value_in_hour"
LOOKBACK_DAYS = 7
MAX_AGE_SECONDS = 3600
RENAME = {"PM25": "PM2.5", "PM10": "PM10"}


def fetch(days: int = LOOKBACK_DAYS) -> pd.DataFrame:
    """Raw long table from read_cpcb: the last `days` days up to the current IST hour."""
    from signalsfunc import read_cpcb  # private package, geospatial env only

    end = pd.Timestamp(datetime.now(IST).replace(tzinfo=None)).floor("h")
    start = (end - pd.Timedelta(days=days)).floor("D")
    df = read_cpcb(PARAMETERS, start, end, city_names_to_filter=[CITY], aggregate_to_city=True)
    if df is None or df.empty:
        raise ValueError(f"read_cpcb returned no rows for {CITY}, {start} to {end}")
    return df.sort_values(["parameter", "observation_hour_start"]).reset_index(drop=True)


def refresh(path: Path = CPCB_HOURLY_CACHE) -> pd.DataFrame:
    """Fetch and write the cache atomically (a reader never sees half a file)."""
    df = fetch()
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    df.to_csv(tmp, index=False)
    os.replace(tmp, path)
    logger.info("read_cpcb: %d rows for %s written to %s", len(df), CITY, path)
    return df


def cache_age(path: Path = CPCB_HOURLY_CACHE):
    """Seconds since the cache was written, or None if there is no cache."""
    try:
        return datetime.now().timestamp() - path.stat().st_mtime
    except OSError:
        return None


def load(path: Path = CPCB_HOURLY_CACHE, max_age: int = MAX_AGE_SECONDS):
    """(raw long table, fetched_at as IST datetime or None, stale: bool).

    Fresh cache -> read it. Otherwise call read_cpcb; on failure fall back to
    whatever cache exists (stale=True). Empty table when there's nothing."""
    age = cache_age(path)
    if age is None or age > max_age:
        try:
            refresh(path)
            age = cache_age(path)
        except Exception as e:  # missing package, network, upstream error
            logger.warning("read_cpcb refresh failed (%s: %s); using the existing cache", type(e).__name__, e)
    if age is None:
        return pd.DataFrame(), None, True
    try:
        raw = pd.read_csv(path)
    except (OSError, pd.errors.EmptyDataError):
        return pd.DataFrame(), None, True
    fetched_at = datetime.fromtimestamp(path.stat().st_mtime, IST)
    return raw, fetched_at, age > max_age


def to_wide(raw: pd.DataFrame) -> pd.DataFrame:
    """Long read_cpcb table -> time, PM2.5, PM10 (one row per hour, sorted)."""
    if raw.empty or not {"parameter", "observation_hour_start", VALUE_COL} <= set(raw.columns):
        return pd.DataFrame()
    df = raw.assign(time=pd.to_datetime(raw["observation_hour_start"]),
                    value=pd.to_numeric(raw[VALUE_COL], errors="coerce"))
    wide = df.pivot_table(index="time", columns="parameter", values="value", aggfunc="mean")
    wide = wide.rename(columns=RENAME).reset_index()
    wide.columns.name = None
    keep = ["time"] + [c for c in ("PM2.5", "PM10") if c in wide.columns]
    return wide[keep].sort_values("time").reset_index(drop=True)


if __name__ == "__main__":
    wide = to_wide(refresh())
    print(f"{len(wide)} hours, {wide['time'].min()} to {wide['time'].max()} -> {CPCB_HOURLY_CACHE}")
    print(wide.tail())
