"""JWT auth middleware — validates Auth0-issued access tokens."""

from __future__ import annotations

import os
import time
from typing import Any

import httpx
import jwt

_jwks_cache: dict[str, Any] = {}
_jwks_fetched_at: float = 0
JWKS_TTL = 3600


def _get_jwks() -> dict[str, Any]:
    global _jwks_cache, _jwks_fetched_at

    if _jwks_cache and (time.time() - _jwks_fetched_at) < JWKS_TTL:
        return _jwks_cache

    domain = os.environ.get("AUTH0_DOMAIN", "")
    jwks_url = f"https://{domain}/.well-known/jwks.json"
    _jwks_cache = httpx.get(jwks_url, timeout=10).json()
    _jwks_fetched_at = time.time()
    return _jwks_cache


def validate_token(token: str) -> dict | None:
    """Validate an Auth0 JWT. Returns decoded claims or None if invalid."""
    try:
        domain = os.environ.get("AUTH0_DOMAIN", "")
        audience = os.environ.get("AUTH0_AUDIENCE", "")

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

        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            issuer=f"https://{domain}/",
            audience=audience,
            options={"verify_aud": True},
        )
        return claims
    except (jwt.InvalidTokenError, httpx.HTTPError, KeyError):
        return None
