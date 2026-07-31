import pytz
import streamlit as st
from datetime import datetime, timedelta
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
from views.components import hr, outage_banner, render_status_strip, section_header
from views.home import render_home_overview, render_glossary
from pathlib import Path
from streamlit_javascript import st_javascript
from config.settings import EFFECTIVE_DATE_CUTOFF
from config.access import is_allowed_user, ALLOWED_EMAIL_DOMAIN

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

st.markdown("""
<meta name="viewport" content="width=device-width, initial-scale=1.0">
""", unsafe_allow_html=True)

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
        _, login_column, _ = st.columns([1, 1.35, 1])
        with login_column:
            with st.container(border=False, key="auth-login"):
                logo_left, logo, logo_right = st.columns([1, 1.4, 1])
                with logo:
                    st.image("assets/ceew_bg.png", width='stretch')
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
                st.button("Sign in with Google", on_click=st.login, key="login_button", type="primary", icon=":material/login:", width='stretch')
        st.stop()
    if not is_allowed_user(st.user):
        st.error(f"Access is restricted to @{ALLOWED_EMAIL_DOMAIN} accounts.")
        st.button("Log out", on_click=st.logout, key="logout_button_1", type="secondary")
        st.stop()

width = st_javascript("window.innerWidth")

if width is None:
    st.info("Detecting device type…")
    st.stop()

st.session_state.is_mobile = width <= 768
is_mobile = st.session_state.is_mobile

# Hide the default Streamlit header and footer
st.markdown("""
    <style>
    .css-1aumxhk, .css-1y4p8pa {
        visibility: hidden;
    }
    </style>
""", unsafe_allow_html=True)


# ---------- Main header ---------- #
with st.container(border=False, key="air-today-hero"):
    col1, col2 = st.columns([3, 1], vertical_alignment="center")
    with col1:
        st.markdown(
            """
            <div class="hero-eyebrow"><span></span>Delhi air quality update</div>
            <h1 class="hero-title">Air Today</h1>
            <p class="hero-copy">Daily updates on Delhi's air pollution</p>
            """,
            unsafe_allow_html=True,
        )
        if AUTH_CONFIGURED:
            st.markdown("<br>", unsafe_allow_html=True)
            c1, c2, _= st.columns([1, 1, 3], gap="small")
            with c1:
                st.markdown(f'<span class="static-user-button"><svg xmlns="http://www.w3.org/2000/svg" enable-background="new 0 0 20 20" height="20px" viewBox="0 0 20 20" width="18px" fill="#FFFFFF"><g><rect fill="none" height="20" width="18"/></g><g><g><path d="M10 5.5c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3zm0 4.5c-.83 0-1.5-.67-1.5-1.5S9.17 7 10 7s1.5.67 1.5 1.5S10.83 10 10 10z"/><path d="M10 2c-4.42 0-8 3.58-8 8s3.58 8 8 8 8-3.58 8-8-3.58-8-8-8zm0 14.5c-1.49 0-2.86-.51-3.96-1.36C7.19 14.42 8.55 14 10 14s2.81.42 3.96 1.14c-1.1.85-2.47 1.36-3.96 1.36zm5.07-2.44c-1.44-.99-3.19-1.56-5.07-1.56s-3.62.58-5.07 1.56C4.04 12.95 3.5 11.54 3.5 10c0-3.58 2.92-6.5 6.5-6.5s6.5 2.92 6.5 6.5c0 1.54-.54 2.95-1.43 4.06z"/></g></g></svg> {st.user.name}</span>', unsafe_allow_html=True)
            with c2:
                st.button("Log out", on_click=st.logout, key="logout_button_2", type="primary", icon=":material/logout:", use_container_width=False)
    if not st.session_state.is_mobile:
        with col2:
            st.image("assets/ceew_bg.png", width='stretch')

st.space(1)

#hr(margin_top="0.5rem", margin_bottom="1rem", style="dashed")

error_flag, _ = get_error_message()

now = datetime.now()
if now.time() >= EFFECTIVE_DATE_CUTOFF:
    date_str = now.strftime("%d %B %Y")
else:
    date_str = (now - timedelta(days=1)).strftime("%d %B %Y")


# ---------- Pages ---------- #
# Each page below is a thin wrapper: it only decides layout/grouping. Every
# render_*() call is the same existing function from views/, unchanged, per
# design.md ("presentation-layer regrouping only").

def page_overview():
    render_home_overview(error_flag, is_mobile=is_mobile)
    

def page_today():
    aqi_rows = render_aqi_delhi(compact=is_mobile)
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
    section_header("Weather Forecast")
    render_weather_fcast()


def page_fires():
    section_header("Fire counts - Punjab & Haryana")
    render_fires_dashboard()
    with st.expander("Context: farm fires in Punjab and Haryana"):
        render_farm_fires()

def page_pm25():
    section_header("Pollutant and AQI tracker")
    render_pm25_hourly()

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


pages = {
    "Overview": [st.Page(page_overview, title="Overview", icon=":material/insights:", default=True)],
    "Air Quality": [
        st.Page(page_today, title="Today's Update", icon=":material/event:"),
        st.Page(page_forecast, title="Forecast", icon=":material/trending_up:"),
    ],
    "Trackers": [
        st.Page(page_pm25, title="PM2.5 Tracker", icon=":material/aq:"),
        st.Page(page_weather, title="Weather Tracker", icon=":material/weather_hail:"),
        st.Page(page_fires, title="Fires Tracker", icon=":material/local_fire_department:"),
    ],
    "Reference": [
        st.Page(page_bulletin, title="IMD Bulletin", icon=":material/push_pin:"),
        st.Page(page_interventions, title="Sectoral Interventions", icon=":material/assistant:"),
        st.Page(page_general_info, title="Briefing Note", icon=":material/info:"),
        st.Page(page_trends, title="Recent Trends", icon=":material/bar_chart:"),
        st.Page(page_glossary, title="Glossary", icon=":material/book:")
    ],
    "Archive": [st.Page(page_archive, title="Archived Updates", icon=":material/archive:")]
}

ist = pytz.timezone("Asia/Kolkata")
upd_time = datetime.now(ist).strftime("%d %b %Y, %I:%M %p")

# Keep application identity and supporting details with the navigation.  This
# is deliberately separate from the page hero so it remains visible while
# users move between dashboard pages.
st.sidebar.markdown(
    """
    <div class="sidebar-brand" role="banner" aria-label="AirToday, Delhi">
        <div class="sidebar-brand-mark" aria-hidden="true">AT</div>
        <div>
            <div class="sidebar-brand-name">AirToday</div>
            <div class="sidebar-brand-caption">Delhi</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

nav = st.navigation(pages, position="sidebar", expanded=True)
render_status_strip(error_flag)
hr(margin_top="-2rem", margin_bottom="1rem")
st.sidebar.markdown(
    f"""
    <div class="sidebar-footer">
        <div>Last updated: {upd_time}</div>
        <div>© {datetime.now(ist).year} CEEW. All rights reserved.</div>
    </div>
    """,
    unsafe_allow_html=True,
)
nav.run()
