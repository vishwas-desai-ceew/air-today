"""Single read layer for the dashboard.

Every page used to open its own CSV/JSON with its own path logic and its own
(or no) caching. All reads now go through here: cached, tolerant of missing
files, and pointing at the same paths the ingestion scripts write
(config/settings.py).
"""
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from config.settings import (
    AQEWS_AQI_CSV, AQEWS_CATEGORY_CSV, ARCHIVE_TEMP, CPCB_AQI_CSV, FIRE_CSV, IMD_BULLETIN_PDF, INSIGHTS_JSON,
    IST, METEO_HOURLY_CSV, PIPELINE_STATUS_JSON, VENTILATION_CSV, effective_today,
)
from ingestion.json_store import read_json


def _read_csv(path, **kwargs):
    try:
        return pd.read_csv(path, **kwargs)
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return pd.DataFrame()


@st.cache_data(ttl=600)
def cpcb_history() -> pd.DataFrame:
    df = _read_csv(CPCB_AQI_CSV)
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["aqi"] = pd.to_numeric(df["aqi"], errors="coerce")
    return df.sort_values("date")


def aqi_today_and_yesterday():
    """(today_row, yesterday_row) as dicts, either may be None."""
    df = cpcb_history()
    if df.empty:
        return None, None
    today = effective_today()
    by_date = {r["date"]: r for r in df.dropna(subset=["aqi"]).to_dict("records")}
    return by_date.get(today), by_date.get(today - timedelta(days=1))


@st.cache_data(ttl=600)
def aqews_daily() -> pd.DataFrame:
    df = _read_csv(AQEWS_AQI_CSV)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


@st.cache_data(ttl=600)
def bulletin_forecast() -> pd.DataFrame:
    """date, mixing_depth, ventilation_index, category from the AQEWS bulletin text."""
    vi = _read_csv(VENTILATION_CSV)
    cat = _read_csv(AQEWS_CATEGORY_CSV)
    for df in (vi, cat):
        if not df.empty:
            df.columns = df.columns.str.strip()
            df["date"] = pd.to_datetime(df["date"]).dt.date
    if vi.empty:
        return cat
    if cat.empty:
        return vi
    return vi.merge(cat, on="date", how="outer").sort_values("date")


def forecast_for(day):
    """Best available outlook for `day`: AQEWS numeric AQI, else the bulletin's category."""
    out = {"aqi": None, "category": None, "ventilation_index": None, "mixing_depth": None}
    df = aqews_daily()
    if not df.empty:
        row = df[df["date"] == day]
        if not row.empty:
            out["aqi"] = int(round(row.iloc[0]["AQI_overall"]))
            out["category"] = row.iloc[0]["category"]
    bf = bulletin_forecast()
    if not bf.empty:
        row = bf[bf["date"] == day]
        if not row.empty:
            r = row.iloc[0]
            for key in ("ventilation_index", "mixing_depth"):
                if key in r and pd.notna(r[key]):
                    out[key] = int(r[key])
            if out["category"] is None and "category" in r and pd.notna(r["category"]):
                out["category"] = r["category"]
    return out


@st.cache_data(ttl=600)
def meteo_hourly() -> pd.DataFrame:
    df = _read_csv(METEO_HOURLY_CSV)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"], utc=True).dt.tz_convert(IST)
    return df


@st.cache_data(ttl=300, show_spinner=False)
def current_weather() -> dict:
    """Observed METAR conditions (Safdarjung) + Open-Meteo gaps, 5-min cache.
    Falls back to the nearest hour of the last cron forecast if both APIs
    are unreachable."""
    from ingestion.weather import fetch_live

    try:
        return fetch_live()
    except Exception:
        df = meteo_hourly()
        if df.empty:
            return {}
        now = pd.Timestamp.now(tz=IST)
        row = df.iloc[(df["date"] - now).abs().argmin()].to_dict()
        row["time"] = row.pop("date").isoformat()
        row["source"] = "Open-Meteo (cached forecast)"
        return row


@st.cache_data(ttl=600)
def fire_counts(day):
    """{state: count} for `day`, or None if the fire feed hasn't covered it."""
    df = _read_csv(FIRE_CSV)
    if df.empty:
        return None
    dates = pd.to_datetime(df["date"]).dt.date
    if dates.max() < day:
        return None
    return df[dates == day].groupby("state_name")["count_of_incidents"].sum().to_dict()


SOURCE_FILES = {
    "cpcb": ("CPCB AQI", CPCB_AQI_CSV),
    "aqews": ("AQEWS forecast", AQEWS_AQI_CSV),
    "weather": ("Weather", METEO_HOURLY_CSV),
    "imd": ("IMD bulletin", IMD_BULLETIN_PDF),
    "fires": ("Farm fires", FIRE_CSV),
}


@st.cache_data(ttl=300)
def source_health() -> list[dict]:
    """One row per source for the sidebar panel: label, ok/stale/failed, when.

    Prefers data/pipeline_status.json (written by ingestion/run_daily.py) and
    falls back to file timestamps for setups still on the old per-script crons."""
    status = read_json(PIPELINE_STATUS_JSON)
    now = datetime.now(IST)
    rows = []
    for key, (label, path) in SOURCE_FILES.items():
        step = status.get(key, {})
        when = None
        if step.get("last_success"):
            when = datetime.fromisoformat(step["last_success"])
        elif path.exists():
            when = datetime.fromtimestamp(path.stat().st_mtime, IST)
        if step.get("ok") is False:
            state, note = "failed", step.get("error", "Last run failed")
        elif when is None:
            state, note = "missing", "No data yet"
        elif (now - when).total_seconds() > 30 * 3600:
            state, note = "stale", "Update overdue"
        else:
            state, note = "ok", "Up to date"
        rows.append({"key": key, "label": label, "state": state, "note": note, "when": when})
    return rows


@st.cache_data(ttl=600)
def insights_today() -> dict:
    """Structured daily update written by ingestion/get_aqi_summary.py."""
    return read_json(INSIGHTS_JSON)


@st.cache_data(ttl=600)
def daily_update_text() -> list:
    """The archived sentences for the latest update."""
    archive = read_json(ARCHIVE_TEMP)
    return next(iter(archive.values()), []) if archive else []
