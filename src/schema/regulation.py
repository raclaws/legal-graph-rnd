"""Core data models for Indonesian legal documents (Lampiran II UU 12/2011)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class RegulationType(Enum):
    UU = "UU"
    PERPPU = "Perppu"
    PP = "PP"
    PERPRES = "Perpres"
    PERMEN = "Permen"
    PERDA_PROVINSI = "Perda-Provinsi"
    PERDA_KABKOTA = "Perda-KabKota"


class NodeType(Enum):
    BAB = "Bab"
    BAGIAN = "Bagian"
    PARAGRAF = "Paragraf"
    PASAL = "Pasal"
    AYAT = "Ayat"
    HURUF = "Huruf"
    ANGKA = "Angka"


@dataclass
class NodeID:
    """Globally unique reference for any provision.

    Format: {type}/{year}/{number}/...path
    Example: UU/2023/6/Pasal/81/Ayat/1/Huruf/a
    """

    reg_type: str
    year: int
    number: str
    path: list[tuple[str, str]] = field(default_factory=list)

    def __str__(self) -> str:
        base = f"{self.reg_type}/{self.year}/{self.number}"
        if self.path:
            segments = "/".join(f"{kind}/{val}" for kind, val in self.path)
            return f"{base}/{segments}"
        return base

    @classmethod
    def parse(cls, ref: str) -> NodeID:
        parts = ref.split("/")
        reg_type = parts[0]
        year = int(parts[1])
        number = parts[2]
        path = []
        for i in range(3, len(parts) - 1, 2):
            path.append((parts[i], parts[i + 1]))
        return cls(reg_type=reg_type, year=year, number=number, path=path)


@dataclass
class Reference:
    raw_text: str
    resolved_id: Optional[NodeID] = None


@dataclass
class Node:
    id: NodeID
    node_type: NodeType
    number: str
    title: Optional[str] = None
    text: Optional[str] = None
    children: list[Node] = field(default_factory=list)


@dataclass
class Pembukaan:
    konsiderans: list[str] = field(default_factory=list)
    dasar_hukum: list[Reference] = field(default_factory=list)


@dataclass
class Penutup:
    tanggal: Optional[date] = None
    tempat: Optional[str] = None
    penandatangan: Optional[str] = None


@dataclass
class Regulation:
    reg_type: RegulationType
    number: str
    year: int
    title: str
    pembukaan: Pembukaan = field(default_factory=Pembukaan)
    batang_tubuh: list[Node] = field(default_factory=list)
    penutup: Penutup = field(default_factory=Penutup)
    penjelasan_umum: Optional[str] = None
    penjelasan_pasal: dict[str, str] = field(default_factory=dict)

    @property
    def node_id(self) -> NodeID:
        return NodeID(reg_type=self.reg_type.value, year=self.year, number=self.number)
