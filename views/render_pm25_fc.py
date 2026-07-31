import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import plotly.graph_objects as go

PARENT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PARENT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def generate_pm_plot(df, x_col, y_cols, val):
    title_dict = {
        "PM2.5": "10 day forecast",
    }
    y_label = val
    fig_title = title_dict.get(val, "Weather Data")
    fig = go.Figure()

    for col in y_cols:

        fig.add_trace(
            go.Scatter(
                x=df[x_col],
                y=df[col],
                mode="lines",
                line=dict(width=0),
                fill="tozeroy",
                fillcolor="rgba(0, 123, 255, 0.15)",  # soft translucent blue
                showlegend=False,
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df[x_col],
                y=df[col],
                mode="lines+markers",
                line=dict(width=2.5, color="rgba(0, 123, 255, 1)"),
                marker=dict(
                    size=6, symbol="circle", line=dict(width=0.5, color="black")
                ),
                name=col,
                hovertemplate=(
                    "<b>%{x|%b %d, %H:%M}</b><br>"  # formatted timestamp
                    f"PM2.5: <b>%{{y:.1f}}&nbsp;µg/m³</b><extra></extra>"  # no trace name in extra box
                ),
            )
        )
    fig.update_layout(
        showlegend=False,
        margin=dict(l=26, r=20, t=60, b=40),
        plot_bgcolor="#F8F8F8",
        paper_bgcolor="#F8F8F8",
        xaxis_title=dict(text="<b>Date</b>", font=dict(color="black", size=17)),
        yaxis_title=dict(text=f"<b>{y_label}</b>", font=dict(color="black", size=17)),
        font=dict(family="sans-serif", size=17, color="black"),
    )

    fig.update_xaxes(type="date", tickformat="%b %d", gridcolor="rgba(0,0,0,0.1)")
    fig.update_yaxes(gridcolor="rgba(0,0,0,0.1)")

    return fig


def get_pm25_error_html():
    html_message = f"""
    <div class="aqi-pm25-error"">
       <div class="aqi-forecast-error-title">PM₂.₅ AQEWS forecast temporarily unavailable</div>
        <ul class="custom-list1">
            <li>The AQEWS portal is currently experiencing outage or data inconsistency</li>
            <li>10 day PM₂.₅ forecast cannot be displayed at this time</li>
        </ul>
    </div>
    """
    return html_message


def load_pm25_forecast():
    df = pd.read_csv(DATA_DIR / "AQEWS_PM25_forecast.csv")
    df["time"] = pd.to_datetime(df["time"])
    return df


def render_pm25_fc():

    st.markdown("##### PM$_{2.5}$ - Next 10-days forecast (10km resolution)")
    
    try:
        df_pm25 = load_pm25_forecast()
    except Exception as e:
        st.markdown(get_pm25_error_html(), unsafe_allow_html=True)
        return

    if "PM2.5" not in df_pm25.columns or df_pm25["PM2.5"].fillna(0).sum() == 0:
        error_message = get_pm25_error_html()
        st.markdown(error_message, unsafe_allow_html=True)
        return

    
    st.plotly_chart(
        generate_pm_plot(df_pm25, "time", ["PM2.5"], "PM2.5 (µg/m³)"),
        key="pm25_chart",
        width='stretch',
    )
