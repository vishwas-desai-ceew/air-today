# AQ Winter Dashboard — Technical Review

**Scope:** Read-only review of `dashboard.py`, `scripts/` (14 files), `utils/` (16 files), `get_imd_aqbulletin.py`, `.streamlit/config.toml`, `data/`, and project structure. No code changes made. Total app code: ~2,900 lines across 31 Python files.

**Context:** Internal single-page Streamlit dashboard (7 tabs) for CEEW's winter air-quality monitoring, pulling from CPCB, IMD, Open-Meteo, NASA fire data, and Google Gemini (for text summarization). No git repo currently exists in this directory, no tests, no CI/CD, no auth.

---

## 1. Overall Architecture

**Structure today:**
```
aq_winter/
├── dashboard.py          # 259 lines, single flat script, 0 functions
├── get_imd_aqbulletin.py # orphaned — output never read by anything
├── scripts/               # 14 files, mostly render_*() for Streamlit UI
├── utils/                 # 16 files, data fetch/transform, cron-run separately
├── data/                  # JSON/CSV state files (some orphaned)
├── assets/, .streamlit/, style.css
├── py_envs/               # 963 MB, ~53,000-file virtualenv sitting in the project dir
├── misc.ipynb, ews_forecast_scripts.txt, nohup.out, .cache.sqlite  # stray root clutter
```

**Findings:**
- `dashboard.py` has **zero function/class definitions** — the entire page (imports → page config → mobile detection → 7 tabs → footer) executes top-to-bottom on every rerun. This is workable at 259 lines but is already at the point where a `render_home_tab()`/`render_page()` split would help.
- Responsibility separation between `utils/` (data fetch) and `scripts/` (render) is a **reasonable and consistent convention** — this is the strongest architectural decision in the project and should be preserved, not replaced.
- No circular imports were found.
- **`sectors.py`** exists in `scripts/` but is never imported (its import is commented out at `dashboard.py:8`) — dead code, or a feature that was pulled but never removed.
- Two clearly **superseded/dead pipelines** still ship in the codebase:
  - `get_imd_aqbulletin.py` + `data/imd_aq_bulletin.json` — nothing reads the JSON it produces; superseded by `utils/get_gemini_summary.py`, which summarizes the same PDF via Gemini directly.
  - `utils/get_forecast_aqi.py` (Selenium) → `utils/agg_aqi_fc.py` → `data/pm25.json`/`pm10.json` → `AQI_forecast.csv` — superseded by the lighter JS-scraping pair `utils/get_pm25_aqews.py`/`utils/get_aqews_aqi.py` → `AQEWS_*_forecast.csv`, which is what `scripts/render_aqi_fc.py` actually reads.
