import json
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    bot_token: str = Field(alias="BOT_TOKEN")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    admin_ids: str = Field(default="", alias="ADMIN_IDS")
    target_group_id: int = Field(default=0, alias="TARGET_GROUP_ID")
    topics_json: str = Field(default='{"umumiy":0}', alias="TOPICS_JSON")
    max_parallel_jobs: int = Field(default=1, alias="MAX_PARALLEL_JOBS")
    frames_per_video: int = Field(default=10, alias="FRAMES_PER_VIDEO")
    db_path: str = Field(default="data/bot.db", alias="DB_PATH")
    storage_dir: str = Field(default="data", alias="STORAGE_DIR")
    temp_dir: str = Field(default="temp", alias="TEMP_DIR")
    require_admin_approval: bool = Field(default=True, alias="REQUIRE_ADMIN_APPROVAL")

    # Image generation — endi Pollinations.ai (bepul, API kalit kerakmas)
    enable_ai_image_gen: bool = Field(default=True, alias="ENABLE_AI_IMAGE_GEN")
    # OpenAI faqat vision tahlil va transkripsiya uchun (agar kerak bo'lsa)
    enable_audio_transcription: bool = Field(default=True, alias="ENABLE_AUDIO_TRANSCRIPTION")
    image_model: str = Field(default="gpt-image-1", alias="OPENAI_IMAGE_MODEL")
    vision_model: str = Field(default="gpt-4o-mini", alias="OPENAI_VISION_MODEL")
    transcribe_model: str = Field(default="gpt-4o-mini-transcribe", alias="OPENAI_TRANSCRIBE_MODEL")

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def admin_id_list(self) -> list[int]:
        return [int(x.strip()) for x in self.admin_ids.split(",") if x.strip().isdigit()]

    @property
    def topics(self) -> dict[str, int]:
        try:
            return {str(k): int(v) for k, v in json.loads(self.topics_json).items()}
        except Exception:
            return {"umumiy": 0}


settings = Settings()
Path(settings.storage_dir).mkdir(parents=True, exist_ok=True)
Path(settings.temp_dir).mkdir(parents=True, exist_ok=True)
Path(Path(settings.db_path).parent).mkdir(parents=True, exist_ok=True)
