from __future__ import annotations
import base64, json
from pathlib import Path
from openai import OpenAI
from app.config import settings


def _b64(path: str) -> str:
    return base64.b64encode(Path(path).read_bytes()).decode("utf-8")


def _fallback(frames: list[str], attempt: int = 0) -> dict:
    return {
        "products": [{
            "name": "Mahsulot nomi aniqlashtiriladi",
            "category": "umumiy",
            "topic_key": "umumiy",
            "color": "aniqlashtirish kerak",
            "description": "Mahsulot ko‘rinishi yuborilgan video/rasm kadridan olindi. Narx, o‘lcham va model admin tomonidan aniqlashtiriladi.",
            "caption": "🛍 Yangi mahsulot keldi!\n\n📌 Model: aniqlashtiriladi\n📏 O‘lcham: admin orqali\n🚚 Yetkazib berish: kelishiladi\n\nBuyurtma uchun yozing 👇\n#yangi_mahsulot #savdo",
            "hashtags": ["#yangi_mahsulot", "#savdo"],
            "confidence": 0.35,
            "source_frame_index": 0
        }],
        "recommended_topic": "umumiy",
        "notes": "AI aniqligi past bo‘ldi. Rasm/post tayyorlandi, lekin admin tekshirishi kerak."
    }


def analyze_product_frames(frames: list[str], attempt: int = 0, feedback: str | None = None) -> dict:
    if not settings.openai_api_key:
        return _fallback(frames, attempt)

    client = OpenAI(api_key=settings.openai_api_key)
    topic_keys = ", ".join(settings.topics.keys()) or "kiyim, oyoq_kiyim, umumiy"
    prompt = f"""
Siz xalqaro darajadagi e-commerce merchandiser, fashion/product visual analyst va Telegram savdo kopirayterisiz.
Vazifa: yuborilgan video/rasm kadrlarini real ko‘rib chiqib, undagi mahsulot(lar)ni aniqlash.

QOIDALAR:
1) Mahsulotni ko‘rmasdan uydirmang. Noaniq bo‘lsa confidence pasaytiring.
2) Agar bir nechta mahsulot ko‘rinsa, har birini alohida products ro‘yxatiga kiriting.
3) Kategoriya va topic_key faqat mavjud topiclarga yaqin bo‘lsin. Mavjud topiclar: {topic_keys}
4) Kiyim bo‘lsa: kiyim turi, rang, uslub, kimlar uchun mosligini yozing.
5) Oyoq kiyim bo‘lsa: turi, rang, mavsum, qulaylik haqida yozing.
6) Narxni, brendni, o‘lchamni uydirmang. Kerak bo‘lsa “o‘lcham admin orqali aniqlashtiriladi” deb yozing.
7) Caption juda chiroyli, sotuvga mos, ishonchli, qisqa va kuchli bo‘lsin. Uzbek lotin yozuvida yozing.
8) Qayta tayyorlash bo‘lsa, oldingi xatoni tuzatishga harakat qiling.

Admin feedback: {feedback or 'yo‘q'}
Urinish raqami: {attempt}

Faqat JSON qaytaring:
{{
 "products":[{{
   "name":"aniq mahsulot nomi",
   "category":"kategoriya nomi",
   "topic_key":"{topic_keys.split(',')[0].strip() if topic_keys else 'umumiy'}",
   "color":"rang",
   "description":"1-2 gap real tavsif",
   "caption":"Telegram sotuv posti",
   "hashtags":["#..."],
   "confidence":0.0,
   "source_frame_index":0
 }}],
 "recommended_topic":"topic_key",
 "notes":"admin uchun qisqa izoh"
}}
"""
    content = [{"type": "text", "text": prompt}]
    for f in frames[:settings.frames_per_video]:
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_b64(f)}", "detail": "high"}})
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": content}],
            response_format={"type": "json_object"},
            temperature=0.35,
        )
        data = json.loads(resp.choices[0].message.content)
        if not data.get("products"):
            return _fallback(frames, attempt)
        # Normalize topic
        for p in data.get("products", []):
            p.setdefault("topic_key", p.get("category", "umumiy"))
            p.setdefault("source_frame_index", 0)
        data.setdefault("recommended_topic", data.get("products", [{}])[0].get("topic_key", "umumiy"))
        return data
    except Exception as e:
        data = _fallback(frames, attempt)
        data["notes"] = f"AI xatolik: {e}. Fallback post tayyorlandi."
        return data
