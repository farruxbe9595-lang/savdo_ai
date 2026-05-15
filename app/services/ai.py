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
            "name": "Video asosida aniqlangan mahsulot",
            "category": "umumiy",
            "color": "aniqlashtirish kerak",
            "description": "Mahsulot ko‘rinishi video kadrlaridan olindi. Narx va o‘lcham admin tomonidan kiritiladi.",
            "caption": "🛍 Yangi mahsulot!\n\nVideo/kadrdagi tovar sotuvga tayyorlandi.\n✅ Sifatli ko‘rinish\n✅ Buyurtma Telegram orqali\n✅ Batafsil ma’lumot uchun adminga yozing\n\n#yangi_mahsulot #savdo",
            "hashtags": ["#yangi_mahsulot", "#savdo"],
            "confidence": 0.45,
            "source_frame": frames[0] if frames else None
        }],
        "recommended_topic": "umumiy",
        "notes": "OPENAI_API_KEY yo‘q yoki AI javob bermadi. Fallback post tayyorlandi."
    }


def analyze_product_frames(frames: list[str], attempt: int = 0, feedback: str | None = None) -> dict:
    if not settings.openai_api_key:
        return _fallback(frames, attempt)
    client = OpenAI(api_key=settings.openai_api_key)
    content = [{"type": "text", "text": f"""
Siz professional e-commerce AI merchandiser va Telegram savdo post kopirayterisiz.
Video kadrlarini ko‘rib, mahsulotlarni aniqlang. Agar bir nechta tovar bo‘lsa, hammasini alohida yozing.
Muhim: mahsulotga mos category tanlang: oyoq_kiyim, ayollar_kiyimi, erkaklar_kiyimi, bolalar, uy_rozgor, kosmetika, aksessuar, umumiy.
Har bir mahsulot uchun sotuvga kuchli, ishonchli, o‘zbekcha lotin yozuvida caption yozing.
Narxni uydirmang. O‘lcham noma’lum bo‘lsa 'o‘lcham aniqlashtiriladi' deb yozing.
Qayta generatsiya urinish raqami: {attempt}. Admin feedback: {feedback or 'yo‘q'}.
Faqat JSON qaytaring:
{{"products":[{{"name":"...","category":"...","color":"...","description":"...","caption":"...","hashtags":["#..."],"confidence":0.0}}],"recommended_topic":"...","notes":"..."}}
"""}]
    for f in frames[:settings.frames_per_video]:
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_b64(f)}"}})
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": content}],
            response_format={"type":"json_object"},
            temperature=0.55,
        )
        data = json.loads(resp.choices[0].message.content)
        if not data.get("products"):
            return _fallback(frames, attempt)
        return data
    except Exception as e:
        data = _fallback(frames, attempt)
        data["notes"] = f"AI xatolik: {e}. Fallback post tayyorlandi."
        return data
