"""Settings endpoint — GET/POST /api/settings."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from ..services.llm import _load_settings, _save_settings, get_llm_config

router = APIRouter()


class SettingsUpdate(BaseModel):
    model: str | None = None
    base_url: str | None = None


@router.get("/settings")
async def get_settings():
    _, base_url, model = get_llm_config()
    return {"model": model, "base_url": base_url}


@router.post("/settings")
async def update_settings(req: SettingsUpdate):
    settings = _load_settings()
    if req.model is not None:
        settings["model"] = req.model
    if req.base_url is not None:
        settings["base_url"] = req.base_url
    _save_settings(settings)
    _, base_url, model = get_llm_config()
    return {"model": model, "base_url": base_url}


@router.get("/settings/models")
async def list_models():
    """Fetch available models from the gateway's /models endpoint."""
    import httpx

    api_key, base_url, _ = get_llm_config()
    url = base_url.rstrip("/")
    if not url.endswith("/v1"):
        url += "/v1"
    url += "/models"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(url, headers={"Authorization": f"Bearer {api_key}"})
            res.raise_for_status()
            data = res.json()
            models = [m["id"] for m in data.get("data", [])]
            models.sort()
            return {"models": models}
    except Exception:
        return {"models": []}
