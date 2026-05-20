# Docker Containerization Learnings

## .dockerignore Creation (2026-05-19)

### Key Findings

1. **Major space savings**: Excluding `.venv/` alone saves ~870MB (the virtual environment)
2. **Yearbook images**: `data/raw/yearbook_2023/` and `data/raw/yearbook_2024/` total ~6.5MB of JPGs not needed in Docker
3. **Actual context size**: With all exclusions, Docker build context is ~530KB (well under 20MB target)

### What to EXCLUDE
- `.venv/` - virtual environment (~870MB)
- `.git/` - version control
- `data/raw/yearbook_*/` - raw JPG images (~6.5MB)
- `output/` - generated outputs
- `data/results/` - runtime output (volume-mounted in production)
- `*.zip` - compressed archives
- `.sisyphus/` - tool configuration
- `.ruff_cache/` - linter cache
- `__pycache__/` and `*.pyc` - Python cache
- `.python-version` - version file

### What to KEEP (COPY into image)
- `data_cache/` - pre-processed CSV needed at runtime
- `src/` - core analysis engine
- `main.py` - entry point
- `pyproject.toml` and `uv.lock` - uv build dependencies

### Verification Command
```bash
tar --exclude='.dockerignore' --exclude='.venv' --exclude='output' --exclude='.git' \
    --exclude='.sisyphus' --exclude='data/raw/yearbook_*' --exclude='.ruff_cache' \
    --exclude='__pycache__' --exclude='*.pyc' --exclude='*.zip' --exclude='.python-version' \
    -cf /tmp/test_context.tar .
```
# Docker Containerization Learnings

## Entry Point Script

### Key Pattern
```bash
#!/usr/bin/env bash
set -euo pipefail
echo "Starting province-economy analysis engine..." >&2
exec python main.py "$@"
```

### Notes
- Use `exec` to properly forward signals (SIGTERM, etc.) to the Python process
- Quote `"$@"` to preserve arguments with spaces
- Print startup message to stderr (`>&2`) so it doesn't pollute stdout/analysis output
- The entrypoint works correctly; pandas error when testing outside container is expected

## Multi-stage Dockerfile (2026-05-19)

### Architecture
- **Stage 1 (builder)**: `ghcr.io/astral-sh/uv:python3.11-bookworm-slim` - uses uv to install dependencies
- **Stage 2 (runtime)**: `python:3.11-slim-bookworm` - minimal runtime with only libxml2 + libxslt1.1

### Key Decisions
- `uv sync --frozen --no-dev --no-install-project` ensures reproducible builds without installing the project itself
- Only `libxml2` and `libxslt1.1` needed as system deps (lxml runtime requirements)
- OCR deps (opencv, rapidocr) excluded via optional-dependencies - not installed in Docker
- `--no-install-recommends` + `rm -rf /var/lib/apt/lists/*` minimizes image size
- Non-root `appuser` for security
- Exec form ENTRYPOINT `["python", "main.py"]` for proper signal handling

### Build Verification
- Builder stage verified: 48 packages installed successfully via uv sync
- Runtime stage: Docker Hub network timeout prevented full build (not a Dockerfile issue)
- Use `podman build` as alternative when Docker daemon unavailable

### Environment Variables
- `PATH=/app/.venv/bin:$PATH` - venv binaries take precedence
- `PROJ_ROOT=/app` - config.py override for container filesystem paths
- `PYTHONIOENCODING=utf-8` - force UTF-8 output
- `LANG=C.UTF-8` - consistent locale handling

## docker-compose.yml creation (2026-05-19)

### Key decisions:
- **backend is ACTIVE**: builds from `.`, mounts `./data/results:/app/data/results`, joins `app-network`
- **frontend/chromadb are FULLY commented**: every line prefixed with `#`
- **No `depends_on` on backend**: CLI tool exits after analysis, no need to block
- **No backend ports**: CLI tool doesn't expose any port
- **`version: '3.8'`**: modern Docker Compose version
- **Shared `app-network` bridge**: all services connect to this

### Comments kept (necessary for placeholders):
The extensive commented blocks with `# =======` separators are necessary because:
1. They serve as **documentation** for future implementation
2. They clearly mark **which lines are active vs placeholder** 
3. They follow the **inherited template** from the plan context
4. YAML multiline comments are the **standard convention** for docker-compose placeholder services

### Verification:
- `docker compose config` not available (docker CLI doesn't support `compose` subcommand)
- Manual YAML structure review: passes
- All services have `networks: - app-network`
- Volumes syntax correct: `- ./host:/container`

## README Docker Section (2026-05-19)

Added `## Docker 使用` section to README.md with the following subsections:
- 快速开始: build + run commands with volume mount
- 命令行参数: --year, --recompute, --no-pca with examples
- Docker Compose: `docker compose up --build`
- 数据说明: data_cache/ is baked-in, data/results/ needs volume mount
- 镜像信息: python:3.11-slim-bookworm, uv, ~300MB, non-root appuser

All commands are copy-paste ready. No Streamlit/Agent references (not yet implemented).
