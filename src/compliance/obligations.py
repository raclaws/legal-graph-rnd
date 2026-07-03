"""Obligation Layer — deterministic compliance evaluation.

Architecture:
    Corpus (Pasal in Neo4j)
        ↓ derived from (human-verified)
    Obligation Layer (this file)
        ↓ matched against
    Extracted Document Fields (LLM schema-fill)
        ↓ evaluated by
    Deterministic Verdict

Principles:
1. Every obligation traces to a specific Pasal (auditable provenance)
2. Evaluation is pure logic — no LLM judgment in compliance determination
3. Missing data = "tidak dapat dievaluasi" (never assumed compliant)
4. Edge cases are stated explicitly with their conditions
5. Temporal: obligations know when they took effect (pre/post Cipta Kerja)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# === Core types ===

class Verdict(Enum):
    COMPLIANT = "compliant"
    VIOLATED = "violated"
    PARTIAL = "partial"
    NOT_EVALUATED = "tidak_dapat_dievaluasi"
    NOT_APPLICABLE = "tidak_berlaku"


class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DocType(Enum):
    PKWT = "pkwt"
    PKWTT = "pkwtt"
    SK_PHK = "sk_phk"
    SLIP_GAJI = "slip_gaji"
    PERATURAN_PERUSAHAAN = "peraturan_perusahaan"
    SURAT_PERINGATAN = "surat_peringatan"
    OTHER = "other"


class Operator(Enum):
    GTE = "gte"
    LTE = "lte"
    GT = "gt"
    LT = "lt"
    EQ = "eq"
    NEQ = "neq"
    IN = "in"
    NOT_IN = "not_in"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"
    BETWEEN = "between"
    MAX_DAYS = "max_days"
    BEFORE = "before"


@dataclass
class Condition:
    """When does this obligation apply?"""
    field: str
    operator: Operator
    value: Any
    description: str = ""


@dataclass
class Evidence:
    """What field in the document proves fulfillment?"""
    field_path: str
    operator: Operator
    value: Any = None
    description: str = ""


@dataclass
class EdgeCase:
    """Explicit edge case — stated, not hidden."""
    condition: str
    behavior: str
    legal_basis: str


@dataclass
class Obligation:
    """A single evaluable compliance requirement.

    Traces to corpus: legal_basis is a NodeID path in the graph.
    """
    id: str
    description: str
    legal_basis: str
    legal_text_summary: str
    applies_to: list[DocType]
    conditions: list[Condition] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    severity: Severity = Severity.HIGH
    consequence: str = ""
    effective_from: str = ""
    edge_cases: list[EdgeCase] = field(default_factory=list)


@dataclass
class EvaluationResult:
    """Result of evaluating one obligation against one document."""
    obligation_id: str
    obligation_description: str
    legal_basis: str
    verdict: Verdict
    detail: str
    severity: Severity
    extracted_value: Any = None
    expected_value: Any = None
    edge_case_triggered: str | None = None


@dataclass
class ComplianceReport:
    """Full deterministic compliance report for a document."""
    doc_type: DocType
    results: list[EvaluationResult]
    extracted_fields: dict
    obligations_checked: int = 0
    compliant: int = 0
    violated: int = 0
    not_evaluated: int = 0
    not_applicable: int = 0
    score_pct: int = 0

    def compute_summary(self):
        self.obligations_checked = len(self.results)
        self.compliant = sum(1 for r in self.results if r.verdict == Verdict.COMPLIANT)
        self.violated = sum(1 for r in self.results if r.verdict == Verdict.VIOLATED)
        self.not_evaluated = sum(1 for r in self.results if r.verdict == Verdict.NOT_EVALUATED)
        self.not_applicable = sum(1 for r in self.results if r.verdict == Verdict.NOT_APPLICABLE)
        evaluable = self.obligations_checked - self.not_applicable - self.not_evaluated
        self.score_pct = int((self.compliant / evaluable) * 100) if evaluable > 0 else 0


# === Evaluator (pure logic) ===

def _get_nested(data: dict, path: str) -> Any:
    """Get nested value from dot-separated path."""
    parts = path.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
        if current is None:
            return None
    return current


def _check_evidence(evidence: Evidence, fields: dict) -> tuple[Verdict, Any]:
    """Check one piece of evidence against extracted fields.

    Returns (verdict, extracted_value).
    """
    actual = _get_nested(fields, evidence.field_path)

    if evidence.operator == Operator.EXISTS:
        if actual is not None and actual != "" and actual is not False:
            return Verdict.COMPLIANT, actual
        return Verdict.VIOLATED, None

    if evidence.operator == Operator.NOT_EXISTS:
        if actual is None or actual == "":
            return Verdict.COMPLIANT, None
        return Verdict.VIOLATED, actual

    if actual is None:
        return Verdict.NOT_EVALUATED, None

    if evidence.operator == Operator.GTE:
        if actual >= evidence.value:
            return Verdict.COMPLIANT, actual
        return Verdict.VIOLATED, actual

    if evidence.operator == Operator.LTE:
        if actual <= evidence.value:
            return Verdict.COMPLIANT, actual
        return Verdict.VIOLATED, actual

    if evidence.operator == Operator.GT:
        if actual > evidence.value:
            return Verdict.COMPLIANT, actual
        return Verdict.VIOLATED, actual

    if evidence.operator == Operator.LT:
        if actual < evidence.value:
            return Verdict.COMPLIANT, actual
        return Verdict.VIOLATED, actual

    if evidence.operator == Operator.EQ:
        if actual == evidence.value:
            return Verdict.COMPLIANT, actual
        return Verdict.VIOLATED, actual

    if evidence.operator == Operator.NEQ:
        if actual != evidence.value:
            return Verdict.COMPLIANT, actual
        return Verdict.VIOLATED, actual

    if evidence.operator == Operator.IN:
        if actual in evidence.value:
            return Verdict.COMPLIANT, actual
        return Verdict.VIOLATED, actual

    if evidence.operator == Operator.MAX_DAYS:
        if isinstance(actual, (int, float)) and actual <= evidence.value:
            return Verdict.COMPLIANT, actual
        elif isinstance(actual, (int, float)):
            return Verdict.VIOLATED, actual
        return Verdict.NOT_EVALUATED, actual

    return Verdict.NOT_EVALUATED, actual


def _check_conditions(conditions: list[Condition], fields: dict) -> bool:
    """Check if obligation applies given document fields.

    Returns True if ALL conditions are met (obligation applies).
    If a condition field is missing, assume obligation applies (conservative).
    """
    for cond in conditions:
        actual = _get_nested(fields, cond.field)
        if actual is None:
            continue

        if cond.operator == Operator.EQ and actual != cond.value:
            return False
        if cond.operator == Operator.NEQ and actual == cond.value:
            return False
        if cond.operator == Operator.IN and actual not in cond.value:
            return False
        if cond.operator == Operator.GTE and actual < cond.value:
            return False
        if cond.operator == Operator.LTE and actual > cond.value:
            return False

    return True


def _check_edge_cases(obligation: Obligation, fields: dict) -> EdgeCase | None:
    """Check if any edge case applies. Returns first matching edge case."""
    for ec in obligation.edge_cases:
        pass
    return None


def evaluate_obligation(obligation: Obligation, doc_type: DocType, fields: dict) -> EvaluationResult:
    """Evaluate a single obligation against extracted fields. Pure logic."""

    if doc_type not in obligation.applies_to:
        return EvaluationResult(
            obligation_id=obligation.id,
            obligation_description=obligation.description,
            legal_basis=obligation.legal_basis,
            verdict=Verdict.NOT_APPLICABLE,
            detail=f"Tidak berlaku untuk dokumen tipe {doc_type.value}",
            severity=obligation.severity,
        )

    if not _check_conditions(obligation.conditions, fields):
        return EvaluationResult(
            obligation_id=obligation.id,
            obligation_description=obligation.description,
            legal_basis=obligation.legal_basis,
            verdict=Verdict.NOT_APPLICABLE,
            detail="Kondisi tidak terpenuhi",
            severity=obligation.severity,
        )

    if not obligation.evidence:
        return EvaluationResult(
            obligation_id=obligation.id,
            obligation_description=obligation.description,
            legal_basis=obligation.legal_basis,
            verdict=Verdict.NOT_EVALUATED,
            detail="Tidak ada evidence rule yang didefinisikan",
            severity=obligation.severity,
        )

    # Evaluate all evidence — ALL must pass for compliant
    worst_verdict = Verdict.COMPLIANT
    details = []
    extracted = None
    expected = None

    for ev in obligation.evidence:
        verdict, actual = _check_evidence(ev, fields)
        extracted = actual
        expected = ev.value

        if verdict == Verdict.VIOLATED:
            worst_verdict = Verdict.VIOLATED
            details.append(f"GAGAL: {ev.description or ev.field_path} — ditemukan: {actual}, diharuskan: {ev.operator.value} {ev.value}")
        elif verdict == Verdict.NOT_EVALUATED:
            if worst_verdict != Verdict.VIOLATED:
                worst_verdict = Verdict.NOT_EVALUATED
            details.append(f"TIDAK DAPAT DIEVALUASI: {ev.description or ev.field_path} — data tidak ditemukan dalam dokumen")
        else:
            details.append(f"OK: {ev.description or ev.field_path}")

    return EvaluationResult(
        obligation_id=obligation.id,
        obligation_description=obligation.description,
        legal_basis=obligation.legal_basis,
        verdict=worst_verdict,
        detail=" | ".join(details),
        severity=obligation.severity,
        extracted_value=extracted,
        expected_value=expected,
    )


def evaluate_document(doc_type: DocType, fields: dict, obligations: list[Obligation]) -> ComplianceReport:
    """Evaluate all obligations against a document. Deterministic."""
    results = []
    for ob in obligations:
        result = evaluate_obligation(ob, doc_type, fields)
        results.append(result)

    report = ComplianceReport(
        doc_type=doc_type,
        results=results,
        extracted_fields=fields,
    )
    report.compute_summary()
    return report
