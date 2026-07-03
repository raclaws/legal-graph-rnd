"""Document extraction schemas — defines what the LLM must extract per doc type.

The LLM's ONLY job is to fill these schemas from document text.
It does NOT judge compliance. It does NOT interpret law.
If a field cannot be found, it returns null — never guesses.

Post-extraction, code computes derived fields (e.g. salary_meets_ump)
before passing to the obligation evaluator.
"""

from __future__ import annotations

PKWT_EXTRACTION_SCHEMA = {
    "type": "object",
    "description": "Fields extracted from a PKWT (kontrak kerja waktu tertentu) document. Return null for any field not explicitly stated in the document. NEVER infer or guess.",
    "properties": {
        "is_written_document": {
            "type": "boolean",
            "description": "Always true if you are reading this (it's a document)."
        },
        "language": {
            "type": "string",
            "enum": ["indonesian", "english", "bilingual", "other"],
            "description": "Primary language of the document. 'bilingual' if both Indonesian and another language."
        },
        "company_name": {
            "type": ["string", "null"],
            "description": "Nama perusahaan/pemberi kerja. Exact text from document."
        },
        "company_address": {
            "type": ["string", "null"],
            "description": "Alamat perusahaan. Exact text."
        },
        "employee_name": {
            "type": ["string", "null"],
            "description": "Nama pekerja. Exact text."
        },
        "employee_address": {
            "type": ["string", "null"],
            "description": "Alamat pekerja. Exact text."
        },
        "position": {
            "type": ["string", "null"],
            "description": "Jabatan atau jenis pekerjaan. Exact text."
        },
        "work_type_stated": {
            "type": ["string", "null"],
            "description": "Jenis/sifat pekerjaan yang menjadi dasar PKWT (waktu tertentu, musiman, produk baru). Exact text or null if not stated."
        },
        "start_date": {
            "type": ["string", "null"],
            "description": "Tanggal mulai kerja (YYYY-MM-DD). Parse from document."
        },
        "end_date": {
            "type": ["string", "null"],
            "description": "Tanggal berakhir kontrak (YYYY-MM-DD). Null if completion-based (selesainya pekerjaan)."
        },
        "total_duration_months": {
            "type": ["integer", "null"],
            "description": "Total durasi kontrak dalam bulan (termasuk perpanjangan jika disebut). Calculate from dates if both present."
        },
        "is_extension": {
            "type": ["boolean", "null"],
            "description": "Apakah ini perpanjangan PKWT (bukan kontrak pertama)?"
        },
        "previous_contract_ref": {
            "type": ["string", "null"],
            "description": "Referensi ke kontrak sebelumnya jika ini perpanjangan."
        },
        "has_probation": {
            "type": ["boolean", "null"],
            "description": "Apakah ada klausul masa percobaan (probation)? True if any mention of 'masa percobaan', 'probation period', or equivalent. Also true if there's a clause allowing termination without compensation during initial period."
        },
        "salary": {
            "type": ["integer", "null"],
            "description": "Gaji pokok per bulan dalam Rupiah. Number only, no formatting."
        },
        "salary_includes_allowances": {
            "type": ["boolean", "null"],
            "description": "Apakah nominal gaji sudah termasuk tunjangan tetap?"
        },
        "total_compensation": {
            "type": ["integer", "null"],
            "description": "Total upah (gaji pokok + tunjangan tetap) per bulan. If only one number stated, same as salary."
        },
        "province": {
            "type": ["string", "null"],
            "description": "Provinsi tempat kerja. Infer from company address if not explicit. Use standard province name (e.g. 'DKI Jakarta', 'Jawa Barat')."
        },
        "weekly_hours": {
            "type": ["integer", "null"],
            "description": "Jam kerja per minggu. Calculate: daily_hours × work_days if stated separately."
        },
        "work_days_per_week": {
            "type": ["integer", "null"],
            "description": "Hari kerja per minggu (5 or 6)."
        },
        "daily_hours": {
            "type": ["integer", "null"],
            "description": "Jam kerja per hari."
        },
        "annual_leave_days": {
            "type": ["integer", "null"],
            "description": "Jumlah cuti tahunan (hari kerja). Number only."
        },
        "bpjs_mentioned": {
            "type": ["boolean", "null"],
            "description": "Apakah dokumen menyebutkan BPJS (Ketenagakerjaan dan/atau Kesehatan)?"
        },
        "bpjs_tk_mentioned": {
            "type": ["boolean", "null"],
            "description": "BPJS Ketenagakerjaan specifically mentioned?"
        },
        "bpjs_kes_mentioned": {
            "type": ["boolean", "null"],
            "description": "BPJS Kesehatan specifically mentioned?"
        },
        "compensation_clause_exists": {
            "type": ["boolean", "null"],
            "description": "Apakah ada klausul tentang kompensasi/uang kompensasi saat kontrak berakhir?"
        },
        "registered_disnaker": {
            "type": ["boolean", "null"],
            "description": "Apakah ada bukti/pernyataan pencatatan di Disnaker?"
        },
        "regulation_references": {
            "type": "array",
            "items": {"type": "string"},
            "description": "All regulation citations found in the document (e.g. 'UU No. 13 Tahun 2003', 'PP 35 Tahun 2021'). Exact text."
        },
        "termination_clauses": {
            "type": ["string", "null"],
            "description": "Summary of early termination conditions if stated."
        },
        "non_compete_clause": {
            "type": ["boolean", "null"],
            "description": "Apakah ada klausul non-kompetisi?"
        },
        "signed_by_both": {
            "type": ["boolean", "null"],
            "description": "Apakah ada tanda tangan kedua belah pihak?"
        }
    },
    "required": ["is_written_document", "language"]
}


