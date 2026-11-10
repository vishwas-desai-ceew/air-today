"""CREAMS bulletin parsing. Rows below are copied from what pdfplumber returns
for bulletin no. 56 (09-Nov-2026), including its blank spacer cells; the full
62-page PDF is too large to keep as a fixture."""
from datetime import date

import pandas as pd

from ingestion import creams, get_met_details

PAGE_HTML = """
<a href="/Creams_website_bulletin/Fire_bulletin_2025/Fire_bulletin_2025r/77.RiceResidueFireBulletin_30Nov_2025_ICAR.pdf">77</a>
<a href="/Creams_website_bulletin/Fire_bulletin_2026/Fire_bulletin_2026r/55.RiceResidueFireBulletin_08Nov_2026_ICAR.pdf">55</a>
<a href="/Creams_website_bulletin/Fire_bulletin_2026/Fire_bulletin_2026r/56.RiceResidueFireBulletin_09Nov_2026_ICAR.pdf">56</a>
<a href="/Creams_website_bulletin/Fire_bulletin_2022/Fire_bulletin_2022w/40.WheatResidueFireBulletin_15May_2022_ICAR.pdf">wheat</a>
"""

DAILY_ROWS = [
    ["", "", None, "Punjab", None, None, "Haryana", None, "", "Uttar Pradesh", None, ""],
    ["Date", None, None, "2020", None, "2021", None, "2022", "2023", "2024", "2025", "2026"],
    ["", "08-Nov", "", "3674", "", "4397", "604", "2003", "730", "238", "1152", "", "115", "138", "11", "44", "29",
     "42", "80", "169", "21", "44", "47", "55", "158", "16"],
    ["09-Nov", None, "1718", "5079", "1778", "639", "237", "440", "198", "21", "217", "69", "27", "24", "67", "17",
     "115", "51", "58", "17", "139", "105", "47"],
    ["", "Uttarakhand", None, ""],
    ["09-Nov", None, "8", "13", "3", "3", "6", "10", "8"],
]


def _event(n, district, lat):
    return [str(n), district, "BLOCK", "JPSS-1", str(lat), "75.1", "13:48:44", "D", "4.00"]


def test_lists_rice_bulletins_newest_last():
    found = creams.list_bulletins(PAGE_HTML)
    assert [b["number"] for b in found] == [77, 55, 56]           # by date, wheat ignored
    assert found[-1]["date"] == date(2026, 11, 9)
    assert found[-1]["url"].startswith("https://creams.iari.res.in/Creams_website_bulletin/Fire_bulletin_2026/")


def test_date_wise_rows_split_into_states_and_years():
    df = pd.DataFrame(creams.parse_daily_rows(DAILY_ROWS, 2026), columns=creams.DAILY_COLUMNS)
    nov9 = df[df["date"] == date(2026, 11, 9)].set_index("state")["events"].to_dict()
    assert nov9 == {"Punjab": 198, "Haryana": 17, "Uttar Pradesh": 47, "Uttarakhand": 8}
    assert df[(df["state"] == "Punjab") & (df["date"] == date(2020, 11, 8))]["events"].item() == 3674
    assert len(df) == 7 * (3 * 2 + 1)                            # 7 years x (3 states x 2 days + 1)


def test_short_row_is_skipped_not_misassigned():
    rows = [["Punjab"], ["09-Nov", "1", "2", "3"]]
    assert creams.parse_daily_rows(rows, 2026) == []


def test_fires_follow_state_headings_across_pages():
    # Haryana's list starts part-way down the page that ends Punjab's.
    pages = [
        ("Details of paddy residue burning events in Punjab on 09-Nov-2026", [_event(1, "BARNALA", 30.1)]),
        ("Details of paddy residue burning events in Haryana on 09-Nov-2026",
         [_event(2, "SANGRUR", 30.2), _event(1, "JIND", 29.3), ["S. No.", "District"]]),
    ]
    ev = creams.parse_event_rows(pages)
    assert [(e["state"], e["district"]) for e in ev] == [("Punjab", "Barnala"), ("Punjab", "Sangrur"), ("Haryana", "Jind")]
    assert ev[0]["date"] == date(2026, 11, 9) and ev[0]["frp_w_m2"] == 4.0


