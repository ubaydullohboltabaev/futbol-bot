"""API-Football (api-sports.io) orqali o'yinlar.

Bir kunlik barcha o'yinlar bitta so'rov bilan olinadi, keyin bizning
ligalar bo'yicha filtrlanadi. Bepul tarif: kuniga 100 so'rov.
"""

from datetime import date, datetime

import requests

from .config import API_FOOTBALL_BASE, API_FOOTBALL_KEY, TZ

FINISHED = {"FT", "AET", "PEN"}
LIVE = {"1H", "HT", "2H", "ET", "BT", "P", "INT", "LIVE"}


class ApiError(RuntimeError):
    pass


def _get(path, params):
    if not API_FOOTBALL_KEY:
        raise ApiError("API_FOOTBALL_KEY sozlanmagan")
    r = requests.get(f"{API_FOOTBALL_BASE}/{path}", params=params,
                     headers={"x-apisports-key": API_FOOTBALL_KEY}, timeout=30)
    r.raise_for_status()
    data = r.json()
    errors = data.get("errors")
    if errors:  # API xatoni 200 bilan, "errors" maydonida qaytaradi
        raise ApiError(f"API-Football xatosi: {errors}")
    return data


def parse_fixture(item):
    fx, teams, goals = item["fixture"], item["teams"], item.get("goals") or {}
    status = (fx.get("status") or {}).get("short", "NS")
    return {
        "id": fx.get("id"),
        "league_id": item["league"]["id"],
        "home": teams["home"]["name"],
        "away": teams["away"]["name"],
        "home_score": goals.get("home"),
        "away_score": goals.get("away"),
        "kickoff": datetime.fromisoformat(fx["date"]).astimezone(TZ),
        "status": status,
        "completed": status in FINISHED,
        "live": status in LIVE,
        "venue": (fx.get("venue") or {}).get("name") or "",
    }


def fixtures_by_league(day: date, league_ids):
    """{league_id: [match, ...]} — berilgan kun (Toshkent vaqti) uchun."""
    data = _get("fixtures", {"date": day.isoformat(), "timezone": "Asia/Tashkent"})
    wanted = set(league_ids)
    out = {i: [] for i in league_ids}
    for item in data.get("response", []):
        try:
            m = parse_fixture(item)
        except (KeyError, TypeError, ValueError):
            continue
        if m["league_id"] in wanted:
            out[m["league_id"]].append(m)
    for matches in out.values():
        matches.sort(key=lambda m: m["kickoff"])
    return out
