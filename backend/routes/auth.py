"""Auth endpoint — POST /api/auth/login, GET /api/auth/check."""

from __future__ import annotations

import hashlib
import os
import secrets
import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter()

_tokens: dict[str, float] = {}  # token -> expiry timestamp
TOKEN_TTL = 86400 * 7  # 7 days


def _get_credentials() -> tuple[str, str]:
    return (
        os.environ.get("AUTH_USER", "admin"),
        os.environ.get("AUTH_PASS", "admin"),
    )


def _verify_token(token: str) -> bool:
    if token in _tokens:
        if _tokens[token] > time.time():
            return True
        del _tokens[token]
    return False


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/auth/login")
async def login(req: LoginRequest):
    user, password = _get_credentials()
    if req.username == user and req.password == password:
        token = secrets.token_hex(32)
        _tokens[token] = time.time() + TOKEN_TTL
        return {"token": token}
    return JSONResponse(status_code=401, content={"detail": "Invalid credentials"})


@router.get("/auth/check")
async def check(request: Request):
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer ") and _verify_token(auth[7:]):
        return {"ok": True}
    return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
