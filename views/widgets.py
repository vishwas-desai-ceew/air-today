"""Sky theme building blocks: the page hero and top bar (with data health and
the signed-in user), weather-style KPI cards and the Key insights dialog. Pure presentation - all numbers come from views/data.py."""
from datetime import datetime, timedelta
from html import escape

import streamlit as st

from config.reference import SOURCES
from config.settings import IST, effective_today
from views import data

# 24x24 stroke icons (Lucide-style geometry, drawn inline so no icon font is needed)
ICONS = {
    "aqi": '<path d="M3 12h4l3-8 4 16 3-8h4"/>',
    "forecast": '<path d="M3 17l6-6 4 4 8-8"/><path d="M14 7h7v7"/>',
    "archive": '<rect x="3" y="4" width="18" height="4" rx="1"/><path d="M5 8v11a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8"/><path d="M10 12h4"/>',
    "alert": '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><path d="M12 8h.01"/>',
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
    "cloud-sun": '<path d="M12 2v2M4.93 4.93l1.41 1.41M20 12h2M19.07 4.93l-1.41 1.41"/><path d="M15.95 12.65A4 4 0 0 0 8.4 9.5"/><path d="M13 22H7a5 5 0 1 1 4.9-6H13a3 3 0 0 1 0 6z"/>',
    "cloud-moon": '<path d="M13 16a3 3 0 1 1 0 6H7a5 5 0 1 1 4.9-6z"/><path d="M10.1 9A6 6 0 0 1 16 4a4.24 4.24 0 0 0 6 6 6 6 0 0 1-3 5.2"/>',
    "fog": '<path d="M20 15.5A4.5 4.5 0 0 0 17.5 7h-1.79A7 7 0 1 0 4 13"/><path d="M4 17h16M6 21h12"/>',
    "storm": '<path d="M19 16.9A5 5 0 0 0 18 7h-1.26a8 8 0 1 0-11.62 9"/><path d="m13 11-4 6h6l-4 6"/>',
    "drop": '<path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z"/>',
    "gauge": '<path d="m12 14 4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/>',
    "sunrise": '<path d="M12 2v8M4.93 10.93l1.41 1.41M2 18h2M20 18h2M19.07 10.93l-1.41 1.41M22 22H2M8 6l4-4 4 4M16 18a4 4 0 0 0-8 0"/>',
    "sunset": '<path d="M12 10V2M4.93 10.93l1.41 1.41M2 18h2M20 18h2M19.07 10.93l-1.41 1.41M22 22H2M16 6l-4 4-4-4M16 18a4 4 0 0 0-8 0"/>',
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


def src(key, label=None, url=None):
    """<a> to a source in config.reference.SOURCES (label/url override, e.g. the day's CPCB PDF)."""
    name, href = SOURCES.get(key, (key, None))
    href = url or href
    text = escape(label or name)
    return f'<a href="{escape(href)}" target="_blank" rel="noopener">{text}</a>' if href else text


def source_html(*links, cls="card-source"):
    links = [l for l in links if l]
    return f'<div class="{cls}">Source: {" · ".join(links)}</div>' if links else ""


def side_source(*links):
    """Source line for a chart's side panel: bold 'Source', each source linked
    where it has a URL (pass src(...) / cpcb_src(...) results or plain text)."""
    links = [l for l in links if l]
    return f"<div class='side-source'><b>Source</b>{' · '.join(links)}</div>" if links else ""


def side_points(points):
    """Two or three short bullet points for a chart's side panel (HTML allowed)."""
    return "<ul class='side-points'>" + "".join(f"<li>{p}</li>" for p in points) + "</ul>"


def cpcb_src(row):
    return src("cpcb", "CPCB bulletin", data.cpcb_bulletin_url(row)) if row else src("cpcb", "CPCB", "https://cpcb.gov.in/")


def metar_src(wx, short=True):
    """Link to the METAR report of the station the observation came from
    (IGI Airport VIDP, or Safdarjung VIDD as fallback)."""
    station = wx.get("station") or "IGI Airport (VIDP)"
    icao = station.split("(")[-1].rstrip(")") if "(" in station else "VIDP"
    label = f"METAR, {station.split(' (')[0] if short else station}"
    return src("metar", label, f"https://aviationweather.gov/data/metar/?ids={icao}")


# What a METAR report can supply (ingestion/weather.py fetch_metar), for cached
# readings saved before observed_fields was recorded.
METAR_FIELDS = ["relative_humidity_2m", "surface_pressure", "temperature_2m", "visibility",
                "wind_direction_10m", "wind_speed_10m"]


def observed_fields(wx):
    """Fields that came from METAR rather than the Open-Meteo model."""
    if "observed_fields" in wx:
        return wx["observed_fields"] or []
    return METAR_FIELDS if wx.get("observed_at") else []


def wx_src(wx, field):
    """METAR for a field the latest observation reported, else the Open-Meteo model."""
    return metar_src(wx) if field in observed_fields(wx) else src("open_meteo_model")


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


# Each publisher's own small site icon, loaded from its site, to make the source
# easy to spot. TOI's favicon.ico is fully transparent, so its home-screen icon is used.
PUBLISHER_ICONS = {
    "The Hindu": "https://www.thehindu.com/favicon.ico",
    "Times of India": "https://m.timesofindia.com/touch-icon-iphone-precomposed.png",
    "NDTV": "https://www.ndtv.com/favicon.ico",
}
NEWS_NOTE = ("Headlines picked automatically by keyword from the Delhi news feeds of The Hindu, "
             "Times of India and NDTV, newest first. Links open the publisher's article; "
             "they are not reviewed or endorsed by CEEW.")


def publisher_badge(name):
    icon_url = PUBLISHER_ICONS.get(name)
    img = (f"<img src='{icon_url}' alt='' width='14' height='14' referrerpolicy='no-referrer'>"
           if icon_url else "")
    return f"<span class='lrn-pub'>{img}{escape(name)}</span>"


def news_items_html(items):
    return "".join(
        f"<a class='lrn-news-item' href='{escape(it['link'], quote=True)}' target='_blank' rel='noopener'>"
        f"<b>{escape(it['title'])}</b><small>{publisher_badge(it['publisher'])}"
        f"{' · ' + it['published'].strftime('%d %b, %H:%M') if it['published'] else ''}</small></a>"
        for it in items
    )


def _news_pill(limit=6):
    """'AQI in the news' dropdown for the header: the latest headlines."""
    try:
        items = data.aqi_news()
    except Exception:
        items = []
    if not items:
        return ""
    return (
        '<details class="hero-health hero-news"><summary>AQI in the news'
        f'<span class="hero-news-count">{len(items)}</span><span class="hero-caret">▾</span></summary>'
        f'<div class="hero-news-panel">{news_items_html(items[:limit])}'
        f'<a class="hero-news-more" href="/trends" target="_self">All headlines on Recent trends →</a>'
        f'<p>{escape(NEWS_NOTE)}</p></div></details>'
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
        f'<div class="hero-actions">{_news_pill()}{_health_pill()}{_user_chip()}</div></div>'
    )


def render_topbar():
    """Slim sky strip for every page except Overview (which has the full hero)."""
    from views.sky import apply_sky  # sky imports this module
    apply_sky()
    st.markdown(_html(f'<section class="sky-topbar">{_top_row()}</section>'), unsafe_allow_html=True)


# ------------------------------------------------------------------- hero --
def _hero_aqi_html():
    aqi_row, prev_row = data.aqi_today_and_yesterday()
    if not aqi_row:
        return _html("""
            <div class="hero-box hero-aqi hero-aqi--pending">
                <div class="hero-aqi-value">—</div>
                <div><div class="hero-box-eyebrow">AQI · CPCB</div><div class="hero-aqi-cat">Awaiting bulletin</div>
                <div class="hero-aqi-meta">Published around 4 PM IST</div>
                """ + source_html(cpcb_src(None), cls="hero-source") + """</div>
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
                {source_html(cpcb_src(aqi_row), cls="hero-source")}
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
                + source_html(src("cpcb", "CPCB"), src("aqews", "AQEWS"), src("open_meteo_model", "Open-Meteo"), src("creams", "ICAR-IARI CREAMS"), cls="hero-source")
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
    from views.sky import sky_phase, wx_icon_name
    desc = wx.get("condition") or describe_weather(wx.get("weather_code"), wx.get("is_day", 1))
    sky = wx_icon_name(wx.get("weather_code"), sky_phase() in ("day", "dawn", "dusk") if wx.get("is_day") is None
                       else wx.get("is_day"), wx.get("precipitation"), condition=desc)
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
                {source_html(wx_src(wx, "temperature_2m"), src("open_meteo_model", "Open-Meteo") if observed_fields(wx) else "", cls="hero-source")}
            </div>
        </div>"""), unsafe_allow_html=True)


