"""Runtime settings for the PolyaBrain backend."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings shared by the local backend."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "PolyaBrain Backend"
    app_version: str = "0.1.0"
    environment: str = Field(default="local", alias="POLYABRAIN_ENV")
    log_level: str = Field(default="INFO", alias="POLYABRAIN_LOG_LEVEL")
    secret_key: str = Field(default="", alias="POLYABRAIN_SECRET_KEY")
    database_url: str = Field(
        default="postgresql+psycopg://polyabrain:polyabrain@localhost:5432/polyabrain",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")


@lru_cache
def get_settings() -> Settings:
    """Return cached settings so app startup and tests share one config object."""
    return Settings()
