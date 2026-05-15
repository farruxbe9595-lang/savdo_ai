from __future__ import annotations

import asyncio
import json
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, FSInputFile

from app.config import settings
from app.db.models import init_db
from app.db import repo
from app.services.video import extract_frames, prepare_image_frame, extract_audio
from app.services.ai import analyze_product_frames, transcribe_audio
from app.services.image_gen import generate_product_visuals
from app.services.render import make_final_poster
from app.services.telegram_post import compose_preview_text, send_final_post, _topic_key
from app.services.progress import update_progress
from app.keyboards.inline import review_keyboard, topics_keyboard


bot = Bot(settings.bot_token)
dp = Dispatcher()

job_queue: asyncio.Queue[int] = asyncio.Queue()
semaphore = asyncio.Semaphore(settings.max_parallel_jobs)
PROGRESS_MESSAGES: dict[int, dict[str, int]] = {}


def is_admin(user_id: int) -> bool:
    return not settings.admin_id_list or user_id in settings.admin_id_list


async def progress(job_id: int, percent: int, text: str):
    data = PROGRESS_MESSAGES.get(job_id)
    if not data:
        return

    await update_progress(
        bot=bot,
        chat_id=data["chat_id"],
        message_id=data["message_id"],
        job_id=job_id,
        percent=percent,
        text=text,
    )


