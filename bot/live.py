"""Jonli rejim: o'yin davomida gol, kartochka, VAR va hokazolarni kanalga yuborish.

Bitta ishga tushirish "oyna" (taxminan 6 soat) davomida ishlaydi:
1. Oynadagi bizning ligalar o'yinlarini topadi.
2. O'yin boshlanmaguncha uxlaydi (so'rov sarflamaydi).
3. O'yin ketayotganda voqealarni so'raydi va yangilarini kanalga yuboradi.

Bepul tarif kuniga 100 so'rov beradi, shuning uchun so'rovlar orasidagi vaqt
qolgan limitga qarab avtomatik tanlanadi.
"""

import json
import os
import random
import time
from datetime import datetime, timedelta, timezone
from datetime import time as dtime

from . import football, telegram
from .config import (BIG_TEAMS, KNOCKOUT_WORDS, LEAGUES, LIVE_MIN_INTERVAL, LIVE_STATE_FILE,
                     LIVE_TOP_N, LIVE_YELLOW_CARDS, MENU_HOUR, TELEGRAM_ADMIN_ID, TZ)
from .posts import esc

MATCH_LENGTH = timedelta(minutes=115)  # tanaffus va qo'shilgan vaqt bilan taxminan
DEAD = {"PST", "CANC", "ABD", "AWD", "WO", "SUSP"}
RESERVE_PER_DAY = 6  # ertalabki post va keyingi oynalar uchun zaxira so'rovlar

GOAL_JOKES = [
    "Darvozabon faqat qarab qoldi 👀",
    "Tribunalar portladi! 🔥",
    "Qo'shnilar uyg'onib ketdi 😅",
    "Bu golni nevaralarga aytib berasiz 👴",
    "To'p to'rga, muxlislar osmonga! 🚀",
    "Himoyachilar choy ichishga ketgan ekan ☕️",
]
OWN_GOAL_JOKES = [
    "O'z darvozasiga! Do'stlarga yordam berishni yaxshi ko'radi 🤦‍♂️",
    "Raqibga sovg'a 🎁 Bayram hali kelmagan edi-ku",
]
PEN_MISS_JOKES = [
    "Penaltini ham o'tkazib bo'larkan 😳",
    "To'p oyga uchib ketdi, NASA qidiryapti 🛰",
]
RED_JOKES = [
    "Dushga erta ketdi 🚿",
    "Hakam: 'Uyga bor, bolam' 🏠",
]
YELLOW_JOKES = ["Ehtiyot bo'l, ukam ⚠️", "Hakam daftarga yozib qo'ydi 📒"]
VAR_JOKES = ["Hamma ekranga qaradi 📺", "Texnologiya aralashdi 🤖"]
KICKOFF_JOKES = ["Choy tayyormi? Ketdik! ☕️", "Divanga o'tiring, boshlandi! 🛋"]
HT_JOKES = ["Tanaffus — somsa vaqti 🥟", "Yarim vaqt. Choyni yangilang ☕️"]


def league_cfg(league_id):
    for lg in LEAGUES:
        if lg["id"] == league_id:
            return lg
    return None


def live_league_ids():
    return {lg["id"] for lg in LEAGUES if lg.get("live", True)}


# ---------- qaysi o'yinlar muhim ----------

def is_big(name):
    return any(name == b or name.startswith(b + " ") for b in BIG_TEAMS)


def why_important(m, ranks):
    """Muhim bo'lsa sababini, bo'lmasa None qaytaradi. ranks: {team_id: o'rni}."""
    lg = league_cfg(m["league_id"]) or {}
    for side in ("home", "away"):
        if is_big(m[side]):
            return f"katta jamoa: {m[side]}"
    if lg.get("cup"):
        if any(w.lower() in m["round"].lower() for w in KNOCKOUT_WORDS):
            return f"pley-off: {m['round']}"
        return None
    for side in ("home", "away"):
        r = ranks.get(m[f"{side}_id"])
        if r is not None and r <= LIVE_TOP_N:
            return f"lider: {m[side]} ({r}-o'rin)"
    return None


