# CEEW Air Today

An internal Streamlit dashboard for Delhi's winter air quality, used by the CEEW Clean Air team. It brings together the official CPCB AQI, the IITM AQEWS forecast, weather, farm fires and CAQM's GRAP orders, and turns them into a daily update. Access is limited to CEEW Google Workspace accounts.

> For how each page works, where every number comes from, the assumptions behind the thresholds and the open review items, see **[docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md)**.

## What's in the dashboard

| Section | Page | What it shows |
|---|---|---|
| Today | **Overview** | Hero with today's CPCB AQI, key insights and live weather; ten KPI cards; the Delhi weather card (current conditions, daylight curve, 24-hour and 3-day outlook) |
| | **Daily update** | The latest CPCB bulletin and recent days, key insights with the archived text, and a health advisory for the day's AQI category |
| | **AQEWS Forecast** | IITM AQEWS 10-day AQI, PM2.5 and PM10 forecast; the AQEWS bulletin; what the AQI categories mean |
| Trackers | **Pollutants and AQI** | Hourly PM2.5/PM10 against the CPCB bands, the last 7 days of CPCB AQI, and where Delhi's PM2.5 comes from (AQEWS DSS) |
| | **Weather Forecast** | 3-day forecast read for dispersion: temperature and humidity, wind, mixing height, rain |
| | **Farm fires** | Daily satellite fire detections in Punjab and Haryana, by instrument |
| Reports | **IMD bulletin** | The day's IMD air quality bulletin (PDF) |
| | **Briefing note** | The team's briefing note (a published Google Doc); **hidden** for now (`HIDDEN_PAGES` in `dashboard.py`) |
| | **Archive** | Every past daily update, on a calendar |
| | **GRAP** | CAQM GRAP orders by winter, with the stage in force each day |
| Learn | **Recent trends** | Season-by-season AQI, same-date comparison across winters, AQI in the news |
| | **Sectoral interventions** | The team's recommended actions by source and policy lever ; **hidden** for now (`HIDDEN_PAGES` in `dashboard.py`) |
| | **Glossary** | The AQI and GRAP scale, and an A–Z of terms used on the dashboard |

The top bar on every page has an "AQI in the news" dropdown and a data-health pill showing whether each source updated on time.

## How it works

```
upstream sources ──► ingestion/ (run_daily.py, cron) ──► data/ (CSV, JSON, PDF) ──► views/ (Streamlit pages)
```

- **Ingestion** (`ingestion/run_daily.py`) fetches every source once a day and writes local files in `data/`. Each step's outcome goes to `data/pipeline_status.json`, which feeds the health pill.
- **The dashboard** (`dashboard.py` + `views/`) reads those local files. Only three things are fetched live while someone is using it: current weather (METAR + Open-Meteo, cached 5 minutes), news headlines (cached 30 minutes) and the published Google Doc.
- **Configuration**: paths and URLs live in `config/settings.py`; source links, thresholds, AQI bands and sourced text (health advisory, glossary sources) live in `config/reference.py`.

## Main data sources

| Source | Used for |
|---|---|
| [CPCB](https://cpcb.gov.in/) daily AQI bulletin | Official daily AQI, category, prominent pollutant |
| [IITM AQEWS](https://ews.tropmet.res.in/) | 10-day AQI/PM forecast, ventilation index, mixing depth, source apportionment |
| [Open-Meteo](https://open-meteo.com/) | Hourly weather forecast, mixing height |
| [NOAA aviationweather.gov](https://aviationweather.gov/) METAR (IGI Airport, VIDP) | Current observed weather |
| [IMD](https://nwp.imd.gov.in/silam/aqbulletin.pdf) | Daily air quality bulletin PDF |
| NASA VIIRS/MODIS via the private `signalsfunc` package | Punjab and Haryana fire counts |
| [CAQM](https://caqm.nic.in/) | GRAP orders |
| [MoHFW / NCDC](https://ncdc.mohfw.gov.in/uploads/pdf/air2.pdf) | Health advisory text |
| The Hindu, Times of India, NDTV RSS feeds | AQI in the news |

The full list, with what each value means and its caveats, is in the developer guide.

## Running it locally

Requires Python 3.13.

```bash
python3.13 -m venv py_envs
```

```bash
py_envs/bin/pip install -r requirements-dev.txt
```

1. **Secrets.** Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`. With no `[auth]` section, sign-in is switched off locally. With it, Google sign-in is on and only `@ceew.in` accounts get in.
2. **Data.** `data/` is not in git. Fill it by running the pipeline once:

   ```bash
   py_envs/bin/python ingestion/run_daily.py
   ```

   The fires step needs the private `signalsfunc` package and is skipped (not failed) without it.
3. **Run the app.** Open http://127.0.0.1:8501. Use `127.0.0.1`, not `localhost`, when sign-in is on, because the sign-in cookie is tied to that host.

   ```bash
   py_envs/bin/streamlit run dashboard.py
   ```

4. **Tests:**

   ```bash
   py_envs/bin/python -m pytest -q
   ```

## Deployment

The live server runs `streamlit run dashboard.py` from a clone of this repository and runs the pipeline on a cron schedule. The suggested schedule (IST clock) is in the docstring of `ingestion/run_daily.py`:

```
20 16 * * *  cd /path/to/aq_winter && py_envs/bin/python ingestion/run_daily.py
10 18 * * *  cd /path/to/aq_winter && py_envs/bin/python ingestion/run_daily.py
30 2  * * *  cd /path/to/aq_winter && py_envs/bin/python ingestion/run_daily.py --only imd fires
```

To update the server: pull `main`, then restart the Streamlit process. A restart (not just a browser refresh) is needed whenever Python dependencies or the sign-in configuration change. The server needs outbound internet access to every source above.

## Repository layout

```
dashboard.py            Entry point: page setup, sign-in gate, navigation
views/                  One module per page or component (Streamlit + HTML/CSS)
ingestion/              Fetchers and the daily pipeline (run_daily.py)
config/                 settings.py (paths, URLs), reference.py (sources, bands, thresholds), access.py (sign-in rule)
style.css               All styling, injected on every page
assets/                 Logos and images
tests/                  pytest suite, with fixtures captured from the live sources
docs/                   Developer guide and the data-source survey
data/                   Generated by the pipeline (git-ignored)
deprecated/             Retired scripts kept for reference (git-ignored)
```

## Working on it

- **New figures, thresholds and text:** anything shown as a fact needs a source. Add it to `SOURCES` in `config/reference.py` and show it with a linked source line.
- **Verify:** open and check every source before it goes into a CEEW output.
- **Tests:** add or update tests in `tests/` with any parser change. Parsers break silently when an upstream page changes; the AQEWS redesign in November 2026 is the example.
- **Spelling:** UK spelling throughout.
