---
name: legal-functions-taxonomy
description: Research taxonomy of legal text functions beyond obligations — prep for expanding norm compiler
metadata:
  type: project
  originSessionId: current
---

## Legal Contextual Functions Taxonomy (2026-07-03)

**Why:** The norm compiler currently only extracts OBLIGATIONS (wajib/harus/dilarang). Legal text serves many more functions. A complete legal assistant needs to model these to answer "what", "how", "when", "who" — not just "is this compliant?"

**How to apply:** Use this taxonomy when expanding the compiler. Each function type needs its own signal detection patterns and output format.

---

## Theoretical Framework

### 1. Deontic Logic (Normative)
The classical framework from legal philosophy. Norms express:
- **Obligation** (O): must do X → `wajib`, `harus`
- **Prohibition** (F): must not do X → `dilarang`, `tidak boleh`
- **Permission** (P): may do X → `dapat`, `berhak`
- **Power** (Pw): authority to do X → `berwenang`, `menetapkan`

### 2. Hohfeld's Legal Relations
More granular framework for rights/duties:
- **Right** ↔ **Duty** (correlative pair)
- **Privilege** ↔ **No-right**
- **Power** ↔ **Liability**
- **Immunity** ↔ **Disability**

### 3. Constitutive vs Regulative (Searle)
- **Regulative rules**: govern pre-existing behavior ("employers shall...")
- **Constitutive rules**: create new institutional facts ("PKWT is defined as...")

---

## Proposed Function Types for Indonesian Legal Text

Based on UU 12/2011 Lampiran II (legislative drafting standard) and observed patterns in our corpus:

### Type 1: DEFINITION (Ketentuan Umum) — IMPLEMENTED
- **Location:** Pasal 1, Bab I Ketentuan Umum
- **Pattern:** "yang dimaksud dengan ... adalah ..."
- **Output:** term → definition mapping
- **Use:** Answer "apa itu X?", provide context to other functions
- **Status:** ✅ Detected by norm compiler, used in explanation layer

### Type 2: OBLIGATION (Kewajiban) — IMPLEMENTED
- **Location:** Batang Tubuh (anywhere)
- **Pattern:** `wajib`, `harus`, `dilarang`, `tidak boleh`
- **Output:** subject + action + condition + consequence
- **Use:** Compliance checking ("is document X compliant?")
- **Status:** ✅ Core norm compiler output

### Type 3: RIGHT (Hak)
- **Location:** Batang Tubuh, often paired with obligations
- **Pattern:** `berhak`, `mempunyai hak`, `berhak atas`, `berhak memperoleh`
- **Output:** subject + entitlement + condition
- **Use:** Answer "apa hak pekerja jika X?", severance/benefit calculations
- **Distinction from obligation:** Rights are claims by the subject; obligations are duties on others
- **Example signals:**
  ```
  berhak                     → right
  berhak atas                → entitlement
  berhak memperoleh          → benefit right
  berhak mendapatkan         → benefit right
  berhak menolak             → refusal right
  mendapatkan ... sekurang-kurangnya → minimum entitlement
  ```

### Type 4: SCOPE (Ruang Lingkup)
- **Location:** Bab I or II, early provisions
- **Pattern:** `berlaku bagi`, `meliputi`, `tidak termasuk`, `dikecualikan`
- **Output:** rule + applicability boundary
- **Use:** Answer "does this apply to company X?" / "siapa yang tunduk pada aturan ini?"
- **Example signals:**
  ```
  berlaku bagi               → positive scope
  meliputi                   → enumerated scope
  tidak termasuk             → exclusion
  dikecualikan               → exception
  berlaku untuk              → positive scope
  tidak berlaku              → negative scope
  sepanjang                  → conditional scope
  ```

### Type 5: PROCEDURE (Tata Cara)
- **Location:** Often in implementing regulations (PP, Permen)
- **Pattern:** `dilakukan dengan cara`, `tata cara`, `mekanisme`, sequential numbered steps
- **Output:** ordered steps + actors + timelines
- **Use:** Answer "bagaimana cara X?" / "what's the process for X?"
- **Example signals:**
  ```
  tata cara                  → procedure marker
  dilakukan dengan cara      → method
  melalui tahapan            → staged process
  wajib menyampaikan ... paling lambat → deadline procedure
  diajukan kepada            → submission procedure
  numbered list (a. b. c.)   → sequential steps
  ```

### Type 6: THRESHOLD (Batasan Kuantitatif) — PARTIALLY IMPLEMENTED
- **Location:** Anywhere with numbers
- **Pattern:** `paling lama`, `paling sedikit`, `paling banyak`, numeric + unit
- **Output:** parameter + operator + value + unit
- **Use:** Calculators, automated checks ("is 6 years > max PKWT?")
- **Status:** ⚠️ Detected as THRESHOLD in classifier but not structured
- **Example signals:**
  ```
  paling lama N tahun/bulan  → maximum duration
  paling sedikit N%          → minimum percentage
  paling banyak N orang      → maximum count
  tidak melebihi             → ceiling
  sekurang-kurangnya         → floor
  N (spelled) unit           → quantified value
  ```

