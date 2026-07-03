"""Explain endpoint — GET /api/explain?term=PKWT

Returns legal definitions and related provisions for a term.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from ..schemas import ExplainResponse, ExplainDefinition
from ..services.graph import search_definitions, search_provisions_by_topic
from ..services.llm import call_llm_simple

router = APIRouter()


EXPLAIN_PROMPT_TEMPLATE = """Kamu adalah asisten hukum ketenagakerjaan Indonesia.

Berdasarkan kutipan pasal berikut, jelaskan secara ringkas dan akurat:
**Apa yang dimaksud dengan "{term}"?**

KUTIPAN PASAL:
{provisions_text}

FORMAT JAWABAN (JSON):
{{
  "definition": "definisi singkat (1-2 kalimat)",
  "explanation": "penjelasan lebih lengkap (2-4 kalimat, konteks praktis)",
  "related_provisions": ["node_id_1", "node_id_2"],
  "key_points": ["poin 1", "poin 2", "poin 3"]
}}

RULES:
- Definisi HARUS berdasarkan pasal yang dikutip, bukan pengetahuan umum
- Jika term tidak ditemukan dalam kutipan, jawab definition: "Tidak ditemukan definisi resmi dalam regulasi yang tersedia"
- Return ONLY valid JSON"""


@router.get("/explain", response_model=ExplainResponse)
async def explain(term: str = Query(..., min_length=2)):
    keywords = [term]
    # Add common variations
    term_lower = term.lower()
    if term_lower == "pkwt":
        keywords.extend(["perjanjian kerja waktu tertentu", "PKWT"])
    elif term_lower == "pkwtt":
        keywords.extend(["perjanjian kerja waktu tidak tertentu", "PKWTT"])
    elif term_lower == "phk":
        keywords.extend(["pemutusan hubungan kerja", "PHK"])
    elif term_lower == "ump":
        keywords.extend(["upah minimum provinsi", "UMP"])
    elif term_lower == "umk":
        keywords.extend(["upah minimum kabupaten", "UMK"])
    elif term_lower == "thr":
        keywords.extend(["tunjangan hari raya", "THR"])
    elif term_lower == "bpjs":
        keywords.extend(["jaminan sosial", "BPJS"])
    elif term_lower == "jht":
        keywords.extend(["jaminan hari tua", "JHT"])
    elif term_lower == "jkk":
        keywords.extend(["jaminan kecelakaan kerja", "JKK"])
    elif term_lower == "jkm":
        keywords.extend(["jaminan kematian", "JKM"])
    elif term_lower == "jp":
        keywords.extend(["jaminan pensiun", "JP"])
    elif term_lower == "alih daya":
        keywords.extend(["outsourcing", "pemborongan"])
    elif term_lower == "tka":
        keywords.extend(["tenaga kerja asing", "TKA", "RPTKA"])

    # Fetch definition provisions
    definitions = search_definitions(keywords, limit=8)

    if not definitions:
        return ExplainResponse(
            term=term,
            definition="Tidak ditemukan definisi resmi dalam regulasi yang tersedia.",
            explanation=None,
            sources=[],
            key_points=[],
        )

    # Build prompt with provision text
    provisions_text = ""
    for d in definitions:
        text_preview = (d["text"] or "")[:500]
        provisions_text += f"\n[{d['node_id']}]\n{text_preview}\n"

    prompt = EXPLAIN_PROMPT_TEMPLATE.format(term=term, provisions_text=provisions_text)
    raw = call_llm_simple(prompt)

    if not raw:
        # Fallback: return raw definitions without LLM
        return ExplainResponse(
            term=term,
            definition=definitions[0]["text"][:200] if definitions else "",
            explanation=None,
            sources=[ExplainDefinition(node_id=d["node_id"], text=d["text"][:200]) for d in definitions[:5]],
            key_points=[],
        )

    # Parse LLM response
    import json
    try:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()
        parsed = json.loads(raw)
    except (json.JSONDecodeError, Exception):
        return ExplainResponse(
            term=term,
            definition=definitions[0]["text"][:200] if definitions else "",
            explanation=None,
            sources=[ExplainDefinition(node_id=d["node_id"], text=d["text"][:200]) for d in definitions[:5]],
            key_points=[],
        )

    sources = [
        ExplainDefinition(node_id=d["node_id"], text=d["text"][:200])
        for d in definitions[:5]
    ]

    return ExplainResponse(
        term=term,
        definition=parsed.get("definition", ""),
        explanation=parsed.get("explanation"),
        sources=sources,
        key_points=parsed.get("key_points", []),
    )
