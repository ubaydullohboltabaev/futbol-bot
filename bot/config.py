"""Ligalar ro'yxati va umumiy sozlamalar.

"id" — API-Football'dagi liga raqami (dashboard.api-football.com'da tekshirish mumkin).
"Qayerda ko'rish" qatorlarini o'zingiz yangilab turing: translyatsiya huquqlari
mavsumdan mavsumga o'zgaradi.
"""

import os
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Tashkent")

# Har bir liga: ESPN slug -> nom, emoji, qayerda ko'rish
LEAGUES = [
    {"id": 39, "name": "Angliya Premyer Ligasi (APL)", "emoji": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
     "watch": "Setanta Sports, Megogo"},
    {"id": 140, "name": "La Liga", "emoji": "🇪🇸",
     "watch": "Setanta Sports, Megogo"},
    {"id": 2, "name": "Chempionlar Ligasi", "emoji": "⭐️",
     "watch": "Futbol TV, Setanta Sports, Megogo"},
    {"id": 369, "name": "O'zbekiston Superligasi", "emoji": "🇺🇿",
     "watch": "Futbol TV, Sport TV, PFL YouTube"},
    {"id": 307, "name": "Saudiya Pro Ligasi", "emoji": "🇸🇦",
     "watch": "Thmanyah, Setanta Sports"},
    {"id": 17, "name": "Osiyo Chempionlar Ligasi", "emoji": "🌏",
     "watch": "Futbol TV, AFC YouTube"},
    {"id": 253, "name": "MLS", "emoji": "🇺🇸",
     "watch": "Apple TV (MLS Season Pass)"},
    {"id": 1, "name": "Jahon Chempionati", "emoji": "🏆",
     "watch": "Futbol TV, Sport TV"},
    {"id": 4, "name": "Yevropa Chempionati", "emoji": "🇪🇺",
     "watch": "Futbol TV, Setanta Sports"},
    {"id": 7, "name": "Osiyo Kubogi", "emoji": "🏆",
     "watch": "Futbol TV, Sport TV"},
]

API_FOOTBALL_BASE = "https://v3.football.api-sports.io"
API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY", "")

# Yangiliklar manbalari (RSS). O'zbekcha/ruscha saytlarning RSS'ini ham qo'shish mumkin.
NEWS_FEEDS = [
    "https://feeds.bbci.co.uk/sport/football/rss.xml",
]

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "")  # masalan: @kanal_nomi
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
AI_MODEL = os.environ.get("AI_MODEL", "claude-haiku-5-5")
CHANNEL_SIGNATURE = os.environ.get("CHANNEL_SIGNATURE", "")  # postlar oxiriga qo'shiladi

# Yangiliklar: oxirgi necha soatda chiqqanlarini olish (cron oralig'i bilan bir xil bo'lsin)
NEWS_WINDOW_HOURS = int(os.environ.get("NEWS_WINDOW_HOURS", "3"))
NEWS_MAX_PER_RUN = int(os.environ.get("NEWS_MAX_PER_RUN", "3"))
