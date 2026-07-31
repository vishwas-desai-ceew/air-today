import streamlit as st
from views.interventions import render_interventions
from views.farm_fires import render_farm_fires
from views.recent_trends import render_recent_trends

def render_aqi_insights():

    options = ["**Recent Trends**", "**Farm Fires in Punjab and Haryana**", "**Prevention Measures**"]
    selection = st.pills("**Know More**", options, selection_mode="single", default=options[0])
    if selection == options[0]:
        with st.expander(":red-badge[**Trends**]", expanded=True):
            st.markdown("<h3>Recent Trends in PM<sub style='font-size:15px;'> 2.5</sub> concentrations</h3>", unsafe_allow_html=True)
            st.write("")
            render_recent_trends()
    elif selection == options[1]:
        with st.expander(":red-badge[**Farm Fires**]", expanded=True):
            st.markdown("<h3>Farm Fires in Punjab and Haryana</h3>", unsafe_allow_html=True)
            st.write("")
            render_farm_fires()
    elif selection == options[2]:
        with st.expander(":red-badge[**Interventions**]", expanded=True):
            st.markdown("<h3>Interventions to Tackle Air Pollution</h3>", unsafe_allow_html=True)
            st.write("")
            render_interventions()
    else:
        st.warning("Select an option")
    
