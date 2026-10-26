"""Sky theme building blocks: the page hero, weather-style KPI cards and the
sidebar data-health list. Pure presentation - all numbers come from views/data.py."""
from datetime import timedelta
from html import escape

import streamlit as st

from config.settings import effective_today
from views import data

# 24x24 stroke icons (Lucide-style geometry, drawn inline so no icon font is needed)
ICONS = {
    "aqi": '<path d="M3 12h4l3-8 4 16 3-8h4"/>',
    "forecast": '<path d="M3 17l6-6 4 4 8-8"/><path d="M14 7h7v7"/>',
    "temp": '<path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z"/>',
    "humidity": '<path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/>',
    "wind": '<path d="M9.59 4.59A2 2 0 1 1 11 8H2"/><path d="M12.59 19.41A2 2 0 1 0 14 16H2"/><path d="M17.73 7.73A2.5 2.5 0 1 1 19.5 12H2"/>',
    "layers": '<path d="M12 2 2 7l10 5 10-5-10-5z"/><path d="m2 17 10 5 10-5"/><path d="m2 12 10 5 10-5"/>',
    "vent": '<path d="M12 12c-2-2.67-2-5.33 0-8 4 0 4 4 0 8z"/><path d="M12 12c2.67-2 5.33-2 8 0 0 4-4 4-8 0z"/><path d="M12 12c2 2.67 2 5.33 0 8-4 0-4-4 0-8z"/><path d="M12 12c-2.67 2-5.33 2-8 0 0-4 4-4 8 0z"/>',
    "eye": '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/>',
    "rain": '<path d="M20 16.58A5 5 0 0 0 18 7h-1.26A8 8 0 1 0 4 15.25"/><path d="M8 19v2M8 13v2M16 19v2M16 13v2M12 21v2M12 15v2"/>',
    "fire": '<path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.07-2.14 0-5.5 3-7 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.15.43-2.29 1-3a2.5 2.5 0 0 0 2.5 2.5z"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>',
    "moon": '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9z"/>',
    "cloud": '<path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9z"/>',
}

AQI_COLOURS = {
    "Good": "#2d662a", "Satisfactory": "#03a303", "Moderate": "#e0b400",
    "Poor": "#f78c00", "Very Poor": "#fc4d02", "Severe": "#e91902",
}

# WMO weather interpretation codes used by Open-Meteo, grouped
WEATHER_CODES = [
    ({0}, "Clear sky"), ({1, 2}, "Partly cloudy"), ({3}, "Overcast"), ({45, 48}, "Fog"),
    ({51, 53, 55, 56, 57}, "Drizzle"), ({61, 63, 65, 66, 67, 80, 81, 82}, "Rain"),
    ({71, 73, 75, 77, 85, 86}, "Snow"), ({95, 96, 99}, "Thunderstorm"),
]
COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def _html(markup):
    """Strip per-line indentation: Markdown treats indented lines after a blank
    line as a code block, which printed the hero's HTML as text."""
    return "".join(line.strip() for line in markup.splitlines())


def icon(name, size=20):
    return (
        f'<svg class="sky-icon" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" '
        f'aria-hidden="true">{ICONS[name]}</svg>'
    )


def describe_weather(code, is_day=1):
    for codes, label in WEATHER_CODES:
        if code in codes:
            if label == "Clear sky" and not is_day:
                return "Clear night"
            return label
    return "—"


def compass(degrees):
    if degrees is None:
        return ""
    return COMPASS[int((degrees % 360) / 45 + 0.5) % 8]


def _fmt(value, pattern="{:.0f}", fallback="—"):
    if value is None:
        return fallback
    try:
        return pattern.format(value)
    except (TypeError, ValueError):
        return fallback


