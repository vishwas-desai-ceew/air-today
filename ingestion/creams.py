"""Paddy residue burning events from the ICAR-IARI CREAMS Lab daily bulletin.

CREAMS (Consortium for Research on Agroecosystem Monitoring and Modeling from
Space, Division of Agricultural Physics, ICAR-IARI) publishes one PDF per day
during the kharif season, listed at CREAMS_PAGE_URL. It counts paddy residue
burning events under the "Standard Protocol for Estimation of Crop Residue
Burning Fire Events using Satellite Data", for Punjab, Haryana, Uttar Pradesh,
Delhi, Rajasthan, Madhya Pradesh and Uttarakhand.

Each bulletin covers that same day's fires ("Events Date" = "Issue Date") and
usually goes up between 5 and 9 pm IST; a few go up the next day. Every
bulletin repeats the whole season to date for 2020 onwards, so one download
is enough to rebuild the history, and a missed day corrects itself.

Writes:
    data/creams_fires.csv        date, state, events      (pages "State-wise and date-wise")
    data/creams_fire_events.csv  one row per fire          (pages "Details of ... events in <state>")
    data/creams_bulletin.json    bulletin number, dates, URL, highlights text

    python ingestion/creams.py            # newest bulletin (skipped if unchanged)
    python ingestion/creams.py --force    # re-download and re-parse it anyway
"""
import argparse
import io
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.logging_config import get_logger
from config.settings import (
    CREAMS_BULLETIN_JSON, CREAMS_EVENTS_CSV, CREAMS_FIRES_CSV, CREAMS_PAGE_URL, HTTP_HEADERS, IST,
)
from ingestion.json_store import read_json, write_json_atomic

logger = get_logger(__name__)

STATES = ["Punjab", "Haryana", "Uttar Pradesh", "Delhi", "Rajasthan", "Madhya Pradesh", "Uttarakhand"]
FIRST_YEAR = 2020  # the date-wise tables have one column per year from 2020 to the season's year
DAILY_COLUMNS = ["date", "state", "events"]
EVENT_COLUMNS = ["date", "state", "district", "tehsil", "satellite", "latitude", "longitude",
                 "acq_time", "day_night", "frp_w_m2"]
LINK_RE = re.compile(r"(\d+)\.RiceResidueFireBulletin_(\d{1,2}[A-Za-z]{3})_(\d{4})_ICAR\.pdf$")
DAY_RE = re.compile(r"\d{2}-[A-Z][a-z]{2}")
EVENT_HEADING_RE = re.compile(r"Details of paddy residue burning events in (.+?) on (\d{2}-[A-Za-z]{3}-\d{4})")
TIME_RE = re.compile(r"\d{1,2}:\d{2}(:\d{2})?")
NUM_RE = re.compile(r"-?\d+(\.\d+)?")


# ------------------------------------------------------------------ listing --
def list_bulletins(html: str, base_url: str = CREAMS_PAGE_URL) -> list[dict]:
    """Every rice residue bulletin linked on the CREAMS page, oldest first:
    {number, date, url}. Wheat-season and other PDFs are ignored."""
    from bs4 import BeautifulSoup

    out = {}
    for a in BeautifulSoup(html, "html.parser").find_all("a", href=True):
        m = LINK_RE.search(a["href"])
        if not m:
            continue
        day = datetime.strptime(f"{m.group(2)}{m.group(3)}", "%d%b%Y").date()
        out[(day, int(m.group(1)))] = {"number": int(m.group(1)), "date": day,
                                       "url": urljoin(base_url, a["href"])}
    return [out[k] for k in sorted(out)]


# ------------------------------------------------------------------ parsing --
def _cells(row) -> list[str]:
    """Non-empty cells of a pdfplumber table row. The date-wise tables come out
    with blank spacer cells between the numbers."""
    return [c.strip() for c in row if c and c.strip()]


def parse_daily_rows(rows, season_year: int) -> list[tuple]:
    """(date, state, events) from the "State-wise and date-wise" tables.

    `rows` are pdfplumber table rows in page order. A row holding only state
    names sets which states the following date rows cover (three per page,
    one on the Uttarakhand page); each date row then has seven numbers per
    state, one per year from 2020."""
    years = list(range(FIRST_YEAR, season_year + 1))
    out, states = [], None
    for row in rows:
        r = _cells(row)
        if not r:
            continue
        if all(c in STATES for c in r):
            states = r
            continue
        if states and DAY_RE.fullmatch(r[0]) and all(c.isdigit() for c in r[1:]):
            nums = [int(c) for c in r[1:]]
            if len(nums) != len(years) * len(states):
                logger.warning("CREAMS row %s has %d numbers, expected %d; skipped", r[0], len(nums),
                               len(years) * len(states))
                continue
            for k, state in enumerate(states):
                for year, n in zip(years, nums[k * len(years):(k + 1) * len(years)]):
                    day = datetime.strptime(f"{r[0]}-{year}", "%d-%b-%Y").date()
                    out.append((day, state, n))
    return out


