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
  AQEWS_PM10_forecast.csv         2-hourly PM10 concentration
  aqews_bulletin.json             full text of the day's bulletin (title + numbered sections)
  ventilation_index_forecast.csv  date, mixing_depth, ventilation_index
  AQI_forecast_category.csv       date, category
  aqews_bulletin_days.csv         the bulletin's day cards in full (sky, temps, wind, MD, VI)
  aqews_source_apportionment.json DSS source shares of Delhi's daily-mean PM2.5

The home page was redesigned around 7 Nov 2026: the prose bulletin
("The ventilation index is likely to be ... on 25.10.2026") was replaced by
one card per day (section#ewsBulletin). The card parser is used first; the
prose parser stays as a fallback. If neither finds a forecast the run fails,
so the dashboard's health panel flags it instead of serving stale files.

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
    AQEWS_10DAY_URL, AQEWS_AQI_CSV, AQEWS_BULLETIN_JSON, AQEWS_CATEGORY_CSV, AQEWS_HOME_URL,
    AQEWS_BULLETIN_DAYS_CSV, AQEWS_PM10_CSV, AQEWS_PM25_CSV, AQEWS_SOURCES_JSON, HTTP_HEADERS, IST,
    VENTILATION_CSV,
)
from config.logging_config import get_logger
from ingestion.cpcb_common import AQI_BINS, AQI_LABELS
from ingestion.json_store import write_json_atomic

logger = get_logger(__name__)

# Chart.js dataset variables on 10_days_forecast.php
CHART_VARS = {"pm25_conc": "datastack9", "pm10_conc": "datastack10",
              "aqi_pm25": "datastack17", "aqi_pm10": "datastack18"}

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
    for key, col, path in (("pm25_conc", "PM2.5", AQEWS_PM25_CSV), ("pm10_conc", "PM10", AQEWS_PM10_CSV)):
        if key in charts:
            labels, values = charts[key]
            df = pd.DataFrame({"time": pd.to_datetime(labels), col: pd.to_numeric(values, errors="coerce").round(2)})
            df.to_csv(path, index=False)


# ----------------------------------------------------------- bulletin text --
def bulletin_text(html: str) -> str:
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text)


def extract_bulletin(html: str) -> dict:
    """The day's bulletin as shown on the AQEWS home page: English title and
    its paragraphs (numbered sections 1-5 and the closing links). The Hindi
    title line is dropped; the body on the page is English only."""
    soup = BeautifulSoup(html, "html.parser")
    box = soup.select_one("div.scrollbar.marq")
    if box is None:
        raise ValueError("AQEWS bulletin block (div.scrollbar.marq) not found")
    paras = [re.sub(r"\s+", " ", p.get_text(" ", strip=True)) for p in box.find_all("p")]
    paras = [p for p in paras if p]
    title = next((p for p in paras if "Bulletin for Delhi" in p), None)
    body = [p for p in paras if p != title and not re.search(r"[\u0900-\u097F]", p)]
    if not body:
        raise ValueError("AQEWS bulletin block is empty")
    m = re.search(DATE_RE, title or "")
    return {
        "title": title or "Air Quality and Weather Bulletin for Delhi",
        "date": _to_date(*m.groups()).isoformat() if m else None,
        "paragraphs": body,
        "source_url": AQEWS_HOME_URL,
        "fetched_at": datetime.now(IST).isoformat(timespec="minutes"),
    }


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


# ------------------------------------------------- bulletin day cards (new) --
NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")


def _infer_date(label: str, ref):
    """'Tue, 10 Nov' -> date, choosing the year that puts it closest to `ref`
    (the bulletin's issue date), so a card for 1 Jan issued on 31 Dec works."""
    m = re.search(r"(\d{1,2})\s+([A-Za-z]{3})", label or "")
    if not m:
        return None
    best = None
    for year in (ref.year - 1, ref.year, ref.year + 1):
        try:
            d = datetime.strptime(f"{m.group(1)} {m.group(2)} {year}", "%d %b %Y").date()
        except ValueError:
            continue
        if best is None or abs((d - ref).days) < abs((best - ref).days):
            best = d
    return best