def test_check_events_flags_mismatch():
    daily = pd.DataFrame([(date(2026, 11, 9), "Punjab", 2)], columns=creams.DAILY_COLUMNS)
    events = pd.DataFrame([{"date": date(2026, 11, 9), "state": "Punjab"}])
    assert creams.check_events(daily, events) == ["Punjab 2026-11-09: 1 fires listed, table says 2"]


def test_highlights_and_cover():
    text = ("Bulletin No: 56\nEvents Date: 09-Nov-2026\nIssue Date: 09-Nov-2026\nHighlights For 09-Nov-2026\n"
            "Satellites detected 559 residue burning events in the six study States\non 09-Nov-2026. Thick clouds "
            "cover northern\nPunjab.\nTemporal distribution of paddy residue burning events")
    meta = creams.parse_highlights(text)
    assert meta["bulletin_no"] == 56 and meta["events_date"] == "2026-11-09"
    assert meta["highlights"] == ["Satellites detected 559 residue burning events in the six study States on 09-Nov-2026.",
                                  "Thick clouds cover northern Punjab."]


def test_save_upserts_and_latest_headline(tmp_path, monkeypatch):
    daily_path, events_path = tmp_path / "creams_fires.csv", tmp_path / "creams_fire_events.csv"
    first = pd.DataFrame([(date(2026, 11, 8), "Punjab", 10), (date(2026, 11, 8), "Haryana", 1)], columns=creams.DAILY_COLUMNS)
    creams.save({"daily": first, "events": pd.DataFrame(columns=creams.EVENT_COLUMNS)}, daily_path, events_path)
    second = pd.DataFrame([(date(2026, 11, 8), "Punjab", 12), (date(2026, 11, 9), "Punjab", 198),
                           (date(2026, 11, 9), "Haryana", 17)], columns=creams.DAILY_COLUMNS)
    creams.save({"daily": second, "events": pd.DataFrame(columns=creams.EVENT_COLUMNS)}, daily_path, events_path)

    df = creams.read_daily(daily_path)
    assert df[(df["date"] == date(2026, 11, 8)) & (df["state"] == "Punjab")]["events"].item() == 12   # replaced
    assert creams.latest_headline(["Punjab", "Haryana"], df) == (date(2026, 11, 9), {"Punjab": 198, "Haryana": 17})
    # A day only some states have (a partial row) isn't "latest"
    partial = pd.concat([df, pd.DataFrame([(date(2026, 11, 10), "Punjab", 5)], columns=creams.DAILY_COLUMNS)])
    assert creams.latest_headline(["Punjab", "Haryana"], partial)[0] == date(2026, 11, 9)
    assert creams.latest_headline(["Punjab"], df.iloc[0:0]) == (None, None)

    monkeypatch.setattr(creams, "read_daily", lambda path=None: df)
    assert get_met_details.get_latest_fire_count() == (date(2026, 11, 9), {"Punjab": 198, "Haryana": 17})


def test_insights_take_a_newer_bulletin_than_the_summary():
    from views.data import with_live_fires
    facts = {"fire_date": "2026-11-08", "fires": {"total": 1232, "punjab": 1152, "haryana": 80}}
    newer = with_live_fires(facts, (date(2026, 11, 9), {"Punjab": 198, "Haryana": 17}))
    assert newer["fire_date"] == "2026-11-09" and newer["fires"] == {"total": 215, "punjab": 198, "haryana": 17}
    assert with_live_fires(facts, (date(2026, 11, 8), {"Punjab": 1, "Haryana": 1})) is facts      # not newer
    assert with_live_fires({"fire_date": "2026-11-08", "fires": None},
                           (date(2026, 11, 8), {"Punjab": 1, "Haryana": 2}))["fires"]["total"] == 3   # fills a gap
    assert with_live_fires(facts, (None, None)) is facts
