"""Collect CAQM's GRAP orders into one JSON per winter season.

Source: the list behind CAQM's GRAP Orders page
(https://caqm.nic.in/landingpage/pages/grap/grap-orders), which the site
loads from a public JSON API. Each order's PDF path comes from CAQM's
document API. Both are read-only GETs, made once a day.

    python ingestion/grap_orders.py                    # current season (and any later ones)
    python ingestion/grap_orders.py --from-season 2025-26
    python ingestion/grap_orders.py --season 2025-26 --import-legacy data/grap_orders_2025_26.json

Writes data/grap/grap_<YYYY>_<YY>.json (schema_version 2), one per season.
A season runs 1 October to 30 September, so Stage I orders in spring belong
to the winter before them:

    {
      "schema_version": 2,
      "season": "2026-27",
      "region": "Delhi-NCR",
      "updated_at": "2026-11-08T16:20:00+05:30",
      "source": {"name": "CAQM, GRAP orders", "url": "..."},
      "stage_at_start": 0,          # highest stage in force on 1 October
      "orders": [                   # oldest first; same-day orders by stage
        {
          "id": "caqm-21668",
          "date": "2026-10-21",
          "action": "invoke",       # invoke | revoke | other
          "stages": [1],            # GRAP stages the order invokes/revokes
          "headline": "Stage I invoked",
          "title": "<CAQM's title, verbatim>",
          "pdf_url": "https://caqm.nic.in/FileUploadDomain/...pdf",
          "caqm_document_id": 21668,
          "source": "caqm",         # caqm | team_archive
          "details": {              # optional, from the team's archive sheet
            "aqi_trigger": "...", "aqi_category": "...", "key_decision": "...", "reason": "..."
          }
        }
      ]
    }

Stages are cumulative: invoking Stage N puts Stages I..N in force, and
revoking Stage N leaves Stages I..N-1. The page derives each day's stages
from `stage_at_start` and the orders, so the file only records what CAQM
issued. Re-running keeps `details` already in the file (matched by id).
"""
import argparse
import re
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import GRAP_DIR, IST
from config.logging_config import get_logger
from ingestion.json_store import read_json, write_json_atomic

logger = get_logger(__name__)

BASE = "https://caqm.nic.in"
LIST_URL = f"{BASE}/website/api/Home/GetLatestDocumentPolicy?category=10&subcategory=18"
DOC_URL = f"{BASE}/DMSAPI/api/Document/GetAllDocuments?documentId={{}}"
FILE_URL = f"{BASE}/FileUploadDomain/{{}}"
PAGE_URL = f"{BASE}/landingpage/pages/grap/grap-orders"
HEADERS = {"User-Agent": "AirToday-dashboard/1.0 (air quality research dashboard)"}
SCHEMA_VERSION = 2
ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "ILL": 3, "1": 1, "2": 2, "3": 3, "4": 4}
ROMAN_OUT = {1: "I", 2: "II", 3: "III", 4: "IV"}


# ------------------------------------------------------------ parsing --
def season_of(day):
    start = day.year if day.month >= 10 else day.year - 1
    return f"{start}-{str(start + 1)[2:]}"


def season_bounds(season):
    start = int(season[:4])
    return date(start, 10, 1), date(start + 1, 9, 30)


def title_date(title):
    """'Order dated 02.11. 2026 - ...' -> date(2026, 11, 2), else None."""
    m = re.search(r"(?:dated?|dt\.?)\s+(\d{1,2})\s*\.\s*(\d{1,2})\s*\.\s*(\d{4})", title, re.I)
    if not m:
        return None
    d, mth, y = map(int, m.groups())
    try:
        return date(y, mth, d)
    except ValueError:
        return None


_STAGE = r"stage\s*[-–]?\s*(IV|III|Ill|II|I|[1-4])\b"