def _range(text):
    """'27–29' -> (27.0, 29.0); '16' -> (16.0, 16.0); None if no number."""
    nums = [float(n) for n in NUM_RE.findall((text or "").replace("–", " ").replace("-", " "))]
    if not nums:
        return None, None
    return nums[0], nums[1] if len(nums) > 1 else nums[0]


def extract_bulletin_cards(html: str) -> dict:
    """The redesigned home page's bulletin: issue date plus one dict per day card."""
    soup = BeautifulSoup(html, "html.parser")
    box = soup.select_one("#ewsBulletin")
    if box is None:
        raise ValueError("AQEWS bulletin cards (#ewsBulletin) not found")
    ts = box.select_one(".ews-ts")
    m = re.search(DATE_RE, ts.get_text(" ", strip=True) if ts else "")
    issued = _to_date(*m.groups()) if m else datetime.now(IST).date()
    days = []
    for card in box.select(".ews-bday"):
        txt = lambda sel: (card.select_one(sel).get_text(" ", strip=True) if card.select_one(sel) else "")
        day = _infer_date(txt(".bd"), issued)
        if day is None:
            continue
        tmax = _range(txt(".bt"))
        subs = [s.get_text(" ", strip=True) for s in card.select(".bsub")]
        min_txt = next((s for s in subs if s.startswith("Min")), "")
        wind_txt = next((s for s in subs if s.startswith("Wind")), "")
        tmin = _range(re.sub(r"\(.*?\)", "", min_txt))
        wind_dir = card.select_one(".bsub b")
        speed = re.search(r"up to\s*(\d+)\s*km/h", wind_txt)
        md = re.search(r"(\d+)\s*m\b", txt(".bkv"))
        vi_el = card.select_one(".bvg .gv") or card.select_one(".bvg")
        vi = re.search(r"(\d[\d,]*)", vi_el.get_text(" ", strip=True) if vi_el else "")
        days.append({
            "date": day,
            "category": txt(".bcat") or None,
            "sky": txt(".bsky") or None,
            "tmax_low": tmax[0], "tmax_high": tmax[1],
            "tmin_low": tmin[0], "tmin_high": tmin[1],
            "tmin_observed": "observed" in min_txt,
            "wind_direction": wind_dir.get_text(" ", strip=True).replace(" ", "") if wind_dir and wind_txt else None,
            "wind_max_kmh": int(speed.group(1)) if speed else None,
            "mixing_depth": int(md.group(1)) if md else None,
            "ventilation_index": int(vi.group(1).replace(",", "")) if vi else None,
            "dispersion_unfavourable": bool(card.select_one(".bwarn")),
        })
    if not days:
        raise ValueError("AQEWS bulletin cards are empty")
    return {"issued": issued, "days": days}


def cards_to_parsed(cards: dict) -> dict:
    """Day cards in the shape parse_bulletin returns, so save_bulletin is shared."""
    out = {"mixing_depth": {}, "ventilation_index": {}, "category": {}, "outlook": None}
    for d in cards["days"]:
        for key in ("mixing_depth", "ventilation_index", "category"):
            if d.get(key) is not None:
                out[key][d["date"]] = d[key]
    return out


def save_bulletin_cards(cards: dict, path=AQEWS_BULLETIN_DAYS_CSV):
    df = pd.DataFrame(cards["days"])
    df.insert(1, "issued", cards["issued"])
    df.to_csv(path, index=False)
    return df


