# Jurisprudence Layer — R&D Plan

## Overview

Layer 4 of the legal knowledge graph: court decisions that show how norms are actually enforced. Turns compliance advice from "what the law says" into "what actually happens in court."

**Why it matters:**
- Indonesia is civil law — precedent isn't binding, but it reveals judicial tendency
- The same norm can produce different outcomes depending on facts + court + judge
- "Demi hukum menjadi PKWTT" is the norm. "70% of PHI judges enforce it" is the reality.
- Clients pay for the reality, not the theory.

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│ Product: "Berdasarkan 8 putusan serupa,         │
│  posisi perusahaan lemah (75% kalah)"           │
└───────────────────────┬─────────────────────────┘
                        │ reads
┌───────────────────────▼─────────────────────────┐
│ Layer 4: Jurisprudence                          │
│ - Court decisions (PHI, PT, MA)                 │
│ - Parsed into: facts, norms cited, outcome      │
│ - Linked to Norm nodes (VALIDATES/CONTRADICTS)  │
│ - Statistical: win rate per norm × fact pattern │
└───────────────────────┬─────────────────────────┘
                        │ links to
┌───────────────────────▼─────────────────────────┐
│ Layer 3: Norms (27 norms, growing)              │
│ Layer 1-2: Structural graph (5,685 provisions)  │
└─────────────────────────────────────────────────┘
```

---

## Data Sources

### Primary: putusan3.mahkamahagung.go.id

The official court decision database. Contains all Indonesian court decisions.

| Fact | Detail |
|------|--------|
| Total decisions | ~500,000+ |
| PHI (labor) subset | Estimated 20,000-50,000 |
| Format | HTML pages + some PDF |
| Access | Public, but behind Cloudflare WAF |
| Search | By keyword, court type, date, classification |
| URL pattern | `https://putusan3.mahkamahagung.go.id/direktori/putusan/{hash}.html` |

### Secondary: Existing datasets

| Source | Content | Usefulness |
|--------|---------|-----------|
| indo-law (CSUI) | 22,630 criminal decisions, XML annotated | Format reference only (wrong domain) |
| Hukumonline | Curated landmark decisions | Paywalled, but cites case numbers we can look up |
| Legal journals/blogs | Analysis of important decisions | Case numbers + summaries as starting seeds |
| Law firm publications | Client alerts citing recent decisions | Good for landmark cases |

### Court hierarchy (for HR/labor)

```
PHI (Pengadilan Hubungan Industrial)  ← first instance, highest volume
  ↓ appeal
PT (Pengadilan Tinggi)                ← rarely used for PHI
  ↓ cassation  
MA (Mahkamah Agung)                   ← final word, highest authority
  
MK (Mahkamah Konstitusi)              ← separate track, judicial review of UU
```

For labor cases: PHI → MA (direct cassation, skips PT). So we need PHI + MA decisions.

---

## Case Schema

### Node: Case

```yaml
Case:
  id: string                    # "PHI/JKT/2024/123" or MA decision number
  court: string                 # "PHI Jakarta", "MA"
  court_type: enum              # phi | pt | ma | mk
  case_number: string           # "45/Pdt.Sus-PHI/2024/PN.Jkt.Pst"
  date: date                    # decision date
  year: int
  province: string
  
  # Parties
  plaintiff_type: enum          # employee | employer | union
  defendant_type: enum          # employee | employer
  
  # Substance
  dispute_type: string          # "PHK", "PKWT conversion", "upah", "union busting"
  facts_summary: string         # extracted key facts
  facts_structured: {           # machine-readable facts
    contract_type?: "PKWT" | "PKWTT",
    masa_kerja_bulan?: int,
    upah?: int,
    alasan_phk?: string,
    sp_count?: int,
    has_written_contract?: bool,
    ...
  }
  
  # Legal basis
  norms_cited: [string]         # norm IDs applied by judge
  provisions_cited: [string]    # provision node_ids referenced
  
  # Outcome
  outcome: enum                 # employee_wins | employer_wins | partial | settlement
  outcome_detail: string        # specific: "PKWT dinyatakan PKWTT, pesangon 2×"
  award_amount?: int            # if monetary award
  
  # Reasoning
  pertimbangan_summary: string  # judge's key reasoning
  
  # Meta
  source_url: string
  scraped_at: timestamp
  confidence: enum              # high | medium | low (parsing quality)
```

