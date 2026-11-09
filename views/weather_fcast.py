"""Weather Forecast page: 3-day outlook for Delhi, read for what it means for
pollution. Daily cards first, then one strip per parameter (explainer on the
left, chart on the right) on a shared time axis with night shaded.

Data: Open-Meteo hourly model forecast (data/meteo_api_hourly.csv, m/s).
Thresholds: IITM AQEWS (ventilation index, wind) and IMD (rainfall classes);
see config/reference.py.
"""
from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config.reference import RAIN_CLASSES_24H, VENTILATION_INDEX_UNFAVOURABLE, WIND_UNFAVOURABLE_KMH
from views import data
from views.charts import PLOT_CONFIG, base_layout, hex_rgba
from views.sky import solar_elevation
from views.widgets import compass, icon, side_points, side_source, src

WIND_LIMIT_MS = round(WIND_UNFAVOURABLE_KMH / 3.6, 1)  # 10 km/h = 2.8 m/s
GOOD, BAD = "#1e8e5a", "#c22a1e"


# ------------------------------------------------------------ helpers --
def _night_spans(times):
    """[(start, end)] of hours with the sun below the horizon (naive IST)."""
    spans, start = [], None
    for t in times:
        night = solar_elevation(t) < -0.833
        if night and start is None:
            start = t
        elif not night and start is not None:
            spans.append((start, t))
            start = None
    if start is not None:
        spans.append((start, times.iloc[-1]))
    return spans


def _shade_night(fig, spans):
    for a, b in spans:
        fig.add_vrect(x0=a, x1=b, fillcolor="rgba(13,36,64,0.06)", line_width=0, layer="below")
    return fig


def _rain_class(mm):
    if mm is None or mm < 0.1:
        return "No rain"
    for name, low, high in RAIN_CLASSES_24H:
        if high is None or mm <= high:
            return name
    return RAIN_CLASSES_24H[-1][0]


def _finish(fig, spans, y_title, height=230):
    _shade_night(fig, spans)
    base_layout(fig, height=height, y_title=y_title)
    fig.update_layout(margin=dict(l=56, r=16, t=28, b=36))
    fig.update_xaxes(tickformat="%H:%M<br>%a %d %b", dtick=12 * 3600 * 1000, tick0="2000-01-01 00:00")
    return fig


@st.cache_data(ttl=3600)
def load_weather_data():
    df = data.meteo_hourly()
    if df.empty:
        return df
    # Plot in naive IST: Plotly shifts tz-aware shapes (night shading) to UTC.
    df = df.sort_values("date").reset_index(drop=True)
    df["date"] = df["date"].dt.tz_localize(None)
    return df


# ------------------------------------------------------------- charts --
def temp_chart(df, spans):
    fig = go.Figure()
    t = df["temperature_2m"]
    fig.add_scatter(x=df["date"], y=t, name="Temperature (°C)", mode="lines",
                    line=dict(color="#e8590c", width=3, shape="spline"),
                    fill="tozeroy", fillcolor="rgba(232,89,12,0.08)",
                    hovertemplate="%{y:.1f} °C<extra></extra>")
    if "relative_humidity_2m" in df:
        fig.add_scatter(x=df["date"], y=df["relative_humidity_2m"], name="Humidity (%)", yaxis="y2",
                        mode="lines", line=dict(color="#2f8ff0", width=1.6, dash="dot"),
                        hovertemplate="RH %{y:.0f}%<extra></extra>")
    for idx, label, pos in ((t.idxmax(), "High", "top center"), (t.idxmin(), "Low", "bottom center")):
        fig.add_scatter(x=[df.loc[idx, "date"]], y=[t[idx]], mode="markers+text", showlegend=False,
                        marker=dict(size=9, color="#e8590c", line=dict(width=2, color="#fff")),
                        text=[f"<b>{label} {t[idx]:.0f}°</b>"], textposition=pos,
                        textfont=dict(color="#9c3d06", size=12), hoverinfo="skip")
    _finish(fig, spans, "°C")
    fig.update_yaxes(range=[t.min() - 4, t.max() + 4])
    fig.update_layout(yaxis2=dict(overlaying="y", side="right", range=[0, 100], showgrid=False,
                                  title=dict(text="RH %", font=dict(size=12)), fixedrange=True))
    return fig


