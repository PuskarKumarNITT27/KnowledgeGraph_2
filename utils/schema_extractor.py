from utils.query_extractor import run_neo4j_query

_cached_schema = None

def get_schema_text():
    global _cached_schema

    if _cached_schema is not None:
        return _cached_schema   # ✅ reuse cached schema

    # Fetch schema ONLY ONCE
    success_l, labels = run_neo4j_query("CALL db.labels()")
    labels_list = [r["label"] for r in labels] if success_l else []

    success_r, rels = run_neo4j_query("CALL db.relationshipTypes()")
    rels_list = [r["relationshipType"] for r in rels] if success_r else []

    # Limit size (important)
    labels_list = labels_list[:30]
    rels_list = rels_list[:50]

    _cached_schema = f"""
Node Labels:
{", ".join(labels_list)}

Relationships:
{", ".join(rels_list)}
"""

    return _cached_schema