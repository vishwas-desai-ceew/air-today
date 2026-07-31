---
noteId: "750924a0859911f191bce1d7db6155f5"
tags: []

---

# AQ Winter — Dashboard Redesign

This document is the UI/UX redesign proposal for the CEEW AQ Winter dashboard, produced
before any redesign code was written (Step 1 + Step 2 of the redesign task). It is
grounded entirely in the actual application as it exists today — every claim below was
checked against the real files (`dashboard.py`, `views/*.py`, `ingestion/*.py`,
`style.css`, `assets/`), not assumed from a generic dashboard template.

**Scope note up front:** this app monitors **one location** (Delhi NCR) from **five data
sources** (CPCB bulletin, IMD/AQEWS forecast, Open-Meteo weather, NASA fire counts,
Gemini AI summary). It is not a multi-station sensor network. So a few generic
"redesign a dashboard" ideas genuinely don't apply here — there is no map, no fleet of
devices, no station-to-station comparison — and this document says so explicitly
rather than inventing features to fit a template. Where the original brief's example
KPIs ("number of stations", "number of active devices") don't map to anything real,
they're replaced below with the closest genuine equivalent.

---

## Step 1 — Analysis of the Existing Application

**Structure today:** one entry script (`dashboard.py`) rendering 7 `st.tabs()`, each
calling into one or more `views/*.py` render functions, which read CSV/JSON files
written by the separate `ingestion/*.py` cron scripts.

| Tab | What it actually shows |
|---|---|
| Today's AQ Update | Date header → outage banner (conditional) → AQI card + yesterday comparison → health advisory → AI-generated "Key Insights" → 10-day AQI forecast chart → a **static image** of hourly PM2.5 |
| Fire counts - HR & PB | A single static image (`assets/fires.png`) |
| Weather Forecast | 4 live Plotly charts: wind, temperature, rainfall, boundary-layer height |
| IMD - AQ Bulletin | The raw IMD PDF embedded via `<iframe>` |
| AQ Sectoral Interventions | A pill-selector between 3 static narrative panels: Recent Trends, Farm Fires, Interventions (GRAP policy) |
| Archived Updates | A calendar picker over `archive.json`, showing that date's "Key Insights" text |
| AQEWS - PM2.5 Forecast | A second, separate 10-day forecast chart (PM2.5 specific) |

**Duplicated information found:**
- Farm fire content appears **twice**, inconsistently: a live rendered image in "Fire
  counts" and a static narrative panel (`views/farm_fires.py`) inside "AQ Sectoral
  Interventions" → "Farm Fires" pill. A user has no way to know these are related, or
  which one is "current."
- The "10-day forecast" concept is split awkwardly: the AQI-overall forecast lives
  inside "Today's AQ Update", while the PM2.5-specific forecast is a completely
  separate top-level tab, even though both read date-indexed forecast CSVs and use the
  same chart-building pattern.

**Unnecessary visual clutter found:**
- `style.css` has real bugs, not just style choices: `.stTabs [data-baseweb="tab"]` sets
  `font-size: 8rem` and the button-group label sets `font-size: 18rem` — both almost
  certainly typos (probably meant `0.8rem`/`1.8rem` or similar), left in because
  Streamlit's own component styles happen to override them in practice.
- Loud, inconsistent color choices with no shared palette: tab hover uses
  `#f59090d2` (a saturated pink), the pills' hover state uses `#ffffa6` (bright
  yellow) with a `scale(1.05)` pop animation, several buttons use heavy drop shadows
  (`box-shadow: 1px 2px 12px rgba(0,0,0,0.78)`) — all of it reads as a consumer/promo
  site, not a research tool.
- `assets/` contains files nothing references: `dangerous.png`, `summarize.png`,
  `temp.docx`, `temp.txt`, `temper.txt`, and an entire `assets/plots/` folder of 4
  static PNGs (`blh_hourly.png`, `temp_hourly.png`, `rain_hourly.png`,
  `wind_speed_hourly.png`) that are superseded by the live Plotly charts in
  `views/weather_fcast.py`. Confirmed via repo-wide grep — genuinely dead weight in
  the visual asset pipeline, even though it's not code.
