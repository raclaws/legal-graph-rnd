# Legal Graph R&D — Prototype Report

**Date:** 2026-07-03
**Status:** All 6 R&D success criteria met + first product use case (HR Compliance) functional
**Sessions:** 2 (morning: foundation + Cipta Kerja, afternoon: corpus expansion + UMP)

---

## What Was Built

End-to-end pipeline: PDF → Structural Parser → Neo4j Knowledge Graph → Compliance Engine → Streamlit UI

### Stack (as deployed)

| Component | Implementation |
|-----------|---------------|
| Parser | Python 3.12, regex-based (Lampiran II spec) |
| OCR normalization | Digit/letter confusion fix (2O2O→2020) |
| Schema | Python dataclasses (Regulation, Node, NodeID) |
| Graph DB | Neo4j 5 Community (Docker on VPS 194.233.90.61) |
| Corpus source | peraturan.go.id PDFs via pymupdf |
| Compliance engine | Severance calculator + UMP checker |
| Stale ref detector | Cypher queries (regulation-level + inline text) |
| LLM layer | Anthropic-compatible gateway, natural language → structured extraction |
| UI | Streamlit (5 tabs: Tanya AI, Severance, PKWT, Graph, Settings) |

---

## Graph State (current)

```
Regulations:     29 (17 fully parsed, 12 stubs from dasar_hukum)
Provisions:      5,676
MinimumWage:     42 (38 provinces × 2025 + 4 × 2026)

Edges:
  CONTAINS:      ~5,600
  REFERENCES:    20+
  IMPLEMENTS:    6
  AMENDS:        4
  REVOKES:       1
  DERIVED_FROM:  42 (UMP → PP 51/2023)
```

---

## Regulations Ingested

### Fully Parsed

| # | ID | Title | Nodes |
|---|-----|-------|-------|
| 1 | Perppu/2022/2 | Cipta Kerja | 16 BAB, 1147 Pasal, 1866 Ayat |
| 2 | UU/2023/6 | Penetapan Perppu 2/2022 menjadi UU | 2 Pasal |
| 3 | UU/2003/13 | Ketenagakerjaan | 18 BAB, 193 Pasal, 414 Ayat |
| 4 | PP/2021/35 | PKWT, Alih Daya, Waktu Kerja, PHK | 9 BAB, 66 Pasal, 132 Ayat |
| 5 | PP/2021/36 | Pengupahan | 15 BAB, 82 Pasal, 201 Ayat |
| 6 | PP/2021/37 | Jaminan Kehilangan Pekerjaan (JKP) | 9 BAB, 50 Pasal, 100 Ayat |
| 7 | PP/2021/34 | Penggunaan Tenaga Kerja Asing (TKA) | 11 BAB, 48 Pasal, 103 Ayat |
| 8 | UU/2004/2 | Penyelesaian Perselisihan Hubungan Industrial | 8 BAB, 126 Pasal, 203 Ayat |
| 9 | PP/2023/51 | Perubahan PP 36/2021 (UMP/UMK formula) | 20 BAB, 48 Pasal |
| 10 | PP/2024/21 | Perubahan PP 25/2020 (Tapera) | 6 Pasal, 14 Ayat |
| 11 | PP/2015/44 | JKK + JKM (rates, claims, benefits) | 11 BAB, 66 Pasal, 182 Ayat |
| 12 | PP/2015/45 | Jaminan Pensiun (JP) | 7 BAB, 38 Pasal, 98 Ayat |
| 13 | PP/2015/46 | Jaminan Hari Tua (JHT) | 8 BAB, 40 Pasal, 96 Ayat |
| 14 | Perpres/2020/64 | BPJS Kesehatan (JKN rates) | 13 Pasal |
| 15 | Perpres/2024/19 | Perubahan Perpres 64/2020 (JKN update) | 12 Pasal |
| 16 | Permen/2022/18 | Pelaksanaan PKWT, Alih Daya, Waktu Kerja | 4 BAB, 19 Pasal, 43 Ayat |
| 17 | Permen/2023/6 | BPJS Ketenagakerjaan iuran/manfaat | 12 BAB, 27 Pasal, 47 Ayat |

### Stub Nodes (metadata only)

| ID | Title | Created From |
|----|-------|--------------|
| UU/2020/11 | Cipta Kerja (original, revoked) | Perppu dasar_hukum |
| PP/2020/25 | Penyelenggaraan Tapera | PP 21/2024 dasar_hukum |
| UU/2016/4 | Tabungan Perumahan Rakyat | PP 21/2024 dasar_hukum |
| UU/2004/40 | SJSN | PP 37/2021 dasar_hukum |
| UU/2011/24 | BPJS | PP 37/2021 dasar_hukum |
| UU/2022/2 | Perppu ref in PP 51 | PP 51/2023 dasar_hukum |

---

## Relationship Map

