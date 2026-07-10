"""Axiom observability middleware — HTTP request logging + error capture."""

from __future__ import annotations

import os
import time
import traceback
from datetime import datetime, timezone

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client

    token = os.environ.get("AXIOM_TOKEN")
    if not token:
        return None

    try:
        from axiom_py import Client
        _client = Client(token=token)
        return _client
    except Exception:
        return None


def _dataset() -> str:
    return os.environ.get("AXIOM_DATASET", "legal-graph")


def ingest(events: list[dict]):
    client = _get_client()
    if not client:
        return
    try:
        client.ingest_events(_dataset(), events)
    except Exception:
        pass


def log_llm(function: str, model: str, duration_ms: float, error: str | None = None, **extra):
    event = {
        "_time": datetime.now(timezone.utc).isoformat(),
        "type": "llm",
        "function": function,
        "model": model,
        "duration_ms": round(duration_ms, 1),
    }
    if error:
        event["error"] = error
    event.update(extra)
    ingest([event])


def log_error(path: str, error_type: str, message: str, tb: str | None = None):
    event = {
        "_time": datetime.now(timezone.utc).isoformat(),
        "type": "error",
        "path": path,
        "error_type": error_type,
        "message": message,
    }
    if tb:
        event["traceback"] = tb
    ingest([event])


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        status = 500

        try:
            response = await call_next(request)
            status = response.status_code
            return response
        except Exception as exc:
            log_error(
                path=request.url.path,
                error_type=type(exc).__name__,
                message=str(exc),
                tb=traceback.format_exc(),
            )
            raise
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            user_sub = None
            if hasattr(request, "state") and hasattr(request.state, "user"):
                user_sub = request.state.user.get("sub")

            ingest([{
                "_time": datetime.now(timezone.utc).isoformat(),
                "type": "http",
                "method": request.method,
                "path": request.url.path,
                "status": status,
                "duration_ms": round(duration_ms, 1),
                "user_sub": user_sub,
            }])
