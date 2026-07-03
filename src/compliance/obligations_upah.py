"""Upah (Wages) Obligations — derived from PP 36/2021 + PP 51/2023.

Applies to ANY document that contains wage/salary claims:
- PKWT / PKWTT (salary clause)
- Slip Gaji (actual payment)
- Peraturan Perusahaan (wage policy)
- SK PHK (severance amounts reference base salary)

Topic: upah
Trigger: document contains salary/wage information

Source regulations:
- PP/2021/36 (Pengupahan)
- PP/2023/51 (Perubahan PP 36 — UMP/UMK formula)
- UU/2003/13/Bab/X (Pengupahan — base)
"""

from .obligations import (
    Condition,
    DocType,
    EdgeCase,
    Evidence,
    Obligation,
    Operator,
    Severity,
)


UPAH_OBLIGATIONS: list[Obligation] = [
    # --- 1. Salary >= UMP ---
    Obligation(
        id="UPAH-01",
        description="Upah tidak boleh lebih rendah dari upah minimum",
        legal_basis="PP/2021/36/Bab/IV/Pasal/23",
        legal_text_summary="Pengusaha dilarang membayar Upah lebih rendah dari Upah minimum.",
        applies_to=[DocType.PKWT, DocType.PKWTT, DocType.SLIP_GAJI, DocType.PERATURAN_PERUSAHAAN],
        evidence=[
            Evidence(
                field_path="salary_meets_ump",
                operator=Operator.EQ,
                value=True,
                description="Gaji >= UMP provinsi",
            ),
        ],
        severity=Severity.CRITICAL,
        consequence="Pidana penjara 1-4 tahun dan/atau denda Rp 100jt-400jt (UU 13/2003 Pasal 185)",
        effective_from="2003-03-25",
        edge_cases=[
            EdgeCase(
                condition="Usaha mikro dan kecil",
                behavior="Dapat dikecualikan berdasarkan Perpres (PP 36/2021 Pasal 36-38). Harus memenuhi kriteria UU UMKM.",
                legal_basis="PP/2021/36/Bab/VI/Pasal/36",
            ),
            EdgeCase(
                condition="Upah harian (bukan bulanan)",
                behavior="Dihitung: upah sehari x 25 (6 hari kerja) atau x 21 (5 hari kerja). Hasil harus >= UMP/bulan.",
                legal_basis="PP/2021/36/Bab/III/Pasal/17",
            ),
            EdgeCase(
                condition="Upah satuan hasil (piece-rate)",
                behavior="Upah bulanan efektif tetap harus >= UMP. Dihitung dari rata-rata hasil kerja sebulan.",
                legal_basis="PP/2021/36/Bab/III/Pasal/19",
            ),
            EdgeCase(
                condition="Gaji pokok < UMP tapi total (pokok + tunjangan tetap) >= UMP",
                behavior="Yang dibandingkan: upah = gaji pokok + tunjangan tetap. Tunjangan tidak tetap tidak dihitung.",
                legal_basis="PP/2021/36/Bab/I/Pasal/7",
            ),
        ],
    ),

    # --- 2. UMP applies to workers < 1 year tenure ---
    Obligation(
        id="UPAH-02",
        description="UMP berlaku untuk pekerja dengan masa kerja kurang dari 1 tahun",
        legal_basis="PP/2021/36/Bab/IV/Pasal/25",
        legal_text_summary="Upah minimum berlaku bagi Pekerja/Buruh dengan masa kerja kurang dari 1 (satu) tahun pada Perusahaan yang bersangkutan.",
        applies_to=[DocType.PKWT, DocType.PKWTT, DocType.SLIP_GAJI],
        conditions=[
            Condition(
                field="tenure_months",
                operator=Operator.LT,
                value=12,
                description="Masa kerja < 12 bulan",
            ),
        ],
        evidence=[
            Evidence(
                field_path="salary_meets_ump",
                operator=Operator.EQ,
                value=True,
                description="Gaji >= UMP meskipun masa kerja < 1 tahun",
            ),
        ],
        severity=Severity.HIGH,
        consequence="Pekerja baru tetap berhak UMP — tidak boleh digaji di bawah UMP dengan alasan masa kerja pendek",
        effective_from="2021-02-02",
    ),

    # --- 3. Companies with >1yr workers must have wage structure ---
    Obligation(
        id="UPAH-03",
        description="Perusahaan wajib menyusun struktur dan skala upah",
        legal_basis="PP/2021/36/Bab/II/Pasal/4",
        legal_text_summary="Pengusaha wajib menyusun dan menerapkan Struktur dan Skala Upah di Perusahaan.",
        applies_to=[DocType.PERATURAN_PERUSAHAAN],
        evidence=[
            Evidence(
                field_path="has_wage_structure",
                operator=Operator.EQ,
                value=True,
                description="Struktur dan skala upah tercantum",
            ),
        ],
        severity=Severity.MEDIUM,
        consequence="Sanksi administratif (PP 36/2021 Pasal 13)",
        effective_from="2021-02-02",
        edge_cases=[
            EdgeCase(
                condition="Perusahaan baru (belum 1 tahun beroperasi)",
                behavior="Tetap wajib menyusun — tidak ada pengecualian berdasarkan usia perusahaan",
                legal_basis="PP/2021/36/Bab/II/Pasal/4 — no exception",
            ),
        ],
    ),

    # --- 4. Wage must be paid in Rupiah ---
    Obligation(
        id="UPAH-04",
        description="Upah wajib dibayar dalam mata uang Rupiah",
        legal_basis="PP/2021/36/Bab/VIII/Pasal/53",
        legal_text_summary="Upah wajib dibayarkan dalam mata uang rupiah Negara Republik Indonesia.",
        applies_to=[DocType.PKWT, DocType.PKWTT, DocType.SLIP_GAJI, DocType.PERATURAN_PERUSAHAAN],
        evidence=[
            Evidence(
                field_path="currency",
                operator=Operator.IN,
                value=["idr", "rupiah", None],
                description="Mata uang Rupiah (atau tidak disebut = default Rupiah)",
            ),
        ],
        severity=Severity.MEDIUM,
        consequence="Pembayaran dalam mata uang asing tidak sah kecuali ada perjanjian khusus",
        effective_from="2021-02-02",
        edge_cases=[
            EdgeCase(
                condition="TKA yang diperbantukan dari luar negeri (secondment)",
                behavior="Upah dapat dibayar dalam mata uang asing jika hubungan kerja dengan perusahaan luar negeri, bukan perusahaan Indonesia",
                legal_basis="PP/2021/34 (TKA) — hubungan kerja dengan entity luar negeri",
            ),
        ],
    ),

    # --- 5. Wage paid on time (max once per month) ---
    Obligation(
        id="UPAH-05",
        description="Upah dibayarkan paling lambat dalam jangka waktu yang diperjanjikan",
        legal_basis="PP/2021/36/Bab/VIII/Pasal/55",
        legal_text_summary="Pengusaha wajib membayar Upah pada waktu yang telah diperjanjikan antara Pengusaha dengan Pekerja/Buruh.",
        applies_to=[DocType.PKWT, DocType.PKWTT, DocType.PERATURAN_PERUSAHAAN],
        evidence=[
            Evidence(
                field_path="payment_schedule_stated",
                operator=Operator.EXISTS,
                description="Jadwal pembayaran upah tercantum",
            ),
        ],
        severity=Severity.MEDIUM,
        consequence="Denda keterlambatan (PP 36/2021 Pasal 56)",
        effective_from="2021-02-02",
    ),

    # --- 6. Late payment penalty ---
    Obligation(
        id="UPAH-06",
        description="Keterlambatan pembayaran upah dikenakan denda",
        legal_basis="PP/2021/36/Bab/VIII/Pasal/56",
        legal_text_summary="Pengusaha yang terlambat membayar Upah dikenai denda sesuai persentase tertentu dari Upah.",
        applies_to=[DocType.PERATURAN_PERUSAHAAN],
        evidence=[
            Evidence(
                field_path="late_penalty_clause",
                operator=Operator.EXISTS,
                description="Klausul denda keterlambatan upah tercantum",
            ),
        ],
        severity=Severity.LOW,
        consequence="Denda berlaku berdasarkan UU meskipun tidak tercantum dalam PP — ini reminder, bukan violation",
        effective_from="2021-02-02",
    ),

    # --- 7. Overtime must be paid ---
    Obligation(
        id="UPAH-07",
        description="Kerja lembur wajib dibayar upah lembur",
        legal_basis="PP/2021/36/Bab/VII/Pasal/39",
        legal_text_summary="Upah kerja lembur wajib dibayar oleh Pengusaha yang mempekerjakan Pekerja/Buruh melebihi waktu kerja.",
        applies_to=[DocType.PKWT, DocType.PKWTT, DocType.PERATURAN_PERUSAHAAN, DocType.SLIP_GAJI],
        evidence=[
            Evidence(
                field_path="overtime_paid",
                operator=Operator.EQ,
                value=True,
                description="Lembur dibayar / klausul lembur ada",
            ),
        ],
        severity=Severity.HIGH,
        consequence="Pekerja berhak atas upah lembur — tidak dapat diwaiver oleh perjanjian",
        effective_from="2021-02-02",
        edge_cases=[
            EdgeCase(
                condition="Perjanjian 'all-in salary' (gaji sudah termasuk lembur)",
                behavior="Tidak sah jika jam kerja melebihi batas. Lembur di atas 40 jam/minggu tetap wajib dibayar terpisah.",
                legal_basis="PP/2021/36/Bab/VII/Pasal/39 — hak normatif, tidak dapat dikurangi",
            ),
            EdgeCase(
                condition="Pekerja golongan jabatan tertentu (manajerial)",
                behavior="PP 35/2021 Pasal 25 Ayat 2: pekerja dengan tanggung jawab sebagai pemikir/perencana/pengendali jalannya perusahaan dapat dikecualikan dari lembur",
                legal_basis="PP/2021/35/Bab/IV/Pasal/25/Ayat/2",
            ),
        ],
    ),

    # --- 8. Overtime rate formula ---
    Obligation(
        id="UPAH-08",
        description="Upah lembur dihitung berdasarkan formula: 1/173 x upah sebulan",
        legal_basis="PP/2021/36/Bab/VII/Pasal/40",
        legal_text_summary="Upah kerja lembur per jam: 1/173 x Upah sebulan. Jam pertama: 1.5x, jam berikutnya: 2x.",
        applies_to=[DocType.SLIP_GAJI],
        conditions=[
            Condition(
                field="overtime_hours",
                operator=Operator.GT,
                value=0,
                description="Ada jam lembur",
            ),
        ],
        evidence=[
            Evidence(
                field_path="overtime_rate_correct",
                operator=Operator.EQ,
                value=True,
                description="Tarif lembur sesuai formula 1/173",
            ),
        ],
        severity=Severity.HIGH,
        consequence="Pekerja berhak selisih jika tarif lembur di bawah ketentuan",
        effective_from="2021-02-02",
    ),

    # --- 9. Wage deductions max 50% ---
    Obligation(
        id="UPAH-09",
        description="Total pemotongan upah maksimal 50% dari pembayaran",
        legal_basis="PP/2021/36/Bab/IX/Pasal/65",
        legal_text_summary="Jumlah keseluruhan pemotongan Upah paling banyak 50% dari setiap pembayaran Upah yang diterima Pekerja/Buruh.",
        applies_to=[DocType.SLIP_GAJI],
        evidence=[
            Evidence(
                field_path="deduction_pct_valid",
                operator=Operator.EQ,
                value=True,
                description="Total potongan <= 50% dari gaji",
            ),
        ],
        severity=Severity.HIGH,
        consequence="Pemotongan di atas 50% melanggar hak pekerja",
        effective_from="2021-02-02",
    ),

    # --- 10. THR (Religious Holiday Allowance) ---
    Obligation(
        id="UPAH-10",
        description="Pekerja berhak atas THR Keagamaan",
        legal_basis="PP/2021/36/Bab/VII/Pasal/52",
        legal_text_summary="Pengusaha wajib membayar THR Keagamaan kepada Pekerja/Buruh.",
        applies_to=[DocType.PKWT, DocType.PKWTT, DocType.PERATURAN_PERUSAHAAN],
        evidence=[
            Evidence(
                field_path="thr_clause_exists",
                operator=Operator.EXISTS,
                description="Klausul THR ada dalam dokumen",
            ),
        ],
        severity=Severity.HIGH,
        consequence="THR adalah hak normatif — wajib dibayar H-7 hari raya. Denda jika terlambat.",
        effective_from="2021-02-02",
        edge_cases=[
            EdgeCase(
                condition="Pekerja dengan masa kerja < 1 bulan",
                behavior="Tidak berhak THR. Masa kerja minimum 1 bulan untuk THR proporsional.",
                legal_basis="PP/2021/36/Bab/VII/Pasal/52 Ayat 2",
            ),
            EdgeCase(
                condition="Pekerja resign sebelum hari raya tapi sudah masa kerja >= 1 bulan",
                behavior="Tetap berhak THR proporsional",
                legal_basis="PP/2021/36/Bab/VII/Pasal/52",
            ),
        ],
    ),

    # --- 11. Wage paid during leave/illness ---
    Obligation(
        id="UPAH-11",
        description="Upah tetap dibayar saat pekerja sakit berkepanjangan",
        legal_basis="PP/2021/36/Bab/VII/Pasal/43",
        legal_text_summary="Pengusaha wajib membayar Upah kepada Pekerja/Buruh yang tidak masuk bekerja karena sakit: 4 bulan pertama 100%, 4 bulan kedua 75%, 4 bulan ketiga 50%, selanjutnya 25% sebelum PHK.",
        applies_to=[DocType.PERATURAN_PERUSAHAAN],
        evidence=[
            Evidence(
                field_path="sick_leave_pay_policy",
                operator=Operator.EXISTS,
                description="Kebijakan upah sakit berkepanjangan tercantum",
            ),
        ],
        severity=Severity.MEDIUM,
        consequence="Hak normatif pekerja — berlaku meskipun tidak tercantum dalam PP",
        effective_from="2021-02-02",
    ),

    # --- 12. Wage component transparency ---
    Obligation(
        id="UPAH-12",
        description="Upah terdiri dari gaji pokok dan tunjangan (pokok minimal 75%)",
        legal_basis="PP/2021/36/Bab/II/Pasal/7",
        legal_text_summary="Upah terdiri atas komponen: gaji pokok dan tunjangan tetap/tidak tetap. Gaji pokok paling sedikit 75% dari jumlah gaji pokok dan tunjangan tetap.",
        applies_to=[DocType.PKWT, DocType.PKWTT, DocType.SLIP_GAJI],
        evidence=[
            Evidence(
                field_path="base_salary_ratio_valid",
                operator=Operator.EQ,
                value=True,
                description="Gaji pokok >= 75% dari (pokok + tunjangan tetap)",
            ),
        ],
        severity=Severity.MEDIUM,
        consequence="Struktur upah tidak sesuai ketentuan",
        effective_from="2021-02-02",
        edge_cases=[
            EdgeCase(
                condition="Tunjangan tetap = 0 (hanya gaji pokok)",
                behavior="Otomatis compliant — 100% adalah gaji pokok",
                legal_basis="PP/2021/36/Bab/II/Pasal/7",
            ),
        ],
    ),
]


def get_upah_obligations() -> list[Obligation]:
    """Return all wage-related obligations."""
    return UPAH_OBLIGATIONS