def ranks_for(league_id, season, state, today):
    """Jadvalni kuniga bir marta oladi va holatda saqlaydi (so'rov tejash)."""
    key = f"{league_id}:{season}:{today}"
    cache = state.setdefault("standings", {})
    if key not in cache:
        try:
            cache[key] = {str(k): v for k, v in football.standings(league_id, season).items()}
        except Exception as e:
            # bepul tarif joriy mavsum jadvalini bermaydi — bugun qayta so'ramaymiz
            print(f"[ogohlantirish] jadval {league_id}: {e}")
            cache[key] = {}
        for old in [k for k in cache if not k.endswith(str(today))]:
            del cache[old]
    return {int(k): v for k, v in cache[key].items()}


# ---------- holat (qaysi voqealar yuborilgan) ----------

def load_state(path=LIVE_STATE_FILE):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"sent": [], "status": {}}


def save_state(state, path=LIVE_STATE_FILE):
    state["sent"] = state["sent"][-3000:]  # fayl kattalashib ketmasin
    with open(path, "w") as f:
        json.dump(state, f)


def event_key(fixture_id, ev):
    t = ev.get("time") or {}
    return ":".join(str(x) for x in (
        fixture_id, ev.get("type"), ev.get("detail"), t.get("elapsed"), t.get("extra"),
        (ev.get("player") or {}).get("id") or (ev.get("player") or {}).get("name"),
    ))


# ---------- post matnlari ----------

def _minute(ev):
    t = ev.get("time") or {}
    if t.get("elapsed") is None:
        return ""
    return f"{t['elapsed']}+{t['extra']}'" if t.get("extra") else f"{t['elapsed']}'"


def _score(m):
    h = 0 if m["home_score"] is None else m["home_score"]
    a = 0 if m["away_score"] is None else m["away_score"]
    return f"{esc(m['home'])} <b>{h}:{a}</b> {esc(m['away'])}"


def _head(m):
    lg = league_cfg(m["league_id"]) or {"emoji": "⚽️", "name": ""}
    return f"{lg['emoji']} {esc(lg['name'])}"


def event_text(m, ev, rng=random):
    """Voqea uchun post matni, yoki None (yuborilmaydigan voqea)."""
    etype, detail = ev.get("type"), ev.get("detail") or ""
    player = esc((ev.get("player") or {}).get("name") or "")
    team = esc((ev.get("team") or {}).get("name") or "")
    assist = esc((ev.get("assist") or {}).get("name") or "")
    minute = _minute(ev)

    if etype == "Goal":
        if detail == "Missed Penalty":
            body = f"❌ <b>PENALTI O'TMADI!</b> {minute}\n{player} ({team})\n{rng.choice(PEN_MISS_JOKES)}"
        elif detail == "Own Goal":
            body = f"🙈 <b>AVTOGOL!</b> {minute}\n{player} ({team})\n{rng.choice(OWN_GOAL_JOKES)}"
        else:
            kind = " (penalti)" if detail == "Penalty" else ""
            line = f"⚽️ <b>GOOOL!</b> {minute}\n{player}{kind} — {team}"
            if assist:
                line += f"\n🅰️ Pas: {assist}"
            body = f"{line}\n{rng.choice(GOAL_JOKES)}"
    elif etype == "Card":
        if "Red" in detail or "Second Yellow" in detail:
            body = f"🟥 <b>QIZIL KARTOCHKA!</b> {minute}\n{player} ({team})\n{rng.choice(RED_JOKES)}"
        elif LIVE_YELLOW_CARDS and "Yellow" in detail:
            body = f"🟨 Sariq kartochka {minute}\n{player} ({team})\n{rng.choice(YELLOW_JOKES)}"
        else:
            return None
    elif etype == "Var":
        uz = {
            "Goal cancelled": "Gol bekor qilindi ❌",
            "Goal Disallowed": "Gol bekor qilindi ❌",
            "Penalty confirmed": "Penalti tasdiqlandi ✅",
            "Penalty cancelled": "Penalti bekor qilindi ❌",
            "Goal confirmed": "Gol tasdiqlandi ✅",
            "Card upgrade": "Kartochka o'zgartirildi",
        }.get(detail, esc(detail))
        body = f"📺 <b>VAR</b> {minute}\n{uz} ({team})\n{rng.choice(VAR_JOKES)}"
    else:
        return None
    return f"{_head(m)}\n{body}\n\n{_score(m)}"


