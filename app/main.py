"""My Stuff FastAPI application entrypoint."""

import os
from collections.abc import Sequence
from enum import Enum

import uvicorn
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes.accent import router as accent_router
from app.api.routes.admin.pre_registration import (
    router as admin_pre_registration_router,
)
from app.api.routes.auth import router as auth_router
from app.api.routes.blog import router as blog_router
from app.api.routes.collections import router as collections_router
from app.api.routes.comments import router as comments_router
from app.api.routes.contact import router as contact_router
from app.api.routes.docs import router as docs_router
from app.api.routes.editor_sync import router as editor_sync_router
from app.api.routes.feedback import router as feedback_router
from app.api.routes.files import router as files_router
from app.api.routes.health import router as health_router
from app.api.routes.logs import router as logs_router
from app.api.routes.media import router as media_router
from app.api.routes.notes import router as notes_router
from app.api.routes.notifications import router as notifications_router
from app.api.routes.onboarding import router as onboarding_router
from app.api.routes.pre_registration import (
    router as pre_registration_router,
)
from app.api.routes.shares import router as shares_router
from app.api.routes.users import router as users_router
from app.api.routes.workspace import router as workspace_router
from app.api.websocket.dictate import router as dictate_ws_router
from app.api.websocket.feedback import router as feedback_ws_router
from app.api.websocket.lyrics import router as lyrics_ws_router
from app.api.websocket.notifications import (
    router as notifications_ws_router,
)
from app.api.websocket.sync import router as editor_sync_ws_router
from app.api.websocket.telemetry import router as telemetry_ws_router
from app.core.config import settings
from app.core.lifespan import lifespan

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=("My Stuff API — notes, workspace, files, media, collaboration and AI services."),
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------

settings.UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

app.mount(
    "/uploads",
    StaticFiles(directory=str(settings.UPLOAD_DIR)),
    name="uploads",
)


# ---------------------------------------------------------------------------
# REST API routes
# ---------------------------------------------------------------------------

REST_ROUTERS: tuple[tuple[APIRouter, str, Sequence[str | Enum]], ...] = (
    (health_router, "/api/health", ["Health"]),
    (auth_router, "/api/auth", ["Authentication"]),
    (users_router, "/api/users", ["Users"]),
    (onboarding_router, "/api/onboarding", ["Onboarding"]),
    (notes_router, "/api/notes", ["Notes"]),
    (editor_sync_router, "/api/notes", ["Editor Sync"]),
    (comments_router, "/api/notes", ["Comments"]),
    (collections_router, "/api/files/collections", ["Collections"]),
    (files_router, "/api/files", ["Files"]),
    (media_router, "/api/media", ["Media"]),
    (workspace_router, "/api/workspace", ["Workspace"]),
    (shares_router, "/api/shares", ["Sharing"]),
    (notifications_router, "/api/notifications", ["Notifications"]),
    (feedback_router, "/api/feedback", ["Feedback"]),
    (logs_router, "/api/logs", ["Logs"]),
    (blog_router, "/api/blog", ["Blog"]),
    (docs_router, "/api/documentation", ["Documentation"]),
    (contact_router, "/api/contact", ["Contact"]),
    (accent_router, "/api/accent", ["Accent"]),
    (pre_registration_router, "/api/pre-register", ["Pre-registration"]),
)

for api_router, prefix, tags in REST_ROUTERS:
    app.include_router(
        api_router,
        prefix=prefix,
        tags=list(tags),
    )


# This router manages its own administrative prefix.
app.include_router(admin_pre_registration_router)


# ---------------------------------------------------------------------------
# WebSocket routes
# ---------------------------------------------------------------------------

WEBSOCKET_ROUTERS: tuple[APIRouter, ...] = (
    dictate_ws_router,
    lyrics_ws_router,
    telemetry_ws_router,
    notifications_ws_router,
    editor_sync_ws_router,
    feedback_ws_router,
)


for websocket_router in WEBSOCKET_ROUTERS:
    app.include_router(websocket_router)


# ---------------------------------------------------------------------------
# Root endpoint
# ---------------------------------------------------------------------------


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    """Return basic API information."""
    return {
        "message": f"{settings.APP_NAME} is running",
        "docs": "/api/docs",
        "openapi": "/api/openapi.json",
        "version": settings.APP_VERSION,
    }


# ---------------------------------------------------------------------------
# Development entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
        reload=settings.DEBUG,
    )
