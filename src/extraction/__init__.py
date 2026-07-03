"""LLM-assisted extraction for implicit references."""

from __future__ import annotations

from dataclasses import dataclass

from src.schema import NodeID


@dataclass
class ExtractionResult:
    source_id: NodeID
    target_ref: str
    resolved_id: NodeID | None = None
    confidence: float = 0.0
    context: str = ""


EXTRACTION_PROMPT = """You are analyzing Indonesian legal text. Extract all cross-references to other regulations or provisions.

For each reference found, return:
- raw_text: the exact text of the reference
- target_type: regulation type (UU, PP, Perpres, Permen, etc.)
- target_number: regulation number
- target_year: year
- target_provision: specific provision if mentioned (e.g., "Pasal 5 Ayat 1")

Common patterns:
- "sebagaimana dimaksud dalam Pasal X" (internal reference)
- "sebagaimana dimaksud dalam Pasal X Undang-Undang Nomor Y Tahun Z" (external reference)
- "berdasarkan ketentuan Pasal X" (basis reference)
- "sebagaimana telah diubah dengan..." (amendment reference)

Return JSON array. If no references found, return [].
"""


def build_extraction_messages(text: str, source_id: str) -> list[dict]:
    """Build messages for LLM extraction call."""
    return [
        {"role": "system", "content": EXTRACTION_PROMPT},
        {
            "role": "user",
            "content": f"Source: {source_id}\n\nText:\n{text}",
        },
    ]
