"""Recent Delhi air-quality headlines from three national publishers' own RSS
feeds (no aggregator, no API key), for the Recent trends page.

Each feed is the publisher's Delhi / cities section. Items are kept when the
headline mentions air quality (AQI, pollution, smog, GRAP, PM2.5, stubble);
opinion pieces are dropped. Only the headline, link, publisher and date are
shown, and every item links to the publisher's own page.
"""
import html
import re
import sys
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.settings import HTTP_HEADERS, IST
from config.logging_config import get_logger

logger = get_logger(__name__)

FEEDS = [
    ("The Hindu", "https://www.thehindu.com/news/cities/Delhi/feeder/default.rss"),
    ("Times of India", "https://timesofindia.indiatimes.com/rssfeeds/-2128839596.cms"),
    ("NDTV", "https://feeds.feedburner.com/ndtvnews-cities-news"),
]
TOPIC = re.compile(r"\b(AQI|air quality|air pollution|pollution|smog|GRAP|PM ?2\.5|stubble|farm fires?)\b", re.I)
PLACE = re.compile(r"\b(Delhi|NCR|Noida|Gurugram|Gurgaon|Ghaziabad|Faridabad)\b", re.I)
OPINION = re.compile(r"^\s*(opinion|editorial|blog)\b", re.I)


def _tag(item, name):
    m = re.search(rf"<{name}[^>]*>(.*?)</{name}>", item, re.S)
    if not m:
        return ""
    return html.unescape(re.sub(r"<!\[CDATA\[|\]\]>", "", m.group(1))).strip()


def _date(text):
    """RFC 822 (The Hindu, NDTV) or ISO 8601 (TOI) -> aware IST datetime."""
    for parse in (parsedate_to_datetime, datetime.fromisoformat):
        try:
            d = parse(text)
            return d.astimezone(IST) if d.tzinfo else d.replace(tzinfo=IST)
        except (TypeError, ValueError):
            continue
    return None


def _parse(publisher, xml):
    out = []
    for item in re.findall(r"<item>(.*?)</item>", xml, re.S):
        title, link = _tag(item, "title"), _tag(item, "link")
        if not title or not link.startswith("http") or OPINION.search(title) or not TOPIC.search(title):
            continue
        # The Hindu and TOI feeds are Delhi sections; NDTV's covers all cities
        if publisher == "NDTV" and not PLACE.search(title):
            continue
        published = _date(_tag(item, "pubDate"))
        out.append({"title": title, "link": link, "publisher": publisher, "published": published})
    return out


def fetch_aqi_news(limit=15) -> list:
    """Newest first, de-duplicated by headline. A feed that fails is skipped."""
    items = []
    for publisher, url in FEEDS:
        try:
            r = requests.get(url, headers=HTTP_HEADERS, timeout=8)
            r.raise_for_status()
            items += _parse(publisher, r.text)
        except Exception as e:
            logger.warning("News feed %s unavailable: %s", publisher, e)
    seen, unique = set(), []
    for it in sorted(items, key=lambda x: x["published"] or datetime.min.replace(tzinfo=IST), reverse=True):
        key = re.sub(r"\W+", " ", it["title"].lower()).strip()
        if key not in seen:
            seen.add(key)
            unique.append(it)
    return unique[:limit]


if __name__ == "__main__":
    for it in fetch_aqi_news():
        print(f"{it['published']:%d %b %H:%M}  {it['publisher']:<14} {it['title'][:90]}")
