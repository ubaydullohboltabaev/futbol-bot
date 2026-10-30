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


# ---------- admin bilan muloqot (tugmalar orqali tanlash) ----------

def send_markup(chat_id, text, markup):
    data = _call("sendMessage", {"chat_id": chat_id, "text": text, "parse_mode": "HTML",
                                 "reply_markup": markup})
    return data["result"]["message_id"]


def edit_markup(chat_id, message_id, markup):
    try:
        _call("editMessageReplyMarkup", {"chat_id": chat_id, "message_id": message_id,
                                         "reply_markup": markup})
    except RuntimeError as e:
        if "not modified" not in str(e):
            raise


def answer_callback(callback_id, text=""):
    _call("answerCallbackQuery", {"callback_query_id": callback_id, "text": text})


def get_updates(offset, timeout):
    """Long polling: yangi xabar/tugma bosilishini `timeout` soniyagacha kutadi."""
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN sozlanmagan")
    r = requests.post(API.format(token=TELEGRAM_BOT_TOKEN, method="getUpdates"),
                      json={"offset": offset, "timeout": int(timeout),
                            "allowed_updates": ["callback_query", "message"]},
                      timeout=timeout + 15)
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram xatosi: {data.get('description')}")
    return data["result"]
