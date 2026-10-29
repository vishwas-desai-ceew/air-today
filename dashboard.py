import pytz
import streamlit as st
from datetime import datetime
from views.interventions import render_interventions
from views.farm_fires import render_farm_fires
from views.pm25_hourly import render_pm25_hourly
from views.recent_trends import render_recent_trends
from views.archive import render_archive_data
from views.weather_fcast import render_weather_fcast
from views.delhi_weather import render_aqi_delhi, render_health_advisory
from views.render_aqi_pdf import render_aqi_pdf
from views.render_farm_firesh_dash import render_fires_dashboard
from views.render_google_doc import render_google_doc
from views.render_aqi_fc import render_aqi_fc, get_error_message
from views.render_pm25_fc import render_pm25_fc
from views.components import hr, outage_banner, section_header
from views.home import render_home_overview, render_glossary
from views.widgets import render_hero, render_insights_panel, render_topbar
from pathlib import Path
from config.access import is_allowed_user, origin_mismatch, ALLOWED_EMAIL_DOMAIN

# Set up the Streamlit page configuration
st.set_page_config(
        page_title="CEEW Air Today",
        page_icon="assets/icon.png",
        layout="wide",
        menu_items={
        'Get Help': 'mailto:john@example.com',
        'Report a bug': "mailto:john@example.com",
        'About': "# Winter Updates \n Made with ❤️ in India"
        }
    )

css_path = Path("style.css")
if css_path.exists():
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
else:
    st.warning("style.css not found")

# --- Google Workspace login gate ---
# Inactive no-op until an [auth] section (client_id/client_secret/cookie_secret,
# from a Google Cloud Console OAuth client) is added to .streamlit/secrets.toml.
# See project-refactor-status.md for the exact setup steps.
try:
    AUTH_CONFIGURED = "auth" in st.secrets
except Exception:
    # st.secrets raises (rather than returning False) when secrets.toml doesn't
    # exist at all - only hit on a fresh checkout with zero secrets configured.
    AUTH_CONFIGURED = False
