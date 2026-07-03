"""Structural parser for Indonesian legal documents.

Parses HTML/text from peraturan.go.id into a Regulation tree
following the structure defined in Lampiran II UU 12/2011.
"""

from __future__ import annotations

import re
from typing import Optional

from src.schema import (
    Node,
    NodeID,
    NodeType,
    Pembukaan,
    Penutup,
    Reference,
    Regulation,
    RegulationType,
)

# --- Regex patterns for structural elements ---

RE_BAB = re.compile(r"^BAB\s+([IVXLCDM]+)\s*$", re.MULTILINE)
RE_BAB_TITLE = re.compile(r"^BAB\s+[IVXLCDM]+\s*\n(.+)$", re.MULTILINE)
RE_BAGIAN = re.compile(r"^Bagian\s+(Kesatu|Kedua|Ketiga|Keempat|Kelima|Keenam|Ketujuh|Kedelapan|Kesembilan|Kesepuluh|\w+)\s*$", re.MULTILINE)
RE_PARAGRAF = re.compile(r"^Paragraf\s+(\d+)\s*$", re.MULTILINE)
RE_PASAL = re.compile(r"^\s*Pasal\s+(\d+[A-Z]?)\s*$", re.MULTILINE)
RE_AYAT = re.compile(r"^\((\d+)\)\s+([A-Z].*)", re.MULTILINE)
RE_HURUF = re.compile(r"^([a-z])\.\s+(.*)$", re.MULTILINE)
RE_ANGKA = re.compile(r"^(\d+)\.\s+(.*)$", re.MULTILINE)

RE_MENIMBANG = re.compile(r"Menimbang\s*:?", re.IGNORECASE)
RE_MENGINGAT = re.compile(r"Mengingat\s*:?", re.IGNORECASE)

RE_REG_REFERENCE = re.compile(
    r"(Undang-Undang|Peraturan Pemerintah|Peraturan Presiden|Peraturan Menteri"
    r"|Perppu|UU|PP|Perpres|Permen)"
    r"\s+(?:Nomor\s+)?(\d+)\s+Tahun\s+(\d{4})"
)


def normalize_ocr_text(text: str) -> str:
    """Fix common OCR artifacts in Indonesian legal PDFs."""
    # Fix digit/letter confusion in years: 2O2O -> 2020, 2OL6 -> 2016
    def fix_year(m):
        raw = m.group(1)
        fixed = raw.replace("O", "0").replace("l", "1").replace("L", "1")
        return f"Tahun {fixed}"

    text = re.sub(r"Tahun\s+([0-9OolL]{4})", fix_year, text)

    # Fix common OCR swaps
    text = text.replace("lndonesia", "Indonesia")
    text = text.replace("kmbaran", "Lembaran")
    text = text.replace("hunrf", "huruf")
    return text


def detect_regulation_type(text: str) -> Optional[RegulationType]:
    """Detect regulation type from title/header text."""
    text_upper = text.upper()
    if "UNDANG-UNDANG" in text_upper and "PERPU" not in text_upper:
        return RegulationType.UU
    if "PERPU" in text_upper or "PERPPU" in text_upper:
        return RegulationType.PERPPU
    if "PERATURAN PEMERINTAH" in text_upper:
        return RegulationType.PP
    if "PERATURAN PRESIDEN" in text_upper:
        return RegulationType.PERPRES
    if "PERATURAN MENTERI" in text_upper:
        return RegulationType.PERMEN
    if "PERATURAN DAERAH" in text_upper:
        if "PROVINSI" in text_upper:
            return RegulationType.PERDA_PROVINSI
        return RegulationType.PERDA_KABKOTA
    return None


