"""Tests for the severance calculator."""

from src.compliance import (
    TerminationReason,
    calculate_severance,
    get_penghargaan_months,
    get_pesangon_months,
)


def test_pesangon_table():
    assert get_pesangon_months(0) == 1
    assert get_pesangon_months(1) == 2
    assert get_pesangon_months(5) == 6
    assert get_pesangon_months(8) == 9
    assert get_pesangon_months(15) == 9  # capped at 9


def test_penghargaan_table():
    assert get_penghargaan_months(0) == 0
    assert get_penghargaan_months(2) == 0
    assert get_penghargaan_months(3) == 2
    assert get_penghargaan_months(7) == 3
    assert get_penghargaan_months(24) == 10
    assert get_penghargaan_months(30) == 10  # capped at 10


def test_efficiency_closure_5_years():
    """5 years, Rp 10M, efficiency closure — the canonical test case."""
    r = calculate_severance(5, 10_000_000, TerminationReason.EFFICIENCY_CLOSURE)
    assert r.pesangon_months == 6
    assert r.pesangon == 60_000_000
    assert r.penghargaan_months == 2
    assert r.penghargaan == 20_000_000
    assert r.penggantian_hak == 12_000_000
    assert r.total == 92_000_000


def test_resignation_no_pesangon():
    """Resignation gets 0 pesangon but still gets penghargaan."""
    r = calculate_severance(7, 15_000_000, TerminationReason.RESIGNATION)
    assert r.pesangon == 0
    assert r.penghargaan == 45_000_000
    assert r.total == 51_750_000


def test_disability_2x_pesangon():
    """Disability/prolonged illness gets 2x pesangon."""
    r = calculate_severance(10, 12_000_000, TerminationReason.DISABILITY)
    assert r.pesangon == 216_000_000  # 9 months * 12M * 2x
    assert r.penghargaan == 48_000_000  # 4 months * 12M


def test_legal_basis_includes_reason():
    """Legal basis should include the reason-specific Pasal."""
    r = calculate_severance(3, 5_000_000, TerminationReason.MERGER)
    assert any("Pasal/41" in b for b in r.legal_basis)
