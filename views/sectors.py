import streamlit as st
import pandas as pd

def load_sector_data():
    return pd.read_csv("data/sectors.csv")

sectors_df = load_sector_data()

def render_sector_contributions():
    _, table_col,_ = st.columns([1, 5, 1])
    with table_col:
        st.markdown("**Note: The latest information from the AQDSS is for 01 January 2025**")
        st.dataframe(sectors_df)
        st.caption("Source: CEEW analysis of data from the AQDSS")

    st.write("")
    st.write("")
    df = pd.DataFrame({
        "Fire Contribution": ["28 December 2024"],
        "Value": [0]
    })
    st.markdown("<h5>The AQDSS does not provide future stubble-burning contributions to PM<sub style='font-size:15px';>2.5</sub> <br> Therefore, we provide yesterday's contribution in the table below</h5>", unsafe_allow_html=True)
    st.write("")
    _, col_T, _ = st.columns([1, 5, 1])
    with col_T:
        st.dataframe(df)

    st.write("")
    st.write("")
    st.markdown("<h5> Farm fires in neighbouring states contributed 10% to 30% to Delhi's PM<sub style='font-size:13px';>2.5</sub> between mid-Oct and mid-Nov 2024</h5>", unsafe_allow_html=True)
    _, image_col, _ = st.columns([1, 9, 1])
    with image_col:
        st.image("assets/daily_mean_fire_cont.png", width='stretch')
        st.caption("**Source: [AQDSS maintained by the Ministry of Earth Sciences](https://ews.tropmet.res.in/dss/index.php)**")