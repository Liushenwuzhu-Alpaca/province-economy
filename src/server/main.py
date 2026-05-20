from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .data_api import load_all_data

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_STATIC_DIR = Path(__file__).parent / "static"


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="Province Economy Dashboard API")

# CORS middleware — allow all origins for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files at /static
if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/", include_in_schema=False)
async def root() -> FileResponse:
    index_path = _STATIC_DIR / "index.html"
    if not index_path.exists():
        raise RuntimeError(
            f"index.html not found at {index_path}. "
            "Place the dashboard static files in src/server/static/."
        )
    return FileResponse(path=str(index_path))


@app.get("/api/data")
def api_data(year: int = Query(default=2024, description="Analysis year")) -> dict:
    return load_all_data(year=year)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.server.main:app",
        host="0.0.0.0",
        port=8765,
        reload=True,
    )
