"""Application settings and configuration management."""

from pathlib import Path
from typing import Literal

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"


class Settings(BaseSettings):
    """Application settings configuration."""

    # ==========================================================================
    # Application
    # ==========================================================================

    APP_NAME: str = "My Stuff API"
    APP_VERSION: str = "1.0.0"

    ENVIRONMENT: Literal[
        "development",
        "staging",
        "production",
    ] = "development"

    DEBUG: bool = False

    API_PREFIX: str = "/api"

    # ==========================================================================
    # Database
    # ==========================================================================

    DATABASE_URL: str = f"sqlite:///{PROJECT_ROOT / 'data' / 'db' / 'mystuff.db'}"
    POSTGRES_POOL_SIZE: int = 10
    POSTGRES_MAX_OVERFLOW: int = 20

    @computed_field
    @property
    def is_sqlite(self) -> bool:
        """Whether the application is using SQLite."""
        return self.DATABASE_URL.startswith("sqlite")

    # ==========================================================================
    # Security
    # ==========================================================================

    SECRET_KEY: str

    ALGORITHM: Literal["HS256"] = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 720
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ==========================================================================
    # Uploads
    # ==========================================================================

    UPLOAD_DIR: Path = DEFAULT_UPLOAD_DIR

    MAX_UPLOAD_SIZE_MB: int = 500

    @computed_field
    @property
    def max_upload_size_bytes(self) -> int:
        """Maximum upload size in bytes."""
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    # ==========================================================================
    # Storage
    # ==========================================================================

    STORAGE_PROVIDER: Literal[
        "local",
        "r2",
        "s3",
    ] = "local"

    S3_ACCESS_KEY_ID: str | None = None
    S3_SECRET_ACCESS_KEY: str | None = None
    S3_ENDPOINT_URL: str | None = None
    S3_BUCKET_NAME: str = "mystuff"
    S3_REGION: str = "auto"
    S3_CUSTOM_DOMAIN: str | None = None

    # ==========================================================================
    # Hugging Face
    # ==========================================================================

    HF_TOKEN: str | None = None

    # ==========================================================================
    # Email
    # ==========================================================================

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@mystuff.app"

    # ==========================================================================
    # Features
    # ==========================================================================

    DEMO_MODE: bool = True

    # ==========================================================================
    # CORS
    # ==========================================================================

    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://localhost:5173",
        "https://mystuff.vercel.app",
    ]

    # ==========================================================================
    # Pydantic Settings
    # ==========================================================================

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()  # pyright: ignore[reportCallIssue]
