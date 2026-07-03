"""Tests for the structural parser."""

from src.parser import (
    detect_regulation_type,
    extract_dasar_hukum,
    parse_pasal_content,
    split_into_pasal_blocks,
)
from src.schema import NodeID, NodeType, RegulationType


def test_detect_regulation_type():
    assert detect_regulation_type("UNDANG-UNDANG NOMOR 6 TAHUN 2023") == RegulationType.UU
    assert detect_regulation_type("PERATURAN PEMERINTAH NOMOR 21 TAHUN 2024") == RegulationType.PP
    assert detect_regulation_type("PERATURAN PRESIDEN NOMOR 5 TAHUN 2023") == RegulationType.PERPRES
    assert detect_regulation_type("random text") is None


def test_extract_dasar_hukum():
    text = """
    1. Undang-Undang Nomor 12 Tahun 2011 tentang Pembentukan Peraturan Perundang-undangan;
    2. Peraturan Pemerintah Nomor 5 Tahun 2021 tentang Penyelenggaraan Perizinan Berusaha;
    """
    refs = extract_dasar_hukum(text)
    assert len(refs) == 2
    assert "Undang-Undang Nomor 12 Tahun 2011" in refs[0].raw_text
    assert "Peraturan Pemerintah Nomor 5 Tahun 2021" in refs[1].raw_text


def test_split_into_pasal_blocks():
    text = """
Pasal 1
Dalam Undang-Undang ini yang dimaksud dengan:
(1) Cipta Kerja adalah...

Pasal 2
Undang-Undang ini bertujuan untuk:
(1) menciptakan lapangan kerja
"""
    blocks = split_into_pasal_blocks(text)
    assert len(blocks) == 2
    assert blocks[0][0] == "1"
    assert blocks[1][0] == "2"
    assert "Cipta Kerja" in blocks[0][1]


def test_parse_pasal_content():
    base_id = NodeID(reg_type="UU", year=2023, number="6")
    text = "(1) Ayat pertama tentang sesuatu.\n(2) Ayat kedua tentang hal lain."

    node = parse_pasal_content("1", text, base_id)
    assert node.node_type == NodeType.PASAL
    assert node.number == "1"
    assert len(node.children) == 2
    assert node.children[0].node_type == NodeType.AYAT
    assert node.children[0].number == "1"
    assert str(node.id) == "UU/2023/6/Pasal/1"
    assert str(node.children[1].id) == "UU/2023/6/Pasal/1/Ayat/2"
