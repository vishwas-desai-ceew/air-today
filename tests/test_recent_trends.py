from datetime import date

import pandas as pd

from ingestion.news import _date, _parse
from views.recent_trends import _longest_run, _same_day


def _days(start, values):
    d = pd.date_range(start, periods=len(values), freq="D")
    return pd.DataFrame({"date": d, "aqi": values})


def test_longest_run_counts_consecutive_days_only():
    s = _days("2025-11-01", [320, 330, 250, 310, 340, 360, 280])
    days, first, last = _longest_run(s)
    assert days == 3
    assert (first, last) == (pd.Timestamp("2025-11-04"), pd.Timestamp("2025-11-06"))


def test_longest_run_none():
    assert _longest_run(_days("2025-11-01", [120, 200]))[0] == 0


def test_same_day_matches_calendar_date_across_winters():
    df = pd.concat([_days("2025-11-08", [300, 310]), _days("2024-11-08", [280, 290])])
    start = df["date"].dt.year.where(df["date"].dt.month >= 10, df["date"].dt.year - 1)
    df["season"] = start.astype(str) + "-" + (start + 1).astype(str).str[-2:]
    rows = _same_day(df, date(2025, 11, 9))
    assert rows == [(pd.Timestamp("2025-11-09"), 310.0), (pd.Timestamp("2024-11-09"), 290.0)]


def test_news_parse_keeps_air_quality_headlines_only():
    xml = (
        "<item><title><![CDATA[Delhi AQI turns severe]]></title><link>https://x.in/a</link>"
        "<pubDate>Sun, 09 Nov 2026 10:00:00 +0530</pubDate></item>"
        "<item><title>Metro timings change</title><link>https://x.in/b</link></item>"
        "<item><title>Opinion | Why pollution persists</title><link>https://x.in/c</link></item>"
    )
    items = _parse("The Hindu", xml)
    assert [i["title"] for i in items] == ["Delhi AQI turns severe"]


def test_news_dates_in_both_feed_formats():
    assert _date("Sun, 09 Nov 2026 10:00:00 +0530").hour == 10
    assert _date("2026-11-09T21:13:32+05:30").hour == 21
    assert _date("not a date") is None
