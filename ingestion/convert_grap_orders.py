"""Convert a winter's GRAP orders sheet (Excel) into static JSON for the GRAP page.

GRAP archives are closed once a season ends, so the dashboard reads JSON
rather than parsing workbooks on every page load (and the app venv doesn't
need openpyxl). One JSON per season; the GRAP page lists whichever exist.

    python ingestion/convert_grap_orders.py "data/AS - Winter GRAP Orders 01Oct2026.xlsx" --season 2025-26
    python ingestion/convert_grap_orders.py data/grap_2024_25.xlsx --season 2024-25

Needs openpyxl (requirements-dev.txt). Writes data/grap_orders_<YYYY>_<YY>.json:
    {"season": "2025-26", "source": "<xlsx name>",
     "orders": {"YYYY-MM-DD": [{<field>: <text>, ...}, ...]}}

Columns can differ between seasons. Every column is kept, keyed by a
snake_case version of its header ("AQI / Trigger" -> aqi_trigger); a few
aliases keep the names the page knows ("GRAP Stage" -> stage). The first
column whose header contains "date" is the order date: either a real Excel
date or text like "11-Nov-2025 (Clarification order)", whose bracket is kept
as date_label. Several orders can share a date, so each date maps to a list
in sheet order. Cell text is copied verbatim apart from surrounding whitespace.
"""
import argparse
import json
import re
from datetime import datetime
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
ALIASES = {"grap_stage": "stage", "stage_of_grap": "stage", "sr_no_": "sr_no", "s_no": "sr_no"}


def slug(header):
    key = re.sub(r"[^0-9a-z]+", "_", str(header).strip().lower()).strip("_")
    return ALIASES.get(key, key)


def parse_order_date(value):
    """Returns (date, note)."""
    if isinstance(value, datetime):
        return value.date(), ""
    text = str(value).strip()
    for pattern, fmt in ((r"\d{1,2}-[A-Za-z]{3}-\d{4}", "%d-%b-%Y"), (r"\d{1,2}[./]\d{1,2}[./]\d{4}", None),
                         (r"\d{4}-\d{2}-\d{2}", "%Y-%m-%d")):
        m = re.match(rf"({pattern})\s*(?:\((.*)\))?", text)
        if m:
            raw = m.group(1)
            day = (datetime.strptime(raw.replace("/", "."), "%d.%m.%Y") if fmt is None
                   else datetime.strptime(raw, fmt)).date()
            return day, (m.group(2) or "").strip()
    raise ValueError(f"Unrecognised order date: {text!r}")


def convert(src, season):
    ws = openpyxl.load_workbook(src, read_only=True, data_only=True).active
    rows = ws.iter_rows(values_only=True)
    header = list(next(rows))
    cols = [(i, slug(h)) for i, h in enumerate(header) if h is not None and str(h).strip()]
    date_idx = next(i for i, h in cols if "date" in h)

    orders = {}
    for row in rows:
        if date_idx >= len(row) or row[date_idx] is None:
            continue
        day, note = parse_order_date(row[date_idx])
        rec = {}
        for i, key in cols:
            if i == date_idx:
                continue
            val = row[i] if i < len(row) else None
            rec[key] = "" if val is None else str(val).strip()
        if rec.get("sr_no"):
            try:
                rec["sr_no"] = int(float(rec["sr_no"]))
            except ValueError:
                pass
        rec["date_label"] = note
        orders.setdefault(day.isoformat(), []).append(rec)

    return {"season": season, "source": Path(src).name, "orders": dict(sorted(orders.items()))}


def out_path(season):
    return ROOT / "data" / f"grap_orders_{season.replace('-', '_')}.json"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("xlsx", type=Path)
    ap.add_argument("--season", required=True, help='e.g. "2025-26"')
    args = ap.parse_args()
    if not re.fullmatch(r"\d{4}-\d{2}", args.season):
        ap.error("--season must look like 2025-26")
    payload = convert(args.xlsx, args.season)
    out = out_path(args.season)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    n = sum(len(v) for v in payload["orders"].values())
    print(f"Wrote {n} orders on {len(payload['orders'])} dates -> {out.relative_to(ROOT)}")
    print("data/ is git-ignored: commit it with  git add -f", out.relative_to(ROOT))
