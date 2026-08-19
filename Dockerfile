# syntax=docker/dockerfile:1

# ============================================================
# Stage 1: Builder (heavy work happens here)
# ============================================================
FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

# Minimal build-time system deps
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgomp1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Static FFmpeg
COPY --from=mwader/static-ffmpeg:9.0 /ffmpeg  /usr/local/bin/ffmpeg
COPY --from=mwader/static-ffmpeg:9.0 /ffprobe /usr/local/bin/ffprobe

# uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Dependency files first (better caching)
COPY pyproject.toml uv.lock ./

# Install with BuildKit cache mounts (huge win on rebuilds)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --group ai

# Copy application code
COPY app ./app

# ============================================================
# Stage 2: Runtime (tiny final image)
# ============================================================
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    PATH="/app/.venv/bin:$PATH"

# Only runtime system libs
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Static FFmpeg
COPY --from=mwader/static-ffmpeg:9.0 /ffmpeg  /usr/local/bin/ffmpeg
COPY --from=mwader/static-ffmpeg:9.0 /ffprobe /usr/local/bin/ffprobe

WORKDIR /app

# Copy the virtualenv + app from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/app ./app

# Runtime directories + non-root user
RUN mkdir -p /app/data/uploads \
    && useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]