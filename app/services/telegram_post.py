from aiogram import Bot
from aiogram.types import FSInputFile
from app.config import settings


def _topic_key(key: str | None) -> str:
    key = (key or "umumiy").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "oyoqkiyim": "oyoq_kiyim",
        "oyoq_kiyimlar": "oyoq_kiyim",
        "poyabzal": "oyoq_kiyim",
        "krossovka": "oyoq_kiyim",
        "sport_krossovka": "oyoq_kiyim",
        "ayollar_kiyimi": "kiyim",
        "erkaklar_kiyimi": "kiyim",
        "kiyimlar": "kiyim",
    }
    key = aliases.get(key, key)
    if key not in settings.topics and "oyoq" in key:
        return "oyoq_kiyim"
    if key not in settings.topics and "kiyim" in key:
        return "kiyim"
    return key


def make_sale_caption(result: dict) -> str:
    p = (result.get("products") or [{}])[0]
    name = p.get("name") or "Yangi mahsulot"
    desc = p.get("description") or "Qulay va kundalik foydalanishga mos."
    features = p.get("short_features") or []
    lines = [f"🛍 {name}", ""]
    if features:
        lines.append(" • ".join([str(x) for x in features[:3]]))
    else:
        lines.append(desc)
    lines.append("Buyurtma uchun yozing.")
    return "\n".join(lines)[:1024]


def compose_preview_text(job_id: int, result: dict) -> str:
    topic = _topic_key(result.get("recommended_topic", "umumiy"))
    p = (result.get("products") or [{}])[0]
    return "\n".join([
        f"✅ #{job_id} buyurtma tayyor",
        "",
        f"📌 Tavsiya topic: {topic}",
        "",
        f"🛍 Mahsulot: {p.get('name','Noma’lum')}",
        f"Kategoriya: {_topic_key(p.get('topic_key') or p.get('category'))}",
        f"Ishonchlilik: {int(float(p.get('confidence',0))*100)}%",
        "",
        make_sale_caption(result),
        "",
        "ℹ️ Rasm ichida matn yo‘q. Post matni rasm ostida alohida caption bo‘lib joylanadi."
    ])[:3900]


async def send_final_post(bot: Bot, topic_name: str, result: dict, images: list[str]) -> None:
    topic_name = _topic_key(topic_name)
    thread_id = settings.topics.get(topic_name)
    caption = make_sale_caption(result)
    kwargs = {}
    if thread_id:
        kwargs["message_thread_id"] = int(thread_id)
    if images:
        await bot.send_photo(settings.target_group_id, FSInputFile(images[0]), caption=caption, **kwargs)
    else:
        await bot.send_message(settings.target_group_id, caption, **kwargs)
