import streamlit as st

from views.components import outage_banner, section_header
from views.sky import render_weather_card
from views.widgets import render_kpi_grid


def render_home_overview(error_flag, is_mobile=False):
    """Landing page: weather-style KPI cards for air and met conditions. The
    day's written update lives in the hero's Key insights dialog."""
    section_header("Conditions now", caption="Air quality, dispersion and weather for Delhi at a glance")
    render_kpi_grid()
    if error_flag:
        outage_banner(compact=is_mobile)
    section_header("Delhi weather", caption="Observed now, next 24 hours and 3-day outlook")
    render_weather_card()
