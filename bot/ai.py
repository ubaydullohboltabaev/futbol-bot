"""Inglizcha yangilikni o'zbekchaga, yumor bilan qayta yozish (Claude API orqali).

ANTHROPIC_API_KEY bo'lmasa, yangiliklar o'tkazib yuboriladi
(inglizcha matnni kanalga tashlash yaxshi emas).
"""

import json

import requests

from .config import AI_MODEL, ANTHROPIC_API_KEY

STYLE = """Sen o'zbek futbol Telegram kanali muharririsan. Uslub: jonli, hazilkash,
ko'cha tilida, lekin haqoratsiz. Qisqa gaplar, mos emojilar, futbolchilar va
klublar ustidan yengil kinoya, muxlislar hazili (masalan "Arsenal yana 2-o'rinda",
"Ronaldu yana gol urdi, yoshi esa sir"). Faktlarni o'zgartirma, to'qima.
Faqat lotin yozuvidagi o'zbek tilida yoz."""

PROMPT = """Quyidagi futbol yangiligini kanal uchun qayta yoz.

Sarlavha: {headline}
Matn: {description}

Faqat JSON qaytar: {{"title": "qisqa qiziqarli sarlavha (emoji bilan)", "body": "2-4 gap, hazil bilan"}}"""


def enabled():
    return bool(ANTHROPIC_API_KEY)


def rewrite(headline, description):
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": AI_MODEL,
            "max_tokens": 500,
            "system": STYLE,
            "messages": [{"role": "user", "content": PROMPT.format(
                headline=headline, description=description)}],
        },
        timeout=60,
    )
    r.raise_for_status()
    text = "".join(b.get("text", "") for b in r.json().get("content", []))
    start, end = text.find("{"), text.rfind("}")
    data = json.loads(text[start:end + 1])
    return data["title"], data["body"]