def parse_event_rows(pages) -> list[dict]:
    """One dict per fire from the "Details of paddy residue burning events in
    <state> on <date>" tables. `pages` is [(page_text, table_rows), ...].

    A state's list starts at S. No. 1 under its heading and can begin part-way
    down a page that ends the previous state's list, so the state is taken from
    the headings in the order they appear, moving on at each S. No. 1."""
    headings, events, current = [], [], None
    for text, rows in pages:
        headings += EVENT_HEADING_RE.findall(text or "")
        for row in rows:
            r = [(c or "").strip() for c in row]
            if len(r) != 9 or not r[0].isdigit() or not TIME_RE.fullmatch(r[6]):
                continue
            if r[0] == "1" or current is None:
                if not headings:
                    logger.warning("CREAMS fire row before any state heading; skipped")
                    continue
                state, day = headings.pop(0)
                current = (state.strip(), datetime.strptime(day, "%d-%b-%Y").date())
            try:
                lat, lon, frp = float(r[4]), float(r[5]), float(r[8]) if NUM_RE.fullmatch(r[8]) else None
            except ValueError:
                logger.warning("CREAMS fire row with bad coordinates skipped: %s", r)
                continue
            events.append({"date": current[1], "state": current[0], "district": r[1].title(),
                           "tehsil": r[2].title(), "satellite": r[3], "latitude": lat, "longitude": lon,
                           "acq_time": r[6], "day_night": r[7], "frp_w_m2": frp})
    return events


def parse_highlights(text: str) -> dict:
    """The day's headline paragraph (page 2) as sentences, plus the bulletin
    number and dates from the cover page text."""
    out = {}
    for key, pat in (("bulletin_no", r"Bulletin No:\s*(\d+)"), ("events_date", r"Events Date:\s*(\d{2}-[A-Za-z]{3}-\d{4})"),
                     ("issue_date", r"Issue Date:\s*(\d{2}-[A-Za-z]{3}-\d{4})")):
        m = re.search(pat, text)
        if m:
            out[key] = int(m.group(1)) if key == "bulletin_no" else datetime.strptime(m.group(1), "%d-%b-%Y").date().isoformat()
    m = re.search(r"Highlights For \S+\s*\n(.*?)\n\s*Temporal distribution", text, re.S)
    if m:
        para = re.sub(r"\s+", " ", m.group(1)).strip()
        out["highlights"] = [s for s in re.split(r"(?<=\.)\s+(?=[A-Z])", para) if s]
    return out


def parse_bulletin(pdf_bytes: bytes, season_year: int) -> dict:
    """{daily: DataFrame, events: DataFrame, meta: dict} from one bulletin PDF."""
    import pdfplumber

    # Every page goes to both parsers: each only acts on rows of its own shape.
    pages, cover = [], ""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            if i < 2:
                cover += text + "\n"
            pages.append((text, [row for t in page.extract_tables() for row in t]))
    daily_rows = [row for _, rows in pages for row in rows]
    event_pages = pages
    daily = pd.DataFrame(parse_daily_rows(daily_rows, season_year), columns=DAILY_COLUMNS).drop_duplicates(["date", "state"])
    events = pd.DataFrame(parse_event_rows(event_pages), columns=EVENT_COLUMNS)
    meta = parse_highlights(cover)
    if daily.empty:
        raise ValueError("no state-wise date-wise table found in the CREAMS bulletin (layout changed?)")
    check_events(daily, events)
    return {"daily": daily, "events": events, "meta": meta}


def check_events(daily: pd.DataFrame, events: pd.DataFrame) -> list[str]:
    """Warn when the per-fire list doesn't add up to the date-wise count."""
    problems = []
    if events.empty:
        return problems
    got = events.groupby(["date", "state"]).size()
    for (day, state), n in got.items():
        want = daily.loc[(daily["date"] == day) & (daily["state"] == state), "events"]
        if not want.empty and int(want.iloc[0]) != n:
            problems.append(f"{state} {day}: {n} fires listed, table says {int(want.iloc[0])}")
    for p in problems:
        logger.warning("CREAMS: %s", p)
    return problems


# ------------------------------------------------------------------ storage --
def read_daily(path=CREAMS_FIRES_CSV) -> pd.DataFrame:
    try:
        df = pd.read_csv(path)
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return pd.DataFrame(columns=DAILY_COLUMNS)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


