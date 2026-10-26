"""IITM AQEWS (ews.tropmet.res.in) -> forecast CSVs, in two HTTP requests total.

Previously four scripts hit the same two pages separately (get_aqews_aqi.py,
get_pm25_aqews.py, get_aqi_fc_cat.py, get_v_index.py), and two of them sent
the bulletin text to Gemini to pull out a handful of numbers. The bulletin is
templated prose ("The ventilation index is likely to be 4800 m2/s on
25.10.2026, ..."), so plain regexes extract the same values deterministically,
for free, and fail loudly instead of hallucinating.

Writes:
  AQEWS_AQI_forecast.csv          daily AQI (PM2.5/PM10 sub-indices, overall, category)
  AQEWS_PM25_forecast.csv         2-hourly PM2.5 concentration
  ventilation_index_forecast.csv  date, mixing_depth, ventilation_index
  AQI_forecast_category.csv       date, category   (from the IMD/IITM bulletin text)

Usage (cron, daily ~17:30 IST):  python ingestion/aqews.py
"""
import re
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

PARENT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PARENT_DIR))
from config.settings import (
    AQEWS_10DAY_URL, AQEWS_AQI_CSV, AQEWS_CATEGORY_CSV, AQEWS_HOME_URL,
    AQEWS_PM25_CSV, HTTP_HEADERS, VENTILATION_CSV,
)
from config.logging_config import get_logger
from ingestion.cpcb_common import AQI_BINS, AQI_LABELS

logger = get_logger(__name__)

# Chart.js dataset variables on 10_days_forecast.php
CHART_VARS = {"pm25_conc": "datastack9", "aqi_pm25": "datastack17", "aqi_pm10": "datastack18"}

DATE_RE = r"(\d{1,2})\s*\.\s*(\d{1,2})\s*\.\s*((?:\d\s*){3}\d)"
CATEGORY_WORDS = r"(?:Good|Satisfactory|Moderate|Poor|Very Poor|Severe)"


def _fetch(url, timeout=40):
    r = requests.get(url, headers=HTTP_HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.text


def _to_date(d, m, y):
    return datetime(int(re.sub(r"\s", "", y)), int(m), int(d)).date()


# ------------------------------------------------------------ 10-day charts --
def extract_charts(html: str) -> dict:
    """Evaluates the Chart.js object literals once, returns {name: (labels, values)}."""
    from py_mini_racer import py_mini_racer

    soup = BeautifulSoup(html, "html.parser")
    script_text = "\n".join(s.get_text() for s in soup.find_all("script") if "datastack" in s.get_text())
    ctx = py_mini_racer.MiniRacer()
    charts = {}
    for name, var in CHART_VARS.items():
        m = re.search(rf"const\s+{var}\s*=\s*(\{{.*?\}});", script_text, re.S)
        if not m:
            logger.warning("AQEWS chart %s (%s) not found", name, var)
            continue
        ds = json.loads(ctx.eval(f"JSON.stringify({m.group(1)})"))
        charts[name] = (ds["labels"], ds["datasets"][0]["data"])
    return charts


def save_aqi_to_csv(df_pm25, df_pm10, out_path=AQEWS_AQI_CSV):
    """Hourly AQI sub-indices -> daily overall AQI. The +8h shift aligns AQEWS's
    timestamps with CPCB's 4 PM-to-4 PM bulletin day."""
    df_pm25 = df_pm25.copy()
    df_pm10 = df_pm10.copy()
    df_pm25["report_date"] = (df_pm25["datetime"] + pd.Timedelta(hours=8)).dt.date
    df_pm10["report_date"] = (df_pm10["datetime"] + pd.Timedelta(hours=8)).dt.date

    def daily(df, col):
        return (
            df.groupby("report_date")[col].mean().round().astype(int)
            .reset_index().rename(columns={"report_date": "date"})
        )

    df_daily = pd.merge(daily(df_pm25, "AQI_PM25"), daily(df_pm10, "AQI_PM10"), on="date", how="outer")
    df_daily["AQI_overall"] = df_daily[["AQI_PM25", "AQI_PM10"]].max(axis=1)
    df_daily["prominent_pollutant"] = (
        df_daily[["AQI_PM25", "AQI_PM10"]].idxmax(axis=1).str.replace("AQI_", "")
    )
    df_daily["category"] = pd.cut(
        df_daily["AQI_overall"], bins=AQI_BINS, labels=AQI_LABELS, right=True, include_lowest=True
    )
    df_daily.to_csv(out_path, index=False)
    return df_daily


def save_charts(charts: dict):
    if "aqi_pm25" in charts and "aqi_pm10" in charts:
        (l25, v25), (l10, v10) = charts["aqi_pm25"], charts["aqi_pm10"]
        df_pm25 = pd.DataFrame({"datetime": pd.to_datetime(l25), "AQI_PM25": v25})
        df_pm10 = pd.DataFrame({"datetime": pd.to_datetime(l10), "AQI_PM10": v10})
        save_aqi_to_csv(df_pm25, df_pm10)
    if "pm25_conc" in charts:
        labels, values = charts["pm25_conc"]
        df = pd.DataFrame({"time": pd.to_datetime(labels), "PM2.5": pd.to_numeric(values, errors="coerce").round(2)})
        df.to_csv(AQEWS_PM25_CSV, index=False)


# ----------------------------------------------------------- bulletin text --
def bulletin_text(html: str) -> str:
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text)


