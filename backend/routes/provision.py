"""Provision lookup — GET /api/provision/{node_id}."""

from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException

from ..schemas import ProvisionChild, ProvisionResponse
from ..services.graph import get_provision

router = APIRouter()


def _clean_text(text: str | None) -> str | None:
    if not text:
        return text
    # Join broken lines from PDF extraction (word\n word → word word)
    cleaned = re.sub(r'\s*\n\s*', ' ', text)
    # Collapse multiple spaces
    cleaned = re.sub(r' {2,}', ' ', cleaned)
    return cleaned.strip()


@router.get("/provision/{node_id:path}", response_model=ProvisionResponse)
async def provision(node_id: str):
    data = get_provision(node_id)
    if not data:
        raise HTTPException(status_code=404, detail="Provision not found")

    children = [
        ProvisionChild(
            node_id=c["node_id"],
            type=c.get("type", ""),
            number=c.get("number", ""),
            text_preview=_clean_text((c.get("text") or "")[:100]) or None,
        )
        for c in data.get("children", [])
    ]

    return ProvisionResponse(
        node_id=data["node_id"],
        type=data["type"],
        number=data["number"],
        text=_clean_text(data.get("text")),
        parent=data.get("parent"),
        children=children,
        norms_derived=data.get("norms_derived", []),
    )