# ------------------------------------------------------------------- hero --
def render_hero():
    today = effective_today()
    aqi_row, prev_row = data.aqi_today_and_yesterday()
    wx = data.current_weather()

    if aqi_row:
        category = aqi_row["category"]
        colour = AQI_COLOURS.get(category, "#5a6b85")
        delta = ""
        if prev_row:
            diff = int(aqi_row["aqi"]) - int(prev_row["aqi"])
            if diff == 0:
                text = "• Same as yesterday"
            else:
                text = f'{"▲" if diff > 0 else "▼"} {abs(diff)} {"worse" if diff > 0 else "better"} than yesterday'
            delta = f'<span class="hero-delta {"bad" if diff > 0 else "good"}">{text}</span>'
        aqi_html = f"""
            <div class="hero-aqi" style="--aqi:{colour}">
                <div class="hero-aqi-value">{int(aqi_row["aqi"])}</div>
                <div>
                    <div class="hero-aqi-cat">{escape(category)}</div>
                    <div class="hero-aqi-meta">AQI · CPCB 24-h average · {escape(str(aqi_row.get("pollutant") or ""))}</div>
                    {delta}
                </div>
            </div>"""
    else:
        aqi_html = """
            <div class="hero-aqi hero-aqi--pending">
                <div class="hero-aqi-value">—</div>
                <div><div class="hero-aqi-cat">Awaiting bulletin</div>
                <div class="hero-aqi-meta">CPCB publishes around 4 PM IST</div></div>
            </div>"""

    if wx:
        sky = "sun" if wx.get("is_day", 1) else "moon"
        if wx.get("weather_code") not in (0, 1, None):
            sky = "cloud"
        wx_html = f"""
            <div class="hero-wx">
                <div class="hero-wx-icon">{icon(sky, 44)}</div>
                <div>
                    <div class="hero-wx-temp">{_fmt(wx.get("temperature_2m"))}°<small>C</small></div>
                    <div class="hero-wx-desc">{describe_weather(wx.get("weather_code"), wx.get("is_day", 1))}</div>
                    <div class="hero-wx-range">H {_fmt(wx.get("temperature_2m_max"))}° · L {_fmt(wx.get("temperature_2m_min"))}°</div>
                </div>
            </div>"""
    else:
        wx_html = ""

    st.markdown(_html(
        f"""
        <section class="sky-hero" aria-label="Today in Delhi">
            <div class="sky-hero-clouds" aria-hidden="true"></div>
            <div class="sky-hero-top">
                <div class="hero-eyebrow"><span></span>New Delhi · {today.strftime("%A, %d %B %Y")}</div>
            </div>
            <div class="sky-hero-body">
                <div>
                    <h1 class="hero-title">Air Today</h1>
                    {aqi_html}
                </div>
                {wx_html}
            </div>
        </section>
        """),
        unsafe_allow_html=True,
    )


# -------------------------------------------------------------- KPI cards --
def kpi_card(icon_name, label, value, unit="", note="", tone=None, accent=None, extra=""):
    """A weather-widget style card. tone: "good" | "bad" | None colours the note chip."""
    note_html = f'<span class="sky-kpi-note {tone or ""}">{note}</span>' if note else ""
    style = f' style="--accent:{accent}"' if accent else ""
    return f"""
        <article class="sky-kpi"{style}>
            <div class="sky-kpi-head">{icon(icon_name)}<span>{label}</span></div>
            <div class="sky-kpi-value">{value}<small>{unit}</small>{extra}</div>
            {note_html}
        </article>"""


