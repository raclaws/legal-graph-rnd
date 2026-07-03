"""Graph service — Neo4j queries for the API."""

from __future__ import annotations

from src.graph import LegalGraph


def get_provision(node_id: str) -> dict | None:
    try:
        g = LegalGraph()
        with g.driver.session() as session:
            # Try exact match first
            r = session.run(
                """MATCH (p:Provision {node_id: $nid})
                   OPTIONAL MATCH (parent)-[:CONTAINS]->(p)
                   OPTIONAL MATCH (p)-[:CONTAINS]->(child)
                   OPTIONAL MATCH (p)-[:IMPOSES]->(n:Norm)
                   RETURN p, parent.node_id AS parent_id,
                          collect(DISTINCT {node_id: child.node_id, type: child.type, number: child.number, text: child.text}) AS children,
                          collect(DISTINCT {id: n.id, description: n.description, severity: n.severity}) AS norms""",
                nid=node_id,
            )
            rec = r.single()

            # If not found, try scoped fuzzy match (LLM often omits Bab segment)
            if not rec or rec["p"] is None:
                parts = node_id.split("/")
                if len(parts) >= 3:
                    reg_prefix = "/".join(parts[:3])
                    rest = "/" + "/".join(parts[3:])
                    pasal_idx = rest.find("/Pasal/")
                    pasal_part = rest[pasal_idx:] if pasal_idx >= 0 else ""
                    if pasal_part:
                        r = session.run(
                            """MATCH (p:Provision) WHERE p.node_id STARTS WITH $prefix AND p.node_id ENDS WITH $suffix
                               WITH p LIMIT 1
                               OPTIONAL MATCH (parent)-[:CONTAINS]->(p)
                               OPTIONAL MATCH (p)-[:CONTAINS]->(child)
                               OPTIONAL MATCH (p)-[:IMPOSES]->(n:Norm)
                               RETURN p, parent.node_id AS parent_id,
                                      collect(DISTINCT {node_id: child.node_id, type: child.type, number: child.number, text: child.text}) AS children,
                                      collect(DISTINCT {id: n.id, description: n.description, severity: n.severity}) AS norms""",
                            prefix=reg_prefix,
                            suffix=pasal_part,
                        )
                        rec = r.single()

            if not rec or rec["p"] is None:
                return None

            p = rec["p"]
            children = [c for c in rec["children"] if c["node_id"] is not None]

            result = {
                "node_id": p["node_id"],
                "type": p.get("type", ""),
                "number": p.get("number", ""),
                "text": p.get("text"),
                "parent": rec["parent_id"],
                "children": children,
                "norms_derived": [n for n in rec["norms"] if n["id"] is not None],
            }
        g.close()
        return result
    except Exception:
        return None


def validate_citations(node_ids: list[str]) -> dict[str, bool]:
    """Check which node_ids actually exist in the graph. Returns {node_id: exists}."""
    if not node_ids:
        return {}

    results = {nid: False for nid in node_ids}

    try:
        g = LegalGraph()
        with g.driver.session() as session:
            for nid in node_ids:
                # Exact match
                r = session.run(
                    "MATCH (p:Provision {node_id: $nid}) RETURN p.node_id LIMIT 1",
                    nid=nid,
                )
                if r.single():
                    results[nid] = True
                    continue

                # Fuzzy match (without Bab)
                parts = nid.split("/")
                if len(parts) >= 3:
                    reg_prefix = "/".join(parts[:3])
                    rest = "/" + "/".join(parts[3:])
                    pasal_idx = rest.find("/Pasal/")
                    pasal_part = rest[pasal_idx:] if pasal_idx >= 0 else ""
                    if pasal_part:
                        r = session.run(
                            "MATCH (p:Provision) WHERE p.node_id STARTS WITH $prefix AND p.node_id ENDS WITH $suffix RETURN p.node_id LIMIT 1",
                            prefix=reg_prefix,
                            suffix=pasal_part,
                        )
                        if r.single():
                            results[nid] = True
        g.close()
    except Exception:
        pass

    return results
    try:
        g = LegalGraph()
        with g.driver.session() as session:
            r = session.run("MATCH (p:Provision) RETURN count(p) AS provisions")
            provisions = r.single()["provisions"]
            r = session.run("MATCH (r:Regulation) RETURN count(r) AS regulations")
            regulations = r.single()["regulations"]
            r = session.run("MATCH (n:Norm) RETURN count(n) AS norms")
            norms = r.single()["norms"]
        g.close()
        return {"provisions": provisions, "regulations": regulations, "norms": norms}
    except Exception:
        return {"provisions": 0, "regulations": 0, "norms": 0}
