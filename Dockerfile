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
# 3. Minimal system dependencies only
#    - libgomp1  → required by NumPy / PyTorch OpenMP
#    - curl      → health checks / diagnostics (optional)
# ============================================================
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgomp1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ============================================================
# 4. Static FFmpeg + FFprobe (no shared-library bloat)
# ============================================================
COPY --from=mwader/static-ffmpeg:9.0 /ffmpeg  /usr/local/bin/ffmpeg
COPY --from=mwader/static-ffmpeg:9.0 /ffprobe /usr/local/bin/ffprobe

# ============================================================
# 5. Install uv
# ============================================================
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# ============================================================
# 6. Application directory
# ============================================================
WORKDIR /app

# ============================================================
# 7. Dependency definitions
# ============================================================
COPY pyproject.toml uv.lock ./

# ============================================================
# 8. Install locked production dependencies
# ============================================================
RUN uv sync --frozen --no-dev --group ai

# ============================================================
# 9. Copy application source
# ============================================================
COPY app ./app

# ============================================================
# 10. Runtime directories
# ============================================================
RUN mkdir -p /app/data/uploads

# ============================================================
# 11. Create non-root user
# ============================================================
RUN useradd \
        --create-home \
        --shell /bin/bash \
        appuser \
    && chown -R appuser:appuser /app

USER appuser

# ============================================================
# 12. Port
# ============================================================
EXPOSE 8000

# ============================================================
# 13. Production startup
# ============================================================
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]