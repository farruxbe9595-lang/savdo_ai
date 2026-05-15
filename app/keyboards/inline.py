from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.config import settings


def review_keyboard(job_id: int, recommended_topic: str) -> InlineKeyboardMarkup:
    """
    Admin uchun eng sodda review panel:
    1) Tayyor reklamani guruhga yuborish
    2) Reklamani qayta tayyorlash
    """

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Guruhga yuborish",
                    callback_data=f"post:{job_id}:{recommended_topic}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔁 Qayta tayyorlash",
                    callback_data=f"regen:{job_id}",
                )
            ],
        ]
    )


def topics_keyboard(job_id: int) -> InlineKeyboardMarkup:
    """
    Eski main.py importi buzilmasligi uchun qoldirildi.
    Lekin review_keyboard ichida topic tanlash tugmasi endi ko‘rinmaydi.
    """
    rows = []

    for name in settings.topics.keys():
        rows.append(
            [
                InlineKeyboardButton(
                    text=name.replace("_", " ").title(),
                    callback_data=f"post:{job_id}:{name}",
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Orqaga",
                callback_data=f"back:{job_id}",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)
