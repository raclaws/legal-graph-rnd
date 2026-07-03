"""Tests for the schema models."""

from src.schema import NodeID, RegulationType, Regulation


def test_node_id_str():
    nid = NodeID(reg_type="UU", year=2023, number="6", path=[("Pasal", "81"), ("Ayat", "1")])
    assert str(nid) == "UU/2023/6/Pasal/81/Ayat/1"


def test_node_id_parse():
    nid = NodeID.parse("PP/2024/21/Pasal/14/Ayat/2")
    assert nid.reg_type == "PP"
    assert nid.year == 2024
    assert nid.number == "21"
    assert nid.path == [("Pasal", "14"), ("Ayat", "2")]


def test_regulation_node_id():
    reg = Regulation(
        reg_type=RegulationType.UU,
        number="6",
        year=2023,
        title="Penetapan Perppu 2/2022 tentang Cipta Kerja menjadi UU",
    )
    assert str(reg.node_id) == "UU/2023/6"
