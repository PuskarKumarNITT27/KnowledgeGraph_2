"""
utils/schema_inspector.py

Fast schema fetch — uses bulk APOC-style queries and Neo4j's built-in
schema procedures to get everything in as few round trips as possible.

Old approach : 1 query per label + 2 queries per relationship = 40+ round trips
New approach : 4 total queries regardless of how many labels/rels exist
"""

from typing import Tuple, Dict, List
from utils.query_extractor import _get_driver
import json
from pathlib import Path
CACHE_FILE = Path("schema_cache.json")


try:
    from neo4j.exceptions import Neo4jError, ServiceUnavailable
except ImportError:
    Neo4jError = Exception
    ServiceUnavailable = Exception


def load_schema_from_cache():
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r") as f:
                return True, json.load(f)
        except Exception:
            return False, "Cache read error"
    return False, "No cache found"


def save_schema_to_cache(schema: dict):
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(schema, f)
    except Exception:
        pass
    
    
def fetch_full_schema() -> Tuple[bool, Dict]:
    try:
        driver = _get_driver()

        with driver.session() as session:
            labels        = _bulk_get_labels(session)
            relationships = _bulk_get_relationships(session)
            totals        = _bulk_get_totals(session)

        driver.close()

        # ✅ CREATE SCHEMA OBJECT
        schema = {
            "labels":        labels,
            "relationships": relationships,
            "totals":        totals,
        }

        # ✅ SAVE TO CACHE (ADD THIS LINE)
        save_schema_to_cache(schema)

        # ✅ RETURN SAME AS BEFORE
        return True, schema

    except ServiceUnavailable as e:
        return False, f"Cannot reach Neo4j Aura: {e}"
    except Neo4jError as e:
        return False, f"Neo4j error: {e}"
    except Exception as e:
        return False, f"Unexpected error: {e}"

# ── Bulk queries (4 total) ────────────────────────────────────────────────────

def _bulk_get_labels(session) -> List[Dict]:
    """
    Query 1 — one sample node per label + count, all in a single query.

    Uses CALL { ... } IN TRANSACTIONS style supported in Neo4j 4.4+.
    Falls back to a simpler UNION query if that fails.
    """
    try:
        # Single query: for each label get count + one sample node
        result = session.run("""
            CALL db.labels() YIELD label
            CALL {
                WITH label
                MATCH (n)
                WHERE label IN labels(n)
                RETURN count(n) AS cnt, collect(n)[0] AS sample
            }
            RETURN label, cnt, sample
            ORDER BY label
        """)

        output = []
        for row in result:
            label  = row["label"]
            count  = row["cnt"]
            sample = row["sample"]

            props = []
            if sample:
                for key in sample.keys():
                    val = sample.get(key)
                    sample_val = str(val)[:80] + "…" if len(str(val)) > 80 else str(val)
                    props.append({"key": key, "sample": sample_val})

            output.append({"label": label, "count": count, "properties": props})

        return output

    except Exception:
        # Fallback: use schema() procedure which is always fast
        return _bulk_get_labels_fallback(session)


def _bulk_get_labels_fallback(session) -> List[Dict]:
    """
    Fallback Query 1b — uses db.schema.nodeTypeProperties() which is
    a single fast metadata call (no full graph scan).
    """
    try:
        result = session.run("""
            CALL db.schema.nodeTypeProperties()
            YIELD nodeType, nodeLabels, propertyName, propertyTypes
            RETURN nodeLabels[0] AS label,
                   collect({key: propertyName, sample: propertyTypes[0]}) AS properties
            ORDER BY label
        """)

        output = []
        seen = set()
        for row in result:
            label = row["label"]
            if label in seen:
                continue
            seen.add(label)

            props = [
                {"key": p["key"], "sample": f"[type: {p['sample']}]"}
                for p in row["properties"]
                if p["key"]
            ]
            output.append({"label": label, "count": "?", "properties": props})

        return output

    except Exception:
        # Last resort: just return label names with no properties
        res = session.run("CALL db.labels() YIELD label RETURN label ORDER BY label")
        return [
            {"label": r["label"], "count": "?", "properties": []}
            for r in res
        ]


def _bulk_get_relationships(session) -> List[Dict]:
    """
    Single query — gets all relationship types, real counts, and label-pairs at once.
    Skips the metadata-only approach (which cannot return counts) and goes straight
    to the counting query, which also gives us label pairs in the same pass.
    """
    try:
        result = session.run("""
            MATCH (a)-[r]->(b)
            WITH type(r)          AS rel_type,
                 labels(a)[0]     AS from_lbl,
                 labels(b)[0]     AS to_lbl,
                 count(r)         AS cnt
            RETURN rel_type,
                   collect(DISTINCT [from_lbl, to_lbl])[0..3] AS pairs,
                   sum(cnt) AS total_count
            ORDER BY rel_type
        """)
        output = []
        for row in result:
            pairs = [(p[0], p[1]) for p in row["pairs"]]
            output.append({
                "type":  row["rel_type"],
                "count": row["total_count"],
                "pairs": pairs,
            })
        return output

    except Exception:
        # Last resort — names only, no counts
        try:
            res = session.run(
                "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType ORDER BY relationshipType"
            )
            return [
                {"type": r["relationshipType"], "count": "?", "pairs": []}
                for r in res
            ]
        except Exception:
            return []


def _bulk_get_totals(session) -> Dict:
    """
    Query 4 — both totals in a single query using count store
    (instant — Neo4j keeps these cached, no graph scan).
    """
    try:
        result = session.run("""
            MATCH (n)
            WITH count(n) AS node_count
            MATCH ()-[r]->()
            RETURN node_count, count(r) AS rel_count
        """)
        row = result.single()
        return {
            "nodes":         row["node_count"],
            "relationships": row["rel_count"],
        }
    except Exception:
        return {"nodes": "?", "relationships": "?"}