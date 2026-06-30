from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    anthropic_api_key: str
    anthropic_model: str = "claude-haiku-4-5-20251001"
    max_tokens: int = 1024

    elevenlabs_api_key: str | None = None
    elevenlabs_agent_id: str | None = None

    picovoice_access_key: str | None = None

@lru_cache
def get_settings()-> Settings:
    return Settings()