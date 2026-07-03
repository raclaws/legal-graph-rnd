"""Chat endpoint — POST /api/chat."""

from __future__ import annotations

import base64
import uuid

from fastapi import APIRouter, File, Form, UploadFile

from ..schemas import (
    ActionItem,
    AnalisisBlock,
    ChatRequest,
    ChatResponse,
    ChatResponseBody,
    HukumItem,
    PerluDikonfirmasiItem,
)
from ..services.llm import call_llm_chat, call_llm_simple

router = APIRouter()

_sessions: dict[str, list[dict]] = {}


def _extract_text(content: bytes, filename: str) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        try:
            import pymupdf
            doc = pymupdf.open(stream=content, filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text() + "\n"
            return text[:8000] if text.strip() else "[PDF is scanned/image-based]"
        except Exception:
            return "[Could not read PDF]"
    elif name.endswith(".txt"):
        try:
            return content.decode("utf-8")[:8000]
        except Exception:
            return content.decode("latin-1")[:8000]
    return f"[File: {filename}, {len(content)} bytes]"


def _parse_llm_response(parsed: dict) -> ChatResponseBody:
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

    return ChatResponseBody(hukum=hukum, analisis=analisis, perlu_dikonfirmasi=perlu)


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())

    if session_id not in _sessions:
        _sessions[session_id] = []

    message = req.message

    if req.attachments:
        for att in req.attachments:
            content = base64.b64decode(att.data_base64)
            doc_text = _extract_text(content, att.filename)
            message += f"\n\n[Document: {att.filename}]\n{doc_text}"

    _sessions[session_id].append({"role": "user", "content": message})

    parsed = call_llm_chat(_sessions[session_id])

    if not parsed:
        body = ChatResponseBody(
            hukum=[],
            analisis=AnalisisBlock(text="Tidak dapat memproses permintaan. Coba lagi."),
            perlu_dikonfirmasi=[],
        )
        return ChatResponse(session_id=session_id, response=body)

    body = _parse_llm_response(parsed)
    _sessions[session_id].append({"role": "assistant", "content": str(parsed)})

    return ChatResponse(session_id=session_id, response=body)


@router.post("/chat/upload", response_model=ChatResponse)
async def chat_upload(
    file: UploadFile = File(...),
    message: str = Form("Analisis dokumen ini"),
    session_id: str = Form(""),
):
    """Upload a document and run compliance analysis."""
    from src.compliance.pipeline import run_compliance_pipeline

    sid = session_id or str(uuid.uuid4())
    if sid not in _sessions:
        _sessions[sid] = []

    content = await file.read()
    doc_text = _extract_text(content, file.filename or "document")

    _sessions[sid].append({"role": "user", "content": f"{message}\n\n[Document: {file.filename}]"})

    report, logs = run_compliance_pipeline(doc_text, call_llm_simple, file.filename or "document")

    if report:
        from src.compliance.obligations import Verdict
        hukum = []
        actions = []
        unclear = []
        for r in report.results:
            if r.verdict == Verdict.VIOLATED:
                evidence = None
                if r.extracted_value is not None:
                    evidence = f"Ditemukan: {r.extracted_value}"
                elif "GAGAL:" in (r.detail or ""):
                    evidence = r.detail.split("|")[0].strip()

                hukum.append(HukumItem(
                    description=r.obligation_description,
                    legal_basis=r.legal_basis,
                    severity=r.severity.value,
                    doc_evidence=evidence,
                ))
                actions.append(ActionItem(
                    description=f"Perbaiki: {r.obligation_description}",
                    severity=r.severity.value,
                    legal_basis=r.legal_basis,
                ))
            elif r.verdict == Verdict.NOT_EVALUATED:
                unclear.append(r.obligation_description)
            elif r.verdict == Verdict.COMPLIANT:
                hukum.append(HukumItem(
                    description=r.obligation_description,
                    legal_basis=r.legal_basis,
                    severity="low",
                ))

        unclear_text = ""
        if unclear:
            unclear_text = f"\n\nTidak dapat dievaluasi ({len(unclear)} item — data tidak ditemukan dalam dokumen):\n" + "\n".join(f"• {u}" for u in unclear)

        analisis = AnalisisBlock(
            text=f"Score: {report.score_pct}% — {report.compliant} compliant, {report.violated} violations, {len(unclear)} tidak dapat dievaluasi{unclear_text}"
        )

        body = ChatResponseBody(hukum=hukum, analisis=analisis, perlu_dikonfirmasi=[], actions=actions)
    else:
        parsed = call_llm_chat(_sessions[sid] + [{"role": "user", "content": doc_text[:4000]}])
        if parsed:
            body = _parse_llm_response(parsed)
        else:
            body = ChatResponseBody(
                hukum=[],
                analisis=AnalisisBlock(text="Gagal menganalisis dokumen."),
                perlu_dikonfirmasi=[],
            )

    _sessions[sid].append({"role": "assistant", "content": "compliance report"})
    return ChatResponse(session_id=sid, response=body)