def status_text(m, status, rng=random):
    if status == "1H":
        return f"{_head(m)}\n🟢 <b>O'YIN BOSHLANDI!</b>\n{esc(m['home'])} — {esc(m['away'])}\n{rng.choice(KICKOFF_JOKES)}"
    if status == "HT":
        return f"{_head(m)}\n⏸ <b>TANAFFUS</b>\n{_score(m)}\n{rng.choice(HT_JOKES)}"
    if status in football.FINISHED:
        extra = {"AET": " (qo'shimcha vaqtda)", "PEN": " (penaltilar seriyasida)"}.get(status, "")
        return f"{_head(m)}\n🏁 <b>O'YIN TUGADI{extra}</b>\n{_score(m)}"
    return None


def process(m, state, rng=random):
    """O'yinning yangi voqealari uchun post matnlari ro'yxati. Holatni yangilaydi."""
    fid = str(m["id"])
    sent = set(state["sent"])
    prev = state["status"].get(fid)
    cur = m["status"]
    first_seen = prev is None
    before, events, after = [], [], []

    if cur != prev:
        # boshlanish xabari faqat o'yin boshida ko'rgan bo'lsak
        if cur == "1H" and prev in (None, "NS", "TBD") and (m["elapsed"] or 0) <= 10:
            before.append(status_text(m, "1H", rng))
        elif cur == "HT" or cur in football.FINISHED:
            after.append(status_text(m, cur, rng))
        state["status"][fid] = cur

    for ev in m["events"]:
        key = event_key(fid, ev)
        if key in sent:
            continue
        state["sent"].append(key)
        sent.add(key)
        # bot o'yin o'rtasida ulansa, eski voqealarni qayta yubormaymiz
        ev_min = (ev.get("time") or {}).get("elapsed") or 0
        if first_seen and m["elapsed"] and ev_min < m["elapsed"] - 10:
            continue
        text = event_text(m, ev, rng)
        if text:
            events.append(text)
    return [t for t in before + events + after if t]


# ---------- asosiy tsikl ----------

def poll_interval(now, matches, deadline):
    """Qolgan limit va kutilayotgan jonli vaqtga qarab so'rovlar oralig'i (soniya)."""
    remaining = football.quota["remaining"]
    if remaining is None:
        return max(LIVE_MIN_INTERVAL, 180)
    budget = max(1, remaining - RESERVE_PER_DAY)
    # oynada qolgan "jonli" vaqt (o'yinlar ustma-ust tushsa bir marta hisoblanadi)
    spans = sorted((max(now, m["kickoff"]), min(deadline, m["kickoff"] + MATCH_LENGTH))
                   for m in matches if not m["completed"])
    live_secs, cur_end = 0, None
    for s, e in spans:
        if e <= s:
            continue
        if cur_end is None or s > cur_end:
            live_secs += (e - s).total_seconds()
            cur_end = e
        elif e > cur_end:
            live_secs += (e - cur_end).total_seconds()
            cur_end = e
    return max(LIVE_MIN_INTERVAL, int(live_secs / budget) if live_secs else LIVE_MIN_INTERVAL)


# ---------- ertalabki tanlov menyusi ----------

def menu_day(now):
    """Joriy menyu kuni: Toshkent vaqti bilan MENU_HOUR dan keyingi 24 soat."""
    return (now.astimezone(TZ) - timedelta(hours=MENU_HOUR)).date()


def menu_bounds(day):
    start = datetime.combine(day, dtime(MENU_HOUR), TZ)
    return start, start + timedelta(days=1)


def build_menu(day, wanted, state):
    """Kun o'yinlari ro'yxati va avtomatik takliflar (2-3 so'rov)."""
    lo, hi = menu_bounds(day)
    fixtures = {}
    for d in sorted({lo.astimezone(timezone.utc).date(), hi.astimezone(timezone.utc).date()}):
        for m in football.fixtures_on(d):
            if m["league_id"] in wanted and m["status"] not in DEAD and lo <= m["kickoff"] < hi:
                fixtures[m["id"]] = m
    selected = []
    for m in sorted(fixtures.values(), key=lambda m: m["kickoff"]):
        lg = league_cfg(m["league_id"]) or {}
        ranks = {} if lg.get("cup") else ranks_for(m["league_id"], m["season"], state, day.isoformat())
        if why_important(m, ranks):
            selected.append(str(m["id"]))
    return {
        "day": day.isoformat(),
        "message_id": None,
        "fixtures": {str(m["id"]): {"league_id": m["league_id"], "home": m["home"], "away": m["away"],
                                    "kickoff": m["kickoff"].isoformat()}
                     for m in fixtures.values()},
        "selected": selected,
    }


