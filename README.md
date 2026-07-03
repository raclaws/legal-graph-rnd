# legal-graph-rnd

Indonesian Legal Knowledge Graph with deterministic HR Compliance Checker.

Parses Indonesian labor regulations into a structured graph, extracts legal obligations mechanically (no LLM for evaluation), and checks HR documents against them with full traceability to source Pasal.

## What it does

1. **Structural Parser** — Converts regulation PDFs into a provision tree (BAB → Pasal → Ayat → Huruf) following Lampiran II UU 12/2011
2. **Knowledge Graph** — Neo4j graph with 5,676 provisions, cross-references, and amendment chains
3. **Norm Compiler** — Signal-based regex compiler that extracts obligations from Pasal text without LLM (1,224 candidates from 16 regulations)
4. **Deterministic Evaluator** — LLM extracts document fields, code evaluates compliance. Same input = same output.
5. **Compliance Pipeline** — Upload HR document → extract fields → match against graph-backed norms → verdicts with legal basis

## Architecture

```
Document (PKWT, Slip Gaji, PP)
    ↓
LLM Extraction (fields only, never judges)
    ↓
Derived Fields (salary vs UMP, duration calc)
    ↓
Norm Matching (graph-backed obligations)
    ↓
Deterministic Verdict (COMPLIANT / VIOLATION / NEEDS_REVIEW)
    ↓
Report (traced to specific Pasal)
```

## Stack

- **Runtime:** Python 3.12, Streamlit
- **Parser:** regex + pymupdf (no ML)
- **Graph:** Neo4j 5 (Docker)
- **LLM:** Claude API (extraction only)
- **Norm Compiler:** regex signal detection, 4-layer classification
- **Corpus:** 16 regulations, post-Cipta Kerja (PP 35-37/2021, UU 6/2023, etc.)

## Setup

```bash
# Install dependencies
pip install -e ".[dev]"

# Start Neo4j
docker compose up -d

# Parse and ingest corpus
python scripts/reparse_corpus.py

# Migrate hand-crafted norms to graph
python scripts/migrate_norms.py

# Run the app
streamlit run app.py

# Run tests
pytest
```

## Project Structure

```
src/
  parser/         — Structural parser (Lampiran II spec)
  schema/         — Data models (Regulation, Node, NodeID)
  graph/          — Neo4j operations (ingest, query, IMPOSES edges)
  extraction/     — LLM-assisted implicit reference extraction
  compliance/
    obligations.py        — Deterministic evaluator engine
    obligations_pkwt.py   — 15 PKWT norms (verified)
    obligations_upah.py   — 12 wage norms (verified)
    extraction_schemas.py — LLM extraction prompts
    pipeline.py           — 4-step orchestrator (detect → extract → derive → evaluate)
    norm_compiler.py      — Signal-based norm compiler (no LLM)
scripts/
  reparse_corpus.py   — Re-ingest all regulations with fixed parser
  migrate_norms.py    — Push norms to Neo4j
  run_compiler.py     — Run norm compiler against full corpus
corpus/
  raw/            — Source PDF files
app.py            — Streamlit UI (document upload + compliance report)
docker-compose.yml
```

## Node ID Convention

```
PP/2021/35/Bab/IV/Pasal/15/Ayat/1
UU/2003/13/Bab/IX/Pasal/59/Ayat/4
```

Pattern: `{type}/{year}/{number}/Bab/{roman}/Pasal/{num}/Ayat/{num}`

## Norm Compiler

The compiler detects obligations in provision text using 4 signal layers:

1. **Explicit obligations** — wajib, harus, dilarang, tidak boleh
2. **Threshold markers** — paling lama, sekurang-kurangnya, paling sedikit
3. **Passive constraints** — dilaksanakan/diberikan + limit
4. **Cross-provision consequence** — penalty Pasal references obligation Pasal

Output: 1,224 candidate norms (249 high confidence, 927 medium, 48 low) from 16 regulations.

## Principles

- **Deterministic:** LLM extracts fields, code evaluates. No LLM judgment.
- **Traceable:** Every verdict links to a specific Pasal.
- **Edge cases explicit:** Never hidden — stated as NormEdgeCase nodes in graph.
- **Graph-first:** Norms load from Neo4j at runtime, Python fallback only.
- **No training required:** Compiler uses linguistic patterns, not ML.

## Coverage

| Category | Norms | Status |
|----------|-------|--------|
| PKWT (fixed-term contracts) | 15 | Verified, linked |
| Upah (wages) | 12 | Verified, linked |
| BPJS (social security) | — | Backlog |
| TKA (foreign workers) | — | Backlog |
| PHK (termination) | — | Backlog |

## License

Private R&D. Not for distribution.