def render_hero():
    from views.sky import apply_sky  # sky imports this module
    apply_sky()
    # A keyed container (not one HTML block) so the three boxes can mix HTML
    # with a real button (Key insights) and a self-refreshing fragment (weather).
    with st.container(key="sky-hero"):
        st.markdown(_html(
            f'<div class="sky-hero-clouds" aria-hidden="true"></div>{_top_row()}'
            f'<h1 class="hero-title">Air Today</h1>'
        ), unsafe_allow_html=True)
        aqi_col, ins_col, wx_col = st.columns(3, gap="medium", vertical_alignment="top")
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


def _aqi_tone(category):
    """Colour an AQI row by its category, not by the change vs yesterday: a
    Very Poor day that improved on a Severe one is still bad air."""
    cat = str(category or "").lower()
    if cat.startswith(("poor", "very poor", "severe")):
        return "bad"
    if cat in ("good", "satisfactory"):
        return "good"
    return None


def insight_items(facts):
    """facts (data/insights_today.json) -> compact rows: icon, label, value, chip, note, tone."""
    items = []
    aqi, fc = facts["aqi"], facts["forecast"]
    cpcb_link = cpcb_src({"date": datetime.fromisoformat(facts["date"]), "source": ""})
    if aqi["value"] is not None:
        diff = aqi["value"] - aqi["prev_value"] if aqi["prev_value"] is not None else None
        note = "" if diff is None else f'{"▲" if diff > 0 else "▼" if diff < 0 else "•"} {abs(diff)} vs {_short_date(aqi["prev_date"])}'
        items.append(dict(icon="aqi", label=f'AQI · {_short_date(facts["date"])}', value=aqi["value"], unit="",
                          chip=aqi["category"], note=" · ".join(x for x in (note, aqi["pollutant"]) if x), source=cpcb_link,
                          tone=_aqi_tone(aqi["category"])))
    else:
        items.append(dict(icon="aqi", label=f'AQI · {_short_date(facts["date"])}', value="—", unit="",
                          chip=None, note="CPCB bulletin not out yet", source=cpcb_src(None), tone=None))
    items.append(dict(icon="forecast", label=f'Forecast · {_short_date(facts["forecast_date"])}',
                      value=fc["aqi"] if fc["aqi"] is not None else "—", unit="", chip=fc["category"],
                      note=(fc["source"] or "AQEWS unavailable").replace("AQEWS model", "AQEWS"),
                      source=src("aqews", "AQEWS"), tone=_aqi_tone(fc["category"])))
    wind = facts["wind_ms"]
    items.append(dict(icon="wind", label="Avg wind", value=_fmt(wind, "{:.1f}"), unit="m/s", chip=None,
                      note="needs > 2.8 m/s to disperse",
                      source=src("open_meteo_model", "Open-Meteo forecast"), tone=None if wind is None else ("good" if wind > 2.8 else "bad")))
    vi = facts["ventilation_index"]
    items.append(dict(icon="vent", label="Ventilation index", value=_fmt(vi, "{:,.0f}"), unit="m²/s", chip=None,
                      note="needs > 6,000 m²/s", source=src("aqews", "AQEWS"), tone=None if vi is None else ("good" if vi > 6000 else "bad")))
    tmin = facts["min_temp_c"]
    items.append(dict(icon="temp", label="Min temperature", value=_fmt(tmin, "{:.1f}"), unit="°C", chip=None,
                      note="< 10 °C raises biomass burning",
                      source=src("open_meteo_model", "Open-Meteo forecast"), tone=None if tmin is None else ("bad" if tmin < 10 else None)))
    rain = facts["rain_mm"]
    items.append(dict(icon="rain", label="Rain (avg)", value=_fmt(rain, "{:.1f}"), unit="mm/h", chip=None,
                      note="washout likely (≥ 0.1 mm/h)" if (rain or 0) >= 0.1 else "dry (< 0.1 mm/h)",
                      source=src("open_meteo_model", "Open-Meteo forecast"),
                      tone="good" if (rain or 0) >= 0.1 else None))
    fires = facts["fires"]
    items.append(dict(icon="fire", label=f'Fires PB+HR · {_short_date(facts["fire_date"])}',
                      value="—" if fires is None else fires["total"], unit="", chip=None,
                      note="bulletin not out yet" if fires is None else f'PB {fires["punjab"]} · HR {fires["haryana"]} · paddy residue',
                      source=src("creams", "ICAR-IARI CREAMS"), tone=None))
    return items


