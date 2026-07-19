"""Application settings and configuration management."""

from typing import Literal

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"


class Settings(BaseSettings):
    """Application settings configuration."""

    APP_NAME: str = "My Stuff API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    API_PREFIX: str = "/api"

    DATABASE_URL: str = "sqlite:///./mystuff.db"

    SECRET_KEY: str = "OoprAVGnRFk9ui77CEIo8H-XQJV3BOFW8WmZNLpkGwc"
    ALGORITHM: Literal["HS256"] = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 720  # 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    UPLOAD_DIR: Path = DEFAULT_UPLOAD_DIR
    MAX_UPLOAD_SIZE_MB: int = 500

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@mystuff.app"

    DEMO_MODE: bool = True

    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://localhost:5173",
        "https://mystuff.vercel.app"
    ]

    @computed_field
    @property
    def max_upload_size_bytes(self) -> int:
        """Calculate max upload size in bytes."""
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
    )


settings = Settings()