def wind_chart(df, spans):
    ws = df["wind_speed_10m"]
    colours = [GOOD if v >= WIND_LIMIT_MS else BAD for v in ws]
    fig = go.Figure()
    y_max = max(WIND_LIMIT_MS * 2, ws.max() * 1.35)
    fig.add_hrect(y0=0, y1=WIND_LIMIT_MS, fillcolor=hex_rgba(BAD, 0.07), line_width=0, layer="below")
    fig.add_bar(x=df["date"], y=ws, name="Wind speed (m/s)", marker=dict(color=colours, cornerradius=3),
                customdata=[compass(d) for d in df.get("wind_direction_10m", [None] * len(df))],
                hovertemplate="%{y:.1f} m/s from %{customdata}<extra></extra>")
    if "wind_direction_10m" in df:
        every = df.iloc[::3]
        fig.add_scatter(x=every["date"], y=[y_max * 0.92] * len(every), mode="markers", name="Direction (blowing to)",
                        marker=dict(symbol="arrow", size=13, color="#0a3d7a",
                                    angle=[(d + 180) % 360 for d in every["wind_direction_10m"]]),
                        hoverinfo="skip")
    fig.add_hline(y=WIND_LIMIT_MS, line=dict(color=BAD, width=1.5, dash="dash"))
    fig.add_annotation(x=0, xref="x domain", y=WIND_LIMIT_MS, text=f"{WIND_LIMIT_MS} m/s (10 km/h)",
                       showarrow=False, xanchor="left", yshift=9, font=dict(size=11, color=BAD))
    _finish(fig, spans, "m/s")
    fig.update_yaxes(range=[0, y_max])
    return fig


def blh_chart(df, spans):
    b = df["boundary_layer_height"]
    fig = go.Figure()
    fig.add_scatter(x=df["date"], y=b, name="Mixing height (m)", mode="lines",
                    line=dict(color="#7048e8", width=2.5),
                    fill="tozeroy", fillcolor="rgba(112,72,232,0.16)",
                    hovertemplate="%{y:,.0f} m<extra></extra>")
    idx = b.idxmin()
    fig.add_annotation(x=df.loc[idx, "date"], y=b[idx], text=f"lid at {b[idx]:,.0f} m", showarrow=True,
                       arrowhead=0, ay=-28, font=dict(size=11, color="#5f3dc4"))
    _finish(fig, spans, "metres")
    fig.update_yaxes(range=[0, b.max() * 1.15])
    return fig


def rain_chart(df, spans):
    fig = go.Figure()
    fig.add_bar(x=df["date"], y=df["rain"], name="Rain (mm/h)", marker=dict(color="#1c7ed6", cornerradius=3),
                hovertemplate="%{y:.1f} mm<extra></extra>")
    if "precipitation_probability" in df:
        fig.add_scatter(x=df["date"], y=df["precipitation_probability"], name="Chance of rain (%)", yaxis="y2",
                        mode="lines", line=dict(color="#74c0fc", width=2),
                        fill="tozeroy", fillcolor="rgba(116,192,252,0.15)",
                        hovertemplate="%{y:.0f}% chance<extra></extra>")
    _finish(fig, spans, "mm per hour")
    fig.update_yaxes(range=[0, max(1, df["rain"].max() * 1.3)])
    fig.update_layout(yaxis2=dict(overlaying="y", side="right", range=[0, 100], showgrid=False,
                                  title=dict(text="chance %", font=dict(size=12)), fixedrange=True))
    return fig


# --------------------------------------------------------------- cards --
def _day_cards(df):
    bf = data.bulletin_forecast()
    vi_by_day = ({r["date"]: r["ventilation_index"] for _, r in bf.iterrows() if pd.notna(r.get("ventilation_index"))}
                 if not bf.empty and "ventilation_index" in bf.columns else {})
    cards = []
    for day, g in df.groupby(df["date"].dt.date):
        if len(g) < 12:  # skip partial days at the edges
            continue
        wind = g["wind_speed_10m"].mean()
        rain = g["rain"].sum()
        vi = vi_by_day.get(day)
        poor_wind = wind < WIND_LIMIT_MS
        poor_vi = vi is not None and vi < VENTILATION_INDEX_UNFAVOURABLE
        if vi is not None:
            verdict = ("bad", "Unfavourable for dispersion") if (poor_wind and poor_vi) else ("good", "Favourable for dispersion") if not (poor_wind or poor_vi) else ("mid", "Mixed dispersion")
        else:
            verdict = ("bad", "Weak winds") if poor_wind else ("good", "Winds aid dispersion")
        vi_html = (f"<div><span>Ventilation index</span><b class='{'bad' if poor_vi else 'good'}'>{vi:,.0f}</b><small>m²/s · IITM</small></div>"
                   if vi is not None else "")
        cards.append(f"""
            <article class="wx-day {verdict[0]}">
              <header><strong>{day:%A}</strong><span>{day:%d %b}</span></header>
              <div class="wx-day-temp">{g['temperature_2m'].max():.0f}°<small> / {g['temperature_2m'].min():.0f}°</small></div>
              <div class="wx-day-verdict">{escape(verdict[1])}</div>
              <div class="wx-day-grid">
                <div><span>Mean wind</span><b class='{'bad' if poor_wind else 'good'}'>{wind:.1f}</b><small>m/s</small></div>
                <div><span>Lowest mixing height</span><b>{g['boundary_layer_height'].min():,.0f}</b><small>m</small></div>
                <div><span>Rain (24 h)</span><b>{rain:.1f}</b><small>mm · {escape(_rain_class(rain))}</small></div>
                {vi_html}
              </div>
            </article>""")
    return "<div class='wx-days'>" + "".join("".join(l.strip() for l in c.splitlines()) for c in cards) + "</div>"


