# syntax=docker/dockerfile:1

# ============================================================
# 1. Python runtime
# ============================================================
FROM python:3.13-slim

# ============================================================
# 2. Environment
# ============================================================
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

# ============================================================
# 3. System dependencies
#
# ffmpeg  -> audio/video processing
# libgomp1 -> NumPy/PyTorch/OpenMP runtime
# curl    -> health checks / diagnostics
# ============================================================
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        libgomp1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ============================================================
# 4. Install uv
# ============================================================
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# ============================================================
# 5. Application directory
# ============================================================
WORKDIR /app

# ============================================================
# 6. Dependency definitions
# ============================================================
COPY pyproject.toml uv.lock ./

# ============================================================
# 7. Install locked production dependencies
# ============================================================
RUN uv sync --frozen --no-dev --group ai

# ============================================================
# 8. Copy application source
# ============================================================
COPY app ./app

# ============================================================
# 9. Runtime directories
# ============================================================
RUN mkdir -p /app/data/uploads

# ============================================================
# 10. Create non-root user
# ============================================================
RUN useradd \
        --create-home \
        --shell /bin/bash \
        appuser \
    && chown -R appuser:appuser /app

USER appuser

# ============================================================
# 11. Port
# ============================================================
EXPOSE 8000

# ============================================================
# 12. Production startup
# ============================================================
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]