# =============================================================================
# Province-Economy Dashboard - Multi-stage Docker Build
# =============================================================================
# Stage 1: Build Python deps with uv
# Stage 2: FastAPI server + ECharts dashboard + analysis engine
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder - install Python dependencies via uv
FROM python:3.11-slim-bookworm AS builder

# Install uv via pip
RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# ---------------------------------------------------------------------------
# Stage 2: Runtime - FastAPI server + dashboard
# ---------------------------------------------------------------------------
FROM python:3.11-slim-bookworm AS runtime

# System deps: lxml (libxml2/libxslt), scikit-learn (libgomp), Chinese font
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libxml2 \
        libxslt1.1 \
        libgomp1 \
        libgfortran5 \
        fonts-wqy-microhei \
    && rm -rf /var/lib/apt/lists/*

# Copy uv binary (server uses "uv run main.py" to auto-generate missing data)
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv
COPY --from=builder /usr/local/bin/uvx /usr/local/bin/uvx

# Copy pre-built venv
COPY --from=builder /app/.venv /app/.venv

# Copy source (server + visualization + models + data modules + static frontend)
COPY src/ /app/src/
COPY main.py /app/

# Copy pre-processed data (indicators CSV + GeoJSON ~100KB)
COPY data_cache/ /app/data_cache/

COPY data_cache/huggingface/ /root/.cache/huggingface/

# Environment
ENV PATH="/app/.venv/bin:$PATH" \
    PROJ_ROOT=/app \
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8

# Non-root user
# RUN useradd --create-home appuser

# RUN chown -R appuser:appuser /home/appuser/.cache

# USER appuser
WORKDIR /app

# Expose FastAPI port
EXPOSE 8765

# Start FastAPI server
ENTRYPOINT ["python", "-m", "src.server.main"]