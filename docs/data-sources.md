# Air Today: data sources and pipeline

Checked 26–27 October 2026. **[LIVE]** = called or fetched and a response seen; **[DOC]** = provider documentation or search results only. Open and verify every link before anything here goes into a CEEW output.

## 1. What the dashboard uses now

| Need | Source | How | Script |
|---|---|---|---|
| Official daily AQI | CPCB NCR AQI bulletin (national bulletin as fallback) | PDF, pdfplumber | `ingestion/cpcb.py` |
| AQI and PM2.5 forecast | IITM AQEWS 10-day page | Chart.js data on the page | `ingestion/aqews.py` |
| Ventilation index, mixing depth, AQ category | AQEWS / IMD bulletin text | Regex (was Gemini) | `ingestion/aqews.py` |
| Weather forecast and current conditions | Open-Meteo | JSON API, no key | `ingestion/weather.py` |
| IMD AQ bulletin PDF | nwp.imd.gov.in | Download | `ingestion/download_imd_bulletin.py` |
| IMD bulletin summary | Gemini 2.5 Flash on the IMD PDF | API key | `ingestion/get_gemini_summary.py` |
| Punjab/Haryana fire counts | NASA VIIRS via private `signalsfunc` | Python package | `ingestion/get_fire_pbhr.py` |
| Station pollutants, fire map | Earthmetry Superset dashboards | iframe | `views/pm25_hourly.py`, `views/render_farm_firesh_dash.py` |

All of it runs from one command, `ingestion/run_daily.py`. The suggested crontab is in that file's docstring. Each step's result goes to `data/pipeline_status.json`, which feeds the sidebar's data-health panel.

## 2. OAQ API (oaq.notf.in): verdict

**Not suitable as a primary production source. At most, it is an optional extra layer.**

- **Operator:** Aurassure (a sensor company), with Rainmatter Foundation funding. The backend is a Firebase project. **[LIVE]** https://oaq.notf.in/
- **Data:** The API re-serves CPCB CAAQMS data (530+ stations) and adds low-cost sensor networks (AirView+, Aurassure, CSTEP AirNet). **[LIVE]**, read from the documentation code. https://oaq.notf.in/documentation/api
- **Access:**
  - You need an API key, which is exchanged for a signed URL that lasts 24 hours.
  - Unsigned calls returned **HTTP 403**, so I could not check the response shape or how fresh the data is. **[LIVE]**
  - There is no self-service key sign-up.
- **Licence:** **CC BY-NC-SA 4.0**. Share-alike would bind outputs built on it. It is also questionable for the CPCB portion, which is government data being relicensed. https://creativecommons.org/licenses/by-nc-sa/4.0/
- **Reliability:**
  - No published rate limits, SLA, status page or official repository.
  - It is a young project that depends on a single vendor.