def _headline(facts):
    """One-line takeaway, e.g. 'Poor on 6 Nov → Very Poor on 7 Nov. Weak wind will hold pollution in.'"""
    parts = []
    today_cat, fc_cat = facts["aqi"]["category"], facts["forecast"]["category"]
    day = _short_date(facts["date"]).lstrip("0")
    fc_day = _short_date(facts.get("forecast_date")).lstrip("0")
    if today_cat and fc_cat:
        parts.append(f"{today_cat} on {day} → {fc_cat} on {fc_day}.")
    elif today_cat:
        parts.append(f"{today_cat} on {day}.")
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


@st.dialog("Key insights (in text, as archived)", width="large")
def archived_text_dialog(sentences):
    # st.code for its built-in copy icon (top right); CSS restyles it as prose
    with st.container(key="archived-text"):
        st.code("\n".join(f"• {s}" for s in sentences), language=None, wrap_lines=True)


def render_insights_panel(full_text="expander"):
    """full_text: "dialog" opens the archived text in its own dialog (Daily
    update page); "expander" keeps it inline, for when this panel is itself
    shown in a dialog (Streamlit can't open a dialog from inside one)."""
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
            f'<div class="ins-note">{escape(it["note"])}</div>{source_html(it.get("source"))}</div></div>'
        )
    st.markdown(_html(
        f'<div class="ins-headline">{escape(_headline(facts))}</div>'
        f'<div class="ins-grid">{"".join(rows)}</div>'
        f'<div class="ins-legend"><span class="ins-dot good"></span>helps air quality'
        f'<span class="ins-dot bad"></span>works against it</div>'
    ), unsafe_allow_html=True)
    sentences = data.daily_update_text()
    if not sentences:
        return
    label = "Key insights (in text, as archived)"
    if full_text == "dialog":
        with st.container(key="archived-text-open"):
            if st.button(label, key="open_archived_text", icon=":material/notes:", type="primary"):
                archived_text_dialog(sentences)
    else:
        with st.container(key="archived-text-inline"):
            with st.expander(label, icon=":material/notes:"):
                with st.container(key="archived-text"):
                    st.code("\n".join(f"• {s}" for s in sentences), language=None, wrap_lines=True)


