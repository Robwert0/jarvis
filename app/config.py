from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    anthropic_api_key: str
    anthropic_model: str = "claude-opus-4-7"
    max_tokens: int = 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
