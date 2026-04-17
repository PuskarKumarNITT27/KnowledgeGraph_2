"""
utils/query_extractor.py
Connects to Neo4j Aura, executes Cypher queries,
and optionally returns graph-ready node/edge data.
"""

import os
from typing import Tuple, Union, List, Dict

try:
    from neo4j import GraphDatabase
    from neo4j.exceptions import Neo4jError, ServiceUnavailable
    from neo4j.graph import Node, Relationship, Path   # ✅ ADDED Path
except ImportError:
    GraphDatabase = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ── Configuration ─────────────────────────────────────────────────────────────
NEO4J_URI      = os.getenv("NEO4J_URI", "neo4j+s://<your-aura-instance>.databases.neo4j.io")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")


# ── Public API ────────────────────────────────────────────────────────────────

def run_neo4j_query(query: str) -> Tuple[bool, Union[List[Dict], str]]:
    """
    Execute a Cypher query and return results as a list of plain dicts.
    Used for tabular display in the UI.
    """
    if GraphDatabase is None:
        return False, "neo4j driver is not installed. Run: pip install neo4j"

    if not NEO4J_PASSWORD:
        return False, "NEO4J_PASSWORD is not set. Add it to your .env file."

    try:
        driver = _get_driver()
        records = _execute_query(driver, query)
        driver.close()
        return True, records

    except ServiceUnavailable as exc:
        return False, f"Cannot reach Neo4j Aura — check URI and network: {exc}"
    except Neo4jError as exc:
        return False, f"Neo4j query error: {exc.message}"
    except Exception as exc:
        return False, f"Unexpected error: {exc}"


def run_neo4j_graph_query(query: str) -> Tuple[bool, Union[Dict, str]]:
    """
    Execute a Cypher query and return graph-ready data.
    """
    if GraphDatabase is None:
        return False, "neo4j driver is not installed. Run: pip install neo4j"

    if not NEO4J_PASSWORD:
        return False, "NEO4J_PASSWORD is not set. Add it to your .env file."

    try:
        driver = _get_driver()
        graph_data = _execute_graph_query(driver, query)
        driver.close()
        return True, graph_data

    except ServiceUnavailable as exc:
        return False, f"Cannot reach Neo4j Aura: {exc}"
    except Neo4jError as exc:
        return False, f"Neo4j query error: {exc.message}"
    except Exception as exc:
        return False, f"Unexpected error: {exc}"


# ── Internal helpers ──────────────────────────────────────────────────────────

def _get_driver():
    return GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USERNAME, NEO4J_PASSWORD),
    )


# ✅ NEW: serializer (fixes Arrow error)
def _serialize_value(value):
    if isinstance(value, Node):
        return dict(value)

    elif isinstance(value, Relationship):
        return value.type

    elif isinstance(value, Path):
        return " -> ".join(
            [n.get("id") or n.get("name") or "" for n in value.nodes]
        )

    return value


def _execute_query(driver, query: str) -> List[Dict]:
    """Run query and return results as plain dicts (for st.dataframe)."""
    with driver.session() as session:
        result = session.run(query)

        rows = []
        for record in result:
            row = {}
            for key, value in record.items():
                row[key] = _serialize_value(value)   # ✅ FIX APPLIED
            rows.append(row)

        return rows


def _execute_graph_query(driver, query: str) -> Dict:
    """
    Run query and extract nodes + relationships from the result.
    NOW handles Path also.
    """
    nodes_dict = {}
    edges_list = []

    with driver.session() as session:
        result = session.run(query)

        for record in result:
            for value in record.values():

                # ✅ HANDLE PATH (MAIN FIX)
                if isinstance(value, Path):

                    # Nodes
                    for node in value.nodes:
                        node_id = node.element_id
                        if node_id not in nodes_dict:
                            label = list(node.labels)[0] if node.labels else "Node"
                            display = (
                                node.get("name")
                                or node.get("title")
                                or node.get("id")
                                or label
                            )

                            nodes_dict[node_id] = {
                                "id": node_id,
                                "label": str(display),
                                "title": str(dict(node)),
                                "group": label,
                            }

                    # Relationships
                    for rel in value.relationships:
                        edges_list.append({
                            "source": rel.start_node.element_id,
                            "target": rel.end_node.element_id,
                            "label": rel.type,
                        })

                # Node
                elif isinstance(value, Node):
                    node_id = value.element_id
                    if node_id not in nodes_dict:
                        label = list(value.labels)[0] if value.labels else "Node"
                        display = (
                            value.get("name")
                            or value.get("title")
                            or value.get("id")
                            or label
                        )

                        nodes_dict[node_id] = {
                            "id": node_id,
                            "label": str(display),
                            "title": str(dict(value)),
                            "group": label,
                        }

                # Relationship
                elif isinstance(value, Relationship):
                    edges_list.append({
                        "source": value.start_node.element_id,
                        "target": value.end_node.element_id,
                        "label": value.type,
                    })

    return {
        "nodes": list(nodes_dict.values()),
        "edges": edges_list,
    }