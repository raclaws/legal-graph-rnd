"""Severance calculator — POST /api/calculate/severance."""

from __future__ import annotations

from fastapi import APIRouter

from src.compliance import TerminationReason, calculate_severance

from ..schemas import SeveranceComponent, SeveranceRequest, SeveranceResponse

router = APIRouter()


@router.post("/calculate/severance", response_model=SeveranceResponse)
async def severance(req: SeveranceRequest):
    years = req.masa_kerja_bulan // 12
    salary = req.upah_pokok + req.tunjangan_tetap

    try:
        reason = TerminationReason(req.alasan_phk)
    except ValueError:
        reason = TerminationReason.EFFICIENCY_CLOSURE

    result = calculate_severance(years, salary, reason)

    return SeveranceResponse(
        pesangon=SeveranceComponent(
            amount=result.pesangon,
            formula=f"{result.pesangon_months} bulan x Rp {salary:,} x {result.pesangon_multiplier}x",
            multiplier=result.pesangon_multiplier,
        ),
        penghargaan=SeveranceComponent(
            amount=result.penghargaan,
            formula=f"{result.penghargaan_months} bulan x Rp {salary:,}",
        ),
        penggantian_hak=SeveranceComponent(
            amount=result.penggantian_hak,
            formula="15% x (pesangon + penghargaan)",
        ),
        total=result.total,
        legal_basis=[
            {"pasal": "PP/2021/35/Bab/V/Pasal/40", "description": "Formula pesangon"},
            {"pasal": "PP/2021/35/Bab/V/Pasal/36", "description": f"Alasan PHK: {req.alasan_phk}"},
        ],
    )