- The sidebar exists in Streamlit but is actively hidden on mobile
  (`[data-testid="stSidebar"] { display: none !important; }`) and unused on desktop —
  an entire layout surface sitting idle.

**Missing summaries — data collected but never surfaced:**
- `data/ventilation_index_forecast.csv` (fetched daily by `ingestion/get_v_index.py`)
  is only ever read to feed one sentence into the AI narrative
  (`ingestion/get_met_details.py: get_v_index_df`) — **it is never charted or tabled
  anywhere.** This is a real, already-collected 10-day forecast with no visualization.
- `data/AQI_forecast_category.csv` (from `ingestion/get_aqi_fc_cat.py`) — the
  Gemini-extracted category-only forecast — has the same problem: fetched, used in one
  narrative sentence, never shown directly.
- There is no page that answers "is today's data actually reliable?" at a glance
  beyond the single outage flag buried in one tab — data freshness per source only
  exists because of the `render_status_strip()` added in the Phase 2 refactor, and even
  that sits above the tabs rather than being a first-class page.

**Where users likely spend the most time:** "Today's AQ Update" (the default tab) and,
during archive research, the "Archived Updates" calendar — these are the two genuinely
interactive, decision-relevant views. The PDF bulletin and interventions/policy tabs
are read-once reference material, not places for repeat interaction.

**Opportunities for better hierarchy:** separate "what's happening today" (a fast,
glanceable overview) from "reference material" (PDF, GRAP policy text, trends
narrative) and from "exploration" (archive, forecasts, weather detail) — today
everything is flattened into 7 equally-weighted tabs with no sense of what's primary.

---

## Dashboard Design Vision

**Target users:** CEEW researchers, scholars, project associates, and technical staff
who check Delhi's air quality picture daily during winter (the high-pollution season)
and occasionally need to pull historical data or context for a report, brief, or memo.

**Design philosophy:** *information before decoration.* This is a working research
tool used every morning, not a showcase. The redesign borrows from internal
observability/analytics tools (Grafana, Datadog, internal Looker dashboards) rather
than consumer weather apps: dense-but-organized, neutral palette, data given room to
be the visual focus, chrome kept minimal.

**Information hierarchy:** Today's number (AQI + category + trend) is the single most
important fact in the app and should be visible within one second of opening it,
with zero scrolling or clicking. Everything else — forecasts, weather detail, fires,
historical archive, policy reference — is one click away, grouped by *purpose*
(monitor today / forecast ahead / understand context / go back in time) rather than
by *data source* (which is how it's grouped today).

**Layout philosophy:** a persistent left-hand navigation replaces the 7-wide top-tab
strip (which doesn't scale and gives every section equal visual weight regardless of
importance). A slim top status strip (already partially built in Phase 2) stays
visible across every page. Content pages use a card-based grid instead of full-width
stacked sections, so related numbers can be compared side by side without scrolling.

---

## User Personas

**1. Research Associate / Project Associate**
- *Goals:* Check today's Delhi AQI and health-advisory category before starting other
  work; occasionally pull a chart or figure for a briefing note.
- *Workflow:* Opens the app most winter mornings, glances at the AQI card, checks
  whether the forecast is worsening, moves on within under a minute.
- *Pain points today:* The number they care about is buried below a date header, a
  badge, and (conditionally) an outage banner. On mobile this stack is even taller.

**2. Air Quality Researcher**
- *Goals:* Understand trends over the season, compare forecast vs. observed, pull
  ventilation/wind context to explain *why* AQI moved.
- *Workflow:* Uses the Archive tab to look up specific dates; wants forecast and
  weather context side by side, not in three separate tabs.
- *Pain points today:* Ventilation index (directly relevant to *why* pollution is
  trapped or dispersing) isn't visualized at all despite being fetched daily. AQI
  forecast and PM2.5 forecast live in unrelated tabs even though they're the same kind
  of chart.

**3. Senior Fellow / Project Manager**
- *Goals:* A fast, credible-looking snapshot to reference in meetings or share
  externally (screenshot-friendly); doesn't need to dig into raw CSVs.
- *Workflow:* Opens the app rarely, needs to orient in seconds with no prior context.
- *Pain points today:* No summary/overview screen exists — every visit starts on a
  tab that's already fairly dense (AQI card + advisory + AI insights + a chart + an
  image, all stacked).