def menu_markup(menu):
    rows = []
    sel = set(menu["selected"])
    by_league = {}
    for fid, f in menu["fixtures"].items():
        by_league.setdefault(f["league_id"], []).append((fid, f))
    for lg in LEAGUES:
        items = sorted(by_league.get(lg["id"], []), key=lambda x: x[1]["kickoff"])
        if not items:
            continue
        rows.append([{"text": f"— {lg['emoji']} {lg['name']} —", "callback_data": "noop"}])
        for fid, f in items:
            ko = datetime.fromisoformat(f["kickoff"]).astimezone(TZ)
            mark = "✅" if fid in sel else "▫️"
            rows.append([{"text": f"{mark} {ko:%H:%M} {f['home']} — {f['away']}",
                          "callback_data": f"t:{menu['day']}:{fid}"}])
    rows.append([{"text": "✅ Hammasi", "callback_data": f"a:{menu['day']}:all"},
                 {"text": "▫️ Hech biri", "callback_data": f"a:{menu['day']}:none"}])
    return {"inline_keyboard": rows}


def menu_text(menu):
    from .posts import uz_date
    day = datetime.fromisoformat(menu["day"]).date()
    if not menu["fixtures"]:
        return f"📋 <b>{uz_date(day)}</b>\n\nBugun bizning ligalarda o'yin yo'q 😴"
    return (f"📋 <b>Jonli efir uchun o'yinlar — {uz_date(day)}</b>\n\n"
            "Qaysi o'yinlarni kanalda jonli beramiz? Bosib belgilang ✅\n"
            "Men muhim deb hisoblaganlarini oldindan belgiladim. "
            "O'yin boshlangandan keyin ham o'zgartirsa bo'ladi.\n\n"
            "Menyuni qayta olish: /menu")


def send_menu(menu, dry_run=False):
    if dry_run or not TELEGRAM_ADMIN_ID:
        print(f"Menyu ({menu['day']}): {len(menu['fixtures'])} o'yin, tanlangan: {len(menu['selected'])}")
        return
    if not menu["fixtures"]:
        telegram.send_markup(TELEGRAM_ADMIN_ID, menu_text(menu), {"inline_keyboard": []})
        return
    menu["message_id"] = telegram.send_markup(TELEGRAM_ADMIN_ID, menu_text(menu), menu_markup(menu))


def handle_update(upd, state):
    """Admin tugma bosganda yoki /menu yozganda. Tanlov o'zgarsa True qaytaradi."""
    menus = state["menus"]
    cb = upd.get("callback_query")
    if cb:
        if str((cb.get("from") or {}).get("id")) != TELEGRAM_ADMIN_ID:
            return False
        data = cb.get("data") or ""
        parts = data.split(":")
        changed, note = False, ""
        if len(parts) == 3 and parts[1] in menus:
            menu = menus[parts[1]]
            if parts[0] == "t" and parts[2] in menu["fixtures"]:
                if parts[2] in menu["selected"]:
                    menu["selected"].remove(parts[2])
                    note = "Jonli efirdan olib tashlandi"
                else:
                    menu["selected"].append(parts[2])
                    note = "Jonli efirga qo'shildi ✅"
                changed = True
            elif parts[0] == "a":
                menu["selected"] = list(menu["fixtures"]) if parts[2] == "all" else []
                note = "Hammasi tanlandi" if parts[2] == "all" else "Hech biri tanlanmadi"
                changed = True
            if changed:
                msg = cb.get("message") or {}
                telegram.edit_markup(TELEGRAM_ADMIN_ID, msg.get("message_id") or menu["message_id"],
                                     menu_markup(menu))
        elif parts[0] in ("t", "a"):
            note = "Bu menyu eskirgan"
        telegram.answer_callback(cb["id"], note)
        return changed
    msg = upd.get("message") or {}
    if str((msg.get("chat") or {}).get("id")) == TELEGRAM_ADMIN_ID and \
            (msg.get("text") or "").strip() in ("/menu", "/start"):
        if menus:
            send_menu(menus[max(menus)])
    return False


