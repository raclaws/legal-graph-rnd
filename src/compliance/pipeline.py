"""Compliance Pipeline — connects extraction to evaluation.

Flow:
    1. detect_doc_type(text) → DocType
    2. extract_fields(text, doc_type) → dict (LLM fills schema)
    3. compute_derived_fields(fields, doc_type) → dict (code adds computed values)
    4. evaluate(doc_type, fields) → ComplianceReport (deterministic)

LLM is used ONLY in steps 1 and 2. Steps 3 and 4 are pure code.
"""

from __future__ import annotations

import json

from .extraction_schemas import EXTRACTION_SCHEMAS, get_extraction_prompt
from .obligations import (
    ComplianceReport,
    DocType,
    Obligation,
    evaluate_document,
)
from .obligations_pkwt import get_pkwt_obligations
from .obligations_upah import get_upah_obligations
from .ump_2025 import UMP_2025


def load_norms_from_graph(doc_type: DocType) -> list[Obligation] | None:
    """Load norms from Neo4j for a given doc type. Returns None if graph unavailable."""
    try:
        from src.graph import LegalGraph
        import json as _json

        g = LegalGraph()
        norms = []

        with g.driver.session() as session:
            # Load norms that APPLIES_TO this doc type
            r = session.run(
                """MATCH (n:Norm)-[:APPLIES_TO]->(d:DocType {name: $dt})
                   OPTIONAL MATCH (p:Provision)-[:IMPOSES]->(n)
                   RETURN n, p.node_id AS source_pasal""",
                dt=doc_type.value,
            )

            norm_ids = []
            norm_map = {}
            for rec in r:
                node = rec["n"]
                norm_id = node["id"]
                if norm_id in norm_map:
                    continue
                norm_ids.append(norm_id)
                norm_map[norm_id] = {
                    "id": norm_id,
                    "description": node.get("description", ""),
                    "legal_basis": node.get("legal_basis", ""),
                    "legal_text_summary": node.get("legal_text_summary", ""),
                    "severity": node.get("severity", "high"),
                    "consequence": node.get("consequence", ""),
                    "effective_from": node.get("effective_from", ""),
                    "source_pasal": rec["source_pasal"],
                    "evidence": [],
                    "conditions": [],
                    "edge_cases": [],
                    "applies_to": [],
                }

            # Load evidence for these norms
            if norm_ids:
                r = session.run(
                    """MATCH (n:Norm)-[:REQUIRES]->(e:NormEvidence)
                       WHERE n.id IN $ids
                       RETURN n.id AS norm_id, e""",
                    ids=norm_ids,
                )
                for rec in r:
                    ev = rec["e"]
                    norm_map[rec["norm_id"]]["evidence"].append({
                        "field_path": ev.get("field_path", ""),
                        "operator": ev.get("operator", "exists"),
                        "value": _json.loads(ev["value"]) if ev.get("value") else None,
                        "description": ev.get("description", ""),
                    })

                # Load conditions
                r = session.run(
                    """MATCH (n:Norm)-[:APPLIES_WHEN]->(c:NormCondition)
                       WHERE n.id IN $ids
                       RETURN n.id AS norm_id, c""",
                    ids=norm_ids,
                )
                for rec in r:
                    c = rec["c"]
                    norm_map[rec["norm_id"]]["conditions"].append({
                        "field": c.get("field", ""),
                        "operator": c.get("operator", "eq"),
                        "value": _json.loads(c["value"]) if c.get("value") else None,
                        "description": c.get("description", ""),
                    })

                # Load edge cases
                r = session.run(
                    """MATCH (n:Norm)-[:EXCEPTION]->(ec:NormEdgeCase)
                       WHERE n.id IN $ids
                       RETURN n.id AS norm_id, ec""",
                    ids=norm_ids,
                )
                for rec in r:
                    ec = rec["ec"]
                    norm_map[rec["norm_id"]]["edge_cases"].append({
                        "condition": ec.get("condition_text", ""),
                        "behavior": ec.get("behavior", ""),
                        "legal_basis": ec.get("legal_basis", ""),
                    })

                # Load all applies_to doc types per norm
                r = session.run(
                    """MATCH (n:Norm)-[:APPLIES_TO]->(d:DocType)
                       WHERE n.id IN $ids
                       RETURN n.id AS norm_id, d.name AS dt_name""",
                    ids=norm_ids,
                )
                for rec in r:
                    norm_map[rec["norm_id"]]["applies_to"].append(rec["dt_name"])

        g.close()

        # Convert to Obligation objects
        from .obligations import Condition, Evidence, EdgeCase, Severity, Operator

        operator_map = {v.value: v for v in Operator}
        severity_map = {v.value: v for v in Severity}
        doctype_map = {v.value: v for v in DocType}

        for nm in norm_map.values():
            evidence_list = []
            for ev in nm["evidence"]:
                op = operator_map.get(ev["operator"], Operator.EXISTS)
                evidence_list.append(Evidence(
                    field_path=ev["field_path"],
                    operator=op,
                    value=ev["value"],
                    description=ev["description"],
                ))

            condition_list = []
            for c in nm["conditions"]:
                op = operator_map.get(c["operator"], Operator.EQ)
                condition_list.append(Condition(
                    field=c["field"],
                    operator=op,
                    value=c["value"],
                    description=c["description"],
                ))

            edge_case_list = []
            for ec in nm["edge_cases"]:
                edge_case_list.append(EdgeCase(
                    condition=ec["condition"],
                    behavior=ec["behavior"],
                    legal_basis=ec["legal_basis"],
                ))

            applies_to_list = [doctype_map[dt] for dt in nm["applies_to"] if dt in doctype_map]

            norms.append(Obligation(
                id=nm["id"],
                description=nm["description"],
                legal_basis=nm["legal_basis"],
                legal_text_summary=nm["legal_text_summary"],
                applies_to=applies_to_list,
                conditions=condition_list,
                evidence=evidence_list,
                severity=severity_map.get(nm["severity"], Severity.HIGH),
                consequence=nm["consequence"],
                effective_from=nm["effective_from"],
                edge_cases=edge_case_list,
            ))

        return norms if norms else None

    except Exception:
        return None


