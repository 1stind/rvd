"""
Application configuration.
Loads settings from environment variables (.env).
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Web Voting Championship"
    APP_VERSION: str = "1.0.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # postgresql+asyncpg://... untuk production.
    # sqlite+aiosqlite:///./web_voting.db untuk dev/test tanpa Postgres.
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/web_voting"
    SECRET_KEY: str = "change-this-secret-key"

    MIDTRANS_SERVER_KEY: str = ""
    MIDTRANS_CLIENT_KEY: str = ""
    MIDTRANS_IS_PRODUCTION: bool = False
    APP_BASE_URL: str = "http://localhost:8000"

    REDIS_URL: str = "redis://localhost:6379/0"
    CLOUDFLARE_API_KEY: str = ""
    MAX_ACTIVE_USER: int = 500

    JWT_SECRET_KEY: str = "change-this-secret-key"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.SECRET_KEY == "change-this-secret-key":
            raise RuntimeError("SECRET_KEY must be set to a secure value in production")

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")

    @property
    def is_redis_available(self) -> bool:
        return bool(self.REDIS_URL) and not self.REDIS_URL.startswith("memory://")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

# Diagnostic startup log — logs driver type and source without exposing credentials.
import logging as _logging
_driver = settings.DATABASE_URL.split("://", 1)[0] if "://" in settings.DATABASE_URL else "unknown"
_logging.getLogger("app.core.config").warning(
    "DB diag: driver=%s is_sqlite=%s",
    _driver, settings.is_sqlite,
)
