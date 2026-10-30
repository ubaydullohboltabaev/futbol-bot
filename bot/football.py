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


# Oxirgi javobdagi kunlik qolgan so'rovlar soni (limitni tejash uchun)
quota = {"remaining": None}


def _get(path, params):
    if not API_FOOTBALL_KEY:
        raise ApiError("API_FOOTBALL_KEY sozlanmagan")
    r = requests.get(f"{API_FOOTBALL_BASE}/{path}", params=params,
                     headers={"x-apisports-key": API_FOOTBALL_KEY}, timeout=30)
    r.raise_for_status()
    rem = r.headers.get("x-ratelimit-requests-remaining")
    if rem is not None and rem.lstrip("-").isdigit():
        quota["remaining"] = int(rem)
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
        "season": item["league"].get("season"),
        "round": item["league"].get("round") or "",
        "home_id": teams["home"].get("id"),
        "away_id": teams["away"].get("id"),
        "home": teams["home"]["name"],
        "away": teams["away"]["name"],
        "home_score": goals.get("home"),
        "away_score": goals.get("away"),
        "kickoff": datetime.fromisoformat(fx["date"]).astimezone(TZ),
        "status": status,
        "completed": status in FINISHED,
        "live": status in LIVE,
        "venue": (fx.get("venue") or {}).get("name") or "",
        "elapsed": (fx.get("status") or {}).get("elapsed"),
        "events": item.get("events") or [],
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


def fixtures_on(day_utc: date):
    """Berilgan UTC kunidagi barcha o'yinlar (filtrsiz)."""
    return _parse_all(_get("fixtures", {"date": day_utc.isoformat(), "timezone": "UTC"}))


def _parse_all(data):
    out = []
    for item in data.get("response", []):
        try:
            out.append(parse_fixture(item))
        except (KeyError, TypeError, ValueError):
            continue
    return out


def fixture_by_id(fid):
    """Bitta o'yin voqealari bilan (bepul tarifda "ids" yo'q, "id" bor)."""
    data = _get("fixtures", {"id": fid, "timezone": "UTC"})
    res = _parse_all(data)
    return res[0] if res else None


def live_fixtures(league_ids):
    """Hozir ketayotgan o'yinlar (bitta so'rov). Voqealar bo'lishi ham, bo'lmasligi ham mumkin."""
    data = _get("fixtures", {"live": "-".join(str(i) for i in sorted(set(league_ids))),
                             "timezone": "UTC"})
    for item in data.get("response", []):
        item.setdefault("_has_events", "events" in item)
    out = []
    for item in data.get("response", []):
        try:
            m = parse_fixture(item)
        except (KeyError, TypeError, ValueError):
            continue
        m["has_events"] = item["_has_events"]
        out.append(m)
    return out


def standings(league_id, season):
    """{team_id: o'rni} — liga jadvali (guruhlar bo'lsa, guruhdagi o'rni)."""
    data = _get("standings", {"league": league_id, "season": season})
    ranks = {}
    for entry in data.get("response", []):
        for group in (entry.get("league") or {}).get("standings") or []:
            for row in group:
                tid = (row.get("team") or {}).get("id")
                if tid is not None:
                    ranks[tid] = min(row.get("rank") or 99, ranks.get(tid, 99))
    return ranks
