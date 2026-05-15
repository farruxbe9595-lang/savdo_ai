from aiogram import Bot
from aiogram.types import FSInputFile
from app.config import settings


def compose_preview_text(job_id: int, result: dict) -> str:
    topic = result.get("recommended_topic", "umumiy")
    p = (result.get("products") or [{}])[0]
    lines = [
        f"✅ #{job_id} buyurtma tayyor",
        "",
        f"📌 Tavsiya topic: {topic}",
        "",
        f"🛍 Mahsulot: {p.get('name','Noma’lum')}",
        f"Kategoriya: {p.get('category','umumiy')}",
        f"Ishonchlilik: {int(float(p.get('confidence',0))*100)}%",
        "",
        p.get("caption", ""),
    ]
    if result.get("transcript_used"):
        lines += ["", "🎙 Video ovozidan foydali ma’lumot qo‘shildi."]
    if result.get("notes"):
        lines += ["", f"ℹ️ {result['notes']}"]
    return "\n".join(lines)[:3900]


async def send_final_post(bot: Bot, topic_name: str, result: dict, images: list[str]) -> None:
    thread_id = settings.topics.get(topic_name, settings.topics.get("umumiy", 0))
    p = (result.get("products") or [{}])[0]
    caption = p.get("caption") or p.get("description") or p.get("name", "Mahsulot")
    if images:
        # One final professional poster only
        await bot.send_photo(settings.target_group_id, FSInputFile(images[0]), caption=caption[:1024], message_thread_id=thread_id or None)
    else:
        await bot.send_message(settings.target_group_id, caption[:3900], message_thread_id=thread_id or None)