### Relationships

| Edge | From → To | Meaning |
|------|-----------|---------|
| VALIDATES | Case → Norm | Court enforced this norm as written |
| CONTRADICTS | Case → Norm | Court ruled against the norm's plain reading |
| INTERPRETS | Case → Norm | Court added nuance/condition not in the text |
| CITES | Case → Provision | Decision references this specific Pasal |
| APPEALS | Case → Case | This decision appeals/overturns another |
| SIMILAR_FACTS | Case → Case | Factually similar (for pattern detection) |

---

## Parsing Pipeline

### Decision document structure (PHI)

Indonesian court decisions follow a standard format:

```
PUTUSAN
Nomor: XX/Pdt.Sus-PHI/20XX/PN.XXX

DEMI KEADILAN BERDASARKAN KETUHANAN YANG MAHA ESA

Pengadilan Hubungan Industrial pada Pengadilan Negeri ...

[IDENTITAS PARA PIHAK]
  - Penggugat: ... (employee/employer)
  - Tergugat: ... (employer/employee)

[TENTANG DUDUK PERKARA]           ← FACTS (what happened)
  - Kronologi
  - Gugatan

[TENTANG PERTIMBANGAN HUKUM]      ← REASONING (why the judge decided)
  - Menimbang...
  - References to Pasal/UU
  - Judge's analysis

MENGADILI:                         ← OUTCOME (what was decided)
  1. Mengabulkan gugatan Penggugat untuk sebagian
  2. Menyatakan hubungan kerja...
  3. Menghukum Tergugat membayar...
```

### Extraction algorithm

```python
def parse_putusan(html_or_text: str) -> Case:
    sections = split_sections(text)  
    # Sections detected by markers:
    #   "TENTANG DUDUK PERKARA" / "Menimbang, bahwa Penggugat"
    #   "TENTANG PERTIMBANGAN HUKUM" / "Menimbang, bahwa"
    #   "MENGADILI" / "M E N G A D I L I"
    
    # 1. Extract parties
    parties = extract_parties(sections.header)
    # Signal: "Penggugat" (plaintiff), "Tergugat" (defendant)
    # Determine: who is employee, who is employer
    
    # 2. Extract facts
    facts = extract_facts(sections.duduk_perkara)
    # Look for: contract type, duration, salary, termination reason
    # Structured extraction via LLM or pattern matching
    
    # 3. Extract legal basis cited
    provisions = extract_citations(sections.pertimbangan_hukum)
    # Regex: "Pasal \d+ (ayat \(\d+\))? (UU|PP|Permen|Perppu) (Nomor )?\d+(/| Tahun )\d+"
    # Map to node_ids in graph
    
    # 4. Extract outcome
    outcome = extract_outcome(sections.amar_putusan)
    # Signals:
    #   "Mengabulkan gugatan" → plaintiff wins
    #   "Menolak gugatan" → defendant wins  
    #   "Mengabulkan ... untuk sebagian" → partial
    #   "Menghukum ... membayar" → monetary award (extract amount)
    
    # 5. Match to norms
    norms = match_to_norms(provisions, facts)
    # Given cited provisions + facts, which of our Norm nodes apply?
    
    return Case(...)
```

### Key extraction signals

| Field | Signal phrases |
|-------|---------------|
| Employee wins | "mengabulkan gugatan Penggugat", "menyatakan putus hubungan kerja" |
| Employer wins | "menolak gugatan", "gugatan tidak dapat diterima" |
| PKWT→PKWTT conversion | "demi hukum menjadi PKWTT", "berubah menjadi PKWTT" |
| Severance awarded | "menghukum Tergugat membayar uang pesangon" + amount |
| SP procedure evaluated | "surat peringatan", "SP-1", "SP-2", "SP-3" |
| Duration issue | "melebihi jangka waktu", "lebih dari 5 (lima) tahun" |

---

## Access Strategy: Cloudflare Bypass

### The problem

putusan3.mahkamahagung.go.id uses Cloudflare WAF. Direct curl → 403.

### Approaches (ordered by reliability)

**1. Browser automation + stealth (recommended for scraping)**

```python
# playwright with stealth
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

async def scrape_putusan(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 ...",
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()
        await stealth_async(page)
        await page.goto(url, wait_until="networkidle")
        content = await page.content()
        await browser.close()
        return content
```

