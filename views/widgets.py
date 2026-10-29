"""Sky theme building blocks: the page hero and top bar (with data health and
the signed-in user), weather-style KPI cards and the Key insights dialog. Pure presentation - all numbers come from views/data.py."""
from datetime import datetime, timedelta
from html import escape

import streamlit as st

from config.settings import IST, effective_today
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


# ------------------------------------------------------------- top bar --
def _health_pill():
    """Data-health dropdown for the header (was a sidebar panel)."""
    rows = data.source_health()
    issues = sum(r["state"] != "ok" for r in rows)
    summary = "All sources up to date" if not issues else f"{issues} source{'s need' if issues > 1 else ' needs'} attention"
    items = "".join(
        f'<li class="health-row {r["state"]}" title="{escape(r["note"])}">'
        f'<span class="health-dot"></span><span class="health-label">{r["label"]}</span>'
        f'<span class="health-when">{r["when"].strftime("%d %b, %H:%M") if r["when"] else "—"}</span></li>'
        for r in rows
    )
    return (
        f'<details class="hero-health"><summary><span class="health-dot {"ok" if not issues else "stale"}"></span>'
        f'{summary}<span class="hero-caret">▾</span></summary><ul>{items}</ul></details>'
    )


def _user_chip():
    """Signed-in user + log out. The log-out link hits Streamlit's /auth/logout
    route directly (what st.logout() does), so it can live inside HTML."""
    # st.user has no is_logged_in at all when [auth] isn't configured
    if not st.user.get("is_logged_in", False):
        return ""
    name = st.user.get("name") or st.user.get("email") or ""
    picture = st.user.get("picture")
    initials = "".join(part[0] for part in name.split()[:2]).upper() or "?"
    avatar = (f'<img class="hero-avatar" src="{escape(picture)}" alt="" referrerpolicy="no-referrer">'
              if picture else f'<span class="hero-avatar">{escape(initials)}</span>')
    return (
        f'<div class="hero-user">{avatar}<span class="hero-user-name">{escape(name)}</span>'
        f'<a class="hero-logout" href="/auth/logout" target="_self">Log out</a></div>'
    )


def _top_row():
    now = datetime.now(IST)
    return (
        f'<div class="sky-hero-top"><div class="hero-eyebrow"><span></span>New Delhi · {now.strftime("%A, %d %B %Y")}</div>'
        f'<div class="hero-actions">{_health_pill()}{_user_chip()}</div></div>'
    )


def render_topbar():
    """Slim sky strip for every page except Overview (which has the full hero)."""
    st.markdown(_html(f'<section class="sky-topbar">{_top_row()}</section>'), unsafe_allow_html=True)


# ------------------------------------------------------------------- hero --
def _hero_aqi_html():
    aqi_row, prev_row = data.aqi_today_and_yesterday()
    if not aqi_row:
        return _html("""
            <div class="hero-box hero-aqi hero-aqi--pending">
                <div class="hero-aqi-value">—</div>
                <div><div class="hero-box-eyebrow">AQI · CPCB</div><div class="hero-aqi-cat">Awaiting bulletin</div>
                <div class="hero-aqi-meta">Published around 4 PM IST</div></div>
            </div>""")
    category = aqi_row["category"]
    delta = ""
    if prev_row:
        diff = int(aqi_row["aqi"]) - int(prev_row["aqi"])
        text = (f"• Same as {_d(prev_row['date'])}" if diff == 0
                else f'{"▲" if diff > 0 else "▼"} {abs(diff)} vs {_d(prev_row["date"])}')
        delta = f'<span class="hero-delta {"bad" if diff > 0 else "good" if diff < 0 else ""}">{text}</span>'
    return _html(f"""
        <div class="hero-box hero-aqi" style="--aqi:{AQI_COLOURS.get(category, '#5a6b85')}">
            <div class="hero-aqi-value">{int(aqi_row["aqi"])}</div>
            <div>
                <div class="hero-box-eyebrow">AQI · {_d(aqi_row["date"])}</div>
                <div class="hero-aqi-cat">{escape(category)}</div>
                <div class="hero-aqi-meta">CPCB 24-h avg · {escape(str(aqi_row.get("pollutant") or ""))}</div>
                {delta}
            </div>
        </div>""")


