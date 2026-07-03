# HR Compliance Corpus — Reference

**Last updated:** 2026-07-03
**Graph:** Neo4j on 194.233.90.61:7474

---

## Corpus Status

### Fully Parsed & Ingested

| # | Regulation | Title | Nodes | Status |
|---|-----------|-------|-------|--------|
| 1 | UU 13/2003 | Ketenagakerjaan (base law) | 18 BAB, 193 Pasal, 414 Ayat | ✅ |
| 2 | Perppu 2/2022 | Cipta Kerja (substance) | 16 BAB, 1147 Pasal, 1866 Ayat | ✅ |
| 3 | UU 6/2023 | Penetapan Perppu 2/2022 menjadi UU | 2 Pasal | ✅ |
| 4 | PP 35/2021 | PKWT, Alih Daya, Waktu Kerja, PHK | 9 BAB, 66 Pasal, 132 Ayat | ✅ |
| 5 | PP 36/2021 | Pengupahan | 15 BAB, 82 Pasal, 201 Ayat | ✅ |
| 6 | PP 37/2021 | Jaminan Kehilangan Pekerjaan (JKP) | 9 BAB, 50 Pasal, 100 Ayat | ✅ |
| 7 | PP 34/2021 | Penggunaan Tenaga Kerja Asing (TKA) | 11 BAB, 48 Pasal, 103 Ayat | ✅ |
| 8 | UU 2/2004 | Penyelesaian Perselisihan Hubungan Industrial | 8 BAB, 126 Pasal, 203 Ayat | ✅ |
| 9 | PP 51/2023 | Perubahan PP 36/2021 (UMP/UMK formula) | 20 BAB, 48 Pasal | ✅ |
| 10 | PP 21/2024 | Perubahan PP 25/2020 (Tapera) | 6 Pasal, 14 Ayat | ✅ |

### Stub Nodes (metadata only, not parsed)

| # | Regulation | Title | Created From |
|---|-----------|-------|--------------|
| 1 | UU/2020/11 | Cipta Kerja (original, revoked) | Perppu dasar_hukum |
| 2 | PP/2020/25 | Penyelenggaraan Tapera | PP 21/2024 dasar_hukum |
| 3 | UU/2016/4 | Tabungan Perumahan Rakyat | PP 21/2024 dasar_hukum |
| 4 | UU/2004/40 | SJSN | PP 37/2021 dasar_hukum |
| 5 | UU/2011/24 | BPJS | PP 37/2021 dasar_hukum |
| 6 | UU/2022/2 | (Perppu ref in PP 51) | PP 51/2023 dasar_hukum |

---

## Graph Statistics

```
Regulations:  16 (10 parsed, 6 stubs)
Provisions:   4,906
Edges:
  CONTAINS:   4,882
  REFERENCES: 17
  IMPLEMENTS: 5
  AMENDS:     3
  REVOKES:    1
```

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
```

---

## Stale References Detected

| Source | References | Which Is Revoked By |
|--------|-----------|-------------------|
| PP/2021/34 | UU/2020/11 | Perppu/2022/2 |
| PP/2021/35 | UU/2020/11 | Perppu/2022/2 |
| PP/2021/36 | UU/2020/11 | Perppu/2022/2 |
| PP/2021/37 | UU/2020/11 | Perppu/2022/2 |

**Note:** These are genuine — the PPs were issued Feb 2021 citing UU 11/2020, which was later replaced Dec 2022. The PPs remain valid (they implement Cipta Kerja regardless of the UU number change) but their dasar_hukum text is technically outdated.

---

## Not Yet Parsed (backlog)

| Priority | Regulation | Subject | Why |
|----------|-----------|---------|-----|
| 🟡 | Permenaker 18/2022 | PKWT implementation detail | Supplements PP 35/2021 |
| 🟡 | Permenaker 6/2023 | BPJS Ketenagakerjaan contributions | Current rates |
| 🟡 | Perpres 64/2020 jo. 19/2024 | BPJS Kesehatan rates | Health insurance % |
| 🟡 | PP 33/2021 | Upah Minimum (override formula) | Min wage calculation |
| ⬜ | UU 40/2004 | SJSN (social security framework) | Structural foundation |
| ⬜ | UU 24/2011 | BPJS (organization law) | Enrollment obligations |
| ⬜ | Annual Kepgub | UMP/UMK per province | Temporal nodes, yearly |

---

## UMP/UMK (Minimum Wage) System

### How It Works

Indonesian minimum wages operate on 3 levels:

```
UMP (Upah Minimum Provinsi)
  = Provincial minimum wage
  = Set by Governor (Kepgub) annually
  = Formula defined in PP 36/2021 jo. PP 51/2023
  = Base floor — applies to all workers in the province

