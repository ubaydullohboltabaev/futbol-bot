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
    monkeypatch.setattr(live, "fetch_active", lambda active, ld, now: [seq.pop(0)])
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


def test_menu_and_toggle(monkeypatch):
    monkeypatch.setattr(live, "TELEGRAM_ADMIN_ID", "777")
    edits, answers = [], []
    monkeypatch.setattr(live.telegram, "edit_markup", lambda c, mid, mk: edits.append(mk))
    monkeypatch.setattr(live.telegram, "answer_callback", lambda cid, t="": answers.append(t))
    other = {**match("NS", None, fid=2), "home": "Burnley", "away": "Luton", "home_id": 5, "away_id": 6}
    monkeypatch.setattr(football, "fixtures_on", lambda d: [match("NS", None), other])
    monkeypatch.setattr(football, "standings", lambda lid, s: {40: 1})
    st = fresh()
    st["menus"] = {}
    day = live.menu_day(KO)
    menu = live.build_menu(day, live.live_league_ids(), st)
    assert menu["selected"] == ["1"]  # Liverpool taklif qilinadi, Burnley yo'q
    st["menus"][menu["day"]] = menu
    texts = [b["text"] for row in live.menu_markup(menu)["inline_keyboard"] for b in row]
    assert any(t.startswith("✅") and "Liverpool" in t for t in texts)
    assert any(t.startswith("▫️") and "Burnley" in t for t in texts)

    tap = {"update_id": 1, "callback_query": {"id": "c", "from": {"id": 777},
           "message": {"message_id": 5}, "data": f"t:{menu['day']}:2"}}
    assert live.handle_update(tap, st) and "2" in menu["selected"] and edits
    # begona odam bosa — e'tiborsiz
    stranger = {"update_id": 2, "callback_query": {"id": "d", "from": {"id": 1}, "data": f"t:{menu['day']}:2"}}
    assert not live.handle_update(stranger, st) and "2" in menu["selected"]
    none = {"update_id": 3, "callback_query": {"id": "e", "from": {"id": 777},
            "message": {"message_id": 5}, "data": f"a:{menu['day']}:none"}}
    assert live.handle_update(none, st) and menu["selected"] == []


def test_interactive_run_follows_admin_choice(monkeypatch):
    monkeypatch.setattr(live, "TELEGRAM_ADMIN_ID", "777")
    monkeypatch.setattr(live, "load_state", lambda path=None: fresh())
    monkeypatch.setattr(live, "save_state", lambda st, path=None: None)
    clock = {"t": KO - timedelta(minutes=30)}
    other = {**match("NS", None, fid=2), "home": "Burnley", "away": "Luton", "home_id": 5, "away_id": 6}
    monkeypatch.setattr(football, "fixtures_on", lambda d: [match("NS", None), other])
    monkeypatch.setattr(football, "standings", lambda lid, s: {40: 1})
    menus_sent, posted, polled = [], [], []
    monkeypatch.setattr(live.telegram, "send_markup", lambda c, t, mk: menus_sent.append(mk) or 9)
    monkeypatch.setattr(live.telegram, "edit_markup", lambda *a: None)
    monkeypatch.setattr(live.telegram, "answer_callback", lambda *a: None)
    monkeypatch.setattr(live.telegram, "send", lambda text, dry_run=False: posted.append(text))
    taps = [[{"update_id": 1, "callback_query": {"id": "c", "from": {"id": 777}, "message": {"message_id": 9},
              "data": f"t:{live.menu_day(KO).isoformat()}:1"}}]]  # admin Liverpool'ni o'chiradi

    def get_updates(offset, timeout):
        clock["t"] += timedelta(seconds=timeout)
        return taps.pop(0) if taps else []
    monkeypatch.setattr(live.telegram, "get_updates", get_updates)
    monkeypatch.setattr(live, "fetch_active", lambda active, ld, now: polled.append(active) or [])
    live.run(hours=3, now_fn=lambda: clock["t"], sleep=lambda s: None)
    assert len(menus_sent) == 1 and polled == [] and posted == []


def test_standings_failure_not_retried(monkeypatch):
    calls = []

    def boom(lid, s):
        calls.append(lid)
        raise football.ApiError("Free plans do not have access to this season")
    monkeypatch.setattr(football, "standings", boom)
    st = fresh()
    assert live.ranks_for(307, 2026, st, "d") == {} and live.ranks_for(307, 2026, st, "d") == {}
    assert calls == [307]



def test_fetch_active_uses_live_feed_then_id(monkeypatch):
    calls = []
    a = {"id": 1, "kickoff": KO, "completed": False, "league_id": 39}
    feed_m = {**match("1H", 20, hs=1), "has_events": False}
    monkeypatch.setattr(football, "live_fixtures", lambda lids: calls.append(("live", lids)) or [feed_m])
    monkeypatch.setattr(football, "fixture_by_id",
                        lambda fid: calls.append(("id", fid)) or match("1H", 20, [goal(19)], hs=1))
    # hisob o'zgardi, voqealar yo'q -> id bilan so'raladi
    out = live.fetch_active([a], {}, KO + timedelta(minutes=20))
    assert out[0]["events"] and calls == [("live", {39}), ("id", 1)]
    # o'zgarmadi -> eski voqealar ishlatiladi, qo'shimcha so'rov yo'q
    calls.clear()
    out = live.fetch_active([a], {"1": out[0]}, KO + timedelta(minutes=22))
    assert calls == [("live", {39})] and out[0]["events"]
    # o'yin feeddan chiqdi (tugadi) -> id bilan yakuniy holat
    calls.clear()
    monkeypatch.setattr(football, "live_fixtures", lambda lids: [])
    monkeypatch.setattr(football, "fixture_by_id", lambda fid: calls.append(fid) or match("FT", 90, hs=1))
    out = live.fetch_active([a], {"1": match("2H", 88, hs=1)}, KO + timedelta(minutes=110))
    assert out[0]["status"] == "FT" and calls == [1]
    # hali boshlanmagan (feedda yo'q, yaqinda) -> hech narsa so'ralmaydi
    calls.clear()
    assert live.fetch_active([a], {}, KO + timedelta(minutes=2)) == [] and calls == []


def test_live_fixtures_uses_all_and_filters(monkeypatch):
    seen = {}

    def get(path, params):
        seen.update(params)
        item = lambda lid, fid: {"fixture": {"id": fid, "date": "2026-10-31T15:00:00+00:00",
                                             "status": {"short": "1H", "elapsed": 5}},
                                 "league": {"id": lid}, "teams": {"home": {"name": "A"}, "away": {"name": "B"}},
                                 "goals": {"home": 0, "away": 0}}
        return {"response": [item(39, 1), item(999, 2)]}
    monkeypatch.setattr(football, "_get", get)
    out = football.live_fixtures({39})
    assert seen["live"] == "all" and [m["id"] for m in out] == [1] and out[0]["has_events"] is False