- **Fallback for station data:**
  - CPCB directly, through the data.gov.in OGD API. The resource ID is `3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69`. It needs a free key and still has to be tested with a real one.
  - Or the CPCB CCR portal (https://app.cpcbccr.com/ccr/), which needs scraping.

The current Pollutants page embeds an Earthmetry Superset dashboard, not OAQ. Replacing it with first-party CPCB data via data.gov.in is the recommended next step. It needs a data.gov.in API key.

## 3. Inventory of open sources for New Delhi

| # | Source | Variables | Access | Verdict |
|---|---|---|---|---|
| 1 | CPCB daily AQI bulletin | City AQI, prominent pollutant | PDF, no auth **[LIVE]** | **In use.** Official daily figure |
| 2 | CPCB CCR / NAQI portal | Station pollutants and met, 15 min–1 h | JavaScript app, scrape **[LIVE]** https://app.cpcbccr.com/ccr/ | Fallback; fragile |
| 3 | data.gov.in real-time AQI (CPCB) | Station pollutant min/max/avg, ~hourly | Free API key; returns "Authorization field missing" without one **[LIVE]** | **Recommended** for station data; test with a key |
| 4 | IITM AQEWS Delhi | AQI and PM forecast, VI, mixing depth | Web page, no API **[LIVE]** https://ews.tropmet.res.in/ | **In use** |
| 5 | IITM DSS Delhi | Source contributions | Web only **[LIVE]** https://ews.tropmet.res.in/dss/index.php | Link out |
| 6 | SAFAR | AQI, forecast | Timed out **[LIVE]** | Not viable |
| 7 | IMD APIs | City forecast, nowcast | JWT key and IP whitelisting **[DOC]** https://mausam.imd.gov.in/responsive/apis.php | Conditional |
| 8 | DPCC real-time stations | 26 Delhi stations | Page prohibits scraping **[LIVE]** https://www.dpccairdata.com/dpccairdata/display/index.php | Not viable (also in CPCB CCR) |
| 9 | CAQM | GRAP orders | No feed **[LIVE]** https://caqm.nic.in/ | Link out |
| 10 | Open-Meteo Air Quality (CAMS) | PM2.5, PM10, NO2, O3, dust, AOD; ~45 km model | No key **[LIVE]** https://open-meteo.com/en/docs/air-quality-api | Viable as a modelled forecast, labelled as model data |
| 11 | Open-Meteo Forecast / ERA5 | Weather, BLH, history from 1940 | No key **[LIVE]** https://open-meteo.com/en/docs | **In use** |
| 12 | CAMS via Copernicus ADS | Gridded CAMS fields | Personal token **[DOC]** https://ads.atmosphere.copernicus.eu/how-to-api | Research and maps |
| 13 | NASA FIRMS | VIIRS/MODIS fire points, FRP | Free MAP_KEY **[DOC]** https://firms.modaps.eosdis.nasa.gov/api/area/ | **Recommended** to replace private `signalsfunc` |
| 14 | NASA POWER | Daily met, 0.5° | No key; about 4-day lag **[LIVE]** https://power.larc.nasa.gov/docs/services/api/temporal/daily/ | History only |
| 15 | OpenAQ v3 | Re-hosted station data | API key **[LIVE]**; limits **[DOC]** https://docs.openaq.org/using-the-api/rate-limits | History fallback |
| 16 | Sentinel-5P TROPOMI | NO2, CO columns | Free registration **[DOC]** https://documentation.dataspace.copernicus.eu/Data/SentinelMissions/Sentinel5P.html | Map layer |
| 17 | MODIS/MAIAC AOD | AOD | Earthdata login **[DOC]** | Optional layer |
| 18 | UrbanEmissions.info | Forecast images | No API **[LIVE]** | Link out |

**Excluded (commercial aggregators):** aqi.in, IQAir, AQICN/WAQI, BreezoMeter, Ambee.

**Count:**
- 12 sources are viable: #1–4 and #10–17.
- 1 is conditional: the IMD API, #7.
- The rest are link-out only or not viable.

**Caveats:**
- Open-Meteo's free tier is labelled non-commercial (https://open-meteo.com/en/terms). Confirm with the legal team that an internal not-for-profit dashboard qualifies.
- The data.gov.in endpoint still needs a test with a real key.

## 4. Google sign-in (SSO)

**Why sign-in looped back to the login screen:**
- `auth.redirect_uri` sends Google back to `http://127.0.0.1:8501/oauth2callback`.
- The app was normally opened at `http://localhost:8501`. That is what Streamlit printed, because `browser.serverAddress` was set to `localhost`.
- The sign-in state cookie is tied to one hostname. Set on `localhost`, it was never sent to `127.0.0.1`, so the callback found no state and redirected to `/`.

**Fixes:**
- `dashboard.py` now detects the mismatch and sends users to the right host before they click sign in.
- `config.toml` now prints the `127.0.0.1` address.

**Recommended setup:** see `.streamlit/secrets.toml.example`. In particular, set `hd = "ceew.in"` so Google's account chooser only offers CEEW accounts. The server still checks the domain itself; `hd` only makes the chooser behave.

**For a hosted deployment:**
- Set `redirect_uri` to the public URL, for example `https://<app>/oauth2callback`.
- Add that exact URI under Authorised redirect URIs in Google Cloud Console.