# Side-panel text: two or three short points per chart, sources linked
SHORT_LABELS = {"open_meteo": "Open-Meteo", "iitm_aqews": "IITM AQEWS bulletin", "imd_glossary": "IMD glossary"}
PARAMS = [
    dict(key="temp", icon="temp", title="Temperature & humidity", chart=temp_chart,
         points=["Cold nights strengthen the inversion that traps pollution near the ground.",
                 "High humidity helps fog and smog form."],
         stat=lambda d: f"{d['temperature_2m'].min():.0f}° to {d['temperature_2m'].max():.0f}°C",
         sources=("open_meteo",)),
    dict(key="wind", icon="wind", title="Wind", chart=wind_chart,
         points=[f"Below {WIND_LIMIT_MS} m/s (10 km/h), dispersion is poor. Red bars mark those hours.",
                 "Arrows show where the wind blows to.",
                 "North-westerlies can bring crop-fire smoke from Punjab and Haryana."],
         stat=lambda d: f"mean {d['wind_speed_10m'].mean():.1f} m/s",
         sources=("open_meteo", "iitm_aqews")),
    dict(key="blh", icon="layers", title="Mixing height", chart=blh_chart,
         points=["The depth of air that pollution mixes into.",
                 "Drops to a few hundred metres at night, trapping emissions.",
                 f"× wind speed = ventilation index; below {VENTILATION_INDEX_UNFAVOURABLE:,} m²/s is unfavourable."],
         stat=lambda d: f"{d['boundary_layer_height'].min():,.0f}–{d['boundary_layer_height'].max():,.0f} m",
         sources=("open_meteo", "iitm_aqews")),
    dict(key="rain", icon="rain", title="Rain", chart=rain_chart,
         points=["Rain washes particles out of the air.",
                 "Light rain is 2.5–7.5 mm in a day (IMD); the day cards use these classes."],
         stat=lambda d: f"{d['rain'].sum():.1f} mm in 72 h",
         sources=("open_meteo", "imd_glossary")),
]


def render_weather_fcast():
    df = load_weather_data()
    if df.empty:
        st.info("The weather forecast hasn't been downloaded yet.")
        return
    spans = _night_spans(df["date"])

    st.markdown(_day_cards(df), unsafe_allow_html=True)
    st.markdown(
        "<div class='wx-key'><span><i class='night'></i>Night (sun below horizon)</span>"
        f"<span><i style='background:{BAD}'></i>Unfavourable for dispersion</span>"
        f"<span><i style='background:{GOOD}'></i>Favourable</span></div>",
        unsafe_allow_html=True,
    )
    for p in PARAMS:
        with st.container(border=True, key=f"wx-strip-{p['key']}"):
            info, chart = st.columns([1, 3], gap="medium")
            with info:
                st.markdown(
                    f"<div class='wx-info'><div class='wx-info-head'>{icon(p['icon'], 22)}<span>{escape(p['title'])}</span></div>"
                    f"<div class='wx-info-stat'>{escape(p['stat'](df))}</div>"
                    f"{side_points([escape(t) for t in p['points']])}"
                    f"{side_source(*(src(k, SHORT_LABELS.get(k)) for k in p['sources']))}</div>",
                    unsafe_allow_html=True,
                )
            with chart:
                st.plotly_chart(p["chart"](df, spans), key=f"wx_{p['key']}", width="stretch", config=PLOT_CONFIG)
    st.caption("Forecast: Open-Meteo model for central Delhi, hourly, next 3 days. Model output, not IMD's forecast; "
               "night shading is computed from the sun's position.")
