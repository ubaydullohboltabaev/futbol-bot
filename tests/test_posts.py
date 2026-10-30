import random
from datetime import date, datetime

from bot import posts, telegram
from bot.config import LEAGUES, TZ
from bot.espn import parse_event

EVENT = {
    "id": "1", "date": "2026-10-31T15:00Z",
    "status": {"type": {"state": "post", "completed": True, "shortDetail": "FT"}},
    "competitions": [{"venue": {"fullName": "Anfield"}, "competitors": [
        {"homeAway": "home", "score": "4", "team": {"displayName": "Liverpool", "shortDisplayName": "Liverpool"}},
        {"homeAway": "away", "score": "0", "team": {"displayName": "Arsenal", "shortDisplayName": "Arsenal"}},
    ]}],
}


def test_parse_event_converts_to_tashkent():
    m = parse_event(EVENT)
    assert m["kickoff"].hour == 20 and m["home"] == "Liverpool" and m["completed"]


def test_fixtures_post():
    m = parse_event(EVENT)
    text = posts.fixtures_post(date(2026, 10, 31), [(LEAGUES[0], [m])], rng=random.Random(1))
    assert "20:00 | Liverpool — Arsenal" in text and "Setanta" in text and "Shanba" in text


def test_fixtures_post_empty():
    assert "o'yin yo'q" in posts.fixtures_post(date(2026, 10, 31), [], rng=random.Random(1))


def test_results_post_big_win_joke():
    m = parse_event(EVENT)
    text = posts.results_post(date(2026, 10, 31), [(LEAGUES[0], [m])], rng=random.Random(1))
    assert "4:0" in text and any(j in text for j in posts.BIG_WIN_JOKES)


def test_html_escaped():
    assert posts.news_post(LEAGUES[0], "A<b>", "x & y").count("&lt;b&gt;") == 1


def test_split_long_text():
    parts = telegram.split("\n\n".join(["x" * 1000] * 10))
    assert all(len(p) <= telegram.LIMIT for p in parts) and len(parts) > 1
