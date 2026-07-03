"""PKWT Obligations — derived from PP 35/2021 Bab II + Permenaker 18/2022.

Every obligation here traces to a specific Pasal in the graph.
Edge cases are stated explicitly, never hidden.

Source regulations (in graph):
- PP/2021/35/Bab/II (PKWT)
- Permen/2022/18 (Pelaksanaan PKWT)
- UU/2003/13/Bab/IX (Hubungan Kerja — base, partially amended)
"""

from ..compliance.obligations import (
    Condition,
    DocType,
    EdgeCase,
    Evidence,
    Obligation,
    Operator,
    Severity,
)


PKWT_OBLIGATIONS: list[Obligation] = [
    # --- 1. Contract must be written (not oral) ---
    Obligation(
        id="PKWT-01",
        description="PKWT wajib dibuat secara tertulis",
        legal_basis="PP/2021/35/Bab/II/Pasal/2/Ayat/1",
        legal_text_summary="Perjanjian kerja waktu tertentu dibuat secara tertulis serta harus menggunakan bahasa Indonesia dan huruf latin.",
        applies_to=[DocType.PKWT],
        evidence=[
            Evidence(
                field_path="is_written_document",
                operator=Operator.EQ,
                value=True,
                description="Dokumen tertulis",
            ),
        ],
        severity=Severity.CRITICAL,
        consequence="PKWT yang tidak tertulis demi hukum menjadi PKWTT (PP 35/2021 Pasal 2 Ayat 2)",
        effective_from="2021-02-02",
        edge_cases=[
            EdgeCase(
                condition="PKWT untuk pekerjaan tertentu yang bersifat sederhana/kecil dengan upah di bawah batas tertentu",
                behavior="Tetap wajib tertulis post-Cipta Kerja, tidak ada pengecualian",
                legal_basis="PP/2021/35/Bab/II/Pasal/2/Ayat/1 — no exception clause",
            ),
        ],
    ),

    # --- 2. Must use Bahasa Indonesia ---
    Obligation(
        id="PKWT-02",
        description="PKWT wajib menggunakan bahasa Indonesia dan huruf latin",
        legal_basis="PP/2021/35/Bab/II/Pasal/2/Ayat/1",
        legal_text_summary="...harus menggunakan bahasa Indonesia dan huruf latin.",
        applies_to=[DocType.PKWT],
        evidence=[
            Evidence(
                field_path="language",
                operator=Operator.IN,
                value=["indonesian", "bilingual"],
                description="Bahasa Indonesia (boleh bilingual)",
            ),
        ],
        severity=Severity.HIGH,
        consequence="Kontrak dalam bahasa asing saja tanpa versi Indonesia dapat disengketakan",
        effective_from="2021-02-02",
        edge_cases=[
            EdgeCase(
                condition="Kontrak bilingual (Indonesia + English) dengan klausul 'versi Indonesia yang berlaku'",
                behavior="Compliant — bilingual diperbolehkan selama versi Indonesia ada",
                legal_basis="PP/2021/35/Bab/II/Pasal/2/Ayat/1 + UU 24/2009 Pasal 31",
            ),
            EdgeCase(
                condition="TKA (tenaga kerja asing) dengan kontrak English-only",
                behavior="VIOLATED — tetap wajib ada versi Indonesia meskipun pekerja asing",
                legal_basis="PP/2021/35/Bab/II/Pasal/2/Ayat/1 — no TKA exception",
            ),
        ],
    ),

    # --- 3. Cannot have probation period ---
    Obligation(
        id="PKWT-03",
        description="PKWT tidak boleh mensyaratkan masa percobaan",
        legal_basis="PP/2021/35/Bab/II/Pasal/5/Ayat/1",
        legal_text_summary="PKWT tidak dapat mensyaratkan adanya masa percobaan kerja.",
        applies_to=[DocType.PKWT],
        evidence=[
            Evidence(
                field_path="has_probation",
                operator=Operator.EQ,
                value=False,
                description="Tidak ada masa percobaan",
            ),
        ],
        severity=Severity.HIGH,
        consequence="Klausul masa percobaan batal demi hukum, masa percobaan dihitung sebagai masa kerja (PP 35/2021 Pasal 5 Ayat 2)",
        effective_from="2021-02-02",
        edge_cases=[
            EdgeCase(
                condition="Dokumen menyebut 'masa orientasi' atau 'masa pengenalan' bukan 'masa percobaan'",
                behavior="Evaluasi substansi: jika ada konsekuensi PHK tanpa pesangon selama masa tersebut, secara substansi = masa percobaan → VIOLATED",
                legal_basis="PP/2021/35/Bab/II/Pasal/5 — substansi di atas label",
            ),
        ],
    ),

    # --- 4. Maximum duration 5 years (including extensions) ---
    Obligation(
        id="PKWT-04",
        description="Jangka waktu PKWT (termasuk perpanjangan) maksimal 5 tahun",
        legal_basis="PP/2021/35/Bab/II/Pasal/8",
        legal_text_summary="Jangka waktu atau selesainya suatu pekerjaan tertentu... paling lama 5 (lima) tahun.",
        applies_to=[DocType.PKWT],
        evidence=[
            Evidence(
                field_path="total_duration_months",
                operator=Operator.LTE,
                value=60,
                description="Total durasi <= 60 bulan (5 tahun)",
            ),
        ],
        severity=Severity.CRITICAL,
        consequence="PKWT yang melebihi 5 tahun demi hukum menjadi PKWTT (PP 35/2021 Pasal 8)",
        effective_from="2021-02-02",
        edge_cases=[
            EdgeCase(
                condition="PKWT berdasarkan selesainya pekerjaan tertentu (bukan waktu tertentu)",
                behavior="Tidak ada batas 5 tahun — batas adalah selesainya pekerjaan. Tapi jika pekerjaan melebihi waktu yang diperjanjikan, dapat diperpanjang sampai selesai (Pasal 7)",
                legal_basis="PP/2021/35/Bab/II/Pasal/7",
            ),
            EdgeCase(
                condition="PKWT sebelum Cipta Kerja (pre-2021) yang masih berjalan",
                behavior="Tunduk pada aturan lama (UU 13/2003): maks 2 tahun + 1 tahun perpanjangan + 2 tahun pembaruan",
                legal_basis="PP/2021/35/Pasal/66 (ketentuan peralihan)",
            ),
        ],
    ),

    # --- 5. Must state type of work ---
    Obligation(
        id="PKWT-05",
        description="PKWT wajib menyebutkan jenis pekerjaan",
        legal_basis="PP/2021/35/Bab/II/Pasal/3",
        legal_text_summary="PKWT hanya dapat dibuat untuk: (a) pekerjaan yang selesai dalam waktu tertentu; (b) pekerjaan yang bersifat musiman; (c) pekerjaan yang berhubungan dengan produk/kegiatan baru.",
        applies_to=[DocType.PKWT],
        evidence=[
            Evidence(
                field_path="work_type_stated",
                operator=Operator.EXISTS,
                description="Jenis pekerjaan disebutkan dalam kontrak",
            ),
        ],
        severity=Severity.HIGH,
        consequence="Tanpa jenis pekerjaan yang jelas, PKWT dapat disengketakan sebagai PKWTT",
        effective_from="2021-02-02",
        edge_cases=[
            EdgeCase(
                condition="Pekerjaan yang bersifat tetap (continuous/permanent nature)",
                behavior="Tidak boleh PKWT sama sekali — harus PKWTT. Jenis pekerjaan tetap = PKWT invalid.",
                legal_basis="PP/2021/35/Bab/II/Pasal/4",
            ),
        ],
    ),

    # --- 6. Must have definite end condition ---
    Obligation(
        id="PKWT-06",
        description="PKWT wajib mencantumkan waktu berakhirnya atau selesainya pekerjaan",
        legal_basis="PP/2021/35/Bab/II/Pasal/6",
        legal_text_summary="PKWT berdasarkan jangka waktu harus mencantumkan jangka waktu berakhirnya perjanjian kerja.",
        applies_to=[DocType.PKWT],
        evidence=[
            Evidence(
                field_path="end_date",
                operator=Operator.EXISTS,
                description="Tanggal berakhir kontrak ada",
            ),
        ],
        severity=Severity.HIGH,
        consequence="PKWT tanpa batas waktu yang jelas = tidak memenuhi syarat PKWT",
        effective_from="2021-02-02",
        edge_cases=[
            EdgeCase(
                condition="PKWT selesainya pekerjaan (bukan jangka waktu)",
                behavior="Tidak perlu end_date eksplisit — cukup 'selesainya pekerjaan X'. Tapi wajib ada perkiraan waktu selesai (Pasal 7 Ayat 2).",
                legal_basis="PP/2021/35/Bab/II/Pasal/7/Ayat/2",
            ),
        ],
    ),

    # --- 7. Salary must meet UMP ---
    Obligation(
        id="PKWT-07",
        description="Upah tidak boleh di bawah upah minimum (UMP/UMK)",
        legal_basis="PP/2021/36/Bab/IV/Pasal/23",
        legal_text_summary="Pengusaha dilarang membayar Upah lebih rendah dari Upah minimum.",
        applies_to=[DocType.PKWT, DocType.PKWTT, DocType.SLIP_GAJI],
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
                behavior="Dapat dikecualikan dari UMP berdasarkan Perpres (PP 36/2021 Pasal 36). Harus ada Perpres terbit.",
                legal_basis="PP/2021/36/Bab/IV/Pasal/36",
            ),
            EdgeCase(
                condition="Pekerja dengan masa kerja < 1 tahun",
                behavior="UMP tetap berlaku — Pasal 25 PP 36/2021 menyatakan UMP berlaku untuk pekerja masa kerja < 1 tahun",
                legal_basis="PP/2021/36/Bab/IV/Pasal/25",
            ),
            EdgeCase(
                condition="Gaji pokok < UMP tapi total take-home (dengan tunjangan tetap) ≥ UMP",
                behavior="Yang dibandingkan adalah upah (gaji pokok + tunjangan tetap), bukan gaji pokok saja",
                legal_basis="PP/2021/36/Bab/I/Pasal/7",
            ),
        ],
    ),

    # --- 8. Kompensasi at end of PKWT ---
    Obligation(
        id="PKWT-08",
        description="Pengusaha wajib memberikan uang kompensasi pada saat berakhirnya PKWT",
        legal_basis="PP/2021/35/Bab/II/Pasal/15",
        legal_text_summary="Pengusaha wajib memberikan uang kompensasi kepada Pekerja/Buruh pada saat berakhirnya PKWT.",
        applies_to=[DocType.PKWT],
        evidence=[
            Evidence(
                field_path="compensation_clause_exists",
                operator=Operator.EQ,
                value=True,
                description="Klausul kompensasi akhir kontrak ada",
            ),
        ],
        severity=Severity.HIGH,
        consequence="Wajib bayar meskipun tidak tercantum dalam kontrak — ini hak normatif pekerja",
        effective_from="2021-02-02",
        edge_cases=[
            EdgeCase(
                condition="PKWT untuk pekerjaan yang kurang dari 1 bulan",
                behavior="Tetap wajib kompensasi — dihitung proporsional (Pasal 16 Ayat 4)",
                legal_basis="PP/2021/35/Bab/II/Pasal/16/Ayat/4",
            ),
            EdgeCase(
                condition="Pekerja mengundurkan diri sebelum PKWT berakhir",
                behavior="Tidak berhak atas kompensasi (Pasal 17)",
                legal_basis="PP/2021/35/Bab/II/Pasal/17",
            ),
            EdgeCase(
                condition="TKA (tenaga kerja asing)",
                behavior="TKA tidak berhak atas kompensasi PKWT (Pasal 15 Ayat 2)",
                legal_basis="PP/2021/35/Bab/II/Pasal/15/Ayat/2",
            ),
        ],
    ),

    # --- 9. Must be registered at Disnaker ---
    Obligation(
        id="PKWT-09",
        description="PKWT wajib dicatatkan di instansi ketenagakerjaan",
        legal_basis="Permen/2022/18/Bab/II/Pasal/14",
        legal_text_summary="Pengusaha wajib mencatatkan PKWT secara daring pada instansi yang menyelenggarakan urusan pemerintahan di bidang ketenagakerjaan.",
        applies_to=[DocType.PKWT],
        evidence=[
            Evidence(
                field_path="registered_disnaker",
                operator=Operator.EQ,
                value=True,
                description="Tercatat di Disnaker (WLKP Online)",
            ),
        ],
        severity=Severity.MEDIUM,
        consequence="Sanksi administratif (teguran tertulis). Tidak membatalkan kontrak.",
        effective_from="2022-12-14",
        edge_cases=[
            EdgeCase(
                condition="Pencatatan dilakukan setelah pekerjaan dimulai (terlambat)",
                behavior="Selama dicatat dalam 3 hari kerja sejak penandatanganan, masih compliant (Pasal 14 Ayat 3)",
                legal_basis="Permen/2022/18/Bab/II/Pasal/14/Ayat/3",
            ),
        ],
    ),

    # --- 10. Working hours ---
    Obligation(
        id="PKWT-10",
        description="Waktu kerja tidak boleh melebihi ketentuan",
        legal_basis="PP/2021/35/Bab/IV/Pasal/21",
        legal_text_summary="Waktu Kerja meliputi: (a) 7 jam 1 hari dan 40 jam 1 minggu untuk 6 hari kerja; atau (b) 8 jam 1 hari dan 40 jam 1 minggu untuk 5 hari kerja.",
        applies_to=[DocType.PKWT, DocType.PKWTT, DocType.PERATURAN_PERUSAHAAN],
        evidence=[
            Evidence(
                field_path="weekly_hours",
                operator=Operator.LTE,
                value=40,
                description="Jam kerja <= 40 jam/minggu",
            ),
        ],
        severity=Severity.HIGH,
        consequence="Kelebihan jam kerja harus dihitung sebagai lembur dengan tarif lembur (PP 35/2021 Pasal 26-28)",
        effective_from="2021-02-02",
        edge_cases=[
            EdgeCase(
                condition="Sektor tertentu: migas, pertambangan, perkebunan, transportasi, perikanan",
                behavior="Dapat menerapkan waktu kerja khusus (PP 35/2021 Pasal 23) — shift/roster system diperbolehkan",
                legal_basis="PP/2021/35/Bab/IV/Pasal/23",
            ),
            EdgeCase(
                condition="Pekerjaan yang waktu kerjanya kurang dari 35 jam/minggu (part-time)",
                behavior="Diperbolehkan — hanya gaji yang proporsional. Tetap wajib BPJS.",
                legal_basis="PP/2021/35/Bab/IV/Pasal/21/Ayat/3",
            ),
        ],
    ),

    # --- 11. Leave entitlement ---
    Obligation(
        id="PKWT-11",
        description="Pekerja berhak atas cuti tahunan paling sedikit 12 hari kerja",
        legal_basis="UU/2003/13/Bab/X/Pasal/79/Ayat/3",
        legal_text_summary="Cuti tahunan sekurang-kurangnya 12 (dua belas) hari kerja setelah pekerja bekerja selama 12 (dua belas) bulan secara terus menerus.",
        applies_to=[DocType.PKWT, DocType.PKWTT, DocType.PERATURAN_PERUSAHAAN],
        evidence=[
            Evidence(
                field_path="annual_leave_days",
                operator=Operator.GTE,
                value=12,
                description="Cuti tahunan ≥ 12 hari",
            ),
        ],
        severity=Severity.MEDIUM,
        consequence="Hak normatif — pekerja dapat menuntut",
        effective_from="2003-03-25",
        edge_cases=[
            EdgeCase(
                condition="PKWT < 12 bulan",
                behavior="Hak cuti baru muncul setelah 12 bulan kerja terus-menerus. Untuk kontrak < 12 bulan, cuti proporsional atau per kebijakan perusahaan.",
                legal_basis="UU/2003/13/Bab/X/Pasal/79/Ayat/3 — 'setelah bekerja selama 12 bulan'",
            ),
        ],
    ),

    # --- 12. BPJS enrollment ---
    Obligation(
        id="PKWT-12",
        description="Pekerja PKWT wajib didaftarkan BPJS Ketenagakerjaan dan Kesehatan",
        legal_basis="PP/2021/35/Bab/II/Pasal/14",
        legal_text_summary="Pekerja/Buruh PKWT berhak atas... jaminan sosial.",
        applies_to=[DocType.PKWT, DocType.PKWTT],
        evidence=[
            Evidence(
                field_path="bpjs_mentioned",
                operator=Operator.EQ,
                value=True,
                description="BPJS disebut/diatur dalam kontrak",
            ),
        ],
        severity=Severity.HIGH,
        consequence="Sanksi administratif + pekerja berhak atas manfaat yang seharusnya diterima",
        effective_from="2015-07-01",
        edge_cases=[
            EdgeCase(
                condition="Pekerja sudah terdaftar BPJS dari pemberi kerja lain (rangkap)",
                behavior="Tetap wajib didaftarkan — iuran JKK/JKM oleh masing-masing pemberi kerja",
                legal_basis="Perpres/2020/64/Pasal/5",
            ),
        ],
    ),

    # --- 13. Must contain identity of parties ---
    Obligation(
        id="PKWT-13",
        description="PKWT wajib memuat identitas para pihak",
        legal_basis="UU/2003/13/Bab/IX/Pasal/54/Ayat/1",
        legal_text_summary="Perjanjian kerja dibuat secara tertulis sekurang-kurangnya memuat: (a) nama, alamat perusahaan, dan jenis usaha; (b) nama, jenis kelamin, umur, dan alamat pekerja...",
        applies_to=[DocType.PKWT, DocType.PKWTT],
        evidence=[
            Evidence(
                field_path="company_name",
                operator=Operator.EXISTS,
                description="Nama perusahaan tercantum",
            ),
            Evidence(
                field_path="employee_name",
                operator=Operator.EXISTS,
                description="Nama pekerja tercantum",
            ),
        ],
        severity=Severity.MEDIUM,
        consequence="Kontrak tidak memenuhi syarat minimum UU 13/2003 Pasal 54",
        effective_from="2003-03-25",
    ),

    # --- 14. Job description / position ---
    Obligation(
        id="PKWT-14",
        description="PKWT wajib memuat jabatan atau jenis pekerjaan",
        legal_basis="UU/2003/13/Bab/IX/Pasal/54/Ayat/1/huruf/c",
        legal_text_summary="...memuat: (c) jabatan atau jenis pekerjaan...",
        applies_to=[DocType.PKWT, DocType.PKWTT],
        evidence=[
            Evidence(
                field_path="position",
                operator=Operator.EXISTS,
                description="Jabatan/posisi tercantum",
            ),
        ],
        severity=Severity.MEDIUM,
        consequence="Kontrak tidak memenuhi syarat minimum UU 13/2003 Pasal 54",
        effective_from="2003-03-25",
    ),

    # --- 15. Salary amount stated ---
    Obligation(
        id="PKWT-15",
        description="PKWT wajib memuat besarnya upah dan cara pembayarannya",
        legal_basis="UU/2003/13/Bab/IX/Pasal/54/Ayat/1/huruf/e",
        legal_text_summary="...memuat: (e) besarnya upah dan cara pembayarannya...",
        applies_to=[DocType.PKWT, DocType.PKWTT],
        evidence=[
            Evidence(
                field_path="salary",
                operator=Operator.EXISTS,
                description="Nominal gaji tercantum",
            ),
        ],
        severity=Severity.HIGH,
        consequence="Tanpa besaran upah eksplisit, sulit dibuktikan jika ada sengketa",
        effective_from="2003-03-25",
    ),
]


def get_pkwt_obligations() -> list[Obligation]:
    """Return all PKWT obligations for evaluation."""
    return PKWT_OBLIGATIONS
