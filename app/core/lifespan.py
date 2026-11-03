"""FastAPI lifespan management and startup tasks."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.core.config import settings
from app.core.logger import setup_logging


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    """Lifespan.

    Args:
        _ (FastAPI): The  .

    Returns:
        AsyncGenerator[None]: AsyncGenerator[None] result.
    """
    setup_logging()

    upload_dir = Path(settings.UPLOAD_DIR)

    upload_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    for subdir in [
        "images",
        "videos",
        "audio",
        "files",
        "gifs",
    ]:
        (upload_dir / subdir).mkdir(
            parents=True,
            exist_ok=True,
        )

    yield