# ---------- asosiy tsikl ----------

def run(hours=5.9, dry_run=False, sleep=time.sleep, now_fn=lambda: datetime.now(timezone.utc)):
    start = now_fn()
    deadline = start + timedelta(hours=hours)
    wanted = live_league_ids()
    state = load_state()
    state.setdefault("menus", {})
    live_data = {}  # fid -> API'dan kelgan so'nggi holat
    interactive = bool(TELEGRAM_ADMIN_ID) and not dry_run

    def wait(seconds):
        """Kutish. Admin rejimida shu vaqt ichida tugma bosilishini tinglaydi."""
        end = now_fn() + timedelta(seconds=seconds)
        while True:
            left = (end - now_fn()).total_seconds()
            if left <= 0:
                return
            if not interactive:
                sleep(left)
                return
            try:
                updates = telegram.get_updates(state.get("tg_offset"), min(50, max(1, left)))
            except Exception as e:
                print(f"[ogohlantirish] getUpdates: {e}")
                sleep(min(30, left))
                continue
            changed = False
            for upd in updates:
                state["tg_offset"] = upd["update_id"] + 1
                try:
                    changed |= handle_update(upd, state)
                except Exception as e:
                    print(f"[ogohlantirish] tugma: {e}")
            if updates:
                save_state(state)
            if changed:
                return  # tanlov o'zgardi — darhol qayta hisoblaymiz

    def selected_matches(now):
        out = []
        for menu in state["menus"].values():
            for fid in menu["selected"]:
                f = menu["fixtures"].get(fid)
                if not f:
                    continue
                ko = datetime.fromisoformat(f["kickoff"])
                done = live_data.get(fid, {}).get("completed")
                if not done and now - timedelta(hours=4) <= ko <= deadline:
                    out.append({"id": int(fid), "kickoff": ko, "completed": False})
        return out

    try:
        while True:
            now = now_fn()
            if now >= deadline:
                break
            day = menu_day(now)
            if day.isoformat() not in state["menus"]:
                try:
                    menu = build_menu(day, wanted, state)
                except Exception as e:
                    print(f"[ogohlantirish] menyu: {e}")
                    wait(300)
                    continue
                state["menus"][menu["day"]] = menu
                for old in sorted(state["menus"])[:-2]:
                    del state["menus"][old]
                send_menu(menu, dry_run=dry_run)
                save_state(state)
                for fid in menu["selected"]:
                    f = menu["fixtures"][fid]
                    print(f"Taklif: {f['home']} — {f['away']}")

            todo = selected_matches(now)
            active = [m for m in todo if m["kickoff"] - timedelta(minutes=1) <= now]
            if not active:
                next_menu = menu_bounds(day)[1].astimezone(timezone.utc)
                upcoming = [m["kickoff"] for m in todo if m["kickoff"] > now]
                if not interactive and not upcoming and next_menu > deadline:
                    break  # kutadigan narsa yo'q
                target = min(upcoming + [next_menu, deadline])
                secs = max(30, (target - now).total_seconds())
                print(f"{int(secs // 60)} daqiqa kutaman")
                wait(secs)
                continue

            try:
                fresh = football.fixtures_by_ids([m["id"] for m in active])
            except Exception as e:  # tarmoq xatosi bo'lsa, oyna to'xtamasin
                print(f"[ogohlantirish] {e}")
                wait(120)
                continue
            for m in fresh:
                for text in process(m, state):
                    try:
                        telegram.send(text, dry_run=dry_run)
                    except Exception as e:
                        print(f"[ogohlantirish] Telegram: {e}")
                if m["status"] in DEAD or (
                        not m["completed"] and now - m["kickoff"] > timedelta(hours=4)):
                    m["completed"] = True  # qoldirilgan yoki osilib qolgan o'yin
                live_data[str(m["id"])] = m
            save_state(state)

            todo = selected_matches(now_fn())
            interval = poll_interval(now_fn(), todo, deadline)
            print(f"Qolgan so'rovlar: {football.quota['remaining']}, keyingi tekshiruv {interval} s dan keyin")
            wait(interval)
    finally:
        save_state(state)
