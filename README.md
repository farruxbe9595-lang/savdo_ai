# AI Video Market Poster Bot

Telegram savdo guruhi uchun AI bot: admin video yuboradi, bot videoni navbatga oladi, mahsulotlarni tahlil qiladi, sotuv posti va 3 xil reklama rasm formatini tayyorlaydi, admin tasdiqlasa kerakli forum topicga joylaydi.

## Yakuniy imkoniyatlar

- Bir vaqtning o‘zida ko‘p video qabul qiladi.
- Har bir video avtomatik buyurtma raqami oladi: `#1`, `#2`, `#3`...
- Bot video tahlil qilayotgan paytda ham yangi videolarni qabul qiladi.
- Navbat tizimi bor: `QUEUED`, `PROCESSING`, `READY_FOR_REVIEW`, `POSTED`, `FAILED`.
- Videodan kadrlar ajratadi.
- OpenAI Vision orqali mahsulotni aniqlaydi.
- Videoda bir nechta mahsulot bo‘lsa, ularni post matnida alohida ko‘rsatadi.
- Mahsulotga mos category/topic tavsiya qiladi.
- 3 ta reklama rasmi tayyorlaydi:
  - Telegram/Instagram post: 1080x1080
  - Story: 1080x1920
  - Wide banner: 1280x720
- Admin preview oladi.
- Admin tugmalari:
  - Tavsiya qilingan topicga joylash
  - Topicni qo‘lda tanlash
  - Qayta tayyorlash
  - Bekor qilish
- Guruh topicga yuborish uchun `message_thread_id` ishlatiladi.
- Railway deployga tayyor.
- GitHubga yuklashga tayyor.

## Muhim eslatma

Bu MVP mahsulotning asl kadrini reklama dizayn ichida saqlaydi. Odam kiyib turgan yangi AI mockup generatsiyasi keyingi PRO bosqichda OpenAI Image API yoki boshqa image-model orqali qo‘shiladi. Hozirgi versiya real savdo uchun xavfsizroq: mahsulotni buzib yubormaydi, asl kadrdan foydalanadi.

## O‘rnatish

```bash
git clone YOUR_REPO_URL
cd ai_video_market_poster_bot
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```

## .env sozlamalari

```env
BOT_TOKEN=123456:YOUR_TELEGRAM_BOT_TOKEN
OPENAI_API_KEY=sk-your-openai-key
ADMIN_IDS=123456789
TARGET_GROUP_ID=-1001234567890
TOPICS_JSON={"oyoq_kiyim":11,"ayollar_kiyimi":12,"erkaklar_kiyimi":13,"bolalar":14,"uy_rozgor":15,"kosmetika":16,"aksessuar":17,"umumiy":18}
MAX_PARALLEL_JOBS=1
FRAMES_PER_VIDEO=10
DB_PATH=/app/storage/bot.db
STORAGE_DIR=/app/storage
TEMP_DIR=/app/temp
```

## Telegram forum topic ID olish

Guruh forum/topic rejimida bo‘lishi kerak. Botni guruhga admin qiling. Har bir topic uchun `message_thread_id` kerak bo‘ladi. Uni olishning eng oson yo‘li:

1. Botga vaqtincha update log qo‘shish yoki boshqa helper bot orqali topicdagi xabarni tekshirish.
2. Topicda xabar yuborilganda Telegram update ichida `message_thread_id` ko‘rinadi.
3. Shu raqamni `.env` ichidagi `TOPICS_JSON` ga yozasiz.

## Railway deploy

1. GitHubga yuklang.
2. Railway → New Project → Deploy from GitHub.
3. Variables bo‘limiga `.env.example` dagi qiymatlarni kiriting.
4. Volume qo‘shish tavsiya qilinadi:
   - Mount path: `/app/storage`
5. Deploy qiling.

## Ishlash tartibi

1. Admin botga video yuboradi.
2. Bot javob beradi: `#12 video qabul qilindi`.
3. Bot video kadrlarini tahlil qiladi.
4. Tayyor bo‘lsa admin bot ichida preview ko‘radi.
5. Admin tugmalardan birini bosadi.
6. Tasdiqlansa reklama kerakli topicga joylanadi.

## Keyingi PRO bosqichlar

- Narx va o‘lcham so‘rash formasi.
- Kiyim/oyoq kiyim uchun modelda kiyib ko‘rsatilgan AI mockup.
- Har bir mahsulotni videodan alohida crop qilish.
- Post matnini A/B variantlarda chiqarish.
- Operator izohi bilan qayta generatsiya: “rangni noto‘g‘ri topdi”, “captionni qisqaroq qil”.
- Admin web panel.
- Buyurtmalar statistikasi.
- Instagram/TikTok/Reels post format eksporti.
- CRM va mijozlar bazasi.
