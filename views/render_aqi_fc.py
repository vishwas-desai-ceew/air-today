import streamlit as st  
import pandas as pd
import plotly.express as px
from pathlib import Path
import plotly.graph_objects as go
from datetime import datetime, time, timedelta

PARENT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PARENT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def generate_pm_plot(df, x_col, y_cols, val, height=390):
    y_label = val
    fig = go.Figure()

    for col in y_cols:
       
        fig.add_trace(
            go.Scatter(
                x=df[x_col],
                y=df[col],
                mode="lines",
                line=dict(width=0),
                fill="tozeroy",
                fillcolor="rgba(27, 79, 214, 0.14)",
                showlegend=False,
                hoverinfo="skip"
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df[x_col],
                y=df[col],
                mode="lines+markers+text",
                line=dict(width=3, color="#1B4FD6"),
                marker=dict(size=8, symbol="circle", line=dict(width=2, color="#FFFFFF")),
                text=[f"{v:.0f}" for v in df[col]],
                textposition="top center",
                textfont=dict(size=12, color="#243B64"),
                name=col,
                hovertemplate=(
                    "<b>%{x|%b %d}</b><br>"  # formatted timestamp
                    f"{y_label}: <b>%{{y:.0f}}</b><extra></extra>"  # no trace name in extra box
                ),
            )
        )
    fig.update_layout(
        showlegend=False,
        height=height,
        hoverlabel=dict(bgcolor="#152C57", bordercolor="#152C57", font=dict(color="#FFFFFF", size=13)),
        margin=dict(l=45, r=24, t=36, b=42),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        xaxis_title=None,
        yaxis_title=dict(text="AQI", font=dict(color="#52627A", size=13)),
        font=dict(family="Arial, sans-serif", size=13, color="#52627A"),
    )

    fig.update_xaxes(
        tickformat="%d %b",
        gridcolor="rgba(0,0,0,0)",
        linecolor="#DCE4F0",
        tickfont=dict(color="#6A7992"),
        fixedrange=True,
    )
    fig.update_yaxes(
        gridcolor="#E7ECF3",
        gridwidth=1,
        linecolor="#DCE4F0",
        tickfont=dict(color="#6A7992"),
        zeroline=False,
        fixedrange=True,
    )

    return fig


def is_data_flat(df, col, window=6):
    if col not in df.columns or len(df[col].dropna()) < window:
        return False

    recent = df[col].dropna().tail(window)
    if all(recent <= 0):
        return True

    if recent.nunique() == 1:
        return True

    return False


def is_data_old(df):
    df["date"] = pd.to_datetime(df["date"], errors='coerce')
    last_date = df["date"].max().date()
    return last_date < datetime.today().date()

    
def get_aqi_error_msg():
    return """
    <div class="aqi-forecast-error">
        <div class="aqi-forecast-error-title">AQI forecast temporarily unavailable</div>
        <ul class="custom-list1">
            <li>The AQEWS portal is currently experiencing outage or data inconsistency</li>
            <li>10 day AQI forecast data appears unresponsive or stale</li>
            <li>Forecasts and insights cannot be displayed at this time</li>
        </ul>
    </div>
    """


def get_error_message():
    df_aqi = pd.read_csv(DATA_DIR / "AQEWS_AQI_forecast.csv")
    df_aqi['date'] = pd.to_datetime(df_aqi['date'])
    error_flag = False
    if is_data_flat(df_aqi, "AQI_overall") or is_data_old(df_aqi):
        error_flag = True
    return error_flag, df_aqi


def render_aqi_fc(isMobile=False, compact=False):
    st.markdown("##### AQI - Next 10-days forecast")
    height = 390 if not compact else 290
    flag, df_aqi = get_error_message()
    if flag:
        st.markdown(get_aqi_error_msg(), unsafe_allow_html=True)
        st.write("")
        return

    start_date = df_aqi["date"].min()
    end_date = df_aqi["date"].max()
    range_str = f"{start_date.strftime('%d %b')} – {end_date.strftime('%d %b %Y')}"
    latest_aqi = df_aqi["AQI_overall"].dropna().iloc[-1]

    with st.container(border=False, key="aqi-forecast-card"):
        
        st.markdown(
            f"""
            <div class="aqi-forecast-header">
                <div>
                    <p class="aqi-forecast-eyebrow">AQEWS forecast</p>
                    <h3>Air Quality Index outlook</h3>
                    <p class="aqi-forecast-range">{range_str}</p>
                </div>
                <div class="aqi-forecast-latest">
                    <span>Latest forecast</span>
                    <strong>{latest_aqi:.0f}</strong>
                    <small>AQI</small>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.plotly_chart(
            generate_pm_plot(df_aqi, "date", ["AQI_overall"], "AQI", height=height),
            key="aqi_forecast_chart",
            width='stretch',
            config={"displayModeBar": False},
        )

   