def _hero_insights():
    """Key insights summary box with the button that opens the dialog."""
    facts = data.insights_today()
    with st.container(key="hero-insights"):
        if facts:
            items = insight_items(facts)
            alerts = [i for i in items if i["tone"] == "bad"]
            traps = [{"wind": "wind", "vent": "ventilation"}[i["icon"]] for i in alerts if i["icon"] in ("wind", "vent")]
            title = f'{len(alerts)} alert{"s" if len(alerts) != 1 else ""}' if alerts else "No alerts"
            line = (f'{" and ".join(traps).capitalize()} unfavourable' if traps
                    else f'{len(items)} indicators checked')
            st.markdown(_html(
                f'<div class="hero-box-eyebrow">Key insights · {_d(datetime.fromisoformat(facts["date"]))}</div>'
                f'<div class="hero-ins-title">{title}</div><div class="hero-aqi-meta">{escape(line)}</div>'
            ), unsafe_allow_html=True)
        else:
            st.markdown(_html('<div class="hero-box-eyebrow">Key insights</div>'
                              '<div class="hero-ins-title">Not generated yet</div>'), unsafe_allow_html=True)
        if st.button("View", key="open_insights", icon=":material/lightbulb:", disabled=not facts):
            insights_dialog()


@st.fragment(run_every="5m")
def _hero_weather():
    """Its own fragment: re-runs every 5 minutes without reloading the page."""
    wx = data.current_weather()
    if not wx:
        return
    sky = "sun" if wx.get("is_day", 1) else "moon"
    if wx.get("weather_code") not in (0, 1, None) or wx.get("condition") not in (None, "", "Clear sky", "Mostly clear"):
        sky = "cloud"
    desc = wx.get("condition") or describe_weather(wx.get("weather_code"), wx.get("is_day", 1))
    at = _obs_time(wx)
    where = wx.get("station", "Open-Meteo model").split(" (")[0]
    st.markdown(_html(f"""
        <div class="hero-box hero-wx">
            <div class="hero-wx-icon">{icon(sky, 40)}</div>
            <div>
                <div class="hero-box-eyebrow">{escape(where)} · {at} IST</div>
                <div class="hero-wx-temp">{_fmt(wx.get("temperature_2m"))}°<small>C</small></div>
                <div class="hero-wx-desc">{escape(desc)}</div>
                <div class="hero-wx-range">Forecast H {_fmt(wx.get("temperature_2m_max"))}° · L {_fmt(wx.get("temperature_2m_min"))}°</div>
            </div>
        </div>"""), unsafe_allow_html=True)


def render_hero():
    # A keyed container (not one HTML block) so the three boxes can mix HTML
    # with a real button (Key insights) and a self-refreshing fragment (weather).
    with st.container(key="sky-hero"):
        st.markdown(_html(
            f'<div class="sky-hero-clouds" aria-hidden="true"></div>{_top_row()}'
            f'<h1 class="hero-title">Air Today</h1>'
        ), unsafe_allow_html=True)
        aqi_col, ins_col, wx_col = st.columns([1.3, 1, 1], gap="medium", vertical_alignment="center")
        with aqi_col:
            st.markdown(_hero_aqi_html(), unsafe_allow_html=True)
        with ins_col:
            _hero_insights()
        with wx_col:
            _hero_weather()


# ---------------------------------------------------------- key insights --
def _short_date(iso):
    from datetime import date as _date
    return _date.fromisoformat(iso).strftime("%d %b") if iso else ""


def insight_items(facts):
    """facts (data/insights_today.json) -> compact rows: icon, label, value, chip, note, tone."""
    items = []
    aqi, fc = facts["aqi"], facts["forecast"]
    if aqi["value"] is not None:
        diff = aqi["value"] - aqi["prev_value"] if aqi["prev_value"] is not None else None
        note = "" if diff is None else f'{"▲" if diff > 0 else "▼" if diff < 0 else "•"} {abs(diff)} vs {_short_date(aqi["prev_date"])}'
        items.append(dict(icon="aqi", label=f'AQI · {_short_date(facts["date"])}', value=aqi["value"], unit="",
                          chip=aqi["category"], note=" · ".join(x for x in (note, aqi["pollutant"]) if x),
                          tone="bad" if diff and diff > 0 else "good" if diff and diff < 0 else None))
    else:
        items.append(dict(icon="aqi", label=f'AQI · {_short_date(facts["date"])}', value="—", unit="",
                          chip=None, note="CPCB bulletin not out yet", tone=None))
    items.append(dict(icon="forecast", label=f'Forecast · {_short_date(facts["forecast_date"])}',
                      value=fc["aqi"] if fc["aqi"] is not None else "—", unit="", chip=fc["category"],
                      note=fc["source"] or "AQEWS unavailable", tone="bad" if not fc["source"] else None))
    wind = facts["wind_ms"]
    items.append(dict(icon="wind", label="Avg wind", value=_fmt(wind, "{:.1f}"), unit="m/s", chip=None,
                      note="needs > 2.8 to disperse", tone=None if wind is None else ("good" if wind > 2.8 else "bad")))
    vi = facts["ventilation_index"]
    items.append(dict(icon="vent", label="Ventilation index", value=_fmt(vi, "{:,.0f}"), unit="m²/s", chip=None,
                      note="needs > 6,000", tone=None if vi is None else ("good" if vi > 6000 else "bad")))
    tmin = facts["min_temp_c"]
    items.append(dict(icon="temp", label="Min temperature", value=_fmt(tmin, "{:.1f}"), unit="°C", chip=None,
                      note="< 10 °C raises biomass burning", tone=None if tmin is None else ("bad" if tmin < 10 else None)))
    rain = facts["rain_mm"]
    items.append(dict(icon="rain", label="Rain (avg)", value=_fmt(rain, "{:.1f}"), unit="mm/h", chip=None,
                      note="washout likely" if (rain or 0) >= 0.1 else "dry",
                      tone="good" if (rain or 0) >= 0.1 else None))
    fires = facts["fires"]
    items.append(dict(icon="fire", label=f'Fires PB+HR · {_short_date(facts["fire_date"])}',
                      value="—" if fires is None else fires["total"], unit="", chip=None,
                      note="feed not updated" if fires is None else f'PB {fires["punjab"]} · HR {fires["haryana"]}',
                      tone=None))
    return items


