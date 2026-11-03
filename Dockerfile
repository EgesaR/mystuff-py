
# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.13
ARG RUST_TOOLCHAIN=stable

# ============================================================
# Stage 1: Build Python dependencies and native Rust extensions
# ============================================================

FROM python:${PYTHON_VERSION}-slim AS builder

ARG RUST_TOOLCHAIN

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    CARGO_HOME=/root/.cargo \
    RUSTUP_HOME=/root/.rustup

ENV PATH="/root/.cargo/bin:$PATH"

WORKDIR /app

# Git is needed for the pinned IronVeil Git dependency.
# Build tools are needed for the PyO3/Maturin native extension.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
        curl \
        ca-certificates \
        build-essential \
        pkg-config \
        libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Rust only in the builder stage.
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
    | sh -s -- -y \
        --profile minimal \
        --default-toolchain "${RUST_TOOLCHAIN}" \
    && rustc --version \
    && cargo --version

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency manifests first to preserve Docker layer caching.
COPY pyproject.toml uv.lock ./

# Install application dependencies and compile IronVeil.
# The Git source and exact commit are recorded in uv.lock.
# --no-install-project avoids installing My Stuff before its source
# is available. The app itself is copied into the runtime stage.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=cache,target=/root/.cargo/registry \
    --mount=type=cache,target=/root/.cargo/git \
    uv sync \
        --frozen \
        --no-dev \
        --group ai \
        --no-install-project

# Verify the native extension and AI runtime dependencies.
RUN /app/.venv/bin/python -c \
    "import ironveil; import ironveil._native; print('IronVeil build successful')"

RUN /app/.venv/bin/python -c \
    "import onnxruntime; print('ONNX Runtime:', onnxruntime.__version__)"


# ============================================================
# Stage 2: Minimal production runtime
# ============================================================

FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PATH="/app/.venv/bin:$PATH" \
    LD_LIBRARY_PATH="/app/.venv/lib/python3.13/site-packages/onnxruntime/capi" \
    PORT=8000

WORKDIR /app

# Runtime dependencies only.
# No Rust, Cargo, Git, compiler, uv or build tooling.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        libgomp1 \
        libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root application user.
RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown appuser:appuser /app

# Copy the completed virtual environment.
COPY --from=builder --chown=appuser:appuser \
    /app/.venv /app/.venv

# Copy application source and Alembic configuration.
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser alembic.ini ./alembic.ini

USER appuser

# Verify the actual runtime environment.
RUN python -c \
    "import ironveil; import ironveil._native; print('IronVeil runtime successful')"

RUN python -c \
    "import onnxruntime; print('ONNX Runtime:', onnxruntime.__version__)"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