Tools:
- `playwright-stealth` (Python) or `puppeteer-extra-plugin-stealth` (Node)
- Camofox (Hermes-native via Browserbase)
- undetected-chromedriver (Python, older but works)

**2. Residential proxy rotation**

If stealth alone fails, add residential proxies:
- Bright Data, Oxylabs, or SmartProxy
- Indonesian residential IPs for best results (same country as target)
- Rotate per request to avoid pattern detection

**3. Formal data request**

Contact MA directly:
- Bagian Humas Mahkamah Agung
- Frame as academic/legal tech research
- CSUI got their 22k dataset this way
- Slower (weeks/months) but gives bulk access without scraping

**4. Hybrid: manual seed + automated expansion**

1. Manually collect 30-50 case numbers from legal blogs / Hukumonline citations
2. Use browser automation to fetch only those specific URLs
3. Low volume = less likely to trigger WAF
4. Proves the pipeline without bulk scraping

### Rate limiting (for any automated approach)

```
- Max 1 request per 5-10 seconds
- Random delays between requests (3-15s)
- Rotate user agents
- Session cookies: create new session every 50-100 requests
- Time of day: scrape during off-hours (2-6 AM WIB)
- Save raw HTML immediately (don't re-fetch)
```

### Storage for raw scrapes

```
corpus/putusan/
├── raw/
│   ├── phi_jkt_2024_001.html
│   ├── phi_sby_2024_002.html
│   └── ...
├── parsed/
│   ├── phi_jkt_2024_001.json
│   └── ...
└── metadata.json  # index of what's been scraped
```

---

## Statistical Layer

### What to compute once you have enough cases

**Win rate per norm:**
```
Norm PKWT-04 (max 5 years):
  Total cases citing this: 45
  Employee wins: 34 (75.6%)
  Employer wins: 8 (17.8%)
  Partial: 3 (6.7%)
  
  → "Strong norm — judges consistently enforce"
```

**Win rate by fact pattern:**
```
PKWT-04 + employee consented in writing to extension:
  Employee wins: 4/10 (40%)
  → Consent significantly weakens employee position

PKWT-04 + no written consent:
  Employee wins: 30/35 (85.7%)
  → Very strong position without consent evidence
```

**Court-level tendency:**
```
PHI Jakarta: 78% employee wins on PKWT conversion
PHI Surabaya: 65% employee wins on PKWT conversion
MA (cassation): 60% upholds PHI
  → PHI Jakarta is most employee-friendly
```

**Minimum sample sizes:**
```
Norm-level stats: meaningful at n≥10
Fact-pattern stats: meaningful at n≥20
Court-level comparison: meaningful at n≥30 per court
Predictive model: needs n≥100 per dispute type
```

---

## Product Output (what this enables)

### Without jurisprudence (current):
```
📎 HUKUM: PKWT yang melebihi 5 tahun demi hukum menjadi PKWTT
   (PP 35/2021 Pasal 8)
```

### With jurisprudence:
```
📎 HUKUM: PKWT yang melebihi 5 tahun demi hukum menjadi PKWTT
   (PP 35/2021 Pasal 8)

📊 PRAKTIK PENGADILAN:
   • 34/45 putusan PHI (75%) menyatakan konversi otomatis
   • Faktor penguat: tidak ada persetujuan tertulis perpanjangan
   • Faktor pelemah: karyawan menandatangani perpanjangan sadar
   • Putusan terbaru: PHI Jakarta No. 123/2024 — mengabulkan konversi
   
   ⚠️ MA kadang membatalkan jika ada bukti consent (8/45 kasus)
```

The `📊 PRAKTIK PENGADILAN` becomes a fourth space in the output — or folds into the Analisis space with explicit statistical backing.

---

## Implementation Phases

### Phase 1: Manual seed collection (1-2 days)

```
□ Collect 30-50 PHI case numbers from:
  - Legal blog analysis posts
  - Hukumonline case citations
  - Google: "putusan PHI PKWT 2023 2024"
  - Academic papers on labor dispute outcomes
□ Record: case_number, court, year, dispute_type, brief outcome
□ Store in corpus/putusan/seeds.json
□ This gives you target URLs for Phase 2
```

### Phase 2: Access pipeline (3-5 days)

