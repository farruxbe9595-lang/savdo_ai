import asyncio


def progress_text(job_id: int, percent: int, text: str) -> str:
    bar_len = 10
    filled = max(0, min(bar_len, percent // 10))
    bar = "🟩" * filled + "⬜" * (bar_len - filled)

    return (
        f"⏳ #{job_id} jarayon: {percent}%\n"
        f"{bar}\n\n"
        f"📌 {text}"
    )


async def update_progress(
    bot,
    chat_id: int,
    message_id: int,
    job_id: int,
    percent: int,
    text: str,
):
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=progress_text(job_id, percent, text),
        )
    except Exception:
        pass

    await asyncio.sleep(0.25)