### Type 7: DELEGATION (Delegasi/Atribusi)
- **Location:** End of chapters or in specific provisions
- **Pattern:** `diatur lebih lanjut dengan/dalam`, `ditetapkan oleh`, `sesuai peraturan`
- **Output:** delegating_provision → delegated_regulation + authority
- **Use:** Navigate regulation hierarchy, find implementing rules
- **Example signals:**
  ```
  diatur lebih lanjut dengan → delegation to lower regulation
  diatur dengan              → delegation (strong)
  ditetapkan oleh Menteri    → ministerial authority
  berdasarkan ... yang ditetapkan → derived authority
  sesuai dengan ketentuan peraturan perundang-undangan → general delegation
  ```

### Type 8: TRANSITIONAL (Ketentuan Peralihan)
- **Location:** Bab Ketentuan Peralihan (near end)
- **Pattern:** `tetap berlaku`, `paling lama ... sejak`, `dinyatakan masih tetap berlaku`
- **Output:** old_rule + new_rule + transition_period + conditions
- **Use:** Answer "is old regulation X still valid?" / temporal applicability
- **Example signals:**
  ```
  tetap berlaku              → grandfathering
  masih tetap berlaku sepanjang → conditional continuation
  paling lama ... sejak ... diundangkan → grace period
  wajib menyesuaikan        → adaptation requirement
  dicabut dan dinyatakan tidak berlaku → revocation
  ```

### Type 9: SANCTION (Sanksi)
- **Location:** Bab Ketentuan Pidana / Sanksi Administratif
- **Pattern:** `dipidana`, `denda`, `sanksi administratif`, `pencabutan izin`
- **Output:** violation_reference + sanction_type + severity + amount
- **Use:** Link to obligations (consequence map), severity classification
- **Status:** ⚠️ Used in consequence_map but not standalone
- **Example signals:**
  ```
  dipidana dengan pidana ... paling lama → criminal
  denda paling banyak/sedikit → fine
  sanksi administratif berupa → admin sanction
  pencabutan izin            → license revocation
  teguran tertulis           → written warning
  ```

### Type 10: CONDITION (Syarat)
- **Location:** Paired with obligations or rights
- **Pattern:** `dengan syarat`, `apabila`, `dalam hal`, `jika`
- **Output:** trigger_condition + consequence_rule
- **Use:** Decision trees, conditional compliance ("if X then Y applies")
- **Example signals:**
  ```
  dengan syarat              → prerequisite
  apabila                    → conditional trigger
  dalam hal                  → contextual condition
  jika                       → if-trigger
  kecuali                    → exception condition
  sepanjang                  → bounded condition
  ```

---

## Implementation Priority

Based on user value and detection difficulty:

| Priority | Type | Value | Difficulty | Notes |
|----------|------|-------|------------|-------|
| P0 | OBLIGATION | ★★★★★ | Done | Core compliance |
| P0 | DEFINITION | ★★★★☆ | Done | Explanation layer |
| P1 | RIGHT | ★★★★★ | Low | Similar signals to obligation, high user value |
| P1 | THRESHOLD | ★★★★☆ | Low | Already detected, needs structured extraction |
| P2 | SCOPE | ★★★☆☆ | Medium | Critical for "does this apply?" questions |
| P2 | PROCEDURE | ★★★☆☆ | Medium | High value for "how to" questions |
| P2 | CONDITION | ★★★★☆ | Medium | Needed for decision trees |
| P3 | DELEGATION | ★★☆☆☆ | Low | Navigation aid, links regulations |
| P3 | SANCTION | ★★★☆☆ | Done (partial) | consequence_map already handles this |
| P4 | TRANSITIONAL | ★★☆☆☆ | Medium | Important for temporal questions |

---

## Detection Approach Per Type

All types follow the same 4-layer pattern proven by the norm compiler:

1. **Signal extraction** — regex patterns on provision text
2. **Classification** — decision tree using signal combinations
3. **Structured extraction** — parse the classified text into typed output
4. **Cross-reference** — link to related provisions (e.g., right ↔ obligation pairs)

For P1 items (RIGHT, THRESHOLD), we can extend the existing `extract_signals()` and `classify()` functions. The signal markers are already partially there (`berhak` is in OBLIGATION_MARKERS with 0.7 weight).

---

## Key Insight: Functions Are Not Mutually Exclusive

A single provision can serve multiple functions:
- "Pekerja **berhak** memperoleh upah **paling sedikit** sebesar UMP" 
  → RIGHT + THRESHOLD
- "Pengusaha **wajib** ... **paling lambat** 7 hari sebelum ..."
  → OBLIGATION + PROCEDURE + THRESHOLD
- "**Dalam hal** pekerja ... maka pengusaha **wajib** ..."
  → CONDITION + OBLIGATION

The compiler should tag provisions with ALL applicable types, not force a single classification.

---

## Relation to Current System

```
Current:  provision → [NORM | SOFT_NORM | THRESHOLD | DEFINITION | PROCEDURAL | REFERENCE]
                       (mutually exclusive single classification)

Proposed: provision → Set[OBLIGATION, RIGHT, SCOPE, PROCEDURE, THRESHOLD, ...]
                       (multi-label, each with structured extraction)
```

This means refactoring `classify()` from a decision tree returning one type to a tagger returning multiple types with confidence scores.