# === Step 1: Doc type detection ===

DOC_TYPE_PROMPT = """Classify this Indonesian HR document into exactly one type.

Types:
- pkwt: Perjanjian Kerja Waktu Tertentu (fixed-term employment contract)
- pkwtt: Perjanjian Kerja Waktu Tidak Tertentu (permanent employment contract)
- sk_phk: Surat Keputusan PHK (termination letter)
- slip_gaji: Slip gaji / payslip
- peraturan_perusahaan: Peraturan Perusahaan (company regulation)
- surat_peringatan: Surat Peringatan (warning letter)
- other: None of the above

Return ONLY the type string, nothing else. Example: pkwt

DOCUMENT TEXT (first 2000 chars):
{text}"""


def detect_doc_type_prompt(text: str) -> str:
    """Return the prompt for doc type classification."""
    return DOC_TYPE_PROMPT.format(text=text[:2000])


def parse_doc_type(llm_response: str) -> DocType:
    """Parse LLM response into DocType. Conservative — defaults to OTHER."""
    cleaned = llm_response.strip().lower().replace('"', '').replace("'", "")
    mapping = {
        "pkwt": DocType.PKWT,
        "pkwtt": DocType.PKWTT,
        "sk_phk": DocType.SK_PHK,
        "slip_gaji": DocType.SLIP_GAJI,
        "peraturan_perusahaan": DocType.PERATURAN_PERUSAHAAN,
        "surat_peringatan": DocType.SURAT_PERINGATAN,
        "other": DocType.OTHER,
    }
    return mapping.get(cleaned, DocType.OTHER)


# === Step 2: Field extraction (LLM) ===

def parse_extracted_fields(llm_response: str) -> dict | None:
    """Parse LLM extraction response into dict. Returns None on failure."""
    raw = llm_response.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return None


# === Step 3: Derived fields (pure code) ===