def _headline(facts):
    """One-line takeaway, e.g. 'Poor today → Very Poor tomorrow. Weak wind, low ventilation.'"""
    parts = []
    today_cat, fc_cat = facts["aqi"]["category"], facts["forecast"]["category"]
    if today_cat and fc_cat:
        parts.append(f"{today_cat} today → {fc_cat} tomorrow.")
    elif today_cat:
        parts.append(f"{today_cat} today.")
    traps = []
    if facts["wind_ms"] is not None and facts["wind_ms"] <= 2.8:
        traps.append("weak wind")
    if facts["ventilation_index"] is not None and facts["ventilation_index"] <= 6000:
        traps.append("low ventilation")
    if traps:
        parts.append(f'{" and ".join(traps).capitalize()} will hold pollution in.')
    elif facts["wind_ms"] is not None:
        parts.append("Conditions favour dispersion.")
    return " ".join(parts)


def render_insights_panel():
    facts = data.insights_today()
    if not facts:
        st.info("Today's update hasn't been generated yet.")
        return
    rows = []
    for it in insight_items(facts):
        chip = (f'<span class="ins-chip" style="--chip:{AQI_COLOURS.get(str(it["chip"]), "#5a6b85")}">{escape(str(it["chip"]))}</span>'
                if it["chip"] else "")
        rows.append(
            f'<div class="ins-row {it["tone"] or ""}"><div class="ins-icon">{icon(it["icon"], 18)}</div>'
            f'<div class="ins-body"><div class="ins-label">{escape(it["label"])}</div>'
            f'<div class="ins-value">{it["value"]}<small>{it["unit"]}</small>{chip}</div>'
            f'<div class="ins-note">{escape(it["note"])}</div></div></div>'
        )
    st.markdown(_html(
        f'<div class="ins-headline">{escape(_headline(facts))}</div>'
        f'<div class="ins-grid">{"".join(rows)}</div>'
        f'<div class="ins-legend"><span class="ins-dot good"></span>helps air quality'
        f'<span class="ins-dot bad"></span>works against it</div>'
    ), unsafe_allow_html=True)
    sentences = data.daily_update_text()
    if sentences:
        with st.expander("Full text (as archived)", icon=":material/notes:"):
            # st.code for its built-in copy icon (top right); CSS restyles it as prose
            with st.container(key="archived-text"):
                st.code("\n".join(f"• {s}" for s in sentences), language=None, wrap_lines=True)


@st.dialog("Key insights", width="large")
def insights_dialog():
    render_insights_panel()


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


def _d(day):
    """28 Oct"""
    return day.strftime("%d %b").lstrip("0")


def _obs_time(wx):
    """HH:MM IST of the weather observation (METAR), else of the model step."""
    stamp = wx.get("observed_at") or wx.get("time") or ""
    return stamp[11:16]


