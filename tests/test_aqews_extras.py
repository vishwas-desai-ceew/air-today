from pathlib import Path

import pandas as pd

from ingestion import aqews
from views.aqews_bulletin import bulletin_html

HOME = (Path(__file__).parent / "fixtures" / "aqews_home_bulletin_2026_11_06.html").read_text()


def test_extract_bulletin_keeps_english_sections_in_order():
    b = aqews.extract_bulletin(HOME)
    assert b["title"] == "Air Quality and Weather Bulletin for Delhi (06.11.2026)"
    assert b["date"] == "2026-11-06"
    assert [p[:2] for p in b["paragraphs"][:5]] == ["1.", "2.", "3.", "4.", "5."]
    assert b["paragraphs"][-1].startswith("For further information")
    assert not any("बुलेटिन" in p for p in b["paragraphs"])  # Hindi title dropped


def test_bulletin_html_numbers_sections_and_links_urls():
    html = bulletin_html(aqews.extract_bulletin(HOME))
    assert html.count("class='aqb-num'") == 5
    assert '<a href="https://nwp.imd.gov.in/airqualityfc_bulletin_mausam.php"' in html
    assert "<b>Past Weather and Air Quality Observation</b>" in html


def test_save_charts_writes_pm10(tmp_path, monkeypatch):
    monkeypatch.setattr(aqews, "AQEWS_PM10_CSV", tmp_path / "pm10.csv")
    monkeypatch.setattr(aqews, "AQEWS_PM25_CSV", tmp_path / "pm25.csv")
    aqews.save_charts({"pm10_conc": (["2026-11-05 17:00:00", "2026-11-05 19:00:00"], [182.27, "207.03"])})
    df = pd.read_csv(tmp_path / "pm10.csv")
    assert list(df.columns) == ["time", "PM10"] and df["PM10"].tolist() == [182.27, 207.03]
    assert not (tmp_path / "pm25.csv").exists()