def compute_derived_fields(fields: dict, doc_type: DocType) -> dict:
    """Add computed fields that the evaluator needs. No LLM, pure logic.

    This is where UMP comparison, duration calculation, etc. happen.
    """
    enriched = dict(fields)

    # --- Salary vs UMP ---
    salary = fields.get("total_compensation") or fields.get("salary")
    province = fields.get("province")

    if salary and province:
        ump_entry = next(
            (u for u in UMP_2025 if u["province"].lower() == province.lower()),
            None,
        )
        if ump_entry:
            enriched["salary_meets_ump"] = salary >= ump_entry["amount"]
            enriched["_ump_amount"] = ump_entry["amount"]
            enriched["_ump_province"] = ump_entry["province"]
        else:
            enriched["salary_meets_ump"] = None
    else:
        enriched["salary_meets_ump"] = None

    # --- Duration calculation ---
    start = fields.get("start_date")
    end = fields.get("end_date")
    if start and end and not fields.get("total_duration_months"):
        try:
            from datetime import date
            s = date.fromisoformat(start)
            e = date.fromisoformat(end)
            months = (e.year - s.year) * 12 + (e.month - s.month)
            enriched["total_duration_months"] = max(months, 1)
        except (ValueError, TypeError):
            pass

    # --- Weekly hours calculation ---
    if not fields.get("weekly_hours"):
        daily = fields.get("daily_hours")
        days = fields.get("work_days_per_week")
        if daily and days:
            enriched["weekly_hours"] = daily * days

    # --- is_written_document is always true (we're reading a document) ---
    enriched["is_written_document"] = True

    # --- Slip gaji derived fields ---
    if doc_type == DocType.SLIP_GAJI:
        gaji_pokok = fields.get("gaji_pokok")
        tunjangan_tetap = fields.get("tunjangan_tetap") or 0
        total_pendapatan = fields.get("total_pendapatan")
        total_potongan = fields.get("total_potongan")

        # salary for UMP comparison = gaji_pokok + tunjangan_tetap
        if gaji_pokok and not salary:
            salary = gaji_pokok + tunjangan_tetap
            enriched["salary"] = salary
            if province:
                ump_entry = next(
                    (u for u in UMP_2025 if u["province"].lower() == province.lower()),
                    None,
                )
                if ump_entry:
                    enriched["salary_meets_ump"] = salary >= ump_entry["amount"]
                    enriched["_ump_amount"] = ump_entry["amount"]
                    enriched["_ump_province"] = ump_entry["province"]

        # Base salary ratio: pokok >= 75% of (pokok + tunjangan_tetap)
        if gaji_pokok and tunjangan_tetap > 0:
            total_fixed = gaji_pokok + tunjangan_tetap
            enriched["base_salary_ratio_valid"] = gaji_pokok >= (total_fixed * 0.75)
        elif gaji_pokok:
            enriched["base_salary_ratio_valid"] = True  # 100% is pokok

        # Deduction percentage check: total_potongan <= 50% of total_pendapatan
        if total_potongan and total_pendapatan and total_pendapatan > 0:
            enriched["deduction_pct_valid"] = total_potongan <= (total_pendapatan * 0.50)

        # Overtime paid check
        lembur_jam = fields.get("lembur_jam")
        lembur_amount = fields.get("lembur_amount")
        if lembur_jam and lembur_jam > 0:
            enriched["overtime_hours"] = lembur_jam
            enriched["overtime_paid"] = lembur_amount is not None and lembur_amount > 0
            # Rate check: 1/173 * salary * 1.5 for first hour
            if lembur_amount and salary:
                expected_first_hour = (salary / 173) * 1.5
                enriched["overtime_rate_correct"] = lembur_amount >= (expected_first_hour * 0.9)  # 10% tolerance
        elif lembur_jam == 0 or lembur_jam is None:
            enriched["overtime_paid"] = True  # no overtime = no issue

        # BPJS check
        if fields.get("potongan_bpjs_tk") or fields.get("potongan_bpjs_kes"):
            enriched["bpjs_mentioned"] = True

    # --- Peraturan Perusahaan derived fields ---
    if doc_type == DocType.PERATURAN_PERUSAHAAN:
        if not fields.get("currency"):
            enriched["currency"] = None

    # --- SK PHK derived fields ---
    if doc_type == DocType.SK_PHK:
        # Notice period: days between notice_date and effective_date
        notice_date = fields.get("notice_date")
        effective_date = fields.get("effective_date")
        if notice_date and effective_date and not fields.get("notice_period_days"):
            try:
                from datetime import date
                nd = date.fromisoformat(notice_date)
                ed = date.fromisoformat(effective_date)
                enriched["notice_period_days"] = (ed - nd).days
            except (ValueError, TypeError):
                pass

        # Severance formula check: PP 35/2021 Pasal 40
        # Table: <1yr=1, 1-2=2, 2-3=3, 3-4=4, 4-5=5, 5-6=6, 6-7=7, 7-8=8, >=8=9
        tenure = fields.get("tenure_years")
        severance_months = fields.get("severance_months")
        if tenure is not None and severance_months is not None:
            if tenure < 1:
                expected = 1
            elif tenure < 2:
                expected = 2
            elif tenure < 3:
                expected = 3
            elif tenure < 4:
                expected = 4
            elif tenure < 5:
                expected = 5
            elif tenure < 6:
                expected = 6
            elif tenure < 7:
                expected = 7
            elif tenure < 8:
                expected = 8
            else:
                expected = 9
            enriched["severance_meets_formula"] = severance_months >= expected
            enriched["_expected_severance_months"] = expected

    # --- Surat Peringatan derived fields ---
    if doc_type == DocType.SURAT_PERINGATAN:
        # valid_period_days from issued_date and valid_until
        issued = fields.get("issued_date")
        valid_until = fields.get("valid_until")
        if issued and valid_until and not fields.get("valid_period_days"):
            try:
                from datetime import date
                id_ = date.fromisoformat(issued)
                vu = date.fromisoformat(valid_until)
                enriched["valid_period_days"] = (vu - id_).days
            except (ValueError, TypeError):
                pass

    return enriched