def render_kpi_grid():
    today = effective_today()
    tomorrow = today + timedelta(days=1)
    aqi_row, prev_row = data.aqi_today_and_yesterday()
    fc = data.forecast_for(tomorrow)
    wx = data.current_weather()
    fires = data.fire_counts(today - timedelta(days=1))

    cards = []
    if aqi_row:
        diff = int(aqi_row["aqi"]) - int(prev_row["aqi"]) if prev_row else None
        note = "" if diff is None else f'{"▲" if diff > 0 else "▼" if diff < 0 else "•"} {abs(diff)} vs yesterday'
        tone = None if not diff else ("bad" if diff > 0 else "good")
        cards.append(kpi_card("aqi", "AQI today", int(aqi_row["aqi"]), "", note, tone,
                              AQI_COLOURS.get(aqi_row["category"])))
    else:
        cards.append(kpi_card("aqi", "AQI today", "—", "", "Bulletin pending"))

    if fc["aqi"] is not None or fc["category"]:
        cards.append(kpi_card("forecast", "Tomorrow (AQEWS)", fc["aqi"] if fc["aqi"] is not None else "—", "",
                              escape(str(fc["category"] or "")), None, AQI_COLOURS.get(str(fc["category"]))))
    else:
        cards.append(kpi_card("forecast", "Tomorrow (AQEWS)", "—", "", "Forecast unavailable", "bad"))

    wind = wx.get("wind_speed_10m")
    wind_dir = wx.get("wind_direction_10m")
    arrow = (f'<span class="sky-wind-arrow" style="transform:rotate({(wind_dir + 180) % 360}deg)">↑</span>'
             if wind_dir is not None else "")
    cards.append(kpi_card(
        "wind", f"Wind {compass(wind_dir)}".strip(), _fmt(wind, "{:.1f}"), " m/s",
        "" if wind is None else ("Favourable for dispersion" if wind >= 2.8 else "Weak dispersion"),
        None if wind is None else ("good" if wind >= 2.8 else "bad"), extra=arrow,
    ))

    vi = fc["ventilation_index"]
    cards.append(kpi_card(
        "vent", "Ventilation index (tmrw)", _fmt(vi, "{:,.0f}"), " m²/s",
        "" if vi is None else ("Favourable (> 6,000)" if vi > 6000 else "Unfavourable (≤ 6,000)"),
        None if vi is None else ("good" if vi > 6000 else "bad"),
    ))

    blh = wx.get("boundary_layer_height")
    cards.append(kpi_card("layers", "Mixing height now", _fmt(blh), " m",
                          "" if blh is None else ("Shallow – pollutants trapped" if blh < 500 else "Deep mixing"),
                          None if blh is None else ("bad" if blh < 500 else "good")))

    cards.append(kpi_card("temp", "Temperature", _fmt(wx.get("temperature_2m"), "{:.1f}"), " °C",
                          f'Feels {_fmt(wx.get("apparent_temperature"))}° · min {_fmt(wx.get("temperature_2m_min"))}°'))
    cards.append(kpi_card("humidity", "Humidity", _fmt(wx.get("relative_humidity_2m")), " %",
                          f'Cloud {_fmt(wx.get("cloud_cover"))}%'))
    vis = wx.get("visibility")
    cards.append(kpi_card("eye", "Visibility", _fmt(None if vis is None else vis / 1000, "{:.1f}"), " km",
                          "" if vis is None else ("Haze / smog likely" if vis < 2000 else "Clear"),
                          None if vis is None else ("bad" if vis < 2000 else None)))
    cards.append(kpi_card("rain", "Rain (last hour)", _fmt(wx.get("precipitation"), "{:.1f}"), " mm",
                          "Rain helps wash out PM" if (wx.get("precipitation") or 0) > 0 else "Dry"))
    if fires is None:
        cards.append(kpi_card("fire", "Fires PB + HR (yday)", "—", "", "Fire feed not updated"))
    else:
        cards.append(kpi_card("fire", "Fires PB + HR (yday)", sum(fires.values()), "",
                              f'Punjab {fires.get("Punjab", 0)} · Haryana {fires.get("Haryana", 0)}'))

    st.markdown(_html(f'<div class="sky-kpi-grid">{"".join(cards)}</div>'), unsafe_allow_html=True)
    if wx:
        st.markdown(
            f'<div class="sky-kpi-source">AQI: CPCB daily bulletin · Forecast and ventilation index: IITM AQEWS · '
            f'Weather: {escape(wx.get("source", "Open-Meteo"))} (model data for central Delhi, observed {escape(str(wx.get("time", ""))[11:16])} IST)</div>',
            unsafe_allow_html=True,
        )


# ------------------------------------------------------------ sidebar --
def render_sidebar_health():
    rows = data.source_health()
    items = "".join(
        f"""<li class="health-row {r['state']}" title="{escape(r['note'])}">
                <span class="health-dot" aria-hidden="true"></span>
                <span class="health-label">{r['label']}</span>
                <span class="health-when">{r['when'].strftime('%d %b, %H:%M') if r['when'] else '—'}</span>
            </li>"""
        for r in rows
    )
    issues = sum(r["state"] != "ok" for r in rows)
    summary = "All sources up to date" if not issues else f"{issues} source{'s need' if issues > 1 else ' needs'} attention"
    st.sidebar.markdown(_html(
        f"""
        <details class="sidebar-health" {'open' if issues else ''}>
            <summary><span class="health-dot {'ok' if not issues else 'stale'}"></span>{summary}</summary>
            <ul>{items}</ul>
        </details>
        """),
        unsafe_allow_html=True,
    )
