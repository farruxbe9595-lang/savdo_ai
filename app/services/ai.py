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
            "name": "Yangi mahsulot",
            "category": "umumiy",
            "topic_key": "umumiy",
            "color": "aniqlashtirish kerak",
            "description": "Mahsulot rasmi asosida reklama tayyorlandi. O‘lcham, narx va mavjud ranglar admin orqali aniqlashtiriladi.",
            "caption": "Yangi mahsulot\n\nQulay va kundalik foydalanishga mos. Buyurtma uchun yozing.",
            "poster_title": "YANGI MAHSULOT",
            "poster_subtitle": "Qulay • Zamonaviy • Buyurtma uchun yozing",
            "short_features": ["Qulay", "Zamonaviy", "Kundalik"],
            "hashtags": ["#yangi_mahsulot", "#savdo"],
            "confidence": 0.35,
            "source_frame_index": 0
        }],
        "recommended_topic": "umumiy",
        "notes": "AI aniqligi past bo‘ldi. Admin tekshirishi kerak.",
        "transcript_used": ""
    }


def transcribe_audio(audio_path: str | None) -> str:
    if not audio_path or not settings.enable_audio_transcription or not settings.openai_api_key:
        return ""
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        with open(audio_path, "rb") as f:
            txt = client.audio.transcriptions.create(
                model=settings.transcribe_model,
                file=f,
                response_format="text",
                prompt="Uzbek, Russian, Turkish and mixed marketplace product sale speech. Return clean text."
            )
        return str(txt or "").strip()[:3000]
    except Exception:
        return ""


def analyze_product_frames(frames: list[str], attempt: int = 0, feedback: str | None = None, transcript: str = "") -> dict:
    if not settings.openai_api_key:
        data = _fallback(frames, attempt)
        data["transcript_used"] = transcript
        return data

    client = OpenAI(api_key=settings.openai_api_key)
    topic_keys = ", ".join(settings.topics.keys()) or "kiyim, oyoq_kiyim, umumiy"
    prompt = f"""
Siz professional e-commerce merchandiser, product visual analyst va Telegram savdo kopirayterisiz.
Kadrlarni REAL ko‘rib tahlil qiling. Maqsad: reklama posteri uchun aniq, qisqa va sotuvga mos ma'lumot berish.

MAVJUD TOPICLAR: {topic_keys}
ADMIN FEEDBACK: {feedback or 'yo‘q'}
VIDEO OVOZIDAN TRANSKRIPT: {transcript or 'yo‘q'}
URINISH: {attempt}

QOIDALAR:
1) Uydirmang. Ko‘rinmagan narx, brend, o‘lchamni yozmang.
2) Mahsulot nomi aniq bo‘lsin: masalan “Qora sport krossovka”, “Ayollar ko‘ylagi”.
3) Post qisqa bo‘lsin. Ortiqcha emoji, ortiqcha uzun gaplar kerak emas.
4) Poster ichida yoziladigan matn: nom + 1 qator foyda/afzallik.
5) Video ovozida real ma’lumot bo‘lsa, faqat keraklisini qo‘shing.
6) Agar bir nechta mahsulot bo‘lsa, products ro‘yxatiga alohida kiriting.
7) recommended_topic mavjud topiclardan biriga mos bo‘lsin.
8) Uzbek lotin yozuvida yozing.

Faqat JSON qaytaring:
{{
 "products":[{{
   "name":"aniq mahsulot nomi",
   "category":"kategoriya",
   "topic_key":"mavjud topic key",
   "color":"rang",
   "description":"1 gap: mahsulot haqida real tavsif",
   "caption":"Telegram uchun qisqa post, 2-4 qator",
   "poster_title":"posterda katta yoziladigan nom",
   "poster_subtitle":"posterda kichik yoziladigan 1 qator afzallik",
   "short_features":["3 tagacha qisqa afzallik"],
   "hashtags":["#..."],
   "confidence":0.0,
   "source_frame_index":0
 }}],
 "recommended_topic":"topic_key",
 "notes":"admin uchun qisqa izoh",
 "transcript_used":"transkriptdan olingan foydali ma’lumot yoki bo‘sh"
}}
"""
    content = [{"type": "text", "text": prompt}]
    for f in frames[:settings.frames_per_video]:
        content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_b64(f)}", "detail": "high"}})
    try:
        resp = client.chat.completions.create(
            model=settings.vision_model,
            messages=[{"role": "user", "content": content}],
            response_format={"type": "json_object"},
            temperature=0.25,
        )
        data = json.loads(resp.choices[0].message.content)
        if not data.get("products"):
            return _fallback(frames, attempt)
        for p in data.get("products", []):
            p.setdefault("topic_key", p.get("category", "umumiy"))
            p.setdefault("source_frame_index", 0)
            p.setdefault("poster_title", p.get("name", "Yangi mahsulot"))
            p.setdefault("poster_subtitle", p.get("description", "Buyurtma uchun yozing"))
            p.setdefault("caption", f"{p.get('name','Yangi mahsulot')}\n\n{p.get('description','Buyurtma uchun yozing.')}")
        data.setdefault("recommended_topic", data.get("products", [{}])[0].get("topic_key", "umumiy"))
        data.setdefault("transcript_used", transcript[:800])
        return data
    except Exception as e:
        data = _fallback(frames, attempt)
        data["notes"] = f"AI xatolik: {e}. Fallback post tayyorlandi."
        data["transcript_used"] = transcript
        return data
