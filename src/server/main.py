from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .data_api import load_all_data, load_trend_data

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_STATIC_DIR = Path(__file__).parent / "static"
_RESULTS_DIR = Path("data/results")
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


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
def api_data(
    year: int = Query(default=2024, description="Analysis year"),
) -> dict[str, Any]:
    scores_file = _RESULTS_DIR / f"{year}_pca" / "scores.csv"
    if not scores_file.exists():
        subprocess.run(
            ["uv", "run", "main.py", "--year", str(year)],
            check=True,
            cwd=_PROJECT_ROOT,
            timeout=120,
        )
    return load_all_data(year=year)


@app.get("/api/years")
def api_years() -> dict[str, Any]:
    years = []
    if _RESULTS_DIR.exists():
        for entry in _RESULTS_DIR.iterdir():
            if entry.is_dir():
                scores_file = entry / "scores.csv"
                if scores_file.exists():
                    m = re.match(r"^(\d{4})_pca$", entry.name)
                    if m:
                        years.append(int(m.group(1)))
    years.sort()
    return {"years": years}


@app.get("/api/trend")
def api_trend() -> dict[str, Any]:
    return load_trend_data()


@app.post("/api/chat")
async def api_chat(body: dict) -> StreamingResponse:
    """SSE streaming chat endpoint."""
    from src.agent.agent import chat_stream

    user_message = (body.get("message") or "").strip()
    if not user_message:
        def _empty():
            yield 'event: error\ndata: {"text": "请输入您的问题。"}\n\n'
            yield 'event: done\ndata: {}\n\n'
        return StreamingResponse(_empty(), media_type="text/event-stream")

    # Input validation
    if len(user_message) > 2000:
        def _too_long():
            yield 'event: error\ndata: {"text": "问题过长，请限制在2000字符以内。"}\n\n'
            yield 'event: done\ndata: {}\n\n'
        return StreamingResponse(_too_long(), media_type="text/event-stream")

    history = body.get("history")
    if isinstance(history, list):
        history = history[-20:]

    return StreamingResponse(
        chat_stream(user_message, history=history),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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