- **`py_envs/` is a live virtualenv (963 MB, ~53k files)** sitting inside the project directory. It is not currently a structural bug (there's no `.git` yet) but it must be excluded the moment this becomes a repo — see Security §7.
- Root-level clutter that doesn't belong in the delivered app: `misc.ipynb` (233 KB), `ews_forecast_scripts.txt` (82 KB), `nohup.out` (a stale log file), `.cache.sqlite`, a duplicated `ventilation_index_forecast.csv` (exists both at root and in `data/`), and `cpcb_cert.pem` (generated for TLS pinning, referenced in comments, but never actually used — see §7).

**Suggested folder structure** (incremental, not a rewrite):
```
aq_winter/
├── app/
│   ├── dashboard.py        # thin entrypoint: page config + tab wiring only
│   └── components.py       # shared UI helpers (hr(), tab_header(), banner())
├── ingestion/               # renamed from utils/ — one cron-run fetcher per source
│   ├── cpcb/                # download_cpcb_bulletin.py + get_aqi_cpcb_v2.py merged
│   ├── imd/
│   ├── aqews/
│   └── common.py            # shared HTTP session, retry, date/cutoff helpers
├── views/                   # renamed from scripts/ — one render_*() per tab
├── config/
│   ├── settings.py          # single source of truth: cutoff time, breakpoints, URLs
├── data/                    # generated state only, gitignored
├── requirements.txt          # real, root-level, not buried in a venv
└── .gitignore
```
This is a rename-and-consolidate exercise, not a rebuild — every file above already has a near-equivalent today.

---

## 2. Backend Engineering

**Duplicated code (highest-value refactor target — this project has a lot of copy-pasted pipelines):**

| Duplicate | Locations | Fix |
|---|---|---|
| CPCB PDF parsing (`extract_pollutants`, `get_relevant_page`, `save_aqi_to_csv`) | `utils/get_aqi_cpcb_v2.py` vs `utils/download_cpcb_bulletin.py` — near byte-for-byte identical | Merge into one `ingestion/cpcb.py`; keep one CLI entrypoint |
| `ordinal()` date-suffix helper | `utils/get_aqi_summary.py:34-39` and `scripts/archive.py:34-39` — identical | Move to a shared `common/dates.py` |
| "Effective date" cutoff logic | `utils/get_aqi_summary.py` (17:48), `scripts/delhi_weather.py` (12:27, but comment says "5:57 PM"), `scripts/archive.py` (17:57), `dashboard.py:91` (17:57) — **four different values for what should be one constant** | **This is a correctness bug, not just duplication** — see below |
| Gemini bulletin-scraping boilerplate + API key | `utils/get_aqi_fc_cat.py` and `utils/get_v_index.py` | Merge into one `ingestion/gemini_extract.py` parametrized by prompt |
| AQI category bins/labels | `utils/get_aqews_aqi.py:58-59`, `utils/agg_aqi_fc.py:38-39`, plus a hand-maintained colour dict in `scripts/delhi_weather.py:21-29` | One `AQI_CATEGORIES` constant in `config/settings.py` |
| Plotly forecast chart builder | `scripts/render_aqi_fc.py:13-65` vs `scripts/render_pm25_fc.py:12-61` — structurally identical | One parametrized `build_forecast_chart()` helper |
| JSON read-modify-write pattern | `utils/get_aqi_summary.py`, `utils/update_archive_json.py`, `scripts/archive.py`, `scripts/delhi_weather.py` | One `JsonStore` helper (load/save with atomic write) |

**Correctness risk, not cosmetic:** three independent "what date counts as today" implementations disagree (12:27 PM / 17:48 / 17:57), and one has a comment that contradicts its own code (`scripts/delhi_weather.py:36`, comment says "5:57 PM IST" but the code says `time(12, 27)`). Between roughly 12:27 PM and 5:57 PM, different parts of the same page can show different "as-of" dates. **This should be fixed as a single shared constant/function, not four.**

**Other backend issues:**
- No shared HTTP session/retry/timeout policy — every scraper (`utils/download_cpcb_bulletin.py`, `utils/get_aqi_cpcb_v2.py`, `get_imd_aqbulletin.py`) reimplements its own `requests.get()` inline. `utils/get_aqi_cpcb_v2.py`'s main PDF GET and `get_imd_aqbulletin.py:34` have **no timeout at all** — a hung server would hang the whole cron job.
- SSL verification is disabled (`verify=False`) in three files against `cpcb.nic.in`, with `urllib3.disable_warnings()` to silence the resulting warnings. A `cpcb_cert.pem` exists specifically to fix this properly (referenced in comments) but is never actually passed to `requests`. Worth finishing that fix rather than suppressing the warning.
- CSV files are fully rewritten (load → concat → sort → overwrite) on every run in at least three places (`utils/get_aqi_cpcb_v2.py`, `utils/download_cpcb_bulletin.py`, `utils/get_fire_pbhr.py`) rather than appended — fine at current size, will not scale gracefully as archives grow across winters.
- `data/archive.json` (full read-modify-write, no locking) grows every year with no rotation strategy; an overlapping cron retry could interleave writes.
- Error handling is almost entirely broad `except Exception: print(...)` — failures are swallowed with no structured detail (`utils/get_aqi_cpcb_v2.py:121,129`, `utils/get_aqi_summary.py:80-101`, `utils/download_cpcb_bulletin.py:117,125`).
- `utils/get_fire_pbhr.py` calls into an external private package (`signalsfunc`) with **no try/except at all** — a single upstream failure would crash that cron job entirely.
- `utils/get_aqi_summary.py:5` does a bare same-directory import (`from get_met_details import ...`) with no package structure — fragile, only works if `utils/` happens to be the working directory.

---

## 3. Streamlit Best Practices

- **`st.cache_data`/`st.cache_resource` are used nowhere in the entire codebase** (confirmed by grep across `dashboard.py`, `scripts/`, `utils/`). Every render function re-reads its CSV/JSON from disk, and `scripts/render_aqi_pdf.py` re-base64-encodes the full IMD PDF, on every single rerun/tab click. This is the single highest-impact Streamlit-specific fix available (see Performance §8).
- `st.session_state` is used for exactly one thing (`is_mobile`, `dashboard.py:45-46`) — not a maturity problem by itself, but it means there's no existing pattern to build on for auth session state (§6) or cross-tab filter state (§5).
- Navigation is a single `st.tabs([...])` block with 7 hardcoded tabs — reasonable for 7 items, but note tab state does **not** survive a rerun triggered from outside the tabs (e.g. a global filter), which will matter if you add the cross-cutting filters suggested in §5.
- Device detection via `streamlit_javascript.st_javascript("window.innerWidth")` blocks the entire app with `st.stop()` if the JS call returns `None` (`dashboard.py:41-43`) — no retry, no fallback, no way to force desktop/mobile manually. On a flaky connection or inside an iframe this can render a permanently blank "Detecting device type…" screen.
- The manual CSS-hiding block (`dashboard.py:56-62`) targets Streamlit's auto-generated `.css-1aumxhk`/`.css-1y4p8pa` classes, which are version-specific and change across Streamlit releases — likely already stale against the installed 1.45.1. Prefer `st.set_page_config`/theming or documented CSS anchors over guessing at internal class names.
- No loading indicators (`st.spinner`) around any external call — a slow CPCB/Gemini fetch just shows a frozen tab.
- No re-run/refresh affordance for the user — if the underlying data updates mid-session, the only way to see it is a manual browser refresh.

---

## 4. UI / UX Review

Benchmarked against internal analytics tools (Grafana, Datadog, Looker, Cloud Console style — dense, functional, low-chrome), not consumer apps.

**What's working:** tab-based navigation for 7 sections is appropriate at this scale; the mobile/desktop split shows real attention to responsive use; a real theme is configured (not default Streamlit).

**What needs work:**
- **Duplicated markup as a design smell, not just a code smell.** The literal `<hr style='border: 0.3px solid gray;...'>` string appears **11 times** verbatim in `dashboard.py`, and the AQEWS-outage banner HTML is duplicated near-identically between the mobile and desktop branches. Any visual tweak today requires editing the same style in 5–10 places — this is exactly the kind of drift that produces the "inconsistent spacing/dividers" feel typical of ungoverned dashboards. Centralizing into `style.css` classes + 2–3 small Python helpers (`hr()`, `outage_banner()`) is both a code and a visual-consistency fix.
- **Visual hierarchy relies on ad hoc inline HTML** (`dashboard.py:102-129`, `159-170`) with hand-picked font sizes/colors per block rather than a defined type scale — a Grafana/Datadog-style dashboard typically has 3-4 defined text levels (page title, section header, metric label, body) applied consistently via CSS classes, not per-instance inline styles.
- **Density:** each tab is single-column, one chart/section at a time, with generous vertical whitespace (`st.write("")` used as a spacer in ~10 places) — for an internal ops-style dashboard, a denser multi-column layout (metrics row + chart side-by-side) reads as more "product-grade" than a scrolling single-column page, and reduces the amount of scrolling to compare related numbers.
- **No persistent "state of the system" strip** — Grafana/Datadog-style tools put a slim status bar at the top (last data refresh time per source, any pipeline errors) that's visible regardless of which tab you're on. Today, "last updated" only appears in the footer after scrolling through all 7 tabs, and there's no visibility into *per-source* freshness (e.g., did the CPCB fetch succeed today, even if IMD did not).
- **Color usage is inconsistent across ad hoc inline styles** (`#e6f0ff`, `#E6E6FA`/`#4B0082`, `#ffcccc`/`#cc0000`, plus the `primaryColor="#1b1bda"` theme) — no single defined palette for status/severity that's reused consistently (e.g. the AQI category colors are hand-maintained separately in `scripts/delhi_weather.py`, see §2, rather than driving the UI's accent colors too).
- Minor but visible: placeholder `mailto:john@example.com` in the app's own "Get Help"/"Report a bug" menu (`dashboard.py:29-30`), and a hardcoded `© 2025` footer that is already stale (today is 2026-07-20).

