# utils/template_generator.py

import json


def load_schema(schema_path="schema_cache.json"):
    with open(schema_path, "r") as f:
        return json.load(f)


def generate_single_hop_templates(schema_path="schema_cache.json"):
    schema = load_schema(schema_path)

    templates = []

    for rel in schema.get("relationships", []):
        rel_type = rel["type"]

        templates.append({
            "name": f"___ {rel_type} ___",
            "relation": rel_type,
            "query": (
                f"MATCH (a)-[r:{rel_type}]->(b)\n"
                "WHERE toLower(coalesce(a.id,'')) CONTAINS toLower('{SUBJECT}')\n"
                "RETURN a.id AS subject, type(r) AS relation, b.id AS object\n"
                "LIMIT {LIMIT}"
            )
        })

    return templates


def generate_multi_hop_templates(schema_path="schema_cache.json"):
    schema = load_schema(schema_path)

    rels = [r["type"] for r in schema.get("relationships", [])]

    templates = []

    for i in range(min(len(rels), 100)):
        for j in range(i + 1, min(i + 5, len(rels))):

            r1 = rels[i]
            r2 = rels[j]

            templates.append({
                "name": f"___ {r1} ___ → ___ {r2} ___",
                "r1": r1,
                "r2": r2,
                "query": (
                    f"MATCH (a)-[r1:{r1}]->(b)-[r2:{r2}]->(c)\n"
                    "WHERE toLower(coalesce(a.id,'')) CONTAINS toLower('{SUBJECT}')\n"
                    "RETURN a.id, type(r1), b.id, type(r2), c.id\n"
                    "LIMIT {LIMIT}"
                )
            })

    return templates