if AUTH_CONFIGURED:
    if not st.user.is_logged_in:
        # Google returns users to redirect_uri's host. If they started on a
        # different host (localhost vs 127.0.0.1) the login-state cookie isn't
        # sent back and the sign-in silently loops - so send them to the
        # right host before they click.
        canonical = origin_mismatch(
            st.context.url,
            st.secrets["auth"].get("redirect_uri", ""),
            st.get_option("server.port"),
        )
        _, login_column, _ = st.columns([1, 1.35, 1])
        with login_column:
            with st.container(border=False, key="auth-login"):
                logo_left, logo, logo_right = st.columns([1, 1.4, 1])
                with logo:
                    st.image("assets/ceew_bg_t.png", width='stretch')
                st.markdown(
                    f"""
                    <div class="auth-login-copy">
                        <div class="auth-login-eyebrow">CEEW Air Quality Platform</div>
                        <h1>Air Today</h1>
                        <p>Sign in with your CEEW Google Workspace account (<strong>@{ALLOWED_EMAIL_DOMAIN}</strong>)</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if canonical:
                    st.link_button("Continue to sign in", canonical, type="primary", icon=":material/login:", width='stretch')
                    st.caption(f"Sign-in only works from {canonical}.")
                else:
                    st.button("Sign in with Google", on_click=st.login, key="login_button", type="primary", icon=":material/login:", width='stretch')
        st.stop()
    if not is_allowed_user(st.user):
        st.error(f"Access is restricted to verified @{ALLOWED_EMAIL_DOMAIN} Google Workspace accounts.")
        st.button("Log out", on_click=st.logout, key="logout_button_1", type="secondary")
        st.stop()

# Device detection from the User-Agent header. Replaces the st_javascript
# probe, which rendered a "Detecting device type…" screen and forced an extra
# rerun on every page load.
user_agent = st.context.headers.get("User-Agent", "")
st.session_state.is_mobile = any(k in user_agent for k in ("Mobi", "Android", "iPhone"))
is_mobile = st.session_state.is_mobile

error_flag, _ = get_error_message()


# ---------- Pages ---------- #
# Each page below is a thin wrapper: it only decides layout/grouping. Every
# render_*() call is the same existing function from views/, unchanged, per
# design.md ("presentation-layer regrouping only").

def page_overview():
    render_hero()
    render_home_overview(error_flag, is_mobile=is_mobile)


def page_today():
    section_header("Daily update", caption="CPCB bulletin, key insights and health advisory")
    aqi_rows = render_aqi_delhi(compact=is_mobile, show_insights=False)
    with st.container(key="insights-inline"):
        st.markdown("<div class='aqi-panel-title'>Key insights</div>", unsafe_allow_html=True)
        render_insights_panel()
    render_health_advisory(aqi_rows)
    if error_flag:
        outage_banner(compact=is_mobile)


def page_forecast():
    section_header("AQEWS 10-day Forecast", caption="AQI and PM2.5 forecasts")
    fc_options = ["**AQI**", "**PM2.5**"]
    selection = st.segmented_control(
            "**Select Variable**",
            options=fc_options,
            selection_mode="single",
            default=fc_options[0],
            key="var_selection",
        )
    hr(margin_top="-1rem", margin_bottom="1rem", style="dashed")
    if selection == fc_options[0]:
        render_aqi_fc(compact=is_mobile)
    else:
        render_pm25_fc()


def page_weather():
    section_header("Weather Forecast", caption="Open-Meteo, next 3 days")
    render_weather_fcast()


def page_fires():
    section_header("Fire counts - Punjab & Haryana")
    render_fires_dashboard()
    with st.expander("Context: farm fires in Punjab and Haryana"):
        render_farm_fires()

def page_pm25():
    section_header("Pollutant and AQI tracker", caption="CAAQMS station data")
    render_pm25_hourly(isMobile=is_mobile)

def page_bulletin():
    section_header("IMD - AQ Bulletin")
    render_aqi_pdf()


def page_interventions():
    section_header("AQ Sectoral Interventions")
    render_interventions()


def page_general_info():
    section_header("Clean Air Team - Briefing Note")
    render_google_doc()


def page_trends():
    section_header("Recent Trends")
    render_recent_trends()


def page_archive():
    section_header("Archived Updates", caption="View past updates")
    render_archive_data()

def page_glossary():
    section_header("Glossary")
    render_glossary()


# Four groups, ordered by how often each is used: today's picture first,
# live trackers next, documents, then background reading.
pages = {
    "Today": [
        st.Page(page_overview, title="Overview", icon=":material/partly_cloudy_day:", default=True),
        st.Page(page_today, title="Daily update", url_path="daily-update", icon=":material/article:"),
        st.Page(page_forecast, title="Forecast", url_path="forecast", icon=":material/trending_up:"),
    ],
    "Trackers": [
        st.Page(page_pm25, title="Pollutants (CAAQMS)", url_path="pollutants", icon=":material/aq:"),
        st.Page(page_weather, title="Weather", url_path="weather", icon=":material/air:"),
        st.Page(page_fires, title="Farm fires", url_path="fires", icon=":material/local_fire_department:"),
    ],
    "Reports": [
        st.Page(page_bulletin, title="IMD bulletin", url_path="imd-bulletin", icon=":material/picture_as_pdf:"),
        st.Page(page_general_info, title="Briefing note", url_path="briefing-note", icon=":material/description:"),
        st.Page(page_archive, title="Archive", url_path="archive", icon=":material/history:"),
    ],
    "Learn": [
        st.Page(page_trends, title="Recent trends", url_path="trends", icon=":material/bar_chart:"),
        st.Page(page_interventions, title="Sectoral interventions", url_path="interventions", icon=":material/policy:"),
        st.Page(page_glossary, title="Glossary", url_path="glossary", icon=":material/menu_book:"),
    ],
}

ist = pytz.timezone("Asia/Kolkata")

# st.navigation always renders first in the sidebar, so the brand goes in
# st.logo (which Streamlit places above it) rather than a markdown block.
st.space(2)
st.logo("assets/ceew_bg_t.png", size="small", icon_image="assets/icon.png")

nav = st.navigation(pages, position="sidebar", expanded=True)
# Overview has the full hero; every other page gets the slim top bar with
# the same data-health and user controls.
if nav.url_path:
    render_topbar()
# New Delhi clock: rendered server-side, then ticked in the browser (no app
# reruns needed). The interval is stored on window so reruns don't stack timers.
now_ist = datetime.now(ist)
st.sidebar.html(
    f"""
    <div class="sidebar-footer">
        <div class="ist-clock" aria-live="off">
            <div class="ist-clock-label">New Delhi time (IST)</div>
            <div class="ist-clock-time" id="ist-clock-time">{now_ist.strftime("%H:%M")}</div>
            <div class="ist-clock-date" id="ist-clock-date">{now_ist.strftime("%d %B %Y").lstrip("0")}</div>
        </div>
        <div>© {now_ist.year} CEEW. All rights reserved.</div>
    </div>
    <script>
    (function () {{
        const tick = () => {{
            const now = new Date();
            const t = document.getElementById("ist-clock-time");
            const d = document.getElementById("ist-clock-date");
            if (!t || !d) return;
            t.textContent = now.toLocaleTimeString("en-GB", {{timeZone: "Asia/Kolkata", hour: "2-digit", minute: "2-digit", hour12: false}});
            d.textContent = now.toLocaleDateString("en-GB", {{timeZone: "Asia/Kolkata", day: "numeric", month: "long", year: "numeric"}});
        }};
        tick();
        if (window.__istClock) clearInterval(window.__istClock);
        window.__istClock = setInterval(tick, 10000);
    }})();
    </script>
    """,
    unsafe_allow_javascript=True,
)
nav.run()
