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


SK_PHK_EXTRACTION_SCHEMA = {
    "type": "object",
    "description": "Fields extracted from an SK PHK (termination letter). Return null for any field not found.",
    "properties": {
        "company_name": {"type": ["string", "null"], "description": "Nama perusahaan yang menerbitkan SK"},
        "employee_name": {"type": ["string", "null"], "description": "Nama pekerja yang di-PHK"},
        "employee_position": {"type": ["string", "null"], "description": "Jabatan pekerja"},
        "phk_reason_stated": {"type": ["string", "null"], "description": "Alasan PHK yang tercantum (exact text)"},
        "phk_reason_legal_basis": {"type": ["string", "null"], "description": "Dasar hukum yang dirujuk untuk PHK (e.g. 'PP 35/2021 Pasal 43')"},
        "effective_date": {"type": ["string", "null"], "description": "Tanggal efektif PHK (YYYY-MM-DD)"},
        "notice_date": {"type": ["string", "null"], "description": "Tanggal surat pemberitahuan diterbitkan (YYYY-MM-DD)"},
        "notice_period_days": {"type": ["integer", "null"], "description": "Jarak hari antara notice_date dan effective_date"},
        "tenure_years": {"type": ["number", "null"], "description": "Masa kerja pekerja (tahun, bisa desimal)"},
        "start_date": {"type": ["string", "null"], "description": "Tanggal mulai bekerja (YYYY-MM-DD)"},
        "severance_months": {"type": ["number", "null"], "description": "Jumlah bulan pesangon yang diberikan"},
        "severance_amount": {"type": ["integer", "null"], "description": "Nominal pesangon (Rupiah)"},
        "uang_penghargaan_stated": {"type": ["boolean", "null"], "description": "Uang penghargaan masa kerja (UPMK) disebutkan"},
        "uang_penghargaan_amount": {"type": ["integer", "null"], "description": "Nominal UPMK (Rupiah)"},
        "uang_penggantian_hak_stated": {"type": ["boolean", "null"], "description": "Uang penggantian hak disebutkan"},
        "uang_penggantian_hak_amount": {"type": ["integer", "null"], "description": "Nominal penggantian hak (Rupiah)"},
        "bipartit_evidence": {"type": ["boolean", "null"], "description": "Bukti/referensi perundingan bipartit ada dalam dokumen"},
        "bipartit_date": {"type": ["string", "null"], "description": "Tanggal perundingan bipartit jika disebutkan (YYYY-MM-DD)"},
        "severance_meets_formula": {"type": ["boolean", "null"], "description": "Jika bisa dihitung: apakah pesangon sesuai formula PP 35/2021 Pasal 40. Null jika tidak bisa dihitung."},
        "base_salary": {"type": ["integer", "null"], "description": "Upah pokok + tunjangan tetap per bulan (basis perhitungan pesangon)"},
        "signed_by": {"type": ["string", "null"], "description": "Nama dan jabatan penandatangan SK"},
    },
    "required": []
}


SURAT_PERINGATAN_EXTRACTION_SCHEMA = {
    "type": "object",
    "description": "Fields extracted from a Surat Peringatan (warning letter). Return null for any field not found.",
    "properties": {
        "company_name": {"type": ["string", "null"], "description": "Nama perusahaan"},
        "employee_name": {"type": ["string", "null"], "description": "Nama pekerja yang dikenai SP"},
        "employee_position": {"type": ["string", "null"], "description": "Jabatan pekerja"},
        "sp_level": {"type": ["integer", "null"], "description": "Tingkat SP: 1, 2, atau 3"},
        "violation_stated": {"type": ["string", "null"], "description": "Pelanggaran yang dituduhkan (exact text)"},
        "violation_date": {"type": ["string", "null"], "description": "Tanggal pelanggaran terjadi (YYYY-MM-DD)"},
        "regulation_basis_stated": {"type": ["boolean", "null"], "description": "Apakah ada rujukan ke aturan yang dilanggar (PK/PP/PKB)"},
        "regulation_basis_text": {"type": ["string", "null"], "description": "Teks rujukan aturan yang dilanggar"},
        "issued_date": {"type": ["string", "null"], "description": "Tanggal SP dikeluarkan (YYYY-MM-DD)"},
        "valid_until": {"type": ["string", "null"], "description": "Tanggal berakhir masa berlaku SP (YYYY-MM-DD)"},
        "valid_period_days": {"type": ["integer", "null"], "description": "Masa berlaku SP dalam hari (hitung dari issued_date ke valid_until, atau dari teks eksplisit)"},
        "previous_sp_referenced": {"type": ["boolean", "null"], "description": "Apakah SP sebelumnya direferensikan (untuk SP-2/SP-3)"},
        "previous_sp_number": {"type": ["string", "null"], "description": "Nomor SP sebelumnya jika direferensikan"},
        "right_to_respond_stated": {"type": ["boolean", "null"], "description": "Apakah hak pekerja untuk menanggapi disebutkan"},
        "consequence_stated": {"type": ["string", "null"], "description": "Konsekuensi jika pelanggaran berulang (exact text)"},
        "signed_by_authority": {"type": ["boolean", "null"], "description": "Ditandatangani oleh pejabat berwenang (HRD/Direktur/atasan)"},
        "signed_by": {"type": ["string", "null"], "description": "Nama dan jabatan penandatangan"},
    },
    "required": []
}


