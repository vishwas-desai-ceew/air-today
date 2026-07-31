import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
from views.components import chart_card

PARENT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PARENT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def generate_plot(df, x_col, y_cols, val):
    var_dict = {
    "wind": "Wind Speed (m/s)",
    "temperature": "Temperature (°C)",
    "blh": "Boundary Layer Height (m)"
    }
    title_dict = {
        "wind": "Hourly Wind Speed (at 10m)",
        "temperature": "Hourly Temperature (at 2m)",
        "blh": "Boundary Layer Height"
    }

    y_label = var_dict.get(val, val)
    fig_title = title_dict.get(val, "Weather Data")  
    
    fig = px.line(
        df,
        x=x_col,
        y=y_cols,
        labels={"value": y_label, "time": "Time"},  
        title=f"<b>&nbsp;{fig_title}</b>"                  
    )
    thresholds = {
    "wind": 2.8,
    "temperature": 10
    }

    if val in thresholds:
        thr = thresholds[val]

        # add threshold line
        fig.add_shape(
            type="line",
            x0=df["date"].min(),
            x1=df["date"].max(),
            y0=thr,
            y1=thr,
            line=dict(color="red", width=2, dash="dash")
        )

        # add annotation
        x = "m/s" if val == "wind" else "°C"
        fig.add_annotation(
            x=df["date"].min(),
            y=thr,
            text=f"{thr} {x}",   # optional label
            showarrow=False,
            yshift=10,
            font=dict(color="red")
        )
        
    fig.update_layout(
        showlegend=False,
        margin=dict(l=20, r=20, t=60, b=20),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        xaxis_title=dict(text="<b>Time</b>", font=dict(color="black", size=17)),
        yaxis_title=dict(text=f"<b>{y_label}</b>", font=dict(color="black", size=17)),
        font=dict(family="sans-serif", size=17, color="black")
    )
    fig.update_xaxes(tickformat="%d %b, %H:%M")
    return fig


def generate_bar_plot(df, x_col, y_col, title, y_label):
    df[x_col] = pd.to_datetime(df[x_col])
    df[y_col] = pd.to_numeric(df[y_col], errors='coerce')

    fig = px.bar(
        df,
        x=x_col,
        y=y_col,
        text=df[y_col],
        title=title
    )

    fig.update_traces(texttemplate='%{text:.1f}', textposition='outside')
    fig.update_layout(
        showlegend=False,
        margin=dict(l=20, r=20, t=60, b=20),
        plot_bgcolor="#FFFFFF",
        paper_bgcolor="#FFFFFF",
        xaxis_title=dict(text="<b>Time</b>", font=dict(color="black", size=17)),
        yaxis_title=dict(text=f"<b>{y_label}</b>", font=dict(color="black", size=17)),
        font=dict(family="sans-serif", size=17, color="black"),
        yaxis=dict(range=[0.1, 1 * 1.2])
    )
    fig.update_xaxes(tickformat="%d %b, %H:%M")

    return fig


@st.cache_data(ttl=3600)
def load_weather_data():
    df = pd.read_csv(DATA_DIR / "meteo_api_hourly.csv")
    df['date'] = pd.to_datetime(df['date'])
    return df


def render_weather_fcast():
    df = load_weather_data()
    colWind, colTemp = st.columns([1, 1], gap="small")
    with colWind, chart_card():
        st.plotly_chart(generate_plot(df, "date", ["wind_speed_10m"], "wind"), width='stretch')
    with colTemp, chart_card():
        st.plotly_chart(generate_plot(df, "date", ["temperature_2m"], "temperature"), width='stretch')
    colRain, colBLH = st.columns([1, 1], gap="small")
    with colRain, chart_card():
        st.plotly_chart(generate_bar_plot(df, "date", "rain", "Rainfall", "Rain(mm)"), width='stretch')
    with colBLH, chart_card():
        st.plotly_chart(generate_plot(df, "date", ["boundary_layer_height"], "blh"), width='stretch')