"""HR Compliance Checker — FastAPI Backend."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import calculator, chat, compliance, explain, provision


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="HR Compliance API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/api")
app.include_router(calculator.router, prefix="/api")
app.include_router(provision.router, prefix="/api")
app.include_router(compliance.router, prefix="/api")
app.include_router(explain.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}
