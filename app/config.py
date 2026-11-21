from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
LogFormat = Literal["text", "json"]


class Settings(BaseSettings):
    """Настройки приложения. Значения берутся из переменных окружения."""

    database_url: str

    # Логирование (см. app/logging_config.py).
    log_level: LogLevel = "INFO"
    log_format: LogFormat = "text"
    log_sql: bool = False
    log_file: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalize_level(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("log_format", mode="before")
    @classmethod
    def _normalize_format(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("log_file", mode="before")
    @classmethod
    def _empty_file_is_none(cls, value: object) -> object:
        return value or None


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