def read_events(path=CREAMS_EVENTS_CSV) -> pd.DataFrame:
    try:
        df = pd.read_csv(path)
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return pd.DataFrame(columns=EVENT_COLUMNS)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df


def _write_csv(df: pd.DataFrame, path: Path) -> None:
    tmp = path.with_suffix(".csv.tmp")
    df.to_csv(tmp, index=False, encoding="utf-8")
    tmp.replace(path)


def save(parsed: dict, daily_path=CREAMS_FIRES_CSV, events_path=CREAMS_EVENTS_CSV) -> None:
    """Upsert: the new bulletin's (date, state) counts and fire lists replace
    any older ones; days it doesn't cover (e.g. late November of past years,
    before the season reaches them) are kept."""
    new = parsed["daily"]
    old = read_daily(daily_path)
    keys = set(zip(new["date"], new["state"]))
    old = old[[k not in keys for k in zip(old["date"], old["state"])]]
    daily = (pd.concat([old, new], ignore_index=True) if not old.empty else new).sort_values(["date", "state"])
    _write_csv(daily[DAILY_COLUMNS], daily_path)

    ev = parsed["events"]
    if not ev.empty:
        old_ev = read_events(events_path)
        old_ev = old_ev[~old_ev["date"].isin(set(ev["date"]))]
        events = (pd.concat([old_ev, ev], ignore_index=True) if not old_ev.empty else ev).sort_values(["date", "state", "district"])
        _write_csv(events[EVENT_COLUMNS], events_path)


def headline_counts(day, states, path=CREAMS_FIRES_CSV):
    """{state: events} for `day`, or None when no bulletin has covered `day`
    yet (so a missing day is never shown as 0)."""
    df = read_daily(path)
    rows = df[df["date"] == day].set_index("state")["events"]
    if any(s not in rows.index for s in states):
        return None
    return {s: int(rows[s]) for s in states}


# ---------------------------------------------------------------------- run --
def run(force: bool = False) -> dict:
    """Fetch the newest bulletin listed on the CREAMS page; skip the download
    when it is the one already stored and the server copy hasn't changed."""
    r = requests.get(CREAMS_PAGE_URL, headers=HTTP_HEADERS, timeout=60)
    r.raise_for_status()
    bulletins = list_bulletins(r.text)
    if not bulletins:
        raise ValueError("no rice residue burning bulletin linked on the CREAMS page (layout changed?)")
    latest = bulletins[-1]
    head = requests.head(latest["url"], headers=HTTP_HEADERS, timeout=60, allow_redirects=True)
    last_modified = head.headers.get("Last-Modified")
    stored = read_json(CREAMS_BULLETIN_JSON)
    if (not force and stored.get("url") == latest["url"] and stored.get("last_modified") == last_modified
            and CREAMS_FIRES_CSV.exists()):
        logger.info("CREAMS bulletin %s already stored", latest["number"])
        return {"bulletin": latest["number"], "date": latest["date"].isoformat(), "skipped": "unchanged"}

    pdf = requests.get(latest["url"], headers=HTTP_HEADERS, timeout=180)
    pdf.raise_for_status()
    if not pdf.content.startswith(b"%PDF"):
        raise ValueError("CREAMS returned a non-PDF response")
    parsed = parse_bulletin(pdf.content, latest["date"].year)
    save(parsed)
    problems = check_events(parsed["daily"], parsed["events"])
    meta = {
        "number": latest["number"],
        "events_date": parsed["meta"].get("events_date", latest["date"].isoformat()),
        "issue_date": parsed["meta"].get("issue_date"),
        "url": latest["url"],
        "last_modified": last_modified,
        "highlights": parsed["meta"].get("highlights", []),
        "fires_listed": int(len(parsed["events"])),
        "check_problems": problems,
        "source_page": CREAMS_PAGE_URL,
        "fetched_at": datetime.now(IST).isoformat(timespec="minutes"),
    }
    write_json_atomic(CREAMS_BULLETIN_JSON, meta, indent=2, ensure_ascii=False)
    logger.info("CREAMS bulletin %s (%s): %d daily rows, %d fires", latest["number"], latest["date"],
                len(parsed["daily"]), len(parsed["events"]))
    return {"bulletin": latest["number"], "date": latest["date"].isoformat(),
            "daily_rows": int(len(parsed["daily"])), "fires": int(len(parsed["events"])),
            **({"check_problems": problems} if problems else {})}


def main():
    parser = argparse.ArgumentParser(description="Fetch the latest CREAMS paddy residue burning bulletin")
    parser.add_argument("--force", action="store_true", help="re-download even if unchanged")
    print(run(force=parser.parse_args().force))


if __name__ == "__main__":
    main()