```
□ Set up playwright + stealth for putusan3
□ Test: can you load a single decision page without 403?
□ If blocked: add residential proxy
□ If still blocked: try Camofox / Browserbase
□ Fetch the 30-50 seeded decisions
□ Save raw HTML to corpus/putusan/raw/
□ Verify: can you extract text from saved HTML?
```

### Phase 3: Parser (1-2 weeks)

```
□ Build section splitter (DUDUK PERKARA / PERTIMBANGAN / MENGADILI)
□ Build party extractor (who is plaintiff, who is defendant, roles)
□ Build outcome extractor (wins/loses/partial + amount)
□ Build citation extractor (Pasal references → node_ids)
□ Build fact extractor (LLM-assisted: contract type, duration, salary)
□ Test against 10 hand-verified decisions
□ Measure: accuracy per field
```

### Phase 4: Graph integration (3-5 days)

```
□ Load Case nodes into Neo4j
□ Wire VALIDATES/CONTRADICTS/INTERPRETS edges to Norm nodes
□ Wire CITES edges to Provision nodes
□ Build basic queries:
  - "What cases cite Norm PKWT-04?"
  - "What's the win rate for employees on PKWT conversion?"
  - "Show me cases where MA overturned PHI"
□ Verify: traversal from Norm → Cases works correctly
```

### Phase 5: Statistics (1 week)

```
□ Compute win rate per norm (with enough cases)
□ Compute win rate by fact pattern (need structured facts)
□ Surface in API: /api/norm/{id}/statistics
□ Integrate into three-space output (PRAKTIK PENGADILAN section)
□ Handle: "insufficient data" gracefully (< 10 cases = don't show stats)
```

### Phase 6: Scale (ongoing)

```
□ Expand to 500+ PHI decisions (automated scraping)
□ Add MA cassation decisions (different URL pattern)
□ Build APPEALS edges (PHI → MA, track overturn rate)
□ Time-series: "Has judicial tendency changed since Cipta Kerja?"
□ Alert: new decision published that cites tracked norms
```

---

## Validation

### Parser accuracy test

For each of the first 30 parsed decisions, manually verify:

| Field | Target accuracy |
|-------|----------------|
| Outcome (win/lose/partial) | ≥95% (this is the easiest — "MENGADILI" section is formulaic) |
| Parties (who is employee/employer) | ≥90% |
| Dispute type | ≥85% |
| Provisions cited | ≥80% (regex catches most, misses informal references) |
| Facts extraction | ≥70% (hardest — unstructured prose) |
| Norm linking | ≥75% (depends on provision extraction quality) |

### Statistical validity

```
For any statistic shown to users:
  - Minimum n=10 cases to show any percentage
  - Minimum n=20 to show fact-pattern breakdowns
  - Always show sample size: "34/45 putusan (75%)"
  - Never present as prediction without confidence interval
  - Recency bias: weight last 2 years higher than 5+ years ago
```

---

## Risk & Mitigation

| Risk | Probability | Mitigation |
|------|-------------|------------|
| Cloudflare blocks all scraping attempts | Medium | Formal data request to MA as backup path |
| PHI decisions are too unstructured to parse reliably | Low | Format is fairly standard; LLM handles edge cases |
| Not enough PHI decisions for statistical significance | Medium | Start with most common dispute types (PKWT, PHK); 20-50 is enough for directional insight |
| MA overturns PHI in ways that invalidate norm validation | Expected | Track overturn rate per norm; surface "MA may disagree" in output |
| Decisions reference old law (pre-Cipta Kerja) | Expected | Temporal filter: distinguish pre/post CK decisions; weight post-CK higher |
| Parsing hallucinates outcomes | Low-Medium | Outcome extraction is from formulaic "MENGADILI" section; regex-first, LLM-fallback |

---

## First Session Checklist

```
□ Google 30 PHI decision case numbers (PKWT/PHK disputes, 2022-2024)
□ Try playwright-stealth against putusan3 — can you load a page?
□ If yes: fetch 5 decisions, save HTML
□ If no: try with residential proxy OR fall back to manual collection
□ Pick 1 decision, manually annotate: parties, facts, outcome, provisions cited
□ Write section splitter (regex for DUDUK PERKARA / PERTIMBANGAN / MENGADILI)
□ Parse the 1 decision programmatically, compare to manual annotation
□ If extraction works: you have a pipeline. Scale it.
```
