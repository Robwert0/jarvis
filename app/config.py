from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-haiku-4-5-20251001"
    whisper_model: str = "small"
    elevenlabs_api_key: str | None = None
    elevenlabs_voice_id: str | None = None
    max_tokens: int = 1024

@lru_cache
def get_settings()-> Settings:
    return Settings()