@st.dialog("Key insights", width="large")
def insights_dialog():
    render_insights_panel()


# -------------------------------------------------------------- KPI cards --
def kpi_card(icon_name, label, value, unit="", note="", tone=None, accent=None, extra="", source="", stamp=""):
    """A weather-widget style card. tone: "good" | "bad" | None colours the note chip.
    stamp: the date/time of the data point, shown on its own line under the label."""
    note_html = f'<span class="sky-kpi-note {tone or ""}">{note}</span>' if note else ""
    style = f' style="--accent:{accent}"' if accent else ""
    return f"""
        <article class="sky-kpi"{style}>
            <div class="sky-kpi-head">{icon(icon_name)}<span>{label}</span></div>
            {f'<div class="sky-kpi-stamp">{stamp}</div>' if stamp else ""}
            <div class="sky-kpi-value">{value}<small>{unit}</small>{extra}</div>
            {note_html}
            {source_html(source) if source else ""}
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
    at_stamp = f"{at} IST" if at else ""

    cards = []
    if aqi_row:
        diff = int(aqi_row["aqi"]) - int(prev_row["aqi"]) if prev_row else None
        note = "" if diff is None else f'{"▲" if diff > 0 else "▼" if diff < 0 else "•"} {abs(diff)} vs {_d(prev_row["date"])}'
        tone = None if not diff else ("bad" if diff > 0 else "good")
        cards.append(kpi_card("aqi", "AQI", int(aqi_row["aqi"]), "", note, tone,
                              AQI_COLOURS.get(aqi_row["category"]), source=cpcb_src(aqi_row), stamp=_d(aqi_row["date"])))
    else:
        cards.append(kpi_card("aqi", "AQI", "—", "", "Bulletin pending", source=cpcb_src(None), stamp=_d(today)))

    if fc["aqi"] is not None or fc["category"]:
        cards.append(kpi_card("forecast", "AQI forecast", fc["aqi"] if fc["aqi"] is not None else "—", "",
                              escape(str(fc["category"] or "")), None, AQI_COLOURS.get(str(fc["category"])),
                              source=src("aqews", "AQEWS"), stamp=f"For {_d(tomorrow)}"))
    else:
        cards.append(kpi_card("forecast", "AQI forecast", "—", "", "AQEWS forecast unavailable", "bad",
                              source=src("aqews", "AQEWS"), stamp=f"For {_d(tomorrow)}"))

    wind = wx.get("wind_speed_10m")
    wind_dir = wx.get("wind_direction_10m")
    arrow = (f'<span class="sky-wind-arrow" style="transform:rotate({(wind_dir + 180) % 360}deg)">↑</span>'
             if wind_dir is not None else "")
    cards.append(kpi_card(
        "wind", f"Wind {compass(wind_dir)}".strip(), _fmt(wind, "{:.1f}"), " m/s",
        "" if wind is None else ("Favourable for dispersion" if wind >= 2.8 else "Weak dispersion"),
        None if wind is None else ("good" if wind >= 2.8 else "bad"), extra=arrow,
        source=wx_src(wx, "wind_speed_10m"), stamp=at_stamp,
    ))

    vi = fc["ventilation_index"]
    cards.append(kpi_card(
        "vent", "Ventilation index", _fmt(vi, "{:,.0f}"), " m²/s",
        "" if vi is None else ("Favourable (> 6,000 m²/s)" if vi > 6000 else "Unfavourable (≤ 6,000 m²/s)"),
        None if vi is None else ("good" if vi > 6000 else "bad"), source=src("aqews", "AQEWS"),
        stamp=f"For {_d(tomorrow)}",
    ))

    blh = wx.get("boundary_layer_height")
    cards.append(kpi_card("layers", "Mixing height", _fmt(blh), " m",
                          "" if blh is None else ("Shallow (< 500 m) – pollutants trapped" if blh < 500 else "Deep mixing (≥ 500 m)"),
                          None if blh is None else ("bad" if blh < 500 else "good"),
                          source=src("open_meteo_model"), stamp=at_stamp))

    cards.append(kpi_card("temp", "Temperature", _fmt(wx.get("temperature_2m"), "{:.1f}"), " °C",
                          f'Feels {_fmt(wx.get("apparent_temperature"))}° · fcst min {_fmt(wx.get("temperature_2m_min"))}°',
                          source=wx_src(wx, "temperature_2m"), stamp=at_stamp))
    cards.append(kpi_card("humidity", "Humidity", _fmt(wx.get("relative_humidity_2m")), " %",
                          f'Cloud {_fmt(wx.get("cloud_cover"))}%', source=wx_src(wx, "relative_humidity_2m"), stamp=at_stamp))
    vis = wx.get("visibility")
    vis_note = wx.get("condition") or ("Haze / smog likely" if vis is not None and vis < 2000 else "Clear")
    cards.append(kpi_card("eye", "Visibility", _fmt(None if vis is None else vis / 1000, "{:.1f}"), " km",
                          "" if vis is None else escape(vis_note),
                          None if vis is None else ("bad" if vis < 2000 else None), source=wx_src(wx, "visibility"), stamp=at_stamp))
    cards.append(kpi_card("rain", "Rain", _fmt(wx.get("precipitation"), "{:.1f}"), " mm",
                          "Rain helps wash out PM" if (wx.get("precipitation") or 0) > 0 else "Dry",
                          source=src("open_meteo_model"), stamp="Last hour"))
    fire_day = _d(today - timedelta(days=1))
    if fires is None:
        cards.append(kpi_card("fire", "Fires PB + HR", "—", "", "CREAMS bulletin not out yet",
                              source=src("creams", "ICAR-IARI CREAMS"), stamp=fire_day))
    else:
        cards.append(kpi_card("fire", "Fires PB + HR", sum(fires.values()), "",
                              f'Punjab {fires.get("Punjab", 0)} · Haryana {fires.get("Haryana", 0)} · paddy residue',
                              source=src("creams", "ICAR-IARI CREAMS"), stamp=fire_day))

    st.markdown(_html(f'<div class="sky-kpi-grid">{"".join(cards)}</div>'), unsafe_allow_html=True)
    if wx:
        st.markdown(
            f'<div class="sky-kpi-source">Weather cards{" observed at " + at + " IST" if at else ""} · refresh every 5 min</div>',
            unsafe_allow_html=True,
        )
