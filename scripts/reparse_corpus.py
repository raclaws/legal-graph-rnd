"""Re-parse and re-ingest all regulations with the fixed parser.

The fix: leading text before first Ayat is now captured in both
the Pasal node (text property) and prepended to Ayat 1.

This script:
1. For each PDF in corpus/raw/
2. Re-parses with the fixed parser
3. Deletes existing provisions for that regulation
4. Re-ingests the new parse

Norms (Norm, NormEvidence, NormEdgeCase) are untouched — they link by node_id.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pymupdf
from src.parser import parse_regulation
from src.schema import RegulationType
from src.graph import LegalGraph


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

CORPUS_DIR = Path(__file__).parent.parent / "corpus" / "raw"


def extract_pdf_text(pdf_path: Path) -> str:
    doc = pymupdf.open(str(pdf_path))
    text = ""
    for page in doc:
        text += page.get_text() + "\n"
    return text


def reparse_and_ingest():
    g = LegalGraph()
    total_provisions = 0

    for filename, reg_type, number, year, title in CORPUS:
        pdf_path = CORPUS_DIR / filename
        if not pdf_path.exists():
            print(f"SKIP: {filename} not found")
            continue

        print(f"Parsing {filename}...", end=" ", flush=True)

        text = extract_pdf_text(pdf_path)
        reg = parse_regulation(text, reg_type, number, year, title)

        # Count provisions
        def count_nodes(node):
            c = 1
            for child in node.children:
                c += count_nodes(child)
            return c

        provision_count = sum(count_nodes(n) for n in reg.batang_tubuh)
        print(f"{provision_count} provisions", end=" ", flush=True)

        # Delete existing provisions for this regulation
        reg_prefix = f"{reg_type.value}/{year}/{number}"
        with g.driver.session() as session:
            session.run(
                "MATCH (p:Provision) WHERE p.node_id STARTS WITH $prefix DETACH DELETE p",
                prefix=reg_prefix,
            )

        # Re-ingest
        g.ingest_regulation(reg)
        total_provisions += provision_count
        print("-> ingested")

    # Final stats
    with g.driver.session() as session:
        r = session.run("MATCH (p:Provision) RETURN count(p) AS c")
        print(f"\nTotal provisions in graph: {r.single()['c']}")
        r = session.run("MATCH (p:Provision) WHERE p.text IS NOT NULL AND p.text <> '' RETURN count(p) AS c")
        print(f"Provisions with text: {r.single()['c']}")
        r = session.run("MATCH (:Provision)-[:IMPOSES]->(:Norm) RETURN count(*) AS c")
        print(f"IMPOSES edges (should be unchanged): {r.single()['c']}")

    g.close()
    print(f"\nDone. Re-parsed {len(CORPUS)} regulations, {total_provisions} provisions total.")


if __name__ == "__main__":
    reparse_and_ingest()
