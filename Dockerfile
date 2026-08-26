# syntax=docker/dockerfile:1
ARG PYTHON_VERSION=3.13

# ---------- Stage 1: install deps into a venv (never shipped as-is) ----------
FROM python:${PYTHON_VERSION}-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Manifests only — this layer is cache-hit unless deps actually change
COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --group ai

# ---------- Stage 2: slim runtime, nothing build-related survives ----------
FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PATH="/app/.venv/bin:$PATH" \
    PORT=8000

WORKDIR /app

# Only what the app needs at runtime — no compilers, no uv, no apt cache.
# Dropped `curl`: nothing in this Dockerfile uses it (Render health-checks
# your app over HTTP externally, it doesn't need curl inside the container).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /usr/sbin/nologin appuser

# Pull in just the built venv from the builder stage — not uv, not pip cache,
# not apt lists, not build tooling. This is what actually shrinks the image.
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --chown=appuser:appuser app ./app

USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]