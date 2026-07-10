"""JWT auth middleware — validates Logto-issued access tokens."""

from __future__ import annotations

import os
import time
from typing import Any

import httpx
import jwt

LOGTO_ENDPOINT = os.environ.get("LOGTO_ENDPOINT", "https://i8a3uv.logto.app/")

_jwks_cache: dict[str, Any] = {}
_jwks_fetched_at: float = 0
JWKS_TTL = 3600


def _get_jwks() -> dict[str, Any]:
    global _jwks_cache, _jwks_fetched_at

    if _jwks_cache and (time.time() - _jwks_fetched_at) < JWKS_TTL:
        return _jwks_cache

    endpoint = LOGTO_ENDPOINT.rstrip("/")
    oidc_config = httpx.get(f"{endpoint}/oidc/.well-known/openid-configuration", timeout=10).json()
    jwks_uri = oidc_config["jwks_uri"]
    _jwks_cache = httpx.get(jwks_uri, timeout=10).json()
    _jwks_fetched_at = time.time()
    return _jwks_cache


def validate_token(token: str) -> dict | None:
    """Validate a Logto JWT. Returns decoded claims or None if invalid."""
    try:
        jwks = _get_jwks()
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        key = None
        for k in jwks.get("keys", []):
            if k.get("kid") == kid:
                key = jwt.algorithms.RSAAlgorithm.from_jwk(k)
                break

        if not key:
            return None

        endpoint = LOGTO_ENDPOINT.rstrip("/")
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            issuer=f"{endpoint}/oidc",
            options={"verify_aud": True},
            audience=os.environ.get("LOGTO_APP_ID", "78s9jpal807pel5bgj88k"),
        )
        return claims
    except (jwt.InvalidTokenError, httpx.HTTPError, KeyError):
        return None
