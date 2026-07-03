"""Graph service — Neo4j queries for the API."""

from __future__ import annotations

from src.graph import LegalGraph


def get_provision(node_id: str) -> dict | None:
    try:
        g = LegalGraph()
        with g.driver.session() as session:
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
            if not rec:
                return None

            p = rec["p"]
            children = [c for c in rec["children"] if c["node_id"] is not None]

            return {
                "node_id": p["node_id"],
                "type": p.get("type", ""),
                "number": p.get("number", ""),
                "text": p.get("text"),
                "parent": rec["parent_id"],
                "children": children,
                "norms_derived": [n for n in rec["norms"] if n["id"] is not None],
            }
        g.close()
    except Exception:
        return None


def get_graph_stats() -> dict:
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