UMK (Upah Minimum Kabupaten/Kota)
  = Regency/City minimum wage
  = Must be ≥ UMP of that province
  = Set by Governor based on Bupati/Walikota recommendation
  = Not all kabupaten/kota have a separate UMK

UMSP (Upah Minimum Sektoral Provinsi) — ABOLISHED by Cipta Kerja
  = Sector-based minimum wage
  = No longer valid post-2022
```

### Formula (PP 36/2021 jo. PP 51/2023)

```
UMP(n+1) = UMP(n) × (1 + % kenaikan)

% kenaikan = f(inflasi, pertumbuhan_ekonomi, indeks_tertentu)

Cap: increase cannot exceed a maximum % set by government
Floor: UMP cannot decrease year-over-year
```

### Coverage by Province (38 provinces)

| Region | Provinces | Typical UMP Range (2025) |
|--------|-----------|--------------------------|
| Java | DKI Jakarta, Jawa Barat, Jawa Tengah, Jawa Timur, DIY, Banten | Rp 2.0M - 5.4M |
| Sumatra | Sumut, Sumbar, Riau, Jambi, Sumsel, Bengkulu, Lampung, Babel, Kepri | Rp 2.8M - 3.5M |
| Kalimantan | Kalbar, Kalteng, Kalsel, Kaltim, Kaltara | Rp 2.9M - 3.5M |
| Sulawesi | Sulut, Sulteng, Sulsel, Sultra, Gorontalo, Sulbar | Rp 2.8M - 3.6M |
| Bali & Nusa Tenggara | Bali, NTB, NTT | Rp 2.5M - 3.0M |
| Maluku & Papua | Maluku, Malut, Papua, Papua Barat, etc. | Rp 2.9M - 3.9M |

### Data Model for UMP/UMK

```yaml
MinimumWage:
  id: "UMP/2025/DKI-Jakarta"
  province: "DKI Jakarta"
  type: "UMP"  # or "UMK"
  kabupaten_kota: null  # only for UMK
  year: 2025
  amount: 5396000  # Rp per month
  effective_date: "2025-01-01"
  decree: "Kepgub DKI Jakarta Nomor X Tahun 2024"
  previous: "UMP/2024/DKI-Jakarta"
  formula_applied: "PP/2023/51"  # which formula PP was used
```

### Implementation Notes

1. **Source:** Annual Kepgub (Governor Decrees) — announced Nov-Dec for next year
2. **Structure:** One node per province per year, linked to previous year
3. **UMK is optional:** Only some kabupaten/kota have separate UMK
4. **Temporal:** Must query "what's the UMP for province X in year Y?"
5. **The graph edge:** Each UMP node → DERIVED_FROM → PP/2023/51 (or PP/2021/36 for pre-2024)
6. **UMSP abolished:** If system encounters pre-2022 sector minimum wages, flag as obsolete

### Key Compliance Rules

| Rule | Legal Basis | Risk |
|------|------------|------|
| Employer MUST pay ≥ UMP/UMK | PP 36/2021 Pasal 23 | Criminal penalty |
| UMP applies to workers with < 1 year tenure | PP 36/2021 Pasal 25 | Underpayment claim |
| Employers with > 1 year workers must have wage structure | PP 36/2021 Pasal 3 | Administrative sanction |
| UMP cannot be waived by agreement | UU 13/2003 Pasal 91 | Void clause |
| Small/micro enterprises may be exempt (Perpres) | PP 36/2021 Pasal 36 | Depends on Perpres |

### Integration Strategy

For the compliance product:
1. **Ingest:** Scrape annual Kepgub decrees (34-38 per year, one per province)
2. **Store:** As temporal nodes in graph with EFFECTIVE_IN year
3. **Query:** "Is salary X compliant for province Y?" → compare against UMP/UMK
4. **Alert:** When new year UMP announced, flag employees below new threshold
5. **History:** "What was UMP Jakarta in 2023?" → temporal traversal

### Data Sources for UMP/UMK

| Source | Coverage | Format |
|--------|----------|--------|
| jdih.kemnaker.go.id | Permenaker on formula | PDF |
| Provincial JDIH sites | Kepgub per province | PDF/HTML |
| bps.go.id | Inflation/growth inputs to formula | Structured data |
| kemnaker.go.id/informasi | Annual summary tables | HTML |
| gajimu.com | Unofficial aggregator (cross-reference only) | HTML |
