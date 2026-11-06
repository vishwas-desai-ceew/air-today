"""CPCB daily AQI bulletin -> data/delhi_aqi_cpcb.csv

Replaces the old HEAD-then-GET / first-table / substring-matching logic in
download_cpcb_bulletin.py, which had three silent failure modes:

1. cpcb.nic.in now 301-redirects to cpcb.gov.in; the HEAD check didn't follow
   redirects, so the NCR bulletin was always treated as missing.
2. The NCR bulletin now lists Delhi under District="OuterNorth",
   City/Town="Delhi", on page 2 - matching District=="Delhi" on page 1 fails.
3. extract_pollutants() matched bare substrings ("O", "NO", "PM"), so almost
   every row was tagged "PM2.5, PM10, NO2, SO2, O3".

Usage (cron, after 16:15 IST):  python ingestion/cpcb.py [--backfill 7]
"""
import re
import sys
import time
import argparse
from io import BytesIO
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import pdfplumber
import requests

PARENT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PARENT_DIR))
from config.settings import CPCB_AQI_CSV, HTTP_HEADERS, IST, effective_today
from config.logging_config import get_logger
from ingestion.cpcb_common import AQI_LABELS, aqi_category, build_cpcb_urls

logger = get_logger(__name__)

CSV_COLUMNS = ["date", "aqi", "category", "pollutant", "stations", "source"]
POLLUTANT_ORDER = ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3", "NH3", "Pb"]
POLLUTANT_ALIASES = {
    "PM2.5": "PM2.5", "PM25": "PM2.5",
    "PM10": "PM10",
    "NO2": "NO2", "NITROGENDIOXIDE": "NO2",
    "SO2": "SO2", "SULPHURDIOXIDE": "SO2", "SULFURDIOXIDE": "SO2",
    "CO": "CO", "CARBONMONOXIDE": "CO",
    "O3": "O3", "OZONE": "O3",
    "NH3": "NH3", "AMMONIA": "NH3",
    "PB": "Pb", "LEAD": "Pb",
}
MONTH_ABBR = "Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"


class BulletinNotFound(Exception):
    pass


# ---------------------------------------------------------------- download --
def _get(url, attempts=3, timeout=30):
    """GET with redirects, TLS verification and a short backoff. Returns None on 404."""
    last_error = None
    for attempt in range(attempts):
        try:
            r = requests.get(url, headers=HTTP_HEADERS, timeout=timeout, allow_redirects=True)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            if not r.content.startswith(b"%PDF"):
                # CPCB serves an HTML error page with 200 for some missing files
                return None
            return r.content
        except requests.RequestException as e:
            last_error = e
            time.sleep(2 ** attempt)
    raise last_error


def fetch_bulletin(day: date):
    """Returns (pdf_bytes, source_label). NCR bulletin first, national as fallback."""
    primary, fallback = build_cpcb_urls(day.strftime("%Y_%m_%d"))
    for url, label in ((primary, "CPCB NCR bulletin"), (fallback, "CPCB national bulletin")):
        content = _get(url)
        if content:
            logger.info("Fetched %s for %s", label, day)
            return content, label
    raise BulletinNotFound(f"No CPCB bulletin published for {day}")


# ----------------------------------------------------------------- parsing --
def _clean(cell):
    return re.sub(r"\s+", " ", cell or "").strip()


def normalise_pollutants(text) -> str:
    """'PM\\n2.5, PM\\n10' / 'OZONE,PM10' / 'PM2.5, O3' -> 'PM2.5, PM10'.
    Splits on commas and maps whole tokens - never bare substrings."""
    if not isinstance(text, str) or not text.strip():
        return ""
    found = set()
    for token in re.split(r"[,/&]|\band\b", text.upper()):
        key = re.sub(r"[^A-Z0-9.]", "", token)
        if key in POLLUTANT_ALIASES:
            found.add(POLLUTANT_ALIASES[key])
    return ", ".join(p for p in POLLUTANT_ORDER if p in found)


def _column_map(header):
    cols = {}
    for i, raw in enumerate(header):
        h = _clean(raw).lower()
        if "index" in h:
            cols["aqi"] = i
        elif "air quality" in h:
            cols["category"] = i
        elif "prominent" in h or "pollutant" in h:
            cols["pollutant"] = i
        elif "city" in h:
            cols["city"] = i
        elif "district" in h:
            cols["district"] = i
        elif "station" in h:
            cols["stations"] = i
    return cols


