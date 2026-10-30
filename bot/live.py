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

from . import football, telegram
from .config import LEAGUES, LIVE_MIN_INTERVAL, LIVE_STATE_FILE, LIVE_YELLOW_CARDS
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


def run(hours=5.8, dry_run=False, sleep=time.sleep, now_fn=lambda: datetime.now(timezone.utc)):
    start = now_fn()
    deadline = start + timedelta(hours=hours)
    wanted = live_league_ids()

    # oynaga tegishli o'yinlar (1-2 so'rov)
    days = sorted({(start - MATCH_LENGTH).date(), start.date(), deadline.date()})
    matches = {}
    for d in days:
        for m in football.fixtures_on(d):
            if m["league_id"] not in wanted or m["status"] in DEAD:
                continue
            if m["completed"] and m["kickoff"] + MATCH_LENGTH < start:
                continue
            if start - MATCH_LENGTH * 2 <= m["kickoff"] <= deadline:
                matches[m["id"]] = m
    print(f"Oynada {len(matches)} ta o'yin kuzatiladi")
    state = load_state()

    try:
        while matches:
            now = now_fn()
            if now >= deadline:
                break
            active = [m for m in matches.values()
                      if not m["completed"] and m["kickoff"] - timedelta(minutes=1) <= now]
            if not active:
                upcoming = [m["kickoff"] for m in matches.values() if m["kickoff"] > now]
                if not upcoming:
                    break
                wait = (min(min(upcoming), deadline) - now).total_seconds()
                print(f"Keyingi o'yingacha {int(wait // 60)} daqiqa uxlayman")
                sleep(max(30, wait))
                continue

            try:
                fresh = football.fixtures_by_ids([m["id"] for m in active])
            except Exception as e:  # tarmoq xatosi bo'lsa, oyna to'xtamasin
                print(f"[ogohlantirish] {e}")
                sleep(120)
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
                matches[m["id"]] = m
            save_state(state)

            interval = poll_interval(now_fn(), list(matches.values()), deadline)
            print(f"Qolgan so'rovlar: {football.quota['remaining']}, keyingi tekshiruv {interval} s dan keyin")
            sleep(interval)
    finally:
        save_state(state)
