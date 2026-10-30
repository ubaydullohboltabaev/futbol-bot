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

## Jonli rejim

"Jonli o'yinlar" workflow'i har 6 soatda o'zi ishga tushadi va o'yin ketayotganda kanalga yuboradi:
o'yin boshlanishi, gollar (pas bergan bilan), avtogol, o'tkazilgan penalti, qizil kartochka, VAR, tanaffus va yakuniy hisob.

- O'yin bo'lmagan vaqtda so'rov sarflamaydi, faqat kutadi.
- Bepul tarif kuniga 100 so'rov beradi, shuning uchun bot tekshiruvlar orasidagi vaqtni qolgan limitga qarab o'zi tanlaydi
  (odatda 2–6 daqiqa). Pullik tarifda (kuniga 7500 so'rov) har daqiqada tekshiradi.
- **Har kuni soat 09:00 da bot sizga shaxsiy xabarda** shu kungi barcha o'yinlar ro'yxatini tugmalar bilan yuboradi.
  Qaysi o'yinni jonli berishni o'zingiz belgilaysiz (✅ / ▫️). Menyuni qayta olish: botga `/menu` deb yozing.
  Buning uchun `TELEGRAM_ADMIN_ID` secretiga o'z Telegram ID raqamingizni qo'ying (@userinfobot ko'rsatadi)
  va botga bir marta `/start` yozing.
- Menyuda quyidagi **muhim o'yinlar** oldindan belgilangan bo'ladi (`TELEGRAM_ADMIN_ID` bo'lmasa, faqat shular avtomatik beriladi):
  - ligalarda jadvalning top-3 jamoasi o'ynasa (`LIVE_TOP_N`);
  - Chempionlar Ligasi, Osiyo CL, Jahon, Yevro, Osiyo kubogida — pley-off bosqichi;
  - istalgan turnirda `BIG_TEAMS` ro'yxatidagi jamoa (O'zbekiston terma jamoasi, Real, Barselona, Paxtakor va h.k.) o'ynasa.
- Ligani jonli rejimdan butunlay chiqarish uchun `bot/config.py` da unga `"live": False` qo'shing.
- Sariq kartochkalarni ham yuborish uchun Variables'da `LIVE_YELLOW_CARDS=1` qo'ying.
