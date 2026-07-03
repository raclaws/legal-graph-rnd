---
name: precedence-algorithm
description: Algorithmic formalization of asas hukum for conflict resolution between provisions
metadata:
  type: project
---

## Legal Precedence Algorithm (2026-07-03)

**Why:** When two provisions give contradictory answers, the system needs a deterministic, explainable resolution. Indonesian legal doctrine provides clear rules — they just need formalization.

**How to apply:** This becomes the resolution layer when norm conflicts arise during compliance checking.

---

## Input

Two conflicting provisions A and B, each with:
- `reg_type`: UU | PERPPU | PP | PERPRES | PERMEN | PERDA
- `year`: enactment year
- `number`: regulation number
- `scope`: general | specific (derived from position in hierarchy)
- `amendment_of`: nullable FK to parent regulation it amends
- `revoked_by`: nullable FK if explicitly revoked

## Decision Tree

```
resolve(A, B):

  1. REVOCATION CHECK
     if A.revoked_by is not null → B wins (A is dead law)
     if B.revoked_by is not null → A wins

  2. LEX SUPERIOR (hierarchy rank)
     rank = {UU: 1, PERPPU: 1, PP: 2, PERPRES: 3, PERMEN: 4, PERDA_PROV: 5, PERDA_KAB: 6}
     if rank(A) < rank(B) → A wins (higher authority)
     if rank(B) < rank(A) → B wins

  3. LEX SPECIALIS (specificity)
     if A is implementing regulation of B → A wins
       (detected via: A.amendment_of == B, or IMPLEMENTS edge in graph)
     if B is implementing regulation of A → B wins
     
     if A covers narrower subject than B → A wins
       (detected via: A has fewer provisions, or A's title targets specific topic
        that B's title covers broadly)
     
  4. LEX POSTERIOR (temporal)
     if same rank AND same scope:
       if A.year > B.year → A wins (newer)
       if B.year > A.year → B wins
       if same year: A.number > B.number → A wins (later in same year)

  5. AMBIGUITY (cannot resolve)
     → flag both, return confidence: "ambiguous"
     → apply IN DUBIO PRO OPERARIO (favor worker) as tiebreaker
       if A favors worker → A wins
       if B favors worker → B wins
       else → return both with explanation
```

## Properties

- **Deterministic**: same inputs always produce same output
- **Explainable**: every decision cites which asas was applied
- **Conservative**: only declares a winner when doctrine clearly supports it
- **Auditable**: returns the full decision path, not just the winner

## Output

```python
@dataclass
class Resolution:
    winner: str           # node_id of winning provision
    loser: str            # node_id of losing provision
    asas_applied: str     # "lex_superior" | "lex_specialis" | "lex_posterior" | "revoked" | "in_dubio_pro_operario"
    confidence: str       # "certain" | "high" | "ambiguous"
    explanation: str      # human-readable: "PP 35/2021 Ps.8 prevails over UU 13/2003 Ps.59 (lex posterior + lex specialis: PP is implementing regulation enacted after UU)"
```

## Design Principle

**Mechanical by default, explicit edges for edge cases.**

- Steps 1, 2, 4 are purely algorithmic (rank lookup, year comparison, revocation flag)
- Step 3a (implementing regulation) uses structural `IMPLEMENTS` edges from the graph
- Step 3b (narrower scope / lex specialis) is NOT inferred — requires an explicit `SUPERSEDES` edge added via curation
- Conflict detection is NOT automatic — conflicts surface as duplicate/contradictory norms in compiler output, which is the signal to add a `CONFLICTS_WITH` edge manually

The system only resolves conflicts it knows about via graph edges. No semantic inference, no embeddings, no LLM in the resolution path. Every decision traces to either a structural rule or a human-curated edge.

Unknown conflicts appearing in output = curation queue item.

---

## Edge Cases

### Amendment chains
PP 51/2023 amends PP 36/2021 which implements UU 6/2023 (Cipta Kerja) which amends UU 13/2003.
- PP 51/2023 Pasal X vs PP 36/2021 Pasal X → PP 51 wins (lex posterior, explicit amendment)
- PP 51/2023 vs UU 13/2003 → PP 51 wins (lex specialis via amendment chain)
- But: PP cannot contradict its parent UU — if PP exceeds UU's delegation, UU wins (ultra vires)

### Parallel specificity
PP 35/2021 (PKWT) vs PP 36/2021 (Upah) — both same rank, same year, different scope.
- Not in conflict if they cover different topics
- If overlap (e.g. "upah for PKWT workers"): the one whose BAB specifically addresses the topic wins

### PERPPU edge case
PERPPU has UU-level authority but is temporary. If confirmed as UU (like Perppu 2/2022 → UU 6/2023), treat as UU from confirmation date.

## Graph Encoding

Required metadata on Regulation nodes:
```
(:Regulation {
  node_id, type, year, number,
  hierarchy_rank: int,        // 1-6 from rank table
  amends: [node_id],          // explicit amendment targets
  implements: [node_id],      // delegation source
  revoked: boolean,
  revoked_by: node_id | null,
  confirmed_as: node_id | null  // PERPPU → UU
})
```

Required edges (some already exist):
- `AMENDS` — with {pasal_scope: [...]} to know which provisions are affected
- `IMPLEMENTS` — delegation relationship
- `REVOKES` — explicit revocation
- `SUPERSEDES` — computed from algorithm output (cached resolution)

## Implementation Plan

1. Add `hierarchy_rank` to existing Regulation nodes (one-time migration)
2. Enrich `AMENDS` edges with pasal-level scope (from parser: "Ketentuan Pasal X diubah")  
3. Implement `resolve(A, B)` as pure function (no DB needed beyond metadata)
4. Cache results as `SUPERSEDES` edges for fast lookup during compliance
5. Surface in UI: when Hukum shows a provision, note if it supersedes an older one

## Future: Jurisprudence Tiebreaker (Step 6)

When step 5 returns "ambiguous", the real tiebreaker is court precedent — how judges actually resolved the conflict.

```
6. JURISPRUDENCE
   if conflict previously adjudicated:
     → winner = provision favored by court
     → cite: case number, court level, date
     → confidence: "jurisprudence"
```

Requires:
- Ingest putusan from SIPP Mahkamah Agung / direktori putusan
- Extract: which Pasal in conflict + court's resolution + reasoning
- Store as `RESOLVED_BY` edge with case metadata

This is a separate R&D track — parked until regulation layer is stable.

---

## Relation to Norm Compiler

Currently the compiler doesn't check for conflicts — it compiles ALL provisions independently. With this algorithm:
- After compilation, run pairwise conflict detection on norms covering same topic
- Auto-resolve using the tree above
- Flag `ambiguous` cases for human review
- Only the "winner" norm is used in compliance evaluation

This prevents contradictory results like "max PKWT is 3 years AND 5 years".