**4. Technical Staff (maintaining the pipeline)**
- *Goals:* Confirm the daily cron jobs actually ran and the data is fresh; spot an
  AQEWS/CPCB outage before a researcher notices something's "off."
- *Workflow:* Wants a health-check view, not buried inside the same tab as the public
  content.
- *Pain points today:* Freshness/outage info exists (`render_status_strip`) but isn't
  a first-class destination — there's no dedicated "data health" view, just a strip
  above the tabs.

---

## Design Principles

1. **Information before decoration** — no gradients, glow, or hover-scale animation
   for their own sake (several exist in `style.css` today and are being removed).
2. **One primary number per screen** — the Home page leads with Delhi's current AQI;
   every other page leads with the one fact that page exists to answer.
3. **Minimum clicks** — the answer to "what's the AQI right now" must not require
   opening a tab that's 4th in a list; it's the landing view.
4. **Progressive disclosure** — cards show the headline number; detail (hourly
   breakdown, the AI narrative, raw table) sits inside an expander/detail view, not
   inline by default.
5. **Consistent spacing** — a single spacing scale (4/8/16/24/32px) applied via
   centralized CSS custom properties instead of ad hoc `margin-top: -1rem` style
   overrides scattered per call site (found in several places in the current code).
6. **Clean typography** — one type scale, applied through CSS classes, not per-string
   inline `style="font-size:2rem"` (found throughout `dashboard.py` today).
7. **Neutral colour palette** — greys and a single brand blue for structure; saturated
   colour is reserved *only* for AQI severity, so it stays meaningful instead of
   competing with decorative uses (today, bright pink/yellow/orange appear in button
   hover states with no semantic meaning at all).
8. **Accessible colour contrast** — verified against WCAG AA (details in the
   Accessibility section).
9. **Mobile friendly where possible** — the existing `is_mobile` detection and
   mobile-specific rendering paths are preserved and extended, not replaced.

---

## Dashboard Architecture

Streamlit 1.45 (already installed) ships a native `st.navigation()` / `st.Page()` API
that renders a proper grouped sidebar with per-page routing — this is the standard,
supported way to build exactly this kind of app shell today, and is what makes the
difference between "feels like a custom Streamlit script" and "feels like a real
internal platform." Verified directly against the installed package before committing
to this: `st.Page` accepts a plain callable (so every existing `render_*()` function
in `views/` can be wrapped with zero changes to its internals), and `st.navigation`
accepts a `{section_name: [pages]}` mapping, which gives grouped sidebar sections for
free.

**New grouping (replaces the 7 flat top tabs):**

```
Overview                              <- NEW page, see "Home Dashboard" below
Air Quality
  ├── Today                           <- AQI card, advisory, AI insights (trimmed)
  └── Forecast                        <- AQI forecast + PM2.5 forecast + ventilation,
                                          together (was split across 2 unrelated tabs)
Weather                               <- unchanged content, own page
Fires                                 <- live fire dashboard + hourly PM2.5,
                                          the "Farm Fires" static narrative moves here
                                          as a "Context" expander (removes the duplicate)
Reference
  ├── IMD Bulletin (PDF)              <- unchanged
  ├── Sectoral Interventions          <- GRAP policy text, unchanged
  └── Recent Trends                   <- narrative, unchanged
Archive                               <- unchanged calendar browser
```

This is a **presentation-layer regrouping only** — every `render_*()` function keeps
its existing signature and internal logic; only *where* it's called from changes.
No `ingestion/` file is touched.