def extract_dasar_hukum(text: str) -> list[Reference]:
    """Extract legal basis references from the 'Mengingat' section."""
    refs = []
    seen = set()
    for match in RE_REG_REFERENCE.finditer(text):
        raw = match.group(0)
        reg_type_str = match.group(1)
        number = match.group(2)
        year = match.group(3)

        # Map to canonical type
        type_map = {
            "Undang-Undang": "UU",
            "Peraturan Pemerintah": "PP",
            "Peraturan Presiden": "Perpres",
            "Peraturan Menteri": "Permen",
            "Perppu": "Perppu",
            "UU": "UU",
            "PP": "PP",
            "Perpres": "Perpres",
            "Permen": "Permen",
        }
        canonical = type_map.get(reg_type_str, reg_type_str)
        resolved = NodeID(reg_type=canonical, year=int(year), number=number)

        # Deduplicate
        key = str(resolved)
        if key in seen:
            continue
        seen.add(key)

        refs.append(Reference(raw_text=raw, resolved_id=resolved))
    return refs


def split_into_bab_blocks(text: str) -> list[tuple[str, str, str]]:
    """Split body text into (bab_number, bab_title, bab_text) blocks."""
    bab_pattern = re.compile(r"^BAB\s+([IVXLCDM]+)\s*\n(.+?)$", re.MULTILINE)
    matches = list(bab_pattern.finditer(text))
    if not matches:
        return []
    blocks = []
    for i, m in enumerate(matches):
        number = m.group(1)
        title = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block_text = text[start:end].strip()
        blocks.append((number, title, block_text))
    return blocks


def split_into_pasal_blocks(text: str) -> list[tuple[str, str]]:
    """Split body text into (pasal_number, pasal_text) blocks."""
    matches = list(RE_PASAL.finditer(text))

    # Filter out false positives: references like "dimaksud dalam\nPasal 4\nayat (1)"
    # Real Pasal headers are followed by (1), a capital letter, or blank then content.
    # False ones are followed by lowercase "ayat", "huruf", "angka" (broken references).
    valid_matches = []
    for m in matches:
        after = text[m.end():m.end()+30].lstrip('\n')
        if re.match(r'^(ayat|huruf|angka)\b', after, re.IGNORECASE) and not after.startswith('('):
            continue
        # Also check before: false matches are preceded by "dimaksud dalam", "sebagaimana", etc.
        before = text[max(0, m.start()-40):m.start()]
        if re.search(r'(dimaksud|dalam|sebagaimana)\s*$', before):
            continue
        valid_matches.append(m)

    blocks = []
    for i, m in enumerate(valid_matches):
        number = m.group(1)
        start = m.end()
        end = valid_matches[i + 1].start() if i + 1 < len(valid_matches) else len(text)
        block_text = text[start:end].strip()
        blocks.append((number, block_text))
    return blocks


def parse_pasal_content(pasal_number: str, text: str, base_id: NodeID) -> Node:
    """Parse a single Pasal block into a Node with children (Ayat/Huruf/Angka)."""
    pasal_path = base_id.path + [("Pasal", pasal_number)]
    pasal_id = NodeID(
        reg_type=base_id.reg_type,
        year=base_id.year,
        number=base_id.number,
        path=pasal_path,
    )

    pasal_node = Node(id=pasal_id, node_type=NodeType.PASAL, number=pasal_number)

    ayat_matches = list(RE_AYAT.finditer(text))
    if ayat_matches:
        # Capture leading text before first Ayat as the Pasal's own text
        leading_text = text[:ayat_matches[0].start()].strip()
        if leading_text:
            pasal_node.text = leading_text

        seen_ayat: set[str] = set()
        for i, m in enumerate(ayat_matches):
            ayat_num = m.group(1)
            if ayat_num in seen_ayat:
                continue
            seen_ayat.add(ayat_num)

            ayat_text_start = m.start()
            ayat_text_end = ayat_matches[i + 1].start() if i + 1 < len(ayat_matches) else len(text)
            ayat_full_text = text[ayat_text_start:ayat_text_end].strip()

            # Ayat content = leading text (from Pasal) + ayat's own text
            # This gives each Ayat the full sentence context
            ayat_content = m.group(2)
            remaining = ayat_full_text[m.end() - ayat_text_start:].strip()
            if remaining:
                ayat_content = ayat_content + " " + remaining

            # Prepend Pasal leading text to Ayat 1 for full sentence
            if ayat_num == "1" and leading_text:
                ayat_content = leading_text + " " + ayat_content

            ayat_id = NodeID(
                reg_type=base_id.reg_type,
                year=base_id.year,
                number=base_id.number,
                path=pasal_path + [("Ayat", ayat_num)],
            )
            ayat_node = Node(
                id=ayat_id, node_type=NodeType.AYAT, number=ayat_num, text=ayat_content
            )
            pasal_node.children.append(ayat_node)
    else:
        pasal_node.text = text

    return pasal_node


