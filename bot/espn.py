"""ESPN'ning bepul (kalitsiz) API'sidan o'yinlar va yangiliklarni olish."""

from datetime import date, datetime

import requests

from .config import ESPN_BASE, TZ

HEADERS = {"User-Agent": "Mozilla/5.0 (futbol-bot)"}


def _get(url, params=None):
    r = requests.get(url, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.json()


def parse_event(ev):
    """ESPN event'ini oddiy dict'ga aylantiradi."""
    comp = ev["competitions"][0]
    teams = {c["homeAway"]: c for c in comp["competitors"]}
    status = ev.get("status") or comp.get("status") or {}
    stype = status.get("type", {})
    kickoff = datetime.fromisoformat(ev["date"].replace("Z", "+00:00")).astimezone(TZ)
    return {
        "id": ev.get("id"),
        "home": teams["home"]["team"].get("shortDisplayName") or teams["home"]["team"]["displayName"],
        "away": teams["away"]["team"].get("shortDisplayName") or teams["away"]["team"]["displayName"],
        "home_score": teams["home"].get("score"),
        "away_score": teams["away"].get("score"),
        "kickoff": kickoff,
        "state": stype.get("state", "pre"),  # pre / in / post
        "completed": bool(stype.get("completed")),
        "status_text": stype.get("shortDetail", ""),
        "venue": (comp.get("venue") or {}).get("fullName", ""),
    }


def fixtures(slug, day: date):
    """Berilgan kun (Toshkent vaqti) uchun ligadagi o'yinlar.

    ESPN sanani UTC bo'yicha oladi, shuning uchun ikki kunni olib,
    Toshkent vaqti bo'yicha filtrlaymiz.
    """
    from datetime import timedelta

    events = {}
    for d in (day - timedelta(days=1), day):
        data = _get(f"{ESPN_BASE}/{slug}/scoreboard", {"dates": d.strftime("%Y%m%d")})
        for ev in data.get("events", []):
            try:
                m = parse_event(ev)
            except (KeyError, IndexError, ValueError):
                continue
            if m["kickoff"].date() == day:
                events[m["id"]] = m
    return sorted(events.values(), key=lambda m: m["kickoff"])


def news(slug):
    data = _get(f"{ESPN_BASE}/{slug}/news")
    out = []
    for a in data.get("articles", []):
        published = a.get("published") or a.get("lastModified")
        if not published:
            continue
        out.append({
            "headline": a.get("headline", ""),
            "description": a.get("description", ""),
            "published": datetime.fromisoformat(published.replace("Z", "+00:00")),
            "url": ((a.get("links") or {}).get("web") or {}).get("href", ""),
            "image": ((a.get("images") or [{}])[0]).get("url", ""),
        })
    return out
