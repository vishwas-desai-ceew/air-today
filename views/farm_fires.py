import streamlit as st
import pandas as pd


def load_farm_fire_data():
    return pd.read_csv("data/farm_fires.csv")

farm_fires_df = load_farm_fire_data()

def  render_farm_fires():

    st.markdown("""
        <div style='font-size: 18px;' align='justify'>
        <strong>Observing the variation of satellite-derived farm fires between 2016 and 2024</strong><br>
        <ul style="padding-left:5px;padding-right: 10px; list-style-type: square; margin-top: 5px;">
            <li>There has been a decline in farm fires in the NCR states since 2021</li>
            <li>This is attributable to a slew of measures taken by both the Union and the State governments</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
    _, col_F, _ = st.columns([0.1, 3, 0.1])
    with col_F:
        st.dataframe(farm_fires_df, hide_index=True)
        st.caption("**_Source: Data from NASA VIIRS 375m active fires dataset_**")
    st.error("**Note**: _Real-time data was not available from **04/11 - 08/11 2024** due to data outages._")
    st.markdown("""
                <div style='font-size: 18px;' align='justify'>
                <strong>
                While satellite-derived fires can offer nearly a decade's record of global fire activity, there are
                certain limitations that need to be approached with caution.
                </strong>
                <br>
                <ul style="padding-left:20px;padding-right: 40px; list-style-type: square; margin-top: 15px;">
                    <li>
                        <strong>Coarser resolution:</strong> The VIIRS instrument captures a 'snapshot' of fire events when
                        they overpass at 375m*375m resolution, which is nearly four times the average land
                        holding size (3.62 Ha = 36,200 m2) in Punjab. The location of the active fire in the
                        snapshot denotes the centre of the pixel flagged as containing one or more fires.
                        This results in uncertainty around the location of fires and leads to the possibility of
                        counting several small fires as one.
                    </li><br>
                    <li> 
                        <strong>Limited overpass:</strong> The VIIRS instruments are aboard polar-orbiting satellites that
                        provide data only twice daily (1:30 am & pm IST). This leaves out the possibility of
                        capturing short-lived fires that started and ended outside the satellite overpass
                        window. This is critical since field interviews suggest that most farmers burn in the
                        evening hour after 6 pm to take advantage of this. Additionally, burning in the case
                        of partial burning + in situ CRM combination lasts only for a few hours, making it
                        difficult for satellites to detect. As per a CEEW study, of the 58 per cent of in-situ
                        CRM practising farmers in Punjab, more than half of them followed partial burning in Kharif 2022
                    </li><br>
                    <li>
                        <strong>Missing data due to cloud obscuration:</strong> The VIIRS instrument is an optical sensor
                        which has inherent limitations in observing the earth's surface on cloudy days. Cloud
                        masks the radiance reflected by features of the earth's surface, and thus limits the
                        accurate detection of fires by optical sensors.
                    </li><br>
                </ul>
                </div>
                """, unsafe_allow_html=True)
    