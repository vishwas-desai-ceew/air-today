"""Time-of-day sky for the hero/top bar, and the Overview weather card.

The hero used to be a fixed daytime blue. It now follows the sun over Delhi:
day, dawn/dusk (sun within 6° of the horizon, i.e. civil twilight), and night
(navy with stars), with a greyer wash when the observed weather is haze,
smoke, mist or fog.

The weather card is an hourly/daily layout in the style of consumer weather
apps (current conditions, a scrolling 24-hour strip, a 3-day range view and
a details grid), built from the dashboard's own data and look.
"""
import math
from datetime import datetime
from html import escape

import pandas as pd
import streamlit as st

from config.settings import DELHI_LAT, DELHI_LON, IST
from views import data
from views.widgets import _fmt, compass, describe_weather, icon

HAZY = ("haze", "smoke", "mist", "fog", "dust", "sand")


# ------------------------------------------------------------------ sun --
def solar_elevation(ts):
    """Approximate solar elevation in degrees for Delhi (±0.5°; ignores the
    equation of time - enough for shading and colour)."""
    ts = pd.Timestamp(ts)
    if ts.tzinfo is None:
        ts = ts.tz_localize(IST)
    n = ts.dayofyear
    decl = math.radians(23.44) * math.sin(math.radians(360 / 365 * (284 + n)))
    utc = ts.tz_convert("UTC")
    hour_angle = math.radians(15 * (utc.hour + utc.minute / 60 + DELHI_LON / 15 - 12))
    lat = math.radians(DELHI_LAT)
    return math.degrees(math.asin(math.sin(lat) * math.sin(decl)
                                  + math.cos(lat) * math.cos(decl) * math.cos(hour_angle)))


def sky_phase(now=None):
    """'day' | 'dawn' | 'dusk' | 'night'."""
    now = now or datetime.now(IST)
    elev = solar_elevation(now)
    if elev >= 6:
        return "day"
    if elev <= -6:
        return "night"
    return "dawn" if now.hour < 12 else "dusk"


SKIES = {
    "day": ("radial-gradient(circle at 92% 8%, rgba(255,236,170,0.55), transparent 22%),"
            "linear-gradient(160deg, #0a4f9e 0%, #1f7fe0 45%, #6fb8ff 100%)", "rgba(11,79,158,0.25)"),
    "dawn": ("radial-gradient(circle at 12% 95%, rgba(255,196,120,0.7), transparent 40%),"
             "linear-gradient(170deg, #2b3f7d 0%, #7b6bb0 45%, #f2a07b 100%)", "rgba(80,60,130,0.28)"),
    "dusk": ("radial-gradient(circle at 88% 95%, rgba(255,150,90,0.65), transparent 40%),"
             "linear-gradient(170deg, #1d2b5c 0%, #5a3f86 50%, #e07a5f 100%)", "rgba(60,40,100,0.3)"),
    "night": ("radial-gradient(circle at 88% 14%, rgba(235,240,255,0.35), transparent 9%),"
              "radial-gradient(1px 1px at 20% 30%, #fff, transparent), radial-gradient(1px 1px at 35% 12%, #fff, transparent),"
              "radial-gradient(1.5px 1.5px at 62% 22%, #fff, transparent), radial-gradient(1px 1px at 75% 40%, #dfe8ff, transparent),"
              "radial-gradient(1px 1px at 48% 8%, #fff, transparent), radial-gradient(1px 1px at 8% 14%, #dfe8ff, transparent),"
              "linear-gradient(165deg, #050b1f 0%, #0c1c45 55%, #1b3270 100%)", "rgba(5,11,31,0.4)"),
}


def sky_style(phase, condition=""):
    """<style> that repaints the hero, top bar and weather card for `phase`."""
    bg, shadow = SKIES[phase]
    if any(w in (condition or "").lower() for w in HAZY):
        bg = "linear-gradient(160deg, rgba(160,150,135,0.45), rgba(120,120,120,0.25))," + bg
    return (
        "<style>"
        f".st-key-sky-hero,.sky-topbar,.wxc{{background:{bg} !important;box-shadow:0 18px 40px {shadow} !important;}}"
        + (".st-key-sky-hero .sky-hero-clouds{opacity:.25}" if phase == "night" else "")
        + "</style>"
    )


def apply_sky():
    wx = data.current_weather()
    st.html(sky_style(sky_phase(), wx.get("condition", "") if wx else ""))


# -------------------------------------------------------------- icons --
def wx_icon_name(code=None, is_day=1, rain=0.0, prob=None, condition=""):
    c = (condition or "").lower()
    if any(w in c for w in ("thunder",)) or code in (95, 96, 99):
        return "storm"
    if any(w in c for w in ("rain", "drizzle", "shower")) or (code is not None and 51 <= code <= 82) or (rain or 0) >= 0.1:
        return "rain"
    if any(w in c for w in HAZY) or code in (45, 48):
        return "fog"
    if code == 3 or "overcast" in c or "mostly cloudy" in c:
        return "cloud"
    if code in (1, 2) or "partly" in c or "mostly clear" in c:
        return "cloud-sun" if is_day else "cloud-moon"
    return "sun" if is_day else "moon"


