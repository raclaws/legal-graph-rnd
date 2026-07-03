"""Stale reference detection — find provisions pointing to revoked regulations."""

from __future__ import annotations

from dataclasses import dataclass

from src.graph import LegalGraph


@dataclass
class StaleReference:
    source_id: str
    source_title: str
    revoked_target_id: str
    revoked_target_title: str
    replaced_by_id: str
    replaced_by_title: str


STALE_REF_QUERY = """
MATCH (source:Regulation)-[:REFERENCES]->(target:Regulation)<-[:REVOKES]-(replacement)
WHERE source <> replacement
RETURN source.node_id AS stale_source,
       source.title AS source_title,
       target.node_id AS revoked_target,
       target.title AS target_title,
       replacement.node_id AS replaced_by,
       replacement.title AS replacement_title
"""

STALE_REF_INLINE_QUERY = """
MATCH (target:Regulation)<-[:REVOKES]-(replacement)
WHERE target.node_id IS NOT NULL
WITH target, replacement
MATCH (provision:Provision)
WHERE provision.text CONTAINS target.title
  AND NOT EXISTS { MATCH (provision)<-[:CONTAINS*]-(replacement) }
RETURN provision.node_id AS provision_id,
       provision.text AS text,
       target.node_id AS revoked_target,
       target.title AS target_title,
       replacement.node_id AS replaced_by
LIMIT 50
"""


def find_stale_references(g: LegalGraph) -> list[StaleReference]:
    """Find regulation-level references pointing to revoked targets."""
    results = []
    with g.driver.session() as session:
        records = session.run(STALE_REF_QUERY)
        for r in records:
            results.append(StaleReference(
                source_id=r["stale_source"],
                source_title=r["source_title"],
                revoked_target_id=r["revoked_target"],
                revoked_target_title=r["target_title"],
                replaced_by_id=r["replaced_by"],
                replaced_by_title=r["replacement_title"],
            ))
    return results


def find_stale_inline_references(g: LegalGraph) -> list[dict]:
    """Find provision text that mentions a revoked regulation by name."""
    results = []
    with g.driver.session() as session:
        records = session.run(STALE_REF_INLINE_QUERY)
        for r in records:
            results.append({
                "provision_id": r["provision_id"],
                "text_snippet": (r["text"] or "")[:200],
                "revoked_target": r["revoked_target"],
                "target_title": r["target_title"],
                "replaced_by": r["replaced_by"],
            })
    return results


if __name__ == "__main__":
    g = LegalGraph()

    print("=== Stale Regulation-Level References ===")
    stale = find_stale_references(g)
    if stale:
        for s in stale:
            print(f"\n  {s.source_id} ({s.source_title})")
            print(f"    references REVOKED: {s.revoked_target_id} ({s.revoked_target_title})")
            print(f"    should reference: {s.replaced_by_id} ({s.replaced_by_title})")
    else:
        print("  No stale regulation-level references found.")

    print("\n=== Stale Inline Text References ===")
    inline = find_stale_inline_references(g)
    if inline:
        for item in inline:
            print(f"\n  {item['provision_id']}")
            print(f"    mentions: {item['target_title']} (REVOKED)")
            print(f"    text: {item['text_snippet'][:100]}...")
            print(f"    replaced by: {item['replaced_by']}")
    else:
        print("  No stale inline references found.")

    g.close()
