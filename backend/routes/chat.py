"""Chat endpoint — POST /api/chat."""

from __future__ import annotations

import uuid

from fastapi import APIRouter

from ..schemas import (
    AnalisisBlock,
    ChatRequest,
    ChatResponse,
    ChatResponseBody,
    HukumItem,
    PerluDikonfirmasiItem,
)
from ..services.llm import call_llm_chat

router = APIRouter()

# In-memory session store (replace with Redis if needed)
_sessions: dict[str, list[dict]] = {}


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())

    if session_id not in _sessions:
        _sessions[session_id] = []

    _sessions[session_id].append({"role": "user", "content": req.message})

    parsed = call_llm_chat(_sessions[session_id])

    if not parsed:
        body = ChatResponseBody(
            hukum=[],
            analisis=AnalisisBlock(text="Tidak dapat memproses permintaan. Coba lagi."),
            perlu_dikonfirmasi=[],
        )
        return ChatResponse(session_id=session_id, response=body)

    hukum = []
    for item in parsed.get("hukum", []):
        if isinstance(item, str):
            hukum.append(HukumItem(description=item, legal_basis="", severity="medium"))
        elif isinstance(item, dict):
            hukum.append(HukumItem(
                description=item.get("description", ""),
                legal_basis=item.get("legal_basis", ""),
                severity=item.get("severity", "medium"),
            ))

    analisis = None
    if parsed.get("analisis"):
        analisis = AnalisisBlock(text=parsed["analisis"])

    perlu = []
    for q in parsed.get("perlu_dikonfirmasi") or []:
        perlu.append(PerluDikonfirmasiItem(
            question=q.get("question", ""),
            why=q.get("why", ""),
            options=q.get("options"),
            parameter_key=q.get("key", ""),
            type=q.get("type", "text"),
        ))

    body = ChatResponseBody(
        hukum=hukum,
        analisis=analisis,
        perlu_dikonfirmasi=perlu,
    )

    _sessions[session_id].append({"role": "assistant", "content": str(parsed)})

    return ChatResponse(session_id=session_id, response=body)
