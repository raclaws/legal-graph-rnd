"""HR Compliance Checker — FastAPI Backend."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .middleware.auth import validate_token
from .middleware.observability import ObservabilityMiddleware
from .routes import calculator, chat, chat_v2, compliance, explain, provision, settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.environ.get("INFISICAL_CLIENT_ID"):
        _load_infisical_secrets()
    yield


def _load_infisical_secrets():
    """Fetch secrets from Infisical at boot via Universal Auth."""
    from infisical_client import (
        ClientSettings,
        InfisicalClient,
        ListSecretsOptions,
        AuthenticationOptions,
        UniversalAuthMethod,
    )

    client = InfisicalClient(ClientSettings(
        auth=AuthenticationOptions(
            universal_auth=UniversalAuthMethod(
                client_id=os.environ["INFISICAL_CLIENT_ID"],
                client_secret=os.environ["INFISICAL_CLIENT_SECRET"],
            )
        )
    ))

    secrets = client.listSecrets(options=ListSecretsOptions(
        environment=os.environ.get("INFISICAL_ENV", "prod"),
        project_id="877bab29-028e-492d-aad1-acb44ca4f529",
        path="/",
    ))

    for s in secrets:
        os.environ.setdefault(s.secret_key, s.secret_value)


app = FastAPI(
    title="HR Compliance API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        os.environ.get("CORS_ORIGIN", ""),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(ObservabilityMiddleware)

_PUBLIC_PATHS = {"/health"}


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if request.url.path in _PUBLIC_PATHS:
        return await call_next(request)

    # Skip auth if no Logto endpoint configured (local dev without auth)
    if not os.environ.get("LOGTO_ENDPOINT"):
        return await call_next(request)

    token = request.headers.get("Authorization", "")
    if token.startswith("Bearer "):
        claims = validate_token(token[7:])
        if claims:
            request.state.user = claims
            return await call_next(request)

    return JSONResponse(status_code=401, content={"detail": "Unauthorized"})


app.include_router(chat.router, prefix="/api")
app.include_router(chat_v2.router, prefix="/api")
app.include_router(calculator.router, prefix="/api")
app.include_router(provision.router, prefix="/api")
app.include_router(compliance.router, prefix="/api")
app.include_router(explain.router, prefix="/api")
app.include_router(settings.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}
