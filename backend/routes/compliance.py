"""Compliance check — POST /api/compliance/check."""

from __future__ import annotations

from fastapi import APIRouter

from src.compliance.obligations import DocType, Verdict
from src.compliance.pipeline import evaluate, compute_derived_fields

from ..schemas import ComplianceCheckRequest, ComplianceCheckResponse, ComplianceCheckResult

router = APIRouter()


@router.post("/compliance/check", response_model=ComplianceCheckResponse)
async def compliance_check(req: ComplianceCheckRequest):
    ctx = req.context

    contract_type = ctx.get("contract_type", "pkwt")
    try:
        doc_type = DocType(contract_type)
    except ValueError:
        doc_type = DocType.PKWT

    fields = dict(ctx)
    report = evaluate(doc_type, fields)

    results = []
    for r in report.results:
        status_map = {
            Verdict.COMPLIANT: "pass",
            Verdict.VIOLATED: "violation",
            Verdict.NOT_EVALUATED: "unknown",
            Verdict.NOT_APPLICABLE: "pass",
            Verdict.PARTIAL: "warning",
        }
        results.append(ComplianceCheckResult(
            norm_id=r.obligation_id,
            norm_description=r.obligation_description,
            status=status_map.get(r.verdict, "unknown"),
            severity=r.severity.value,
            detail=r.detail,
            legal_basis=r.legal_basis,
        ))

    return ComplianceCheckResponse(
        summary={
            "passed": report.compliant + report.not_applicable,
            "warnings": 0,
            "violations": report.violated,
        },
        results=results,
    )
