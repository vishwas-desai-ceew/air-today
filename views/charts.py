"""Shared Plotly styling for the forecast and weather pages: one base layout,
shaded reference bands, and a source line under each chart."""
from html import escape

import plotly.graph_objects as go
import streamlit as st

from config.reference import SOURCES

FONT = "Arial, Helvetica, sans-serif"  # a font Plotly can measure before web fonts load (avoids clipped legends)
INK = "#0d2440"
MUTED = "#46607f"
GRID = "#e6eef8"


def hex_rgba(hex_colour, alpha):
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def base_layout(fig, height=380, y_title=None, legend=True):
    fig.update_layout(
        height=height,
        margin=dict(l=56, r=16, t=16, b=40),
        plot_bgcolor="#ffffff",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=13, color=MUTED),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#0a3d7a", bordercolor="#0a3d7a", font=dict(color="#fff", size=13, family=FONT)),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(size=12),
                    bgcolor="rgba(0,0,0,0)"),
        bargap=0.25,
    )
    fig.update_xaxes(showgrid=False, linecolor="#c9d8ea", ticks="outside", tickcolor="#c9d8ea",
                     fixedrange=True, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, fixedrange=True, tickfont=dict(color=MUTED),
                     title=dict(text=y_title, font=dict(size=12, color=MUTED)) if y_title else None)
    return fig


def add_bands(fig, bands, y_max, alpha=0.13, label=True, row=None, col=None):
    """Shade horizontal bands, labelled in the right margin.
    bands: [(name, low, high|None, colour)]."""
    kw = {} if row is None else dict(row=row, col=col)
    if label:
        fig.update_layout(margin=dict(r=86))
    for name, low, high, colour in bands:
        if low >= y_max:
            break
        top = y_max if high is None else min(high, y_max)
        fig.add_hrect(y0=low, y1=top, fillcolor=hex_rgba(colour, alpha), line_width=0, layer="below", **kw)
        if label and top - low > y_max * 0.05:
            fig.add_annotation(
                x=1.005, xref="x domain" if row is None else f"x{'' if row == 1 else row} domain",
                y=(low + top) / 2, yref="y" if row is None else f"y{'' if row == 1 else row}",
                text=f"<b>{name}</b>", showarrow=False, xanchor="left", font=dict(size=11, color=colour),
            )
    return fig


def source_line(*keys, note=""):
    links = " · ".join(f'<a href="{SOURCES[k][1]}" target="_blank">{escape(SOURCES[k][0])}</a>' for k in keys)
    st.markdown(
        f"<div class='chart-source'>Source: {links}{(' · ' + escape(note)) if note else ''}</div>",
        unsafe_allow_html=True,
    )


PLOT_CONFIG = {"displayModeBar": False}


def empty_fig():
    return go.Figure()