# --------------------------------------------- source apportionment (DSS) --
def extract_source_apportionment(html: str, ref=None) -> dict:
    """DSS shares of Delhi's daily-mean PM2.5 from the home page's pie legend."""
    soup = BeautifulSoup(html, "html.parser")
    card = soup.select_one(".ews-outlook-card")
    if card is None:
        raise ValueError("AQEWS source apportionment card not found")
    ref = ref or datetime.now(IST).date()
    ts = card.select_one(".ews-ts")
    sources = []
    for li in card.select(".ews-pie-legend-list li"):
        spans, b = li.find_all("span"), li.find("b")
        name = spans[-1].get_text(" ", strip=True) if spans else ""
        pct = NUM_RE.search(b.get_text() if b else "")
        if name and pct:
            sources.append({"source": name, "percent": float(pct.group())})
    if not sources:
        raise ValueError("AQEWS source apportionment legend is empty")
    split = {}
    for span in card.select(".ews-src-split span"):
        label = span.get_text(" ", strip=True)
        pct = NUM_RE.search(span.find("b").get_text() if span.find("b") else "")
        if pct:
            split["local_percent" if label.lower().startswith("local") else "non_local_percent"] = float(pct.group())
    day = _infer_date(ts.get_text(" ", strip=True) if ts else "", ref)
    return {
        "date": day.isoformat() if day else None,
        "model": "AQEWS Decision Support System (DSS), Delhi-NCR",
        **split,
        "sources": sorted(sources, key=lambda r: -r["percent"]),
        "source_url": AQEWS_HOME_URL,
        "fetched_at": datetime.now(IST).isoformat(timespec="minutes"),
    }


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
        home = _fetch(AQEWS_HOME_URL)
        try:
            cards = extract_bulletin_cards(home)
            save_bulletin_cards(cards)
            parsed = cards_to_parsed(cards)
            write_json_atomic(AQEWS_BULLETIN_JSON, {
                "title": f"Air Quality and Weather Bulletin for Delhi ({cards['issued']:%d.%m.%Y})",
                "date": cards["issued"].isoformat(),
                "days": [{**d, "date": d["date"].isoformat()} for d in cards["days"]],
                "source_url": AQEWS_HOME_URL,
                "fetched_at": datetime.now(IST).isoformat(timespec="minutes"),
            }, indent=2, ensure_ascii=False)
            result["bulletin_format"] = "cards"
        except ValueError as e:
            logger.warning("AQEWS bulletin cards not found (%s); trying the old prose bulletin", e)
            parsed = parse_bulletin(bulletin_text(home))
            try:
                write_json_atomic(AQEWS_BULLETIN_JSON, extract_bulletin(home), indent=2, ensure_ascii=False)
            except Exception as e2:
                logger.warning("AQEWS bulletin text not saved: %s", e2)
            result["bulletin_format"] = "prose"
        if not (parsed["ventilation_index"] or parsed["category"]):
            raise ValueError("no forecast found in either the bulletin cards or the prose bulletin "
                             "(AQEWS page layout may have changed)")
        save_bulletin(parsed)
        result["bulletin_days"] = len(parsed["category"])
        result["ventilation_days"] = len(parsed["ventilation_index"])
        result["outlook"] = parsed["outlook"]
        try:
            sa = extract_source_apportionment(home)
            write_json_atomic(AQEWS_SOURCES_JSON, sa, indent=2, ensure_ascii=False)
            result["source_apportionment_date"] = sa["date"]
        except Exception as e:
            logger.warning("AQEWS source apportionment not saved: %s", e)
    except Exception as e:
        logger.error("AQEWS bulletin failed: %s", e)
        result["bulletin_error"] = str(e)
    if "charts_error" in result and "bulletin_error" in result:
        raise RuntimeError(f"AQEWS unavailable: {result['charts_error']}")
    if "bulletin_error" in result:
        # Charts were saved; fail the step so the health panel shows the bulletin is missing
        raise RuntimeError(f"AQEWS bulletin: {result['bulletin_error']} (10-day charts saved)")
    return result


if __name__ == "__main__":
    print(run())
