# ⚽️ Futbol kanal boti

Telegram kanalga har kuni o'zbek tilida, hazil bilan avtomatik post yuboradi:

- **09:00 (Toshkent)** — kechagi natijalar + bugungi o'yinlar (kim kim bilan, soat nechada, qayerda ko'rish mumkin)
- **Har 3 soatda** — so'nggi yangiliklar, AI yordamida o'zbekchaga hazil bilan qayta yozilgan

Ligalar: APL, La Liga, Chempionlar Ligasi, O'zbekiston Superligasi, Saudiya Pro Ligasi, Osiyo Chempionlar Ligasi, MLS, Jahon chempionati, Yevro, Osiyo kubogi. Ro'yxat va "qayerda ko'rish" qatorlari `bot/config.py` faylida.

O'yinlar [API-Football](https://www.api-football.com/)'dan olinadi (kunlik bitta so'rov), yangiliklar RSS lentalardan (`bot/config.py` → `NEWS_FEEDS`). Bot GitHub Actions'da bepul ishlaydi, server kerak emas.

## Sozlash

1. **Bot yaratish:** Telegram'da @BotFather → `/newbot` → token oling.
2. **Botni kanalga admin qiling:** kanal → Administratorlar → botni qo'shing, "Xabar yuborish" huquqini bering.
3. **GitHub sirlari:** repo → Settings → Secrets and variables → Actions → *New repository secret*:
   - `TELEGRAM_BOT_TOKEN` — BotFather bergan token
   - `TELEGRAM_CHANNEL_ID` — masalan `@kanal_nomi`
   - `API_FOOTBALL_KEY` — [dashboard.api-football.com](https://dashboard.api-football.com/register) da ro'yxatdan o'tib olinadi
   - `ANTHROPIC_API_KEY` — yangiliklar uchun (console.anthropic.com). Bo'lmasa faqat o'yinlar va natijalar chiqadi.
   - (ixtiyoriy) *Variables* bo'limida `CHANNEL_SIGNATURE` — har post oxiriga qo'shiladigan imzo, masalan `👉 @kanal_nomi`
4. **Sinash:** Actions → "Ertalabki post" → *Run workflow*. `dry_run` belgilansa, kanalga yubormaydi, natijani faqat logda ko'rsatadi.

⚠️ Tokenni hech qachon kodga yoki chatga yozmang, faqat GitHub Secrets'ga.

## Kompyuterda ishlatish

```bash
pip install -r requirements.txt
cp .env.example .env   # to'ldiring
export $(cat .env | xargs)
python main.py morning --dry-run   # kanalga yubormay, ekranda ko'rish
python main.py news --dry-run
```

Testlar: `pip install pytest && python -m pytest tests`

## Keyingi bosqich

Jonli o'yin: gol, kartochka, VAR voqealarini o'yin davomida kanalga yuborish.