SLIP_GAJI_EXTRACTION_SCHEMA = {
    "type": "object",
    "description": "Fields extracted from a slip gaji (payslip). Return null for any field not found.",
    "properties": {
        "company_name": {"type": ["string", "null"]},
        "employee_name": {"type": ["string", "null"]},
        "period": {"type": ["string", "null"], "description": "Pay period (e.g. 'Juni 2025')"},
        "province": {"type": ["string", "null"]},
        "gaji_pokok": {"type": ["integer", "null"], "description": "Basic salary"},
        "tunjangan_tetap": {"type": ["integer", "null"], "description": "Fixed allowances total"},
        "tunjangan_tidak_tetap": {"type": ["integer", "null"], "description": "Variable allowances"},
        "total_pendapatan": {"type": ["integer", "null"], "description": "Gross income"},
        "potongan_bpjs_tk": {"type": ["integer", "null"], "description": "BPJS TK employee deduction"},
        "potongan_bpjs_kes": {"type": ["integer", "null"], "description": "BPJS Kesehatan employee deduction"},
        "potongan_pph21": {"type": ["integer", "null"], "description": "Income tax deduction"},
        "total_potongan": {"type": ["integer", "null"], "description": "Total deductions"},
        "take_home_pay": {"type": ["integer", "null"], "description": "Net pay"},
        "lembur_jam": {"type": ["integer", "null"], "description": "Overtime hours"},
        "lembur_amount": {"type": ["integer", "null"], "description": "Overtime pay amount"},
        "salary": {"type": ["integer", "null"], "description": "= gaji_pokok + tunjangan_tetap (for UMP comparison)"},
        "bpjs_mentioned": {"type": "boolean", "description": "True if any BPJS line item exists"}
    },
    "required": []
}


# Maps doc type string → schema
EXTRACTION_SCHEMAS = {
    "pkwt": PKWT_EXTRACTION_SCHEMA,
    "pkwtt": PKWT_EXTRACTION_SCHEMA,
    "slip_gaji": SLIP_GAJI_EXTRACTION_SCHEMA,
}


def get_extraction_prompt(doc_type: str, doc_text: str) -> str:
    """Build LLM prompt for schema-constrained extraction.

    The prompt tells the LLM to ONLY extract, never judge.
    """
    schema = EXTRACTION_SCHEMAS.get(doc_type, PKWT_EXTRACTION_SCHEMA)

    import json
    schema_str = json.dumps(schema, indent=2, ensure_ascii=False)

    return f"""Extract structured fields from this Indonesian HR document.

RULES:
1. ONLY extract what is explicitly stated in the document.
2. Return null for any field you cannot find. NEVER guess or infer.
3. If a value is ambiguous, return null.
4. For salary, always return the monthly amount in Rupiah (integer, no dots/commas).
5. For dates, use YYYY-MM-DD format.
6. For boolean fields, only return true if explicitly stated or clearly implied by specific text.

OUTPUT: Return ONLY a JSON object matching this schema:
{schema_str}

DOCUMENT TEXT:
{doc_text}

Return ONLY valid JSON. No explanation, no markdown."""
