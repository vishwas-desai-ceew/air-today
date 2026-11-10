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
    AQEWS_AQI_CSV, AQEWS_CATEGORY_CSV, AQEWS_SOURCES_JSON, ARCHIVE_TEMP, CPCB_AQI_CSV, CREAMS_BULLETIN_JSON, CREAMS_FIRES_CSV, CREAMS_HEADLINE_STATES, IMD_BULLETIN_PDF, INSIGHTS_JSON,
    IST, METEO_HOURLY_CSV, PIPELINE_STATUS_JSON, SIGNALS_HOURLY_CSV, VENTILATION_CSV, effective_today,
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


def cpcb_bulletin_url(row) -> str:
    """Link to the CPCB PDF a cpcb_history() row was read from: the NCR
    bulletin, or the national one when that was the fallback used."""
    from ingestion.cpcb_common import build_cpcb_urls
    ncr, national = build_cpcb_urls(row["date"].strftime("%Y_%m_%d"))
    return national if "national" in str(row.get("source") or "").lower() else ncr


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
    """Observed METAR conditions (IGI Airport, VIDP) + Open-Meteo gaps, 5-min cache.
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


@st.cache_data(ttl=600, show_spinner="Fetching hourly PM data from Earthmetry...")
def pm_hourly() -> tuple[pd.DataFrame, dict]:
    """Delhi hourly PM2.5 and PM10: (time, PM2.5, PM10 sorted; info).

    Live from signalsfunc.read_cpcb via an hour-long file cache
    (ingestion/cpcb_hourly.py). Falls back to the sample CSV only when no
    live data has ever been fetched. info = {source: live|sample, fetched_at, stale}."""
    from ingestion import cpcb_hourly

    raw, fetched_at, stale = cpcb_hourly.load()
    wide = cpcb_hourly.to_wide(raw)
    if not wide.empty:
        return wide, {"source": "live", "fetched_at": fetched_at, "stale": stale}
    return _pm_sample(), {"source": "sample", "fetched_at": None, "stale": True}


def _pm_sample() -> pd.DataFrame:
    df = _read_csv(SIGNALS_HOURLY_CSV)
    if df.empty or "observation_hour_start" not in df.columns:
        return pd.DataFrame()
    df = df.rename(columns={"observation_hour_start": "time", "PM25": "PM2.5"})
    df["time"] = pd.to_datetime(df["time"])
    keep = ["time"] + [c for c in ("PM2.5", "PM10") if c in df.columns]
    for c in keep[1:]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df[keep].sort_values("time").reset_index(drop=True)


@st.cache_data(ttl=600)
def creams_daily() -> pd.DataFrame:
    """date, state, events: CREAMS paddy residue burning events, 2020 onwards."""
    from ingestion.creams import read_daily
    return read_daily()


@st.cache_data(ttl=600)
def creams_events() -> pd.DataFrame:
    """One row per fire from the CREAMS bulletins (district, lat/lon, satellite, FRP)."""
    from ingestion.creams import read_events
    return read_events()


@st.cache_data(ttl=600)
def creams_bulletin() -> dict:
    """The latest CREAMS bulletin: number, dates, URL, highlights."""
    return read_json(CREAMS_BULLETIN_JSON)


def latest_fire_counts():
    """(date, {state: events}) for Punjab and Haryana from the newest CREAMS
    bulletin, or (None, None)."""
    from ingestion.creams import latest_headline
    return latest_headline(CREAMS_HEADLINE_STATES, creams_daily())


def with_live_fires(facts: dict, latest) -> dict:
    """Swap in a newer CREAMS bulletin than the summary saw (the evening
    CREAMS run lands after the afternoon summary). `latest` is (date, counts)."""
    day, counts = latest
    if not facts or day is None:
        return facts
    have = facts.get("fire_date")
    if facts.get("fires") is not None and have and datetime.fromisoformat(have).date() >= day:
        return facts
    return {**facts, "fire_date": day.isoformat(), "fires": {
        "total": sum(counts.values()), "punjab": counts.get("Punjab", 0), "haryana": counts.get("Haryana", 0)}}


SOURCE_FILES = {
    "cpcb": ("CPCB AQI", CPCB_AQI_CSV),
    "aqews": ("AQEWS forecast", AQEWS_AQI_CSV),
    "weather": ("Weather", METEO_HOURLY_CSV),
    "imd": ("IMD bulletin", IMD_BULLETIN_PDF),
    "creams": ("Paddy residue burning (CREAMS)", CREAMS_FIRES_CSV),
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
def _insights_snapshot() -> dict:
    return read_json(INSIGHTS_JSON)


def with_live_ventilation(facts: dict, lookup) -> dict:
    """Fill a missing ventilation index from the live AQEWS file. The summary
    is a snapshot: if the AQEWS step filled the CSV after the summary ran, the
    Overview (which reads the CSV live) would show a value that Key insights lacks."""
    if not facts or facts.get("ventilation_index") is not None or not facts.get("forecast_date"):
        return facts
    vi = lookup(datetime.fromisoformat(facts["forecast_date"]).date()).get("ventilation_index")
    return facts if vi is None else {**facts, "ventilation_index": float(vi)}


def insights_today() -> dict:
    """Structured daily update written by ingestion/get_aqi_summary.py, with
    the ventilation index filled live when the snapshot is missing it and the
    fires taken from the newest CREAMS bulletin."""
    return with_live_fires(with_live_ventilation(_insights_snapshot(), forecast_for), latest_fire_counts())


@st.cache_data(ttl=600)
def daily_update_text() -> list:
    """The archived sentences for the latest update."""
    archive = read_json(ARCHIVE_TEMP)
    return next(iter(archive.values()), []) if archive else []


@st.cache_data(ttl=1800, show_spinner=False)
def aqi_news() -> list[dict]:
    """Delhi air-quality headlines (The Hindu, TOI, NDTV feeds), 30-min cache.
    Shared by the header dropdown and the Recent trends page."""
    from ingestion.news import fetch_aqi_news
    return fetch_aqi_news(limit=15)


@st.cache_data(ttl=600)
def aqews_sources() -> dict:
    """AQEWS DSS source apportionment of Delhi's daily-mean PM2.5, saved by
    ingestion/aqews.py: date, local/non-local split and per-source shares."""
    return read_json(AQEWS_SOURCES_JSON) or {}
