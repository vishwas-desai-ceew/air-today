# Air Today: developer guide

How the dashboard is built, page by page: what each page shows, where every value comes from, the assumptions behind it, and what still needs review. The [README](../README.md) has the short overview and setup.

**Written:** 10 November 2026, against `main` plus the `aqews-landing-page` branch (AQEWS fix, health advisory, forecast page changes).
**Keep it current:** update this file in the same change as the code it describes.
**Sources:** links here are to the sources the code uses. Open and verify each one before anything from it goes into a CEEW output.

## Contents

1. [Architecture](#1-architecture)
2. [Shared building blocks](#2-shared-building-blocks)
3. [Pages](#3-pages)
4. [The daily pipeline](#4-the-daily-pipeline)
5. [Data files](#5-data-files)
6. [External sources](#6-external-sources)
7. [Thresholds and assumptions](#7-thresholds-and-assumptions)
8. [To be reviewed](#8-to-be-reviewed)
9. [Conventions and gotchas](#9-conventions-and-gotchas)

---

## 1. Architecture

```
                      cron (IST)
upstream ──► ingestion/run_daily.py ──► data/*.csv|json|pdf ──► views/*.py ──► browser
                     │                         ▲
                     └──► data/pipeline_status.json ──► header health pill

live, at page view:  METAR + Open-Meteo (5 min cache) · news RSS (30 min) · published Google Doc
```

- **Two halves.** The pipeline fetches and parses; the dashboard only reads local files. A slow or broken upstream therefore never slows a page, except for the three live fetches above.
- **Entry point:** `dashboard.py`. In order, it:
  - sets up the page and injects `style.css`;
  - runs the sign-in gate;
  - detects phones from the User-Agent;
  - registers the 13 pages with `st.navigation`;
  - renders the sidebar (IST clock, CEEW footer).
- **Caching:** `views/data.py` wraps every file read in `st.cache_data`. TTLs are 5–10 minutes for files, 5 minutes for live weather and 30 minutes for news.
- **App menu:** `client.toolbarMode = "minimal"` in `.streamlit/config.toml` limits the ⋮ menu to the items in `st.set_page_config`: Get help, Report a bug (both email vishwas.desai@ceew.in) and About. Rerun, theme settings, Print, Record and Deploy are hidden for everyone.
- **AQEWS outage check:** `views/render_aqi_fc.aqews_outage()` runs only on Overview, Daily update and AQEWS Forecast. It reads through the cached `data.aqews_daily()` and never raises: a missing, empty, stale (by IST date) or flat forecast is reported as an outage.
- **Styling:** one stylesheet, `style.css`, for every page. Components are mostly HTML strings rendered with `st.markdown(..., unsafe_allow_html=True)`. CSS targets Streamlit containers through their `key=` (Streamlit adds the class `st-key-<key>`).

### Sign-in

- **Enabled by:** an `[auth]` section in `.streamlit/secrets.toml`. Without it, the gate does nothing.
- **Mechanism:** Streamlit's native `st.login()`, backed by Authlib 1.6.5. Do not upgrade Authlib to 1.7.x; it breaks Streamlit's sign-in (see `project-refactor-status.md`).
- **Rule:** `config/access.py` `is_allowed_user`. The email must end `@ceew.in`, `email_verified` must not be false, and the `hd` claim, if present, must be `ceew.in`.
- **Host:** the sign-in cookie is tied to one hostname. `dashboard.py` sends users to the host in `redirect_uri` (`origin_mismatch`), so `localhost` and `127.0.0.1` don't fight each other.
- **Secrets keys** (see `.streamlit/secrets.toml.example`):
  - `[auth]`: `redirect_uri`, `cookie_secret`, `client_id`, `client_secret`, `server_metadata_url`
  - `[auth.client_kwargs]`: `hd`, `prompt`

---

## 2. Shared building blocks

| File | What lives there |
|---|---|
| `config/settings.py` | Every data path, upstream URL, Delhi's coordinates, `HTTP_HEADERS`, `IST`, and `effective_today()` |
| `config/reference.py` | `SOURCES` (name + URL for every source shown), AQI/PM bands (CPCB), NAAQS limits, GRAP stage ranges and colours, thresholds, `AQI_HEALTH` (CPCB Table 3.12), `HEALTH_ADVISORY` (MoHFW/NCDC) |
| `config/access.py` | Sign-in rule |
| `config/logging_config.py` | `get_logger()`: rotating file `logs/aq_winter.log` (5 MB × 3) plus console |
| `views/data.py` | Cached loaders for every data file; `source_health()` for the health pill; `aqi_news()`; `aqews_sources()` |
| `views/widgets.py` | Hero, top bar (news dropdown, health pill, user chip), KPI grid, key insights, icons, and source helpers `src()`, `side_source()`, `side_points()` |
| `views/components.py` | Section headers, outage banner, the AQEWS availability dialog |
| `views/charts.py` | Plotly base layout, AQI band shading, `source_line()` |
| `views/calendar_grid.py` | Month picker and clickable month calendar (Archive, GRAP) |
| `views/sky.py` | Time-of-day sky colours, solar position, the Overview weather card |
| `ingestion/json_store.py` | `read_json` and atomic `write_json_atomic` |

### `effective_today()` (`config/settings.py`)

- **What it decides:** which day counts as "today" for the bulletin.
- **Rule:** the calendar date (IST) if it is 17:57 IST or later, or if `delhi_aqi_cpcb.csv` already has today's AQI; otherwise yesterday. So the dashboard switches to the new day as soon as the CPCB bulletin is in.

### Top bar (every page)

- **Date eyebrow**, in IST.
- **AQI in the news:** a dropdown with the 6 latest headlines from The Hindu (Delhi), Times of India (Delhi) and NDTV (Cities) RSS feeds.
  - Filtered by keyword (AQI, pollution, smog, GRAP, PM2.5, stubble); opinion pieces are dropped.
  - Publisher icons load from the publishers' own sites.
  - Hidden if no feed answers.
  - Code: `ingestion/news.py` and `views/widgets._news_pill`.
- **Data health pill:** one row per tracked source, showing ok, stale (over 30 h), failed or missing. Code: `views/data.source_health`, `SOURCE_FILES`.
- **User chip and log-out link,** when sign-in is on.

---

## 3. Pages

Each entry lists what the page shows, the files it reads, the sources it credits, then the assumptions and review points. Review points also appear in the master list in §8.

### 3.1 Overview (`/`, `page_overview`)

- **Shows:**
  - **Hero:** the time-of-day sky background and three boxes:
    - CPCB AQI for `effective_today()` with the change from the previous day, linking to that day's CPCB PDF. "Awaiting bulletin" until it's out.
    - Key insights: a count of alerts, and a "View" dialog.
    - Live weather.
  - **KPI grid:** ten cards, refreshing every 5 minutes. AQI · tomorrow's forecast · wind · ventilation index · mixing height · temperature · humidity · visibility · rain (last hour) · fires PB+HR.
  - **Delhi weather card** (`views/sky.render_weather_card`, refreshes every 5 minutes):
    - Current conditions from METAR, with gaps filled from Open-Meteo.
    - Daylight panel: a computed sun path, with sunrise and sunset times from Open-Meteo.
    - Wind, humidity, visibility and pressure.
    - 2-hourly next 24 hours and a 3-day outlook.
    - One footer line with the source and caveat.
- **Reads:**
  - `delhi_aqi_cpcb.csv`
  - `insights_today.json`
  - `AQEWS_AQI_forecast.csv`, `ventilation_index_forecast.csv`, `AQI_forecast_category.csv`
  - `meteo_api_hourly.csv`
  - `fires_*.csv`
  - live METAR + Open-Meteo
- **Assumptions:**
  - Weather station: IGI Airport (VIDP) first, Safdarjung (VIDD) as fallback. Safdarjung is IMD's reference station for Delhi, so values may differ from IMD's Delhi figures.
  - Rain chances are shown only from 10% upwards (`RAIN_SHOW_PCT`).
- **Review:**
  - The KPI and insight thresholds (§7) are fixed in code.
  - The fires card shows only NOAA/VIIRS.

### 3.2 Daily update (`/daily-update`, `page_today`)

- **Shows:**
  - The latest CPCB bulletin card, plus four earlier days (category, health impact, prominent pollutant, change, PDF link).
  - Key insights: AQI, forecast, wind, ventilation index, minimum temperature, rain, fires, each flagged good or bad. A dialog shows the archived text for the day.
  - **Health advisory:**
    - Possible health effects, plus advice for everyone and for vulnerable groups, for the day's CPCB category.
    - On days above AQI 200, five practical steps.
    - Source: [MoHFW / NCDC Health Advisory on Air Pollution (NPCCHH), 1 Nov 2025](https://ncdc.mohfw.gov.in/uploads/pdf/air2.pdf).
    - The text is in `config/reference.py` with page references.
- **Reads:** `delhi_aqi_cpcb.csv`, `insights_today.json`, `archive_temp.json`.
- **How the text is made:** deterministic templates in `ingestion/get_aqi_summary.py`. No LLM is involved.
- **Review:**
  - The health advisory wording was read from a **scanned** PDF. Check it against pages 6–7 (PDF pages 10–11) and Annexure II (pages 19–20) of the advisory.
  - The "Insufficient AQI Data" card always mentions an AQEWS outage, even when only CPCB is missing (`views/delhi_weather.get_aqi_error_html`).
  - `delhi_weather.STYLES[...]["impact"]` paraphrases CPCB's health statements and is still used on the bulletin cards. The exact wording is in `AQI_HEALTH`.

### 3.3 AQEWS Forecast (`/forecast`, `page_forecast`)

- **Shows:**
  - A link to the AQEWS portal.
  - **Read the AQEWS bulletin** (navy button): a dialog with the day cards, showing date, category, sky, max/min temperature, wind, mixing depth, ventilation index and the dispersion flag.
  - **What the AQI categories mean** (white button): a dialog with CPCB Table 3.12.
  - An AQI / PM2.5 / PM10 switch:
    - **AQI:** the Daily AQI forecast card, with the day cards above a line chart over the CPCB bands.
    - **PM2.5 / PM10:** 2-hourly concentration charts with a summary box.
- **Reads:** `AQEWS_AQI_forecast.csv`, `AQEWS_PM25_forecast.csv`, `AQEWS_PM10_forecast.csv`, `aqews_bulletin.json`.
- **Assumptions:**
  - The daily AQI is computed by `ingestion/aqews.save_aqi_to_csv` from AQEWS's hourly sub-indices. Steps:
    1. Shift the hourly timestamps by 8 hours, to line up with CPCB's 4 PM-to-4 PM bulletin day.
    2. Take the daily mean of each sub-index.
    3. Take the maximum across PM2.5 and PM10.
  - This is our aggregation, not a published AQEWS daily figure.
- **Outage handling:** a missing, stale or flat forecast shows the "AQI forecast temporarily unavailable" card here and the outage banner on Overview and Daily update; no page crashes. Because the reader is cached for 10 minutes, a restored file shows up within that time.

### 3.4 Pollutants and AQI (`/pollutants`, `page_pm25`)

- **Shows:** three panels, each with a short side panel and a linked source line:
  1. **Hourly PM2.5 / PM10:** CPCB band shading and the 24-hour NAAQS line.
  2. **Delhi AQI, last 7 days:** CPCB bulletin values.
  3. **Where Delhi's PM2.5 comes from:**
     - AQEWS DSS source apportionment: Delhi vs outside-Delhi split, and the top 12 sources.
     - Sources starting with "Delhi" count as local. A test checks this matches AQEWS's own local share.
     - Code: `views/source_apportionment.py`.
- **Reads:** `signalsfunc_pm25_sample_data.csv`, `delhi_aqi_cpcb.csv`, `aqews_source_apportionment.json`.
- **Review:**
  - **The hourly PM data is a hand-placed sample file**, labelled "sample data" on the page. No pipeline step writes it, and it has no PM10. It needs a live source; `docs/data-sources.md` recommends the data.gov.in CPCB API.
  - The DSS shares are model estimates, and the page says so.

### 3.5 Weather Forecast (`/weather`, `page_weather`)

- **Shows:**
  - Day cards, one per full day, with a dispersion verdict from mean wind, plus the ventilation index when AQEWS provides it.
  - A night-shading key.
  - Four panels: temperature and humidity, wind (with direction arrows), mixing height, and rain. Each has 2–3 points and a linked source.
- **Reads:** `meteo_api_hourly.csv`, `ventilation_index_forecast.csv`, `AQI_forecast_category.csv`.
- **Assumptions:**
  - Unfavourable dispersion means wind below 10 km/h (2.8 m/s) or ventilation index below 6,000 m²/s, per the IITM AQEWS bulletin.
  - Night is computed from the sun's position.
- **Review:** Open-Meteo is model output, not IMD's forecast; the page caption says so.

### 3.6 Farm fires (`/fires`, `page_fires`)

- **Shows:**
  - A choice of Punjab, Haryana or both states.
  - Three instrument cards (NOAA/VIIRS, Aqua/MODIS, Terra/MODIS) with the latest day and its change.
  - A line chart with one line per instrument. Instruments are never summed, because each one detects the same fires separately.
  - A table with a CSV download.
  - A dialog embedding the Earthmetry Signals dashboard.
- **Reads:** `fires_punjab.csv`, `fires_haryana.csv`.
- **Assumptions:**
  - Detections at all confidence levels (low, nominal and high) are counted.
  - A day with no data has no row, rather than zero.
- **Review:**
  - The fetcher needs the private `signalsfunc` package. Without it the step is skipped; the last local run (9 Nov 2026) skipped it. Check the server has it.
  - The embedded dashboard is on a **demo** host (`signals-demo.earthmetry.com`).
  - `docs/data-sources.md` recommends the public NASA FIRMS API to replace `signalsfunc`.

### 3.7 IMD bulletin (`/imd-bulletin`, `page_bulletin`)

- **Shows:** the day's IMD AQ bulletin PDF, embedded as a `data:` URI, with a download link. "Updated" is the file's timestamp.
- **Reads:** `imd_bulletin_today.pdf`, downloaded from <https://nwp.imd.gov.in/silam/aqbulletin.pdf>.
- **Review:**
  - Some browsers block PDF `data:` iframes, and the whole PDF is sent in the page.
  - `views/render_aqi_pdf.py` and `ingestion/download_imd_bulletin.py` redefine their own paths and URL instead of using `config/settings.py`; the downloader also doesn't send `HTTP_HEADERS`.

### 3.8 Briefing note (`/briefing-note`, `page_general_info`)

- **Shows:** a Google Doc published to the web, in an iframe, with Refresh and "Download as a PDF" buttons.
- **Reads:** nothing local. The document URL is hard-coded in `views/render_google_doc.py`.
- **Review:** anyone with edit access to that Google Doc changes this page directly. Confirm who owns it.

### 3.9 Archive (`/archive`, `page_archive`)

- **Shows:**
  - A year picker, a month picker and a month calendar. Archived days open a dialog with that day's sentences.
  - Days with no AQEWS forecast carry an amber marker.
  - A side panel with counts, a legend, "Open latest" and the AQEWS availability dialog.
- **Reads:** `archive.json`, `missing_forecast_days.txt`. Both paths are redefined in `views/archive.py`.
- **Review:**
  - The page crashes if `missing_forecast_days.txt` doesn't exist.
  - `archive.json` grows every year, with no rotation.

### 3.10 GRAP (`/grap`, `page_grap`)

- **Shows:**
  - A winter picker.
  - A season timeline: the stage bar, order marks, today's marker, and the stages in force today.
  - A month calendar coloured by the stage in force. Days with orders open a dialog with the order, the team's notes and the CAQM PDF.
  - The month's orders as a side list.
  - The "AQI and GRAP stages" dialog.
- **Reads:** `data/grap/grap_<season>.json`, written by `ingestion/grap_orders.py` from CAQM's document API.
  - **Season:** 1 October to 30 September.
  - **Order date:** taken from the title, falling back to the issue date, then the publish date.
  - **Order type:** regex rules in `classify()`.
- **Assumptions:**
  - The stage in force is cumulative from the orders.
  - Stage colours are Air Today's own; CAQM has no official colours. This is disclosed on the page (`GRAP_COLOURS_DISCLAIMER`).
- **Review:**
  - `views/grap.py` uses `date.today()` (server clock, not IST).
  - The note "Order notes for 2025-26 are from the team's GRAP archive" is hard-coded and appears for any season with notes.
  - `grap_orders.py` maps "ILL" to Stage III as a typo workaround.
  - The team's notes come from an Excel sheet converted offline (`ingestion/convert_grap_orders.py`, then `grap_orders.py --import-legacy`).

### 3.11 Recent trends (`/trends`, `page_trends`)

- **Shows** (designed to fit one 15-inch laptop screen):
  - A season picker, with Season notes (dialog) and GRAP orders (popover).
  - Six tiles: days recorded, worst day, longest Very Poor+ spell, Very Poor or worse, Severe, Good or Satisfactory.
  - Daily AQI as a time series with GRAP order markers, plus an expand-to-dialog button.
  - "Same date, other winters": today's date in each winter on record.
  - "In the news": three headlines, with "More headlines" opening a dialog.
- **Reads:**
  - `data/delhi_aqi_01Oct24_28Feb25.csv` and `delhi_aqi_cpcb.csv`
  - GRAP JSON
  - the news feeds
- **Assumptions:**
  - **AQI is never averaged**, because an AQI is a daily index, not a quantity. The page reports days, streaks and single-day values instead. "Compare whole winters" plots daily values, not means.
  - A winter runs from 1 October to the end of February.
- **Review:**
  - The season notes (`RECENT_TRENDS`) exist only for 2024-25.
  - The headlines are picked automatically and not reviewed by CEEW; the page says so.

### 3.12 Sectoral interventions (`/interventions`, `page_interventions`)

- **Shows:**
  - A red disclaimer.
  - Three counts and a filter (Sources / Governance / People).
  - Eight cards; each opens a dialog with the full list of actions. "Under way" marks measures the government already carries out.
- **Reads:** text in `views/interventions.py`, which is the Clean Air team's wording, unchanged.
- **Review:** several figures are as originally written and dated (for example "until 28th February 2025", "~40% of PM2.5 from vehicles"). The disclaimer asks readers to check sources before citing; the text needs a refresh each winter.

### 3.13 Glossary (`/glossary`, `page_glossary`)

- **Shows:**
  - The AQI scale with the GRAP stages bracketed beneath.
  - A category filter.
  - An A–Z list: a jump bar, EB Garamond letter headings, and terms as pills showing their expansion. Clicking a pill opens the definition and source.
- **Reads:** `TERMS` in `views/glossary.py`, 57 terms.
- **Font:** EB Garamond loads from Google Fonts for the capital letters only (`@import` at the top of `style.css`).
- **Review:**
  - 23 terms were added on 10 Nov 2026.
  - The NAAQS values were checked against the [CPCB Gazette notification](https://cpcb.gov.in/uploads/National_Ambient_Air_Quality_Standards.pdf).
  - The VIIRS (375 m) and MODIS (1 km) resolutions were not checked against a source read during that change.
  - "Earthmetry Signals" is not defined, because no reliable description was available.

---

## 4. The daily pipeline

`ingestion/run_daily.py` runs the seven steps below, in order. A failure in one step doesn't stop the others. Each result goes to `data/pipeline_status.json`, and the exit code is 1 if any step failed. A missing optional package marks the step as skipped (`ok: null`), not failed.

| # | Step | Code | Writes |
|---|---|---|---|
| 1 | `weather` | `weather.run()` | `meteo_api_hourly.csv` |
| 2 | `aqews` | `aqews.run()` | `AQEWS_{AQI,PM25,PM10}_forecast.csv`, `ventilation_index_forecast.csv`, `AQI_forecast_category.csv`, `aqews_bulletin.json`, `aqews_bulletin_days.csv`, `aqews_source_apportionment.json` |
| 3 | `cpcb` | `cpcb.run()` | `delhi_aqi_cpcb.csv` |
| 4 | `imd` | `download_imd_bulletin.download_pdf()` | `imd_bulletin_today.pdf` |
| 5 | `fires` | `get_fire_pbhr.run()` | `fires_punjab.csv`, `fires_haryana.csv` |
| 6 | `grap` | `grap_orders.run()` | `grap/grap_<season>.json` |
| 7 | `summary` | `get_aqi_summary.run()` | `archive_temp.json`, `archive.json`, `insights_today.json`, appends to `missing_forecast_days.txt` |

**Schedule:** suggested crontab (IST): full runs at 16:20 and 18:10, plus `--only imd fires` at 02:30. See the docstring.

**Run a single step:**

```bash
py_envs/bin/python ingestion/run_daily.py --only aqews
```

### Notes per step

- **CPCB** (`ingestion/cpcb.py`):
  - **Where from:** the NCR bulletin (`.../Delhi-NCR/NCR_AQI_Bulletin_YYYY_MM_DD.pdf`), falling back to the national bulletin (`.../AQI_Bulletin_YYYYMMDD.pdf`).
  - **Parsing:** pdfplumber finds the Delhi row on any page and checks the bulletin date. The fetch retries 3 times with backoff.
  - **Backfill:** fills gaps over the last 7 days.
  - **Quirk:** if the bulletin is late at 16:20, the step is marked failed until the 18:10 run (see §8).
- **AQEWS** (`ingestion/aqews.py`):
  - **10-day page:** two requests. The Chart.js datasets on the 10-day page are evaluated with `py_mini_racer`.
  - **Home page:** gives the bulletin and source apportionment.
  - **Since about 7 Nov 2026 the home page shows day cards** (`#ewsBulletin`) instead of written text. The card parser runs first and the old text parser is the fallback.
  - **If neither finds a forecast, the step fails loudly.** Before this fix, it kept serving the 6 Nov files without any warning.
- **Weather:** Open-Meteo hourly forecast for central Delhi (28.6448 N, 77.2167 E), with no API key.
- **Fires:** `signalsfunc.read_nasa_active_fires` for IN-PB and IN-HR, per state, per day, split by satellite. Re-fetches the last 3 days.
- **GRAP:** CAQM document API. Merges new orders into the season JSON, keeping the team's notes by order ID.
- **Summary:** seven template sentences and a structured `facts` dict. Days without a numeric AQEWS forecast are logged to `missing_forecast_days.txt`.

### Cron-compatibility shims

These only call another module's `run()`. They're kept so old crontab lines keep working:
- `download_cpcb_bulletin.py`
- `get_aqews_aqi.py`, `get_pm25_aqews.py`, `get_aqi_fc_cat.py`, `get_v_index.py`
- `meteo_api.py`

---

## 5. Data files

All files are in `data/`, which is **not in git**. The server's copy is the only copy, so back it up.

| File | Written by | Read by |
|---|---|---|
| `delhi_aqi_cpcb.csv` (`date, aqi, category, pollutant, stations, source`) | cpcb | Overview, Daily update, Pollutants, Recent trends, summary |
| `delhi_aqi_01Oct24_28Feb25.csv` | one-off backfill (`get_hist_aqi.py`) | Recent trends (2024-25) |
| `AQEWS_AQI_forecast.csv`, `AQEWS_PM25_forecast.csv`, `AQEWS_PM10_forecast.csv` | aqews | Forecast page, KPIs, summary, outage check |
| `ventilation_index_forecast.csv`, `AQI_forecast_category.csv` | aqews | KPIs, Weather day cards, summary |
| `aqews_bulletin.json`, `aqews_bulletin_days.csv` | aqews | Bulletin dialog |
| `aqews_source_apportionment.json` | aqews | Pollutants (DSS panel) |
| `meteo_api_hourly.csv` | weather | Weather page, weather card, KPIs, summary |
| `imd_bulletin_today.pdf` | imd | IMD bulletin page |
| `fires_punjab.csv`, `fires_haryana.csv` | fires | Fires page, KPIs, summary |
| `grap/grap_<season>.json` | grap | GRAP page, Recent trends |
| `archive.json`, `archive_temp.json`, `insights_today.json`, `missing_forecast_days.txt` | summary | Archive, Daily update, Overview |
| `pipeline_status.json` | run_daily | Health pill |
| `signalsfunc_pm25_sample_data.csv` | **placed by hand** | Pollutants (hourly PM) |
| `gemini_summary.json` | removed step (Nov 2026) | nothing; safe to delete |
| `sectors.csv`, `farm_fires.csv`, `fire_pbhr.csv` | legacy | nothing on a live page |

---

## 6. External sources

| Source | URL | Access | Notes |
|---|---|---|---|
| CPCB AQI bulletin | <https://cpcb.gov.in/upload/Downloads/Delhi-NCR/> | PDF, no key | Official daily AQI; published around 4 PM IST |
| CPCB National AQI (2014) | <https://smartnet.niua.org/sites/default/files/resources/Air%20Quality%20Index.pdf> | PDF | Bands (Table 3.2), health statements (Table 3.12) |
| CPCB NAAQS (2009) | <https://cpcb.gov.in/uploads/National_Ambient_Air_Quality_Standards.pdf> | Scanned PDF | PM2.5 60 / 40, PM10 100 / 60 µg/m³ (24 h / annual) |
| IITM AQEWS | <https://ews.tropmet.res.in/> | Web pages, no API | Forecast, day cards, DSS source apportionment |
| Open-Meteo | <https://open-meteo.com/> | JSON API, no key | Free tier is labelled non-commercial; see §8 |
| NOAA aviationweather.gov | <https://aviationweather.gov/data/metar/?ids=VIDP> | JSON API, no key | METAR, refreshed about every 30 min |
| IMD AQ bulletin | <https://nwp.imd.gov.in/silam/aqbulletin.pdf> | PDF | |
| NASA FIRMS (via `signalsfunc`) | <https://firms.modaps.eosdis.nasa.gov/> | Private package | VIIRS 375 m, MODIS 1 km |
| CAQM GRAP | <https://caqm.nic.in/landingpage/pages/grap/grap-orders> | Document API | Orders and schedule |
| MoHFW / NCDC advisory | <https://ncdc.mohfw.gov.in/uploads/pdf/air2.pdf> | Scanned PDF | Health advisory, 1 Nov 2025 |
| The Hindu, TOI, NDTV | RSS (see `ingestion/news.py`) | RSS, no key | Headlines only, linked to the publisher |
| Earthmetry Signals | <https://signals-demo.earthmetry.com/> | iframe | Fires dashboard (demo host) |
| Google Docs | published doc | iframe | Briefing note |
| Google Fonts | fonts.googleapis.com | CSS | EB Garamond (glossary letters) |

The wider survey of sources considered (OAQ, data.gov.in, SAFAR, CAMS and others) is in [data-sources.md](data-sources.md). It was written on 26–27 Oct 2026, and some of its "in use" rows are now out of date (see §8).

---

## 7. Thresholds and assumptions

| Value | Where | Basis |
|---|---|---|
| Wind below 10 km/h (2.8 m/s) is unfavourable for dispersion | `WIND_UNFAVOURABLE_KMH` | IITM AQEWS bulletin |
| Ventilation index below 6,000 m²/s is unfavourable | `VENTILATION_INDEX_UNFAVOURABLE` | IITM AQEWS bulletin |
| Mixing height below 500 m is "shallow" | KPI grid | Dashboard choice; no cited source |
| Visibility below 2,000 m is "haze / smog likely" | KPI grid | Dashboard choice; no cited source |
| Minimum temperature below 10 °C favours biomass burning | insights | Dashboard choice; no cited source |
| Mean hourly rain of 0.1 mm or more counts as rain | summary, insights | Dashboard choice. IMD's lowest class ("very light", 0.1 mm) is a 24-hour total, so this is not the same rule |
| Rain chance shown only from 10% | `RAIN_SHOW_PCT` | Display choice |
| Fires headline instrument is NOAA/VIIRS; instruments are never summed | `FIRE_HEADLINE_INSTRUMENT` | Separate detections of overlapping fires |
| AQEWS daily AQI: hourly sub-indices, 8 h shift, daily mean, maximum of PM2.5 and PM10 | `aqews.save_aqi_to_csv` | Aligns with CPCB's 4 PM bulletin day; our aggregation |
| AQI above 200 triggers the health steps | health advisory | MoHFW/NCDC advisory, Annexure II |
| "Delhi …" sources are local in the DSS split | `source_apportionment._is_local` | Matches AQEWS's local share; checked by a test |
| A winter is 1 Oct to end of Feb; the GRAP season is 1 Oct to 30 Sep | Recent trends, GRAP | Convention |
| Bulletin day switches at 17:57 IST or when the bulletin is in | `effective_today` | CPCB publishing time |

**Needs review:** the rows marked "Dashboard choice; no cited source". They should either get a source or be labelled as Air Today's own rule of thumb.

---

## 8. To be reviewed

Grouped by priority. File references point to where to start.

### Accuracy and sourcing

1. **Health advisory wording** (`config/reference.py` `HEALTH_ADVISORY`): read from a scanned PDF. Check it against the advisory before relying on it publicly.
2. **Hourly PM on the Pollutants page** comes live from `signalsfunc.read_cpcb` (Earthmetry, city = Delhi, PM2.5 + PM10, last 7 days), cached for an hour in a temp file (`CPCB_HOURLY_CACHE`, `ingestion/cpcb_hourly.py`). The app needs `signalsfunc` importable to refresh it; otherwise run `python ingestion/cpcb_hourly.py` hourly from the `geospatial` env. With no cache at all it falls back to `SIGNALS_HOURLY_CSV`, labelled as sample data.
3. **Thresholds without a source** (§7): the 500 m mixing height, the 2,000 m visibility, the 10 °C minimum temperature and the 0.1 mm hourly rain rule.
4. **New glossary terms** (`views/glossary.py`, added 10 Nov 2026): the VIIRS and MODIS resolutions are unverified in-session. Review all 23 new definitions.
5. **Sectoral interventions text** (`views/interventions.py`): dated figures from the 2024-25 winter.
6. **Season notes** (`views/recent_trends.py` `RECENT_TRENDS`): 2024-25 only.
7. **AQI in the news:** headlines are filtered automatically from three publishers and not reviewed. Confirm the team is comfortable with an unreviewed feed on every page.
8. **Open-Meteo terms:** the free tier is labelled non-commercial. Confirm an internal not-for-profit dashboard qualifies (from `docs/data-sources.md`).
9. **Weather station:** IGI Airport (VIDP) is the primary METAR station, while IMD's Delhi reference is Safdarjung. Comparisons with IMD figures may differ.

### Reliability

10. **AQEWS fix awaits deployment:** until the `aqews-landing-page` branch is merged and the server is updated, the live server serves ventilation index, mixing depth and categories from 6 Nov 2026.
11. **Fires on the server:** confirm `signalsfunc` is installed there. Without it the fires step is skipped and the fires KPI goes stale.
12. ~~Every page depended on `AQEWS_AQI_forecast.csv`~~ **Fixed (10 Nov 2026):** the outage check is fail-safe, uses IST, and runs only on the three pages that show it.
13. **CPCB 16:20 run marks the step failed** when the bulletin is late. The health pill then shows "failed" until 18:10, which looks like an outage.
14. **Archive crashes** without `missing_forecast_days.txt` (`views/archive.load_missing_days`).
15. **Health pill coverage:** it tracks CPCB, AQEWS, weather, IMD and fires (Punjab file only). It doesn't track GRAP, the daily summary or the news feeds.
16. **`data/` is not in git:** back up the server's copy, especially `archive.json`, which can't be regenerated.
17. **Timezone:** `views/grap.py` (`date.today()`) uses the server clock. Fine on an IST server; wrong elsewhere.

### Cost and clean-up

18. ~~Gemini summary was unused~~ **Removed (10 Nov 2026):** the step, `ingestion/get_gemini_summary.py`, the `google-genai` dependency and `GEMINI_API_KEY`. The dashboard uses no LLM. An old `data/gemini_summary.json` can be deleted.
19. ~~Placeholder help links~~ **Fixed (10 Nov 2026):** the menu emails vishwas.desai@ceew.in and has a real About text.
20. **Earthmetry demo host** on the Fires page (`views/fires.py` `EXTERNAL_DASHBOARD`).
21. **Dead code:**
    - `views/render_insights.py`, and `views/farm_fires.py` (reachable only from it)
    - `views/sectors.py`
    - `ingestion/get_hist_aqi.py` (one-off; old URL with `verify=False`)
    - `delhi_weather.get_insights/highlight_text/load_summary_json`
    - `archive.get_effective_date_utc`
    - `settings.FIRE_CSV`
    - `ingestion/update_archive_json.py`: superseded, tests only
22. **Out-of-date docs:**
    - `docs/data-sources.md`: the Pollutants iframe and the "regex on bulletin text" rows.
    - `.github/workflows/ci.yml`: the comment says there is no git repository.
    - `deprecated/README.md`: refers to `utils/` paths.
    - `config/settings.py`: comments say the bulletin comes out around 18:00, while the code and hero say about 16:00.
23. **IMD bulletin page:** embeds the PDF as a `data:` URI. Consider serving it as a static file instead.

---

## 9. Conventions and gotchas

### Sourcing

- Every figure, threshold or statement shown as fact gets an entry in `SOURCES` (`config/reference.py`) and a linked source line on the page. Use `side_source()` (bold **Source**) or `source_line()`.
- Prefer official sources: CPCB, IMD, IITM, MoHFW, CAQM. Note scans and anything paraphrased in a code comment.
- Never average AQI values. Report days, streaks or single values.
- UK spelling.

### Streamlit and CSS gotchas

These all came up in practice:

- **Text overlap:** a site-wide rule gives markdown blocks a −16px bottom margin. Inside bordered containers with a reduced `gap`, text then overlaps whatever follows. Fix it for the specific container with `[data-testid="stMarkdownContainer"] { margin-bottom: 0 }`.
- **Text clipped on phones:** the mobile rule `.element-container { overflow-x: auto }` clips the bottom of text blocks. Add the block's class to the exemption list (search `style.css` for "The site-wide mobile rule").
- **Equal-height cards:** cards in `st.columns` only stretch if their wrapper does. See the `[data-testid="stLayoutWrapper"]:has(...)` rules for Recent trends. Apply them above 640px only, or phones squash the content.
- **Labels showing anyway:** global CSS forces `stDateInput` labels to show, so `label_visibility="collapsed"` isn't enough.
- **Restart, don't refresh:** after a dependency or `[auth]` change, restart the Streamlit process. Script reruns don't rebuild the server's routes.

### Checking a page without signing in

Run a second copy from a folder whose `.streamlit/` has only `config.toml`, with no `secrets.toml`, and everything else symlinked to the repo. Sign-in is then off. That's how the layouts in this branch were checked at 1440×820 (a 15-inch laptop) and 375×812 (a phone).

### Tests

- `py_envs/bin/python -m pytest -q`; 110 tests as of 10 Nov 2026.
- Parsers are tested on fixtures captured from the live sources (`tests/fixtures/`).
- **When an upstream page changes:** capture a new fixture, keep the old one, and test both the new and fallback paths.