@st.fragment(run_every="5m")
def render_kpi_grid():
    """Re-runs itself every 5 minutes so the live weather cards stay current."""
    today = effective_today()
    tomorrow = today + timedelta(days=1)
    aqi_row, prev_row = data.aqi_today_and_yesterday()
    fc = data.forecast_for(tomorrow)
    wx = data.current_weather()
    fires = data.fire_counts(today - timedelta(days=1))
    at = _obs_time(wx)
    at_label = f" · {at}" if at else ""

    cards = []
    if aqi_row:
        diff = int(aqi_row["aqi"]) - int(prev_row["aqi"]) if prev_row else None
        note = "" if diff is None else f'{"▲" if diff > 0 else "▼" if diff < 0 else "•"} {abs(diff)} vs {_d(prev_row["date"])}'
        tone = None if not diff else ("bad" if diff > 0 else "good")
        cards.append(kpi_card("aqi", f"AQI · {_d(aqi_row['date'])}", int(aqi_row["aqi"]), "", note, tone,
                              AQI_COLOURS.get(aqi_row["category"])))
    else:
        cards.append(kpi_card("aqi", f"AQI · {_d(today)}", "—", "", "Bulletin pending"))

    if fc["aqi"] is not None or fc["category"]:
        cards.append(kpi_card("forecast", f"Forecast · {_d(tomorrow)}", fc["aqi"] if fc["aqi"] is not None else "—", "",
                              escape(str(fc["category"] or "")), None, AQI_COLOURS.get(str(fc["category"]))))
    else:
        cards.append(kpi_card("forecast", f"Forecast · {_d(tomorrow)}", "—", "", "AQEWS forecast unavailable", "bad"))

    wind = wx.get("wind_speed_10m")
    wind_dir = wx.get("wind_direction_10m")
    arrow = (f'<span class="sky-wind-arrow" style="transform:rotate({(wind_dir + 180) % 360}deg)">↑</span>'
             if wind_dir is not None else "")
    cards.append(kpi_card(
        "wind", f"Wind {compass(wind_dir)}{at_label}".strip(), _fmt(wind, "{:.1f}"), " m/s",
        "" if wind is None else ("Favourable for dispersion" if wind >= 2.8 else "Weak dispersion"),
        None if wind is None else ("good" if wind >= 2.8 else "bad"), extra=arrow,
    ))

    vi = fc["ventilation_index"]
    cards.append(kpi_card(
        "vent", f"Ventilation index · {_d(tomorrow)}", _fmt(vi, "{:,.0f}"), " m²/s",
        "" if vi is None else ("Favourable (> 6,000)" if vi > 6000 else "Unfavourable (≤ 6,000)"),
        None if vi is None else ("good" if vi > 6000 else "bad"),
    ))

    blh = wx.get("boundary_layer_height")
    cards.append(kpi_card("layers", f"Mixing height{at_label}", _fmt(blh), " m",
                          "" if blh is None else ("Shallow – pollutants trapped" if blh < 500 else "Deep mixing"),
                          None if blh is None else ("bad" if blh < 500 else "good")))

    cards.append(kpi_card("temp", f"Temperature{at_label}", _fmt(wx.get("temperature_2m"), "{:.1f}"), " °C",
                          f'Feels {_fmt(wx.get("apparent_temperature"))}° · fcst min {_fmt(wx.get("temperature_2m_min"))}°'))
    cards.append(kpi_card("humidity", f"Humidity{at_label}", _fmt(wx.get("relative_humidity_2m")), " %",
                          f'Cloud {_fmt(wx.get("cloud_cover"))}%'))
    vis = wx.get("visibility")
    vis_note = wx.get("condition") or ("Haze / smog likely" if vis is not None and vis < 2000 else "Clear")
    cards.append(kpi_card("eye", f"Visibility{at_label}", _fmt(None if vis is None else vis / 1000, "{:.1f}"), " km",
                          "" if vis is None else escape(vis_note),
                          None if vis is None else ("bad" if vis < 2000 else None)))
    cards.append(kpi_card("rain", "Rain · last hour", _fmt(wx.get("precipitation"), "{:.1f}"), " mm",
                          "Rain helps wash out PM" if (wx.get("precipitation") or 0) > 0 else "Dry"))
    fire_day = _d(today - timedelta(days=1))
    if fires is None:
        cards.append(kpi_card("fire", f"Fires PB + HR · {fire_day}", "—", "", "Fire feed not updated"))
    else:
        cards.append(kpi_card("fire", f"Fires PB + HR · {fire_day}", sum(fires.values()), "",
                              f'Punjab {fires.get("Punjab", 0)} · Haryana {fires.get("Haryana", 0)}'))

    st.markdown(_html(f'<div class="sky-kpi-grid">{"".join(cards)}</div>'), unsafe_allow_html=True)
    if wx:
        st.markdown(
            f'<div class="sky-kpi-source">AQI: CPCB daily bulletin · Forecast and ventilation index: IITM AQEWS · '
            f'Weather: {escape(wx.get("source", "Open-Meteo"))}{" at " + at + " IST" if at else ""} · refreshes every 5 min</div>',
            unsafe_allow_html=True,
        )
