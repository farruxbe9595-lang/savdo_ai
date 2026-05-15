from aiogram import Bot
from aiogram.types import FSInputFile
from app.config import settings


def compose_preview_text(job_id: int, result: dict) -> str:
    topic = result.get("recommended_topic", "umumiy")
    lines = [f"✅ #{job_id} buyurtma tayyor", "", f"📌 Tavsiya topic: {topic}", ""]
    for i,p in enumerate(result.get("products", []), 1):
        lines += [f"🛍 Mahsulot {i}: {p.get('name','Noma’lum')}", f"Kategoriya: {p.get('category','umumiy')}", f"Ishonchlilik: {int(float(p.get('confidence',0))*100)}%", "", p.get("caption", ""), ""]
    if result.get("notes"):
        lines.append(f"ℹ️ {result['notes']}")
    return "\n".join(lines)[:3900]

async def send_final_post(bot: Bot, topic_name: str, result: dict, images: list[str]) -> None:
    thread_id = settings.topics.get(topic_name, settings.topics.get("umumiy", 0))
    for idx,p in enumerate(result.get("products", []), 1):
        caption = p.get("caption") or p.get("description") or p.get("name", "Mahsulot")
        if images:
            await bot.send_photo(settings.target_group_id, FSInputFile(images[0]), caption=caption[:1024], message_thread_id=thread_id or None)
            for img in images[1:3]:
                await bot.send_photo(settings.target_group_id, FSInputFile(img), message_thread_id=thread_id or None)
        else:
            await bot.send_message(settings.target_group_id, caption[:3900], message_thread_id=thread_id or None)
