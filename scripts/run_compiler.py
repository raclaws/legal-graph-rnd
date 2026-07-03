"""Run norm compiler against full corpus in Neo4j.

Pulls all provisions with text, runs signal extraction + classification,
builds consequence map, and outputs stats + candidate norms.
"""

import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.graph import LegalGraph
from src.compliance.norm_compiler import (
    compile_norms,
    build_consequence_map,
    resolve_consequence_map,
    extract_signals,
    classify,
    ProvisionType,
)


def fetch_all_provisions(graph: LegalGraph) -> list[dict]:
    """Fetch all provisions with text from Neo4j."""
    with graph.driver.session() as session:
        result = session.run(
            """
            MATCH (p:Provision)
            WHERE p.text IS NOT NULL AND p.text <> ''
            RETURN p.node_id AS node_id, p.text AS text
            ORDER BY p.node_id
            """
        )
        return [{"node_id": r["node_id"], "text": r["text"]} for r in result]


def fetch_all_node_ids(graph: LegalGraph) -> list[str]:
    """Fetch all provision node_ids for consequence map resolution."""
    with graph.driver.session() as session:
        result = session.run("MATCH (p:Provision) RETURN p.node_id AS node_id")
        return [r["node_id"] for r in result]


def main():
    g = LegalGraph()

    # Stats
    with g.driver.session() as session:
        total = session.run("MATCH (p:Provision) RETURN count(p) AS c").single()["c"]
        with_text = session.run(
            "MATCH (p:Provision) WHERE p.text IS NOT NULL AND p.text <> '' RETURN count(p) AS c"
        ).single()["c"]
    print(f"Corpus: {total} provisions total, {with_text} with text")

    # Fetch
    print("Fetching provisions...", end=" ", flush=True)
    provisions = fetch_all_provisions(g)
    all_node_ids = fetch_all_node_ids(g)
    print(f"got {len(provisions)}")

    # Classify all
    print("Classifying...", end=" ", flush=True)
    type_counts = Counter()
    for p in provisions:
        signals = extract_signals(p["text"])
        ptype = classify(signals)
        type_counts[ptype] += 1
    print("done")
    print(f"\nClassification breakdown:")
    for ptype, count in type_counts.most_common():
        print(f"  {ptype:15s}: {count}")

    # Build consequence map
    print("\nBuilding consequence map...", end=" ", flush=True)
    raw_cmap = build_consequence_map(provisions)
    cmap = resolve_consequence_map(raw_cmap, all_node_ids)
    print(f"{len(raw_cmap)} raw -> {len(cmap)} resolved")

    # Compile norms
    print("Compiling norms...", end=" ", flush=True)
    candidates = compile_norms(provisions, cmap)
    print(f"{len(candidates)} candidates")

    # Breakdown by confidence
    conf_counts = Counter(c.confidence for c in candidates)
    print(f"\nConfidence breakdown:")
    for conf, count in conf_counts.most_common():
        print(f"  {conf:10s}: {count}")

    # Breakdown by severity
    sev_counts = Counter(c.severity for c in candidates)
    print(f"\nSeverity breakdown:")
    for sev, count in sev_counts.most_common():
        print(f"  {sev:10s}: {count}")

    # Breakdown by provision type
    pt_counts = Counter(c.provision_type for c in candidates)
    print(f"\nProvision type breakdown:")
    for pt, count in pt_counts.most_common():
        print(f"  {pt:15s}: {count}")

    # With consequence linked
    with_consequence = sum(1 for c in candidates if c.consequence)
    print(f"\nWith consequence linked: {with_consequence}/{len(candidates)}")

    # Per-regulation breakdown
    print(f"\nPer-regulation candidate count (top 10):")
    reg_counts = Counter()
    for c in candidates:
        m = c.source.split("/")
        if len(m) >= 3:
            reg_counts[f"{m[0]}/{m[1]}/{m[2]}"] += 1
    for reg, count in reg_counts.most_common(10):
        print(f"  {reg:25s}: {count}")

    # Definitions (for explanation layer)
    definitions = [p for p in provisions if classify(extract_signals(p["text"])) == ProvisionType.DEFINITION]
    print(f"\nDefinition provisions (for explanation layer): {len(definitions)}")

    g.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