def classify(text):
    """(action, stages) from an order title or the team sheet's stage text.

    invoke: "Implementation/Invocation of actions under Stage-III ..."
    revoke: "Revocation of actions under Stage-III ... and intensifying ..."
    Anything else (clarifications, schedule revisions, standalone directions)
    is "other", even if it mentions a stage.
    """
    t = " ".join(str(text).split())
    low = t.lower()
    head = re.sub(r"^(order|letter)\s+(?:dated?|dt\.?)\s+[\d.\s]+\s*[-–:]?\s*", "", low).strip()
    if head.startswith(("clarification", "withdrawal")) or "corrigendum" in low or "no new stage" in low or "no stage invoked" in low \
            or "not a grap-stage" in low:
        return "other", []
    if re.search(r"\b(revocation|revoked|revoking)\b", low):
        action = "revoke"
        # "...revocation of Stage III and intensifying actions under Stage II" - only the first part counts;
        # the team sheet writes "Stage III revoked; Stages I and II remain".
        part = re.split(r"intensif|;|remain", t, flags=re.I)[0]
    elif re.search(r"\b(implementation|invocation|invoked|invoking)\b(\s+of)?\s+(the\s+)?actions?\s+under|"
                   r"\bstage\s*[-–]?\s*(iv|iii|ii|i)\s+invoked", low):
        action = "invoke"
        part = re.split(r"\(in addition|already in force", t, flags=re.I)[0]
    else:
        return "other", []
    stages = [ROMAN[s.upper()] for s in re.findall(_STAGE, part, re.I)]
    stages += [ROMAN[s.upper()] for s in re.findall(r"(?:&|and)\s*(IV|III|II)\b", part)]
    stages = sorted(set(stages))
    return (action, stages) if stages else ("other", [])


def headline(action, stages, title):
    if "corrigendum" in title.lower():
        named = sorted({ROMAN[x.upper()] for x in re.findall(_STAGE, title, re.I)})
        return "Corrigendum" + (f" to the Stage {' & '.join(ROMAN_OUT[n] for n in named)} order" if named else "")
    if action in ("invoke", "revoke") and stages:
        names = " & ".join(ROMAN_OUT[s] for s in stages)
        word = "invoked" if action == "invoke" else "revoked"
        return f"Stage{'s' if len(stages) > 1 else ''} {names} {word}"
    short = re.sub(r"^(order|letter)\s+(?:dated?|dt\.?)\s+[\d.\s]+\s*[-–:]?\s*", "", " ".join(title.split()), flags=re.I)
    return (short[:1].upper() + short[1:])[:90] if short else "Order"


def apply_order(level, action, stages):
    """Highest stage in force after an order (stages are cumulative)."""
    if action == "invoke" and stages:
        return max(level, max(stages))
    if action == "revoke" and stages:
        return min(level, min(stages) - 1)
    return level


def sort_key(o):
    # Same-day orders: invocations in ascending stage, then revocations, then others.
    rank = {"invoke": 0, "revoke": 1, "other": 2}[o["action"]]
    return (o["date"], rank, max(o["stages"] or [0]))


# ------------------------------------------------------------ fetching --
def _get_json(session, url):
    r = session.get(url, headers=HEADERS, timeout=40)
    r.raise_for_status()
    return r.json()


def fetch_list(session):
    data = _get_json(session, LIST_URL).get("data") or []
    if not data:
        raise RuntimeError("CAQM GRAP order list came back empty")
    return data


def fetch_document(session, doc_id):
    """(issue date or None, absolute PDF URL or None) for one CAQM document."""
    rows = _get_json(session, DOC_URL.format(doc_id)).get("data") or []
    if not rows:
        return None, None
    row = rows[0]
    issued = None
    if row.get("documentIssueDate"):
        try:
            issued = date.fromisoformat(str(row["documentIssueDate"])[:10])
        except ValueError:
            pass
    path = row.get("documentPath")
    return issued, (FILE_URL.format(quote(path)) if path else None)


# ------------------------------------------------------------ building --
def out_path(season):
    return GRAP_DIR / f"grap_{season.replace('-', '_')}.json"


