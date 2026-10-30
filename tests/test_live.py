import random
from datetime import datetime, timedelta, timezone

from bot import football, live

KO = datetime(2026, 10, 31, 15, 0, tzinfo=timezone.utc)


def match(status="1H", elapsed=5, events=(), hs=0, as_=0, fid=1, league=39):
    return {"id": fid, "league_id": league, "home": "Liverpool", "away": "Arsenal",
            "home_score": hs, "away_score": as_, "kickoff": KO, "status": status,
            "completed": status in football.FINISHED, "live": True, "venue": "",
            "elapsed": elapsed, "events": list(events), "season": 2026, "round": "",
            "home_id": 40, "away_id": 42}


def goal(minute, name="Salah", detail="Normal Goal"):
    return {"time": {"elapsed": minute, "extra": None}, "team": {"name": "Liverpool"},
            "player": {"id": 1, "name": name}, "assist": {"name": "Szoboszlai"},
            "type": "Goal", "detail": detail}


def fresh():
    return {"sent": [], "status": {}}


def test_kickoff_goal_and_no_duplicates():
    st, rng = fresh(), random.Random(1)
    out = live.process(match("1H", 3), st, rng)
    assert len(out) == 1 and "BOSHLANDI" in out[0]
    out = live.process(match("1H", 12, [goal(11)], hs=1), st, rng)
    assert len(out) == 1 and "GOOOL" in out[0] and "11'" in out[0] and "<b>1:0</b>" in out[0]
    assert live.process(match("1H", 14, [goal(11)], hs=1), st, rng) == []


def test_fulltime_after_events():
    st = fresh()
    live.process(match("2H", 80), st)
    out = live.process(match("FT", 90, [goal(89)], hs=1), st)
    assert "GOOOL" in out[0] and "TUGADI" in out[-1]


def test_joining_midgame_skips_old_events():
    out = live.process(match("2H", 70, [goal(20), goal(68, "Nunez")], hs=2), fresh())
    assert len(out) == 1 and "Nunez" in out[0]


def test_red_card_and_var_and_yellow_skipped():
    evs = [
        {"time": {"elapsed": 30}, "team": {"name": "Arsenal"}, "player": {"name": "Saliba"},
         "type": "Card", "detail": "Red Card"},
        {"time": {"elapsed": 31}, "team": {"name": "Arsenal"}, "player": {"name": "Rice"},
         "type": "Card", "detail": "Yellow Card"},
        {"time": {"elapsed": 40}, "team": {"name": "Liverpool"}, "player": {"name": "Salah"},
         "type": "Var", "detail": "Goal cancelled"},
        {"time": {"elapsed": 41}, "team": {"name": "Liverpool"}, "player": {"name": "X"},
         "type": "subst", "detail": "Substitution 1"},
    ]
    st = fresh()
    live.process(match("1H", 25), st)
    out = live.process(match("1H", 42, evs), st)
    assert len(out) == 2 and "QIZIL" in out[0] and "VAR" in out[1] and "bekor" in out[1]


def test_poll_interval_uses_budget(monkeypatch):
    monkeypatch.setitem(football.quota, "remaining", 36)  # 30 so'rov ishlatsa bo'ladi
    now = KO
    iv = live.poll_interval(now, [match("1H")], now + timedelta(hours=6))
    assert iv == int(115 * 60 / 30)
    monkeypatch.setitem(football.quota, "remaining", 1000)
    assert live.poll_interval(now, [match("1H")], now + timedelta(hours=6)) == live.LIVE_MIN_INTERVAL


def test_run_loop(monkeypatch, tmp_path):
    monkeypatch.setattr(live, "LIVE_STATE_FILE", str(tmp_path / "s.json"))
    monkeypatch.setattr(live, "load_state", lambda path=None: fresh())
    monkeypatch.setattr(live, "save_state", lambda st, path=None: None)
    clock = {"t": KO - timedelta(minutes=30)}
    sent = []
    seq = [match("1H", 2), match("1H", 20, [goal(19)], hs=1), match("FT", 90, [goal(19)], hs=1)]
    other = {**match("NS", None, fid=2), "home": "Burnley", "away": "Luton", "home_id": 5, "away_id": 6}
    monkeypatch.setattr(football, "fixtures_on", lambda d: [match("NS", None), other])
    monkeypatch.setattr(football, "standings", lambda lid, season: {40: 1, 5: 15, 6: 20})
    monkeypatch.setattr(football, "fixtures_by_ids", lambda ids: [seq.pop(0)])
    monkeypatch.setattr(live.telegram, "send", lambda text, dry_run=False: sent.append(text))

    def sleep(s):
        clock["t"] += timedelta(seconds=s)
    live.run(hours=5, sleep=sleep, now_fn=lambda: clock["t"])
    assert [("BOSHLANDI" in s, "GOOOL" in s, "TUGADI" in s) for s in sent] == [
        (True, False, False), (False, True, False), (False, False, True)]


def plain(home, away, hid, aid, league=39, rnd="Regular Season - 10"):
    return {**match("NS", None, league=league), "home": home, "away": away,
            "home_id": hid, "away_id": aid, "round": rnd}


def test_importance_rules():
    ranks = {10: 1, 11: 2, 12: 3, 13: 4, 14: 15}
    assert live.why_important(plain("Brentford", "Fulham", 13, 14), ranks) is None
    assert "lider" in live.why_important(plain("Brentford", "Leeds", 12, 14), ranks)
    assert "katta" in live.why_important(plain("Fulham", "Real Madrid", 14, 99, league=140), {})
    assert "katta" in live.why_important(plain("Bayern München", "X", 1, 2, league=2), {})
    # kubok: guruh bosqichi oddiy o'yin — yo'q, pley-off — ha
    assert live.why_important(plain("Celtic", "Brugge", 1, 2, league=2, rnd="League Stage - 3"), {}) is None
    assert "pley-off" in live.why_important(plain("Celtic", "Brugge", 1, 2, league=2, rnd="Quarter-finals"), {})
    assert live.why_important(plain("Interactive", "X", 1, 2), {}) is None


def test_standings_cached_once_per_day(monkeypatch):
    calls = []
    monkeypatch.setattr(football, "standings", lambda lid, s: calls.append(lid) or {7: 1})
    st = fresh()
    assert live.ranks_for(39, 2026, st, "2026-10-30") == {7: 1}
    assert live.ranks_for(39, 2026, st, "2026-10-30") == {7: 1}
    assert calls == [39]
