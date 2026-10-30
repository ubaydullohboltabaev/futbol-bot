"""Ligalar ro'yxati va umumiy sozlamalar.

ESPN kodlari (slug) bepul ESPN API uchun. "Qayerda ko'rish" qatorlarini
o'zingiz yangilab turing: translyatsiya huquqlari mavsumdan mavsumga o'zgaradi.
"""

import os
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Tashkent")

# Har bir liga: ESPN slug -> nom, emoji, qayerda ko'rish
LEAGUES = [
    {"slug": "eng.1", "name": "Angliya Premyer Ligasi (APL)", "emoji": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
     "watch": "Setanta Sports, Megogo"},
    {"slug": "esp.1", "name": "La Liga", "emoji": "🇪🇸",
     "watch": "Setanta Sports, Megogo"},
    {"slug": "uefa.champions", "name": "Chempionlar Ligasi", "emoji": "⭐️",
     "watch": "Futbol TV, Setanta Sports, Megogo"},
    {"slug": "uzb.1", "name": "O'zbekiston Superligasi", "emoji": "🇺🇿",
     "watch": "Futbol TV, Sport TV, PFL YouTube"},
    {"slug": "ksa.1", "name": "Saudiya Pro Ligasi", "emoji": "🇸🇦",
     "watch": "Thmanyah, Setanta Sports"},
    {"slug": "afc.champions", "name": "Osiyo Chempionlar Ligasi", "emoji": "🌏",
     "watch": "Futbol TV, AFC YouTube"},
    {"slug": "usa.1", "name": "MLS", "emoji": "🇺🇸",
     "watch": "Apple TV (MLS Season Pass)"},
    {"slug": "fifa.world", "name": "Jahon Chempionati", "emoji": "🏆",
     "watch": "Futbol TV, Sport TV"},
    {"slug": "uefa.euro", "name": "Yevropa Chempionati", "emoji": "🇪🇺",
     "watch": "Futbol TV, Setanta Sports"},
    {"slug": "afc.asian", "name": "Osiyo Kubogi", "emoji": "🏆",
     "watch": "Futbol TV, Sport TV"},
]

ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "")  # masalan: @kanal_nomi
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
AI_MODEL = os.environ.get("AI_MODEL", "claude-haiku-5-5")
CHANNEL_SIGNATURE = os.environ.get("CHANNEL_SIGNATURE", "")  # postlar oxiriga qo'shiladi

# Yangiliklar: oxirgi necha soatda chiqqanlarini olish (cron oralig'i bilan bir xil bo'lsin)
NEWS_WINDOW_HOURS = int(os.environ.get("NEWS_WINDOW_HOURS", "3"))
NEWS_MAX_PER_RUN = int(os.environ.get("NEWS_MAX_PER_RUN", "3"))
