"""Seed SQLite database from corpus PDFs + compiled data.

Usage: python -m scripts.seed_sqlite [--force]

Reads:
  - corpus/raw/*.pdf → regulations + provisions
  - corpus/validation/compiled_PP_2021_35.json → norms
  - corpus/putusan/targeted_results.json → putusan + citations
  - src/compliance/domains/*.yaml → provision_edges (legal_basis refs)

Writes:
  - data/legal.db
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pymupdf
from src.parser import parse_regulation
from src.schema import Node, Regulation, RegulationType

PROJECT_ROOT = Path(__file__).parent.parent
CORPUS_DIR = PROJECT_ROOT / "corpus" / "raw"
DB_PATH = PROJECT_ROOT / "data" / "legal.db"
SCHEMA_PATH = PROJECT_ROOT / "backend" / "db" / "schema.sql"

CORPUS = [
    ("pp_35_2021.pdf", RegulationType.PP, "35", 2021, "PKWT, Alih Daya, Waktu Kerja, PHK"),
    ("pp_36_2021.pdf", RegulationType.PP, "36", 2021, "Pengupahan"),
    ("pp_37_2021.pdf", RegulationType.PP, "37", 2021, "Jaminan Kehilangan Pekerjaan"),
    ("pp_34_2021.pdf", RegulationType.PP, "34", 2021, "Penggunaan Tenaga Kerja Asing"),
    ("pp_51_2023.pdf", RegulationType.PP, "51", 2023, "Perubahan PP 36/2021 (UMP/UMK)"),
    ("pp_21_2024.pdf", RegulationType.PP, "21", 2024, "Perubahan PP 25/2020 (Tapera)"),
    ("pp_44_2015.pdf", RegulationType.PP, "44", 2015, "JKK + JKM"),
    ("pp_45_2015.pdf", RegulationType.PP, "45", 2015, "Jaminan Pensiun"),
    ("pp_46_2015.pdf", RegulationType.PP, "46", 2015, "Jaminan Hari Tua"),
    ("uu_13_2003.pdf", RegulationType.UU, "13", 2003, "Ketenagakerjaan"),
    ("uu_2_2004.pdf", RegulationType.UU, "2", 2004, "Penyelesaian Perselisihan Hubungan Industrial"),
    ("uu_6_2023.pdf", RegulationType.UU, "6", 2023, "Penetapan Perppu 2/2022 menjadi UU"),
    ("permenaker_18_2022.pdf", RegulationType.PERMEN, "18", 2022, "Pelaksanaan PKWT"),
    ("permenaker_6_2023.pdf", RegulationType.PERMEN, "6", 2023, "BPJS Ketenagakerjaan"),
    ("perpres_64_2020.pdf", RegulationType.PERPRES, "64", 2020, "BPJS Kesehatan"),
    ("perpres_19_2024.pdf", RegulationType.PERPRES, "19", 2024, "Perubahan Perpres 64/2020"),
]


def extract_pdf_text(pdf_path: Path) -> str:
    doc = pymupdf.open(str(pdf_path))
    text = ""
    for page in doc:
        text += page.get_text() + "\n"
    return text


def insert_regulation(db: sqlite3.Connection, reg: Regulation):
    reg_node_id = str(reg.node_id)
    db.execute(
        "INSERT OR REPLACE INTO regulations (node_id, reg_type, number, year, title) VALUES (?, ?, ?, ?, ?)",
        (reg_node_id, reg.reg_type.value, reg.number, reg.year, reg.title),
    )

    def insert_node(node: Node, parent_id: str | None):
        node_id = str(node.id)
        db.execute(
            "INSERT OR REPLACE INTO provisions (node_id, regulation_id, parent_id, type, number, title, text) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (node_id, reg_node_id, parent_id, node.node_type.value, node.number, node.title, node.text),
        )
        for child in node.children:
            insert_node(child, node_id)

    for node in reg.batang_tubuh:
        insert_node(node, reg_node_id)

    # Insert dasar_hukum references as edges
    for ref in reg.pembukaan.dasar_hukum:
        if ref.resolved_id:
            db.execute(
                "INSERT OR IGNORE INTO provision_edges (source_id, target_id, edge_type) VALUES (?, ?, ?)",
                (reg_node_id, str(ref.resolved_id), "REFERENCES"),
            )


def seed_regulations(db: sqlite3.Connection):
    print("=== Seeding regulations from PDFs ===")
    total = 0
    for filename, reg_type, number, year, title in CORPUS:
        pdf_path = CORPUS_DIR / filename
        if not pdf_path.exists():
            print(f"  SKIP: {filename} not found")
            continue

        print(f"  {filename}...", end=" ", flush=True)
        text = extract_pdf_text(pdf_path)
        reg = parse_regulation(text, reg_type, number, year, title)

        def count_nodes(node: Node) -> int:
            return 1 + sum(count_nodes(c) for c in node.children)

        count = sum(count_nodes(n) for n in reg.batang_tubuh)
        insert_regulation(db, reg)
        total += count
        print(f"{count} provisions")

    db.commit()
    print(f"  Total: {total} provisions\n")


def seed_norms(db: sqlite3.Connection):
    print("=== Seeding compiled norms ===")
    compiled_path = PROJECT_ROOT / "corpus" / "validation" / "compiled_PP_2021_35.json"
    if not compiled_path.exists():
        print("  SKIP: compiled_PP_2021_35.json not found\n")
        return

    data = json.loads(compiled_path.read_text(encoding="utf-8"))
    count = 0
    for norm in data.get("norms", []):
        ext = norm.get("current_extraction", {})
        db.execute(
            "INSERT OR REPLACE INTO norms (id, provision_id, description, subjects, severity, consequence, obligation_markers, quantities) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                norm["node_id"],
                norm["node_id"],
                ext.get("description", ""),
                json.dumps(ext.get("subjects", [])),
                ext.get("severity", "medium"),
                ext.get("consequence", ""),
                json.dumps(ext.get("obligation_markers", [])),
                json.dumps(ext.get("quantities", [])),
            ),
        )
        count += 1

    db.commit()
    print(f"  Inserted {count} norms\n")


def seed_putusan(db: sqlite3.Connection):
    print("=== Seeding court decisions ===")
    targeted_path = PROJECT_ROOT / "corpus" / "putusan" / "targeted_results.json"
    if not targeted_path.exists():
        print("  SKIP: targeted_results.json not found\n")
        return

    data = json.loads(targeted_path.read_text(encoding="utf-8"))
    count = 0
    for case in data:
        case_number = case.get("case_number", "")
        if not case_number:
            continue

        db.execute(
            "INSERT OR IGNORE INTO putusan (case_number, court, court_type, year, province, dispute_type, outcome, facts_summary, pdf_file) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                case_number,
                case.get("court", ""),
                case.get("court_type"),
                case.get("year", 0),
                case.get("province"),
                case.get("dispute_type"),
                case.get("outcome"),
                case.get("facts_summary"),
                case.get("file"),
            ),
        )

        putusan_id = db.execute(
            "SELECT id FROM putusan WHERE case_number = ?", (case_number,)
        ).fetchone()
        if putusan_id:
            for cit in case.get("provisions_cited", []):
                db.execute(
                    "INSERT OR IGNORE INTO putusan_citations (putusan_id, raw_citation, pasal, provision_id) "
                    "VALUES (?, ?, ?, ?)",
                    (putusan_id[0], cit.get("raw", ""), cit.get("pasal"), None),
                )
        count += 1

    db.commit()
    print(f"  Inserted {count} decisions\n")


def build_fts(db: sqlite3.Connection):
    print("=== Building FTS index ===")
    db.execute("DROP TABLE IF EXISTS provisions_fts")
    db.execute("CREATE VIRTUAL TABLE provisions_fts USING fts5(node_id, text)")
    db.execute(
        "INSERT INTO provisions_fts(node_id, text) "
        "SELECT node_id, text FROM provisions WHERE text IS NOT NULL AND text != ''"
    )
    db.commit()
    fts_count = db.execute("SELECT count(*) FROM provisions_fts").fetchone()[0]
    print(f"  Indexed {fts_count} provisions\n")


def main():
    force = "--force" in sys.argv

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    if DB_PATH.exists():
        if force:
            DB_PATH.unlink()
            print(f"Removed existing {DB_PATH}")
        else:
            print(f"Database already exists: {DB_PATH}")
            print("Use --force to recreate from scratch")
            return

    db = sqlite3.connect(str(DB_PATH))
    db.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    print(f"Created {DB_PATH}\n")

    seed_regulations(db)
    seed_norms(db)
    seed_putusan(db)
    build_fts(db)

    # Summary
    provisions = db.execute("SELECT count(*) FROM provisions").fetchone()[0]
    regulations = db.execute("SELECT count(*) FROM regulations").fetchone()[0]
    norms = db.execute("SELECT count(*) FROM norms").fetchone()[0]
    putusan = db.execute("SELECT count(*) FROM putusan").fetchone()[0]
    edges = db.execute("SELECT count(*) FROM provision_edges").fetchone()[0]

    print("=== Summary ===")
    print(f"  Regulations: {regulations}")
    print(f"  Provisions:  {provisions}")
    print(f"  Norms:       {norms}")
    print(f"  Putusan:     {putusan}")
    print(f"  Edges:       {edges}")
    print(f"\nDatabase: {DB_PATH} ({DB_PATH.stat().st_size / 1024:.0f} KB)")

    db.close()


if __name__ == "__main__":
    main()