```
UU/2023/6 —IMPLEMENTS→ Perppu/2022/2
Perppu/2022/2 —REVOKES→ UU/2020/11
Perppu/2022/2 —AMENDS→ UU/2003/13

PP/2021/34 —IMPLEMENTS→ Perppu/2022/2  (TKA)
PP/2021/35 —IMPLEMENTS→ Perppu/2022/2  (PKWT, PHK)
PP/2021/36 —IMPLEMENTS→ Perppu/2022/2  (Wages)
PP/2021/37 —IMPLEMENTS→ Perppu/2022/2  (JKP)

PP/2023/51 —AMENDS→ PP/2021/36  (UMP/UMK formula update)
PP/2024/21 —AMENDS→ PP/2020/25  (Tapera)

42 MinimumWage nodes —DERIVED_FROM→ PP/2023/51
```

---

## Stale References Detected

| Source | References | Revoked By |
|--------|-----------|------------|
| PP/2021/34 | UU/2020/11 | Perppu/2022/2 |
| PP/2021/35 | UU/2020/11 | Perppu/2022/2 |
| PP/2021/36 | UU/2020/11 | Perppu/2022/2 |
| PP/2021/37 | UU/2020/11 | Perppu/2022/2 |

These are genuine — PPs issued Feb 2021 citing UU 11/2020, which was replaced Dec 2022. PPs remain valid but dasar_hukum text is technically outdated.

---

## UMP/UMK System

### Coverage

```
38 provinces × UMP 2025 (all with values)
 4 provinces × UMP 2026 (decree found, amount pending parse)
```

### Source Quality Tiers

| Tier | Count | Meaning |
|------|-------|---------|
| primary_verified | 1 | PDF read, amount confirmed against decree (Jawa Tengah) |
| primary | 3 | Decree linked on JDIH, amount pending PDF parse (Kaltim, Sulteng, DKI 2026) |
| primary_unresolved | 1 | Decree found on listing, PDF URL not resolved (Banten 2026) |
| secondary | 37 | Value from public reports, no decree linked |

### JDIH Portal Availability (all 38 provinces checked)

| Status | Count | Notes |
|--------|-------|-------|
| Accessible | 27 | Can upgrade to primary source |
| Blocked (403) | 3 | Jabar, Jatim, Kalsel — likely work from Indonesian IP |
| Unreachable | 4 | Sumbar, Papua, Sulsel, Papua Pegunungan |
| Compromised | 2 | Sultra, Papua Barat (spam-injected) |
| Broken/Empty | 1 | DIY (empty Vite shell) |
| SSL Error | 1 | NTB |

### Data Model

Every MinimumWage node carries:
- `amount`, `province`, `year`, `type` (UMP/UMK)
- `source_quality` (primary_verified / primary / secondary)
- `source_note` (human-readable provenance)
- `primary_source` (decree number if known)
- `decree_url`, `pdf_url` (if available)
- `jdih_url`, `jdih_status` (portal availability)
- `captured_at`, `verified_at` (temporal metadata)

---

## R&D Success Criteria

| # | Criterion | Result |
|---|-----------|--------|
| 1 | Parse UU 6/2023 into full tree (200+ Pasal) | ✅ 1,147 Pasal parsed from embedded Perppu |
| 2 | Extract all dasar_hukum references | ✅ Resolved to NodeIDs, deduped |
| 3 | Map implementing PPs (from dasar_hukum) | ✅ 5 IMPLEMENTS edges |
| 4 | Show temporal chain: UU/2020/11 → revoked → UU/2023/6 | ✅ Full chain |
| 5 | Query "labor provisions" → correct Pasal chain | ✅ Bab IV → 66 Pasal |
| 6 | Detect stale reference to revoked UU | ✅ 4 real findings |

---

## Implementation Progress vs. HR Compliance Use Case

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1: Corpus completion | ✅ Done | All must-have + edge cases + BPJS detail regs |
| Phase 2: Compliance rules layer | ✅ Done | Severance + UMP + BPJS rates encoded |
| Phase 3: Query engine | ✅ Done | Three-space LLM output (Hukum/Analisis/Perlu Dikonfirmasi) |
| Phase 4: Severance calculator | ✅ Done | Full formula, 15 termination reasons, 6 tests |
| Phase 5: Minimal UI | ✅ Done | Streamlit 6 tabs, wide layout, BPJS calc, UMP check |
| UMP Compliance | ✅ Done | 38 provinces, source quality tracking, JDIH mapping |
| Document Context Layer | ⬜ Not started | Architecture defined, privacy contract locked |

---

## Key Technical Decisions

### 1. BAB-scoped node IDs
Cipta Kerja embeds amendments to dozens of laws. Without BAB in the path, Pasal numbers collide. Solution: `Perppu/2022/2/Bab/IV/Pasal/81`.

### 2. Disambiguation suffixes for repeated numbers
BAB V appears twice in Cipta Kerja. Pasal numbers repeat within BABs. Solution: append `_N` suffix when a number repeats within its parent scope.