PERATURAN_PERUSAHAAN_EXTRACTION_SCHEMA = {
    "type": "object",
    "description": "Fields extracted from a Peraturan Perusahaan (company regulation). Return null for any field not found. For boolean 'has_X' fields, return true only if the topic is substantively addressed (not just mentioned in passing).",
    "properties": {
        "company_name": {"type": ["string", "null"], "description": "Nama perusahaan"},
        "approved_by_disnaker": {"type": ["boolean", "null"], "description": "Ada bukti pengesahan Disnaker (nomor SK, tanda pengesahan)"},
        "approval_number": {"type": ["string", "null"], "description": "Nomor SK pengesahan Disnaker"},
        "valid_from": {"type": ["string", "null"], "description": "Tanggal mulai berlaku (YYYY-MM-DD)"},
        "valid_until": {"type": ["string", "null"], "description": "Tanggal berakhir (YYYY-MM-DD)"},
        "valid_period_stated": {"type": ["boolean", "null"], "description": "Masa berlaku PP disebutkan eksplisit"},
        "employee_count": {"type": ["integer", "null"], "description": "Jumlah pekerja yang disebutkan dalam dokumen"},
        "has_wage_structure": {"type": ["boolean", "null"], "description": "Bab/pasal tentang struktur dan skala upah ada"},
        "weekly_hours": {"type": ["integer", "null"], "description": "Jam kerja per minggu yang ditetapkan"},
        "work_days_per_week": {"type": ["integer", "null"], "description": "Hari kerja per minggu (5 atau 6)"},
        "annual_leave_days": {"type": ["integer", "null"], "description": "Jumlah cuti tahunan"},
        "overtime_paid": {"type": ["boolean", "null"], "description": "Klausul lembur dan pembayaran ada"},
        "thr_clause_exists": {"type": ["boolean", "null"], "description": "Klausul THR ada"},
        "sick_leave_pay_policy": {"type": ["boolean", "null"], "description": "Kebijakan upah sakit tercantum"},
        "bpjs_policy_stated": {"type": ["boolean", "null"], "description": "Kebijakan BPJS tercantum"},
        "phk_procedure_stated": {"type": ["boolean", "null"], "description": "Prosedur PHK diatur"},
        "disciplinary_procedure": {"type": ["boolean", "null"], "description": "Prosedur disiplin/SP diatur"},
        "grievance_mechanism": {"type": ["boolean", "null"], "description": "Mekanisme pengaduan pekerja ada"},
        "late_penalty_clause": {"type": ["boolean", "null"], "description": "Klausul denda keterlambatan upah ada"},
        "payment_schedule_stated": {"type": ["string", "null"], "description": "Jadwal pembayaran upah"},
        "province": {"type": ["string", "null"], "description": "Provinsi lokasi perusahaan"},
        "salary_meets_ump": {"type": ["boolean", "null"], "description": "Jika upah minimum disebutkan, apakah >= UMP. Null jika tidak disebutkan."},
    },
    "required": []
}


# Maps doc type string → schema
EXTRACTION_SCHEMAS = {
    "pkwt": PKWT_EXTRACTION_SCHEMA,
    "pkwtt": PKWT_EXTRACTION_SCHEMA,
    "slip_gaji": SLIP_GAJI_EXTRACTION_SCHEMA,
    "sk_phk": SK_PHK_EXTRACTION_SCHEMA,
    "surat_peringatan": SURAT_PERINGATAN_EXTRACTION_SCHEMA,
    "peraturan_perusahaan": PERATURAN_PERUSAHAAN_EXTRACTION_SCHEMA,
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
