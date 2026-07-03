"""Norm graph schema + migration from Python obligation files to Neo4j.

Graph schema:
    (:Pasal)-[:IMPOSES]->(:Norm {id, description, severity, consequence, effective_from, topic})
    (:Norm)-[:APPLIES_TO]->(:DocType {name})
    (:Norm)-[:REQUIRES]->(:NormEvidence {field_path, operator, value, description})
    (:Norm)-[:APPLIES_WHEN]->(:NormCondition {field, operator, value, description})
    (:Norm)-[:EXCEPTION]->(:NormEdgeCase {condition, behavior, legal_basis})

Reversible: MATCH (n) WHERE n:Norm OR n:NormEvidence OR n:NormCondition OR n:NormEdgeCase OR n:DocType DETACH DELETE n
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.compliance.obligations import Obligation, DocType
from src.compliance.obligations_pkwt import get_pkwt_obligations
from src.compliance.obligations_upah import get_upah_obligations
from src.graph import LegalGraph


def migrate_obligations_to_graph(obligations: list[Obligation], dry_run: bool = False) -> list[str]:
    """Write obligation objects into Neo4j as Norm nodes.

    Returns execution log.
    """
    if dry_run:
        return [f"{len(obligations)} obligations would be migrated"]

    log = []
    g = LegalGraph()

    with g.driver.session() as session:
        # Create DocType nodes
        for dt in DocType:
            session.run("MERGE (:DocType {name: $name})", name=dt.value)
        log.append(f"DocType nodes created: {len(DocType)}")

        for ob in obligations:
            # Create Norm node
            session.run(
                """MERGE (n:Norm {id: $id})
                   SET n.description = $description,
                       n.legal_basis = $legal_basis,
                       n.legal_text_summary = $legal_text_summary,
                       n.severity = $severity,
                       n.consequence = $consequence,
                       n.effective_from = $effective_from""",
                id=ob.id,
                description=ob.description,
                legal_basis=ob.legal_basis,
                legal_text_summary=ob.legal_text_summary,
                severity=ob.severity.value,
                consequence=ob.consequence,
                effective_from=ob.effective_from,
            )

            # Link to Pasal (IMPOSES)
            session.run(
                """MATCH (p:Provision {node_id: $node_id})
                   MATCH (n:Norm {id: $norm_id})
                   MERGE (p)-[:IMPOSES]->(n)""",
                node_id=ob.legal_basis,
                norm_id=ob.id,
            )

            # Link to DocTypes (APPLIES_TO)
            for dt in ob.applies_to:
                session.run(
                    """MATCH (n:Norm {id: $norm_id})
                       MATCH (d:DocType {name: $dt_name})
                       MERGE (n)-[:APPLIES_TO]->(d)""",
                    norm_id=ob.id,
                    dt_name=dt.value,
                )

            # Create Evidence nodes (REQUIRES)
            for i, ev in enumerate(ob.evidence):
                ev_id = f"{ob.id}_ev_{i}"
                session.run(
                    """MERGE (e:NormEvidence {id: $id})
                       SET e.field_path = $field_path,
                           e.operator = $operator,
                           e.value = $value,
                           e.description = $description""",
                    id=ev_id,
                    field_path=ev.field_path,
                    operator=ev.operator.value,
                    value=json.dumps(ev.value) if ev.value is not None else None,
                    description=ev.description,
                )
                session.run(
                    """MATCH (n:Norm {id: $norm_id})
                       MATCH (e:NormEvidence {id: $ev_id})
                       MERGE (n)-[:REQUIRES]->(e)""",
                    norm_id=ob.id,
                    ev_id=ev_id,
                )

            # Create Condition nodes (APPLIES_WHEN)
            for i, cond in enumerate(ob.conditions):
                cond_id = f"{ob.id}_cond_{i}"
                session.run(
                    """MERGE (c:NormCondition {id: $id})
                       SET c.field = $field,
                           c.operator = $operator,
                           c.value = $value,
                           c.description = $description""",
                    id=cond_id,
                    field=cond.field,
                    operator=cond.operator.value,
                    value=json.dumps(cond.value),
                    description=cond.description,
                )
                session.run(
                    """MATCH (n:Norm {id: $norm_id})
                       MATCH (c:NormCondition {id: $cond_id})
                       MERGE (n)-[:APPLIES_WHEN]->(c)""",
                    norm_id=ob.id,
                    cond_id=cond_id,
                )

            # Create EdgeCase nodes (EXCEPTION)
            for i, ec in enumerate(ob.edge_cases):
                ec_id = f"{ob.id}_ec_{i}"
                session.run(
                    """MERGE (ec:NormEdgeCase {id: $id})
                       SET ec.condition_text = $condition,
                           ec.behavior = $behavior,
                           ec.legal_basis = $legal_basis""",
                    id=ec_id,
                    condition=ec.condition,
                    behavior=ec.behavior,
                    legal_basis=ec.legal_basis,
                )
                session.run(
                    """MATCH (n:Norm {id: $norm_id})
                       MATCH (ec:NormEdgeCase {id: $ec_id})
                       MERGE (n)-[:EXCEPTION]->(ec)""",
                    norm_id=ob.id,
                    ec_id=ec_id,
                )

        log.append(f"Processed {len(obligations)} obligations")

    # Verify
    with g.driver.session() as session:
        r = session.run("MATCH (n:Norm) RETURN count(n) AS c")
        log.append(f"Norm nodes: {r.single()['c']}")
        r = session.run("MATCH (:Provision)-[:IMPOSES]->(:Norm) RETURN count(*) AS c")
        log.append(f"IMPOSES edges: {r.single()['c']}")
        r = session.run("MATCH (:Norm)-[:APPLIES_TO]->(:DocType) RETURN count(*) AS c")
        log.append(f"APPLIES_TO edges: {r.single()['c']}")
        r = session.run("MATCH (:Norm)-[:REQUIRES]->(:NormEvidence) RETURN count(*) AS c")
        log.append(f"REQUIRES edges: {r.single()['c']}")
        r = session.run("MATCH (:Norm)-[:EXCEPTION]->(:NormEdgeCase) RETURN count(*) AS c")
        log.append(f"EXCEPTION edges: {r.single()['c']}")

    g.close()
    return log


def rollback_norms():
    """Remove all norm nodes from graph. Corpus untouched."""
    g = LegalGraph()
    with g.driver.session() as session:
        session.run("MATCH (n) WHERE n:Norm OR n:NormEvidence OR n:NormCondition OR n:NormEdgeCase OR n:DocType DETACH DELETE n")
        r = session.run("MATCH (n:Norm) RETURN count(n) AS c")
        remaining = r.single()["c"]
    g.close()
    return f"Rollback complete. Remaining Norm nodes: {remaining}"


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        print(rollback_norms())
    elif len(sys.argv) > 1 and sys.argv[1] == "--dry-run":
        all_obs = get_pkwt_obligations() + get_upah_obligations()
        stmts = migrate_obligations_to_graph(all_obs, dry_run=True)
        print(f"{len(stmts)} statements would be executed")
        for s in stmts[:20]:
            print(f"  {s[:100]}")
    else:
        all_obs = get_pkwt_obligations() + get_upah_obligations()
        log = migrate_obligations_to_graph(all_obs)
        for line in log:
            print(line)
