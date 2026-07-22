"""
Single application entrypoint.

Registers:
- REST routes
- WebSocket handlers
- Accent profile endpoints
- Static upload serving
"""

import os
import sys
from typing import Any

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.requests import Request

from app.api.routes.auth import router as auth_router
from app.api.routes.collections import router as collection_router
from app.api.routes.files import router as files_router
from app.api.routes.health import router as health_router
from app.api.routes.logs import router as logs_router
from app.api.routes.media import router as media_router
from app.api.routes.notes import router as notes_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.users import router as users_router
from app.api.websocket.dictate import router as dictate_ws_router
from app.api.websocket.lyrics import router as lyrics_ws_router
from app.api.websocket.notifications import router as notifications_ws_router
from app.api.websocket.telemetry import router as telemetry_ws_router
from app.core.config import settings
from app.core.errors import UserAlreadyExistsError
from app.core.lifespan import lifespan
from app.services.transcription_service import TranscriptionService

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="My Stuff — file, note, media management + AI dictation API",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Upload storage
settings.UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


app.mount(
    "/uploads",
    StaticFiles(directory=str(settings.UPLOAD_DIR)),
    name="uploads",
)


# REST
app.include_router(
    health_router,
    prefix="/api/health",
    tags=["Health"],
)

app.include_router(
    auth_router,
    prefix="/api/auth",
    tags=["Auth"],
)

app.include_router(
    collection_router,
    prefix="/api/files/collections",
    tags=["Collections"],
)

app.include_router(
    users_router,
    prefix="/api/users",
    tags=["Users"],
)

app.include_router(
    files_router,
    prefix="/api/files",
    tags=["Files"],
)

app.include_router(
    notes_router,
    prefix="/api/notes",
    tags=["Notes"],
)

app.include_router(
    media_router,
    prefix="/api/media",
    tags=["Media"],
)

app.include_router(
    logs_router,
    prefix="/api/logs",
    tags=["Logs"],
)

app.include_router(
    notifications_router,
    prefix="/api/notifications",
    tags=["Notifications"],
)


# WebSockets
app.include_router(dictate_ws_router)
app.include_router(lyrics_ws_router)
app.include_router(telemetry_ws_router)
app.include_router(notifications_ws_router)


class CorrectionRequest(BaseModel):
    raw: str
    corrected: str


@app.post("/api/accent/correct", tags=["AI / Accent"])
async def accent_correct(
    body: CorrectionRequest,
) -> dict[str, Any]:
    return TranscriptionService.submit_correction(
        body.raw,
        body.corrected,
    )


@app.get("/api/accent/profile", tags=["AI / Accent"])
async def accent_profile() -> dict[str, Any]:
    return TranscriptionService.get_profile()


@app.delete("/api/accent/forget/{word}", tags=["AI / Accent"])
async def accent_forget(
    word: str,
) -> dict[str, Any]:
    return TranscriptionService.forget_correction(word)


@app.get("/")
async def root() -> dict[str, Any]:
    return {
        "message": f"{settings.APP_NAME} is running",
        "docs": "/docs",
        "version": settings.APP_VERSION,
    }


@app.exception_handler(UserAlreadyExistsError)
async def user_exists_exception_handler(
    _request: Request,
    exc: UserAlreadyExistsError,
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "detail": str(exc),
        },
    )


if __name__ == "__main__":

    port = int(os.environ.get("PORT", 8000))

    print(f"🚀 API     → http://localhost:{port}/docs")
    print(f"🎙 Dictate → ws://localhost:{port}/ws/dictate")
    print(f"🎵 Lyrics  → ws://localhost:{port}/ws/lyrics")
    print(f"🔔 Notify  → ws://localhost:{port}/ws/notifications")
    print(f"🧠 Accent  → http://localhost:{port}/api/accent/profile")

    try:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=port,
        )

    except KeyboardInterrupt:
        sys.exit(0)
