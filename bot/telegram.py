"""Telegram kanalga post yuborish."""

import requests

from .config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID

API = "https://api.telegram.org/bot{token}/{method}"
LIMIT = 4000  # Telegram limiti 4096, biroz zaxira


def _call(method, payload):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
        raise RuntimeError("TELEGRAM_BOT_TOKEN va TELEGRAM_CHANNEL_ID sozlanmagan")
    r = requests.post(API.format(token=TELEGRAM_BOT_TOKEN, method=method), json=payload, timeout=20)
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram xatosi: {data.get('description')}")
    return data


def split(text, limit=LIMIT):
    """Uzun matnni bo'sh qatorlar bo'yicha bo'laklarga ajratadi."""
    parts, cur = [], ""
    for block in text.split("\n\n"):
        candidate = f"{cur}\n\n{block}" if cur else block
        if len(candidate) > limit and cur:
            parts.append(cur)
            cur = block
        else:
            cur = candidate
    if cur:
        parts.append(cur)
    return parts


def send(text, dry_run=False):
    for part in split(text):
        if dry_run:
            print(part)
            print("-" * 40)
            continue
        _call("sendMessage", {
            "chat_id": TELEGRAM_CHANNEL_ID,
            "text": part,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        })


def send_photo(photo_url, caption, dry_run=False):
    if dry_run or not photo_url or len(caption) > 1000:
        return send(caption, dry_run=dry_run)
    _call("sendPhoto", {
        "chat_id": TELEGRAM_CHANNEL_ID,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "HTML",
    })
