"""Futbol kanal boti.

Ishlatish:
  python main.py morning   # kechagi natijalar + bugungi o'yinlar
  python main.py fixtures  # faqat bugungi o'yinlar
  python main.py results   # faqat kechagi natijalar
  python main.py news      # so'nggi yangiliklar (ANTHROPIC_API_KEY kerak)
  python main.py live      # jonli rejim: ~6 soat davomida o'yin voqealarini yuboradi

--dry-run qo'shsangiz, kanalga yubormaydi, faqat ekranga chiqaradi.
"""

import argparse
import sys
from datetime import datetime, timedelta, timezone

from bot import ai, football, live, news, posts, telegram
from bot.config import LEAGUES, NEWS_MAX_PER_RUN, NEWS_WINDOW_HOURS, TZ


def collect(day):
    try:
        data = football.fixtures_by_league(day, [lg["id"] for lg in LEAGUES])
    except Exception as e:
        # Ma'lumot kelmasa, "bugun o'yin yo'q" deb noto'g'ri post yubormaymiz
        sys.exit(f"Xato: o'yinlar olinmadi: {e}")
    return [(lg, data.get(lg["id"], [])) for lg in LEAGUES]


def run_fixtures(dry):
    today = datetime.now(TZ).date()
    telegram.send(posts.fixtures_post(today, collect(today)), dry_run=dry)


def run_results(dry):
    yesterday = datetime.now(TZ).date() - timedelta(days=1)
    text = posts.results_post(yesterday, collect(yesterday))
    if text:
        telegram.send(text, dry_run=dry)
    else:
        print("Kecha tugagan o'yin yo'q")


def run_news(dry):
    if not ai.enabled():
        print("ANTHROPIC_API_KEY yo'q — yangiliklar o'tkazib yuborildi")
        return
    since = datetime.now(timezone.utc) - timedelta(hours=NEWS_WINDOW_HOURS)
    try:
        items = [a for a in news.latest() if a["published"] >= since and a["headline"]]
    except Exception as e:
        sys.exit(f"Xato: yangiliklar olinmadi: {e}")
    # bir xil yangilik bir nechta ligada chiqishi mumkin
    seen, unique = set(), []
    for a in sorted(items, key=lambda x: x["published"], reverse=True):
        if a["headline"] not in seen:
            seen.add(a["headline"])
            unique.append(a)
    for a in unique[:NEWS_MAX_PER_RUN]:
        try:
            title, body = ai.rewrite(a["headline"], a["description"])
        except Exception as e:
            print(f"[ogohlantirish] AI: {e}", file=sys.stderr)
            continue
        telegram.send_photo(a["image"], posts.news_post(title, body, a["url"]), dry_run=dry)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=["morning", "fixtures", "results", "news", "live"])
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--hours", type=float, default=5.8, help="jonli rejim necha soat ishlasin")
    args = p.parse_args()
    if args.command in ("morning", "results"):
        run_results(args.dry_run)
    if args.command in ("morning", "fixtures"):
        run_fixtures(args.dry_run)
    if args.command == "news":
        run_news(args.dry_run)
    if args.command == "live":
        live.run(hours=args.hours, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