**Concrete UI component suggestions** (fits naturally, no new dependency required beyond what's installed):
- A slim top status strip: per-source last-refresh timestamp + a red/green dot, using `st.columns` + `st.metric`.
- Convert the two "Today's AQ Update" HTML banners into 2-3 `st.metric`/`st.container(border=True)` cards — Streamlit's native bordered containers (available in 1.45.1) give a "card" look without hand-rolled CSS.
- A single reusable `hr()`/`section_header(title)` helper (see §2) instead of the repeated literal `<hr>` string.

---

## 5. Dashboard Features

Recommendations that fit the *existing* data/pipelines — not speculative additions:

- **Per-source data-freshness indicator.** You already compute "last updated" once for the whole page; the underlying data is that CPCB, IMD, and AQEWS are fetched by *separate* cron jobs that can fail independently (confirmed in §2/§3 — several fetchers have no retry and swallow exceptions). A small "data health" panel (last successful fetch per source, red flag if a JSON/CSV is stale beyond its expected cadence) would directly surface the failure modes already possible in the current pipeline, and is cheap to build from file mtimes alone.
- **Surface the existing AQEWS-outage flag more prominently.** `render_aqi_fc.py`'s `get_error_message()` already detects an AQEWS outage condition (`dashboard.py:132,176`) — right now it only shows inside the "Today's AQ Update" tab. Promoting this to the global status strip above would make an existing signal more visible without new data work.
- **Archive/trend comparison.** `scripts/archive.py` and `data/archive.json` already hold the full multi-day history — a "compare to same date last winter" or a rolling 7/14-day trend sparkline next to today's AQI card is a natural extension of data you already collect and haven't yet surfaced as a trend (only `scripts/recent_trends.py` touches this today).
- **Export.** Given this is used internally for monitoring/reporting, a "download this tab's data as CSV" button (`st.download_button`) on the archive and forecast tabs would be low-effort and high-value for anyone compiling reports from this dashboard.
- **AI-summary provenance.** `utils/get_gemini_summary.py` already generates an LLM summary of the IMD bulletin — the UI should visibly label AI-generated text as such (with a timestamp of when it was generated) so viewers don't mistake it for the original bulletin text; this is good practice generally and specifically relevant given CEEW's standards around distinguishing verified data from AI output.

Not recommending: user-facing anomaly detection / ML-based alerting — no existing modeling pipeline or labeled ground truth for anomalies exists in this codebase today, so that would be new infrastructure rather than a natural extension. Flagging it as a possible future item rather than a near-term feature.

---

## 6. Google Authentication

**Current state:** no authentication exists at all (confirmed by full-codebase search) — the dashboard is completely open to anyone who can reach it.

**Feasibility:** high. Streamlit 1.45.1 (the version already pinned in `py_envs/requirements.txt`) ships **native `st.login()`/`st.logout()`** backed by Authlib, which supports Google as a generic OIDC provider — no third-party Streamlit component needed.

**Recommended approach (simplest production-ready path):**
1. Register an OAuth 2.0 Client ID in Google Cloud Console (Workspace-restricted), authorized redirect URI = the deployed dashboard URL.
2. Add to `.streamlit/secrets.toml` (which already exists and already holds `GEMINI_API_KEY`):
   ```toml
   [auth]
   redirect_uri = "https://<your-domain>/oauth2callback"
   cookie_secret = "<random-string>"
   client_id = "<from Google Cloud Console>"
   client_secret = "<from Google Cloud Console>"
   server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
   ```
3. In `dashboard.py`, gate the page behind login before any tab content renders:
   ```python
   if not st.user.is_logged_in:
       st.button("Log in with Google", on_click=st.login)
       st.stop()
   ```
4. **Domain restriction (role-based access, simplest form):** since every user is on the CEEW Workspace, check `st.user.email.endswith("@ceew.in")` after login and reject/log out anyone outside that domain — this is a reasonable first-cut "role" given no existing role system exists in the codebase today. A small `config/access.py` allowlist can extend this later if finer-grained roles (e.g. admin-only archive editing) become necessary.
5. **Logout:** `st.button("Log out", on_click=st.logout)` — clears the session cookie.
6. **Session handling:** `st.user` is populated from the signed session cookie Streamlit manages itself (via `cookie_secret`); no manual session-state bookkeeping is needed beyond what's already in `st.session_state.is_mobile`.

**Security considerations:**
- `cookie_secret` and the OAuth client secret must live only in `secrets.toml` (never hardcoded — see §7, which already flags a precedent of hardcoded keys in this codebase that must not repeat here).
- Since there's no HTTPS/reverse-proxy config visible in this repo (no Docker/nginx config found), confirm wherever this is deployed terminates TLS in front of Streamlit — OAuth redirect URIs must be `https://` in production.
- This native approach avoids needing `streamlit-google-auth` or hand-rolled `google-auth-oauthlib` flows, which would otherwise require you to build the session-cookie handling Streamlit now does for you.

---

## 7. Security Review

**Critical:**
- **Hardcoded Gemini API key in two files**, `utils/get_aqi_fc_cat.py:13` and `utils/get_v_index.py:13` (identical value in both) — passed to `genai.configure(api_key=API_KEY)`. This is inconsistent with the correct pattern already used three lines away in spirit at `utils/get_gemini_summary.py:13` (`st.secrets["GEMINI_API_KEY"]`). **Action: move both to `st.secrets`, and rotate the key**, since it has been sitting in plaintext on disk — treat as compromised regardless of git history.

**High:**
- **No authentication at all** on an internal-only dashboard with no other access control layer visible (no Docker/nginx/firewall config in this repo) — see §6 for the fix.
- **No `.gitignore` and no git repo yet**, while a 963 MB virtualenv (`py_envs/`) and `.streamlit/secrets.toml` both sit inside the project directory. **Before this is ever `git init`'d**, a root `.gitignore` must exclude at minimum: `py_envs/`, `.streamlit/secrets.toml`, `__pycache__/`, `.cache.sqlite`, `.DS_Store`, `nohup.out`, and generated files under `data/`.
- SSL verification disabled (`verify=False`) against `cpcb.nic.in` in three files, with warnings suppressed via `urllib3.disable_warnings()`. A `cpcb_cert.pem` exists (apparently generated to fix this properly) but is never passed to `requests`. This should either be finished (pin the cert) or the risk explicitly accepted and documented — silently disabling verification is the weaker of the two options.

**Medium:**
- Hardcoded absolute local path in `utils/get_gemini_summary.py:14` (`/Users/Vishwas/Desktop/CEEW/...`) — not a secret, but will silently break on any other machine/deployment and should use the same `Path`/`DATA_DIR` pattern already used elsewhere in that file.
- No input validation is a lower concern here since there's no user-submitted input anywhere in the app (no forms, no query params consumed) — not flagging as a gap.
- Logging gaps (ad hoc `print()`, broad `except Exception` swallowing errors, no persisted structured logs) mean a security-relevant failure (e.g. a fetch silently failing, an auth misconfiguration once added) may go unnoticed — see §9 for the logging fix, which is also a security-observability fix.

**Not a current issue, but on the horizon:** no personal/participant data appears in this codebase (it's public environmental monitoring data), so CEEW's data-handling rules around personal/survey data don't appear implicated here — worth re-confirming once/if any user-account data (from §6's auth work) starts being logged or stored.

---

## 8. Performance Review

Ranked by expected impact for the effort required:

1. **(Highest impact, lowest effort) Add `st.cache_data`/`st.cache_resource`.** Zero caching exists anywhere today. Every rerun re-reads JSON/CSV from disk and, worse, re-does the PDF base64-encode in `scripts/render_aqi_pdf.py` and re-renders every chart from scratch. Wrapping the `utils/get_*` data-loading functions in `@st.cache_data(ttl=...)` (a TTL matched to the ~daily update cadence, e.g. 1 hour) would cut redundant disk I/O and recomputation on every tab click/interaction with minimal code change.
2. **(High impact, low effort) Add timeouts to the two ungated `requests.get()` calls** (`utils/get_aqi_cpcb_v2.py`'s PDF GET, `get_imd_aqbulletin.py:34`) — currently these can hang a cron job indefinitely.
3. **(Medium impact, medium effort) Stop full-file CSV/JSON rewrites on every fetch** (`utils/get_aqi_cpcb_v2.py`, `utils/download_cpcb_bulletin.py`, `utils/get_fire_pbhr.py`, `utils/update_archive_json.py`) — append-only or partitioned writes would scale better as the archive grows across winters, though this is not yet a bottleneck at current file sizes (largest is `archive.json` at 138 KB).
4. **(Medium impact, low effort once flagged) Remove the two dead pipelines** (`get_imd_aqbulletin.py`, and the Selenium `get_forecast_aqi.py`→`agg_aqi_fc.py` chain) if they are still running on a cron schedule — the Selenium browser spin-up in particular is the single heaviest operation in the codebase and appears to produce data nothing reads.
5. **(Low impact, already-good pattern) `utils/meteo_api.py`** is the one file with proper `requests_cache` + retry/backoff — worth using as the template when consolidating the other fetchers (§2), rather than a performance problem in itself.

No async/parallelization work is recommended as a first step — the day-by-day backfill loops in `utils/get_hist_aqi.py`/`utils/get_aqi_cpcb_v2.py` are slow but run rarely (historical backfill, not the daily hot path), so caching and timeouts will deliver most of the available win before concurrency is worth the added complexity.

---

## 9. Code Quality

- **No type hints anywhere** in the reviewed code (`dashboard.py`, `scripts/`, `utils/`) — e.g. `scripts/render_aqi_fc.py:13`'s `generate_pm_plot(df, x_col, y_cols, val)` has no parameter/return annotations. Not urgent to retrofit everywhere, but worth adopting for any new/refactored code from this review (especially the proposed shared helpers in §2).
- **No docstrings** in `dashboard.py` or roughly half the `utils/`/`scripts/` files. Given the render/fetch naming convention is already self-descriptive (`render_aqi_delhi`, `get_hist_aqi`), a one-line docstring per public function noting *inputs/outputs and side effects* (e.g. "writes to data/archive.json") would help more than restating the function name.
- **No structured logging** — `import logging` appears nowhere in the project; status/error reporting is ~30 scattered `print()` calls, several standing in for actual error handling (`print(f"[Warning] ...")` with no re-raise, no context, no timestamp in most cases). Recommend one `logging.getLogger(__name__)` per module, INFO for status, WARNING/ERROR for the current broad-except cases, writing to a rotating file for cron jobs (rather than relying on `nohup.out`, which is the current de facto log).
- **Dead code**: unused `fig_title` variable computed in both `scripts/render_aqi_fc.py:18` and `scripts/render_pm25_fc.py:17`; unused `pandas`/`plotly.express` imports in a few files (§2 duplication table covers the functional duplicates).
- **Naming**: the `render_*`/`get_*` convention is good and consistent; the exception is that some render-producing modules aren't prefixed `render_` at the filename level (`weather_fcast.py`, `interventions.py`, `farm_fires.py`, `archive.py`, `sectors.py`) even though they export `render_*` functions — a minor but easy consistency fix during the `scripts/`→`views/` rename in §1.
- **Configuration management**: no central config file — cutoff times, AQI bins, breakpoints, and API URLs are inline literals repeated across files (root cause of the §2 duplication and the §2 cutoff-time bug). A `config/settings.py` module is the single most leveraged code-quality fix in this review, since it would also resolve several of the duplication and correctness issues above rather than being a separate task.

---

## 10. Prioritized Improvement Roadmap

### Quick Wins (1–2 hours each)
| Item | Priority | Impact | Why |
|---|---|---|---|
| Rotate + move the two hardcoded Gemini API keys (`utils/get_aqi_fc_cat.py:13`, `utils/get_v_index.py:13`) to `st.secrets` | **Critical** | High | Plaintext credential on disk; must fix before any git init or sharing |
| Add a root `.gitignore` (exclude `py_envs/`, `secrets.toml`, `data/` generated files, caches) | Critical | High | Prevents a 963 MB venv + secrets from being committed the moment this becomes a repo |
| Add timeouts to the 2 ungated `requests.get()` calls | High | Medium | Prevents an indefinite hang in a cron job |
| Fix the placeholder `mailto:john@example.com` and stale `© 2025` footer | Low | Low | Visible, easy, currently reads as unfinished |
| Wrap the ~8 data-loading `utils/get_*` functions in `@st.cache_data(ttl=3600)` | High | High | Single highest perf win available; near-zero risk |
| Add `st.spinner()` around the external-call render functions | Medium | Medium | Basic UX polish, avoids "frozen tab" feel during fetch |

### Medium Improvements (1–2 days)
| Item | Priority | Impact | Why |
|---|---|---|---|
| Unify the 4 conflicting "effective date"/cutoff implementations into one `config/settings.py` constant | **High** | High | Currently a real correctness bug — different tabs can disagree on "today" for ~5 hours a day |
| Extract shared helpers: `hr()`/`outage_banner()` in dashboard.py, `ordinal()`, CPCB URL builder, JSON read-modify-write | High | Medium | Removes the largest duplication cluster; makes future edits single-source |
| Add Google Workspace login via native `st.login()`/`st.logout()` + `@ceew.in` domain check | High | High | Currently zero access control on an internal tool |
| Replace `print()`-based status/error reporting with `logging` module + rotating file handler | Medium | Medium | Currently failures are invisible once deployed under `nohup` |
| Remove or clearly quarantine the two dead pipelines (`get_imd_aqbulletin.py`, Selenium `get_forecast_aqi.py` chain) and orphaned data files (`gemini_summary1.json`, `archive_backup_v0.json`) | Medium | Medium | Reduces maintenance surface, removes the heaviest operation in the codebase if it's still cron-scheduled |
| Add a top status strip (per-source last-refresh + AQEWS-outage flag promoted from tab 1) | Medium | Medium | Surfaces failure modes that already exist in the pipeline but aren't visible today |

### Major Refactors (1–2 weeks)
| Item | Priority | Impact | Why |
|---|---|---|---|
| Consolidate `utils/` fetchers into per-source modules (CPCB, IMD, AQEWS) with one shared HTTP session/retry/timeout policy, modeled on the already-correct `utils/meteo_api.py` pattern | High | High | Removes the largest code-duplication cluster in the project and fixes the SSL-verification and no-timeout issues in one pass |
| Rename/restructure `scripts/`→`views/`, `utils/`→`ingestion/`, split `dashboard.py` into a thin entrypoint + `components.py` | Medium | Medium | Structural clarity as the app grows; not urgent, best done alongside the helper extraction above |
| Introduce a real `requirements.txt` at root (generated from the venv, trimmed to actual imports) + basic project packaging so a new dev doesn't need to reverse-engineer `py_envs/requirements.txt` | Medium | Medium | Currently the root `requirements.txt` is empty; onboarding friction |
| Add a minimal test suite around the pure-logic pieces (date/cutoff logic, AQI category binning, JSON merge logic) | Medium | Medium | Zero tests exist today; the cutoff-time bug in particular would have been caught by one unit test |
| CI/CD: a basic GitHub Actions workflow (lint + the above tests) once this becomes a git repo | Low | Medium | No CI exists today; natural follow-on once tests exist and the repo is initialized |

---

## Notes on scope
- Everything above is based on reading the actual files in this working directory (verified `dashboard.py` line-by-line; line counts and structure for all 31 `.py` files confirmed via direct file reads and `wc -l`). No secret values were read or reproduced — hardcoded-credential findings are reported as file:line locations only.
- This document is the deliverable itself (a review, not a code change) — no files have been modified.
