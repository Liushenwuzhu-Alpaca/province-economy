"""Lightweight structured logging for the Agent."""

from __future__ import annotations

import json
import logging
import time
from functools import wraps
from pathlib import Path
from typing import Callable

LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"

_logger: logging.Logger | None = None


def _get_logger() -> logging.Logger:
    global _logger
    if _logger is not None:
        return _logger

    LOG_DIR.mkdir(exist_ok=True)

    _logger = logging.getLogger("agent")
    _logger.setLevel(logging.DEBUG)

    # File handler — JSON lines
    fh = logging.FileHandler(LOG_DIR / "agent.log", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(_JSONFormatter())
    _logger.addHandler(fh)

    # Console handler — human-readable
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s", datefmt="%H:%M:%S"))
    _logger.addHandler(ch)

    return _logger


class _JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "ts": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "msg": record.getMessage(),
        }
        if hasattr(record, "extra_data"):
            entry.update(record.extra_data)  # type: ignore[attr-defined]
        return json.dumps(entry, ensure_ascii=False)


def log_api_call(
    model: str, latency_ms: float, prompt_tokens: int, completion_tokens: int, success: bool,
) -> None:
    logger = _get_logger()
    record = logger.makeRecord(
        "agent", logging.INFO, "", 0,
        f"API call {model} {'OK' if success else 'FAIL'} {latency_ms:.0f}ms {prompt_tokens}+{completion_tokens}tok",
        None, None,
    )
    record.extra_data = {  # type: ignore[attr-defined]
        "event": "api_call",
        "model": model,
        "latency_ms": round(latency_ms),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "success": success,
    }
    logger.handle(record)


def log_tool_call(name: str, success: bool, error: str | None = None) -> None:
    logger = _get_logger()
    record = logger.makeRecord(
        "agent", logging.INFO, "", 0,
        f"Tool {name} {'OK' if success else 'FAIL'}" + (f" — {error}" if error else ""),
        None, None,
    )
    record.extra_data = {  # type: ignore[attr-defined]
        "event": "tool_call",
        "tool": name,
        "success": success,
    }
    if error:
        record.extra_data["error"] = error  # type: ignore[attr-defined]
    logger.handle(record)


def timed(fn: Callable) -> Callable:
    """Decorator: measure execution time and return (result, elapsed_ms)."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = fn(*args, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000
        return result, elapsed
    return wrapper
