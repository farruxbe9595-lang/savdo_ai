from __future__ import annotations
import asyncio, json, shutil
from pathlib import Path
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, FSInputFile
from app.config import settings
from app.db.models import init_db
from app.db import repo
from app.services.video import extract_frames, prepare_image_frame
from app.services.ai import analyze_product_frames
from app.services.render import make_ad_cards
from app.services.telegram_post import compose_preview_text, send_final_post
from app.keyboards.inline import review_keyboard, topics_keyboard

bot = Bot(settings.bot_token)
dp = Dispatcher()
job_queue: asyncio.Queue[int] = asyncio.Queue()
semaphore = asyncio.Semaphore(settings.max_parallel_jobs)

def is_admin(user_id: int) -> bool:
    return not settings.admin_id_list or user_id in settings.admin_id_list

@dp.message(CommandStart())
async def start(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Siz admin ro‘yxatida emassiz.")
        return
    await message.answer("🤖 AI Video Market Poster Bot tayyor. Video yuboring — bot navbatga qo‘yadi, analiz qiladi va preview beradi. /status orqali holatni ko‘rasiz.")

@dp.message(Command("status"))
async def status(message: Message):
    jobs = repo.list_recent(message.from_user.id, 15)
    if not jobs:
        await message.answer("Hali buyurtma yo‘q.")
        return
    text = "📊 Oxirgi buyurtmalar:\n\n" + "\n".join([f"#{j.id} — {j.status}" for j in jobs])
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
        await message.answer("Video yoki rasm topilmadi. Oddiy video, dumaloq video-message yoki rasm yuboring.")
        return

    # file_id ichida media turini ham saqlaymiz, DB sxemasini buzmaslik uchun
    job = repo.create_job(message.from_user.id, f"{kind}|{tg_file.file_id}")
    await job_queue.put(job.id)

    label = {"video": "video", "video_note": "dumaloq video-message", "photo": "rasm"}.get(kind, "media")
    await message.answer(f"✅ #{job.id} {label} qabul qilindi. Navbatga qo‘yildi. Tayyor bo‘lganda xabar beraman.")

async def process_job(job_id: int, feedback: str | None = None):
    async with semaphore:
        job = repo.update_job(job_id, status="PROCESSING", attempts=(repo.get_job(job_id).attempts + 1 if repo.get_job(job_id) else 1))
        if not job: return
        work_dir = Path(settings.temp_dir) / f"job_{job_id}"
        frames_dir = work_dir / "frames"
        ads_dir = work_dir / "ads"
        work_dir.mkdir(parents=True, exist_ok=True)
        try:
            raw_file_id = job.file_id
            kind = "video"
            file_id = raw_file_id
            if "|" in raw_file_id:
                kind, file_id = raw_file_id.split("|", 1)

            media_path = work_dir / ("input.jpg" if kind == "photo" else "input.mp4")
            tg_file = await bot.get_file(file_id)
            await bot.download_file(tg_file.file_path, destination=media_path)
            repo.update_job(job_id, video_path=str(media_path))

            if kind == "photo":
                frames = prepare_image_frame(str(media_path), str(frames_dir))
            else:
                frames = extract_frames(str(media_path), str(frames_dir), settings.frames_per_video)
            if not frames:
                raise RuntimeError("Media fayldan sifatli kadr ajratib bo‘lmadi.")

            result = analyze_product_frames(frames, attempt=job.attempts, feedback=feedback)
            topic = result.get("recommended_topic", "umumiy")
            first_product = result.get("products", [{}])[0]
            frame_index = int(first_product.get("source_frame_index", 0) or 0)
            source_frame = frames[min(max(frame_index, 0), len(frames)-1)]
            cards = make_ad_cards(
                source_frame,
                first_product.get("name", "Mahsulot"),
                first_product.get("category", topic),
                str(ads_dir),
                first_product.get("caption", "")
            )
            result["ad_images"] = cards
            repo.update_job(job_id, status="READY_FOR_REVIEW", result_json=json.dumps(result, ensure_ascii=False), recommended_topic=topic)
            await bot.send_message(job.admin_id, compose_preview_text(job_id, result), reply_markup=review_keyboard(job_id, topic))
            for img in cards[:3]:
                await bot.send_photo(job.admin_id, FSInputFile(img))
        except Exception as e:
            repo.update_job(job_id, status="FAILED", error=str(e))
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
    await cb.message.answer(f"🔄 #{job_id} qayta tayyorlanmoqda. Oldingi variantdan boshqacharoq va aniqlashtirilgan preview beriladi.")
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
    job = repo.get_job(job_id)
    if not job or not job.result_json:
        await cb.answer("Natija topilmadi", show_alert=True); return
    result = json.loads(job.result_json)
    images = result.get("ad_images", [])
    try:
        await send_final_post(bot, topic_name, result, images)
        repo.update_job(job_id, status="POSTED", selected_topic=topic_name)
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
