import streamlit as st
import pandas as pd
import streamlit.components.v1 as components


def render_fires_dashboard():
    _, colPlot, _ = st.columns([0.01, 1, 0.01])
    with colPlot:
        components.iframe("https://signals-demo.earthmetry.com/superset/dashboard/fires-pb-hr?standalone=True", height=950)