import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from datetime import datetime, timedelta

def day_suffix(day):
    if 11 <= day <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    

def render_pm25_hourly(isMobile=False, compact=False):
    height = 950 if not compact else 450
    _, colPlot, _ = st.columns([0.01, 1, 0.01])
    with colPlot:
        today = datetime.today()
        seven_days_ago = today - timedelta(days=6)
        start_str = f"{seven_days_ago.day}{day_suffix(seven_days_ago.day)} {seven_days_ago.strftime('%b %Y')}"
        end_str = f"{today.day}{day_suffix(today.day)} {today.strftime('%b %Y')}"
        range_str = f"{start_str} - {end_str}"
        html = f"""
        <div class="time-period-badge">
            <strong>Time Period:&nbsp;{range_str}</strong>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)
        st.write("")
        st.badge("**Note:** AQI is from 11 AM to 11 AM", color="blue")
        st.write("")
        src = "https://signals-demo.earthmetry.com/superset/dashboard/delhi-2025?standalone=True"
        if isMobile==True:
            st.link_button("Go to Dashboard", src, type="primary")
            st.markdown("""
            <script>
            const links = window.parent.document.querySelectorAll('a[data-testid="stLinkButton"]');
            links.forEach(link => link.setAttribute('target', '_blank'));
            </script>
            """, unsafe_allow_html=True)
        else:
            components.iframe(src, height=950, scrolling=True)
        