"""Severance calculator based on PP 35/2021 Pasal 40-59.

Encodes the post-Cipta Kerja severance formula (PMTK).
Every calculation returns the legal basis (Pasal reference) alongside the amount.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TerminationReason(Enum):
    EFFICIENCY_CLOSURE = "efisiensi_tutup"
    EFFICIENCY_LOSS = "efisiensi_rugi"
    MERGER = "penggabungan"
    ACQUISITION_UNWILLING = "pengambilalihan_tidak_bersedia"
    ACQUISITION_WILLING = "pengambilalihan_bersedia"
    BANKRUPTCY = "pailit"
    EMPLOYER_VIOLATION = "pelanggaran_pengusaha"
    WORKER_VIOLATION = "pelanggaran_pekerja"
    RESIGNATION = "pengunduran_diri"
    ABSENT_5_DAYS = "mangkir_5_hari"
    CRIMINAL_DETENTION = "penahanan"
    DISABILITY = "cacat_sakit_berkepanjangan"
    RETIREMENT = "pensiun"
    DEATH = "meninggal"
    FORCE_MAJEURE = "force_majeure"


# PP 35/2021 Pasal 40 Ayat (2) — Uang Pesangon table
# masa_kerja (years) → months of salary
PESANGON_TABLE = {
    0: 1,   # < 1 year
    1: 2,   # 1 - < 2 years
    2: 3,   # 2 - < 3 years
    3: 4,   # 3 - < 4 years
    4: 5,   # 4 - < 5 years
    5: 6,   # 5 - < 6 years
    6: 7,   # 6 - < 7 years
    7: 8,   # 7 - < 8 years
    8: 9,   # 8+ years (max)
}

# PP 35/2021 Pasal 40 Ayat (3) — Uang Penghargaan Masa Kerja table
PENGHARGAAN_TABLE = {
    3: 2,    # 3 - < 6 years
    6: 3,    # 6 - < 9 years
    9: 4,    # 9 - < 12 years
    12: 5,   # 12 - < 15 years
    15: 6,   # 15 - < 18 years
    18: 7,   # 18 - < 21 years
    21: 8,   # 21 - < 24 years
    24: 10,  # 24+ years (max)
}

# PP 35/2021 Pasal 40 Ayat (4) — Uang Penggantian Hak
# 15% of (pesangon + penghargaan) for housing/medical allowance
PENGGANTIAN_HAK_PCT = 0.15

# Multiplier per termination reason
# Format: (pesangon_multiplier, penghargaan_multiplier, penggantian_hak)
# Source: PP 35/2021 Pasal 41-59
REASON_MULTIPLIERS: dict[TerminationReason, tuple[float, float, bool]] = {
    TerminationReason.MERGER: (1.0, 1.0, True),                        # Pasal 41
    TerminationReason.ACQUISITION_UNWILLING: (1.0, 1.0, True),         # Pasal 42(1)
    TerminationReason.ACQUISITION_WILLING: (0.5, 1.0, True),           # Pasal 42(2)
    TerminationReason.EFFICIENCY_CLOSURE: (1.0, 1.0, True),            # Pasal 43(1) — not bankrupt
    TerminationReason.EFFICIENCY_LOSS: (0.5, 1.0, True),               # Pasal 43(2) — 2 years loss
    TerminationReason.FORCE_MAJEURE: (0.5, 1.0, True),                 # Pasal 44(1)
    TerminationReason.BANKRUPTCY: (0.5, 1.0, True),                    # Pasal 44(2)
    TerminationReason.EMPLOYER_VIOLATION: (1.0, 1.0, True),            # Pasal 45
    TerminationReason.WORKER_VIOLATION: (0.5, 1.0, True),              # Pasal 52
    TerminationReason.RESIGNATION: (0.0, 1.0, True),                   # Pasal 50 — no pesangon
    TerminationReason.ABSENT_5_DAYS: (0.0, 1.0, True),                 # Pasal 51
    TerminationReason.CRIMINAL_DETENTION: (0.0, 1.0, True),            # Pasal 54
    TerminationReason.DISABILITY: (2.0, 1.0, True),                    # Pasal 55 — 2x pesangon
    TerminationReason.RETIREMENT: (1.75, 1.0, True),                   # Pasal 56 — 1.75x
    TerminationReason.DEATH: (2.0, 1.0, True),                         # Pasal 57 — 2x pesangon
}


def get_pesangon_months(years_of_service: int) -> int:
    """Look up pesangon months from the table (PP 35/2021 Pasal 40 Ayat 2)."""
    key = min(years_of_service, 8)
    return PESANGON_TABLE[key]


def get_penghargaan_months(years_of_service: int) -> int:
    """Look up penghargaan months from the table (PP 35/2021 Pasal 40 Ayat 3)."""
    if years_of_service < 3:
        return 0
    thresholds = sorted(PENGHARGAAN_TABLE.keys(), reverse=True)
    for t in thresholds:
        if years_of_service >= t:
            return PENGHARGAAN_TABLE[t]
    return 0


@dataclass
class SeveranceResult:
    pesangon: int
    pesangon_months: int
    pesangon_multiplier: float
    penghargaan: int
    penghargaan_months: int
    penggantian_hak: int
    total: int
    years_of_service: int
    monthly_salary: int
    reason: TerminationReason
    legal_basis: list[str]


def calculate_severance(
    years_of_service: int,
    monthly_salary: int,
    reason: TerminationReason,
) -> SeveranceResult:
    """Calculate severance per PP 35/2021 Pasal 40-59.

    Returns breakdown with legal citations.
    """
    multipliers = REASON_MULTIPLIERS.get(reason, (1.0, 1.0, True))
    pesangon_mult, penghargaan_mult, include_penggantian = multipliers

    # Uang Pesangon
    pesangon_months = get_pesangon_months(years_of_service)
    pesangon = int(pesangon_months * monthly_salary * pesangon_mult)

    # Uang Penghargaan Masa Kerja
    penghargaan_months = get_penghargaan_months(years_of_service)
    penghargaan = int(penghargaan_months * monthly_salary * penghargaan_mult)

    # Uang Penggantian Hak (15% of pesangon + penghargaan)
    penggantian_hak = int((pesangon + penghargaan) * PENGGANTIAN_HAK_PCT) if include_penggantian else 0

    total = pesangon + penghargaan + penggantian_hak

    # Build legal basis citations
    legal_basis = [
        "PP/2021/35/Bab/V/Pasal/40/Ayat/1 (kewajiban pembayaran)",
        "PP/2021/35/Bab/V/Pasal/40/Ayat/2 (tabel uang pesangon)",
        "PP/2021/35/Bab/V/Pasal/40/Ayat/3 (tabel uang penghargaan masa kerja)",
        "PP/2021/35/Bab/V/Pasal/40/Ayat/4 (uang penggantian hak)",
    ]

    # Add reason-specific pasal
    reason_pasal = {
        TerminationReason.MERGER: "PP/2021/35/Bab/V/Pasal/41",
        TerminationReason.ACQUISITION_UNWILLING: "PP/2021/35/Bab/V/Pasal/42/Ayat/1",
        TerminationReason.ACQUISITION_WILLING: "PP/2021/35/Bab/V/Pasal/42/Ayat/2",
        TerminationReason.EFFICIENCY_CLOSURE: "PP/2021/35/Bab/V/Pasal/43/Ayat/1",
        TerminationReason.EFFICIENCY_LOSS: "PP/2021/35/Bab/V/Pasal/43/Ayat/2",
        TerminationReason.FORCE_MAJEURE: "PP/2021/35/Bab/V/Pasal/44/Ayat/1",
        TerminationReason.BANKRUPTCY: "PP/2021/35/Bab/V/Pasal/44/Ayat/2",
        TerminationReason.EMPLOYER_VIOLATION: "PP/2021/35/Bab/V/Pasal/45",
        TerminationReason.RESIGNATION: "PP/2021/35/Bab/V/Pasal/50",
        TerminationReason.ABSENT_5_DAYS: "PP/2021/35/Bab/V/Pasal/51",
        TerminationReason.WORKER_VIOLATION: "PP/2021/35/Bab/V/Pasal/52",
        TerminationReason.CRIMINAL_DETENTION: "PP/2021/35/Bab/V/Pasal/54",
        TerminationReason.DISABILITY: "PP/2021/35/Bab/V/Pasal/55",
        TerminationReason.RETIREMENT: "PP/2021/35/Bab/V/Pasal/56",
        TerminationReason.DEATH: "PP/2021/35/Bab/V/Pasal/57",
    }
    if reason in reason_pasal:
        legal_basis.append(f"{reason_pasal[reason]} (alasan PHK: {reason.value})")

    return SeveranceResult(
        pesangon=pesangon,
        pesangon_months=pesangon_months,
        pesangon_multiplier=pesangon_mult,
        penghargaan=penghargaan,
        penghargaan_months=penghargaan_months,
        penggantian_hak=penggantian_hak,
        total=total,
        years_of_service=years_of_service,
        monthly_salary=monthly_salary,
        reason=reason,
        legal_basis=legal_basis,
    )


def format_result(r: SeveranceResult) -> str:
    """Format severance result as readable output."""
    lines = [
        f"=== Perhitungan Pesangon (PP 35/2021) ===",
        f"",
        f"Masa kerja: {r.years_of_service} tahun",
        f"Upah bulanan: Rp {r.monthly_salary:,.0f}",
        f"Alasan PHK: {r.reason.value}",
        f"",
        f"--- Rincian ---",
        f"Uang Pesangon: {r.pesangon_months} bulan × Rp {r.monthly_salary:,.0f} × {r.pesangon_multiplier}x = Rp {r.pesangon:,.0f}",
        f"Uang Penghargaan Masa Kerja: {r.penghargaan_months} bulan × Rp {r.monthly_salary:,.0f} = Rp {r.penghargaan:,.0f}",
        f"Uang Penggantian Hak (15%): Rp {r.penggantian_hak:,.0f}",
        f"",
        f"TOTAL: Rp {r.total:,.0f}",
        f"",
        f"--- Dasar Hukum ---",
    ]
    for basis in r.legal_basis:
        lines.append(f"  • {basis}")
    return "\n".join(lines)