def parse_bulletin(text: str) -> dict:
    """Pulls mixing depth, ventilation index and AQ category per date out of the
    IMD/IITM Delhi bulletin prose."""
    text = re.sub(r"\s+", " ", text)
    out = {"mixing_depth": {}, "ventilation_index": {}, "category": {}, "outlook": None}

    m = re.search(r"mixing depth is likely to be(.*?)over Delhi", text, re.I)
    if m:
        for value, d, mo, y in re.findall(rf"(\d+)\s*m\s+on\s+{DATE_RE}", m.group(1)):
            out["mixing_depth"][_to_date(d, mo, y)] = int(value)

    m = re.search(r"ventilation index is likely to be(.*?)over Delhi", text, re.I)
    if m:
        for value, d, mo, y in re.findall(rf"(\d+)\s*m\s*2?\s*/\s*s\s+on\s+{DATE_RE}", m.group(1)):
            out["ventilation_index"][_to_date(d, mo, y)] = int(value)

    cat_re = rf"in the ({CATEGORY_WORDS}(?:\s+to\s+{CATEGORY_WORDS})?) category (?:on {DATE_RE}|from {DATE_RE} to {DATE_RE})"
    for cat, d, mo, y, d1, m1, y1, d2, m2, y2 in re.findall(cat_re, text, re.I):
        if d:
            out["category"][_to_date(d, mo, y)] = cat.strip()
        else:
            start, end = _to_date(d1, m1, y1), _to_date(d2, m2, y2)
            while start <= end:
                out["category"][start] = cat.strip()
                start += timedelta(days=1)

    m = re.search(rf"outlook for the subsequent (\d+) days?.*?in the ({CATEGORY_WORDS}(?:\s+to\s+{CATEGORY_WORDS})?) category", text, re.I)
    if m:
        out["outlook"] = f"{m.group(2)} over the following {m.group(1)} days"
    return out


def save_bulletin(parsed: dict):
    days = sorted(set(parsed["mixing_depth"]) | set(parsed["ventilation_index"]))
    if days:
        pd.DataFrame({
            "date": days,
            "mixing_depth": [parsed["mixing_depth"].get(d) for d in days],
            "ventilation_index": [parsed["ventilation_index"].get(d) for d in days],
        }).to_csv(VENTILATION_CSV, index=False)
    else:
        logger.warning("No ventilation index found in AQEWS bulletin")
    if parsed["category"]:
        cats = sorted(parsed["category"].items())
        pd.DataFrame(cats, columns=["date", "category"]).to_csv(AQEWS_CATEGORY_CSV, index=False)
    else:
        logger.warning("No AQ category found in AQEWS bulletin")


def run() -> dict:
    """Both AQEWS pages, each fetched once. Each half fails independently."""
    result = {}
    try:
        charts = extract_charts(_fetch(AQEWS_10DAY_URL))
        save_charts(charts)
        result["charts"] = sorted(charts)
    except Exception as e:
        logger.error("AQEWS 10-day charts failed: %s", e)
        result["charts_error"] = str(e)
    try:
        parsed = parse_bulletin(bulletin_text(_fetch(AQEWS_HOME_URL)))
        save_bulletin(parsed)
        result["bulletin_days"] = len(parsed["category"])
        result["outlook"] = parsed["outlook"]
    except Exception as e:
        logger.error("AQEWS bulletin failed: %s", e)
        result["bulletin_error"] = str(e)
    if "charts_error" in result and "bulletin_error" in result:
        raise RuntimeError(f"AQEWS unavailable: {result['charts_error']}")
    return result


if __name__ == "__main__":
    print(run())
