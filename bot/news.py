"""Yangiliklarni RSS lentalardan olish."""

import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import requests

from .config import NEWS_FEEDS

MEDIA = "{http://search.yahoo.com/mrss/}"


def parse_rss(xml_text):
    root = ET.fromstring(xml_text)
    out = []
    for item in root.iter("item"):
        pub = item.findtext("pubDate")
        if not pub:
            continue
        thumb = item.find(f"{MEDIA}thumbnail")
        out.append({
            "headline": (item.findtext("title") or "").strip(),
            "description": (item.findtext("description") or "").strip(),
            "published": parsedate_to_datetime(pub),
            "url": (item.findtext("link") or "").strip(),
            "image": thumb.get("url", "") if thumb is not None else "",
        })
    return out


def latest():
    items = []
    for url in NEWS_FEEDS:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        items += parse_rss(r.text)
    return items