@dp.message(CommandStart())
async def start(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Siz admin ro‘yxatida emassiz.")
        return

    await message.answer(
        "🤖 SavdoAI PRO tayyor.\n\n"
        "Rasm, video yoki dumaloq video yuboring — bot mahsulotni analiz qiladi, "
        "professional reklama poster tayyorlaydi va topicga joylashdan oldin preview beradi."
    )


@dp.message(Command("status"))
async def status(message: Message):
    jobs = repo.list_recent(message.from_user.id, 15)
    if not jobs:
        await message.answer("Hali buyurtma yo‘q.")
        return

    text = "📊 Oxirgi buyurtmalar:\n\n" + "\n".join(
        [f"#{j.id} — {j.status}" for j in jobs]
    )
    await message.answer(text)


@dp.message(F.video | F.document | F.video_note | F.photo)
async def receive_media(message: Message):
    if not is_admin(message.from_user.id):
        return

    kind = "video"
    tg_file = None

    if message.video:
        tg_file = message.video
        kind = "video"
    elif message.video_note:
        tg_file = message.video_note
        kind = "video_note"
    elif message.photo:
        tg_file = message.photo[-1]
        kind = "photo"
    elif message.document:
        mime = message.document.mime_type or ""
        if mime.startswith("video/"):
            tg_file = message.document
            kind = "video"
        elif mime.startswith("image/"):
            tg_file = message.document
            kind = "photo"
        else:
            await message.answer("Iltimos, video yoki rasm yuboring.")
            return

    if not tg_file:
        await message.answer("Video yoki rasm topilmadi.")
        return

    job = repo.create_job(message.from_user.id, f"{kind}|{tg_file.file_id}")

    progress_msg = await message.answer(
        f"⏳ #{job.id} jarayon: 5%\n"
        f"🟩⬜⬜⬜⬜⬜⬜⬜⬜⬜\n\n"
        f"📌 Media qabul qilindi. Navbatga qo‘yildi..."
    )

    PROGRESS_MESSAGES[job.id] = {
        "chat_id": message.chat.id,
        "message_id": progress_msg.message_id,
    }

    await job_queue.put(job.id)


async def process_job(job_id: int, feedback: str | None = None):
    async with semaphore:
        current = repo.get_job(job_id)

        job = repo.update_job(
            job_id,
            status="PROCESSING",
            attempts=(current.attempts + 1 if current else 1),
        )

        if not job:
            return

        work_dir = Path(settings.temp_dir) / f"job_{job_id}"
        frames_dir = work_dir / "frames"
        visuals_dir = work_dir / "visuals"
        ads_dir = work_dir / "ads"
        work_dir.mkdir(parents=True, exist_ok=True)

        try:
            await progress(job_id, 10, "Fayl yuklab olinmoqda...")

            raw_file_id = job.file_id
            kind = "video"
            file_id = raw_file_id

            if "|" in raw_file_id:
                kind, file_id = raw_file_id.split("|", 1)

            media_path = work_dir / ("input.jpg" if kind == "photo" else "input.mp4")

            tg_file = await bot.get_file(file_id)
            await bot.download_file(tg_file.file_path, destination=media_path)
            repo.update_job(job_id, video_path=str(media_path))

            await progress(job_id, 25, "Rasm yoki video kadrlari tayyorlanmoqda...")

            transcript = ""

            if kind == "photo":
                frames = prepare_image_frame(str(media_path), str(frames_dir))
            else:
                frames = extract_frames(
                    str(media_path),
                    str(frames_dir),
                    settings.frames_per_video,
                )

                await progress(job_id, 35, "Video ovozi ajratilmoqda...")

                audio_path = extract_audio(str(media_path), str(work_dir / "audio"))
                transcript = transcribe_audio(audio_path)

            if not frames:
                raise RuntimeError("Media fayldan sifatli kadr ajratib bo‘lmadi.")

            await progress(job_id, 45, "AI mahsulotni tahlil qilmoqda...")

            result = analyze_product_frames(
                frames,
                attempt=job.attempts,
                feedback=feedback,
                transcript=transcript,
            )

            topic = _topic_key(result.get("recommended_topic", "umumiy"))
            result["recommended_topic"] = topic

            if result.get("products"):
                result["products"][0]["topic_key"] = _topic_key(
                    result["products"][0].get("topic_key")
                    or result["products"][0].get("category")
                )

            first_product = (result.get("products") or [{}])[0]
            frame_index = int(first_product.get("source_frame_index", 0) or 0)
            source_frame = frames[min(max(frame_index, 0), len(frames) - 1)]

            await progress(job_id, 65, "AI reklama rasmlari generatsiya qilinmoqda...")

            generated = generate_product_visuals(
                source_frame,
                first_product,
                str(visuals_dir),
            )

            await progress(job_id, 85, "Final reklama poster tayyorlanmoqda...")

            final_poster = make_final_poster(
                source_frame,
                generated,
                first_product,
                str(ads_dir),
            )

            result["ad_images"] = [final_poster]

            repo.update_job(
                job_id,
                status="READY_FOR_REVIEW",
                result_json=json.dumps(result, ensure_ascii=False),
                recommended_topic=topic,
            )

            await progress(job_id, 100, "Tayyor. Preview yuborilmoqda...")

            await bot.send_message(
                job.admin_id,
                compose_preview_text(job_id, result),
                reply_markup=review_keyboard(job_id, topic),
            )

            await bot.send_photo(job.admin_id, FSInputFile(final_poster))

        except Exception as e:
            repo.update_job(job_id, status="FAILED", error=str(e))
            await progress(job_id, 100, f"Xatolik yuz berdi: {e}")
            await bot.send_message(job.admin_id, f"❌ #{job_id} xatolik: {e}")


async def worker_loop():
    while True:
        job_id = await job_queue.get()
        asyncio.create_task(process_job(job_id))
        job_queue.task_done()


@dp.callback_query(F.data.startswith("topics:"))
async def choose_topic(cb: CallbackQuery):
    job_id = int(cb.data.split(":")[1])
    await cb.message.edit_reply_markup(reply_markup=topics_keyboard(job_id))
    await cb.answer()


@dp.callback_query(F.data.startswith("back:"))
async def back(cb: CallbackQuery):
    job_id = int(cb.data.split(":")[1])
    job = repo.get_job(job_id)
    topic = job.recommended_topic if job else "umumiy"

    await cb.message.edit_reply_markup(reply_markup=review_keyboard(job_id, topic))
    await cb.answer()


@dp.callback_query(F.data.startswith("regen:"))
async def regenerate(cb: CallbackQuery):
    job_id = int(cb.data.split(":")[1])
    repo.update_job(job_id, status="REGENERATING")

    progress_msg = await cb.message.answer(
        f"⏳ #{job_id} jarayon: 5%\n"
        f"🟩⬜⬜⬜⬜⬜⬜⬜⬜⬜\n\n"
        f"📌 Qayta tayyorlash boshlandi..."
    )

    PROGRESS_MESSAGES[job_id] = {
        "chat_id": cb.message.chat.id,
        "message_id": progress_msg.message_id,
    }

    await job_queue.put(job_id)
    await cb.answer()


@dp.callback_query(F.data.startswith("cancel:"))
async def cancel(cb: CallbackQuery):
    job_id = int(cb.data.split(":")[1])
    repo.update_job(job_id, status="CANCELLED")

    await cb.message.answer(f"❌ #{job_id} bekor qilindi.")
    await cb.answer()


@dp.callback_query(F.data.startswith("post:"))
async def post(cb: CallbackQuery):
    _, job_id_s, topic_name = cb.data.split(":", 2)

    job_id = int(job_id_s)
    topic_name = _topic_key(topic_name)

    job = repo.get_job(job_id)

    if not job or not job.result_json:
        await cb.answer("Natija topilmadi", show_alert=True)
        return

    result = json.loads(job.result_json)
    images = result.get("ad_images", [])

    try:
        await send_final_post(bot, topic_name, result, images)

        repo.update_job(
            job_id,
            status="POSTED",
            selected_topic=topic_name,
        )

        await cb.message.answer(f"✅ #{job_id} reklama joylandi. Topic: {topic_name}")

    except Exception as e:
        repo.update_job(job_id, status="FAILED", error=str(e))
        await cb.message.answer(f"❌ Joylashda xatolik: {e}")

    await cb.answer()


async def main():
    init_db()
    asyncio.create_task(worker_loop())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
