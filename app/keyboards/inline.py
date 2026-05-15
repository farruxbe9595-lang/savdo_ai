from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.config import settings


def review_keyboard(job_id: int, recommended_topic: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ Tavsiya topicga joylash: {recommended_topic}", callback_data=f"post:{job_id}:{recommended_topic}")],
        [InlineKeyboardButton(text="📂 Topicni o‘zim tanlayman", callback_data=f"topics:{job_id}")],
        [InlineKeyboardButton(text="🔄 Qayta tayyorlash", callback_data=f"regen:{job_id}")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"cancel:{job_id}")],
    ])


def topics_keyboard(job_id: int) -> InlineKeyboardMarkup:
    rows = []
    for name in settings.topics.keys():
        rows.append([InlineKeyboardButton(text=name.replace("_", " ").title(), callback_data=f"post:{job_id}:{name}")])
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga", callback_data=f"back:{job_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