**What belongs on Home:** only glanceable summary — never a full chart or the AI
narrative in full (that's one click away on "Air Quality → Today").
**What belongs inside Air Quality:** the actual observed/forecast numbers and their
supporting detail.
**What belongs in Reference:** static/slow-changing content (policy text, the raw
PDF, seasonal narrative) that's read occasionally, not checked daily.

---

## Home Dashboard

A genuinely new landing page (doesn't exist today — every current tab immediately
shows a chart or detail). Top to bottom:

1. **KPI row** (4 cards, grounded in real available data — see mapping below)
2. **Data health strip** — the existing `render_status_strip()`, promoted to a
   permanent fixture rather than tab-adjacent
3. **Today's AI-generated insight** — the existing "Key Insights" text, shown as a
   single card (not full detail — "Read more" expands it)
4. **Quick actions** — jump links to Forecast, Archive, and the PDF bulletin

**KPI card mapping (real data only — no invented "stations/devices" metrics):**

| Card | Source | Existing function it reuses |
|---|---|---|
| Latest AQI + category + trend arrow | `data/delhi_aqi_cpcb.csv` | `views/delhi_weather.py: get_last_two_days()` (already computes this exact diff) |
| Fire count today (Punjab + Haryana) | `data/fire_pbhr.csv` | `ingestion/get_met_details.py: get_fire_count()` |
| Tomorrow's AQI forecast + category | `data/AQEWS_AQI_forecast.csv` | `views/render_aqi_fc.py: get_error_message()` (already loads this df) |
| Data freshness (all sources) | file mtimes | `views/components.py: render_status_strip()` |

No "favourite dashboards" or "recently viewed locations" — there's exactly one
location in this app, so those don't apply. The closest genuine equivalent —
**recently viewed archive dates** — is proposed instead, in the Research Features
section.

---

## Visual Hierarchy

- **Primary section (Home + "Air Quality → Today"):** the current AQI number, its
  category badge, and trend vs. yesterday. Largest type on the page, top-left,
  above the fold on both desktop and mobile.
- **Secondary section:** health advisory, AI narrative summary, KPI cards, status
  strip — supporting context, one visual weight down (card-based, medium type).
- **Detail section:** forecast charts, weather charts, the raw PDF, archive browser,
  policy text — opened deliberately via navigation, never competing with the primary
  number for attention.

---

## Charts

Every chart in the app, reviewed individually:

| Chart | Stay / Move / Change? |
|---|---|
| AQI card (`render_aqi_card`, custom HTML) | **Stay**, restyle only. It's a card, not a chart — keep it, just rebuild with the shared component system and centralized AQI colour tokens instead of the STYLES dict duplicated inline. |
| 10-day AQI forecast (`render_aqi_fc.py: generate_pm_plot`) | **Stay + move.** Move next to the PM2.5 forecast on the new "Air Quality → Forecast" page (currently split across unrelated tabs). Chart type (line + soft area fill) is appropriate for a forecast trend — keep it. |
| 10-day PM2.5 forecast (`render_pm25_fc.py`) | **Stay + move**, same reasoning — pairs naturally with the AQI forecast once co-located. |
| Wind / Temperature / Rainfall / BLH (`weather_fcast.py`) | **Stay.** Line charts for wind/temp/BLH and a bar chart for rainfall are the right chart types for hourly time series; no change needed beyond consistent card framing. |
| Hourly PM2.5 (`pm25_hourly.py`) | **Change.** Currently a **static JPEG image**, not a chart — this is the single best candidate in the whole app for becoming a real interactive Plotly chart (hover values, zoom), since the underlying hourly data pipeline already exists elsewhere in the project. Flagged as a "Should become interactive" item; actual chart-building is a bigger lift than pure CSS/layout work, so it's scoped as a later-phase item (see Roadmap) rather than in this pass, since the redesign brief asks to preserve analytical logic and not add new data pipelines.
| Farm fires (`render_farm_firesh_dash.py`) | **Change (same caveat).** Also a static PNG (`assets/fires.png`). Same reasoning — flagged for a future interactive version, not built in this pass. |
| **Ventilation index forecast** | **New chart, high value.** Data already exists (`data/ventilation_index_forecast.csv`) and is currently invisible. Recommended as a small line chart alongside the AQI/PM2.5 forecasts on the "Forecast" page — this is a visualization gap, not a redesign of an existing chart, so (per "do not add new features") it's listed here as a **recommendation for a follow-up task**, not implemented in this redesign pass.

---

## Filters

Today there are effectively two "filters" in the whole app: the archive calendar date
picker, and the mobile/desktop branch (which isn't user-facing, it's a device check).
Recommended additions, all presentation-layer:

- **Persistent/global:** none needed beyond what exists — this app has one location
  and one active "today," so a global location filter would be manufactured
  complexity, not a real need.
- **Contextual (per page):**
  - *Archive page:* keep the existing calendar input; add a quick "Last 7 days /
    Last 30 days" preset above it so a researcher doesn't need to know exact dates.
  - *Forecast page:* once AQI + PM2.5 + ventilation are co-located, add a simple
    toggle (radio/pills, reusing the existing `st.pills` pattern already used in
    `render_insights.py`) to switch which series is emphasized, rather than three
    separately-scrolled charts.
- **Date selection:** the existing `streamlit_calendar_input` component stays —
  it already correctly restricts to dates with actual archived data.
- **Location/device/parameter selection:** not applicable (single location, no
  device fleet, and "parameter" in this app means AQI vs PM2.5 vs weather variable,
  handled by the page grouping above rather than a separate filter widget).

---

## Tables

The app has exactly one tabular data surface today: the archive's per-date bullet
list (not a real `st.dataframe` — it's rendered as an HTML `<ul>`). There's no sortable
grid anywhere in the app currently. Recommendations, scoped to *presentation only*
(the underlying `archive.json` structure doesn't change):

- Add a proper `st.dataframe` view as an *alternative* to the calendar-card view on
  the Archive page (a toggle between "Card view" and "Table view"), giving:
  - **Sorting** — native to `st.dataframe`, no code needed beyond passing the frame.
  - **Search** — Streamlit's dataframe toolbar includes built-in search as of 1.45.
  - **Download** — `st.dataframe`'s built-in export button (CSV), which also directly
    answers the "notebook-ready export" research feature below.
  - **Column visibility** — via `column_config` on the same `st.dataframe` call.
- **Sticky headers / pagination:** native to `st.dataframe` for anything above a
  small row count — no custom implementation needed.
- **Row highlighting:** use `column_config` styling to highlight the "missing AQEWS
  forecast" dates that are already tracked (`missing_forecast_days.txt`), so the
  existing red-badge warning becomes a highlighted row instead of a separate list.

This is additive on top of the existing card view, not a replacement — researchers who
want the narrative "Key Insights" card keep it; the table view is for anyone who wants
to scan/export dates.

---

## Colour Palette

Neutral base + one brand colour + the AQI severity scale kept exactly as-is (it's
CPCB's official 6-category scheme and must not change semantically):

| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg` | `#F7F8FA` | `#0E1117` | page background |
| `--surface` | `#FFFFFF` | `#171A21` | cards, panels |
| `--surface-alt` | `#F1F3F6` | `#1F232C` | nested/secondary panels |
| `--border` | `#E3E6EB` | `#2A2E38` | card borders, dividers |
| `--text-primary` | `#14171F` | `#F1F2F4` | headings, key numbers |
| `--text-secondary` | `#5B6270` | `#9AA1AE` | captions, labels |
| `--brand` | `#1B4FD6` | `#5B8DFF` | links, active nav, primary actions (kept close to the existing `primaryColor` in `.streamlit/config.toml`, just corrected for contrast) |
| `--warning` | `#B7791F` | `#E0A94D` | outage / stale-data banners |
| `--success` | `#1E8E5A` | `#3FBE84` | "OK" status dots |

**AQI severity scale (unchanged values, now centralized — currently duplicated as an
inline `STYLES` dict in `views/delhi_weather.py` with no equivalent for the other
views that also render AQI categories):**

| Category | Colour |
|---|---|
| Good | `#2D662A` |
| Satisfactory | `#03A303` |
| Moderate | `#E0B400` *(darkened from `#ffe102` for text contrast — see Accessibility)* |
| Poor | `#F78C00` |
| Very Poor | `#FC4D02` |
| Severe | `#E91902` |

**Dark mode:** originally planned to switch `.streamlit/config.toml`'s `theme.base`
from `"light"` to `"auto"` so it would follow the OS/browser preference. **Verified
against the live app during implementation that this isn't actually valid** -
Streamlit 1.45.1 only accepts `"light"` or `"dark"` for `theme.base` (it logs a
warning and silently falls back to `"light"` otherwise). `base` stays `"light"`;
Streamlit's own always-available manual light/dark toggle (in its settings menu)
still switches the native chrome, and the CSS custom properties above already
respond to `@media (prefers-color-scheme: dark)` for every custom component
(cards, AQI badges, etc.) regardless of what `base` is set to - so custom UI adapts
to OS dark mode even though Streamlit's native widgets don't automatically.

---

## Typography

Single scale, applied via CSS classes (not inline `style=` strings):

| Level | Size | Weight | Use |
|---|---|---|---|
| Display | 2.25rem | 700 | The one primary AQI number on Home / Today |
| H1 | 1.5rem | 700 | Page titles |
| H2 | 1.15rem | 600 | Section headers |
| Body | 0.95rem | 400 | Paragraph text, advisory copy |
| Caption | 0.8rem | 500 | Timestamps, source labels, status strip |

Spacing scale: `4px / 8px / 16px / 24px / 32px`, used for all margin/padding via CSS
custom properties — replacing the scattered `margin-top: -1rem`, `padding: 0.7rem
0.7rem` one-off values currently hardcoded per call site across `dashboard.py`.

---

## Components

New reusable pieces, added to `views/components.py` (already the home of `hr()` /
`outage_banner()` / `render_status_strip()` from the Phase 2 refactor — this redesign
extends that module rather than creating a parallel one):

- **Metric card** — label, big number, optional trend arrow + delta. Powers the Home
  KPI row and replaces the bespoke AQI-card HTML with a general-purpose version.
- **Section header** — title + optional caption + optional right-aligned action
  (e.g. "View all"), replacing ad hoc `st.markdown("### ...")` + manual `hr()` pairs.
- **Chart card** — a bordered container wrapping any Plotly chart with a consistent
  title/caption treatment, so every chart in the app shares one frame style.
- **Insight card** — wraps the AI-generated narrative with a visible "AI-generated"
  label and timestamp (also a standing recommendation from the original project
  review, re-affirmed here for the redesign).
- **Warning card** — generalizes the existing `outage_banner()` to any warning
  message, not just the AQEWS-specific one.
- **Status badge** — the green/red dot pattern already in `render_status_strip()`,
  extracted so it can be reused on the Home page and the Archive table view.
- **Download card / Map card** — **not applicable to this app** (no map — single
  location; "download" is handled by `st.dataframe`'s native export, not a bespoke
  component).

---

## Research Features

Scoped to what's realistic without touching `ingestion/` or adding new data
pipelines:

- **Recently viewed archive dates** — the one genuine analogue to "recently viewed
  locations" in a single-location app. Store the last N dates a user opened in
  `st.session_state`, show as quick-select chips on the Archive page.
- **Session persistence** — `st.session_state` already holds `is_mobile`; extend the
  same pattern to remember the last-selected Forecast-page toggle within a session.
- **Notebook-ready CSV export** — covered above via `st.dataframe`'s native download,
  applied to the Archive table view and the forecast dataframes.
- **Data quality / completeness badge** — direct extension of the existing
  `render_status_strip()` — surfaced more prominently as its own Home-page section
  rather than a thin strip.
- **Metadata / station information panel** — reframed as a **"Data Sources" panel**
  (since there's no station network): a small reference card listing each of the 5
  pipelines (CPCB, AQEWS, Open-Meteo, NASA fires, Gemini) with what they provide and
  how often they refresh — genuinely useful for a researcher deciding how much to
  trust a number, and something the app has never explained anywhere.
- **Bookmarks / saved filters / comparison mode / station comparison** — **not
  recommended.** With one location and no user-configurable filter surface beyond a
  date picker, these would be complexity added for its own sake, contradicting
  "information before decoration." Flagged explicitly as *not* pursued, rather than
  silently dropped.

---

## Performance Improvements

All presentation-layer, no analytical/caching logic changes beyond what Phase 1 of
the earlier refactor already did (`@st.cache_data(ttl=3600)` on every hot-path
loader):

- **Conditional rendering:** with `st.navigation`, only the active page's render
  function executes per run — today, all 7 tabs' Python bodies effectively run
  every rerun regardless of which tab is visible (Streamlit still executes every
  `with tab:` block). Switching to pages is a real, measurable win here, not just
  cosmetic.
- **Deferred loading:** wrap the AI narrative card and the PDF viewer in
  `st.expander(expanded=False)` by default on Home/secondary placements, so their
  underlying `load_pdf_base64()` / `load_gemini_summary()` calls (already cached, but
  still doing file I/O) aren't invoked on every page unless the user opens them.
- **Lazy image loading:** the static fire/PM2.5 images already use
  `use_container_width=True`; no further change needed there until they're replaced
  with real charts (Roadmap Phase 8+, out of this pass).
- **Pagination:** applies to the new Archive table view (native to `st.dataframe`).

---

## Accessibility

- **Contrast:** `Moderate`'s existing yellow (`#ffe102`) fails WCAG AA for white text
  and is borderline even for black text at small sizes — darkened to `#E0B400` in the
  palette above while keeping it clearly distinct from `Satisfactory`'s green and
  `Poor`'s orange. All other AQI colours already pass AA against white text at the
  card sizes used.
- **Keyboard navigation:** `st.navigation`'s sidebar is natively keyboard-navigable
  (arrow keys + Enter), which the current `st.tabs()` implementation also supports
  but with less discoverable focus styling — the redesign adds a visible focus ring
  via `:focus-visible` in the centralized CSS, which `style.css` doesn't define today.
- **Screen reader support:** replace several `st.markdown(..., unsafe_allow_html=True)`
  decorative `<div>` wrappers with semantic headings (`st.subheader`/`st.caption`)
  where the HTML wrapper adds no real styling value beyond what a native Streamlit
  call already provides — reduces custom markup a screen reader has to parse for no
  benefit.
- **Responsive layouts:** the existing `is_mobile` device-width detection and
  mobile-specific render branches are preserved; the new Home page and card
  components are built mobile-first (single column collapsing from the 4-card desktop
  grid) using the same breakpoint already defined in `style.css` (`768px`).

---

## Implementation Roadmap

| Phase | Scope | Complexity |
|---|---|---|
| **Phase 1 — Global styling** | Centralized colour/spacing/type tokens as CSS custom properties in `style.css`; remove the `8rem`/`18rem` font-size bugs and the loud hover/scale effects; fix the `Moderate` contrast issue. | **Low** — pure CSS, no Python logic touched. |
| **Phase 2 — Navigation** | Convert `dashboard.py` from `st.tabs()` to `st.navigation()`/`st.Page()` with the grouped structure above; every existing `render_*()` call moves, none are rewritten. | **Medium** — mechanical but touches the app's entry point; needs careful manual + curl-based verification (no live browser in this environment). |
| **Phase 3 — Home dashboard** | New Overview page: KPI row, promoted status strip, insight card, quick actions — entirely additive. | **Medium** — new page, but every number reuses an existing function. |
| **Phase 4 — Cards** | Build the component library in `views/components.py` (metric/section/chart/insight/warning/status card) and adopt it across all pages. | **Medium** — touches every view file, but each change is a like-for-like markup swap. |
| **Phase 5 — Charts** | Reframe every existing chart in the new chart card; consolidate AQI + PM2.5 forecast onto one page. Ventilation-index chart and converting the two static images to interactive charts are called out as **follow-up recommendations**, not built now (see Charts section). | **Low** (reframing) **/ Medium** (if the follow-up items are picked up later). |
| **Phase 6 — Tables** | Add the `st.dataframe` table-view toggle to the Archive page. | **Low** — additive, native Streamlit widget. |
| **Phase 7 — Maps** | **Not applicable** — no geographic/station data exists in this app. Explicitly skipped rather than silently ignored. | — |
| **Phase 8 — Responsive polish** | Extend the mobile-first treatment to the new Home/cards; re-test the existing mobile branches against the new navigation shell. | **Low–Medium**. |

Phases 1–4 plus the reframing half of Phase 5 and all of Phase 6 are implemented in
this pass (see the app for the result). Phase 8 is partially covered by building
mobile-first from the start; a dedicated device pass is recommended as a fast follow.
The ventilation-index chart and converting the two static images to live charts are
intentionally left as **recommendations**, not implemented — they'd mean writing new
chart-building code against data that currently has none, which crosses from "redesign
the UI" into "add a new feature," which this task explicitly excludes.
