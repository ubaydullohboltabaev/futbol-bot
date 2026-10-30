"""Postlar matnini yasash: o'zbekcha, yumor bilan."""

import html
import random

from .config import CHANNEL_SIGNATURE

OYLAR = ["yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul",
         "avgust", "sentabr", "oktabr", "noyabr", "dekabr"]
HAFTA = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]

FIXTURES_INTRO = [
    "Choy damlang, chigit chaqing — bugun futbol kuni! ☕️⚽️",
    "Xotiningizga oldindan uzr so'rab qo'ying, bugun televizor bizniki 📺😅",
    "Ish-pish keyin, avval jadvalni ko'rib oling 👇",
    "Bugun uxlamaymiz, chunki o'yin bor! 🦉⚽️",
    "Divanni tayyorlang, pultni yashirib qo'ying 🛋🔥",
]
FIXTURES_OUTRO = [
    "Qaysi o'yinga stavka... yo'q, qaysi o'yinni ko'rasiz? Izohda yozing 👇😄",
    "Kim yutadi deb o'ylaysiz? Bashoratlaringizni yozing, keyin uyaltiramiz 😏",
    "Kanalni yoqib qo'ying, gollar haqida birinchi bo'lib bilasiz 🔔",
]
NO_MATCHES = [
    "Bugun bizning ligalarda o'yin yo'q 😴 Futbolsiz kun — xotin-qizlar bayrami 💐",
    "Bugun o'yin yo'q. Dam oling, oilangizni eslang, ular sizni sog'ingan 😅",
]
RESULTS_INTRO = [
    "Kecha nima bo'ldi? Uxlab qolganlar uchun hisobot 😴👇",
    "Kechagi jang natijalari. Kimdir xursand, kimdir hali ham yig'layapti 😭😂",
    "Kecha kim kimni urdi — qisqacha 👊",
]
DRAW_JOKES = [
    "durang, hamma xursand, hech kim xursand emas 🤝",
    "do'stlik g'alaba qozondi 🤝",
    "ochkoni bo'lishib olishdi, xuddi to'ydagi osh kabi 🍚",
]
BIG_WIN_JOKES = [
    "bu o'yin emas, mashg'ulot bo'ldi 😳",
    "raqib avtobusni darvoza oldiga qo'yishni unutibdi 🚌",
    "darvozabon hali ham to'pni qidiryapti 🔍",
]
ZERO_ZERO_JOKES = [
    "0:0 — uxlatib qo'ygan o'yin uchun rahmat 😴",
    "gol yo'q, lekin hissiyot... ham yo'q 🥱",
]


def esc(s):
    return html.escape(str(s or ""), quote=False)


def uz_date(d):
    return f"{d.day}-{OYLAR[d.month - 1]}, {HAFTA[d.weekday()]}"


def _sign(text):
    return f"{text}\n\n{CHANNEL_SIGNATURE}" if CHANNEL_SIGNATURE else text


def fixtures_post(day, by_league, rng=random):
    """by_league: [(league_cfg, [match, ...]), ...]"""
    lines = [f"📅 <b>BUGUNGI O'YINLAR — {uz_date(day)}</b>", "", rng.choice(FIXTURES_INTRO)]
    total = 0
    for league, matches in by_league:
        if not matches:
            continue
        total += len(matches)
        lines += ["", f"{league['emoji']} <b>{esc(league['name'])}</b>"]
        for m in matches:
            lines.append(f"🕒 {m['kickoff']:%H:%M} | {esc(m['home'])} — {esc(m['away'])}")
        lines.append(f"📺 <i>{esc(league['watch'])}</i>")
    if total == 0:
        return _sign(f"📅 <b>{uz_date(day)}</b>\n\n{rng.choice(NO_MATCHES)}")
    lines += ["", "⏰ Vaqtlar Toshkent vaqti bilan.", rng.choice(FIXTURES_OUTRO)]
    return _sign("\n".join(lines))


def _result_comment(m, rng):
    try:
        h, a = int(m["home_score"]), int(m["away_score"])
    except (TypeError, ValueError):
        return ""
    if h == a == 0:
        return rng.choice(ZERO_ZERO_JOKES)
    if h == a:
        return rng.choice(DRAW_JOKES)
    if abs(h - a) >= 3:
        return rng.choice(BIG_WIN_JOKES)
    return ""


def results_post(day, by_league, rng=random):
    blocks = []
    for league, matches in by_league:
        done = [m for m in matches if m["completed"]]
        if not done:
            continue
        rows = [f"{league['emoji']} <b>{esc(league['name'])}</b>"]
        for m in done:
            row = f"{esc(m['home'])} <b>{esc(m['home_score'])}:{esc(m['away_score'])}</b> {esc(m['away'])}"
            joke = _result_comment(m, rng)
            rows.append(f"⚽️ {row}" + (f" — {joke}" if joke else ""))
        blocks.append("\n".join(rows))
    if not blocks:
        return None
    head = f"📊 <b>KECHAGI NATIJALAR — {uz_date(day)}</b>\n\n{rng.choice(RESULTS_INTRO)}"
    return _sign(head + "\n\n" + "\n\n".join(blocks))


def news_post(league, title, body, url=""):
    text = f"{league['emoji']} <b>{esc(title)}</b>\n\n{esc(body)}"
    if url:
        text += f'\n\n🔗 <a href="{esc(url)}">Batafsil</a>'
    return _sign(text)