def parse_regulation(text: str, reg_type: RegulationType, number: str, year: int, title: str) -> Regulation:
    """Parse full regulation text into structured Regulation object."""
    text = normalize_ocr_text(text)

    # Split off Penjelasan section to avoid duplicate Pasal matches
    penjelasan_idx = re.search(r"\nPENJELASAN\s*\n", text)
    body_text = text[:penjelasan_idx.start()] if penjelasan_idx else text
    penjelasan_text = text[penjelasan_idx.start():] if penjelasan_idx else ""

    reg = Regulation(reg_type=reg_type, number=number, year=year, title=title)
    base_id = reg.node_id

    # Extract Pembukaan
    mengingat_match = RE_MENGINGAT.search(body_text)
    if mengingat_match:
        start = mengingat_match.end()
        end_match = re.search(r"(MEMUTUSKAN|BAB\s+[IVX])", body_text[start:])
        end = start + end_match.start() if end_match else start + 2000
        dasar_hukum_text = body_text[start:end]
        reg.pembukaan.dasar_hukum = extract_dasar_hukum(dasar_hukum_text)

    # Try BAB-level parsing first
    bab_blocks = split_into_bab_blocks(body_text)
    if bab_blocks:
        bab_counter: dict[str, int] = {}
        for bab_number, bab_title, bab_text in bab_blocks:
            # Disambiguate repeated BAB numbers (e.g. Cipta Kerja has BAB V twice)
            bab_counter[bab_number] = bab_counter.get(bab_number, 0) + 1
            bab_key = bab_number if bab_counter[bab_number] == 1 else f"{bab_number}_{bab_counter[bab_number]}"

            bab_path = [("Bab", bab_key)]
            bab_id = NodeID(
                reg_type=base_id.reg_type,
                year=base_id.year,
                number=base_id.number,
                path=bab_path,
            )
            bab_node = Node(
                id=bab_id, node_type=NodeType.BAB, number=bab_number, title=bab_title
            )

            pasal_blocks = split_into_pasal_blocks(bab_text)
            # Pre-scan for repeated Pasal numbers to disambiguate all occurrences
            pasal_num_counts: dict[str, int] = {}
            for pn, _ in pasal_blocks:
                pasal_num_counts[pn] = pasal_num_counts.get(pn, 0) + 1

            pasal_counter: dict[str, int] = {}
            for pasal_number, pasal_text in pasal_blocks:
                pasal_counter[pasal_number] = pasal_counter.get(pasal_number, 0) + 1
                # Only disambiguate if this Pasal number appears more than once
                if pasal_num_counts[pasal_number] > 1:
                    pasal_key = f"{pasal_number}_{pasal_counter[pasal_number]}"
                else:
                    pasal_key = pasal_number

                pasal_base = NodeID(
                    reg_type=base_id.reg_type,
                    year=base_id.year,
                    number=base_id.number,
                    path=bab_path,
                )
                node = parse_pasal_content(pasal_key, pasal_text, pasal_base)
                bab_node.children.append(node)

            reg.batang_tubuh.append(bab_node)
    else:
        # Flat structure (no BABs) — parse Pasal directly
        pasal_blocks = split_into_pasal_blocks(body_text)
        for pasal_number, pasal_text in pasal_blocks:
            node = parse_pasal_content(pasal_number, pasal_text, base_id)
            reg.batang_tubuh.append(node)

    # Store penjelasan umum if present
    if penjelasan_text:
        umum_match = re.search(r"UMUM\s*\n(.+?)(?=PASAL DEMI PASAL|$)", penjelasan_text, re.DOTALL)
        if umum_match:
            reg.penjelasan_umum = umum_match.group(1).strip()

    return reg