def build(listing, session=None, seasons=None, existing=None):
    """{season: payload} for the requested seasons. `existing` maps season ->
    current payload, to reuse PDF links and team details already fetched."""
    existing = existing or {}
    known = {o["id"]: o for p in existing.values() for o in p.get("orders", [])}
    orders, seen = [], set()
    for row in listing:
        doc_id = row.get("documentId")
        title = " ".join(str(row.get("title") or "").split())
        if not doc_id or not title:
            continue
        oid = f"caqm-{doc_id}"
        prev = known.get(oid, {})
        day = title_date(title) or (date.fromisoformat(prev["date"]) if prev.get("date") else None)
        pdf = prev.get("pdf_url")
        needs_doc = day is None or (pdf is None and (seasons is None or season_of(day) in seasons))
        if needs_doc and session is not None:
            try:
                issued, pdf = fetch_document(session, doc_id)
                day = day or issued
            except requests.RequestException as e:
                logger.warning("CAQM document %s: %s", doc_id, e)
        if day is None:
            stamp = str(row.get("publishDate") or row.get("updatedDatetimeString") or "")[:10]
            day = date.fromisoformat(stamp) if stamp else None
        if day is None:
            logger.warning("Skipping undated CAQM order %s: %s", doc_id, title)
            continue
        if (day, title.lower()) in seen:  # CAQM sometimes lists the same order twice
            continue
        seen.add((day, title.lower()))
        action, stages = classify(title)
        rec = {"id": oid, "date": day.isoformat(), "action": action, "stages": stages,
               "headline": headline(action, stages, title), "title": title, "pdf_url": pdf,
               "caqm_document_id": doc_id, "source": "caqm"}
        if prev.get("details"):
            rec["details"] = prev["details"]
        orders.append(rec)

    # Team-archive records with no CAQM counterpart are kept as they are.
    caqm_ids = {o["id"] for o in orders}
    orders += [o for o in known.values() if o.get("source") == "team_archive" and o["id"] not in caqm_ids]
    orders.sort(key=sort_key)

    wanted = seasons or sorted({season_of(date.fromisoformat(o["date"])) for o in orders})
    now = datetime.now(IST).isoformat(timespec="seconds")
    out = {}
    for season in wanted:
        start, end = season_bounds(season)
        level = 0
        for o in orders:  # everything before 1 October sets the stage carried into the season
            if date.fromisoformat(o["date"]) >= start:
                break
            level = apply_order(level, o["action"], o["stages"])
        out[season] = {
            "schema_version": SCHEMA_VERSION,
            "season": season,
            "region": "Delhi-NCR",
            "updated_at": now,
            "source": {"name": "CAQM, GRAP orders", "url": PAGE_URL},
            "stage_at_start": level,
            "orders": [o for o in orders if start <= date.fromisoformat(o["date"]) <= end],
        }
    return out


def import_legacy(payload, legacy):
    """Attach the team sheet's notes (data/grap_orders_<season>.json, the old
    format written by convert_grap_orders.py) to the matching CAQM orders:
    same date, action and stages. Unmatched sheet rows become team_archive orders."""
    by_date = {}
    for o in payload["orders"]:
        by_date.setdefault(o["date"], []).append(o)
    keep = ("aqi_category", "aqi_trigger", "key_decision", "reason")
    for day, rows in legacy.get("orders", {}).items():
        for i, row in enumerate(rows):
            action, stages = classify(row.get("stage", ""))
            details = {k: row[k] for k in keep if str(row.get(k, "")).strip()}
            match = next((o for o in by_date.get(day, []) if "details" not in o
                          and o["action"] == action and o["stages"] == stages), None)
            if match is None and action == "other":
                match = next((o for o in by_date.get(day, []) if "details" not in o and o["action"] == "other"), None)
            if match is not None:
                match["details"] = details
                continue
            label = row.get("stage") or "Order"
            payload["orders"].append({
                "id": f"team-{day}-{i}", "date": day, "action": action, "stages": stages,
                "headline": headline(action, stages, label) if stages else label.split("(")[0].strip()[:90],
                "title": label, "pdf_url": None, "caqm_document_id": None,
                "source": "team_archive", "details": details,
            })
            logger.info("Legacy row %s kept as team_archive: %s", day, label)
    payload["orders"].sort(key=sort_key)
    return payload


def run(from_season=None, only_season=None, legacy=None):
    today = datetime.now(IST).date()
    first = only_season or from_season or season_of(today)
    session = requests.Session()
    listing = fetch_list(session)
    # Seasons from `first` to the current one.
    seasons = [first] if only_season else []
    if not only_season:
        y = int(first[:4])
        while y <= int(season_of(today)[:4]):
            seasons.append(f"{y}-{str(y + 1)[2:]}")
            y += 1
    existing = {s: read_json(out_path(s)) for s in seasons if out_path(s).exists()}
    payloads = build(listing, session=session, seasons=seasons, existing=existing)
    GRAP_DIR.mkdir(parents=True, exist_ok=True)
    written = {}
    for season, payload in payloads.items():
        if legacy and season == only_season:
            payload = import_legacy(payload, read_json(legacy))
        write_json_atomic(out_path(season), payload, ensure_ascii=False, indent=2)
        written[season] = len(payload["orders"])
        logger.info("GRAP %s: %d orders -> %s", season, len(payload["orders"]), out_path(season))
    return {"orders": written}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--from-season", help='first season to write, e.g. "2025-26" (default: current)')
    g.add_argument("--season", help="write just this season")
    ap.add_argument("--import-legacy", type=Path, help="old-format team JSON to merge (needs --season)")
    args = ap.parse_args()
    for s in (args.from_season, args.season):
        if s and not re.fullmatch(r"\d{4}-\d{2}", s):
            ap.error("seasons look like 2025-26")
    if args.import_legacy and not args.season:
        ap.error("--import-legacy needs --season")
    print(run(from_season=args.from_season, only_season=args.season, legacy=args.import_legacy))


if __name__ == "__main__":
    main()
