"""app/main.py
Single application entrypoint.

Registers:
  - REST routes (auth, users, files, notes, media, logs, health)
  - WebSocket handlers (dictate, lyrics, telemetry)
  - Accent-profile REST endpoints (from old standalone main.py)
  - Static file serving for uploads
"""

import os
import socket
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.requests import Request

# ── REST routers ──────────────────────────────────────────────────────────────
from app.api.routes.auth import router as auth_router
from app.api.routes.files import router as files_router
from app.api.routes.health import router as health_router
from app.api.routes.logs import router as logs_router
from app.api.routes.media import router as media_router
from app.api.routes.notes import router as notes_router
from app.api.routes.users import router as users_router

# ── WebSocket routers ─────────────────────────────────────────────────────────
from app.api.websocket.dictate import router as dictate_ws_router
from app.api.websocket.lyrics import router as lyrics_ws_router
from app.api.websocket.telemetry import router as telemetry_ws_router
from app.core.config import settings
from app.core.errors import UserAlreadyExistsError
from app.core.lifespan import lifespan

# ── Accent service (for REST endpoints) ──────────────────────────────────────
from app.services.transcription_service import TranscriptionService

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="My Stuff — file, note, media management + AI dictation API",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static uploads ────────────────────────────────────────────────────────────
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

app.mount(
    "/uploads",
    StaticFiles(directory=settings.UPLOAD_DIR),
    name="uploads",
)

# ── REST routes ───────────────────────────────────────────────────────────────
app.include_router(health_router,  prefix="/api/health",  tags=["Health"])
app.include_router(auth_router,    prefix="/api/auth",    tags=["Auth"])
app.include_router(users_router,   prefix="/api/users",   tags=["Users"])
app.include_router(files_router,   prefix="/api/files",   tags=["Files"])
app.include_router(notes_router,   prefix="/api/notes",   tags=["Notes"])
app.include_router(media_router,   prefix="/api/media",   tags=["Media"])
app.include_router(logs_router,    prefix="/api/logs",    tags=["Logs"])

# ── WebSocket handlers ────────────────────────────────────────────────────────
app.include_router(dictate_ws_router)    # /ws/dictate
app.include_router(lyrics_ws_router)     # /ws/lyrics
app.include_router(telemetry_ws_router)  # /ws/admin/telemetry

# ── Accent-profile REST endpoints ─────────────────────────────────────────────

class CorrectionRequest(BaseModel):
    """Schema for incoming ASR token correction pairs."""

    raw: str        # what the ASR produced
    corrected: str  # what the user intended


@app.post("/api/accent/correct", tags=["AI / Accent"])
async def accent_correct(body: CorrectionRequest) -> dict[str, Any]:
    """Submit a correction pair to evolve the personal accent profile."""
    return TranscriptionService.submit_correction(body.raw, body.corrected)


@app.get("/api/accent/profile", tags=["AI / Accent"])
async def accent_profile() -> dict[str, Any]:
    """Return the full learned accent profile."""
    return TranscriptionService.get_profile()


@app.delete("/api/accent/forget/{word}", tags=["AI / Accent"])
async def accent_forget(word: str) -> dict[str, Any]:
    """Remove all learned corrections for a specific raw token."""
    return TranscriptionService.forget_correction(word)


# ── Root / docs redirect ──────────────────────────────────────────────────────

@app.get("/", tags=["Root"])
async def root() -> dict[str, Any]:
    """Return application metadata status and core redirection targets."""
    return {
        "message": f"{settings.APP_NAME} is running",
        "docs": "/docs",
        "version": settings.APP_VERSION,
    }


@app.exception_handler(UserAlreadyExistsError)
async def user_exists_exception_handler(
    _request: Request, exc: UserAlreadyExistsError
) -> JSONResponse:
    """Handle custom UserAlreadyExistsError and return 400."""
    return JSONResponse(status_code=400, content={"detail": str(exc)})

# ── Dev entrypoint ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import socket
    import sys

    import uvicorn

    def _find_free_port(start: int = 8000, host: str = "0.0.0.0") -> int:
        """Find an available port starting from the given start port."""
        candidate_port = start
        while True:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind((host, candidate_port))
                    return candidate_port
                except OSError:
                    candidate_port += 1

    # Get the port
    PORT: int = _find_free_port()

    print(f"🚀  API     → http://localhost:{PORT}/docs")
    print(f"🎙️  Dictate → ws://localhost:{PORT}/ws/dictate")
    print(f"🎵  Lyrics  → ws://localhost:{PORT}/ws/lyrics")
    print(f"🧠  Accent  → http://localhost:{PORT}/api/accent/profile")

    try:
        # Run with log_level="info" to see logs
        uvicorn.run("app.main:app", host="0.0.0.0", port=PORT, reload=True)
    except KeyboardInterrupt:
        print("\nProcess interrupted. Cleaning up...")
    finally:
        sys.exit(0)
