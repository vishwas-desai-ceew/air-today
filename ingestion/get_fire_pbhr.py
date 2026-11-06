"""Daily satellite fire counts for Punjab and Haryana, one CSV per state.

    data/fires_punjab.csv, data/fires_haryana.csv
    date,NOAA/VIIRS,Aqua/MODIS,Terra/MODIS

Each instrument is a separate column because each satellite detects the same
fires on its own overpass: the columns are not additive.

Counts come from the private `signalsfunc` package (NASA active fires), so
this step runs in the `geospatial` environment on the server. Only the fetch
imports it; the read/write helpers below work anywhere.

Every run re-fetches the last few days and overwrites them, so a day NASA
fills in late, or a day a run missed, is corrected next time.

    python ingestion/get_fire_pbhr.py                          # last 3 days
    python ingestion/get_fire_pbhr.py --from 2026-09-15        # backfill to yesterday
    python ingestion/get_fire_pbhr.py --from 2026-10-01 --to 2026-10-31
"""
import argparse
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.logging_config import get_logger
from config.settings import FIRE_INSTRUMENTS, FIRE_STATE_CSVS, IST

logger = get_logger(__name__)

STATE_CODES = {"Punjab": "IN-PB", "Haryana": "IN-HR"}
CONFIDENCE_LEVELS = ["1.Low", "2.Nominal", "3.High"]
LOOKBACK_DAYS = 3
COLUMNS = ["date"] + FIRE_INSTRUMENTS


def fetch_day(day: date) -> pd.DataFrame:
    """Raw per-state, per-instrument counts for one day from signalsfunc."""
    from signalsfunc import read_nasa_active_fires  # private package, geospatial env only

    start = pd.Timestamp(day)
    end = start + pd.Timedelta(hours=23)
    return read_nasa_active_fires(
        start, end,
        confidence_levels_to_filter=CONFIDENCE_LEVELS,
        state_codes_to_filter=list(STATE_CODES.values()),
        spatial_aggregation_level="state",
        temporal_aggregation_level="day",
        split_by_satellite=True,
    )


def to_state_rows(raw: pd.DataFrame, day: date) -> dict:
    """{state: {date, instrument: count, ...}} for one day.

    An empty result means NASA returned nothing for the day (usually not yet
    published), so no row is written rather than recording zeros. When the
    day has data, an instrument or state with no rows had no detections: 0."""
    if raw is None or raw.empty:
        return {}
    unknown = set(raw["satellite_instrument"]) - set(FIRE_INSTRUMENTS)
    if unknown:
        logger.info("Ignoring instruments not tracked in the state CSVs: %s", sorted(unknown))
    counts = raw.groupby(["state_name", "satellite_instrument"])["count_of_incidents"].sum()
    rows = {}
    for state in FIRE_STATE_CSVS:
        row = {"date": day.isoformat()}
        for inst in FIRE_INSTRUMENTS:
            row[inst] = int(counts.get((state, inst), 0))
        rows[state] = row
    return rows


def read_state_fires(state: str) -> pd.DataFrame:
    """The state's CSV, sorted by date; empty frame with the right columns if missing."""
    try:
        df = pd.read_csv(FIRE_STATE_CSVS[state])
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return pd.DataFrame(columns=COLUMNS)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    for inst in FIRE_INSTRUMENTS:
        if inst not in df.columns:
            df[inst] = 0
    return df[COLUMNS].sort_values("date").reset_index(drop=True)


def upsert(csv_path: Path, new_rows: list) -> None:
    """Write rows into the CSV, replacing any existing row for the same date."""
    if not new_rows:
        return
    new = pd.DataFrame(new_rows, columns=COLUMNS)
    try:
        old = pd.read_csv(csv_path)
        old = old[~old["date"].astype(str).isin(new["date"])]
        df = pd.concat([old, new], ignore_index=True)
    except (FileNotFoundError, pd.errors.EmptyDataError):
        df = new
    df = df.sort_values("date")[COLUMNS]
    tmp = csv_path.with_suffix(".csv.tmp")
    df.to_csv(tmp, index=False, encoding="utf-8")
    tmp.replace(csv_path)


def run(start: date = None, end: date = None) -> dict:
    """Fetch [start, end] (default: the last LOOKBACK_DAYS days to yesterday, IST)."""
    yesterday = datetime.now(IST).date() - timedelta(days=1)
    end = end or yesterday
    start = start or end - timedelta(days=LOOKBACK_DAYS - 1)
    per_state = {state: [] for state in FIRE_STATE_CSVS}
    no_data = []
    day = start
    while day <= end:
        rows = to_state_rows(fetch_day(day), day)
        if not rows:
            no_data.append(day.isoformat())
            logger.warning("No fire data returned for %s (not published yet?)", day)
        for state, row in rows.items():
            per_state[state].append(row)
        day += timedelta(days=1)
    for state, rows in per_state.items():
        upsert(FIRE_STATE_CSVS[state], rows)
    written = len(per_state["Punjab"])
    logger.info("Fires %s..%s: %d day(s) written, %d with no data", start, end, written, len(no_data))
    return {"from": start.isoformat(), "to": end.isoformat(), "days_written": written, "no_data": no_data}


def main():
    parser = argparse.ArgumentParser(description="Fetch Punjab/Haryana fire counts per instrument")
    parser.add_argument("--from", dest="start", type=date.fromisoformat, help="first day, YYYY-MM-DD")
    parser.add_argument("--to", dest="end", type=date.fromisoformat, help="last day, YYYY-MM-DD (default yesterday)")
    args = parser.parse_args()
    print(run(args.start, args.end))


if __name__ == "__main__":
    main()