# === Step 4: Evaluate (deterministic) ===

def _get_engine_registry():
    """Lazy-load the YAML-based engine registry."""
    from pathlib import Path
    from src.compliance.engine.registry import Registry

    domains_dir = Path(__file__).parent / "domains"
    registry = Registry()
    registry.load_directory(domains_dir)
    return registry


def get_obligations_for_doc_type(doc_type: DocType) -> list[Obligation]:
    """Load obligations for a doc type. Engine-first, graph, then Python fallback."""

    # Try YAML engine
    registry = _get_engine_registry()
    engine_obs = registry.get_obligations(doc_type.value)
    if engine_obs:
        # Adapt engine Obligation to pipeline Obligation (same interface)
        from src.compliance.engine.types import Obligation as EngOb
        from .obligations import Obligation as PipeOb, Evidence as PipeEv, Condition as PipeCond, EdgeCase as PipeEC, Severity as PipeSev, Operator as PipeOp

        op_map = {
            "eq": PipeOp.EQ, "neq": PipeOp.NEQ, "gt": PipeOp.GT, "gte": PipeOp.GTE,
            "lt": PipeOp.LT, "lte": PipeOp.LTE, "in": PipeOp.IN, "not_in": PipeOp.NOT_IN,
            "exists": PipeOp.EXISTS, "not_exists": PipeOp.NOT_EXISTS, "between": PipeOp.BETWEEN,
        }
        sev_map = {"critical": PipeSev.CRITICAL, "high": PipeSev.HIGH, "medium": PipeSev.MEDIUM, "low": PipeSev.LOW}

        adapted = []
        for eo in engine_obs:
            adapted.append(PipeOb(
                id=eo.id,
                description=eo.description,
                legal_basis=eo.legal_basis,
                legal_text_summary=eo.legal_text,
                applies_to=[doc_type],
                conditions=[PipeCond(field=c.field, operator=op_map[c.op.value], value=c.value, description=c.note) for c in eo.conditions],
                evidence=[PipeEv(field_path=e.field, operator=op_map[e.op.value], value=e.value, description=e.note) for e in eo.evidence],
                severity=sev_map[eo.severity.value],
                consequence=eo.consequence,
                effective_from=eo.effective_from,
                edge_cases=[PipeEC(condition=ec.when, behavior=ec.then, legal_basis=ec.basis) for ec in eo.edge_cases],
            ))
        return adapted

    # Try loading from Neo4j
    graph_norms = load_norms_from_graph(doc_type)
    if graph_norms:
        return graph_norms

    # Fallback to Python files
    all_obligations: list[Obligation] = []

    if doc_type in (DocType.PKWT, DocType.PKWTT):
        all_obligations.extend(get_pkwt_obligations())

    all_obligations.extend(get_upah_obligations())

    # Deduplicate by ID
    seen = set()
    deduped = []
    for ob in all_obligations:
        if ob.id not in seen:
            seen.add(ob.id)
            deduped.append(ob)

    return deduped