# ------------------------------------------------------- weather card --
def _hourly_next(df, now, hours=24):
    nxt = df[df["date"] >= now.replace(minute=0, second=0, microsecond=0)].head(hours)
    return nxt


def _row_icon(r):
    code = r.get("weather_code")
    code = None if pd.isna(code) else int(code)
    is_day = r.get("is_day")
    is_day = (solar_elevation(r["date"]) > -0.833) if is_day is None or pd.isna(is_day) else bool(is_day)
    return wx_icon_name(code, is_day, r.get("rain", 0), r.get("precipitation_probability"))


def render_weather_card():
    wx = data.current_weather()
    df = data.meteo_hourly()
    if not wx and df.empty:
        return
    now = datetime.now(IST)
    phase = sky_phase(now)
    cond = wx.get("condition") or describe_weather(wx.get("weather_code"), wx.get("is_day", 1))
    main_icon = wx_icon_name(wx.get("weather_code"), wx.get("is_day", phase == "day"), wx.get("precipitation"),
                             condition=cond)
    obs = (wx.get("observed_at") or wx.get("time") or "")[11:16]
    where = (wx.get("station") or "Delhi").split(" (")[0]

    hours_html = ""
    if not df.empty:
        for _, r in _hourly_next(df, now).iterrows():
            prob = r.get("precipitation_probability")
            hours_html += (
                f"<div class='wxc-hour'><span>{r['date'].strftime('%H:%M')}</span>"
                f"{icon(_row_icon(r), 26)}<b>{r['temperature_2m']:.0f}°</b>"
                f"<small>{icon('drop', 11)}{_fmt(prob)}%</small></div>"
            )

    days_html = ""
    if not df.empty:
        g = df.groupby(df["date"].dt.date)
        lo_all, hi_all = df["temperature_2m"].min(), df["temperature_2m"].max()
        span = max(hi_all - lo_all, 1)
        for day, d in g:
            lo, hi = d["temperature_2m"].min(), d["temperature_2m"].max()
            day_rows = d[d["date"].dt.hour.between(9, 17)]
            rep = day_rows.iloc[len(day_rows) // 2] if len(day_rows) else d.iloc[len(d) // 2]
            name = "Today" if day == now.date() else day.strftime("%a")
            days_html += (
                f"<div class='wxc-day'><span>{name}</span>{icon(_row_icon(rep), 22)}"
                f"<small>{icon('drop', 11)}{_fmt(d['precipitation_probability'].max())}%</small>"
                f"<em>{lo:.0f}°</em><div class='wxc-range'><i style='left:{(lo - lo_all) / span * 100:.0f}%;"
                f"right:{(hi_all - hi) / span * 100:.0f}%'></i></div><b>{hi:.0f}°</b></div>"
            )

    wind = wx.get("wind_speed_10m")
    vis = wx.get("visibility")
    details = [
        ("wind", "Wind", "Calm" if wind is not None and wind < 0.3
         else f"{compass(wx.get('wind_direction_10m'))} {_fmt(wind, '{:.1f}')} m/s"),
        ("humidity", "Humidity", f"{_fmt(wx.get('relative_humidity_2m'))}%"),
        ("eye", "Visibility", f"{_fmt(None if vis is None else vis / 1000, '{:.1f}')} km"),
        ("gauge", "Pressure", f"{_fmt(wx.get('surface_pressure'))} hPa"),
        ("sunrise", "Sunrise", (wx.get("sunrise") or "")[11:16] or "—"),
        ("sunset", "Sunset", (wx.get("sunset") or "")[11:16] or "—"),
    ]
    details_html = "".join(f"<div>{icon(k, 18)}<span>{lbl}</span><b>{escape(v)}</b></div>" for k, lbl, v in details)

    st.html(sky_style(phase, cond))
    st.markdown("".join(line.strip() for line in f"""
        <section class="wxc {phase}">
          <div class="wxc-now">
            <div class="wxc-where">{escape(where)} · {obs} IST</div>
            <div class="wxc-main">
              <div class="wxc-temp">{_fmt(wx.get('temperature_2m'))}°</div>
              <div class="wxc-icon">{icon(main_icon, 64)}</div>
            </div>
            <div class="wxc-cond">{escape(cond)}</div>
            <div class="wxc-feel">Feels like {_fmt(wx.get('apparent_temperature'))}° · H {_fmt(wx.get('temperature_2m_max'))}° L {_fmt(wx.get('temperature_2m_min'))}°</div>
            <div class="wxc-details">{details_html}</div>
          </div>
          <div class="wxc-side">
            <div class="wxc-label">Next 24 hours</div>
            <div class="wxc-hours">{hours_html}</div>
            <div class="wxc-label">3-day outlook</div>
            <div class="wxc-days">{days_html}</div>
          </div>
        </section>""".splitlines()), unsafe_allow_html=True)
    st.markdown(
        f"<div class='sky-kpi-source'>Now: {escape(wx.get('source', 'Open-Meteo'))} · "
        "Hourly and 3-day: Open-Meteo model forecast</div>", unsafe_allow_html=True)
