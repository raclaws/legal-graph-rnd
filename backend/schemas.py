"""Pydantic models for API request/response."""

from __future__ import annotations

from pydantic import BaseModel


# --- Chat ---

class ChatAttachment(BaseModel):
    filename: str
    content_type: str
    data_base64: str


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str
    attachments: list[ChatAttachment] | None = None
    context: dict | None = None


class HukumItem(BaseModel):
    description: str
    legal_basis: str
    severity: str = "medium"
    legal_text_summary: str | None = None


class PerluDikonfirmasiItem(BaseModel):
    question: str
    why: str = ""
    options: list[str] | None = None
    parameter_key: str = ""
    type: str = "text"


class AnalisisBlock(BaseModel):
    text: str
    disclaimer: str = "Interpretasi — bukan hukum. Hasil di pengadilan bisa berbeda."


class ChatResponse(BaseModel):
    session_id: str
    response: ChatResponseBody


class ChatResponseBody(BaseModel):
    hukum: list[HukumItem] = []
    analisis: AnalisisBlock | None = None
    perlu_dikonfirmasi: list[PerluDikonfirmasiItem] = []
    quick_actions: list[dict] | None = None


# --- Severance Calculator ---

class SeveranceRequest(BaseModel):
    masa_kerja_bulan: int
    upah_pokok: int
    tunjangan_tetap: int = 0
    alasan_phk: str
    tanggal_phk: str | None = None


class SeveranceComponent(BaseModel):
    amount: int
    formula: str
    multiplier: float | None = None


class SeveranceResponse(BaseModel):
    pesangon: SeveranceComponent
    penghargaan: SeveranceComponent
    penggantian_hak: SeveranceComponent
    total: int
    legal_basis: list[dict]
    comparison: dict | None = None


# --- Compliance Check ---

class ComplianceCheckRequest(BaseModel):
    context: dict
    document: ChatAttachment | None = None


class ComplianceCheckResult(BaseModel):
    norm_id: str
    norm_description: str
    status: str
    severity: str
    detail: str
    legal_basis: str
    evidence_needed: str | None = None
    edge_case: str | None = None


class ComplianceCheckResponse(BaseModel):
    summary: dict
    results: list[ComplianceCheckResult]


# --- Provision ---

class ProvisionChild(BaseModel):
    node_id: str
    type: str
    number: str
    text_preview: str | None = None


class ProvisionResponse(BaseModel):
    node_id: str
    type: str
    number: str
    text: str | None = None
    parent: str | None = None
    children: list[ProvisionChild] = []
    regulation: dict | None = None
    norms_derived: list[dict] = []