### 3. OCR normalization layer
Government PDFs have consistent OCR artifacts (O↔0, l↔1 in years). Fixed with a pre-parse normalization pass.

### 4. Penjelasan separation
Penjelasan section re-uses "Pasal N" markers. Solution: split on `\nPENJELASAN\n` before parsing body.

### 5. Ayat regex tightening
PDF line breaks create false Ayat matches. Fix: require `(N)` followed by uppercase letter start.

### 6. Source quality as first-class metadata
Every data point carries provenance (`captured_at`, `source_quality`, `verified_at`). The system never presents secondary-source data as if it were primary.

---

## Design Decisions (locked)

### Three-Space Output Architecture

Every response split into labeled zones:
- **Hukum** — graph-backed facts only, every line has `source_node_id`, zero hallucination risk
- **Analisis** — model interpretation, explicitly labeled, never introduces new legal claims
- **Perlu Dikonfirmasi** — questions back to user when critical info is missing

Rule: system NEVER gives Analisis before Hukum is sufficiently populated.

### Document Context Layer (platform-agnostic)

- Documents processed in memory only, no persistence after session
- No model training on user data, no cross-user learning
- LLM-assisted extraction (free-form docs)
- Matching to graph via semantic similarity + explicit regulation reference detection

### Privacy Contract

| Rule | Rationale |
|------|-----------|
| In-memory only | Legal docs are most sensitive business asset |
| No persistence after session | Trust = adoption |
| No model training on user data | User is not the product |
| No cross-user learning | Never "other companies do X" |
| User-initiated save only | Their storage, their encryption key |

### Bright-Line Test

System must say "Pasal tersebut tidak ditemukan" for fictional references. If an unverifiable claim ever appears in the Hukum space, the guardrail has failed.

---

## What Works (proven)

- **Addressable nodes**: any provision queryable by path
- **Cross-regulation traversal**: "What did Cipta Kerja change in the labor law?" → graph query
- **Temporal chain**: point-in-time queries via enacted/revoked metadata
- **Stale detection**: finds regulations/provisions referencing revoked targets (4 real hits)
- **Scale proven**: Cipta Kerja (1127 pages, 1147 Pasal) fully parsed
- **Severance calculator**: 15 termination reasons, cited legal basis, 6 passing tests
- **UMP compliance check**: "is salary X legal in province Y?" → yes/no + citation
- **Natural language query**: free-text Indonesian → LLM extraction → calculator/graph → answer
- **Source provenance**: every node tracked with quality tier + capture date

## Known Limitations

| # | Issue | Severity | Plan |
|---|-------|----------|------|
| 1 | No Huruf/Angka nodes | Low | Extract in Layer 1e |
| 2 | Dasar hukum misses constitutional refs | Low | No "Nomor X Tahun Y" pattern |
| 3 | Amendment-style Pasal have empty text | Info | Content in Ayat children |
| 4 | OCR quality varies by PDF age | Medium | Heavier normalization for pre-2011 |
| 5 | No Bagian/Paragraf parsing | Medium | Nesting between Bab and Pasal |
| 6 | 37/38 UMP still secondary source | Medium | JDIH scraping (27 accessible) |
| 7 | Most JDIH sites need headless browser | Medium | JS-driven search forms |

---

## Next Steps (prioritized)

1. **Document Context Layer** — ephemeral upload → extract → cross-reference against graph
2. **Claim extractor + citation validator** — guardrail routing LLM output, verify Hukum claims exist in graph
3. **JDIH headless scraper** — upgrade 27 provinces from secondary → primary UMP source
4. **UMK (city-level)** — ~100 kabupaten/kota with separate minimum wages
5. **Annual THR circular** — payment deadlines and penalties
6. **Bagian/Paragraf parser** — complete Lampiran II hierarchy
7. **Old vs New comparison** — show both UU 13/2003 and PP 35/2021 severance results

---

## Files

```
legal-graph-rnd/
├── src/
│   ├── schema/regulation.py       — Core data models
│   ├── parser/__init__.py         — Structural parser (regex + OCR fix)
│   ├── graph/__init__.py          — Neo4j operations
│   ├── extraction/__init__.py     — LLM prompt templates
│   └── compliance/
│       ├── __init__.py            — Severance calculator (PP 35/2021)
│       └── ump_2025.py            — UMP 2025 data (38 provinces)
├── scripts/
│   ├── fetch_corpus.py            — Download regulations
│   └── detect_stale_refs.py       — Stale reference detector
├── corpus/raw/                    — Source PDFs (10 regulations)
├── tests/                         — 13 passing tests
├── app.py                         — Streamlit UI (5 tabs)
├── docker-compose.yml             — Neo4j deployment
├── pyproject.toml                 — Dependencies
├── PROTOTYPE_REPORT.md            — This file
└── CORPUS_REFERENCE.md            — Full corpus map + UMP documentation
```
