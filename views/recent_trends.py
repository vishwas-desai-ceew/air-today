import streamlit as st


RECENT_TRENDS = [
    (
        "Persistent poor and very poor PM₂.₅ conditions",
        "Since 13 October 2024, Delhi's 24-hour average PM₂.₅ concentration has been in the poor (>90 µg/m³) or very poor (>121 µg/m³) category every day.",
    ),
    (
        "Severe nighttime PM₂.₅ episodes",
        "Between the last week of October and the last week of November, hourly PM₂.₅ concentrations slipped into the severe category (>250 µg/m³) for a few nighttime hours.",
    ),
    (
        "Peak pollution episode in November",
        "PM₂.₅ concentrations breached 500 µg/m³ from 17 to 19 November.",
    ),
    (
        "Daytime improvement, nighttime deterioration",
        "High daytime wind speeds have brought Delhi's average PM₂.₅ below the poor threshold (90 µg/m³) around 3 PM since the first week of December. Concentrations still cross the very poor threshold (120 µg/m³) at night.",
    ),
    (
        "GRAP eased from Stage IV to Stage II",
        "On 5 December, the Supreme Court allowed CAQM to ease restrictions from GRAP Stage IV, which had been in force since 18 November, to Stage II.",
    ),
    (
        "GRAP changes in December",
        "CAQM invoked GRAP III on 16 December as AQI breached 350, then escalated to GRAP IV at 10 PM as AQI crossed 400. GRAP IV was revoked and GRAP III reimposed on 24 December; GRAP III was revoked on 27 December as air quality improved.",
    ),
    (
        "GRAP III invoked in early January",
        "With AQI above 350 and forecasts indicating adverse conditions, CAQM invoked GRAP III on 3 January. It was later revoked on 5 January.",
    ),
    (
        "GRAP III action in mid-January",
        "An increase in observed AQI on 9 January led to the invocation of GRAP III, which was revoked on 12 January.",
    ),
    (
        "Further GRAP III and IV restrictions",
        "CAQM imposed GRAP III and IV on 15 January. GRAP IV and III restrictions were revoked on 16 and 17 January respectively. GRAP III was imposed again on 29 January and revoked on 3 February.",
    ),
    (
        "GRAP I and II revoked",
        "CAQM revoked GRAP II on 24 February and GRAP I on 3 March following an improvement in AQI.",
    ),
]


def render_recent_trends():
    st.caption("Key air-quality observations and GRAP actions. Select a card to view the full update.")
    for number, (title, detail) in enumerate(RECENT_TRENDS, start=1):
        st.markdown(
            f"""
            <details class="recent-trend">
                <summary><span>{number:02d}</span>{title}</summary>
                <p>{detail}</p>
            </details>
            """,
            unsafe_allow_html=True,
        )