def _find_delhi_row(pdf):
    """Scans every table on every page. Tables continuing across pages reuse the
    last header seen."""
    cols = None
    for page in pdf.pages:
        for table in page.extract_tables():
            for row in table:
                candidate = _column_map(row)
                if "aqi" in candidate and ("city" in candidate or "district" in candidate):
                    cols = candidate
                    continue
                if cols is None:
                    continue
                place_idx = cols.get("city", cols.get("district"))
                if place_idx is not None and place_idx < len(row) and _clean(row[place_idx]).lower() == "delhi":
                    return row, cols
    return None, None


def _bulletin_date(text):
    m = re.search(rf"({MONTH_ABBR})[a-z]*\.?\s+(\d{{1,2}}),\s+(\d{{4}})", text)
    if not m:
        return None
    return datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%b %d %Y").date()


def parse_bulletin(pdf_bytes: bytes, expected_date: date | None = None) -> dict:
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        first_text = pdf.pages[0].extract_text() or ""
        bulletin_date = _bulletin_date(first_text)
        if expected_date and bulletin_date and bulletin_date != expected_date:
            raise ValueError(f"Bulletin is dated {bulletin_date}, expected {expected_date}")
        row, cols = _find_delhi_row(pdf)

    if row is None:
        raise ValueError("Delhi row not found in any table of the bulletin")

    aqi_text = re.sub(r"\D", "", row[cols["aqi"]] or "")
    if not aqi_text:
        raise ValueError(f"Delhi row has no index value: {row}")
    aqi = int(aqi_text)

    category = _clean(row[cols["category"]]) if "category" in cols else ""
    if category not in AQI_LABELS:
        category = aqi_category(aqi)
    elif category != aqi_category(aqi):
        logger.warning("CPCB category %s disagrees with AQI %s", category, aqi)

    return {
        "date": (expected_date or bulletin_date).strftime("%Y-%m-%d"),
        "aqi": aqi,
        "category": category,
        "pollutant": normalise_pollutants(row[cols["pollutant"]]) if "pollutant" in cols else "",
        "stations": _clean(row[cols["stations"]]) if "stations" in cols else "",
    }


# ----------------------------------------------------------------- storage --
def upsert_aqi(entry: dict, csv_path=CPCB_AQI_CSV):
    """Insert or replace the row for entry['date'] (previously a failed day's
    NaN row could never be overwritten by a later successful run)."""
    csv_path = Path(csv_path)
    new_row = pd.DataFrame([entry])
    if csv_path.exists():
        existing = pd.read_csv(csv_path, dtype={"date": str})
        existing = existing[existing["date"] != entry["date"]]
        combined = pd.concat([existing, new_row], ignore_index=True)
    else:
        combined = new_row
    for col in CSV_COLUMNS:
        if col not in combined.columns:
            combined[col] = ""
    combined = combined[CSV_COLUMNS].sort_values("date")
    tmp = csv_path.with_suffix(".csv.tmp")
    combined.to_csv(tmp, index=False, encoding="utf-8")
    tmp.replace(csv_path)


def existing_dates(csv_path=CPCB_AQI_CSV) -> set:
    if not Path(csv_path).exists():
        return set()
    df = pd.read_csv(csv_path, dtype={"date": str})
    return set(df.loc[df["aqi"].notna(), "date"])


def update_day(day: date, csv_path=CPCB_AQI_CSV) -> dict:
    pdf_bytes, source = fetch_bulletin(day)
    entry = parse_bulletin(pdf_bytes, expected_date=day)
    entry["source"] = source
    upsert_aqi(entry, csv_path)
    logger.info("CPCB AQI %s: %s (%s, %s)", entry["date"], entry["aqi"], entry["category"], entry["pollutant"])
    return entry


def run(backfill_days: int = 7, csv_path=CPCB_AQI_CSV) -> dict:
    """Fetch the latest bulletin, and quietly fill any gaps in the last `backfill_days`.

    CPCB publishes at ~16:00 IST, ahead of the dashboard's 17:57 cutoff, so try
    the calendar date first and only fall back to the previous day."""
    today = datetime.now(IST).date()
    have = existing_dates(csv_path)
    try:
        latest = update_day(today, csv_path)
    except BulletinNotFound:
        today = effective_today()
        if today.strftime("%Y-%m-%d") in have:
            raise
        latest = update_day(today, csv_path)
    for offset in range(1, backfill_days + 1):
        day = today - timedelta(days=offset)
        if day.strftime("%Y-%m-%d") in have:
            continue
        try:
            update_day(day, csv_path)
        except Exception as e:
            logger.warning("Backfill %s skipped: %s", day, e)
    return latest


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--backfill", type=int, default=7, help="days of gaps to fill")
    args = parser.parse_args()
    run(backfill_days=args.backfill)


if __name__ == "__main__":
    main()
