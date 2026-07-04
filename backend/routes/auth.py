"""Auth endpoint — POST /api/auth/login, GET /api/auth/check."""

from __future__ import annotations

import os
import secrets
import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter()

_tokens: dict[str, float] = {}  # token -> expiry timestamp
TOKEN_TTL = 86400 * 7  # 7 days

_login_attempts: dict[str, list[float]] = {}  # ip -> timestamps
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 300


def _get_credentials() -> tuple[str, str]:
    return (
        os.environ.get("AUTH_USER", ""),
        os.environ.get("AUTH_PASS", ""),
    )


def _verify_token(token: str) -> bool:
    if token in _tokens:
        if _tokens[token] > time.time():
            return True
        del _tokens[token]
    return False


def _is_rate_limited(ip: str) -> bool:
    now = time.time()
    attempts = _login_attempts.get(ip, [])
    attempts = [t for t in attempts if now - t < WINDOW_SECONDS]
    _login_attempts[ip] = attempts
    return len(attempts) >= MAX_ATTEMPTS


def _record_attempt(ip: str):
    _login_attempts.setdefault(ip, []).append(time.time())


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/auth/login")
async def login(req: LoginRequest, request: Request):
    ip = request.client.host if request.client else "unknown"

    if _is_rate_limited(ip):
        return JSONResponse(status_code=429, content={"detail": "Too many attempts. Try again later."})

    user, password = _get_credentials()
    if not user or not password:
        return JSONResponse(status_code=500, content={"detail": "Auth not configured"})

    if secrets.compare_digest(req.username, user) and secrets.compare_digest(req.password, password):
        _login_attempts.pop(ip, None)
        token = secrets.token_hex(32)
        _tokens[token] = time.time() + TOKEN_TTL
        return {"token": token}

    _record_attempt(ip)
    return JSONResponse(status_code=401, content={"detail": "Invalid credentials"})


@router.get("/auth/check")
async def check(request: Request):
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer ") and _verify_token(auth[7:]):
        return {"ok": True}
    return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
