# =============================================================================
# Province-Economy Analysis Engine - Multi-stage Docker Build
# =============================================================================
# Stage 1: Build Python dependencies with uv (cached, reproducible)
# Stage 2: Minimal runtime image with pre-processed CSV data
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder - install Python dependencies via uv
# ---------------------------------------------------------------------------
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

WORKDIR /app

# Copy dependency manifests first for layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies into .venv without the project itself
# --frozen: lockfile must match pyproject.toml exactly (no resolution)
# --no-dev: skip dev/test dependencies
# --no-install-project: only install third-party deps, not the project
RUN uv sync --frozen --no-dev --no-install-project

# ---------------------------------------------------------------------------
# Stage 2: Runtime - minimal image with only runtime system libs
# ---------------------------------------------------------------------------
FROM python:3.11-slim-bookworm AS runtime

# Install only the system libraries needed by lxml (which wraps libxml2/libxslt)
# --no-install-recommends: skip non-essential suggested packages
# Clean apt cache to minimize image size
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libxml2 \
        libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

# Copy the pre-built virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application source code
COPY src/ /app/src/
COPY main.py /app/

# Copy pre-processed CSV data (~28KB total)
COPY data_cache/ /app/data_cache/

# Environment configuration
# PATH: ensure venv binaries take precedence
# PROJ_ROOT: override config.py base path for container filesystem
# PYTHONIOENCODING: force UTF-8 output encoding
# LANG: C.UTF-8 locale for consistent string handling
ENV PATH="/app/.venv/bin:$PATH" \
    PROJ_ROOT=/app \
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8

# Create non-root user for security
RUN useradd --create-home appuser

# Switch to non-root user
USER appuser

# Set working directory
WORKDIR /app

# Entrypoint: exec form for proper signal handling
# Usage: docker run <image> [args]
#   docker run <image> --year 2023
#   docker run <image> --recompute
#   docker run <image> --no-pca
ENTRYPOINT ["python", "main.py"]