def evaluate(doc_type: DocType, fields: dict) -> ComplianceReport:
    """Run deterministic evaluation. No LLM."""
    enriched = compute_derived_fields(fields, doc_type)
    obligations = get_obligations_for_doc_type(doc_type)
    return evaluate_document(doc_type, enriched, obligations)


# === Full pipeline (orchestrator) ===

def run_compliance_pipeline(
    doc_text: str,
    call_llm_fn,
    filename: str = "",
) -> tuple[ComplianceReport | None, list[str]]:
    """Run the full compliance pipeline.

    Args:
        doc_text: Extracted document text
        call_llm_fn: Function(prompt: str) -> str that calls the LLM
        filename: Original filename (for logging)

    Returns:
        (ComplianceReport, logs) — report is None if pipeline fails
    """
    logs = []

    # Step 1: Detect doc type
    logs.append("Step 1/4: Detecting document type...")
    type_prompt = detect_doc_type_prompt(doc_text)
    type_response = call_llm_fn(type_prompt)
    if not type_response:
        logs.append("  FAILED: no LLM response for doc type")
        return None, logs
    doc_type = parse_doc_type(type_response)
    logs.append(f"  → {doc_type.value}")

    if doc_type == DocType.OTHER:
        logs.append("  Document type not supported for deterministic evaluation")
        return None, logs

    # Step 2: Extract fields
    logs.append("Step 2/4: Extracting fields (LLM schema-fill)...")
    extraction_prompt = get_extraction_prompt(doc_type.value, doc_text)
    extraction_response = call_llm_fn(extraction_prompt)
    if not extraction_response:
        logs.append("  FAILED: no LLM response for extraction")
        return None, logs
    fields = parse_extracted_fields(extraction_response)
    if not fields:
        logs.append("  FAILED: could not parse extraction JSON")
        return None, logs

    non_null = sum(1 for v in fields.values() if v is not None)
    logs.append(f"  → {non_null} fields extracted")

    # Step 3: Compute derived fields
    logs.append("Step 3/4: Computing derived fields...")
    enriched = compute_derived_fields(fields, doc_type)
    derived_count = len(enriched) - len(fields)
    logs.append(f"  → {derived_count} derived fields added")

    if enriched.get("salary_meets_ump") is not None:
        ump_str = f"Rp {enriched.get('_ump_amount', 0):,.0f}"
        sal_str = f"Rp {enriched.get('total_compensation') or enriched.get('salary', 0):,.0f}"
        logs.append(f"  → UMP check: {sal_str} vs {ump_str} ({enriched.get('_ump_province', '?')})")

    # Step 4: Evaluate
    logs.append("Step 4/4: Evaluating obligations (deterministic)...")
    obligations = get_obligations_for_doc_type(doc_type)
    report = evaluate_document(doc_type, enriched, obligations)
    report.extracted_fields = enriched
    logs.append(f"  → {report.obligations_checked} obligations checked")
    logs.append(f"  → Compliant: {report.compliant} | Violated: {report.violated} | Not evaluated: {report.not_evaluated}")
    logs.append(f"  → Score: {report.score_pct}%")

    return report, logs
