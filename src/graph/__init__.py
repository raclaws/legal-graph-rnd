"""Neo4j graph operations for the legal knowledge graph."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

from neo4j import GraphDatabase

from src.schema import Node, NodeID, Regulation


def _load_env():
    """Load .env file if present."""
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())


_load_env()

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "")


class EdgeType(Enum):
    IMPLEMENTS = "IMPLEMENTS"
    AMENDS = "AMENDS"
    REVOKES = "REVOKES"
    REFERENCES = "REFERENCES"
    CONFLICTS_WITH = "CONFLICTS_WITH"
    SUPERSEDES = "SUPERSEDES"
    SPECIALIZES = "SPECIALIZES"


@dataclass
class Edge:
    source: NodeID
    target: NodeID
    edge_type: EdgeType
    confidence: float = 1.0
    enacted: Optional[str] = None


class LegalGraph:
    def __init__(self, uri: str = NEO4J_URI, user: str = NEO4J_USER, password: str = NEO4J_PASSWORD):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def create_constraints(self):
        with self.driver.session() as session:
            session.run(
                "CREATE CONSTRAINT node_id_unique IF NOT EXISTS "
                "FOR (n:Provision) REQUIRE n.node_id IS UNIQUE"
            )
            session.run(
                "CREATE CONSTRAINT reg_id_unique IF NOT EXISTS "
                "FOR (r:Regulation) REQUIRE r.node_id IS UNIQUE"
            )

    def ingest_regulation(self, reg: Regulation):
        """Load a parsed regulation into the graph."""
        with self.driver.session() as session:
            # Create regulation node
            session.run(
                """
                MERGE (r:Regulation {node_id: $node_id})
                SET r.type = $type,
                    r.number = $number,
                    r.year = $year,
                    r.title = $title
                """,
                node_id=str(reg.node_id),
                type=reg.reg_type.value,
                number=reg.number,
                year=reg.year,
                title=reg.title,
            )

            # Create provision nodes
            for node in reg.batang_tubuh:
                self._ingest_node(session, node, str(reg.node_id))

            # Create dasar_hukum edges (explicit REFERENCES)
            for ref in reg.pembukaan.dasar_hukum:
                if ref.resolved_id:
                    session.run(
                        """
                        MATCH (source:Regulation {node_id: $source_id})
                        MERGE (target:Regulation {node_id: $target_id})
                        MERGE (source)-[:REFERENCES {confidence: 1.0}]->(target)
                        """,
                        source_id=str(reg.node_id),
                        target_id=str(ref.resolved_id),
                    )

    def _ingest_node(self, session, node: Node, parent_id: str):
        """Recursively create provision nodes."""
        session.run(
            """
            MERGE (n:Provision {node_id: $node_id})
            SET n.type = $type,
                n.number = $number,
                n.title = $title,
                n.text = $text
            WITH n
            MATCH (p {node_id: $parent_id})
            MERGE (p)-[:CONTAINS]->(n)
            """,
            node_id=str(node.id),
            type=node.node_type.value,
            number=node.number,
            title=node.title,
            text=node.text,
            parent_id=parent_id,
        )
        for child in node.children:
            self._ingest_node(session, child, str(node.id))

    def add_edge(self, edge: Edge):
        """Create a typed relationship between two nodes."""
        with self.driver.session() as session:
            session.run(
                f"""
                MATCH (source {{node_id: $source_id}})
                MATCH (target {{node_id: $target_id}})
                MERGE (source)-[r:{edge.edge_type.value}]->(target)
                SET r.confidence = $confidence,
                    r.enacted = $enacted
                """,
                source_id=str(edge.source),
                target_id=str(edge.target),
                confidence=edge.confidence,
                enacted=edge.enacted,
            )

    def query_implements(self, regulation_id: str) -> list[dict]:
        """Find all regulations that implement a given regulation."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (r:Regulation {node_id: $reg_id})<-[:IMPLEMENTS]-(impl)
                RETURN impl.node_id AS id, impl.title AS title
                """,
                reg_id=regulation_id,
            )
            return [dict(record) for record in result]

    def query_point_in_time(self, node_id: str, as_of: str) -> Optional[dict]:
        """Get the state of a provision at a specific date."""
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (n {node_id: $node_id})
                WHERE (n.enacted IS NULL OR n.enacted <= $as_of)
                  AND (n.revoked IS NULL OR n.revoked > $as_of)
                RETURN n
                """,
                node_id=node_id,
                as_of=as_of,
            )
            record = result.single()
            return dict(record["n"]) if record else None
