# Docker Containerization Decisions

## Multi-stage Dockerfile (2026-05-19)

### Decision: Use uv official Docker image for builder stage
- **Chosen**: `ghcr.io/astral-sh/uv:python3.11-bookworm-slim`
- **Rationale**: Official uv image ensures compatible Python + uv version; bookworm-slim matches runtime base
- **Alternative considered**: Installing uv manually in a python base image (more steps, version drift risk)

### Decision: Use python:3.11-slim-bookworm for runtime
- **Chosen**: Debian bookworm slim (not Alpine)
- **Rationale**: musl libc in Alpine has compatibility issues with numpy/scipy/pandas; bookworm-slim is ~40MB smaller than full bookworm
- **Alternative rejected**: Alpine (musl incompatibility with scientific Python stack)

### Decision: Only install libxml2 + libxslt1.1 as system deps
- **Chosen**: Minimal apt-get with just lxml runtime libs
- **Rationale**: OCR deps (opencv, rapidocr) moved to optional-dependencies; no opencv system libs needed
- **Alternative rejected**: Installing opencv system deps (libgl1, libglib2.0-0, etc.) - unnecessary without OCR

### Decision: Exec form ENTRYPOINT
- **Chosen**: `ENTRYPOINT ["python", "main.py"]`
- **Rationale**: Exec form enables proper PID 1 signal handling; allows `docker run image --year 2023` passthrough
- **Alternative rejected**: Shell form `ENTRYPOINT python main.py` - breaks SIGTERM handling
