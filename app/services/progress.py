import asyncio


async def update_progress(bot, chat_id: int, message_id: int, percent: int, text: str):
    bar_len = 10
    filled = max(0, min(bar_len, percent // 10))
    bar = "🟩" * filled + "⬜" * (bar_len - filled)

    msg = (
        f"⏳ Jarayon: {percent}%\n"
        f"{bar}\n\n"
        f"📌 {text}"
    )

    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=msg
        )
    except Exception:
        pass

    await asyncio.sleep(0.3)
