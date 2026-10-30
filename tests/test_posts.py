import random
from datetime import date

from bot import football, news, posts, telegram
from bot.config import LEAGUES

ITEM = {
    "fixture": {"id": 1, "date": "2026-10-31T20:00:00+05:00",
                "status": {"short": "FT"}, "venue": {"name": "Anfield"}},
    "league": {"id": 39, "name": "Premier League"},
    "teams": {"home": {"name": "Liverpool"}, "away": {"name": "Arsenal"}},
    "goals": {"home": 4, "away": 0},
}

RSS = """<?xml version="1.0"?><rss xmlns:media="http://search.yahoo.com/mrss/"><channel>
<item><title>Salah scores</title><description>Big win</description>
<link>https://bbc.co.uk/x</link><pubDate>Fri, 30 Oct 2026 09:00:00 GMT</pubDate>
<media:thumbnail url="https://img/x.jpg"/></item></channel></rss>"""


def test_parse_fixture():
    m = football.parse_fixture(ITEM)
    assert m["kickoff"].hour == 20 and m["home"] == "Liverpool" and m["completed"]
    assert m["league_id"] == 39


def test_fixtures_by_league_filters(monkeypatch):
    other = {**ITEM, "league": {"id": 9999}}
    monkeypatch.setattr(football, "_get", lambda *a: {"response": [ITEM, other]})
    out = football.fixtures_by_league(date(2026, 10, 31), [39, 140])
    assert len(out[39]) == 1 and out[140] == []


def test_api_errors_raise(monkeypatch):
    class R:
        headers = {}
        def raise_for_status(self): pass
        def json(self): return {"errors": {"plan": "Free plans do not have access"}, "response": []}
    monkeypatch.setattr(football, "API_FOOTBALL_KEY", "k")
    monkeypatch.setattr(football.requests, "get", lambda *a, **k: R())
    try:
        football._get("fixtures", {})
        assert False
    except football.ApiError as e:
        assert "Free plans" in str(e)


def test_fixtures_post():
    m = football.parse_fixture(ITEM)
    text = posts.fixtures_post(date(2026, 10, 31), [(LEAGUES[0], [m])], rng=random.Random(1))
    assert "20:00 | Liverpool — Arsenal" in text and "Setanta" in text and "Shanba" in text


def test_fixtures_post_empty():
    assert "o'yin yo'q" in posts.fixtures_post(date(2026, 10, 31), [], rng=random.Random(1))


def test_results_post_big_win_joke():
    m = football.parse_fixture(ITEM)
    text = posts.results_post(date(2026, 10, 31), [(LEAGUES[0], [m])], rng=random.Random(1))
    assert "4:0" in text and any(j in text for j in posts.BIG_WIN_JOKES)


def test_rss():
    a = news.parse_rss(RSS)[0]
    assert a["headline"] == "Salah scores" and a["image"] == "https://img/x.jpg"
    assert a["published"].year == 2026


def test_html_escaped():
    assert posts.news_post("A<b>", "x & y").count("&lt;b&gt;") == 1


def test_split_long_text():
    parts = telegram.split("\n\n".join(["x" * 1000] * 10))
    assert all(len(p) <= telegram.LIMIT for p in parts) and len(parts) > 1
